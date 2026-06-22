#!/usr/bin/env python3
# autoreward <-> autoresearch bridge.
#
# An autonomous loop (karpathy/autoresearch and the like) MAXIMIZES a scalar
# metric. In objective domains that's given (val_bpb). autoreward lets you make
# that scalar a GAUGE - a tier-C distance to a target, or a tier-B proxy - so the
# loop can run in subjective domains. This is the thin adapter: register a gauge,
# get back a reward the loop maximizes.
#
# Contract: a gauge is callable(candidate, target=None) -> float. By default LOWER
# is better (a distance); pass higher_is_better=True for a preference/quality score.

GAUGES = {}  # name -> (fn, higher_is_better)


def register(name, fn, higher_is_better=False):
    """Register a gauge. fn(candidate, target=None) -> float."""
    GAUGES[name] = (fn, higher_is_better)
    return fn


def reward(name, candidate, target=None):
    """Scalar the loop MAXIMIZES. Distances are negated; scores pass through."""
    fn, hib = GAUGES[name]
    v = float(fn(candidate, target) if target is not None else fn(candidate))
    return v if hib else -v


def best_of(name, candidates, target=None):
    """Pick the candidate with the highest reward (the loop's select step)."""
    return max(candidates, key=lambda c: reward(name, c, target))


# --- example: wire a tier-C structure gauge as a reward (numpy only) ----------
if __name__ == "__main__":
    import numpy as np

    def structure_distance(cand, tgt):           # tier-C: distance to target, lower=better
        et = np.mean(np.hypot(*np.gradient(tgt)))
        return abs(np.mean(np.hypot(*np.gradient(cand))) - et)

    register("structure", structure_distance)    # higher_is_better=False (a distance)
    rng = np.random.default_rng(0)
    target = rng.random((64, 64))
    blurry = np.full_like(target, target.mean())
    faithful = target + 0.01 * rng.standard_normal(target.shape)
    print("reward(blurry)  =", round(reward("structure", blurry, target), 4))
    print("reward(faithful)=", round(reward("structure", faithful, target), 4), "(higher = loop keeps this)")
    print("loop picks:", "faithful" if best_of("structure", [blurry, faithful], target) is faithful else "blurry")
    print()
    print("In a real loop: each round your generator proposes candidates; score them")
    print("with reward(<gauge>, cand, target); keep the max; iterate. Swap 'structure'")
    print("for an LPIPS/identity/reward-model gauge from models/index.json. Spot-check")
    print("with humans (tier A) periodically to recalibrate a tier-B proxy.")
