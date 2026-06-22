# Agent policy injection (drop into CLAUDE.md / system prompt)

Paste this into an agent's persistent instructions so it frames every quality
judgment with the A/B/C tiers and strives for C > B > A.

```markdown
## Validation Tiers - frame every "is it good?" judgment as A/B/C (prefer C > B > A)

Before claiming something works, classify HOW you know, and build the highest tier you can:
- C (empirical, target-anchored): define a known-good target + a distance metric;
  pass/fail on a threshold. Build this whenever a target can be defined - INCLUDING
  qualitative domains (encode the expert's criteria as feature vectors). C is the goal.
- B (learned proxy): score with a model trained on human responses. Use when no
  objective target exists but preference data/model does. State its calibration
  (agreement with held-out human labels) when you cite it. B proxies a general human.
- A (human review): only when neither exists. Treat each A as a DATA POINT - record
  the judgment to bootstrap a B or C gauge next time (the ratchet).

Rules:
1. NEVER validate by eyeballing a video/image alone and calling it good - that is
   tier A masquerading as a result. Name the tier explicitly.
2. A gauge must be HARD TO FOOL: pair it with an orthogonal cross-check. If two
   gauges disagree, the weaker one is suspect (a blob once passed silhouette-IoU; a
   head-less reconstruction passed a deformation metric - both needed a 2nd gauge).
3. When you escalate to A, say so and propose the C/B gauge that removes the need
   next time.
4. Report results AS a tier + number, not a vibe: "torso interior-frac 0.52 (C)",
   not "looks better".
5. C and B can be the reward in an iterate-and-select (RLAIF) loop; spot-check with
   A to recalibrate B and confirm C wasn't gamed.
```

See this repo's `README.md` for the method, `gauges/by-goal.md` for examples to
adapt, and `models/index.json` for B-proxy models by domain.
