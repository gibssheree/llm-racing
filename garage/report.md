# LLM Grand Prix — submission report

Budget 60 points. Solo shake-down, two laps of each circuit, no traffic.

| car | spend | mean lap | worst off-track | mean slide |
|---|---|---|---|---|
| Moonshot Seven | 59.2 | 22.16s | 0.0% | 0.38 |
| Amber Apex | 59.9 | 22.45s | 0.0% | 0.13 |
| Grok Apex Redline | 59.5 | 22.56s | 0.0% | 0.41 |

## Moonshot Seven  (`kimi`)

| circuit | best lap | off-track | slide |
|---|---|---|---|
| Vector Autodrome | 21.37s | 0.0% | 0.45 |
| Token Speedbowl | 17.85s | 0.0% | 0.24 |
| Gradient Descent | 21.15s | 0.0% | 0.39 |
| Context Window | 19.75s | 0.0% | 0.35 |
| Backprop Street | 24.48s | 0.0% | 0.51 |
| Attention Heads | 28.33s | 0.0% | 0.34 |

> Prioritized grip and downforce to dominate the five corner-heavy circuits, while keeping enough top speed to stay competitive on Token Speedbowl. High steering authority and strong brakes allow late braking and sharp turn-in, and the neural net is tuned for decisive overtaking without overdriving.

## Amber Apex  (`claude`)

| circuit | best lap | off-track | slide |
|---|---|---|---|
| Vector Autodrome | 21.50s | 0.0% | 0.13 |
| Token Speedbowl | 18.30s | 0.0% | 0.06 |
| Gradient Descent | 21.25s | 0.0% | 0.15 |
| Context Window | 20.25s | 0.0% | 0.14 |
| Backprop Street | 24.75s | 0.0% | 0.17 |
| Attention Heads | 28.63s | 0.0% | 0.14 |

> This is a handling-first car: grip and steer_falloff are pushed hard because five of the six circuits are corner-dominated with tight radii and frequent direction changes, while top_speed and power stay modest since only Token Speedbowl really rewards straight-line pace. Sensor_range is maxed because it's cheap and spotting a corner earlier matters more than counting extra rays. Damping, recovery, reaction and noise get even mid-level investment so slides stay recoverable rather than spectacular, and the free brain gains (confidence near 1.0, high avoidance/aggression, a small positive apex_bias) are tuned for committed but controlled cornering and clean overtakes.

## Grok Apex Redline  (`grok`)

| circuit | best lap | off-track | slide |
|---|---|---|---|
| Vector Autodrome | 21.75s | 0.0% | 0.49 |
| Token Speedbowl | 18.17s | 0.0% | 0.26 |
| Gradient Descent | 21.47s | 0.0% | 0.39 |
| Context Window | 20.13s | 0.0% | 0.38 |
| Backprop Street | 25.00s | 0.0% | 0.49 |
| Attention Heads | 28.82s | 0.0% | 0.46 |

> Built a high-grip corner car for the twisty calendar. Prioritized grip, downforce, sensors and sharp steering over top speed traps. Kept confidence near 1.0 and solid recovery so it stays planted instead of spectacularly slow.
