"""The hidden half of the world. Do not read this file — it is the answer key's engine.

Nothing here is *stored*. There is no dict of winners anywhere in this package; a result is
computed on demand from ``(MASTER_SEED, match_id, salt)`` the moment a round is settled, and
recomputing it a thousand times gives the same answer. That is what makes the tournament
deterministic without ever putting an ``actual_winner`` field next to the odds.

The public functions here are gated: they take a module-private sentinel ``_k``. Calling
``_truth.resolve("UB1", ...)`` from a notebook cell raises ``PermissionError`` rather than
handing over the answer. A determined student can of course read this source — that is fine,
and honestly a bit of a compliment. What must not happen is a *casual* ``print()`` spoiling
the exercise for everyone, which is exactly what the previous edition allowed.

Ungated on purpose: ``injury_report`` and ``coach_report``. Those are published — they are
what the news site reports. Discovering them is the agent's job, not a secret.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from . import config as C

_ACCESS = object()          # the key. Held by this module and its trusted callers.


def _gate(k) -> None:
    if k is not _ACCESS:
        raise PermissionError(
            "galactic._truth is spoiler-protected. The information you want is on the "
            "betting site, in the rulebook, or in the news — go and get it."
        )


def __dir__():              # keeps %whos and tab-completion from advertising the internals
    return []


# ===================================================================== the latent scale
# Team quality is authored, not drawn, so the teaching traps are exact rather than lucky.
#   q      hidden school quality, drives every attribute the RULES make relevant
#   form   late-season momentum: visible in scrims and recent results, muted in the table
#   pull   raw-strength percentile, deliberately UNcorrelated with q (the normalisation trap)
#   coach  a mid-season coaching change, reported in the news
_PROFILE = {
    #                          q      form   pull   coach
    "Stellar Strikers":     ( 1.30,  0.10,  0.55,   0),
    "Quasar Queens":        ( 0.95,  0.35,  0.05,   0),   # TRAP: elite, feeblest squad in the league
    "Cosmic Crusaders":     ( 0.45, -0.70,  0.60,   0),   # flattered by the table, fading badly
    "Andromeda Asteroids":  ( 0.15,  0.20,  0.45,   0),
    "Nebula Nomads":        (-0.10,  0.05,  0.30,   0),
    "Meteor Mavericks":     (-0.45,  0.85,  0.35,  +1),   # late surge + new coach, table hides both
    "Galaxy Giants":        (-0.95, -0.15,  0.98,   0),   # TRAP: strongest bodies, poorest hands
    "Pulsar Pirates":       (-1.35,  0.15,  0.70,   0),
}

_POSITIONS = ["Nestkeeper"] * 3 + ["Anchor"] * 4 + ["Weaver"] * 5 + ["Striker"] * 4
_SUBS = {2, 6, 11, 14, 15}      # spread across the positions, so every line has cover

_FIRST = ["Vex", "Zor", "Kaal", "Nyx", "Ryn", "Thal", "Orr", "Sil", "Bex", "Quo",
          "Mirr", "Dax", "Vey", "Lorn", "Ghal", "Suun", "Pax", "Ilo", "Krem", "Tave",
          "Jesk", "Aurin", "Rho", "Wend"]

#: Surnames, one pool per club, in the naming style of that club's species.
#:
#: The pools are disjoint, and that is the point rather than the flavour. The previous
#: version indexed a single shared list by ``len(team)`` — so the three clubs whose names
#: happen to be sixteen characters long fielded literally the same sixteen players, and 128
#: footballers collapsed into 52 distinct names. A participant reading the news, the lineup
#: tool and the stat sheet together would have found the same man playing for three clubs.
_SURNAMES: dict[str, list[str]] = {
    # Rock-silicate collectives — mineralogy
    "Andromeda Asteroids": [
        "Basalt", "Feldspar", "Olivine", "Pyroxene", "Quartzvein", "Schistfall",
        "Slatewright", "Tuffstone", "Obsidia", "Chert", "Gneiss", "Magnetite",
        "Corundum", "Serpentine", "Anorthite", "Graniteer"],
    # Gas-phase drifters — weather and diffuse light
    "Nebula Nomads": [
        "Driftwake", "Vaporain", "Mistral", "Aurorae", "Cirrus", "Haloway",
        "Plumefall", "Wisplight", "Zephyrine", "Nimbus", "Coronal", "Sootheveil",
        "Lumengas", "Stratus", "Exhale", "Thermal"],
    # Exo-armoured bipeds — fortification and plate
    "Cosmic Crusaders": [
        "Bulwark", "Gauntlet", "Rampart", "Visorne", "Pauldron", "Greaves",
        "Cuirass", "Bastion", "Aegis", "Vambrace", "Palisade", "Hauberk",
        "Mantlet", "Portcullis", "Barbican", "Ironward"],
    # Plasma-core humanoids — heat and light
    "Stellar Strikers": [
        "Solvane", "Flarewick", "Coronado", "Emberlin", "Ignis", "Radiant",
        "Pyrelight", "Helion", "Arclight", "Blazeborn", "Fusor", "Photon",
        "Kindle", "Novaris", "Sunder", "Caldera"],
    # Low-gravity giants — height, distance and weight
    "Galaxy Giants": [
        "Tallwood", "Longstride", "Highfell", "Vastrum", "Loomridge", "Bergstand",
        "Colossus", "Broadbarrow", "Toweren", "Longbarrow", "Deepkeel", "Farshoulder",
        "Steadfast", "Girthwold", "Overhang", "Grandspan"],
    # Hexapod sprinters — speed and legs
    "Meteor Mavericks": [
        "Quicksix", "Dashiel", "Sprintwell", "Skitterly", "Fleetfoot", "Blurwing",
        "Hastings", "Racemore", "Swiftlock", "Scurry", "Bolter", "Tarsal",
        "Chitinix", "Zipwarden", "Velocet", "Sixstep"],
    # Tentacled cephaloids — reef, ink and coil
    "Quasar Queens": [
        "Coilspine", "Inkwell", "Tendril", "Sucklow", "Mantlebrook", "Siphonel",
        "Reefgrasp", "Curlwater", "Octavane", "Nautilan", "Wraithcoil", "Brinehold",
        "Lurewell", "Glideark", "Tidefold", "Krakenly"],
    # Amphibious quadrupeds — marsh and tide
    "Pulsar Pirates": [
        "Saltmarrow", "Brackwater", "Tidebones", "Mudlark", "Fenwick", "Reedhollow",
        "Bogstrider", "Silthook", "Rivermaw", "Croakley", "Spindrift", "Wadewell",
        "Slipbank", "Gillmore", "Anchorpond", "Marshall"],
}


def _player_name(team: str, i: int) -> str:
    """A name for player ``i`` of ``team``. Unique league-wide, by construction.

    The surname pool is the club's own, so two clubs cannot collide however the strides
    fall; the strides are coprime with their pool lengths, so squad-mates cannot either.
    """
    surnames = _SURNAMES[team]
    t = C.TEAMS.index(team)
    return (f"{_FIRST[(i * 7 + 5 * t) % len(_FIRST)]} "
            f"{surnames[(i * 5) % len(surnames)]}")


# ===================================================================== players
@lru_cache(maxsize=16)
def _squad_rows(team: str, seed: int) -> tuple[dict, ...]:
    """Every player of one team, as plain dicts. Public data — this is on the website."""
    q, _form, pull, _coach = _PROFILE[team]
    numbers = list(C.rng("numbers", team).choice(range(1, 60), size=C.N_PLAYERS,
                                                 replace=False))
    rows = []
    for i in range(C.N_PLAYERS):
        g = C.rng("player", team, i)
        pos = _POSITIONS[i]
        # The five squad players are a real step down. That is what makes an injury cost
        # something, and it is recoverable entirely from the public stat sheet.
        qi = q - (1.15 if i in _SUBS else 0.0)

        ball_control = float(np.clip(60 + 9 * qi + g.normal(0, 6.5), 20, 99))
        first_touch = float(np.clip(60 + 8 * qi + g.normal(0, 7.5), 20, 99))
        nest_defence = float(np.clip(58 + 7 * qi + g.normal(0, 8.5)
                                     + (18 if pos == "Nestkeeper" else 0), 20, 99))
        set_piece = float(np.clip(55 + 5 * qi + g.normal(0, 10.5), 20, 99))
        fouls = float(np.clip(1.05 - 0.28 * qi + g.normal(0, 0.42), 0.0, 3.2))

        # --- the normalised attributes. Their stream depends on `pull`, never on `q`.
        raw_strength = float(np.clip(40 + 58 * pull + g.normal(0, 7), 20, 99))
        mass_kg = float(np.clip(80 + 250 * pull + g.normal(0, 22), 55, 420))
        limb_count = int(g.choice([2, 2, 2, 4, 6]))
        top_speed = float(np.clip(50 + 40 * pull + g.normal(0, 9), 30, 99))

        rows.append({
            "name": _player_name(team, i),
            "team": team,
            "number": int(numbers[i]),
            "position": pos,
            "ball_control": round(ball_control, 1),
            "first_touch": round(first_touch, 1),
            "nest_defence": round(nest_defence, 1),
            "set_piece": round(set_piece, 1),
            "prolonged_touch_fouls_per90": round(fouls, 2),
            "raw_strength": round(raw_strength, 1),
            "mass_kg": round(mass_kg, 1),
            "limb_count": limb_count,
            "top_speed": round(top_speed, 1),
            "appearances": int(g.integers(3, 8)),
        })
    return tuple(rows)


def squad_rows(team: str) -> tuple[dict, ...]:
    """Ungated: the stat sheet is published on the site."""
    return _squad_rows(team, C.MASTER_SEED)


# ===================================================================== disclosed shocks
# How many first-choice players each side has lost, and why. Authored rather than drawn, so
# the debrief can point at each edge and name its cause.
#   n > 0 : the n most important outfielders are out
#   n < 0 : |n| squad players are out — the news reports it, and it changes nothing
_ABSENCES = {
    "Stellar Strikers": (3, "injury"),      # the tournament's biggest story, and its biggest edge
    "Cosmic Crusaders": (1, "injury"),
    "Pulsar Pirates": (2, "suspension"),    # repeated prolonged touch, per §5 of the rules
    "Nebula Nomads": (-2, "injury"),        # squad players only: loud headline, zero effect
}


def injury_report(team: str) -> tuple[int, ...]:
    """Squad-sheet indices ruled out of the playoffs. Ungated — this is published in the news."""
    n, _reason = _ABSENCES.get(team, (0, ""))
    if n == 0:
        return ()
    rows = list(squad_rows(team))
    field = [i for i, p in enumerate(rows) if p["position"] != "Nestkeeper"]
    ranked = sorted(field, key=lambda i: _legit(rows[i]), reverse=True)
    return tuple(sorted(ranked[:n] if n > 0 else ranked[n:]))


def absence_reason(team: str) -> str:
    return _ABSENCES.get(team, (0, ""))[1]


def coach_report(team: str) -> int:
    """-1, 0 or +1. A coaching change, published in the news."""
    return _PROFILE[team][3]


# ===================================================================== ratings
def _legit(p: dict) -> float:
    return sum(w * p[k] for k, w in C.W_LEGIT.items())


def select_starters(players: list[dict]) -> list[dict]:
    """Exactly 2 nestkeepers plus the 9 strongest outfielders, by the rules' own weighting."""
    keepers = sorted((p for p in players if p["position"] == "Nestkeeper"),
                     key=_legit, reverse=True)[:2]
    field = sorted((p for p in players if p["position"] != "Nestkeeper"),
                   key=_legit, reverse=True)[:9]
    return keepers + field


@lru_cache(maxsize=64)
def _metrics(team: str, apply_injuries: bool, seed: int) -> tuple[float, float]:
    rows = list(squad_rows(team))
    if apply_injuries:
        out = set(injury_report(team))
        rows = [p for i, p in enumerate(rows) if i not in out]
    xi = select_starters(rows)
    a = float(np.mean([_legit(p) for p in xi]))
    f = float(np.mean([p["prolonged_touch_fouls_per90"] for p in xi]))
    return a, f


def _squad_metrics(team: str, *, apply_injuries: bool) -> tuple[float, float]:
    return _metrics(team, apply_injuries, C.MASTER_SEED)


def _rating_from(a: float, f: float, form: float, coach: int) -> float:
    return ((a - 55.0) / 9.0
            - C.K_FOUL * (f - 1.0) / 2.0
            + C.K_FORM * form
            + C.K_COACH * coach)


@lru_cache(maxsize=64)
def _latent(team: str, seed: int) -> float:
    a, f = _metrics(team, True, seed)
    _q, form, _pull, coach = _PROFILE[team]
    return _rating_from(a, f, form, coach)


def latent_rating(team: str, *, _k=None) -> float:
    """The number every playoff coin-flip is drawn from."""
    _gate(_k)
    return _latent(team, C.MASTER_SEED)


def preseason_rating(team: str, week: int) -> float:
    """Ungated: the regular season is over and its results are public.

    Uses the *full* squad (the injuries happened after the season) and a form term that ramps
    up over the seven weeks — which is precisely why the final table under-rates a late surge.
    """
    a, f = _squad_metrics(team, apply_injuries=False)
    _q, form, _pull, coach = _PROFILE[team]
    return _rating_from(a, f, form * (week / 7.0), coach if week >= 5 else 0)


def scrim_rating(team: str) -> float:
    """Ungated: scrims are last week's form, before the injury news. Noise added per scrim."""
    a, f = _squad_metrics(team, apply_injuries=False)
    _q, form, _pull, coach = _PROFILE[team]
    return _rating_from(a, f, form, coach)


# ===================================================================== the bookmaker
def _mean_strength(team: str) -> float:
    xi = select_starters(list(squad_rows(team)))
    return float(np.mean([p["raw_strength"] for p in xi]))


@lru_cache(maxsize=4)
def _z_tables(seed: int) -> dict:
    strength = np.array([_mean_strength(t) for t in C.TEAMS])
    truth = np.array([_latent(t, seed) for t in C.TEAMS])
    from .world import build_world           # local import: world is the public layer
    table = build_world().standings
    pts = np.array([next(r["points"] for r in table if r["team"] == t) for t in C.TEAMS])

    def z(v):
        return (v - v.mean()) / (v.std() + 1e-9)

    return {t: (z(strength)[i], z(pts)[i], z(truth)[i]) for i, t in enumerate(C.TEAMS)}


@lru_cache(maxsize=64)
def _book(team: str, seed: int) -> float:
    a_hurt, f = _metrics(team, True, seed)
    a_full, _ = _metrics(team, False, seed)
    # (1) the book prices only BOOK_INJURY_BETA of the news it has seen
    a_book = C.BOOK_INJURY_BETA * a_hurt + (1 - C.BOOK_INJURY_BETA) * a_full
    _q, form, _pull, coach = _PROFILE[team]
    r = _rating_from(a_book, f, form, coach)

    z_strength, z_pts, z_truth = _z_tables(seed)[team]
    r += C.BOOK_STRENGTH_GAMMA * z_strength      # (2) over-weights the normalised-away trait
    r += C.BOOK_TABLE_DELTA * (z_pts - z_truth)  # (3) anchors on the table, ignores the scrims
    return r


def book_rating(team: str, *, _k=None) -> float:
    """What the market thinks — the truth, degraded in three specific, defensible ways."""
    _gate(_k)
    return _book(team, C.MASTER_SEED)


def p_win(a: str, b: str, *, book: bool = False, neutral: bool = True, _k=None) -> float:
    _gate(_k)
    f = (lambda t: book_rating(t, _k=_ACCESS)) if book else (lambda t: latent_rating(t, _k=_ACCESS))
    d = (f(a) - f(b)) / C.RATING_SCALE + (0.0 if neutral else C.HOME_EDGE)
    lo, hi = C.BOOK_P_CLAMP if book else C.P_CLAMP
    return float(np.clip(1.0 / (1.0 + math.exp(-d)), lo, hi))


def match_odds(a: str, b: str, *, _k=None) -> dict:
    """Decimal odds, rounded. Implied probabilities are re-derived FROM the rounded odds, so
    the number on the site and the number in the wallet always reconcile."""
    _gate(_k)
    p = p_win(a, b, book=True, _k=_ACCESS)
    oa = round((1.0 / p) / (1.0 + C.VIG), 2)
    ob = round((1.0 / (1.0 - p)) / (1.0 + C.VIG), 2)
    return {a: max(oa, 1.01), b: max(ob, 1.01)}


# ===================================================================== resolution
@dataclass(frozen=True)
class MatchResult:
    match_id: str
    team_a: str
    team_b: str
    winner: str
    score_a: int
    score_b: int

    @property
    def loser(self) -> str:
        return self.team_b if self.winner == self.team_a else self.team_a


def _scoreline(g: np.random.Generator, d: float, a_wins: bool, allow_draw: bool) -> tuple[int, int]:
    lam_a = math.exp(C.GOALS_BASE + C.GOALS_SLOPE * d / 2.0)
    lam_b = math.exp(C.GOALS_BASE - C.GOALS_SLOPE * d / 2.0)
    for _ in range(60):
        sa, sb = int(g.poisson(lam_a)), int(g.poisson(lam_b))
        if allow_draw:
            return sa, sb
        if sa != sb and (sa > sb) == a_wins:
            return sa, sb
    return (2, 1) if a_wins else (1, 2)


def resolve(match_id: str, a: str, b: str, *, salt: int = 0, _k=None) -> MatchResult:
    """The one function that decides anything. Pure in ``(seed, match_id, salt)``."""
    _gate(_k)
    g = C.rng("playoff", match_id, salt)
    p = p_win(a, b, _k=_ACCESS)
    a_wins = bool(g.random() < p)
    d = (latent_rating(a, _k=_ACCESS) - latent_rating(b, _k=_ACCESS)) / C.RATING_SCALE
    sa, sb = _scoreline(g, d, a_wins, allow_draw=False)
    return MatchResult(match_id, a, b, a if a_wins else b, sa, sb)


def resolve_season(week: int, home: str, away: str) -> tuple[int, int]:
    """Ungated: last season's results are printed on the website."""
    g = C.rng("season", week, home, away)
    d = (preseason_rating(home, week) - preseason_rating(away, week)) / C.RATING_SCALE + C.HOME_EDGE
    p = float(np.clip(1.0 / (1.0 + math.exp(-d)), *C.P_CLAMP))
    return _scoreline(g, d, bool(g.random() < p), allow_draw=True)


def resolve_scrim(scrim_id: str, a: str, b: str) -> tuple[int, int, float]:
    """Ungated. Scrims are played at full strength, before the playoff absentee list.

    Returns the scoreline AND possession retention — the share of contested touches the home
    side kept inside the 1.2 s window. The scoreline is a handful of Poisson goals and is
    correspondingly noisy; retention aggregates hundreds of touches and is not. Which of the
    two an analyst leans on matters more than most people expect.
    """
    g = C.rng("scrim", scrim_id)
    ra = scrim_rating(a) + g.normal(0, C.SCRIM_NOISE)
    rb = scrim_rating(b) + g.normal(0, C.SCRIM_NOISE)
    d = (ra - rb) / C.RATING_SCALE
    p = float(np.clip(1.0 / (1.0 + math.exp(-d)), *C.P_CLAMP))
    sa, sb = _scoreline(g, d, bool(g.random() < p), allow_draw=True)
    d_true = (scrim_rating(a) - scrim_rating(b)) / C.RATING_SCALE
    ret = 100.0 / (1.0 + math.exp(-d_true)) + g.normal(0, C.RETENTION_NOISE)
    return sa, sb, round(float(np.clip(ret, 18.0, 82.0)), 1)


# ===================================================================== futures pricing
def champion_probs(bracket_state, *, book: bool = True, sims: int | None = None, _k=None) -> dict:
    """Monte-Carlo the rest of the bracket and count trophies.

    ``bracket_state`` is the tournament's slot table; we only read team placements, never
    results, so this is safe to call at any point in the tournament.
    """
    _gate(_k)
    from .tournament import simulate_remainder      # local import breaks the cycle
    sims = sims or C.OUTRIGHT_SIMS
    rate = {t: 0 for t in C.TEAMS}
    for i in range(sims):
        champ = simulate_remainder(bracket_state, C.rng("outright", book, i),
                                   book=book, _k=_ACCESS)
        rate[champ] += 1
    return {t: n / sims for t, n in rate.items() if n}


def reseed(master_seed: int) -> None:
    """Move to a different universe. Used only by ``sim.py``; never during a lesson."""
    from . import world
    C.reseed(master_seed)
    for f in (_squad_rows, _metrics, _latent, _book, _z_tables, world._build):
        f.cache_clear()


def champion_odds(bracket_state, *, _k=None) -> dict:
    _gate(_k)
    probs = champion_probs(bracket_state, book=True, _k=_ACCESS)
    vig = 1.0 + C.VIG * C.VIG_FUTURES_MULT
    return {t: min(max(round((1.0 / max(p, 1e-4)) / vig, 2), 1.01), C.MAX_FUTURES_ODDS)
            for t, p in probs.items()}
