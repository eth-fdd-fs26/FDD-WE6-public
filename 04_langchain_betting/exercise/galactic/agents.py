"""Three ways to run the same tools with the same model, and the prompts to run them on.

The harness is the part people forget to vary. It is not the model and it is not the prompt;
it is the loop that decides how the model is allowed to think and act. Swapping it, with
everything else held fixed, changes the transcript more than most prompt edits do.

  react_classic   The 2022 design: one text stream, the model writes
                  "Thought / Action / Action Input" and a parser reads it back. It works, and
                  you will watch it fumble a multi-argument call, which is exactly why the
                  next one exists.
  tool_calling    The modern default: the model emits structured tool calls the API itself
                  validates. Fewer steps, no parsing, and a wrong argument comes back as a
                  type error rather than as confident nonsense.
  two_pass        Research, then decide. Pass one gets read-only tools and must return
                  structured notes; pass two gets the notes plus the betting tool and nothing
                  else. Longer to run, but it cannot bet before it has read, and the notes
                  are a machine-readable artefact you can diff across runs.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Literal

from . import config as C

Harness = Literal["react_classic", "tool_calling", "two_pass"]

HARNESS_LABELS = {
    "react_classic": "Classic ReAct (text-parsed)",
    "tool_calling": "Tool calling (structured)",
    "two_pass": "Two-pass: research → decide",
}


# ===================================================================== the model
def get_api_key(explicit: str | None = None) -> str:
    """Colab secret, then environment. Raises rather than limping on with no key."""
    if explicit:
        return explicit.strip()
    try:
        from google.colab import userdata
        key = userdata.get("OPENROUTER_API_KEY")
        if key:
            return key.strip()
    except Exception:
        pass
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "No OpenRouter API key found.\n"
            "  · In Colab: open the 🔑 Secrets panel, add OPENROUTER_API_KEY, and toggle "
            "notebook access on.\n"
            "  · Locally:  export OPENROUTER_API_KEY=sk-or-...\n"
            "Get a key at https://openrouter.ai/keys")
    return key


def build_model(api_key: str | None = None, model: str | None = None,
                temperature: float | None = None):
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=model or C.DEFAULT_MODEL,
        api_key=get_api_key(api_key),
        base_url=C.OPENROUTER_BASE_URL,
        temperature=C.DEFAULT_TEMPERATURE if temperature is None else temperature,
        timeout=90,
        max_retries=2,
    )


def check_api_key(api_key: str | None = None, model: str | None = None) -> str:
    """One cheap call, so a bad key fails here rather than sixteen tool calls in."""
    llm = build_model(api_key, model, temperature=0)
    llm.invoke("Reply with the single word: ready")
    return f"OpenRouter reachable · model {model or C.DEFAULT_MODEL} ✅"


# ===================================================================== prompts
SYSTEM = """You are a betting analyst for the Galactic Premier League playoffs.

You have a fixed bankroll and a set of open markets. Your job is to find prices that are
wrong and stake against them — not to back whoever is most likely to win. A short price on a
strong side is worth nothing; a long price on a side that is better than the market thinks is
worth everything.

Work in this order, and do not skip the first step:
1. Read the rulebook. It is a genuinely unusual sport and it decides which of the published
   statistics can possibly bear on a result.
2. Gather evidence with your other tools.
3. Only then place bets, and only where you think the price is wrong.

Never stake more than you have. Say what you are betting and why, in one sentence per bet."""

PROMPTS = {
    "value_hunter": """Round {round} of the Galactic Premier League playoffs is open and you
have {wallet:.0f} {currency}.

Find the mispriced selections and back them. Read the rules first, then research the clubs
involved in the open markets, then bet. Stake between 5% and 20% of your bankroll per bet, and
place no more than three bets. If you cannot find a price you think is wrong, place nothing
and say so.""",

    "favourites": """Round {round} is open and you have {wallet:.0f} {currency}. Back the
favourite in every open market — the selection with the shortest odds — staking 10% of your
bankroll on each. Do not research anything.""",

    "news_first": """Round {round} is open and you have {wallet:.0f} {currency}.

Start with the news. Find every story about squad availability, work out which of them
actually changes a side's strength and which is filler, then check whether the prices have
moved to reflect it. Bet only where you think the market has under-reacted.""",

    "cautious": """Round {round} is open and you have {wallet:.0f} {currency}.

Be conservative. Research thoroughly, then place at most ONE bet, and only if you believe your
own estimate of the probability beats the price implied by the odds by more than ten
percentage points. Explain your estimate before you bet. If nothing clears that bar, bet
nothing — that is a valid answer.""",

    "hunch": """Round {round} is open and you have {wallet:.0f} {currency}. Look at the open
markets and back whichever teams you like the sound of. Trust your instincts.""",
}

PROMPT_LABELS = {
    "value_hunter": "Value hunter — read everything, bet the mispricings",
    "news_first": "News first — hunt for information the market hasn't priced",
    "cautious": "Cautious — one bet, only on a big edge",
    "favourites": "Favourite-backer — no research, back the short prices",
    "hunch": "On a hunch — no method at all",
}


def render_prompt(key_or_text: str, tournament) -> str:
    template = PROMPTS.get(key_or_text, key_or_text)
    return template.format(round=tournament.round, wallet=tournament.wallet,
                           currency=C.CURRENCY)


# ===================================================================== the harnesses
REACT_TEMPLATE = """Answer the following as best you can. You have access to these tools:

{tools}

Use this format, exactly:

Question: the input question you must answer
Thought: what to do next
Action: the action to take, one of [{tool_names}]
Action Input: a JSON object of arguments, e.g. {{"mode": "table"}}
Observation: the result
... (Thought/Action/Action Input/Observation can repeat)
Thought: I now know the final answer
Final Answer: your summary of the bets you placed and why

Write EITHER an Action and an Action Input, OR a Final Answer — never both in one message,
and never anything after them. Wait for the Observation before writing your next Thought.

Begin.

Question: {input}
Thought:{agent_scratchpad}"""


@dataclass
class AgentRun:
    harness: str
    output: str
    steps: int = 0
    error: str | None = None
    notes: list = field(default_factory=list)


def _legacy_adapters(tools):
    """Wrap structured tools so the classic text protocol can reach them.

    This is the tax the old design charges, and it is worth seeing rather than hiding.
    ReAct has the model *write out* its arguments as free text, and an output parser hands
    whatever it wrote to the tool as one string — so something has to sit in the middle and
    turn that string back into keyword arguments, guessing when it is malformed. The
    tool-calling harness needs none of this: the model emits a structured call and the API
    validates it before it ever reaches Python. Note that this adapter lives here, in the
    legacy harness, and not in ``tools.py``.
    """
    from langchain_core.tools import Tool

    def adapt(structured):
        def call(text: str):
            text = (text or "").strip().strip("`")
            try:
                args = json.loads(text) if text.startswith("{") else {"mode": text}
            except json.JSONDecodeError:
                return ("Could not parse that Action Input. It must be a JSON object, for "
                        f'example {{"mode": "table"}}. You sent: {text!r}')
            if not isinstance(args, dict) or "mode" not in args:
                return 'Action Input must be a JSON object containing a "mode" key.'
            try:
                return structured.func(**args)
            except TypeError as exc:
                return f"Those arguments do not fit this tool: {exc}"
            except Exception as exc:                              # noqa: BLE001
                return f"{type(exc).__name__}: {exc}"
        return Tool(name=structured.name, func=call,
                    description=structured.description +
                    '\n\nAction Input must be a single JSON object, e.g. {"mode": "table"}.')

    return [adapt(t) for t in tools]


def _react(model, tools, system_prompt, max_steps, on_parse_error=None):
    from langchain_classic.agents import AgentExecutor, create_react_agent
    from langchain_core.prompts import PromptTemplate
    legacy = _legacy_adapters(tools)
    prompt = PromptTemplate.from_template(system_prompt + "\n\n" + REACT_TEMPLATE)

    def handle(exc):
        """Turn a parse failure into a correction the model can act on — and a trace card.

        This is not an error in the exercise; it is the exercise. Classic ReAct asks the
        model to write its action as prose and then parses that prose back, so a stray
        sentence, a missing ``Action Input:`` or a final answer arriving in the same breath
        as an action all land here. ``handle_parsing_errors`` accepts a callable, so instead
        of a bare "Invalid Format" we say what was wrong, and the trace records that a turn
        was spent on it. The tool-calling harness cannot reach this code at all, which is
        the comparison the notebook is asking you to make.
        """
        if on_parse_error is not None:
            on_parse_error(exc)
        return ("Your last message did not follow the format. Reply with exactly one of:\n"
                "  Action: <tool name>\n  Action Input: <a JSON object>\n"
                "or, if you are done:\n  Final Answer: <your summary>\n"
                "Do not write both in the same message, and write nothing after them.")

    return AgentExecutor(
        agent=create_react_agent(model, legacy, prompt),
        tools=legacy, max_iterations=max_steps,
        handle_parsing_errors=handle, return_intermediate_steps=True, verbose=False)


def _tool_calling(model, tools, system_prompt, max_steps):
    from langchain.agents import create_agent
    return create_agent(model=model, tools=tools, system_prompt=system_prompt)


class ResearchNote(dict):
    pass


TWO_PASS_RESEARCH = """You are researching, not betting. You have no betting tool.

Read the rulebook first, then gather evidence on the clubs in this round's open markets.
Finish with a short report: for each open market, your own estimate of each side's win
probability, the two or three pieces of evidence behind it, and how confident you are.
Do not recommend stakes."""

TWO_PASS_DECIDE = """Here are your analyst's research notes:

{notes}

You have {wallet:.0f} {currency} and can only place bets — you cannot look anything else up.
Use the notes and the market prices to decide. Bet only where the notes say the true
probability beats the price. State each bet in one sentence."""


def _parse_error_reporter(callbacks):
    """A hook that draws a parse failure on the trace, if there is a trace to draw on."""
    sinks = [cb for cb in (callbacks or []) if hasattr(cb, "add")]
    if not sinks:
        return None

    def report(exc):
        from html import escape
        for sink in sinks:
            sink.add("parse", "↩️ could not parse the model's action",
                     f"<pre>{escape(str(exc)[:400])}</pre>"
                     "<div class=\"foot\">This is the tax classic ReAct charges: the action "
                     "was written as prose and the parser could not read it back. The turn is "
                     "spent; the model is told the format again. Structured tool calling has "
                     "no equivalent failure.</div>")
    return report


def run_agent(harness: Harness, *, model, tools, prompt: str, tournament,
              callbacks=None, max_steps: int = C.DEFAULT_MAX_STEPS) -> AgentRun:
    """Run one harness to completion. Never raises — a failure comes back on ``.error`` so
    the launcher can show it as a card rather than a traceback."""
    cfg = {"callbacks": callbacks or [], "recursion_limit": max(2 * max_steps + 6, 30)}
    async_only = [t.name for t in tools if getattr(t, "func", None) is None
                  and getattr(t, "coroutine", None) is not None]
    if async_only:
        # MCP tools land here: they live at the end of an async transport and have no
        # synchronous implementation. This runner is sync because the launcher is driven
        # from a widget callback, so say so plainly rather than surfacing a bare
        # NotImplementedError from six frames down.
        return AgentRun(harness, "", error=(
            f"These tools are async-only and cannot be driven by the launcher: "
            f"{', '.join(async_only)}. Await the agent directly instead — "
            f"`await agent.ainvoke(...)` — as the MCP section of the notebook does."))
    try:
        if harness == "react_classic":
            ex = _react(model, tools, SYSTEM, max_steps,
                        on_parse_error=_parse_error_reporter(callbacks))
            res = ex.invoke({"input": prompt}, config=cfg)
            return AgentRun(harness, res.get("output", ""),
                            steps=len(res.get("intermediate_steps", [])))

        if harness == "tool_calling":
            agent = _tool_calling(model, tools, SYSTEM, max_steps)
            res = agent.invoke({"messages": [{"role": "user", "content": prompt}]},
                               config=cfg)
            msgs = res["messages"]
            calls = sum(len(getattr(m, "tool_calls", []) or []) for m in msgs)
            return AgentRun(harness, msgs[-1].content, steps=calls)

        if harness == "two_pass":
            from langchain.agents import create_agent
            read_only = [t for t in tools if t.name != "betting"]
            betting_only = [t for t in tools if t.name == "betting"]
            researcher = create_agent(model=model, tools=read_only,
                                      system_prompt=TWO_PASS_RESEARCH)
            r1 = researcher.invoke({"messages": [{"role": "user", "content": prompt}]},
                                   config=cfg)
            notes = r1["messages"][-1].content
            decide = TWO_PASS_DECIDE.format(notes=notes, wallet=tournament.wallet,
                                            currency=C.CURRENCY)
            decider = create_agent(model=model, tools=betting_only, system_prompt=SYSTEM)
            r2 = decider.invoke({"messages": [{"role": "user", "content": decide}]},
                                config=cfg)
            steps = sum(len(getattr(m, "tool_calls", []) or [])
                        for m in r1["messages"] + r2["messages"])
            return AgentRun(harness, r2["messages"][-1].content, steps=steps,
                            notes=[notes])

        raise ValueError(f"unknown harness {harness!r}")
    except Exception as exc:                     # noqa: BLE001 — surfaced in the UI
        return AgentRun(harness, "", error=f"{type(exc).__name__}: {exc}")


def build_agent(harness: Harness, model, tools, system_prompt: str = SYSTEM,
                max_steps: int = C.DEFAULT_MAX_STEPS):
    """The runnable itself, for a notebook cell that wants to poke at it directly."""
    return {"react_classic": _react, "tool_calling": _tool_calling,
            "two_pass": _tool_calling}[harness](model, tools, system_prompt, max_steps)


def summarise_tool_calls(run: AgentRun) -> str:
    return json.dumps({"harness": run.harness, "steps": run.steps,
                       "error": run.error}, indent=2)
