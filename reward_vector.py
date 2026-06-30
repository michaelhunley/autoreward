# (C) Copyright 2026 michaelhunley/autoreward contributors. MIT licensed.
"""
Per-characteristic reward vectors for multi-objective optimization.

A RewardVector holds one score in [0, 1] per named characteristic. Higher = better match.
compute_reward_vector() derives it from feature dicts using a caller-supplied char_map.

Typical usage:
    from reward_vector import RewardVector, compute_reward_vector

    char_map = {
        "key_direction": {
            "features": ["key_side"],
            "weights":  {"key_side": 1.0},
            "scale":    0.5,          # expected max weighted distance (calibrate per char)
        },
        "fill": {
            "features": ["subject_exposure"],
            "weights":  {"subject_exposure": 1.0},
            "scale":    0.4,
        },
    }
    rv = compute_reward_vector(current_features, target_features, char_map)
    worst_char, worst_score = rv.worst()
    scalar = rv.scalar("min")   # for autoresearch bridge

The char_map is domain-specific and lives in the consuming project.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RewardVector:
    """Per-characteristic reward scores in [0, 1]. Higher = better."""

    scores: dict[str, float]

    def worst(self) -> tuple[str, float]:
        """Return (characteristic_name, score) for the most-deficient characteristic."""
        return min(self.scores.items(), key=lambda kv: kv[1])

    def best(self) -> tuple[str, float]:
        return max(self.scores.items(), key=lambda kv: kv[1])

    def min_score(self) -> float:
        return min(self.scores.values()) if self.scores else 0.0

    def mean_score(self) -> float:
        return sum(self.scores.values()) / len(self.scores) if self.scores else 0.0

    def soft_min(self, k: float = 5.0) -> float:
        """Smoothed maximin: differentiable approximation of min(). k controls sharpness."""
        import math
        vals = list(self.scores.values())
        if not vals:
            return 0.0
        return -math.log(sum(math.exp(-k * v) for v in vals)) / k

    def scalar(self, method: str = "min") -> float:
        """
        Collapse to a scalar for logging or autoresearch bridge.

        method:
          "min"      -- maximin criterion (use as the search's primary signal)
          "mean"     -- unweighted mean (use for reporting / tracking)
          "soft_min" -- smooth approximation of min() (k=5)
        """
        if method == "min":
            return self.min_score()
        if method == "mean":
            return self.mean_score()
        if method == "soft_min":
            return self.soft_min()
        raise ValueError(f"unknown method {method!r}; use 'min', 'mean', or 'soft_min'")

    def is_pareto_improvement(self, baseline: "RewardVector",
                               regression_tol: float = 0.02) -> bool:
        """
        True if self raises >= 1 characteristic and regresses none beyond regression_tol.

        regression_tol gives a grace band so tiny numerical noise doesn't block acceptance.
        """
        shared = set(self.scores) & set(baseline.scores)
        if not shared:
            return False
        any_improved = any(self.scores[k] > baseline.scores[k] for k in shared)
        none_regressed = all(self.scores[k] >= baseline.scores[k] - regression_tol
                             for k in shared)
        return any_improved and none_regressed

    def dominates(self, other: "RewardVector", tol: float = 0.0) -> bool:
        """
        True if self Pareto-dominates other: >= on all shared characteristics,
        strictly > on at least one.
        """
        shared = set(self.scores) & set(other.scores)
        if not shared:
            return False
        geq_all = all(self.scores[k] >= other.scores[k] - tol for k in shared)
        gt_one  = any(self.scores[k] >  other.scores[k] + tol for k in shared)
        return geq_all and gt_one

    def __repr__(self) -> str:
        parts = ", ".join(f"{k}={v:.3f}" for k, v in self.scores.items())
        return f"RewardVector({parts})"


def compute_reward_vector(
    current: dict[str, float],
    target: dict[str, float],
    char_map: dict[str, dict],
) -> RewardVector:
    """
    Derive a RewardVector from current/target feature dicts and a characteristic map.

    char_map structure:
        {
            "<char_name>": {
                "features": ["feat_a", "feat_b"],   # which features score this characteristic
                "weights":  {"feat_a": 1.0, "feat_b": 0.5},  # optional; defaults 1.0
                "scale":    <float>,   # expected max weighted-mean distance (calibrate per char)
            },
        }

    r_c = clamp(1 - dist_c / scale_c, 0, 1)
    dist_c = weighted mean of |current[f] - target[f]| over that characteristic's features.

    Features absent from either current or target are silently skipped; if ALL features
    for a characteristic are missing the score is 0.0 (maximally deficient).
    """
    scores: dict[str, float] = {}
    for char, cfg in char_map.items():
        feats   = cfg.get("features", [])
        weights = cfg.get("weights", {})
        scale   = float(cfg.get("scale", 1.0))

        total_w = 0.0
        dist    = 0.0
        for f in feats:
            if f not in current or f not in target:
                continue
            w     = float(weights.get(f, 1.0))
            dist += w * abs(current[f] - target[f])
            total_w += w

        if total_w > 0.0:
            dist /= total_w
            scores[char] = float(max(0.0, min(1.0, 1.0 - dist / (scale + 1e-12))))
        else:
            scores[char] = 0.0

    return RewardVector(scores=scores)
