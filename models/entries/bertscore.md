---
id: "bertscore"
modality: "text"
encodes: "semantic token alignment ~ human similarity to a reference text"
use_as: "C-metric (semantic distance to a reference)"
domains_strong: [summary/translation vs reference]
domains_weak: [no-reference quality, factuality]
ranking_score: 4
ranking_basis: "better human correlation than ROUGE/BLEU"
ref: "Zhang et al. 2020"
---

# bertscore

**Use as:** C-metric (semantic distance to a reference)

bertscore(candidate, reference)

