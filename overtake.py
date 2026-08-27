"""Measure whether the racing is actually close.

Counts genuine position changes - the first few seconds are skipped, because
seven cars leaving a standing grid swap places constantly without anybody
overtaking anybody - and reports how strung out the field is at the flag.
"""
import sys
sys.path.insert(0, '.')
from llmrace.track import Track
from llmrace.race import Race, FINISHED
from llmrace.tracks import PRESETS

SETTLE = 4.0


def race_once(preset, laps=None, limit=400.0):
    track = Track(preset.control)
    race = Race(track, laps=laps or preset.laps, countdown=False)
    prev = {c.entry.key: c.race_position for c in race.cars}
    passes = 0
    while race.state != FINISHED and race.time < limit:
        race.update(1 / 60)
        if race.time < SETTLE:
            prev = {c.entry.key: c.race_position for c in race.cars}
            continue
        for c in race.cars:
            if c.race_position < prev[c.entry.key] and not c.finished:
                passes += 1
            prev[c.entry.key] = c.race_position
    order = race.standings()
    win, last = order[0], order[-1]
    spread = ((last.finish_time or race.time) - (win.finish_time or race.time))
    return passes, spread, win.name, race.time


if __name__ == "__main__":
    tot_p = tot_s = 0.0
    print(f"{'circuit':20s} {'passes':>7} {'1st to last':>12} {'winner':>18}")
    for p in PRESETS:
        passes, spread, win, t = race_once(p)
        tot_p += passes
        tot_s += spread
        print(f"{p.name:20s} {passes:7d} {spread:11.2f}s {win:>18}")
    n = len(PRESETS)
    print(f"\n{'AVERAGE':20s} {tot_p/n:7.1f} {tot_s/n:11.2f}s")
