"""Auto-balance the grid across every circuit.

Every model keeps its own character - top speed, power, brakes, sensors and
temperament are exactly as authored. The only thing searched is `confidence`,
which is literally how much corner speed that model believes its own car can
carry.

Balancing on one circuit does not transfer: a setting that is quick round the
Autodrome puts a loose chassis in the grass at Gradient Descent. So a candidate
has to keep the car on the road on *all four* tracks before its pace counts.

Run:  python balance.py
"""
import sys
import copy
import statistics

sys.path.insert(0, '.')
from llmrace.track import Track
from llmrace.race import Race
from llmrace.drivers import ROSTER
from llmrace.tracks import PRESETS

TARGET = None             # None = median of the field as authored
TOLERANCE = 0.15          # laps within this of target count as equally good
MAX_OFF = 2.0             # percent of a lap in the grass before it is rejected
LAPS = 2
CONF_LO, CONF_HI = 0.78, 1.30
STEPS = 11


def solo(track, entry, laps=LAPS, limit=70.0):
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


def across(tracks, entry):
    """(mean lap, worst off-track %, worst slip) over every circuit."""
    laps, offs, slips = [], [], []
    for t in tracks:
        lap, off, slip = solo(t, entry)
        laps.append(lap)
        offs.append(off)
        slips.append(slip)
    return statistics.mean(laps), max(offs), max(slips)


def with_confidence(entry, k):
    e = copy.deepcopy(entry)
    e.brain.confidence = round(k, 4)
    return e


def solve(tracks, entry, target):
    ok = []
    for i in range(STEPS):
        k = CONF_LO + (CONF_HI - CONF_LO) * i / (STEPS - 1)
        lap, off, slip = across(tracks, with_confidence(entry, k))
        if lap >= 99.0 or off > MAX_OFF:
            continue
        ok.append((abs(lap - target), slip, k, lap, off))
    if not ok:
        return CONF_LO, None
    close = [c for c in ok if c[0] <= TOLERANCE]
    # Several settings hit the target; take the tidiest, so that how much a car
    # slides comes from its chassis rather than from an artefact of this search.
    pick = min(close, key=lambda c: c[1]) if close else min(ok, key=lambda c: c[0])
    return pick[2], pick


if __name__ == "__main__":
    tracks = [Track(p.control) for p in PRESETS]
    print(f"balancing across {len(tracks)} circuits: "
          + ", ".join(p.name for p in PRESETS))
    base = {e.key: across(tracks, e) for e in ROSTER}
    target = TARGET or round(statistics.median(v[0] for v in base.values() if v[0] < 99), 2)
    print(f"target mean lap {target:.2f}s\n")
    print(f"{'model':18s} {'was':>7} {'off':>6} {'conf':>6} {'now':>7} {'off':>6} {'slip':>6}")
    out = []
    for e in ROSTER:
        k, pick = solve(tracks, e, target)
        lap, off, slip = across(tracks, with_confidence(e, k))
        b = base[e.key]
        print(f"{e.name:18s} {b[0]:6.2f}s {b[1]:5.1f}% {k:6.3f} "
              f"{lap:6.2f}s {off:5.1f}% {slip:6.3f}")
        out.append((e.key, round(k, 3)))
    print("\nCONFIDENCE = {")
    for key, k in out:
        print(f"    {key!r}: {k},")
    print("}")
