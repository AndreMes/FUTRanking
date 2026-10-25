"""Coleta incremental para o workflow, com reconciliação periódica."""
from __future__ import annotations

import argparse
import time
from datetime import date, timedelta
from pathlib import Path

from .database import connect, initialise
from .football_data import FootballDataError, sync_season


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', required=True)
    parser.add_argument('--watermark', required=True)
    parser.add_argument('--full', action='store_true')
    args = parser.parse_args()
    today = date.today()
    marker = Path(args.watermark)
    last_sync = date.fromisoformat(marker.read_text(encoding='utf-8').strip()) if marker.exists() else None
    if last_sync and last_sync > today:
        raise ValueError('A última sincronização está no futuro; verifique o banco antes de continuar.')
    start = min(today - timedelta(days=7), last_sync - timedelta(days=1)) if last_sync else None
    full = args.full or last_sync is None
    database = connect(args.database)
    initialise(database)
    first_year = 2023 if full else max(2023, start.year)
    for season in range(first_year, today.year + 1):
        for attempt in range(3):
            try:
                count = sync_season(database, season, **({} if full else {
                    'date_from': start.isoformat(), 'date_to': (today + timedelta(days=91)).isoformat()}))
                print(f'Temporada {season}: {count} resultados encontrados.')
                break
            except FootballDataError as error:
                if 'HTTP 429' not in str(error) or attempt == 2:
                    raise
                print('Limite de requisições: aguardando 60 segundos.')
                time.sleep(60)
    # O marcador só é publicado junto com o banco após processamento bem-sucedido.
    marker.write_text(today.isoformat() + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()

