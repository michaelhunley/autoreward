# (C) Copyright 2026 michaelhunley/autoreward contributors. MIT licensed.
"""
descent.py -- a DRIVER for the multi-objective value layer: bisection + joint Gauss-Newton.

`optimizer.run` (DFS + Pareto + maximin) is the general-purpose driver: it treats candidates as
opaque and only needs an ordered `candidates()` proposer, so it works on discrete/structured spaces.
`descent` is a second driver for the common case where the candidate is a vector of CONTINUOUS KNOBS
and each feature is (locally) MONOTONE in a few of them. Then you don't have to STEP -- you can:

  1. BISECT each feature's controlling knob(s) to its target in ~log2 evals (coordinate descent), and
  2. resolve the COUPLED residual with a joint GAUSS-NEWTON solve (numerical Jacobian -> weighted
     least-squares over all active knobs at once), which escapes the coordinate-descent plateau that
     a strict no-regression rule gets stuck in.

Both share the same value layer: features -> `compute_reward_vector` -> maximin/Pareto. `descent`
returns the best candidate + its feature dict; the caller scores it with its char_map as usual.

CONTRACT (all domain logic injected, same spirit as optimizer.run):
    knobs   : list of Knob (name, lo, hi, get, set, drives). `get(cand)->float`, `set(cand,v)`
              MUTATES the candidate. `drives` = {feature: +/-1} the *hint* of which features this knob
              moves and the sign. Hints are optional-quality: the numerical Jacobian measures the
              real slopes; wrong hints only cost a few evals, they don't bias the GN solve.
    measure : candidate -> dict[feature -> float]  (the expensive step; apply + evaluate).
    target  : dict[feature -> float]               (what to match; e.g. reference features).
    weights : dict[feature -> float]               (per-feature importance; default 1.0).

IMPORTANT (the hard-won caveat): a driver is only as good as its Jacobian. A HAND-SEEDED `drives`
map + a numerical Jacobian estimated from a few NOISY evals can converge confidently to the wrong
place -- worse than the simple DFS driver on a real engine. For production, LEARN the Jacobian from
logged (knob-edit -> feature-delta) samples and pass it in, rather than relying on hand hints.

Standalone example: python autoreward/descent.py
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Knob:
    name: str
    lo: float
    hi: float
    get: Callable[[Any], float]
    set: Callable[[Any, float], None]
    drives: dict = field(default_factory=dict)   # {feature: +1/-1} hint

    def read(self, cand) -> float:
        try:
            return float(self.get(cand))
        except Exception:
            return (self.lo + self.hi) / 2.0

    def read_norm(self, cand) -> float:
        return _clamp((self.read(cand) - self.lo) / (self.hi - self.lo)) if self.hi != self.lo else 0.0

    def set_norm(self, cand, xn):
        self.set(cand, self.lo + _clamp(xn) * (self.hi - self.lo))


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def total_error(cur, target, weights):
    return round(sum(weights.get(f, 1.0) * abs(cur.get(f, 0.0) - target[f]) for f in target), 6)


def _knobs_for_feature(feature, knobs):
    """Knobs driving `feature`, most-SELECTIVE first (fewest other features perturbed)."""
    return sorted((k for k in knobs if feature in k.drives), key=lambda k: len(k.drives))


def bisect_search(candidate, knobs, measure, target, *, weights=None, budget=40, sweeps=5,
                  bisect_steps=4, tol=0.03, record=None):
    """Coordinate-descent multi-knob line search. Each sweep ranks unmet features by weighted error
    and, for each, moves ALL its knobs together toward the end that raises it, bisecting the
    interpolation fraction to hit the target with minimal movement. Returns (best, best_feats, evals,
    trace)."""
    weights = weights or {}
    feats = list(target)
    cand = copy.deepcopy(candidate)
    cur = measure(cand)
    evals = 1
    best, best_feats = copy.deepcopy(cand), dict(cur)
    trace = [{"phase": "baseline", "err": total_error(cur, target, weights)}]
    for sweep in range(sweeps):
        if evals >= budget:
            break
        ranked = sorted(feats, key=lambda f: -abs(cur.get(f, 0.0) - target[f]) * weights.get(f, 1.0))
        for f in ranked:
            if evals >= budget:
                break
            if abs(cur.get(f, 0.0) - target[f]) < tol:
                continue
            cands = _knobs_for_feature(f, knobs)
            if not cands:
                continue
            base = {k.name: k.read(cand) for k in cands}
            ends = {k.name: (k.hi if k.drives[f] > 0 else k.lo) for k in cands}
            lo_t, hi_t = 0.0, 1.0
            for _ in range(bisect_steps):
                if evals >= budget:
                    break
                t = (lo_t + hi_t) / 2.0
                for k in cands:
                    k.set(cand, base[k.name] + t * (ends[k.name] - base[k.name]))
                cur = measure(cand)
                evals += 1
                if total_error(cur, target, weights) < total_error(best_feats, target, weights):
                    best, best_feats = copy.deepcopy(cand), dict(cur)
                if cur.get(f, 0.0) < target[f]:
                    lo_t = t
                else:
                    hi_t = t
                if abs(cur.get(f, 0.0) - target[f]) < tol:
                    break
            if record:
                record({"sweep": sweep, "feature": f, "value": cur.get(f, 0.0), "evals": evals})
        trace.append({"phase": f"sweep{sweep}", "err": total_error(best_feats, target, weights), "evals": evals})
    return best, best_feats, evals, trace


def _deficient_knobs(cur, target, weights, knobs, k_features):
    worst = sorted(target, key=lambda f: -weights.get(f, 1.0) * abs(cur.get(f, 0.0) - target[f]))[:k_features]
    names = []
    for f in worst:
        for k in knobs:
            if f in k.drives and k.name not in names:
                names.append(k.name)
    return [k for k in knobs if k.name in names]


def gauss_newton(candidate, knobs, measure, target, *, weights=None, budget=90, iters=4,
                 damping=0.6, jacobian_features=6, jacobian=None):
    """Joint solve that breaks the coupled plateau. Each iteration builds the Jacobian d(feature)/
    d(knob) -- either the supplied LEARNED `jacobian` (dict {(feature,knob): slope}, no extra evals)
    or estimated NUMERICALLY over the DEFICIENT knobs (top `jacobian_features` worst features) -- and
    solves the weighted least-squares J*dx = (target-current), damped + clamped, keep-best. Restricting
    to deficient knobs cuts a numerical iteration from O(all knobs) to ~5 renders. Returns
    (best, best_feats, evals)."""
    try:
        import numpy as np
    except Exception:
        return candidate, measure(candidate), 0
    weights = weights or {}
    feats = list(target)
    cand = copy.deepcopy(candidate)
    cur = measure(cand)
    evals = 1
    best, best_err, best_feats = copy.deepcopy(cand), total_error(cur, target, weights), dict(cur)
    W = np.diag([weights.get(f, 1.0) for f in feats])
    for _ in range(iters):
        active = _deficient_knobs(cur, target, weights, knobs, jacobian_features)
        if not active:
            break
        x0 = [k.read_norm(cand) for k in active]
        r = np.array([target[f] - cur.get(f, 0.0) for f in feats])
        J = np.zeros((len(feats), len(active)))
        if jacobian:                                    # LEARNED Jacobian -- no perturbation evals
            for j, k in enumerate(active):
                for i, f in enumerate(feats):
                    J[i, j] = float(jacobian.get((f, k.name), 0.0))
        else:                                           # numerical Jacobian over the deficient knobs
            if evals + len(active) + 1 > budget:
                break
            for j, k in enumerate(active):
                k.set_norm(cand, x0[j] + 0.06)
                cp = measure(cand)
                evals += 1
                for i, f in enumerate(feats):
                    J[i, j] = (cp.get(f, 0.0) - cur.get(f, 0.0)) / 0.06
                k.set_norm(cand, x0[j])
        try:
            dx, *_ = np.linalg.lstsq(W @ J, W @ r, rcond=None)
        except Exception:
            break
        for j, k in enumerate(active):
            k.set_norm(cand, x0[j] + damping * float(dx[j]))
        cur = measure(cand)
        evals += 1
        e = total_error(cur, target, weights)
        if e < best_err:
            best_err, best, best_feats = e, copy.deepcopy(cand), dict(cur)
        else:
            cand = copy.deepcopy(best)
            cur = measure(cand)
            evals += 1
            damping *= 0.5
    return best, best_feats, evals


def descent(candidate, knobs, measure, target, *, weights=None, bisect_budget=40, gn_budget=90,
            jacobian_features=6, jacobian=None, record=None):
    """Full driver: bisection (coordinate descent) THEN a joint Gauss-Newton polish for the coupled
    residual. Returns (best_candidate, best_features, total_evals, trace)."""
    b, bf, e1, tr = bisect_search(candidate, knobs, measure, target, weights=weights,
                                  budget=bisect_budget, record=record)
    g, gf, e2 = gauss_newton(b, knobs, measure, target, weights=weights, budget=gn_budget + e1,
                             jacobian_features=jacobian_features, jacobian=jacobian)
    return g, gf, e1 + e2, tr


if __name__ == "__main__":
    # Toy 3-knob / 3-feature coupled problem (feature C = mean of A,B -> needs both together).
    TARGET = {"a": 0.7, "b": 0.6, "c": 0.65}

    def _measure(cand):
        return {"a": cand["x"], "b": cand["y"], "c": 0.5 * cand["x"] + 0.5 * cand["y"]}

    KN = [Knob("x", 0, 1, lambda c: c["x"], lambda c, v: c.__setitem__("x", v), {"a": +1, "c": +1}),
          Knob("y", 0, 1, lambda c: c["y"], lambda c, v: c.__setitem__("y", v), {"b": +1, "c": +1})]
    best, feats, evals, _ = descent({"x": 0.1, "y": 0.1}, KN, _measure, TARGET)
    print(f"done in {evals} evals -> {best}  feats={feats}  err={total_error(feats, TARGET, {})}")
