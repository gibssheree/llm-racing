"""The car: physics integration, lap bookkeeping, and contact with rivals."""
import math

from . import config as cfg
from .ai import Driver
from .vec import clamp

RUNOFF = 52.0            # width of grass before the barrier. Kept tight so that
                         # two stretches of track running close together do not
                         # end up sharing run-off.
SKID_HISTORY = 90        # how many skid points a car remembers


class Car:
    def __init__(self, entry, track, grid_slot, index):
        self.entry = entry
        self.track = track
        self.index = index
        self.driver = Driver(entry, track)

        (x, y), heading, idx = grid_slot
        self.x, self.y = x, y
        self.heading = heading
        self.vx = self.vy = 0.0
        self.speed = 0.0
        self.lateral_speed = 0.0
        self.grid_index = idx

        # controls, filled in by the driver each frame
        self.throttle = self.brake = self.steer = 0.0
        self.reversing = False
        self.on_road = True
        self.slip_ratio = 0.0

        # Race state. Cars line up *behind* the line, so they start on lap -1:
        # the first crossing promotes them to lap 0 and starts their clock.
        # Every crossing after that is a completed timed lap.
        self.lap = -1
        self.progress = track.progress(x, y)[0]
        self.sectors = [True, True]   # both already cleared: the grid is behind the line
        self.lap_start = 0.0
        self.last_lap = None
        self.best_lap = None
        self.lap_times = []
        self.finished = False
        self.finish_time = None
        self.race_position = index + 1
        self.total_distance = 0.0
        self.skids = []

    # ---------------------------------------------------------------- info --
    @property
    def name(self):
        return self.entry.name

    @property
    def color(self):
        return self.entry.color

    def race_progress(self):
        """Laps completed plus fraction of the current lap - the sort key."""
        return self.lap + self.progress

    @property
    def display_lap(self):
        """1-based lap number for the HUD."""
        return max(1, self.lap + 1)

    # --------------------------------------------------------------- update --
    def think(self, rivals, dt):
        if self.finished:
            self.throttle, self.brake = 0.0, 0.6
            return
        self.steer, self.throttle, self.brake = self.driver.think(self, rivals, dt)

    def step(self, dt, race_time):
        ch = self.entry.chassis
        sub = cfg.SUBSTEPS
        h = dt / sub
        for _ in range(sub):
            self._integrate(h, ch)
        self._update_lap(race_time)

    def _integrate(self, dt, ch):
        # Basis at the start of the step. `right` is the car's right-hand axis
        # (screen y grows downwards, so +heading rotates clockwise).
        fx, fy = math.cos(self.heading), math.sin(self.heading)
        rx, ry = -fy, fx

        v_fwd = self.vx * fx + self.vy * fy
        v_lat = self.vx * rx + self.vy * ry

        self.on_road = self.track.on_track(self.x, self.y)
        sn = math.hypot(self.vx, self.vy) / ch.top_speed

        # --- longitudinal ----------------------------------------------------
        # Resistance is calibrated so that full throttle settles exactly on
        # top_speed: power = drag*v^2 + roll*v at v = top_speed. `ch.drag` then
        # only shapes *how* the car gets there, not where it ends up.
        roll_c = 0.12
        drag_c = max(1e-6, (ch.power - roll_c * ch.top_speed) / (ch.top_speed ** 2))
        drive = -ch.power * 0.45 if self.reversing else ch.power * self.throttle
        accel = drive - drag_c * ch.drag * v_fwd * abs(v_fwd) - roll_c * v_fwd
        if not self.on_road:
            accel -= cfg.OFFTRACK_DRAG * v_fwd
        if self.brake > 0.0 and abs(v_fwd) > 1.0:
            stop = math.copysign(ch.brake * self.brake, v_fwd)
            if abs(stop) * dt > abs(v_fwd):
                v_fwd, accel = 0.0, 0.0       # brakes stop it, never reverse it
            else:
                accel -= stop
        v_fwd = clamp(v_fwd + accel * dt, -ch.top_speed * 0.35, ch.top_speed)

        self.vx = fx * v_fwd + rx * v_lat
        self.vy = fy * v_fwd + ry * v_lat

        # --- yaw --------------------------------------------------------------
        # Steering authority falls away with speed, so a fast car cannot turn
        # in as sharply as a slow one. This is what makes braking zones matter.
        authority = ch.steer_rate / (1.0 + ch.steer_falloff * sn)
        if abs(v_fwd) < 24.0:
            authority *= abs(v_fwd) / 24.0    # no steering while stationary
        self.heading += self.steer * authority * (1.0 if v_fwd >= 0 else -1.0) * dt

        # --- lateral grip -------------------------------------------------------
        # Crucially the world velocity is *not* rotated with the car. Turning the
        # wheel only points the tyres somewhere new; the tyres then have to drag
        # the existing momentum around, and they can only pull so hard. When the
        # corner demands more than `grip`, the difference shows up as a slide.
        fx, fy = math.cos(self.heading), math.sin(self.heading)
        rx, ry = -fy, fx
        v_fwd = self.vx * fx + self.vy * fy
        v_lat = self.vx * rx + self.vy * ry

        grip = ch.grip * (1.0 + ch.downforce * sn * sn)
        if not self.on_road:
            grip *= cfg.OFFTRACK_GRIP_MULT
        bite = grip * dt
        if abs(v_lat) <= bite:
            v_lat = 0.0
        else:
            v_lat -= math.copysign(bite, v_lat)

        self.vx = fx * v_fwd + rx * v_lat
        self.vy = fy * v_fwd + ry * v_lat
        self.x += self.vx * dt
        self.y += self.vy * dt

        self.speed = math.hypot(self.vx, self.vy)
        self.lateral_speed = v_lat
        self.slip_ratio = abs(v_lat) / max(40.0, self.speed)
        self.total_distance += abs(v_fwd) * dt

        self._barrier()

    def _barrier(self):
        """Keep cars inside the run-off. Hitting it costs a lot of speed."""
        idx, d = self.track.nearest(self.x, self.y)
        limit = self.track.half_width + RUNOFF
        if d <= limit:
            return
        cx, cy = self.track.center[idx]
        nx, ny = (self.x - cx) / d, (self.y - cy) / d
        self.x = cx + nx * limit
        self.y = cy + ny * limit
        vn = self.vx * nx + self.vy * ny
        if vn > 0:
            self.vx -= (1.0 + cfg.WALL_BOUNCE) * vn * nx
            self.vy -= (1.0 + cfg.WALL_BOUNCE) * vn * ny
        self.vx *= 0.72
        self.vy *= 0.72

    def _update_lap(self, race_time):
        p, _ = self.track.progress(self.x, self.y)
        prev = self.progress
        self.progress = p
        # Two sector gates, not one. A car that spins off and rejoins can jump
        # its progress value around; requiring both thirds of the lap to be
        # visited in order stops that from being scored as a flying lap.
        if 0.30 < p < 0.55:
            self.sectors[0] = True
        if self.sectors[0] and 0.62 < p < 0.88:
            self.sectors[1] = True
        if all(self.sectors) and prev > 0.80 and p < 0.20:
            self.sectors = [False, False]
            self.lap += 1
            t = race_time - self.lap_start
            self.lap_start = race_time
            if self.lap > 0:      # lap 0 is the standing start, not a timed lap
                self.last_lap = t
                self.lap_times.append(t)
                if self.best_lap is None or t < self.best_lap:
                    self.best_lap = t

    # ------------------------------------------------------------- contact --
    @staticmethod
    def resolve_contact(a, b):
        dx, dy = b.x - a.x, b.y - a.y
        d = math.hypot(dx, dy)
        r = cfg.COLLISION_RADIUS * 2
        if d >= r or d < 1e-6:
            return False
        nx, ny = dx / d, dy / d
        overlap = r - d
        ma, mb = a.entry.chassis.mass, b.entry.chassis.mass
        total = ma + mb
        a.x -= nx * overlap * (mb / total)
        a.y -= ny * overlap * (mb / total)
        b.x += nx * overlap * (ma / total)
        b.y += ny * overlap * (ma / total)

        rvn = (b.vx - a.vx) * nx + (b.vy - a.vy) * ny
        if rvn > 0:
            return True
        j = -(1.0 + 0.14) * rvn / (1.0 / ma + 1.0 / mb)
        a.vx -= j * nx / ma
        a.vy -= j * ny / ma
        b.vx += j * nx / mb
        b.vy += j * ny / mb
        return True
