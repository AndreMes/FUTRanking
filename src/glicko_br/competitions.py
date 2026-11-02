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
    scope: str = "domestic"
    start_year: int = 2016


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
    # Pelo alcance nacional e pela presença recorrente de clubes de várias
    # divisões, a Copa do Brasil funciona como ponte de informação entre
    # ecossistemas competitivos. No modelo ela recebe peso continental.
    Competition("bra.copa_do_brazil", "Copa do Brasil", "continental"),
    Competition("conmebol.libertadores", "CONMEBOL Libertadores", "continental"),
    Competition("conmebol.sudamericana", "CONMEBOL Sul-Americana", "continental"),
    Competition("FIFA.CWC", "FIFA Club World Cup", "world"),
    # Europa: nomes de exibição seguem o uso editorial das próprias ligas.
    # Os dados históricos são carregados uma vez por competição, e não alteram
    # o acervo já consolidado das demais coberturas.
    Competition("eng.1", "Premier League"),
    Competition("eng.2", "EFL Championship"),
    Competition("esp.1", "LaLiga"),
    Competition("esp.2", "LaLiga 2"),
    Competition("ita.1", "Serie A"),
    Competition("ita.2", "Serie B"),
    Competition("ger.1", "Bundesliga"),
    Competition("ger.2", "2. Bundesliga"),
    Competition("fra.1", "Ligue 1"),
    Competition("fra.2", "Ligue 2"),
    Competition("por.1", "Primeira Liga"),
    Competition("ned.1", "Eredivisie"),
    Competition("bel.1", "Belgian Pro League"),
    Competition("tur.1", "Turkish Super Lig"),
    Competition("sco.1", "Scottish Premiership"),
    Competition("sui.1", "Swiss Super League"),
    Competition("aut.1", "Austrian Bundesliga"),
    Competition("den.1", "Danish Superliga"),
    Competition("gre.1", "Greek Super League"),
    Competition("cze.1", "Czech First League"),
    # Expansão internacional: ligas com presença relevante em competições
    # intercontinentais e clubes com jogadores brasileiros em atividade.
    Competition("mex.1", "Liga MX"),
    Competition("usa.1", "MLS"),
    Competition("jpn.1", "J1 League"),
    Competition("ksa.1", "Saudi Pro League"),
    Competition("rus.1", "Russian Premier League"),
    Competition("uefa.champions", "UEFA Champions League", "continental"),
    Competition("uefa.europa", "UEFA Europa League", "continental"),
    Competition("uefa.europa.conf", "UEFA Conference League", "continental", 2021),
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
    "Supercopa do Brasil",
    "CONMEBOL Recopa Sul-Americana",
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
    "Supercopa do Brasil": "Brasil",
    "Copa do Brasil": "Brasil",
    "Primera División do Chile": "Chile",
    "Primera A Colombiana": "Colômbia",
    "LigaPro Equador": "Equador",
    "Liga AUF Uruguaia": "Uruguai",
    "Primera División do Paraguai": "Paraguai",
    "Liga 1 do Peru": "Peru",
    "Liga Profissional da Bolívia": "Bolívia",
    "Primera División da Venezuela": "Venezuela",
    "Premier League": "Inglaterra",
    "EFL Championship": "Inglaterra",
    "LaLiga": "Espanha",
    "LaLiga 2": "Espanha",
    "Serie A": "Itália",
    "Serie B": "Itália",
    "Bundesliga": "Alemanha",
    "2. Bundesliga": "Alemanha",
    "Ligue 1": "França",
    "Ligue 2": "França",
    "Primeira Liga": "Portugal",
    "Eredivisie": "Holanda",
    "Belgian Pro League": "Bélgica",
    "Turkish Super Lig": "Turquia",
    "Scottish Premiership": "Escócia",
    "Swiss Super League": "Suíça",
    "Austrian Bundesliga": "Áustria",
    "Danish Superliga": "Dinamarca",
    "Greek Super League": "Grécia",
    "Czech First League": "Tchéquia",
    "Liga MX": "México",
    "MLS": "Estados Unidos",
    "J1 League": "Japão",
    "Saudi Pro League": "Arábia Saudita",
    "Russian Premier League": "Rússia",
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

# O alcance é uma característica do torneio, não do clube participante. Isto
# impede, por exemplo, que uma liga nacional pequena seja tratada como jogo
# continental só porque tem um campeão que também disputa a Libertadores.
COMPETITION_SCOPE_WEIGHTS = {
    "domestic": 1.00,
    "continental": 1.50,
    "world": 3.00,
}
CONTINENTAL_COMPETITION_NAMES = frozenset(
    competition.name for competition in ESPN_COMPETITIONS if competition.scope == "continental"
) | frozenset({"CONMEBOL Recopa Sul-Americana"})
WORLD_COMPETITION_NAMES = frozenset(
    competition.name for competition in ESPN_COMPETITIONS if competition.scope == "world"
)


def competition_scope(competition: str) -> str:
    """Classifica o escopo esportivo de uma competição do catálogo."""
    if competition in WORLD_COMPETITION_NAMES:
        return "world"
    if competition in CONTINENTAL_COMPETITION_NAMES:
        return "continental"
    return "domestic"


def competition_scope_weight(competition: str) -> float:
    """Retorna o multiplicador de evidência aplicável à competição."""
    return COMPETITION_SCOPE_WEIGHTS[competition_scope(competition)]


COMPETITION_SCOPE_VERSION = "scope-domestic-1.00-continental-1.50-world-3.00-copa-brasil-continental"
COMPETITION_CATALOG_VERSION = "|".join(
    f"{competition.espn_slug}:{competition.name}:{competition.scope}:{competition.start_year}" for competition in ESPN_COMPETITIONS
) + f"|{COMPETITION_SCOPE_VERSION}"
# Atualiza uma única vez os bancos persistidos que ainda não carregaram a Série B 2026.
DATA_ENRICHMENT_VERSION = "club-country-venue-v3-serie-b"

