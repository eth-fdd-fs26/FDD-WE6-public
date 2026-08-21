"""The problem, and the part of it nobody is allowed to change.

A three-class spiral, and a training protocol frozen in this file — same number of gradient
steps, same loss, same data, same initialisation seeds, for every candidate the search ever
looks at. That is not fussiness. It is the whole reason a score means anything.

If a candidate could choose its own training budget, the cheapest way to score well would be
to train for ten thousand steps, and the search would find that within about three
generations. Every knob you leave open is a knob that gets optimised, and only some of them
are the ones you meant. So the evolvable program gets to answer exactly one question —
*what shape should the network be, and how should it be optimised* — and everything else
lives here, where it cannot be touched.

The dataset is deliberately calibrated (see `notes/calibration.md`): the linear seed program
lands near chance-plus-a-bit, a compact network under the parameter cap does far better, and
the ceiling is well short of 100% so there is always somewhere left to climb.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

import numpy as np
import torch
import torch.nn as nn

# ===================================================================== the frozen protocol
TURNS = 2.0            # how far each spiral arm wraps — the difficulty dial
NOISE = 0.10           # radial jitter, as a fraction of radius
N_PER_CLASS = 200      # 600 training points in total
N_CLASSES = 3
STEPS = 200            # gradient steps. NOT evolvable — see the module docstring.
INIT_SEEDS = (0, 1)    # two weight initialisations per candidate, to blunt lucky starts
PARAM_CAP = 500        # trainable parameters a candidate may use

SEED_TRAIN, SEED_VAL, SEED_TEST = 42, 101, 202

torch.set_num_threads(2)   # keeps candidate timings comparable across machines


# ===================================================================== the data
def make_spirals(n_per_class: int = N_PER_CLASS, classes: int = N_CLASSES,
                 noise: float = NOISE, turns: float = TURNS,
                 seed: int = SEED_TRAIN) -> tuple[np.ndarray, np.ndarray]:
    """Interleaved Archimedean spirals, one arm per class.

    Args:
        n_per_class: points drawn along each arm.
        classes: number of arms, evenly spaced in angle.
        noise: jitter added to each point, scaled by its radius, so the arms are
            well separated near the origin and blur into each other at the rim.
        turns: how many full rotations each arm makes. The difficulty dial: more
            turns means more decision boundary to describe.
        seed: RNG seed. Same seed, same points, always.

    Returns:
        `(X, y)` with X of shape `(n_per_class * classes, 2)` and integer labels y.
    """
    rng = np.random.default_rng(seed)
    X, y = [], []
    for c in range(classes):
        t = np.sqrt(rng.uniform(0.04, 1.0, n_per_class)) * turns * 2 * math.pi
        r = t / (turns * 2 * math.pi)
        theta = t + c * (2 * math.pi / classes)
        px = r * np.cos(theta) + rng.normal(0, noise, n_per_class) * r
        py = r * np.sin(theta) + rng.normal(0, noise, n_per_class) * r
        X.append(np.stack([px, py], 1))
        y.append(np.full(n_per_class, c))
    return np.concatenate(X).astype(np.float32), np.concatenate(y).astype(np.int64)


@dataclass
class SpiralData:
    """Three splits, and a firm rule about who is allowed to look at each.

    train: the candidate is fitted on this.
    val:   the *search* is scored on this. Every generation sees it, so by the end of a
           run it has been consulted a hundred times and is no longer really held out.
    test:  looked at exactly once, by you, at the end. This is the only number that
           honestly answers "did the search find something, or did it fit my evaluator?"
    """

    X_train: torch.Tensor
    y_train: torch.Tensor
    X_val: torch.Tensor
    y_val: torch.Tensor
    X_test: torch.Tensor
    y_test: torch.Tensor


def load_data(turns: float = TURNS, noise: float = NOISE) -> SpiralData:
    """Build the three splits, standardised with training-set statistics only."""
    Xtr, ytr = make_spirals(noise=noise, turns=turns, seed=SEED_TRAIN)
    Xva, yva = make_spirals(noise=noise, turns=turns, seed=SEED_VAL)
    Xte, yte = make_spirals(noise=noise, turns=turns, seed=SEED_TEST)

    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-8      # fitted on train, applied to all three
    Xtr, Xva, Xte = (Xtr - mu) / sd, (Xva - mu) / sd, (Xte - mu) / sd

    t = torch.from_numpy
    return SpiralData(t(Xtr), t(ytr), t(Xva), t(yva), t(Xte), t(yte))


# ===================================================================== training a candidate
def count_params(model: nn.Module) -> int:
    """Trainable parameters — the quantity the cap and the size penalty both talk about."""
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


@dataclass
class TrainResult:
    """Everything the evaluator is allowed to know about a candidate."""

    ok: bool
    n_params: int = 0
    train_accuracy: float = 0.0
    val_accuracy: float = 0.0
    final_loss: float = float("nan")
    seconds: float = 0.0
    error: str = ""
    models: list = field(default_factory=list)


@torch.no_grad()
def accuracy(model: nn.Module, X: torch.Tensor, y: torch.Tensor) -> float:
    """Fraction of points the model labels correctly."""
    return (model(X).argmax(1) == y).float().mean().item()


def train_and_evaluate(program, data: SpiralData,
                       seeds: tuple[int, ...] = INIT_SEEDS) -> TrainResult:
    """Run one candidate through the frozen protocol.

    The candidate supplies `build_model()` and `build_optimizer(model)`. Everything else —
    the loss, the number of steps, the data, the seeds — comes from this module, identically
    for every candidate ever evaluated.

    Args:
        program: namespace exposing `build_model` and `build_optimizer`.
        data: the three splits.
        seeds: weight-initialisation seeds. The candidate is trained once per seed and the
            reported accuracies are averaged, so a candidate cannot win on a lucky start.

    Returns:
        A `TrainResult`. `ok=False` means the candidate failed to run at all — wrong output
        shape, an exception, or a loss that stopped being a number. It never raises: a
        broken candidate is a normal event in a search, not a crash.
    """
    t0 = time.time()
    loss_fn = nn.CrossEntropyLoss()
    train_accs, val_accs, models, final_loss = [], [], [], float("nan")

    for s in seeds:
        torch.manual_seed(s)
        try:
            model = program.build_model()
            opt = program.build_optimizer(model)
        except Exception as e:
            return TrainResult(ok=False, error=f"could not build: {type(e).__name__}: {e}",
                               seconds=time.time() - t0)

        probe = model(data.X_train[:4])
        if probe.shape != (4, N_CLASSES):
            return TrainResult(ok=False, seconds=time.time() - t0,
                               error=f"expected logits of shape (batch, {N_CLASSES}), "
                                     f"got {tuple(probe.shape)}")

        for _ in range(STEPS):
            opt.zero_grad()
            loss = loss_fn(model(data.X_train), data.y_train)
            if not torch.isfinite(loss):
                return TrainResult(ok=False, n_params=count_params(model),
                                   final_loss=float("nan"), seconds=time.time() - t0,
                                   error="loss became NaN or infinite")
            loss.backward()
            opt.step()

        final_loss = float(loss.detach())
        train_accs.append(accuracy(model, data.X_train, data.y_train))
        val_accs.append(accuracy(model, data.X_val, data.y_val))
        models.append(model)

    return TrainResult(
        ok=True,
        n_params=count_params(models[0]),
        train_accuracy=float(np.mean(train_accs)),
        val_accuracy=float(np.mean(val_accs)),
        final_loss=final_loss,
        seconds=time.time() - t0,
        models=models,
    )


def test_accuracy(result: TrainResult, data: SpiralData) -> float:
    """The number the search never sees. Averaged over the same initialisation seeds."""
    if not result.ok or not result.models:
        return 0.0
    return float(np.mean([accuracy(m, data.X_test, data.y_test) for m in result.models]))
