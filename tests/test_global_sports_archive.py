from glicko_br.database import connect, initialise, store_match
from glicko_br.global_sports_archive import (
    BY_NAME,
    STATE_COMPETITION_NAMES,
    _season_urls,
    _calendar_rounds,
    _existing_equivalent_id,
    _match_rows,
    sync_season,
)

HTML = """
<div class="gsa-widget-match-competition-list__rounds-item__title">Final</div>
<a href="https://globalsportsarchive.com/en/soccer/match/2026-10-24/guarani-vs-boa/12345" class="gsa-match-rounds-v2__match gsa-color-unset">
  <img src="https://images.example/guarani.png" alt="logo of Guarani FC"/>
  <div class="gsa-match-played"><div>2</div><div>: </div><div>1</div></div></div></div>
  <img src="https://images.example/boa.png" alt="logo of Boa EC"/>
</a>
"""

def test_gsa_parser_reads_completed_match_and_stage():
    rows = _match_rows(HTML, "Série C")
    assert rows[0]["external_id"] == "gsa:12345"
    assert rows[0]["stage"] == "Final"
    assert rows[0]["home_team"] == "Guarani FC"
    assert rows[0]["away_goals"] == "1"

def test_gsa_ignores_invalid_card_that_repeats_the_same_club():
    invalid = HTML.replace("Boa EC", "Guarani FC")
    assert _match_rows(invalid, "Série C") == []

def test_gsa_reuses_equivalent_espn_match():
    database = connect(":memory:")
    initialise(database)
    store_match(database, {
        "external_id": "espn:old", "played_at": "2026-10-24T19:30:00Z",
        "competition": "Série C", "home_team": "Guarani",
        "away_team": "Boa Esporte", "home_goals": "0", "away_goals": "0",
    })
    assert _existing_equivalent_id(database, _match_rows(HTML, "Série C")[0]) == "espn:old"

def test_gsa_calendar_reads_public_gameweeks():
    html = """
    <div class="gsa-widget-match-competition-list__rounds-item__title">Regular Season</div>
    <div class="gsa-comp-calendar" data-competition_id="77984"
         data-weeks="{&quot;138513_1&quot;:1,&quot;138513_2&quot;:2}"></div>
    """
    assert _calendar_rounds(html) == [
        ("Regular Season", "77984", "138513_1"),
        ("Regular Season", "77984", "138513_2"),
    ]

def test_gsa_season_catalog_accepts_sponsor_renames():
    html = """
    <a href="https://globalsportsarchive.com/en/soccer/competition/paulistao-itaipava-2016/11212">2016</a>
    <a href="https://globalsportsarchive.com/en/soccer/competition/paulistao-casas-bahia-2026/78189">2026</a>
    """
    assert _season_urls(html, BY_NAME["Campeonato Paulista"]) == {
        2016: "https://globalsportsarchive.com/en/soccer/competition/paulistao-itaipava-2016/11212",
        2026: "https://globalsportsarchive.com/en/soccer/competition/paulistao-casas-bahia-2026/78189",
    }

def test_state_competition_catalog_contains_requested_bridges():
    assert set(STATE_COMPETITION_NAMES) == {
        "Campeonato Paulista", "Paulista A2", "Campeonato Carioca", "Campeonato Mineiro", "Campeonato Gaúcho",
        "Campeonato Paranaense", "Campeonato Baiano", "Campeonato Pernambucano", "Campeonato Cearense",
        "Campeonato Goiano", "Campeonato Catarinense",
    }

def test_gsa_sync_walks_all_gameweeks_on_full_load():
    competition = BY_NAME["Série C"]
    seed = "https://globalsportsarchive.com/en/soccer/competition/serie-c-2026/77984"
    page = """
    <div class="gsa-widget-match-competition-list__rounds-item__title">Regular Season</div>
    <div class="gsa-comp-calendar" data-competition_id="77984"
         data-weeks="{&quot;138513_1&quot;:1,&quot;138513_2&quot;:2}"></div>
    """
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
