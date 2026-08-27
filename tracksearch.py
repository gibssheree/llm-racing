"""Author circuits, then check and repair them.

Hand-placed control points keep producing corners tighter than the road is
wide, or sections of track that run into each other. Rather than search for a
layout blindly - which only ever produced rounded blobs - this takes a shape
somebody actually drew and nudges it the smallest amount needed to make it
legal, so the intended silhouette survives.
"""
import sys
import math
import random

sys.path.insert(0, '.')
from llmrace.track import Track
from llmrace import config as cfg

MIN_RADIUS = 145.0      # tight enough for a real hairpin at a 100px half width
MIN_CLEAR = 252.0       # 2 * half width + room for a car between two straights
MARGIN = 46.0
SEP = 26                # samples apart before two bits of track count as separate


def radii(t):
    return [1.0 / k if k > 1e-9 else 1e9 for k in t.curvature]


def clearance(t):
    """Closest approach between two non-adjacent parts of the circuit.

    Uses a spatial hash; the naive all-pairs version is far too slow to sit
    inside a repair loop.
    """
    pts = t.center
    m = len(pts)
    cell = MIN_CLEAR
    grid = {}
    for i, (x, y) in enumerate(pts):
        grid.setdefault((int(x // cell), int(y // cell)), []).append(i)
    worst, pair = 1e9, None
    for i, (x, y) in enumerate(pts):
        cx, cy = int(x // cell), int(y // cell)
        for gx in range(cx - 1, cx + 2):
            for gy in range(cy - 1, cy + 2):
                for j in grid.get((gx, gy), ()):
                    if j <= i:
                        continue
                    if j - i < SEP or m - (j - i) < SEP:
                        continue
                    d = math.dist(pts[i], pts[j])
                    if d < worst:
                        worst, pair = d, (i, j)
    return worst, pair


def metrics(control):
    t = Track(control)
    m = t.sample_count()
    rs = radii(t)
    clear, pair = clearance(t)
    xs = [p[0] for p in t.left + t.right]
    ys = [p[1] for p in t.left + t.right]
    fwd = [t.raycast(*t.center[i], *t.tangent[i]) for i in range(m)]
    hair = sum(1 for r in rs if r < 260) / m
    return {
        "track": t, "minR": min(rs), "clear": clear, "pair": pair,
        "len": t.length, "flat": sum(1 for d in fwd if d >= 559) / m,
        "corner": sum(1 for c in t.corner if c > 0.0016) / m,
        "hairpin": hair, "turns": direction_changes(t),
        "x0": min(xs), "y0": min(ys), "x1": max(xs), "y1": max(ys),
    }


def direction_changes(t):
    """How many times the circuit swaps from turning left to turning right.

    A high count is what makes a lap feel varied rather than like one long oval.
    """
    m = len(t.center)
    sign = 0
    flips = 0
    run = 0
    for i in range(m):
        a = t.tangent[(i - 3) % m]
        b = t.tangent[(i + 3) % m]
        cross = a[0] * b[1] - a[1] * b[0]
        s = 1 if cross > 4e-3 else (-1 if cross < -4e-3 else 0)
        if s == 0:
            continue
        if s != sign:
            run += 1
            if run > 5:          # ignore jitter, count a settled change
                flips += 1
                sign = s
                run = 0
        else:
            run = 0
    return flips


def penalty(control):
    """How illegal is this layout, plus how far it drifted from the drawing."""
    # no tarmac bitmap: rasterising one per candidate makes repair ~5x slower
    # and nothing in here casts a ray
    t = Track(control, build_mask=False)
    p = 0.0
    for r in radii(t):
        if r < MIN_RADIUS:
            p += (MIN_RADIUS - r) ** 2
    clear, _ = clearance(t)
    if clear < MIN_CLEAR:
        p += (MIN_CLEAR - clear) ** 2 * 4.0
    xs = [q[0] for q in t.left + t.right]
    ys = [q[1] for q in t.left + t.right]
    for over in (MARGIN - min(xs), MARGIN - min(ys),
                 max(xs) - (cfg.WORLD_W - MARGIN), max(ys) - (cfg.WORLD_H - MARGIN)):
        if over > 0:
            p += over ** 2 * 4.0
    return p


def legal(control):
    m = metrics(control)
    return (m["minR"] >= MIN_RADIUS and m["clear"] >= MIN_CLEAR
            and m["x0"] >= MARGIN and m["y0"] >= MARGIN
            and m["x1"] <= cfg.WORLD_W - MARGIN and m["y1"] <= cfg.WORLD_H - MARGIN)


def repair(control, iters=500, seed=5, drift=0.03):
    """Nudge control points until the layout is legal, staying near the original."""
    rng = random.Random(seed)
    origin = [tuple(p) for p in control]

    def cost(cp):
        dev = sum(math.dist(a, b) ** 2 for a, b in zip(cp, origin))
        return penalty(cp) + dev * drift

    cur = [list(p) for p in control]
    best = cost([tuple(p) for p in cur])
    amp = 55.0
    for _ in range(iters):
        if penalty([tuple(p) for p in cur]) <= 0.0:
            break
        cand = [list(p) for p in cur]
        for _ in range(rng.randint(1, 3)):
            k = rng.randrange(len(cand))
            cand[k][0] += rng.gauss(0, amp)
            cand[k][1] += rng.gauss(0, amp)
        c = cost([tuple(p) for p in cand])
        if c < best:
            best, cur = c, cand
        amp = max(9.0, amp * 0.995)
    return [(round(p[0]), round(p[1])) for p in cur]


def report(name, control):
    m = metrics(control)
    ok = "OK " if legal(control) else "BAD"
    print(f"{ok} {name:20s} len={m['len']:5.0f} minR={m['minR']:5.0f} "
          f"clear={m['clear']:5.0f} flat={m['flat']*100:4.1f}% corner={m['corner']*100:4.1f}% "
          f"tight={m['hairpin']*100:4.1f}% swaps={m['turns']:2d} "
          f"box=({m['x0']:.0f},{m['y0']:.0f})-({m['x1']:.0f},{m['y1']:.0f})")
    return m
