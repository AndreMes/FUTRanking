"""Diagnóstico interno da cobertura do banco por país, temporada e competição."""
from __future__ import annotations

from typing import Iterable

from .club_metadata import COUNTRY_OVERRIDES
from .competitions import DOMESTIC_COMPETITION_COUNTRIES


def _countries(database) -> dict[str, str]:
    known = {
        row["name"]: row["country"] for row in database.execute(
            "SELECT name, country FROM clubs WHERE country IS NOT NULL AND country <> ''"
        )
    }
    placeholders = ", ".join("?" for _ in DOMESTIC_COMPETITION_COUNTRIES)
    rows = database.execute(
        f"""SELECT competition, name FROM (
               SELECT m.competition, home.name AS name FROM matches m JOIN clubs home ON home.id=m.home_club_id WHERE m.competition IN ({placeholders})
               UNION SELECT m.competition, away.name AS name FROM matches m JOIN clubs away ON away.id=m.away_club_id WHERE m.competition IN ({placeholders})
           )""",
        tuple(DOMESTIC_COMPETITION_COUNTRIES) * 2,
    )
    for row in rows:
        known.setdefault(row["name"], DOMESTIC_COMPETITION_COUNTRIES[row["competition"]])
    for name, country in COUNTRY_OVERRIDES.items():
        known.setdefault(name, country)
    return known


def coverage_rows(database, *, country: str | None = None, season: str | None = None) -> list[dict[str, object]]:
    """Conta cada jogo uma vez para cada país que teve clube participante."""
    countries = _countries(database)
    grouped: dict[tuple[str, str, str], dict[str, object]] = {}
    rows = database.execute(
        """SELECT m.external_id, m.played_at, m.competition, home.name AS home_team, away.name AS away_team
           FROM matches m JOIN clubs home ON home.id=m.home_club_id JOIN clubs away ON away.id=m.away_club_id"""
    )
    for row in rows:
        row_season = str(row["played_at"])[:4]
        if season and row_season != str(season):
            continue
        participants = ((row["home_team"], countries.get(row["home_team"])), (row["away_team"], countries.get(row["away_team"])))
        for row_country in {value for _, value in participants if value}:
            if country and row_country != country:
                continue
            key = (row_country, row_season, row["competition"])
            item = grouped.setdefault(key, {"country": row_country, "season": row_season, "competition": row["competition"], "match_ids": set(), "teams": set(), "first_match": row["played_at"], "last_match": row["played_at"]})
            item["match_ids"].add(row["external_id"])
            item["teams"].update(team for team, team_country in participants if team_country == row_country)
            item["first_match"] = min(item["first_match"], row["played_at"])
            item["last_match"] = max(item["last_match"], row["played_at"])
    return [
        {"country": item["country"], "season": item["season"], "competition": item["competition"], "matches": len(item["match_ids"]), "teams": len(item["teams"]), "first_match": item["first_match"], "last_match": item["last_match"]}
        for item in sorted(grouped.values(), key=lambda item: (item["country"], item["season"], item["competition"]), reverse=False)
    ]


def format_report(rows: Iterable[dict[str, object]]) -> str:
    rows = list(rows)
    if not rows:
        return "Nenhuma partida encontrada para esse recorte."
    header = f"{'PAÍS':<12} {'TEMP.':<6} {'COMPETIÇÃO':<36} {'JOGOS':>7} {'CLUBES':>7}  PERÍODO"
    lines = [header, "-" * len(header)]
    for row in rows:
        period = f"{str(row['first_match'])[:10]} a {str(row['last_match'])[:10]}"
        lines.append(f"{row['country']:<12} {row['season']:<6} {row['competition']:<36} {row['matches']:>7} {row['teams']:>7}  {period}")
    return "\n".join(lines)
