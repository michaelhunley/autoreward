# Discovery prompt — auto-grow the model index

Run this prompt with a capable agent (Claude/etc.) to find new human-response
models and add validated entries, so maintaining `models/` doesn't fall to manual
curation. It encodes *how to vet a proxy*, not just how to list one.

```markdown
You are maintaining autoreward's model index (models/entries/*.md) - a catalog of
models that ENCODE HUMAN JUDGMENT (perceptual similarity, preference/reward,
quality/aesthetic, identity) usable as Predicted proxies or Measured feature distances.

TASK: discover models NOT already in models/index.json and add a validated entry
for each strong one.

1. SCOUT (per modality: image, image-text, video, text, audio, 3d, motion):
   search recent papers/leaderboards/repos for models trained on or evaluated
   against HUMAN responses - perceptual-similarity (2AFC), preference/reward
   (RLHF/RLAIF), quality (MOS/IQA), aesthetic, identity. Skip anything already in
   models/index.json (check ids).
2. VALIDATE each candidate before adding (this is the point):
   - What human responses does it encode? (the `encodes` field)
   - Is there PUBLISHED human-correlation / calibration evidence? Quote it. No
     evidence -> ranking_score <= 2, say so.
   - Strong domains AND honest weak/failure domains (most important field).
   - Is it runnable/available (weights, license)? Note it.
   - Cross-check: does it duplicate an existing entry? If better, propose a
     ranking update to the old one instead.
3. SCORE with the SCHEMA.md rubric (1-5) and JUSTIFY in ranking_basis.
4. EMIT models/entries/<id>.md (frontmatter per SCHEMA.md + a short how-to body),
   run `python scripts/build.py`, and open a PR. Include your evidence links.

Bias to PRECISION over recall: a wrong/over-ranked proxy is worse than a missing
one, because people will trust it where it lies. When unsure, lower the score and
spell out the weak domains.
```

Cadence: run it when a modality you care about has moved (new SOTA reward model,
new perceptual metric). The CI (`.github/workflows/ci.yml`) validates the entries
parse and the catalog rebuilds; a human reviews the PR for the calibration claims.
