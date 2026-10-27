from __future__ import annotations

import argparse
import csv
from pathlib import Path

from .database import connect, initialise, latest_ranking, process_pending, rebuild, store_match
from .api_football import ApiFootballError, sync_season
from .sofascore import SofascoreError, sync_season as sync_sofascore_season
from .football_data import FootballDataError, sync_season as sync_football_data_season
from .espn import EspnError, sync_period as sync_espn_period


def main() -> None:
    parser = argparse.ArgumentParser(prog="glicko-br")
    parser.add_argument("command", choices=("init", "ingest", "sync-api-football", "sync-sofascore", "sync-football-data", "sync-espn", "process", "rebuild", "ranking"))
    parser.add_argument("--database", required=True)
    parser.add_argument("--csv")
    parser.add_argument("--season", type=int, help="Ano de início da temporada")
    parser.add_argument("--date-from", help="Data inicial inclusiva (AAAA-MM-DD)")
    parser.add_argument("--date-to", help="Data final exclusiva (AAAA-MM-DD)")
    args = parser.parse_args()
    database_path = Path(args.database)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    database = connect(database_path)
    initialise(database)
    if args.command == "ingest":
        if not args.csv:
            parser.error("ingest exige --csv")
        with open(args.csv, encoding="utf-8", newline="") as source:
            for row in csv.DictReader(source):
                store_match(database, row)
        database.commit()
        print("Partidas importadas. Execute process para atualizar o ranking.")
    elif args.command == "process":
        print(f"{process_pending(database)} partidas novas processadas.")
    elif args.command == "rebuild":
        print(f"{rebuild(database)} partidas processadas.")
    elif args.command == "sync-api-football":
        if not args.season:
            parser.error("sync-api-football exige --season")
        try:
            print(f"{sync_season(database, args.season)} partidas importadas/atualizadas.")
        except ApiFootballError as error:
            parser.error(str(error))
    elif args.command == "sync-sofascore":
        if not args.season:
            parser.error("sync-sofascore exige --season")
        try:
            print(f"{sync_sofascore_season(database, args.season)} partidas importadas/atualizadas.")
        except SofascoreError as error:
            parser.error(str(error))
    elif args.command == "sync-football-data":
        if not args.season:
            parser.error("sync-football-data exige --season")
        try:
            print(f"{sync_football_data_season(database, args.season, date_from=args.date_from, date_to=args.date_to)} partidas importadas/atualizadas.")
        except FootballDataError as error:
            parser.error(str(error))
    elif args.command == "sync-espn":
        if not args.season:
            parser.error("sync-espn exige --season")
        try:
            print(f"{sync_espn_period(database, str(args.season))} partidas ESPN importadas/atualizadas.")
            database.commit()
        except EspnError as error:
            parser.error(str(error))
    elif args.command == "ranking":
        for position, row in enumerate(latest_ranking(database), 1):
            print(f"{position:>2}. {row['name']:<24} {row['rating']:7.1f}  RD {row['rd']:5.1f}")
    else:
        print(f"Banco inicializado em {database_path}")


if __name__ == "__main__":
    main()
