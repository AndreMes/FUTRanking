from glicko_br.database import connect, initialise, reconcile_club_identities, store_match


def match(external_id: str, home: str, away: str) -> dict[str, str]:
    return {
        "external_id": external_id, "played_at": "2026-02-01T12:00:00-03:00", "competition": "Campeonato Paulista",
        "home_team": home, "away_team": away, "home_country": "Brasil", "away_country": "Brasil",
        "home_goals": "1", "away_goals": "0",
    }


def test_known_provider_aliases_share_one_club_identity():
    database = connect(":memory:")
    initialise(database)
    store_match(database, match("one", "Palmeiras", "Santos"))
    store_match(database, match("two", "SE Palmeiras", "São Paulo FC"))

    clubs = [row["name"] for row in database.execute("SELECT name FROM clubs ORDER BY name")]
    assert "SE Palmeiras" not in clubs
    assert clubs.count("Palmeiras") == 1
    assert database.execute("SELECT COUNT(DISTINCT home_club_id) FROM matches WHERE external_id IN ('one', 'two')").fetchone()[0] == 1


def test_ambiguous_names_are_not_merged_by_text_similarity():
    database = connect(":memory:")
    initialise(database)
    store_match(database, match("one", "Botafogo", "Santos"))
    store_match(database, match("two", "Botafogo FC", "São Paulo"))

    assert database.execute("SELECT COUNT(*) FROM clubs WHERE name LIKE 'Botafogo%'").fetchone()[0] == 2


def test_legacy_alias_migration_merges_existing_matches_and_resets_processing():
    database = connect(":memory:")
    initialise(database)
    database.execute("INSERT INTO clubs(id, name, country) VALUES (1, 'Palmeiras', 'Brasil')")
    database.execute("INSERT INTO clubs(id, name, country) VALUES (2, 'SE Palmeiras', 'Brasil')")
    database.execute("INSERT INTO clubs(id, name, country) VALUES (3, 'Santos', 'Brasil')")
    database.execute("""INSERT INTO matches(external_id, played_at, competition, home_club_id, away_club_id, home_goals, away_goals)
                        VALUES ('legacy', '2026-02-01T12:00:00-03:00', 'Campeonato Paulista', 2, 3, 1, 0)""")
    database.execute("INSERT INTO processed_matches(external_id, processed_at) VALUES ('legacy', '2026-02-02')")

    merged, duplicates = reconcile_club_identities(database)

    assert (merged, duplicates) == (1, 0)
    assert database.execute("SELECT home_club_id FROM matches WHERE external_id='legacy'").fetchone()[0] == 1
    assert database.execute("SELECT COUNT(*) FROM processed_matches").fetchone()[0] == 0
