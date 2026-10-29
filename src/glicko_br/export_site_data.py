"""Exporta o último ranking calculado para o painel estático."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .database import MAX_INACTIVITY_DAYS, MAX_RANKING_RD, connect, initialise, latest_ranking
from .glicko2 import Rating
from .database import HOME_ADVANTAGE
from .simulation import outcome_probabilities, simulate_season
from .neutral_sites import is_neutral_event
from .club_metadata import COUNTRY_OVERRIDES
from .competitions import DOMESTIC_COMPETITION_COUNTRIES
from .competitions import ESPN_COMPETITIONS
from .model_selection import EVALUATION_VERSION
from .crest_colors import backfill_fixture_colors


def public_crest_url(url: str | None) -> str | None:
    """Converte URLs históricos da GSA para o domínio HTTPS que não redireciona."""
    return url.replace("https://dsg-images.com/", "https://www.dsg-images.com/") if url else url


def exported_matches(database) -> list[dict[str, object]]:
    """Resultados brutos que explicam o ranking exibido no site."""
    rows = database.execute(
        """SELECT m.external_id, m.played_at, m.competition, m.matchday, m.neutral_site, m.home_advantage, m.venue_country, m.stage, m.group_name, home.name AS home_team, home.crest_url AS home_crest, home.primary_color AS home_color,
                  away.name AS away_team, away.crest_url AS away_crest, away.primary_color AS away_color, m.home_goals, m.away_goals,
                  home_effect.rating_after AS home_rating_after, home_effect.rating_effect AS home_rating_effect,
                  away_effect.rating_after AS away_rating_after, away_effect.rating_effect AS away_rating_effect
           FROM matches m
           JOIN clubs home ON home.id = m.home_club_id
           JOIN clubs away ON away.id = m.away_club_id
           LEFT JOIN match_rating_effects home_effect ON home_effect.external_id = m.external_id AND home_effect.club_id = m.home_club_id
           LEFT JOIN match_rating_effects away_effect ON away_effect.external_id = m.external_id AND away_effect.club_id = m.away_club_id
           ORDER BY m.played_at DESC, m.external_id DESC"""
    ).fetchall()
    matches = []
    for row in rows:
        match = dict(row)
        match["home_crest"] = public_crest_url(match.get("home_crest"))
        match["away_crest"] = public_crest_url(match.get("away_crest"))
        matches.append(match)
    return matches


def team_performance(matches: list[dict[str, object]], team: str) -> dict[str, int]:
    games = wins = draws = losses = goals_for = goals_against = 0
    for match in matches:
        is_home = match["home_team"] == team
        if not is_home and match["away_team"] != team:
            continue
        scored = int(match["home_goals"] if is_home else match["away_goals"])
        conceded = int(match["away_goals"] if is_home else match["home_goals"])
        games += 1
        goals_for += scored
        goals_against += conceded
        if scored > conceded:
            wins += 1
        elif scored == conceded:
            draws += 1
        else:
            losses += 1
    return {
        "games": games, "wins": wins, "draws": draws, "losses": losses,
        "goals_for": goals_for, "goals_against": goals_against,
        "points": wins * 3 + draws,
    }


DEFAULT_DRAW_RATE = 0.25


def fixture_draw_rates(database) -> tuple[dict[tuple[str, str], float], dict[str, float]]:
    """Taxas observadas por competição/temporada, com histórico como reserva."""
    seasonal = {
        (row["competition"], row["season"]): float(row["draw_rate"])
        for row in database.execute(
            """SELECT competition, substr(played_at, 1, 4) AS season,
                      AVG(home_goals = away_goals) AS draw_rate
               FROM matches GROUP BY competition, season"""
        )
    }
    historical = {
        row["competition"]: float(row["draw_rate"])
        for row in database.execute(
            "SELECT competition, AVG(home_goals = away_goals) AS draw_rate FROM matches GROUP BY competition"
        )
    }
    return seasonal, historical


def exported_fixtures(database, ranking) -> list[dict[str, object]]:
    ratings = {row["name"]: Rating(row["rating"], row["rd"], row["volatility"]) for row in ranking}
    seasonal_draw_rates, historical_draw_rates = fixture_draw_rates(database)
    rows = database.execute(
        """SELECT f.external_id, f.scheduled_at, f.status, f.competition, f.matchday, f.neutral_site, f.home_advantage, f.venue_country, f.stage, f.group_name, home.name AS home_team, home.crest_url AS home_crest,
                  away.name AS away_team, away.crest_url AS away_crest
           FROM fixtures f JOIN clubs home ON home.id=f.home_club_id JOIN clubs away ON away.id=f.away_club_id
           WHERE NOT EXISTS (SELECT 1 FROM matches m WHERE m.external_id=f.external_id)
           ORDER BY f.scheduled_at""",
    ).fetchall()
    fixtures = []
    for row in rows:
        neutral_site = bool(row["neutral_site"]) or is_neutral_event(row["external_id"])
        home, away = ratings.get(row["home_team"], Rating()), ratings.get(row["away_team"], Rating())
        home_advantage = 0.0 if neutral_site else float(row["home_advantage"])
        season = str(row["scheduled_at"])[:4]
        draw_rate = seasonal_draw_rates.get(
            (row["competition"], season), historical_draw_rates.get(row["competition"], DEFAULT_DRAW_RATE)
        )
        home_chance, draw_chance, away_chance = outcome_probabilities(home, away, home_advantage, draw_rate)
        # Ao exibir uma casa decimal, fechamos a terceira ponta por diferença
        # para o mercado 1×2 continuar somando exatamente 100,0%.
        home_percentage = round(home_chance * 100, 1)
        draw_percentage = round(draw_chance * 100, 1)
        away_percentage = round(100.0 - home_percentage - draw_percentage, 1)
        fixture = dict(row)
        fixture["home_crest"] = public_crest_url(fixture.get("home_crest"))
        fixture["away_crest"] = public_crest_url(fixture.get("away_crest"))
        fixtures.append({**fixture, "neutral_site": neutral_site, "home_advantage": home_advantage, "home_rating": home.rating, "away_rating": away.rating,
                         "home_favoritism": home_percentage, "draw_probability": draw_percentage,
                         "away_favoritism": away_percentage, "draw_rate_reference": round(draw_rate * 100, 1)})
    return fixtures


def exported_simulation(database, ranking, fixtures: list[dict[str, object]]) -> dict[str, object]:
    """Prepara projeções independentes para as Séries A e B em andamento."""
    season = datetime.now(timezone.utc).year
    ratings = {row["name"]: Rating(row["rating"], row["rd"], row["volatility"]) for row in ranking}
    crests = {row["name"]: public_crest_url(row["crest_url"]) for row in database.execute("SELECT name, crest_url FROM clubs")}
    simulations = []
    for competition, promotion_slots, playoff_promotion_slots in (("Série A", 0, 0), ("Série B", 4, 2)):
        matches = [dict(row) for row in database.execute(
            """SELECT home.name AS home_team, away.name AS away_team, m.home_goals, m.away_goals
               FROM matches m JOIN clubs home ON home.id=m.home_club_id JOIN clubs away ON away.id=m.away_club_id
               WHERE m.competition=? AND m.played_at >= ? AND m.played_at < ?""",
            (competition, f"{season}-01-01", f"{season + 1}-01-01"),
        ).fetchall()]
        # A agenda da ESPN pode anunciar uma fase futura como "TBD Home" x
        # "TBD Away". Ela não representa um 21º/22º clube e não pode entrar
        # numa simulação de pontos corridos antes que os participantes existam.
        competition_fixtures = [
            fixture for fixture in fixtures
            if fixture["competition"] == competition
            and str(fixture["scheduled_at"])[:4] == str(season)
            and not str(fixture["home_team"]).strip().lower().startswith("tbd")
            and not str(fixture["away_team"]).strip().lower().startswith("tbd")
        ]
        simulation = (
            simulate_season(
                matches, competition_fixtures, ratings, seed=season,
                promotion_slots=promotion_slots, playoff_promotion_slots=playoff_promotion_slots,
            )
            if competition_fixtures else {
                "available": False,
                "completed_matches": len(matches),
                "fixtures_remaining": 0,
                "unavailable_reason": "Ainda não há fixtures restantes importados para esta competição.",
            }
        )
        simulation.update({"competition": competition, "season": season, "playoff_promotion_slots": playoff_promotion_slots})
        if simulation["available"]:
            for team in simulation["teams"]:
                team["crest"] = crests.get(team["name"])
        simulations.append(simulation)
    return {"available": any(simulation["available"] for simulation in simulations), "season": season, "competitions": simulations}


def current_divisions(database) -> dict[str, set[str]]:
    """Identifica as divisões nacionais disputadas por cada clube na temporada atual."""
    season = str(datetime.now(timezone.utc).year)
    divisions: dict[str, set[str]] = {}
    rows = database.execute(
        """SELECT competition, team FROM (
               SELECT m.competition, home.name AS team FROM matches m JOIN clubs home ON home.id=m.home_club_id
                WHERE m.competition IN ('Série A', 'Série B', 'Série C', 'Série D') AND m.played_at LIKE ?
               UNION
               SELECT m.competition, away.name AS team FROM matches m JOIN clubs away ON away.id=m.away_club_id
                WHERE m.competition IN ('Série A', 'Série B', 'Série C', 'Série D') AND m.played_at LIKE ?
               UNION
               SELECT f.competition, home.name AS team FROM fixtures f JOIN clubs home ON home.id=f.home_club_id
                WHERE f.competition IN ('Série A', 'Série B', 'Série C', 'Série D') AND f.scheduled_at LIKE ?
               UNION
               SELECT f.competition, away.name AS team FROM fixtures f JOIN clubs away ON away.id=f.away_club_id
                WHERE f.competition IN ('Série A', 'Série B', 'Série C', 'Série D') AND f.scheduled_at LIKE ?
           )""",
        (f"{season}%", f"{season}%", f"{season}%", f"{season}%"),
    ).fetchall()
    for row in rows:
        divisions.setdefault(row["team"], set()).add(row["competition"])
    return divisions


def club_countries(database) -> dict[str, str]:
    """Completa países a partir das ligas nacionais quando necessário."""
    countries = {
        row["name"]: row["country"] for row in database.execute(
            "SELECT name, country FROM clubs WHERE country IS NOT NULL AND country <> ''"
        ).fetchall()
    }
    placeholders = ", ".join("?" for _ in DOMESTIC_COMPETITION_COUNTRIES)
    rows = database.execute(
        f"""SELECT competition, name FROM (
               SELECT m.competition, home.name AS name FROM matches m JOIN clubs home ON home.id=m.home_club_id WHERE m.competition IN ({placeholders})
               UNION SELECT m.competition, away.name AS name FROM matches m JOIN clubs away ON away.id=m.away_club_id WHERE m.competition IN ({placeholders})
               UNION SELECT f.competition, home.name AS name FROM fixtures f JOIN clubs home ON home.id=f.home_club_id WHERE f.competition IN ({placeholders})
               UNION SELECT f.competition, away.name AS name FROM fixtures f JOIN clubs away ON away.id=f.away_club_id WHERE f.competition IN ({placeholders})
           )""",
        tuple(DOMESTIC_COMPETITION_COUNTRIES) * 4,
    ).fetchall()
    for row in rows:
        countries.setdefault(row["name"], DOMESTIC_COMPETITION_COUNTRIES[row["competition"]])
    for name, country in COUNTRY_OVERRIDES.items():
        countries.setdefault(name, country)
    return countries


def exported_data_health(database) -> list[dict[str, object]]:
    """Resume a cobertura efetivamente persistida, por competição.

    A página não infere disponibilidade da fonte: ela apresenta somente o que
    já foi importado para o banco usado no ranking publicado.
    """
    matches = {
        row["competition"]: dict(row)
        for row in database.execute(
            """SELECT competition, COUNT(*) AS finished_matches,
                      MIN(played_at) AS first_match_at, MAX(played_at) AS last_match_at
               FROM matches GROUP BY competition"""
        ).fetchall()
    }
    fixtures = {
        row["competition"]: int(row["pending_fixtures"])
        for row in database.execute(
            "SELECT competition, COUNT(*) AS pending_fixtures FROM fixtures GROUP BY competition"
        ).fetchall()
    }
    names = sorted(set(matches) | set(fixtures), key=lambda value: value.lower())
    return [
        {
            "competition": name,
            "finished_matches": int(matches.get(name, {}).get("finished_matches", 0)),
            "first_match_at": matches.get(name, {}).get("first_match_at"),
            "last_match_at": matches.get(name, {}).get("last_match_at"),
            "pending_fixtures": fixtures.get(name, 0),
        }
        for name in names
    ]


def data_sources_for(competition: str) -> list[dict[str, str]]:
    """Proveniência pública exibida junto da competição em Dados."""
    espn = {item.name: item.espn_slug for item in ESPN_COMPETITIONS}
    if competition == "Série C":
        return [{"period": "2016–2025", "source": "ESPN", "url": "https://www.espn.com/soccer/scoreboard/_/league/bra.3"}, {"period": "2026–atual", "source": "Global Sports Archive", "url": "https://globalsportsarchive.com/en/soccer/competition/serie-c-2026/77984"}]
    if competition == "Série D":
        return [{"period": "2016–atual", "source": "Global Sports Archive", "url": "https://globalsportsarchive.com/en/soccer/competition/serie-d-2026/77985"}]
    if competition in espn:
        return [{"period": "2016–atual", "source": "ESPN", "url": f"https://www.espn.com/soccer/scoreboard/_/league/{espn[competition]}"}]
    return []


def _backtest_summary(rows) -> dict[str, object]:
    """Agrega previsões feitas antes do jogo em faixas de calibração."""
    rows = list(rows)
    bins = [{"label": f"{start}\u2013{start + 10}%", "count": 0, "predicted_total": 0.0, "observed_total": 0.0} for start in range(0, 100, 10)]
    for row in rows:
        expected, observed = float(row["home_expected"]), float(row["home_score"])
        bucket = bins[min(9, int(expected * 10))]
        bucket["count"] += 1
        bucket["predicted_total"] += expected
        bucket["observed_total"] += observed
    count = len(rows)
    summary_bins = [
        {
            "label": bucket["label"],
            "count": bucket["count"],
            "predicted": round(bucket["predicted_total"] / bucket["count"], 4),
            "observed": round(bucket["observed_total"] / bucket["count"], 4),
        }
        for bucket in bins if bucket["count"]
    ]
    if not count:
        return {"matches": 0, "mean_prediction": None, "mean_observed": None, "brier_score": None, "mean_absolute_error": None, "bins": []}
    return {
        "matches": count,
        "mean_prediction": round(sum(float(row["home_expected"]) for row in rows) / count, 4),
        "mean_observed": round(sum(float(row["home_score"]) for row in rows) / count, 4),
        "brier_score": round(sum((float(row["home_expected"]) - float(row["home_score"])) ** 2 for row in rows) / count, 4),
        "mean_absolute_error": round(sum(abs(float(row["home_expected"]) - float(row["home_score"])) for row in rows) / count, 4),
        "bins": summary_bins,
    }


def exported_backtest(database) -> dict[str, object]:
    """Mede a calibração com previsões persistidas antes de cada resultado."""
    rows = database.execute(
        """SELECT m.competition, forecast.home_expected, forecast.home_score
           FROM match_forecasts forecast JOIN matches m ON m.external_id=forecast.external_id
           ORDER BY m.played_at"""
    ).fetchall()
    by_competition: dict[str, list] = {}
    for row in rows:
        by_competition.setdefault(row["competition"], []).append(row)
    return {
        "overall": _backtest_summary(rows),
        "competitions": [
            {"competition": competition, **_backtest_summary(competition_rows)}
            for competition, competition_rows in sorted(by_competition.items())
        ],
    }


def exported_model_selection(database) -> dict[str, object] | None:
    """Entrega o último experimento temporal já calculado pelo workflow."""
    row = database.execute(
        "SELECT payload FROM model_evaluations WHERE version=?", (EVALUATION_VERSION,)
    ).fetchone()
    return json.loads(row["payload"]) if row else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    database = connect(args.database)
    initialise(database)
    colors_updated = backfill_fixture_colors(database)
    if colors_updated:
        database.commit()
        print(f"{colors_updated} cores de escudo armazenadas para os fixtures.")
    ranking = latest_ranking(database)
    if not ranking:
        parser.error("O banco ainda não possui um ranking para exportar.")
    matches = exported_matches(database)
    divisions = current_divisions(database)
    countries = club_countries(database)
    teams = []
    excluded_teams = []
    for row in ranking:
        name = row["name"]
        team = {
            "name": name,
            "crest": public_crest_url(row["crest_url"]),
            "rating": row["rating"],
            "rd": round(row["rd"], 1),
            "last_tracked_at": row["last_tracked_at"],
            "days_without_tracking": row["days_without_tracking"],
            "performance": team_performance(matches, name),
            "divisions": sorted(divisions.get(name, set())),
            "country": countries.get(name, "País não informado"),
        }
        if row["eligible"]:
            team["position"] = len(teams) + 1
            teams.append(team)
        else:
            team["ineligibility_reasons"] = row["ineligibility_reasons"]
            excluded_teams.append(team)
    fixtures = exported_fixtures(database, ranking)
    health = exported_data_health(database)
    for row in health:
        row["sources"] = data_sources_for(str(row["competition"]))
    payload = {
        "competition": "Campeonato Brasileiro Série A",
        "period_date": ranking[0]["period_date"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "ESPN + Global Sports Archive (Séries C/D)",
        "scope_note": "Desempenho calculado sobre todas as partidas importadas neste ranking.",
        "eligibility": {"max_inactivity_days": MAX_INACTIVITY_DAYS, "max_rd": MAX_RANKING_RD},
        "teams": teams,
        "excluded_teams": excluded_teams,
        "matches": matches,
        "fixtures": fixtures,
        "data_health": health,
        "simulation": exported_simulation(database, ranking, fixtures),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(ranking)} clubes exportados para {output}")


if __name__ == "__main__":
    main()
