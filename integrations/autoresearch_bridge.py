#!/usr/bin/env python3
# autoreward <-> autoresearch bridge.
#
# An autonomous loop (karpathy/autoresearch and the like) MAXIMIZES a scalar
# metric. In objective domains that's given (val_bpb). autoreward lets you make
# that scalar a GAUGE - a Measured distance to a target, or a Predicted proxy - so the
# loop can run in subjective domains. This is the thin adapter: register a gauge,
# get back a reward the loop maximizes.
#
# Contract: a gauge is callable(candidate, target=None) -> float. By default LOWER
# is better (a distance); pass higher_is_better=True for a preference/quality score.
#
# CONVENTION / RANGE: reward() and loss() are UNBOUNDED and in the gauge's NATIVE
# units (a cosine is -1..1, a negated distance is <=0, PSNR is 0..50+). Only the
# ORDERING / direction is guaranteed - and that is all a keep-the-best loop (and
# autoresearch) needs. Do NOT assume reward is in 0..1. If your use case is
# gradient-RL that needs a bounded [0,1] reward, wrap it with normalize().

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


def loss(name, candidate, target=None):
    """Scalar a MINIMIZING loop (e.g. autoresearch, whose val_bpb is lower=better)
    reads. This is just -reward; REPORT THIS as your run's headline metric so the
    loop's 'lower is better' convention optimizes your gauge the right direction."""
    return -reward(name, candidate, target)


def normalize(name, candidate, lo, hi, target=None):
    """Map reward() into [0,1] (lo->0, hi->1, clamped) for gradient-RL that needs a
    BOUNDED reward. lo/hi are the worst/best reward you expect in reward units
    (remember reward = score, or -distance). ONLY needed for policy-gradient-style
    training - keep/discard loops and autoresearch do NOT need this (ordering is
    enough), so reach for it only when reward magnitude/scale actually matters."""
    r = reward(name, candidate, target)
    return max(0.0, min(1.0, (r - lo) / (hi - lo + 1e-12)))


def best_of(name, candidates, target=None):
    """Pick the candidate with the highest reward (the loop's select step)."""
    return max(candidates, key=lambda c: reward(name, c, target))


# --- example: wire a Measured structure gauge as a reward (numpy only) ----------
if __name__ == "__main__":
    import numpy as np

    def structure_distance(cand, tgt):           # Measured: distance to target, lower=better
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
    print("loss(faithful) =", round(loss("structure", faithful, target), 4), "(lower=better; autoresearch reads this)")
    print("normalize(faithful, lo=-0.3, hi=0.0) =",
          round(normalize("structure", faithful, -0.3, 0.0, target), 3), "(0..1 for gradient-RL)")
    print()
    print("In a real loop: each round your generator proposes candidates; score them")
    print("with reward(<gauge>, cand, target); keep the max; iterate. Swap 'structure'")
    print("for an LPIPS/identity/reward-model gauge from models/index.json. Spot-check")
    print("with humans (Reviewed tier) periodically to recalibrate a Predicted proxy.")
