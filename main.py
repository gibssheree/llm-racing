"""LLM Grand Prix - entry point.

    python main.py                 3-lap race, full grid
    python main.py --laps 5
    python main.py --only claude gpt grok llama
    python main.py --track technical --laps 5
"""
import argparse
import sys

from llmrace import config as cfg
from llmrace.drivers import ROSTER, by_key
from llmrace.game import Game
from llmrace.menu import MIN_CARS
from llmrace.tracks import PRESETS


def main(argv=None):
    ap = argparse.ArgumentParser(description="LLM Grand Prix")
    ap.add_argument("--laps", type=int, default=None,
                    help="override the circuit's default race distance")
    ap.add_argument("--track", metavar="KEY",
                    help="start on a circuit, e.g. --track technical")
    ap.add_argument("--only", nargs="+", metavar="KEY",
                    help="race a subset, e.g. --only claude grok gemini")
    ap.add_argument("--list", action="store_true", help="list model keys and exit")
    args = ap.parse_args(argv)

    if args.list:
        print("cars:")
        for e in ROSTER:
            print(f"  {e.key:12s} {e.name:20s} {e.vendor}")
        print("circuits:")
        for t in PRESETS:
            print(f"  {t.key:12s} {t.name:20s} {t.laps} laps   {t.blurb}")
        return 0

    entries = [by_key(k) for k in args.only] if args.only else None
    if entries is not None and len(entries) < MIN_CARS:
        ap.error(f"--only needs at least {MIN_CARS} cars")
    Game(laps=args.laps and max(1, args.laps), entries=entries,
         track_key=args.track).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
