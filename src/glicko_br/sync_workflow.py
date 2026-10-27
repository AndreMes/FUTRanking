"""Coleta ESPN incremental, com carga histórica única e reconciliação periódica."""
from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

from .database import connect, initialise, store_source_payload
from .espn import EspnError, sync_period

ESPN_BOOTSTRAP_VERSION = "espn-brazil-2016-v1"
HISTORY_START_YEAR = 2016


def reset_match_data(database) -> None:
    """Remove a carga anterior dentro da transação de migração ESPN."""
    for table in ("match_rating_effects", "rating_snapshots", "rating_states", "processed_matches", "fixtures", "matches", "source_payloads", "clubs", "rating_model"):
        database.execute(f"DELETE FROM {table}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', required=True)
    parser.add_argument('--watermark', required=True)
    parser.add_argument('--full', action='store_true', help='Reconcilia a temporada corrente inteira.')
    args = parser.parse_args()
    today = date.today()
    marker = Path(args.watermark)
    last_sync = date.fromisoformat(marker.read_text(encoding='utf-8').strip()) if marker.exists() else None
    if last_sync and last_sync > today:
        raise ValueError('A última sincronização está no futuro; verifique o banco antes de continuar.')
    database = connect(args.database)
    initialise(database)
    bootstrap = not database.execute(
        "SELECT 1 FROM source_payloads WHERE source='espn-bootstrap' AND request_path=? LIMIT 1",
        (ESPN_BOOTSTRAP_VERSION,),
    ).fetchone()
    with database:
        if bootstrap:
            reset_match_data(database)
            total = 0
            for season in range(HISTORY_START_YEAR, today.year + 1):
                count = sync_period(database, str(season))
                total += count
                print(f'Temporada {season}: {count} resultados ESPN encontrados.')
            if not total:
                raise EspnError('A carga histórica ESPN não retornou resultados; banco anterior preservado.')
            store_source_payload(database, "espn-bootstrap", ESPN_BOOTSTRAP_VERSION, "{}")
            print(f'Carga histórica ESPN concluída: {total} resultados.')
        else:
            start = min(today - timedelta(days=7), last_sync - timedelta(days=1)) if last_sync else today - timedelta(days=7)
            for offset in range((today - start).days + 1):
                checked = start + timedelta(days=offset)
                count = sync_period(database, checked.strftime('%Y%m%d'))
                print(f'{checked.isoformat()}: {count} resultados ESPN encontrados.')
            if args.full:
                count = sync_period(database, str(today.year))
                print(f'Reconciliação {today.year}: {count} resultados ESPN encontrados.')
    marker.write_text(today.isoformat() + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
