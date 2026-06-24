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

## How autoresearch actually works (the connection point)

autoresearch is an **agentic loop**, not a function you call. An LLM agent edits a
single experiment script (`train.py` in the original - "architecture,
hyperparameters, optimizer... everything is fair game"), runs it for a few minutes,
**reads ONE scalar metric the run reports** (`val_bpb`, where **lower is better**),
and keeps or discards the change. The "tuning variable" is whatever your script
exposes; the "objective" is simply the number your run prints. So you do not swap a
library call - **you change WHAT your run reports and tell the agent to optimize it.**

## Wiring (the contract)

1. **Pick/build a gauge** for your goal (see `gauges/by-goal.md`): a callable
   `gauge(candidate, target=None) -> float`.
2. **Make your experiment report the gauge as its headline metric**, matching
   autoresearch's **lower-is-better** convention - report a LOSS, not a reward:
   ```python
   from integrations.autoresearch_bridge import register, loss
   register("my_gauge", my_gauge, higher_is_better=True)   # if it's a quality score
   print(f"val_metric: {loss('my_gauge', candidate, target):.6f}")   # lower = better
   ```
   `loss()` is `-reward()`, so a higher-quality candidate prints a LOWER number -
   exactly what a val_bpb-style minimizing loop wants. (If your gauge is already a
   distance where lower=better, register it with `higher_is_better=False` and
   `loss()` passes it through.)
3. **Point the agent at that metric.** In autoresearch's task/config, set the
   objective to the scalar your run prints (replace its `val_bpb` target with your
   `val_metric`). The agent now edits the experiment to drive your gauge down.
4. **Keep humans in the loop sparingly (the ratchet).** Every N rounds, spot-check
   the top candidate by hand (Reviewed tier). If a Predicted proxy disagrees with
   humans, lower its `ranking_score` and add the evidence - this stops proxy drift.
   And **cross-check the gauge**: if the metric drops while the result looks wrong,
   the gauge is being gamed - pair it with an orthogonal gauge (per the README).

## Why this matters

A loop is only as good as its reward. autoresearch proved the loop works with a
clean metric; autoreward is what lets you point that loop at "is this render a
match / the same character / good?" without falling back to eyeballing. Run
`python integrations/autoresearch_bridge.py` for a tiny working example.
