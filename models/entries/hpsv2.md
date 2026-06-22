---
id: "hpsv2"
modality: "image-text"
encodes: "human preference for generated images"
use_as: "B-proxy"
domains_strong: [T2I preference ranking]
domains_weak: [fine fidelity to a specific target]
ranking_score: 4
ranking_basis: "human-preference-trained; common T2I benchmark"
ref: "Wu et al. 2023"
---

# hpsv2

**Use as:** B-proxy

hps(prompt, image)

