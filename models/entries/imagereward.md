---
id: "imagereward"
modality: "image-text"
encodes: "human ratings of T2I (alignment + fidelity + aesthetics)"
use_as: "B-proxy (reward for RLAIF on T2I)"
domains_strong: [T2I reward signal]
domains_weak: [non-generative]
ranking_score: 4
ranking_basis: "purpose-built reward model with human ratings"
ref: "Xu et al. 2023"
---

# imagereward

**Use as:** B-proxy (reward for RLAIF on T2I)

reward(prompt, image)

