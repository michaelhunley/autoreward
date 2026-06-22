#!/usr/bin/env python3
# (autoreward) RUNNABLE PROOF of value - no IP, numpy only.
#
# The core claim: validating quality by eyeballing (tier A) or by a naive metric
# is unreliable; the RIGHT tier-C gauge (target-anchored, structure/perception
# aware) makes the correct call. Here a trivial 2-pixel shift tanks PSNR while a
# detail-destroying blur scores BETTER on PSNR - so PSNR (and "looks sharp")
# pick the wrong candidate. A structure-aware gauge picks the faithful one.
#
# Run:  python demos/naive_metric_fooled.py
import numpy as np

rng = np.random.default_rng(0)
H = W = 128
target = np.zeros((H, W))
target[::8, :] = 1.0          # grid edges = real high-frequency structure
target[:, ::8] = 1.0
target = np.clip(target + 0.25 * rng.standard_normal((H, W)), 0, 1)

def box_blur(x, k=7):
    pad = k // 2
    xp = np.pad(x, pad, mode="reflect")
    out = np.zeros_like(x)
    for i in range(k):
        for j in range(k):
            out += xp[i:i + H, j:j + W]
    return out / (k * k)

A_blur = box_blur(target, 7)          # detail DESTROYED (a human sees this as worse)
B_shift = np.roll(target, 2, axis=1)  # sharp, shifted 2px (a human sees ~identical)

def psnr(a, b):
    m = float(np.mean((a - b) ** 2))
    return 99.0 if m == 0 else 10 * np.log10(1.0 / m)

def edge_energy(x):
    return float(np.mean(np.hypot(*np.gradient(x))))

et = edge_energy(target)
def structure_score(x):               # shift-invariant, blur-sensitive; higher=better
    return -abs(edge_energy(x) - et)

pa, pb = psnr(target, A_blur), psnr(target, B_shift)
sa, sb = structure_score(A_blur), structure_score(B_shift)

print("Candidate A = heavy blur (detail destroyed)   |  Candidate B = sharp, shifted 2px")
print(f"  PSNR (naive C / proxy for 'looks clean'):  A={pa:5.1f} dB   B={pb:5.1f} dB"
      f"   -> picks {'A (blur) - WRONG' if pa > pb else 'B'}")
print(f"  structure gauge (right tier-C):            A={sa:6.3f}     B={sb:6.3f}"
      f"   -> picks {'B (sharp) - RIGHT' if sb > sa else 'A'}")
print()
print("Lesson: a naive metric mis-ranks (a 2px shift wrecks PSNR; blur 'wins' by")
print("smoothing error) and eyeballing can't tell either. The framework's value is")
print("choosing a target-anchored, structure/perception-aware gauge AND a cross-check.")
print("In production use LPIPS / DreamSim (human-aligned, models/index.json) as the C")
print("metric, with a second gauge as the cross-check.")
