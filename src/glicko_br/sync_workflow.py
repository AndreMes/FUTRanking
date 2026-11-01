"""Coleta ESPN incremental, com carga histórica única e reconciliação periódica."""
from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path
from time import monotonic

from .competitions import COMPETITION_CATALOG_VERSION, DATA_ENRICHMENT_VERSION, ESPN_COMPETITIONS
from .database import HOME_ADVANTAGE, connect, initialise, prune_stale_fixtures, recreate_matches_table, store_source_payload
from .espn import EspnClient, EspnError, sync_fixture_schedule, sync_period
from .global_sports_archive import GlobalSportsArchiveClient, GlobalSportsArchiveError, bootstrap_national_cups, bootstrap_regional_bridges, bootstrap_serie_d, bootstrap_state_competitions, sync_current as sync_gsa_current

HISTORY_START_YEAR = 2016
ESPN_BOOTSTRAP_VERSION = f"espn-{HISTORY_START_YEAR}-{COMPETITION_CATALOG_VERSION}-{DATA_ENRICHMENT_VERSION}-home-{int(HOME_ADVANTAGE)}"
# A primeira expansão internacional revelou que o antigo identificador global
# por nome confundia homônimos de países diferentes (por exemplo Liverpool).
# Esta marca dispara uma única reconstrução com IDs estáveis do provedor.
IDENTITY_REBUILD_VERSION = "country-scoped-provider-identity-v1"
# Catálogo que já estava coberto antes da expansão europeia. Ao migrar o
# marcador, ele evita baixar novamente dezenas de milhares de partidas que já
# vivem no banco persistente.
LEGACY_ESPN_SLUGS = frozenset({
    "arg.1", "bra.1", "bra.2", "bra.3", "bra.4", "bra.camp.paulista",
    "bra.camp.carioca", "bra.camp.mineiro", "bra.camp.gaucho", "bra.copa_do_brazil",
    "conmebol.libertadores", "conmebol.sudamericana", "FIFA.CWC", "chi.1", "col.1",
    "ecu.1", "uru.1", "par.1", "per.1", "bol.1", "ven.1",
})
GSA_SERIE_D_BOOTSTRAP_VERSION = "global-sports-archive-serie-d-2016-v1"
GSA_STATE_BOOTSTRAP_VERSION = "global-sports-archive-state-leagues-2016-v1"
GSA_REGIONAL_BRIDGES_BOOTSTRAP_VERSION = "global-sports-archive-regional-bridges-2016-v4"
GSA_NATIONAL_CUPS_BOOTSTRAP_VERSION = "global-sports-archive-national-cups-2016-v1"


def reset_match_data(database) -> None:
    """Remove a carga anterior dentro da transação de migração ESPN."""
    for table in ("match_rating_effects", "match_forecasts", "rating_snapshots", "rating_states", "processed_matches", "fixtures", "matches", "source_payloads", "club_provider_ids", "club_aliases", "clubs", "rating_model", "model_evaluations"):
        database.execute(f"DELETE FROM {table}")


def _history_marker(competition) -> str:
    return f"{competition.espn_slug}:{competition.start_year}:v1"


def _has_history_marker(database, competition) -> bool:
    return bool(database.execute(
        "SELECT 1 FROM source_payloads WHERE source='espn-history-coverage' AND request_path=? LIMIT 1",
        (_history_marker(competition),),
    ).fetchone())


def _mark_history_loaded(database, competition) -> None:
    store_source_payload(database, "espn-history-coverage", _history_marker(competition), "{}")


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
    identity_rebuild = not database.execute(
        "SELECT 1 FROM source_payloads WHERE source='identity-rebuild' AND request_path=? LIMIT 1",
        (IDENTITY_REBUILD_VERSION,),
    ).fetchone()
    if identity_rebuild:
        print("[identidade] reconstrução única: substituindo nomes globais por identidade país+provedor.")
        with database:
            reset_match_data(database)
            recreate_matches_table(database)
            store_source_payload(database, "identity-rebuild", IDENTITY_REBUILD_VERSION, "{}")
    legacy_bootstrap = bool(database.execute(
        "SELECT 1 FROM source_payloads WHERE source='espn-bootstrap' LIMIT 1"
    ).fetchone())
    missing_history = [competition for competition in ESPN_COMPETITIONS if not _has_history_marker(database, competition)]
    # Bancos existentes ganham marcadores para as competições que já estavam
    # no catálogo. Só as ligas novas são baixadas; não há reconstrução total.
    if legacy_bootstrap:
        for competition in list(missing_history):
            if competition.espn_slug in LEGACY_ESPN_SLUGS:
                _mark_history_loaded(database, competition)
        missing_history = [competition for competition in ESPN_COMPETITIONS if not _has_history_marker(database, competition)]
    try:
        with database:
            if not legacy_bootstrap:
                # Primeiro banco: cria um acervo íntegro de uma vez.
                reset_match_data(database)
                recreate_matches_table(database)
                missing_history = list(ESPN_COMPETITIONS)
            if missing_history:
                total = 0
                for competition in missing_history:
                    competition_total = 0
                    started_competition = monotonic()
                    requests_before_competition = client.request_count
                    for season in range(max(HISTORY_START_YEAR, competition.start_year), today.year + 1):
                        started = monotonic()
                        requests_before = client.request_count
                        count = sync_period(
                            database, str(season), leagues={competition.espn_slug: competition.name}, client=client
                        )
                        total += count
                        competition_total += count
                        print(
                            f'[ESPN][histórico] {competition.name} {season}: {count} resultados; '
                            f'{client.request_count - requests_before} chamadas; {monotonic() - started:.1f}s.'
                        )
                    _mark_history_loaded(database, competition)
                    print(
                        f'[ESPN][histórico] {competition.name}: concluído — {competition_total} resultados; '
                        f'{client.request_count - requests_before_competition} chamadas; '
                        f'{monotonic() - started_competition:.1f}s.'
                    )
                if not total:
                    raise EspnError('A carga histórica ESPN não retornou resultados; banco anterior preservado.')
                store_source_payload(database, "espn-bootstrap", ESPN_BOOTSTRAP_VERSION, "{}")
                database.commit()
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
                # A rotina de resultados olha somente os dias recentes. Uma
                # passagem curta pela temporada corrente preserva os fixtures
                # futuros sem refazer o cálculo de partidas já finalizadas.
                started = monotonic()
                requests_before = client.request_count
                fixtures_count = sync_fixture_schedule(database, str(today.year), client=client)
                print(
                    f'[ESPN][agenda] {fixtures_count} fixtures futuros encontrados; '
                    f'{client.request_count - requests_before} chamadas; {monotonic() - started:.1f}s.'
                )
            gsa_bootstrap = not database.execute(
                "SELECT 1 FROM source_payloads WHERE source='global-sports-archive-bootstrap' AND request_path=? LIMIT 1",
                (GSA_SERIE_D_BOOTSTRAP_VERSION,),
            ).fetchone()
            if gsa_bootstrap:
                total = bootstrap_serie_d(database, client=gsa_client, today=today)
                store_source_payload(database, "global-sports-archive-bootstrap", GSA_SERIE_D_BOOTSTRAP_VERSION, "{}")
                database.commit()
                print(f'Carga histórica Série D concluída: {total} partidas GSA.')
            state_bootstrap = not database.execute(
                "SELECT 1 FROM source_payloads WHERE source='global-sports-archive-bootstrap' AND request_path=? LIMIT 1",
                (GSA_STATE_BOOTSTRAP_VERSION,),
            ).fetchone()
            if state_bootstrap:
                total = bootstrap_state_competitions(database, client=gsa_client, today=today)
                store_source_payload(database, "global-sports-archive-bootstrap", GSA_STATE_BOOTSTRAP_VERSION, "{}")
                database.commit()
                print(f'Carga histórica dos estaduais concluída: {total} partidas GSA.')
            regional_bootstrap = not database.execute(
                "SELECT 1 FROM source_payloads WHERE source='global-sports-archive-bootstrap' AND request_path=? LIMIT 1",
                (GSA_REGIONAL_BRIDGES_BOOTSTRAP_VERSION,),
            ).fetchone()
            if regional_bootstrap:
                total = bootstrap_regional_bridges(database, client=gsa_client, today=today)
                store_source_payload(database, "global-sports-archive-bootstrap", GSA_REGIONAL_BRIDGES_BOOTSTRAP_VERSION, "{}")
                database.commit()
                print(f'Carga histórica das pontes regionais concluída: {total} partidas GSA.')
            national_cups_bootstrap = not database.execute(
                "SELECT 1 FROM source_payloads WHERE source='global-sports-archive-bootstrap' AND request_path=? LIMIT 1",
                (GSA_NATIONAL_CUPS_BOOTSTRAP_VERSION,),
            ).fetchone()
            if national_cups_bootstrap:
                total = bootstrap_national_cups(database, client=gsa_client, today=today)
                store_source_payload(database, "global-sports-archive-bootstrap", GSA_NATIONAL_CUPS_BOOTSTRAP_VERSION, "{}")
                database.commit()
                print(f'Carga histórica das copas nacionais concluída: {total} partidas GSA.')
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
                database.commit()
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
