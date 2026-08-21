"""mini-evolve — the four verbs of an evolutionary coding agent, in about forty lines.

  spirals.py   the problem, and the training protocol nobody is allowed to change
  seed.py      the seed program and the EVOLVE-BLOCK contract
  llm.py       the mutation operator: one OpenRouter call
  loop.py      SAMPLE and MUTATE, plus the driver that calls YOUR evaluate and store

The two verbs the lecture calls the human's job — the score and the archive — are not in
this package on purpose. You write them in the notebook.
"""

from . import llm, loop, seed, spirals  # noqa: F401

__all__ = ["spirals", "seed", "llm", "loop"]
