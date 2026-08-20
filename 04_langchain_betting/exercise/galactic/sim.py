"""Offline calibration. Does a well-informed bettor actually beat this book?

Not a student-facing module — it is the evidence that the exercise is winnable, and the knob
we tuned the bookmaker's biases against. Run it:

    python -m galactic.sim --n 400

Each trial rebuilds the entire universe from a fresh master seed (new squads, new season, new
scrims, new coin flips) and plays all four rounds with each policy. Policies see only what the
agent's tools see; none of them touches ``_truth.latent_rating``.
"""

from __future__ import annotations

import argparse
import math
import statistics as stats
from functools import lru_cache
from typing import Callable

import numpy as np

from . import _truth
from . import config as C
from .tournament import Tournament
from .world import build_world, squad, standings

Policy = Callable[[dict, dict], list[tuple[str, float]]]   # (market, ctx) -> [(team, weight)]


# ===================================================================== shared helpers
def _legit(p: dict) -> float:
    return sum(w * p[k] for k, w in C.W_LEGIT.items())


def available_xi(team: str) -> list[dict]:
    out = set(_truth.injury_report(team))
    rows = [p for i, p in enumerate(squad(team)) if i not in out]
    return _truth.select_starters(rows)


def _base_rating(xi: list[dict]) -> float:
    a = float(np.mean([_legit(p) for p in xi]))
    f = float(np.mean([p["prolonged_touch_fouls_per90"] for p in xi]))
    return (a - 55.0) / 9.0 - C.K_FOUL * (f - 1.0) / 2.0


@lru_cache(maxsize=64)
def _informed(team: str, seed: int) -> float:
    """Exactly what a student who read the rules and the news can compute.

    The stat sheet plus the absentee list does most of the work. The scrim block adds a
    small, heavily shrunk form correction: goal margins over ten matches are noisy enough
    that trusting them fully makes the estimate *worse*, which is itself worth a sentence
    in the debrief.
    """
    w = build_world()
    # 1. What every side was worth at FULL strength, from scrim possession retention.
    #    The scrim schedule is a balanced round robin, so a side's mean retention is a
    #    direct read on where it sits relative to the league — no opponent adjustment
    #    needed. Kept linear on purpose: inverting the logit blows the noise up on the
    #    lopsided matches, which is where a bettor least wants extra variance.
    ret = {}
    for t in C.TEAMS:
        rs = [m["retention_home"] if m["home"] == t else m["retention_away"]
              for m in w.scrims if t in (m["home"], m["away"])]
        ret[t] = (float(np.mean(rs)) - 50.0) / C.RETENTION_SLOPE if rs else 0.0
    # 2. The stat sheet, centred the same way, as the second opinion.
    sheet = {t: _base_rating(_truth.select_starters(squad(t))) for t in C.TEAMS}
    mu = float(np.mean(list(sheet.values())))
    full = C.W_SCRIM * ret[team] + (1 - C.W_SCRIM) * (sheet[team] - mu)
    # 3. What the playoff absentees cost, priced off the same stat sheet.
    cost = _base_rating(available_xi(team)) - sheet[team]
    return full + cost


def informed_rating(team: str) -> float:
    return _informed(team, C.MASTER_SEED)


def _logistic(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _mean_strength(team: str) -> float:
    return float(np.mean([p["raw_strength"] for p in available_xi(team)]))


# ===================================================================== policies
def naive_favourite(market: dict, ctx: dict) -> list[tuple[str, float]]:
    best = min(market["selections"], key=lambda s: s["odds"])
    return [(best["team"], 0.10)]


def strength_picker(market: dict, ctx: dict) -> list[tuple[str, float]]:
    a, b = market["team_a"], market["team_b"]
    return [(a if _mean_strength(a) > _mean_strength(b) else b, 0.10)]


def table_only(market: dict, ctx: dict) -> list[tuple[str, float]]:
    rank = {r["team"]: r["rank"] for r in standings()}
    a, b = market["team_a"], market["team_b"]
    return [(a if rank[a] < rank[b] else b, 0.10)]


def sheet_only_rating(team: str) -> float:
    """Rules + news, but no scrim data: the stat sheet of whoever is actually available."""
    return _base_rating(available_xi(team))


def _edges(market: dict, rating=None) -> list[tuple[str, float, float]]:
    rating = rating or informed_rating
    a, b = market["team_a"], market["team_b"]
    p_a = _logistic((rating(a) - rating(b)) / C.RATING_SCALE)
    odds = {s["team"]: s["odds"] for s in market["selections"]}
    return [(a, p_a, p_a * odds[a] - 1.0), (b, 1 - p_a, (1 - p_a) * odds[b] - 1.0)]


def rules_only_rating(team: str) -> float:
    """Read the rulebook, weight the stat sheet correctly — but never open the news, so the
    absentee list is invisible and the squad is assumed intact."""
    return _base_rating(_truth.select_starters(squad(team)))


def rules_only(market: dict, ctx: dict) -> list[tuple[str, float]]:
    picks = [(t, 0.10) for t, _p, e in _edges(market, rules_only_rating) if e > 0.03]
    return picks[:1]


def rules_and_news(market: dict, ctx: dict) -> list[tuple[str, float]]:
    picks = [(t, 0.10) for t, _p, e in _edges(market, sheet_only_rating) if e > 0.03]
    return picks[:1]


def informed(market: dict, ctx: dict) -> list[tuple[str, float]]:
    picks = [(t, 0.10) for t, _p, e in _edges(market) if e > 0.03]
    return picks[:1]


def informed_kelly(market: dict, ctx: dict) -> list[tuple[str, float]]:
    odds = {s["team"]: s["odds"] for s in market["selections"]}
    out = []
    for t, p, e in _edges(market):
        if e <= 0.03:
            continue
        k = e / (odds[t] - 1.0)                 # Kelly fraction
        out.append((t, min(0.5 * k, 0.15)))     # half-Kelly, capped
    return out[:1]


POLICIES: dict[str, Policy] = {
    "naive_favourite": naive_favourite,
    "strength_picker": strength_picker,
    "table_only": table_only,
    "rules_only": rules_only,
    "rules_and_news": rules_and_news,
    "informed": informed,
    "informed_kelly": informed_kelly,
}


# ===================================================================== the harness
def _futures_pick(market: dict, is_informed: bool) -> str:
    if not is_informed:
        return min(market["selections"], key=lambda s: s["odds"])["team"]
    # crude but honest: relative rating -> share of the field -> expected return
    rs = {s["team"]: informed_rating(s["team"]) for s in market["selections"]}
    ex = {t: math.exp(r / C.RATING_SCALE) for t, r in rs.items()}
    tot = sum(ex.values())
    return max(market["selections"], key=lambda s: ex[s["team"]] / tot * s["odds"])["team"]


def play(policy: Policy, *, is_informed: bool = False, futures: bool = True) -> dict:
    t = Tournament()
    staked = won = n_bets = n_hits = 0.0
    while not t.finished:
        for m in t.open_markets():
            if m["kind"] != "match":
                continue
            for team, frac in policy(m, {}):
                stake = round(max(C.MIN_STAKE, t.wallet * frac), 2)
                if stake > t.wallet:
                    continue
                t.place_bet(m["market_id"], team, stake)
                staked += stake
                n_bets += 1
        if futures and t.round == 1:
            ch = t.market("f:champion:r1")
            stake = round(max(C.MIN_STAKE, t.wallet * 0.05), 2)
            if stake <= t.wallet:
                t.place_bet(ch["market_id"], _futures_pick(ch, is_informed), stake)
                staked += stake
                n_bets += 1
        rep = t.advance_round("ADVANCE")
        won += rep.returned
        n_hits += sum(1 for b in rep.settled_bets if b["status"] == "won")
    return {"final": t.wallet, "staked": staked, "returned": won,
            "n_bets": n_bets, "hit_rate": n_hits / max(n_bets, 1),
            "edge": (won - staked) / max(staked, 1e-9)}


def simulate(n: int = 200, base_seed: int = 1_000_000,
             policies: dict[str, Policy] | None = None) -> dict:
    policies = policies or POLICIES
    rows = {k: [] for k in policies}
    for i in range(n):
        _truth.reseed(base_seed + i)
        _informed.cache_clear()
        for name, pol in policies.items():
            rows[name].append(play(pol, is_informed=name.startswith(("informed", "rules_and"))))
    _truth.reseed(C.MASTER_SEED)
    return rows


def _ci(xs: list[float], reps: int = 2000) -> tuple[float, float]:
    g = np.random.default_rng(0)
    arr = np.array(xs)
    boot = arr[g.integers(0, len(arr), size=(reps, len(arr)))].mean(axis=1)
    return float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))


def calibration_report(rows: dict) -> str:
    head = (f"{'policy':<18}{'EV/bet':>9}{'ROI':>9}{'ROI 95% CI':>20}"
            f"{'P(profit)':>11}{'hit rate':>10}")
    lines = [head, "-" * len(head)]
    for name, rs in rows.items():
        roi = [(r["final"] - C.STARTING_BANKROLL) / C.STARTING_BANKROLL for r in rs]
        lo, hi = _ci(roi)
        lines.append(
            f"{name:<18}{stats.mean(r['edge'] for r in rs):>+8.1%}"
            f"{stats.mean(roi):>+9.1%}"
            f"{f'[{lo:+.1%}, {hi:+.1%}]':>20}"
            f"{sum(1 for x in roi if x > 0) / len(roi):>11.0%}"
            f"{stats.mean(r['hit_rate'] for r in rs):>10.0%}")
    return "\n".join(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    a = ap.parse_args()
    print(f"Galactic Premier League — bookmaker calibration over {a.n} universes\n")
    print(calibration_report(simulate(a.n)))


#: Result of ``simulate(150)`` with the shipped parameters. Quoted in the notebook's debrief
#: so participants see the sampling distribution BEFORE running their own single agent.
#: Re-run this module if you touch the bookmaker's biases or the rating weights.
#:     policy -> (EV per bet, mean ROI, 95% CI on ROI, P(profit), hit rate)
CALIBRATION = {
    "naive_favourite": (-0.105, -0.092, (-0.127, -0.056), 0.33, 0.59),
    "strength_picker": (-0.263, -0.219, (-0.265, -0.169), 0.20, 0.38),
    "table_only":      (-0.166, -0.151, (-0.187, -0.115), 0.23, 0.54),
    "rules_only":      (+0.095, +0.105, (+0.057, +0.156), 0.60, 0.55),
    "rules_and_news":  (+0.166, +0.169, (+0.097, +0.247), 0.60, 0.53),
    "informed":        (+0.175, +0.176, (+0.106, +0.251), 0.60, 0.52),
    "informed_kelly":  (+0.254, +0.186, (+0.118, +0.261), 0.64, 0.52),
}

CALIBRATION_LABELS = {
    "naive_favourite": "Back the favourite (odds only)",
    "strength_picker": "Back the physically stronger side",
    "table_only": "Back the higher league finish",
    "rules_only": "Rulebook + stat sheet",
    "rules_and_news": "\u2026 plus the absentee list from the news",
    "informed": "\u2026 plus scrim possession retention",
    "informed_kelly": "\u2026 plus staking proportional to edge",
}

CALIBRATION_NOTE = (
    "150 independent universes, four rounds each. Every policy sees only what the agent's "
    "tools expose. Two things are worth sitting with. First, the ladder: reading the rulebook "
    "is what flips the sign, and the news is worth another seven points on top of it \u2014 "
    "while the two most intuitive shortcuts, backing the stronger side and backing the league "
    "table, are the two worst strategies on the board. Second, the last column: even the best "
    "policy here loses money in more than a third of tournaments. Fourteen matches is a very "
    "small sample for a 17% edge, and a single agent run tells you almost nothing about "
    "whether your prompt was any good."
)
