from glicko_br.sofascore import event_to_match


def test_finished_event_is_normalised():
    event = {"id": 5, "startTimestamp": 1712001600, "status": {"type": "finished"}, "homeTeam": {"name": "Casa"}, "awayTeam": {"name": "Fora"}, "homeScore": {"current": 2, "normaltime": 2}, "awayScore": {"current": 1, "normaltime": 1}}
    assert event_to_match(event, "Série A")["external_id"] == "sofascore:5"


def test_penalty_decision_is_draw_for_rating():
    event = {"id": 6, "startTimestamp": 1712001600, "status": {"type": "finished"}, "homeTeam": {"name": "Casa"}, "awayTeam": {"name": "Fora"}, "homeScore": {"current": 5, "normaltime": 1, "overtime": 1}, "awayScore": {"current": 4, "normaltime": 1, "overtime": 1}}
    match = event_to_match(event, "Copa do Brasil")
    assert match["home_goals"] == match["away_goals"] == "0"
