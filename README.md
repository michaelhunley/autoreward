# Gauge Atlas

**A systematic way to turn subjective / qualitative judgment into empirical signals — so agents and humans iterate toward "best" instead of arguing about "looks good."**

Most hard problems in ML, creative tooling, and agentic work stall on the same
failure: validating quality by *looking at it and deciding it's good*. That is
slow, irreproducible, and easy to fool. This repo is a catalog and a method for
escaping it.

It has three parts:
1. **The Tiers (A/B/C)** — a discipline for *how you know* something is good.
2. **The Gauge Atlas** — a library of worked examples, organized **by workflow
   goal**, you can copy and adapt to a new problem.
3. **The Model Index** — a catalog of models that encode human judgment (the
   tier-B proxies), with the domains each is good in and a reliability ranking.

---

## The Tiers: A / B / C (prefer C > B > A)

Every "is this good / correct / a match?" judgment is one of three tiers. Always
push toward the highest one you can build.

| Tier | What it is | Cost | Reproducible | Hard to fool | Directly optimizable |
|------|-----------|------|--------------|--------------|----------------------|
| **C — Empirical, target-anchored** | A computable distance from a *defined known-good target*; pass/fail on a threshold. | low | yes | yes (with a cross-check) | yes (search/gradient) |
| **B — Learned proxy** | A model trained on human responses predicts what a human would say. | low/med | ~yes | partially (can be gamed/drift) | yes |
| **A — Human review** | A person judges directly. | high | no | n/a | no |

- **C** needs (i) a known-good target and (ii) a distance metric. It is **not**
  limited to physics — qualitative criteria can be *encoded* as feature vectors
  (identity, pose, lighting, composition). When C encodes an expert's criteria,
  it proxies an **expert**.
- **B** proxies a **general** human; use it when no objective target exists but
  human-preference data does. Always report its *calibration* (agreement with
  held-out human labels) when you cite it.
- **A** is the last resort.

### Two rules that make it work

1. **The Ratchet.** Every time you're forced down to A, capture the human's
   judgment as labeled data, so the *next* time the same problem is B or C. You
   never stay at A for the same problem twice. Coverage ratchets toward C.
2. **No gauge trusted alone.** A gauge must be *hard to fool*: pair it with a
   cross-check. (Real examples: a featureless blob once passed silhouette-IoU; a
   head-less 3D reconstruction passed a 1.9% deformation metric. Both needed a
   second, orthogonal gauge to catch.)

### Why C > B > A (the punchline)

C lets you iterate without a human in the loop, reproducibly, and optimize
directly. B scales human judgment but can drift and be gamed. A is ground truth
but doesn't scale. **C and B together are the reward signal for RLAIF-style
loops** (generate -> score -> select/refine), with periodic A spot-checks to
recalibrate B and confirm C wasn't gamed.

---

## How to apply this to a new problem

1. State the **workflow goal** in one line ("is the rendered character the same
   person as the reference?").
2. Ask: **can I define a known-good target + a distance?** -> build **C**.
   Look in [`gauges/by-goal.md`](gauges/by-goal.md) for a close example to adapt.
3. If not, is there **human-preference data or a model that encodes it?** -> use
   **B**. Pick from [`models/index.json`](models/index.json) by domain + ranking.
4. Otherwise **A** — and log the judgment to bootstrap B/C next time.
5. Add a **cross-check** gauge so the primary can't be silently fooled.
6. Register your gauge (see [`SCHEMA.md`](SCHEMA.md)) and, ideally, contribute it
   back as a new worked example.

---

## Use it in your own project (onboarding)

Gauge Atlas is meant to be **injected into your own repo** so your coding agent
adopts the discipline — same idea as a shareable `CLAUDE.md` policy pack.

```bash
# 1. get it (clone next to your projects)
git clone https://github.com/<you>/gauge-atlas && cd gauge-atlas

# 2. inject the policy into YOUR project's CLAUDE.md (idempotent)
bash install.sh /path/to/your/project          # or: powershell -File install.ps1 C:\path\to\project
#   -> appends a marked block with the A/B/C policy + pointers to this atlas

# 3. (optional) just read the one file you need
#   AGENT_POLICY.md  - the snippet to paste by hand if you prefer
```

Then work normally. When your agent (or you) hits a "is this good?" question it now:
1. names the tier (A/B/C) instead of eyeballing,
2. opens `gauges/by-goal.md`, finds the closest workflow goal, and adapts that gauge,
3. if it needs a learned proxy, picks one from `models/index.json` by domain + ranking,
4. adds a cross-check, reports a **number + tier**, and logs any tier-A call so the
   next run can be B or C (the ratchet).

No runtime, no dependency to install — it's a method + a reference library + an
injectable prompt. Contribute your new gauge back via a PR.

## Relationship to autoresearch (complementary)

[karpathy/autoresearch](https://github.com/karpathy/autoresearch) lets an agent run
LLM training experiments autonomously overnight and keep the ones that improve a
metric (`val_bpb`). It works **because it already has a clean tier-C metric** —
lower bits-per-byte is objective, reproducible, and hard to fool.

Most domains aren't so lucky. In creative/qualitative/subjective spaces (does this
render match the target? is it the same character? is the motion natural?) the hard
part is that **there is no obvious metric** — so the loop has nothing to optimize
and you fall back to staring at outputs.

**Gauge Atlas is the missing half: the method for *constructing* the reward signal**
(tier C if a target can be defined, tier B if only human preference exists) so that
an autoresearch-style loop can run in those domains. autoresearch is the *engine*
(generate → score → keep best, on a budget); Gauge Atlas supplies the *score*. They
compose directly: define your `val_*` with a gauge from here, then let an
autoresearch-style loop optimize it — with periodic human spot-checks to recalibrate
B and confirm C wasn't gamed (RLAIF). The onboarding pattern here (one injectable
agent-instruction file, point your agent at it) is deliberately modeled on
autoresearch's `program.md`.

## Repo layout

```
README.md            this file - the method
SCHEMA.md            the gauge + model-index entry schemas
gauges/
  by-goal.md         the library: workflow goal -> recommended tier/metric/model
  examples/*.json    worked gauges (real + generalized), copy-and-adapt
models/
  index.json         models that encode human responses (tier-B proxies)
  README.md          how the ranking + domain fit are assigned
```

This atlas is meant to grow. The point is not the specific examples — it is to
make "how do we know this is good?" a **systematic, answerable** question in any
subjective or qualitative problem space.
