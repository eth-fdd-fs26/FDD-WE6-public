"""The public world: teams, squads, the regular season, the scrim block.

Everything in here is information a fan could get. It is what the website shows and what the
agent's read-only tools return. No function in this module can tell you who wins a playoff
match — that lives behind the gate in ``_truth``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from . import config as C
from . import _truth


# ===================================================================== fixtures
def _round_robin(teams: list[str]) -> list[list[tuple[str, str]]]:
    """Circle method: 8 teams, 7 weeks, every pairing exactly once, everyone plays every week."""
    fixed, rot = teams[0], teams[1:]
    weeks = []
    for w in range(len(teams) - 1):
        ring = rot[w:] + rot[:w]
        pairs = [(fixed, ring[0])] if w % 2 == 0 else [(ring[0], fixed)]
        for i in range(1, len(teams) // 2):
            a, b = ring[i], ring[-i]
            pairs.append((a, b) if (w + i) % 2 == 0 else (b, a))
        weeks.append(pairs)
    return weeks


# ===================================================================== the world
@dataclass
class World:
    seed: int
    teams: list[dict]
    players: dict[str, list[dict]] = field(repr=False)
    season: list[dict] = field(repr=False)
    scrims: list[dict] = field(repr=False)
    standings: list[dict] = field(repr=False)

    def __repr__(self) -> str:
        return (f"World(seed={self.seed}, teams={len(self.teams)}, "
                f"season_matches={len(self.season)}, scrims={len(self.scrims)})")


@lru_cache(maxsize=4)
def _build(seed: int) -> World:
    teams = [{
        "name": t,
        "abbr": C.TEAM_ABBR[t],
        "colour": C.TEAM_COLORS[t],
        "glyph": C.TEAM_GLYPH[t],
        "species": C.TEAM_SPECIES[t],
    } for t in C.TEAMS]

    players = {t: [dict(p) for p in _truth.squad_rows(t)] for t in C.TEAMS}

    season = []
    for w, pairs in enumerate(_round_robin(C.TEAMS), start=1):
        for home, away in pairs:
            hs, as_ = _truth.resolve_season(w, home, away)
            season.append({
                "week": w,
                "date": f"2026-0{2 + (w - 1) // 4}-{(((w - 1) % 4) * 7 + 3):02d}",
                "home": home, "away": away,
                "home_score": hs, "away_score": as_,
                "competition": "Regular season",
            })

    # Same circle method, so every side plays exactly N_SCRIMS_PER_TEAM closed-doors matches
    # against a balanced spread of opponents. Uneven scrim counts would quietly bias any
    # form estimate built from them.
    rounds = _round_robin(C.TEAMS)
    scrims = []
    for block in range(C.N_SCRIMS_PER_TEAM):
        for j, (a, b) in enumerate(rounds[block % len(rounds)]):
            sid = f"S{block * 4 + j:03d}"
            sa, sb, ret = _truth.resolve_scrim(sid, a, b)
            scrims.append({
                "scrim_id": sid, "block": block + 1,
                "date": f"2026-04-{(2 + block):02d}",
                "home": a, "away": b, "home_score": sa, "away_score": sb,
                "retention_home": ret, "retention_away": round(100.0 - ret, 1),
                "competition": "Closed-doors scrim",
            })

    return World(seed=seed, teams=teams, players=players, season=season,
                 scrims=scrims, standings=_standings(season))


def build_world(seed: int | None = None) -> World:
    return _build(C.MASTER_SEED if seed is None else seed)


# ===================================================================== derived views
def _standings(season: list[dict]) -> list[dict]:
    rows = {t: {"team": t, "abbr": C.TEAM_ABBR[t], "played": 0, "won": 0, "drawn": 0,
                "lost": 0, "gf": 0, "ga": 0, "gd": 0, "points": 0} for t in C.TEAMS}
    for m in season:
        h, a = rows[m["home"]], rows[m["away"]]
        hs, as_ = m["home_score"], m["away_score"]
        for r, gf, ga in ((h, hs, as_), (a, as_, hs)):
            r["played"] += 1
            r["gf"] += gf
            r["ga"] += ga
            r["gd"] = r["gf"] - r["ga"]
        if hs > as_:
            h["won"] += 1
            h["points"] += 3
            a["lost"] += 1
        elif as_ > hs:
            a["won"] += 1
            a["points"] += 3
            h["lost"] += 1
        else:
            h["drawn"] += 1
            a["drawn"] += 1
            h["points"] += 1
            a["points"] += 1
    table = sorted(rows.values(), key=lambda r: (-r["points"], -r["gd"], -r["gf"], r["team"]))
    for i, r in enumerate(table, start=1):
        r["rank"] = i
    return table


def standings(world: World | None = None) -> list[dict]:
    return (world or build_world()).standings


def team_row(team: str, world: World | None = None) -> dict:
    return next(r for r in standings(world) if r["team"] == team)


def seeds(world: World | None = None) -> list[str]:
    """Playoff seeding = final league position."""
    return [r["team"] for r in standings(world)]


def matches_of(team: str, world: World | None = None, *, source: str = "season") -> list[dict]:
    w = world or build_world()
    pool = w.season if source == "season" else w.scrims
    return [m for m in pool if team in (m["home"], m["away"])]


def result_letter(m: dict, team: str) -> str:
    gf, ga = ((m["home_score"], m["away_score"]) if m["home"] == team
              else (m["away_score"], m["home_score"]))
    return "W" if gf > ga else ("D" if gf == ga else "L")


def recent_form(team: str, n: int = 4, world: World | None = None) -> list[str]:
    ms = sorted(matches_of(team, world), key=lambda m: m["week"])[-n:]
    return [result_letter(m, team) for m in ms]


def head_to_head(a: str, b: str, world: World | None = None) -> list[dict]:
    w = world or build_world()
    return [m for m in w.season + w.scrims
            if {m["home"], m["away"]} == {a, b}]


def squad(team: str, world: World | None = None) -> list[dict]:
    return list((world or build_world()).players[team])


def select_starters(players: list[dict]) -> list[dict]:
    """Two nestkeepers plus the nine strongest outfielders. Re-exported for the students."""
    return _truth.select_starters(players)
