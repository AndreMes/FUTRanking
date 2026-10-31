from glicko_br.polymarket import event_odds, games_from_events, keyset_url, serie_a_metadata, series_ids_for_sport


def test_series_ids_for_brazilian_sport_come_from_metadata():
    sports = [{"sport": "epl", "series": "12"}, {"sport": "bra", "series": "101, 102"}]
    assert series_ids_for_sport(sports) == ["101", "102"]


def test_metadata_falls_back_to_the_league_name_when_the_visual_route_is_not_an_id():
    sports = [{"sport": "br1", "name": "Brazilian Serie A", "series": "201", "primaryTagId": 999}]
    assert serie_a_metadata(sports) == sports[0]
    assert series_ids_for_sport(sports) == ["201"]


def test_keyset_url_uses_cursor_not_offset():
    url = keyset_url([("series_id", "101"), ("series_id", "102")], "next-page-token")
    assert "events/keyset?" in url
    assert "series_id=101" in url and "series_id=102" in url
    assert "after_cursor=next-page-token" in url
    assert "offset" not in url


def test_games_from_events_uses_embedded_api_markets():
    events = [{
        "slug": "bra-cor1-mir-2026-10-30",
        "title": "SC Corinthians Paulista vs. Mirassol FC",
        "eventStartTime": "2026-10-30T23:00:00Z",
        "markets": [
            {"slug": "bra-cor1-mir-2026-10-30-cor1", "title": "COR1", "outcomePrices": '["0.55", "0.45"]'},
            {"slug": "bra-cor1-mir-2026-10-30-draw", "title": "DRAW", "outcomePrices": '["0.27", "0.73"]'},
            {"slug": "bra-cor1-mir-2026-10-30-mir", "title": "MIR", "outcomePrices": '["0.20", "0.80"]'},
        ],
    }]
    assert games_from_events(events) == [{
        "title": "SC Corinthians Paulista vs. Mirassol FC",
        "home": 0.55,
        "draw": 0.27,
        "away": 0.20,
        "codes": {"home": "COR1", "away": "MIR"},
        "scheduled_at": "2026-10-30T23:00:00Z",
        "event_slug": "bra-cor1-mir-2026-10-30",
    }]


def test_event_odds_uses_moneyline_contract_suffixes():
    event = {"slug": "bra-cor1-mir-2026-10-30", "title": "SC Corinthians Paulista vs. Mirassol FC"}
    markets = [
        {"slug": "bra-cor1-mir-2026-10-30-cor1", "title": "COR1", "outcomePrices": '["0.55", "0.45"]'},
        {"slug": "bra-cor1-mir-2026-10-30-draw", "title": "DRAW", "outcomePrices": '["0.27", "0.73"]'},
        {"slug": "bra-cor1-mir-2026-10-30-mir", "title": "MIR", "outcomePrices": '["0.20", "0.80"]'},
        {"slug": "bra-cor1-mir-2026-10-30-total-2pt5", "title": "O 2.5", "outcomePrices": '["0.49", "0.51"]'},
    ]
    assert event_odds(event, markets)["codes"] == {"home": "COR1", "away": "MIR"}
