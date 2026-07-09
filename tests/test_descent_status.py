# (C) Copyright 2026 michaelhunley/autoreward contributors. MIT licensed.
"""Tests for the exit-reason status bookkeeping ported from cinepipe-director's bsp_search."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from autoreward.descent import (Knob, bisect_search, gauss_newton, descent,  # noqa: E402
                                 check_stationarity, learn_jacobian)

TARGET = {"a": 0.7, "b": 0.6, "c": 0.65}


def _knobs():
    return [Knob("x", 0, 1, lambda c: c["x"], lambda c, v: c.__setitem__("x", v), {"a": +1, "c": +1}),
            Knob("y", 0, 1, lambda c: c["y"], lambda c, v: c.__setitem__("y", v), {"b": +1, "c": +1})]


def _measure(c):
    return {"a": c["x"], "b": c["y"], "c": 0.5 * c["x"] + 0.5 * c["y"]}


def test_bisect_returns_status_5_tuple():
    out = bisect_search({"x": 0.1, "y": 0.1}, _knobs(), _measure, TARGET, budget=40)
    assert len(out) == 5
    _, _, _, _, status = out
    assert set(status) == set(TARGET)
    assert all(v in ("converged", "steps_exhausted", "budget_exhausted", "skipped_no_knobs")
               for v in status.values())


def test_bisect_skipped_no_knobs():
    # a feature with no driving knob -> "skipped_no_knobs"
    tgt = dict(TARGET, d=0.5)
    _, _, _, _, status = bisect_search({"x": 0.1, "y": 0.1}, _knobs(), _measure, tgt, budget=40)
    assert status["d"] == "skipped_no_knobs"


def test_bisect_budget_exhausted():
    _, _, _, _, status = bisect_search({"x": 0.1, "y": 0.1}, _knobs(), _measure, TARGET, budget=2)
    assert any(v == "budget_exhausted" for v in status.values())


def test_gauss_newton_returns_status():
    out = gauss_newton({"x": 0.1, "y": 0.1}, _knobs(), _measure, TARGET)
    assert len(out) == 4
    _, _, _, status = out
    assert "per_feature" in status and "exit_reason" in status
    assert status["exit_reason"] in ("converged", "iters_exhausted", "budget_exhausted",
                                     "damping_collapsed", "no_active_knobs", "solve_failed", "no_numpy")


def test_descent_status_contract():
    _, feats, _, _, status = descent({"x": 0.1, "y": 0.1}, _knobs(), _measure, TARGET)
    assert set(status) == {"bisect", "gn", "stationarity"}
    assert abs(feats["c"] - TARGET["c"]) < 0.1                       # actually converges


def test_learn_jacobian_measures_slopes():
    jac, base, used = learn_jacobian({"x": 0.5, "y": 0.5}, _knobs(), _measure, TARGET)
    assert used == 1 + len(_knobs())
    assert abs(jac[("a", "x")] - 1.0) < 1e-6                         # a = x -> slope 1
    assert abs(jac[("c", "x")] - 0.5) < 1e-6                         # c = 0.5x+0.5y -> slope .5


def test_check_stationarity_trace_is_free():
    # a feature is unconverged only if BOTH bisect AND gn left it unconverged (matches director)
    st = check_stationarity({"x": 0.1}, {"a": 0.1}, _knobs(), _measure, TARGET,
                            {"a": "steps_exhausted"}, {"per_feature": {"a": "unconverged"}}, mode="trace")
    assert st["evals_used"] == 0 and "a" in st["still_improvable"]


if __name__ == "__main__":
    import traceback
    passed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); passed += 1; print(f"  PASS {name}")
            except Exception:
                print(f"  FAIL {name}"); traceback.print_exc()
    print(f"{passed} passed")
