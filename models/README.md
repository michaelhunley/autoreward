# Model Index

`index.json` catalogs models that **encode human responses** — the Predicted proxies
(and the backbones for Measured feature distances). Use it to pick a proxy by
**domain fit** and **reliability ranking** instead of guessing.

Each entry says what human responses the model encodes, where it's strong, where
it misleads, and a `ranking_score` (1–5) for how trustworthy it is as a human
proxy in its strong domains. See `../SCHEMA.md` for the rubric.

## Picking a model

1. Match `modality` + your `workflow_goal` to `domains_strong`.
2. Prefer higher `ranking_score`; read `domains_weak` for the failure modes.
3. Decide `use_as`:
   - **measured-metric** — distance to a *target* (e.g. LPIPS/ArcFace cosine to a reference). Preferred.
   - **predicted-proxy** — preference/quality score when there's no target (e.g. PickScore, reward models).
4. Always add a cross-check (a second model or an orthogonal metric).

## Calibration is part of the score

A predicted-proxy is only as good as its agreement with real human labels. When you
deploy one, hold out human judgments and track the agreement; if it drops, the
score here is too high for your distribution — lower it locally and note why. The
ranking here is a prior, not a guarantee.

## Contributing

Add a model: fill the schema, justify `ranking_score` with calibration evidence or
adoption, and list honest `domains_weak`. The index is most useful when the weak
domains are accurate — that's what stops people from trusting a proxy where it
lies.
