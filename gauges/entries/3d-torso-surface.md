---
id: "3d-torso-surface"
workflow_goal: "A 3D reconstruction (e.g. a gaussian splat) of a clothed torso is a tight SURFACE, not a fuzzy filled volume (which renders faint/translucent)."
domain: "3d-reconstruction"
tier: "measured"
target: "a real surface = a thin shell; quantify relative to a crisp reference reconstruction vs a known-bad (diffuse) one"
metric: "torso cross-section interior-fraction: take torso primitives (by bone), PCA to the body's vertical axis, project the cross-section, fraction with radial distance < 0.5 * p90-radius. Low = hollow shell (surface); high = filled volume."
threshold: "interior_frac < 0.30 = crisp surface"
model: "None"
cross_check: "render the reconstruction from a held-out view; a surface renders solid, a volume renders faint - and individual-primitive stats (opacity/flatness) can look identical while the spatial distribution differs"
fooled_by: "a height-band slice (instead of by-bone parts) catches the arms at torso height and reads falsely crisp - select by semantic part, not raw height"
ratchet: "n/a (already C)"
example_values: "illustrative: ~0.23 interior = crisp shell; ~0.58 = diffuse volume"
source: "a 3D character-reconstruction project - this gauge distinguished a usable from an unusable pipeline in minutes, after days of 'the render looks off' (Reviewed tier) getting nowhere"
---

# 3d-torso-surface

A 3D reconstruction (e.g. a gaussian splat) of a clothed torso is a tight SURFACE, not a fuzzy filled volume (which renders faint/translucent).

