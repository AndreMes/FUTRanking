"""Coleta estática das odds 1X2 da Série A pela API oficial do Polymarket."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


GAMMA_SPORTS_URL = "https://gamma-api.polymarket.com/sports"
GAMMA_EVENTS_KEYSET_URL = "https://gamma-api.polymarket.com/events/keyset"
MAX_EVENT_PAGES = 5


def parsed_list(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []
    return []


def serie_a_metadata(sports: object) -> dict[str, object] | None:
    """Encontra a liga por seus metadados oficiais, não pela rota visual do site."""
    if not isinstance(sports, list):
        return None
    entries = [entry for entry in sports if isinstance(entry, dict)]
    exact = next((entry for entry in entries if str(entry.get("sport") or "").lower() == "bra"), None)
    if exact:
        return exact
    # O identificador pode mudar; nome e fonte de resolução são estáveis no catálogo.
    def score(entry: dict[str, object]) -> int:
        text = " ".join(str(entry.get(field) or "") for field in ("sport", "name", "resolution")).lower()
        return int("brasil" in text or "brazil" in text) + int("serie a" in text or "brasileirao" in text or "brasileiro" in text)
    return max(entries, key=score, default=None) if any(score(entry) >= 2 for entry in entries) else None


def series_ids_for_sport(sports: object) -> list[str]:
    """Obtém os identificadores de série publicados no catálogo oficial."""
    item = serie_a_metadata(sports)
    if item is None:
        return []
    raw = item.get("series")
    values = raw if isinstance(raw, list) else str(raw or "").split(",")
    return [str(value).strip() for value in values if str(value).strip().isdigit()]


def keyset_url(filters: list[tuple[str, str]], cursor: str | None = None) -> str:
    """Cria uma consulta paginada, sem offset, filtrada pela série brasileira."""
    query: list[tuple[str, str]] = [
        ("limit", "100"),
        ("closed", "false"),
        ("order", "eventStartTime"),
        ("ascending", "true"),
    ]
    query.extend(filters)
    if cursor:
        query.append(("after_cursor", cursor))
    return f"{GAMMA_EVENTS_KEYSET_URL}?{urlencode(query)}"


def event_odds(event: dict[str, object], markets: list[dict[str, object]], slug: str | None = None) -> dict[str, object] | None:
    """Reconstrói o 1X2 pelos três contratos binários de um evento da API."""
    event_slug = str(slug or event.get("slug") or "").lower()
    if not event_slug:
        return None
    prefix = f"{event_slug}-"
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
        if not 0 < price < 1:
            continue
        legs[suffix] = (str(market.get("title") or suffix).upper(), price)
    draw_key = next((key for key in legs if key == "draw"), None)
    sides = [(key, value) for key, value in legs.items() if key != draw_key]
    title = str(event.get("title") or "").strip()
    if draw_key is None or len(sides) != 2 or not re.search(r"\s+vs\.?\s+", title, re.IGNORECASE):
        return None
    (_, (home_code, home)), (_, (away_code, away)) = sides
    return {
        "title": title,
        "home": home,
        "draw": legs[draw_key][1],
        "away": away,
        "codes": {"home": home_code, "away": away_code},
        "scheduled_at": event.get("gameStartTime") or event.get("eventStartTime") or event.get("startDate"),
        "event_slug": event_slug,
    }


def games_from_events(events: object) -> list[dict[str, object]]:
    """Extrai um registro por partida; os mercados já vêm aninhados nos eventos."""
    if not isinstance(events, list):
        return []
    games: list[dict[str, object]] = []
    seen: set[str] = set()
    for event in events:
        if not isinstance(event, dict):
            continue
        game = event_odds(event, [market for market in event.get("markets") or [] if isinstance(market, dict)])
        if not game or game["event_slug"] in seen:
            continue
        seen.add(game["event_slug"])
        games.append(game)
    return sorted(games, key=lambda game: str(game.get("scheduled_at") or ""))


def request_json(url: str, opener) -> object:
    request = Request(url, headers={"User-Agent": "FUTRanking/1.0", "Accept": "application/json"})
    with opener(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_event_pages(filters: list[tuple[str, str]], opener) -> tuple[list[object], int]:
    """Segue somente os cursors devolvidos pela API e retorna páginas realmente lidas."""
    events: list[object] = []
    cursor: str | None = None
    pages = 0
    for _ in range(MAX_EVENT_PAGES):
        page = request_json(keyset_url(filters, cursor), opener)
        pages += 1
        if not isinstance(page, dict):
            break
        batch = page.get("events")
        if not isinstance(batch, list) or not batch:
            break
        events.extend(batch)
        cursor = page.get("next_cursor") if isinstance(page.get("next_cursor"), str) else None
        if not cursor:
            break
    return events, pages


def fetch_brazil_serie_a_odds(opener=urlopen) -> dict[str, object]:
    """Consulta somente a API: catálogo de esportes e eventos keyset da Série A."""
    sports = request_json(GAMMA_SPORTS_URL, opener)
    metadata = serie_a_metadata(sports)
    series_ids = series_ids_for_sport(sports)
    if not series_ids:
        raise RuntimeError("o catálogo não identificou a Série A brasileira por série")
    events, pages = fetch_event_pages([("series_id", identifier) for identifier in series_ids], opener)
    games = games_from_events(events)
    # A documentação expõe a tag primária da liga. Se a série ainda não tiver
    # eventos abertos, tentamos a própria tag sem misturar campeonatos.
    fallback_used = False
    if not games and metadata and str(metadata.get("primaryTagId") or "").isdigit():
        events, tag_pages = fetch_event_pages([("tag_id", str(metadata["primaryTagId"]))], opener)
        pages += tag_pages
        games = games_from_events(events)
        fallback_used = True
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_url": GAMMA_EVENTS_KEYSET_URL,
        "source": "Polymarket Gamma API · events/keyset",
        "games": games,
        "diagnostics": {
            "sport": metadata.get("sport") if metadata else None,
            "series_ids": series_ids,
            "primary_tag_id": metadata.get("primaryTagId") if metadata else None,
            "pages": pages,
            "events": len(events),
            "tag_fallback": fallback_used,
        },
        "error": None if games else "A API respondeu, mas não retornou mercados 1X2 ativos para a Série A.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        payload = fetch_brazil_serie_a_odds()
    except Exception as exc:  # A indisponibilidade da fonte não interrompe o ranking.
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_url": GAMMA_EVENTS_KEYSET_URL,
            "source": "Polymarket Gamma API · events/keyset",
            "games": [],
            "error": f"Falha ao consultar a API: {exc}",
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[polymarket][api] Série A: {len(payload['games'])} jogos 1X2 exportados.")
    if payload["error"]:
        print(f"[polymarket][api] {payload['error']}")


if __name__ == "__main__":
    main()
