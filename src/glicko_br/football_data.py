"""Importador da Série A via football-data.org v4."""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .database import replace_fixtures, store_match, store_source_payload

BASE_URL = "https://api.football-data.org/v4"
BRASILEIRAO_SERIE_A = "BSA"


class FootballDataError(RuntimeError):
    pass


class FootballDataClient:
    def __init__(self, token: str | None = None) -> None:
        self.token = token or os.getenv("FOOTBALL_DATA_TOKEN")
        if not self.token:
            raise FootballDataError("Defina FOOTBALL_DATA_TOKEN como variável de ambiente antes de sincronizar.")

    def get(self, path: str, **params: object) -> tuple[dict, str, str]:
        query = urlencode({key: value for key, value in params.items() if value is not None})
        request_path = f"{path}?{query}" if query else path
        request = Request(f"{BASE_URL}{request_path}", headers={"X-Auth-Token": self.token})
        try:
            with urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as error:
            raise FootballDataError(f"football-data.org respondeu HTTP {error.code} para {request_path}") from error
        except URLError as error:
            raise FootballDataError(f"Não foi possível acessar football-data.org: {error.reason}") from error
        try:
            return json.loads(raw), raw, request_path
        except json.JSONDecodeError as error:
            raise FootballDataError("football-data.org retornou uma resposta inválida.") from error


def match_to_row(match: dict) -> dict[str, str]:
    score = match.get("score", {}).get("fullTime", {})
    home_goals, away_goals = score.get("home"), score.get("away")
    if home_goals is None or away_goals is None:
        raise FootballDataError(f"Partida {match.get('id')} sem placar final.")
    return {"external_id": f"football-data:{match['id']}", "played_at": match["utcDate"], "competition": "Série A", "matchday": str(match.get("matchday") or ""), "stage": match.get("stage") or "", "group_name": match.get("group") or "", "home_team": match["homeTeam"]["name"], "away_team": match["awayTeam"]["name"], "home_crest": match["homeTeam"].get("crest", ""), "away_crest": match["awayTeam"].get("crest", ""), "home_goals": str(home_goals), "away_goals": str(away_goals)}


def sync_season(database, season: int) -> int:
    client = FootballDataClient()
    # Uma única fotografia da temporada evita lacunas entre consultas de estados diferentes.
    data, raw, request_path = client.get(f"/competitions/{BRASILEIRAO_SERIE_A}/matches", season=season)
    if not isinstance(data.get("matches"), list) or not data["matches"]:
        raise FootballDataError(f"A fonte não retornou partidas para a temporada {season}; publicação interrompida.")
    store_source_payload(database, "football-data.org", request_path, raw)
    imported = 0
    pending = []
    for match in data["matches"]:
        score = (match.get("score") or {}).get("fullTime") or {}
        if match.get("status") == "FINISHED" and score.get("home") is not None and score.get("away") is not None:
            store_match(database, match_to_row(match))
            imported += 1
        else:
            pending.append(match)
    replace_fixtures(database, [
        {"external_id": f"football-data:{match['id']}", "scheduled_at": match["utcDate"], "competition": "Série A",
         "status": match["status"], "matchday": str(match.get("matchday") or ""), "stage": match.get("stage") or "", "group_name": match.get("group") or "", "home_team": match["homeTeam"]["name"], "away_team": match["awayTeam"]["name"],
         "home_crest": match["homeTeam"].get("crest", ""), "away_crest": match["awayTeam"].get("crest", "")}
        for match in pending
    ])
    database.commit()
    return imported

