# The Atlas: gauges by workflow goal

A library of logical mappings. Find the row closest to your problem, copy the
approach, adapt the target/metric. Each lists the **best tier you can usually
build**, with the fallback. Detailed worked examples live in `examples/`.

> Read C > B > A as "build the C if you can; drop to B/A only when you must."

## 3D / reconstruction / avatars

| Workflow goal | Tier | Metric (target-anchored) | Model | Cross-check |
|---|---|---|---|---|
| Reconstruction is a tight **surface**, not a fuzzy volume | **C** | torso/region cross-section **interior-fraction** (gaussians inside r<0.5 of the shell); ~0.23 crisp vs ~0.58 diffuse | none | rendered view from a held-out camera |
| Driven/animated model **deforms correctly** | **C** | per-point distance to the artist-skinned ground-truth mesh, % of body height (<5%) | none | the surface gauge above (deformation can pass on incomplete geometry) |
| Reconstructed character **is the same identity** | **C** | feature-embedding cosine (render vs reference render, same camera) | ArcFace (faces) / CLIP / DreamSim | held-out pose; a blob can match a single view |
| Capture **coverage** is complete (no holes when posed) | **C** | per-region primitive counts + point-cloud overlay on the rest mesh | none | pose to motion extremes, recheck |

## Image generation / editing

| Workflow goal | Tier | Metric | Model | Cross-check |
|---|---|---|---|---|
| Output **matches a target image** | **C** | LPIPS / DreamSim (primary), SSIM/PSNR on aligned crop | LPIPS, DreamSim | identity gauge if a person is involved |
| Output **matches a text prompt** (no target image) | **C/B** | CLIP image-text cosine (C, if prompt is the target); else preference score | CLIP, PickScore, HPSv2 | human spot-check to calibrate |
| **Rank** generations by general human preference | **B** | preference/reward score | PickScore, HPSv2, ImageReward | A spot-check on ties |
| **Aesthetic** quality | **B** | aesthetic predictor score | LAION-Aesthetic, CLIP-IQA | A, sparingly |
| Re-render **matches a target shot** (camera/lighting/pose) | **C** | feature-vector match: identity + pose-keypoints + camera silhouette-IoU + lighting histogram/EMD + LPIPS | CLIP, ArcFace, pose model | each vector cross-checks the others |

## Text / language

| Workflow goal | Tier | Metric | Model | Cross-check |
|---|---|---|---|---|
| Summary/answer **matches a reference** | **C** | BERTScore / ROUGE vs reference | BERTScore | A on disagreement |
| Output quality with **no reference** | **B** | reward/judge model score | RLHF reward model, LLM-as-judge | A spot-check; judge-model bias audit |
| **Factual/grounded** | **C** | claim-support check against sources (entailment) | NLI model | A on flagged claims |

## Code

| Workflow goal | Tier | Metric | Model | Cross-check |
|---|---|---|---|---|
| Change is **correct** | **C** | tests pass + typecheck + lint | none | adversarial test added for the bug |
| Change **does what was asked** | **C/A** | acceptance test from the spec | none | human review of intent |

## Animation / motion / video / audio

| Workflow goal | Tier | Metric | Model | Cross-check |
|---|---|---|---|---|
| Motion **matches reference** mocap/clip | **C** | per-joint trajectory error (normalized) + optical-flow agreement | pose model | render review for visual artifacts |
| Motion **looks human/natural** (no reference) | **B** | motion-quality/human-likeness score | motion-quality models | A (animator) spot-check |
| Video **perceptual quality** | **C/B** | VMAF (human-tuned) | VMAF | A on edge cases |
| Speech **intelligibility / match** | **C** | WER vs transcript; speaker-embedding cosine vs reference | ASR, speaker-id | A for prosody/expression |

---

### The pattern to notice

Wherever a **target** exists, there is a **C**. Where only **human preference**
exists, there is a **B** (pick the model by domain + ranking from
`models/index.json`). **A** appears only where neither does — and each A is a
chance to collect data and build the B or C for next time.
