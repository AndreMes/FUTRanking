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
    # Cobertura ESPN confirmada para todo o período-base. Os demais estaduais
    # entram pela GSA, que mantém melhor acervo histórico nesse nível.
    Competition("bra.camp.paulista", "Campeonato Paulista"),
    Competition("bra.camp.carioca", "Campeonato Carioca"),
    Competition("bra.camp.mineiro", "Campeonato Mineiro"),
    Competition("bra.camp.gaucho", "Campeonato Gaúcho"),
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

# Competições brasileiras complementares que são coletadas exclusivamente pela
# Global Sports Archive. Elas ficam no catálogo comum para que banco,
# exportação e filtros reconheçam os seus jogos, sem aumentar as chamadas à ESPN.
GSA_ONLY_COMPETITIONS = (
    "Paulista A2",
    "Campeonato Paranaense",
    "Campeonato Baiano",
    "Campeonato Pernambucano",
    "Campeonato Cearense",
    "Campeonato Goiano",
    "Campeonato Catarinense",
    "Copa do Nordeste",
    "Copa Paulista",
    "Campeonato Paraense",
    "Campeonato Alagoano",
    "Campeonato Potiguar",
    "Campeonato Amazonense",
    "Campeonato Paraibano",
    "Campeonato Maranhense",
    "Campeonato Piauiense",
    "Campeonato Sergipano",
    "Campeonato Mato-Grossense",
    "Campeonato Acreano",
    "Campeonato Amapaense",
    "Campeonato Brasiliense",
    "Campeonato Capixaba",
    "Campeonato Rondoniense",
    "Campeonato Roraimense",
    "Campeonato Sul-Mato-Grossense",
    "Campeonato Tocantinense",
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
    "Campeonato Paulista": "Brasil",
    "Paulista A2": "Brasil",
    "Campeonato Carioca": "Brasil",
    "Campeonato Mineiro": "Brasil",
    "Campeonato Gaúcho": "Brasil",
    "Campeonato Paranaense": "Brasil",
    "Campeonato Baiano": "Brasil",
    "Campeonato Pernambucano": "Brasil",
    "Campeonato Cearense": "Brasil",
    "Campeonato Goiano": "Brasil",
    "Campeonato Catarinense": "Brasil",
    "Copa do Nordeste": "Brasil",
    "Copa Paulista": "Brasil",
    "Campeonato Paraense": "Brasil",
    "Campeonato Alagoano": "Brasil",
    "Campeonato Potiguar": "Brasil",
    "Campeonato Amazonense": "Brasil",
    "Campeonato Paraibano": "Brasil",
    "Campeonato Maranhense": "Brasil",
    "Campeonato Piauiense": "Brasil",
    "Campeonato Sergipano": "Brasil",
    "Campeonato Mato-Grossense": "Brasil",
    "Campeonato Acreano": "Brasil",
    "Campeonato Amapaense": "Brasil",
    "Campeonato Brasiliense": "Brasil",
    "Campeonato Capixaba": "Brasil",
    "Campeonato Rondoniense": "Brasil",
    "Campeonato Roraimense": "Brasil",
    "Campeonato Sul-Mato-Grossense": "Brasil",
    "Campeonato Tocantinense": "Brasil",
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

# Os estaduais não são apenas competições: eles também fornecem uma evidência
# pública e estável da UF de origem do clube. Isso permite apresentar o estado
# no perfil e torna a auditoria de homônimos (por exemplo, Botafogo) segura.
BRAZILIAN_STATE_BY_COMPETITION = {
    "Campeonato Paulista": "SP", "Paulista A2": "SP",
    "Campeonato Carioca": "RJ", "Campeonato Mineiro": "MG",
    "Campeonato Gaúcho": "RS", "Campeonato Paranaense": "PR",
    "Campeonato Baiano": "BA", "Campeonato Pernambucano": "PE",
    "Campeonato Cearense": "CE", "Campeonato Goiano": "GO",
    "Campeonato Catarinense": "SC", "Copa Paulista": "SP",
    "Campeonato Paraense": "PA", "Campeonato Alagoano": "AL",
    "Campeonato Potiguar": "RN", "Campeonato Amazonense": "AM",
    "Campeonato Paraibano": "PB", "Campeonato Maranhense": "MA",
    "Campeonato Piauiense": "PI", "Campeonato Sergipano": "SE",
    "Campeonato Mato-Grossense": "MT",
    "Campeonato Acreano": "AC", "Campeonato Amapaense": "AP",
    "Campeonato Brasiliense": "DF", "Campeonato Capixaba": "ES",
    "Campeonato Rondoniense": "RO", "Campeonato Roraimense": "RR",
    "Campeonato Sul-Mato-Grossense": "MS", "Campeonato Tocantinense": "TO",
}

COMPETITION_NAMES = frozenset(competition.name for competition in ESPN_COMPETITIONS) | frozenset(GSA_ONLY_COMPETITIONS)
COMPETITION_CATALOG_VERSION = "|".join(
    f"{competition.espn_slug}:{competition.name}" for competition in ESPN_COMPETITIONS
)
# Atualiza uma única vez os bancos persistidos que ainda não carregaram a Série B 2026.
DATA_ENRICHMENT_VERSION = "club-country-venue-v3-serie-b"


