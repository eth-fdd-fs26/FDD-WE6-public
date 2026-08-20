"""Two threaded HTTP servers, embedded in the notebook as iframes.

Idempotent by design: re-running the cell shuts the old servers down cleanly and rebinds,
rather than leaving orphans and drifting up the port range. Works in Colab (via
``serve_kernel_port_as_iframe``) and locally in Jupyter or VS Code (via a plain iframe), so
the notebook can be authored and rehearsed outside Colab.
"""

from __future__ import annotations

import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import render

_SERVERS: dict[str, tuple[ThreadingHTTPServer, threading.Thread, int]] = {}


def _free_port(start: int = 8710, span: int = 120) -> int:
    for p in range(start, start + span):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    raise RuntimeError("no free port in range")


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):        # keep the notebook output clean
        pass

    #: Bumped whenever the page's content should change. The page polls it (see
    #: ``render.page_shell``) and reloads itself, so settling a round visibly advances the
    #: site instead of leaving a stale bracket sitting in an iframe.
    def state_token(self) -> str:
        return "static"

    def do_GET(self):
        u = urlparse(self.path)
        query = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path.strip("/") == "__state":
            return self._send(self.state_token(), "text/plain; charset=utf-8")
        try:
            html = self.render(u.path.strip("/") or "", query)
        except Exception as exc:                      # never take the notebook down
            html = (f"<pre style='color:#f4566d;background:#0b0c10;padding:20px;"
                    f"font-family:monospace'>{type(exc).__name__}: {exc}</pre>")
        self._send(html, "text/html; charset=utf-8")

    def _send(self, text: str, content_type: str):
        body = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


class _BettingHandler(_Handler):
    tournament = None

    def render(self, path, query):
        return render.betting_page(self.tournament, path or "bracket", query,
                                   state=self.state_token())

    def state_token(self):
        return render.state_token(self.tournament)


class _NewsHandler(_Handler):
    tournament = None

    def render(self, path, query):
        return render.news_page(query.get("q", ""), self.tournament,
                                state=self.state_token())

    def state_token(self):
        return render.state_token(self.tournament)


def _serve(key: str, handler_cls) -> int:
    stop(key)
    port = _free_port()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), handler_cls)
    httpd.daemon_threads = True
    httpd.allow_reuse_address = True
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    _SERVERS[key] = (httpd, thread, port)
    return port


def stop(key: str | None = None) -> None:
    for k in ([key] if key else list(_SERVERS)):
        entry = _SERVERS.pop(k, None)
        if entry:
            entry[0].shutdown()
            entry[0].server_close()


def stop_sites() -> None:
    """Shut both sites down. Call it at the end of the notebook, or before re-running."""
    stop()


def _in_colab() -> bool:
    try:
        import google.colab  # noqa: F401
        return True
    except Exception:
        return False


def _embed(port: int, height: int, label: str):
    from IPython.display import HTML, display
    if _in_colab():
        from google.colab import output
        output.serve_kernel_port_as_iframe(port, height=str(height))
        return
    display(HTML(
        f'<div style="font:600 12px system-ui;color:#8b93a7;margin:6px 0">{label} · '
        f'<a href="http://127.0.0.1:{port}" target="_blank" '
        f'style="color:#4c8dff">open in a tab</a></div>'
        f'<iframe src="http://127.0.0.1:{port}" width="100%" height="{height}" '
        f'style="border:1px solid #272b36;border-radius:10px;background:#0b0c10"></iframe>'))


def bind(tournament) -> None:
    """Point whichever sites are already running at this tournament.

    Cheap insurance against the one mistake that looks like a bug: re-running the cell that
    creates the tournament gives you a *second* ``Tournament``. The launcher would then be
    settling one object while the iframes render another, and the bracket would sit at round
    1 for ever while the desk insisted it had advanced. Anything that acts on a tournament
    calls this, so the pages always show the tournament you are actually playing.
    """
    if "betting" in _SERVERS:
        _BettingHandler.tournament = tournament
    if "news" in _SERVERS:
        _NewsHandler.tournament = tournament


def open_betting(tournament, height: int = 940):
    """Serve GalacticBets.gg and show it inline."""
    _BettingHandler.tournament = tournament
    port = _serve("betting", _BettingHandler)
    _embed(port, height, "GalacticBets.gg")
    return port


def open_news(tournament=None, height: int = 940):
    """Serve StarScoop and show it inline.

    Pass the tournament: StarScoop covers the playoffs as they happen, and without it the
    front page is frozen on the week before they started.

    Same window height as GalacticBets: the front page grows by three stories every time a
    round settles, and a short frame turns that into a lot of scrolling.
    """
    _NewsHandler.tournament = tournament
    port = _serve("news", _NewsHandler)
    _embed(port, height, "StarScoop")
    return port


def open_sites(tournament, height: int = 940):
    """Both sites, one after the other."""
    return open_betting(tournament, height), open_news(tournament, height)
