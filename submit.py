"""Check the cars that came back from the models, and see if they are any good.

Put each model's reply in garage/<key>.json, then:

    python submit.py                 # check and simulate everything in the garage
    python submit.py --key claude    # just that one
    python submit.py --race          # also run a full race of the new grid
    python submit.py --report        # write garage/report.md to send back

A submission is validated against llmrace/spec.py, priced against the budget,
then driven solo on every circuit. The report is the feedback a model needs to
revise its design, so it is written to be pasted straight back to it.
"""
import argparse
import os
import sys

sys.path.insert(0, '.')
from llmrace import garage, spec
from llmrace.drivers import ROSTER, by_key
from llmrace.race import Race, FINISHED
from llmrace.track import Track
from llmrace.tracks import PRESETS


def solo(track, entry, laps=2, limit=160.0):
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


def shake_down(entry, tracks):
    rows = []
    for preset, track in tracks:
        lap, off, slip = solo(track, entry)
        rows.append((preset.name, lap, off, slip))
    return rows


def spend_breakdown(values):
    out = []
    for group in spec.GROUPS:
        pts = sum(spec.BY_NAME[p.name].points(values[p.name])
                  for p in spec.group_params(group) if p.name in values)
        out.append((group, pts))
    return out


def check_one(key, record, tracks, factory):
    values, meta, problems, cost = record
    name = meta.get("car_name") or key
    print(f"\n{'=' * 66}")
    print(f"{key}  ->  {name}")
    if meta.get("tagline"):
        print(f"  \"{meta['tagline']}\"")
    print(f"{'=' * 66}")

    if problems:
        print(f"  REJECTED - {len(problems)} problem(s):")
        for p in problems:
            print(f"    - {p}")
        if cost > spec.BUDGET + spec.TOLERANCE and values:
            # Show where the money went, so the reply can be pasted straight
            # back to the model instead of it having to guess what to cut.
            over = cost - spec.BUDGET
            print("")
            print("  --- paste this back to the model ---")
            print(f"  Your car spends {cost:.1f} of the {spec.BUDGET:.0f} point "
                  f"budget, so it is rejected.")
            print(f"  You need to free up at least {over:.1f} points. Your "
                  f"biggest line items are:")
            top = sorted(((spec.BY_NAME[k].points(v), k, v) for k, v in values.items()
                          if spec.BY_NAME[k].cost > 0), reverse=True)[:6]
            for pts, k, v in top:
                par = spec.BY_NAME[k]
                cheap = par.lo if par.higher_is_better else par.hi
                print(f"    {k} = {v:g} costs {pts:.1f} pts "
                      f"(range {par.lo:g}..{par.hi:g}, free end is {cheap:g})")
            print(f"  Resend the full JSON with the same format.")
            print(f"  ------------------------------------")
        return None

    print(f"  spend {cost:.1f} / {spec.BUDGET:.0f} points"
          f"   ({spec.BUDGET - cost:+.1f} left)")
    for group, pts in spend_breakdown(values):
        print(f"    {group:9s} {pts:5.1f}")

    entry = garage.apply_values(factory, values, meta.get("car_name"),
                                meta.get("tagline"))
    rows = shake_down(entry, tracks)
    mean = sum(r[1] for r in rows) / len(rows)
    worst_off = max(r[2] for r in rows)
    mean_slip = sum(r[3] for r in rows) / len(rows)

    print(f"\n  {'circuit':22s} {'best lap':>9} {'off-track':>10} {'slide':>7}")
    for cname, lap, off, slip in rows:
        flag = "  <-- undriveable" if (lap >= 99 or off > 5) else ""
        print(f"  {cname:22s} {lap:8.2f}s {off:9.1f}% {slip:7.2f}{flag}")
    print(f"  {'MEAN':22s} {mean:8.2f}s {worst_off:9.1f}% {mean_slip:7.2f}")

    verdict = []
    if worst_off > 5:
        verdict.append("spends too long off the road - overdriven, or short of "
                       "grip/damping/recovery")
    if mean_slip > 0.7:
        verdict.append("slides almost everywhere - lower confidence or buy grip")
    elif mean_slip < 0.05:
        verdict.append("never troubles the tyres - there is probably free lap "
                       "time in more confidence")
    if cost < spec.BUDGET - 8:
        verdict.append(f"{spec.BUDGET - cost:.0f} points left unspent")
    if verdict:
        print("\n  notes:")
        for v in verdict:
            print(f"    - {v}")
    return {"key": key, "name": name, "entry": entry, "cost": cost,
            "mean": mean, "off": worst_off, "slip": mean_slip, "rows": rows,
            "meta": meta}


def full_race(results, tracks):
    """Race whatever is in the garage against whatever is not."""
    grid = []
    swapped = {r["key"]: r["entry"] for r in results}
    for e in ROSTER:
        grid.append(swapped.get(e.key, e))
    print(f"\n{'=' * 66}")
    print("RACE - the garage against the factory")
    print(f"{'=' * 66}")
    for preset, track in tracks:
        race = Race(track, grid, laps=preset.laps, countdown=False)
        while race.state != FINISHED and race.time < 400:
            race.update(1 / 60)
        order = race.standings()
        win = order[0]
        print(f"\n{preset.name}")
        for c in order:
            tag = "*" if c.entry.key in swapped else " "
            gap = ("winner" if c is win else
                   (f"+{c.finish_time - win.finish_time:.2f}s"
                    if c.finish_time and win.finish_time else "not classified"))
            print(f"  {tag} P{c.race_position} {c.name:22s} {gap:>15}")
    print("\n  * = designed by a model, from the garage")


def write_report(results, path="garage/report.md"):
    lines = ["# LLM Grand Prix — submission report", "",
             f"Budget {spec.BUDGET:.0f} points. Solo shake-down, two laps of each "
             "circuit, no traffic.", "",
             "| car | spend | mean lap | worst off-track | mean slide |",
             "|---|---|---|---|---|"]
    for r in sorted(results, key=lambda r: r["mean"]):
        lines.append(f"| {r['name']} | {r['cost']:.1f} | {r['mean']:.2f}s | "
                     f"{r['off']:.1f}% | {r['slip']:.2f} |")
    for r in sorted(results, key=lambda r: r["mean"]):
        lines += ["", f"## {r['name']}  (`{r['key']}`)", "",
                  "| circuit | best lap | off-track | slide |", "|---|---|---|---|"]
        for cname, lap, off, slip in r["rows"]:
            lines.append(f"| {cname} | {lap:.2f}s | {off:.1f}% | {slip:.2f} |")
        if r["meta"].get("reasoning"):
            lines += ["", f"> {r['meta']['reasoning']}"]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"\nwrote {path}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="check cars designed by models")
    ap.add_argument("--key", help="only this entrant")
    ap.add_argument("--dir", default=garage.GARAGE_DIR)
    ap.add_argument("--race", action="store_true", help="also run a full race")
    ap.add_argument("--report", action="store_true", help="write garage/report.md")
    args = ap.parse_args(argv)

    subs = garage.load_all(args.dir)
    if args.key:
        subs = {k: v for k, v in subs.items() if k == args.key}
    if not subs:
        print(f"nothing in {args.dir}.")
        print("Run 'python brief.py', send each briefs/<key>.md to its model,")
        print("then save the JSON it replies with as garage/<key>.json.")
        return 1

    tracks = [(p, Track(p.control)) for p in PRESETS]
    factory = {e.key: e for e in ROSTER}
    results = []
    for key, record in subs.items():
        if key not in factory:
            print(f"\n{key}: no entrant with that key - "
                  f"expected one of {', '.join(factory)}")
            continue
        got = check_one(key, record, tracks, factory[key])
        if got:
            results.append(got)

    print(f"\n{'=' * 66}")
    print(f"{len(results)} of {len(subs)} submissions accepted")
    if results and args.race:
        full_race(results, tracks)
    if results and args.report:
        write_report(results)
    return 0 if results else 1


if __name__ == "__main__":
    sys.exit(main())
