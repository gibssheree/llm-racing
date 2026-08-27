"""The car design specification: what a model may choose, and what it costs.

This is the contract between the game and an outside language model. Every
tunable number is declared here once - its range, its units, what it does, and
what it costs against the budget - and both the design brief and the submission
validator are generated from this list, so the two can never drift apart.

A budget is the whole point. Without one every entrant maxes every field and
the grid is seven identical cars. With one, a model has to decide what kind of
racing car it actually believes in.
"""
from dataclasses import dataclass

SPEC_VERSION = 2          # bumped when a unit changes, so old submissions
                          # can still be read correctly
LEGACY_SENSOR_SCALE = 1.27  # v1 sensor_range was quoted for the smaller world

BUDGET = 60.0             # design points a model may spend, out of a
                          # theoretical 100 if every field were maxed. The
                          # factory cars spend between 39.5 and 59.8.
TOLERANCE = 0.5           # small overspend allowed for rounding


@dataclass
class Param:
    name: str
    group: str            # chassis | brain | temper | sensors
    lo: float
    hi: float
    unit: str
    what: str             # what it does, in one line
    cost: float = 0.0     # points at the expensive end of the range
    higher_is_better: bool = True
    step: float = 0.0     # 0 = continuous
    choices: tuple = ()

    def clamp(self, v):
        return max(self.lo, min(self.hi, v))

    def unit_value(self, v):
        """0 at the cheap end of the range, 1 at the expensive end."""
        if self.hi == self.lo:
            return 0.0
        t = (self.clamp(v) - self.lo) / (self.hi - self.lo)
        return t if self.higher_is_better else 1.0 - t

    def points(self, v):
        return self.cost * self.unit_value(v)

    def midpoint(self):
        return (self.lo + self.hi) / 2


# Costs are weighted by how much lap time each field is actually worth. Grip is
# the single most valuable thing on circuits this twisty; mass buys nothing but
# the upper hand in a collision, so it is cheap.
PARAMS = [
    # ---- chassis: the physical car -----------------------------------------
    Param("power", "chassis", 240, 340, "px/s^2",
          "Engine force. How hard it accelerates out of a corner.", cost=11.0),
    Param("top_speed", "chassis", 380, 460, "px/s",
          "The limiter. Only pays on the straights.", cost=10.0),
    Param("brake", "chassis", 440, 620, "px/s^2",
          "Stopping power. Decides how late it can brake.", cost=8.0),
    Param("grip", "chassis", 200, 320, "px/s^2",
          "Maximum lateral acceleration before the tyres let go. "
          "The most valuable stat on a twisty circuit.", cost=16.0),
    Param("steer_rate", "chassis", 2.40, 3.60, "rad/s",
          "Yaw rate at low speed. How sharply it can turn in.", cost=7.0),
    Param("steer_falloff", "chassis", 0.40, 0.75, "-",
          "Steering authority lost as speed rises. Lower is better.",
          cost=7.0, higher_is_better=False),
    Param("mass", "chassis", 0.85, 1.20, "x reference",
          "Inertia in contact. Heavier wins the shove, but buys nothing else.",
          cost=3.0),
    Param("downforce", "chassis", 0.20, 0.45, "-",
          "Extra grip that arrives with speed: grip * (1 + downforce * (v/top)^2).",
          cost=7.0),
    Param("drag", "chassis", 0.88, 1.10, "shape",
          "How eagerly it reaches top speed. Below 1 gets there sooner. Does "
          "not change where it tops out.", cost=3.0, higher_is_better=False),

    # ---- brain: gains baked into the driving network ------------------------
    Param("wide_gain", "brain", 1.05, 1.60, "-",
          "Reaction to the wide-angle gap. High turns in hard, low runs wide."),
    Param("fine_gain", "brain", 0.45, 0.85, "-",
          "Steering trim from the rays nearest the nose."),
    Param("damping", "brain", 0.20, 0.60, "-",
          "Counter-steer against its own slide. High is stable, low is lively.",
          cost=4.0),
    Param("confidence", "brain", 0.85, 1.15, "-",
          "How much corner speed it believes its own car can carry. Free, but "
          "overdriving is slower, not faster."),
    Param("caution", "brain", 0.80, 1.15, "-",
          "How early it lifts when the road ahead closes up."),
    Param("brake_gain", "brain", 0.90, 1.30, "-",
          "How hard it leans on the brakes to reach its target speed."),
    Param("throttle_gain", "brain", 0.95, 1.30, "-",
          "How hard it leans on the throttle to reach its target speed."),
    Param("apex_bias", "brain", -0.05, 0.25, "-",
          "Above zero hugs the inside kerb, below zero runs a wider, safer line."),
    Param("avoidance", "brain", 0.80, 1.40, "-",
          "How decisively it steers around a car ahead. The overtaking dial."),
    Param("recovery", "brain", 0.80, 1.25, "-",
          "Skill at rescuing an off-track moment and rejoining.", cost=4.0),

    # ---- temper: behaviour under pressure -----------------------------------
    Param("reaction", "temper", 0.055, 0.115, "seconds",
          "Control lag. It cannot snap to a new input. Lower is sharper.",
          cost=6.0, higher_is_better=False),
    Param("noise", "temper", 0.005, 0.030, "rad",
          "Random steering jitter. Lower is cleaner.",
          cost=5.0, higher_is_better=False),
    Param("aggression", "temper", 0.55, 1.00, "-",
          "Willingness to stay on the throttle in traffic. Free: brave and "
          "reckless are the same number."),
    Param("consistency", "temper", 0.70, 1.00, "-",
          "Scales the steering jitter down over a clean lap.", cost=4.0),

    # ---- sensors: what the driver can see -----------------------------------
    Param("sensor_count", "sensors", 7, 13, "rays",
          "How many directions it measures. More is finer, but each ray costs.",
          cost=3.0, step=2, choices=(7, 9, 11, 13)),
    Param("sensor_range", "sensors", 533, 965, "px",
          "How far ahead it sees the road run out. Spotting a corner earlier "
          "is worth a great deal.", cost=2.0),
]

BY_NAME = {p.name: p for p in PARAMS}
GROUPS = ("chassis", "brain", "temper", "sensors")


def group_params(group):
    return [p for p in PARAMS if p.group == group]


def total_cost(values):
    return sum(BY_NAME[k].points(v) for k, v in values.items() if k in BY_NAME)


def reference_car():
    """The midpoint of every range - a legal, utterly average car."""
    out = {}
    for p in PARAMS:
        v = p.midpoint()
        if p.choices:
            v = min(p.choices, key=lambda c: abs(c - v))
        out[p.name] = round(v, 4)
    return out


def entry_values(entry):
    """Pull the flat parameter dict back out of a ModelEntry."""
    import dataclasses
    out = {}
    for obj in (entry.chassis, entry.brain, entry.temper):
        for f in dataclasses.fields(obj):
            out[f.name] = getattr(obj, f.name)
    out["sensor_count"] = entry.sensor_count
    out["sensor_range"] = entry.sensor_range
    return out
