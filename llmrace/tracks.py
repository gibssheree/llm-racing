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
        stats={"length": 7649, "min_radius": 145,
               "flat_out": 0.273, "turns": 9},
        control=[
            (455, 302), (1099, 279), (1784, 271), (2335, 346),
            (2631, 571), (2622, 825), (2491, 1014), (2488, 1210),
            (2468, 1513), (2124, 1746), (1720, 1795), (1369, 1696),
            (1311, 1485), (1450, 1188), (1323, 996), (874, 1052),
            (725, 1364), (504, 1463), (287, 1263), (331, 781),
        ]),
    TrackPreset(
        key="speedbowl", name="Token Speedbowl",
        blurb="Two enormous straights joined by a hairpin at each end. Bring top speed.",
        laps=3,
        stats={"length": 7045, "min_radius": 146,
               "flat_out": 0.398, "turns": 9},
        control=[
            (420, 319), (1170, 275), (1958, 286), (2446, 367),
            (2727, 623), (2724, 894), (2571, 1154), (2582, 1369),
            (2467, 1596), (2056, 1777), (1241, 1730), (720, 1761),
            (352, 1438), (441, 1087), (488, 864), (302, 576),
        ]),
    TrackPreset(
        key="technical", name="Gradient Descent",
        blurb="An infield knot. Chicane, hairpin, esses, and almost nowhere to rest.",
        laps=3,
        stats={"length": 7410, "min_radius": 144,
               "flat_out": 0.111, "turns": 13},
        control=[
            (525, 302), (953, 225), (1250, 418), (1620, 372),
            (1866, 429), (2173, 327), (2575, 453), (2618, 724),
            (2495, 974), (2540, 1331), (2390, 1492), (1992, 1446),
            (1694, 1687), (1431, 1741), (1288, 1557), (1212, 1159),
            (1000, 1112), (756, 1414), (433, 1488), (319, 1305),
            (542, 960), (586, 773), (448, 530),
        ]),
    TrackPreset(
        key="endurance", name="Context Window",
        blurb="The longest lap here. Wide sweepers, a stadium section, one heavy stop.",
        laps=3,
        stats={"length": 7280, "min_radius": 150,
               "flat_out": 0.338, "turns": 11},
        control=[
            (386, 622), (790, 318), (1410, 307), (2061, 315),
            (2542, 358), (2792, 703), (2766, 1037), (2594, 1271),
            (2582, 1542), (2413, 1781), (1895, 1792), (1434, 1727),
            (1280, 1573), (1242, 1271), (1079, 1170), (822, 1282),
            (530, 1474), (323, 1352), (356, 898),
        ]),
    TrackPreset(
        key="street", name="Backprop Street",
        blurb="Angular street circuit. Long drags into near right-angle corners.",
        laps=2,
        stats={"length": 8444, "min_radius": 144,
               "flat_out": 0.320, "turns": 11},
        control=[
            (389, 406), (1143, 337), (1946, 342), (2626, 403),
            (2683, 688), (2299, 925), (2303, 1155), (2675, 1344),
            (2655, 1697), (1954, 1800), (1470, 1714), (1342, 1244),
            (1050, 1194), (807, 1703), (493, 1699), (382, 1399),
            (479, 1118), (334, 792),
        ]),
    TrackPreset(
        key="twinloop", name="Attention Heads",
        blurb="Two big loops pinched together in the middle. Rhythm is everything.",
        laps=2,
        stats={"length": 10594, "min_radius": 146,
               "flat_out": 0.238, "turns": 9},
        control=[
            (544, 470), (1069, 320), (1480, 530), (1389, 895),
            (883, 979), (714, 1348), (1016, 1586), (1593, 1566),
            (2063, 1566), (2154, 1250), (1836, 943), (1910, 627),
            (2327, 436), (2731, 606), (2794, 1078), (2669, 1547),
            (2268, 1828), (1557, 1836), (798, 1834), (315, 1588),
            (305, 1021), (347, 695),
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
