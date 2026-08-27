# LLM Grand Prix

A 2D racing game in Python + Pygame where every car is a different large language model.
Each car's engine, grip, brakes, steering and **driving brain** are its own spec, so the
result of a race is emergent, not scripted.

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows;  source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
python main.py
```

Everything is configurable from the menus. The command line is just a shortcut:

```bash
python main.py --track technical --laps 5
python main.py --only claude grok gemini deepseek
python main.py --list
```

## Front end

- **Main menu** — start a race, or jump to the circuit, grid and settings screens.
- **Circuit** — six layouts with live previews; picking one also sets its default distance.
- **Grid** — click any model to enter or withdraw it. A race needs at least four cars, so
  the fourth cannot be removed. Full chassis stats are on each row.
- **Settings** — race distance, sensor overlay, telemetry panel, tyre marks, leader-cam.

## The grid

| Car | Model | Vendor | Character |
|---|---|---|---|
| orange | Claude Opus 5 | Anthropic | Late on the brakes, never off the road |
| white/black | GPT-5.5 | OpenAI | Generalist chassis, fastest on the straights |
| blue | Gemini 3 Flash | Google | Blistering out of corners, sometimes too keen |
| teal | Sonar Large | Perplexity | 11 sensors at 700px: sees the corner first |
| green | DeepSeek V3.2 | DeepSeek | Enormous grip for the money, never slides |
| red | Grok 4 | xAI | Enormous top end, the brakes are a rumour |
| yellow | Kimi K2 | Moonshot AI | Featherweight, quick to change its line |

## How a car drives

No car knows where the track goes. Every frame each one:

1. **Sees.** A fan of raycasts (9 for most, 11 for Sonar) measures how far the road runs
   in each direction. Readings are divided by how far that ray *would* reach on a straight
   road, so the network reads deviation-from-straight rather than raw geometry. Rival cars
   are cast against separately, on a second input channel.
2. **Thinks.** A small feed-forward network (`nn.py`) turns those readings into a steering
   command and a target speed. The hidden layer is hand-authored into named detectors —
   gap direction, forward clearance, closing rate, slide, traffic — and the output layer
   mixes them using *that model's* gains.
3. **Acts.** A longitudinal controller converts target speed into throttle or brake, then a
   per-model control filter applies that model's reaction lag and jitter.

The target-speed head is grounded in real physics rather than guessed. For a road of
half-width `w`, a nose ray reaches about `sqrt(2Rw)` around a bend of radius `R`, so
`R ≈ d²/2w` and the grip-limited corner speed `sqrt(grip·R)` is **proportional to forward
clearance**. That is why the head is linear, and its coefficients were least-squares fitted
against the ideal speed at every sample of the circuit (rms error 0.03 of top speed).
Each car rescales it by `sqrt(grip)/top_speed`, so a model that built a grippier car
genuinely commits to faster corners.

Three safety systems sit outside the network, all scaled by that model's `recovery` stat:

- **Off-track recovery** — when every ray reads short the network's vision is useless, so a
  lower-level system aims at the nearest centreline.
- **Wrong-way correction** — a road looks *identical* forwards and backwards through a fan of
  range sensors, so the network cannot tell which way the lap runs. Without this, a car that
  got turned around at the start would happily circulate backwards for the entire race,
  never scoring a lap. It is told which way the circuit goes, the way a real driver knows.
- **Un-beaching** — reverse out when something solid is in the way. Deliberately *not*
  triggered by simply being held up: reversing out of a start-line queue was what spun cars
  round to face the wrong way in the first place.

## Overtaking

Rivals shorten sensor rays the way walls do, but on a **separate input channel**. A wall
ahead means brake; a car ahead means find a way past. Feeding both down one channel made
the entire field queue up nose-to-tail and crawl. With them split, a rival eating into the
right-hand rays pushes the gap detector left and the car goes round — overtaking falls out
of the same behaviour that keeps it on the road, weighted per model by `avoidance`.

A car sitting directly behind a rival gives up 12–20% of its target speed, which is what
stops the field rear-ending each other. But the quickest and slowest cars are separated by
only about 4% on lap time, so a follower that never gets out of the slipstream can never
close. The penalty releases as soon as the car is more than 34px offline — so how much road
there is to step out into decides whether anybody ever passes.

On the 200px road that was 34% of the half-width, and the racing died: `overtake.py`
measured **0.7 passes per race**. Widening to 240px took it to **8**. Scaling the whole world
up 1.27x afterwards — same car size, bigger circuits, 300px road — took it to **34**. Run
`python overtake.py` to measure it after any change.

Two things had to move with the world when it grew, because both are measured in world pixels
rather than being properties of a car:

- `SENSOR_RANGE`, the reference the sensors normalise against. Left at 560 on the enlarged
  circuits, the forward beam saturated for 46% of a lap and the driver could no longer tell a
  hairpin from a straight. It scales to 711.
- Each car's own `sensor_range`. Submissions carry a `spec_version`; anything written against
  the older, smaller world is converted on load, so a car's *relative* choice within the
  allowed band is preserved and nobody's design is edited.

## Physics

Bicycle-style model at 120Hz. Turning the wheel points the tyres somewhere new; the tyres
then have to drag existing momentum around and can only pull so hard. When a corner demands
more than `grip`, the excess shows up as a slide. Grip rises with speed via `downforce` and
collapses off-track. Resistance is calibrated so full throttle settles exactly on `top_speed`.

## Controls

**Watching a particular car**

| | |
|---|---|
| `TAB` / `SHIFT`+`TAB` | next / previous car |
| `←` `→` (or `[` `]`) | previous / next car |
| `1`–`9` | jump straight to that car |
| click a car | focus it |
| `L` | follow the leader instead |

**Camera**

| | |
|---|---|
| drag | pan freely |
| wheel | zoom to the cursor |
| right-click, or `F` | drop free cam, go back to following |
| `C` | chase / wide / whole circuit |

**Race**

| | |
|---|---|
| `SPACE` | pause |
| `V` | vision fan |
| `T` | telemetry panel |
| `+` / `-` | simulation speed |
| `R` | restart |
| `ESC` | back to the menu |

The status line along the bottom always says which camera mode is live and who is
being watched.

## Letting the real models design their own cars

The seven cars shipped here are my guesses at what each vendor would build. The
point of `spec.py` is that they do not have to stay guesses — you can send each
model the actual design brief and race whatever it sends back.

```bash
python brief.py                 # writes briefs/<key>.md, one per entrant
```

Send `briefs/claude.md` to Claude, `briefs/gpt.md` to GPT, and so on. Each brief
is self-contained: the physics, what the driver can see, the six circuits, all
25 fields with ranges and units, the budget rules, and the exact JSON to reply
with. It is generated from `llmrace/spec.py`, so it can never describe a field
the game does not have or quote a range the validator would reject.

Save each reply as `garage/<key>.json` — the raw JSON is fine, a markdown fence
around it is fine too — then:

```bash
python submit.py                # validate, price, and shake down every entry
python submit.py --race         # also race the garage against the factory
python submit.py --report       # write garage/report.md to send back
```

`submit.py` rejects anything out of range, missing, or over budget, then drives
each accepted car solo on all six circuits and reports lap times, time off the
road, and how much it slid. That report is written to be pasted straight back
to the model so it can revise — which is the interesting part, because the first
answer is usually not the quick one.

Any valid car in `garage/` automatically replaces its factory entry next time
the game starts, and is badged **DESIGNED BY THE MODEL** on the grid screen.

### The budget

Without a cap every entrant maxes every field and you get seven identical cars.
There are **60 points** to spend against a theoretical 100 if every field were
set to its most expensive value. Cost is linear across each field's range, and
weighted by how much lap time it is actually worth — `grip` costs 16 because it
is the most valuable thing on this calendar, `mass` costs 3 because it buys
nothing but the upper hand in a collision. Driving-style fields like `caution`
and `apex_bias` are free: they change the character of the car, not its ceiling.

The factory cars spend between 39.5 and 59.8 points, so they are all legal
entries and make honest reference points.

## Balance

The field laps within a few percent of each other, but with visibly different styles — mean
peak slip runs from 0.01 (DeepSeek, glued down) through 0.25 (Claude) to 0.65 (Kimi, sideways
everywhere). That balance is not hand-typed: `balance.py` searches each model's `confidence` —
literally how much corner speed it believes its own car can carry — against the field median,
preferring the tidiest setting that hits the target.

Slip is *averaged* across circuits rather than maxed. Over six tracks almost every setting
touches full slide somewhere, so a worst-case reading stopped telling the tidy setups apart
from the ragged ones, and the balancer happily handed every car a setup that slid everywhere.

Balancing on one circuit does not transfer, which is why the search runs on **all six**: a
setting that was quick round the Autodrome put Grok in the grass for 16% of a lap at Gradient
Descent. A candidate has to keep the car on the road everywhere before its pace counts. The
pecking order still changes track to track — Sonar's extra sensors win the twisty one,
DeepSeek's grip wins the long one.

A race is called `FLAG_GRACE` seconds after the winner crosses the line, and anyone still out
is classified where they lie. Without that rule one car in trouble hangs the session forever.

## Layout

| File | |
|---|---|
| `main.py` | entry point |
| `llmrace/drivers.py` | **the roster** — every model's chassis, brain gains, temperament |
| `llmrace/ai.py` | vision, brain construction, the closed-loop driver |
| `llmrace/nn.py` | the network |
| `llmrace/car.py` | physics, lap timing, contact |
| `llmrace/track.py` | circuit spline, tarmac bitmap, raycasting |
| `llmrace/race.py` | race session (headless-capable) |
| `llmrace/render.py` | camera, circuit art, cars, skid marks |
| `llmrace/hud.py` | standings, telemetry, minimap, results |
| `llmrace/game.py` | window, input, camera, render loop |
| `llmrace/menu.py` | main menu, circuit picker, grid picker, settings |
| `llmrace/ui.py` | buttons, toggles, steppers |
| `llmrace/tracks.py` | the four circuit presets |

## Tools

```bash
python headless.py --laps 3     # run a race with no window
python bench.py                 # solo hot-lap for every model
python racelog.py               # full race + every position change
python balance.py               # re-balance the field
python tracksearch.py           # hill-climb a new circuit under geometry constraints
python shot.py                  # render frames off-screen to shots/
```

```bash
python benchall.py              # every model on every circuit - the "nothing is broken" check
python uitest.py                # drive every menu screen and a full race off-screen
python repair_all.py            # re-legalise the drawn layouts in layouts.py
python gen_tracks.py            # regenerate llmrace/tracks.py from them
python refit.py                 # refit the speed head after a geometry change
python trackshots.py            # contact sheet of every circuit
```

### Drawing circuits

The first version of `tracksearch.py` hill-climbed layouts from scratch, and every one came
out a rounded blob — a blind search optimising for flat-out road has no reason to invent a
hairpin. It now works the other way round: shapes are **drawn by hand** in `layouts.py`, and
`repair()` nudges control points the smallest amount that makes them legal, so the intended
silhouette survives. That is where the hairpins, chicanes and esses come from.

Making that work also meant growing the world to 3000×2000 and, at first, narrowing the road
to 200px. A corner cannot be tighter than roughly 1.3× the road's half-width before the inside
kerb folds over itself, so a wide road can only ever produce gentle curves.

The road is back at 240px now, because 200px turned out to be too narrow to race on — see
**Overtaking** below. Widening it meant re-running `repair_all.py` against a higher minimum
radius, which is why the hairpins are slightly rounder than the drawings.

The start line is not control point zero — `Track._pick_start` puts it on the longest
straight, because the grid forms up *behind* the line and lining seven cars up round the
outside of a hairpin looks absurd.

| Circuit | Length | Min radius | Flat out | Direction changes |
|---|---|---|---|---|
| Vector Autodrome | 9747 | 195 | 47% | 9 |
| Token Speedbowl | 8894 | 203 | 54% | 9 |
| Gradient Descent | 9167 | 195 | 30% | 13 |
| Context Window | 9276 | 195 | 51% | 11 |
| Backprop Street | 10806 | 193 | 47% | 9 |
| Attention Heads | 13609 | 193 | 46% | 11 |
