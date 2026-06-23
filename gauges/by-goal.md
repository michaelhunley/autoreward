# The Atlas: gauges by workflow goal

A library of logical mappings. Find the row closest to your problem, copy the
approach, adapt the target/metric. Each lists the **best tier you can usually
build**, with the fallback. Detailed worked examples live in `examples/`.

> Read Measured > Predicted > Reviewed as "build the Measured if you can; drop to Predicted/Reviewed only when you must."

## 3D / reconstruction / avatars

| Workflow goal | Tier | Metric (target-anchored) | Model | Cross-check |
|---|---|---|---|---|
| Reconstruction is a tight **surface**, not a fuzzy volume | **Measured** | torso/region cross-section **interior-fraction** (gaussians inside r<0.5 of the shell); ~0.23 crisp vs ~0.58 diffuse | none | rendered view from a held-out camera |
| Driven/animated model **deforms correctly** | **Measured** | per-point distance to the artist-skinned ground-truth mesh, % of body height (<5%) | none | the surface gauge above (deformation can pass on incomplete geometry) |
| Reconstructed character **is the same identity** | **Measured** | feature-embedding cosine (render vs reference render, same camera) | ArcFace (faces) / CLIP / DreamSim | held-out pose; a blob can match a single view |
| Capture **coverage** is complete (no holes when posed) | **Measured** | per-region primitive counts + point-cloud overlay on the rest mesh | none | pose to motion extremes, recheck |

## Image generation / editing

| Workflow goal | Tier | Metric | Model | Cross-check |
|---|---|---|---|---|
| Output **matches a target image** | **Measured** | LPIPS / DreamSim (primary), SSIM/PSNR on aligned crop | LPIPS, DreamSim | identity gauge if a person is involved |
| Output **matches a text prompt** (no target image) | **Measured/Predicted** | CLIP image-text cosine (C, if prompt is the target); else preference score | CLIP, PickScore, HPSv2 | human spot-check to calibrate |
| **Rank** generations by general human preference | **Predicted** | preference/reward score | PickScore, HPSv2, ImageReward | Reviewed spot-check on ties |
| **Aesthetic** quality | **Predicted** | aesthetic predictor score | LAION-Aesthetic, CLIP-IQA | Reviewed, sparingly |
| Re-render **matches a target shot** (camera/lighting/pose) | **Measured** | feature-vector match: identity + pose-keypoints + camera silhouette-IoU + lighting histogram/EMD + LPIPS | CLIP, ArcFace, pose model | each vector cross-checks the others |

## Text / language

| Workflow goal | Tier | Metric | Model | Cross-check |
|---|---|---|---|---|
| Summary/answer **matches a reference** | **Measured** | BERTScore / ROUGE vs reference | BERTScore | Reviewed on disagreement |
| Output quality with **no reference** | **Predicted** | reward/judge model score | RLHF reward model, LLM-as-judge | Reviewed spot-check; judge-model bias audit |
| **Factual/grounded** | **Measured** | claim-support check against sources (entailment) | NLI model | Reviewed on flagged claims |

## Code

| Workflow goal | Tier | Metric | Model | Cross-check |
|---|---|---|---|---|
| Change is **correct** | **Measured** | tests pass + typecheck + lint | none | adversarial test added for the bug |
| Change **does what was asked** | **Measured/Reviewed** | acceptance test from the spec | none | human review of intent |

## Animation / motion / video / audio

| Workflow goal | Tier | Metric | Model | Cross-check |
|---|---|---|---|---|
| Motion **matches reference** mocap/clip | **Measured** | per-joint trajectory error (normalized) + optical-flow agreement | pose model | render review for visual artifacts |
| Motion **looks human/natural** (no reference) | **Predicted** | motion-quality/human-likeness score | motion-quality models | Reviewed (animator) spot-check |
| Video **perceptual quality** | **Measured/Predicted** | VMAF (human-tuned) | VMAF | Reviewed on edge cases |
| Speech **intelligibility / match** | **Measured** | WER vs transcript; speaker-embedding cosine vs reference | ASR, speaker-id | A for prosody/expression |

---

### The pattern to notice

Wherever a **target** exists, there is a **Measured**. Where only **human preference**
exists, there is a **Predicted** (pick the model by domain + ranking from
`models/index.json`). **Reviewed** appears only where neither does — and each A is a
chance to collect data and build the Predicted or Measured for next time.
