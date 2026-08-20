"""Every constant and the one random-number factory the whole world is built from.

Students are not meant to read this file, but nothing in here spoils anything: it holds
weights and seeds, not outcomes. The outcomes are *computed* from these, on demand, in
``_truth.py``.

The one idea worth knowing: there is no global random state anywhere in this package. Every
draw names its own stream — ``rng("player", team, i)``, ``rng("playoff", "UB1", salt)`` — so
the world is a pure function of the seed. Browsing the website, re-running the agent forty
times, or rendering the news page in a different order cannot move a single result.
"""

from __future__ import annotations

import hashlib

import numpy as np

# ----------------------------------------------------------------- seeding
MASTER_SEED = 20260416          # the canonical universe the students play in
RNG_NAMESPACE = "gpl26"         # Galactic Premier League, 2026 season


def rng(*parts: object) -> np.random.Generator:
    """A generator uniquely determined by ``(MASTER_SEED, *parts)``.

    Independent of call order, so any part of the world can be built lazily.
    """
    key = "|".join([RNG_NAMESPACE, str(MASTER_SEED), *(str(p) for p in parts)])
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return np.random.default_rng(int.from_bytes(digest[:8], "big"))


def reseed(master_seed: int) -> None:
    """Move the whole package to a different universe (used only by ``sim.py``)."""
    global MASTER_SEED
    MASTER_SEED = int(master_seed)


# ----------------------------------------------------------------- the league
LEAGUE_NAME = "Galactic Premier League"
SEASON = "2026"

TEAMS = [
    "Andromeda Asteroids",
    "Nebula Nomads",
    "Cosmic Crusaders",
    "Stellar Strikers",
    "Galaxy Giants",
    "Meteor Mavericks",
    "Quasar Queens",
    "Pulsar Pirates",
]

TEAM_ABBR = {
    "Andromeda Asteroids": "AND",
    "Nebula Nomads": "NEB",
    "Cosmic Crusaders": "CSM",
    "Stellar Strikers": "STL",
    "Galaxy Giants": "GXG",
    "Meteor Mavericks": "MTR",
    "Quasar Queens": "QSR",
    "Pulsar Pirates": "PLS",
}

TEAM_COLORS = {
    "Andromeda Asteroids": "#e8813a",
    "Nebula Nomads": "#7c5cff",
    "Cosmic Crusaders": "#2fb8a4",
    "Stellar Strikers": "#f2c14e",
    "Galaxy Giants": "#4a83ff",
    "Meteor Mavericks": "#e5546a",
    "Quasar Queens": "#c45cd6",
    "Pulsar Pirates": "#4fbf5f",
}

TEAM_GLYPH = {
    "Andromeda Asteroids": "☄",
    "Nebula Nomads": "\U0001f30c",
    "Cosmic Crusaders": "\U0001f6e1",
    "Stellar Strikers": "⭐",
    "Galaxy Giants": "\U0001f30c",
    "Meteor Mavericks": "☀",
    "Quasar Queens": "\U0001f451",
    "Pulsar Pirates": "☠",
}

TEAM_SPECIES = {
    "Andromeda Asteroids": "Rock-silicate collectives",
    "Nebula Nomads": "Gas-phase drifters",
    "Cosmic Crusaders": "Exo-armoured bipeds",
    "Stellar Strikers": "Plasma-core humanoids",
    "Galaxy Giants": "Low-gravity giants",
    "Meteor Mavericks": "Hexapod sprinters",
    "Quasar Queens": "Tentacled cephaloids",
    "Pulsar Pirates": "Amphibious quadrupeds",
}

# ----------------------------------------------------------------- the rating model
# The four attributes the *rules* make relevant, and how much each is worth.
W_LEGIT = {
    "ball_control": 0.40,
    "first_touch": 0.25,
    "nest_defence": 0.20,
    "set_piece": 0.15,
}

# Attributes the normalisation protocols erase before kickoff. Drawn from streams that are
# statistically independent of team quality — they carry exactly zero information.
RED_HERRINGS = ["raw_strength", "mass_kg", "limb_count", "top_speed"]

K_FOUL = 2.0        # prolonged-touch fouls per 90, relative to a league-average 1.0
K_FORM = 0.60       # late-season momentum
K_COACH = 0.25      # a coaching change, up or down

HOME_EDGE = 0.06    # regular season only; playoffs are on neutral ground
RATING_SCALE = 1.6  # rating points per logit — keeps even a mismatch bettable
P_CLAMP = (0.12, 0.88)
GOALS_BASE = 0.95   # log-mean goals per side (two goals + two nests => high-scoring)
GOALS_SLOPE = 0.30
SCRIM_NOISE = 0.35     # per-side rating noise in a closed-doors scrim
RETENTION_NOISE = 9.0  # noise on possession retention, in percentage points
RETENTION_SLOPE = 15.6 # retention percentage points per rating point, near parity
W_SCRIM = 0.60         # how much an analyst leans on scrims vs the stat sheet

# ----------------------------------------------------------------- the bookmaker
# The book does not price off the true rating. It prices off a degraded one, in three
# named ways — each a real bookmaking failure mode. This is where the agent's edge lives.
VIG = 0.06                  # margin on match markets
VIG_FUTURES_MULT = 1.5      # futures carry a fatter margin, as in reality
BOOK_INJURY_BETA = 0.35     # only a third of the news-driven injury impact reaches the price
BOOK_STRENGTH_GAMMA = 0.25  # the book over-weights the crowd-pleasing red herring
BOOK_TABLE_DELTA = 0.35     # the book anchors on the league table, ignoring scrims
BOOK_P_CLAMP = (0.10, 0.90)
OUTRIGHT_SIMS = 6000
MAX_FUTURES_ODDS = 250.0

# ----------------------------------------------------------------- the game
STARTING_BANKROLL = 1000.0
CURRENCY = "GC"             # Galactic Credits
MIN_STAKE = 10.0

N_PLAYERS = 16              # 11 starters + 5 substitutes
N_STARTERS = 11
N_SCRIMS_PER_TEAM = 10

# ----------------------------------------------------------------- the agent
DEFAULT_MODEL = "google/gemini-3-flash-preview"
MODEL_CHOICES = [
    "google/gemini-3-flash-preview",
    "anthropic/claude-haiku-4.5",
    "openai/gpt-5.1-mini",
]
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_TEMPERATURE = 0.3
DEFAULT_MAX_STEPS = 18
