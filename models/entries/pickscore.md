---
id: "pickscore"
modality: "image-text"
encodes: "human preference between text-to-image generations"
use_as: "B-proxy (which generation a general human prefers)"
domains_strong: [ranking T2I outputs for a prompt]
domains_weak: [absolute quality, non-generative images]
ranking_score: 4
ranking_basis: "trained on large human preference set; good ranking correlation"
ref: "Kirstain et al. 2023"
---

# pickscore

**Use as:** B-proxy (which generation a general human prefers)

score(prompt, image); higher = more preferred

