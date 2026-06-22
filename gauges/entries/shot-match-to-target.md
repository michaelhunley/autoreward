---
id: "shot-match-to-target"
workflow_goal: "An engine/render is driven (camera, pose, lighting, character) to EMPIRICALLY match a target frame/clip. C encodes an EXPERT's 'does this match' as feature vectors."
domain: "rendering | image-gen"
tier: "C"
target: "the target frame/clip"
metric: "a weighted vector of orthogonal distances: identity (embedding cosine), pose (normalized joint/keypoint error), camera (silhouette-IoU + subject bbox), lighting (brightness/contrast/color-histogram EMD + key-light direction), perceptual (LPIPS), composition (placement); temporal (pose-trajectory + optical-flow) for clips"
threshold: "each component under its own tolerance; identity + perceptual are gates"
model: "clip | arcface | lpips | pose-model"
cross_check: "the components cross-check each other (e.g. high identity but bad pose-error => wrong frame; good LPIPS but low identity => right composition, wrong subject)"
fooled_by: "optimizing one component while others regress; LPIPS at denoise=1.0 traps (compare partial-denoise)"
ratchet: "n/a; this IS expert-judgment-as-metric. Gaps the vector can't capture get logged as A and folded into new components"
example_values: "n/a (framework)"
source: "an engine-to-target matching loop - the canonical 'iterate engine params to a known-good target' RLAIF-style loop; reward = the combined vector"
---

# shot-match-to-target

An engine/render is driven (camera, pose, lighting, character) to EMPIRICALLY match a target frame/clip. C encodes an EXPERT's 'does this match' as feature vectors.

