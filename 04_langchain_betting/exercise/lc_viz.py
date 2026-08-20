"""Every diagram, card and quiz in notebook 04, kept out of the notebook itself.

Two reasons. The teaching cells stay about the idea rather than about HTML, and a quiz whose
answer key lives in the cell above it is not a quiz. **Please don't read this file** — it will
spoil about twenty minutes of the session for you.

Same shape as WE0's ``pdm_viz`` and WE4's ``pg_viz``: generic renderers at the bottom, content
dictionaries at the top.
"""

from __future__ import annotations

import json as _json

from IPython.display import HTML, display

# ===================================================================== palette
ACC = "#4c5bd4"
ACC2 = "#7c4dbd"
OK = "#46b46e"
NO = "#e07a7a"
INK = "#2b2d6b"
MUTE = "#6b7280"
FONT = "system-ui,Segoe UI,Roboto,sans-serif"


def _card(inner: str, maxw: int = 880) -> str:
    return (f'<div style="font-family:{FONT};border:1px solid #e6e8ee;border-radius:14px;'
            f'padding:18px;max-width:{maxw}px;background:#fff">{inner}</div>')


def _show(html: str):
    display(HTML(html))


# ===================================================================== Part 1 diagrams
def framework_diagram():
    """Hand-rolled agent loop vs the same thing with a framework."""
    left = """
<b style="color:#c0554e">By hand</b>
<pre style="font-size:11.5px;line-height:1.55;background:#fbfbfd;border:1px solid #eceef4;
border-radius:8px;padding:11px;overflow:auto;margin:8px 0 0">schema = {"name": "multiply",
  "description": "...",
  "parameters": {"type": "object",
    "properties": {"a": {"type": "number"},
                   "b": {"type": "number"}},
    "required": ["a", "b"]}}

while True:
    r = client.messages.create(tools=[schema], ...)
    if r.stop_reason != "tool_use":
        break
    for block in r.content:
        if block.type == "tool_use":
            try:
                out = FUNCS[block.name](**block.input)
            except Exception as e:
                out = f"error: {e}"
            messages.append(tool_result(block.id, out))
    if len(messages) > 40:
        break                      # and don't forget this</pre>"""
    right = """
<b style="color:#2e7d5b">With a framework</b>
<pre style="font-size:11.5px;line-height:1.55;background:#fbfbfd;border:1px solid #eceef4;
border-radius:8px;padding:11px;overflow:auto;margin:8px 0 0">@tool
def multiply(a: float, b: float) -> float:
    """ + '"""Multiply two numbers."""' + """
    return a * b

agent = create_agent(model, [multiply])
agent.invoke({"messages": [...]})</pre>
<div style="font-size:12.5px;color:#444;line-height:1.6;margin-top:10px">
The schema is read off the type hints. The description is the docstring. The loop, the
error handling and the step limit are the framework's problem. What you are left holding is
the part only you could have written: <b>the function</b>.</div>"""
    _show(_card(
        f'<div style="font-weight:800;font-size:15px;color:{INK};margin-bottom:4px">'
        f'The same agent, twice</div>'
        f'<div style="font-size:12.5px;color:{MUTE};margin-bottom:12px">Neither column is '
        f'wrong. The question is which one you want to maintain in six months.</div>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">'
        f'<div>{left}</div><div>{right}</div></div>', maxw=940))


_SHELF = [
    ("Search &amp; browsing", "DuckDuckGo · Tavily · Brave · Google Serper · Requests",
     "Answer questions about anything after the training cutoff."),
    ("Knowledge", "Wikipedia · arXiv · PubMed · Wolfram Alpha · SQL",
     "Look things up in a source you can cite."),
    ("Files &amp; data", "CSV · Pandas dataframe · file system · S3 · Google Drive",
     "Read and write the things the work actually lives in."),
    ("Code", "Python REPL · shell · Riza · E2B sandbox",
     "Compute rather than guess — the fix for arithmetic."),
    ("Products", "Gmail · Slack · GitHub · Jira · Notion · Twilio",
     "Do the thing, not just describe it."),
    ("Anything else", "MCP servers",
     "Someone else's tools, in any language, over one protocol."),
]


def tool_catalogue():
    rows = "".join(
        f'<div style="display:flex;gap:14px;padding:10px 0;border-bottom:1px solid #f0f1f6">'
        f'<div style="width:150px;font-weight:700;font-size:13px;color:{INK}">{a}</div>'
        f'<div style="flex:1"><div style="font-family:ui-monospace,monospace;font-size:11.5px;'
        f'color:{ACC}">{b}</div>'
        f'<div style="font-size:12.5px;color:#555;margin-top:2px">{c}</div></div></div>'
        for a, b, c in _SHELF)
    _show(_card(
        f'<div style="font-weight:800;font-size:15px;color:{INK}">The shelf</div>'
        f'<div style="font-size:12.5px;color:{MUTE};margin-bottom:6px">A few hundred tools '
        f'already exist, maintained by people who are not you. Two of them are one import '
        f'away in the next cell.</div>{rows}'))


def mcp_diagram():
    """The translation layer, both directions — which is all an MCP server is."""
    _show(_card(f"""
<div style="font-weight:800;font-size:15px;color:{INK}">The layer in the middle</div>
<div style="font-size:12.5px;color:{MUTE};margin-bottom:16px">One side speaks text. The other
side speaks Python objects. Somebody has to translate, in <b>both</b> directions.</div>
<div style="display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:14px;
font-size:12px">
  <div style="border:1px solid #e2e5ef;border-radius:10px;padding:12px 14px;background:#fbfbfd">
    <b>your agent</b><br><span style="color:{MUTE}">only ever emits and reads<br>
    <b style="color:{ACC}">text</b> — and, if you ask nicely, <b style="color:{ACC}">JSON</b>
    </span></div>
  <div style="display:grid;gap:14px;justify-items:center;color:{MUTE};font-size:11.5px">
    <div style="text-align:center"><span style="color:{ACC};font-weight:800;font-size:15px">
      &larr;</span><br>objects &rarr; text<br><span style="color:{MUTE}">so it can be read</span></div>
    <div style="text-align:center"><span style="color:{ACC2};font-weight:800;font-size:15px">
      &rarr;</span><br>JSON &rarr; objects<br><span style="color:{MUTE}">so it can be run</span></div>
  </div>
  <div style="border:1px solid #e2e5ef;border-radius:10px;padding:12px 14px;background:#fbfbfd">
    <b>your service</b><br><span style="color:{MUTE}">a normal Python program:<br>
    <b style="color:{ACC2}">objects</b> in, <b style="color:{ACC2}">objects</b> out,<br>
    written before agents existed</span></div>
</div>
<div style="border:2px solid {ACC};border-radius:10px;padding:11px 14px;background:#f4f5ff;
margin-top:14px;font-size:12.5px;line-height:1.6">
  <b>MCP</b> is that layer, given a standard shape — a small program that advertises its tools,
  their JSON argument schemas and their descriptions over stdio or HTTP. You were going to have
  to write both directions anyway. Writing them <i>as an MCP server</i> costs the same and
  means <b>any</b> agent, in any framework, in any language, can now use your service.</div>
<div style="font-size:12.5px;color:#444;line-height:1.65;margin-top:12px">
Which is also why you can consume other people's: a TypeScript server, or a vendor's hosted one
&mdash; Stripe, Sentry, Linear, GitHub &mdash; is the identical two directions, written by the
people who own the system.</div>"""))


_HARNESSES = [
    ("Classic ReAct", "#c0554e",
     "The model writes <code>Thought / Action / Action Input</code> as plain text and a "
     "parser reads it back.",
     ["works with any model that can produce text",
      "the transcript reads like reasoning, which is nice to teach with",
      "arguments are guessed from prose, so multi-argument calls go wrong",
      "a malformed line costs a whole turn"]),
    ("Tool calling", "#2e7d5b",
     "The model emits a structured call. The API validates it against your schema before "
     "Python ever sees it.",
     ["no parsing layer, so no parsing bugs",
      "wrong arguments come back as a type error, not as confident nonsense",
      "fewer wasted steps",
      "needs a model trained for it — all the current ones are"]),
    ("Two-pass", "#5b53a8",
     "<b>Two agents, in a row.</b> The first gets every tool <i>except</i> betting and must "
     "write up what it found. Those notes — and nothing else — are handed to a second agent, "
     "which gets the betting tool and no way to look anything up.",
     ["the second agent cannot bet before the reading is done: it has no other tools",
      "the notes in between are a plain-text artefact you can read and diff between runs",
      "two model calls instead of one, so slower and dearer",
      "whatever the first agent failed to write down does not exist to the second"]),
]


def harness_diagram():
    cols = "".join(
        f'<div style="border:1px solid #e2e5ef;border-left:3px solid {colour};'
        f'border-radius:10px;padding:13px">'
        f'<div style="font-weight:800;font-size:13.5px;color:{colour}">{name}</div>'
        f'<div style="font-size:12.5px;color:#444;margin:6px 0 9px;line-height:1.55">{blurb}'
        f'</div><ul style="margin:0;padding-left:17px;font-size:12px;color:#555;'
        f'line-height:1.7">' + "".join(f"<li>{p}</li>" for p in points) + "</ul></div>"
        for name, colour, blurb, points in _HARNESSES)
    _show(_card(
        f'<div style="font-weight:800;font-size:15px;color:{INK}">Three harnesses</div>'
        f'<div style="font-size:12.5px;color:{MUTE};margin-bottom:12px">Same model, same '
        f'tools, same prompt. The harness is the loop around them, and swapping it changes '
        f'the transcript more than most prompt edits do.</div>'
        f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">{cols}</div>',
        maxw=980))


# ===================================================================== Part 2 cards
def signal_ladder():
    """The calibration table, as a chart. Numbers come from galactic.sim."""
    from galactic.sim import CALIBRATION, CALIBRATION_LABELS, CALIBRATION_NOTE

    rows = []
    span = max(abs(v[1]) for v in CALIBRATION.values())
    for key, (ev, roi, ci, pwin, hit) in CALIBRATION.items():
        w = 50 * abs(roi) / span
        left, width, colour = ((50 - w, w, NO) if roi < 0 else (50, w, OK))
        rows.append(
            f'<div style="display:flex;align-items:center;gap:12px;padding:5px 0">'
            f'<div style="width:280px;font-size:12.5px">{CALIBRATION_LABELS[key]}</div>'
            f'<div style="flex:1;position:relative;height:16px;background:#f6f7fb;'
            f'border-radius:4px">'
            f'<div style="position:absolute;left:50%;top:0;bottom:0;width:1px;'
            f'background:#d6d9e6"></div>'
            f'<div style="position:absolute;left:{left}%;width:{width}%;top:3px;height:10px;'
            f'background:{colour};border-radius:3px"></div></div>'
            f'<div style="width:64px;text-align:right;font-family:ui-monospace,monospace;'
            f'font-size:12px;color:{colour};font-weight:700">{roi:+.0%}</div>'
            f'<div style="width:78px;text-align:right;font-size:11.5px;color:{MUTE}">'
            f'{pwin:.0%} profit</div></div>')
    _show(_card(
        f'<div style="font-weight:800;font-size:15px;color:{INK}">What each piece of '
        f'information is worth</div>'
        f'<div style="font-size:12.5px;color:{MUTE};margin-bottom:10px">Mean return on a '
        f'1,000 GC bankroll, over 150 independent tournaments.</div>'
        f'{"".join(rows)}'
        f'<div style="font-size:12.5px;color:#444;line-height:1.65;margin-top:14px;'
        f'border-top:1px solid #f0f1f6;padding-top:12px">{CALIBRATION_NOTE}</div>', maxw=940))


def edge_vs_variance(n: int = 400):
    """Where a single tournament lands, given a genuine edge. Matplotlib."""
    import numpy as np
    import matplotlib.pyplot as plt

    g = np.random.default_rng(7)
    # 13 bets a tournament at ~10% of bankroll, 17% edge, prices around 2.0
    def run(edge):
        b = np.full(n, 1000.0)
        for _ in range(13):
            p = 0.5 + edge / 2
            won = g.random(n) < p
            stake = b * 0.10
            b = b - stake + won * stake * 2.0
        return b

    fig, ax = plt.subplots(figsize=(8, 3.1))
    for edge, colour, label in ((-0.105, "#e07a7a", "no edge (backing favourites)"),
                                (0.175, "#46b46e", "a 17% edge (informed)")):
        ax.hist(run(edge), bins=45, alpha=.62, color=colour, label=label)
    ax.axvline(1000, color="#444", lw=1.2, ls="--")
    ax.set_xlabel("bankroll after one tournament (GC)")
    ax.set_ylabel("tournaments")
    ax.set_title("A real edge, and one tournament's worth of noise", fontsize=11)
    ax.legend(fontsize=9, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    plt.show()
    print("The green distribution is genuinely better. It also overlaps the red one almost "
          "completely.\nThat overlap is why you cannot judge a prompt from a single run.")


def the_whole_point():
    """The four things worth carrying out of the room, as one card."""
    items = [
        ("🧱", "A framework is plumbing you did not write",
         "The schema, the loop, the retries and the step limit are identical in every agent "
         "ever built, and wrong in half of them. Reach for the framework and you are left "
         "holding the only part that was ever yours: <b>the function that does the thing</b>.",
         ACC),
        ("🗣️", "Agents earn their keep where language and judgement meet",
         "Nothing here needed an agent to compute a number — a script does that better. It "
         "needed something that could <b>read a rulebook, read a tabloid, and work out which "
         "of the two mattered</b>. That is the shape of problem worth pointing one at.",
         ACC2),
        ("🎲", "One run tells you almost nothing",
         "Same prompt, same tools, same prices, three runs — and bankrolls hundreds of credits "
         "apart. Before you conclude that a new harness or a new model is better, "
         "<b>measure the spread, not the winner</b>. A single A/B of one run each is noise "
         "with a conclusion attached.",
         OK),
        ("🧰", "Tool choice is a dial, and both ends are bad",
         "Too few tools and the agent cannot learn the thing that decides the answer. Too many "
         "and the signal is buried in plausible noise it has to read anyway. <b>Every tool you "
         "add is also prompt you are spending</b>.",
         "#c0554e"),
    ]
    rows = "".join(
        f'<div style="display:flex;gap:14px;padding:14px 0;border-top:1px solid #f0f1f6">'
        f'<div style="flex:0 0 34px;font-size:22px;line-height:1.1">{glyph}</div>'
        f'<div><div style="font-weight:800;font-size:13.5px;color:{colour};margin-bottom:4px">'
        f'{title}</div>'
        f'<div style="font-size:12.5px;color:#444;line-height:1.65">{body}</div></div></div>'
        for glyph, title, body, colour in items)
    _show(_card(
        f'<div style="font-weight:800;font-size:15px;color:{INK}">The whole point, in four '
        f'lines</div>'
        f'<div style="font-size:12.5px;color:{MUTE};margin-bottom:4px">You will forget the '
        f'sport. These are the bits that transfer.</div>{rows}', maxw=880))


# ===================================================================== quizzes
_MC = {
    "framework": (
        "🧠 Quick check — what does the framework actually save you?",
        "You have already written an agent loop by hand this morning. Given that, what is the "
        "strongest reason to reach for LangChain on the next one?",
        [
            "It makes the model reason better, because the prompts are written by experts.",
            "It is faster at inference, because the framework batches the calls.",
            "It removes the schema, the loop and the error handling — the parts that are "
            "identical in every agent and wrong in half of them.",
            "It avoids vendor lock-in, since a framework agent runs without an API key.",
        ], 2,
        "The model is the same model. What changes is how much undifferentiated plumbing you "
        "own: schema generation, the tool-call loop, retries, step limits, streaming. Those "
        "are the same in every project, and they are where hand-rolled agents break."),

    "mcp": (
        "🧠 Quick check — what problem does MCP solve?",
        "Your desk already has <code>place_bets(selections, stake_each)</code>, and it works. "
        "What does putting an MCP server in front of it actually add?",
        [
            "It lets the model call the Python function directly, with nothing in between.",
            "It caches what the function returns, so repeated calls cost less.",
            "A published JSON shape the model can emit, and a translation into the arguments "
            "the function already takes — written once, for any agent that speaks the protocol.",
            "It rewrites the function so its arguments are strings, which is what models "
            "produce anyway.",
        ], 2,
        "The two directions do not go away: something has to turn objects into text on the way "
        "out and the model's JSON into arguments on the way in. You were writing that anyway. "
        "Writing it as an MCP server costs the same and means anyone's agent — any framework, "
        "any language — can use your service, which is why the vendors now ship their own."),

    "seeding": (
        "🧠 Quick check — the table says Andromeda finished top. How much should that move "
        "your price?",
        "Andromeda Asteroids won the regular season on points. Every side played the same "
        "seven opponents. What is the honest read?",
        [
            "Some, but less than it looks: seven matches is a small sample, and the table "
            "weights an early win exactly as heavily as a late one.",
            "A great deal — a full round robin where everyone plays everyone is the fairest "
            "measure available, so the table is close to the truth.",
            "None at all — regular-season form has no bearing on knockout football.",
            "It depends entirely on goal difference, which is the more reliable column.",
        ], 0,
        "It is real evidence and it is weak evidence. Seven matches is thin, and a season "
        "total cannot tell you a side has changed since. Anything that measures the last few "
        "weeks — recent results, the scrim block — sees things the table structurally cannot."),

    "subskills": (
        "🧠 Quick check — you switch off one sub-skill. What has actually changed?",
        "In the launcher you untick <code>player_stats → Discipline</code> and run the same "
        "prompt with the same model. What is different about the run?",
        [
            "The agent can still ask for discipline data, but the tool politely refuses and "
            "the agent has to work around it.",
            "Nothing changes unless the prompt happens to mention fouls.",
            "The agent has no way to learn that prolonged-touch fouls exist: the mode is gone "
            "from the schema and every mention of it is gone from the tool's description.",
            "The data is still returned, but the agent is instructed not to use it.",
        ], 2,
        "A tool's description <i>is</i> part of the prompt. Removing a sub-skill removes the "
        "sentence that describes it, so the concept never enters the agent's context at all — "
        "and the mode is dropped from the argument enum, so calling it is not possible either."),
}

_TF = {
    "rules": ("🧠 The rulebook — click every statement you think is TRUE", [
        ("A player may legally strike the ball with a tentacle.", True),
        ("A 340 kg side has a physical advantage over a 70 kg side once the match starts.",
         False),
        ("Each side defends two goals and two nests.", True),
        ("Handling the ball is a foul.", False),
        ("Repeated prolonged-touch offences can cost a side a player for the rest of the "
         "tournament.", True),
        ("The normalisation protocols also equalise first-touch control, so touch ratings "
         "can be ignored.", False),
        ("Playoff matches are played at a neutral venue.", True),
        ("A side that loses its opening playoff match is eliminated.", False),
    ]),

    "signal": ("🧠 Signal and noise — click every statement you think is TRUE", [
        ("A club's mean raw strength is useful for predicting playoff results.", False),
        ("A story about three first-choice starters being ruled out should move a price.",
         True),
        ("Possession retention over ten scrims is a steadier measure than the scrim "
         "scorelines.", True),
        ("Every article on the news site concerns something that affects results.", False),
        ("The number of limbs a squad averages is published by the League, so it must bear "
         "on the outcome.", False),
        ("Two clubs can have identical league positions and quite different current "
         "strength.", True),
    ]),

    "agents": ("🧠 Agents and harnesses — click every statement you think is TRUE", [
        ("The harness can change how many steps an agent takes without the prompt changing.",
         True),
        ("Under classic ReAct, the tool's arguments arrive as text that something has to "
         "parse.", True),
        ("A tool's docstring is documentation for you, not context for the model.", False),
        ("Running the same agent setup three times can produce three different sets of "
         "bets.", True),
        ("Giving an agent more tools reliably improves its decisions.", False),
        ("A structured tool call can be rejected for a type error before any of your code "
         "runs.", True),
        ("Switching harness requires switching model as well.", False),
        ("An agent that finds no good bet and places none has failed at its task.", False),
    ]),
}

_FLASH = [
    # --- the sport (balanced 8/8)
    ("A side fields eleven players.", True),
    ("There are two nests and two goals to defend.", True),
    ("A nest is worth more than a goal.", False),
    ("The ball may be touched with any part of the body.", True),
    ("Holding the ball for two seconds is legal.", False),
    ("Prolonged touch is a foul regardless of which limb commits it.", True),
    ("The normalisation protocols equalise body mass across the field.", True),
    ("The protocols also equalise ball control.", False),
    ("Playoff matches can end level.", False),
    ("The regular season is a single round robin of seven matches each.", True),
    ("The playoffs are single elimination.", False),
    ("Playoff seeding comes from the final league table.", True),
    ("Raw strength is published by the League.", True),
    ("Because raw strength is published, it predicts results.", False),
    ("Scrims are official fixtures and count towards the table.", False),
    ("Scrims are played at full strength.", True),
    # --- judgement (balanced 3/3). Not odds arithmetic: this notebook is about agents,
    # and a manager does not need to compute an implied probability to learn any of it.
    ("Backing the favourite every time is still a losing strategy.", True),
    ("A market that has closed can be bet into again if you have the market id.", False),
    ("Plausible information that turns out to be irrelevant is harmless.", False),
    ("A side can finish top of the table and still be badly overpriced.", True),
    ("An agent that places no bet has necessarily failed.", False),
    ("Evidence that is published is not automatically evidence that predicts.", True),
    # --- agents (balanced 7/7)
    ("A tool's description is part of what the model reads.", True),
    ("Removing a sub-skill only affects documentation, not what the model can call.", False),
    ("The harness is the loop around the model, not the model itself.", True),
    ("Classic ReAct parses the model's text to work out which tool to call.", True),
    ("A tool-calling agent needs a parser for the model's action lines.", False),
    ("LangChain generates a tool's argument schema from its type hints.", True),
    ("An agent given no tools can still look things up.", False),
    ("The same prompt and model can produce different tool calls on two runs.", True),
    ("Temperature zero makes an agent fully deterministic end to end.", False),
    ("A two-pass harness can be made structurally unable to act before it reads.", True),
    ("More tools always means better decisions.", False),
    ("An MCP server has to be written in Python.", False),
    ("An MCP server runs as a separate process from your agent.", True),
    ("One agent run is enough to judge whether a prompt is good.", False),
    ("Turning an object into text for the agent, and turning the agent's JSON into arguments, "
     "are two separate jobs.", True),
    ("Once a service exists in Python, an agent can call it with nothing in between.", False),
    ("A tool that returns accurate but irrelevant detail still costs the agent context.", True),
    ("A tool the agent never calls costs nothing, because its description is not sent.", False),
    ("The protocol decides which of your tools the agent should call.", False),
]


# ===================================================================== renderers
def _uid(prefix: str, payload) -> str:
    return f"{prefix}_{abs(hash(_json.dumps(payload, default=str))) % 10 ** 8}"


_QUIZ_CSS = """
#__UID__{font-family:__FONT__;border:1px solid #e6e8ee;border-radius:14px;padding:16px;
  max-width:820px;background:#fff}
#__UID__ .h{font-weight:800;font-size:14.5px;margin-bottom:4px;color:#2b2d6b}
#__UID__ .q{color:#444;font-size:13px;margin-bottom:12px;line-height:1.6}
#__UID__ .o{display:flex;align-items:flex-start;gap:10px;border:1px solid #e2e5ef;
  border-radius:10px;padding:10px 12px;margin-bottom:8px;cursor:pointer;font-size:13px;
  line-height:1.55;transition:.12s}
#__UID__ .o:hover{border-color:#7c4dbd;background:#faf9ff}
#__UID__ .o.sel{border-color:#7c4dbd;background:#f2edff}
#__UID__ .o.ok{border-color:#46b46e;background:#e7f7ec}
#__UID__ .o.no{border-color:#e07a7a;background:#fdecec}
#__UID__ .btn{cursor:pointer;border:none;border-radius:8px;padding:9px 18px;font-size:13px;
  font-weight:700;color:#fff;background:linear-gradient(135deg,#4c5bd4,#7c4dbd);margin-top:6px}
#__UID__ .rev{font-size:12.5px;color:#444;margin-top:10px;line-height:1.6}
#__UID__ input[type=text]{border:1px solid #e2e5ef;border-radius:8px;padding:7px 10px;
  font-size:13px;width:90px;font-family:ui-monospace,monospace}
#__UID__ .dot{width:14px;height:14px;border-radius:50%;border:2px solid #c9cee0;flex:0 0 14px;
  margin-top:2px}
#__UID__ .o.sel .dot{border-color:#7c4dbd;background:#7c4dbd}
"""


def mc_quiz(key: str):
    title, question, options, answer, reveal = _MC[key]
    uid = _uid("mc", (question, options))
    data = _json.dumps({"opts": options, "ans": answer, "reveal": reveal})
    _show(f"""<style>{_QUIZ_CSS.replace("__UID__", uid).replace("__FONT__", FONT)}</style>
<div id="{uid}"><div class="h">{title}</div><div class="q">{question}</div>
<div class="list"></div><button class="btn">Check my answer</button>
<div class="rev"></div></div>
<script>(function(){{
  const D={data}, root=document.getElementById("{uid}");
  let idx=D.opts.map((_,i)=>i);
  for(let i=idx.length-1;i>0;i--){{const j=Math.floor(Math.random()*(i+1));
    [idx[i],idx[j]]=[idx[j],idx[i]];}}
  const list=root.querySelector(".list");
  idx.forEach(o=>{{const e=document.createElement("div");e.className="o";e.dataset.i=o;
    e.innerHTML='<span class="dot"></span><span>'+D.opts[o]+'</span>';list.appendChild(e);}});
  const opts=list.querySelectorAll(".o"); let sel=null;
  opts.forEach(o=>o.addEventListener("click",()=>{{sel=+o.dataset.i;
    opts.forEach(x=>x.classList.remove("sel","ok","no"));o.classList.add("sel");
    root.querySelector(".rev").textContent="";}}));
  root.querySelector(".btn").addEventListener("click",()=>{{
    if(sel===null){{root.querySelector(".rev").textContent="Pick one first.";return;}}
    opts.forEach(o=>{{const i=+o.dataset.i;o.classList.remove("sel");
      if(i===D.ans)o.classList.add("ok");else if(i===sel)o.classList.add("no");}});
    root.querySelector(".rev").innerHTML=(sel===D.ans?"✅ Correct. ":"❌ Not quite. ")+D.reveal;
  }});}})();</script>""")


def true_false_quiz(key: str):
    title, statements = _TF[key]
    uid = _uid("tf", (title, [s for s, _ in statements]))
    data = _json.dumps([{"t": s, "v": v} for s, v in statements])
    _show(f"""<style>{_QUIZ_CSS.replace("__UID__", uid).replace("__FONT__", FONT)}</style>
<div id="{uid}"><div class="h">{title}</div>
<div class="q">Click every statement you think is true, then check.</div>
<div class="list"></div><button class="btn">Check</button><div class="rev"></div></div>
<script>(function(){{
  const D={data}, root=document.getElementById("{uid}");
  let idx=D.map((_,i)=>i);
  for(let i=idx.length-1;i>0;i--){{const j=Math.floor(Math.random()*(i+1));
    [idx[i],idx[j]]=[idx[j],idx[i]];}}
  const list=root.querySelector(".list");
  idx.forEach(o=>{{const e=document.createElement("div");e.className="o";e.dataset.i=o;
    e.innerHTML='<span class="dot"></span><span>'+D[o].t+'</span>';list.appendChild(e);}});
  const opts=list.querySelectorAll(".o");
  opts.forEach(o=>o.addEventListener("click",()=>o.classList.toggle("sel")));
  root.querySelector(".btn").addEventListener("click",()=>{{
    let right=0;
    opts.forEach(o=>{{const d=D[+o.dataset.i], picked=o.classList.contains("sel");
      o.classList.remove("sel");
      if(picked===d.v)right++;
      if(d.v)o.classList.add("ok"); else if(picked)o.classList.add("no");}});
    root.querySelector(".rev").innerHTML=right+" / "+D.length+" correct"+
      (right===D.length?" 🎉":" — green is what is actually true.");
  }});}})();</script>""")


def flash_quiz(n_to_pass: int = 12, lives: int = 3, seconds: int = 10):
    """Timed true/false 'final boss'.

    Deliberately the same component as WE4's — same card, same outlined TRUE/FALSE pair, same
    heart counter, same gradient clock, same end screen with a replay button. A participant
    meets this quiz at the end of several notebooks in the weekend and it should be the same
    object each time; a bespoke one reads as a different course.

    All logic runs in the browser, so nothing in this cell reveals an answer.
    """
    pool = [{"t": t, "a": bool(a)} for t, a in _FLASH]
    data = {"pool": pool, "need": int(n_to_pass), "lives0": int(lives), "secs": int(seconds)}
    uid = _uid("flash", [t for t, _ in _FLASH])
    tmpl = r'''
<style>
#__UID__{font-family:__FONT__;border:1px solid #e6e8ee;border-radius:16px;padding:20px;max-width:640px;background:#fff;position:relative}
#__UID__ .fq-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}
#__UID__ .fq-title{font-weight:800;font-size:16px;color:#2b2d6b}
#__UID__ .fq-lives{font-size:18px;letter-spacing:2px}
#__UID__ .fq-meta{display:flex;justify-content:space-between;font-size:12.5px;color:#666;margin-bottom:10px}
#__UID__ .fq-bar{height:8px;border-radius:5px;background:#eceeffa8;overflow:hidden;margin-bottom:16px}
#__UID__ .fq-bar > div{height:100%;width:100%;background:linear-gradient(90deg,#46b46e,#e0a500,#e07a7a);transition:width .1s linear}
#__UID__ .fq-stmt{font-size:16px;line-height:1.5;color:#1c1e2a;min-height:64px;display:flex;align-items:center;padding:6px 2px}
#__UID__ .fq-btns{display:flex;gap:12px;margin-top:10px}
#__UID__ .fq-btn{flex:1;cursor:pointer;border:2px solid;border-radius:12px;padding:14px;font-size:15px;font-weight:800;background:#fff;transition:.1s}
#__UID__ .fq-true{border-color:#46b46e;color:#1d7a46}#__UID__ .fq-true:hover{background:#e7f7ec}
#__UID__ .fq-false{border-color:#e07a7a;color:#b23b34}#__UID__ .fq-false:hover{background:#fdecec}
#__UID__ .fq-flash{font-size:13px;font-weight:700;margin-top:12px;min-height:20px}
#__UID__ .fq-end{text-align:center;padding:14px 6px}
#__UID__ .fq-end h3{font-size:22px;margin:6px 0}
#__UID__ .fq-restart{cursor:pointer;border:none;border-radius:10px;padding:10px 20px;font-size:14px;font-weight:700;color:#fff;background:linear-gradient(135deg,#4c5bd4,#7c4dbd);margin-top:8px}
</style>
<div id="__UID__">
  <div class="fq-top">
    <div class="fq-title">🏁 Final boss — beat the clock</div>
    <div class="fq-lives"></div>
  </div>
  <div class="fq-meta"><span class="fq-prog"></span><span class="fq-time"></span></div>
  <div class="fq-bar"><div></div></div>
  <div class="fq-body">
    <div class="fq-stmt"></div>
    <div class="fq-btns">
      <button class="fq-btn fq-true">TRUE</button>
      <button class="fq-btn fq-false">FALSE</button>
    </div>
    <div class="fq-flash"></div>
  </div>
</div>
<script>
(function(){
  const D=__DATA__, root=document.getElementById("__UID__");
  const $=s=>root.querySelector(s);
  const bar=$(".fq-bar>div");
  const stmt=()=>$(".fq-stmt"), flash=()=>$(".fq-flash");
  const livesEl=$(".fq-lives"), progEl=$(".fq-prog"), timeEl=$(".fq-time");
  let order=[], ptr=0, correct=0, lives=D.lives0, timer=null, deadline=0, locked=false;
  function shuffle(a){for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;}
  function reorder(){order=shuffle(D.pool.map((_,i)=>i));ptr=0;}
  function renderHUD(){
    livesEl.textContent="❤️".repeat(lives)+"🖤".repeat(D.lives0-lives);
    progEl.textContent="Correct: "+correct+" / "+D.need;
  }
  function nextQ(){
    if(ptr>=order.length){reorder();}
    locked=false; flash().textContent=""; flash().style.color="";
    root.querySelectorAll(".fq-btn").forEach(b=>b.disabled=false);
    stmt().textContent=D.pool[order[ptr]].t;
    startTimer();
  }
  function startTimer(){
    deadline=Date.now()+D.secs*1000;
    clearInterval(timer);
    timer=setInterval(()=>{
      const left=Math.max(0,deadline-Date.now());
      bar.style.width=(100*left/(D.secs*1000))+"%";
      timeEl.textContent=(left/1000).toFixed(1)+"s";
      if(left<=0){clearInterval(timer); timeout();}
    },80);
  }
  function answer(val){
    if(locked)return; locked=true; clearInterval(timer);
    root.querySelectorAll(".fq-btn").forEach(b=>b.disabled=true);
    const q=D.pool[order[ptr]];
    if(val===q.a){correct++; flash().style.color="#1d7a46"; flash().textContent="✅ Correct!";}
    else{lives--; flash().style.color="#b23b34"; flash().textContent="❌ Wrong — it was "+(q.a?"TRUE":"FALSE")+".";}
    ptr++; renderHUD(); advance();
  }
  function timeout(){
    if(locked)return; locked=true;
    root.querySelectorAll(".fq-btn").forEach(b=>b.disabled=true);
    lives--; ptr++; flash().style.color="#b23b34"; flash().textContent="⏱️ Out of time — life lost.";
    renderHUD(); advance();
  }
  function advance(){
    if(correct>=D.need){return finish(true);}
    if(lives<=0){return finish(false);}
    setTimeout(nextQ, 850);
  }
  function finish(won){
    clearInterval(timer);
    root.querySelector(".fq-body").innerHTML=
      '<div class="fq-end"><h3>'+(won?"🎉 Passed!":"💀 Out of lives")+'</h3>'
      +'<div style="font-size:14px;color:#555">'
      +(won?("You cleared "+correct+" questions. You have the sport, the tools and the harnesses — go and bet."):
            ("You reached "+correct+" / "+D.need+" correct. Scroll back up — the rulebook is the bit most people skip."))
      +'</div><button class="fq-restart">Play again</button></div>';
    root.querySelector(".fq-restart").addEventListener("click",start);
    timeEl.textContent=""; bar.style.width="0%";
  }
  function start(){
    correct=0; lives=D.lives0; reorder();
    root.querySelector(".fq-body").innerHTML=
      '<div class="fq-stmt"></div><div class="fq-btns">'
      +'<button class="fq-btn fq-true">TRUE</button>'
      +'<button class="fq-btn fq-false">FALSE</button></div>'
      +'<div class="fq-flash"></div>';
    bind(); renderHUD(); nextQ();
  }
  function bind(){
    root.querySelector(".fq-true").addEventListener("click",()=>answer(true));
    root.querySelector(".fq-false").addEventListener("click",()=>answer(false));
  }
  start();
})();
</script>'''
    _show(tmpl.replace("__UID__", uid).replace("__FONT__", FONT)
              .replace("__DATA__", _json.dumps(data)))


def quiz_pool_balance() -> str:
    """Used by the test suite: the flash pool must not be answerable by guessing 'true'."""
    t = sum(1 for _s, v in _FLASH if v)
    return f"{t} true / {len(_FLASH) - t} false"
