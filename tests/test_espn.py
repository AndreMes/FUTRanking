from unittest.mock import patch

from glicko_br.database import connect, initialise
from glicko_br.espn import sync_period
from glicko_br.export_site_data import exported_fixtures, exported_matches


def event(event_id: str = "123", *, completed: bool = True) -> dict:
    return {
        "id": event_id,
        "date": "2026-10-24T19:30Z",
        "season": {"slug": "2026-brasileiro-serie-a"},
        "status": {"type": {"completed": completed, "name": "STATUS_FULL_TIME" if completed else "STATUS_SCHEDULED"}},
        "competitions": [{"competitors": [
            {"homeAway": "home", "score": "2" if completed else None, "team": {"displayName": "Casa", "logo": "home.png"}},
            {"homeAway": "away", "score": "1" if completed else None, "team": {"displayName": "Fora", "logo": "away.png"}},
        ]}],
    }


def test_espn_event_upserts_by_stable_event_id_and_final_beats_fixture():
    database = connect(":memory:")
    initialise(database)
    payload = {"events": [event(completed=False)]}

    class Client:
        def get_scoreboard(self, league, *, dates):
            return payload, "{}", f"/{league}/scoreboard"

    with patch("glicko_br.espn.EspnClient", Client):
        sync_period(database, "20261024", leagues={"bra.1": "Série A"})
        assert len(exported_fixtures(database, [])) == 1
        payload["events"] = [event(completed=True)]
        sync_period(database, "20261024", leagues={"bra.1": "Série A"})
        sync_period(database, "20261024", leagues={"bra.1": "Série A"})

    assert not exported_fixtures(database, [])
    matches = exported_matches(database)
    assert len(matches) == 1
    assert matches[0]["external_id"] == "espn:123"


def test_espn_infers_domestic_country_without_requesting_profiles():
    database = connect(":memory:")
    initialise(database)
    database.execute("INSERT INTO clubs(name, country) VALUES (?, ?)", ("Casa", "Brasil"))
    payload = {"events": [event()]}
    competitors = payload["events"][0]["competitions"][0]["competitors"]
    competitors[0]["team"]["id"] = "home-id"
    competitors[1]["team"]["id"] = "away-id"

    class Client:
        def __init__(self):
            self.country_requests = []

        def get_scoreboard(self, league, *, dates):
            return payload, "{}", f"/{league}/scoreboard"

        def get_team_country(self, league, team_id):
            self.country_requests.append(team_id)
            return "Argentina"

    client = Client()
    sync_period(database, "20261024", leagues={"bra.1": "Série A"}, client=client)

    assert client.country_requests == []
    countries = dict(database.execute("SELECT name, country FROM clubs"))
    assert countries == {"Casa": "Brasil", "Fora": "Brasil"}
