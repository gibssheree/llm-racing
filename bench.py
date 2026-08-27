"""Solo hot-lap benchmark for every model. Used to balance the field."""
import sys, math
sys.path.insert(0, '.')
from llmrace.track import Track
from llmrace.race import Race
from llmrace.drivers import ROSTER


def bench(laps=4, limit=150.0):
    track = Track()
    rows = []
    for e in ROSTER:
        r = Race(track, [e], laps=laps, countdown=False)
        c = r.cars[0]
        mx = off = n = 0
        slip = 0.0
        while r.time < limit and c.lap < laps:
            r.update(1 / 60)
            n += 1
            mx = max(mx, c.speed)
            slip = max(slip, c.slip_ratio)
            if not c.on_road:
                off += 1
        rows.append({"e": e, "best": c.best_lap or 99.0, "max": mx,
                     "off": off / max(n, 1) * 100, "slip": slip,
                     "avg": c.total_distance / max(r.time, 1e-9),
                     "laps": c.lap})
    rows.sort(key=lambda d: d["best"])
    b = rows[0]["best"]
    print(f"{'model':18s} {'best lap':>9} {'gap':>6} {'avg':>5} {'max':>5} {'%top':>5} {'off%':>6} {'slip':>6}")
    for d in rows:
        e = d["e"]
        print(f"{e.name:18s} {d['best']:8.2f}s {d['best']-b:+5.2f} {d['avg']:5.0f} "
              f"{d['max']:5.0f} {d['max']/e.chassis.top_speed*100:4.0f}% {d['off']:5.1f}% {d['slip']:6.3f}")
    print(f"\nfield spread: {rows[-1]['best']-b:.2f}s ({(rows[-1]['best']/b-1)*100:.1f}%)")
    return rows


if __name__ == "__main__":
    bench()
