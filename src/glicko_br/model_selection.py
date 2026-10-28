"""Avaliação temporal de variantes do Glicko-2, sem alterar o modelo publicado."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date, datetime, timezone
from math import log

from .competitions import COMPETITION_CATALOG_VERSION
from .database import (
    GOAL_MARGIN_WEIGHT_COEFFICIENT,
    HOME_ADVANTAGE,
    MAX_GOAL_MARGIN_WEIGHT,
    _advance_inactive,
    connect,
    initialise,
    knockout_stage_weight,
)
from .glicko2 import OpponentResult, Rating, expected_score, update

# A grade é custosa e deve ser refeita só uma vez por mês, não em cada cron diário.
EVALUATION_VERSION = f"temporal-grid-v1|{COMPETITION_CATALOG_VERSION}|{date.today():%Y-%m}"
HOME_ADVANTAGES = (40.0, 50.0, 60.0)
GOAL_MARGIN_COEFFICIENTS = (0.25, GOAL_MARGIN_WEIGHT_COEFFICIENT, 0.75)
HOLDOUT_SHARE = 0.20


def _groups(rows):
    grouped: dict[str, list] = defaultdict(list)
    for row in rows:
        grouped[row["played_at"]].append(row)
    return [grouped[key] for key in sorted(grouped)]


def _test_start(groups: list[list]) -> int:
    """Escolhe uma fronteira temporal próxima a 80% das partidas."""
    total = sum(len(group) for group in groups)
    target = total * (1.0 - HOLDOUT_SHARE)
    seen = 0
    for index, group in enumerate(groups):
        if seen >= target:
            return index
        seen += len(group)
    return max(1, len(groups) - 1)


def _margin_weight(home_goals: int, away_goals: int, coefficient: float) -> float:
    difference = abs(home_goals - away_goals)
    if difference <= 1:
        return 1.0
    return min(MAX_GOAL_MARGIN_WEIGHT, 1.0 + coefficient * log(difference))


def _home_offset(game, home_advantage: float) -> float:
    """Preserva campo neutro e mando visitante, alterando só a intensidade."""
    if game["neutral_site"]:
        return 0.0
    return home_advantage if float(game["home_advantage"]) >= 0 else -home_advantage


def _evaluate_variant(groups: list[list], test_start: int, home_advantage: float, goal_coefficient: float) -> dict[str, object]:
    ratings: dict[int, Rating] = {}
    last_played: dict[int, str] = {}
    squared_error = absolute_error = predicted_total = observed_total = 0.0
    evaluated = 0
    for group_index, games in enumerate(groups):
        played_at = games[0]["played_at"]
        club_ids = {club for game in games for club in (game["home_club_id"], game["away_club_id"])}
        before = {club: _advance_inactive(ratings.get(club, Rating()), last_played.get(club), played_at) for club in club_ids}
        outcomes: dict[int, list[OpponentResult]] = defaultdict(list)
        for game in games:
            home_id, away_id = game["home_club_id"], game["away_club_id"]
            offset = _home_offset(game, home_advantage)
            expected = expected_score(before[home_id], before[away_id], offset)
            score = 1.0 if game["home_goals"] > game["away_goals"] else 0.5 if game["home_goals"] == game["away_goals"] else 0.0
            if group_index >= test_start:
                evaluated += 1
                predicted_total += expected
                observed_total += score
                squared_error += (expected - score) ** 2
                absolute_error += abs(expected - score)
            weight = _margin_weight(game["home_goals"], game["away_goals"], goal_coefficient) * knockout_stage_weight(game["stage"])
            outcomes[home_id].append(OpponentResult(before[away_id], score, offset, weight))
            outcomes[away_id].append(OpponentResult(before[home_id], 1.0 - score, -offset, weight))
        after = {club: update(before[club], results) for club, results in outcomes.items()}
        ratings.update(after)
        last_played.update({club: played_at for club in after})
    return {
        "home_advantage": int(home_advantage),
        "goal_margin_coefficient": goal_coefficient,
        "evaluated_matches": evaluated,
        "brier_score": round(squared_error / evaluated, 4),
        "mean_absolute_error": round(absolute_error / evaluated, 4),
        "calibration_bias": round((observed_total - predicted_total) / evaluated, 4),
    }


def evaluate(database) -> dict[str, object]:
    """Executa uma única grade temporal por versão do catálogo e a persiste."""
    existing = database.execute("SELECT payload FROM model_evaluations WHERE version=?", (EVALUATION_VERSION,)).fetchone()
    if existing:
        return json.loads(existing["payload"])
    rows = database.execute(
        """SELECT external_id, played_at, neutral_site, home_advantage, stage, home_club_id, away_club_id, home_goals, away_goals
           FROM matches ORDER BY played_at, external_id"""
    ).fetchall()
    groups = _groups(rows)
    if len(groups) < 2:
        raise ValueError("São necessárias ao menos duas datas de jogos para avaliar variantes.")
    test_start = _test_start(groups)
    variants = [
        _evaluate_variant(groups, test_start, home_advantage, coefficient)
        for home_advantage in HOME_ADVANTAGES
        for coefficient in GOAL_MARGIN_COEFFICIENTS
    ]
    variants.sort(key=lambda item: (item["brier_score"], item["mean_absolute_error"]))
    result = {
        "version": EVALUATION_VERSION,
        "method": "walk_forward_temporal_80_20",
        "training_matches": sum(len(group) for group in groups[:test_start]),
        "test_matches": sum(len(group) for group in groups[test_start:]),
        "test_start": groups[test_start][0]["played_at"],
        "variants": variants,
        "winner": variants[0],
    }
    database.execute(
        "INSERT INTO model_evaluations(version, evaluated_at, payload) VALUES (?, ?, ?)",
        (EVALUATION_VERSION, datetime.now(timezone.utc).isoformat(), json.dumps(result, ensure_ascii=False)),
    )
    database.commit()
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    args = parser.parse_args()
    database = connect(args.database)
    initialise(database)
    result = evaluate(database)
    winner = result["winner"]
    print(f"{len(result['variants'])} variantes avaliadas; melhor EQM {winner['brier_score']:.4f} (mando {winner['home_advantage']}, margem {winner['goal_margin_coefficient']}).")


if __name__ == "__main__":
    main()
