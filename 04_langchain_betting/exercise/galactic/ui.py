"""Shared look and feel for everything this package draws *inside the notebook*.

One rule, and it is the reason this module exists: **notebook output must never emit a
global CSS selector**. The websites are served in real browser frames and may style `body`,
`table` and `:root` as they like — but a `<style>` block in a notebook output cell lands in
the notebook's own document, where `body { background: #0b0c10 }` repaints Colab and
`:root { --text: … }` quietly rewires half the page. That is what made the rulebook cell
unreadable: dark-theme variables applied to a light-theme document, so text and background
converged.

So there are exactly two safe ways to draw, and everything here is one of them:

  * ``frame(...)`` — a full document inside a sandboxed ``srcdoc`` iframe. Its CSS cannot
    escape. Use this for anything page-shaped (the rulebook).
  * ``scoped(...)`` — CSS in which every rule is prefixed with a unique element id. Use this
    for small components that must sit inline (panel chrome, cards).

Both are theme-neutral: light surfaces, dark ink, matching ``lc_viz``.
"""

from __future__ import annotations

import itertools
import json
import re
from html import escape

# ===================================================================== palette
# These are `lc_viz`'s tokens, deliberately to the hex. The quizzes, the diagrams and these
# panels sit in the same scroll, and a panel that is nearly-but-not-quite the same purple
# reads as a bug rather than as a second voice. Change them here and in `lc_viz` together.
INK = "#2b2d6b"          # headings
BODY = "#444444"         # running text
MUTED = "#6b7280"
FAINT = "#9aa1b2"
LINE = "#e6e8ee"         # card edge
LINE_2 = "#e2e5ef"       # control edge
LINE_SOFT = "#f0f1f6"
SURFACE = "#ffffff"
SURFACE_2 = "#fbfbfd"    # inset panels, code
HOVER = "#faf9ff"
SELECT = "#f2edff"
ACCENT = "#4c5bd4"
ACCENT_2 = "#7c4dbd"
GRADIENT = f"linear-gradient(135deg,{ACCENT},{ACCENT_2})"
OK = "#46b46e"
OK_BG = "#e7f7ec"
WARN = "#b45309"
NO = "#e07a7a"
NO_BG = "#fdecec"
GOLD = "#a16207"
GOLD_BG = "#fff8ec"
RADIUS = "14px"          # cards
RADIUS_2 = "10px"        # inner blocks
RADIUS_3 = "8px"         # controls
SANS = 'system-ui,-apple-system,"Segoe UI",Roboto,sans-serif'
MONO = 'ui-monospace,"SF Mono","JetBrains Mono",Menlo,Consolas,monospace'

_counter = itertools.count(1)


def uid(prefix: str = "gpl") -> str:
    """A fresh element id, so two copies of the same widget never collide."""
    return f"{prefix}-{next(_counter)}"


def scoped(css: str, root: str) -> str:
    """Return ``css`` with ``__U__`` replaced by ``root``, wrapped in a style tag.

    ``root`` is a complete selector — ``#some-id`` for plain HTML, ``.some-class`` for an
    ipywidgets box you called ``add_class`` on. Write every rule as ``__U__ .thing { … }``;
    anything that does not start there is rejected, because a notebook has only one document
    and a stray ``body`` rule repaints all of it.
    """
    body = css.replace("__U__", root)
    stray = [ln for ln in body.splitlines()
             if ln.strip() and "{" in ln
             and not ln.strip().startswith((root, "}", "@", "/*", "to", "from"))]
    assert not stray, f"unscoped CSS rule(s): {stray[:2]}"
    return f"<style>{body}</style>"


def frame(document: str, height: int = 640, *, border: bool = True) -> str:
    """A complete HTML document in a sandboxed iframe. Its styles cannot leak out."""
    edge = f"1px solid {LINE}" if border else "none"
    # The wrapping div is not decoration: IPython's HTML() warns "consider using IFrame"
    # whenever its payload *starts* with an iframe tag, and prints that warning into the
    # notebook in a red box. IFrame itself takes a src URL, which is exactly what we do not
    # have — the whole point is that the document is inline and self-contained.
    return (f'<div style="margin:0">'
            f'<iframe srcdoc="{escape(document, quote=True)}" height="{height}" '
            f'style="width:100%;border:{edge};border-radius:14px;background:{SURFACE};'
            f'display:block;color-scheme:light" loading="lazy"></iframe></div>')


# ===================================================================== widget skin
#: Restyles the stock ipywidgets controls into the notebook's own look — the white card, the
#: `#e6e8ee` edge, the purple gradient on the primary action. Everything is scoped, so this
#: repaints one panel and never the notebook's own toolbars.
#:
#: The selectors are the ones ipywidgets 7 and 8 both emit (`.jupyter-button`, `.mod-active`,
#: `.widget-label`), because Colab's shipped version is not ours to choose.
WIDGET_SKIN = f"""
__U__ {{font-family:{SANS};color:{BODY};font-size:13.5px}}
__U__ .widget-label, __U__ .widget-inline-hbox .widget-label {{color:{MUTED};
  font-family:{SANS};font-size:12.5px}}

__U__ .jupyter-button {{border:1px solid {LINE_2};border-radius:{RADIUS_3};background:#fff;
  color:{INK};font-family:{SANS};font-size:12.5px;font-weight:700;box-shadow:none;
  height:auto;min-height:32px;padding:7px 15px;transition:.12s}}
__U__ .jupyter-button:hover:enabled {{border-color:{ACCENT_2};background:{HOVER};
  box-shadow:none}}
__U__ .jupyter-button:disabled {{opacity:.4;cursor:not-allowed}}
__U__ .jupyter-button.mod-primary {{background:{GRADIENT};border-color:transparent;
  color:#fff}}
__U__ .jupyter-button.mod-primary:hover:enabled {{filter:brightness(1.07)}}
__U__ .jupyter-button.mod-danger {{background:{NO};border-color:transparent;color:#fff}}

__U__ .widget-toggle-buttons {{margin:0 0 2px}}
__U__ .widget-toggle-button {{font-weight:600;color:{MUTED};margin-right:5px}}
__U__ .widget-toggle-button.mod-active {{border-color:{ACCENT_2};background:{SELECT};
  color:#4a3a86;font-weight:700;box-shadow:0 0 0 3px rgba(124,77,189,.10)}}

__U__ select, __U__ textarea,
__U__ input[type="text"], __U__ input[type="number"] {{border:1px solid {LINE_2};
  border-radius:{RADIUS_3};background:#fff;color:{BODY};font-family:{SANS};font-size:12.5px;
  padding:6px 9px;box-shadow:none}}
__U__ textarea {{font-family:{MONO};font-size:11.5px;line-height:1.55;padding:10px 12px}}
__U__ select:focus, __U__ textarea:focus,
__U__ input[type="text"]:focus {{outline:none;border-color:{ACCENT_2};
  box-shadow:0 0 0 3px rgba(124,77,189,.12)}}

__U__ input[type="checkbox"], __U__ input[type="radio"] {{accent-color:{ACCENT_2}}}
__U__ .widget-checkbox label, __U__ .widget-radio-box label {{font-size:12.5px;
  color:{BODY};font-family:{SANS}}}
__U__ .widget-radio-box {{padding-top:2px}}

__U__ .noUi-connect {{background:{ACCENT_2}}}
__U__ .noUi-handle {{border-color:{LINE_2};box-shadow:none}}
__U__ .widget-readout {{border-color:{LINE_2};border-radius:6px;color:{INK};
  font-family:{MONO};font-size:11.5px}}
"""

#: The outer card every panel sits in — same geometry as an ``lc_viz`` card.
def card_css(max_width: int = 980) -> str:
    return f"""
__U__ {{background:{SURFACE};border:1px solid {LINE};border-radius:{RADIUS};padding:18px;
  max-width:{max_width}px}}
__U__ .title {{font-weight:800;font-size:15px;color:{INK}}}
__U__ .tagline {{color:{MUTED};font-size:12.5px;margin:3px 0 14px;line-height:1.6}}
"""


# ===================================================================== text helpers
#: Runs of shouted capitals — the rulebook's own emphasis. Rendered rather than ignored.
#: A run must *start* with capitals, which is what keeps "1974 Giants Era" out of it, but a
#: number inside one belongs to it — "FOULS PER 90 MINUTES" is a single shouted phrase.
_CAPS = re.compile(r"\b[A-Z]{2,}(?:[ \-](?:[A-Z]{2,}|\d+))*\b")
#: The quantities a law turns on. Shouting is not available for these, so the author wrote
#: them in ordinary prose and they disappear; a threshold is exactly what a reader is looking
#: for, so give it back.
_QTY = re.compile(r"\b\d+(?:\.\d+)?\s+(?:seconds?|per (?:player )?(?:per )?90(?: minutes)?)\b")


def emphasise(text: str) -> str:
    """Escape ``text``, then give back the emphasis: SHOUTED phrases, and thresholds."""
    out = _CAPS.sub(lambda m: f'<b class="k">{m.group(0)}</b>', escape(text))
    return _QTY.sub(lambda m: f'<b class="q">{m.group(0)}</b>', out)


def paragraphs(text: str, keep=lambda _line: True) -> str:
    """Blank-line-separated plain text into ``<p>`` elements, emphasis applied."""
    blocks = [b.strip() for b in text.strip().split("\n\n")]
    return "".join(f"<p>{emphasise(' '.join(b.split()))}</p>"
                   for b in blocks if b and keep(b))


# ===================================================================== tool output
def _cell(value) -> str:
    if isinstance(value, float):
        return f'<span class="mono">{value:,.2f}</span>'
    if isinstance(value, int) and not isinstance(value, bool):
        return f'<span class="mono">{value:,}</span>'
    if isinstance(value, (list, dict)):
        return f'<span class="mono">{escape(json.dumps(value, default=str))}</span>'
    return escape(str(value))


def result_html(value, *, css_class: str = "res") -> str:
    """Render whatever a tool returned, in the shape it actually has.

    A list of same-shaped records is a table — which is the point of a structured tool, and
    reading one as a wall of JSON hides it. Everything else falls back to indented JSON.
    """
    if isinstance(value, list) and value and all(isinstance(r, dict) for r in value):
        keys = list(dict.fromkeys(k for r in value for k in r))
        if len(keys) <= 12:
            head = "".join(f"<th>{escape(k)}</th>" for k in keys)
            rows = "".join(
                "<tr>" + "".join(f"<td>{_cell(r.get(k, ''))}</td>" for k in keys) + "</tr>"
                for r in value)
            return (f'<div class="{css_class} tbl"><table><thead><tr>{head}</tr></thead>'
                    f"<tbody>{rows}</tbody></table></div>")
    if isinstance(value, str):
        return f'<div class="{css_class}"><pre>{escape(value)}</pre></div>'
    return (f'<div class="{css_class}"><pre>'
            f"{escape(json.dumps(value, indent=2, default=str))}</pre></div>")
