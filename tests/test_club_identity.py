from glicko_br.club_identity import canonical_name, must_remain_separate
from glicko_br.database import connect, identity_candidates, initialise, reconcile_club_identities, reconcile_provider_identities, store_match


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


def test_state_is_inferred_from_state_league_and_keeps_candidates_for_review():
    database = connect(":memory:")
    initialise(database)
    store_match(database, match("one", "Botafogo", "Flamengo"))
    store_match(database, match("two", "Botafogo FC", "Vasco da Gama"))

    states = dict(database.execute("SELECT name, state FROM clubs"))
    assert states["Botafogo"] == "SP"
    assert states["Botafogo FC"] == "SP"
    assert identity_candidates(database) == [{"state": "SP", "key": "botafogo", "clubs": ["Botafogo", "Botafogo FC"]}]


def test_provider_reconciliation_handles_institutional_names_only_with_full_match_evidence():
    database = connect(":memory:")
    initialise(database)
    store_match(database, {**match("espn:one", "Ferroviária", "Maringá"), "competition": "Série C"})
    store_match(database, {**match("gsa:one", "Associação Ferroviária de Esportes", "Maringá FC"), "competition": "Série C"})

    merged, duplicates = reconcile_provider_identities(database)

    assert (merged, duplicates) == (2, 1)
    assert [row["name"] for row in database.execute("SELECT name FROM clubs ORDER BY name")] == ["Ferroviária", "Maringá"]


def test_reviewed_aliases_from_first_admin_round():
    assert canonical_name("Paysandu SC", "BR") == "Paysandu"
    assert canonical_name("Rio Branco FC", "BR") == "Rio Branco AC"
    assert canonical_name("Águia de Marabá FC", "BR") == "Aguia de Maraba"
    assert canonical_name("EC Democrata", "BR") == "Democrata FC"


def test_second_admin_round_aliases_and_separate_decisions():
    assert canonical_name("EC Internacional", "BR") == "Internacional"
    assert canonical_name("São Bernardo FC", "BR") == "São Bernardo"
    assert canonical_name("EC XV de Novembro de Piracicaba", "BR") == "XV de Piracicaba"
    assert must_remain_separate("América FC", "América SE", "BR")
    assert must_remain_separate("Náutico", "Náutico FC", "BR")


def test_unmergeable_provider_candidate_does_not_clear_processed_ratings():
    database = connect(":memory:")
    initialise(database)
    for name in ("Equipe", "Equipe FC", "Rival", "Rival FC"):
        database.execute("INSERT INTO clubs(name, country) VALUES (?, 'Brasil')", (name,))
    ids = {row["name"]: row["id"] for row in database.execute("SELECT id, name FROM clubs")}
    def insert(external_id, played_at, home, away):
        database.execute(
            """INSERT INTO matches(external_id, played_at, competition, home_club_id, away_club_id, home_goals, away_goals)
               VALUES (?, ?, 'Série C', ?, ?, 1, 0)""",
            (external_id, played_at, ids[home], ids[away]),
        )
    insert("espn:one", "2026-01-01T12:00:00-03:00", "Equipe", "Rival")
    insert("gsa:one", "2026-01-01T12:00:00-03:00", "Equipe FC", "Rival FC")
    insert("other:one", "2026-01-02T12:00:00-03:00", "Equipe", "Equipe FC")
    insert("other:two", "2026-01-03T12:00:00-03:00", "Rival", "Rival FC")
    database.execute("INSERT INTO processed_matches(external_id, processed_at) VALUES ('espn:one', '2026-01-01')")

    assert reconcile_provider_identities(database) == (0, 0)
    assert database.execute("SELECT COUNT(*) FROM processed_matches").fetchone()[0] == 1

