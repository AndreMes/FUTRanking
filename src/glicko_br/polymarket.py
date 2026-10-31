"""Coleta estática das odds 1X2 da Série A pela API oficial do Polymarket."""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.error import HTTPError
from urllib.request import Request, urlopen


GAMMA_SPORTS_URL = "https://gamma-api.polymarket.com/sports"
GAMMA_EVENTS_KEYSET_URL = "https://gamma-api.polymarket.com/events/keyset"
CLOB_PRICE_URL = "https://clob.polymarket.com/price"
MAX_EVENT_PAGES = 5
HALFTIME_PATTERN = re.compile(r"\b(?:half[ -]?time|half[ -]?time result|first half|second half|1st half|2nd half|primeiro tempo|segundo tempo|intervalo)\b", re.IGNORECASE)
DIVISIONS = {
    "serie_a": {"label": "Série A", "codes": {"bra"}, "pattern": re.compile(r"(?:serie|série)\s*a\b|brasileir[aã]o")},
    "serie_b": {"label": "Série B", "codes": {"brb", "bra2"}, "pattern": re.compile(r"(?:serie|série)\s*b\b|brasileir[aã]o.*\bb\b")},
}


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


def yes_token_id(market: dict[str, object]) -> str | None:
    """Retorna o token do resultado ``Yes`` do contrato binário.

    ``outcomePrices`` do Gamma é um snapshot/último preço e não é, por si só,
    a cotação de compra mostrada no livro. A ordem de ``outcomes`` e
    ``clobTokenIds`` é paralela, portanto esta função evita supor que o índice
    zero sempre é o contrato que queremos precificar.
    """
    outcomes = parsed_list(market.get("outcomes"))
    tokens = parsed_list(market.get("clobTokenIds"))
    for index, outcome in enumerate(outcomes):
        if str(outcome).strip().casefold() in {"yes", "sim"} and index < len(tokens):
            token = str(tokens[index]).strip()
            return token or None
    return None


def gamma_yes_price(market: dict[str, object]) -> float | None:
    """Fallback determinístico usado somente nos testes e em dados legados."""
    outcomes = parsed_list(market.get("outcomes"))
    prices = parsed_list(market.get("outcomePrices"))
    yes_index = next(
        (index for index, outcome in enumerate(outcomes) if str(outcome).strip().casefold() in {"yes", "sim"}),
        0 if not outcomes else None,
    )
    if yes_index is None:
        return None
    try:
        price = float(prices[yes_index])
    except (IndexError, TypeError, ValueError):
        return None
    return price if 0 < price < 1 else None


def normalized_text(value: object) -> str:
    """Normaliza nomes e códigos sem transformar ordem de mercados em identidade."""
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def split_event_teams(title: str) -> tuple[str, str] | None:
    parts = re.split(r"\s+vs\.?\s+", title, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) != 2 or not all(part.strip() for part in parts):
        return None
    return parts[0].strip(), parts[1].strip()


def team_code_candidates(team: str) -> set[str]:
    """Códigos curtos comuns em mercados esportivos, apenas como último recurso."""
    words = [word for word in normalized_text(team).split() if word not in {"fc", "ec", "sc", "ac", "clube", "futebol"}]
    if not words:
        return set()
    compact = "".join(words)
    candidates = {compact[:3], "".join(word[0] for word in words)}
    if len(words) > 1:
        candidates.add(words[0][:2] + "".join(word[0] for word in words[1:]))
    return {candidate for candidate in candidates if len(candidate) >= 2}


def market_matches_team(market: dict[str, object], suffix: str, team: str) -> bool:
    """Exige evidência de que o contrato pertence ao mandante ou visitante."""
    text = normalized_text(" ".join(str(market.get(field) or "") for field in ("title", "question", "groupItemTitle", "description")))
    team_text = normalized_text(team)
    if len(team_text) >= 4 and team_text in text:
        return True
    words = [word for word in team_text.split() if len(word) >= 4 and word not in {"clube", "futebol"}]
    if words and all(word in text.split() for word in words):
        return True
    code = re.sub(r"\d+$", "", normalized_text(suffix).replace(" ", ""))
    return code in team_code_candidates(team)


def serie_metadata(sports: object, division: str) -> dict[str, object] | None:
    """Encontra cada divisão por metadados da API, sem depender da rota visual."""
    if not isinstance(sports, list):
        return None
    config = DIVISIONS[division]
    entries = [entry for entry in sports if isinstance(entry, dict)]
    exact = next((entry for entry in entries if str(entry.get("sport") or "").lower() in config["codes"]), None)
    if exact:
        return exact
    # O identificador pode mudar; nome e fonte de resolução são estáveis no catálogo.
    def score(entry: dict[str, object]) -> int:
        text = " ".join(str(entry.get(field) or "") for field in ("sport", "name", "resolution")).lower()
        return int("brasil" in text or "brazil" in text) + int(bool(config["pattern"].search(text)))
    return max(entries, key=score, default=None) if any(score(entry) >= 2 for entry in entries) else None


def serie_a_metadata(sports: object) -> dict[str, object] | None:
    """Compatibilidade para os consumidores da Série A."""
    return serie_metadata(sports, "serie_a")


def series_ids_for_sport(sports: object, division: str = "serie_a") -> list[str]:
    """Obtém os identificadores de série publicados no catálogo oficial."""
    item = serie_metadata(sports, division)
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
    ]
    query.extend(filters)
    if cursor:
        query.append(("after_cursor", cursor))
    return f"{GAMMA_EVENTS_KEYSET_URL}?{urlencode(query)}"


def event_odds(
    event: dict[str, object],
    markets: list[dict[str, object]],
    slug: str | None = None,
    price_for_market=None,
) -> dict[str, object] | None:
    """Reconstrói o 1X2 pelos três contratos binários de um evento da API."""
    event_slug = str(slug or event.get("slug") or "").lower()
    if not event_slug:
        return None
    title = str(event.get("title") or "").strip()
    if HALFTIME_PATTERN.search(title):
        return None
    teams = split_event_teams(title)
    if teams is None:
        return None
    home_team, away_team = teams
    prefix = f"{event_slug}-"
    legs: dict[str, tuple[str, float]] = {}
    for market in markets:
        market_text = " ".join(str(market.get(field) or "") for field in ("title", "question", "groupItemTitle", "description", "slug"))
        market_type = str(market.get("sportsMarketType") or market.get("marketType") or "").lower()
        # Quando a API identifica o tipo, aceitamos somente a moneyline 1X2.
        if market_type and not any(token in market_type for token in ("moneyline", "1x2", "match winner", "game winner")):
            continue
        if HALFTIME_PATTERN.search(market_text):
            continue
        market_slug = str(market.get("slug") or "").lower()
        suffix = market_slug.removeprefix(prefix)
        if not market_slug.startswith(prefix) or not re.fullmatch(r"[a-z0-9]+", suffix):
            continue
        price = price_for_market(market) if price_for_market else gamma_yes_price(market)
        if price is None:
            continue
        code = str(market.get("title") or suffix).upper()
        if suffix == "draw":
            key = "draw"
        elif market_matches_team(market, suffix, home_team):
            key = "home"
        elif market_matches_team(market, suffix, away_team):
            key = "away"
        else:
            # É preferível omitir um jogo a comparar uma equipa ao contrato errado.
            continue
        if key in legs:
            return None
        legs[key] = (code, price)
    if set(legs) != {"home", "draw", "away"}:
        return None
    home_code, home = legs["home"]
    away_code, away = legs["away"]
    # Um 1X2 de partida inteira tem três probabilidades competitivas. Um preço
    # praticamente resolvido sinaliza mercado de período/estado indevidamente aninhado.
    if max(home, legs["draw"][1], away) >= 0.95:
        return None
    return {
        "title": title,
        "home": home,
        "draw": legs["draw"][1],
        "away": away,
        "codes": {"home": home_code, "away": away_code},
        "scheduled_at": event.get("gameStartTime") or event.get("eventStartTime") or event.get("startDate"),
        "event_slug": event_slug,
    }


def games_from_events(events: object, price_for_market=None) -> list[dict[str, object]]:
    """Extrai um registro por partida; os mercados já vêm aninhados nos eventos."""
    if not isinstance(events, list):
        return []
    games: list[dict[str, object]] = []
    seen: set[str] = set()
    for event in events:
        if not isinstance(event, dict):
            continue
        game = event_odds(
            event,
            [market for market in event.get("markets") or [] if isinstance(market, dict)],
            price_for_market=price_for_market,
        )
        if not game or game["event_slug"] in seen:
            continue
        seen.add(game["event_slug"])
        games.append(game)
    return sorted(games, key=lambda game: str(game.get("scheduled_at") or ""))


def request_json(url: str, opener) -> object:
    request = Request(url, headers={"User-Agent": "FUTRanking/1.0", "Accept": "application/json"})
    try:
        with opener(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"HTTP {error.code}: {detail}") from error


def clob_yes_buy_price(market: dict[str, object], opener) -> float | None:
    """Lê a melhor oferta de compra atual do token Yes no CLOB oficial.

    É a mesma semântica do botão ``Buy`` da interface pública. Não usamos o
    snapshot ``outcomePrices`` do Gamma para gerar alfa ou Kelly.
    """
    token_id = yes_token_id(market)
    if not token_id:
        return None
    try:
        payload = request_json(f"{CLOB_PRICE_URL}?{urlencode({'token_id': token_id, 'side': 'BUY'})}", opener)
        price = float(payload.get("price")) if isinstance(payload, dict) else None
    except (RuntimeError, TypeError, ValueError):
        return None
    return price if price is not None and 0 < price < 1 else None


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


def fetch_division_odds(sports: object, division: str, opener) -> dict[str, object]:
    """Coleta uma divisão brasileira e conserva diagnóstico por fonte."""
    metadata = serie_metadata(sports, division)
    series_ids = series_ids_for_sport(sports, division)
    label = DIVISIONS[division]["label"]
    if not series_ids:
        raise RuntimeError(f"o catálogo não identificou {label} brasileira por série")
    events, pages = fetch_event_pages([("series_id", identifier) for identifier in series_ids], opener)
    games = games_from_events(events, price_for_market=lambda market: clob_yes_buy_price(market, opener))
    # A documentação expõe a tag primária da liga. Se a série ainda não tiver
    # eventos abertos, tentamos a própria tag sem misturar campeonatos.
    fallback_used = False
    if not games and metadata and str(metadata.get("primaryTagId") or "").isdigit():
        events, tag_pages = fetch_event_pages([("tag_id", str(metadata["primaryTagId"]))], opener)
        pages += tag_pages
        games = games_from_events(events, price_for_market=lambda market: clob_yes_buy_price(market, opener))
        fallback_used = True
    return {
        "label": label,
        "games": games,
        "diagnostics": {
            "sport": metadata.get("sport") if metadata else None,
            "series_ids": series_ids,
            "primary_tag_id": metadata.get("primaryTagId") if metadata else None,
            "pages": pages,
            "events": len(events),
            "tag_fallback": fallback_used,
            "price_source": "CLOB API · melhor preço de compra do token Yes",
        },
        "error": None if games else f"A API respondeu, mas não retornou mercados 1X2 ativos para a {label}.",
    }


def fetch_brazil_serie_a_odds(opener=urlopen) -> dict[str, object]:
    """Consulta A e B pela API e publica uma coleção independente por divisão."""
    sports = request_json(GAMMA_SPORTS_URL, opener)
    competitions: dict[str, dict[str, object]] = {}
    for division in DIVISIONS:
        try:
            competitions[division] = fetch_division_odds(sports, division, opener)
        except Exception as exc:
            competitions[division] = {"label": DIVISIONS[division]["label"], "games": [], "diagnostics": {}, "error": f"Falha ao consultar a API: {exc}"}
    serie_a = competitions["serie_a"]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_url": GAMMA_EVENTS_KEYSET_URL,
        "source": "Polymarket Gamma API + CLOB API · preços Buy do token Yes",
        "competitions": competitions,
        # Compatibilidade com a página já publicada até ela ler competitions.
        "games": serie_a["games"],
        "diagnostics": serie_a["diagnostics"],
        "error": serie_a["error"],
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
            "source": "Polymarket Gamma API + CLOB API · preços Buy do token Yes",
            "games": [],
            "error": f"Falha ao consultar a API: {exc}",
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    for division, competition in payload.get("competitions", {}).items():
        print(f"[polymarket][api] {competition['label']}: {len(competition['games'])} jogos 1X2 exportados.")
        if competition["error"]:
            print(f"[polymarket][api] {division}: {competition['error']}")


if __name__ == "__main__":
    main()
