---
id: "clip"
modality: "image-text"
encodes: "web-scale image-caption association ~ human semantic 'what is this / does it match this description'"
use_as: "C-metric (image/text feature cosine to a target) and weak B-proxy"
domains_strong: [semantic similarity, does-this-look-like-X, text-image match]
domains_weak: [fine identity, fine geometry, small spatial differences]
ranking_score: 4
ranking_basis: "huge adoption; strong semantic correlation, weak on fine detail"
ref: "Radford et al. 2021"
---

# clip

**Use as:** C-metric (image/text feature cosine to a target) and weak B-proxy

cosine of CLIP embeddings of render vs reference render (or text)

