"""The double-elimination bracket, laid out from the graph rather than typed out by hand.

Positions are computed: a match's column comes from its round, and its row is the midpoint of
whichever of its two feeder matches sit in the same band. Add a round to ``DE8_GRAPH`` and the
picture redraws itself. Empty slots print where their occupant will come from ("Winner UB3",
"Loser UB6") instead of a row of identical TBDs, so the wiring is legible before a ball is
kicked.
"""

from __future__ import annotations

from html import escape

from .. import config as C
from ..tournament import DE8_GRAPH, GRAPH

# Keep SLOT comfortably above CARD_H or first-round cards overlap each other.
CARD_W = 200
COL_GAP = 44
CARD_H = 84
SLOT = 102           # vertical pitch of one first-round match
BAND_GAP = 58
TOP_PAD = 26


# ===================================================================== layout
def _layout() -> tuple[dict, dict, float]:
    """{match_id: (x, y)}, {band: (label_y, columns)}, total height."""
    pos: dict[str, tuple[int, float]] = {}
    bands: dict[str, dict] = {}
    y_cursor = 0.0

    for band in ("UB", "LB"):
        nodes = [n for n in DE8_GRAPH if n[1] == band]
        cols: dict[int, list] = {}
        for n in nodes:
            cols.setdefault(n[3], []).append(n)

        rows: dict[str, float] = {}
        for col in sorted(cols):
            for i, n in enumerate(cols[col]):
                mid, sa, sb = n[0], n[4], n[5]
                feeders = [s[1] for s in (sa, sb)
                           if s[0] in ("win", "lose") and s[1] in rows]
                rows[mid] = (sum(rows[f] for f in feeders) / len(feeders)
                             if feeders else float(i))
        height = (max(rows.values()) + 1) * SLOT
        for mid, r in rows.items():
            col = GRAPH[mid][3]
            pos[mid] = (col * (CARD_W + COL_GAP), y_cursor + r * SLOT)
        bands[band] = {
            "label_y": y_cursor,
            "columns": {col: cols[col][0][2] for col in sorted(cols)},
        }
        y_cursor += height + BAND_GAP

    total = y_cursor - BAND_GAP

    # The grand final belongs to neither band: it sits one column further right, vertically
    # centred on the whole figure.
    last_col = max(GRAPH[m][3] for m in pos)
    gy = (total - CARD_H) / 2
    pos["GF"] = ((last_col + 1) * (CARD_W + COL_GAP), gy)
    bands["GF"] = {"label_y": gy - 24, "columns": {last_col + 1: "Grand Final"}}
    return pos, bands, total + TOP_PAD


# ===================================================================== drawing
def _logo(team: str | None) -> str:
    if not team:
        return '<span class="logo" style="background:#262a35"></span>'
    return (f'<span class="logo" style="background:{C.TEAM_COLORS[team]}">'
            f'{C.TEAM_GLYPH[team]}</span>')


def _side(slot: dict, side: str) -> str:
    team = slot[f"team_{side}"]
    score = slot[f"score_{side}"]
    if team is None:
        return (f'<div class="row tbd"><span class="logo" style="background:#20242e"></span>'
                f'<span class="nm">{escape(slot[f"source_{side}"])}</span></div>')
    cls = ""
    if slot["winner"]:
        cls = " won" if slot["winner"] == team else " lost"
    return (f'<div class="row{cls}">{_logo(team)}'
            f'<span class="nm">{escape(team)}</span>'
            f'<span class="sc">{"–" if score is None else score}</span></div>')


def _connectors(pos: dict) -> str:
    """Elbows between a match and its feeders, but only inside the same band — a line from
    the upper bracket down to the lower would cross half the figure to say what the slot
    label already says."""
    paths = []
    for mid, _b, _lab, _c, sa, sb, _w, _l in DE8_GRAPH:
        if mid not in pos:
            continue
        x2, y2 = pos[mid]
        for src in (sa, sb):
            if src[0] == "seed" or src[1] not in pos:
                continue
            if GRAPH[src[1]][1] != GRAPH[mid][1]:
                continue
            x1, y1 = pos[src[1]]
            sx, sy = x1 + CARD_W, y1 + CARD_H / 2 + TOP_PAD
            ex, ey = x2, y2 + CARD_H / 2 + TOP_PAD
            mx = sx + (ex - sx) / 2
            paths.append(f'<path d="M{sx},{sy} H{mx} V{ey} H{ex}"/>')
    return "".join(paths)


def render_bracket(slots: list[dict]) -> str:
    pos, bands, height = _layout()
    by_id = {s["match_id"]: s for s in slots}

    cards = []
    for mid, (x, y) in pos.items():
        s = by_id[mid]
        cards.append(
            f'<div class="m {s["status"]}" style="left:{x}px;top:{y + TOP_PAD}px">'
            f'<div class="tag"><span class="id">{mid}</span> · {escape(s["round_label"])}'
            f'{" · LIVE" if s["status"] == "live" else ""}</div>'
            f'{_side(s, "a")}{_side(s, "b")}</div>')

    labels = []
    for info in bands.values():
        for col, label in info["columns"].items():
            labels.append(f'<div class="collabel" '
                          f'style="left:{col * (CARD_W + COL_GAP)}px;'
                          f'top:{info["label_y"] + 6}px">{escape(label)}</div>')

    width = max(x for x, _y in pos.values()) + CARD_W + 20
    return (f'<div class="bracket-scroll"><div class="bracket" '
            f'style="width:{width}px;height:{height + 20}px">'
            f'<svg width="{width}" height="{height + 20}">{_connectors(pos)}</svg>'
            f'{"".join(labels)}{"".join(cards)}</div></div>')
