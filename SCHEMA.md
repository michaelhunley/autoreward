# Schemas

## Gauge entry (`gauges/examples/*.json`)

A gauge is one way to answer "is this good?" for a specific workflow goal.

```json
{
  "id": "string - unique slug",
  "workflow_goal": "one-line description of what is being judged",
  "domain": "e.g. 3d-reconstruction | image-gen | text | code | animation | audio",
  "tier": "C | B | A",
  "target": "the known-good reference (C) | the preference data/model (B) | who reviews (A)",
  "metric": "the computable distance or score, named precisely",
  "threshold": "pass/fail rule, e.g. 'interior_frac < 0.30' or 'cosine > 0.8'",
  "model": "model id from models/index.json if the metric uses one, else null",
  "cross_check": "an orthogonal gauge that catches this one being fooled",
  "fooled_by": "known failure mode(s) - how a bad result can still pass",
  "ratchet": "if tier A/B, what data this run produces to move toward C next time",
  "example_values": "real numbers seen, e.g. 'crisp 0.23, diffuse 0.58'",
  "source": "where this gauge came from / reference"
}
```

Tier is chosen by the C>B>A rule: use C if a target+metric can be defined; else B
if a proxy model/data exists; else A.

## Model index entry (`models/index.json`)

A model that encodes human responses and can serve as a tier-B proxy (or power a
C metric, e.g. a perceptual-feature distance).

```json
{
  "id": "string",
  "modality": "image | image-text | video | text | audio | 3d | motion",
  "encodes": "what human responses it was trained on / approximates",
  "use_as": "B-proxy (preference/quality score) | C-metric (feature distance to a target)",
  "domains_strong": ["where it is reliable"],
  "domains_weak": ["where it misleads"],
  "ranking_score": "1-5 reliability as a human proxy in its strong domains",
  "ranking_basis": "why that score - calibration evidence / adoption",
  "how_to_use": "one line on wiring it as a gauge",
  "ref": "paper/repo"
}
```

`ranking_score` rubric:
- **5** — strong published human-correlation + wide adoption + stable.
- **4** — good human-correlation in its domain; some drift/edge cases.
- **3** — useful proxy; correlation domain-specific or partial.
- **2** — weak/indirect proxy; use only with a cross-check.
- **1** — anecdotal; treat as tier-A assistance, not a gauge.
