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
from llmrace import config as cfg
from llmrace.track import Track
from llmrace.ai import build_brain, Vision, N_EXTRA_FEATURES, REF_GRIP, REF_TOP_SPEED
from llmrace.drivers import ROSTER
from llmrace.tracks import PRESETS


def reference_entry():
    """A clean reference car, so the fit is self-consistent.

    The head's coefficients are quoted per unit of `confidence * phys`, and
    phys is 1.0 only when grip and top_speed match the reference chassis. Using
    a car off the grid - especially one designed by a model - silently folded
    its own grip and bravery into the constants.
    """
    import copy
    e = copy.deepcopy(ROSTER[0])
    e.chassis.grip = REF_GRIP
    e.chassis.top_speed = REF_TOP_SPEED
    e.brain.confidence = 1.0
    e.sensor_count = 9
    e.sensor_range = cfg.SENSOR_RANGE
    return e


def main():
    e = reference_entry()
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
    # ordinary least squares on a single predictor - closed form, no numpy
    n = len(targets)
    xs = [r[0] for r in rows]
    mx = sum(xs) / n
    my = sum(targets) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, targets))
    slope = sxy / sxx
    intercept = my - slope * mx
    coef = (slope, intercept)
    pred = [slope * x + intercept for x in xs]
    rms = math.sqrt(sum((p - y) ** 2 for p, y in zip(pred, targets)) / n)
    worst = max(abs(p - y) for p, y in zip(pred, targets))
    print(f"fitted over {n} samples on {len(PRESETS)} circuits")
    print(f"  frac = {coef[0]:.3f}*h2 {coef[1]:+.3f}")
    print(f"  rms  = {rms:.4f}   max = {worst:.4f}")
    print(f"  predicted {min(pred):.2f}..{max(pred):.2f}  "
          f"ideal {min(targets):.2f}..{max(targets):.2f}")
    print()
    print("in llmrace/ai.py build_brain():")
    print(f"    net.w2[1][2] = {coef[0] / e.brain.confidence:.2f} * b.confidence * phys")
    print(f"    net.b2[1] = {coef[1]:.2f} * phys")


if __name__ == "__main__":
    main()
