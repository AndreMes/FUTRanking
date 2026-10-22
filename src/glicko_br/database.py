"""Banco SQLite e recálculo auditável de ratings."""
from __future__ import annotations

import sqlite3
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from .glicko2 import DEFAULT_RATING, Rating, OpponentResult, update

COMPETITIONS = {"Série A", "Série B", "Série C", "Série D", "Copa do Brasil"}
HOME_ADVANTAGE = 55.0

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS clubs (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE
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
  external_id TEXT NOT NULL REFERENCES matches(external_id),
  club_id INTEGER NOT NULL REFERENCES clubs(id),
  rating_before REAL NOT NULL, rating_after REAL NOT NULL, rating_effect REAL NOT NULL,
  PRIMARY KEY(external_id, club_id)
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
    database.commit()


def _club_id(database: sqlite3.Connection, name: str) -> int:
    database.execute("INSERT OR IGNORE INTO clubs(name) VALUES (?)", (name.strip(),))
    return database.execute("SELECT id FROM clubs WHERE name = ?", (name.strip(),)).fetchone()[0]


def store_match(database: sqlite3.Connection, match: dict[str, str]) -> None:
    competition = match["competition"].strip()
    if competition not in COMPETITIONS:
        raise ValueError(f"Competição fora do escopo do MVP: {competition}")
    played_at = date.fromisoformat(match["played_at"][:10]).isoformat()
    home, away = _club_id(database, match["home_team"]), _club_id(database, match["away_team"])
    database.execute(
        """INSERT INTO matches(external_id, played_at, competition, home_club_id, away_club_id, home_goals, away_goals)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(external_id) DO UPDATE SET played_at=excluded.played_at, competition=excluded.competition,
           home_club_id=excluded.home_club_id, away_club_id=excluded.away_club_id,
           home_goals=excluded.home_goals, away_goals=excluded.away_goals""",
        (match["external_id"], played_at, competition, home, away, int(match["home_goals"]), int(match["away_goals"])),
    )


def store_source_payload(database: sqlite3.Connection, source: str, request_path: str, payload: str) -> None:
    """Mantém a resposta original para auditoria e reprodução de importações."""
    database.execute(
        "INSERT INTO source_payloads(source, request_path, fetched_at, payload) VALUES (?, ?, datetime('now'), ?)",
        (source, request_path, payload),
    )


def replace_fixtures(database: sqlite3.Connection, fixtures: list[dict[str, str]]) -> None:
    """Substitui a agenda futura da Série A; ela não participa do rating."""
    database.execute("DELETE FROM fixtures WHERE competition = 'Série A'")
    for fixture in fixtures:
        home, away = _club_id(database, fixture["home_team"]), _club_id(database, fixture["away_team"])
        database.execute(
            "INSERT INTO fixtures(external_id, scheduled_at, competition, status, home_club_id, away_club_id) VALUES (?, ?, ?, ?, ?, ?)",
            (fixture["external_id"], fixture["scheduled_at"], fixture["competition"], fixture["status"], home, away),
        )


def rebuild(database: sqlite3.Connection) -> int:
    """Refaz todo o histórico derivado; resultados brutos nunca são apagados."""
    database.execute("DELETE FROM rating_snapshots")
    database.execute("DELETE FROM match_rating_effects")
    rows = database.execute(
        """SELECT m.*, home.name home_name, away.name away_name FROM matches m
           JOIN clubs home ON home.id=m.home_club_id JOIN clubs away ON away.id=m.away_club_id
           ORDER BY played_at, external_id"""
    ).fetchall()
    ratings: dict[int, Rating] = {}
    by_week: dict[date, list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        played_on = date.fromisoformat(row["played_at"])
        by_week[played_on - timedelta(days=played_on.weekday())].append(row)

    previous_week: date | None = None
    for week, games in sorted(by_week.items()):
        # Uma semana é o período de rating. Semanas inteiras sem partidas fazem
        # o RD crescer — especialmente importante entre uma temporada e outra.
        if previous_week is not None:
            inactive_periods = max(0, (week - previous_week).days // 7 - 1)
            for _ in range(inactive_periods):
                ratings = {club_id: update(rating, ()) for club_id, rating in ratings.items()}
        before = dict(ratings)
        outcomes: dict[int, list[OpponentResult]] = defaultdict(list)
        for game in games:
            home = before.get(game["home_club_id"], Rating())
            away = before.get(game["away_club_id"], Rating())
            home_score = 1.0 if game["home_goals"] > game["away_goals"] else 0.5 if game["home_goals"] == game["away_goals"] else 0.0
            outcomes[game["home_club_id"]].append(OpponentResult(away, home_score, HOME_ADVANTAGE))
            outcomes[game["away_club_id"]].append(OpponentResult(home, 1.0 - home_score, -HOME_ADVANTAGE))
        # Clubes sem jogo neste período mantêm o rating, mas ganham incerteza.
        # Também registramos seu snapshot: o ranking de hoje não pode omitir um
        # clube só porque outro jogo aconteceu por último.
        for club_id, rating in before.items():
            if club_id not in outcomes:
                ratings[club_id] = update(rating, ())
        for club_id, result in outcomes.items():
            ratings[club_id] = update(before.get(club_id, Rating()), result)
        # O Glicko-2 avalia a semana como uma única rodada. Para explicar cada
        # jogo sem introduzir uma ordem artificial, medimos seu efeito como a
        # diferença entre o cálculo completo e o mesmo cálculo sem esse jogo.
        effects = []
        for game in games:
            pairs = (
                (game["home_club_id"], game["away_club_id"], HOME_ADVANTAGE),
                (game["away_club_id"], game["home_club_id"], -HOME_ADVANTAGE),
            )
            for club_id, opponent_id, advantage in pairs:
                all_results = outcomes[club_id]
                omitted = next(
                    result for result in all_results
                    if result.opponent == before.get(opponent_id, Rating()) and result.rating_offset == advantage
                )
                without_game = tuple(result for result in all_results if result is not omitted)
                counterfactual = update(before.get(club_id, Rating()), without_game)
                effects.append((game["external_id"], club_id, before.get(club_id, Rating()).rating,
                                ratings[club_id].rating, ratings[club_id].rating - counterfactual.rating))
        database.executemany(
            "INSERT INTO match_rating_effects(external_id, club_id, rating_before, rating_after, rating_effect) VALUES (?, ?, ?, ?, ?)",
            effects,
        )
        database.executemany(
            "INSERT INTO rating_snapshots(period_date, club_id, rating, rd, volatility) VALUES (?, ?, ?, ?, ?)",
            [(week.isoformat(), club, rating.rating, rating.rd, rating.volatility) for club, rating in ratings.items()],
        )
        previous_week = week
    database.commit()
    return len(rows)


def latest_ranking(database: sqlite3.Connection) -> list[sqlite3.Row]:
    latest = database.execute("SELECT MAX(period_date) FROM rating_snapshots").fetchone()[0]
    if not latest:
        return []
    return database.execute(
        """SELECT c.name, s.rating, s.rd, s.volatility, s.period_date FROM rating_snapshots s
           JOIN clubs c ON c.id=s.club_id WHERE s.period_date=? ORDER BY s.rating DESC, s.rd ASC, c.name""", (latest,)
    ).fetchall()

