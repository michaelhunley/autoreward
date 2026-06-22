---
id: "rlhf-reward-model"
modality: "text"
encodes: "human preference between responses"
use_as: "B-proxy (text quality/helpfulness reward)"
domains_strong: [response preference ranking, RLHF/RLAIF reward]
domains_weak: [factuality, reward hacking under optimization]
ranking_score: 4
ranking_basis: "core of RLHF; strong but gameable under heavy optimization"
ref: "Ouyang et al. 2022"
---

# rlhf-reward-model

**Use as:** B-proxy (text quality/helpfulness reward)

reward(prompt, response)

