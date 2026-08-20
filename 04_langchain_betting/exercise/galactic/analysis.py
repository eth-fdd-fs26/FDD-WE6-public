"""Helpers for the tool you are about to write.

Everything tedious is done for you here: pulling a squad, working out who is actually
available, averaging a stat over the eleven who will start, turning decimal odds into a
probability. What is *not* done for you is the part the rulebook decides — which columns of
the stat sheet belong in a rating at all, and which way a foul count should push it.

    from galactic.analysis import available, legit_index, foul_rate, logistic, ...
"""

from __future__ import annotations

import contextlib
import math

import numpy as np

from . import _truth
from . import config as C
from .world import build_world, squad

#: Rating points per logit. Two teams one full point apart win about 61% of the time.
RATING_SCALE = C.RATING_SCALE

#: The weights §7 of the rulebook implies, once you have read §3 and §4.
LEGIT_WEIGHTS = dict(C.W_LEGIT)


# ===================================================================== squads
def absentees(team: str) -> list[dict]:
    """The players who will NOT take the field: injured, suspended, or otherwise out.

    This is the same list the news site reports, in structured form.
    """
    rows = squad(team)
    return [rows[i] for i in _truth.injury_report(team)]


def available(team: str) -> list[dict]:
    """The eleven who will actually start: two nestkeepers plus the nine strongest
    outfielders, with anyone on the absentee list removed and a substitute promoted."""
    out = set(_truth.injury_report(team))
    return _truth.select_starters([p for i, p in enumerate(squad(team)) if i not in out])


def full_strength(team: str) -> list[dict]:
    """The eleven who would have started if nobody were missing."""
    return _truth.select_starters(squad(team))


# ===================================================================== stat aggregation
def legit_index(players: list[dict]) -> float:
    """The rulebook-weighted average of the attributes the protocols do NOT normalise away.

    Roughly 35 for the weakest side in the league and 75 for the strongest.
    """
    return float(np.mean([sum(w * p[k] for k, w in LEGIT_WEIGHTS.items()) for p in players]))


def foul_rate(players: list[dict]) -> float:
    """Mean prolonged-touch fouls per 90. League average is about 1.0."""
    return float(np.mean([p["prolonged_touch_fouls_per90"] for p in players]))


def mean_stat(players: list[dict], stat: str) -> float:
    return float(np.mean([p[stat] for p in players]))


# ===================================================================== the scrim channel
def _sheet(players: list[dict]) -> float:
    # Deliberately private: it is the formula you are about to write, and the scrim
    # correction below needs it to be on the same scale. Calling it from your tool would be
    # cheating, though admittedly efficient cheating.
    return (legit_index(players) - 55.0) / 9.0 - C.K_FOUL * (foul_rate(players) - 1.0) / 2.0


def scrim_adjustment(team: str) -> float:
    """How much better (or worse) the scrim block says a side is than its stat sheet does.

    Provided rather than left as an exercise, because the derivation is a detour. The idea:
    the scrim schedule is a balanced round robin, so a side's mean possession retention says
    where it sits relative to the league without any opponent adjustment. Retention comes off
    hundreds of touches, whereas a scrim scoreline is four or five Poisson goals — which is
    why this uses the possession figure and ignores who won.

    Returns a correction in rating points, already shrunk toward the stat sheet.
    """
    w = build_world()
    ret, sheet = {}, {}
    for t in C.TEAMS:
        rs = [m["retention_home"] if m["home"] == t else m["retention_away"]
              for m in w.scrims if t in (m["home"], m["away"])]
        ret[t] = (float(np.mean(rs)) - 50.0) / C.RETENTION_SLOPE if rs else 0.0
        sheet[t] = _sheet(full_strength(t))
    mu = float(np.mean(list(sheet.values())))
    return C.W_SCRIM * (ret[team] - (sheet[team] - mu))

# ===================================================================== maths
def logistic(x: float) -> float:
    """1 / (1 + e^-x). Turns a rating *difference* into a win probability."""
    return 1.0 / (1.0 + math.exp(-x))


def implied_probability(decimal_odds: float) -> float:
    """What the bookmaker's price says the chance is. Note these sum to more than 1 across a
    market — the surplus is the margin."""
    return 1.0 / float(decimal_odds)


# ===================================================================== market access
def market_for(match_id: str, tournament) -> dict:
    """The open market on one playoff match, with both prices."""
    return tournament.market(f"m:{match_id.strip().upper()}")


def odds_of(market: dict, team: str) -> float:
    for s in market["selections"]:
        if s["team"] == team:
            return s["odds"]
    raise KeyError(f"{team!r} is not in this market: "
                   f"{[s['team'] for s in market['selections']]}")


# ===================================================================== testing support
@contextlib.contextmanager
def perturbed(team: str, stat: str, delta: float):
    """Temporarily shift one stat for every player at a club.

    Used by the self-check to ask a question your formula must answer correctly: does it
    react to attributes the normalisation protocols erase?
    """
    players = build_world().players[team]
    original = [p[stat] for p in players]
    try:
        for p in players:
            p[stat] = p[stat] + delta
        yield
    finally:
        for p, v in zip(players, original):
            p[stat] = v
