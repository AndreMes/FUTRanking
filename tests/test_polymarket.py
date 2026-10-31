from glicko_br.polymarket import event_odds, games_from_events, gamma_yes_price, keyset_url, serie_a_metadata, serie_metadata, series_ids_for_sport, yes_token_id


def test_series_ids_for_brazilian_sport_come_from_metadata():
    sports = [{"sport": "epl", "series": "12"}, {"sport": "bra", "series": "101, 102"}]
    assert series_ids_for_sport(sports) == ["101", "102"]


def test_metadata_falls_back_to_the_league_name_when_the_visual_route_is_not_an_id():
    sports = [{"sport": "br1", "name": "Brazilian Serie A", "series": "201", "primaryTagId": 999}]
    assert serie_a_metadata(sports) == sports[0]
    assert series_ids_for_sport(sports) == ["201"]


def test_series_b_is_discovered_independently_from_serie_a():
    sports = [
        {"sport": "bra", "name": "Brazilian Serie A", "series": "201"},
        {"sport": "brb", "name": "Brazilian Serie B", "series": "202", "primaryTagId": 1002},
    ]
    assert serie_metadata(sports, "serie_b") == sports[1]
    assert series_ids_for_sport(sports, "serie_b") == ["202"]


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


def test_yes_price_and_token_follow_the_yes_outcome_not_a_fixed_index():
    market = {
        "outcomes": '["No", "Yes"]',
        "outcomePrices": '["0.38", "0.62"]',
        "clobTokenIds": '["no-token", "yes-token"]',
    }
    assert yes_token_id(market) == "yes-token"
    assert gamma_yes_price(market) == 0.62


def test_games_from_events_excludes_halftime_and_non_competitive_triplets():
    markets = [
        {"slug": "bra-cor-mir-cor", "title": "COR", "outcomePrices": '["0.52", "0.48"]', "sportsMarketType": "moneyline"},
        {"slug": "bra-cor-mir-draw", "title": "DRAW", "outcomePrices": '["0.27", "0.73"]', "sportsMarketType": "moneyline"},
        {"slug": "bra-cor-mir-mir", "title": "MIR", "outcomePrices": '["0.22", "0.78"]', "sportsMarketType": "moneyline"},
    ]
    events = [
        {"slug": "bra-cor-mir", "title": "Corinthians vs. Mirassol", "markets": markets},
        {"slug": "bra-cor-mir-half", "title": "Corinthians vs. Mirassol - Halftime Result", "markets": markets},
        {"slug": "bra-cor-mir-resolved", "title": "Corinthians vs. Mirassol", "markets": [
            {**markets[0], "slug": "bra-cor-mir-resolved-cor", "outcomePrices": '["1.0", "0.0"]'},
            {**markets[1], "slug": "bra-cor-mir-resolved-draw", "outcomePrices": '["0.004", "0.996"]'},
            {**markets[2], "slug": "bra-cor-mir-resolved-mir", "outcomePrices": '["0.001", "0.999"]'},
        ]},
    ]
    assert [game["title"] for game in games_from_events(events)] == ["Corinthians vs. Mirassol"]
