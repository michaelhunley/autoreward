# What is a Jacobian? (a plain-language explainer)

autoreward's `descent` driver (see [DESCENT.md](DESCENT.md)) leans on a thing called the **Jacobian**.
The word sounds scary; the idea is simple.

## The one-sentence version

A Jacobian is a **sensitivity table**: for every *knob* you can turn and every *thing you measure*,
it says **"if I nudge this knob a little, how much does this measurement move, and which way?"**

## The mixing-board picture

Imagine a sound mixing board. You have **sliders** (knobs) and **VU meters** (measurements). Push one
slider and *several* meters twitch — by different amounts, some up, some down. A slider isn't wired to
exactly one meter; it bleeds into a few.

The Jacobian is the chart of that bleed:

|                    | slider: sun brightness | slider: sun angle | slider: fill light |
|--------------------|-----------------------:|------------------:|-------------------:|
| meter: warmth      |                  +0.02 |             +0.10 |              +0.30 |
| meter: highlights  |                  +0.40 |             +0.25 |              −0.05 |
| meter: shadows     |                  −0.30 |             +0.15 |              +0.60 |

Each number is a **slope**: "per unit of slider, this meter moves this much." Positive = up,
negative = down, big = strong effect, ~0 = that slider barely touches that meter. (In math notation
each cell is `∂measurement / ∂knob`, but it's just "rise over run" — how fast the meter changes as
you move the knob.)

## Why it's useful

Our optimizer's job: get every meter to its **target** (match the reference look). Without the table,
it's trial-and-error — push a slider, re-check every meter, guess again. Slow, and it fights itself
(fixing one meter breaks another).

**With** the table, you can do the smart thing. You know how far each meter is from target (the "gap")
and you know how each slider moves each meter (the Jacobian). So you can **solve for the exact slider
moves** that close all the gaps at once — a small bit of linear algebra (weighted least-squares):

```
knob_moves  =  solve( Jacobian · knob_moves ≈ gaps )
```

That's the **Gauss-Newton** step in `descent`: one calculated move toward the answer instead of a
hundred nudges. When meters conflict (no move satisfies all), the math finds the best compromise.

## Two ways to get the table — and why it matters

- **Numerical (measure it live):** nudge each slider a hair, watch the meters, record the slopes.
  Honest, needs no prior knowledge — but it costs **one render per knob every time**, and on a noisy
  engine the measured slopes wobble.
- **Learned (fit it from history):** you've logged thousands of "I moved this knob, these meters
  changed" events. Fit those into the table once. Now the optimizer reads the slopes **for free** at
  run time, and they're **averaged over lots of data** so they're stable and correct.
- **Guessed (hand-written):** someone writes the table from intuition. Fast to start, but if the
  guesses are wrong the optimizer marches **confidently in the wrong direction** — worse than not
  having a table at all. (We learned this the hard way: a hand-guessed table made the fancy optimizer
  do *worse* than the simple one on the real engine.)

## The punchline

The optimizer is only as smart as its Jacobian. A **good** table = it walks straight to the target
in a handful of steps. So the highest-value thing you can do is **learn the table from real data**
(or measure it around a known-good result), not guess it. That's why ground-truth examples are for
*training the table*, not for solving any single run.

*In `descent`: pass `jacobian={(feature, knob): slope, ...}` to use a learned table (no per-run
perturbation cost); omit it to measure the table numerically.*
