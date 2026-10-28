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
    MAX_GOAL_MARGIN_WEIGHT,
    _advance_inactive,
    connect,
    initialise,
    knockout_stage_weight,
)
from .glicko2 import OpponentResult, Rating, expected_score, update

# A grade é custosa e deve ser refeita só uma vez por mês, não em cada cron diário.
EVALUATION_VERSION = f"rolling-home-grid-v3|{COMPETITION_CATALOG_VERSION}|{date.today():%Y-%m}"
HOME_ADVANTAGES = (65.0, 70.0, 75.0, 80.0)
# A primeira rodada não distinguiu o peso da margem; nesta rodada ele é fixado
# no valor publicado, para isolar o efeito do mando de campo.
GOAL_MARGIN_COEFFICIENTS = (GOAL_MARGIN_WEIGHT_COEFFICIENT,)
WINDOW_START_SHARES = (0.60, 0.70, 0.80, 0.90)


def _groups(rows):
    grouped: dict[str, list] = defaultdict(list)
    for row in rows:
        grouped[row["played_at"]].append(row)
    return [grouped[key] for key in sorted(grouped)]


def _window_starts(groups: list[list]) -> list[int]:
    """Converte cortes percentuais em fronteiras de horário, sem dividir grupos."""
    total = sum(len(group) for group in groups)
    starts = []
    for share in WINDOW_START_SHARES:
        target, seen = total * share, 0
        for index, group in enumerate(groups):
            if seen >= target:
                starts.append(index)
                break
            seen += len(group)
        else:
            starts.append(len(groups) - 1)
    return sorted(set(starts))


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


def _blank_metrics() -> dict[str, float]:
    return {"evaluated": 0, "squared_error": 0.0, "absolute_error": 0.0, "predicted_total": 0.0, "observed_total": 0.0}


def _finish_metrics(metrics: dict[str, float]) -> dict[str, object]:
    evaluated = int(metrics["evaluated"])
    return {
        "evaluated_matches": evaluated,
        "brier_score": round(metrics["squared_error"] / evaluated, 4),
        "mean_absolute_error": round(metrics["absolute_error"] / evaluated, 4),
        "calibration_bias": round((metrics["observed_total"] - metrics["predicted_total"]) / evaluated, 4),
    }


def _evaluate_variant(groups: list[list], window_starts: list[int], home_advantage: float, goal_coefficient: float) -> dict[str, object]:
    ratings: dict[int, Rating] = {}
    last_played: dict[int, str] = {}
    total_metrics = _blank_metrics()
    window_metrics = [_blank_metrics() for _ in window_starts]
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
            if group_index >= window_starts[0]:
                window = max(index for index, start in enumerate(window_starts) if group_index >= start)
                for metrics in (total_metrics, window_metrics[window]):
                    metrics["evaluated"] += 1
                    metrics["predicted_total"] += expected
                    metrics["observed_total"] += score
                    metrics["squared_error"] += (expected - score) ** 2
                    metrics["absolute_error"] += abs(expected - score)
            weight = _margin_weight(game["home_goals"], game["away_goals"], goal_coefficient) * knockout_stage_weight(game["stage"])
            outcomes[home_id].append(OpponentResult(before[away_id], score, offset, weight))
            outcomes[away_id].append(OpponentResult(before[home_id], 1.0 - score, -offset, weight))
        after = {club: update(before[club], results) for club, results in outcomes.items()}
        ratings.update(after)
        last_played.update({club: played_at for club in after})
    return {
        "home_advantage": int(home_advantage),
        "goal_margin_coefficient": goal_coefficient,
        **_finish_metrics(total_metrics),
        "windows": [_finish_metrics(metrics) for metrics in window_metrics],
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
    window_starts = _window_starts(groups)
    variants = [
        _evaluate_variant(groups, window_starts, home_advantage, coefficient)
        for home_advantage in HOME_ADVANTAGES
        for coefficient in GOAL_MARGIN_COEFFICIENTS
    ]
    variants.sort(key=lambda item: (item["brier_score"], item["mean_absolute_error"]))
    result = {
        "version": EVALUATION_VERSION,
        "method": "walk_forward_temporal_60_100",
        "goal_margin_coefficient": GOAL_MARGIN_COEFFICIENTS[0],
        "windows": [
            {
                "label": f"Janela {index + 1}",
                "start": groups[start][0]["played_at"],
                "training_matches": sum(len(group) for group in groups[:start]),
                "test_matches": sum(len(group) for group in groups[start:window_starts[index + 1] if index + 1 < len(window_starts) else len(groups)]),
            }
            for index, start in enumerate(window_starts)
        ],
        "training_matches": sum(len(group) for group in groups[:window_starts[0]]),
        "test_matches": sum(len(group) for group in groups[window_starts[0]:]),
        "test_start": groups[window_starts[0]][0]["played_at"],
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
