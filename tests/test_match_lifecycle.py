from unittest.mock import patch

from glicko_br.database import connect, initialise
from glicko_br.export_site_data import exported_fixtures, exported_matches, exported_simulation
from glicko_br.football_data import sync_season


def test_pending_match_stays_visible_until_result_arrives():
    database = connect(":memory:")
    initialise(database)
    match = {"id": 42, "utcDate": "2026-10-24T19:30:00Z", "status": "IN_PLAY",
             "homeTeam": {"name": "Casa"}, "awayTeam": {"name": "Fora"},
             "score": {"fullTime": {"home": None, "away": None}}}
    class Client:
        def get(self, path, **params):
            assert params == {"season": 2026}
            return {"matches": [match]}, "{}", path

    with patch("glicko_br.football_data.FootballDataClient", Client):
        sync_season(database, 2026)
        fixtures = exported_fixtures(database, [])
        assert len(fixtures) == 1 and fixtures[0]["status"] == "IN_PLAY"
        assert not exported_matches(database)
        with patch("glicko_br.export_site_data.simulate_season", return_value={"available": True, "teams": []}) as simulate:
            assert exported_simulation(database, [], fixtures)["available"]
            assert simulate.call_args.args[1] == fixtures
        match["status"] = "FINISHED"
        match["score"]["fullTime"] = {"home": 2, "away": 1}
        sync_season(database, 2026)
        assert not exported_fixtures(database, [])
        assert len(exported_matches(database)) == 1


def test_finished_without_score_remains_pending():
    database = connect(":memory:")
    initialise(database)
    match = {"id": 43, "utcDate": "2026-10-24T19:30:00Z", "status": "FINISHED",
             "homeTeam": {"name": "Casa"}, "awayTeam": {"name": "Fora"}, "score": {"fullTime": {}}}
    class Client:
        def get(self, path, **params):
            return {"matches": [match]}, "{}", path
    with patch("glicko_br.football_data.FootballDataClient", Client):
        sync_season(database, 2026)
    assert len(exported_fixtures(database, [])) == 1
    assert not exported_matches(database)

