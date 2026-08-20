"""Watching the agent think — and watching it spend.

One callback handler, rendered as a stage strip over a stack of cards. The same handler works
for both runtimes: ``AgentExecutor`` calls the callbacks directly, and ``create_agent`` builds
on LangGraph, which propagates ``config["callbacks"]`` down the whole runnable tree — so
nothing here is harness-specific.

The stage strip is the part worth explaining. A transcript answers "what did it do"; the
question a participant actually has is "what did it spend my money on, and what did it look
at first". Every tool call is therefore mapped onto one of five stages, in the order a
competent analyst would do them, and the strip lights up as the run moves through — so a
harness that bets before it reads is visible at a glance rather than by scrolling.

Three rendering details matter more than they look:

* The whole thing is re-rendered and assigned to one ``HTML.value`` in a single go. Appending
  per event flickers and bloats the saved notebook; an ``ipywidgets.Output`` was worse still,
  because assigning its ``outputs`` tuple is not reliably supported in Colab.
* Renders are throttled — a chatty agent emits events faster than a browser can lay them out.
* Every CSS rule is prefixed with ``.gpl-trace``, so nothing here can style the notebook
  around it.
"""

from __future__ import annotations

import json
import time
from html import escape

from langchain_core.callbacks import BaseCallbackHandler

from . import config as C, ui

_MAX_OBS = 700
_MIN_INTERVAL = 0.25       # seconds between re-renders

#: (key, label, which tools land here). Order is the order a good analyst works in.
STAGES: list[tuple[str, str, tuple[str, ...]]] = [
    ("rules", "reads the rules", ("read_rules",)),
    ("research", "researches the clubs", ("research_team", "player_stats", "read_news")),
    ("market", "checks the prices", ("betting",)),
    ("stake", "stakes the money", ()),          # driven by the wallet, not by a tool name
    ("done", "explains itself", ()),
]

CSS = f"""
<style>
.gpl-trace{{font-family:{ui.SANS};font-size:13px;color:{ui.BODY};background:{ui.SURFACE};
  border:1px solid {ui.LINE};border-radius:{ui.RADIUS_2};padding:14px;margin-top:12px}}
.gpl-trace .sandbox{{background:{ui.GOLD_BG};border:1px solid #f0dcb4;color:{ui.GOLD};
  border-radius:9px;padding:6px 10px;margin-bottom:10px;font-weight:800;font-size:10.5px;
  letter-spacing:.07em;text-transform:uppercase}}
.gpl-trace .strip{{display:flex;align-items:center;gap:4px;flex-wrap:wrap;
  padding-bottom:11px;margin-bottom:11px;border-bottom:1px solid {ui.LINE_SOFT}}}
.gpl-trace .st{{display:flex;align-items:center;gap:6px;border:1px solid {ui.LINE_2};
  border-radius:999px;padding:4px 11px;font-size:11.5px;color:{ui.FAINT};
  background:{ui.SURFACE_2}}}
.gpl-trace .st .dot{{width:7px;height:7px;border-radius:50%;background:#d6d9e6;flex:0 0 7px}}
.gpl-trace .st.hit{{color:#2e7d5b;border-color:#c9e6d4;background:{ui.OK_BG}}}
.gpl-trace .st.hit .dot{{background:{ui.OK}}}
.gpl-trace .st.live{{color:#4a3a86;border-color:{ui.ACCENT_2};background:{ui.SELECT};
  font-weight:700;box-shadow:0 0 0 3px rgba(124,77,189,.10)}}
.gpl-trace .st.live .dot{{background:{ui.ACCENT_2}}}
.gpl-trace .sep{{color:#d6d9e6;font-size:10px}}
.gpl-trace .spend{{margin-left:auto;font-family:{ui.MONO};font-size:11.5px;color:{ui.MUTED}}}
.gpl-trace .spend b{{color:{ui.INK}}}
/* No max-height, and therefore no inner scrollbar. Every new message repaints this whole
   block, which reset an inner scroll offset to the top each time and made watching a live
   run genuinely unpleasant. Letting the cell grow keeps the page's own scroll position. */
.gpl-trace .scroll{{overflow:visible}}
.gpl-trace .c{{border:1px solid {ui.LINE_2};border-radius:{ui.RADIUS_2};padding:10px 12px;
  margin-bottom:7px;background:{ui.SURFACE};line-height:1.55}}
.gpl-trace .c .h{{font-size:10px;font-weight:800;letter-spacing:.09em;
  text-transform:uppercase;color:{ui.FAINT};margin-bottom:5px;display:flex;gap:8px;
  align-items:center}}
.gpl-trace .c.think{{border-left:3px solid #c2c7da;background:{ui.SURFACE_2}}}
.gpl-trace .c.call{{border-left:3px solid {ui.ACCENT}}}
.gpl-trace .c.call .h{{color:{ui.ACCENT}}}
.gpl-trace .c.obs{{border-left:3px solid #dfe3ee;color:{ui.MUTED}}}
.gpl-trace .c.bet{{border-left:3px solid #e0a33c;background:{ui.GOLD_BG}}}
.gpl-trace .c.bet .h{{color:{ui.GOLD}}}
.gpl-trace .c.err{{border-left:3px solid {ui.NO};background:{ui.NO_BG}}}
.gpl-trace .c.err .h{{color:#c0554e}}
.gpl-trace .c.parse{{border-left:3px solid #e0a500;background:#fffbf0}}
.gpl-trace .c.parse .h{{color:#8a6d3b}}
.gpl-trace .c.done{{border-left:3px solid {ui.OK};background:{ui.OK_BG}}}
.gpl-trace .c.done .h{{color:#2e7d5b}}
.gpl-trace pre{{margin:0;font-family:{ui.MONO};font-size:11.5px;white-space:pre-wrap;
  word-break:break-word}}
.gpl-trace .pill{{background:{ui.SELECT};border:1px solid #ddd3f2;border-radius:5px;
  padding:1px 7px;font-family:{ui.MONO};color:#4a3a86;letter-spacing:0;
  text-transform:none;font-weight:700}}
.gpl-trace .foot{{color:{ui.FAINT};font-size:11px;padding:5px 2px 0}}
.gpl-trace details summary{{cursor:pointer;color:{ui.FAINT};font-size:11.5px;margin-top:5px}}
</style>"""


def _reasoning_of(msg) -> str:
    """The model's own words, whatever shape the provider sent them in.

    A tool-calling turn frequently has no plain string content at all: the text arrives as a
    list of typed blocks next to the tool calls, or as a separate reasoning field the chat
    model hangs off ``additional_kwargs``. Reading only ``msg.content`` when it happened to
    be a ``str`` meant the reasoning between tool calls was silently dropped, and the trace
    looked like an agent that never thought about anything.
    """
    if msg is None:
        return ""
    content = getattr(msg, "content", "")
    if isinstance(content, str) and content.strip():
        return content
    parts = []
    if isinstance(content, list):
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(block.get("text") or block.get("thinking")
                             or block.get("reasoning") or "")
    text = "\n".join(p for p in parts if p).strip()
    if text:
        return text
    extra = getattr(msg, "additional_kwargs", None) or {}
    return str(extra.get("reasoning_content") or extra.get("reasoning") or "").strip()


def _short(text, limit: int = _MAX_OBS) -> str:
    text = text if isinstance(text, str) else json.dumps(text, default=str)
    if len(text) <= limit:
        return f"<pre>{escape(text)}</pre>"
    return (f"<pre>{escape(text[:limit])}…</pre>"
            f"<details><summary>show all {len(text):,} characters</summary>"
            f"<pre>{escape(text)}</pre></details>")


class TraceRenderer(BaseCallbackHandler):
    """Collects cards and paints them into an ``ipywidgets.HTML``."""

    def __init__(self, sink=None, tournament=None, *, sandbox_label: str = ""):
        self.sink = sink
        self.cards: list[str] = []
        self.tool_calls = 0
        self.staked = 0.0
        self.n_bets = 0
        self.stage = -1                      # index into STAGES; -1 is "not started"
        self.reached: set[str] = set()
        self.started = time.time()
        self._last_render = 0.0
        self.sandbox_label = sandbox_label
        self._open_tools: dict = {}
        if tournament is not None:
            tournament.on_event(self._on_event)

    # ---------------------------------------------------------------- stages
    def _enter(self, key: str) -> None:
        idx = next(i for i, (k, _l, _t) in enumerate(STAGES) if k == key)
        self.reached.add(key)
        self.stage = max(self.stage, idx) if key != "done" else idx

    def _stage_for(self, tool_name: str) -> str | None:
        for key, _label, tools in STAGES:
            if tool_name in tools:
                return key
        return None

    # ---------------------------------------------------------------- cards
    def add(self, kind: str, head: str, body: str = "") -> None:
        self.cards.append(f'<div class="c {kind}"><div class="h">{head}</div>{body}</div>')
        self._render()

    def _on_event(self, event) -> None:
        if event.kind == "bet_placed":
            b = event.payload["bet"]
            self.staked += b["stake"]
            self.n_bets += 1
            self._enter("stake")
            self.add("bet", "💰 bet placed",
                     f'<b>{escape(b["selection"])}</b> · {b["stake"]:,.0f} {C.CURRENCY} '
                     f'@ {b["odds"]:.2f} → returns {b["to_return"]:,.0f} if it lands'
                     f'<div class="foot">{escape(b["label"])} · balance now '
                     f'{event.payload["wallet"]:,.0f} {C.CURRENCY}</div>')

    # ---------------------------------------------------------------- callbacks
    def on_llm_end(self, response, **kw):
        try:
            gen = response.generations[0][0]
        except Exception:
            return
        text = _reasoning_of(getattr(gen, "message", None)) or getattr(gen, "text", "") or ""
        # classic ReAct puts the plan and the action in one string; keep the plan
        text = text.split("Action:")[0].replace("Thought:", "").strip()
        if len(text) > 3:
            self.add("think", "🧠 thinking", _short(text, 600))

    def on_tool_start(self, serialized, input_str, *, run_id=None, **kw):
        name = (serialized or {}).get("name", kw.get("name", "tool"))
        self.tool_calls += 1
        self._open_tools[run_id] = name
        stage = self._stage_for(str(name))
        if stage:
            self._enter(stage)
        try:
            args = json.loads(input_str) if isinstance(input_str, str) else dict(input_str)
            shown = json.dumps(args, indent=2, default=str)
        except Exception:
            shown = str(input_str)
        self.add("call", f'🔧 <span class="pill">{escape(str(name))}</span> '
                         f'· call {self.tool_calls}', f"<pre>{escape(shown)}</pre>")

    def on_tool_end(self, output, *, run_id=None, **kw):
        name = self._open_tools.pop(run_id, "tool")
        content = getattr(output, "content", output)
        self.add("obs", f"📄 {escape(str(name))} returned", _short(content))

    def on_tool_error(self, error, *, run_id=None, **kw):
        name = self._open_tools.pop(run_id, "tool")
        self.add("err", f"⚠️ {escape(str(name))} failed", f"<pre>{escape(str(error))}</pre>")

    def on_agent_finish(self, finish, **kw):
        text = (finish.return_values or {}).get("output", "")
        if text:
            self._enter("done")
            self.add("done", "✅ finished", _short(str(text), 1200))

    def on_chain_error(self, error, **kw):
        self.add("err", "⚠️ run failed", f"<pre>{escape(str(error))}</pre>")

    # ---------------------------------------------------------------- painting
    def finish(self, run=None) -> None:
        if run is not None:
            if run.error:
                self.add("err", "⚠️ run failed", f"<pre>{escape(run.error)}</pre>")
            elif run.output:
                self._enter("done")
                self.add("done", "✅ the agent's summary", _short(str(run.output), 1600))
        self._render(force=True)

    def _strip_html(self) -> str:
        pills = []
        for i, (key, label, _tools) in enumerate(STAGES):
            cls = ("live" if i == self.stage else "hit") if key in self.reached else ""
            pills.append(f'<span class="st {cls}"><span class="dot"></span>'
                         f'{escape(label)}</span>')
        spend = (f'<span class="spend">staked <b>{self.staked:,.0f} {C.CURRENCY}</b> '
                 f'over {self.n_bets} bet{"s" * (self.n_bets != 1)}</span>')
        return ('<div class="strip">'
                + '<span class="sep">›</span>'.join(pills) + spend + "</div>")

    def html(self) -> str:
        banner = (f'<div class="sandbox">{escape(self.sandbox_label)}</div>'
                  if self.sandbox_label else "")
        foot = (f'<div class="foot">{self.tool_calls} tool call'
                f'{"s" * (self.tool_calls != 1)} · {time.time() - self.started:.0f}s</div>')
        body = "".join(self.cards) or '<div class="foot">Waiting for the agent…</div>'
        return (f'{CSS}<div class="gpl-trace">{banner}{self._strip_html()}'
                f'<div class="scroll">{body}</div>{foot}</div>')

    def _render(self, force: bool = False) -> None:
        if self.sink is None:
            return
        now = time.time()
        if not force and now - self._last_render < _MIN_INTERVAL:
            return
        self._last_render = now
        # One atomic assignment. Never `with out: display(...)` from a worker thread.
        self.sink.value = self.html()
