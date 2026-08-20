"""The stage machine: an 8-team double-elimination bracket, bet on across four rounds.

The two rules that matter:

1. **A round settles once, and settling is final.** ``advance_round`` is the only mutator of
   ``round``, there is no inverse, and betting into a closed market raises. You cannot place a
   bet once you know how it turned out — which is the entire point of doing this in stages.
2. **The state is primitives only.** No sockets, no callbacks, no model clients live in
   ``TournamentState``. That is what makes ``fork()`` — three sandbox universes branching off
   the current round — a two-line, provably-safe operation.
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass, field, replace
from typing import Callable

from . import config as C
from . import _truth
from .world import build_world, seeds

_K = _truth._ACCESS


# ===================================================================== the bracket, as data
# (id, bracket, round label, column, source_a, source_b, winner_to, loser_to)
DE8_GRAPH = [
    ("UB1", "UB", "Upper R1", 0, ("seed", 1), ("seed", 8), "UB5", "LB1"),
    ("UB2", "UB", "Upper R1", 0, ("seed", 4), ("seed", 5), "UB5", "LB2"),
    ("UB3", "UB", "Upper R1", 0, ("seed", 2), ("seed", 7), "UB6", "LB2"),
    ("UB4", "UB", "Upper R1", 0, ("seed", 3), ("seed", 6), "UB6", "LB1"),

    ("UB5", "UB", "Upper Semi", 1, ("win", "UB1"), ("win", "UB2"), "UB7", "LB4"),
    ("UB6", "UB", "Upper Semi", 1, ("win", "UB3"), ("win", "UB4"), "UB7", "LB3"),
    ("LB1", "LB", "Lower R1", 0, ("lose", "UB1"), ("lose", "UB4"), "LB3", None),
    ("LB2", "LB", "Lower R1", 0, ("lose", "UB2"), ("lose", "UB3"), "LB4", None),

    ("UB7", "UB", "Upper Final", 2, ("win", "UB5"), ("win", "UB6"), "GF", "LB6"),
    ("LB3", "LB", "Lower R2", 1, ("win", "LB1"), ("lose", "UB6"), "LB5", None),
    ("LB4", "LB", "Lower R2", 1, ("win", "LB2"), ("lose", "UB5"), "LB5", None),

    ("LB5", "LB", "Lower Semi", 2, ("win", "LB3"), ("win", "LB4"), "LB6", None),
    ("LB6", "LB", "Lower Final", 3, ("win", "LB5"), ("lose", "UB7"), "GF", None),
    ("GF", "GF", "Grand Final", 4, ("win", "UB7"), ("win", "LB6"), None, None),
]

GRAPH = {n[0]: n for n in DE8_GRAPH}
ORDER = [n[0] for n in DE8_GRAPH]

#: which matches are decided at the end of each betting round
ROUND_MATCHES = {
    1: ["UB1", "UB2", "UB3", "UB4"],
    2: ["UB5", "UB6", "LB1", "LB2"],
    3: ["UB7", "LB3", "LB4"],
    4: ["LB5", "LB6", "GF"],
}

#: which of those you may actually bet on as a match market (the rest need teams we don't
#: know yet — the champion futures market is how you back them)
ROUND_MARKETS = {
    1: ["UB1", "UB2", "UB3", "UB4"],
    2: ["UB5", "UB6", "LB1", "LB2"],
    3: ["UB7", "LB3", "LB4"],
    4: ["LB5"],
}

N_ROUNDS = 4


class MarketClosed(Exception):
    pass


class RoundError(Exception):
    pass


# ===================================================================== state
@dataclass
class Slot:
    match_id: str
    bracket: str
    round_label: str
    column: int
    source_a: tuple
    source_b: tuple
    team_a: str | None = None
    team_b: str | None = None
    winner: str | None = None
    score_a: int | None = None
    score_b: int | None = None

    @property
    def settled(self) -> bool:
        return self.winner is not None


@dataclass
class Market:
    market_id: str
    kind: str                  # "match" | "champion"
    label: str
    selections: dict           # team -> decimal odds
    opens_round: int
    closes_round: int
    settles_round: int
    status: str = "open"       # open | closed | settled
    match_id: str | None = None


@dataclass
class Bet:
    bet_id: str
    market_id: str
    selection: str
    stake: float
    odds: float
    round_placed: int
    status: str = "open"       # open | won | lost
    payout: float = 0.0
    label: str = ""


@dataclass
class RoundReport:
    round_index: int
    results: list[dict]
    settled_bets: list[dict]
    staked: float
    returned: float
    wallet_before: float
    wallet_after: float


@dataclass
class TournamentState:
    seed: int
    salt: int
    sandbox: bool
    round_index: int
    wallet: float
    slots: dict[str, Slot]
    markets: dict[str, Market]
    bets: list[Bet] = field(default_factory=list)
    history: list[RoundReport] = field(default_factory=list)
    locked_rounds: frozenset = frozenset()
    champion: str | None = None
    _bet_counter: int = 0


@dataclass
class Event:
    kind: str
    payload: dict


# ===================================================================== simulation helper
def _source_team(slots: dict, src: tuple, seed_list: list[str]) -> str | None:
    kind, ref = src
    if kind == "seed":
        return seed_list[ref - 1]
    s = slots.get(ref)
    if s is None or s.winner is None:
        return None
    return s.winner if kind == "win" else (s.team_b if s.winner == s.team_a else s.team_a)


def _fill(slots: dict, seed_list: list[str]) -> None:
    for mid in ORDER:
        s = slots[mid]
        if s.team_a is None:
            s.team_a = _source_team(slots, s.source_a, seed_list)
        if s.team_b is None:
            s.team_b = _source_team(slots, s.source_b, seed_list)


def simulate_remainder(slots: dict, g, *, book: bool = True, _k=None) -> str:
    """Play out every unsettled match with coin flips from ``g``; return the champion.

    Used only to price the champion futures market. Takes a *copy* of the slot table.
    """
    if _k is not _truth._ACCESS:
        raise PermissionError("simulate_remainder is spoiler-protected")
    sim = {mid: replace(s) for mid, s in slots.items()}
    seed_list = seeds()
    for mid in ORDER:
        _fill(sim, seed_list)
        s = sim[mid]
        if s.winner is not None:
            continue
        p = _truth.p_win(s.team_a, s.team_b, book=book, _k=_truth._ACCESS)
        s.winner = s.team_a if g.random() < p else s.team_b
    return sim["GF"].winner


# ===================================================================== the tournament
class Tournament:
    """One playable tournament. ``sandbox=True`` instances never touch the real wallet."""

    _MUTABLE = {"_state", "_subs", "_world"}

    def __init__(self, *, bankroll: float | None = None, salt: int = 0, sandbox: bool = False):
        self._world = build_world()
        self._subs: list[Callable[[Event], None]] = []
        slots = {mid: Slot(mid, br, lab, col, sa, sb)
                 for mid, br, lab, col, sa, sb, _w, _l in DE8_GRAPH}
        _fill(slots, seeds(self._world))
        self._state = TournamentState(
            seed=C.MASTER_SEED, salt=salt, sandbox=sandbox, round_index=1,
            wallet=C.STARTING_BANKROLL if bankroll is None else float(bankroll),
            slots=slots, markets={},
        )
        self._open_markets_for(1)

    # ---------------------------------------------------------------- immutability guards
    def __setattr__(self, name, value):
        if name not in self._MUTABLE and hasattr(self, "_state"):
            raise AttributeError(f"Tournament.{name} is read-only")
        object.__setattr__(self, name, value)

    def __repr__(self) -> str:
        tag = " SANDBOX" if self._state.sandbox else ""
        return (f"<Tournament{tag} round={self._state.round_index}/{N_ROUNDS} "
                f"wallet={self._state.wallet:.0f}{C.CURRENCY} "
                f"open_markets={len(self.open_markets())} bets={len(self._state.bets)}>")

    @classmethod
    def _from_state(cls, st: TournamentState) -> "Tournament":
        t = cls.__new__(cls)
        object.__setattr__(t, "_world", build_world())
        object.__setattr__(t, "_subs", [])
        object.__setattr__(t, "_state", st)
        return t

    # ---------------------------------------------------------------- read-only surface
    @property
    def round(self) -> int:
        return self._state.round_index

    @property
    def sandbox(self) -> bool:
        return self._state.sandbox

    @property
    def wallet(self) -> float:
        return round(self._state.wallet, 2)

    @property
    def finished(self) -> bool:
        return self._state.round_index > N_ROUNDS

    @property
    def champion(self) -> str | None:
        return self._state.champion

    def on_event(self, cb: Callable[[Event], None]) -> None:
        self._subs.append(cb)

    def _emit(self, kind: str, **payload) -> None:
        for cb in list(self._subs):
            try:
                cb(Event(kind, payload))
            except Exception:
                pass

    # ---------------------------------------------------------------- markets
    def _open_markets_for(self, r: int) -> None:
        st = self._state
        _fill(st.slots, seeds(self._world))
        for mid in ROUND_MARKETS[r]:
            s = st.slots[mid]
            if s.team_a is None or s.team_b is None:
                continue
            st.markets[f"m:{mid}"] = Market(
                market_id=f"m:{mid}", kind="match", label=f"{s.round_label}: "
                f"{s.team_a} vs {s.team_b}",
                selections=_truth.match_odds(s.team_a, s.team_b, _k=_K),
                opens_round=r, closes_round=r, settles_round=r, match_id=mid,
            )
        st.markets[f"f:champion:r{r}"] = Market(
            market_id=f"f:champion:r{r}", kind="champion",
            label=f"Champion (priced in round {r})",
            selections=_truth.champion_odds(st.slots, _k=_K),
            opens_round=r, closes_round=r, settles_round=N_ROUNDS,
        )

    def open_markets(self) -> list[dict]:
        return [self._market_view(m) for m in self._state.markets.values()
                if m.status == "open"]

    def _market_view(self, m: Market) -> dict:
        v = {
            "market_id": m.market_id, "kind": m.kind, "label": m.label,
            "status": m.status,
            "selections": [
                {"team": t, "odds": o, "implied_probability": round(1.0 / o, 4)}
                for t, o in m.selections.items()
            ],
        }
        if m.match_id:
            s = self._state.slots[m.match_id]
            v |= {"match_id": m.match_id, "round_label": s.round_label,
                  "team_a": s.team_a, "team_b": s.team_b}
        return v

    def market(self, market_id: str) -> dict:
        m = self._state.markets.get(market_id)
        if m is None:
            raise KeyError(f"no market {market_id!r}; open markets: "
                           f"{[k for k, v in self._state.markets.items() if v.status == 'open']}")
        return self._market_view(m)

    # ---------------------------------------------------------------- betting
    def place_bet(self, market_id: str, selection: str, stake: float) -> dict:
        st = self._state
        m = st.markets.get(market_id)
        if m is None:
            raise KeyError(f"no market {market_id!r}")
        if m.status != "open":
            raise MarketClosed(
                f"{market_id} closed when round {m.closes_round} was settled — "
                "no betting with hindsight.")
        if selection not in m.selections:
            raise ValueError(f"{selection!r} is not a selection on {market_id}. "
                             f"Choose one of {list(m.selections)}.")
        stake = round(float(stake), 2)
        if stake < C.MIN_STAKE:
            raise ValueError(f"minimum stake is {C.MIN_STAKE:.0f} {C.CURRENCY}")
        if stake > st.wallet + 1e-9:
            raise ValueError(f"insufficient funds: stake {stake:.2f} > wallet {st.wallet:.2f}")

        st._bet_counter += 1
        bet = Bet(bet_id=f"B{st._bet_counter:03d}", market_id=market_id, selection=selection,
                  stake=stake, odds=m.selections[selection], round_placed=st.round_index,
                  label=m.label)
        st.wallet -= stake
        st.bets.append(bet)
        self._emit("bet_placed", bet=self._bet_view(bet), wallet=self.wallet)
        return self._bet_view(bet)

    def _bet_view(self, b: Bet) -> dict:
        return {"bet_id": b.bet_id, "market_id": b.market_id, "selection": b.selection,
                "stake": b.stake, "odds": b.odds, "to_return": round(b.stake * b.odds, 2),
                "round_placed": b.round_placed, "status": b.status, "payout": b.payout,
                "label": b.label}

    def bets(self, *, status: str | None = None) -> list[dict]:
        return [self._bet_view(b) for b in self._state.bets
                if status is None or b.status == status]

    # ---------------------------------------------------------------- settlement
    def advance_round(self, confirm: str = "") -> RoundReport:
        st = self._state
        if st.round_index > N_ROUNDS:
            raise RoundError("the tournament is over")
        if confirm != "ADVANCE":
            raise RoundError("advance_round is irreversible — call it with confirm='ADVANCE'")
        r = st.round_index
        if r in st.locked_rounds:
            raise RoundError(f"round {r} is already settled")

        wallet_before = st.wallet
        for m in st.markets.values():
            if m.closes_round == r and m.status == "open":
                m.status = "closed"

        results = []
        seed_list = seeds(self._world)
        for mid in ROUND_MATCHES[r]:
            _fill(st.slots, seed_list)
            s = st.slots[mid]
            res = _truth.resolve(mid, s.team_a, s.team_b, salt=st.salt, _k=_K)
            s.winner, s.score_a, s.score_b = res.winner, res.score_a, res.score_b
            results.append({"match_id": mid, "round_label": s.round_label,
                            "team_a": s.team_a, "team_b": s.team_b, "winner": res.winner,
                            "score": f"{res.score_a}–{res.score_b}"})
        _fill(st.slots, seed_list)
        if st.slots["GF"].winner:
            st.champion = st.slots["GF"].winner

        settled, returned = [], 0.0
        for b in st.bets:
            m = st.markets[b.market_id]
            if b.status != "open" or m.settles_round != r:
                continue
            if m.kind == "match":
                won = st.slots[m.match_id].winner == b.selection
            else:
                won = st.champion == b.selection
            b.status = "won" if won else "lost"
            b.payout = round(b.stake * b.odds, 2) if won else 0.0
            st.wallet += b.payout
            returned += b.payout
            settled.append(self._bet_view(b))

        report = RoundReport(
            round_index=r, results=results, settled_bets=settled,
            staked=round(sum(b["stake"] for b in settled), 2), returned=round(returned, 2),
            wallet_before=round(wallet_before, 2), wallet_after=round(st.wallet, 2),
        )
        st.history.append(report)
        st.locked_rounds |= {r}
        st.round_index = r + 1
        if st.round_index <= N_ROUNDS:
            self._open_markets_for(st.round_index)
        self._emit("round_settled", report=report, wallet=self.wallet)
        return report

    # ---------------------------------------------------------------- what has happened
    def results(self) -> list[dict]:
        """Every playoff match that has actually been played, oldest first.

        Only settled matches, ever: this reads ``history``, which is written by
        ``advance_round`` after the fact. It is the honest answer to "what has happened so
        far", and it is what the news desk and the agent's tools are built on — without it,
        an agent waking up in round 2 has no way to know round 1 ever took place.
        """
        out = []
        for rep in self._state.history:
            for r in rep.results:
                s = self._state.slots[r["match_id"]]
                loser = r["team_b"] if r["winner"] == r["team_a"] else r["team_a"]
                # `score` is team_a–team_b, the way the bracket draws it; `score_won_first`
                # is the way a report says it out loud ("beat them 4–3").
                hi, lo = ((s.score_a, s.score_b) if r["winner"] == r["team_a"]
                          else (s.score_b, s.score_a))
                out.append({
                    "round": rep.round_index, "match_id": r["match_id"],
                    "round_label": r["round_label"], "score": r["score"],
                    "score_won_first": f"{hi}\u2013{lo}",
                    "team_a": r["team_a"], "team_b": r["team_b"],
                    "won_by": r["winner"], "lost_by": loser,
                    "loser_eliminated": GRAPH[r["match_id"]][7] is None,
                    "advances_to": GRAPH[r["match_id"]][6],
                })
        return out

    def eliminated(self) -> list[str]:
        """Clubs whose tournament is over — two defeats, or beaten in the grand final."""
        return [r["lost_by"] for r in self.results() if r["loser_eliminated"]]

    def fixtures(self) -> list[dict]:
        """The matches this round decides, whether or not you can bet on all of them."""
        return [s for s in self.bracket() if s["status"] == "live"]

    # ---------------------------------------------------------------- bracket + forking
    def bracket(self) -> list[dict]:
        st = self._state
        out = []
        for mid, br, lab, col, sa, sb, _w, _l in DE8_GRAPH:
            s = st.slots[mid]
            out.append({
                "match_id": mid, "bracket": br, "round_label": lab, "column": col,
                "team_a": s.team_a, "team_b": s.team_b,
                "source_a": _label(sa), "source_b": _label(sb),
                "winner": s.winner, "score_a": s.score_a, "score_b": s.score_b,
                "status": "settled" if s.settled else (
                    "live" if mid in ROUND_MATCHES.get(st.round_index, []) else "upcoming"),
            })
        return out

    def snapshot(self) -> bytes:
        return pickle.dumps(self._state, protocol=5)

    def fork(self, n: int = 3, salt_base: int = 1) -> list["Tournament"]:
        """``n`` sandbox universes branching off *right now*: same ratings, same odds, same
        squads — only the coin flips from here on differ."""
        blob = self.snapshot()
        out = []
        for i in range(n):
            st: TournamentState = pickle.loads(blob)
            st.sandbox = True
            st.salt = salt_base + i
            out.append(Tournament._from_state(st))
        return out


def _label(src: tuple) -> str:
    kind, ref = src
    return {"seed": f"Seed {ref}", "win": f"Winner {ref}", "lose": f"Loser {ref}"}[kind]
