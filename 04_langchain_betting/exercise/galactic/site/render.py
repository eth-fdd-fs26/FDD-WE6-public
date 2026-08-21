"""Every page on both sites. One shell, one stylesheet, one set of components.

``page_shell`` is the only place an ``<html>`` tag is written. GalacticBets and StarScoop are
the same product with different content, which is why they look like siblings.
"""

from __future__ import annotations

import json as _json
from html import escape
from pathlib import Path

from .. import config as C
from .. import news as news_mod
from ..world import build_world, recent_form, squad, standings
from .bracket import render_bracket

CSS = (Path(__file__).parent / "theme.css").read_text(encoding="utf-8")

BETTING_TABS = [("bracket", "Bracket"), ("matches", "Matches"), ("standings", "Standings"),
                ("teams", "Teams"), ("scrims", "Scrims"), ("rules", "Rules"),
                ("bets", "My Bets")]


# ===================================================================== shell
def state_token(t=None) -> str:
    """A short string that changes exactly when the pages should. Rounds settle, wallets
    move, results appear — the browser polls this and reloads itself when it shifts."""
    if t is None:
        return "static"
    return f"r{t.round}|w{t.wallet:.2f}|m{len(t.results())}|b{len(t.bets())}"


#: Polls ``/__state`` and reloads when it changes. Two and a half seconds is fast enough that
#: settling a round in the launcher visibly advances the site while you are still looking at
#: it, and slow enough to be invisible otherwise.
_LIVE_JS = """<script>
(function(){var cur=%s;setInterval(function(){
  fetch("/__state",{cache:"no-store"}).then(function(r){return r.text();}).then(function(txt){
    if(txt.trim()!==cur){location.reload();}}).catch(function(){});},2500);})();
</script>"""


def page_shell(title: str, body: str, *, brand: str, mark: str, tagline: str,
               tabs: list[tuple[str, str]] | None = None, active: str = "",
               right: str = "", body_class: str = "", state: str | None = None) -> str:
    tabhtml = "".join(
        f'<a href="/{k}" class="{"on" if k == active else ""}">{escape(label)}</a>'
        for k, label in (tabs or []))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title><style>{CSS}</style></head>
<body class="{body_class}">
<div class="topbar">
  <div class="brand"><span class="mark">{mark}</span>
    <span>{escape(brand)}<br><small>{escape(tagline)}</small></span></div>
  <nav class="tabs">{tabhtml}</nav>
  <div class="spacer"></div>
  {right}
</div>
{body}
{_LIVE_JS % _json.dumps(state) if state is not None else ""}
</body></html>"""


def _logo(team: str, big: bool = False) -> str:
    """A club badge: the emblem on a disc ringed in the club's colour.

    The art is a lockup with the club's name under the emblem, which is illegible at this size,
    so ``temp/_build_logos.py`` crops each one to the emblem and squares it off. The image is
    served from ``/logos``; the ring keeps the colour coding the rest of the site relies on.
    """
    return (f'<span class="logo{" lg" if big else ""}" style="--team:{C.TEAM_COLORS[team]}">'
            f'<img src="/logos/{C.TEAM_LOGO[team]}" alt="{escape(team)}" loading="lazy"></span>')


def _team_cell(team: str) -> str:
    return (f'<div class="team">{_logo(team)}<span class="abbr">{C.TEAM_ABBR[team]}</span>'
            f'<span class="nm">{escape(team)}</span></div>')


def _form_chips(team: str) -> str:
    return "".join(f'<span class="chip {r}">{r}</span>' for r in recent_form(team, 5))


def _card(title: str, body: str, sub: str = "", flush: bool = False) -> str:
    return (f'<div class="card"><header>{escape(title)}'
            f'{f"<span class=sub>{escape(sub)}</span>" if sub else ""}</header>'
            f'<div class="body{" flush" if flush else ""}">{body}</div></div>')


# ===================================================================== betting site pages
def _wallet(t) -> str:
    from ..tournament import N_ROUNDS
    label = "Tournament complete" if t.finished else f"Round {t.round} of {N_ROUNDS}"
    return (f'<span class="roundpill">{label}</span>'
            f'<div class="wallet"><span class="lbl">Balance</span>'
            f'<span class="amt">{t.wallet:,.2f} {C.CURRENCY}</span></div>')


def _playoff_record(t, team: str) -> list[dict]:
    """One club's playoff matches so far, oldest first."""
    return [r for r in t.results() if team in (r["team_a"], r["team_b"])]


def _playoff_chips(t, team: str) -> str:
    out = t.eliminated()
    chips = "".join(f'<span class="chip {"W" if r["won_by"] == team else "L"}">'
                    f'{"W" if r["won_by"] == team else "L"}</span>'
                    for r in _playoff_record(t, team))
    if not chips:
        return '<span style="color:var(--dim)">—</span>'
    tail = ('<span class="chip L" style="letter-spacing:.04em">OUT</span>'
            if team in out else "")
    return chips + tail


def _round_banner(t) -> str:
    """What just happened and what is happening now, at the top of the bracket. This is the
    line that makes a settled round impossible to miss."""
    from ..tournament import N_ROUNDS
    if t.finished:
        return (f'<div class="empty" style="text-align:left;padding:12px 16px">'
                f'🏆 <b>{escape(t.champion or "—")}</b> are champions. Every match has been '
                f'played and every market has settled.</div>')
    live = ", ".join(f'{escape(f["team_a"])} v {escape(f["team_b"])}' for f in t.fixtures())
    last = [r for r in t.results() if r["round"] == t.round - 1]
    prev = ""
    if last:
        scores = " · ".join(
            f'{escape(r["won_by"])} beat {escape(r["lost_by"])} '
            f'{escape(r["score_won_first"])}'
            for r in last)
        out = t.eliminated()
        prev = (f'<div style="margin-bottom:8px"><b>Round {t.round - 1} is settled.</b> '
                f'{scores}.'
                + (f' Out of the tournament: {escape(", ".join(out))}.' if out else "")
                + '</div>')
    return (f'<div class="empty" style="text-align:left;padding:12px 16px">{prev}'
            f'<div>▶ <b>Round {t.round} of {N_ROUNDS} is live:</b> {live}</div></div>')


def page_bracket(t) -> str:
    return _card(f"{C.LEAGUE_NAME} {C.SEASON} · Playoffs",
                 _round_banner(t) + render_bracket(t.bracket()),
                 sub=f"Double elimination · 8 teams · 14 matches · round {t.round}",
                 flush=True)


def page_matches(t) -> str:
    open_m = [m for m in t.open_markets() if m["kind"] == "match"]
    fut = [m for m in t.open_markets() if m["kind"] == "champion"]
    out = []
    if open_m:
        rows = []
        for m in open_m:
            picks = "".join(
                f'<div class="pick">{_logo(s["team"])}'
                f'<span class="nm">{escape(s["team"])}</span>'
                f'<span><span class="odds">{s["odds"]:.2f}</span> '
                f'<span class="imp">{s["implied_probability"]:.0%}</span></span></div>'
                for s in m["selections"])
            rows.append(f'<div class="mkt"><div class="head">'
                        f'<span class="id">{m["market_id"]}</span> · '
                        f'{escape(m["round_label"])}</div>'
                        f'<div class="picks">{picks}</div></div>')
        out.append(_card("Open markets", "".join(rows),
                         sub="Close when the round is settled", flush=True))
    for m in fut:
        picks = "".join(
            f'<div class="pick">{_logo(s["team"])}'
            f'<span class="nm">{escape(s["team"])}</span>'
            f'<span><span class="odds">{s["odds"]:.2f}</span> '
            f'<span class="imp">{s["implied_probability"]:.0%}</span></span></div>'
            for s in sorted(m["selections"], key=lambda s: s["odds"]))
        out.append(_card("Outright — who lifts the trophy",
                         f'<div class="mkt"><div class="head">'
                         f'<span class="id">{m["market_id"]}</span> · settles after the '
                         f'grand final</div><div class="picks">{picks}</div></div>',
                         flush=True))
    settled = [x for h in t._state.history for x in h.results]
    if settled:
        rows = "".join(
            f'<tr><td class="rank">{r["match_id"]}</td><td>{_team_cell(r["team_a"])}</td>'
            f'<td class="num r">{r["score"]}</td><td>{_team_cell(r["team_b"])}</td>'
            f'<td class="r">{escape(r["round_label"])}</td></tr>' for r in settled)
        out.append(_card("Results", f"<table><tbody>{rows}</tbody></table>", flush=True))
    return "".join(out) or _card("Markets", '<div class="empty">Nothing open.</div>')


def page_standings(t) -> str:
    rows = []
    for r in standings():
        rows.append(
            f'<tr class="{"seedline" if r["rank"] == 4 else ""}">'
            f'<td class="rank">{r["rank"]}</td><td>{_team_cell(r["team"])}</td>'
            f'<td class="num r">{r["played"]}</td><td class="num r">{r["won"]}</td>'
            f'<td class="num r">{r["drawn"]}</td><td class="num r">{r["lost"]}</td>'
            f'<td class="num r">{r["gf"]}</td><td class="num r">{r["ga"]}</td>'
            f'<td class="num r">{r["gd"]:+d}</td>'
            f'<td class="num r"><b>{r["points"]}</b></td>'
            f'<td class="r">{_form_chips(r["team"])}</td>'
            f'<td class="r">{_playoff_chips(t, r["team"])}</td></tr>')
    head = ("<tr><th></th><th>Team</th><th class=r>P</th><th class=r>W</th><th class=r>D</th>"
            "<th class=r>L</th><th class=r>GF</th><th class=r>GA</th><th class=r>GD</th>"
            "<th class=r>Pts</th><th class=r>Last 5</th><th class=r>Playoffs</th></tr>")
    return _card("Regular season — final table",
                 f"<table><thead>{head}</thead><tbody>{''.join(rows)}</tbody></table>",
                 sub="Every side played the same seven opponents · seeds the playoff "
                     "bracket · the last column is this playoff run, and it moves every round",
                 flush=True)


def _player_rows(team: str) -> str:
    from ..analysis import absentees
    out_names = {p["name"] for p in absentees(team)}
    rows = []
    for p in sorted(squad(team), key=lambda p: p["position"]):
        miss = p["name"] in out_names
        style = ' style="opacity:.42"' if miss else ""
        rows.append(
            f'<tr{style}><td class="rank num">{p["number"]}</td>'
            f'<td class="pname">{escape(p["name"])}{" 🚑" if miss else ""}</td>'
            f'<td style="color:var(--dim)">{p["position"]}</td>'
            f'<td class="num r">{p["ball_control"]:.0f}</td>'
            f'<td class="num r">{p["first_touch"]:.0f}</td>'
            f'<td class="num r">{p["nest_defence"]:.0f}</td>'
            f'<td class="num r">{p["set_piece"]:.0f}</td>'
            f'<td class="num r">{p["prolonged_touch_fouls_per90"]:.2f}</td>'
            f'<td class="num r grp">{p["raw_strength"]:.0f}</td>'
            f'<td class="num r">{p["mass_kg"]:.0f}</td>'
            f'<td class="num r">{p["limb_count"]}</td>'
            f'<td class="num r">{p["top_speed"]:.0f}</td></tr>')
    # Two header rows, exactly as §7 of the rulebook groups them. The League publishes the
    # physical column because member worlds ask for it, not because it predicts anything —
    # but the page does not say so, and neither should it.
    head = ("<tr><th colspan=3></th>"
            "<th colspan=5 style='text-align:center'>Performance record</th>"
            "<th colspan=4 class='grp' style='text-align:center'>"
            "Pre-normalisation physical record</th></tr>"
            "<tr><th>#</th><th>Player</th><th>Position</th><th class=r>Ball ctrl</th>"
            "<th class=r>1st touch</th><th class=r>Nest def</th><th class=r>Set piece</th>"
            "<th class=r>Fouls/90</th><th class='r grp'>Strength</th><th class=r>Mass</th>"
            "<th class=r>Limbs</th><th class=r>Speed</th></tr>")
    return f"<table><thead>{head}</thead><tbody>{''.join(rows)}</tbody></table>"


def page_teams(t, team: str | None = None) -> str:
    team = team or standings()[0]["team"]
    picker = " ".join(
        f'<a href="/teams?team={x.replace(" ", "+")}" class="pick" style="display:inline-flex;'
        f'width:auto;margin:0 6px 8px 0;{"border-color:var(--accent)" if x == team else ""}">'
        f'{_logo(x)}<span class="nm">{escape(x)}</span></a>' for x in C.TEAMS)
    row = next(r for r in standings() if r["team"] == team)
    meta = (f'<div style="display:flex;align-items:center;gap:14px;margin-bottom:14px">'
            f'{_logo(team, big=True)}<div><div style="font-size:18px;font-weight:800">'
            f'{escape(team)}</div><div style="color:var(--muted);font-size:12.5px">'
            f'{escape(C.TEAM_SPECIES[team])} · finished {row["rank"]} on {row["points"]} pts '
            f'· last five {"".join(recent_form(team, 5))}</div></div></div>')
    played = _playoff_record(t, team)
    if played:
        lines = "".join(
            f'<div class="slip"><div class="meta"><div class="t">'
            f'{"Beat" if r["won_by"] == team else "Lost to"} '
            f'{escape(r["lost_by"] if r["won_by"] == team else r["won_by"])} '
            f'{escape(r["score_won_first"])}</div>'
            f'<div class="s">Round {r["round"]} · {escape(r["round_label"])} '
            f'({r["match_id"]})</div></div>'
            f'<span class="badge {"won" if r["won_by"] == team else "lost"}">'
            f'{"won" if r["won_by"] == team else "lost"}</span></div>' for r in played)
        status = ("eliminated" if team in t.eliminated() else "still in")
        run = _card(f"{team} — playoff run", lines,
                    sub=f"{len(played)} played · {status}", flush=True)
    else:
        run = ""
    return (_card("Clubs", picker) + run +
            _card(f"{team} — squad", meta + _player_rows(team),
                  sub="League statistical record · 🚑 unavailable for the playoffs"))


def page_scrims(t) -> str:
    w = build_world()
    rows = "".join(
        f'<tr><td class="rank num">{m["scrim_id"]}</td><td>{_team_cell(m["home"])}</td>'
        f'<td class="num r">{m["home_score"]}–{m["away_score"]}</td>'
        f'<td>{_team_cell(m["away"])}</td>'
        f'<td class="num r">{m["retention_home"]:.0f}%</td>'
        f'<td class="num r">{m["retention_away"]:.0f}%</td></tr>'
        for m in w.scrims)
    head = ("<tr><th>ID</th><th>Home</th><th class=r>Score</th><th>Away</th>"
            "<th class=r>Retention H</th><th class=r>Retention A</th></tr>")
    note = ('<div class="empty" style="text-align:left;padding:0 0 12px">'
            'Closed-doors matches played at full strength in the week before the playoffs. '
            'Not official fixtures. <b>Possession retention</b> is the share of contested '
            'touches a side kept inside the 1.2 s window.</div>')
    return _card("Scrim block", note + f"<table><thead>{head}</thead><tbody>{rows}</tbody>"
                 f"</table>", sub=f"{len(w.scrims)} matches · "
                 f"{C.N_SCRIMS_PER_TEAM} per side")


def page_rules(t) -> str:
    # The same reading view the notebook shows, in the site's own skin — so the page a
    # participant studies in §2.2 is the page they find again here, not a second layout.
    from ..rulebook_view import embedded
    return _card("Laws of Intergalactic Football", embedded(theme="dark"), flush=True)


def page_bets(t) -> str:
    bets = t.bets()
    if not bets:
        return _card("My bets", '<div class="empty">No bets placed yet.</div>', flush=True)
    rows = "".join(
        f'<div class="slip"><div class="meta"><div class="t">{escape(b["selection"])}</div>'
        f'<div class="s">{escape(b["label"])} · round {b["round_placed"]} · '
        f'@ {b["odds"]:.2f}</div></div>'
        f'<span class="amt">{b["stake"]:,.0f}</span>'
        f'<span class="badge {b["status"]}">{b["status"]}</span></div>' for b in bets)
    staked = sum(b["stake"] for b in bets)
    back = sum(b["payout"] for b in bets)
    foot = (f'<div class="slip" style="background:var(--panel-2)"><div class="meta">'
            f'<div class="t">Staked {staked:,.0f} · returned {back:,.0f}</div>'
            f'<div class="s">Balance {t.wallet:,.2f} {C.CURRENCY}</div></div>'
            f'<span class="amt" style="color:'
            f'{"var(--win)" if t.wallet >= C.STARTING_BANKROLL else "var(--loss)"}">'
            f'{t.wallet - C.STARTING_BANKROLL:+,.0f}</span></div>')
    return _card("My bets", rows + foot, flush=True)


PAGES = {"bracket": page_bracket, "matches": page_matches, "standings": page_standings,
         "teams": page_teams, "scrims": page_scrims, "rules": page_rules, "bets": page_bets}


def betting_page(t, path: str = "bracket", query: dict | None = None,
                 state: str | None = None) -> str:
    path = path if path in PAGES else "bracket"
    fn = PAGES[path]
    body = (fn(t, (query or {}).get("team")) if path == "teams" else fn(t))
    return page_shell(f"GalacticBets · {path.title()}",
                      f'<div class="wrap">{body}</div>',
                      brand="GalacticBets.gg", mark="◆",
                      tagline=f"{C.LEAGUE_NAME} {C.SEASON}",
                      tabs=BETTING_TABS, active=path, right=_wallet(t), state=state)


# ===================================================================== the tabloid
def _article_html(a: dict) -> str:
    tags = "".join(f"<span>{escape(x)}</span>" for x in a["tags"])
    paras = "".join(f"<p>{escape(' '.join(blk.split()))}</p>"
                    for blk in a["body"].split("\n\n") if blk.strip())
    byline = (f'<div class="byline">{_logo(a["team"])}<span>{escape(a["team"])}</span></div>'
              if a["team"] else "")
    return (f'<article>{byline}<div class="kicker">{a["id"]} · {a["date"]}</div>'
            f'<h2>{escape(a["headline"])}</h2>'
            f'<div class="stand">{escape(a["standfirst"])}</div>'
            f'<div class="text">{paras}</div>'
            f'<div class="tags">{tags}</div></article>')


def news_page(query: str = "", tournament=None, state: str | None = None) -> str:
    hits = (news_mod.search(query, tournament=tournament) if query.strip()
            else sorted(news_mod.all_articles(tournament), key=lambda a: a["date"],
                        reverse=True))
    heading = (f'{len(hits)} result{"s" * (len(hits) != 1)} for "{escape(query)}"'
               if query.strip() else f"{len(hits)} stories")
    body = f"""<div class="wrap">
  <div class="lede">
    <h1>{news_mod.MASTHEAD}</h1>
    <p>{escape(news_mod.TAGLINE)}</p>
    <form class="searchbar" method="get" action="/">
      <input name="q" value="{escape(query)}" placeholder="Search the archive — try a club name, or 'injury'">
      <button type="submit">Search</button>
    </form>
  </div>
  <div style="color:var(--dim);font-size:12px;margin-bottom:4px">{heading}</div>
  {"".join(_article_html(a) for a in hits) or '<div class="empty">Nothing found.</div>'}
</div>"""
    return page_shell("StarScoop", body, brand=news_mod.MASTHEAD, mark="★",
                      tagline="Galactic Premier League", body_class="scoop", state=state)


# ===================================================================== rulebook
# The rulebook's own layout lives in `galactic.rulebook_view`, which renders it in either
# skin. `page_rules` above asks it for the dark one; the notebook asks for the light one.
