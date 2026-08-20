"""One-line fix for running a stdio MCP server inside a notebook kernel.

**The problem.** An MCP stdio server is a *subprocess*. To spawn it, the client hands the
operating system three real file descriptors — stdin, stdout and stderr. The MCP SDK defaults
the third one to ``sys.stderr``:

    async def stdio_client(server, errlog: TextIO = sys.stderr): ...

Inside Jupyter or Colab, ``sys.stderr`` is not a file. It is an ``ipykernel`` stream that
forwards text to your browser over a socket, and it has no underlying descriptor:

    UnsupportedOperation: fileno

Worse, that default was bound when ``mcp`` was first imported, so re-assigning ``sys.stderr``
afterwards changes nothing — the function is already holding the kernel's stream.

**The fix.** ``langchain-mcp-adapters`` does not expose ``errlog``, so we wrap the function it
calls and pass a real file instead. The server's stderr then lands in a log file you can read
if something goes wrong, which is more useful than the notebook swallowing it anyway.

    from galactic import mcp_compat
    mcp_compat.apply()

Idempotent, and a no-op outside a notebook kernel unless you force it.
"""

from __future__ import annotations

import io
import sys
import tempfile
from pathlib import Path

_LOG_PATH: Path | None = None
_APPLIED = False


def _stderr_has_a_real_descriptor() -> bool:
    try:
        sys.stderr.fileno()
        return True
    except (AttributeError, OSError, io.UnsupportedOperation, ValueError):
        return False


def apply(force: bool = False) -> str | None:
    """Make stdio MCP servers spawnable from a notebook. Returns the log path, or None if
    nothing needed doing."""
    global _LOG_PATH, _APPLIED
    if _APPLIED:
        return str(_LOG_PATH)
    if _stderr_has_a_real_descriptor() and not force:
        return None

    from langchain_mcp_adapters import sessions
    from mcp.client.stdio import stdio_client as _real_stdio_client

    log = Path(tempfile.gettempdir()) / "mcp_server_stderr.log"
    handle = open(log, "a", encoding="utf-8", buffering=1)     # noqa: SIM115 — lives on

    def stdio_client_with_a_real_errlog(server, errlog=None):
        return _real_stdio_client(server, errlog=handle)

    sessions.stdio_client = stdio_client_with_a_real_errlog
    _LOG_PATH, _APPLIED = log, True
    return str(log)


def server_log(tail: int = 40) -> str:
    """The MCP server's stderr, if you need to see why it died."""
    if _LOG_PATH is None or not _LOG_PATH.exists():
        return "(nothing logged — the server has not written to stderr)"
    return "\n".join(_LOG_PATH.read_text(encoding="utf-8").splitlines()[-tail:])


# ===================================================================== one-line connection
async def connect(server: str = "scoutbot"):
    """Connect to one of the exercise's MCP servers and return its tools.

    Deliberately a single call. Spawning a stdio subprocess, pointing its stderr somewhere a
    notebook kernel can cope with, and adapting the result into LangChain tools is three
    screens of plumbing that teaches nothing about what MCP *is* — and the point of MCP is
    precisely that connecting is somebody else's problem. Await it::

        mcp_tools = await galactic.connect_mcp()

    One nicety for the notebook: a server that fails to start dies in its own process, so the
    error a participant sees would otherwise be a timeout with nothing in it. We syntax-check
    the file first and, if the connection still fails, attach the server's stderr.
    """
    import os
    import sys

    from langchain_mcp_adapters.client import MultiServerMCPClient

    apply()                      # notebook-only: give the subprocess a real stderr
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script = os.path.join(here, "mcp_servers", f"{server}_server.py")
    if not os.path.exists(script):
        raise FileNotFoundError(
            f"there is no MCP server at {script}. If this is `betting_desk`, it is the file "
            f"Task 2 writes — run the %%writefile cell above (with the two gaps filled in) "
            f"and then run this one again.")

    with open(script, encoding="utf-8") as fh:
        source = fh.read()
    if "???" in source:
        raise ValueError(f"{os.path.basename(script)} still has ??? in it — finish the gaps "
                         f"and re-run the %%writefile cell before connecting.")
    compile(source, script, "exec")          # a SyntaxError here is yours, not the protocol's

    client = MultiServerMCPClient({server: {
        "command": sys.executable, "args": [script], "transport": "stdio"}})
    try:
        return await client.get_tools()
    except Exception as exc:                 # noqa: BLE001 — re-raised with the server's side
        raise RuntimeError(
            f"could not talk to the {server} MCP server. Its own stderr said:\n\n"
            f"{server_log(20)}") from exc


def text(result) -> str:
    """The text of whatever an MCP tool just returned.

    The adapter hands back MCP *content blocks* — a list of ``{"type": "text", ...}`` dicts —
    because a tool is allowed to return images and resources too. Ours return one block of
    text, and unwrapping that is noise in a teaching cell::

        print(galactic.mcp_text(await tool.ainvoke({...})))
    """
    if isinstance(result, str):
        return result
    if isinstance(result, list):
        return "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in result)
    return str(result)
