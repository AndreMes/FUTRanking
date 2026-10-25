"""Implementação pura e determinística do sistema Glicko-2."""
from __future__ import annotations

from dataclasses import dataclass
from math import exp, log, pi, sqrt
from typing import Iterable

SCALE = 173.7178
DEFAULT_RATING = 1500.0
DEFAULT_RD = 350.0
DEFAULT_VOLATILITY = 0.06
TAU = 0.5


@dataclass(frozen=True)
class Rating:
    rating: float = DEFAULT_RATING
    rd: float = DEFAULT_RD
    volatility: float = DEFAULT_VOLATILITY


@dataclass(frozen=True)
class OpponentResult:
    opponent: Rating
    score: float  # 1 vitória, 0,5 empate, 0 derrota
    rating_offset: float = 0.0
    weight: float = 1.0  # evidência relativa da partida; 1,0 preserva o Glicko-2 padrão


def _g(phi: float) -> float:
    return 1.0 / sqrt(1.0 + 3.0 * phi * phi / (pi * pi))


def expected_score(player: Rating, opponent: Rating, rating_offset: float = 0.0) -> float:
    """Probabilidade de o primeiro clube vencer, incluindo ajuste de mando."""
    mu = (player.rating + rating_offset - DEFAULT_RATING) / SCALE
    opponent_mu = (opponent.rating - DEFAULT_RATING) / SCALE
    return 1.0 / (1.0 + exp(-_g(opponent.rd / SCALE) * (mu - opponent_mu)))


def _new_volatility(phi: float, delta: float, variance: float, sigma: float, tau: float) -> float:
    a = log(sigma * sigma)

    def f(x: float) -> float:
        ex = exp(x)
        numerator = ex * (delta * delta - phi * phi - variance - ex)
        denominator = 2.0 * (phi * phi + variance + ex) ** 2
        return numerator / denominator - (x - a) / (tau * tau)

    if delta * delta > phi * phi + variance:
        b = log(delta * delta - phi * phi - variance)
    else:
        k = 1
        b = a - k * tau
        while f(b) < 0:
            k += 1
            b = a - k * tau

    lo, hi = a, b
    f_lo, f_hi = f(lo), f(hi)
    while abs(hi - lo) > 1e-6:
        midpoint = lo + (lo - hi) * f_lo / (f_hi - f_lo)
        f_mid = f(midpoint)
        if f_mid * f_hi < 0:
            lo, f_lo = hi, f_hi
        else:
            f_lo /= 2.0
        hi, f_hi = midpoint, f_mid
    return exp(lo / 2.0)


def update(player: Rating, results: Iterable[OpponentResult], tau: float = TAU) -> Rating:
    """Atualiza um clube durante um período de rating (normalmente um dia)."""
    outcomes = tuple(results)
    mu, phi = (player.rating - DEFAULT_RATING) / SCALE, player.rd / SCALE
    if not outcomes:
        return Rating(player.rating, sqrt(phi * phi + player.volatility**2) * SCALE, player.volatility)

    terms = []
    for outcome in outcomes:
        opponent_phi = outcome.opponent.rd / SCALE
        g = _g(opponent_phi)
        expectation = expected_score(player, outcome.opponent, outcome.rating_offset)
        terms.append((g, expectation, outcome.score, outcome.weight))
    variance = 1.0 / sum(weight * g * g * expectation * (1.0 - expectation) for g, expectation, _, weight in terms)
    delta = variance * sum(weight * g * (score - expectation) for g, expectation, score, weight in terms)
    volatility = _new_volatility(phi, delta, variance, player.volatility, tau)
    phi_star = sqrt(phi * phi + volatility * volatility)
    new_phi = 1.0 / sqrt(1.0 / (phi_star * phi_star) + 1.0 / variance)
    new_mu = mu + new_phi * new_phi * sum(weight * g * (score - expectation) for g, expectation, score, weight in terms)
    return Rating(DEFAULT_RATING + SCALE * new_mu, SCALE * new_phi, volatility)

