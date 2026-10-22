from glicko_br.api_football import fixture_to_match


def test_fixture_is_normalised():
    fixture = {"fixture": {"id": 99, "date": "2026-05-01T20:00:00+00:00"}, "teams": {"home": {"name": "Time Casa"}, "away": {"name": "Time Fora"}}, "goals": {"home": 2, "away": 1}, "score": {"penalty": {"home": None, "away": None}}}
    assert fixture_to_match(fixture, "Série A")["external_id"] == "api-football:99"


def test_penalty_shootout_is_a_draw_for_rating():
    fixture = {"fixture": {"id": 100, "date": "2026-05-01T20:00:00+00:00"}, "teams": {"home": {"name": "Casa"}, "away": {"name": "Fora"}}, "goals": {"home": 5, "away": 4}, "score": {"penalty": {"home": 5, "away": 4}}}
    match = fixture_to_match(fixture, "Copa do Brasil")
    assert match["home_goals"] == match["away_goals"] == "0"
