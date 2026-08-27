"""Run a full race and report the things that make it a race: passes, gaps."""
import sys
sys.path.insert(0, '.')
from llmrace.track import Track
from llmrace.tracks import by_key as track_by_key, DEFAULT
from llmrace.race import Race, FINISHED


def run(laps=None, limit=200.0, show=True, track_key=None):
    preset = track_by_key(track_key) if track_key else DEFAULT
    track = Track(preset.control)
    laps = laps or preset.laps
    race = Race(track, laps=laps, countdown=False)
    prev = {c.entry.key: c.race_position for c in race.cars}
    passes = []
    while race.state != FINISHED and race.time < limit:
        race.update(1 / 60)
        for c in race.cars:
            if c.race_position < prev[c.entry.key] and not c.finished:
                passes.append((race.time, c.name, prev[c.entry.key], c.race_position))
            prev[c.entry.key] = c.race_position
    if show:
        print(f"{'pos':>3} {'model':18s} {'race':>8} {'best':>8} {'gap':>7}")
        lead = race.standings()[0]
        for c in race.standings():
            gap = (c.finish_time - lead.finish_time) if c.finish_time and lead.finish_time else 0
            print(f"{c.race_position:>3} {c.name:18s} {c.finish_time or 0:7.2f}s "
                  f"{c.best_lap or 0:7.2f}s {gap:+6.2f}s")
        print(f"\nposition changes: {len(passes)}")
        for t, n, a, b in passes[:20]:
            print(f"  {t:6.2f}s  {n:18s} P{a} -> P{b}")
        if len(passes) > 20:
            print(f"  ... and {len(passes)-20} more")
    return race, passes


if __name__ == "__main__":
    run()
