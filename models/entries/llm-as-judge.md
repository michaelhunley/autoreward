---
id: "llm-as-judge"
modality: "text"
encodes: "approximates an expert rater via instructions + few-shot"
use_as: "B-proxy (flexible expert-ish judgment)"
domains_strong: [open-ended quality with a rubric, pairwise preference]
domains_weak: [position/verbosity bias, self-preference, calibration drift]
ranking_score: 3
ranking_basis: "flexible and strong with a good rubric; biased - audit + cross-check"
ref: "Zheng et al. 2023 (MT-Bench)"
---

# llm-as-judge

**Use as:** B-proxy (flexible expert-ish judgment)

judge(rubric, item) -> score/preference; debias with pairwise + swaps

