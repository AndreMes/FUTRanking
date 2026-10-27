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
    Competition("bra.1", "Série A"),
    Competition("bra.2", "Série B"),
    Competition("bra.3", "Série C"),
    Competition("bra.4", "Série D"),
    Competition("bra.copa_do_brazil", "Copa do Brasil"),
    Competition("conmebol.libertadores", "CONMEBOL Libertadores"),
)

COMPETITION_NAMES = frozenset(competition.name for competition in ESPN_COMPETITIONS)
COMPETITION_CATALOG_VERSION = "|".join(
    f"{competition.espn_slug}:{competition.name}" for competition in ESPN_COMPETITIONS
)

