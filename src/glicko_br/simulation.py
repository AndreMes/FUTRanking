"""Simulação Monte Carlo da reta final da Série A, sem dependências externas."""
from __future__ import annotations

from collections import defaultdict
from math import exp
from random import Random
from typing import Iterable

from .database import HOME_ADVANTAGE
from .glicko2 import Rating, expected_score

SCENARIOS = 1_000_000
MIN_DRAW_PROBABILITY = 0.12
MAX_DRAW_PROBABILITY = 0.32
DRAW_GAP_SCALE = 400.0


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _standing_rows(matches: Iterable[dict[str, object]]) -> dict[str, dict[str, int]]:
    standings: dict[str, dict[str, int]] = defaultdict(lambda: {"points": 0, "wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0})
    for match in matches:
        home, away = str(match["home_team"]), str(match["away_team"])
        home_goals, away_goals = int(match["home_goals"]), int(match["away_goals"])
        for team in (home, away):
            standings[team]
        standings[home]["goals_for"] += home_goals
        standings[home]["goals_against"] += away_goals
        standings[away]["goals_for"] += away_goals
        standings[away]["goals_against"] += home_goals
        if home_goals > away_goals:
            standings[home]["points"] += 3
            standings[home]["wins"] += 1
            standings[away]["losses"] += 1
        elif home_goals < away_goals:
            standings[away]["points"] += 3
            standings[away]["wins"] += 1
            standings[home]["losses"] += 1
        else:
            standings[home]["points"] += 1
            standings[away]["points"] += 1
            standings[home]["draws"] += 1
            standings[away]["draws"] += 1
    return standings


def simulate_season(
    completed_matches: list[dict[str, object]],
    fixtures: list[dict[str, object]],
    ratings: dict[str, Rating],
    scenarios: int = SCENARIOS,
    seed: int = 2026,
) -> dict[str, object]:
    """Retorna probabilidades de título e rebaixamento para uma Série A em andamento.

    Resultados futuros são independentes condicionais aos ratings atuais. O empate usa a
    taxa observada de empates da temporada, reduzida quando a diferença de força aumenta.
    """
    if not completed_matches or not fixtures:
        return {"available": False}

    standings = _standing_rows(completed_matches)
    teams = sorted(set(standings) | {str(f["home_team"]) for f in fixtures} | {str(f["away_team"]) for f in fixtures})
    if len(teams) != 20:
        return {"available": False}
    team_index = {team: index for index, team in enumerate(teams)}
    base_points = [standings[team]["points"] for team in teams]
    base_wins = [standings[team]["wins"] for team in teams]
    base_goals_for = [standings[team]["goals_for"] for team in teams]
    base_goal_difference = [standings[team]["goals_for"] - standings[team]["goals_against"] for team in teams]
    observed_draw_rate = sum(int(match["home_goals"]) == int(match["away_goals"]) for match in completed_matches) / len(completed_matches)

    projected_fixtures: list[tuple[int, int, float, float]] = []
    for fixture in fixtures:
        home_name, away_name = str(fixture["home_team"]), str(fixture["away_team"])
        home, away = ratings.get(home_name, Rating()), ratings.get(away_name, Rating())
        home_advantage = 0.0 if fixture.get("neutral_site") else HOME_ADVANTAGE
        binary_home = expected_score(home, away, home_advantage)
        gap = home.rating + home_advantage - away.rating
        draw = _clamp(observed_draw_rate * exp(-abs(gap) / DRAW_GAP_SCALE), MIN_DRAW_PROBABILITY, MAX_DRAW_PROBABILITY)
        projected_fixtures.append((team_index[home_name], team_index[away_name], (1.0 - draw) * binary_home, draw))

    champion_counts = [0] * len(teams)
    relegation_counts = [0] * len(teams)
    random = Random(seed)
    for _ in range(scenarios):
        points, wins = base_points.copy(), base_wins.copy()
        goals_for, goal_difference = base_goals_for.copy(), base_goal_difference.copy()
        for home, away, home_win, draw in projected_fixtures:
            outcome = random.random()
            if outcome < home_win:
                points[home] += 3
                wins[home] += 1
                goals_for[home] += 1
                goal_difference[home] += 1
                goal_difference[away] -= 1
            elif outcome < home_win + draw:
                points[home] += 1
                points[away] += 1
                goals_for[home] += 1
                goals_for[away] += 1
            else:
                points[away] += 3
                wins[away] += 1
                goals_for[away] += 1
                goal_difference[away] += 1
                goal_difference[home] -= 1
        ordered = sorted(range(len(teams)), key=lambda i: (-points[i], -wins[i], -goal_difference[i], -goals_for[i], teams[i]))
        champion_counts[ordered[0]] += 1
        for index in ordered[-4:]:
            relegation_counts[index] += 1

    current_order = sorted(range(len(teams)), key=lambda i: (-base_points[i], -base_wins[i], -base_goal_difference[i], -base_goals_for[i], teams[i]))
    current_position = {team_index[teams[index]]: position + 1 for position, index in enumerate(current_order)}
    table = []
    for index, team in enumerate(teams):
        row = standings[team]
        table.append({
            "name": team,
            "position": current_position[index],
            "points": row["points"],
            "champion_probability": champion_counts[index] / scenarios,
            "relegation_probability": relegation_counts[index] / scenarios,
        })
    return {
        "available": True,
        "scenarios": scenarios,
        "seed": seed,
        "fixtures_remaining": len(fixtures),
        "completed_matches": len(completed_matches),
        "observed_draw_rate": observed_draw_rate,
        "draw_limits": [MIN_DRAW_PROBABILITY, MAX_DRAW_PROBABILITY],
        "teams": sorted(table, key=lambda row: row["position"]),
    }
