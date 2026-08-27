"""Run a race with no window - used to tune the field and check lap times."""
import sys, time, argparse
sys.path.insert(0, '.')
from llmrace.track import Track
from llmrace.race import Race, FINISHED
from llmrace.drivers import ROSTER


def run(laps=3, dt=1/60, limit=400.0, verbose=True):
    track = Track()
    race = Race(track, laps=laps, countdown=False)
    t0 = time.perf_counter()
    steps = 0
    off = {c.entry.key: 0 for c in race.cars}
    while race.state != FINISHED and race.time < limit:
        race.update(dt)
        steps += 1
        for c in race.cars:
            if not c.on_road:
                off[c.entry.key] += 1
    wall = time.perf_counter() - t0
    if verbose:
        print(f"sim {race.time:6.1f}s race in {wall:.2f}s wall "
              f"({steps/max(wall,1e-9):.0f} steps/s, {steps} steps)")
        print(f"{'pos':>3} {'model':18s} {'laps':>4} {'race':>8} {'best lap':>9} "
              f"{'avg spd':>8} {'off-track':>9}")
        for c in race.standings():
            best = f"{c.best_lap:.2f}s" if c.best_lap else "   -"
            rt = f"{c.finish_time:.2f}s" if c.finish_time else f"{race.time:.1f}s*"
            avg = c.total_distance / max(race.time, 1e-9)
            print(f"{c.race_position:>3} {c.name:18s} {c.lap:>4} {rt:>8} {best:>9} "
                  f"{avg:7.0f}  {off[c.entry.key]/max(steps,1)*100:7.1f}%")
    return race


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--laps", type=int, default=3)
    ap.add_argument("--limit", type=float, default=400.0)
    run(**vars(ap.parse_args()))
