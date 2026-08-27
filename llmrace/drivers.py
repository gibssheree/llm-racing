"""The grid: one entry per language model.

Each entry bundles three independent things, and all three come from the
"vendor" it represents:

  chassis  - the physical car the model's engineering produced
  brain    - the gains baked into that model's neural driver
  temper   - how the model behaves under pressure (lag, noise, aggression)

Nothing here is scripted to a racing line. Two cars differ only because
these numbers differ, so the standings are an emergent result.
"""
from dataclasses import dataclass, field

from . import config as cfg


@dataclass
class Chassis:
    power: float          # forward acceleration, px/s^2
    top_speed: float      # px/s on the limiter
    brake: float          # braking deceleration, px/s^2
    grip: float           # max lateral acceleration before it slides, px/s^2
    steer_rate: float     # rad/s of yaw at low speed
    steer_falloff: float  # how much steering authority is lost with speed
    mass: float           # 1.0 = reference; affects contact and inertia
    downforce: float      # extra grip that arrives with speed
    drag: float           # drag shape: >1 reaches top speed lazily, <1 eagerly


@dataclass
class Brain:
    wide_gain: float      # how hard it reacts to the wide-angle gap
    fine_gain: float      # trim from the near-centre rays
    damping: float        # counter-steer against its own slide
    confidence: float     # corner-entry speed it believes it can carry
    caution: float        # how early it lifts when the road closes up
    brake_gain: float     # aggressiveness of the speed controller on the brakes
    throttle_gain: float  # aggressiveness on power
    apex_bias: float      # >0 hugs the inside, <0 runs a wider, safer line
    avoidance: float      # how hard it steers around a car ahead
    recovery: float       # skill at rescuing an off-track moment


@dataclass
class Temper:
    reaction: float       # control smoothing constant, seconds (higher = laggier)
    noise: float          # random steering jitter, radians-ish
    aggression: float     # willingness to stay on the throttle in traffic
    consistency: float    # 0..1, scales noise down over a clean lap


@dataclass
class ModelEntry:
    key: str
    name: str             # display name of the model
    vendor: str
    color: tuple
    accent: tuple         # livery stripe
    tagline: str
    chassis: Chassis
    brain: Brain
    temper: Temper
    seed: int
    sensor_range: float = cfg.SENSOR_RANGE
    sensor_count: int = 9
    stats: dict = field(default_factory=dict)


ROSTER = [
    ModelEntry(
        key="claude", name="Claude Opus 5", vendor="Anthropic",
        color=(232, 120, 60), accent=(255, 190, 130),
        tagline="Late on the brakes, never off the road.",
        chassis=Chassis(power=292, top_speed=420, brake=575, grip=250,
                        steer_rate=2.85, steer_falloff=0.52, mass=1.00,
                        downforce=0.34, drag=1.0),
        brain=Brain(wide_gain=1.28, fine_gain=0.62, damping=0.42,
                    confidence=0.988, caution=0.98, brake_gain=1.22,
                    throttle_gain=1.05, apex_bias=0.10, avoidance=1.05, recovery=1.10),
        temper=Temper(reaction=0.085, noise=0.008, aggression=0.72, consistency=0.95),
        seed=1101),
    ModelEntry(
        key="gpt", name="GPT-5.5", vendor="OpenAI",
        color=(238, 238, 242), accent=(24, 24, 28),
        tagline="Generalist chassis. Fastest on the straights.",
        chassis=Chassis(power=286, top_speed=438, brake=520, grip=262,
                        steer_rate=2.75, steer_falloff=0.58, mass=1.02,
                        downforce=0.3, drag=0.94),
        brain=Brain(wide_gain=1.24, fine_gain=0.58, damping=0.38,
                    confidence=0.936, caution=1.00, brake_gain=1.10,
                    throttle_gain=1.12, apex_bias=0.06, avoidance=1.0, recovery=1.00),
        temper=Temper(reaction=0.090, noise=0.011, aggression=0.76, consistency=0.90),
        seed=5505),
    ModelEntry(
        key="gemini", name="Gemini 3 Flash", vendor="Google",
        color=(66, 133, 244), accent=(160, 200, 255),
        tagline="Blistering out of corners. Sometimes too keen.",
        chassis=Chassis(power=322, top_speed=414, brake=522, grip=228,
                        steer_rate=3.15, steer_falloff=0.62, mass=0.95,
                        downforce=0.28, drag=1.04),
        brain=Brain(wide_gain=1.42, fine_gain=0.70, damping=0.30,
                    confidence=0.988, caution=0.90, brake_gain=1.02,
                    throttle_gain=1.24, apex_bias=0.16, avoidance=1.18, recovery=0.92),
        temper=Temper(reaction=0.070, noise=0.020, aggression=0.86, consistency=0.80),
        seed=3037),
    ModelEntry(
        key="perplexity", name="Sonar Large", vendor="Perplexity",
        color=(32, 128, 141), accent=(150, 226, 232),
        tagline="Sees the corner before anyone else does.",
        chassis=Chassis(power=278, top_speed=404, brake=556, grip=268,
                        steer_rate=2.95, steer_falloff=0.52, mass=1.00,
                        downforce=0.33, drag=1.02),
        brain=Brain(wide_gain=1.30, fine_gain=0.66, damping=0.40,
                    confidence=1.04, caution=1.06, brake_gain=1.18,
                    throttle_gain=1.02, apex_bias=0.08, avoidance=0.92, recovery=1.06),
        temper=Temper(reaction=0.078, noise=0.009, aggression=0.66, consistency=0.93),
        seed=7311, sensor_range=700.0, sensor_count=11),
    ModelEntry(
        key="llama", name="Llama 4 Maverick", vendor="Meta",
        color=(76, 175, 80), accent=(190, 240, 190),
        tagline="Heavy, planted, and extremely hard to shake off.",
        chassis=Chassis(power=262, top_speed=402, brake=585, grip=300,
                        steer_rate=2.7, steer_falloff=0.44, mass=1.14,
                        downforce=0.4, drag=1.0),
        brain=Brain(wide_gain=1.20, fine_gain=0.54, damping=0.50,
                    confidence=0.988, caution=1.00, brake_gain=1.16,
                    throttle_gain=1.00, apex_bias=0.04, avoidance=0.88, recovery=1.14),
        temper=Temper(reaction=0.100, noise=0.007, aggression=0.70, consistency=0.96),
        seed=4404),
    ModelEntry(
        key="grok", name="Grok 4", vendor="xAI",
        color=(217, 51, 63), accent=(255, 150, 155),
        tagline="Enormous top end. The brakes are a rumour.",
        chassis=Chassis(power=306, top_speed=448, brake=470, grip=208,
                        steer_rate=2.9, steer_falloff=0.68, mass=0.98,
                        downforce=0.26, drag=0.9),
        brain=Brain(wide_gain=1.36, fine_gain=0.60, damping=0.26,
                    confidence=0.988, caution=0.86, brake_gain=0.96,
                    throttle_gain=1.26, apex_bias=0.18, avoidance=1.3, recovery=0.86),
        temper=Temper(reaction=0.066, noise=0.024, aggression=0.94, consistency=0.74),
        seed=1442),
    ModelEntry(
        key="mistral", name="Le Chat Large", vendor="Mistral",
        color=(242, 179, 61), accent=(255, 225, 150),
        tagline="Featherweight. Changes direction on a whim.",
        chassis=Chassis(power=300, top_speed=410, brake=535, grip=222,
                        steer_rate=3.3, steer_falloff=0.7, mass=0.90,
                        downforce=0.24, drag=1.06),
        brain=Brain(wide_gain=1.46, fine_gain=0.76, damping=0.28,
                    confidence=1.04, caution=0.94, brake_gain=1.08,
                    throttle_gain=1.16, apex_bias=0.14, avoidance=1.22, recovery=0.94),
        temper=Temper(reaction=0.072, noise=0.017, aggression=0.82, consistency=0.83),
        seed=8123),
]


def by_key(key):
    for m in ROSTER:
        if m.key == key:
            return m
    raise KeyError(key)
