"""Galactic Premier League — the world behind the betting exercise.

    import galactic
    t = galactic.Tournament()
    galactic.open_sites(t)
    galactic.control_panel(t)

Nothing you import from here can tell you who wins. Go and read the rules, the stat sheets,
the scrim block and the news — that is the exercise.
"""

from .config import (CURRENCY, DEFAULT_MODEL, LEAGUE_NAME, MODEL_CHOICES, SEASON,
                     STARTING_BANKROLL, TEAMS)
from .tournament import MarketClosed, N_ROUNDS, RoundError, Tournament
from .world import build_world, head_to_head, recent_form, seeds, squad, standings

__all__ = [
    "Tournament", "MarketClosed", "RoundError", "N_ROUNDS",
    "build_world", "standings", "seeds", "squad", "recent_form", "head_to_head",
    "TEAMS", "LEAGUE_NAME", "SEASON", "CURRENCY", "STARTING_BANKROLL",
    "DEFAULT_MODEL", "MODEL_CHOICES",
    # populated lazily below
    "rules", "news", "analysis", "agents", "sim", "mcp_compat", "ui", "desk",
    "open_betting", "open_news", "open_sites", "stop_sites",
    "control_panel", "tool_explorer", "connect_mcp", "mcp_text",
    "make_tools", "TOOL_SPECS",
]


def __getattr__(name):
    if name in ("rules", "news", "analysis", "agents", "sim", "mcp_compat", "ui", "desk"):
        import importlib
        return importlib.import_module(f".{name}", __name__)
    if name in ("open_betting", "open_news", "open_sites", "stop_sites"):
        from . import site
        return getattr(site, name)
    if name == "control_panel":
        from . import launcher
        return launcher.control_panel
    if name == "tool_explorer":
        from . import explorer
        return explorer.tool_explorer
    if name in ("connect_mcp", "mcp_text"):
        from . import mcp_compat
        return {"connect_mcp": mcp_compat.connect, "mcp_text": mcp_compat.text}[name]
    if name in ("make_tools", "TOOL_SPECS", "build_docstring", "describe"):
        from . import tools
        return getattr(tools, name)
    if name == "spoilers":
        import importlib
        return importlib.import_module(".spoilers", __name__)
    raise AttributeError(name)
