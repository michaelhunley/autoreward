---
id: "match-target-image-perceptual"
workflow_goal: "Choose the reconstruction/generation that actually MATCHES a target image, when the higher-PSNR or prettier-looking one is wrong (naive pixel metrics AND eyeballing both get fooled)."
domain: "image-gen | reconstruction"
tier: "measured"
target: "the reference image"
metric: "human-aligned perceptual distance to the target (LPIPS primary; DreamSim) - NOT raw PSNR/MSE"
threshold: "lower perceptual distance = closer; rank candidates"
model: "lpips | dreamsim"
cross_check: "a second human-aligned model or a feature/identity embedding; structure/edge-energy preservation"
fooled_by: "PSNR/MSE prefer a detail-destroying BLUR over a sharp image with a tiny (2px) shift; 'looks sharp' (Reviewed tier) and PSNR (naive C) both mis-rank"
ratchet: "n/a (already C)"
example_values: "see demos/naive_metric_fooled.py - PSNR picks the blur (WRONG), a structure-aware gauge picks the faithful image (RIGHT)"
source: "classic perceptual-metric result (Zhang et al. 2018, LPIPS); included here as a RUNNABLE proof that the right Measured gauge beats both naive metrics and eyeballing"
---

# match-target-image-perceptual

Choose the reconstruction/generation that actually MATCHES a target image, when the higher-PSNR or prettier-looking one is wrong (naive pixel metrics AND eyeballing both get fooled).

