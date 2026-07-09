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
    interpolation fraction to hit the target with minimal movement.

    Returns (best, best_feats, evals, trace, status) where `status` maps each searched feature to why
    ITS OWN bisection stopped: "converged" (hit tol), "steps_exhausted" (bisect_steps ran out first),
    "budget_exhausted" (the shared eval budget ran out first), or "skipped_no_knobs" (no knob drives
    it). To freeze a knob, filter it out of `knobs` before calling (no `skip` param needed)."""
    weights = weights or {}
    feats = list(target)
    cand = copy.deepcopy(candidate)
    cur = measure(cand)
    evals = 1
    best, best_feats = copy.deepcopy(cand), dict(cur)
    trace = [{"phase": "baseline", "err": total_error(cur, target, weights)}]
    status: dict = {}
    budget_hit = False
    for sweep in range(sweeps):
        if evals >= budget:
            budget_hit = True
            break
        ranked = sorted(feats, key=lambda f: -abs(cur.get(f, 0.0) - target[f]) * weights.get(f, 1.0))
        for f in ranked:
            if evals >= budget:
                budget_hit = True
                break
            if abs(cur.get(f, 0.0) - target[f]) < tol:
                status[f] = "converged"
                continue
            cands = _knobs_for_feature(f, knobs)
            if not cands:
                status.setdefault(f, "skipped_no_knobs")
                continue
            base = {k.name: k.read(cand) for k in cands}
            ends = {k.name: (k.hi if k.drives[f] > 0 else k.lo) for k in cands}
            lo_t, hi_t = 0.0, 1.0
            for _ in range(bisect_steps):
                if evals >= budget:
                    budget_hit = True
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
                    status[f] = "converged"
                    break
            else:
                status[f] = "budget_exhausted" if budget_hit else "steps_exhausted"
            if record:
                record({"sweep": sweep, "feature": f, "value": cur.get(f, 0.0), "evals": evals})
        trace.append({"phase": f"sweep{sweep}", "err": total_error(best_feats, target, weights), "evals": evals})
    for f in feats:
        status.setdefault(f, "budget_exhausted" if budget_hit else "steps_exhausted")
    return best, best_feats, evals, trace, status


def _deficient_knobs(cur, target, weights, knobs, k_features):
    worst = sorted(target, key=lambda f: -weights.get(f, 1.0) * abs(cur.get(f, 0.0) - target[f]))[:k_features]
    names = []
    for f in worst:
        for k in knobs:
            if f in k.drives and k.name not in names:
                names.append(k.name)
    return [k for k in knobs if k.name in names]


def gauss_newton(candidate, knobs, measure, target, *, weights=None, budget=90, iters=4,
                 damping=0.6, jacobian_features=6, jacobian=None, tol=0.03):
    """Joint solve that breaks the coupled plateau. Each iteration builds the Jacobian d(feature)/
    d(knob) -- either the supplied LEARNED `jacobian` (dict {(feature,knob): slope}, no extra evals)
    or estimated NUMERICALLY over the DEFICIENT knobs (top `jacobian_features` worst features) -- and
    solves the weighted least-squares J*dx = (target-current), damped + clamped, keep-best. Restricting
    to deficient knobs cuts a numerical iteration from O(all knobs) to ~5 renders.

    Returns (best, best_feats, evals, status) where status = {"per_feature": {feature: "converged"|
    "unconverged" at tol}, "exit_reason": "converged"|"iters_exhausted"|"budget_exhausted"|
    "damping_collapsed"|"no_active_knobs"|"solve_failed"|"no_numpy"}."""
    weights = weights or {}
    feats = list(target)
    try:
        import numpy as np
    except Exception:
        cur0 = measure(candidate)
        pf = {f: ("converged" if abs(cur0.get(f, 0.0) - target[f]) < tol else "unconverged") for f in feats}
        return candidate, dict(cur0), 1, {"per_feature": pf, "exit_reason": "no_numpy"}
    cand = copy.deepcopy(candidate)
    cur = measure(cand)
    evals = 1
    best, best_err, best_feats = copy.deepcopy(cand), total_error(cur, target, weights), dict(cur)
    W = np.diag([weights.get(f, 1.0) for f in feats])
    exit_reason = "iters_exhausted"
    stalled = 0
    for _ in range(iters):
        active = ([k for k in knobs if k.drives] if jacobian
                  else _deficient_knobs(cur, target, weights, knobs, jacobian_features))
        if not active:
            exit_reason = "no_active_knobs"
            break
        if evals + 1 > budget:
            exit_reason = "budget_exhausted"
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
                exit_reason = "budget_exhausted"
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
            exit_reason = "solve_failed"
            break
        for j, k in enumerate(active):
            k.set_norm(cand, x0[j] + damping * float(dx[j]))
        cur = measure(cand)
        evals += 1
        e = total_error(cur, target, weights)
        if e < best_err:
            best_err, best, best_feats = e, copy.deepcopy(cand), dict(cur)
            stalled = 0
        else:
            cand = copy.deepcopy(best)
            cur = measure(cand)
            evals += 1
            damping *= 0.5
            stalled += 1
            if stalled >= 2:
                exit_reason = "damping_collapsed"
                break
    per_feature = {f: ("converged" if abs(best_feats.get(f, 0.0) - target[f]) < tol else "unconverged")
                   for f in feats}
    if all(v == "converged" for v in per_feature.values()):
        exit_reason = "converged"
    return best, best_feats, evals, {"per_feature": per_feature, "exit_reason": exit_reason}


def check_stationarity(candidate, cur, knobs, measure, target, bisect_status, gn_status, *,
                       weights=None, mode="probe", budget=6, probe_frac=0.06, tol=0.03):
    """Post-hoc check for features that did NOT confirm convergence in bisect_search/gauss_newton:
    genuinely stationary (no knob move helps), or just under-searched. `cur` is the already-measured
    feature dict at `candidate` -- reused, not re-measured, to avoid a redundant eval.

    mode="trace" is FREE (zero measure() calls): relabels every not-yet-converged feature as
    "still_improvable" purely from the bookkeeping in bisect_status/gn_status.
    mode="probe" (default) spends up to `budget` measure() calls, ONE per unconverged feature (its
    single most-selective driving knob), nudging by `probe_frac` toward the direction its `drives`
    sign says should help, and checking whether total weighted error improves. Ranked worst-first.

    Returns {"stationary": [...], "still_improvable": [...], "not_probed": [...], "evals_used": int,
    "mode": str}."""
    weights = weights or {}
    feats = list(target)
    gn_pf = (gn_status or {}).get("per_feature", {})
    unconverged = [f for f in feats if bisect_status.get(f) != "converged"
                   and gn_pf.get(f, "converged") != "converged"]
    if mode == "trace":
        return {"stationary": [], "still_improvable": list(unconverged), "not_probed": [],
                "evals_used": 0, "mode": "trace"}
    ranked = sorted(unconverged, key=lambda f: -weights.get(f, 1.0) * abs(cur.get(f, 0.0) - target[f]))
    base_err = total_error(cur, target, weights)
    stationary, still_improvable, not_probed = [], [], []
    evals_used = 0
    for f in ranked:
        if evals_used >= budget:
            not_probed.append(f); continue
        cands = _knobs_for_feature(f, knobs)
        if not cands:
            not_probed.append(f); continue
        k = cands[0]                      # most-selective driving knob
        x0 = k.read_norm(candidate)
        sign = 1.0 if k.drives[f] > 0 else -1.0
        probe = copy.deepcopy(candidate)
        k.set_norm(probe, x0 + sign * probe_frac)
        probe_err = total_error(measure(probe), target, weights)
        evals_used += 1
        (still_improvable if base_err - probe_err > tol else stationary).append(f)
    return {"stationary": stationary, "still_improvable": still_improvable,
            "not_probed": not_probed, "evals_used": evals_used, "mode": mode}


def learn_jacobian(candidate, knobs, measure, target, *, eps=0.06):
    """Measure the REAL Jacobian d(feature)/d(knob) around a known-good candidate: perturb each knob
    by `eps` (normalized), measure, record the feature slopes. Returns ({(feature, knob_name): slope},
    base_features, evals_used). Pass the result to gauss_newton(jacobian=...) so GN needs NO per-run
    perturbation evals and uses true engine slopes instead of hand-hint `drives`."""
    feats = list(target)
    jac = {}
    base = measure(candidate)
    used = 1
    for k in knobs:
        s = copy.deepcopy(candidate)
        x0 = k.read_norm(s)
        k.set_norm(s, x0 + eps)
        f = measure(s)
        used += 1
        for feat in feats:
            jac[(feat, k.name)] = (f.get(feat, 0.0) - base.get(feat, 0.0)) / eps
    return jac, base, used


def descent(candidate, knobs, measure, target, *, weights=None, bisect_budget=40, gn_budget=90,
            jacobian_features=6, jacobian=None, record=None, stationarity_mode="trace",
            stationarity_budget=6):
    """Full driver: bisection (coordinate descent) THEN a joint Gauss-Newton polish for the coupled
    residual, THEN a stationarity check for whatever did not converge.

    Returns (best_candidate, best_features, total_evals, trace, status) where status =
    {"bisect": {feature: reason}, "gn": {"per_feature":..., "exit_reason":...},
     "stationarity": {"stationary":..., "still_improvable":..., "not_probed":...}}."""
    b, bf, e1, tr, bisect_status = bisect_search(candidate, knobs, measure, target, weights=weights,
                                                 budget=bisect_budget, record=record)
    g, gf, e2, gn_status = gauss_newton(b, knobs, measure, target, weights=weights,
                                        budget=gn_budget + e1, jacobian_features=jacobian_features,
                                        jacobian=jacobian)
    stat = check_stationarity(g, gf, knobs, measure, target, bisect_status, gn_status,
                              weights=weights, mode=stationarity_mode, budget=stationarity_budget)
    status = {"bisect": bisect_status, "gn": gn_status, "stationarity": stat}
    return g, gf, e1 + e2 + stat.get("evals_used", 0), tr, status


if __name__ == "__main__":
    # Toy 3-knob / 3-feature coupled problem (feature C = mean of A,B -> needs both together).
    TARGET = {"a": 0.7, "b": 0.6, "c": 0.65}

    def _measure(cand):
        return {"a": cand["x"], "b": cand["y"], "c": 0.5 * cand["x"] + 0.5 * cand["y"]}

    KN = [Knob("x", 0, 1, lambda c: c["x"], lambda c, v: c.__setitem__("x", v), {"a": +1, "c": +1}),
          Knob("y", 0, 1, lambda c: c["y"], lambda c, v: c.__setitem__("y", v), {"b": +1, "c": +1})]
    best, feats, evals, _, status = descent({"x": 0.1, "y": 0.1}, KN, _measure, TARGET)
    print(f"done in {evals} evals -> {best}  feats={feats}  err={total_error(feats, TARGET, {})}")
    print(f"status: bisect={status['bisect']}  gn_exit={status['gn']['exit_reason']}")
