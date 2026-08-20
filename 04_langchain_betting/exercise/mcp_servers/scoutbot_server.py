"""ScoutBot — a tiny MCP server, so the notebook can show MCP working rather than describe it.

This is a separate process that knows nothing about LangChain. It speaks the Model Context
Protocol over stdin/stdout, and that is the entire point: anyone can publish one of these, in
any language, and it drops into a LangChain agent as tools without a line of glue.

Run it by hand to convince yourself it is just a program:

    python mcp_servers/scoutbot_server.py     # then it waits for MCP frames on stdin

Nothing here talks to the internet, so it works in Colab, offline, behind any firewall.
"""

from __future__ import annotations

import datetime as _dt

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("scoutbot")


@mcp.tool()
def scouting_report(club: str) -> str:
    """A scout's one-paragraph verdict on a club, in the scout's own florid style.

    Args:
        club: the club's name.
    """
    seed = sum(ord(c) for c in club.lower())
    moods = ["quietly furious", "unusually calm", "openly split", "in good spirits",
             "hard to read"]
    lines = ["they press higher than the tape suggests",
             "the second nest is defended by committee, which is to say by nobody",
             "their first touch under pressure is the best thing about them",
             "set pieces are an afterthought and it shows",
             "they hold the ball a fraction too long in their own half"]
    return (f"ScoutBot report on {club}. Camp is {moods[seed % len(moods)]}. "
            f"Watching two full matches, one thing stands out: "
            f"{lines[seed % len(lines)]}. Filed {_dt.date.today().isoformat()}. "
            f"Note: this is a scout's opinion, not a statistic, and should be treated "
            f"accordingly.")


@mcp.tool()
def travel_conditions(origin: str, destination: str = "Neutral Orbital 7") -> str:
    """Transit conditions between two orbitals, which affect nothing but are asked about a lot.

    Args:
        origin: where the squad departs from.
        destination: where they are going. Defaults to the playoff venue.
    """
    hours = 6 + (len(origin) * 3) % 40
    return (f"{origin} → {destination}: approximately {hours} hours in transit, "
            f"gravity differential within tolerance, no advisories. The League applies "
            f"normalisation protocols on arrival, so travel has no recorded effect on "
            f"player output.")


if __name__ == "__main__":
    mcp.run(transport="stdio")
