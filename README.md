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

Three parts:
1. **The Tiers (A/B/C)** — how to decide *how you know* something is good, and
   always climb toward an automatable signal.
2. **The Gauge library** — worked, copy-and-adapt examples organized by workflow goal.
3. **The Model Index** — a community catalog of models that encode human judgment
   (the tier-B proxies), with the domains each is good in and a reliability ranking.

> Where it sits: [karpathy/autoresearch](https://github.com/karpathy/autoresearch)
> is the *loop* (run experiments, keep what improves a metric). **autoreward is the
> *reward*** — the score that loop optimizes, for domains where no metric is handed
> to you. They compose directly into an RLAIF loop.

---

## The Tiers: A / B / C — automate the reward, prefer C > B > A

| Tier | What it is | Reproducible | Hard to fool | Optimizable in a loop |
|------|-----------|--------------|--------------|-----------------------|
| **C — Empirical, target-anchored** | computable distance from a *defined known-good target*; pass/fail on a threshold | yes | yes (with a cross-check) | yes |
| **B — Learned proxy** | a model trained on human responses predicts what a human would say | ~yes | partially (drifts / gameable) | yes |
| **A — Human review** | a person judges directly | no | n/a | no |

- **C** needs (i) a known-good target + (ii) a distance metric. Not limited to
  physics — qualitative criteria can be *encoded* as feature vectors (identity,
  pose, lighting, composition). When C encodes an expert's criteria it proxies an
  **expert**.
- **B** proxies a **general** human; use when no target exists but human-preference
  data/model does. Report its calibration (agreement with held-out human labels).
- **A** is the last resort.

**Two rules that make it an automatable reward:**
1. **The Ratchet** — every tier-A judgment is logged as labeled data so the *next*
   run is B or C. You never stay at A for the same problem twice.
2. **No gauge trusted alone** — pair every gauge with an orthogonal cross-check.
   (Real failures: a blob passed a silhouette-IoU; a head-less 3D reconstruction
   passed a deformation metric. Both needed a second gauge to catch.)

**See it fail-then-work in 1 file:** `python demos/naive_metric_fooled.py` — PSNR
(a naive metric) and eyeballing both pick the wrong candidate; the right tier-C
gauge picks the faithful one. That gap *is* the value of this repo.

---

## Use it in your own project (onboarding)

autoreward is **injected into your repo** so your coding agent adopts the discipline.

```bash
git clone https://github.com/michaelhunley/autoreward && cd autoreward

# inject the A/B/C policy + atlas pointers into YOUR project's CLAUDE.md (idempotent)
bash install.sh /path/to/your/project       # or: powershell -File install.ps1 C:\path\to\project
```

Then work normally. On any "is this good?" question your agent now: names the tier,
opens `gauges/by-goal.md` for the closest example, picks a B-proxy from
`models/index.json` by domain + ranking, adds a cross-check, reports a **number +
tier** (not a vibe), and logs any tier-A call (the ratchet). No runtime to install
— it's a method + a library + an injectable prompt (`AGENT_POLICY.md`).

To run an RLAIF loop: define your reward with a gauge from here, then let an
autoresearch-style loop optimize it, with periodic tier-A spot-checks to recalibrate
B and confirm C wasn't gamed.

---

## Contribute (community-driven)

The library grows by PR — same spirit as a context hub. Add one file:
- a **gauge**: `gauges/entries/<id>.md` (markdown + frontmatter; see `SCHEMA.md`)
- a **B-proxy model**: `models/entries/<id>.md`
Then `python scripts/build.py` regenerates `INDEX.md` + `models/index.json`. See
[`CONTRIBUTING.md`](CONTRIBUTING.md). The honest part that matters most: list each
model's **weak** domains and justify its **ranking_score** — that's what stops
people trusting a proxy where it lies.

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

## Repo layout

```
README.md            the method + onboarding
AGENT_POLICY.md      the injectable CLAUDE.md block
SCHEMA.md            gauge + model entry schemas
CONTRIBUTING.md      how to add an entry by PR
INDEX.md             generated catalog (scripts/build.py)
demos/               runnable proofs (naive_metric_fooled.py)
gauges/
  by-goal.md         workflow goal -> recommended tier/metric/model
  entries/*.md       gauge entries (community)
models/
  entries/*.md       B-proxy model entries (community)
  index.json         generated catalog
scripts/build.py     rebuild the catalogs from entries
```

MIT licensed — built to be applied to anyone's subjective or qualitative problem space.
