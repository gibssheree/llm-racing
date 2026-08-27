"""Re-fit the network's target-speed head to the current track geometry.

The head is linear because safe corner speed really is proportional to how far
the nose ray reaches: for a road of half-width w, that ray runs about
sqrt(2*R*w) round a bend of radius R, so R ~ d^2/2w and the grip-limited speed
sqrt(grip*R) comes out as d * sqrt(grip/2w).

Change the road width or the circuit and that constant of proportionality
moves, so the two coefficients in build_brain() have to be refitted. This
prints the replacements.
"""
import sys
import math

sys.path.insert(0, '.')
import numpy as np

from llmrace.track import Track
from llmrace.ai import build_brain, Vision, N_EXTRA_FEATURES
from llmrace.drivers import by_key
from llmrace.tracks import PRESETS

REF = "claude"          # the chassis the head is fitted against


def main():
    e = by_key(REF)
    net = build_brain(e)
    rows, targets = [], []
    for preset in PRESETS:
        t = Track(preset.control)
        v = Vision(e.sensor_count, e.sensor_range, t.half_width)
        k = math.sqrt(e.chassis.grip / (2 * t.half_width))
        pad = [0.0] * e.sensor_count
        for i in range(t.sample_count()):
            d = t.raycast(*t.center[i], *t.tangent[i])
            ideal = min(1.12, 0.90 * e.brain.confidence * k * d / e.chassis.top_speed)
            s = v.scan(t, *t.center[i], t.heading_at(i))
            net.forward(list(s) + pad + [0.8, 0.0, 0.0, 0.0, 0.0][:N_EXTRA_FEATURES])
            rows.append([net.hidden[2], 1.0])
            targets.append(ideal)
    A, Y = np.array(rows), np.array(targets)
    coef, *_ = np.linalg.lstsq(A, Y, rcond=None)
    pred = A @ coef
    print(f"fitted over {len(Y)} samples on {len(PRESETS)} circuits")
    print(f"  frac = {coef[0]:.3f}*h2 {coef[1]:+.3f}")
    print(f"  rms  = {np.sqrt(((pred - Y) ** 2).mean()):.4f}   max = {np.abs(pred - Y).max():.4f}")
    print(f"  predicted {pred.min():.2f}..{pred.max():.2f}  ideal {Y.min():.2f}..{Y.max():.2f}")
    print()
    print("in llmrace/ai.py build_brain():")
    print(f"    net.w2[1][2] = {coef[0] / e.brain.confidence:.2f} * b.confidence * phys")
    print(f"    net.b2[1] = {coef[1]:.2f} * phys")


if __name__ == "__main__":
    main()
