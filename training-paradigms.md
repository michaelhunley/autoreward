# DPO, GRPO, PPO — and where autoreward fits

Fine-tuning a model to produce better outputs requires a signal that says "better."
In coding or math, that signal is easy: the tests pass or they don't. In creative,
visual, or domain-specific work, it isn't obvious — "better" means something a human
(or a stand-in for a human) has to judge. This is exactly the gap autoreward fills.

This document explains the three main paradigms for preference-driven fine-tuning,
what reward signal each one needs, and how to use autoreward's tools to produce
that signal without bottlenecking on human annotation.

---

## The common problem: where does "better" come from?

All three paradigms need you to answer "which output is better?" or "how good is
this output?" — just in different forms.

| Paradigm | What it needs | What autoreward provides |
|----------|--------------|--------------------------|
| **DPO** | Pairs: (prompt, chosen output, rejected output) | Gauges that rank any two outputs automatically |
| **GRPO** | A scalar score per output, per prompt | Gauges as the reward function |
| **PPO** | A reward model that scores any output | Gauge = the reward model (Measured tier) or trains the reward model (Predicted tier labels) |

In domains where you can define a target — "this is what a good render looks like,"
"this is the canonical correct answer" — autoreward's **Measured tier** eliminates
the need for human annotation entirely. In domains where no single target exists,
the **Predicted tier** (a model trained on human responses) provides scalable scoring.
**Reviewed** (human judgment) remains the ground truth but is reserved for
calibration and final sign-off, not per-sample labeling.

---

## DPO — Direct Preference Optimization

### What it is

DPO fine-tunes a model on preference pairs rather than on scalar rewards. For each
prompt you provide two outputs — one the model should prefer ("chosen"), one it
should prefer less ("rejected") — and DPO adjusts the model's weights so it assigns
higher probability to the chosen output.

The key insight behind DPO: you can bypass training a separate reward model and
the expensive PPO loop entirely. The policy update is derived directly from the
preference pairs via a contrastive loss.

```
Training data shape:
  [prompt, chosen_output, rejected_output]
  [prompt, chosen_output, rejected_output]
  ...
```

### What you need from autoreward

**Pair generation without human labeling.** For each prompt, generate N candidate
outputs and score them with your gauge. The highest-scoring output is "chosen"; any
lower-scoring one is "rejected." One gauge call per output, and you have training
data.

```python
from autoreward.integrations.autoresearch_bridge import register, reward

def my_gauge(output, reference):
    """Measured: distance between output features and reference. Lower = better."""
    return feature_distance(extract_features(output), extract_features(reference))

register("quality", my_gauge)   # lower = better (distance)

# For each prompt:
outputs = generate_N_candidates(prompt, n=8)
scores  = [reward("quality", o, reference) for o in outputs]   # higher = better match
chosen  = outputs[scores.index(max(scores))]
rejected = outputs[scores.index(min(scores))]
# -> preference pair (prompt, chosen, rejected)
```

**Calibrate the signal before you scale it.** Run a sample of pairs through human
review (Reviewed tier) to confirm your gauge's ranking agrees with human preference.
If the gauge ranks "bright but detail-free" above "correctly lit with texture," it
will produce pairs that teach the model the wrong lesson at scale. One Reviewed pass
per gauge type is sufficient to catch this.

**Multi-objective pairs.** A scalar gauge can produce "chosen" outputs that are
good on one dimension and fail on another. If your quality definition has multiple
characteristics, generate a RewardVector per output and pick the pair by
maximin score — the chosen output must be the best on its worst characteristic,
not just the best on average:

```python
from autoreward.reward_vector import compute_reward_vector
from autoreward.optimizer import best_by_maximin, Node

def score_output(output, reference, char_map):
    return compute_reward_vector(extract_features(output), extract_features(reference), char_map)

rvs = [score_output(o, reference, char_map) for o in outputs]
nodes = [Node(candidate=o, rv=rv, depth=0) for o, rv in zip(outputs, rvs)]
chosen  = best_by_maximin(nodes).candidate
worst   = min(nodes, key=lambda n: n.rv.min_score()).candidate
# -> preference pair where "chosen" is balanced across all characteristics
```

---

## GRPO — Group Relative Policy Optimization

### What it is

GRPO (used in DeepSeek-R1 and related models) generates a *group* of candidate
outputs for the same prompt, scores each one, and trains the model to assign higher
probability to outputs that scored above the group average.

The "group relative" part means no absolute threshold is needed — the model learns
from the distribution of quality within each batch. An output that scores 0.7 when
the group average is 0.5 is a winner; the same 0.7 score when the group average is
0.9 is a loser.

```
For each prompt:
  1. Generate group of N outputs
  2. Score each: [r1, r2, r3, ..., rN]
  3. Advantage of output i = ri - mean(r1..rN)
  4. Update policy: increase probability of outputs with positive advantage
```

### What you need from autoreward

**A scalar reward function.** This is the simplest fit: your gauge IS the reward
function for step 2. The group-relative calculation happens in your training code,
not in autoreward.

```python
from autoreward.integrations.autoresearch_bridge import register, reward

register("render_quality", perceptual_gauge, higher_is_better=True)

def grpo_reward(prompt, output):
    reference = get_reference(prompt)
    return reward("render_quality", output, reference)

# In your GRPO training loop:
outputs    = generate_group(prompt, n=8)
rewards    = [grpo_reward(prompt, o) for o in outputs]
mean_r     = sum(rewards) / len(rewards)
advantages = [r - mean_r for r in rewards]
# -> train with policy gradient using advantages
```

**Use a Measured gauge when you can.** GRPO is particularly sensitive to reward
hacking because the model sees many samples of the same reward signal during
training. A Measured gauge (computed distance to a reference) is much harder to
hack than a Predicted proxy, because the model cannot overfit to the proxy's biases
— it has to actually get closer to the target. If your domain has a reference,
define the gauge at the Measured tier.

**GRPO with a reward vector.** Standard GRPO trains on a scalar advantage. To train
on multiple characteristics simultaneously, run GRPO independently on each
characteristic's score and sum the advantages (or use the maximin score as the
scalar to keep the worst characteristic from being ignored):

```python
from autoreward.reward_vector import compute_reward_vector

def grpo_reward_vector(prompt, output, char_map):
    current = extract_features(output)
    target  = extract_features(get_reference(prompt))
    return compute_reward_vector(current, target, char_map)

# Per-group:
rvs     = [grpo_reward_vector(prompt, o, char_map) for o in outputs]
scalars = [rv.scalar("min") for rv in rvs]          # maximin scalar
mean_s  = sum(scalars) / len(scalars)
advantages = [s - mean_s for s in scalars]
# -> train on maximin advantage: forces the policy to fix the weakest characteristic
```

Alternatively, compute a separate advantage per characteristic and train with a
multi-head advantage — but scalar-maximin is simpler and often sufficient.

**Watch the group size.** GRPO needs enough diversity within a group to produce
a meaningful mean. A group of N=2 is unstable. N=8–16 is typical. If your measure
function is expensive (a real render takes seconds), autoreward's Predicted-tier
models let you score cheaply in-loop and reserve Measured for the final GRPO batch.

---

## PPO — Proximal Policy Optimization

### What it is

PPO is the classic RLHF loop: train a reward model on human-labeled preference
pairs, then optimize the policy against that reward model using the PPO algorithm.
More infrastructure than DPO or GRPO — a separate reward model to train and
maintain — but the pattern that first produced GPT-4-class alignment results.

```
1. Collect human preference pairs: (prompt, chosen, rejected)
2. Train a reward model on those pairs
3. Generate outputs with the current policy
4. Score each output with the reward model
5. Update the policy with PPO to maximize expected reward
6. Repeat from 3
```

### What you need from autoreward

**Two modes: replace or feed.**

**Mode 1 — Replace the reward model (Measured tier).** If your domain has a
computable target, a Measured gauge can substitute for a trained reward model
entirely. The gauge takes an output and a reference and returns a scalar. This
removes the expense of training and maintaining a reward model:

```python
def reward_model(output, reference):
    """Measured gauge as reward model: no training required."""
    return 1.0 - feature_distance(extract_features(output), extract_features(reference))
```

This works whenever the quality you want to optimize can be expressed as "how
close is this output to a known-good reference?" — which is more domains than
people assume, because references can be computed, synthesized, or derived from
existing good examples.

**Mode 2 — Feed the reward model (Predicted tier).** When no target exists and
you must train a reward model, autoreward's Predicted-tier model index
(`models/index.json`) lists models pre-trained on human responses by domain. These
serve as:
- The reward model directly, avoiding training from scratch.
- The label source for your own reward model — score outputs with the proxy, treat
  those scores as labels, train a lightweight project-specific reward model on them.

```python
# Use an existing Predicted proxy directly as PPO reward model
from imagereward import ImageReward   # see models/entries/imagereward.md
reward_model = ImageReward.load("ImageReward-v1.0")
score = reward_model.score(prompt, output)
```

**Mode 3 — Bootstrap from Reviewed.** For domains where no Predicted proxy exists
yet: run a small Reviewed batch (human labels on 200–500 pairs), train a lightweight
reward model on them, and use autoreward's Ratchet — every subsequent Reviewed pass
adds more labeled data, improving the reward model over time. The cost of Reviewed
annotation falls each cycle because the reward model takes on more of the scoring.

---

## The reward quality ceiling

All three paradigms share a ceiling: **the policy can only be as good as the reward
signal.** A reward signal that can be gamed produces a policy that games it. A
reward signal that correlates poorly with what you actually want produces a policy
that does what you actually don't want.

This is why autoreward's framework matters for fine-tuning, not just for
autoresearch-style optimization loops:

- **Measured > Predicted > Reviewed** is the hierarchy for reliability — place your
  gauge at the highest tier the domain allows, and keep it there.
- **No gauge trusted alone** — the cross-check rule is especially important in
  training, where a gamed reward signal runs for thousands of steps before you notice.
  Pair every training reward with an orthogonal validation gauge that isn't used to
  compute gradients.
- **Multi-objective reward** prevents the policy from learning to sacrifice one
  characteristic for another. A GRPO policy trained on a scalar that averages
  "dramatic" and "detail-preserving" learns to be dramatic AND lose detail. A
  maximin scalar or a per-characteristic advantage keeps both characteristics in play.
- **The ratchet in training** — every human review of a model output is labeled
  data. Log it. It builds the Predicted proxy that replaces the next Reviewed batch.
  Applied to fine-tuning, this means each generation of a trained model improves the
  reward signal for the next generation.

---

## Quick-start by paradigm

### DPO
```python
# 1. Define a gauge
from autoreward.integrations.autoresearch_bridge import register, reward
register("quality", your_gauge, higher_is_better=True)

# 2. Generate pairs
outputs = generate_N(prompt, n=8)
scores  = [reward("quality", o, ref) for o in outputs]
chosen, rejected = outputs[scores.index(max(scores))], outputs[scores.index(min(scores))]
# -> (prompt, chosen, rejected) to your DPO trainer
```

### GRPO
```python
# 1. Same gauge as your GRPO reward function
from autoreward.integrations.autoresearch_bridge import reward
grpo_rewards = [reward("quality", o, ref) for o in group_outputs]
mean_r = sum(grpo_rewards) / len(grpo_rewards)
advantages = [r - mean_r for r in grpo_rewards]
# -> to your GRPO policy gradient update
```

### GRPO (multi-objective / maximin)
```python
from autoreward.reward_vector import compute_reward_vector
rvs = [compute_reward_vector(extract_features(o), target_features, char_map) for o in group_outputs]
scalars = [rv.scalar("min") for rv in rvs]   # maximin: worst characteristic drives the loss
mean_s  = sum(scalars) / len(scalars)
advantages = [s - mean_s for s in scalars]
```

### PPO (Measured gauge as reward model)
```python
from autoreward.integrations.autoresearch_bridge import reward
ppo_reward = lambda output: reward("quality", output, reference)
# -> drop into your PPO training loop as the reward function
```

---

## Further reading

- [`README.md`](README.md) — the tier system, scalar gauges, and multi-objective optimizer
- [`CONNECT.md`](CONNECT.md) — wiring autoreward to karpathy/autoresearch
- [`use-cases.md`](use-cases.md) — worked examples of building gauges that don't lie
- [`models/index.json`](models/index.json) — Predicted-tier models by domain and reliability
- [`gauges/by-goal.md`](gauges/by-goal.md) — gauge templates by workflow goal
