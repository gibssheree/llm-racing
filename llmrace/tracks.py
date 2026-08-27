"""Circuit presets.

Each layout was produced by ``tracksearch.py``, which hill-climbs a control
polygon against hard geometry constraints - minimum corner radius, self
clearance, world margins - so none of these can contain a corner tighter than
the road is wide. They are scored for different characters, which is why the
same grid produces a different pecking order on each one.
"""
from dataclasses import dataclass


@dataclass
class TrackPreset:
    key: str
    name: str
    blurb: str
    control: list
    laps: int = 3


PRESETS = [
    TrackPreset(
        key="autodrome", name="Vector Autodrome",
        blurb="Balanced. Long straight, one heavy stop, a flowing bottom half.",
        laps=3,
        control=[
            (600, 330), (1125, 284), (1485, 285), (2095, 407), (2301, 655),
            (2161, 1092), (1834, 1224), (1436, 1308), (1071, 1296), (830, 1314),
            (589, 1190), (479, 846), (430, 560),
        ]),
    TrackPreset(
        key="speedbowl", name="Token Speedbowl",
        blurb="Half the lap flat out. Rewards top speed and a brave right foot.",
        laps=4,
        control=[
            (523, 470), (1145, 282), (1782, 331), (2200, 470), (2280, 860),
            (1970, 1129), (1515, 1301), (825, 1368), (560, 1120), (346, 739),
        ]),
    TrackPreset(
        key="technical", name="Gradient Descent",
        blurb="Almost no straights. Grip and steering rate decide everything.",
        laps=3,
        control=[
            (708, 334), (1187, 240), (1498, 377), (1959, 360), (2332, 755),
            (2228, 1221), (1778, 1342), (1389, 1214), (1163, 1266), (919, 1279),
            (608, 1127), (445, 921), (430, 642),
        ]),
    TrackPreset(
        key="endurance", name="Context Window",
        blurb="The longest lap on the calendar. Consistency beats outright pace.",
        laps=2,
        control=[
            (480, 560), (820, 340), (1265, 218), (1813, 257), (2188, 352),
            (2360, 720), (2280, 1080), (1940, 1300), (1509, 1389), (1019, 1348),
            (720, 1340), (450, 1100), (389, 799),
        ]),
]


def preview_points(control, samples=14):
    """Cheap centreline sampling for menu thumbnails.

    Deliberately does not build a Track: that rasterises a tarmac bitmap, and
    the track picker only needs a shape to draw.
    """
    n = len(control)
    pts = []
    for i in range(n):
        p0, p1 = control[(i - 1) % n], control[i]
        p2, p3 = control[(i + 1) % n], control[(i + 2) % n]
        for s in range(samples):
            t = s / samples
            t2, t3 = t * t, t * t * t
            pts.append((
                0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t
                       + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                       + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3),
                0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t
                       + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                       + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)))
    return pts


def by_key(key):
    for t in PRESETS:
        if t.key == key:
            return t
    raise KeyError(key)


DEFAULT = PRESETS[0]
