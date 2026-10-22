"""Importador local de resultados públicos do Sofascore.

Não é uma API oficial. Por isso o conector é isolado, limita suas requisições e
armazena cada resposta para que o ranking continue auditável se o formato mudar.
"""
from __future__ import annotations

import json
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .database import COMPETITIONS, store_match, store_source_payload

BASE_URL = "https://www.sofascore.com/api/v1"
REQUEST_PAUSE_SECONDS = 1.0


class SofascoreError(RuntimeError):
    pass


def _normalise(value: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFKD", value.lower()) if not unicodedata.combining(char))


TOURNAMENT_NAMES = {
    "brasileirao serie a": "Série A", "brasileirao serie b": "Série B",
    "brasileirao serie c": "Série C", "brasileirao serie d": "Série D",
    "copa do brasil": "Copa do Brasil",
}


@dataclass(frozen=True)
class Tournament:
    id: int
    name: str
    competition: str


class SofascoreClient:
    def get(self, path: str) -> tuple[dict, str]:
        request = Request(f"{BASE_URL}{path}", headers={"Accept": "application/json", "User-Agent": "IndiceFutebolBR/0.1 (local research)"})
        try:
            with urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as error:
            raise SofascoreError(f"Sofascore respondeu HTTP {error.code} para {path}") from error
        except URLError as error:
            raise SofascoreError(f"Não foi possível acessar o Sofascore: {error.reason}") from error
        try:
            return json.loads(raw), raw
        except json.JSONDecodeError as error:
            raise SofascoreError(f"Resposta inválida do Sofascore para {path}") from error

    def tournaments(self) -> list[Tournament]:
        data, _ = self.get("/config/unique-tournaments/BR/football")
        items = list(data.get("uniqueTournaments", []))
        for group in data.get("groups", []):
            items.extend(group.get("uniqueTournaments", []))
        discovered: dict[int, Tournament] = {}
        for item in items:
            competition = TOURNAMENT_NAMES.get(_normalise(item.get("name", "")))
            if competition in COMPETITIONS:
                discovered[item["id"]] = Tournament(item["id"], item["name"], competition)
        return list(discovered.values())

    def season_id(self, tournament: Tournament, year: int) -> int:
        data, _ = self.get(f"/unique-tournament/{tournament.id}/seasons")
        year_text = str(year)
        for season in data.get("seasons", []):
            if str(season.get("year")) == year_text or year_text in str(season.get("name", "")):
                return season["id"]
        raise SofascoreError(f"Temporada {year} não encontrada para {tournament.name}.")

    def finished_events(self, tournament: Tournament, season_id: int):
        page = 0
        while True:
            path = f"/unique-tournament/{tournament.id}/season/{season_id}/events/last/{page}"
            data, raw = self.get(path)
            yield data.get("events", []), raw, path
            if not data.get("hasNextPage"):
                return
            page += 1
            time.sleep(REQUEST_PAUSE_SECONDS)


def event_to_match(event: dict, competition: str) -> dict[str, str]:
    if event.get("status", {}).get("type") != "finished":
        raise SofascoreError(f"Evento {event.get('id')} não está finalizado.")
    home_score, away_score = event.get("homeScore", {}), event.get("awayScore", {})
    home_goals, away_goals = home_score.get("current"), away_score.get("current")
    if home_goals is None or away_goals is None:
        raise SofascoreError(f"Evento {event.get('id')} sem placar final.")
    # Se a diferença aparece apenas no placar de pênaltis, o Glicko registra empate.
    decided_on_penalties = (home_goals != away_goals and home_score.get("normaltime") == away_score.get("normaltime") and home_score.get("overtime") == away_score.get("overtime"))
    if decided_on_penalties:
        home_goals = away_goals = 0
    played_at = datetime.fromtimestamp(event["startTimestamp"], tz=timezone.utc).isoformat()
    return {"external_id": f"sofascore:{event['id']}", "played_at": played_at, "competition": competition, "home_team": event["homeTeam"]["name"], "away_team": event["awayTeam"]["name"], "home_goals": str(home_goals), "away_goals": str(away_goals)}


def sync_season(database, year: int) -> int:
    client = SofascoreClient()
    tournaments = client.tournaments()
    missing = COMPETITIONS - {tournament.competition for tournament in tournaments}
    if missing:
        print("Aviso: competições não encontradas: " + ", ".join(sorted(missing)))
    imported = 0
    for tournament in tournaments:
        season = client.season_id(tournament, year)
        for events, raw, request_path in client.finished_events(tournament, season):
            store_source_payload(database, "sofascore", request_path, raw)
            for event in events:
                if event.get("status", {}).get("type") == "finished":
                    store_match(database, event_to_match(event, tournament.competition))
                    imported += 1
    database.commit()
    return imported
