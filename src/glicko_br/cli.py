from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

from .database import connect, identity_candidates, initialise, latest_ranking, process_pending, rebuild, store_match
from .api_football import ApiFootballError, sync_season
from .sofascore import SofascoreError, sync_season as sync_sofascore_season
from .football_data import FootballDataError, sync_season as sync_football_data_season
from .espn import EspnError, sync_period as sync_espn_period
from .coverage_report import coverage_rows, format_report
from .club_identity import provider_match_key
from .crest_colors import crest_similarity


def main() -> None:
    parser = argparse.ArgumentParser(prog="glicko-br")
    parser.add_argument("command", choices=("init", "ingest", "sync-api-football", "sync-sofascore", "sync-football-data", "sync-espn", "process", "rebuild", "ranking", "coverage", "identities"))
    parser.add_argument("--database", required=True)
    parser.add_argument("--csv")
    parser.add_argument("--season", type=int, help="Ano de início da temporada na API-Football")
    parser.add_argument("--date-from", help="Data inicial inclusiva (AAAA-MM-DD)")
    parser.add_argument("--date-to", help="Data final exclusiva (AAAA-MM-DD)")
    parser.add_argument("--country", help="Restringe o diagnóstico de cobertura a um país")
    parser.add_argument("--crest-similarity", action="store_true", help="Compara escudos somente em candidatos ESPN×GSA")
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
    elif args.command == "coverage":
        print(format_report(coverage_rows(database, country=args.country, season=str(args.season) if args.season else None)))
    elif args.command == "identities":
        candidates = identity_candidates(database)
        if not candidates:
            print("Identidades: nenhum candidato brasileiro ambíguo encontrado.")
        else:
            print("Identidades: candidatos para revisão (não foram unidos automaticamente):")
            for candidate in candidates:
                print(f"  {candidate['state']} · {candidate['key']}: {' | '.join(candidate['clubs'])}")
        if args.crest_similarity:
            rows = database.execute(
                """SELECT m.external_id, m.competition, substr(m.played_at, 1, 10) AS game_date,
                          m.home_goals, m.away_goals, home.name AS home_name, home.crest_url AS home_crest,
                          away.name AS away_name, away.crest_url AS away_crest
                   FROM matches m JOIN clubs home ON home.id=m.home_club_id JOIN clubs away ON away.id=m.away_club_id"""
            ).fetchall()
            groups = defaultdict(list)
            for row in rows:
                groups[tuple(row[column] for column in ("competition", "game_date", "home_goals", "away_goals"))].append(row)
            visual = []
            for matches in groups.values():
                espn = [row for row in matches if str(row["external_id"]).startswith("espn:")]
                gsa = [row for row in matches if str(row["external_id"]).startswith("gsa:")]
                for left in espn:
                    for right in gsa:
                        if (provider_match_key(str(left["home_name"])), provider_match_key(str(left["away_name"]))) == (provider_match_key(str(right["home_name"])), provider_match_key(str(right["away_name"]))):
                            continue
                        home = crest_similarity(left["home_crest"], right["home_crest"])
                        away = crest_similarity(left["away_crest"], right["away_crest"])
                        if home is not None and away is not None and min(home, away) >= .84:
                            visual.append((left, right, home, away))
            if visual:
                print("Escudos: possíveis partidas equivalentes (somente revisão humana):")
                for left, right, home, away in visual:
                    print(f"  {left['competition']} {left['game_date']}: {left['home_name']} ↔ {right['home_name']} ({home:.0%}); {left['away_name']} ↔ {right['away_name']} ({away:.0%})")
            else:
                print("Escudos: nenhum novo candidato visual com similaridade alta.")
    else:
        print(f"Banco inicializado em {database_path}")


if __name__ == "__main__":
    main()

