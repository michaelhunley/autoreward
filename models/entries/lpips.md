---
id: "lpips"
modality: "image"
encodes: "human 2AFC perceptual-similarity judgments"
use_as: "C-metric (perceptual distance to a target image)"
domains_strong: [perceptual image fidelity vs a target]
domains_weak: [semantic identity, no-reference quality]
ranking_score: 5
ranking_basis: "trained directly on human perceptual judgments; standard"
ref: "Zhang et al. 2018"
---

# lpips

**Use as:** C-metric (perceptual distance to a target image)

lpips(render, target_aligned_crop); lower = closer

