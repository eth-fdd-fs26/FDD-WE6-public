"""The seed program, the markers that fence off what may change, and how a candidate runs.

Slide 5 of the lecture: the two things a human supplies are *a seed program* — any working
baseline, however bad — and *a scoring function*. This file is the first of those.

The seed is `nn.Linear(2, 3)`: nine parameters, no hidden layer, no nonlinearity. On a
spiral it is close to useless, which is exactly the point. You are not supposed to hand the
search a good answer. You are supposed to hand it a *running* answer and a way to tell
better from worse.

The `EVOLVE-BLOCK-START` / `EVOLVE-BLOCK-END` markers are the contract. Everything between
them is the model's to rewrite. Everything outside — the imports, the training loop in
`spirals.py`, the scoring in your evaluator — is frozen scaffolding the model never sees an
opportunity to touch.
"""
from __future__ import annotations

import re
import types

BLOCK_START = "# EVOLVE-BLOCK-START"
BLOCK_END = "# EVOLVE-BLOCK-END"

SEED_PROGRAM = '''import torch
import torch.nn as nn

# EVOLVE-BLOCK-START

def build_model():
    """Return an nn.Module mapping (batch, 2) inputs to (batch, 3) logits."""
    return nn.Linear(2, 3)


def build_optimizer(model):
    """Return a torch optimizer for the model's parameters."""
    return torch.optim.SGD(model.parameters(), lr=0.05)

# EVOLVE-BLOCK-END
'''


def get_block(source: str) -> str:
    """Pull out the evolvable region — the only text the model is asked to rewrite.

    Args:
        source: a full candidate program.

    Returns:
        The text between the markers, markers excluded.

    Raises:
        ValueError: if the markers are missing or out of order.
    """
    m = re.search(re.escape(BLOCK_START) + r"\n(.*?)" + re.escape(BLOCK_END),
                  source, re.DOTALL)
    if not m:
        raise ValueError("no EVOLVE-BLOCK found — the markers are the contract")
    return m.group(1)


def splice_block(source: str, new_block: str) -> str:
    """Put a rewritten block back into the frozen scaffolding.

    This is what keeps the model honest. Even if it returns a whole file, only the part
    between the markers survives; the imports and the harness come from `source`.

    Args:
        source: the program whose scaffolding to keep.
        new_block: replacement text for the evolvable region.

    Returns:
        A complete program.
    """
    return re.sub(re.escape(BLOCK_START) + r"\n.*?" + re.escape(BLOCK_END),
                  BLOCK_START + "\n" + new_block.strip("\n") + "\n" + BLOCK_END,
                  source, flags=re.DOTALL)


def run_program(source: str) -> types.ModuleType:
    """Execute a candidate program and hand back its namespace.

    ⚠️ This runs code a language model wrote, in your process. In Colab that is a throwaway
    virtual machine and the blast radius is a notebook you can restart, which is why it is
    acceptable here. On your own laptop, or anywhere with credentials in the environment, it
    is not: a real deployment sandboxes this step. AlphaEvolve's evaluator pool exists partly
    for this reason. It is worth noticing that the security boundary of the whole method sits
    on this one line.

    Args:
        source: a complete candidate program.

    Returns:
        A module-like namespace exposing `build_model` and `build_optimizer`.

    Raises:
        Exception: anything the candidate raises at import time, plus `AttributeError`
            if it failed to define the two functions the protocol requires.
    """
    ns = types.ModuleType("candidate")
    exec(compile(source, "<candidate>", "exec"), ns.__dict__)
    for required in ("build_model", "build_optimizer"):
        if not callable(getattr(ns, required, None)):
            raise AttributeError(f"candidate does not define {required}()")
    return ns
