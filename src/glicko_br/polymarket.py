"""Coleta pública e estática das odds 1X2 do Brasileirão no Polymarket."""
from __future__ import annotations

import argparse
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


BRA_GAMES_URL = "https://polymarket.com/es/sports/bra/games"
GAMMA_EVENTS_URL = "https://gamma-api.polymarket.com/events?slug={}"
GAMMA_MARKETS_URL = "https://gamma-api.polymarket.com/markets?active=true&closed=false&event_id={}&limit=100"
GAME_SLUG_PATTERN = re.compile(r"/sports/bra/(bra-[a-z0-9-]+)", re.IGNORECASE)
GAME_PATTERN = re.compile(
    r"(?P<title>[A-ZÀ-ÿ][^\n]{2,140}?\s+vs\.?\s+[A-ZÀ-ÿ][^\n]{2,140}?)\s+(?=[A-Z]{2,6}\d?\s*\d{1,2}\s*(?:¢|centavos?))(?P<body>.{0,1800}?)(?=(?:[A-ZÀ-ÿ][^\n]{2,140}?\s+vs\.?\s+[A-ZÀ-ÿ])|\Z)",
    re.IGNORECASE | re.DOTALL,
)
PRICE_PATTERN = re.compile(r"\b([A-Z]{2,6}\d?)\s*(\d{1,2})\s*(?:¢|centavos?)", re.IGNORECASE)


def clean_title(value: str) -> str:
    """Remove preços/estatísticas que precedem ou sucedem o título no card."""
    value = re.sub(r"^.*\b[A-Z]{2,6}\d?\s+\d{1,2}\s*(?:¢|centavos?)\s+", "", value, flags=re.IGNORECASE)
    value = re.split(r"\s+\d{1,2}:\d{2}\b", value, maxsplit=1)[0]
    return " ".join(value.split())


def page_text(markup: str) -> str:
    """Reduz o HTML renderizado a texto, preservando as sequências dos cards."""
    text = re.sub(r"<script[^>]*>.*?</script>|<style[^>]*>.*?</style>", " ", markup, flags=re.IGNORECASE | re.DOTALL)
    marker = "\ue000"
    text = re.sub(r"</?(?:h[1-6]|article)[^>]*>", marker, text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", html.unescape(text)).replace("\xa0", " ")
    return text.replace(marker, "\n")


def extract_games(markup: str) -> list[dict[str, object]]:
    """Extrai os três contratos de moneyline dos cards renderizados da página."""
    games: list[dict[str, object]] = []
    seen: set[str] = set()
    for match in GAME_PATTERN.finditer(page_text(markup)):
        title = clean_title(match.group("title"))
        prices = PRICE_PATTERN.findall(match.group("body"))
        draw_index = next((index for index, (name, _) in enumerate(prices) if name.upper() == "DRAW"), None)
        if not re.search(r"\s+vs\.?\s+", title, re.IGNORECASE) or draw_index is None or draw_index == 0 or draw_index + 1 >= len(prices) or title in seen:
            continue
        home_code, home = prices[draw_index - 1]
        _, draw = prices[draw_index]
        away_code, away = prices[draw_index + 1]
        if len({home_code.upper(), "DRAW", away_code.upper()}) != 3:
            continue
        games.append({
            "title": title,
            "home": int(home) / 100,
            "draw": int(draw) / 100,
            "away": int(away) / 100,
            "codes": {"home": home_code, "away": away_code},
        })
        seen.add(title)
    return games


def extract_game_slugs(markup: str) -> list[str]:
    """Obtém os links dos jogos: são a fronteira estável entre os cards."""
    return list(dict.fromkeys(match.lower() for match in GAME_SLUG_PATTERN.findall(html.unescape(markup))))


def parsed_list(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return []
    return []


def event_odds(event: dict[str, object], markets: list[dict[str, object]], slug: str) -> dict[str, object] | None:
    """Lê somente os três contratos de moneyline do evento identificado."""
    prefix = f"{slug}-"
    legs: dict[str, tuple[str, float]] = {}
    for market in markets:
        market_slug = str(market.get("slug") or "").lower()
        suffix = market_slug.removeprefix(prefix)
        if not market_slug.startswith(prefix) or not re.fullmatch(r"[a-z0-9]+", suffix):
            continue
        prices = parsed_list(market.get("outcomePrices"))
        try:
            price = float(prices[0])
        except (IndexError, TypeError, ValueError):
            continue
        legs[suffix] = (str(market.get("title") or suffix).upper(), price)
    draw_key = next((key for key in legs if key == "draw"), None)
    sides = [(key, value) for key, value in legs.items() if key != draw_key]
    if draw_key is None or len(sides) != 2:
        return None
    (_, (home_code, home)), (_, (away_code, away)) = sides
    title = str(event.get("title") or "").strip()
    if not re.search(r"\s+vs\.?\s+", title, re.IGNORECASE):
        return None
    return {
        "title": title,
        "home": home,
        "draw": legs[draw_key][1],
        "away": away,
        "codes": {"home": home_code, "away": away_code},
        "scheduled_at": event.get("gameStartTime") or event.get("startDate"),
    }


def request_json(url: str, opener) -> object:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; FUTRanking/1.0)", "Accept": "application/json"})
    with opener(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_brazil_serie_a_odds(opener=urlopen) -> dict[str, object]:
    request = Request(BRA_GAMES_URL, headers={"User-Agent": "Mozilla/5.0 (compatible; FUTRanking/1.0)", "Accept-Language": "es,en;q=0.8"})
    with opener(request, timeout=30) as response:
        markup = response.read().decode("utf-8", "ignore")
    games = []
    for slug in extract_game_slugs(markup):
        try:
            response = request_json(GAMMA_EVENTS_URL.format(slug), opener)
            event = response[0] if isinstance(response, list) and response else response
            if not isinstance(event, dict):
                continue
            markets = event.get("markets") or request_json(GAMMA_MARKETS_URL.format(event.get("id")), opener)
            game = event_odds(event, markets, slug) if isinstance(markets, list) else None
        except Exception:
            continue
        if game:
            games.append(game)
    games = sorted(games, key=lambda game: str(game.get("scheduled_at") or "")) or extract_games(markup)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_url": BRA_GAMES_URL,
        "games": games,
        "error": None if games else "A página foi lida, mas nenhum card 1X2 foi reconhecido.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        payload = fetch_brazil_serie_a_odds()
    except Exception as exc:  # A indisponibilidade da fonte não interrompe o ranking.
        payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "source_url": BRA_GAMES_URL, "games": [], "error": f"Falha ao consultar a fonte: {exc}"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[polymarket] Série A: {len(payload['games'])} jogos 1X2 exportados.")
    if payload["error"]:
        print(f"[polymarket] {payload['error']}")


if __name__ == "__main__":
    main()
