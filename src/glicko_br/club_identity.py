"""Identidade canônica de clubes entre provedores de dados.

Nomes comerciais não são identificadores: ESPN e Global Sports Archive podem
usar, por exemplo, ``Palmeiras`` e ``SE Palmeiras`` para o mesmo clube. Este
módulo só automatiza equivalências verificadas. Nomes semelhantes, mas
ambíguos (Botafogo, Guarani, Nacional, Santa Cruz etc.), nunca são unidos por
heurística genérica.
"""
from __future__ import annotations

import re
from unicodedata import normalize


def alias_key(name: str) -> str:
    plain = "".join(char for char in normalize("NFKD", name.lower()) if not "\u0300" <= char <= "\u036f")
    return " ".join(re.findall(r"[a-z0-9]+", plain))


def provider_match_key(name: str) -> str:
    """Chave restrita à conciliação de uma mesma partida entre provedores.

    Não é usada sozinha para unir clubes: apenas junto com competição, data,
    placar e o adversário correspondente. Por isso pode ignorar a razão social
    sem transformar um homônimo em uma identidade única.
    """
    ignored = {
        "ac", "ad", "af", "aa", "associacao", "ca", "clube", "cr", "da", "de", "do",
        "ec", "esporte", "esportes", "fc", "futebol", "saf", "sc", "se", "sociedade",
    }
    return " ".join(word for word in alias_key(name).split() if word not in ignored)


# Alias -> nome publicado canônico. A chave de país evita misturar homônimos
# internacionais. A lista deliberadamente privilegia precisão: novos casos
# são aprendidos apenas quando uma mesma partida é conciliada entre fontes.
BRAZILIAN_ALIASES = {
    "se palmeiras": "Palmeiras", "cr flamengo": "Flamengo", "fluminense fc": "Fluminense",
    "sao paulo fc": "São Paulo", "sc internacional": "Internacional", "santos fc": "Santos",
    "cruzeiro ec": "Cruzeiro", "cr vasco da gama": "Vasco da Gama", "aa ponte preta": "Ponte Preta",
    "ec juventude": "Juventude", "ec bahia": "Bahia", "ec vitoria": "Vitória",
    "goias ec": "Goiás", "associacao chapecoense de futebol": "Chapecoense", "avai fc": "Avaí",
    "vila nova fc": "Vila Nova", "ceara sc": "Ceará", "fortaleza ec": "Fortaleza",
    "criciuma ec": "Criciúma", "londrina ec": "Londrina", "figueirense fc": "Figueirense",
    "ituano fc": "Ituano", "mirassol fc": "Mirassol", "volta redonda fc": "Volta Redonda",
    "tombense fc": "Tombense", "brusque fc": "Brusque", "ypiranga fc": "Ypiranga",
    "oeste fc": "Oeste", "abc fc": "ABC", "ec agua santa": "Água Santa", "aa caldense": "Caldense",
    "anapolis fc": "Anápolis", "ad confianca": "Confiança", "madureira ec": "Madureira",
    "bangu ac": "Bangu", "ec jacuipense": "Jacuipense", "uberlandia ec": "Uberlândia",
    "boa ec": "Boa Esporte", "floresta ec": "Floresta", "retro fc": "Retrô",
    "ca linense": "Linense", "fc atletico cearense": "Atlético Cearense", "pouso alegre fc": "Pouso Alegre",
    "ad bahia de feira": "Bahia de Feira", "ferroviario ac": "Ferroviário", "ec santo andre": "Santo André",
    "ec sao bento": "São Bento", "ad sao caetano": "São Caetano", "aa aparecidense": "Aparecidense",
    "ec novo hamburgo": "Novo Hamburgo", "goianesia ec": "Goianésia", "resende fc": "Resende",
    "cianorte fc": "Cianorte", "ec jacuipe": "Jacuipense", "sampaio correa fc": "Sampaio Corrêa",
    "nova iguacu fc": "Nova Iguaçu", "joinville ec": "Joinville", "manaus fc": "Manaus",
    "salgueiro ac": "Salgueiro", "rio claro fc": "Rio Claro Futebol Clube", "guarani fc": "Guarani",
    "guarany sc": "Guarany", "ca patrocinense": "Patrocinense",
    # Primeira rodada de revisão humana na fila administrativa. Os alvos são
    # grafias já presentes no histórico para que a migração una as partidas.
    "paysandu sc": "Paysandu", "luverdense ec": "Luverdense",
    "aa coruripe": "Coruripe", "tocantinopolis ec": "Tocantinopolis",
    "ivinhema fc": "Ivinhema", "river ac": "River AC",
    "parnahyba sc": "Parnahyba", "galvez ec": "Galvez",
    "santos ap": "Santos FC (AP)", "rio branco fc": "Rio Branco AC",
    "goytacaz fc": "Goytacaz", "murici fc": "Murici",
    "aa luziania": "Luziânia", "gurupi ec": "Gurupi",
    "rondoniense sc": "Rondoniense", "ceilandia ec": "Ceilândia",
    "sinop fc": "Sinop", "cordino ec": "Cordino",
    "interporto fc": "Interporto", "novoperario fc": "Novoperário",
    "treze fc": "Treze", "real ariquemes ec": "Real Ariquemes",
    "brasiliense fc": "Brasiliense", "aa altos": "Altos",
    "corumbaense fc": "Corumbaense", "sobradinho ec": "Sobradinho",
    "mixto ec": "Mixto", "vilhenense ec": "Vilhenense",
    "aquidauanense fc": "Aquidauanense", "lagarto fc": "Lagarto",
    "real brasilia fc": "Real Brasília", "se picos": "Picos",
    "nova mutum ec": "Nova Mutum", "penarol ac": "Penarol",
    "sc humaita": "Humaita", "nova venecia fc": "Nova Venécia",
    "amazonas fc": "Amazonas", "falcon fc": "Falcon",
    "aguia de maraba fc": "Aguia de Maraba", "manauara ec": "Manauara",
    "capital fc": "Capital", "maranhao ac": "Maranhao",
    "betim futebol": "Betim FC", "independencia fc": "Independência",
    "serra branca ec": "Serra Branca", "bare ec": "Bare",
    "iape fc": "IAPE", "monte roraima fc": "Monte Roraima",
    "guapore fc": "Guapore", "galicia ec": "Galicia EC",
    "ec democrata": "Democrata FC", "sao raimundo rr": "São Raimundo EC (RR)",
    "princesa do solimoes ec": "Princesa do Solimoes", "globo fc": "Globo",
}


def canonical_name(name: str, country_key: str | None) -> str:
    """Retorna somente um alvo que foi explicitamente verificado."""
    if country_key == "BR":
        return BRAZILIAN_ALIASES.get(alias_key(name), name.strip())
    return name.strip()

