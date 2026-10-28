"""Catálogo central das competições acompanhadas pelo FUTRanking.

Para acrescentar uma competição ESPN, inclua uma entrada em ``ESPN_COMPETITIONS``.
O identificador do catálogo muda automaticamente, disparando uma recarga histórica
consistente na próxima execução do cron.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Competition:
    espn_slug: str
    name: str


ESPN_COMPETITIONS = (
    Competition("arg.1", "Liga Profissional Argentina"),
    Competition("bra.1", "Série A"),
    Competition("bra.2", "Série B"),
    Competition("bra.3", "Série C"),
    Competition("bra.4", "Série D"),
    Competition("bra.copa_do_brazil", "Copa do Brasil"),
    Competition("conmebol.libertadores", "CONMEBOL Libertadores"),
    Competition("conmebol.sudamericana", "CONMEBOL Sul-Americana"),
    Competition("chi.1", "Primera División do Chile"),
    Competition("col.1", "Primera A Colombiana"),
    Competition("ecu.1", "LigaPro Equador"),
    Competition("uru.1", "Liga AUF Uruguaia"),
    Competition("par.1", "Primera División do Paraguai"),
    Competition("per.1", "Liga 1 do Peru"),
    Competition("bol.1", "Liga Profissional da Bolívia"),
    Competition("ven.1", "Primera División da Venezuela"),
)

# Fallback para a interface caso um perfil de clube não traga país na ESPN.
# Ao cadastrar outra liga nacional, acrescente-a aqui; competições continentais
# não aparecem porque reúnem clubes de vários países.
DOMESTIC_COMPETITION_COUNTRIES = {
    "Liga Profissional Argentina": "Argentina",
    "Série A": "Brasil",
    "Série B": "Brasil",
    "Série C": "Brasil",
    "Série D": "Brasil",
    "Copa do Brasil": "Brasil",
    "Primera División do Chile": "Chile",
    "Primera A Colombiana": "Colômbia",
    "LigaPro Equador": "Equador",
    "Liga AUF Uruguaia": "Uruguai",
    "Primera División do Paraguai": "Paraguai",
    "Liga 1 do Peru": "Peru",
    "Liga Profissional da Bolívia": "Bolívia",
    "Primera División da Venezuela": "Venezuela",
}

COMPETITION_NAMES = frozenset(competition.name for competition in ESPN_COMPETITIONS)
COMPETITION_CATALOG_VERSION = "|".join(
    f"{competition.espn_slug}:{competition.name}" for competition in ESPN_COMPETITIONS
)
DATA_ENRICHMENT_VERSION = "club-country-venue-v2"

