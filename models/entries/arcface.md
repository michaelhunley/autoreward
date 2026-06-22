---
id: "arcface"
modality: "image"
encodes: "face-identity discrimination (margin loss on identity labels)"
use_as: "C-metric (face identity cosine vs a reference face)"
domains_strong: [face identity match]
domains_weak: [non-face, occluded/back views]
ranking_score: 5
ranking_basis: "state-of-practice for face identity"
ref: "Deng et al. 2019"
---

# arcface

**Use as:** C-metric (face identity cosine vs a reference face)

cosine of face embeddings, render-face vs reference-face

