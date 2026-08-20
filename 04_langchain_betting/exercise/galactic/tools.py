"""The agent's tools — built by a factory, from whichever sub-skills you leave switched on.

The interesting bit is that a switched-off sub-skill is not merely undocumented. Its name is
removed from the tool's ``mode`` enum, so the model physically cannot call it, and every
sentence describing it disappears from the tool's docstring — which is to say, from the
agent's entire prompt surface. Turn off ``player_stats/discipline`` and the agent never learns
that prolonged-touch fouls exist, because nothing in its context mentions them.

Every tool here is a real ``StructuredTool`` with a typed argument schema. That is what lets
the whole family of string-parsing hacks — regex-scraping ``match_id=`` out of a sentence,
splitting on commas, stripping stray quotes — simply not exist.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field, create_model

from . import analysis, config as C, news, rules
from .world import build_world, head_to_head, matches_of, recent_form, standings


# ===================================================================== the registry
@dataclass(frozen=True)
class SubSkill:
    key: str
    label: str
    doc: str                                    # one line, goes into the tool's docstring
    fn: Callable[..., Any] = field(repr=False)
    params: tuple[str, ...] = ()                # which optional args this mode reads


@dataclass(frozen=True)
class ToolSpec:
    name: str
    summary: str
    subskills: tuple[SubSkill, ...]
    blurb: str = ""

    @property
    def keys(self) -> list[str]:
        return [s.key for s in self.subskills]


#: Optional arguments, shared across tools. A tool only declares the ones its enabled
#: sub-skills actually read.
_PARAMS = {
    "team": (str | None, "Full club name, e.g. 'Quasar Queens'."),
    "opponent": (str | None, "A second club name, for head-to-head lookups."),
    "section": (str | None, "Rulebook section number, '1' to '7'."),
    "query": (str | None, "Free-text search terms."),
    "article_id": (str | None, "A StarScoop article id, e.g. 'N01'."),
    "match_id": (str | None, "A playoff match id, e.g. 'UB1' or 'GF'."),
    "selection": (str | None, "The club you want to back."),
    "stake": (float | None, f"Amount to stake, in {C.CURRENCY}."),
}


# ===================================================================== implementations
def _rules_full(t, **_):
    return rules.text()


def _rules_section(t, section=None, **_):
    if not section:
        return {"error": "Give a section number.", "contents": rules.contents()}
    return rules.text(section)


def _table(t, **_):
    return [{k: r[k] for k in ("rank", "team", "played", "won", "drawn", "lost",
                               "gf", "ga", "gd", "points")} for r in standings()]


def _form(t, team=None, **_):
    if not team:
        return {"error": "Which club?"}
    ms = sorted(matches_of(team), key=lambda m: m["week"])
    return {"team": team, "last_five": recent_form(team, 5),
            "regular_season": [{"week": m["week"], "opponent": m["away"] if m["home"] == team
                                else m["home"], "score": f"{m['home_score']}–{m['away_score']}",
                                "home": m["home"] == team} for m in ms],
            # played since the playoffs started — empty until a round has been settled
            "playoff_matches": [
                {"round": r["round"], "match_id": r["match_id"], "stage": r["round_label"],
                 "opponent": r["lost_by"] if r["won_by"] == team else r["won_by"],
                 "score": r["score"], "won": r["won_by"] == team}
                for r in t.results() if team in (r["team_a"], r["team_b"])]}


def _h2h(t, team=None, opponent=None, **_):
    if not team or not opponent:
        return {"error": "Give both clubs."}
    return [{"competition": m["competition"], "home": m["home"], "away": m["away"],
             "score": f"{m['home_score']}–{m['away_score']}"}
            for m in head_to_head(team, opponent)]


def _scrims(t, team=None, **_):
    w = build_world()
    rows = [m for m in w.scrims if not team or team in (m["home"], m["away"])]
    return [{"scrim_id": m["scrim_id"], "home": m["home"], "away": m["away"],
             "score": f"{m['home_score']}–{m['away_score']}",
             "possession_retention_home_pct": m["retention_home"],
             "possession_retention_away_pct": m["retention_away"]} for m in rows]


def _touch_stats(t, team=None, **_):
    if not team:
        return {"error": "Which club?"}
    xi = analysis.available(team)
    return {"team": team, "starting_eleven": [
        {"name": p["name"], "position": p["position"], "ball_control": p["ball_control"],
         "first_touch": p["first_touch"], "nest_defence": p["nest_defence"],
         "set_piece": p["set_piece"]} for p in xi]}


def _discipline(t, team=None, **_):
    if not team:
        return {"error": "Which club?"}
    xi = analysis.available(team)
    return {"team": team, "league_average_per90": 1.0,
            "squad_mean_per90": round(analysis.foul_rate(xi), 2),
            "players": [{"name": p["name"],
                         "prolonged_touch_fouls_per90": p["prolonged_touch_fouls_per90"]}
                        for p in xi]}


def _physical(t, team=None, **_):
    if not team:
        return {"error": "Which club?"}
    xi = analysis.available(team)
    return {"team": team, "species": C.TEAM_SPECIES[team], "note":
            "Pre-normalisation figures, as published by the League.",
            "players": [{"name": p["name"], "raw_strength": p["raw_strength"],
                         "mass_kg": p["mass_kg"], "limb_count": p["limb_count"],
                         "top_speed": p["top_speed"]} for p in xi]}


def _lineup(t, team=None, **_):
    if not team:
        return {"error": "Which club?"}
    return {"team": team,
            "starting_eleven": [p["name"] for p in analysis.available(team)],
            "unavailable": [{"name": p["name"], "position": p["position"]}
                            for p in analysis.absentees(team)]}


def _news_search(t, query=None, **_):
    hits = news.search(query or "", limit=6, tournament=t)
    return [{"id": a["id"], "date": a["date"], "headline": a["headline"],
             "standfirst": a["standfirst"], "team": a["team"]} for a in hits]


def _news_latest(t, **_):
    return [{"id": a["id"], "date": a["date"], "headline": a["headline"],
             "standfirst": a["standfirst"], "team": a["team"]} for a in news.latest(8, tournament=t)]


def _news_read(t, article_id=None, **_):
    if not article_id:
        return {"error": "Give an article id — search first."}
    try:
        a = news.read(article_id, tournament=t)
    except KeyError as e:
        return {"error": str(e)}
    return {k: a[k] for k in ("id", "date", "headline", "standfirst", "body", "team")}


def _playoffs(t, **_):
    """What has already been played, and what is being played now.

    Everything here comes out of the tournament's own history, so it exists only for rounds
    that have been settled. In round 1 it is honestly empty — which is itself worth the
    agent knowing.
    """
    out = t.results()
    return {
        "current_round": t.round,
        "matches_this_round": [
            {"match_id": f["match_id"], "stage": f["round_label"],
             "team_a": f["team_a"], "team_b": f["team_b"]} for f in t.fixtures()],
        "played_so_far": [
            {"round": r["round"], "match_id": r["match_id"], "stage": r["round_label"],
             "beat": r["won_by"], "beaten": r["lost_by"], "score": r["score"],
             "beaten_side_eliminated": r["loser_eliminated"]} for r in out],
        "eliminated": t.eliminated(),
        "note": ("Double elimination: a club is out after two defeats. Nothing has been "
                 "played yet." if not out else
                 "Double elimination: a club is out after two defeats."),
    }


# ------------------------------------------------------------------ the almanac
# Everything below is real, published, verbose and worth nothing. It is here because deciding
# a tool is useless is a skill, and you cannot practise it in a toolbox where every tool is
# useful. Note that it costs the agent context on every call, and costs it a decision on every
# turn: the description alone is part of the prompt whether or not the tool is ever used.
_ANTHEM = (
    "Rise, {abbr}, rise / beyond the seventh moon / your colours in the vacuum / "
    "our voices in the dark / rise, {abbr}, rise / we shall not be home by noon"
)


def _almanac_stadium(t, team=None, **_):
    if not team:
        return {"error": "Which club?"}
    r = C.rng("almanac-stadium", team)
    built = int(r.integers(1968, 2005))
    return {"team": team, "ground": f"The {team.split()[0]} Bowl",
            "founded": built, "capacity": int(r.integers(38_000, 210_000)),
            "roof": ["retractable", "fixed dome", "open to the vacuum shield"][int(r.integers(0, 3))],
            "stands": [{"name": n, "opened": built + int(r.integers(1, 20)),
                        "seats": int(r.integers(4_000, 40_000)),
                        "notes": "Refurbished after the 2019 concourse fire."}
                       for n in ("North Terrace", "South Terrace", "The Gantry",
                                 "Visitors' Arc")],
            "listed_status": "Protected structure, Category II, Member Worlds Heritage Register",
            "note": "Playoff matches are played at Neutral Orbital 7, not here."}


def _almanac_mascot(t, team=None, **_):
    if not team:
        return {"error": "Which club?"}
    r = C.rng("almanac-mascot", team)
    names = ["Boggo", "Sir Fluff", "The Hoop", "Nine-Legs", "Captain Vacuum", "Mildred"]
    return {"team": team, "mascot": names[int(r.integers(0, len(names)))],
            "registered": int(r.integers(1998, 2024)),
            "costume_mass_kg": round(float(r.uniform(12, 90)), 1),
            "banned_from": ["the away concourse", "all lifts", "the referees' tunnel"],
            "history": ("Adopted by supporter ballot, retired twice, reinstated after a "
                        "petition of 40,000 signatures, and the subject of a long-running "
                        "trademark dispute with a breakfast-cereal concern."),
            "note": "Mascots do not take the field and have no bearing on results."}


def _almanac_anthem(t, team=None, **_):
    if not team:
        return {"error": "Which club?"}
    r = C.rng("almanac-anthem", team)
    return {"team": team, "anthem": _ANTHEM.format(abbr=C.TEAM_ABBR[team]),
            "composer": f"H. {chr(65 + int(r.integers(0, 26)))}. Vellamir",
            "first_sung": int(r.integers(1974, 2019)),
            "tempo_bpm": int(r.integers(60, 132)),
            "verses": 4, "verses_usually_sung": 1,
            "note": "Sung before every home fixture. No recorded effect on any scoreline."}


def _almanac_transit(t, team=None, **_):
    r = C.rng("almanac-transit", team or "all")
    return {"venue": "Neutral Orbital 7",
            "shuttles": [{"departs": f"{h:02d}:{int(r.integers(0, 6)) * 10:02d}",
                          "from": f"Gate {chr(65 + i)}", "duration_hours": int(r.integers(4, 40)),
                          "gravity_differential": "within tolerance"}
                         for i, h in enumerate(range(6, 22, 3))],
            "baggage_allowance_kg": 40,
            "note": ("The League applies normalisation protocols on arrival, so travel has "
                     "no recorded effect on player output.")}


def _markets(t, **_):
    return t.open_markets()


def _wallet(t, **_):
    return {"balance": t.wallet, "currency": C.CURRENCY, "round": t.round,
            "bets": t.bets()}


def _place(t, market_id=None, selection=None, stake=None, match_id=None, **_):
    market_id = market_id or (f"m:{match_id.strip().upper()}" if match_id else None)
    if not (market_id and selection and stake):
        return {"error": "Need market_id (or match_id), selection and stake."}
    try:
        return t.place_bet(market_id, selection, stake)
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


# ===================================================================== the specs
TOOL_SPECS: dict[str, ToolSpec] = {
    "read_rules": ToolSpec(
        "read_rules",
        "Read the Laws of Intergalactic Football.",
        blurb="The rulebook. Without it, nothing on the stat sheet can be interpreted.",
        subskills=(
            SubSkill("full", "Whole rulebook",
                     "'full' — return the complete rulebook, all seven sections.",
                     _rules_full),
            SubSkill("section", "One section",
                     "'section' — return one section; pass `section` as '1'..'7'.",
                     _rules_section, ("section",)),
        )),

    "research_team": ToolSpec(
        "research_team",
        "Look up a club's competitive record.",
        blurb="League table, recent results, head-to-heads, and the closed-doors scrim block.",
        subskills=(
            SubSkill("table", "League table",
                     "'table' — the final regular-season table; every side played seven.",
                     _table),
            SubSkill("form", "Recent results",
                     "'form' — one club's seven league fixtures in order; pass `team`.",
                     _form, ("team",)),
            SubSkill("head_to_head", "Head to head",
                     "'head_to_head' — every meeting between two clubs; pass `team` and "
                     "`opponent`.", _h2h, ("team", "opponent")),
            SubSkill("playoffs", "Playoffs so far",
                     "'playoffs' — which playoff matches have already been played and how "
                     "they finished, who is eliminated, and what is being played this "
                     "round. Empty before the first round is settled.", _playoffs),
            SubSkill("scrims", "Scrim block",
                     "'scrims' — closed-doors matches from the week before the playoffs, "
                     "with possession-retention percentages; pass `team` to filter.",
                     _scrims, ("team",)),
        )),

    "player_stats": ToolSpec(
        "player_stats",
        "Read the League's published statistical record for a squad.",
        blurb="The stat sheet, split the way the rulebook splits it.",
        subskills=(
            SubSkill("lineup", "Available eleven",
                     "'lineup' — who starts and who is unavailable; pass `team`.",
                     _lineup, ("team",)),
            SubSkill("touch", "Touch and technique",
                     "'touch' — ball control, first touch, nest defence and set-piece "
                     "ratings for the starting eleven; pass `team`.", _touch_stats,
                     ("team",)),
            SubSkill("discipline", "Discipline",
                     "'discipline' — prolonged-touch fouls per 90 for the starting eleven, "
                     "against the league average; pass `team`.", _discipline, ("team",)),
            SubSkill("physical", "Physical record",
                     "'physical' — pre-normalisation strength, mass, limb count and sprint "
                     "speed; pass `team`.", _physical, ("team",)),
        )),

    "read_news": ToolSpec(
        "read_news",
        "Search and read StarScoop, the league's tabloid.",
        blurb="Where squad availability is announced. Also where the hairstyles live.",
        subskills=(
            SubSkill("search", "Search",
                     "'search' — headlines matching `query`; try a club name or a topic.",
                     _news_search, ("query",)),
            SubSkill("latest", "Latest stories",
                     "'latest' — the eight most recent headlines.", _news_latest),
            SubSkill("read", "Read one story",
                     "'read' — the full text of one article; pass `article_id` from a "
                     "search result.", _news_read, ("article_id",)),
        )),

    "galactic_almanac": ToolSpec(
        "galactic_almanac",
        "The League's official Almanac: grounds, mascots, anthems and transit timetables.",
        blurb="Everything the League publishes that is not about football. Long, accurate, "
              "and worth nothing — which is exactly the kind of tool you will be offered.",
        subskills=(
            SubSkill("stadium", "Ground and stands",
                     "'stadium' — a club's home ground: capacity, roof, every stand and its "
                     "refurbishment history; pass `team`.", _almanac_stadium, ("team",)),
            SubSkill("mascot", "Mascot registry",
                     "'mascot' — the club mascot, its costume mass and its disciplinary "
                     "record; pass `team`.", _almanac_mascot, ("team",)),
            SubSkill("anthem", "Club anthem",
                     "'anthem' — lyrics, composer, tempo and first performance; pass `team`.",
                     _almanac_anthem, ("team",)),
            SubSkill("transit", "Transit timetable",
                     "'transit' — shuttle departures to the playoff venue and baggage "
                     "allowances; pass `team` to filter.", _almanac_transit, ("team",)),
        )),

    "betting": ToolSpec(
        "betting",
        "See the open markets, check the balance, and place bets.",
        blurb="The only tool that spends money.",
        subskills=(
            SubSkill("markets", "Open markets",
                     "'markets' — every open market this round with decimal odds and the "
                     "probability each price implies.", _markets),
            SubSkill("wallet", "Balance and bets",
                     "'wallet' — current balance and every bet placed so far.", _wallet),
            SubSkill("place_bet", "Place a bet",
                     "'place_bet' — stake on a selection; pass `market_id` (or `match_id`), "
                     "`selection` and `stake`. The stake leaves the balance immediately.",
                     _place, ("match_id", "selection", "stake")),
        )),
}

#: The launcher starts with **everything on**, Almanac included. That is not an oversight: an
#: agent handed every tool available to it is the situation you will actually be in, and
#: noticing that one of them cannot help is the exercise.
DEFAULT_ENABLED = {name: set(spec.keys) for name, spec in TOOL_SPECS.items()}


# ===================================================================== the factory
def build_docstring(spec: ToolSpec, enabled: set[str]) -> str:
    modes = [s for s in spec.subskills if s.key in enabled]
    lines = [spec.summary, "", f"Modes available to you ({len(modes)}):"]
    lines += [f"  · {s.doc}" for s in modes]
    reads = sorted({p for s in modes for p in s.params})
    if reads:
        lines += ["", "Optional arguments, depending on the mode: " + ", ".join(reads) + "."]
    return "\n".join(lines)


def _args_model(spec: ToolSpec, enabled: set[str]):
    modes = [s for s in spec.subskills if s.key in enabled]
    fields: dict[str, Any] = {
        "mode": (Literal[tuple(s.key for s in modes)],           # type: ignore[valid-type]
                 Field(description="Which of this tool's modes to use.")),
    }
    for p in sorted({p for s in modes for p in s.params}):
        typ, desc = _PARAMS[p]
        fields[p] = (typ, Field(default=None, description=desc))
    return create_model(f"{spec.name.title().replace('_', '')}Args",
                        __base__=BaseModel, **fields)


def _dispatch(tournament, spec: ToolSpec, enabled: set[str], **kwargs):
    mode = kwargs.pop("mode")
    sub = next((s for s in spec.subskills if s.key == mode), None)
    if sub is None or sub.key not in enabled:
        return {"error": f"mode {mode!r} is not available on {spec.name}. "
                         f"Available: {sorted(enabled)}."}
    return sub.fn(tournament, **kwargs)


def _bind(tournament, spec: ToolSpec, keys: set[str], doc: str):
    # A named closure rather than functools.partial: LangChain introspects the callable it
    # is handed, and a partial object has no __name__ for it to read.
    def run(**kwargs):
        return _dispatch(tournament, spec, keys, **kwargs)
    run.__name__ = spec.name
    run.__doc__ = doc
    return run


def make_tools(tournament, enabled: dict[str, set[str]] | None = None) -> list:
    """Build the agent's toolbox. ``enabled`` maps tool name -> set of sub-skill keys; a
    tool with no enabled sub-skills is not built at all."""
    from langchain_core.tools import StructuredTool

    enabled = DEFAULT_ENABLED if enabled is None else enabled
    out = []
    for name, spec in TOOL_SPECS.items():
        keys = set(enabled.get(name, ()))
        if not keys:
            continue
        doc = build_docstring(spec, keys)
        out.append(StructuredTool.from_function(
            func=_bind(tournament, spec, keys, doc),
            name=name,
            description=doc,
            args_schema=_args_model(spec, keys),
        ))
    return out


def call(tournament, tool_name: str, mode: str, **kwargs):
    """Invoke one sub-skill directly, as the model would, without building a tool.

    The notebook's toolbox bench uses this so that what a participant sees by hand is the
    same code path the agent goes through — dispatch included, error strings included.
    """
    spec = TOOL_SPECS[tool_name]
    return _dispatch(tournament, spec, set(spec.keys), mode=mode, **kwargs)


def describe(enabled: dict[str, set[str]] | None = None) -> str:
    """Plain-text summary of a toolbox — handy for a notebook cell."""
    enabled = DEFAULT_ENABLED if enabled is None else enabled
    parts = []
    for name, spec in TOOL_SPECS.items():
        keys = set(enabled.get(name, ()))
        if not keys:
            parts.append(f"✗ {name} — off")
            continue
        parts.append(f"✓ {name}\n" + "\n".join(
            f"    {'✓' if s.key in keys else '✗'} {s.key:12s} {s.label}"
            for s in spec.subskills))
    return "\n".join(parts)
