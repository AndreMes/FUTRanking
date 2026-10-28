"""Coleta ESPN incremental, com carga histórica única e reconciliação periódica."""
from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

from .competitions import COMPETITION_CATALOG_VERSION, DATA_ENRICHMENT_VERSION
from .database import connect, initialise, prune_stale_fixtures, recreate_matches_table, store_source_payload
from .espn import EspnClient, EspnError, sync_period

HISTORY_START_YEAR = 2016
ESPN_BOOTSTRAP_VERSION = f"espn-{HISTORY_START_YEAR}-{COMPETITION_CATALOG_VERSION}-{DATA_ENRICHMENT_VERSION}"


def reset_match_data(database) -> None:
    """Remove a carga anterior dentro da transação de migração ESPN."""
    for table in ("match_rating_effects", "match_forecasts", "rating_snapshots", "rating_states", "processed_matches", "fixtures", "matches", "source_payloads", "clubs", "rating_model", "model_evaluations"):
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
    client = EspnClient()
    bootstrap = not database.execute(
        "SELECT 1 FROM source_payloads WHERE source='espn-bootstrap' AND request_path=? LIMIT 1",
        (ESPN_BOOTSTRAP_VERSION,),
    ).fetchone()
    try:
        with database:
            if bootstrap:
                # Não misturamos IDs de fontes diferentes: a transação troca todo o histórico de uma vez.
                reset_match_data(database)
                recreate_matches_table(database)
                total = 0
                for season in range(HISTORY_START_YEAR, today.year + 1):
                    count = sync_period(database, str(season), client=client)
                    total += count
                    print(f'Temporada {season}: {count} resultados ESPN encontrados.')
                if not total:
                    raise EspnError('A carga histórica ESPN não retornou resultados; banco anterior preservado.')
                store_source_payload(database, "espn-bootstrap", ESPN_BOOTSTRAP_VERSION, "{}")
                print(f'Carga histórica ESPN concluída: {total} resultados.')
            else:
                # Janela curta: revisa uma semana para absorver correções sem consultar temporadas inteiras todo dia.
                start = min(today - timedelta(days=7), last_sync - timedelta(days=1)) if last_sync else today - timedelta(days=7)
                for offset in range((today - start).days + 1):
                    checked = start + timedelta(days=offset)
                    count = sync_period(database, checked.strftime('%Y%m%d'), client=client)
                    print(f'{checked.isoformat()}: {count} resultados ESPN encontrados.')
                if args.full:
                    count = sync_period(database, str(today.year), client=client)
                    print(f'Reconciliação {today.year}: {count} resultados ESPN encontrados.')
            removed = prune_stale_fixtures(database, before=(today - timedelta(days=1)).isoformat())
            if removed:
                print(f'{removed} fixtures antigos sem placar removidos.')
    except EspnError:
        raise
    # O marcador só é publicado junto com o banco após processamento bem-sucedido.
    marker.write_text(today.isoformat() + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
