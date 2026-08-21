"""Four verbs: SAMPLE, MUTATE, EVALUATE, STORE.

Everything else in a system like AlphaEvolve is an implementation detail of this loop. It is
about forty lines and there is nothing hidden in it.

SAMPLE, and the machinery of MUTATE (the API call, assembling the prompt, splicing the reply
back into the program), live here, already written, because they are more interesting to
read than to type. Three things are authored in the notebook instead:

    EVALUATE       the score. Turns a candidate into one number the search can climb.
    STORE          the archive rule. Decides who gets to be a parent later.
    SYSTEM_PROMPT  MUTATE's brief: what the model may change, what is off limits, and how
                   it must reply. Assigned onto this module before the loop runs.

A run is fully recorded, so a run made on a laptop with an API key can be replayed in a room
where the network is not cooperating.
"""
from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import seed as seed_mod

RUNS_DIR = Path(__file__).parent / "runs"


# ===================================================================== what a candidate is
@dataclass
class Candidate:
    """One program, its score, and where it came from."""

    code: str
    score: float = 0.0
    generation: int = 0
    parent: int | None = None
    index: int = 0
    metrics: dict = field(default_factory=dict)
    note: str = ""

    @property
    def block(self) -> str:
        """Just the evolvable region — what actually differs between candidates."""
        return seed_mod.get_block(self.code)


# ===================================================================== behaviour cells
PARAM_BUCKETS = (50, 150, 300)      # edges; four cells in total
BUCKET_LABELS = ("tiny (≤50)", "small (51–150)", "medium (151–300)", "large (301+)")


def param_bucket(n_params: int) -> int:
    """Which size class a candidate belongs to — its coordinate in the archive.

    MAP-Elites needs a *behavioural* description of a program, separate from its score.
    Size is the one that matters here: it is what stops a 480-parameter program at 0.81
    from quietly deleting a 90-parameter program at 0.78, which is a trade you would very
    much like to still have on the table at the end of the run.

    Args:
        n_params: trainable parameter count.

    Returns:
        Cell index 0-3. See `BUCKET_LABELS`.
    """
    for i, edge in enumerate(PARAM_BUCKETS):
        if n_params <= edge:
            return i
    return len(PARAM_BUCKETS)


# ===================================================================== SAMPLE  (provided)
def sample(archive: dict, rng: random.Random) -> tuple[Candidate, list[Candidate]]:
    """Pick a parent to mutate, and a few rivals to show alongside it.

    Note what this deliberately does *not* do: always pick the best. Two thirds of the time
    it picks the champion of a random cell instead.

    Args:
        archive: cell key -> champion candidate.
        rng: seeded RNG, so a replayed run picks the same parents.

    Returns:
        `(parent, inspirations)`. The inspirations are other cells' champions, which is what
        makes the prompt show a fitness *landscape* rather than a single example (slide 12).
    """
    residents = list(archive.values())
    if rng.random() < 0.34:
        parent = max(residents, key=lambda c: c.score)      # exploit the leader
    else:
        parent = rng.choice(residents)                      # explore another cell

    rivals = [c for c in residents if c is not parent]
    rivals.sort(key=lambda c: c.score, reverse=True)
    top = rivals[:2]                                        # the two best
    diverse = rng.sample(rivals[2:], min(1, max(0, len(rivals) - 2))) if len(rivals) > 2 else []
    return parent, top + diverse                            # deliberately not all top


# ===================================================================== MUTATE  (provided)
# SYSTEM_PROMPT is MUTATE's brief: the standing instructions sent with every mutation call.
# It is authored in the notebook (Task 3), built from four provided parts, and assigned onto
# this module attribute before the loop runs: `loop.SYSTEM_PROMPT = <the string you built>`.
# `mutate` fills in `{cap}` with `.format(cap=cap)` at call time, so that placeholder must
# survive the notebook's concatenation. Left empty, `evolve` refuses to start rather than
# silently sending the model no instructions.
SYSTEM_PROMPT = ""


def build_prompt(parent: Candidate, inspirations: list[Candidate], cap: int,
                 failures: list[Candidate] | None = None) -> str:
    """Assemble the context the model mutates against.

    Slide 12 lists four ingredients; three of them are here (the fourth, an evolvable
    meta-prompt, is the thing OpenEvolve itself does not implement either):

      parent        the program to be rewritten, in full
      inspirations  a few rivals *with their scores attached*, so the model sees a gradient
      artifacts     the *rejected* attempts and the reason each was thrown out, fed straight
                    back so the model can debug its own previous mistakes

    That third one is easy to get wrong, and getting it wrong is expensive. A rejected
    candidate scores zero, so it never wins a cell and never becomes a parent — which means
    that if the rejection reason travels only with the parent, it is never seen again and
    the model repeats the same illegal move indefinitely. The failures have to be carried
    separately. This is not a detail: an early version of this file dropped them, and the
    model proposed a 4547-parameter network twelve generations in a row.
    """
    parts = [f"Current program (score {parent.score:.4f}"
             + (f", {parent.metrics.get('params')} params" if parent.metrics else "") + "):",
             "```python", parent.block.strip(), "```"]

    if failures:
        parts += ["", "Recent attempts that were REJECTED, and why. Do not repeat these:"]
        for f in failures:
            parts += [f"\n✗ {f.note}", "```python", f.block.strip()[:400], "```"]

    if inspirations:
        parts += ["", "Other programs that have been tried, with their scores:"]
        for c in inspirations:
            parts += [f"\nscore {c.score:.4f}"
                      + (f", {c.metrics.get('params')} params:" if c.metrics else ":"),
                      "```python", c.block.strip(), "```"]

    parts += ["", f"Propose a better block. Stay under {cap} parameters. "
                  "Change something meaningful: a different shape, activation or optimizer "
                  "beats a tweaked learning rate."]
    return "\n".join(parts)


_IMPORT_LINES = ("import torch", "import torch.nn as nn", "import torch.nn.functional as F",
                 "import numpy as np")


def extract_code(reply: str) -> str:
    """Pull the python block out of a model reply, tolerating a missing fence.

    Also drops any top-level import lines the model repeated back. They are already in the
    frozen scaffolding above the marker, and left in they would accumulate a fresh copy in
    every generation.
    """
    if "```" in reply:
        chunk = reply.split("```")[1]
        if chunk.startswith("python"):
            chunk = chunk[len("python"):]
        reply = chunk
    kept = [ln for ln in reply.strip("\n").splitlines() if ln.strip() not in _IMPORT_LINES]
    return "\n".join(kept).strip("\n")


def mutate(parent: Candidate, inspirations: list[Candidate], cap: int,
           model: str | None = None, api_key: str | None = None,
           failures: list[Candidate] | None = None) -> str:
    """Ask the model for a rewritten block and splice it into the frozen scaffolding.

    Returns:
        A complete candidate program.
    """
    from . import llm
    reply = llm.complete(
        build_prompt(parent, inspirations, cap, failures),
        system=SYSTEM_PROMPT.format(cap=cap),
        model=model, api_key=api_key,
    )
    return seed_mod.splice_block(parent.code, extract_code(reply))


# ===================================================================== the loop
def evolve(evaluate_fn, store_fn, generations: int = 15, cap: int = 500,
           rng_seed: int = 0, model: str | None = None, api_key: str | None = None,
           on_step=None, record_to: str | Path | None = None) -> dict:
    """Run the four verbs in a circle.

    Args:
        evaluate_fn: YOUR scorer. `code -> {"score": float, ...}`.
        store_fn: YOUR archive rule. `(archive, candidate) -> archive`.
        generations: how many mutations to attempt.
        cap: parameter cap, passed to the model and enforced by your scorer.
        rng_seed: seeds parent selection, so two runs differ only by the model's sampling.
        model: OpenRouter model id.
        api_key: overrides the usual key lookup.
        on_step: optional callback, `(candidate, archive)`, for live progress printing.
        record_to: if given, write the whole run to this JSON file for offline replay.

    Returns:
        `{"archive": ..., "history": [...], "best": Candidate}`.
    """
    if not SYSTEM_PROMPT.strip():
        raise RuntimeError(
            "loop.SYSTEM_PROMPT is empty, so MUTATE has no instructions to work from. "
            "Complete Task 3 in the notebook (build SYSTEM_PROMPT from the four provided "
            "parts) and assign it to loop.SYSTEM_PROMPT before calling evolve().")
    first = Candidate(code=seed_mod.SEED_PROGRAM, generation=0, index=0)
    result = evaluate_fn(first.code)
    first.score = result.get("score", 0.0)
    first.metrics = {k: v for k, v in result.items() if k != "score"}
    first.note = result.get("note", "")

    archive: dict = store_fn({}, first)
    history = [first]
    failures: list[Candidate] = []                   # the artifacts channel — see build_prompt
    rng = random.Random(rng_seed)

    for gen in range(1, generations + 1):
        parent, inspirations = sample(archive, rng)
        try:
            code = mutate(parent, inspirations, cap, model=model, api_key=api_key,
                          failures=failures[-3:])
        except Exception as e:                       # a flaky API call must not end the run
            history.append(Candidate(code=parent.code, score=0.0, generation=gen,
                                     parent=parent.index, index=len(history),
                                     note=f"mutation failed: {type(e).__name__}: {e}"))
            if on_step:
                on_step(history[-1], archive)
            continue

        child = Candidate(code=code, generation=gen, parent=parent.index, index=len(history))
        result = evaluate_fn(child.code)
        child.score = result.get("score", 0.0)
        child.metrics = {k: v for k, v in result.items() if k != "score"}
        child.note = result.get("note", "")

        if child.score == 0.0 and child.note:
            failures.append(child)                   # carried forward, not lost with the child

        archive = store_fn(archive, child)
        history.append(child)
        if on_step:
            on_step(child, archive)

    out = {"archive": archive, "history": history,
           "best": max(history, key=lambda c: c.score)}
    if record_to:
        save_run(out, record_to)
    return out


# ===================================================================== record / replay
def save_run(run: dict, path: str | Path) -> Path:
    """Write a completed run to JSON so it can be replayed without an API key."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "history": [asdict(c) for c in run["history"]],
        "archive_keys": [list(k) if isinstance(k, tuple) else k for k in run["archive"]],
    }, indent=1))
    return path


def load_run(name: str) -> list[Candidate]:
    """Load a recorded run's candidates, in the order they were generated.

    Args:
        name: file name inside `minievolve/runs/`, with or without `.json`.

    Returns:
        The candidates, ready to be pushed through your own `store` rule.
    """
    path = RUNS_DIR / (name if name.endswith(".json") else f"{name}.json")
    raw = json.loads(path.read_text())
    return [Candidate(**c) for c in raw["history"]]


def replay(candidates: list[Candidate], store_fn, evaluate_fn=None) -> dict:
    """Re-run the EVALUATE and STORE decisions over a recorded run.

    The mutations are fixed — they are whatever the model proposed on the day — so the only
    things that vary are your two functions. That makes this the honest way to compare
    "keep only the best" against a quality-diversity archive: identical candidates, identical
    code, different retention.

    Args:
        candidates: a recorded run, from `load_run`.
        store_fn: your archive rule.
        evaluate_fn: your scorer. If given, every candidate is re-scored with it rather than
            trusting the recorded number — so a student without an API key still runs their
            own evaluator over real evolved programs. Costs a few seconds.

    Returns:
        The same shape `evolve` returns.
    """
    archive: dict = {}
    out = []
    for c in candidates:
        if evaluate_fn is not None:
            result = evaluate_fn(c.code)
            c = Candidate(code=c.code, generation=c.generation, parent=c.parent,
                          index=c.index, score=result.get("score", 0.0),
                          metrics={k: v for k, v in result.items() if k != "score"},
                          note=result.get("note", ""))
        archive = store_fn(archive, c)
        out.append(c)
    return {"archive": archive, "history": out, "best": max(out, key=lambda c: c.score)}
