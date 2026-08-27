"""Vision, brain construction, and the closed-loop driver.

The pipeline every frame, per car:

    raycast vision  ->  normalised features  ->  MLP  ->  raw commands
                                                       ->  control filter
                                                       ->  throttle/brake/steer

No car knows where the track goes. It only knows how far it can see in a
fan of directions, how fast it is going, whether it is sliding, and whether
someone is in the way. Everything else is the network's problem.
"""
import math
import random

from . import config as cfg
from .nn import MLP
from .vec import clamp

N_EXTRA_FEATURES = 5        # speed, slip, sustained-slide, traffic, off-track
RIVAL_ARC = math.radians(52)  # rivals are only detected inside the front arc
N_HIDDEN = 10
N_OUT = 2                   # steer, target-speed
MAX_SENSOR_ANGLE = 78.0     # degrees either side of the nose
REF_GRIP = 250.0            # the chassis the speed head was fitted against
REF_TOP_SPEED = 420.0       # (Claude's, so its own phys factor comes out at 1.0)
RIVAL_RADIUS = 23.0         # how big another car looks to the sensors
RIVAL_SIGHT_2 = 420.0 ** 2  # squared cutoff for bothering to test a rival
# Explicit fan layouts, in degrees. The three rays nearest the nose are the
# "lookahead beam": at |a| <= 11 deg a ray can run the full sensor range before
# a straight road's edge cuts it off, so those are the only ones that report
# how far ahead the road actually continues. Everything wider reports width.
SENSOR_FANS = {
    9:  [-78, -50, -28, -10, 0, 10, 28, 50, 78],
    11: [-80, -62, -44, -26, -11, 0, 11, 26, 44, 62, 80],
    13: [-80, -66, -52, -38, -24, -11, 0, 11, 24, 38, 52, 66, 80],
}


def sensor_angles(count):
    """Symmetric fan, denser near the nose where precision matters."""
    table = SENSOR_FANS.get(count)
    if table is None:                       # fall back to a generated fan
        table = []
        for i in range(count):
            u = 2.0 * i / (count - 1) - 1.0
            s = -1.0 if u < 0 else 1.0
            table.append(MAX_SENSOR_ANGLE * s * abs(u) ** 1.5)
    return [math.radians(a) for a in table]


def expected_distances(angles, half_width, max_range):
    """How far each ray would reach on a perfectly straight road.

    Dividing the real reading by this makes every sensor read ~1.0 on a
    straight, so the network sees deviation-from-straight rather than raw
    geometry. It is the single biggest reason these brains work untrained.
    """
    out = []
    for a in angles:
        s = abs(math.sin(a))
        out.append(min(max_range, half_width / s) if s > 1e-4 else max_range)
    return out


class Vision:
    """The raycast sensor array bolted to the nose of a car.

    Readings are normalised against a *common* reference range, not against
    the car's own range. A model with better sensors therefore genuinely sees
    further ahead (readings above 1.0) instead of just rescaling its inputs.
    """

    def __init__(self, count, max_range, half_width, ref_range=cfg.SENSOR_RANGE):
        self.count = count
        self.max_range = max_range
        self.angles = sensor_angles(count)
        self.expected = expected_distances(self.angles, half_width, ref_range)
        self.raw = [max_range] * count       # road-only distance
        self.norm = [1.0] * count            # road-only, normalised
        self.occlusion = [0.0] * count       # how much of each ray a rival eats
        self.rival_raw = [max_range] * count # distance to whichever comes first
        self.blocked = [False] * count
        self.front = [abs(a) <= RIVAL_ARC for a in self.angles]

    def scan(self, track, x, y, heading, obstacles=()):
        """Cast every ray against the road edge, then against rival cars.

        Road distance and rival distance are kept apart on purpose. A wall
        ahead means brake; a car ahead means find a way round it. Feeding both
        down the same channel made the entire field queue up and crawl, so the
        two are reported separately and the brain decides how to weigh them.
        """
        for i, a in enumerate(self.angles):
            th = heading + a
            dx, dy = math.cos(th), math.sin(th)
            d = track.raycast(x, y, dx, dy, self.max_range)
            self.raw[i] = d
            self.norm[i] = min(1.9, d / self.expected[i])

            hit = d
            if self.front[i]:
                for ox, oy, r in obstacles:
                    lx, ly = ox - x, oy - y
                    tca = lx * dx + ly * dy
                    if tca <= 0 or tca - r > hit:
                        continue
                    h2 = lx * lx + ly * ly - tca * tca
                    rr = r * r
                    if h2 > rr:
                        continue
                    t = tca - math.sqrt(rr - h2)
                    if 0.0 < t < hit:
                        hit = t
            self.rival_raw[i] = hit
            self.blocked[i] = hit < d
            self.occlusion[i] = (d - hit) / self.expected[i]
        return self.norm


def build_brain(entry):
    """Turn a model's Brain gains into actual network weights.

    The hidden layer is hand-authored into named feature detectors (gap
    direction, clearance, closing rate, ...). The output layer mixes them
    using that model's personality. A seeded jitter then makes every car
    unique even where two recipes agree.
    """
    b = entry.brain
    n_s = entry.sensor_count
    net = MLP(2 * n_s + N_EXTRA_FEATURES, N_HIDDEN, N_OUT)

    angles = sensor_angles(n_s)
    u = [a / math.radians(MAX_SENSOR_ANGLE) for a in angles]   # -1 .. 1
    # inputs: [road clearance] ++ [rival occlusion]
    #         ++ [speed, slip, sustained slide, traffic, off-track]
    occ0 = n_s
    i_speed = 2 * n_s
    i_slip = i_speed + 1
    i_slide = i_speed + 2
    i_traffic = i_speed + 3
    i_off = i_speed + 4

    def gauss(x, w):
        return math.exp(-(x / w) ** 2)

    def sensor_row(row, shape, gain, offset=0):
        """Fill a hidden row from a shape function over the fan, then scale it
        so the row's total weight is `gain` regardless of how many rays the
        model has. Without this a car with 11 sensors would read every signal
        at a different magnitude than a car with 9."""
        raw = [shape(u[i]) for i in range(n_s)]
        total = sum(abs(v) for v in raw) or 1.0
        for i in range(n_s):
            net.w1[row][offset + i] = raw[i] * gain / total

    # h0 - wide gap direction: the weighted centre of free space
    sensor_row(0, lambda x: x, 1.30)
    sensor_row(0, lambda x: -x, 1.30 * b.avoidance, occ0)
    # h1 - fine gap direction: same idea, but only the rays near the nose.
    # The occlusion half is what actually performs an overtake: a rival eating
    # into the right-hand rays pushes this unit left, and the car goes round.
    sensor_row(1, lambda x: x * gauss(x, 0.5), 1.55)
    sensor_row(1, lambda x: -x * gauss(x, 0.5), 1.55 * b.avoidance, occ0)
    # h2 - forward clearance: how much road is left straight ahead.
    #
    # The gain is deliberately small so tanh stays in its linear region - this
    # unit has to encode *how much* room there is, not just whether there is
    # any, because target speed is read straight off it. The window is narrow
    # for the same reason: only the rays within about 11 degrees of the nose
    # can see far enough to report how far the road continues, and letting the
    # wider rays in diluted the signal with what is really just road width.
    sensor_row(2, lambda x: gauss(x, 0.20), 0.62)
    # h3 - speed
    net.w1[3][i_speed] = 1.9
    net.b1[3] = -0.55
    # h4 - closing rate: fast plus no road ahead equals trouble
    sensor_row(4, lambda x: -gauss(x, 0.22), 0.58)
    net.w1[4][i_speed] = 0.90
    # h5 / h6 - mid-range flanks, used to pick a line through the corner
    sensor_row(5, lambda x: gauss(x + 0.5, 0.42) if x < -0.12 else 0.0, 0.95)
    sensor_row(6, lambda x: gauss(x - 0.5, 0.42) if x > 0.12 else 0.0, 0.95)
    # h7 - slide detector
    net.w1[7][i_slip] = 3.4
    # h8 - trouble: off the road, or sliding and not stopping.
    # The sustained-slide input closes a feedback loop the car cannot argue
    # with. Overdrive the thing and its own target speed comes down until the
    # slide stops, which is what keeps a loose chassis on a twisty circuit
    # instead of straight into the scenery.
    net.w1[8][i_off] = 2.2
    net.w1[8][i_slip] = 0.7
    net.w1[8][i_slide] = 1.4
    # h9 - traffic ahead
    net.w1[9][i_traffic] = 2.6
    net.b1[9] = -0.35

    # o0: steering
    net.w2[0][0] = b.wide_gain
    net.w2[0][1] = b.fine_gain
    net.w2[0][5] = -b.apex_bias      # more room to the left, tighten the line
    net.w2[0][6] = b.apex_bias
    net.w2[0][7] = -b.damping        # counter its own slide

    # o1: target speed as a fraction of top speed.
    #
    # Why this is linear rather than squashed: for a road of half-width w,
    # the distance the nose-ray reaches around a bend of radius R is about
    # sqrt(2*R*w), so R ~ d^2/2w. The grip-limited corner speed is
    # sqrt(grip*R) = d * sqrt(grip/2w) - i.e. safe speed is *proportional*
    # to forward clearance. A linear head can express that exactly.
    # Coefficients least-squares fitted against the grip-limited ideal speed at
    # every sample of every circuit - refit with refit.py whenever the road
    # width or the calendar changes (rms error 0.05 of top speed).
    #
    # The fit was done for the reference chassis, so both terms are rescaled by
    # this car's own physics: safe corner speed goes as sqrt(grip), and the head
    # emits a *fraction of top speed*, so it also scales as 1/top_speed. A model
    # that built a grippier car therefore genuinely commits to faster corners.
    ch = entry.chassis
    phys = math.sqrt(ch.grip / REF_GRIP) * (REF_TOP_SPEED / ch.top_speed)
    net.w2[1][2] = 1.97 * b.confidence * phys
    net.w2[1][4] = -0.25 * b.caution     # damper: bleeds speed when fast and blind
    net.w2[1][8] = -0.55                 # off the road, slow down
    net.w2[1][9] = -0.30 * (1.35 - entry.temper.aggression)
    net.b2[1] = 0.10 * phys

    net.jitter(random.Random(entry.seed), 0.006)
    return net


class Driver:
    """Wraps a brain in reflexes: control lag, jitter and a recovery mode."""

    def __init__(self, entry, track, net=None):
        self.entry = entry
        self.track = track
        self.net = net or build_brain(entry)
        self.vision = Vision(entry.sensor_count, entry.sensor_range, track.half_width)
        self.net_in = entry.sensor_count + N_EXTRA_FEATURES
        self.rng = random.Random(entry.seed ^ 0x5A5A)
        self.steer = 0.0
        self.throttle = 0.0
        self.brake = 0.0
        self.target_speed = 0.0
        self.slide = 0.0
        self.stuck_timer = 0.0
        self.recovering = False
        self.wrong_way = False
        self.reverse_timer = 0.0

    def _traffic_signal(self, car, rivals):
        """1.0 = someone is right in front, 0.0 = clear air."""
        worst = 0.0
        fx, fy = math.cos(car.heading), math.sin(car.heading)
        for other in rivals:
            if other is car or other.finished:
                continue
            dx, dy = other.x - car.x, other.y - car.y
            fwd = dx * fx + dy * fy
            if fwd <= 0:
                continue
            if abs(-dx * fy + dy * fx) > 34:
                continue
            d = math.hypot(dx, dy)
            if d < cfg.PROXIMITY_RANGE:
                worst = max(worst, 1.0 - d / cfg.PROXIMITY_RANGE)
        return worst

    def _lap_direction_error(self, car):
        """Signed heading error against the direction the lap actually runs.

        The network cannot work this out for itself: a road looks identical
        forwards and backwards through a fan of range sensors. A real driver
        knows which way round the circuit goes, so the car is told.
        """
        i, _ = self.track.nearest(car.x, car.y)
        tx, ty = self.track.tangent[i]
        along = math.cos(car.heading) * tx + math.sin(car.heading) * ty
        err = (math.atan2(ty, tx) - car.heading + math.pi) % (2 * math.pi) - math.pi
        return along, err

    def _heading_error_to_centre(self, car):
        idx, _ = self.track.nearest(car.x, car.y)
        cx, cy = self.track.center[idx]
        want = math.atan2(cy - car.y, cx - car.x)
        return (want - car.heading + math.pi) % (2 * math.pi) - math.pi

    def think(self, car, rivals, dt):
        ch = self.entry.chassis
        tm = self.entry.temper
        br = self.entry.brain

        obstacles = [(o.x, o.y, RIVAL_RADIUS) for o in rivals
                     if o is not car and (o.x - car.x) ** 2 + (o.y - car.y) ** 2 < RIVAL_SIGHT_2]
        sensors = self.vision.scan(self.track, car.x, car.y, car.heading, obstacles)
        occ = self.vision.occlusion
        speed_norm = clamp(car.speed / ch.top_speed, 0.0, 1.4)
        slip = clamp(car.lateral_speed / 220.0, -1.5, 1.5)
        traffic = self._traffic_signal(car, rivals)
        on = self.track.on_track(car.x, car.y)
        # ~0.7s memory of how loose the car has been feeling
        self.slide += (min(car.slip_ratio, 1.0) - self.slide) * (1.0 - math.exp(-dt / 0.7))

        features = (list(sensors) + list(occ)
                    + [speed_norm, slip, self.slide, traffic, 0.0 if on else 1.0])
        steer_raw, speed_raw = self.net.forward(features)

        want_steer = clamp(steer_raw, -1.0, 1.0)
        target = clamp(speed_raw, 0.16, 1.12) * ch.top_speed

        # --- safety systems -------------------------------------------------
        # Off the road every ray reads short, so the network's vision is
        # useless. A separate low-level system aims the car back at tarmac.
        if not on:
            self.recovering = True
            want_steer = clamp(self._heading_error_to_centre(car) * 1.5 * br.recovery,
                               -1.0, 1.0)
            target = min(target, ch.top_speed * 0.34)
        elif self.recovering and car.speed > ch.top_speed * 0.28:
            self.recovering = False

        # Facing the wrong way round the lap. Hysteresis so a big slide does
        # not flip this on and off; once engaged, slow right down and turn.
        along, dir_err = self._lap_direction_error(car)
        if self.wrong_way:
            if along > 0.35:
                self.wrong_way = False
        elif along < -0.15:
            self.wrong_way = True
        if self.wrong_way:
            want_steer = clamp(dir_err * 2.0, -1.0, 1.0)
            target = min(target, ch.top_speed * 0.22)

        # Beached: back up and try again. Only when something solid is in the
        # way - being held up by the car in front is not being stuck, and
        # reversing out of a start-line queue used to spin cars round to face
        # the wrong way for the rest of the race.
        nose = self.vision.raw[self.vision.count // 2]
        jammed = (not on) or nose < 46.0
        self.stuck_timer = self.stuck_timer + dt if (car.speed < 22.0 and jammed) else 0.0
        if self.stuck_timer > 1.1 and self.reverse_timer <= 0.0:
            self.reverse_timer = 0.85 / max(0.5, br.recovery)
            self.stuck_timer = 0.0

        reversing = self.reverse_timer > 0.0
        if reversing:
            self.reverse_timer -= dt
            # steer while backing up so the car comes out pointing down the lap
            want_steer = clamp(-dir_err * 1.4, -1.0, 1.0)

        # --- longitudinal control law ---------------------------------------
        err = target - car.speed
        if reversing:
            throttle = brake = 0.0
        elif err >= 0:
            throttle = clamp(err / (0.10 * ch.top_speed), 0.0, 1.0) * br.throttle_gain
            brake = 0.0
        else:
            throttle = 0.0
            brake = clamp(-err / (0.16 * ch.top_speed), 0.0, 1.0) * br.brake_gain
        throttle = clamp(throttle, 0.0, 1.0)
        brake = clamp(brake, 0.0, 1.0)

        # In traffic an aggressive model keeps its foot in; a cautious one lifts.
        if traffic > 0.35 and not reversing:
            throttle *= clamp(0.55 + tm.aggression * 0.6, 0.0, 1.0)

        # --- control filter: the model cannot snap to a new input ------------
        jitter = self.rng.gauss(0.0, tm.noise * (1.4 - tm.consistency))
        want_steer = clamp(want_steer + jitter, -1.0, 1.0)
        a = 1.0 - math.exp(-dt / max(1e-3, tm.reaction))
        self.steer += (want_steer - self.steer) * a
        self.throttle += (throttle - self.throttle) * a
        self.brake += (brake - self.brake) * a
        self.target_speed = target
        car.reversing = reversing
        return self.steer, self.throttle, self.brake
