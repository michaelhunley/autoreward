# Agent policy injection (drop into CLAUDE.md / system prompt)

Paste this into an agent's persistent instructions so it frames every quality
judgment with the Measured / Predicted / Reviewed tiers and strives for
Measured > Predicted > Reviewed.

```markdown
## Validation tiers - frame every "is it good?" as Measured > Predicted > Reviewed

Before claiming something works, classify HOW you know, and build the most
automatable tier you can:
- MEASURED (empirical, target-anchored): a computed distance to a known-good
  target; pass/fail on a threshold. Objective, instant, runs on every candidate in
  the loop. Build this whenever a target can be defined - INCLUDING qualitative
  domains (encode the criteria as feature vectors). Measured is the goal.
- PREDICTED (human-response proxy): score with a model trained on human responses
  to predict the verdict. Automatic and in-loop, but an approximation that can
  drift - state its calibration (agreement with held-out human labels) when you
  cite it. Use when no objective target exists but a preference model/data does.
- REVIEWED (a person judges directly): the most trustworthy and the SLOWEST, so it
  is the throughput bottleneck. Do NOT review every iteration - that does not scale.
  Use it OUT of the loop: (a) periodically, to calibrate the Predictor, and (b) once
  at the end, to sign off the single best candidate. Record each Reviewed judgment
  as labeled data to bootstrap a Predicted or Measured gauge next time (the ratchet).

Rules:
1. NEVER validate by eyeballing a video/image alone and calling it good - that is a
   Reviewed judgment masquerading as a result. Name the tier explicitly.
2. A gauge must be HARD TO FOOL: pair it with an orthogonal cross-check. If two
   gauges disagree, the weaker one is suspect (a blob once passed silhouette-IoU; a
   head-less reconstruction passed a deformation metric; a perceptual proxy scored a
   blank output "perfect" - each needed a 2nd, orthogonal gauge).
3. Run MEASURED + PREDICTED TOGETHER on every candidate in the loop: Measured anchors
   to ground truth where you have a target, Predicted covers what you cannot yet
   compute, and being orthogonal each catches the other's blind spot. Keep Reviewed
   outside the loop.
4. Report results AS a tier + number, not a vibe: "torso interior-frac 0.52
   (Measured)", not "looks better". Do not call a result "close" if the right gauge -
   or a human - would reject it.
5. When you must escalate to Reviewed, say so and propose the Measured/Predicted
   gauge that removes the need next time.
```

See this repo's `README.md` for the method, `use-cases.md` for worked examples of
deriving a gauge, `gauges/by-goal.md` for templates to adapt, and `models/index.json`
for Predicted-tier (human-response) models by domain.
