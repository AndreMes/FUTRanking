from glicko_br.database import connect, initialise, store_match
from glicko_br.export_site_data import public_crest_url
from datetime import date

from glicko_br.global_sports_archive import BY_NAME, HISTORICAL_BRIDGE_COMPETITION_NAMES, REGIONAL_BRIDGE_COMPETITION_NAMES, STATE_COMPETITION_NAMES, _calendar_rounds, _crest_url, _existing_equivalent_id, _match_rows, _season_urls, bootstrap_competitions, sync_season


HTML = '''
<div class="gsa-widget-match-competition-list__rounds-item__title">Final</div>
<a href="https://globalsportsarchive.com/en/soccer/match/2026-10-24/guarani-vs-boa/12345" class="gsa-match-rounds-v2__match gsa-color-unset">
  <p>24.10.2026</p>
  <img src="https://images.example/guarani.png" alt="logo of Guarani FC"/>
  <div class="gsa-match-played"><div>2</div><div>: </div><div>1</div></div></div></div>
  <img src="https://images.example/boa.png" alt="logo of Boa EC"/>
</a>
'''


def test_gsa_parser_reads_completed_match_and_knockout_stage():
    rows = _match_rows(HTML, "Série C")

    assert rows == [{
        "external_id": "gsa:12345", "played_at": "2026-10-24T12:00:00-03:00", "competition": "Série C",
        "matchday": "", "stage": "Final", "group_name": "", "home_team": "Guarani FC", "away_team": "Boa EC",
        "home_crest": "https://images.example/guarani.png", "away_crest": "https://images.example/boa.png",
        "home_country": "Brasil", "away_country": "Brasil", "venue_country": "Brasil", "home_goals": "2", "away_goals": "1",
    }]


def test_gsa_crest_urls_stay_on_https():
    assert _crest_url("https://dsg-images.com/clubs/50x50/1.png") == "https://www.dsg-images.com/clubs/50x50/1.png"
    assert public_crest_url("https://dsg-images.com/clubs/50x50/1.png") == "https://www.dsg-images.com/clubs/50x50/1.png"


def test_gsa_ignores_invalid_card_that_repeats_the_same_club():
    invalid = HTML.replace("Boa EC", "Guarani FC")

    assert _match_rows(invalid, "Série C") == []


def test_gsa_reuses_equivalent_espn_match_instead_of_creating_duplicate():
    database = connect(":memory:")
    initialise(database)
    store_match(database, {
        "external_id": "espn:old", "played_at": "2026-10-24T19:30:00Z", "competition": "Série C",
        "home_team": "Guarani", "away_team": "Boa Esporte", "home_goals": "0", "away_goals": "0",
    })
    row = _match_rows(HTML, "Série C")[0]

    assert _existing_equivalent_id(database, row) == "espn:old"


def test_gsa_calendar_rounds_reads_every_public_gameweek():
    html = '''
    <div class="gsa-widget-match-competition-list__rounds-item__title">Regular Season</div>
    <div class="gsa-comp-calendar" data-competition_id="77984"
         data-weeks="{&quot;138513_1&quot;:1,&quot;138513_2&quot;:2}"></div>
    '''

    assert _calendar_rounds(html) == [
        ("Regular Season", "77984", "138513_1"),
        ("Regular Season", "77984", "138513_2"),
    ]


def test_gsa_season_catalog_accepts_sponsor_renames():
    html = '''
    <a href="https://globalsportsarchive.com/en/soccer/competition/paulistao-itaipava-2016/11212">2016</a>
    <a href="https://globalsportsarchive.com/en/soccer/competition/paulistao-casas-bahia-2026/78189">2026</a>
    '''

    assert _season_urls(html, BY_NAME["Campeonato Paulista"]) == {
        2016: "https://globalsportsarchive.com/en/soccer/competition/paulistao-itaipava-2016/11212",
        2026: "https://globalsportsarchive.com/en/soccer/competition/paulistao-casas-bahia-2026/78189",
    }


def test_historical_bootstrap_skips_a_season_absent_from_the_public_catalog():
    competition = BY_NAME["Campeonato Maranhense"]
    catalog = '<a href="https://globalsportsarchive.com/en/soccer/competition/maranhense-2017/2">2017</a>'

    class Client:
        request_count = 0

        def get(self, url):
            return catalog if url == competition.seed_url else HTML

        def get_gameweek(self, **kwargs):
            raise AssertionError("A página de teste não possui calendário paginado.")

    database = connect(":memory:")
    initialise(database)

    assert bootstrap_competitions(
        database, (competition.name,), client=Client(), today=date(2017, 12, 31)
    ) == 1


def test_historical_bridge_catalog_contains_the_requested_competitions():
    assert set(HISTORICAL_BRIDGE_COMPETITION_NAMES) == {
        "Campeonato Paulista", "Paulista A2", "Campeonato Carioca", "Campeonato Mineiro", "Campeonato Gaúcho",
        "Campeonato Paranaense", "Campeonato Baiano", "Campeonato Pernambucano", "Campeonato Cearense",
        "Campeonato Goiano", "Campeonato Catarinense", "Copa do Nordeste", "Copa Paulista",
        "Campeonato Paraense", "Campeonato Alagoano", "Campeonato Potiguar", "Campeonato Amazonense",
        "Campeonato Paraibano", "Campeonato Maranhense", "Campeonato Piauiense", "Campeonato Sergipano",
        "Campeonato Mato-Grossense",
        "Campeonato Acreano", "Campeonato Amapaense", "Campeonato Brasiliense", "Campeonato Capixaba",
        "Campeonato Rondoniense", "Campeonato Roraimense", "Campeonato Sul-Mato-Grossense",
        "Campeonato Tocantinense",
    }
    assert set(REGIONAL_BRIDGE_COMPETITION_NAMES) == {
        "Copa do Nordeste", "Copa Paulista", "Campeonato Paraense", "Campeonato Alagoano",
        "Campeonato Potiguar", "Campeonato Amazonense",
        "Campeonato Paraibano", "Campeonato Maranhense", "Campeonato Piauiense", "Campeonato Sergipano",
        "Campeonato Mato-Grossense",
        "Campeonato Acreano", "Campeonato Amapaense", "Campeonato Brasiliense", "Campeonato Capixaba",
        "Campeonato Rondoniense", "Campeonato Roraimense", "Campeonato Sul-Mato-Grossense",
        "Campeonato Tocantinense",
    }
    assert "Copa Paulista" not in STATE_COMPETITION_NAMES


def test_gsa_sync_walks_every_gameweek_on_annual_load():
    competition = BY_NAME["Série C"]
    seed = 'https://globalsportsarchive.com/en/soccer/competition/serie-c-2026/77984'
    page = '''
    <div class="gsa-widget-match-competition-list__rounds-item__title">Regular Season</div>
    <div class="gsa-comp-calendar" data-competition_id="77984"
         data-weeks="{&quot;138513_1&quot;:1,&quot;138513_2&quot;:2}"></div>
    '''

    class Client:
        def __init__(self):
            self.gameweeks = []

        def get(self, url):
            return seed if url == competition.seed_url else page

        def get_gameweek(self, **kwargs):
            self.gameweeks.append(kwargs["active_sub_round_key"])
            match_id = "1" if kwargs["active_sub_round_key"].endswith("_1") else "2"
            return HTML.replace("12345", match_id).replace("2026-10-24", f"2026-10-2{match_id}")

    database = connect(":memory:")
    initialise(database)
    client = Client()

    assert sync_season(database, competition, 2026, client=client, full=True) == (2, 0)
    assert client.gameweeks == ["138513_1", "138513_2"]

