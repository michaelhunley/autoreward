# autoreward

**The reward layer for autonomous (RLAIF) loops.** Agentic loops that improve a
system — generate, score, keep the best, repeat — only work if the *score* is
trustworthy. In objective domains that score is given (compile, tests, `val_bpb`).
In **subjective / qualitative** domains (does this render match? is it the same
character? is this answer good? is the motion natural?) it isn't — so the loop has
nothing to optimize and you fall back to **eyeballing outputs and calling them
good.** That doesn't scale, isn't reproducible, and is easy to fool.

**autoreward makes the reward signal systematic.** It is a method + a
community-driven library for *constructing* an empirical reward in subjective
spaces, so an autonomous loop can actually run there.

Four parts:
1. **The Tiers (Measured / Predicted / Reviewed)** — how to decide *how you know*
   something is good, and always climb toward an automatable signal.
2. **The Gauge library** — worked, copy-and-adapt examples organized by workflow goal.
3. **The Model Index** — a community catalog of models that encode human judgment
   (the **Predicted**-tier proxies), with the domains each is good in and a reliability ranking.
4. **Multi-objective optimizer** — when you have several things that must all be
   good at once, a reward vector + Pareto-based search that cannot be gamed by
   sacrificing one for another.

> Where it sits: [karpathy/autoresearch](https://github.com/karpathy/autoresearch)
> is the *loop* (run experiments, keep what improves a metric). **autoreward is the
> *reward*** — the score that loop optimizes, for domains where no metric is handed
> to you. They compose directly into an RLAIF loop. See also
> [`training-paradigms.md`](training-paradigms.md) for how autoreward connects to
> DPO, GRPO, and PPO fine-tuning.

---

## The three tiers: Measured > Predicted > Reviewed

You score every "is this good?" at one of three tiers. **Always climb toward the
most automatable** — prefer Measured, fall back to Predicted, use Reviewed last.

| Tier | Who / what judges | Speed & cadence | Reproducible | Hard to fool |
|------|-------------------|-----------------|--------------|--------------|
| 🟢 **Measured** | a computed distance to a *known-good target* | instant — **every candidate, in-loop** | yes | yes (with a cross-check) |
| 🟡 **Predicted** | a model trained on human responses predicts the verdict | fast — **every candidate, in-loop** | ~yes | partially (drifts; calibrate it) |
| 🔴 **Reviewed** | a person judges directly | slow — **out-of-loop only** | no | n/a |

- **Measured** needs (i) a known-good target + (ii) a distance metric. Qualitative
  criteria can be *encoded* as feature vectors (identity, pose, composition), so it
  is not limited to physics. When it encodes an expert's criteria it proxies an **expert**.
- **Predicted** proxies a **general** human; use it when no target exists but a
  human-preference model/data does. Always report its calibration (agreement with
  held-out human labels) — it is an approximation that can drift.
- **Reviewed** is the most trustworthy and the **slowest**, so it is the throughput
  bottleneck. **Do NOT review every iteration** — that is the anti-pattern that does
  not scale. Use Reviewed only (a) periodically, to calibrate the Predictor, and
  (b) once at the end, to sign off the single *best* candidate the loop found.

### Use Measured + Predicted together (the workhorse)
Run BOTH on every candidate inside the loop:
- **Measured** anchors you to ground truth wherever you have a target.
- **Predicted** covers the qualities you cannot yet compute (does it look right /
  natural / on-brand?).
- They are **orthogonal**, so each catches the other's blind spot: a candidate that
  games the Measured metric usually tanks the Predicted score, and vice-versa.

That is the whole speed story: the loop runs at **machine speed** on
Measured + Predicted, and **Reviewed sits outside the loop** — recalibrating
Predicted every N rounds and confirming the final pick. The human is spent only
where it is worth it, never on every iteration.

---

## Getting started

autoreward is a Python package + injectable prompt. Install it from source:

```bash
git clone https://github.com/michaelhunley/autoreward
pip install -e autoreward
```

Or inject just the agent policy into your project's CLAUDE.md (idempotent):
```bash
bash autoreward/install.sh /path/to/your/project
# Windows: powershell -File autoreward/install.ps1 C:\path\to\your\project

# ...or install AND wire up the autonomous loop in one step:
bash autoreward/install.sh /path/to/your/project --with-autoresearch
```

**Then just work.** On any "is this good?" question your agent now: names the tier,
opens `gauges/by-goal.md` for the closest example, picks a **Predicted** proxy from
`models/index.json` by domain + ranking, adds a cross-check, and reports a
**number + tier** instead of a vibe — logging any **Reviewed** call so the next run
is Predicted or Measured (the ratchet).

**See the value in one command:** `python demos/naive_metric_fooled.py` — a naive
metric (PSNR) and eyeballing both pick the wrong candidate; the right **Measured**
gauge picks the faithful one. That gap is the whole point.

**See real worked examples:** [`use-cases.md`](use-cases.md) — abstracted cases of
deriving the correct gauge (the averaged metric that hid a defect, the "maximize"
that rewarded cropping, the proxy fooled by a blank input, and more).

**Run it as an RLAIF loop:** define your reward with a gauge here, then let an
autoresearch-style loop maximize it — see [`CONNECT.md`](CONNECT.md) and
`integrations/autoresearch_bridge.py` (run it for a working example). Spot-check by
hand every N rounds to recalibrate the Predicted proxy and confirm Measured wasn't gamed.

---

## Scalar rewards (single gauge)

The simplest case: one gauge, one number. Register it and the bridge handles the
rest.

```python
from integrations.autoresearch_bridge import register, loss

def my_gauge(candidate, target):
    # your Measured or Predicted metric here
    return compute_perceptual_distance(candidate, target)

register("perceptual", my_gauge)             # lower distance = better
print(f"val_metric: {loss('perceptual', candidate, target):.6f}")  # autoresearch reads this
```

See `integrations/autoresearch_bridge.py` for the full scalar API (`reward`, `loss`,
`normalize`, `best_of`).

---

## Multi-objective rewards (reward vectors)

A single scalar can be gamed. The optimizer finds a configuration that scores well
*overall* by letting one important thing quietly fail — the average hides it.

**The pattern:** lighting a scene. Your gauge rewards "looks warm and dramatic." The
optimizer learns that blowing out the highlights scores well on warmth (they're
bright red) while crushing all the shadow detail. The scalar reward goes up. A
human would reject it immediately.

**The fix:** give each thing that matters its own score. The optimizer can only
accept a move that makes at least one score better and makes none worse. You can
see exactly which characteristic is failing.

### Step 1: name your characteristics

A *characteristic* is one quality your output must have. Map it to the meter
features that measure it, with a scale that defines what "clearly wrong" looks like.

```python
char_map = {
    "key_color": {
        "features": ["warmth", "highlight_chroma"],   # which features score this
        "weights":  {"warmth": 1.0, "highlight_chroma": 1.2},  # relative importance
        "scale":    0.4,    # expected weighted distance when this is clearly wrong
    },
    "shadow_depth": {
        "features": ["bg_black", "bg_contrast"],
        "weights":  {"bg_black": 1.0, "bg_contrast": 1.0},
        "scale":    0.35,
    },
    "fill_light": {
        "features": ["subject_exposure"],
        "weights":  {"subject_exposure": 1.0},
        "scale":    0.3,
    },
}
```

Each score is `clamp(1 - distance / scale, 0, 1)`, where distance is the
weighted-mean L1 distance over that characteristic's features. 1 = perfect match,
0 = clearly wrong.

### Step 2: compute the reward vector

```python
from autoreward.reward_vector import compute_reward_vector

current = extract_features(my_render)   # your feature extractor
target  = extract_features(reference)

rv = compute_reward_vector(current, target, char_map)
# rv.scores = {"key_color": 0.82, "shadow_depth": 0.31, "fill_light": 0.75}

worst_char, worst_score = rv.worst()    # ("shadow_depth", 0.31)
print(rv.scalar("min"))                 # 0.31 — the maximin score
```

`rv.scalar("min")` is the *maximin* score: the value of the worst characteristic.
This is the right signal for an outer autoresearch loop — it forces the loop to
fix the weakest link, not pile onto already-good characteristics.

### Step 3: run the multi-objective optimizer

You provide three small functions; the optimizer handles the search.

```python
from autoreward.optimizer import run, best_by_maximin
from autoreward.reward_vector import compute_reward_vector

def measure(candidate):
    """Score a candidate. Called once per trial — your expensive step."""
    current = extract_features(render(candidate))
    return compute_reward_vector(current, target_features, char_map)

def candidates(candidate, rv, deficient_char):
    """Return an ordered list of things to try from this candidate.
    deficient_char is the name of the worst-scoring characteristic,
    so you can prioritize actions that address it."""
    return generate_actions(candidate, deficient=deficient_char)

def apply(candidate, action):
    """Return a NEW candidate with the action applied. Do not mutate."""
    return apply_action(candidate, action)

front, evals = run(
    initial_candidate,
    measure=measure,
    candidates=candidates,
    apply=apply,
    max_evals=20,
)

best = best_by_maximin(front)
print(f"Best: min_score={best.rv.min_score():.3f}, scores={best.rv.scores}")
```

The optimizer keeps a **Pareto front** — the set of candidates where no single one
is better on every characteristic. The accept rule: a trial is only added to the
front if it raises at least one characteristic and regresses none (within a small
tolerance). This blocks "buy fill by sacrificing shadow."

### Hard constraints

Some things should never be traded away regardless of the scores — like a key light
that must come from a specific direction. Pass a `constraint` hook that returns
`True` to reject a candidate outright before the accept rule runs:

```python
def constraint(candidate, rv):
    if rv.scores.get("key_direction", 1.0) < 0.3:
        return True   # reject: wrong side
    return False

front, evals = run(
    initial_candidate, measure, candidates, apply,
    constraint=constraint,
    max_evals=20,
)
```

### Bridge to autoresearch

If you use autoresearch as an outer loop (tuning config parameters, not the inner
search), report the Pareto-best node's scalar so the outer loop has something to
minimize:

```python
from autoreward.integrations.autoresearch_bridge import vector_loss
best = best_by_maximin(front)
print(f"val_metric: {vector_loss(best.rv):.6f}")  # lower = better; autoresearch reads this
```

### Run the standalone example

```bash
python autoreward/optimizer.py
```

This runs a toy three-characteristic lighting problem — brightness, warmth,
contrast — from a bad starting point to near-perfect in 30 evals and shows the
Pareto front.

### A second driver: `descent` (bisection + Gauss-Newton) — see [DESCENT.md](DESCENT.md)

`optimizer.run` is the general driver (opaque candidates, discrete-friendly). When your candidate is
a vector of **continuous knobs** and features are locally **monotone** in them, `descent` is far more
sample-efficient: it **bisects** each feature's controlling knob to target (~log2 evals) and resolves
the coupled residual with a joint **Gauss-Newton** solve (numerical or a **learned** Jacobian). Same
value layer (`RewardVector`); you pick the driver.

```python
from autoreward.descent import Knob, descent
best, feats, evals, trace = descent(candidate, knobs, measure, target, weights=w, jacobian=learned)
```

Key lesson (why ground truth is *training*, not a crutch): a driver is only as good as its Jacobian.
On the toy coupled target, numerical bisect+GN solves in ~53 evals; a **learned** Jacobian (fitted
from logged knob→feature samples) solves in **~11 evals and more accurately** — so use ground-truth
data to *learn the sensitivity table*, then the fast driver works on a real engine. Full write-up in
[DESCENT.md](DESCENT.md).

---

## Two rules that make it an automatable reward

1. **The Ratchet** — every **Reviewed** judgment is logged as labeled data so the
   *next* run can be Predicted or Measured. You never stay at Reviewed for the same
   problem twice.
2. **No gauge trusted alone** — pair every gauge with an orthogonal cross-check.
   (Real failures: a blob passed a silhouette-IoU; a head-less 3D reconstruction
   passed a deformation metric; a perceptual proxy scored a blank output "perfect."
   Each needed a second, orthogonal gauge to catch.)

The injectable prompt itself lives in `AGENT_POLICY.md`.

---

## Contribute (community-driven)

The library grows by PR — same spirit as a context hub. Add one file:
- a **gauge**: `gauges/entries/<id>.md` (markdown + frontmatter; see `SCHEMA.md`)
- a **Predicted-tier (human-response) model**: `models/entries/<id>.md`
Then `python scripts/build.py` regenerates `INDEX.md` + `models/index.json`. See
[`CONTRIBUTING.md`](CONTRIBUTING.md). The honest part that matters most: list each
model's **weak** domains and justify its **ranking_score** — that's what stops
people trusting a proxy where it lies.

---

## Maintenance & integration

- **Catalog stays current automatically.** CI (`.github/workflows/ci.yml`)
  rebuilds and fails any push/PR where `INDEX.md` / `models/index.json` are stale,
  and smoke-tests the demo. Install `hooks/pre-commit` to auto-rebuild locally
  (`cp hooks/pre-commit .git/hooks/`).
- **Grow the model index with an agent.** `DISCOVERY.md` is a prompt that scouts
  new human-response models, *validates* them (calibration evidence, honest weak
  domains, ranking), and emits entries — so curation isn't all manual.
- **Connect an autonomous loop.** `bash install.sh <proj> --with-autoresearch`
  clones karpathy/autoresearch and points you at `CONNECT.md` +
  `integrations/autoresearch_bridge.py`, which expose any gauge as the scalar
  reward that loop maximizes (run the bridge for a working example).
- **Fine-tuning with DPO or GRPO?** See [`training-paradigms.md`](training-paradigms.md)
  for how autoreward gauges plug into preference data generation (DPO) and per-output
  scoring (GRPO/PPO).

---

## Repo layout

```
README.md               the method + onboarding (this file)
training-paradigms.md   how autoreward connects to DPO, GRPO, PPO fine-tuning
use-cases.md            worked examples of deriving the right gauge
AGENT_POLICY.md         injectable CLAUDE.md block
CONNECT.md              wiring to karpathy/autoresearch
SCHEMA.md               gauge + model entry schemas
CONTRIBUTING.md         how to add an entry by PR
INDEX.md                generated catalog (scripts/build.py)
reward_vector.py        RewardVector, compute_reward_vector()
optimizer.py            multi-objective DFS (run, best_by_maximin, Node)
__init__.py             package entry point
demos/                  runnable proofs (naive_metric_fooled.py)
gauges/
  by-goal.md            workflow goal -> recommended tier/metric/model
  entries/*.md          gauge entries (community)
models/
  entries/*.md          Predicted-tier model entries (community)
  index.json            generated catalog
integrations/
  autoresearch_bridge.py  scalar + vector bridge to autoresearch
scripts/build.py        rebuild the catalogs from entries
```

MIT licensed — built to be applied to anyone's subjective or qualitative problem space.
