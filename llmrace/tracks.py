"""Circuit presets.

Every layout was drawn by hand for a silhouette - a hairpin is a hairpin
because the points double back - and then passed through ``tracksearch.repair``,
which nudges whatever is illegal by the smallest amount that makes it
driveable. That is why they have distinct shapes rather than the rounded blobs
a blind search kept producing.

Regenerate with:  python repair_all.py && python gen_tracks.py
"""
from dataclasses import dataclass


@dataclass
class TrackPreset:
    key: str
    name: str
    blurb: str
    control: list
    laps: int = 3
    stats: dict = None


PRESETS = [
    TrackPreset(
        key="autodrome", name="Vector Autodrome",
        blurb="Long straight, esses down the right, a proper hairpin before the pits.",
        laps=2,
        stats={"length": 9747, "min_radius": 195,
               "flat_out": 0.465, "turns": 9},
        control=[
            (592, 403), (1404, 360), (2270, 341), (2981, 426),
            (3320, 678), (3359, 1050), (3190, 1294), (3163, 1535),
            (3124, 1949), (2700, 2221), (2114, 2281), (1746, 2165),
            (1666, 1906), (1829, 1514), (1667, 1244), (1162, 1275),
            (908, 1769), (627, 1858), (359, 1603), (443, 997),
        ]),
    TrackPreset(
        key="speedbowl", name="Token Speedbowl",
        blurb="Two enormous straights joined by a hairpin at each end. Bring top speed.",
        laps=2,
        stats={"length": 8894, "min_radius": 203,
               "flat_out": 0.540, "turns": 9},
        control=[
            (577, 342), (1469, 361), (2465, 352), (3090, 484),
            (3452, 851), (3459, 1135), (3278, 1481), (3277, 1755),
            (3133, 2027), (2634, 2236), (1576, 2197), (883, 2238),
            (447, 1826), (560, 1380), (580, 1133), (384, 732),
        ]),
    TrackPreset(
        key="technical", name="Gradient Descent",
        blurb="An infield knot. Chicane, hairpin, esses, and almost nowhere to rest.",
        laps=2,
        stats={"length": 9167, "min_radius": 195,
               "flat_out": 0.298, "turns": 13},
        control=[
            (679, 365), (1238, 255), (1597, 503), (2082, 503),
            (2360, 519), (2716, 388), (3244, 572), (3326, 901),
            (3224, 1210), (3216, 1650), (2976, 1878), (2550, 1857),
            (2148, 2181), (1881, 2143), (1731, 1961), (1567, 1485),
            (1224, 1439), (902, 1870), (577, 1910), (410, 1642),
            (628, 1201), (687, 971), (565, 653),
        ]),
    TrackPreset(
        key="endurance", name="Context Window",
        blurb="The longest lap here. Wide sweepers, a stadium section, one heavy stop.",
        laps=2,
        stats={"length": 9276, "min_radius": 195,
               "flat_out": 0.505, "turns": 11},
        control=[
            (494, 789), (1009, 404), (1783, 385), (2619, 406),
            (3231, 452), (3571, 906), (3514, 1328), (3309, 1594),
            (3265, 1939), (3078, 2271), (2398, 2277), (1823, 2194),
            (1645, 1989), (1576, 1625), (1351, 1483), (1079, 1595),
            (666, 1870), (370, 1697), (413, 1138),
        ]),
    TrackPreset(
        key="street", name="Backprop Street",
        blurb="Angular street circuit. Long drags into near right-angle corners.",
        laps=2,
        stats={"length": 10806, "min_radius": 193,
               "flat_out": 0.471, "turns": 9},
        control=[
            (465, 479), (1487, 267), (2459, 297), (3350, 489),
            (3388, 873), (2912, 1148), (2914, 1464), (3405, 1730),
            (3378, 2132), (2480, 2302), (1932, 2171), (1706, 1566),
            (1333, 1535), (1036, 2143), (623, 2154), (453, 1885),
            (598, 1429), (420, 970),
        ]),
    TrackPreset(
        key="twinloop", name="Attention Heads",
        blurb="Two big loops pinched together in the middle. Rhythm is everything.",
        laps=2,
        stats={"length": 13609, "min_radius": 193,
               "flat_out": 0.460, "turns": 11},
        control=[
            (755, 548), (1351, 392), (1878, 647), (1797, 1134),
            (1059, 1296), (880, 1753), (1199, 1952), (1988, 1827),
            (2607, 1953), (2785, 1646), (2353, 1131), (2442, 759),
            (2986, 559), (3499, 777), (3544, 1357), (3407, 2028),
            (2862, 2298), (1933, 2259), (1021, 2298), (390, 2037),
            (414, 1297), (411, 923),
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
