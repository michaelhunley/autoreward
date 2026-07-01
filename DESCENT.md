# Descent driver — bisection + joint Gauss-Newton

`descent.py` is a **driver** for autoreward's multi-objective value layer, complementary to
`optimizer.run` (DFS + Pareto + maximin). Same value layer (`RewardVector`); different search.

## When to use which driver

| | `optimizer.run` (DFS) | `descent` (bisection + GN) |
|---|---|---|
| candidate | opaque; you supply `candidates()` proposer | a vector of **continuous knobs** |
| assumes | nothing | each feature is **locally monotone** in a few knobs |
| strength | discrete / structured spaces, no gradient | fast on continuous knobs; escapes coupled plateaus |
| cost | many small steps + Pareto rejections | ~log2 evals/feature + a few joint solves |

Both minimize distance to a target in reward-vector space. Use `descent` when your candidate is
lights/hyper-params/sliders and features respond monotonically; use `run` otherwise. An
auto-selecting meta-driver (try descent, fall back to DFS where monotonicity breaks) is the intended
end state.

## The algorithm

Most features are (locally) **monotone** in a small set of knobs — a warmer key raises "warmth", a
brighter fill raises "subject exposure". Monotone ⇒ you can **discard half a knob's range** when it
moves a feature the wrong way. Two phases:

**1. Bisection (coordinate descent).** Rank unmet features by weighted error. For each, move *all*
its controlling knobs together toward the end that raises it, and **bisect the interpolation
fraction** to hit the target with minimal movement (least collateral). ~log2 evals nails a feature;
sweeping re-corrects coupling. This is `bisect_search`.

**2. Joint Gauss-Newton.** Coordinate descent stalls in a **coupled** plateau (fixing feature A
breaks B). Escape it with a joint solve: build the Jacobian `∂feature/∂knob`, solve the weighted
least-squares `J·Δknob = (target − current)` over *all active knobs at once*, take a damped, clamped,
keep-best step. This is `gauss_newton`.

**Deficient-knob restriction (cost dial).** The numerical Jacobian is estimated by perturbing knobs
— O(#knobs) evals per iteration. `gauss_newton` restricts perturbation to the knobs driving the top
`jacobian_features` worst features, cutting an iteration from ~all-knobs to ~5 renders. `jacobian_features`
is the speed/detail dial: small = fast (highest-value params only), large = thorough.

## The Jacobian is the whole game — learn it, don't guess it

> New to Jacobians? Read the plain-language [JACOBIAN-EXPLAINED.md](JACOBIAN-EXPLAINED.md) first.

A driver is only as good as its Jacobian. Two ways to get it:

- **Numerical** (default): perturb each active knob, measure the feature deltas. Works with zero
  domain knowledge, but costs evals every iteration and is **noisy** on a real (stochastic/expensive)
  engine — a hand-seeded `drives` hint + noisy numerical estimate can converge *confidently to the
  wrong place*, sometimes worse than the simple DFS driver.
- **Learned** (recommended for production): pass a `jacobian` = `{(feature, knob): slope}` fitted from
  logged `knob-edit → feature-delta` samples across prior runs / ground-truth cases. Then GN needs
  **no perturbation evals** and uses the *true* engine slopes.

Toy validation (`python descent.py` + the learned path): full numerical bisect+GN solves a coupled
3-feature target in **~53 evals** (err 0.005); the **learned-Jacobian GN in ~11 evals** (err 0.0002)
— cheaper *and* more accurate. **This is why ground truth should train the Jacobian, not be a per-run
crutch:** learning the sensitivity table is what makes the fast driver work on a real engine.

## Contract (all domain logic injected)

```python
from autoreward.descent import Knob, descent   # or bisect_search / gauss_newton

knobs = [Knob(name, lo, hi, get, set, drives), ...]   # get(cand)->float; set(cand,v) MUTATES
                                                      # drives = {feature: +1/-1}  (a HINT)
best, feats, evals, trace = descent(
    candidate, knobs, measure, target,               # measure(cand)->{feature:val}; target={feature:val}
    weights={feature: importance, ...},              # per-feature priority (default 1.0)
    jacobian=learned_slopes_or_None,                 # {(feature,knob): slope}; None = numerical
    jacobian_features=6,                             # cost/detail dial for the numerical Jacobian
)
```

`descent` returns the best candidate + its feature dict; score it with your `char_map` via
`compute_reward_vector` exactly as with the DFS driver.
