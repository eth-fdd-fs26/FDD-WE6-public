"""Both sites, written out as plain HTML files.

The sites normally live behind two little HTTP servers (``site.server``) so they can poll a
running tournament and redraw themselves. That is the right thing inside the notebook and the
wrong thing everywhere else: a slide deck, a handout, a GitHub Pages folder or a browser with
no kernel behind it all want files.

This module renders the same pages from the same ``render`` functions and fixes up the three
things that only make sense with a server behind them:

* absolute links (``/matches``, ``/teams?team=Quasar+Queens``) become relative filenames, and
  the club badges are copied in alongside the pages;
* the ``/__state`` poller is left out — a file cannot advance;
* StarScoop's search form, which was a GET to the server, becomes a client-side filter over
  the articles already on the page.

Everything is a snapshot of one tournament at one moment. Nothing is interactive beyond that
search box: there is no wallet to move and no bet to place.

    python -m galactic.site.export --out site_export --rounds 0
"""

from __future__ import annotations

import argparse
import re
import shutil
from html import escape
from pathlib import Path
from urllib.parse import unquote_plus

from .. import config as C
from . import render
from ..rulebook_view import document as rulebook_document

DEFAULT_OUT = "site_export"

#: The betting site's tabs, in the order they appear in the topbar.
_TABS = [k for k, _ in render.BETTING_TABS]

_TEAM_HREF = re.compile(r'href="/teams\?team=([^"]*)"')
_PATH_HREF = re.compile(r'href="/([a-z_]*)"')
#: The club badges are served from ``/logos`` behind the server; in a folder of files they sit
#: in a ``logos`` subfolder next to the pages, so the leading slash has to go.
_ASSET_SRC = re.compile(r'src="/(logos/[^"]+)"')

#: Turns StarScoop's server-side search into a filter over the articles already rendered.
#: Every word of the query must appear somewhere in the article, which is close enough to
#: ``news.search`` for reading purposes — it is not scored, and it does not stop at eight.
_SEARCH_JS = """<script>
(function(){
  var form  = document.querySelector('.searchbar');
  var input = form && form.querySelector('input');
  var count = document.getElementById('scoop-count');
  if(!form || !input){return;}
  var arts = Array.prototype.slice.call(document.querySelectorAll('article'));
  function apply(){
    var words = input.value.toLowerCase().split(/[\\s,]+/).filter(function(w){
      return w.length > 2; });
    var shown = 0;
    arts.forEach(function(a){
      var hay = a.textContent.toLowerCase();
      var hit = words.every(function(w){ return hay.indexOf(w) >= 0; });
      a.style.display = hit ? '' : 'none';
      if(hit){ shown++; }
    });
    if(count){
      count.textContent = words.length
        ? shown + ' result' + (shown === 1 ? '' : 's') + ' for "' + input.value + '"'
        : arts.length + ' stories';
    }
  }
  form.addEventListener('submit', function(e){ e.preventDefault(); apply(); });
  input.addEventListener('input', apply);
})();
</script>"""


def team_file(team: str) -> str:
    """``Quasar Queens`` → ``teams-quasar-queens.html``."""
    return "teams-" + re.sub(r"[^a-z0-9]+", "-", team.lower()).strip("-") + ".html"


def _relink(html: str) -> str:
    """Rewrite the server's absolute links to the files this module writes."""
    html = _TEAM_HREF.sub(lambda m: f'href="{team_file(unquote_plus(m.group(1)))}"', html)
    html = _ASSET_SRC.sub(lambda m: f'src="{m.group(1)}"', html)
    return _PATH_HREF.sub(lambda m: f'href="{m.group(1) or "index"}.html"', html)


def _footer(here: str) -> str:
    """A line at the bottom of every page, because a static file has no back button."""
    links = [("index.html", "◆ Index"), ("bracket.html", "GalacticBets.gg"),
             ("news.html", "StarScoop"), ("rulebook.html", "The rulebook")]
    return ('<div class="wrap" style="opacity:.62;font:600 12px system-ui;'
            'padding-bottom:26px">'
            + " · ".join(f'<a href="{h}" style="color:var(--accent, #4c8dff);'
                         f'text-decoration:none">{escape(label)}</a>'
                         for h, label in links if h != here)
            + ' · <span style="color:#8b93a7">static snapshot — no bets can be placed</span>'
              '</div>')


def _finish(html: str, here: str) -> str:
    return _relink(html).replace("</body>", _footer(here) + "\n</body>")


def _index_page(t) -> str:
    from ..tournament import N_ROUNDS
    tabs = "".join(
        f'<a href="{k}.html" class="pick" style="display:inline-flex;width:auto;'
        f'margin:0 8px 8px 0"><span class="nm">{escape(label)}</span></a>'
        for k, label in render.BETTING_TABS)
    teams = "".join(
        f'<a href="{team_file(x)}" class="pick" style="display:inline-flex;width:auto;'
        f'margin:0 8px 8px 0"><span class="nm">{escape(x)}</span></a>' for x in C.TEAMS)
    state = (f'Round {t.round} of {N_ROUNDS} · balance {t.wallet:,.2f} {C.CURRENCY} · '
             f'{len(t.results())} matches settled · {len(t.bets())} bets placed')
    lead = ('<div class="empty" style="text-align:left;padding:12px 16px">'
            'A static export of the two sites the exercise runs inside the notebook. '
            'Every page below is a file: the bracket will not advance, prices will not move '
            'and the bet slip is whatever it was when this was written. '
            f'<div style="margin-top:8px;color:var(--dim)">{escape(state)}</div></div>')
    body = (render._card(f"{C.LEAGUE_NAME} {C.SEASON}", lead, flush=True)
            + render._card("GalacticBets.gg", tabs, sub="the bookmaker")
            + render._card("Clubs", teams, sub="squad and stat sheet, one page per club")
            + render._card("Elsewhere",
                           '<a href="news.html" class="pick" style="display:inline-flex;'
                           'width:auto;margin:0 8px 8px 0"><span class="nm">StarScoop — the '
                           'tabloid</span></a>'
                           '<a href="rulebook.html" class="pick" style="display:inline-flex;'
                           'width:auto;margin:0 8px 8px 0"><span class="nm">Laws of '
                           'Intergalactic Football</span></a>'))
    return render.page_shell("Galactic Premier League — static export",
                             f'<div class="wrap">{body}</div>',
                             brand="Galactic Premier League", mark="◆",
                             tagline="static export", right="")


def export(out_dir: str | Path = DEFAULT_OUT, tournament=None, *, rounds: int = 0,
           clean: bool = False) -> list[Path]:
    """Write both sites into ``out_dir`` and return the files written.

    ``tournament`` defaults to a fresh one — round 1, nothing settled, 1,000 GC on account.
    ``rounds`` settles that many rounds first, which is how you get an export with results,
    playoff coverage on StarScoop and a bracket that has moved.
    """
    from ..tournament import Tournament

    t = tournament if tournament is not None else Tournament()
    for _ in range(rounds):
        if t.finished:
            break
        t.advance_round(confirm="ADVANCE")

    out = Path(out_dir)
    if clean and out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    logos = Path(__file__).parent / "logos"                # the badges travel with the pages
    if logos.is_dir():
        shutil.copytree(logos, out / "logos", dirs_exist_ok=True)
        written += sorted((out / "logos").glob("*.png"))

    def write(name: str, html: str) -> None:
        path = out / name
        path.write_text(_finish(html, name), encoding="utf-8")
        written.append(path)

    for tab in _TABS:                                   # bracket, matches, … , bets
        write(f"{tab}.html", render.betting_page(t, tab))

    for team in C.TEAMS:                                # one squad page per club
        write(team_file(team), render.betting_page(t, "teams", {"team": team}))

    news = render.news_page("", t)                      # the whole archive, filtered in-page
    news = news.replace('font-size:12px;margin-bottom:4px">',
                        'font-size:12px;margin-bottom:4px" id="scoop-count">', 1)
    write("news.html", news.replace("</body>", _SEARCH_JS + "\n</body>"))

    write("index.html", _index_page(t))

    # The rulebook is already a self-contained document; it only wants the footer.
    write("rulebook.html", rulebook_document(theme="light"))
    return written


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="Export GalacticBets.gg and StarScoop as HTML.")
    p.add_argument("--out", default=DEFAULT_OUT, help=f"output folder (default: {DEFAULT_OUT})")
    p.add_argument("--rounds", type=int, default=0,
                   help="settle this many rounds before exporting (default: 0)")
    p.add_argument("--clean", action="store_true", help="delete the folder first")
    a = p.parse_args(argv)
    files = export(a.out, rounds=a.rounds, clean=a.clean)
    print(f"{len(files)} pages → {Path(a.out).resolve()}")
    print(f"open {Path(a.out).resolve() / 'index.html'}")


if __name__ == "__main__":
    main()
