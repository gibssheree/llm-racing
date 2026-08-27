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
python main.py --only claude grok gemini llama
python main.py --list
```

## Front end

- **Main menu** — start a race, or jump to the circuit, grid and settings screens.
- **Circuit** — four layouts with live previews; picking one also sets its default distance.
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
| green | Llama 4 Maverick | Meta | Heavy, planted, never slides |
| red | Grok 4 | xAI | Enormous top end, the brakes are a rumour |
| yellow | Le Chat Large | Mistral | Featherweight, changes direction on a whim |

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

Two safety systems sit outside the network: an off-track recovery that aims at the nearest
centreline when every ray reads short, and a reversing routine for a car beached on a barrier.
Both are scaled by that model's `recovery` stat.

## Overtaking

Rivals shorten sensor rays the way walls do, but on a **separate input channel**. A wall
ahead means brake; a car ahead means find a way past. Feeding both down one channel made
the entire field queue up nose-to-tail and crawl. With them split, a rival eating into the
right-hand rays pushes the gap detector left and the car goes round — overtaking falls out
of the same behaviour that keeps it on the road, weighted per model by `avoidance`.

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

## Balance

All seven lap within a few tenths of each other, but with visibly different styles — peak
slip runs from 0.00 (Llama, glued down) to 0.55 (Le Chat, sideways everywhere). That balance
is not hand-typed: `balance.py` searches each model's `confidence` — literally how much corner
speed it believes its own car can carry — against the field median, preferring the tidiest
setting that hits the target.

Balancing on one circuit does not transfer, which is why the search runs on **all four**: a
setting that was quick round the Autodrome put Grok in the grass for 16% of a lap at Gradient
Descent. A candidate now has to keep the car on the road everywhere before its pace counts.
The pecking order still changes track to track — Sonar's extra sensors win the twisty one,
Grok's top speed wins the long one.

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
python uitest.py                # drive every menu screen and a full race off-screen
```

`tracksearch.py` exists because hand-placed control points kept producing corners tighter
than the road is wide. It searches layouts scored on flat-out road while rejecting anything
undriveable — minimum corner radius, self-clearance, world margins. All four circuits came
out of it.

| Circuit | Length | Min radius | Flat out |
|---|---|---|---|
| Vector Autodrome | 4926 | 223 | 49% |
| Token Speedbowl | 4916 | 221 | 53% |
| Gradient Descent | 5042 | 219 | 8% |
| Context Window | 5188 | 220 | 47% |
