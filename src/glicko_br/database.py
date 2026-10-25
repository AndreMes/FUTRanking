"""Banco SQLite e processamento cronológico incremental dos ratings."""
from __future__ import annotations

import sqlite3
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from .glicko2 import Rating, OpponentResult, update

COMPETITIONS = {"Série A", "Série B", "Série C", "Série D", "Copa do Brasil"}
HOME_ADVANTAGE = 55.0
MAX_INACTIVITY_DAYS = 180
MAX_RANKING_RD = 120.0

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS clubs (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, crest_url TEXT
);
CREATE TABLE IF NOT EXISTS matches (
  external_id TEXT PRIMARY KEY, played_at TEXT NOT NULL, competition TEXT NOT NULL,
  home_club_id INTEGER NOT NULL REFERENCES clubs(id), away_club_id INTEGER NOT NULL REFERENCES clubs(id),
  home_goals INTEGER NOT NULL CHECK(home_goals >= 0), away_goals INTEGER NOT NULL CHECK(away_goals >= 0),
  CHECK(home_club_id <> away_club_id), CHECK(competition IN ('Série A','Série B','Série C','Série D','Copa do Brasil'))
);
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
CREATE TABLE IF NOT EXISTS rating_states (
  club_id INTEGER PRIMARY KEY REFERENCES clubs(id), rating REAL NOT NULL, rd REAL NOT NULL,
  volatility REAL NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS processed_matches (
  external_id TEXT PRIMARY KEY REFERENCES matches(external_id), processed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fixtures (
  external_id TEXT PRIMARY KEY, scheduled_at TEXT NOT NULL, competition TEXT NOT NULL,
  status TEXT NOT NULL, home_club_id INTEGER NOT NULL REFERENCES clubs(id),
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
    database.commit()


def _club_id(database: sqlite3.Connection, name: str, crest_url: str | None = None) -> int:
    database.execute("INSERT OR IGNORE INTO clubs(name) VALUES (?)", (name.strip(),))
    if crest_url:
        database.execute("UPDATE clubs SET crest_url=? WHERE name=?", (crest_url, name.strip()))
    return database.execute("SELECT id FROM clubs WHERE name=?", (name.strip(),)).fetchone()[0]


def store_match(database: sqlite3.Connection, match: dict[str, str]) -> None:
    competition = match["competition"].strip()
    if competition not in COMPETITIONS:
        raise ValueError(f"Competição fora do escopo do MVP: {competition}")
    played_at = match["played_at"]
    datetime.fromisoformat(played_at.replace("Z", "+00:00"))
    home = _club_id(database, match["home_team"], match.get("home_crest"))
    away = _club_id(database, match["away_team"], match.get("away_crest"))
    values = (played_at, competition, home, away, int(match["home_goals"]), int(match["away_goals"]))
    previous = database.execute(
        "SELECT played_at, competition, home_club_id, away_club_id, home_goals, away_goals FROM matches WHERE external_id=?",
        (match["external_id"],),
    ).fetchone()
    if previous and tuple(previous) == values:
        return
    database.execute(
        """INSERT INTO matches(external_id, played_at, competition, home_club_id, away_club_id, home_goals, away_goals)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(external_id) DO UPDATE SET played_at=excluded.played_at, competition=excluded.competition,
           home_club_id=excluded.home_club_id, away_club_id=excluded.away_club_id,
           home_goals=excluded.home_goals, away_goals=excluded.away_goals""",
        (match["external_id"], *values),
    )
    # Jogo novo ou corrigido precisa ser processado; jogos idênticos não voltam à fila.
    database.execute("DELETE FROM processed_matches WHERE external_id=?", (match["external_id"],))


def store_source_payload(database: sqlite3.Connection, source: str, request_path: str, payload: str) -> None:
    database.execute(
        "INSERT INTO source_payloads(source, request_path, fetched_at, payload) VALUES (?, ?, datetime('now'), ?)",
        (source, request_path, payload),
    )


def replace_fixtures(database: sqlite3.Connection, fixtures: list[dict[str, str]]) -> None:
    database.execute("DELETE FROM fixtures WHERE competition='Série A'")
    for fixture in fixtures:
        home = _club_id(database, fixture["home_team"], fixture.get("home_crest"))
        away = _club_id(database, fixture["away_team"], fixture.get("away_crest"))
        database.execute(
            "INSERT INTO fixtures(external_id, scheduled_at, competition, status, home_club_id, away_club_id) VALUES (?, ?, ?, ?, ?, ?)",
            (fixture["external_id"], fixture["scheduled_at"], fixture["competition"], fixture["status"], home, away),
        )


def _advance_inactive(rating: Rating, since: str | None, until: str) -> Rating:
    """Aplica períodos semanais vazios apenas quando o clube volta a jogar."""
    if not since:
        return rating
    weeks = max(0, (date.fromisoformat(until[:10]) - date.fromisoformat(since[:10])).days // 7 - 1)
    for _ in range(weeks):
        rating = update(rating, ())
    return rating


def _apply_timestamp_group(
    database: sqlite3.Connection, games: list[sqlite3.Row], ratings: dict[int, Rating], last_played: dict[int, str]
) -> None:
    """Atualiza uma rodada de partidas com o mesmo horário; fora disso, a ordem é estrita."""
    played_at = games[0]["played_at"]
    club_ids = {club for game in games for club in (game["home_club_id"], game["away_club_id"])}
    before = {club: _advance_inactive(ratings.get(club, Rating()), last_played.get(club), played_at) for club in club_ids}
    outcomes: dict[int, list[OpponentResult]] = defaultdict(list)
    for game in games:
        home, away = before[game["home_club_id"]], before[game["away_club_id"]]
        home_score = 1.0 if game["home_goals"] > game["away_goals"] else 0.5 if game["home_goals"] == game["away_goals"] else 0.0
        outcomes[game["home_club_id"]].append(OpponentResult(away, home_score, HOME_ADVANTAGE))
        outcomes[game["away_club_id"]].append(OpponentResult(home, 1.0 - home_score, -HOME_ADVANTAGE))
    after = {club: update(before[club], results) for club, results in outcomes.items()}
    effects = []
    for game in games:
        for club, opponent, offset in ((game["home_club_id"], game["away_club_id"], HOME_ADVANTAGE), (game["away_club_id"], game["home_club_id"], -HOME_ADVANTAGE)):
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
    database.execute("DELETE FROM rating_states")
    database.execute("DELETE FROM processed_matches")
    rows = database.execute("SELECT * FROM matches ORDER BY played_at, external_id").fetchall()
    ratings: dict[int, Rating] = {}
    last_played: dict[int, str] = {}
    for games in _groups(rows):
        _apply_timestamp_group(database, games, ratings, last_played)
    database.commit()
    return len(rows)


def process_pending(database: sqlite3.Connection) -> int:
    """Processa apenas placares novos, em ordem temporal, sem refazer o histórico diário."""
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

