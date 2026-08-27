"""Everything that draws the world: track surface, camera, cars, effects."""
import math

import pygame

from . import config as cfg
from .car import RUNOFF
from .vec import clamp

CAR_L = cfg.CAR_LENGTH
CAR_W = cfg.CAR_WIDTH


# ------------------------------------------------------------------ camera --
class Camera:
    """Maps world coordinates to screen coordinates, with smooth follow."""

    def __init__(self, view_w, view_h):
        self.view_w, self.view_h = view_w, view_h
        self.x, self.y = cfg.WORLD_W / 2, cfg.WORLD_H / 2
        self.zoom = 1.0
        self.target_zoom = 1.0
        self.offset = (0.0, 0.0)
        self.clamped = True

    def fit(self, bounds, insets=(0, 0, 0, 0)):
        """Zoom and centre so `bounds` fills the screen area left free by the HUD."""
        left, top, right, bottom = insets
        uw = max(80.0, self.view_w - left - right)
        uh = max(80.0, self.view_h - top - bottom)
        bx, by, bw, bh = bounds
        z = min(uw / bw, uh / bh)
        cx = self.view_w / 2 - (left + uw / 2)
        cy = self.view_h / 2 - (top + uh / 2)
        return z, (bx + bw / 2, by + bh / 2), (-cx, -cy)

    def follow(self, wx, wy, dt, snap=False):
        k = 1.0 if snap else 1.0 - math.exp(-dt * 6.0)
        self.x += (wx - self.x) * k
        self.y += (wy - self.y) * k
        # Zoom snaps rather than eases. Each zoom level owns a pre-scaled copy
        # of the circuit; easing through intermediate values would build a new
        # multi-megabyte surface every single frame.
        self.zoom = self.target_zoom
        if self.clamped:
            self._clamp()

    def _clamp(self):
        half_w = self.view_w / (2 * self.zoom)
        half_h = self.view_h / (2 * self.zoom)
        if cfg.WORLD_W <= half_w * 2:
            self.x = cfg.WORLD_W / 2
        else:
            self.x = clamp(self.x, half_w, cfg.WORLD_W - half_w)
        if cfg.WORLD_H <= half_h * 2:
            self.y = cfg.WORLD_H / 2
        else:
            self.y = clamp(self.y, half_h, cfg.WORLD_H - half_h)

    def to_screen(self, wx, wy):
        return ((wx - self.x) * self.zoom + self.view_w / 2 + self.offset[0],
                (wy - self.y) * self.zoom + self.view_h / 2 + self.offset[1])

    def visible_rect(self):
        half_w = self.view_w / (2 * self.zoom)
        half_h = self.view_h / (2 * self.zoom)
        return pygame.Rect(self.x - half_w - self.offset[0] / self.zoom,
                           self.y - half_h - self.offset[1] / self.zoom,
                           half_w * 2, half_h * 2)


# ----------------------------------------------------------- world surface --
def _road_polygons(track):
    """Quads between consecutive left/right edge points."""
    m = len(track.center)
    for i in range(m):
        j = (i + 1) % m
        yield (track.left[i], track.left[j], track.right[j], track.right[i])


def build_world(track):
    """Pre-render the static circuit once. Blitting a slice of this every frame
    is dramatically cheaper than re-drawing 300 road quads."""
    surf = pygame.Surface((cfg.WORLD_W, cfg.WORLD_H)).convert()
    surf.fill(cfg.C_GRASS_A)

    # mown stripes on the grass, so motion reads at speed
    for y in range(0, cfg.WORLD_H, 96):
        pygame.draw.rect(surf, cfg.C_GRASS_B, (0, y, cfg.WORLD_W, 48))

    m = len(track.center)
    hw = track.half_width

    # run-off apron
    for i in range(m):
        j = (i + 1) % m
        nx, ny = track.normal[i]
        mx, my = track.normal[j]
        w = hw + RUNOFF
        quad = [(track.center[i][0] + nx * w, track.center[i][1] + ny * w),
                (track.center[j][0] + mx * w, track.center[j][1] + my * w),
                (track.center[j][0] - mx * w, track.center[j][1] - my * w),
                (track.center[i][0] - nx * w, track.center[i][1] - ny * w)]
        pygame.draw.polygon(surf, (64, 58, 52), quad)

    for quad in _road_polygons(track):
        pygame.draw.polygon(surf, cfg.C_ROAD, quad)

    # Faint patchwork so the asphalt does not read as one flat fill. Kept to a
    # couple of RGB steps: any more and it looks like floor tiles.
    for i in range(0, m, 3):
        j = (i + 3) % m
        nx, ny = track.normal[i]
        mx, my = track.normal[j]
        r = ((i * 7919) % 17) / 17.0
        lo = hw * (-1.0 + 1.4 * r)
        hi = lo + hw * (0.5 + 0.6 * (((i * 104729) % 11) / 11.0))
        shade = (59, 61, 68) if (i // 3) % 2 else (53, 55, 61)
        pygame.draw.polygon(surf, shade, [
            (track.center[i][0] + nx * lo, track.center[i][1] + ny * lo),
            (track.center[j][0] + mx * lo, track.center[j][1] + my * lo),
            (track.center[j][0] + mx * hi, track.center[j][1] + my * hi),
            (track.center[i][0] + nx * hi, track.center[i][1] + ny * hi)])

    # white edge lines
    for side in (1, -1):
        pts = [(track.center[i][0] + track.normal[i][0] * (hw - 4) * side,
                track.center[i][1] + track.normal[i][1] * (hw - 4) * side)
               for i in range(m)]
        pygame.draw.lines(surf, (196, 198, 205), True, pts, 2)

    # kerbs, alternating red/white, only where the corner is actually tight
    kw = cfg.KERB_WIDTH
    for i in range(m):
        j = (i + 1) % m
        # smoothed curvature, so kerbing appears as one continuous run through
        # a corner rather than flickering on and off sample by sample
        if track.corner[i] < 0.0016:
            continue
        col = cfg.C_KERB_A if (i // 5) % 2 == 0 else cfg.C_KERB_B
        for side in (1, -1):
            nx, ny = track.normal[i]
            mx, my = track.normal[j]
            a = hw * side
            b = (hw - kw) * side
            quad = [(track.center[i][0] + nx * a, track.center[i][1] + ny * a),
                    (track.center[j][0] + mx * a, track.center[j][1] + my * a),
                    (track.center[j][0] + mx * b, track.center[j][1] + my * b),
                    (track.center[i][0] + nx * b, track.center[i][1] + ny * b)]
            pygame.draw.polygon(surf, col, quad)

    # faint centre line, dashed
    for i in range(0, m, 6):
        j = (i + 3) % m
        pygame.draw.line(surf, (74, 77, 84), track.center[i], track.center[j], 2)

    _draw_start_line(surf, track)
    return surf


def _draw_start_line(surf, track):
    i = track.start_index
    nx, ny = track.normal[i]
    cx, cy = track.center[i]
    hw = track.half_width
    tx, ty = track.tangent[i]
    rows, cols = 3, 12
    cell = (hw * 2) / cols
    for r in range(rows):
        for c in range(cols):
            if (r + c) % 2:
                continue
            off = hw - c * cell
            base = (cx + nx * off + tx * r * cell, cy + ny * off + ty * r * cell)
            quad = [base,
                    (base[0] - nx * cell, base[1] - ny * cell),
                    (base[0] - nx * cell + tx * cell, base[1] - ny * cell + ty * cell),
                    (base[0] + tx * cell, base[1] + ty * cell)]
            pygame.draw.polygon(surf, cfg.C_LINE, quad)


# --------------------------------------------------------------- car shapes --
def _car_polygon(entry):
    """A flat-topped wedge: nose, shoulders, tail. Built once per model."""
    l, w = CAR_L / 2, CAR_W / 2
    return [(l, 0.0), (l * 0.55, -w), (-l * 0.85, -w),
            (-l, -w * 0.62), (-l, w * 0.62), (-l * 0.85, w), (l * 0.55, w)]


def _rotate(points, ang, ox, oy, scale):
    c, s = math.cos(ang), math.sin(ang)
    return [((x * c - y * s) * scale + ox, (x * s + y * c) * scale + oy)
            for x, y in points]


def _shade(color, k):
    return tuple(int(clamp(v * k, 0, 255)) for v in color)


class CarArt:
    """Per-model livery, worked out once."""

    def __init__(self, entry, number):
        self.entry = entry
        self.number = number
        self.body = _car_polygon(entry)
        self.dark = _shade(entry.color, 0.55)
        self.light = _shade(entry.color, 1.25)
        l, w = CAR_L / 2, CAR_W / 2
        self.cockpit = [(l * 0.30, -w * 0.52), (-l * 0.30, -w * 0.62),
                        (-l * 0.30, w * 0.62), (l * 0.30, w * 0.52)]
        # the stripe runs nose to tail; GPT's black-on-white livery uses it hard
        self.stripe = [(l, -w * 0.30), (l, w * 0.30),
                       (-l, w * 0.30), (-l, -w * 0.30)]
        self.wing = [(-l * 0.94, -w * 1.12), (-l * 0.70, -w * 1.12),
                     (-l * 0.70, w * 1.12), (-l * 0.94, w * 1.12)]


def draw_car(screen, art, car, camera, highlight=False):
    sx, sy = camera.to_screen(car.x, car.y)
    z = camera.zoom
    if sx < -60 or sy < -60 or sx > camera.view_w + 60 or sy > camera.view_h + 60:
        return
    h = car.heading

    if highlight:
        pygame.draw.circle(screen, _shade(art.entry.color, 0.45),
                           (int(sx), int(sy)), int(26 * z), max(1, int(2 * z)))

    shadow = _rotate(art.body, h, sx + 3 * z, sy + 4 * z, z)
    pygame.draw.polygon(screen, (8, 10, 14), shadow)

    pygame.draw.polygon(screen, art.dark, _rotate(art.wing, h, sx, sy, z))
    pygame.draw.polygon(screen, art.entry.color, _rotate(art.body, h, sx, sy, z))
    if z > 0.45:
        pygame.draw.polygon(screen, art.entry.accent, _rotate(art.stripe, h, sx, sy, z))
        pygame.draw.polygon(screen, art.dark, _rotate(art.cockpit, h, sx, sy, z))
    pygame.draw.polygon(screen, _shade(art.entry.color, 0.35),
                        _rotate(art.body, h, sx, sy, z), max(1, int(1.6 * z)))


def draw_sensors(screen, car, camera, alpha_surface):
    """Draw the focused car's vision fan: what the network is actually reading."""
    v = car.driver.vision
    sx, sy = camera.to_screen(car.x, car.y)
    z = camera.zoom
    for i, a in enumerate(v.angles):
        th = car.heading + a
        d = v.rival_raw[i]
        ex, ey = camera.to_screen(car.x + math.cos(th) * d, car.y + math.sin(th) * d)
        col = (255, 120, 110, 150) if v.blocked[i] else (110, 200, 255, 70)
        pygame.draw.line(alpha_surface, col, (sx, sy), (ex, ey), 1)
        pygame.draw.circle(alpha_surface, col, (int(ex), int(ey)), max(2, int(3 * z)))


class SkidMarks:
    """A rolling buffer of tyre marks. Drawn in world space, culled by camera."""

    def __init__(self, limit=1400):
        self.limit = limit
        self.marks = []

    def emit(self, car):
        if car.slip_ratio < 0.18 or car.speed < 60:
            return
        fx, fy = math.cos(car.heading), math.sin(car.heading)
        rx, ry = -fy, fx
        half = CAR_W * 0.42
        strength = clamp((car.slip_ratio - 0.18) * 2.4, 0.0, 1.0)
        for side in (-1, 1):
            px = car.x - fx * CAR_L * 0.3 + rx * half * side
            py = car.y - fy * CAR_L * 0.3 + ry * half * side
            self.marks.append((px, py, strength))
        if len(self.marks) > self.limit:
            del self.marks[:len(self.marks) - self.limit]

    def draw(self, screen, camera):
        rect = camera.visible_rect()
        z = camera.zoom
        r = max(1, int(2.2 * z))
        for x, y, s in self.marks:
            if not rect.collidepoint(x, y):
                continue
            sx, sy = camera.to_screen(x, y)
            g = int(26 + 22 * (1.0 - s))
            pygame.draw.circle(screen, (g, g, g + 3), (int(sx), int(sy)), r)
