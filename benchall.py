"""Every model, every circuit. The check that nothing is undriveable."""
import sys
sys.path.insert(0, '.')
from llmrace.track import Track
from llmrace.race import Race
from llmrace.drivers import ROSTER
from llmrace.tracks import PRESETS


def solo(track, entry, laps=2, limit=140.0):
    r = Race(track, [entry], laps=laps, countdown=False)
    c = r.cars[0]
    off = n = 0
    slip = 0.0
    while r.time < limit and c.lap < laps:
        r.update(1 / 60)
        n += 1
        slip = max(slip, c.slip_ratio)
        if not c.on_road:
            off += 1
    return (c.best_lap or 99.0), off / max(n, 1) * 100, slip


if __name__ == "__main__":
    bad = 0
    for p in PRESETS:
        track = Track(p.control)
        rows = sorted((solo(track, e) + (e.name,)) for e in ROSTER)
        spread = rows[-1][0] - rows[0][0]
        print(f"\n{p.name:20s} {p.stats['length']:.0f}px  spread {spread:5.2f}s")
        for lap, off, slip, name in rows:
            flag = "" if (lap < 99 and off < 3) else "   <-- problem"
            if flag:
                bad += 1
            print(f"   {name:18s} {lap:6.2f}s  off {off:4.1f}%  slip {slip:.2f}{flag}")
    print(f"\n{bad} problem entries")
