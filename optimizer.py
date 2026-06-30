# (C) Copyright 2026 michaelhunley/autoreward contributors. MIT licensed.
"""
Generic multi-objective optimizer: DFS backtracking + Pareto front + maximin accept rule.

All multi-objective bookkeeping lives here. Callers inject domain logic through hooks:

    measure(candidate) -> RewardVector
        Evaluate a candidate. The expensive step. Called once per trial.

    candidates(candidate, rv, deficient_char) -> list[Action]
        Given the current candidate and its RewardVector, return an ORDERED list of
        actions to try. `deficient_char` is the worst-scoring characteristic so the
        caller can prioritize actions that move it. Action is any value; the optimizer
        passes it opaquely back to apply().

    apply(candidate, action) -> new_candidate
        Return a NEW candidate with the action applied. Must NOT mutate the input.

    constraint(candidate, rv) -> bool                 [optional]
        Return True to REJECT this candidate before the accept rule runs (hard
        constraint violated). A rejected trial is still passed to on_trial.

    on_trial(event: dict)                             [optional]
        Telemetry hook. Fired after every trial, accepted or not. Keys:
          "kind"                "baseline" | "trial"
          "depth"               DFS depth of the parent node
          "action"              the action applied (None for baseline)
          "rv_before"           parent's scores dict
          "rv_after"            this trial's scores dict
          "accepted"            bool
          "constraint_rejected" bool

The optimizer is candidate-type-agnostic: the candidate, action, and their semantics
are entirely the caller's concern.

Standalone example:
    python autoreward/optimizer.py
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

try:
    from reward_vector import RewardVector
except ImportError:
    from autoreward.reward_vector import RewardVector


# ── Pareto front ──────────────────────────────────────────────────────────────

@dataclass
class Node:
    """A point in the search space with its evaluated RewardVector."""
    candidate: Any
    rv: RewardVector
    depth: int = 0


def pareto_front(nodes: list[Node], tol: float = 0.0) -> list[Node]:
    """Return the non-dominated subset of nodes (full Pareto front)."""
    front: list[Node] = []
    for node in nodes:
        if not any(other.rv.dominates(node.rv, tol) for other in nodes if other is not node):
            front.append(node)
    return front


def _update_front(front: list[Node], node: Node, tol: float) -> list[Node]:
    """Add node to front, dropping any node it dominates. Returns updated front."""
    surviving = [n for n in front if not node.rv.dominates(n.rv, tol)]
    if not any(n.rv.dominates(node.rv, tol) for n in surviving):
        surviving.append(node)
    return surviving


def best_by_maximin(front: list[Node]) -> Node:
    """Pick the node with the highest min-score (maximin / Chebyshev criterion)."""
    return max(front, key=lambda n: n.rv.min_score())


def best_by_mean(front: list[Node]) -> Node:
    """Pick the node with the highest mean score (average-maximizer criterion)."""
    return max(front, key=lambda n: n.rv.mean_score())


# ── DFS optimizer ─────────────────────────────────────────────────────────────

def run(
    initial_candidate: Any,
    measure: Callable[[Any], RewardVector],
    candidates: Callable[[Any, RewardVector, str], list],
    apply: Callable[[Any, Any], Any],
    *,
    constraint: Optional[Callable[[Any, RewardVector], bool]] = None,
    on_trial: Optional[Callable[[dict], None]] = None,
    max_evals: int = 20,
    max_children: int = 4,
    regression_tol: float = 0.02,
    pareto_tol: float = 0.0,
    stop_when: Optional[Callable[[list[Node]], bool]] = None,
) -> tuple[list[Node], int]:
    """
    Backtracking DFS with Pareto-front maintenance and maximin accept rule.

    Returns (pareto_front, eval_count).

    The Pareto front is the set of non-dominated nodes found during the search.
    Use best_by_maximin(front) to pick the recommended result, or let a downstream
    judge pick from the front.

    Parameters
    ----------
    initial_candidate   Starting point (any type; opaque to the optimizer).
    measure             (candidate) -> RewardVector.  Called max_evals times total.
    candidates          (candidate, rv, deficient_char) -> list[Action].
                        deficient_char is rv.worst()[0].  Return ordered list; the
                        optimizer tries them left-to-right.
    apply               (candidate, action) -> new_candidate.  Must not mutate input.
    constraint          (candidate, rv) -> bool  (True = REJECT).  Optional.
    on_trial            Telemetry hook.  Optional.
    max_evals           Hard cap on measure() calls (including the baseline).
    max_children        Max actions taken from candidates() per node per visit.
    regression_tol      A score may drop this much and still count as a Pareto
                        improvement (grace band for measurement noise).
    pareto_tol          Dominance tolerance for front deduplication.
    stop_when           (pareto_front) -> bool: return True to exit early.  Optional.
    """
    root_rv = measure(initial_candidate)
    root    = Node(candidate=initial_candidate, rv=root_rv, depth=0)

    if on_trial:
        on_trial({"kind": "baseline", "depth": 0, "action": None,
                  "rv_before": {}, "rv_after": root_rv.scores.copy(),
                  "accepted": True, "constraint_rejected": False})

    front:  list[Node]           = [root]
    evals:  int                  = 1
    # stack entries: [node, untried_actions | None]
    # None means "not yet generated" — we generate lazily on first pop
    stack: list[list]            = [[root, None]]

    while stack and evals < max_evals:
        if stop_when and stop_when(front):
            break

        frame = stack[-1]
        node: Node = frame[0]

        # Generate candidates lazily on first visit to this node
        if frame[1] is None:
            deficient_char, _ = node.rv.worst()
            raw   = candidates(node.candidate, node.rv, deficient_char)
            frame[1] = list(raw[:max_children])

        untried: list = frame[1]

        if not untried:
            stack.pop()   # exhausted → backtrack
            continue

        action        = untried.pop(0)
        new_candidate = apply(node.candidate, action)
        new_rv        = measure(new_candidate)
        evals        += 1

        constraint_rejected = bool(constraint and constraint(new_candidate, new_rv))
        accepted = (
            not constraint_rejected
            and new_rv.is_pareto_improvement(node.rv, regression_tol)
        )

        if on_trial:
            on_trial({
                "kind": "trial",
                "depth": node.depth,
                "action": action,
                "rv_before": node.rv.scores.copy(),
                "rv_after":  new_rv.scores.copy(),
                "accepted":  accepted,
                "constraint_rejected": constraint_rejected,
            })

        if accepted:
            child = Node(candidate=new_candidate, rv=new_rv, depth=node.depth + 1)
            front = _update_front(front, child, pareto_tol)
            stack.append([child, None])   # descend

    return front, evals


# ── Standalone example ────────────────────────────────────────────────────────

if __name__ == "__main__":
    """Toy lighting problem: find knob values that match a target on 3 characteristics."""

    TARGET   = {"brightness": 0.7, "warmth": 0.6, "contrast": 0.8}
    CHAR_MAP = {"bright": "brightness", "warm": "warmth", "crisp": "contrast"}

    def _measure(cand: dict) -> RewardVector:
        scores = {
            char: max(0.0, min(1.0, 1.0 - abs(cand[feat] - TARGET[feat]) / 0.5))
            for char, feat in CHAR_MAP.items()
        }
        return RewardVector(scores=scores)

    def _candidates(cand: dict, rv: RewardVector, deficient_char: str) -> list:
        feat = CHAR_MAP[deficient_char]
        gap  = TARGET[feat] - cand[feat]
        step = 0.15 if gap > 0 else -0.15
        return [{"knob": feat, "delta": step}, {"knob": feat, "delta": step * 0.5}]

    def _apply(cand: dict, action: dict) -> dict:
        c = dict(cand)
        c[action["knob"]] = round(c[action["knob"]] + action["delta"], 3)
        return c

    def _on_trial(e: dict) -> None:
        tag = "[baseline]" if e["kind"] == "baseline" else f"[depth={e['depth']}]"
        rv  = e["rv_after"]
        acc = e.get("accepted", True)
        print(f"  {tag} rv={rv}  accepted={acc}")

    initial = {"brightness": 0.3, "warmth": 0.3, "contrast": 0.3}
    print(f"Initial: {initial}")
    front, evals = run(initial, _measure, _candidates, _apply,
                       on_trial=_on_trial, max_evals=30)

    best = best_by_maximin(front)
    print(f"\nDone in {evals} evals. Pareto front: {len(front)} node(s).")
    print(f"Best (maximin): {best.candidate}")
    print(f"  min_score={best.rv.min_score():.3f}  scores={best.rv.scores}")
