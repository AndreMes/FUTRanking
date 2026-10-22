"""Exporta o último ranking calculado para o painel estático."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .database import connect, initialise, latest_ranking


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
    payload = {
        "competition": "Campeonato Brasileiro Série A",
        "period_date": ranking[0]["period_date"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "football-data.org",
        "teams": [{"position": position, "name": row["name"], "rating": round(row["rating"], 1), "rd": round(row["rd"], 1)} for position, row in enumerate(ranking, 1)],
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(ranking)} clubes exportados para {output}")


if __name__ == "__main__":
    main()
