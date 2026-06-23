# Schemas

## Gauge entry (`gauges/examples/*.json`)

A gauge is one way to answer "is this good?" for a specific workflow goal.

```json
{
  "id": "string - unique slug",
  "workflow_goal": "one-line description of what is being judged",
  "domain": "e.g. 3d-reconstruction | image-gen | text | code | animation | audio",
  "tier": "measured | predicted | reviewed",
  "target": "the known-good reference (measured) | the preference data/model (predicted) | who reviews (reviewed)",
  "metric": "the computable distance or score, named precisely",
  "threshold": "pass/fail rule, e.g. 'interior_frac < 0.30' or 'cosine > 0.8'",
  "model": "model id from models/index.json if the metric uses one, else null",
  "cross_check": "an orthogonal gauge that catches this one being fooled",
  "fooled_by": "known failure mode(s) - how a bad result can still pass",
  "ratchet": "if predicted/reviewed, what data this run produces to move toward measured next time",
  "example_values": "real numbers seen, e.g. 'crisp 0.23, diffuse 0.58'",
  "source": "where this gauge came from / reference"
}
```

Tier is chosen by the Measured > Predicted > Reviewed rule: use Measured if a
target+metric can be defined; else Predicted if a proxy model/data exists; else
Reviewed.

## Model index entry (`models/index.json`)

A model that encodes human responses and can serve as a Predicted-tier proxy (or
power a Measured metric, e.g. a perceptual-feature distance).

```json
{
  "id": "string",
  "modality": "image | image-text | video | text | audio | 3d | motion",
  "encodes": "what human responses it was trained on / approximates",
  "use_as": "predicted-proxy (preference/quality score) | measured-metric (feature distance to a target)",
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
- **1** — anecdotal; treat as Reviewed-tier assistance, not a gauge.
