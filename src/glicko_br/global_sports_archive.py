"""Coletor conservador de resultados do Global Sports Archive.

O GSA complementa a ESPN, mantém as Séries C/D e cobre os estaduais. As
páginas de competição são HTML público, servido já com confrontos e placares,
sem navegador ou endpoints privados.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from html import unescape
import json
import re
from time import monotonic, sleep
from unicodedata import normalize
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .database import register_club_alias, store_match, store_source_payload

BASE_URL = "https://globalsportsarchive.com"
REQUEST_INTERVAL_SECONDS = 1.0
MAX_REQUEST_ATTEMPTS = 3
RETRYABLE_HTTP_STATUS = frozenset({429, 500, 502, 503, 504})
HISTORY_START_YEAR = 2016


@dataclass(frozen=True)
class GsaCompetition:
    name: str
    slug: str
    seed_url: str


COMPETITIONS = (
    GsaCompetition("Série C", "serie-c", f"{BASE_URL}/en/soccer/competition/serie-c-2016/11224"),
    GsaCompetition("Série D", "serie-d", f"{BASE_URL}/en/soccer/competition/serie-d-2016/11777"),
    GsaCompetition("Campeonato Paulista", "campeonato-paulista", f"{BASE_URL}/en/soccer/competition/paulistao-casas-bahia-2026/78189"),
    GsaCompetition("Paulista A2", "paulista-a2", f"{BASE_URL}/en/soccer/competition/paulistao-a2-rivalo-2026/78190"),
    GsaCompetition("Campeonato Carioca", "campeonato-carioca", f"{BASE_URL}/en/soccer/competition/campeonato-carioca-superbet-2026/78042"),
    GsaCompetition("Campeonato Mineiro", "campeonato-mineiro", f"{BASE_URL}/en/soccer/competition/campeonato-mineiro-sicoob-modulo-i-2026/78224"),
    GsaCompetition("Campeonato Gaúcho", "campeonato-gaucho", f"{BASE_URL}/en/soccer/competition/gauchao-superbet-2026/78221"),
    GsaCompetition("Campeonato Paranaense", "campeonato-paranaense", f"{BASE_URL}/en/soccer/competition/campeonato-paranaense-serie-ouro-2026/77422"),
    GsaCompetition("Campeonato Baiano", "campeonato-baiano", f"{BASE_URL}/en/soccer/competition/baianao-serie-a-2027/81914"),
    GsaCompetition("Campeonato Pernambucano", "campeonato-pernambucano", f"{BASE_URL}/en/soccer/competition/campeonato-pernambucano-a1-2026/78215"),
    GsaCompetition("Campeonato Cearense", "campeonato-cearense", f"{BASE_URL}/en/soccer/competition/campeonato-cearense-superbet-serie-a-2026/78058"),
    GsaCompetition("Campeonato Goiano", "campeonato-goiano", f"{BASE_URL}/en/soccer/competition/goianao-novomundo-2026/78214"),
    GsaCompetition("Campeonato Catarinense", "campeonato-catarinense", f"{BASE_URL}/en/soccer/competition/catarinense-fort-atacadista-2026/78219"),
)
BY_NAME = {competition.name: competition for competition in COMPETITIONS}
STATE_COMPETITION_NAMES = tuple(competition.name for competition in COMPETITIONS if competition.name not in {"Série C", "Série D"})


class GlobalSportsArchiveError(RuntimeError):
    pass


class GlobalSportsArchiveClient:
    def __init__(self) -> None:
        self.request_count = 0
        self._last_request_at: float | None = None
        self._cache: dict[str, str] = {}

    def _wait(self) -> None:
        if self._last_request_at is not None:
            remaining = REQUEST_INTERVAL_SECONDS - (monotonic() - self._last_request_at)
            if remaining > 0:
                sleep(remaining)

    def _request(self, request: Request, error_context: str) -> str:
        self._wait()
        for attempt in range(MAX_REQUEST_ATTEMPTS):
            try:
                self._last_request_at = monotonic()
                self.request_count += 1
                with urlopen(request, timeout=30) as response:
                    return response.read().decode("utf-8")
            except HTTPError as error:
                if error.code not in RETRYABLE_HTTP_STATUS or attempt == MAX_REQUEST_ATTEMPTS - 1:
                    raise GlobalSportsArchiveError(
                        f"Global Sports Archive respondeu HTTP {error.code} {error_context}."
                    ) from error
            except (URLError, TimeoutError, ConnectionResetError) as error:
                if attempt == MAX_REQUEST_ATTEMPTS - 1:
                    raise GlobalSportsArchiveError(
                        f"Não foi possível acessar o Global Sports Archive: {getattr(error, 'reason', error)}"
                    ) from error
            sleep(2 ** attempt)
        raise AssertionError("tentativas GSA esgotadas sem erro")

    def get(self, url: str) -> str:
        if url not in self._cache:
            request = Request(url, headers={
                "Accept": "text/html",
                "User-Agent": "FUTRanking/1.0 (+https://andremes.github.io/FUTRanking/)",
            })
            self._cache[url] = self._request(request, f"para {url}")
        return self._cache[url]

    def get_gameweek(self, *, competition_id: str, round_key: str, active_sub_round_key: str) -> str:
        """Replica o POST público acionado pelo seletor de rodadas do site."""
        from urllib.parse import urlencode

        payload = urlencode({
            "sport": "soccer",
            "roundKey": round_key,
            "activeSubRoundKey": active_sub_round_key,
            "wid": "",
            "client_brand": "",
            "client_brand_version": "",
            "user_timezone": "America/Sao_Paulo",
            "isActiveRound": "",
            "competitionId": competition_id,
        }).encode("utf-8")
        request = Request(
            f"{BASE_URL}/en/widget/match_competition_round_gameweek",
            data=payload,
            headers={
                "Accept": "text/html",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "FUTRanking/1.0 (+https://andremes.github.io/FUTRanking/)",
                "X-Requested-With": "XMLHttpRequest",
            },
        )
        return self._request(request, f"ao carregar a rodada {active_sub_round_key}")


def _plain(value: str) -> str:
    return unescape(re.sub(r"<[^>]+>", " ", value)).replace("\xa0", " ").strip()


def _canonical_team_name(name: str) -> str:
    stripped = "".join(
        char for char in normalize("NFKD", name.lower()) if not "\u0300" <= char <= "\u036f"
    )
    ignored = {"ac", "ad", "af", "associacao", "clube", "da", "de", "do", "ec", "esporte", "fc", "futebol", "saf", "sociedade"}
    return " ".join(word for word in re.findall(r"[a-z0-9]+", stripped) if word not in ignored)


def _crest_url(url: str) -> str:
    """Evita o domínio GSA que redireciona imagens HTTPS para HTTP."""
    return url.replace("https://dsg-images.com/", "https://www.dsg-images.com/")


def _season_urls(html: str, competition: GsaCompetition) -> dict[int, str]:
    """Lê a cronologia da própria competição, inclusive nomes patrocinados.

    O endereço muda quando a competição troca de patrocinador. A página de
    cada torneio já lista sua cronologia; portanto não exigimos um *slug*
    idêntico em todos os anos.
    """
    return {
        int(year): f"{BASE_URL}/en/soccer/competition/{slug}-{year}/{identifier}"
        for slug, year, identifier in re.findall(
            r"https?://globalsportsarchive\.com/(?:en/)?soccer/competition/([^\"'<>\s]+?)-(20\d{2})/(\d+)",
            html,
            re.IGNORECASE,
        )
    }


def _stage_positions(html: str) -> list[tuple[int, str]]:
    pattern = re.compile(
        r"gsa-widget-match-competition-list__rounds-item__title[^>]*>(.*?)</div>",
        re.IGNORECASE | re.DOTALL,
    )
    return [(match.start(), _plain(match.group(1))) for match in pattern.finditer(html)]


def _stage_for(position: int, stages: list[tuple[int, str]]) -> str:
    prior = [stage for offset, stage in stages if offset < position]
    return prior[-1] if prior else ""


def _match_rows(html: str, competition: str, *, default_stage: str = "") -> list[dict[str, str]]:
    """Lê os cartões desktop e elimina a cópia mobile pelo identificador GSA."""
    stages = _stage_positions(html)
    pattern = re.compile(
        r'<a\b(?P<attributes>[^>]*\bgsa-match-rounds-v2__match\b[^>]*)>(?P<body>.*?)</a>',
        re.IGNORECASE | re.DOTALL,
    )
    rows: dict[str, dict[str, str]] = {}
    for match in pattern.finditer(html):
        link = re.search(
            r'href="https://globalsportsarchive\.com/en/soccer/match/(?P<date>20\d{2}-\d{2}-\d{2})/[^"]+/(?P<id>\d+)"',
            match.group("attributes"),
            re.IGNORECASE,
        )
        if not link:
            continue
        body = match.group("body")
        teams = re.findall(
            r'<img[^>]+src="(?P<crest>[^"]+)"[^>]+alt="logo of (?P<team>[^"]+)"',
            body,
            re.IGNORECASE,
        )
        score_block = re.search(
            r"gsa-match-played[^>]*>(?P<score>.*?)</div>\s*</div>\s*</div>",
            body,
            re.IGNORECASE | re.DOTALL,
        )
        score = re.search(
            r"(\d+)\s*:\s*(\d+)",
            _plain(score_block.group("score")) if score_block else _plain(body),
        )
        if len(teams) < 2 or not score:
            continue
        (home_crest, home), (away_crest, away) = teams[:2]
        # Alguns cartões históricos incompletos repetem o mesmo clube nos dois
        # lados. Não são partidas válidas e o banco também as rejeita.
        if home.strip().casefold() == away.strip().casefold():
            continue
        match_id = link.group("id")
        rows[match_id] = {
            "external_id": f"gsa:{match_id}",
            # O GSA histórico pode não trazer horário. Isso preserva a data e
            # agrupa jogos do mesmo dia, sem inventar uma ordem entre eles.
            "played_at": f"{link.group('date')}T12:00:00-03:00",
            "competition": competition,
            "matchday": "",
            "stage": _stage_for(match.start(), stages) or default_stage,
            "group_name": "",
            "home_team": unescape(home).strip(),
            "away_team": unescape(away).strip(),
            "home_crest": _crest_url(unescape(home_crest).strip()),
            "away_crest": _crest_url(unescape(away_crest).strip()),
            "home_country": "Brasil",
            "away_country": "Brasil",
            "venue_country": "Brasil",
            "home_goals": score.group(1),
            "away_goals": score.group(2),
        }
    return list(rows.values())


def _existing_equivalent_id(database, row: dict[str, str]) -> str | None:
    """Reutiliza o ID ESPN da mesma partida, sem gerar cópia pela nova fonte."""
    candidates = database.execute(
        """SELECT m.external_id, home.name AS home_team, away.name AS away_team
           FROM matches m
           JOIN clubs home ON home.id=m.home_club_id
           JOIN clubs away ON away.id=m.away_club_id
           WHERE m.competition=? AND substr(m.played_at, 1, 10)=?""",
        (row["competition"], row["played_at"][:10]),
    ).fetchall()
    wanted = (_canonical_team_name(row["home_team"]), _canonical_team_name(row["away_team"]))
    for candidate in candidates:
        actual = (_canonical_team_name(candidate["home_team"]), _canonical_team_name(candidate["away_team"]))
        if wanted == actual:
            return str(candidate["external_id"])
    return None


def _learn_aliases_from_equivalent_match(database, row: dict[str, str], external_id: str) -> None:
    """Aprende um alias apenas quando uma partida coincide entre fontes."""
    existing = database.execute(
        """SELECT home.id AS home_id, away.id AS away_id
           FROM matches m JOIN clubs home ON home.id=m.home_club_id
           JOIN clubs away ON away.id=m.away_club_id WHERE m.external_id=?""",
        (external_id,),
    ).fetchone()
    if existing:
        register_club_alias(database, row["home_team"], row.get("home_country"), int(existing["home_id"]))
        register_club_alias(database, row["away_team"], row.get("away_country"), int(existing["away_id"]))


def _calendar_rounds(html: str) -> list[tuple[str, str, str]]:
    """Retorna fase, competição e sub-rodadas conhecidas pelo seletor público."""
    stages = _stage_positions(html)
    pattern = re.compile(r'<div\s+class="gsa-comp-calendar\b(?P<attributes>[^>]*)>', re.IGNORECASE)
    rounds: list[tuple[str, str, str]] = []
    for match in pattern.finditer(html):
        attrs = match.group("attributes")
        competition_id = re.search(r'data-competition_id="([^"]+)"', attrs)
        weeks = re.search(r'data-weeks="([^"]*)"', attrs)
        if not competition_id or not weeks:
            continue
        try:
            keys = json.loads(unescape(weeks.group(1))).keys()
        except json.JSONDecodeError:
            continue
        stage = _stage_for(match.start(), stages)
        for key in keys:
            rounds.append((stage, competition_id.group(1), str(key)))
    return rounds


def sync_season(database, competition: GsaCompetition, season: int, *, client: GlobalSportsArchiveClient, full: bool = True) -> tuple[int, int]:
    urls = _season_urls(client.get(competition.seed_url), competition)
    if season not in urls:
        raise GlobalSportsArchiveError(f"O Global Sports Archive não listou {competition.name} {season}.")
    url = urls[season]
    page = client.get(url)
    rows = {row["external_id"]: row for row in _match_rows(page, competition.name)}
    calendars: dict[tuple[str, str], list[tuple[str, str, str]]] = {}
    for stage, competition_id, key in _calendar_rounds(page):
        calendars.setdefault((stage, competition_id), []).append((stage, competition_id, key))
    for calendar in calendars.values():
        # A carga anual percorre todas as rodadas. Diariamente, somente as duas
        # mais recentes de cada fase são revistas.
        for stage, competition_id, key in (calendar if full else calendar[-2:]):
            fragment = client.get_gameweek(
                competition_id=competition_id,
                round_key=key.split("_", 1)[0],
                active_sub_round_key=key,
            )
            rows.update({
                row["external_id"]: row
                for row in _match_rows(fragment, competition.name, default_stage=stage)
            })
    if not rows:
        raise GlobalSportsArchiveError(
            f"O Global Sports Archive não retornou partidas concluídas para {competition.name} {season}."
        )
    reused = 0
    for row in rows.values():
        existing_id = _existing_equivalent_id(database, row)
        if existing_id:
            _learn_aliases_from_equivalent_match(database, row, existing_id)
            row["external_id"] = existing_id
            # A Série C já tem jogos ESPN com horário preciso: não o trocamos
            # por um horário aproximado da fonte histórica.
            existing_match = database.execute(
                "SELECT played_at FROM matches WHERE external_id=?", (existing_id,)
            ).fetchone()
            if existing_match:
                row["played_at"] = str(existing_match["played_at"])
            reused += 1
        store_match(database, row)
    store_source_payload(
        database,
        "global-sports-archive",
        url,
        json.dumps(
            {"competition": competition.name, "season": season, "matches": len(rows), "reused_existing_ids": reused},
            separators=(",", ":"),
        ),
    )
    return len(rows), reused


def bootstrap_serie_d(database, *, client: GlobalSportsArchiveClient, today: date | None = None) -> int:
    today = today or date.today()
    total = 0
    competition = BY_NAME["Série D"]
    for season in range(HISTORY_START_YEAR, today.year + 1):
        started = monotonic()
        requests_before = client.request_count
        count, _ = sync_season(database, competition, season, client=client, full=True)
        total += count
        print(
            f"[GSA][histórico] Série D {season}: {count} partidas; "
            f"{client.request_count - requests_before} chamadas; {monotonic() - started:.1f}s."
        )
    return total


def bootstrap_state_competitions(database, *, client: GlobalSportsArchiveClient, today: date | None = None) -> int:
    """Importa todos os estaduais rastreados desde o início da amostra."""
    today = today or date.today()
    total = 0
    for name in STATE_COMPETITION_NAMES:
        competition = BY_NAME[name]
        competition_total = 0
        competition_started = monotonic()
        requests_before_competition = client.request_count
        print(f"[GSA][histórico] {name}: iniciando temporadas {HISTORY_START_YEAR}–{today.year}.")
        for season in range(HISTORY_START_YEAR, today.year + 1):
            started = monotonic()
            requests_before = client.request_count
            count, _ = sync_season(database, competition, season, client=client, full=True)
            competition_total += count
            print(
                f"[GSA][histórico] {name} {season}: {count} partidas; "
                f"{client.request_count - requests_before} chamadas; {monotonic() - started:.1f}s."
            )
        total += competition_total
        print(
            f"[GSA][histórico] {name}: concluído — {competition_total} partidas; "
            f"{client.request_count - requests_before_competition} chamadas; "
            f"{monotonic() - competition_started:.1f}s."
        )
    return total


def sync_current(database, *, client: GlobalSportsArchiveClient, today: date | None = None, full: bool = False) -> tuple[int, int]:
    today = today or date.today()
    total = reused = 0
    # Os estaduais selecionados ocorrem no primeiro semestre. Fora dele, a
    # carga histórica já os consolidou; mantemos apenas C/D para não gastar
    # consultas diárias em torneios encerrados.
    tracked = COMPETITIONS if today.month <= 6 else tuple(
        competition for competition in COMPETITIONS if competition.name in {"Série C", "Série D"}
    )
    for competition in tracked:
        started = monotonic()
        requests_before = client.request_count
        count, existing = sync_season(database, competition, today.year, client=client, full=full)
        total += count
        reused += existing
        print(
            f"[GSA][rotina] {competition.name} {today.year}: {count} partidas verificadas, "
            f"{existing} conciliadas com ESPN; {client.request_count - requests_before} chamadas; "
            f"{monotonic() - started:.1f}s."
        )
    return total, reused
