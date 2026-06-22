---
id: "identity-match"
workflow_goal: "A reconstructed/generated/posed character is recognizably the SAME character as a reference (not just 'a person')."
domain: "3d-reconstruction | image-gen"
tier: "C"
target: "ground-truth render of the reference character from the SAME camera/pose"
metric: "perceptual-feature cosine between the candidate render and the GT render, cropped to the subject (ArcFace for faces; CLIP/DreamSim for whole-character); evaluated across several poses"
threshold: "domain-calibrated; track the gap to the GT-vs-GT self-similarity ceiling, not an absolute number"
model: "arcface | clip | dreamsim"
cross_check: "MUST render candidate and GT from the SAME pose/camera - misaligned views tank the score artificially and a single matching view can hide holes; check multiple poses"
fooled_by: "camera/pose misalignment (false negative); a blob that overlaps one silhouette (false positive on a single view)"
ratchet: "n/a (already C); if no GT render exists, drop to B (a preference model) and log human 'same/different' calls to build the GT set"
example_values: "a blobby reconstruction scores low vs a recognizable one - but only when candidate and GT cameras are aligned"
source: "a character-reconstruction project - replaced 'does it look like them?' (tier A on a video) with a per-pose number"
---

# identity-match

A reconstructed/generated/posed character is recognizably the SAME character as a reference (not just 'a person').

