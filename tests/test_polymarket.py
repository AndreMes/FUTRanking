from glicko_br.polymarket import extract_games


def test_extract_games_reads_visible_moneyline_triplet():
    markup = """
    <h3>SC Corinthians Paulista vs. Mirassol FC</h3>
    <div>COR1 55¢</div><div>DRAW 27¢</div><div>MIR 20¢</div>
    """
    assert extract_games(markup) == [{
        "title": "SC Corinthians Paulista vs. Mirassol FC",
        "home": 0.55,
        "draw": 0.27,
        "away": 0.20,
        "codes": {"home": "COR1", "away": "MIR"},
    }]


def test_extract_games_reads_each_card_not_only_last_card():
    markup = """
    <h3>Santos FC vs. SE Palmeiras</h3><div>SAN 30¢</div><div>DRAW 28¢</div><div>PAL 44¢</div>
    <h3>SC Corinthians Paulista vs. Mirassol FC</h3><div>COR1 55¢</div><div>DRAW 27¢</div><div>MIR 20¢</div>
    """
    assert [game["title"] for game in extract_games(markup)] == [
        "Santos FC vs. SE Palmeiras",
        "SC Corinthians Paulista vs. Mirassol FC",
    ]


def test_extract_games_removes_neighbouring_card_data_from_title():
    markup = """
    <div>CRU 59¢ DRAW 23¢ BAH 22¢ EC Vitória vs. Fluminense FC 23:00 $2.63 Vol
    Vitória 10-8-14 Fluminense 15-9-9 VIT 36¢ DRAW 32¢ FLU 45¢</div>
    """
    assert extract_games(markup)[0]["title"] == "EC Vitória vs. Fluminense FC"
