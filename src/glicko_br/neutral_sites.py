"""Exceções auditáveis para partidas disputadas em campo neutro.

A ESPN não expõe uma flag confiável de neutralidade. Para incluir outro jogo,
adicione o seu identificador estável no formato ``espn:<event-id>`` abaixo.
"""
from __future__ import annotations


NEUTRAL_EVENT_IDS = frozenset({
    # Final única da CONMEBOL Libertadores 2026: Palmeiras x Estudiantes.
    "espn:401912519",
})


def is_neutral_event(external_id: str) -> bool:
    return external_id in NEUTRAL_EVENT_IDS

