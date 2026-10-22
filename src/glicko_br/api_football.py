"""Adaptador mínimo para resultados finais da API-Football v3."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .database import COMPETITIONS, store_match, store_source_payload

BASE_URL = "https://v3.football.api-sports.io"
FINISHED_STATUSES = "FT-AET-PEN"
VENDOR_NAMES = {"Serie A": "Série A", "Serie B": "Série B", "Serie C": "Série C", "Serie D": "Série D", "Copa do Brasil": "Copa do Brasil"}


class ApiFootballError(RuntimeError):
    pass


@dataclass(frozen=True)
class League:
    id: int
    name: str
    canonical_name: str


class ApiFootballClient:
    def __init__(self, key: str | None = None) -> None:
        self.key = key or os.getenv("API_FOOTBALL_KEY")
        if not self.key:
            raise ApiFootballError("Defina API_FOOTBALL_KEY como variável de ambiente antes de sincronizar.")

    def get(self, path: str, **params: object) -> tuple[dict, str, str]:
        query = urlencode({key: value for key, value in params.items() if value is not None})
        request_path = f"{path}?{query}" if query else path
        request = Request(f"{BASE_URL}{request_path}", headers={"x-apisports-key": self.key})
        try:
            with urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as error:
            raise ApiFootballError(f"API-Football respondeu HTTP {error.code} para {request_path}") from error
        except URLError as error:
            raise ApiFootballError(f"Não foi possível acessar a API-Football: {error.reason}") from error
        data = json.loads(raw)
        if data.get("errors"):
            raise ApiFootballError(f"Erro retornado pela API-Football: {data['errors']}")
        return data, raw, request_path

    def leagues_for_season(self, season: int) -> list[League]:
        data, _, _ = self.get("/leagues", country="Brazil", season=season)
        return [League(item["league"]["id"], item["league"]["name"], VENDOR_NAMES[item["league"]["name"]]) for item in data.get("response", []) if item["league"]["name"] in VENDOR_NAMES]

    def completed_fixtures(self, league: League, season: int):
        page = 1
        while True:
            data, raw, request_path = self.get("/fixtures", league=league.id, season=season, status=FINISHED_STATUSES, page=page)
            yield data.get("response", []), raw, request_path
            if page >= int(data.get("paging", {}).get("total", 1)):
                return
            page += 1


def fixture_to_match(fixture: dict, competition: str) -> dict[str, str]:
    """Normaliza placares; pênaltis permanecem empate no Glicko."""
    final = fixture.get("goals", {})
    home_goals, away_goals = final.get("home"), final.get("away")
    if home_goals is None or away_goals is None:
        raise ApiFootballError(f"Partida {fixture['fixture']['id']} sem placar final.")
    penalties = fixture.get("score", {}).get("penalty", {})
    if penalties.get("home") is not None or penalties.get("away") is not None:
        home_goals = away_goals = 0
    return {"external_id": f"api-football:{fixture['fixture']['id']}", "played_at": fixture["fixture"]["date"], "competition": competition, "home_team": fixture["teams"]["home"]["name"], "away_team": fixture["teams"]["away"]["name"], "home_goals": str(home_goals), "away_goals": str(away_goals)}


def sync_season(database, season: int) -> int:
    client = ApiFootballClient()
    leagues = client.leagues_for_season(season)
    missing = COMPETITIONS - {league.canonical_name for league in leagues}
    if missing:
        print("Aviso: competições ainda não encontradas nesta temporada: " + ", ".join(sorted(missing)))
    imported = 0
    for league in leagues:
        for fixtures, raw, request_path in client.completed_fixtures(league, season):
            store_source_payload(database, "api-football", request_path, raw)
            for fixture in fixtures:
                store_match(database, fixture_to_match(fixture, league.canonical_name))
                imported += 1
    database.commit()
    return imported
