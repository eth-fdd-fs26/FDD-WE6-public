"""The toolbox, with the lid off — a bench for calling the agent's tools by hand.

    import galactic
    t = galactic.Tournament()
    galactic.tool_explorer(t)

The launcher later lets you switch tools and sub-skills on and off, which is only an
interesting decision if you know what each one can find out. So this panel is the same
registry, driven manually: pick a tool, pick one of its sub-skills, fill in whatever that
sub-skill reads, and see exactly what comes back — next to the description the *model* gets
for the same tool, which is the thing that decides whether it ever calls it.

One deliberate omission: ``betting → place_bet`` is listed and disabled. This bench is for
finding out what is knowable. The money is the agent's to spend.
"""

from __future__ import annotations

from html import escape

import ipywidgets as W
from IPython.display import display

from . import config as C, tools as T, ui

#: Sub-skills a human may run here. Anything that moves the wallet is the agent's job.
_READ_ONLY_EXCEPTIONS = {("betting", "place_bet")}

#: The questions the site actually answers, and the tool that answers each. Shown as prompts,
#: not as answers — clicking one only selects a tool, it does not run anything.
INVESTIGATIONS = [
    ("Which matches can I bet on right now, and at what price?", "betting", "markets"),
    ("Who is actually going to start for a club this week?", "player_stats", "lineup"),
    ("What is the League's own definition of a foul?", "read_rules", "section"),
    ("Which clubs have had a story written about them?", "read_news", "latest"),
    ("Who kept the ball best in the closed-doors scrims?", "research_team", "scrims"),
    ("Which playoff matches have already been played, and who is out?",
     "research_team", "playoffs"),
]

CSS = ui.card_css(1020) + ui.WIDGET_SKIN + f"""
__U__ .doc {{background:{ui.SURFACE_2};border:1px solid {ui.LINE_2};
  border-radius:{ui.RADIUS_2};padding:12px 14px;font-family:{ui.MONO};font-size:11.5px;
  color:#555;white-space:pre-wrap;max-height:200px;overflow:auto;line-height:1.6}}
__U__ .lbl {{font-size:10px;letter-spacing:.09em;text-transform:uppercase;
  color:{ui.FAINT};font-weight:800;margin:0 0 6px}}
__U__ .res {{border:1px solid {ui.LINE_2};border-radius:{ui.RADIUS_2};max-height:340px;
  overflow:auto;background:{ui.SURFACE}}}
__U__ .res pre {{margin:0;padding:13px;font-family:{ui.MONO};font-size:11.5px;
  white-space:pre-wrap;word-break:break-word;line-height:1.6;color:#555}}
__U__ .res table {{width:100%;border-collapse:collapse}}
__U__ .res th {{position:sticky;top:0;text-align:left;padding:9px 12px;font-size:10px;
  letter-spacing:.07em;text-transform:uppercase;color:{ui.FAINT};font-weight:800;
  background:{ui.SURFACE_2};border-bottom:1px solid {ui.LINE_2};white-space:nowrap}}
__U__ .res td {{padding:8px 12px;border-bottom:1px solid {ui.LINE_SOFT};font-size:12px;
  vertical-align:top}}
__U__ .res tbody tr:last-child td {{border-bottom:none}}
__U__ .res tbody tr:hover {{background:{ui.HOVER}}}
__U__ .mono {{font-family:{ui.MONO};font-size:11.5px;color:#555}}
__U__ .qs {{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}}
__U__ .q {{border:1px solid {ui.LINE_2};border-radius:999px;padding:5px 12px;font-size:11.5px;
  color:{ui.MUTED};background:{ui.SURFACE_2}}}
__U__ .q b {{color:{ui.ACCENT};font-family:{ui.MONO};font-size:11px}}
__U__ .note {{color:#8a6d3b;font-size:12px;line-height:1.55;background:{ui.GOLD_BG};
  border:1px solid #f0dcb4;border-radius:{ui.RADIUS_2};padding:10px 12px;margin-top:8px}}
__U__ .skill {{font-size:12px;color:{ui.MUTED};line-height:1.5;
  border-left:2px solid {ui.ACCENT_2};padding-left:10px;margin:4px 0 2px}}
"""


def _arg_widgets(tournament):
    """One widget per optional argument in the registry, wired to this tournament."""
    match_ids = [m["match_id"] for m in tournament.open_markets()
                 if m.get("kind") == "match"] or ["UB1"]
    teams = list(C.TEAMS)
    return {
        "team": W.Dropdown(options=teams, value=teams[0], description="team"),
        "opponent": W.Dropdown(options=teams, value=teams[1], description="opponent"),
        "section": W.Dropdown(options=[(f"§{k} · {v}", k)
                                       for k, v in _sections().items()],
                              description="section"),
        "query": W.Text(value="injury", description="query",
                        placeholder="free text, e.g. 'suspension'"),
        "article_id": W.Text(value="N01", description="article"),
        "match_id": W.Dropdown(options=match_ids, description="match"),
        "selection": W.Dropdown(options=teams, description="selection"),
        "stake": W.FloatText(value=100.0, description="stake"),
    }


def _sections():
    from . import rules
    return rules.contents()


def tool_explorer(tournament):
    """Display the toolbox bench. Returns the panel, for tests."""
    uid = ui.uid("explore")
    names = list(T.TOOL_SPECS)

    tool_pick = W.ToggleButtons(options=names, value=names[0],
                                style={"button_width": "auto"})
    skill_pick = W.RadioButtons(options=[], layout=W.Layout(width="230px"),
                                style={"description_width": "0px"})
    skill_doc = W.HTML()
    doc_pane = W.HTML()
    args_box = W.VBox()
    result = W.HTML()
    run_btn = W.Button(description="▶  Call it", button_style="primary",
                       layout=W.Layout(width="auto"))
    hint = W.HTML()

    widgets = _arg_widgets(tournament)
    for w in widgets.values():
        w.style.description_width = "78px"
        w.layout.width = "330px"

    def _spec():
        return T.TOOL_SPECS[tool_pick.value]

    def _subskill():
        return next((s for s in _spec().subskills if s.key == skill_pick.value), None)

    def _on_tool(_change=None):
        spec = _spec()
        skill_pick.options = [(f"{s.label}", s.key) for s in spec.subskills]
        skill_pick.value = spec.subskills[0].key
        # what the *model* sees for this tool, with every sub-skill available
        doc = T.build_docstring(spec, set(spec.keys))
        doc_pane.value = (f'<div class="lbl">What the model reads for '
                          f'<b>{escape(spec.name)}</b></div>'
                          f'<div class="doc">{escape(doc)}</div>')
        _on_skill()

    def _on_skill(_change=None):
        sub = _subskill()
        if sub is None:
            return
        skill_doc.value = f'<div class="skill">{escape(sub.doc)}</div>'
        args_box.children = tuple(widgets[p] for p in sub.params)
        blocked = (_spec().name, sub.key) in _READ_ONLY_EXCEPTIONS
        run_btn.disabled = blocked
        hint.value = (
            '<div class="note">🔒 This bench is read-only. Placing a bet is the one thing '
            'you hand to the agent — that is what the launcher below is for.</div>'
            if blocked else "")
        result.value = ""

    def _on_run(_b):
        sub = _subskill()
        if sub is None or (_spec().name, sub.key) in _READ_ONLY_EXCEPTIONS:
            return                      # `disabled` only stops the mouse, not the handler
        kwargs = {p: widgets[p].value for p in sub.params}
        call = ", ".join([f'mode="{sub.key}"'] +
                         [f"{k}={v!r}" for k, v in kwargs.items()])
        try:
            out = T.call(tournament, _spec().name, sub.key, **kwargs)
        except Exception as exc:                                   # noqa: BLE001
            out = {"error": f"{type(exc).__name__}: {exc}"}
        result.value = (f'<div class="lbl">{escape(_spec().name)}.invoke({{{escape(call)}}})'
                        f'</div>{ui.result_html(out)}')

    tool_pick.observe(_on_tool, names="value")
    skill_pick.observe(_on_skill, names="value")
    run_btn.on_click(_on_run)
    _on_tool()

    questions = "".join(
        f'<span class="q">{escape(q)} <b>{tool}/{skill}</b></span>'
        for q, tool, skill in INVESTIGATIONS)

    head = W.HTML(
        f'<div class="title">🧰 The toolbox — what your agent can actually find out</div>'
        f'<div class="tagline">Five tools, each with two to four <b>sub-skills</b>. Pick one, '
        f'call it, and read what comes back. Then look at the panel on the right: that text '
        f'is the entire description the model gets, and it is the only reason the model would '
        f'ever choose this tool over another.</div>'
        f'<div class="qs">{questions}</div>')

    left = W.VBox([W.HTML('<div class="lbl">Sub-skill</div>'), skill_pick, skill_doc,
                   W.HTML('<div class="lbl" style="margin-top:14px">Arguments</div>'),
                   args_box, W.HBox([run_btn]), hint],
                  layout=W.Layout(width="380px"))
    right = W.VBox([doc_pane], layout=W.Layout(width="600px", margin="0 0 0 18px"))

    panel = W.VBox([head, tool_pick, W.HBox([left, right]), result])
    panel.add_class(uid)
    display(W.HTML(ui.scoped(CSS, f".{uid}")))
    display(panel)
    return panel
