from glicko_br.football_data import match_to_row


def test_match_is_normalised():
    match = {"id": 42, "utcDate": "2024-04-14T19:00:00Z", "homeTeam": {"name": "Casa"}, "awayTeam": {"name": "Fora"}, "score": {"fullTime": {"home": 2, "away": 1}}}
    row = match_to_row(match)
    assert row == {"external_id": "football-data:42", "played_at": "2024-04-14T19:00:00Z", "competition": "Série A", "matchday": "", "stage": "", "group_name": "", "home_team": "Casa", "away_team": "Fora", "home_crest": "", "away_crest": "", "home_goals": "2", "away_goals": "1"}

