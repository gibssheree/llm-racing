"""Generate the car design brief that gets sent to each language model.

The brief is written straight out of llmrace/spec.py, so it cannot describe a
parameter the game does not have, or quote a range the validator will reject.

    python brief.py                 # one brief per car on the grid
    python brief.py --key claude    # just that one
    python brief.py --blank         # a generic brief, no model named
"""
import argparse
import os
import sys
import json

sys.path.insert(0, '.')
from llmrace import spec
from llmrace.drivers import ROSTER, by_key
from llmrace.tracks import PRESETS

OUT_DIR = "briefs"


def fmt(v):
    if isinstance(v, int) or (isinstance(v, float) and float(v).is_integer()):
        return str(int(v))
    return f"{v:g}"


def param_table(group):
    rows = ["| field | range | unit | cost | what it does |",
            "|---|---|---|---|---|"]
    for p in spec.group_params(group):
        if p.choices:
            rng = " / ".join(str(c) for c in p.choices)
        else:
            rng = f"{fmt(p.lo)} .. {fmt(p.hi)}"
        cost = "free" if p.cost == 0 else f"{fmt(p.cost)}"
        if p.cost and not p.higher_is_better:
            cost += " (lower costs more)"
        rows.append(f"| `{p.name}` | {rng} | {p.unit} | {cost} | {p.what} |")
    return "\n".join(rows)


def circuits_table():
    rows = ["| circuit | length | tightest corner | flat out | direction changes |",
            "|---|---|---|---|---|"]
    for t in PRESETS:
        s = t.stats or {}
        rows.append(f"| {t.name} | {s.get('length',0):.0f} px | "
                    f"{s.get('min_radius',0):.0f} px radius | "
                    f"{s.get('flat_out',0)*100:.0f}% | {s.get('turns',0)} |")
    return "\n".join(rows)


def response_template():
    car = spec.reference_car()
    body = {"spec_version": spec.SPEC_VERSION,
            "car_name": "<a name for your car>",
            "tagline": "<one line, under 60 characters>",
            "reasoning": "<2-4 sentences: what kind of car did you build, and why>"}
    body.update(car)
    return json.dumps(body, indent=2)


HEADER = """# LLM Grand Prix — car design brief

**You are designing a racing car.** It will be simulated against six cars designed
the same way by other language models, on six circuits, and the results are
published. Everything below is real: these numbers are fed straight into a
physics engine and a neural-network driver, and nothing else about your car is
decided by anyone but you.

Read the whole brief, then reply with **one JSON object and nothing else**.

---

## The game

Top-down 2D racing, 7 cars, no human drivers. Every car is driven by a small
feed-forward neural network that sees the world through a fan of range sensors
and outputs a steering command and a target speed. No car knows the layout of
the circuit or follows a stored racing line — it reacts to what it can see, at
60Hz, and that is all.

You are choosing three things at once:

1. **The chassis** — the physical car. Power, grip, brakes, steering, mass.
2. **The brain** — the gains inside that car's driving network.
3. **The temper** — how it behaves under pressure. Reaction lag, jitter, aggression.

---

## The physics you are designing against

Units are pixels and seconds throughout. Roughly 7px is a metre; the road is
240px wide; cars are 34px long.

**Straight-line speed.** Resistance is calibrated so full throttle always
settles exactly on your `top_speed`. `drag` only shapes how quickly you get
there — it cannot raise or lower the ceiling.

**Cornering.** Turning the wheel points the tyres somewhere new; the tyres then
have to drag the car's existing momentum around, and they can only pull so
hard. When a corner demands more lateral acceleration than `grip` allows, the
excess appears as a slide. Effective grip rises with speed:

    grip_effective = grip * (1 + downforce * (speed / top_speed)^2)

Off the road, grip collapses to 42% and drag climbs sharply.

**The speed a corner allows.** For a road of half-width `w`, the sensor ray
pointing straight ahead reaches about `sqrt(2*R*w)` around a bend of radius `R`.
So `R ~ d^2 / 2w`, and the grip-limited corner speed `sqrt(grip*R)` works out
**proportional to how far ahead the car can see**. The driving network uses
exactly this relationship, scaled by `sqrt(grip) / top_speed`. A grippier car
therefore genuinely commits to faster corners — grip is not just physics, it
changes the decisions your driver makes.

**Steering.** Authority falls away with speed:

    yaw_rate = steer_rate / (1 + steer_falloff * (speed / top_speed))

which is why a very fast car cannot also turn in sharply, and why braking zones
matter.

---

## What your driver can see

A symmetric fan of `sensor_count` rays, spanning 78 degrees either side of the
nose, each measuring how far the road runs in that direction, out to
`sensor_range`. Rival cars are measured on a **separate channel**, because a
wall ahead means brake and a car ahead means find a way past.

Readings are normalised against what each ray would reach on a straight road,
so the network reads *deviation from straight* rather than raw geometry. Only
the two or three rays nearest the nose can see far enough to report how far the
road actually continues; everything wider just measures the width. That is why
`sensor_range` matters more than it looks.

---

## The circuits

Your car races all six. Design for the calendar, not for one track.

{circuits}

---

## The design budget

You have **{budget:.0f} points**. If every field were set to its most expensive
value the total would be 100, so you can afford roughly {pct:.0f}% of a perfect
car and must decide where it goes.

Cost is linear across each field's range: at the cheap end a field costs 0, at
the expensive end it costs the full amount listed, and halfway costs half. For
fields marked *lower costs more* the expensive end is the low end — a quick
`reaction` costs points, a slow one is free.

For reference, the seven factory cars currently on the grid spend between
**39.5** and **59.8** points, and they are separated by under a second a lap.
Spending everything is not the same as being quick.

---

## Chassis

{chassis}

## Brain

The gains that go into the driving network. Most are free: they decide the
*character* of the driving rather than buying performance, and the extremes are
genuinely bad in both directions.

{brain}

## Temper

{temper}

## Sensors

{sensors}

---

## What actually wins

Honest notes from balancing this grid, so you are not designing blind.

- **Grip is the most valuable stat.** Five of the six circuits are corner-dominated.
  It is priced accordingly.
- **`top_speed` is a trap on most of the calendar.** Only Token Speedbowl is
  44% flat out; Gradient Descent is 17%. A very fast car with weak grip is slow.
- **`confidence` is free, and that is not generosity.** Set it too high and the
  car overdrives, slides, and loses more time than it gains. There is a real
  optimum and it is near 1.0 for a well-balanced car.
- **Overtaking is decided by `avoidance` and `aggression`.** A car sitting
  directly behind a rival gives up 12-20% of its target speed until it moves
  more than 34px offline. If it never pulls out, it never passes.
- **`damping` and `noise` decide whether a slide is recoverable.** A car with
  low `damping`, low `recovery` and high `noise` will be spectacular and slow.
- **You cannot buy your way out of a bad shape.** A car that spends everything
  on power and top speed and nothing on grip is comfortably last.

---

## Reply format

Reply with **one JSON object and nothing else** — no prose before or after, no
markdown fence. Every field below is required. Numbers, not strings.

```json
{template}
```

Your submission is rejected if any field is missing, out of range, or if the
total spend exceeds {budget:.0f} points. Pick whatever you like for `car_name`
and `tagline`; `reasoning` is for the write-up and does not affect the car.
"""


def build(entry=None):
    intro = ""
    if entry is not None:
        intro = (f"\n> **Entrant:** {entry.name} ({entry.vendor}).\n"
                 f"> Your car runs in {entry.livery} as car "
                 f"#{[e.key for e in ROSTER].index(entry.key) + 1}.\n"
                 f"> You are designing for yourself — this is your entry.\n")
    body = HEADER.format(
        circuits=circuits_table(),
        budget=spec.BUDGET,
        pct=spec.BUDGET,
        chassis=param_table("chassis"),
        brain=param_table("brain"),
        temper=param_table("temper"),
        sensors=param_table("sensors"),
        template=response_template())
    head, rest = body.split("\n---\n", 1)
    return head + intro + "\n---\n" + rest


def main(argv=None):
    ap = argparse.ArgumentParser(description="generate car design briefs")
    ap.add_argument("--key", help="only this entrant")
    ap.add_argument("--blank", action="store_true",
                    help="a generic brief with no entrant named")
    ap.add_argument("--out", default=OUT_DIR)
    args = ap.parse_args(argv)

    os.makedirs(args.out, exist_ok=True)
    if args.blank:
        targets = [None]
    elif args.key:
        targets = [by_key(args.key)]
    else:
        targets = list(ROSTER)

    for entry in targets:
        name = "blank" if entry is None else entry.key
        path = os.path.join(args.out, f"{name}.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(build(entry))
        print(f"wrote {path}  ({os.path.getsize(path)/1024:.1f} KB)")
    print(f"\nsend one file to each model. collect the JSON it replies with, "
          f"save it as garage/<key>.json, then:  python submit.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
