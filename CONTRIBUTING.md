# Contributing to autoreward

The library grows by pull request. Two kinds of contributions: **gauges** (ways to
score a goal) and **B-proxy models** (models that encode human judgment). Each is a
single markdown file with frontmatter, so PRs never collide on one big file.

## Add a gauge

1. Create `gauges/entries/<your-id>.md` following the gauge schema in
   [`SCHEMA.md`](SCHEMA.md). Frontmatter holds the fields; the body is a short
   how-to. Pick the **highest tier you can build** (C > B > A).
2. State the **target** and **metric** precisely, a **threshold**, and — required —
   a **cross_check** and the known **fooled_by** failure mode. A gauge with no
   cross-check is not accepted; everything is foolable.
3. If your metric uses a model, reference its `id` from `models/index.json`.
4. Run `python scripts/build.py` (stdlib only) and commit the regenerated
   `INDEX.md` + `models/index.json`.

## Add a B-proxy model

1. Create `models/entries/<your-id>.md` per the model-index schema.
2. Be honest about `domains_weak` and justify `ranking_score` with **calibration
   evidence** (agreement with held-out human labels) or adoption. The weak domains
   are the most valuable field — they stop people trusting a proxy where it misleads.
3. Run `python scripts/build.py`.

## Updating a ranking (the feedback loop)

A model's `ranking_score` is a prior, not a guarantee. If you have evidence it
tracks (or fails to track) humans in a domain, open a PR adjusting the score and
add the evidence to `ranking_basis`. This is how the index self-corrects.

## Bar for merge

- No proprietary content or IP — examples must be generic and shareable.
- Reproducible where possible (a runnable demo like `demos/naive_metric_fooled.py`
  is the gold standard).
- Honest failure modes (`fooled_by`, `domains_weak`) present and specific.
