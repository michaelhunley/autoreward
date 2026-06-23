# Use cases: how to derive the right gauge

Real, abstracted examples of turning "is this good?" into a trustworthy gauge.
Each strips the domain specifics and keeps the transferable pattern: the problem,
the objective, why the obvious metric failed, and how the correct gauge was
derived. These are the kinds of entries the gauge library generalizes - the
recurring shapes of "the naive metric lied, here is the one that didn't."

---

## 1. The averaged metric that hid a systematic defect
- **Problem:** an output looked clearly wrong - a uniform wash over the whole
  thing - yet a per-element mean-error metric against a reference scored it "close."
- **Objective:** judge perceptual fidelity to a reference.
- **Why it failed:** mean absolute error averages over a uniform shift, so a defect
  present *everywhere* is nearly invisible to it.
- **Deriving the gauge:** find the DIMENSION the defect actually changes. The wash
  lowered color saturation and local contrast, so the gauge became "saturation +
  contrast vs the reference," not mean error.
- **Tier:** Measured (computable distance to a reference).
- **Takeaway:** pick the metric that lives in the same dimension as your failure
  mode. A global average hides systematic shifts, and an output a human would
  reject must move your number.

## 2. The "maximize" that secretly rewarded destroying the goal
- **Problem:** optimizing "make the subject fill the frame" produced framings that
  cropped the subject.
- **Objective:** maximize subject resolution WHILE keeping the whole subject present.
- **Why it failed:** pure maximization had a hidden failure mode - more fill tips
  into clipping.
- **Deriving the gauge:** express it as a CONSTRAINED objective - reward = fill
  fraction, but only if the subject touches no frame edge; otherwise heavily
  penalized.
- **Tier:** Measured.
- **Takeaway:** when "more is better" can destroy the objective, encode the
  constraint INTO the gauge instead of trusting the bare maximize.

## 3. The learned proxy fooled by a trivial input
- **Problem:** a learned similarity/identity model (a Predicted proxy) gave near-perfect
  scores to blank/empty outputs.
- **Objective:** judge whether an output matches a target using a human-judgment proxy.
- **Why it failed:** the proxy was never meant for degenerate inputs - empty-vs-empty
  reads as "identical."
- **Deriving the gauge:** pair the proxy with an orthogonal VALIDITY check (does the
  output actually contain content?) and only score valid outputs.
- **Tier:** Predicted, with a Measured-style cross-check.
- **Takeaway:** no gauge alone. Pair every proxy with an orthogonal check aimed at
  its specific blind spot.

## 4. Two gauges that each crowned the wrong winner
- **Problem:** a "coverage/solidity" gauge ranked a correct-but-sparse result below a
  wrong-but-dense one; a separate "fidelity" gauge ignored shape entirely.
- **Objective:** judge a result that must be BOTH complete and correctly shaped.
- **Deriving the gauge:** combine orthogonal terms (coverage AND shape/structure),
  because optimizing either alone has a cheap degenerate winner.
- **Tier:** Measured.
- **Takeaway:** if a single gauge has an easy way to win that isn't the goal, it
  needs a second, orthogonal term.

## 5. The per-element outlier audit that also redirected the diagnosis
- **Problem:** a composite looked degraded; suspicion fell on a subset of bad elements.
- **Objective:** QA many elements for local consistency and fix the bad ones.
- **Deriving the gauge:** score each element against its local-neighborhood median
  (distance plus a domain-specific test). That flagged candidates. The decisive
  step was then testing whether FIXING the flagged elements moved the global quality
  number - it did not, which proved the defect was downstream (in how elements were
  combined), not in the elements themselves.
- **Tier:** Measured.
- **Takeaway:** a per-element gauge does double duty - it finds candidates, and by
  checking whether fixing them moves the global metric, it tells you whether you are
  even looking in the right place.

## 6. Localizing a loss by instrumenting stage boundaries
- **Problem:** quality was lost somewhere in a multi-stage pipeline; which stage was
  unclear.
- **Objective:** pinpoint the stage that introduces the defect.
- **Deriving the gauge:** measure the SAME target property at each stage boundary -
  e.g., the value stored after stage N vs the value produced by stage N+1. The stage
  where the number drops is the culprit.
- **Tier:** Measured.
- **Takeaway:** instrument stage boundaries with one consistent gauge to localize,
  instead of guessing which stage is at fault.

## 7. The decomposition gauge that disproved the obvious story
- **Problem:** a transformed/animated output looked like the wrong components were
  responding.
- **Objective:** verify a transformation affects the right components in the right way.
- **Deriving the gauge:** decompose into named components and measure each one's
  behavior against the EXPECTED pattern (which components should change a lot vs stay
  stable). The measurement contradicted the visual assumption and redirected the
  whole investigation.
- **Tier:** Measured.
- **Takeaway:** turn "it looks like X is broken" into a per-component measurement
  against an expected profile. The eye misattributes causes.

---

## The common thread
In every case the naive metric either hid the defect, rewarded a degenerate winner,
or got fooled. The fix was always the same three moves:
1. Measure the dimension the failure actually lives in.
2. Anchor to a reference or an expected pattern where possible (Measured tier).
3. Pair the gauge with an orthogonal cross-check.

When you cannot yet do Measured, a Predicted proxy plus a validity cross-check beats
eyeballing (Reviewed) - and every Reviewed pass becomes the labeled data that builds
Predicted and Measured.
