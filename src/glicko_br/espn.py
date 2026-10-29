"""Importador de placares e agenda brasileiros a partir da ESPN."""
from __future__ import annotations

import json
from time import monotonic, sleep
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .competitions import ESPN_COMPETITIONS
from .database import replace_fixtures, store_match, store_source_payload

BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer"
MAX_REQUEST_ATTEMPTS = 3
RETRYABLE_HTTP_STATUS = frozenset({429, 500, 502, 503, 504})
# Ritmo deliberadamente conservador para não concentrar a coleta diária no provedor.
REQUEST_INTERVAL_SECONDS = 0.35
LEAGUES = {competition.espn_slug: competition.name for competition in ESPN_COMPETITIONS}
COUNTRY_BY_LEAGUE_PREFIX = {
    "arg": "Argentina", "bol": "Bolívia", "bra": "Brasil", "chi": "Chile",
    "col": "Colômbia", "ecu": "Equador", "par": "Paraguai", "per": "Peru",
    "uru": "Uruguai", "ven": "Venezuela", "mex": "México",
}


class EspnError(RuntimeError):
    pass


class EspnClient:
    def __init__(self) -> None:
        self.team_countries: dict[str, str | None] = {}
        self.request_count = 0
        self._last_request_at: float | None = None

    def _reserve_request_slot(self) -> None:
        """Aplica um intervalo mínimo entre quaisquer chamadas à ESPN."""
        if self._last_request_at is not None:
            remaining = REQUEST_INTERVAL_SECONDS - (monotonic() - self._last_request_at)
            if remaining > 0:
                sleep(remaining)
        self._last_request_at = monotonic()
        self.request_count += 1

    def get_scoreboard(self, league: str, *, dates: str) -> tuple[dict, str]:
        query = urlencode({"dates": dates, "limit": 1000})
        request_path = f"/{league}/scoreboard?{query}"
        request = Request(f"{BASE_URL}{request_path}", headers={"Accept": "application/json", "User-Agent": "FUTRanking/1.0"})
        for attempt in range(MAX_REQUEST_ATTEMPTS):
            try:
                self._reserve_request_slot()
                with urlopen(request, timeout=30) as response:
                    raw = response.read().decode("utf-8")
                break
            except HTTPError as error:
                if error.code not in RETRYABLE_HTTP_STATUS or attempt == MAX_REQUEST_ATTEMPTS - 1:
                    raise EspnError(f"ESPN respondeu HTTP {error.code} para {request_path}") from error
            except (URLError, TimeoutError, ConnectionResetError) as error:
                if attempt == MAX_REQUEST_ATTEMPTS - 1:
                    reason = getattr(error, "reason", error)
                    raise EspnError(f"Não foi possível acessar a ESPN: {reason}") from error
            sleep(2 ** attempt)
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as error:
            raise EspnError("A ESPN retornou uma resposta inválida.") from error
        if not isinstance(payload.get("events"), list):
            raise EspnError(f"A ESPN não retornou a lista de eventos para {league}.")
        return payload, request_path

    def get_team_country(self, league: str, team_id: str) -> str | None:
        """Resolve o país pela liga nacional do perfil ESPN, uma vez por clube/processo."""
        if not team_id:
            return None
        if team_id in self.team_countries:
            return self.team_countries[team_id]
        request_path = f"/{league}/teams/{team_id}"
        try:
            request = Request(f"{BASE_URL}{request_path}", headers={"Accept": "application/json", "User-Agent": "FUTRanking/1.0"})
            self._reserve_request_slot()
            with urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
            team = payload.get("team") or {}
            default_league = team.get("defaultLeague") or {}
            abbreviation = str(default_league.get("abbreviation") or team.get("leagueAbbrev") or "")
            if abbreviation.split(".", 1)[0] not in COUNTRY_BY_LEAGUE_PREFIX:
                for link in default_league.get("links") or []:
                    href = str(link.get("href") or "")
                    if "name/" in href:
                        abbreviation = href.split("name/", 1)[1].split("/", 1)[0]
                        break
            country = COUNTRY_BY_LEAGUE_PREFIX.get(abbreviation.split(".", 1)[0])
        except (HTTPError, URLError, json.JSONDecodeError, TimeoutError):
            country = None
        self.team_countries[team_id] = country
        return country


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


def _team(competitor: dict) -> tuple[str, str, str]:
    team = competitor.get("team") or {}
    name = team.get("displayName") or team.get("name")
    if not name:
        raise EspnError("Evento ESPN sem nome de clube.")
    return str(name), str(team.get("logo") or ""), str(team.get("id") or "")


def _context(event: dict) -> tuple[str, str, str]:
    week = event.get("week") or {}
    matchday = str(week.get("number") or "")
    season = event.get("season") or {}
    return matchday, str(season.get("slug") or ""), str(event.get("seasonType") or "")


def _venue_country(event: dict) -> str:
    competitions = event.get("competitions") or []
    venue = (competitions[0].get("venue") or {}) if competitions else {}
    return str(((venue.get("address") or {}).get("country")) or "")


def event_to_row(event: dict, competition: str) -> dict[str, str] | None:
    """Normaliza somente eventos com placar final confirmado pela fonte."""
    status = ((event.get("status") or {}).get("type") or {})
    home, away = _competitors(event)
    home_score, away_score = home.get("score"), away.get("score")
    if not status.get("completed") or home_score is None or away_score is None:
        return None
    home_name, home_crest, home_id = _team(home)
    away_name, away_crest, away_id = _team(away)
    matchday, stage, group_name = _context(event)
    venue_country = _venue_country(event)
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
        "home_espn_team_id": home_id,
        "away_espn_team_id": away_id,
        "venue_country": venue_country,
        "home_goals": str(home_score),
        "away_goals": str(away_score),
    }


def event_to_fixture(event: dict, competition: str) -> dict[str, str] | None:
    """Normaliza eventos pendentes, adiados ou em andamento sem transformar finais em fixtures."""
    if event_to_row(event, competition) is not None:
        return None
    home, away = _competitors(event)
    home_name, home_crest, home_id = _team(home)
    away_name, away_crest, away_id = _team(away)
    matchday, stage, group_name = _context(event)
    venue_country = _venue_country(event)
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
        "home_espn_team_id": home_id,
        "away_espn_team_id": away_id,
        "venue_country": venue_country,
    }


def _enrich_countries(client: EspnClient, league: str, item: dict[str, str]) -> None:
    resolver = getattr(client, "get_team_country", None)
    if resolver is None:
        return
    item["home_country"] = resolver(league, item.get("home_espn_team_id", ""))
    item["away_country"] = resolver(league, item.get("away_espn_team_id", ""))


def sync_period(database, period: str, *, leagues: dict[str, str] = LEAGUES, client: EspnClient | None = None) -> int:
    """Importa uma data ou um ano. É idempotente pelo ID de evento da ESPN."""
    client = client or EspnClient()
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
                _enrich_countries(client, league, row)
                store_match(database, row)
                imported += 1
            else:
                fixture = event_to_fixture(event, competition)
                if fixture is not None:
                    _enrich_countries(client, league, fixture)
                    fixtures.append(fixture)
        replace_fixtures(database, fixtures, replace=False)
    return imported
