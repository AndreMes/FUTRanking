"""Coleta ESPN incremental, com carga histórica única e reconciliação periódica."""
from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path
from time import monotonic

from .competitions import COMPETITION_CATALOG_VERSION, DATA_ENRICHMENT_VERSION
from .database import HOME_ADVANTAGE, connect, initialise, prune_stale_fixtures, recreate_matches_table, store_source_payload
from .espn import EspnClient, EspnError, sync_period
from .global_sports_archive import GlobalSportsArchiveClient, GlobalSportsArchiveError, bootstrap_serie_d, bootstrap_state_competitions, sync_current as sync_gsa_current

HISTORY_START_YEAR = 2016
ESPN_BOOTSTRAP_VERSION = f"espn-{HISTORY_START_YEAR}-{COMPETITION_CATALOG_VERSION}-{DATA_ENRICHMENT_VERSION}-home-{int(HOME_ADVANTAGE)}"
GSA_SERIE_D_BOOTSTRAP_VERSION = "global-sports-archive-serie-d-2016-v1"
GSA_STATE_BOOTSTRAP_VERSION = "global-sports-archive-state-leagues-2016-v1"


def reset_match_data(database) -> None:
    """Remove a carga anterior dentro da transação de migração ESPN."""
    for table in ("match_rating_effects", "match_forecasts", "rating_snapshots", "rating_states", "processed_matches", "fixtures", "matches", "source_payloads", "club_aliases", "clubs", "rating_model", "model_evaluations"):
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
    gsa_client = GlobalSportsArchiveClient()
    workflow_started = monotonic()
    print(f"[sync] início: {today.isoformat()}; última sincronização: {last_sync or 'nenhuma'}; modo completo: {args.full}.")
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
                    started = monotonic()
                    requests_before = client.request_count
                    count = sync_period(database, str(season), client=client)
                    total += count
                    print(
                        f'[ESPN][histórico] temporada {season}: {count} resultados; '
                        f'{client.request_count - requests_before} chamadas; {monotonic() - started:.1f}s.'
                    )
                if not total:
                    raise EspnError('A carga histórica ESPN não retornou resultados; banco anterior preservado.')
                store_source_payload(database, "espn-bootstrap", ESPN_BOOTSTRAP_VERSION, "{}")
                print(f'Carga histórica ESPN concluída: {total} resultados.')
            else:
                # Em rotina normal, retoma o último sucesso com um dia extra de
                # segurança. Se algum ciclo falhar, o marcador persistido faz a
                # próxima execução recuperar automaticamente o período perdido.
                start = min(last_sync - timedelta(days=1), today - timedelta(days=1)) if last_sync else today - timedelta(days=1)
                print(f'[ESPN][rotina] consultando {start.isoformat()} até {today.isoformat()} (1 dia de segurança).')
                for offset in range((today - start).days + 1):
                    checked = start + timedelta(days=offset)
                    started = monotonic()
                    requests_before = client.request_count
                    count = sync_period(database, checked.strftime('%Y%m%d'), client=client)
                    print(
                        f'[ESPN][rotina] {checked.isoformat()}: {count} resultados; '
                        f'{client.request_count - requests_before} chamadas; {monotonic() - started:.1f}s.'
                    )
                if args.full:
                    started = monotonic()
                    requests_before = client.request_count
                    count = sync_period(database, str(today.year), client=client)
                    print(
                        f'[ESPN][reconciliação] {today.year}: {count} resultados; '
                        f'{client.request_count - requests_before} chamadas; {monotonic() - started:.1f}s.'
                    )
            gsa_bootstrap = not database.execute(
                "SELECT 1 FROM source_payloads WHERE source='global-sports-archive-bootstrap' AND request_path=? LIMIT 1",
                (GSA_SERIE_D_BOOTSTRAP_VERSION,),
            ).fetchone()
            if gsa_bootstrap:
                total = bootstrap_serie_d(database, client=gsa_client, today=today)
                store_source_payload(database, "global-sports-archive-bootstrap", GSA_SERIE_D_BOOTSTRAP_VERSION, "{}")
                print(f'Carga histórica Série D concluída: {total} partidas GSA.')
            state_bootstrap = not database.execute(
                "SELECT 1 FROM source_payloads WHERE source='global-sports-archive-bootstrap' AND request_path=? LIMIT 1",
                (GSA_STATE_BOOTSTRAP_VERSION,),
            ).fetchone()
            if state_bootstrap:
                total = bootstrap_state_competitions(database, client=gsa_client, today=today)
                store_source_payload(database, "global-sports-archive-bootstrap", GSA_STATE_BOOTSTRAP_VERSION, "{}")
                print(f'Carga histórica dos estaduais concluída: {total} partidas GSA.')
            current_gsa_version = f"global-sports-archive-current-{today.year}-v2-states"
            current_gsa_bootstrap = not database.execute(
                "SELECT 1 FROM source_payloads WHERE source='global-sports-archive-current' AND request_path=? LIMIT 1",
                (current_gsa_version,),
            ).fetchone()
            # A Série C preserva o legado ESPN: a GSA somente concilia e atualiza
            # a temporada corrente. A primeira coleta anual percorre tudo; nas
            # seguintes, apenas as duas rodadas mais recentes de cada fase.
            gsa_total, gsa_reused = sync_gsa_current(database, client=gsa_client, today=today, full=current_gsa_bootstrap or args.full)
            if current_gsa_bootstrap:
                store_source_payload(database, "global-sports-archive-current", current_gsa_version, "{}")
            print(f'Global Sports Archive: {gsa_client.request_count} chamadas realizadas; {gsa_total} partidas verificadas, {gsa_reused} conciliadas com a ESPN.')
            removed = prune_stale_fixtures(database, before=(today - timedelta(days=1)).isoformat())
            if removed:
                print(f'{removed} fixtures antigos sem placar removidos.')
            print(f'ESPN: {client.request_count} chamadas realizadas com intervalo mínimo de 0,35 s.')
            print(f'[sync] coleta concluída em {monotonic() - workflow_started:.1f}s.')
    except (EspnError, GlobalSportsArchiveError):
        raise
    # O marcador só é publicado junto com o banco após processamento bem-sucedido.
    marker.write_text(today.isoformat() + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
