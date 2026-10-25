from unittest.mock import patch

from glicko_br.database import connect, initialise
from glicko_br.export_site_data import exported_fixtures, exported_matches, exported_simulation
from glicko_br.football_data import sync_season
from glicko_br.seed_site import import_snapshot


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


def test_daily_window_preserves_other_fixtures_and_confirmed_results():
    database = connect(':memory:')
    initialise(database)
    match = {'id': 42, 'utcDate': '2026-10-24T19:30:00Z', 'status': 'FINISHED',
             'homeTeam': {'name': 'Casa'}, 'awayTeam': {'name': 'Fora'},
             'score': {'fullTime': {'home': 2, 'away': 1}}}
    future = {'id': 43, 'utcDate': '2027-01-24T19:30:00Z', 'status': 'TIMED',
              'homeTeam': {'name': 'Casa'}, 'awayTeam': {'name': 'Fora'}, 'score': {}}
    response = [match, future]
    class Client:
        def get(self, path, **params):
            return {'matches': response}, '{}', path
    with patch('glicko_br.football_data.FootballDataClient', Client):
        sync_season(database, 2026)
        response[:] = [{**match, 'status': 'TIMED', 'score': {}}]
        sync_season(database, 2026, date_from='2026-10-20', date_to='2026-11-01')
    assert len(exported_matches(database)) == 1
    fixtures = exported_fixtures(database, [])
    assert len(fixtures) == 1 and fixtures[0]['scheduled_at'] == future['utcDate']


def test_seed_preserves_published_results_and_rejects_empty_snapshot():
    database = connect(':memory:')
    initialise(database)
    match = {'external_id': 'football-data:42', 'played_at': '2026-10-24T19:30:00Z',
             'competition': 'Série A', 'home_team': 'Casa', 'away_team': 'Fora',
             'home_goals': 2, 'away_goals': 1}
    assert import_snapshot(database, {'matches': [match]}) == 1
    assert exported_matches(database)[0]['home_goals'] == 2
    try:
        import_snapshot(database, {'matches': []})
    except ValueError:
        pass
    else:
        raise AssertionError('Um snapshot vazio não deve ser aceito')
