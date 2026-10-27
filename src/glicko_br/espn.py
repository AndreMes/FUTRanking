"""Importador de placares e agenda brasileiros a partir da ESPN."""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .competitions import ESPN_COMPETITIONS
from .database import replace_fixtures, store_match, store_source_payload

BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer"
LEAGUES = {competition.espn_slug: competition.name for competition in ESPN_COMPETITIONS}


class EspnError(RuntimeError):
    pass


class EspnClient:
    def get_scoreboard(self, league: str, *, dates: str) -> tuple[dict, str]:
        query = urlencode({"dates": dates, "limit": 1000})
        request_path = f"/{league}/scoreboard?{query}"
        request = Request(f"{BASE_URL}{request_path}", headers={"Accept": "application/json"})
        try:
            with urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as error:
            raise EspnError(f"ESPN respondeu HTTP {error.code} para {request_path}") from error
        except URLError as error:
            raise EspnError(f"Não foi possível acessar a ESPN: {error.reason}") from error
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as error:
            raise EspnError("A ESPN retornou uma resposta inválida.") from error
        if not isinstance(payload.get("events"), list):
            raise EspnError(f"A ESPN não retornou a lista de eventos para {league}.")
        return payload, request_path


def _competitors(event: dict) -> tuple[dict, dict]:
    competitions = event.get("competitions") or []
    competitors = competitions[0].get("competitors") if competitions else None
    if not isinstance(competitors, list):
        raise EspnError(f"Evento ESPN {event.get('id')} sem participantes.")
    by_home_away = {competitor.get("homeAway"): competitor for competitor in competitors}
    home, away = by_home_away.get("home"), by_home_away.get("away")
    if not home or not away:
        raise EspnError(f"Evento ESPN {event.get('id')} sem mandante ou visitante.")
    return home, away


def _team(competitor: dict) -> tuple[str, str]:
    team = competitor.get("team") or {}
    name = team.get("displayName") or team.get("name")
    if not name:
        raise EspnError("Evento ESPN sem nome de clube.")
    return str(name), str(team.get("logo") or "")


def _context(event: dict) -> tuple[str, str, str]:
    week = event.get("week") or {}
    matchday = str(week.get("number") or "")
    season = event.get("season") or {}
    return matchday, str(season.get("slug") or ""), str(event.get("seasonType") or "")


def event_to_row(event: dict, competition: str) -> dict[str, str] | None:
    """Normaliza somente eventos com placar final confirmado pela fonte."""
    status = ((event.get("status") or {}).get("type") or {})
    home, away = _competitors(event)
    home_score, away_score = home.get("score"), away.get("score")
    if not status.get("completed") or home_score is None or away_score is None:
        return None
    home_name, home_crest = _team(home)
    away_name, away_crest = _team(away)
    matchday, stage, group_name = _context(event)
    return {
        "external_id": f"espn:{event['id']}",
        "played_at": str(event["date"]),
        "competition": competition,
        "matchday": matchday,
        "stage": stage,
        "group_name": group_name,
        "home_team": home_name,
        "away_team": away_name,
        "home_crest": home_crest,
        "away_crest": away_crest,
        "home_goals": str(home_score),
        "away_goals": str(away_score),
    }


def event_to_fixture(event: dict, competition: str) -> dict[str, str] | None:
    """Normaliza eventos pendentes, adiados ou em andamento sem transformar finais em fixtures."""
    if event_to_row(event, competition) is not None:
        return None
    home, away = _competitors(event)
    home_name, home_crest = _team(home)
    away_name, away_crest = _team(away)
    matchday, stage, group_name = _context(event)
    status = ((event.get("status") or {}).get("type") or {})
    return {
        "external_id": f"espn:{event['id']}",
        "scheduled_at": str(event["date"]),
        "competition": competition,
        "status": str(status.get("name") or status.get("description") or "STATUS_SCHEDULED"),
        "matchday": matchday,
        "stage": stage,
        "group_name": group_name,
        "home_team": home_name,
        "away_team": away_name,
        "home_crest": home_crest,
        "away_crest": away_crest,
    }


def sync_period(database, period: str, *, leagues: dict[str, str] = LEAGUES) -> int:
    """Importa uma data ou um ano. É idempotente pelo ID de evento da ESPN."""
    client = EspnClient()
    imported = 0
    for league, competition in leagues.items():
        response = client.get_scoreboard(league, dates=period)
        # Aceita também o formato anterior de três campos durante a transição.
        payload, request_path = response if len(response) == 2 else (response[0], response[-1])
        audit = json.dumps(
            {"league": league, "period": period, "event_count": len(payload["events"])},
            separators=(",", ":"),
        )
        store_source_payload(database, "espn", request_path, audit)
        fixtures = []
        for event in payload["events"]:
            row = event_to_row(event, competition)
            if row is not None:
                store_match(database, row)
                imported += 1
            else:
                fixture = event_to_fixture(event, competition)
                if fixture is not None:
                    fixtures.append(fixture)
        replace_fixtures(database, fixtures, replace=False)
    return imported
