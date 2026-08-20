"""The Laws of Intergalactic Football, 2026 edition.

This is the most important document in the exercise and the easiest one to skip. Every stat
the league publishes is *plausible*; only the rules tell you which ones can possibly matter.
An agent that never opens this file is guessing, and the bookmaker is counting on it.
"""

from __future__ import annotations

RULEBOOK_TITLE = "Laws of Intergalactic Football — Galactic Premier League, 2026 edition"

SECTIONS: dict[str, tuple[str, str]] = {
    "1": ("The sides and the field", """
Each side fields eleven players. Beyond that, species composition is unrestricted: a side may
be entirely bipedal, entirely cephalopod, or any mixture.

The field carries FOUR scoring structures. Each side defends two of them:

  * TWO GOALS — the wide, low structures at either end of the long axis.
  * TWO NESTS — the narrow, elevated baskets at the corners of the defending half.

A side therefore has four things to protect and four things to attack, which is why teams
carry three specialist nestkeepers and why a squad's nest defence is a live concern rather
than a rounding error.
"""),

    "2": ("Scoring", """
A ball placed in an opposing GOAL scores one point. A ball placed in an opposing NEST scores
one point. There is no distinction in value; the distinction is in difficulty, and in who on
your squad is capable of preventing each.

Matches cannot end level. Playoff ties are replayed in sudden-death extra periods until a
side leads, so every playoff fixture has a winner and there is no draw market.
"""),

    "3": ("Contact with the ball", """
A player may contact the ball with ANY part of their body. Hands, feet, tentacles, tails,
mandibles, prehensile crests and gas-phase manifolds are all legal contact surfaces. There is
no handball in Intergalactic Football and there never has been.

What is NOT legal is PROLONGED TOUCH. A player may strike, deflect, head, tap, volley or
cushion the ball, but may not retain contact with it for longer than 1.2 seconds. Carrying,
cradling, clutching, coiling around or gas-trapping the ball is prolonged touch, and it is a
foul regardless of which appendage does it.

The consequence is that possession in this sport is a matter of TOUCH QUALITY, not of grip
strength. A side that can receive a hard pass cleanly and redirect it inside 1.2 seconds
keeps the ball. A side that cannot, does not — no matter how large its players are.
"""),

    "4": ("The normalisation protocols", """
Because member species differ in physical scale by more than two orders of magnitude, the
League applies NORMALISATION PROTOCOLS to every player before kick-off. These are not
handicaps applied to teams; they are per-player field adjustments applied inside the playing
volume, and they are complete rather than partial.

The following attributes are equalised across all twenty-two players on the field:

  * raw strength
  * body mass
  * limb count and reach
  * top sprint speed

After normalisation, a 340 kg six-limbed silicate collective and a 71 kg two-limbed cephaloid
exert identical force, cover ground at identical speed, and present identical reach. This is
why the League can run a single competition across species at all, and it is the reason the
1974 Giants Era ended.

The protocols do NOT touch anything learned rather than inherited: touch quality, first-touch
control, positional reading, nest defence, dead-ball technique, or discipline. Those remain
entirely the player's own.
"""),

    "5": ("Fouls and discipline", """
Prolonged touch is the most common foul in the sport. It concedes possession immediately, and
in the defensive third it concedes a free strike from the nest line.

Prolonged-touch offences accumulate across the competition. A player reaching the threshold is
suspended for the remainder of the tournament — which is why a side's foul discipline is both
a within-match cost and a squad-availability risk.

The League's official statistic is PROLONGED-TOUCH FOULS PER 90 MINUTES. League average is
approximately 1.0 per player per 90.
"""),

    "6": ("Competition format", """
Eight sides contest a single round-robin regular season: every side plays every other side
exactly once, seven matches each, no home-and-away. Three points for a win, one for a draw.
Because every side plays the same seven opponents, the final table is directly comparable —
though it is a seven-match sample, and it weights an early win exactly as heavily as a late
one.

The top eight — that is, all of them — enter a DOUBLE-ELIMINATION playoff seeded by final
league position. A side is eliminated on its second defeat. Fourteen matches decide the
title, and a side that loses early in the upper bracket can still win the whole thing from
the lower bracket.

Playoff matches are held at a neutral orbital, so there is no home advantage in the playoffs.
"""),

    "7": ("The official statistical record", """
For every registered player the League publishes:

    ball_control                  touch quality under pressure, 0-99
    first_touch                   control of a received ball inside the 1.2 s window, 0-99
    nest_defence                  effectiveness defending the elevated baskets, 0-99
    set_piece                     dead-ball technique, 0-99
    prolonged_touch_fouls_per90   discipline, fouls per 90 minutes
    raw_strength                  pre-normalisation force output, 0-99
    mass_kg                       pre-normalisation body mass
    limb_count                    number of manipulating limbs
    top_speed                     pre-normalisation sprint speed, 0-99

The League publishes all nine because member worlds request them and because pre-normalisation
physical data remains of considerable interest to xenobiologists. The League makes no claim
that all nine bear on the result of a match.

Closed-doors scrim results are published in aggregate one week before the playoffs. They are
not official fixtures and carry no competitive weight, but they are played at full strength.
"""),
}

#: A compact reminder used inside tool docstrings.
SUMMARY = (
    "Intergalactic Football: 11 a side, two goals and two nests to attack and defend, any "
    "body part may touch the ball but holding it beyond 1.2 s is a prolonged-touch foul, and "
    "raw strength, mass, limb count and top speed are all normalised away before kick-off."
)


def text(section: str | None = None) -> str:
    """The rulebook as plain text — this is what the agent's ``read_rules`` tool returns."""
    if section is not None:
        key = str(section).strip().lstrip("§").split(".")[0]
        if key not in SECTIONS:
            raise KeyError(f"no section {section!r}; sections are "
                           f"{ {k: v[0] for k, v in SECTIONS.items()} }")
        title, body = SECTIONS[key]
        return f"§{key} {title}\n{body.strip()}"
    parts = [RULEBOOK_TITLE, "=" * len(RULEBOOK_TITLE)]
    for k, (title, body) in SECTIONS.items():
        parts.append(f"\n§{k} {title}\n{body.strip()}")
    return "\n".join(parts)


def contents() -> dict[str, str]:
    return {k: v[0] for k, v in SECTIONS.items()}


def show(section: str | None = None, height: int = 620):
    """Render the rulebook in the notebook, as a reading view rather than a text dump.

    The layout lives in ``rulebook_view``; it draws into a sandboxed iframe, so the
    stylesheet stays inside the frame instead of repainting the notebook around it.
    """
    from .rulebook_view import show as _show
    _show(section, height)
