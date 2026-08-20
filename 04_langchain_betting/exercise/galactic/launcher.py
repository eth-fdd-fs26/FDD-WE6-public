"""The betting desk: choose the prompt, the tools, the sub-skills and the harness, then
watch the agent spend your money.

    import galactic
    t = galactic.Tournament()
    galactic.control_panel(t)

Everything here is deliberately visible. The four things you can change are the four things
that actually determine what an agent does, so each gets its own bookmark, and the run itself
is drawn as a set of stages — reading, researching, pricing, staking — because "what did it
spend the money on" is the question the transcript has to answer.

Two notes on how it is built, both learned the hard way:

* **Every live surface is a ``W.HTML``, never a ``W.Output``.** Repainting an ``Output`` means
  assigning its ``outputs`` tuple, which the notebook front-ends support inconsistently —
  in Colab the trace simply never appeared. Assigning ``HTML.value`` is one comm message and
  works everywhere.
* **Every CSS rule is scoped to this panel's own class** (see ``ui.scoped``). A notebook has
  one document; a stray ``body`` rule repaints the lot.

The round rail at the top is the other half of the design. A settled round is drawn locked,
with its result, and there is no control anywhere that reopens it — once you know who won
round 1 you cannot bet on round 1, which is the only version of this exercise that means
anything.
"""

from __future__ import annotations

import threading
import time
from html import escape

import ipywidgets as W
from IPython.display import display

from . import agents, config as C, tools as T, ui
from .tournament import N_ROUNDS, RoundError
from .trace import STAGES, TraceRenderer

CSS = ui.card_css(1000) + ui.WIDGET_SKIN + f"""
__U__ .bar {{display:flex;align-items:center;gap:16px;padding:13px 16px;
  border-radius:{ui.RADIUS_2};background:{ui.SURFACE_2};border:1px solid {ui.LINE};
  margin-bottom:12px;flex-wrap:wrap}}
__U__ .money {{font-weight:800;font-size:18px;color:{ui.INK};font-family:{ui.MONO};
  letter-spacing:-.02em}}
__U__ .pnl {{font-family:{ui.MONO};font-weight:700;font-size:13px}}
__U__ .up {{color:{ui.OK}}}
__U__ .down {{color:{ui.NO}}}
__U__ .rail {{display:flex;align-items:center;gap:3px;margin-left:auto;flex-wrap:wrap}}
__U__ .stop {{display:flex;flex-direction:column;gap:1px;border-radius:9px;padding:6px 11px;
  border:1px solid {ui.LINE_2};background:{ui.SURFACE};min-width:76px}}
__U__ .stop .t {{font-size:9.5px;letter-spacing:.08em;text-transform:uppercase;
  color:{ui.FAINT};font-weight:800}}
__U__ .stop .v {{font-size:11px;font-family:{ui.MONO};color:{ui.MUTED}}}
__U__ .stop.done {{background:{ui.OK_BG};border-color:#c9e6d4}}
__U__ .stop.done .t {{color:#2e7d5b}}
__U__ .stop.now {{background:{ui.SELECT};border-color:{ui.ACCENT_2};
  box-shadow:0 0 0 3px rgba(124,77,189,.10)}}
__U__ .stop.now .t {{color:#4a3a86}}
__U__ .stop.now .v {{color:{ui.ACCENT_2};font-weight:700}}
__U__ .arrow {{color:#d6d9e6;font-size:11px}}
__U__ .lbl {{font-size:10px;letter-spacing:.09em;text-transform:uppercase;
  color:{ui.FAINT};font-weight:800;margin:0 0 6px}}
__U__ .blurb {{color:{ui.BODY};font-size:12.5px;line-height:1.65;max-width:680px;
  margin:2px 0 12px}}
__U__ .blurb b {{color:{ui.INK}}}
__U__ .doc {{background:{ui.SURFACE_2};border:1px solid {ui.LINE_2};
  border-radius:{ui.RADIUS_2};padding:12px 14px;font-family:{ui.MONO};font-size:11.5px;
  color:#555;white-space:pre-wrap;max-height:280px;overflow:auto;line-height:1.6}}
__U__ .warn {{color:#c0554e;font-size:12.5px;font-weight:700;background:{ui.NO_BG};
  border:1px solid #f3d4d4;border-radius:{ui.RADIUS_2};padding:11px 13px}}
__U__ .tool {{border:1px solid {ui.LINE_2};border-radius:{ui.RADIUS_2};padding:9px 11px 5px;
  background:{ui.SURFACE};margin-bottom:8px;transition:.12s}}
__U__ .tool:hover {{border-color:#cfd4e6}}
__U__ .rep {{border:1px solid {ui.LINE};border-radius:{ui.RADIUS_2};padding:15px 17px;
  background:{ui.SURFACE};font-size:13px;margin-top:12px}}
__U__ .rep h4 {{margin:0 0 10px;font-size:14px;color:{ui.INK};font-weight:800}}
__U__ .rep .row {{display:flex;gap:10px;padding:7px 0;border-bottom:1px solid {ui.LINE_SOFT}}}
__U__ .rep .row:last-of-type {{border-bottom:none}}
__U__ .rep .grow {{flex:1}}
__U__ .rep .num {{font-family:{ui.MONO};text-align:right;min-width:86px}}
__U__ .rep .foot {{color:{ui.MUTED};margin-top:12px;line-height:1.65;font-size:12.5px}}
__U__ .var .row {{display:flex;gap:10px;align-items:center;padding:5px 0}}
__U__ .var .who {{width:66px;color:{ui.MUTED};font-size:12.5px}}
__U__ .var .track {{flex:1;height:9px;border-radius:5px;background:{ui.LINE_SOFT};
  position:relative}}
__U__ .var .fill {{display:block;height:100%;min-width:2px;border-radius:5px}}
__U__ .var .zero {{position:absolute;top:-3px;bottom:-3px;width:1px;background:#c2c7da}}
"""

_BTN = dict(layout=W.Layout(width="auto"), style={"font_weight": "600"})


# ===================================================================== header
def _rail_html(t) -> str:
    """One stop per betting round, plus the trophy. Settled rounds are drawn shut."""
    stops = []
    for r in range(1, N_ROUNDS + 1):
        placed = [b for b in t.bets() if b["round_placed"] == r]
        # an outright backed in round 1 does not settle until the trophy is handed out,
        # so a shut round can still have money running in it
        decided = [b for b in placed if b["status"] in ("won", "lost")]
        won = sum(1 for b in decided if b["status"] == "won")
        if r < t.round:
            if not placed:
                value = "no bets"
            elif decided:
                value = f"{won}/{len(decided)} landed"
            else:
                value = f"{len(placed)} running"
            stops.append(("done", f"🔒 round {r}", value))
        elif r == t.round and not t.finished:
            stops.append(("now", f"▶ round {r}",
                          f"{len(placed)} bet{'s' * (len(placed) != 1)} placed"))
        else:
            stops.append(("", f"round {r}", "locked"))
    stops.append(("done" if t.finished else "", "🏆 champion",
                  t.champion or "undecided"))
    return '<span class="arrow">→</span>'.join(
        f'<span class="stop {cls}"><span class="t">{escape(title)}</span>'
        f'<span class="v">{escape(value)}</span></span>' for cls, title, value in stops)


def _header_html(t) -> str:
    pnl = t.wallet - C.STARTING_BANKROLL
    return (f'<div class="bar"><span class="money">{t.wallet:,.2f} {C.CURRENCY}</span>'
            f'<span class="pnl {"up" if pnl >= 0 else "down"}">{pnl:+,.0f}</span>'
            f'<span class="rail">{_rail_html(t)}</span></div>')


# ===================================================================== settlement report
def _report_html(rep, t) -> str:
    rows = "".join(
        f'<div class="row"><span class="grow">{escape(r["round_label"])} · '
        f'<b>{escape(r["team_a"])}</b> {escape(r["score"])} '
        f'<b>{escape(r["team_b"])}</b></span>'
        f'<span style="color:{ui.OK};font-weight:700">{escape(r["winner"])}</span></div>'
        for r in rep.results)
    bets = "".join(
        f'<div class="row"><span class="grow">{escape(b["selection"])} @ {b["odds"]:.2f}'
        f'</span><span class="num">−{b["stake"]:,.0f}</span>'
        f'<span class="num" style="color:{ui.OK if b["status"] == "won" else ui.NO}">'
        f'{"+" if b["status"] == "won" else ""}{b["payout"]:,.0f}</span></div>'
        for b in rep.settled_bets) or \
        f'<div class="row" style="color:{ui.FAINT}">No bets settled this round.</div>'
    delta = rep.wallet_after - rep.wallet_before
    return (f'<div class="rep"><h4>🔒 Round {rep.round_index} settled — and closed for good'
            f'</h4>{rows}<div class="lbl" style="margin:14px 0 2px">Your bets</div>{bets}'
            f'<div class="foot">Balance {rep.wallet_before:,.0f} → '
            f'<b style="color:{ui.INK}">{rep.wallet_after:,.0f} {C.CURRENCY}</b> '
            f'({delta:+,.0f}). Both sites above have already moved on: new bracket, new '
            f'prices, and StarScoop has covered the round.</div>'
            f'</div>')


def _variability_html(results) -> str:
    wallets = [r["wallet"] for r in results]
    picks = [r["picks"] for r in results]
    overlap = (len(set.intersection(*picks)) / max(len(set.union(*picks)), 1)
               if all(picks) else 0.0)
    # a bar from the starting bankroll outward: losses run left in red, gains right in green,
    # so the three runs are compared against the only number that matters and not against
    # each other's minimum
    start = C.STARTING_BANKROLL
    lo, hi = min(wallets + [start]), max(wallets + [start])
    pad = 0.08 * max(hi - lo, 1.0)
    lo, hi = lo - pad, hi + pad
    span = hi - lo
    zero = 100 * (start - lo) / span
    rows = "".join(
        f'<div class="row"><span class="who">run {i + 1}</span>'
        f'<span class="track"><span class="fill" style="position:absolute;'
        f'left:{min(zero, 100 * (w - lo) / span):.1f}%;'
        f'width:{abs(100 * (w - start) / span):.1f}%;background:'
        f'{ui.OK if w >= start else ui.NO}"></span>'
        f'<span class="zero" style="left:{zero:.1f}%"></span></span>'
        f'<span class="num" style="font-family:{ui.MONO};width:100px;text-align:right">'
        f'{w:,.0f}</span>'
        f'<span style="color:{ui.FAINT};width:96px;text-align:right">'
        f'{r["steps"]} steps · {r["n_bets"]} bet{"s" * (r["n_bets"] != 1)}</span></div>'
        for i, (w, r) in enumerate(zip(wallets, results)))
    return (f'<div class="rep var"><h4>Three universes, one setup</h4>{rows}'
            f'<div class="foot">Spread <b style="color:{ui.INK}">{min(wallets):,.0f} → '
            f'{max(wallets):,.0f} {C.CURRENCY}</b>; the three runs agreed on '
            f'<b style="color:{ui.INK}">{overlap:.0%}</b> of their selections. Same tools, '
            f'same prompt, same prices — the difference is which way the coins fell and which '
            f'token the model happened to sample. Whatever you conclude from a single run, '
            f'this is the width of the thing you concluded it from.</div></div>')


# ===================================================================== the panel
class ControlPanel:
    """The desk. Built by :func:`control_panel`; exposed so tests can press its buttons."""

    def __init__(self, tournament, *, model=None, api_key=None, enabled=None):
        self.t = tournament
        self._bind_sites()          # the two iframes must show the tournament we settle
        self.api_key = api_key
        self.uid = ui.uid("desk")
        self.enabled = {k: set(v) for k, v in (enabled or T.DEFAULT_ENABLED).items()}
        self.busy = False
        self.armed = False
        self._build(model)

    def _bind_sites(self):
        """Point GalacticBets and StarScoop at this desk's tournament.

        Re-running the cell that builds the tournament makes a second one, and without this
        the sites would go on rendering the first: the desk would settle round after round
        while the bracket sat at round 1. Rebinding costs nothing and removes the whole class
        of confusion.
        """
        try:
            from . import site
            site.bind(self.t)
        except Exception:                      # no sites open, or none importable — fine
            pass

    # ------------------------------------------------------------------ chrome
    def _build(self, model):
        self.header = W.HTML(_header_html(self.t))
        self.status = W.HTML()
        self.trace = W.HTML()
        self.report = W.HTML()

        sections = [("📝 Prompt", self._prompt_section(model)),
                    ("🧰 Tools", self._tools_section()),
                    ("⚙️ Harness", self._harness_section()),
                    ("▶️ Run", self._run_section()),
                    ("🎲 Variability", self._variability_section())]
        self.titles = [title for title, _ in sections]
        self.pages = [body for _, body in sections]
        # ToggleButtons, and NOT a `W.Tab`. A Tab would switch in the browser without
        # troubling the kernel, which is nicer in principle — but Colab's widget renderer
        # does not draw `Tab`/`Accordion` containers, so the whole desk comes out blank.
        # That is not a hypothetical: it is what "the control panel does not work at all"
        # was. Switching a bookmark therefore costs a kernel round-trip, which is only
        # noticeable while a run is in flight — and the trace and the report deliberately
        # sit *outside* the bookmarks, so there is nothing you need to switch to mid-run.
        self.nav = W.ToggleButtons(options=self.titles, value=self.titles[0],
                                   style={"button_width": "auto"})
        for i, page in enumerate(self.pages):
            page.layout.display = "" if i == 0 else "none"
        self.nav.observe(self._on_nav, names="value")

        title = W.HTML(
            '<div class="title">🛰️ The betting desk</div>'
            '<div class="tagline">Four things you can change, and between them they are what '
            'decides what any agent does. Change one at a time.</div>')
        self.widget = W.VBox([title, self.header, self.nav, *self.pages,
                              self.status, self.trace, self.report])
        self.widget.add_class(self.uid)

    def _on_nav(self, change):
        idx = self.titles.index(change["new"])
        for i, page in enumerate(self.pages):
            page.layout.display = "" if i == idx else "none"

    # ------------------------------------------------------------------ prompt
    def _prompt_section(self, model):
        self.prompt_pick = W.Dropdown(
            options=[(v, k) for k, v in agents.PROMPT_LABELS.items()],
            value="value_hunter", description="Preset", layout=W.Layout(width="96%"),
            style={"description_width": "92px"})
        self.prompt_text = W.Textarea(
            value=agents.render_prompt("value_hunter", self.t), rows=8,
            layout=W.Layout(width="96%"))
        self.model_pick = W.Dropdown(options=C.MODEL_CHOICES, value=model or C.DEFAULT_MODEL,
                                     description="Model", layout=W.Layout(width="96%"),
                                     style={"description_width": "92px"})
        self.temp = W.FloatSlider(value=C.DEFAULT_TEMPERATURE, min=0.0, max=1.0, step=0.1,
                                  description="Temperature", readout_format=".1f",
                                  style={"description_width": "92px"})
        self.steps = W.IntSlider(value=C.DEFAULT_MAX_STEPS, min=4, max=30,
                                 description="Max steps", style={"description_width": "92px"})

        def on_preset(change):
            if change["new"] in agents.PROMPTS:
                self.prompt_text.value = agents.render_prompt(change["new"], self.t)
        self.prompt_pick.observe(on_preset, names="value")

        return W.VBox([
            W.HTML('<div class="blurb">The preset only fills the box below — <b>edit it</b>. '
                   'This is the whole of what the agent is told about what you want; '
                   'everything else it has to go and find out.</div>'),
            self.prompt_pick, self.prompt_text, self.model_pick, self.temp, self.steps])

    # ------------------------------------------------------------------ tools
    def _tools_section(self):
        self.doc_pane = W.HTML()
        self.boxes: dict[str, tuple[W.Checkbox, dict]] = {}
        cards = []
        for name, spec in T.TOOL_SPECS.items():
            tool_cb = W.Checkbox(value=bool(self.enabled.get(name)), description=name,
                                 indent=False, layout=W.Layout(width="215px"))
            subs = {s.key: W.Checkbox(value=s.key in self.enabled.get(name, set()),
                                      description=s.label, indent=False,
                                      layout=W.Layout(width="200px", margin="0 0 0 20px"))
                    for s in spec.subskills}
            self.boxes[name] = (tool_cb, subs)
            handler = self._sync(name)
            tool_cb.observe(handler, names="value")
            for cb in subs.values():
                cb.observe(handler, names="value")
            card = W.VBox([tool_cb, *subs.values()])
            card.add_class("tool")
            cards.append(card)
        self._refresh_doc()
        return W.VBox([
            W.HTML('<div class="blurb">A sub-skill you switch off is not merely discouraged: '
                   'its name leaves the tool\'s argument enum and every sentence describing '
                   'it leaves the tool\'s description — which <b>is</b> part of the prompt. '
                   'Watch the panel on the right change as you click.</div>'),
            W.HBox([W.VBox(cards, layout=W.Layout(width="250px")),
                    W.Box([self.doc_pane], layout=W.Layout(width="62%",
                                                           margin="0 0 0 16px"))])])

    def _sync(self, name):
        def handler(_change):
            tool_cb, subs = self.boxes[name]
            keys = {k for k, cb in subs.items() if cb.value} if tool_cb.value else set()
            for cb in subs.values():
                cb.disabled = not tool_cb.value
            self.enabled[name] = keys
            self._refresh_doc(name)
        return handler

    def _refresh_doc(self, focus: str | None = None):
        name = focus or next((n for n in T.TOOL_SPECS if self.enabled.get(n)), None)
        if not name:
            self.doc_pane.value = (
                '<div class="warn">Every tool is switched off. The agent can do nothing at '
                'all — which is itself worth trying once, to see what it does instead.</div>')
            return
        spec = T.TOOL_SPECS[name]
        keys = self.enabled.get(name, set())
        doc = (T.build_docstring(spec, keys) if keys else
               f"{spec.name} is switched off — the agent will not see it at all.")
        self.doc_pane.value = (
            f'<div class="lbl">What the agent reads for {escape(name)}</div>'
            f'<div class="doc">{escape(doc)}</div>')

    # ------------------------------------------------------------------ harness
    def _harness_section(self):
        self.harness = W.RadioButtons(
            options=[(v, k) for k, v in agents.HARNESS_LABELS.items()],
            value="tool_calling", layout=W.Layout(width="96%"))
        return W.VBox([
            W.HTML('<div class="blurb">Same model, same tools, same prompt — only the loop '
                   'around them changes. Classic ReAct writes its actions as text and has '
                   'them parsed back; tool calling emits structured calls the API validates; '
                   'two-pass forces all the reading to finish before any of the betting can '
                   'start. Run one setup on two of these and compare the step counts.</div>'),
            self.harness])

    # ------------------------------------------------------------------ run
    def _run_section(self):
        self.run_btn = W.Button(description="▶  Run the agent", button_style="primary",
                                **_BTN)
        self.next_btn = W.Button(description=f"⏭  Settle round {self.t.round} and advance",
                                 **_BTN)
        self.run_btn.on_click(self._on_run)
        self.next_btn.on_click(self._on_next)
        return W.VBox([
            W.HTML('<div class="blurb">▶ runs the agent against the <b>real</b> wallet and '
                   'the stages below fill in as it goes — reading, researching, pricing, '
                   'staking. Run it as many times as you like; the round stays open until '
                   'you settle it.<br>⏭ plays the round out, settles every bet, and moves '
                   'the bracket on. It asks twice, because <b>there is no way back</b>: once '
                   'the results are on the board, betting into that round is over.</div>'),
            W.HBox([self.run_btn, self.next_btn])])

    # ------------------------------------------------------------------ variability
    def _variability_section(self):
        self.vary_btn = W.Button(description="🎲  Run the same setup 3×", **_BTN)
        self.vary_out = W.HTML()
        self.vary_traces = W.HBox()
        self.vary_btn.on_click(self._on_vary)
        return W.VBox([
            W.HTML('<div class="blurb">Three sandbox copies of the tournament, forked from '
                   'this exact round, with the settings you have chosen — run one after '
                   'another so you can see how much of the outcome was your setup and how '
                   'much was luck. <b>Your real wallet is not touched.</b></div>'),
            self.vary_btn, self.vary_traces, self.vary_out])

    # ------------------------------------------------------------------ running
    def _config(self):
        return dict(prompt=self.prompt_text.value, model=self.model_pick.value,
                    temperature=self.temp.value, max_steps=self.steps.value,
                    harness=self.harness.value,
                    enabled={k: set(v) for k, v in self.enabled.items()})

    def _set_busy(self, on: bool, msg: str = ""):
        self.busy = on
        for b in (self.run_btn, self.vary_btn, self.next_btn):
            b.disabled = on or (b is self.next_btn and self.t.finished)
        self.status.value = (f'<div class="blurb" style="padding:4px 0">{escape(msg)}</div>'
                             if msg else "")

    def _run_once(self, target, cfg, sink, label=""):
        tr = TraceRenderer(sink, target, sandbox_label=label)
        try:
            llm = agents.build_model(self.api_key, cfg["model"], cfg["temperature"])
        except Exception as exc:                                   # noqa: BLE001
            tr.add("err", "⚠️ no model", f"<pre>{escape(str(exc))}</pre>")
            tr.finish()
            return None
        box = T.make_tools(target, cfg["enabled"])
        if not box:
            tr.add("err", "⚠️ empty toolbox",
                   "Switch at least one tool on, over on the Tools bookmark.")
            tr.finish()
            return None
        run = agents.run_agent(cfg["harness"], model=llm, tools=box, prompt=cfg["prompt"],
                               tournament=target, callbacks=[tr],
                               max_steps=cfg["max_steps"])
        tr.finish(run)
        return run

    def _on_run(self, _b):
        if self.busy:
            return
        self._set_busy(True, "running…")
        self.report.value = ""
        try:
            self._bind_sites()
            self._run_once(self.t, self._config(), self.trace)
        finally:
            self.header.value = _header_html(self.t)
            self._set_busy(False)

    def _on_vary(self, _b):
        if self.busy:
            return
        self._set_busy(True, "running three sandbox universes, one at a time…")
        cfg = self._config()
        sinks = [W.HTML() for _ in range(3)]
        self.vary_traces.children = tuple(
            W.Box([s], layout=W.Layout(width="33%")) for s in sinks)
        self.vary_out.value = ""
        results = []
        try:
            for i, fork in enumerate(self.t.fork(3)):
                run = self._run_once(fork, cfg, sinks[i],
                                     f"sandbox {i + 1} · your real wallet is untouched")
                fork.advance_round("ADVANCE")
                results.append({"wallet": fork.wallet, "n_bets": len(fork.bets()),
                                "picks": {b["selection"] for b in fork.bets()},
                                "steps": run.steps if run else 0})
            self.vary_out.value = _variability_html(results)
        finally:
            self._set_busy(False)

    def _on_next(self, _b):
        if self.busy or self.t.finished:
            return
        if not self.armed:
            self.armed = True
            self.next_btn.description = f"⚠️  Confirm — round {self.t.round} closes forever"
            self.next_btn.button_style = "danger"

            def disarm():
                time.sleep(5)
                if self.armed:
                    self.armed = False
                    self.next_btn.description = (f"⏭  Settle round {self.t.round} "
                                                 f"and advance")
                    self.next_btn.button_style = ""
            threading.Thread(target=disarm, daemon=True).start()
            return
        self.armed = False
        self.next_btn.button_style = ""
        try:
            rep = self.t.advance_round("ADVANCE")
        except RoundError as exc:
            self.status.value = f'<div class="warn">{escape(str(exc))}</div>'
            return
        self._bind_sites()
        self.report.value = _report_html(rep, self.t)
        self.header.value = _header_html(self.t)
        if self.t.finished:
            self.next_btn.description = f"🏆 Champion: {self.t.champion}"
            self.next_btn.disabled = True
        else:
            self.next_btn.description = f"⏭  Settle round {self.t.round} and advance"
            self.prompt_text.value = agents.render_prompt(self.prompt_pick.value, self.t)

def control_panel(tournament, *, model: str | None = None, api_key: str | None = None,
                  enabled: dict | None = None) -> ControlPanel:
    """Build and display the betting desk for a tournament.

    Note what is *not* here: ``google.colab.output.enable_custom_widget_manager()``. That
    call is for third-party widgets, and it switches Colab away from its built-in renderer to
    one that fetches the widget JS from a CDN. Everything on this desk is a core ipywidget
    that Colab draws natively, so the call buys nothing and adds a way to fail. The toolbox
    bench never called it and always rendered; the desk did, and did not.
    """
    panel = ControlPanel(tournament, model=model, api_key=api_key, enabled=enabled)
    display(W.HTML(ui.scoped(CSS, f".{panel.uid}")))
    display(panel.widget)
    return panel


__all__ = ["ControlPanel", "control_panel", "STAGES"]
