"""Banco SQLite e processamento cronológico incremental dos ratings."""
from __future__ import annotations

import sqlite3
from collections import defaultdict
from datetime import date, datetime
from math import log
from pathlib import Path

from .glicko2 import Rating, OpponentResult, expected_score, update
from .competitions import BRAZILIAN_STATE_BY_COMPETITION, COMPETITION_NAMES
from .club_identity import alias_key, canonical_name
from .neutral_sites import is_neutral_event

COMPETITIONS = COMPETITION_NAMES
HOME_ADVANTAGE = 80.0
GOAL_MARGIN_WEIGHT_COEFFICIENT = 0.5
MAX_GOAL_MARGIN_WEIGHT = 1.8
RATING_MODEL_VERSION = "glicko2-home80-goal-margin-knockout-v4"
MAX_INACTIVITY_DAYS = 90
MAX_RANKING_RD = 120.0

COMPETITION_CHECK = ", ".join(repr(competition) for competition in sorted(COMPETITIONS))
MATCHES_TABLE = f"""CREATE TABLE matches (
  external_id TEXT PRIMARY KEY, played_at TEXT NOT NULL, competition TEXT NOT NULL,
  matchday INTEGER, neutral_site INTEGER NOT NULL DEFAULT 0, home_advantage REAL NOT NULL DEFAULT 80, venue_country TEXT, stage TEXT, group_name TEXT,
  home_club_id INTEGER NOT NULL REFERENCES clubs(id), away_club_id INTEGER NOT NULL REFERENCES clubs(id),
  home_goals INTEGER NOT NULL CHECK(home_goals >= 0), away_goals INTEGER NOT NULL CHECK(away_goals >= 0),
  CHECK(home_club_id <> away_club_id), CHECK(competition IN ({COMPETITION_CHECK}))
);"""

SCHEMA = f"""
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS clubs (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, crest_url TEXT, country TEXT, state TEXT, primary_color TEXT
);
CREATE TABLE IF NOT EXISTS club_aliases (
  alias_key TEXT NOT NULL, country_key TEXT NOT NULL, club_id INTEGER NOT NULL REFERENCES clubs(id),
  PRIMARY KEY(alias_key, country_key)
);
CREATE TABLE IF NOT EXISTS matches {MATCHES_TABLE[MATCHES_TABLE.index('('):]}
CREATE TABLE IF NOT EXISTS rating_snapshots (
  period_date TEXT NOT NULL, club_id INTEGER NOT NULL REFERENCES clubs(id),
  rating REAL NOT NULL, rd REAL NOT NULL, volatility REAL NOT NULL,
  PRIMARY KEY(period_date, club_id)
);
CREATE TABLE IF NOT EXISTS match_rating_effects (
  external_id TEXT NOT NULL REFERENCES matches(external_id), club_id INTEGER NOT NULL REFERENCES clubs(id),
  rating_before REAL NOT NULL, rating_after REAL NOT NULL, rating_effect REAL NOT NULL,
  PRIMARY KEY(external_id, club_id)
);
CREATE TABLE IF NOT EXISTS match_forecasts (
  external_id TEXT PRIMARY KEY REFERENCES matches(external_id),
  home_expected REAL NOT NULL, away_expected REAL NOT NULL, home_score REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS rating_states (
  club_id INTEGER PRIMARY KEY REFERENCES clubs(id), rating REAL NOT NULL, rd REAL NOT NULL,
  volatility REAL NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS processed_matches (
  external_id TEXT PRIMARY KEY REFERENCES matches(external_id), processed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rating_model (
  singleton INTEGER PRIMARY KEY CHECK(singleton = 1), version TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS model_evaluations (
  version TEXT PRIMARY KEY, evaluated_at TEXT NOT NULL, payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fixtures (
  external_id TEXT PRIMARY KEY, scheduled_at TEXT NOT NULL, competition TEXT NOT NULL,
  status TEXT NOT NULL, matchday INTEGER, neutral_site INTEGER NOT NULL DEFAULT 0, home_advantage REAL NOT NULL DEFAULT 80, venue_country TEXT, stage TEXT, group_name TEXT, home_club_id INTEGER NOT NULL REFERENCES clubs(id),
  away_club_id INTEGER NOT NULL REFERENCES clubs(id)
);
CREATE TABLE IF NOT EXISTS source_payloads (
  id INTEGER PRIMARY KEY, source TEXT NOT NULL, request_path TEXT NOT NULL,
  fetched_at TEXT NOT NULL, payload TEXT NOT NULL
);
"""


def connect(path: str | Path) -> sqlite3.Connection:
    database = sqlite3.connect(path)
    database.row_factory = sqlite3.Row
    return database


def initialise(database: sqlite3.Connection) -> None:
    database.executescript(SCHEMA)
    columns = {row["name"] for row in database.execute("PRAGMA table_info(clubs)")}
    if "crest_url" not in columns:
        database.execute("ALTER TABLE clubs ADD COLUMN crest_url TEXT")
    if "country" not in columns:
        database.execute("ALTER TABLE clubs ADD COLUMN country TEXT")
    if "state" not in columns:
        database.execute("ALTER TABLE clubs ADD COLUMN state TEXT")
    if "primary_color" not in columns:
        database.execute("ALTER TABLE clubs ADD COLUMN primary_color TEXT")
    for table in ("matches", "fixtures"):
        columns = {row["name"] for row in database.execute(f"PRAGMA table_info({table})")}
        for column, kind in (("matchday", "INTEGER"), ("neutral_site", "INTEGER NOT NULL DEFAULT 0"), ("home_advantage", "REAL NOT NULL DEFAULT 80"), ("venue_country", "TEXT"), ("stage", "TEXT"), ("group_name", "TEXT")):
            if column not in columns:
                database.execute(f"ALTER TABLE {table} ADD COLUMN {column} {kind}")
    _infer_historical_club_states(database)
    reconcile_club_identities(database)
    database.execute("DELETE FROM fixtures WHERE external_id IN (SELECT external_id FROM matches)")
    database.commit()


def _register_alias(database: sqlite3.Connection, alias: str, country: str | None, club_id: int) -> None:
    key = alias_key(alias)
    country_key = _country_key(country) or ""
    existing = database.execute(
        "SELECT club_id FROM club_aliases WHERE alias_key=? AND country_key=?", (key, country_key)
    ).fetchone()
    if existing is None:
        database.execute(
            "INSERT INTO club_aliases(alias_key, country_key, club_id) VALUES (?, ?, ?)",
            (key, country_key, club_id),
        )


def register_club_alias(database: sqlite3.Connection, alias: str, country: str | None, club_id: int) -> None:
    """Registra uma equivalência confirmada por uma partida conciliada."""
    _register_alias(database, alias, country, club_id)


def _club_id(database: sqlite3.Connection, name: str, crest_url: str | None = None, country: str | None = None, state: str | None = None) -> int:
    country_key = _country_key(country)
    key = alias_key(name)
    alias = database.execute(
        "SELECT club_id FROM club_aliases WHERE alias_key=? AND country_key=?", (key, country_key or "")
    ).fetchone()
    target_name = canonical_name(name, country_key)
    if alias:
        club_id = int(alias["club_id"])
    else:
        database.execute("INSERT OR IGNORE INTO clubs(name) VALUES (?)", (target_name,))
        club_id = int(database.execute("SELECT id FROM clubs WHERE name=?", (target_name,)).fetchone()[0])
        _register_alias(database, target_name, country, club_id)
        _register_alias(database, name, country, club_id)
    if crest_url:
        database.execute("UPDATE clubs SET crest_url=? WHERE id=?", (crest_url, club_id))
    if country:
        database.execute("UPDATE clubs SET country=? WHERE id=?", (country, club_id))
    if state and country_key == "BR":
        database.execute("UPDATE clubs SET state=? WHERE id=?", (state, club_id))
    return club_id


COUNTRY_KEYS = {
    "argentina": "AR", "bolivia": "BO", "bolívia": "BO", "brasil": "BR", "brazil": "BR",
    "chile": "CL", "colombia": "CO", "colômbia": "CO", "ecuador": "EC", "equador": "EC",
    "paraguay": "PY", "paraguai": "PY", "peru": "PE", "perú": "PE", "uruguay": "UY",
    "uruguai": "UY", "venezuela": "VE",
}


def _country_key(country: str | None) -> str | None:
    return COUNTRY_KEYS.get((country or "").strip().lower())


def _clear_rating_rebuild_state(database: sqlite3.Connection) -> None:
    """Força reconstrução após mudar a identidade histórica de um clube."""
    for table in ("match_rating_effects", "match_forecasts", "rating_snapshots", "rating_states", "processed_matches", "rating_model", "model_evaluations"):
        database.execute(f"DELETE FROM {table}")


def _infer_historical_club_states(database: sqlite3.Connection) -> None:
    """Preenche UF somente quando o histórico estadual oferece uma evidência única."""
    rows = database.execute(
        """SELECT m.competition, m.home_club_id AS club_id FROM matches m
           UNION ALL SELECT m.competition, m.away_club_id FROM matches m
           UNION ALL SELECT f.competition, f.home_club_id FROM fixtures f
           UNION ALL SELECT f.competition, f.away_club_id FROM fixtures f"""
    ).fetchall()
    states: dict[int, set[str]] = defaultdict(set)
    for row in rows:
        state = BRAZILIAN_STATE_BY_COMPETITION.get(str(row["competition"]))
        if state:
            states[int(row["club_id"])].add(state)
    for club_id, candidates in states.items():
        if len(candidates) == 1:
            database.execute(
                "UPDATE clubs SET state=COALESCE(state, ?) WHERE id=? AND country IN ('Brasil', 'Brazil')",
                (next(iter(candidates)), club_id),
            )


def _merge_club(database: sqlite3.Connection, source_id: int, target_id: int) -> bool:
    if source_id == target_id:
        return False
    # Não há confronto válido de um clube contra si; esta proteção impede que
    # uma equivalência incorreta torne a tabela de partidas inconsistente.
    same_match = database.execute(
        "SELECT 1 FROM matches WHERE (home_club_id=? AND away_club_id=?) OR (home_club_id=? AND away_club_id=?) LIMIT 1",
        (source_id, target_id, target_id, source_id),
    ).fetchone()
    if same_match:
        return False
    source_state, target_state = database.execute(
        "SELECT state FROM clubs WHERE id IN (?, ?) ORDER BY id", (source_id, target_id)
    ).fetchall()
    if source_state["state"] and target_state["state"] and source_state["state"] != target_state["state"]:
        return False
    database.execute("UPDATE matches SET home_club_id=? WHERE home_club_id=?", (target_id, source_id))
    database.execute("UPDATE matches SET away_club_id=? WHERE away_club_id=?", (target_id, source_id))
    database.execute("UPDATE fixtures SET home_club_id=? WHERE home_club_id=?", (target_id, source_id))
    database.execute("UPDATE fixtures SET away_club_id=? WHERE away_club_id=?", (target_id, source_id))
    database.execute("UPDATE club_aliases SET club_id=? WHERE club_id=?", (target_id, source_id))
    database.execute("DELETE FROM clubs WHERE id=?", (source_id,))
    return True


def _remove_duplicate_matches(database: sqlite3.Connection) -> int:
    """Remove cópias da mesma partida criadas antes da identidade canônica.

    ESPN é preferida quando disponível, pois traz o horário e metadados mais
    completos; caso contrário, preservamos o menor identificador estável.
    """
    rows = database.execute(
        """SELECT external_id, competition, substr(played_at, 1, 10) AS game_date,
                  home_club_id, away_club_id, home_goals, away_goals
           FROM matches ORDER BY CASE WHEN external_id LIKE 'espn:%' THEN 0 ELSE 1 END, external_id"""
    ).fetchall()
    seen: set[tuple[object, ...]] = set()
    duplicate_ids: list[str] = []
    for row in rows:
        key = tuple(row[column] for column in ("competition", "game_date", "home_club_id", "away_club_id", "home_goals", "away_goals"))
        if key in seen:
            duplicate_ids.append(str(row["external_id"]))
        else:
            seen.add(key)
    for external_id in duplicate_ids:
        database.execute("DELETE FROM matches WHERE external_id=?", (external_id,))
    return len(duplicate_ids)


def reconcile_club_identities(database: sqlite3.Connection) -> tuple[int, int]:
    """Consolida aliases conhecidos e prepara o banco para novas fontes.

    A rotina é idempotente e conservadora: somente aliases explicitamente
    registrados são unidos. Homônimos permanecem separados por padrão.
    """
    club_rows = database.execute("SELECT id, name, country, state FROM clubs ORDER BY id").fetchall()
    by_name = {str(row["name"]): row for row in club_rows}
    merges: list[tuple[int, int]] = []
    for row in club_rows:
        target_name = canonical_name(str(row["name"]), _country_key(row["country"]))
        target = by_name.get(target_name)
        if target and int(target["id"]) != int(row["id"]):
            merges.append((int(row["id"]), int(target["id"])))
    if not merges:
        for row in club_rows:
            _register_alias(database, str(row["name"]), row["country"], int(row["id"]))
        return 0, 0
    _clear_rating_rebuild_state(database)
    merged = 0
    for source_id, target_id in merges:
        source_exists = database.execute("SELECT 1 FROM clubs WHERE id=?", (source_id,)).fetchone()
        target_exists = database.execute("SELECT 1 FROM clubs WHERE id=?", (target_id,)).fetchone()
        if source_exists and target_exists and _merge_club(database, source_id, target_id):
            merged += 1
    for row in database.execute("SELECT id, name, country FROM clubs"):
        _register_alias(database, str(row["name"]), row["country"], int(row["id"]))
    return merged, _remove_duplicate_matches(database)


def identity_candidates(database: sqlite3.Connection) -> list[dict[str, object]]:
    """Lista nomes parecidos para revisão humana; nunca faz fusão automática."""
    suffixes = {"ac", "ad", "aa", "ca", "cr", "ec", "fc", "sc", "se", "clube", "esporte", "esportes", "futebol"}
    groups: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for row in database.execute("SELECT name, country, state FROM clubs WHERE country IN ('Brasil', 'Brazil')"):
        tokens = [token for token in alias_key(str(row["name"])).split() if token not in suffixes]
        if tokens:
            groups[("BR", str(row["state"] or "?"), " ".join(tokens))].append(str(row["name"]))
    return [
        {"state": state, "key": key, "clubs": sorted(names)}
        for (_, state, key), names in groups.items() if len(set(names)) > 1
    ]


def _home_advantage(match: dict[str, str]) -> float:
    if bool(match.get("neutral_site")) or is_neutral_event(match["external_id"]):
        return 0.0
    venue, home, away = (_country_key(match.get(key)) for key in ("venue_country", "home_country", "away_country"))
    if venue and home and away:
        if venue == home:
            return HOME_ADVANTAGE
        if venue == away:
            return -HOME_ADVANTAGE
        return 0.0
    return HOME_ADVANTAGE


def store_match(database: sqlite3.Connection, match: dict[str, str]) -> None:
    competition = match["competition"].strip()
    if competition not in COMPETITIONS:
        raise ValueError(f"Competição fora do escopo do MVP: {competition}")
    played_at = match["played_at"]
    datetime.fromisoformat(played_at.replace("Z", "+00:00"))
    inferred_state = BRAZILIAN_STATE_BY_COMPETITION.get(competition)
    home = _club_id(database, match["home_team"], match.get("home_crest"), match.get("home_country"), match.get("home_state") or inferred_state)
    away = _club_id(database, match["away_team"], match.get("away_crest"), match.get("away_country"), match.get("away_state") or inferred_state)
    matchday = int(match["matchday"]) if match.get("matchday") else None
    home_advantage = _home_advantage(match)
    neutral_site = int(home_advantage == 0)
    values = (played_at, competition, matchday, neutral_site, home_advantage, match.get("venue_country"), match.get("stage"), match.get("group_name"), home, away, int(match["home_goals"]), int(match["away_goals"]))
    previous = database.execute(
        "SELECT played_at, competition, matchday, neutral_site, home_advantage, venue_country, stage, group_name, home_club_id, away_club_id, home_goals, away_goals FROM matches WHERE external_id=?",
        (match["external_id"],),
    ).fetchone()
    if previous and tuple(previous) == values:
        return
    database.execute(
        """INSERT INTO matches(external_id, played_at, competition, matchday, neutral_site, home_advantage, venue_country, stage, group_name, home_club_id, away_club_id, home_goals, away_goals)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(external_id) DO UPDATE SET played_at=excluded.played_at, competition=excluded.competition,
           matchday=excluded.matchday, neutral_site=excluded.neutral_site, home_advantage=excluded.home_advantage, venue_country=excluded.venue_country, stage=excluded.stage, group_name=excluded.group_name,
           home_club_id=excluded.home_club_id, away_club_id=excluded.away_club_id,
           home_goals=excluded.home_goals, away_goals=excluded.away_goals""",
        (match["external_id"], *values),
    )
    database.execute("DELETE FROM fixtures WHERE external_id=?", (match["external_id"],))
    # Jogo novo ou corrigido precisa ser processado; jogos idênticos não voltam à fila.
    database.execute("DELETE FROM processed_matches WHERE external_id=?", (match["external_id"],))


def store_source_payload(database: sqlite3.Connection, source: str, request_path: str, payload: str) -> None:
    database.execute(
        "INSERT INTO source_payloads(source, request_path, fetched_at, payload) VALUES (?, ?, datetime('now'), ?)",
        (source, request_path, payload),
    )


def replace_fixtures(database: sqlite3.Connection, fixtures: list[dict[str, str]], *, replace: bool = True) -> None:
    if replace:
        database.execute("DELETE FROM fixtures WHERE competition='Série A'")
    for fixture in fixtures:
        inferred_state = BRAZILIAN_STATE_BY_COMPETITION.get(fixture["competition"])
        home = _club_id(database, fixture["home_team"], fixture.get("home_crest"), fixture.get("home_country"), fixture.get("home_state") or inferred_state)
        away = _club_id(database, fixture["away_team"], fixture.get("away_crest"), fixture.get("away_country"), fixture.get("away_state") or inferred_state)
        home_advantage = _home_advantage(fixture)
        neutral_site = int(home_advantage == 0)
        database.execute(
            """INSERT INTO fixtures(external_id, scheduled_at, competition, status, matchday, neutral_site, home_advantage, venue_country, stage, group_name, home_club_id, away_club_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(external_id) DO UPDATE SET scheduled_at=excluded.scheduled_at, competition=excluded.competition,
               status=excluded.status, matchday=excluded.matchday, neutral_site=excluded.neutral_site, home_advantage=excluded.home_advantage, venue_country=excluded.venue_country, stage=excluded.stage, group_name=excluded.group_name,
               home_club_id=excluded.home_club_id, away_club_id=excluded.away_club_id""",
            (fixture["external_id"], fixture["scheduled_at"], fixture["competition"], fixture["status"],
             int(fixture["matchday"]) if fixture.get("matchday") else None, neutral_site, home_advantage, fixture.get("venue_country"), fixture.get("stage"), fixture.get("group_name"), home, away),
        )
    # A fonte pode manter por alguns minutos um fixture que já chegou no feed de resultados.
    database.execute("DELETE FROM fixtures WHERE external_id IN (SELECT external_id FROM matches)")


def prune_stale_fixtures(database: sqlite3.Connection, *, before: str) -> int:
    """Descarta agendas antigas sem placar, que não são previsões futuras válidas."""
    cursor = database.execute("DELETE FROM fixtures WHERE scheduled_at < ?", (before,))
    return cursor.rowcount


def recreate_matches_table(database: sqlite3.Connection) -> None:
    """Atualiza a validação do catálogo após a limpeza atômica da carga histórica."""
    database.execute("DROP TABLE matches")
    database.execute(MATCHES_TABLE)


def _advance_inactive(rating: Rating, since: str | None, until: str) -> Rating:
    """Aplica períodos semanais vazios apenas quando o clube volta a jogar."""
    if not since:
        return rating
    weeks = max(0, (date.fromisoformat(until[:10]) - date.fromisoformat(since[:10])).days // 7 - 1)
    for _ in range(weeks):
        rating = update(rating, ())
    return rating


def _goal_margin_weight(home_goals: int, away_goals: int) -> float:
    """Amplia com suavidade a evidência de vitórias largas, com teto de segurança."""
    difference = abs(home_goals - away_goals)
    if difference <= 1:
        return 1.0
    return min(MAX_GOAL_MARGIN_WEIGHT, 1.0 + GOAL_MARGIN_WEIGHT_COEFFICIENT * log(difference))


KNOCKOUT_STAGE_WEIGHTS = {
    "FIRST_ROUND": 1.05,
    "SECOND_ROUND": 1.10,
    "LAST_16": 1.20,
    "ROUND_OF_16": 1.20,
    "QUARTER_FINAL": 1.35,
    "QUARTER_FINALS": 1.35,
    "SEMIFINAL": 1.50,
    "SEMI_FINAL": 1.50,
    "SEMI_FINALS": 1.50,
    "FINAL": 1.70,
}


def knockout_stage_weight(stage: str | None) -> float:
    """Aumenta a evidência de jogos eliminatórios sem alterar pontos de liga."""
    normalized = (stage or "").upper().replace("-", "_").replace(" ", "_")
    return KNOCKOUT_STAGE_WEIGHTS.get(normalized, 1.0)


def _apply_timestamp_group(
    database: sqlite3.Connection, games: list[sqlite3.Row], ratings: dict[int, Rating], last_played: dict[int, str]
) -> None:
    """Atualiza uma rodada de partidas com o mesmo horário; fora disso, a ordem é estrita."""
    played_at = games[0]["played_at"]
    club_ids = {club for game in games for club in (game["home_club_id"], game["away_club_id"])}
    before = {club: _advance_inactive(ratings.get(club, Rating()), last_played.get(club), played_at) for club in club_ids}
    outcomes: dict[int, list[OpponentResult]] = defaultdict(list)
    forecasts = []
    for game in games:
        home, away = before[game["home_club_id"]], before[game["away_club_id"]]
        home_offset = game["home_advantage"]
        away_offset = -home_offset
        home_score = 1.0 if game["home_goals"] > game["away_goals"] else 0.5 if game["home_goals"] == game["away_goals"] else 0.0
        forecasts.append((game["external_id"], expected_score(home, away, home_offset), expected_score(away, home, away_offset), home_score))
        weight = _goal_margin_weight(game["home_goals"], game["away_goals"]) * knockout_stage_weight(game["stage"])
        outcomes[game["home_club_id"]].append(OpponentResult(away, home_score, home_offset, weight))
        outcomes[game["away_club_id"]].append(OpponentResult(home, 1.0 - home_score, away_offset, weight))
    after = {club: update(before[club], results) for club, results in outcomes.items()}
    effects = []
    for game in games:
        home_offset = game["home_advantage"]
        for club, opponent, offset in ((game["home_club_id"], game["away_club_id"], home_offset), (game["away_club_id"], game["home_club_id"], -home_offset)):
            omitted = next(result for result in outcomes[club] if result.opponent == before[opponent] and result.rating_offset == offset)
            without = tuple(result for result in outcomes[club] if result is not omitted)
            counterfactual = update(before[club], without)
            effects.append((game["external_id"], club, before[club].rating, after[club].rating, after[club].rating - counterfactual.rating))
    database.executemany(
        """INSERT INTO match_rating_effects(external_id, club_id, rating_before, rating_after, rating_effect) VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(external_id, club_id) DO UPDATE SET rating_before=excluded.rating_before, rating_after=excluded.rating_after, rating_effect=excluded.rating_effect""",
        effects,
    )
    database.executemany(
        """INSERT INTO match_forecasts(external_id, home_expected, away_expected, home_score) VALUES (?, ?, ?, ?)
           ON CONFLICT(external_id) DO UPDATE SET home_expected=excluded.home_expected,
             away_expected=excluded.away_expected, home_score=excluded.home_score""",
        forecasts,
    )
    database.executemany(
        """INSERT INTO rating_states(club_id, rating, rd, volatility, updated_at) VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(club_id) DO UPDATE SET rating=excluded.rating, rd=excluded.rd, volatility=excluded.volatility, updated_at=excluded.updated_at""",
        [(club, value.rating, value.rd, value.volatility, played_at) for club, value in after.items()],
    )
    database.executemany("INSERT OR REPLACE INTO processed_matches(external_id, processed_at) VALUES (?, ?)", [(game["external_id"], played_at) for game in games])
    ratings.update(after)
    last_played.update({club: played_at for club in after})


def _groups(rows: list[sqlite3.Row]):
    grouped: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        grouped[row["played_at"]].append(row)
    return (grouped[key] for key in sorted(grouped))


def rebuild(database: sqlite3.Connection) -> int:
    """Reconstrói todo o histórico, apenas para a carga inicial ou correção excepcional."""
    database.execute("DELETE FROM rating_snapshots")
    database.execute("DELETE FROM match_rating_effects")
    database.execute("DELETE FROM match_forecasts")
    database.execute("DELETE FROM rating_states")
    database.execute("DELETE FROM processed_matches")
    rows = database.execute("SELECT * FROM matches ORDER BY played_at, external_id").fetchall()
    ratings: dict[int, Rating] = {}
    last_played: dict[int, str] = {}
    for games in _groups(rows):
        _apply_timestamp_group(database, games, ratings, last_played)
    database.execute("INSERT OR REPLACE INTO rating_model(singleton, version) VALUES (1, ?)", (RATING_MODEL_VERSION,))
    database.commit()
    return len(rows)


def process_pending(database: sqlite3.Connection) -> int:
    """Processa apenas placares novos, em ordem temporal, sem refazer o histórico diário."""
    stored_version = database.execute("SELECT version FROM rating_model WHERE singleton=1").fetchone()
    if not stored_version or stored_version["version"] != RATING_MODEL_VERSION:
        return rebuild(database)
    pending = database.execute(
        """SELECT m.* FROM matches m LEFT JOIN processed_matches p ON p.external_id=m.external_id
           WHERE p.external_id IS NULL ORDER BY m.played_at, m.external_id"""
    ).fetchall()
    if not pending:
        return 0
    latest = database.execute("SELECT MAX(processed_at) FROM processed_matches").fetchone()[0]
    if latest is None or pending[0]["played_at"] <= latest:
        return rebuild(database)
    state_rows = database.execute("SELECT * FROM rating_states").fetchall()
    ratings = {row["club_id"]: Rating(row["rating"], row["rd"], row["volatility"]) for row in state_rows}
    last_played = {row["club_id"]: row["updated_at"] for row in state_rows}
    for games in _groups(pending):
        _apply_timestamp_group(database, games, ratings, last_played)
    database.commit()
    return len(pending)


def latest_ranking(database: sqlite3.Connection, as_of: str | None = None) -> list[dict[str, object]]:
    latest = database.execute("SELECT MAX(processed_at) FROM processed_matches").fetchone()[0]
    if not latest:
        return []
    as_of = as_of or datetime.now().astimezone().isoformat()
    reference = max(latest, as_of)
    rows = database.execute(
        """SELECT c.name, c.crest_url, s.rating, s.rd, s.volatility, s.updated_at
           FROM rating_states s JOIN clubs c ON c.id=s.club_id ORDER BY s.rating DESC, s.rd ASC, c.name"""
    ).fetchall()
    ranking = []
    for row in rows:
        adjusted = _advance_inactive(Rating(row["rating"], row["rd"], row["volatility"]), row["updated_at"], reference)
        days_without_tracking = max(0, (date.fromisoformat(reference[:10]) - date.fromisoformat(row["updated_at"][:10])).days)
        reasons = []
        if days_without_tracking > MAX_INACTIVITY_DAYS:
            reasons.append("sem resultados rastreados recentes")
        if adjusted.rd >= MAX_RANKING_RD:
            reasons.append("incerteza alta")
        ranking.append({"name": row["name"], "crest_url": row["crest_url"], "rating": adjusted.rating, "rd": adjusted.rd,
                        "volatility": adjusted.volatility, "period_date": reference, "last_tracked_at": row["updated_at"],
                        "days_without_tracking": days_without_tracking, "eligible": not reasons, "ineligibility_reasons": reasons})
    return sorted(ranking, key=lambda row: (-row["rating"], row["rd"], row["name"]))

