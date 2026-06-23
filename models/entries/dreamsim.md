---
id: "dreamsim"
modality: "image"
encodes: "human similarity judgments at the mid-level (layout/pose/identity-ish)"
use_as: "measured-metric (human-aligned image distance)"
domains_strong: [human-aligned 'are these the same thing']
domains_weak: [pixel-exact differences]
ranking_score: 4
ranking_basis: "fine-tuned on human similarity; newer, growing adoption"
ref: "Fu et al. 2023"
---

# dreamsim

**Use as:** measured-metric (human-aligned image distance)

dreamsim(a,b) as a human-aligned distance

