# LLM Grand Prix — car design brief

**You are designing a racing car.** It will be simulated against six cars designed
the same way by other language models, on six circuits, and the results are
published. Everything below is real: these numbers are fed straight into a
physics engine and a neural-network driver, and nothing else about your car is
decided by anyone but you.

Read the whole brief, then reply with **one JSON object and nothing else**.

> **Entrant:** Le Chat Large (Mistral).
> Your car runs in yellow as car #7.
> You are designing for yourself — this is your entry.

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

| circuit | length | tightest corner | flat out | direction changes |
|---|---|---|---|---|
| Vector Autodrome | 7648 px | 161 px radius | 34% | 9 |
| Token Speedbowl | 7004 px | 164 px radius | 44% | 9 |
| Gradient Descent | 7269 px | 159 px radius | 17% | 13 |
| Context Window | 7276 px | 162 px radius | 39% | 11 |
| Backprop Street | 8439 px | 156 px radius | 34% | 7 |
| Attention Heads | 10571 px | 164 px radius | 30% | 9 |

---

## The design budget

You have **60 points**. If every field were set to its most expensive
value the total would be 100, so you can afford roughly 60% of a perfect
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

| field | range | unit | cost | what it does |
|---|---|---|---|---|
| `power` | 240 .. 340 | px/s^2 | 11 | Engine force. How hard it accelerates out of a corner. |
| `top_speed` | 380 .. 460 | px/s | 10 | The limiter. Only pays on the straights. |
| `brake` | 440 .. 620 | px/s^2 | 8 | Stopping power. Decides how late it can brake. |
| `grip` | 200 .. 320 | px/s^2 | 16 | Maximum lateral acceleration before the tyres let go. The most valuable stat on a twisty circuit. |
| `steer_rate` | 2.4 .. 3.6 | rad/s | 7 | Yaw rate at low speed. How sharply it can turn in. |
| `steer_falloff` | 0.4 .. 0.75 | - | 7 (lower costs more) | Steering authority lost as speed rises. Lower is better. |
| `mass` | 0.85 .. 1.2 | x reference | 3 | Inertia in contact. Heavier wins the shove, but buys nothing else. |
| `downforce` | 0.2 .. 0.45 | - | 7 | Extra grip that arrives with speed: grip * (1 + downforce * (v/top)^2). |
| `drag` | 0.88 .. 1.1 | shape | 3 (lower costs more) | How eagerly it reaches top speed. Below 1 gets there sooner. Does not change where it tops out. |

## Brain

The gains that go into the driving network. Most are free: they decide the
*character* of the driving rather than buying performance, and the extremes are
genuinely bad in both directions.

| field | range | unit | cost | what it does |
|---|---|---|---|---|
| `wide_gain` | 1.05 .. 1.6 | - | free | Reaction to the wide-angle gap. High turns in hard, low runs wide. |
| `fine_gain` | 0.45 .. 0.85 | - | free | Steering trim from the rays nearest the nose. |
| `damping` | 0.2 .. 0.6 | - | 4 | Counter-steer against its own slide. High is stable, low is lively. |
| `confidence` | 0.85 .. 1.15 | - | free | How much corner speed it believes its own car can carry. Free, but overdriving is slower, not faster. |
| `caution` | 0.8 .. 1.15 | - | free | How early it lifts when the road ahead closes up. |
| `brake_gain` | 0.9 .. 1.3 | - | free | How hard it leans on the brakes to reach its target speed. |
| `throttle_gain` | 0.95 .. 1.3 | - | free | How hard it leans on the throttle to reach its target speed. |
| `apex_bias` | -0.05 .. 0.25 | - | free | Above zero hugs the inside kerb, below zero runs a wider, safer line. |
| `avoidance` | 0.8 .. 1.4 | - | free | How decisively it steers around a car ahead. The overtaking dial. |
| `recovery` | 0.8 .. 1.25 | - | 4 | Skill at rescuing an off-track moment and rejoining. |

## Temper

| field | range | unit | cost | what it does |
|---|---|---|---|---|
| `reaction` | 0.055 .. 0.115 | seconds | 6 (lower costs more) | Control lag. It cannot snap to a new input. Lower is sharper. |
| `noise` | 0.005 .. 0.03 | rad | 5 (lower costs more) | Random steering jitter. Lower is cleaner. |
| `aggression` | 0.55 .. 1 | - | free | Willingness to stay on the throttle in traffic. Free: brave and reckless are the same number. |
| `consistency` | 0.7 .. 1 | - | 4 | Scales the steering jitter down over a clean lap. |

## Sensors

| field | range | unit | cost | what it does |
|---|---|---|---|---|
| `sensor_count` | 7 / 9 / 11 / 13 | rays | 3 | How many directions it measures. More is finer, but each ray costs. |
| `sensor_range` | 420 .. 760 | px | 2 | How far ahead it sees the road run out. Spotting a corner earlier is worth a great deal. |

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
{
  "car_name": "<a name for your car>",
  "tagline": "<one line, under 60 characters>",
  "reasoning": "<2-4 sentences: what kind of car did you build, and why>",
  "power": 290.0,
  "top_speed": 420.0,
  "brake": 530.0,
  "grip": 260.0,
  "steer_rate": 3.0,
  "steer_falloff": 0.575,
  "mass": 1.025,
  "downforce": 0.325,
  "drag": 0.99,
  "wide_gain": 1.325,
  "fine_gain": 0.65,
  "damping": 0.4,
  "confidence": 1.0,
  "caution": 0.975,
  "brake_gain": 1.1,
  "throttle_gain": 1.125,
  "apex_bias": 0.1,
  "avoidance": 1.1,
  "recovery": 1.025,
  "reaction": 0.085,
  "noise": 0.0175,
  "aggression": 0.775,
  "consistency": 0.85,
  "sensor_count": 9,
  "sensor_range": 590.0
}
```

Your submission is rejected if any field is missing, out of range, or if the
total spend exceeds 60 points. Pick whatever you like for `car_name`
and `tagline`; `reasoning` is for the write-up and does not affect the car.
