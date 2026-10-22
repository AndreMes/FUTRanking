"""Exporta ranking, resultados e desempenho para o painel estático."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .database import connect, initialise, latest_ranking


def exported_matches(database) -> list[dict[str, object]]:
    """Resultados brutos que explicam o ranking exibido no site."""
    rows = database.execute(
        """SELECT m.external_id, m.played_at, m.competition, home.name AS home_team,
                  away.name AS away_team, m.home_goals, m.away_goals
           FROM matches m
           JOIN clubs home ON home.id = m.home_club_id
           JOIN clubs away ON away.id = m.away_club_id
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
    for position, row in enumerate(ranking, 1):
        name = row["name"]
        teams.append({
            "position": position,
            "name": name,
            "rating": round(row["rating"], 1),
            "rd": round(row["rd"], 1),
            "performance": team_performance(matches, name),
        })
    payload = {
        "competition": "Campeonato Brasileiro Série A",
        "period_date": ranking[0]["period_date"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "football-data.org",
        "scope_note": "Desempenho calculado sobre todas as partidas importadas neste ranking.",
        "teams": teams,
        "matches": matches,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(ranking)} clubes exportados para {output}")


if __name__ == "__main__":
    main()
