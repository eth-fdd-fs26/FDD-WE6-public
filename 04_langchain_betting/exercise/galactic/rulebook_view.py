"""The rulebook, rendered for a human rather than for a tool.

``rules.text()`` is what the agent's ``read_rules`` tool returns and it is deliberately plain.
This module is the *reading* view: the same seven sections, laid out so that a participant
with four minutes can find the two paragraphs that matter.

Nothing here adds, removes or interprets a rule. The extra structure is all recovered from
the source text — the shouted phrases become emphasis, the bullet blocks become cards, the
statistical record becomes a table — because working out which sections bear on a result is
the exercise, and a view that flagged them would hand the answer over.

It renders in two skins from one set of markup: **light** for the notebook, where it goes
into a sandboxed iframe (see ``ui.frame``), and **dark** for the Rules tab of
GalacticBets.gg, where it has to sit inside the site's own chrome. Same document, so the
page a participant reads in the notebook is the page they find again on the site.
"""

from __future__ import annotations

import re
from html import escape

from . import rules as R, ui

# ===================================================================== view metadata
#: Glyph and a caption saying what each section *governs* — not what it concludes.
_CAPTIONS: dict[str, tuple[str, str]] = {
    "1": ("🛰", "The field, and how many things there are to defend."),
    "2": ("◎", "How a point is scored, and why nothing ends level."),
    "3": ("✋", "What you may do with the ball, and for how long."),
    "4": ("⚖", "What the League equalises before kick-off."),
    "5": ("🟨", "What it costs to keep giving the ball away."),
    "6": ("🏆", "Who plays whom, and how a title is won."),
    "7": ("📊", "Everything the League prints about a player."),
}

_BULLET = re.compile(r"^\s*\*\s+(.*)$")
_STAT = re.compile(r"^\s{4}(\S+)\s{2,}(.+)$")

#: Extra illustration per section, appended after the prose. Deliberately empty: the laws
#: are written loosely enough that a pitch diagram would have to commit to a geometry the
#: text does not actually fix, and a picture that contradicts the rulebook is worse than none.
_EXTRAS: dict[str, str] = {}


def _blocks(text: str):
    """Split a section body into ('para' | 'bullets' | 'stats', payload) blocks."""
    for raw in text.strip().split("\n\n"):
        lines = [ln for ln in raw.split("\n") if ln.strip()]
        if not lines:
            continue
        if all(_BULLET.match(ln) for ln in lines):
            yield "bullets", [_BULLET.match(ln).group(1) for ln in lines]
        elif all(_STAT.match(ln) for ln in lines) and len(lines) > 2:
            yield "stats", [_STAT.match(ln).groups() for ln in lines]
        else:
            yield "para", " ".join(" ".join(lines).split())


def _bullet_cards(items: list[str]) -> str:
    cells = []
    for item in items:
        head, _, tail = item.partition("—")
        cells.append(f'<div class="fc"><div class="fh">{ui.emphasise(head.strip())}</div>'
                     f'<div class="ft">{escape(tail.strip())}</div></div>'
                     if tail else
                     f'<div class="fc"><div class="fh">{ui.emphasise(item.strip())}</div></div>')
    return f'<div class="cards">{"".join(cells)}</div>'


def _stat_table(rows: list[tuple[str, str]]) -> str:
    body = "".join(f'<tr><td class="mono">{escape(k)}</td><td>{escape(v)}</td></tr>'
                   for k, v in rows)
    return (f'<div class="tw"><table><thead><tr><th>published statistic</th>'
            f'<th>what the League says it measures</th></tr></thead>'
            f'<tbody>{body}</tbody></table></div>')


# ===================================================================== skins
#: One set of markup, two palettes. The notebook reads light, the betting site reads dark.
_PALETTES = {
    "light": dict(rail=ui.SURFACE_2, ink=ui.INK, body=ui.BODY, muted=ui.MUTED,
                  faint=ui.FAINT, line=ui.LINE, soft=ui.LINE_SOFT, accent=ui.ACCENT,
                  accent2=ui.ACCENT_2, chip="#eef0ff", sel=ui.SELECT, inset=ui.SURFACE_2,
                  hover="#eef0f8", card=ui.SURFACE, quiet="#555555"),
    "dark": dict(rail="#0f1116", ink="#e9ebf1", body="#c6cbd8", muted="#8b93a7",
                 faint="#5d6479", line="#272b36", soft="#1e222b", accent="#4c8dff",
                 accent2="#8b5cf6", chip="rgba(76,141,255,.14)", sel="rgba(76,141,255,.14)",
                 inset="#1a1d25", hover="#1a1d25", card="#14161c", quiet="#aeb5c6"),
}

#: Everything is under ``.rulesdoc`` so the dark skin can be dropped straight into a page
#: that already has a stylesheet of its own without the two fighting.
_CSS = """
.rulesdoc{{color:{body};font:14px/1.62 {sans};-webkit-font-smoothing:antialiased}}
.rulesdoc *{{box-sizing:border-box}}
.rulesdoc .wrap{{display:grid;grid-template-columns:212px 1fr;gap:0}}
/* ------------------------------------------------------------- rail */
.rulesdoc .rail{{position:sticky;align-self:start;overflow:auto;padding:18px 12px;
  background:{rail};border-right:1px solid {line}}}
.rulesdoc .crest{{font-weight:800;font-size:13px;color:{ink};line-height:1.3;
  letter-spacing:-.01em}}
.rulesdoc .crestsub{{font-size:10.5px;color:{faint};letter-spacing:.08em;
  text-transform:uppercase;margin:3px 0 14px}}
.rulesdoc .rail a{{display:flex;gap:8px;align-items:baseline;padding:7px 9px;
  border-radius:8px;text-decoration:none;color:{muted};font-size:12.5px;line-height:1.35;
  margin-bottom:2px;cursor:pointer}}
.rulesdoc .rail a .n{{font:700 11px {mono};color:{faint};flex:0 0 20px}}
.rulesdoc .rail a:hover{{background:{hover};color:{ink};text-decoration:none}}
.rulesdoc .rail a.on{{background:{sel};color:{accent};font-weight:700}}
.rulesdoc .rail a.on .n{{color:{accent}}}
.rulesdoc .railfoot{{margin-top:16px;padding:10px;border-radius:9px;background:{card};
  border:1px solid {line};font-size:11.5px;color:{muted};line-height:1.55}}
/* ------------------------------------------------------------- content */
.rulesdoc main{{padding:22px 30px 60px;max-width:780px}}
.rulesdoc .lede{{border-left:3px solid {accent2};background:{inset};
  border-radius:0 10px 10px 0;padding:13px 16px;margin-bottom:26px;font-size:13px;
  color:{body}}}
.rulesdoc .lede b{{color:{ink}}}
.rulesdoc section{{padding:6px 0 26px}}
.rulesdoc section+section{{border-top:1px solid {soft};padding-top:24px}}
.rulesdoc h2{{margin:0;font-size:17px;color:{ink};letter-spacing:-.01em;display:flex;
  gap:10px;align-items:center;font-weight:700}}
.rulesdoc h2 .no{{font:800 11px {mono};color:{accent};background:{chip};border-radius:6px;
  padding:3px 8px;letter-spacing:.04em}}
.rulesdoc h2 .gl{{font-size:15px}}
.rulesdoc .cap{{color:{faint};font-size:12px;margin:5px 0 12px}}
.rulesdoc p{{margin:0 0 12px}}
.rulesdoc .k{{color:{ink};font-weight:700;letter-spacing:.01em}}
.rulesdoc .q{{color:{accent2};font-weight:700;background:{sel};border-radius:5px;
  padding:0 5px;font-family:{mono};font-size:12.5px}}
/* ------------------------------------------------------------- components */
.rulesdoc .cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));
  gap:10px;margin:4px 0 16px}}
.rulesdoc .fc{{border:1px solid {line};border-radius:10px;padding:11px 13px;
  background:{inset}}}
.rulesdoc .fh{{font-size:12.5px;color:{ink};font-weight:700;margin-bottom:3px}}
.rulesdoc .ft{{font-size:12px;color:{muted};line-height:1.5}}
.rulesdoc .tw{{border:1px solid {line};border-radius:10px;overflow:hidden;margin:4px 0 14px}}
.rulesdoc table{{width:100%;border-collapse:collapse}}
.rulesdoc th{{text-align:left;padding:9px 13px;font-size:10.5px;letter-spacing:.07em;
  text-transform:uppercase;color:{faint};background:{inset};border-bottom:1px solid {line};
  font-weight:800}}
.rulesdoc td{{padding:8px 13px;border-bottom:1px solid {soft};font-size:12.5px;
  vertical-align:top;color:{quiet}}}
.rulesdoc tbody tr:last-child td{{border-bottom:none}}
.rulesdoc tbody tr:hover{{background:transparent}}
.rulesdoc td.mono{{font-family:{mono};font-size:11.5px;color:{accent};white-space:nowrap}}
"""

#: Rail links are ``data-go``, never ``href="#s3"``. Inside a ``srcdoc`` iframe there is no
#: document URL to resolve a fragment against, so the browser resolves it against the parent
#: origin and the click navigates the frame to ``localhost/#s3`` — a "site can't be reached"
#: page where the rulebook used to be. Scrolling by script has no such problem, and it works
#: identically when the same markup is served as a real page on the betting site.
_JS = """
<script>
(function(){
  const roots=document.querySelectorAll('.rulesdoc');
  roots.forEach(root=>{
    if(root.dataset.wired) return; root.dataset.wired='1';
    const links=[...root.querySelectorAll('.rail a')];
    const secs=links.map(a=>root.querySelector('#'+a.dataset.go));
    links.forEach((a,i)=>a.addEventListener('click',e=>{
      e.preventDefault();
      if(secs[i]) secs[i].scrollIntoView({behavior:'smooth',block:'start'});
    }));
    function spy(){
      let i=0;
      secs.forEach((s,j)=>{ if(s && s.getBoundingClientRect().top < innerHeight*0.28) i=j; });
      links.forEach((l,j)=>l.classList.toggle('on', j===i));
    }
    addEventListener('scroll',spy,{passive:true}); spy();
  });
})();
</script>"""

LEDE = ("<b>Seven sections, four minutes.</b> Two of them change how a stat sheet reads, and "
        "the League does not say which two — it publishes the laws and the numbers and leaves "
        "the joining-up to you. The bookmaker has already done it.")


def css(theme: str = "light", *, rail_top: str = "0", rail_height: str = "100vh",
        scroll_margin: str = "14px") -> str:
    """The stylesheet for one skin.

    ``rail_*`` place the sticky rail inside its container, and ``scroll_margin`` keeps a
    jumped-to section clear of whatever is pinned above it — on the betting site that is a
    56px topbar, which would otherwise land on the heading you just asked for.
    """
    palette = dict(_PALETTES[theme], sans=ui.SANS, mono=ui.MONO)
    return (_CSS.format(**palette)
            + f".rulesdoc .rail{{top:{rail_top};height:{rail_height}}}"
            + f".rulesdoc section{{scroll-margin-top:{scroll_margin}}}")


def inner(section: str | None = None) -> str:
    """The rulebook markup, skin-free — a ``.rulesdoc`` block ready to embed anywhere."""
    keys = [str(section).lstrip("§")] if section else list(R.SECTIONS)
    if any(k not in R.SECTIONS for k in keys):
        raise KeyError(f"no section {section!r}; sections are {R.contents()}")

    rail = "".join(
        f'<a data-go="s{k}"><span class="n">§{k}</span>'
        f'<span>{escape(R.SECTIONS[k][0])}</span></a>' for k in keys)

    out = []
    for k in keys:
        title, body = R.SECTIONS[k]
        glyph, caption = _CAPTIONS[k]
        parts = []
        for kind, payload in _blocks(body):
            if kind == "para":
                parts.append(f"<p>{ui.emphasise(payload)}</p>")
            elif kind == "bullets":
                parts.append(_bullet_cards(payload))
            else:
                parts.append(_stat_table(payload))
        out.append(
            f'<section id="s{k}"><h2><span class="no">§{k}</span>'
            f'<span class="gl">{glyph}</span>{escape(title)}</h2>'
            f'<div class="cap">{escape(caption)}</div>'
            f'{"".join(parts)}{_EXTRAS.get(k, "")}</section>')

    return f"""<div class="rulesdoc"><div class="wrap">
  <aside class="rail">
    <div class="crest">Laws of<br>Intergalactic Football</div>
    <div class="crestsub">GPL · 2026 edition</div>
    {rail}
    <div class="railfoot">Your agent reads this same text through its
      <b>read_rules</b> tool — whole, or one section at a time.</div>
  </aside>
  <main><div class="lede">{LEDE}</div>{"".join(out)}</main>
</div></div>{_JS}"""


def embedded(section: str | None = None, theme: str = "dark") -> str:
    """Style block plus markup, for dropping into a page that has its own stylesheet."""
    style = css(theme, rail_top="70px", rail_height="auto", scroll_margin="76px")
    return f"<style>{style}</style>{inner(section)}"


def document(section: str | None = None, theme: str = "light") -> str:
    """The whole rulebook as one self-contained HTML page."""
    palette = _PALETTES[theme]
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{escape(R.RULEBOOK_TITLE)}</title>
<style>html{{scroll-behavior:smooth}}
body{{margin:0;background:{palette['card']}}}
{css(theme)}</style></head><body>{inner(section)}</body></html>"""


def show(section: str | None = None, height: int = 760):
    """Display the rulebook in the notebook, sandboxed so its CSS cannot leak."""
    from IPython.display import HTML, display
    display(HTML(ui.frame(document(section), height)))
