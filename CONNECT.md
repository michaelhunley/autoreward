# Connecting autoreward to an autonomous loop (autoresearch)

[karpathy/autoresearch](https://github.com/karpathy/autoresearch) is the *loop*:
an agent proposes changes, runs a short experiment, and keeps what improves a
scalar metric. autoreward is the *reward*: it supplies that scalar for subjective
domains where no metric is handed to you. Together = an RLAIF loop.

## One-command setup

```bash
bash install.sh /path/to/your/project --with-autoresearch
#  - injects the Measured/Predicted/Reviewed policy into your CLAUDE.md
#  - clones karpathy/autoresearch next to autoreward
#  - prints the wiring below
```

## Wiring (the contract)

1. **Pick/build a gauge** for your goal (see `gauges/by-goal.md`). It must be a
   callable `gauge(candidate, target=None) -> float`.
2. **Register it as the reward** via the bridge:
   ```python
   from integrations.autoresearch_bridge import register, reward, best_of
   register("my_gauge", my_gauge)          # higher_is_better=True for a score
   r = reward("my_gauge", candidate, target)   # the loop MAXIMIZES r
   ```
3. **Make it the loop's objective.** autoresearch optimizes `val_bpb`; replace that
   read with `reward("my_gauge", candidate, target)` so the loop selects the
   candidate your gauge says is best.
4. **Keep humans in the loop sparingly (the ratchet).** Every N rounds, spot-check
   the top candidate by hand (Reviewed tier). If a Predicted proxy disagrees with humans,
   lower its `ranking_score` and add the evidence — this stops reward-hacking and
   proxy drift.

## Why this matters

A loop is only as good as its reward. autoresearch proved the loop works with a
clean metric; autoreward is what lets you point that loop at "is this render a
match / the same character / good?" without falling back to eyeballing. Run
`python integrations/autoresearch_bridge.py` for a tiny working example.
