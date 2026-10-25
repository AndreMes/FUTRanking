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


def exported_matches(database) -> list[dict[str, object]]:
    """Resultados brutos que explicam o ranking exibido no site."""
    rows = database.execute(
        """SELECT m.external_id, m.played_at, m.competition, m.matchday, m.stage, m.group_name, home.name AS home_team, home.crest_url AS home_crest,
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
        """SELECT f.scheduled_at, f.status, f.competition, f.matchday, f.stage, f.group_name, home.name AS home_team, home.crest_url AS home_crest,
                  away.name AS away_team, away.crest_url AS away_crest
           FROM fixtures f JOIN clubs home ON home.id=f.home_club_id JOIN clubs away ON away.id=f.away_club_id
           WHERE NOT EXISTS (SELECT 1 FROM matches m WHERE m.external_id=f.external_id)
           ORDER BY f.scheduled_at""",
    ).fetchall()
    fixtures = []
    for row in rows:
        home, away = ratings.get(row["home_team"], Rating()), ratings.get(row["away_team"], Rating())
        home_chance = expected_score(home, away, HOME_ADVANTAGE)
        fixtures.append({**dict(row), "home_rating": round(home.rating, 1), "away_rating": round(away.rating, 1),
                         "home_favoritism": round(home_chance * 100, 1), "away_favoritism": round((1 - home_chance) * 100, 1)})
    return fixtures


def exported_simulation(database, ranking, fixtures: list[dict[str, object]]) -> dict[str, object]:
    """Prepara a projeção exclusiva da temporada em andamento da Série A."""
    years = [int(str(fixture["scheduled_at"])[:4]) for fixture in fixtures if fixture.get("scheduled_at")]
    if not years:
        return {"available": False}
    season = max(years)
    matches = [dict(row) for row in database.execute(
        """SELECT home.name AS home_team, away.name AS away_team, m.home_goals, m.away_goals
           FROM matches m JOIN clubs home ON home.id=m.home_club_id JOIN clubs away ON away.id=m.away_club_id
           WHERE m.competition='Série A' AND m.played_at >= ? AND m.played_at < ?""",
        (f"{season}-01-01", f"{season + 1}-01-01"),
    ).fetchall()]
    ratings = {row["name"]: Rating(row["rating"], row["rd"], row["volatility"]) for row in ranking}
    simulation = simulate_season(matches, fixtures, ratings, seed=season)
    simulation["season"] = season
    if simulation["available"]:
        crests = {row["name"]: row["crest_url"] for row in database.execute("SELECT name, crest_url FROM clubs")}
        for team in simulation["teams"]:
            team["crest"] = crests.get(team["name"])
    return simulation


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
    teams = []
    excluded_teams = []
    for row in ranking:
        name = row["name"]
        team = {
            "name": name,
            "crest": row["crest_url"],
            "rating": round(row["rating"], 1),
            "rd": round(row["rd"], 1),
            "last_tracked_at": row["last_tracked_at"],
            "days_without_tracking": row["days_without_tracking"],
            "performance": team_performance(matches, name),
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
        "source": "football-data.org",
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

