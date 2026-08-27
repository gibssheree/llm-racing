"""Write llmrace/tracks.py from the repaired layouts plus their descriptions."""
import sys, json
sys.path.insert(0, '.')
from tracksearch import metrics, legal

META = [
    ("autodrome", "Vector Autodrome",
     "Long straight, esses down the right, a proper hairpin before the pits."),
    ("speedbowl", "Token Speedbowl",
     "Two enormous straights joined by a hairpin at each end. Bring top speed."),
    ("technical", "Gradient Descent",
     "An infield knot. Chicane, hairpin, esses, and almost nowhere to rest."),
    ("endurance", "Context Window",
     "The longest lap here. Wide sweepers, a stadium section, one heavy stop."),
    ("street", "Backprop Street",
     "Angular street circuit. Long drags into near right-angle corners."),
    ("twinloop", "Attention Heads",
     "Two big loops pinched together in the middle. Rhythm is everything."),
]

HEAD = '''"""Circuit presets.

Every layout was drawn by hand for a silhouette - a hairpin is a hairpin
because the points double back - and then passed through ``tracksearch.repair``,
which nudges whatever is illegal by the smallest amount that makes it
driveable. That is why they have distinct shapes rather than the rounded blobs
a blind search kept producing.

Regenerate with:  python repair_all.py && python gen_tracks.py
"""
from dataclasses import dataclass


@dataclass
class TrackPreset:
    key: str
    name: str
    blurb: str
    control: list
    laps: int = 3
    stats: dict = None


PRESETS = [
'''

TAIL = ''']


def preview_points(control, samples=14):
    """Cheap centreline sampling for menu thumbnails.

    Deliberately does not build a Track: that rasterises a tarmac bitmap, and
    the track picker only needs a shape to draw.
    """
    n = len(control)
    pts = []
    for i in range(n):
        p0, p1 = control[(i - 1) % n], control[i]
        p2, p3 = control[(i + 1) % n], control[(i + 2) % n]
        for s in range(samples):
            t = s / samples
            t2, t3 = t * t, t * t * t
            pts.append((
                0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t
                       + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                       + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3),
                0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t
                       + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                       + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)))
    return pts


def by_key(key):
    for t in PRESETS:
        if t.key == key:
            return t
    raise KeyError(key)


DEFAULT = PRESETS[0]
'''

TARGET_RACE = 62.0      # seconds of racing we want a default distance to give


def main():
    fixed = json.load(open("layouts_fixed.json"))
    out = [HEAD]
    print(f"{'track':20s} {'len':>6} {'minR':>6} {'clear':>6} {'flat':>6} "
          f"{'tight':>6} {'swaps':>6} {'laps':>5}")
    for key, name, blurb in META:
        cp = [tuple(p) for p in fixed[key]]
        m = metrics(cp)
        # roughly 300px/s average, so pick a distance that lasts about a minute
        laps = max(2, min(6, round(TARGET_RACE / (m["len"] / 300.0))))
        flag = "" if legal(cp) else "   <-- ILLEGAL"
        print(f"{name:20s} {m['len']:6.0f} {m['minR']:6.0f} {m['clear']:6.0f} "
              f"{m['flat']*100:5.1f}% {m['hairpin']*100:5.1f}% {m['turns']:6d} "
              f"{laps:5d}{flag}")
        pts = ",\n            ".join(
            ", ".join(f"({x}, {y})" for x, y in cp[i:i + 4]) + ","
            for i in range(0, len(cp), 4))
        out.append(f'''    TrackPreset(
        key="{key}", name="{name}",
        blurb="{blurb}",
        laps={laps},
        stats={{"length": {m['len']:.0f}, "min_radius": {m['minR']:.0f},
               "flat_out": {m['flat']:.3f}, "turns": {m['turns']}}},
        control=[
            {pts}
        ]),
''')
    out.append(TAIL)
    open("llmrace/tracks.py", "w", encoding="utf-8").write("".join(out))
    print("\nwrote llmrace/tracks.py")


if __name__ == "__main__":
    main()
