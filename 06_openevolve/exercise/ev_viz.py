"""Every diagram, plot and quiz in notebook 05, kept out of the notebook itself.

Two reasons. The teaching cells stay about the idea rather than about HTML, and a quiz whose
answer key lives in the cell above it is not a quiz. **Please don't read this file** — it
will spoil about fifteen minutes of the session for you.

Same shape as WE6's ``lc_viz``: generic renderers at the bottom, content dictionaries at the
top. Concept diagrams are inline HTML; anything showing actual numbers is matplotlib.
"""

from __future__ import annotations

import json as _json

from IPython.display import HTML, display

# ===================================================================== palette
ACC = "#4c5bd4"
ACC2 = "#7c4dbd"
OK = "#46b46e"
NO = "#e07a7a"
AMBER = "#e0a23c"
INK = "#2b2d6b"
MUTE = "#6b7280"
FONT = "system-ui,Segoe UI,Roboto,sans-serif"

CLASS_COLORS = ("#4c5bd4", "#e0796d", "#46b46e")


def _card(inner: str, maxw: int = 880) -> str:
    return (f'<div style="font-family:{FONT};border:1px solid #e6e8ee;border-radius:14px;'
            f'padding:18px;max-width:{maxw}px;background:#fff">{inner}</div>')


def _show(html: str):
    display(HTML(html))


def _mpl():
    """House matplotlib style, applied once, lazily."""
    import matplotlib.pyplot as plt
    plt.rcParams["figure.dpi"] = 110
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.spines.right"] = False
    plt.rcParams["font.size"] = 9
    return plt


# ===================================================================== diagrams
def roadmap():
    """What this notebook builds: the problem, the loop that searches it, the output."""
    verbs = [("🎣", "sample"), ("🧬", "mutate"), ("⚖️", "evaluate"), ("🗄️", "store")]
    verb_html = ""
    for i, (ic, name) in enumerate(verbs):
        arrow = ('<div style="align-self:center;font-size:15px;color:#b9a8e6;padding:0 1px">'
                 '→</div>' if i else "")
        verb_html += arrow + (
            f'<div style="flex:1 1 84px;min-width:76px;text-align:center;padding:8px 4px;'
            f'background:#fff;border:1px solid #e2d9f7;border-radius:9px">'
            f'<div style="font-size:17px">{ic}</div>'
            f'<div style="font-weight:800;font-size:10.5px;color:{INK};text-transform:uppercase;'
            f'letter-spacing:.03em">{name}</div></div>')

    def endbox(ic, title, sub, bg):
        return (f'<div style="flex:0 0 148px;text-align:center;padding:14px 10px;'
                f'background:{bg};border-radius:12px">'
                f'<div style="font-size:24px">{ic}</div>'
                f'<div style="font-weight:800;font-size:12.5px;color:{INK};margin-top:4px">'
                f'{title}</div>'
                f'<div style="font-size:10.5px;color:{MUTE};margin-top:3px;line-height:1.4">'
                f'{sub}</div></div>')

    big_arrow = '<div style="align-self:center;font-size:22px;color:#c9cee0;padding:0 6px">→</div>'

    loop_block = (
        f'<div style="flex:1 1 340px;padding:12px 12px 22px;background:#faf8ff;'
        f'border:1.5px dashed #cbb8f0;border-radius:14px">'
        f'<div style="display:flex;align-items:center;gap:2px">{verb_html}</div>'
        f'<div style="text-align:center;font-size:10.5px;color:{ACC2};margin-top:9px;'
        f'font-weight:700">↺ one generation, repeated many times</div></div>')

    problem_sub = "a spiral, three classes, no straight line separates them"
    output_sub = "the best design any generation found"
    body = (f'<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">'
            f'{endbox("🌀", "the problem", problem_sub, "#f6f8ff")}'
            f'{big_arrow}{loop_block}{big_arrow}'
            f'{endbox("🏆", "the output", output_sub, "#f3fbf6")}</div>')

    _show(f'<div style="font-family:{FONT};background:linear-gradient(135deg,#f6f8ff,#fbf5ff);'
          f'border-radius:18px;padding:20px 16px;margin:8px 0;border:1px solid #ecebff">'
          f'<div style="font-size:19px;font-weight:800;color:#3b2d6b;margin:0 0 4px">'
          f'🗺️ What this notebook builds</div>'
          f'<div style="font-size:12px;color:{MUTE};margin-bottom:14px">'
          f'A problem, a loop that searches it by repeating four steps, and the best design '
          f'the loop found.</div>{body}</div>')


def pipeline_diagram():
    """The problem feeding a loop of sample, mutate, evaluate, store, store looping back."""
    verbs = [("🎣", "sample"), ("🧬", "mutate"), ("⚖️", "evaluate"), ("🗄️", "store")]
    verb_html = ""
    for i, (ic, name) in enumerate(verbs):
        arrow = ('<div style="align-self:center;font-size:16px;color:#b9a8e6;padding:0 2px">'
                 '→</div>' if i else "")
        verb_html += arrow + (
            f'<div style="flex:1 1 100px;min-width:90px;text-align:center;padding:10px 6px;'
            f'background:#fff;border:1px solid #e2d9f7;border-radius:10px">'
            f'<div style="font-size:19px">{ic}</div>'
            f'<div style="font-weight:800;font-size:11.5px;color:{INK};text-transform:uppercase;'
            f'letter-spacing:.03em">{name}</div></div>')

    loop_block = (
        f'<div style="padding:14px 14px 16px;background:#faf8ff;'
        f'border:1.5px dashed #cbb8f0;border-radius:14px">'
        f'<div style="display:flex;align-items:center;gap:2px">{verb_html}</div>'
        f'<div style="text-align:center;font-size:11px;color:{ACC2};margin-top:12px;'
        f'font-weight:700">🗄️ store ↩ feeds the next 🎣 sample, one generation at a time'
        f'</div></div>')

    problem_box = (
        f'<div style="flex:0 0 140px;text-align:center;padding:14px 10px;'
        f'background:#f6f8ff;border-radius:12px">'
        f'<div style="font-size:24px">🌀</div>'
        f'<div style="font-weight:800;font-size:12.5px;color:{INK};margin-top:4px">'
        f'the problem</div></div>')
    output_box = (
        f'<div style="flex:0 0 140px;text-align:center;padding:14px 10px;'
        f'background:#f3fbf6;border-radius:12px">'
        f'<div style="font-size:24px">🏆</div>'
        f'<div style="font-weight:800;font-size:12.5px;color:{INK};margin-top:4px">'
        f'best program</div>'
        f'<div style="font-size:10px;color:{MUTE};margin-top:2px">the champion after '
        f'many generations</div></div>')
    big_arrow = ('<div style="align-self:center;font-size:22px;color:#c9cee0;padding:0 6px">'
                 '→</div>')
    out_arrow = (
        f'<div style="align-self:center;text-align:center;font-size:11px;color:{OK};'
        f'font-weight:700;padding:0 6px">↳<br>store also<br>keeps this</div>')

    _show(_card(
        f'<div style="font-weight:800;font-size:15px;color:{INK};margin-bottom:12px">'
        f'The loop: sample, mutate, evaluate, store</div>'
        f'<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">'
        f'{problem_box}{big_arrow}<div style="flex:1 1 380px">{loop_block}</div>'
        f'{out_arrow}{output_box}</div>', 1040))


def sample_rule_diagram():
    """The archive's four size cells, and the 2/3-versus-1/3 rule that picks a parent."""
    cells = [("tiny", "≤50", 9, 0.45, False),
             ("small", "51–150", 75, 0.74, False),
             ("medium", "151–300", 210, 0.79, False),
             ("large", "301+", 480, 0.81, True)]
    cards = ""
    for name, rng_lbl, params, score, is_best in cells:
        crown = " 👑" if is_best else ""
        border = f"2px solid {ACC}" if is_best else "1px solid #e6e8ee"
        arrow_here = (f'<div style="text-align:center;font-size:11px;color:{ACC};'
                      f'font-weight:800;margin-top:4px">↑ 1/3</div>' if is_best else
                      f'<div style="text-align:center;font-size:11px;color:{AMBER};'
                      f'font-weight:800;margin-top:4px">↑ 2/3</div>')
        cards += (
            f'<div style="flex:1 1 130px;text-align:center;padding:10px 8px;background:#fff;'
            f'border:{border};border-radius:10px">'
            f'<div style="font-weight:800;font-size:12px;color:{INK};text-transform:uppercase">'
            f'{name}{crown}</div>'
            f'<div style="font-size:10px;color:{MUTE};margin:1px 0 6px">{rng_lbl} params</div>'
            f'<div style="font-size:10.5px;color:{MUTE}">champion</div>'
            f'<div style="font-size:12.5px;font-weight:700;color:{ACC2}">{params} params</div>'
            f'<div style="font-size:12.5px;font-weight:700;color:{ACC}">score {score:.2f}</div>'
            f'{arrow_here}</div>')

    rule_html = (
        f'<div style="margin-top:10px;padding:10px 12px;background:#fbf7ee;border-left:3px '
        f'solid {AMBER};border-radius:8px;font-size:12px;color:#6b5420;line-height:1.6">'
        f'<b style="color:{AMBER}">2/3 of the time:</b> take the champion of a random cell '
        f'(explore).</div>'
        f'<div style="margin-top:6px;padding:10px 12px;background:#f2edff;border-left:3px '
        f'solid {ACC};border-radius:8px;font-size:12px;color:#3b2d6b;line-height:1.6">'
        f'<b style="color:{ACC}">1/3 of the time:</b> take the single overall best program, '
        f'wherever it lives (exploit).</div>')

    _show(_card(
        f'<div style="font-weight:800;font-size:15px;color:{INK};margin-bottom:3px">'
        f'The parent pool: one champion per cell</div>'
        f'<div style="font-size:12.5px;color:{MUTE};margin-bottom:12px">'
        f'Example champions (illustrative numbers).</div>'
        f'<div style="display:flex;flex-wrap:wrap;gap:8px">{cards}</div>{rule_html}', 900))


def problem_and_search(data):
    """The dataset on the left; three ways of searching a FIXED hyperparameter space on the right."""
    import numpy as np
    plt = _mpl()
    fig = plt.figure(figsize=(10, 4.3))
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.3], wspace=0.4)

    ax0 = fig.add_subplot(gs[0])
    X, y = data.X_train.numpy(), data.y_train.numpy()
    for c in range(3):
        m = y == c
        ax0.scatter(X[m, 0], X[m, 1], s=7, c=CLASS_COLORS[c], label=f"class {c}", alpha=.75)
    ax0.set_title("The data: three interleaved arms", fontsize=9.5)
    ax0.set_xlabel("sensor 1 (standardised)")
    ax0.set_ylabel("sensor 2 (standardised)")
    ax0.legend(frameon=False, fontsize=7.5, loc="upper right")
    ax0.set_aspect("equal")

    rng = np.random.default_rng(0)
    inner = gs[1].subgridspec(1, 3, wspace=0.15)
    grid_x, grid_y = np.meshgrid(np.linspace(.15, .85, 4), np.linspace(.15, .85, 4))
    strategies = [
        ("by hand", rng.uniform(0.15, 0.85, (6, 2)), MUTE),
        ("grid search", np.stack([grid_x.ravel(), grid_y.ravel()], 1), ACC2),
        ("optuna", np.clip(rng.normal(0.72, 0.09, (24, 2)), 0.04, 0.96), ACC),
    ]
    for i, (name, pts, colour) in enumerate(strategies):
        axi = fig.add_subplot(inner[i])
        axi.scatter(pts[:, 0], pts[:, 1], s=13, c=colour, alpha=.8)
        axi.set_xlim(0, 1)
        axi.set_ylim(0, 1)
        axi.set_xticks([])
        axi.set_yticks([])
        for spine in axi.spines.values():
            spine.set_edgecolor("#d7d9e6")
        axi.set_title(name, fontsize=9, color=INK)
        if i == 0:
            axi.set_ylabel("width", fontsize=7.5, color=MUTE)
        axi.set_xlabel("learning rate", fontsize=7.5, color=MUTE)

    fig.text(0.685, 0.955, "Searching a FIXED hyperparameter space", fontsize=10.5,
             fontweight="bold", color=INK, ha="center")
    fig.text(0.685, 0.02, "same architecture family in all three, only the numbers move",
             fontsize=8.5, color=MUTE, ha="center", style="italic")
    plt.tight_layout(rect=[0, 0.05, 1, 0.91])
    plt.show()


def four_verbs():
    """The loop you are about to hold in your hands, and who authors each piece of it."""
    verbs = [
        ("🎣", "SAMPLE", "pick a parent<br>from the archive", "provided", MUTE, None),
        ("🧬", "MUTATE", "the LLM proposes<br>a rewrite", "machinery provided", MUTE,
         "you write its brief"),
        ("⚖️", "EVALUATE", "run it,<br>get a number", "you write this", ACC, None),
        ("🗄️", "STORE", "keep it if it<br>earns a slot", "you write this", ACC, None),
    ]
    cells = ""
    for i, (ic, name, what, who, col, extra) in enumerate(verbs):
        arrow = ('<div style="align-self:center;font-size:20px;color:#c9cee0;padding:0 2px">→</div>'
                 if i else "")
        border = f"2px solid {col}" if col == ACC else "1px solid #e6e8ee"
        extra_html = (f'<div style="font-size:10.5px;font-weight:700;color:{ACC};'
                      f'text-transform:uppercase;letter-spacing:.04em;margin-top:1px">'
                      f'{extra}</div>' if extra else "")
        cells += arrow + (
            f'<div style="flex:1 1 130px;min-width:120px;text-align:center;padding:12px 8px;'
            f'background:#fff;border:{border};border-radius:12px">'
            f'<div style="font-size:22px">{ic}</div>'
            f'<div style="font-weight:800;font-size:13px;color:{INK};letter-spacing:.04em">{name}</div>'
            f'<div style="font-size:11.5px;color:{MUTE};margin:5px 0;line-height:1.45">{what}</div>'
            f'<div style="font-size:10.5px;font-weight:700;color:{col};text-transform:uppercase;'
            f'letter-spacing:.05em">{who}</div>{extra_html}</div>')
    _show(_card(
        f'<div style="font-weight:800;font-size:15px;color:{INK};margin-bottom:3px">'
        f'One loop, four verbs, three things are yours</div>'
        f'<div style="font-size:12.5px;color:{MUTE};margin-bottom:14px;line-height:1.6">'
        f'SAMPLE, and the machinery behind MUTATE, are already written, because they are more '
        f'interesting to read than to type. What you author are the three pieces that decide '
        f'what "good" means here: the score, the archive rule, and the instructions MUTATE '
        f'sends to the model.</div>'
        f'<div style="display:flex;flex-wrap:wrap;gap:6px">{cells}</div>'
        f'<div style="margin-top:14px;padding:10px 12px;background:#f7f5ff;border-left:3px solid '
        f'{ACC2};border-radius:8px;font-size:12px;color:#4b3f7a;line-height:1.6">'
        f'The loop closes: STORE decides who is in the archive, and SAMPLE draws the next '
        f'parent from it. That is why the archive rule is not bookkeeping, it steers '
        f'everything that happens next.</div>', 920))


def frozen_vs_evolvable():
    """The seed program, with the evolve block highlighted against everything that is frozen."""
    from minievolve import seed as _seed
    src = _seed.SEED_PROGRAM
    start, end = _seed.BLOCK_START, _seed.BLOCK_END
    i, j = src.index(start), src.index(end) + len(end)
    head, block, tail = src[:i], src[i:j], src[j:]

    code_html = (
        f'<pre style="margin:0;background:#f8f9fc;border-radius:10px;padding:12px;'
        f'font-size:11px;line-height:1.55;overflow-x:auto;white-space:pre-wrap">'
        f'<span style="color:{MUTE}">{_esc(head)}</span>'
        f'<span style="background:#efe7fb;box-shadow:0 0 0 3px #efe7fb;border-left:3px solid '
        f'{ACC2};border-radius:4px;color:{INK}">{_esc(block)}</span>'
        f'<span style="color:{MUTE}">{_esc(tail)}</span></pre>')

    frozen_items = [("the training loop", "200 gradient steps, cross-entropy, full batch"),
                    ("the data", "same spiral, same splits, same standardisation"),
                    ("the seeds", "two weight initialisations, fixed"),
                    ("the parameter cap", "checked by your evaluator, not by the model")]
    frozen_html = "".join(
        f'<div style="background:#fff;border:1px solid #e6e8ee;border-radius:9px;'
        f'padding:7px 10px;margin-bottom:6px">'
        f'<b style="font-size:11.5px;color:{INK}">{n}</b>'
        f'<div style="font-size:11px;color:{MUTE};margin-top:1px">{d}</div></div>'
        for n, d in frozen_items)

    _show(_card(
        f'<div style="font-weight:800;font-size:15px;color:{INK};margin-bottom:3px">'
        f'The evolve block, highlighted</div>'
        f'<div style="font-size:12.5px;color:{MUTE};margin-bottom:12px;line-height:1.6">'
        f'The purple region between the markers is the only text the model is ever shown as '
        f'rewritable. Everything in grey, plus the items on the right, is fixed and the model '
        f'never gets a chance to touch it. Every knob you leave open is a knob that gets '
        f'optimised, and only some of them are the ones you meant: if a candidate could set '
        f'its own training budget, the cheapest way to score well would be to train ten times '
        f'longer, not to be better designed.</div>'
        f'<div style="display:flex;flex-wrap:wrap;gap:14px">'
        f'<div style="flex:2 1 380px;min-width:320px">{code_html}</div>'
        f'<div style="flex:1 1 220px;min-width:200px">'
        f'<div style="font-weight:800;font-size:12.5px;color:{INK};margin-bottom:6px">'
        f'🔒 Frozen outside this file too</div>{frozen_html}</div></div>', 980))


def archive_cards(archive, labels=None):
    """Show what each behavioural cell is currently holding.

    Not a chart: the point is to read the *code* that survived in each size class, which a
    bar chart cannot show you.
    """
    from minievolve import loop as _loop
    labels = labels or _loop.BUCKET_LABELS
    if not archive:
        _show(_card("<i>archive is empty</i>"))
        return

    cards = ""
    best = max(c.score for c in archive.values())
    for key in sorted(archive, key=lambda k: (k if isinstance(k, int) else 0)):
        c = archive[key]
        name = labels[key] if isinstance(key, int) and key < len(labels) else str(key)
        crown = " 👑" if abs(c.score - best) < 1e-12 else ""
        body = c.block.strip()
        body = body if len(body) < 640 else body[:640] + "\n…"
        cards += (
            f'<div style="flex:1 1 330px;min-width:300px;background:#fff;border:1px solid '
            f'{"#c9c2f0" if crown else "#e6e8ee"};border-radius:12px;padding:12px">'
            f'<div style="display:flex;justify-content:space-between;align-items:baseline">'
            f'<span style="font-weight:800;font-size:12.5px;color:{INK}">{name}{crown}</span>'
            f'<span style="font-size:12px;color:{ACC};font-weight:700">score {c.score:.3f}</span>'
            f'</div>'
            f'<div style="font-size:11px;color:{MUTE};margin:2px 0 8px">'
            f'{c.metrics.get("params", "?")} params · '
            f'val {c.metrics.get("accuracy", float("nan")):.3f} · found in generation '
            f'{c.generation}</div>'
            f'<pre style="margin:0;background:#f8f9fc;border-radius:8px;padding:9px;font-size:10.5px;'
            f'line-height:1.45;overflow-x:auto;white-space:pre">{_esc(body)}</pre></div>')
    _show(_card(
        f'<div style="font-weight:800;font-size:15px;color:{INK};margin-bottom:3px">'
        f'The archive, cell by cell</div>'
        f'<div style="font-size:12.5px;color:{MUTE};margin-bottom:12px;line-height:1.6">'
        f'Each size class keeps its own champion. Competition is local, so a small program is '
        f'never deleted by a big one that merely scores higher.</div>'
        f'<div style="display:flex;flex-wrap:wrap;gap:9px">{cards}</div>', 960))


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ===================================================================== plots (real numbers)
def plot_spirals(data):
    """The dataset, and why a straight line has no chance on it."""
    plt = _mpl()
    fig, ax = plt.subplots(figsize=(4.2, 4.2))
    X, y = data.X_train.numpy(), data.y_train.numpy()
    for c in range(3):
        m = y == c
        ax.scatter(X[m, 0], X[m, 1], s=7, c=CLASS_COLORS[c], label=f"class {c}", alpha=.75)
    ax.set_xlabel("sensor 1 (standardised)")
    ax.set_ylabel("sensor 2 (standardised)")
    ax.set_title("600 training points, three interleaved arms")
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    ax.set_aspect("equal")
    plt.tight_layout()
    plt.show()


def plot_boundary(models, data, titles, split="test"):
    """Decision boundaries side by side, over the split you name.

    Args:
        models: one model, or a list of them.
        data: a `SpiralData`.
        titles: title per model.
        split: which points to draw on top — "train", "val" or "test".
    """
    import numpy as np
    import torch
    plt = _mpl()

    models = models if isinstance(models, (list, tuple)) else [models]
    titles = titles if isinstance(titles, (list, tuple)) else [titles]
    X = getattr(data, f"X_{split}").numpy()
    y = getattr(data, f"y_{split}").numpy()

    lo, hi = X.min() - .4, X.max() + .4
    gx, gy = np.meshgrid(np.linspace(lo, hi, 220), np.linspace(lo, hi, 220))
    grid = torch.from_numpy(np.stack([gx.ravel(), gy.ravel()], 1).astype("float32"))

    fig, axes = plt.subplots(1, len(models), figsize=(4.1 * len(models), 4.2), squeeze=False)
    from matplotlib.colors import ListedColormap
    cmap = ListedColormap([c + "44" for c in CLASS_COLORS])

    for ax, model, title in zip(axes[0], models, titles):
        with torch.no_grad():
            zz = model(grid).argmax(1).numpy().reshape(gx.shape)
        ax.contourf(gx, gy, zz, levels=[-.5, .5, 1.5, 2.5], cmap=cmap)
        for c in range(3):
            m = y == c
            ax.scatter(X[m, 0], X[m, 1], s=6, c=CLASS_COLORS[c], alpha=.85)
        acc = (model(getattr(data, f"X_{split}")).argmax(1).numpy() == y).mean()
        ax.set_title(f"{title}\n{split} accuracy {acc:.1%}", fontsize=9.5)
        ax.set_xlabel("sensor 1")
        ax.set_ylabel("sensor 2")
        ax.set_aspect("equal")
    plt.tight_layout()
    plt.show()


def plot_progress(history):
    """Best-so-far score and model size, generation by generation."""
    plt = _mpl()
    gens = [c.generation for c in history]
    scores = [c.score for c in history]
    best = []
    for s in scores:
        best.append(max(best[-1], s) if best else s)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.4))

    a1.plot(gens, best, color=ACC, lw=2, label="best so far")
    a1.scatter(gens, scores, s=22, color=ACC2, alpha=.65, zorder=3, label="each candidate")
    failed = [(g, s) for g, s in zip(gens, scores) if s == 0.0]
    if failed:
        a1.scatter(*zip(*failed), s=30, color=NO, zorder=4, marker="x",
                   label="rejected (cap / NaN / broken)")
    a1.set_xlabel("generation")
    a1.set_ylabel("score")
    a1.set_title("The score climbs, in jumps not smoothly")
    a1.legend(frameon=False, fontsize=7.5, loc="lower right")

    sized = [(c.generation, c.metrics.get("params", 0)) for c in history
             if c.score > 0 and c.metrics.get("params")]
    if sized:
        a2.scatter(*zip(*sized), s=26, color=AMBER, alpha=.8)
        champ = max(history, key=lambda c: c.score)
        a2.axhline(champ.metrics.get("params", 0), color=OK, lw=1.4, ls="--",
                   label=f"winner: {champ.metrics.get('params')} params")
        a2.legend(frameon=False, fontsize=7.5)
    a2.set_xlabel("generation")
    a2.set_ylabel("trainable parameters")
    a2.set_title("Size of what survived")
    plt.tight_layout()
    plt.show()


def run_tracker():
    """A live-updating table of generations, for use as `evolve`'s `on_step` callback.

    Call it once to get `on_step`, pass `on_step` to `loop.evolve(..., on_step=on_step)`
    (or call `on_step(cand, archive)` yourself once per candidate, e.g. while replaying a
    recorded run through your own STORE). The table updates in place rather than printing a
    new line per generation.
    """
    rows = []
    uid = _uid("run", [len(rows), id(rows)])

    def _row(c, archive):
        kept = c.score > 0
        badge = (f'<span style="color:{OK};font-weight:700">kept</span>' if kept else
                 f'<span style="color:{NO};font-weight:700">rejected</span>')
        params = c.metrics.get("params", "-")
        note = _esc(c.note[:60]) if c.note else ""
        return (f'<tr><td style="padding:4px 8px">{c.generation}</td>'
                f'<td style="padding:4px 8px">{badge}</td>'
                f'<td style="padding:4px 8px;text-align:right">{c.score:.4f}</td>'
                f'<td style="padding:4px 8px;text-align:right">{params}</td>'
                f'<td style="padding:4px 8px;text-align:center">{len(archive)}</td>'
                f'<td style="padding:4px 8px;color:{MUTE};font-size:11px">{note}</td></tr>')

    def _table():
        head = ('<tr style="text-align:left;color:' + MUTE + ';font-size:11px;'
                'text-transform:uppercase">'
                '<th style="padding:4px 8px">gen</th><th style="padding:4px 8px">status</th>'
                '<th style="padding:4px 8px;text-align:right">score</th>'
                '<th style="padding:4px 8px;text-align:right">params</th>'
                '<th style="padding:4px 8px;text-align:center">cells</th>'
                '<th style="padding:4px 8px">note</th></tr>')
        return (f'<div style="font-family:{FONT};border:1px solid #e6e8ee;border-radius:12px;'
                f'padding:6px 10px;max-width:820px;background:#fff">'
                f'<div style="font-weight:800;font-size:13px;color:{INK};padding:6px 4px 2px">'
                f'Generation by generation</div>'
                f'<table style="border-collapse:collapse;width:100%;font-size:12.5px">'
                f'<thead style="border-bottom:2px solid #e6e8ee">{head}</thead>'
                f'<tbody>{"".join(rows)}</tbody></table></div>')

    handle = display(HTML(_table()), display_id=uid)

    def on_step(cand, archive):
        rows.append(_row(cand, archive))
        handle.update(HTML(_table()))

    return on_step


def plot_archive_vs_greedy(qd_archive, greedy_archive, history):
    """What the two retention rules were holding at the end of the same run."""
    plt = _mpl()
    from minievolve import loop as _loop

    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    cells = sorted(qd_archive)
    xs = range(len(cells))
    ax.bar(xs, [qd_archive[k].score for k in cells], color=ACC, width=.6,
           label="quality-diversity: one champion per size class")
    g = max(greedy_archive.values(), key=lambda c: c.score)
    ax.axhline(g.score, color=NO, lw=1.6, ls="--",
               label=f"greedy: one program only ({g.metrics.get('params')} params)")
    ax.set_xticks(list(xs))
    ax.set_xticklabels([_loop.BUCKET_LABELS[k] if isinstance(k, int) else str(k)
                        for k in cells], fontsize=8)
    ax.set_ylabel("score")
    ax.set_title("Same candidates, same scores, different things kept")
    ax.legend(frameon=False, fontsize=7.5, loc="lower right")
    plt.tight_layout()
    plt.show()


# ===================================================================== quizzes
_MC = {
    "output_shape": (
        "🧠 Quick check: problem understanding",
        "Why does the model return an output of shape (N, 3)?",
        [
            "Three logits per sample, one raw score per class. Softmax turns them into class "
            "probabilities, and the largest score gives the predicted class.",
            "Three trained weights of the network.",
            "The two input coordinates plus a bias.",
            "Three probabilities that already sum to one, before any activation is applied.",
        ], 0,
        "A logit is a raw, unnormalised score, one per class. Softmax turns the three logits "
        "into probabilities that sum to one, and the class with the largest logit is also the "
        "class with the largest probability, so no extra step is needed to make a prediction. "
        "None of the wrong options describe what those three numbers actually are: not a "
        "weight, not an input, and not already a probability."),

    "frozen": (
        "🧠 Quick check: problem understanding",
        "Why is the training protocol frozen outside the evolve block?",
        [
            "So that every candidate design is trained and judged under identical conditions. "
            "The search then compares designs fairly, and a candidate cannot win by training "
            "longer instead of being better designed.",
            "Because changing the training loop would make the code run slower.",
            "Because the language model cannot write training loops.",
            "To save GPU memory.",
        ], 0,
        "If a candidate could change how long it trains, the cheapest way to win would be to "
        "train for far longer rather than to have a better architecture, and the search would "
        "find that shortcut within a handful of generations. Freezing the protocol removes the "
        "shortcut, so a higher score can only mean a better design. It has nothing to do with "
        "speed, GPU memory, or what the model is capable of writing."),

    "archive": (
        "🧠 Quick check: what does keeping only the best program cost you?",
        "Generation 6 finds a 480-parameter program scoring 0.79. Generation 7 finds a "
        "70-parameter program scoring 0.74. Under a rule that keeps only the single best "
        "program, what happens next?",
        [
            "Both survive, because they are different sizes.",
            "The small one is discarded, and every later mutation descends from the big one, "
            "so the compact branch is never explored again.",
            "The small one survives, because the score penalises parameters.",
            "Neither survives; the archive only keeps programs above 0.80.",
        ], 1,
        "This is the whole argument for MAP-Elites. The archive is not storage. It is the "
        "pool that SAMPLE draws parents from, so deleting a lineage means never mutating it "
        "again. A 70-parameter program at 0.74 may be two edits from 0.85; you will never "
        "find out. Slide 11: keeping only the best is how you guarantee a local optimum."),

    "validation": (
        "🧠 Quick check: why did we hold a third split back?",
        "Your evaluator scores every candidate on the validation split. Over 15 generations "
        "that split gets consulted 15 times, and the search keeps whatever scored best on it. "
        "What is the problem?",
        [
            "There is none: validation data is held out of training, which is what matters.",
            "The search is selecting for whatever happens to work on that particular sample, "
            "noise included, so its own score is an optimistic estimate of real performance.",
            "The validation split is too small, and a larger one would remove the issue.",
            "The problem is only that we trained on two seeds instead of one.",
        ], 1,
        "Held out from <i>training</i> is not the same as held out from <i>selection</i>. "
        "Anything you optimise against stops being an honest estimate, and with enough "
        "generations the search finds the noise. That is slide 17's 'noisy evaluation selects "
        "noise', and it is why the test split in this notebook is looked at exactly once, "
        "at the end, by you."),

    "test_gap": (
        "🧠 Reflection: the validation-to-test gap",
        "We see a small drop in performance on the test set compared to the validation set. "
        "Why?",
        [
            "It is the split. The validation and test sets are two different samples of "
            "points, and by chance they are not equally hard.",
            "Points far from the centre have more noise and are harder to classify.",
            "The search overfit the validation set.",
        ], 0,
        "The correct answer is the split. The validation set and the test set are two "
        "different samples of points, and they are not equally hard by chance. This is not "
        "overfitting. We only ran a few generations, and the seed program, which was never "
        "selected on the validation set, actually shows the larger gap between validation and "
        "test. If selection had caused the drop, the seed would not show it. So the small "
        "difference comes from the two samples differing slightly in difficulty, not from the "
        "search fitting the validation set."),

    "greedy_vs_qd": (
        "🧠 Reflection: quality-diversity versus greedy",
        "Both the quality-diversity archive and the greedy archive end with the same best "
        "program. Looking at the graph, what is the real difference between them?",
        [
            "The greedy archive keeps fewer programs, so it throws away the non-leading "
            "parents that later produced the winner.",
            "The greedy archive finds a better final program.",
            "The two archives are identical.",
            "The quality-diversity archive uses more generations.",
        ], 0,
        "Both archives keep the same champion, so greedy does not lose on the final program. "
        "It loses because it keeps only one slot and deletes every program that is not "
        "currently best. Those deleted programs are exactly the parents that the eventual "
        "winner descended from. The archive is the pool that sample draws parents from, so "
        "deleting them removes future paths."),
}

_TF = {
    "shape": (
        "🧠 Is your problem shaped like this? Click the ones that are true.",
        [("A candidate has to be scoreable automatically, in seconds to minutes.", True),
         ("You need a baseline that already works, however badly.", True),
         ("The method produces insight into <i>why</i> the answer works.", False),
         ("A cheap degenerate solution that scores well will eventually be found.", True),
         ("Bigger language models remove the need for a held-out set.", False),
         ("Most of the human effort moves to defining the search space and the score.", True)],
    ),
}

# ===================================================================== renderers
def _uid(prefix: str, payload) -> str:
    return f"{prefix}_{abs(hash(_json.dumps(payload, default=str))) % 10 ** 8}"


_QUIZ_CSS = """
#__UID__{font-family:__FONT__;border:1px solid #e6e8ee;border-radius:14px;padding:16px;
  max-width:820px;background:#fff}
#__UID__ .h{font-weight:800;font-size:14.5px;margin-bottom:4px;color:#2b2d6b}
#__UID__ .q{color:#444;font-size:13px;margin-bottom:12px;line-height:1.6}
#__UID__ .o{display:flex;align-items:flex-start;gap:10px;border:1px solid #e2e5ef;
  border-radius:10px;padding:10px 12px;margin-bottom:8px;cursor:pointer;font-size:13px;
  line-height:1.55;transition:.12s}
#__UID__ .o:hover{border-color:#7c4dbd;background:#faf9ff}
#__UID__ .o.sel{border-color:#7c4dbd;background:#f2edff}
#__UID__ .o.ok{border-color:#46b46e;background:#e7f7ec}
#__UID__ .o.no{border-color:#e07a7a;background:#fdecec}
#__UID__ .btn{cursor:pointer;border:none;border-radius:8px;padding:9px 18px;font-size:13px;
  font-weight:700;color:#fff;background:linear-gradient(135deg,#4c5bd4,#7c4dbd);margin-top:6px}
#__UID__ .rev{font-size:12.5px;color:#444;margin-top:10px;line-height:1.6}
#__UID__ .dot{width:14px;height:14px;border-radius:50%;border:2px solid #c9cee0;flex:0 0 14px;
  margin-top:2px}
#__UID__ .o.sel .dot{border-color:#7c4dbd;background:#7c4dbd}
"""


def mc_quiz(key: str):
    title, question, options, answer, reveal = _MC[key]
    uid = _uid("mc", (question, options))
    data = _json.dumps({"opts": options, "ans": answer, "reveal": reveal})
    _show(f"""<style>{_QUIZ_CSS.replace("__UID__", uid).replace("__FONT__", FONT)}</style>
<div id="{uid}"><div class="h">{title}</div><div class="q">{question}</div>
<div class="list"></div><button class="btn">Check my answer</button>
<div class="rev"></div></div>
<script>(function(){{
  const D={data}, root=document.getElementById("{uid}");
  let idx=D.opts.map((_,i)=>i);
  for(let i=idx.length-1;i>0;i--){{const j=Math.floor(Math.random()*(i+1));
    [idx[i],idx[j]]=[idx[j],idx[i]];}}
  const list=root.querySelector(".list");
  idx.forEach(o=>{{const e=document.createElement("div");e.className="o";e.dataset.i=o;
    e.innerHTML='<span class="dot"></span><span>'+D.opts[o]+'</span>';list.appendChild(e);}});
  const opts=list.querySelectorAll(".o"); let sel=null;
  opts.forEach(o=>o.addEventListener("click",()=>{{sel=+o.dataset.i;
    opts.forEach(x=>x.classList.remove("sel","ok","no"));o.classList.add("sel");
    root.querySelector(".rev").textContent="";}}));
  root.querySelector(".btn").addEventListener("click",()=>{{
    if(sel===null){{root.querySelector(".rev").textContent="Pick one first.";return;}}
    opts.forEach(o=>{{const i=+o.dataset.i;o.classList.remove("sel");
      if(i===D.ans)o.classList.add("ok");else if(i===sel)o.classList.add("no");}});
    root.querySelector(".rev").innerHTML=(sel===D.ans?"✅ Correct. ":"❌ Not quite. ")+D.reveal;
  }});}})();</script>""")


def true_false_quiz(key: str):
    title, statements = _TF[key]
    uid = _uid("tf", (title, [s for s, _ in statements]))
    data = _json.dumps([{"t": s, "v": v} for s, v in statements])
    _show(f"""<style>{_QUIZ_CSS.replace("__UID__", uid).replace("__FONT__", FONT)}</style>
<div id="{uid}"><div class="h">{title}</div>
<div class="q">Click every statement you think is true, then check.</div>
<div class="list"></div><button class="btn">Check</button><div class="rev"></div></div>
<script>(function(){{
  const D={data}, root=document.getElementById("{uid}");
  let idx=D.map((_,i)=>i);
  for(let i=idx.length-1;i>0;i--){{const j=Math.floor(Math.random()*(i+1));
    [idx[i],idx[j]]=[idx[j],idx[i]];}}
  const list=root.querySelector(".list");
  idx.forEach(o=>{{const e=document.createElement("div");e.className="o";e.dataset.i=o;
    e.innerHTML='<span class="dot"></span><span>'+D[o].t+'</span>';list.appendChild(e);}});
  const opts=list.querySelectorAll(".o");
  opts.forEach(o=>o.addEventListener("click",()=>o.classList.toggle("sel")));
  root.querySelector(".btn").addEventListener("click",()=>{{
    let right=0;
    opts.forEach(o=>{{const d=D[+o.dataset.i], picked=o.classList.contains("sel");
      o.classList.remove("sel");
      if(picked===d.v)right++;
      if(d.v)o.classList.add("ok"); else if(picked)o.classList.add("no");}});
    root.querySelector(".rev").innerHTML=right+" / "+D.length+" correct"+
      (right===D.length?" 🎉":" (green is what is actually true).");
  }});}})();</script>""")
