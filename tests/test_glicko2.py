from glicko_br.database import connect, initialise, latest_ranking, process_pending, rebuild, store_match
from glicko_br.glicko2 import Rating, expected_score, update, OpponentResult


def test_home_advantage_changes_only_expectation():
    equal = Rating()
    assert expected_score(equal, equal, 55) > 0.5
    assert expected_score(equal, equal, -55) < 0.5


def test_win_increases_rating_and_reduces_rd():
    before = Rating()
    after = update(before, [OpponentResult(Rating(), 1.0, 55)])
    assert after.rating > before.rating
    assert after.rd < before.rd


def test_rebuild_is_idempotent_and_stores_history():
    database = connect(":memory:")
    initialise(database)
    store_match(database, {"external_id": "fixture-1", "played_at": "2025-04-01T20:00:00Z", "competition": "Série A", "home_team": "Clube Azul", "away_team": "Clube Verde", "home_goals": "2", "away_goals": "0"})
    store_match(database, {"external_id": "fixture-2", "played_at": "2025-04-02T20:00:00Z", "competition": "Copa do Brasil", "home_team": "Clube Verde", "away_team": "Clube Azul", "home_goals": "1", "away_goals": "1"})
    assert rebuild(database) == 2
    first = [(row["name"], row["rating"], row["rd"]) for row in latest_ranking(database)]
    assert rebuild(database) == 2
    second = [(row["name"], row["rating"], row["rd"]) for row in latest_ranking(database)]
    assert first == second
    assert len(first) == 2


def test_club_without_game_on_latest_day_remains_in_ranking():
    database = connect(":memory:")
    initialise(database)
    store_match(database, {"external_id": "fixture-1", "played_at": "2025-04-01T20:00:00Z", "competition": "Série A", "home_team": "Azul", "away_team": "Verde", "home_goals": "1", "away_goals": "0"})
    store_match(database, {"external_id": "fixture-2", "played_at": "2025-04-02T20:00:00Z", "competition": "Série A", "home_team": "Amarelo", "away_team": "Roxo", "home_goals": "1", "away_goals": "1"})
    rebuild(database)
    assert {row["name"] for row in latest_ranking(database)} == {"Azul", "Verde", "Amarelo", "Roxo"}


def test_inactivity_between_seasons_increases_rd():
    database = connect(":memory:")
    initialise(database)
    store_match(database, {"external_id": "fixture-1", "played_at": "2024-12-01T20:00:00Z", "competition": "Série A", "home_team": "Azul", "away_team": "Verde", "home_goals": "1", "away_goals": "0"})
    store_match(database, {"external_id": "fixture-2", "played_at": "2025-04-01T20:00:00Z", "competition": "Série A", "home_team": "Amarelo", "away_team": "Roxo", "home_goals": "1", "away_goals": "1"})
    rebuild(database)
    azul = next(row for row in latest_ranking(database) if row["name"] == "Azul")
    assert azul["rd"] > 290


def test_processes_only_new_matches_in_timestamp_order():
    database = connect(":memory:")
    initialise(database)
    store_match(database, {"external_id": "late", "played_at": "2025-04-01T22:00:00Z", "competition": "Série A", "home_team": "Azul", "away_team": "Verde", "home_goals": "0", "away_goals": "1"})
    store_match(database, {"external_id": "early", "played_at": "2025-04-01T18:00:00Z", "competition": "Série A", "home_team": "Azul", "away_team": "Verde", "home_goals": "1", "away_goals": "0"})
    assert process_pending(database) == 2
    first = [(row["name"], row["rating"]) for row in latest_ranking(database)]
    assert process_pending(database) == 0
    assert first == [(row["name"], row["rating"]) for row in latest_ranking(database)]

