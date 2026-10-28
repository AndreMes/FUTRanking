"""Exporta o último ranking calculado para o painel estático."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .database import MAX_INACTIVITY_DAYS, MAX_RANKING_RD, connect, initialise, latest_ranking
from .glicko2 import Rating, expected_score
from .database import HOME_ADVANTAGE
from .simulation import simulate_season
from .neutral_sites import is_neutral_event
from .club_metadata import COUNTRY_OVERRIDES


def exported_matches(database) -> list[dict[str, object]]:
    """Resultados brutos que explicam o ranking exibido no site."""
    rows = database.execute(
        """SELECT m.external_id, m.played_at, m.competition, m.matchday, m.neutral_site, m.home_advantage, m.venue_country, m.stage, m.group_name, home.name AS home_team, home.crest_url AS home_crest,
                  away.name AS away_team, away.crest_url AS away_crest, m.home_goals, m.away_goals,
                  home_effect.rating_after AS home_rating_after, home_effect.rating_effect AS home_rating_effect,
                  away_effect.rating_after AS away_rating_after, away_effect.rating_effect AS away_rating_effect
           FROM matches m
           JOIN clubs home ON home.id = m.home_club_id
           JOIN clubs away ON away.id = m.away_club_id
           LEFT JOIN match_rating_effects home_effect ON home_effect.external_id = m.external_id AND home_effect.club_id = m.home_club_id
           LEFT JOIN match_rating_effects away_effect ON away_effect.external_id = m.external_id AND away_effect.club_id = m.away_club_id
           ORDER BY m.played_at DESC, m.external_id DESC"""
    ).fetchall()
    return [dict(row) for row in rows]


def team_performance(matches: list[dict[str, object]], team: str) -> dict[str, int]:
    games = wins = draws = losses = goals_for = goals_against = 0
    for match in matches:
        is_home = match["home_team"] == team
        if not is_home and match["away_team"] != team:
            continue
        scored = int(match["home_goals"] if is_home else match["away_goals"])
        conceded = int(match["away_goals"] if is_home else match["home_goals"])
        games += 1
        goals_for += scored
        goals_against += conceded
        if scored > conceded:
            wins += 1
        elif scored == conceded:
            draws += 1
        else:
            losses += 1
    return {
        "games": games, "wins": wins, "draws": draws, "losses": losses,
        "goals_for": goals_for, "goals_against": goals_against,
        "points": wins * 3 + draws,
    }


def exported_fixtures(database, ranking) -> list[dict[str, object]]:
    ratings = {row["name"]: Rating(row["rating"], row["rd"], row["volatility"]) for row in ranking}
    rows = database.execute(
        """SELECT f.external_id, f.scheduled_at, f.status, f.competition, f.matchday, f.neutral_site, f.home_advantage, f.venue_country, f.stage, f.group_name, home.name AS home_team, home.crest_url AS home_crest,
                  away.name AS away_team, away.crest_url AS away_crest
           FROM fixtures f JOIN clubs home ON home.id=f.home_club_id JOIN clubs away ON away.id=f.away_club_id
           WHERE NOT EXISTS (SELECT 1 FROM matches m WHERE m.external_id=f.external_id)
           ORDER BY f.scheduled_at""",
    ).fetchall()
    fixtures = []
    for row in rows:
        neutral_site = bool(row["neutral_site"]) or is_neutral_event(row["external_id"])
        home, away = ratings.get(row["home_team"], Rating()), ratings.get(row["away_team"], Rating())
        home_advantage = 0.0 if neutral_site else float(row["home_advantage"])
        home_chance = expected_score(home, away, home_advantage)
        fixtures.append({**dict(row), "neutral_site": neutral_site, "home_advantage": home_advantage, "home_rating": home.rating, "away_rating": away.rating,
                         "home_favoritism": round(home_chance * 100, 1), "away_favoritism": round((1 - home_chance) * 100, 1)})
    return fixtures


def exported_simulation(database, ranking, fixtures: list[dict[str, object]]) -> dict[str, object]:
    """Prepara a projeção exclusiva da temporada em andamento da Série A."""
    season = datetime.now(timezone.utc).year
    serie_a_fixtures = [
        fixture for fixture in fixtures
        if fixture["competition"] == "Série A" and str(fixture["scheduled_at"])[:4] == str(season)
    ]
    matches = [dict(row) for row in database.execute(
        """SELECT home.name AS home_team, away.name AS away_team, m.home_goals, m.away_goals
           FROM matches m JOIN clubs home ON home.id=m.home_club_id JOIN clubs away ON away.id=m.away_club_id
           WHERE m.competition='Série A' AND m.played_at >= ? AND m.played_at < ?""",
        (f"{season}-01-01", f"{season + 1}-01-01"),
    ).fetchall()]
    ratings = {row["name"]: Rating(row["rating"], row["rd"], row["volatility"]) for row in ranking}
    simulation = simulate_season(matches, serie_a_fixtures, ratings, seed=season)
    simulation["season"] = season
    if simulation["available"]:
        crests = {row["name"]: row["crest_url"] for row in database.execute("SELECT name, crest_url FROM clubs")}
        for team in simulation["teams"]:
            team["crest"] = crests.get(team["name"])
    return simulation


def current_divisions(database) -> dict[str, set[str]]:
    """Identifica as divisões nacionais disputadas por cada clube na temporada atual."""
    season = str(datetime.now(timezone.utc).year)
    divisions: dict[str, set[str]] = {}
    rows = database.execute(
        """SELECT competition, team FROM (
               SELECT m.competition, home.name AS team FROM matches m JOIN clubs home ON home.id=m.home_club_id
                WHERE m.competition IN ('Série A', 'Série B', 'Série C') AND m.played_at LIKE ?
               UNION
               SELECT m.competition, away.name AS team FROM matches m JOIN clubs away ON away.id=m.away_club_id
                WHERE m.competition IN ('Série A', 'Série B', 'Série C') AND m.played_at LIKE ?
               UNION
               SELECT f.competition, home.name AS team FROM fixtures f JOIN clubs home ON home.id=f.home_club_id
                WHERE f.competition IN ('Série A', 'Série B', 'Série C') AND f.scheduled_at LIKE ?
               UNION
               SELECT f.competition, away.name AS team FROM fixtures f JOIN clubs away ON away.id=f.away_club_id
                WHERE f.competition IN ('Série A', 'Série B', 'Série C') AND f.scheduled_at LIKE ?
           )""",
        (f"{season}%", f"{season}%", f"{season}%", f"{season}%"),
    ).fetchall()
    for row in rows:
        divisions.setdefault(row["team"], set()).add(row["competition"])
    return divisions


def club_countries(database) -> dict[str, str]:
    """Marca Brasil quando há participação nacional; estrangeiros usam metadado revisável."""
    countries = {
        row["name"]: row["country"] for row in database.execute(
            "SELECT name, country FROM clubs WHERE country IS NOT NULL AND country <> ''"
        ).fetchall()
    }
    rows = database.execute(
        """SELECT DISTINCT name FROM clubs WHERE id IN (
               SELECT home_club_id FROM matches WHERE competition IN ('Série A', 'Série B', 'Série C', 'Série D', 'Copa do Brasil')
               UNION SELECT away_club_id FROM matches WHERE competition IN ('Série A', 'Série B', 'Série C', 'Série D', 'Copa do Brasil')
               UNION SELECT home_club_id FROM fixtures WHERE competition IN ('Série A', 'Série B', 'Série C', 'Série D', 'Copa do Brasil')
               UNION SELECT away_club_id FROM fixtures WHERE competition IN ('Série A', 'Série B', 'Série C', 'Série D', 'Copa do Brasil')
           )"""
    ).fetchall()
    for row in rows:
        countries.setdefault(row["name"], "Brasil")
    for name, country in COUNTRY_OVERRIDES.items():
        countries.setdefault(name, country)
    return countries


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    database = connect(args.database)
    initialise(database)
    ranking = latest_ranking(database)
    if not ranking:
        parser.error("O banco ainda não possui um ranking para exportar.")
    matches = exported_matches(database)
    divisions = current_divisions(database)
    countries = club_countries(database)
    teams = []
    excluded_teams = []
    for row in ranking:
        name = row["name"]
        team = {
            "name": name,
            "crest": row["crest_url"],
            "rating": row["rating"],
            "rd": round(row["rd"], 1),
            "last_tracked_at": row["last_tracked_at"],
            "days_without_tracking": row["days_without_tracking"],
            "performance": team_performance(matches, name),
            "divisions": sorted(divisions.get(name, set())),
            "country": countries.get(name, "País não informado"),
        }
        if row["eligible"]:
            team["position"] = len(teams) + 1
            teams.append(team)
        else:
            team["ineligibility_reasons"] = row["ineligibility_reasons"]
            excluded_teams.append(team)
    fixtures = exported_fixtures(database, ranking)
    payload = {
        "competition": "Campeonato Brasileiro Série A",
        "period_date": ranking[0]["period_date"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "ESPN",
        "scope_note": "Desempenho calculado sobre todas as partidas importadas neste ranking.",
        "eligibility": {"max_inactivity_days": MAX_INACTIVITY_DAYS, "max_rd": MAX_RANKING_RD},
        "teams": teams,
        "excluded_teams": excluded_teams,
        "matches": matches,
        "fixtures": fixtures,
        "simulation": exported_simulation(database, ranking, fixtures),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(ranking)} clubes exportados para {output}")


if __name__ == "__main__":
    main()
