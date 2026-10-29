from glicko_br.database import connect, initialise, store_match
from glicko_br.club_identity import canonical_name


def _match(external_id, home, away, *, country="Brasil"):
    return {
        "external_id": external_id,
        "played_at": "2026-01-01T15:00:00+00:00",
        "competition": "Campeonato Paulista",
        "home_team": home,
        "away_team": away,
        "home_goals": 1,
        "away_goals": 0,
        "home_country": country,
        "away_country": country,
    }


def test_explicit_aliases_share_a_club_id(tmp_path):
    database = connect(tmp_path / "ranking.sqlite3")
    initialise(database)
    store_match(database, _match("one", "Palmeiras", "SE Palmeiras"))
    rows = database.execute("SELECT id, name FROM clubs ORDER BY id").fetchall()
    assert [(row["id"], row["name"]) for row in rows] == [(1, "Palmeiras")]


def test_ambiguous_names_are_not_merged(tmp_path):
    database = connect(tmp_path / "ranking.sqlite3")
    initialise(database)
    store_match(database, _match("one", "Botafogo", "Botafogo FC"))
    names = [row["name"] for row in database.execute("SELECT name FROM clubs ORDER BY name")]
    assert names == ["Botafogo", "Botafogo FC"]


def test_migration_merges_verified_legacy_alias_and_requires_rebuild(tmp_path):
    database = connect(tmp_path / "ranking.sqlite3")
    initialise(database)
    database.execute("INSERT INTO clubs(name, country) VALUES ('Palmeiras', 'Brasil')")
    database.execute("INSERT INTO clubs(name, country) VALUES ('SE Palmeiras', 'Brasil')")
    home_id = database.execute("SELECT id FROM clubs WHERE name='SE Palmeiras'").fetchone()[0]
    away_id = database.execute("SELECT id FROM clubs WHERE name='Palmeiras'").fetchone()[0]
    database.execute(
        """INSERT INTO matches(external_id, played_at, competition, home_club_id, away_club_id, home_goals, away_goals)
           VALUES ('legacy', '2020-01-01T12:00:00+00:00', 'Campeonato Paulista', ?, ?, 1, 0)""",
        (home_id, away_id),
    )
    database.execute("INSERT INTO processed_matches(external_id, processed_at) VALUES ('legacy', '2020-01-01T12:00:00+00:00')")
    database.commit()

    initialise(database)

    assert [row["name"] for row in database.execute("SELECT name FROM clubs")] == ["Palmeiras"]
    match = database.execute("SELECT home_club_id, away_club_id FROM matches WHERE external_id='legacy'").fetchone()
    assert match["home_club_id"] == match["away_club_id"] == 1
    assert database.execute("SELECT COUNT(*) FROM processed_matches").fetchone()[0] == 0


def test_only_brazilian_explicit_aliases_are_canonicalized():
    assert canonical_name("SE Palmeiras", "BR") == "Palmeiras"
    assert canonical_name("SE Palmeiras", "AR") == "SE Palmeiras"
