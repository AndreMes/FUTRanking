from glicko_br.glicko2 import Rating
from glicko_br.simulation import simulate_season


def test_simulation_returns_title_and_relegation_probabilities():
    teams = [f"Clube {index:02}" for index in range(20)]
    completed = [
        {"home_team": teams[index], "away_team": teams[index + 1], "home_goals": 1, "away_goals": 0}
        for index in range(0, 20, 2)
    ]
    fixtures = [{"home_team": teams[0], "away_team": teams[1]}]
    result = simulate_season(completed, fixtures, {team: Rating() for team in teams}, scenarios=1_000, seed=7)
    assert result["available"] is True
    assert len(result["teams"]) == 20
    assert abs(sum(team["champion_probability"] for team in result["teams"]) - 1.0) < 1e-9
    assert abs(sum(team["relegation_probability"] for team in result["teams"]) - 4.0) < 1e-9

