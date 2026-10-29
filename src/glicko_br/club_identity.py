"""Identidade canônica de clubes entre provedores de dados.

Nomes comerciais não são identificadores: ESPN e Global Sports Archive podem
usar, por exemplo, ``Palmeiras`` e ``SE Palmeiras`` para o mesmo clube.
Este módulo só automatiza equivalências verificadas. Nomes semelhantes, mas
ambíguos (Botafogo, Guarani, Nacional, Santa Cruz etc.), nunca são unidos por
heurística genérica.
"""
from __future__ import annotations

import re
from unicodedata import normalize


def alias_key(name: str) -> str:
    plain = "".join(char for char in normalize("NFKD", name.lower()) if not "\u0300" <= char <= "\u036f")
    return " ".join(re.findall(r"[a-z0-9]+", plain))


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
    "cianorte fc": "Cianorte", "ec jacuipe": "Jacuipense", "sampaio correa fc": "Sampaio Corrêa", "nova iguacu fc": "Nova Iguaçu",
    "joinville ec": "Joinville", "manaus fc": "Manaus", "salgueiro ac": "Salgueiro",
    "rio claro fc": "Rio Claro Futebol Clube", "guarani fc": "Guarani", "guarany sc": "Guarany",
    "ca patrocinense": "Patrocinense",
}


def canonical_name(name: str, country_key: str | None) -> str:
    if country_key == "BR":
        return BRAZILIAN_ALIASES.get(alias_key(name), name.strip())
    return name.strip()
