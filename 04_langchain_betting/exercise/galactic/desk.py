"""The scouting desk — an ordinary Python service, written before anyone thought about agents.

This is the thing an MCP server sits in front of, and the reason it has to. Nothing in here
knows what a model is. It takes Python arguments, it returns Python objects, and its objects
print as memory addresses, because that is what Python objects do:

    >>> report = desk.scouting_report("Quasar Queens")
    >>> print(report)
    <galactic.desk.ScoutingReport object at 0x1049c2f10>

That single line is the whole motivation for §1.3 of the notebook. An agent receives text and
nothing else, so *something* has to turn this object into text on the way out — and, when the
agent wants to act, turn the agent's text back into arguments this module will accept on the
way in. Both directions are somebody's job. MCP is the shape that job has agreed on.

Nothing here predicts anything. The ratings are a scout's opinions, deliberately built from
the club's *name* rather than from the world, so this file cannot leak a result even if a
participant reads it.
"""

from __future__ import annotations

from . import config as C


# ===================================================================== the desk's objects
class Rating:
    """A rating as the desk stores it: a number that carries its own scale around.

    Note what it does **not** have — a ``__str__``. ``json.dumps`` will refuse to serialise
    one of these, and ``json.dumps(..., default=str)`` will happily write down its address.
    Deciding what a ``Rating`` looks like on the wire is the wire layer's job, not the desk's.
    """

    def __init__(self, value: float, out_of: float = 100):
        # Kept exactly as the desk recorded them — an int stays an int, so anything that
        # writes one down does not have to apologise for a trailing '.0'.
        self.value = value
        self.out_of = out_of


class ScoutingReport:
    """One scout's verdict on one club. A plain object; no wire format, no JSON, no opinions
    about who is reading it."""

    def __init__(self, club: str, verdict: str, ratings: dict[str, Rating]):
        self.club = club
        self.verdict = verdict
        self.ratings = ratings


# ===================================================================== the desk's API
_MOODS = ["quietly furious", "unusually calm", "openly split", "in good spirits",
          "hard to read"]
_LINES = ["they press higher than the tape suggests",
          "the second nest is defended by committee, which is to say by nobody",
          "their first touch under pressure is the best thing about them",
          "set pieces are an afterthought and it shows",
          "they hold the ball a fraction too long in their own half"]


def scouting_report(club: str) -> ScoutingReport:
    """The desk's verdict on a club. Returns an object, because it is a Python function."""
    seed = sum(ord(c) for c in club.lower())
    verdict = (f"Camp is {_MOODS[seed % len(_MOODS)]}. Watching two full matches, one thing "
               f"stands out: {_LINES[seed % len(_LINES)]}. A scout's opinion, not a League "
               f"statistic.")
    return ScoutingReport(club, verdict, {
        "confidence": Rating(55 + seed % 40),
        "coherence": Rating(50 + (seed * 7) % 45),
        "scout_certainty": Rating(2 + seed % 4, out_of=5),
    })


#: Everything staked through the desk. A toy ledger: this is not your tournament wallet, and
#: nothing here settles. The point of §1.3 is the translation, not the money.
_LEDGER: list[dict] = []


def place_bets(selections: list[str], stake_each: float) -> str:
    """Stake the same amount on each of several clubs.

    The signature is the point. It wants a **list of strings** and **one number** — which is
    not the shape anything an LLM says arrives in, and not the shape a bet slip has either.

    Args:
        selections: the clubs to back, one entry per bet.
        stake_each: how much goes on each one, in Galactic Credits.
    """
    if not selections:
        raise ValueError("no selections — the desk cannot stake nothing on nobody")
    unknown = [s for s in selections if s not in C.TEAMS]
    if unknown:
        raise ValueError(f"not clubs in this league: {unknown}")
    if stake_each <= 0:
        raise ValueError(f"stake_each must be positive, got {stake_each}")
    for s in selections:
        _LEDGER.append({"selection": s, "stake": round(float(stake_each), 2)})
    total = round(float(stake_each) * len(selections), 2)
    return (f"Accepted {len(selections)} bet(s) at {stake_each:.2f} {C.CURRENCY} each "
            f"({total:.2f} {C.CURRENCY} total): {', '.join(selections)}.")


def ledger() -> list[dict]:
    """Everything the desk has accepted so far."""
    return list(_LEDGER)


def clear_ledger() -> None:
    """Used by the tests, and by anyone who wants a clean slate."""
    _LEDGER.clear()
