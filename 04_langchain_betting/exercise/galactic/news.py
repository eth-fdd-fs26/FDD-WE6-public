"""StarScoop — the Galactic Premier League's least reputable and most useful news source.

Roughly a third of what follows moves a price. The rest is hairstyles, mascot litigation and
one very persistent romance. Nothing in an article is tagged as signal or noise; working out
which is which is the job, and the rulebook is what makes it possible — several of the
loudest stories here are loud precisely because they are about attributes the normalisation
protocols erase.
"""

from __future__ import annotations

from functools import lru_cache

from . import _truth
from . import config as C
from .world import build_world, recent_form, squad, standings


def _form_str(team: str) -> str:
    """Most recent first, the way a paddock report would say it."""
    return "-".join(reversed(recent_form(team)))


def _scrim_record(team: str) -> str:
    w = build_world()
    won = lost = drew = 0
    for m in w.scrims:
        if team not in (m["home"], m["away"]):
            continue
        gf, ga = ((m["home_score"], m["away_score"]) if m["home"] == team
                  else (m["away_score"], m["home_score"]))
        won += gf > ga
        lost += ga > gf
        drew += gf == ga
    n = won + drew + lost
    parts = [f"{won} win{'s' * (won != 1)}"]
    if drew:
        parts.append(f"{drew} draw{'s' * (drew != 1)}")
    parts.append(f"{lost} defeat{'s' * (lost != 1)}")
    return f"{', '.join(parts[:-1])} and {parts[-1]} from {n}"

MASTHEAD = "StarScoop"
TAGLINE = "Orbital gossip, transfer lies, and the occasional fact · since 2219"


def _names(team: str, idx: tuple[int, ...]) -> list[str]:
    rows = squad(team)
    return [rows[i]["name"] for i in idx]


def _article(aid, date, headline, standfirst, body, team=None, tags=()):
    return {"id": aid, "date": date, "headline": headline, "standfirst": standfirst,
            "body": body.strip(), "team": team, "tags": list(tags)}


@lru_cache(maxsize=4)
def _articles(seed: int) -> tuple[dict, ...]:
    w = build_world()
    table = {r["team"]: r for r in standings(w)}
    out = []

    # ---------------------------------------------------------------- availability
    stl = _names("Stellar Strikers", _truth.injury_report("Stellar Strikers"))
    out.append(_article(
        "N01", "2026-04-14",
        f"CARNAGE AT THE STRIKERS: {stl[0].split()[0].upper()}, {stl[1].split()[0].upper()} "
        f"AND {stl[2].split()[0].upper()} ALL OUT FOR THE PLAYOFFS",
        "Three first-choice starters ruled out after the coolant-line failure in training.",
        f"""
The Stellar Strikers will contest the playoffs without {stl[0]}, {stl[1]} or {stl[2]}, all
three confirmed out for the remainder of the competition after Tuesday's coolant-line failure
at the Helios training complex.

It is difficult to overstate the size of this. The three are the club's first, second and
fourth highest-rated outfielders on the League's published record, and between them they
started every one of the Strikers' seven league fixtures. Their replacements come off a
squad list that has barely featured this season.

The club's public line is that "the group is deeper than people think". The League's own stat
sheet, which anyone can pull up, does not obviously support that.
""", "Stellar Strikers", ("availability", "injury")))

    pls = _names("Pulsar Pirates", _truth.injury_report("Pulsar Pirates"))
    out.append(_article(
        "N02", "2026-04-15",
        f"PIRATES LOSE {pls[0].upper()} AND {pls[1].upper()} TO PROLONGED-TOUCH BANS",
        "Disciplinary panel confirms both reached the tournament threshold.",
        f"""
{pls[0]} and {pls[1]} have both been suspended for the remainder of the competition after
accumulating prolonged-touch offences past the tournament threshold.

Neither suspension is a surprise. The Pirates have carried the League's worst discipline
record all season and both players sit well above the 1.0-per-90 league average on the
official record. What is a surprise is the timing — the panel sat two days before the
playoff draw, and the club had reportedly expected the count to reset.
""", "Pulsar Pirates", ("availability", "suspension", "discipline")))

    csm = _names("Cosmic Crusaders", _truth.injury_report("Cosmic Crusaders"))
    out.append(_article(
        "N03", "2026-04-13",
        f"{csm[0].upper()} OUT: CRUSADERS LOSE THEIR BEST TOUCH PLAYER",
        "Ligament damage to the primary manipulator. Season over.",
        f"""
{csm[0]} will play no further part in the season. The Crusaders' highest-rated outfielder
sustained ligament damage in the closing minutes of the final league fixture and has been
ruled out of the playoffs entirely.

The Crusaders finished the regular season comfortably in the top half, but they have won one
of their last four and the scrim block has not been kind either. Losing their best receiver
on top of that is not the week they wanted.
""", "Cosmic Crusaders", ("availability", "injury")))

    neb = _names("Nebula Nomads", _truth.injury_report("Nebula Nomads"))
    out.append(_article(
        "N04", "2026-04-15",
        f"NOMADS INJURY CRISIS DEEPENS AS {neb[0].upper()} JOINS {neb[1].upper()} ON SIDELINES",
        "TWO more Nomads ruled out. Is the season already over for the drifters?",
        f"""
Another grim morning at the Nomads' orbital base, where {neb[0]} has followed {neb[1]} onto
the injury list ahead of the playoffs. That is two more names gone in a single week.

Club sources describe the mood as "difficult". Our sources describe it as a crisis. Whether
the head coach can hold a starting eleven together through a double-elimination bracket is
now the question everyone in the paddock is asking.

(League record: both players made a combined four appearances this season.)
""", "Nebula Nomads", ("availability", "injury")))

    # ---------------------------------------------------------------- form and coaching
    out.append(_article(
        "N05", "2026-04-12",
        "MAVERICKS' NEW COACH HAS QUIETLY TURNED THEM INTO SOMETHING ELSE",
        "Four months in, the hexapods are playing the best football in the league. "
        "The table has not caught up.",
        f"""
Nobody paid much attention when the Meteor Mavericks changed coach mid-season. They were
bottom half, they had lost four in a row, and the appointment was made without a press
conference.

Since then, a closed-doors block that has embarrassed sides well above them:
{_scrim_record('Meteor Mavericks')}. The new regime has rebuilt the whole side around receiving
and releasing inside the touch window, and against live opposition it is working.

The league table, which sums the whole season and cannot tell an early point from a late one,
still says {table['Meteor Mavericks']['rank']}th. The last month says something completely
different. Which of the two a bookmaker prices is, as ever, the interesting question.
""", "Meteor Mavericks", ("form", "coaching")))

    out.append(_article(
        "N06", "2026-04-11",
        "CRUSADERS IN FREEFALL: 'WE'VE STOPPED DOING THE BASICS'",
        "One win in four and a scrim block to forget.",
        f"""
Cosmic Crusaders' captain admitted after the final league fixture that the side has
"stopped doing the basics", pointing to a league run of {_form_str('Cosmic Crusaders')}
(newest first) and a closed-doors block of {_scrim_record('Cosmic Crusaders')}.

They finished {table['Cosmic Crusaders']['rank']}th, which flatters a team that banked most of
its points before the midpoint. Nobody in the paddock thinks they are the side that started
the season.
""", "Cosmic Crusaders", ("form",)))

    out.append(_article(
        "N07", "2026-04-10",
        "ASTEROIDS TAKE THE TITLE — BUT NOBODY IS TALKING ABOUT THEM",
        "League winners on points, and still not favourites with the layers.",
        f"""
Andromeda Asteroids finished top on {table['Andromeda Asteroids']['points']} points, a return
that would ordinarily make a side clear playoff favourites. The market disagrees, and the
Asteroids are being sent off behind the Strikers in most books.

Their supporters point to the table. Their detractors point out that they were beaten twice by
sides in the bottom half and that a seven-match season is a seven-match season.
""", "Andromeda Asteroids", ("form", "table")))

    # ---------------------------------------------------------------- the normalisation traps
    out.append(_article(
        "N08", "2026-04-09",
        "'THEY'LL SNAP LIKE KINDLING': GIANTS COACH RELISHES PHYSICAL MISMATCH",
        "Galaxy Giants average 312 kg. Their first-round opponents average 74 kg.",
        """
Galaxy Giants' coach was in no mood for diplomacy at the pre-playoff media session, promising
that lighter opponents would "snap like kindling" once the bracket got going.

The numbers behind the boast are real enough. The Giants field the heaviest and strongest
squad in the League's published record by a distance — six-limbed low-gravity specialists,
none under 250 kg, several over 350.

Whether that translates into anything on the field is a question the Giants' supporters have
been asked all season, and one they have yet to answer with a league position.
""", "Galaxy Giants", ("physical", "quotes")))

    out.append(_article(
        "N09", "2026-04-08",
        "THE LIGHTEST SQUAD IN THE LEAGUE — AND THE ONE NOBODY WANTS TO DRAW",
        "Quasar Queens are physically the smallest side in the competition. It has not "
        "stopped them.",
        """
On paper the Quasar Queens look like they should be brushed aside. The cephaloid side carries
the lowest raw strength, the lowest average mass and the shortest reach in the League's
published record — comfortably last on all three.

They also have the best hands in the competition. Every one of their outfielders is rated
above the League median for touch quality and first-touch control, and their prolonged-touch
count is the lowest in the division by some way.

"People look at the strength column and stop reading," their captain said this week. "That
column is the one the protocols take away. Nobody wants to hear it."
""", "Quasar Queens", ("physical", "quotes")))

    out.append(_article(
        "N10", "2026-04-07",
        "XENOBIOLOGISTS PUBLISH 40-YEAR STUDY OF PRE-NORMALISATION MASS TRENDS",
        "Average registered player mass has risen 31% since 1986. Nobody can agree on why.",
        """
The Interworld Institute has published its four-decade review of registered player physiology,
confirming that mean pre-normalisation mass across the League has risen 31% since 1986 while
mean limb count has held steady at 2.8.

The Institute is careful to note that its data set is of biological interest only and has
"no established relationship with competitive outcomes in the post-protocol era". This has not
stopped three separate member worlds from citing it in recruitment policy.
""", None, ("physical", "science")))

    # ---------------------------------------------------------------- pure noise
    noise = [
        ("N11", "2026-04-16", "BLITZ THUNDERCLAW'S NEW CREST IS DIVIDING THE PADDOCK",
         "Seventeen spines. Coral pink. Opinions are strong.",
         """
The Asteroids' captain arrived at the pre-playoff gala with a seventeen-spine coral crest and
the paddock has talked about nothing else since. Merchandise partners are said to be
delighted. Two team-mates are said to be not speaking to him.
""", "Andromeda Asteroids", ("lifestyle",)),

        ("N12", "2026-04-16", "MASCOT LAWSUIT ENTERS THIRD YEAR",
         "The Pirates' mascot and a licensing consortium remain deadlocked.",
         """
The long-running dispute over ownership of the Pulsar Pirates' mascot likeness has been
adjourned again, this time to the autumn. Neither side would comment. The mascot, who is
contractually forbidden from speaking, waved.
""", "Pulsar Pirates", ("business",)),

        ("N13", "2026-04-15", "ORBITAL CATERING SCANDAL: THE NUTRIENT PASTE IS BACK",
         "Players at three clubs have complained. Again.",
         """
The neutral orbital's catering contractor has confirmed that the vanilla-analogue nutrient
paste will return for the playoffs, overruling objections from at least three clubs. One
senior player described it as "an act of hostility".
""", None, ("lifestyle",)),

        ("N14", "2026-04-14", "ARE THE NOMADS AND THE QUEENS' MEDICAL CHIEF STILL TOGETHER?",
         "Sources say yes. Other sources say very much no.",
         """
The paddock's most durable romance is once again the paddock's most uncertain romance,
following an ambiguous appearance at a charity function on Tuesday. Neither party responded to
requests for comment, which is itself being read as a comment.
""", None, ("lifestyle",)),

        ("N15", "2026-04-13", "TICKET PRICES FOR THE GRAND FINAL UP 22%",
         "Supporters' associations are furious. The League is unmoved.",
         """
Grand Final seating has been repriced upward for the fourth consecutive season. The League
points to demand. Supporters' associations point to the League.
""", None, ("business",)),

        ("N16", "2026-04-12", "STRIKERS UNVEIL FOURTH KIT. IT IS GOLD.",
         "It is extremely gold.",
         """
The Stellar Strikers have released a fourth-choice kit in full metallic gold, to be worn "on
selected occasions". Early reaction has been mixed, in the sense that it has been negative.
""", "Stellar Strikers", ("lifestyle", "business")),

        ("N17", "2026-04-11", "TRANSFER RUMOUR: GIANTS 'MONITORING' HALF THE LEAGUE",
         "An agent has been busy.",
         """
Galaxy Giants are reported to be monitoring at least six players across four rival clubs ahead
of the close season. The same report last year named nine players, of whom the Giants signed
none.
""", "Galaxy Giants", ("transfers",)),

        ("N18", "2026-04-10", "CRUSADERS FAN CLUB VOTES TO CHANGE ANTHEM KEY",
         "A two-year campaign concludes in E flat.",
         """
After two years of lobbying, the Cosmic Crusaders supporters' association has voted to lower
the club anthem by a full tone, citing "widespread respiratory incompatibility" among the
membership.
""", "Cosmic Crusaders", ("lifestyle",)),

        ("N19", "2026-04-09", "ASTROLOGER PREDICTS 'A SIDE IN PURPLE' WILL LIFT THE TROPHY",
         "Three sides play in purple.",
         """
The paddock's resident astrologer has once again declined to name a winner, offering instead
that "a side in purple, or possibly adjacent to purple" will take the title. Three clubs
qualify. Four, if you are generous about the Nomads' away kit.
""", None, ("lifestyle",)),

        ("N20", "2026-04-08", "LEAGUE CONFIRMS PLAYOFF BALL WILL BE THE SAME PLAYOFF BALL",
         "A statement nobody asked for.",
         """
Following speculation, the League has confirmed that the match ball used in the playoffs will
be identical in specification to the one used all season. The statement runs to four pages.
""", None, ("business",)),

        ("N21", "2026-04-07", "QUEENS' NUTRITIONIST WRITES BESTSELLING COOKBOOK",
         "Forty recipes. Thirty-eight of them are brine.",
         """
The Quasar Queens' head of nutrition has topped the orbital bestseller list with a cookbook
aimed at cephaloid households. Critics have noted that the recipes are, in the main, brine.
""", "Quasar Queens", ("lifestyle",)),

        ("N22", "2026-04-06", "MAVERICKS TO TRIAL NEW TRAVEL SCHEDULE",
         "Departure moved four hours earlier. Squad reportedly 'fine about it'.",
         """
Meteor Mavericks will depart for the neutral orbital four hours earlier than in previous
seasons, a change the club describes as "logistical". No player has commented, which the
paddock has decided means something.
""", "Meteor Mavericks", ("logistics",)),
    ]
    out.extend(_article(*n[:6], tags=n[6]) for n in noise)
    return tuple(out)


# ===================================================================== the playoffs, live
# Everything above was written before a ball was kicked. Everything below is written as the
# tournament happens: when a round settles, StarScoop covers it. Without this, an agent that
# wakes up in round 2 has no way of knowing that round 1 was ever played — it would read a
# front page from the week before the playoffs and bet as if nothing had happened.
#
# Nothing here can see an unplayed match. It is built from ``Tournament.results()``, which is
# written *after* a round is settled and holds nothing else.

#: One publication day per betting round. The pre-playoff archive ends on 2026-04-16, so
#: round coverage starts the day after and always sorts to the top of the front page.
ROUND_DATES = {1: "2026-04-17", 2: "2026-04-18", 3: "2026-04-19", 4: "2026-04-20"}

_ROUND_NOISE = [
    ("NESTKEEPER'S HAIRCUT DIVIDES ORBITAL", "Six centimetres. Forty thousand opinions.",
     "The haircut has been described as brave, as a mistake, and as 'the sort of thing that "
     "happens in a playoff week'. The player has not commented. The barber has."),
    ("MASCOT LITIGATION ENTERS THIRTEENTH YEAR", "Still about the cereal. Still unresolved.",
     "Lawyers for both sides met again on the neutral orbital and again failed to agree on "
     "whether a mascot can be said to resemble a breakfast product."),
    ("CATERING CONTRACT AWARDED, SOMEHOW, TO A BRINE CONCERN",
     "Forty thousand seats. One flavour.",
     "The venue's hospitality partner for the remainder of the playoffs will supply brine in "
     "eleven formats. Member worlds have been advised to eat beforehand."),
    ("TROPHY POLISHED IN ADVANCE, TO NOBODY'S SURPRISE",
     "The League insists this implies nothing.",
     "Photographs of the trophy being prepared circulated widely and were read, by some, as "
     "a signal. The League points out that the trophy is polished every year at this stage."),
]


def _round_report(t, rnd: int, rows: list[dict]) -> dict:
    """The one story that actually matters: who played, who won, who is out."""
    lines = []
    for r in rows:
        fate = ("are eliminated" if r["loser_eliminated"]
                else "drop into the lower bracket")
        lines.append(f"{r['won_by']} beat {r['lost_by']} {r['score_won_first']} in "
                     f"{r['round_label']} ({r['match_id']}); {r['lost_by']} {fate}.")
    out = [r["lost_by"] for r in rows if r["loser_eliminated"]]
    tail = (f"Out of the tournament: {', '.join(out)}." if out else
            "Nobody is out yet: a first defeat only costs you the upper bracket.")
    headline = f"PLAYOFF ROUND {rnd}: " + ", ".join(
        f"{r['won_by'].split()[0].upper()} "
        f"{r['score_won_first'].replace(chr(8211), '-')}"
        for r in rows)
    return _article(
        f"R{rnd}A", ROUND_DATES[rnd], headline,
        f"All {len(rows)} match{'es' * (len(rows) != 1)} from round {rnd}, and where each "
        f"club goes next.",
        "\n\n".join([" ".join(lines), tail]), None, ("playoffs", "results", f"round{rnd}"))


def _round_reaction(t, rnd: int, rows: list[dict]) -> dict:
    """Colour. A real result underneath it, and nothing you could not read off the report."""
    def margin(r):
        a, b = (int(x) for x in r["score"].replace("–", "-").split("-"))
        return abs(a - b)
    big = max(rows, key=margin)
    big_score = big["score_won_first"]
    g = C.rng("news-reaction", rnd, big["match_id"])
    verb = ["ROUT", "DISMANTLE", "SEE OFF", "OVERWHELM"][int(g.integers(0, 4))]
    mood = ["furious", "philosophical", "very short", "unusually generous"][int(g.integers(0, 4))]
    return _article(
        f"R{rnd}B", ROUND_DATES[rnd],
        f"{big['won_by'].upper()} {verb} {big['lost_by'].upper()}",
        f"{big_score} in {big['round_label']}, and a {mood} press conference afterwards.",
        f"""
{big['won_by']} were the better side for most of {big['match_id']} and the scoreline says so.
The {big['lost_by']} bench was {mood} afterwards, noting that the tape will show a different
match from the one the table will remember. It will not change the {big_score}.
""", big["won_by"], ("playoffs", "reaction", f"round{rnd}"))


def _round_noise(t, rnd: int) -> dict:
    headline, stand, body = _ROUND_NOISE[(rnd - 1) % len(_ROUND_NOISE)]
    return _article(f"R{rnd}C", ROUND_DATES[rnd], headline, stand, body, None, ("lifestyle",))


def round_articles(t) -> list[dict]:
    """StarScoop's coverage of the rounds that have actually been played. Empty in round 1."""
    if t is None:
        return []
    by_round: dict[int, list[dict]] = {}
    for r in t.results():
        by_round.setdefault(r["round"], []).append(r)
    out = []
    for rnd in sorted(by_round):
        rows = by_round[rnd]
        out += [_round_report(t, rnd, rows), _round_reaction(t, rnd, rows),
                _round_noise(t, rnd)]
    return out


# ===================================================================== the archive
def all_articles(tournament=None) -> list[dict]:
    """Everything published so far — the pre-playoff archive, plus coverage of any round that
    has been settled on ``tournament``."""
    return [dict(a) for a in _articles(C.MASTER_SEED)] + round_articles(tournament)


def latest(n: int = 6, tournament=None) -> list[dict]:
    return sorted(all_articles(tournament), key=lambda a: a["date"], reverse=True)[:n]


def by_team(team: str, tournament=None) -> list[dict]:
    t = team.strip().lower()
    return [a for a in all_articles(tournament)
            if (a["team"] or "").lower() == t or t in a["headline"].lower()
            or t in a["body"].lower()]


def search(query: str, limit: int = 8, tournament=None) -> list[dict]:
    """Score articles by how many of the query's words they contain. Substring matching, so
    'injur' finds 'injury' and 'injured'."""
    words = [w for w in query.lower().replace(",", " ").split() if len(w) > 2]
    if not words:
        return latest(limit, tournament)
    scored = []
    for a in all_articles(tournament):
        hay = f"{a['headline']} {a['standfirst']} {a['body']} {' '.join(a['tags'])} " \
              f"{a['team'] or ''}".lower()
        hits = sum(1 for w in words if w in hay)
        if hits:
            scored.append((-hits, a["date"], a))
    scored.sort(key=lambda x: (x[0], x[1]))
    return [a for _h, _d, a in scored[:limit]]


def read(article_id: str, tournament=None) -> dict:
    for a in all_articles(tournament):
        if a["id"].lower() == article_id.strip().lower():
            return a
    raise KeyError(f"no article {article_id!r}. Search first, then read by id.")
