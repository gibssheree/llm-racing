"""Circuit generation: Catmull-Rom centreline, edges, spatial hash, lap logic."""
import math

from . import config as cfg
from .tracks import DEFAULT
from .vec import dist2, norm, sub




def _catmull_rom(p0, p1, p2, p3, t):
    t2 = t * t
    t3 = t2 * t
    x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t
               + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
               + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
    y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t
               + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
               + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
    return (x, y)


class Track:
    """A closed circuit sampled into a dense centreline.

    Everything the game needs to know about geometry lives here: whether a
    point is on tarmac, how far along the lap it is, and where the edges are.
    """

    def __init__(self, control_points=None, half_width=cfg.TRACK_HALF_WIDTH,
                 build_mask=True):
        # one source of truth for layouts: llmrace/tracks.py
        self.control = list(control_points or DEFAULT.control)
        self.half_width = half_width
        self.center = []      # dense centreline points
        self.tangent = []     # unit forward vector at each sample
        self.normal = []      # unit left-hand normal at each sample
        self.left = []        # outer edge polyline
        self.right = []       # inner edge polyline
        self.arc = []         # cumulative distance at each sample
        self.curvature = []   # |dtheta/ds| at each sample
        self._grid = {}
        self._want_mask = build_mask
        self._build()

    # ------------------------------------------------------------ building --
    @staticmethod
    def _smooth(pts, passes, lam=0.45):
        """Laplacian relaxation on a closed polyline - kills spline kinks."""
        for _ in range(passes):
            m = len(pts)
            pts = [(pts[i][0] + lam * 0.5 * (pts[(i - 1) % m][0] + pts[(i + 1) % m][0] - 2 * pts[i][0]),
                    pts[i][1] + lam * 0.5 * (pts[(i - 1) % m][1] + pts[(i + 1) % m][1] - 2 * pts[i][1]))
                   for i in range(m)]
        return pts

    @staticmethod
    def _resample(pts, spacing):
        """Re-space a closed polyline evenly by arc length.

        Uniform spacing matters: the spatial hash, the lap-progress index and
        the AI's distance estimates all assume one sample == one fixed step.
        """
        m = len(pts)
        segs = [math.dist(pts[i], pts[(i + 1) % m]) for i in range(m)]
        total = sum(segs)
        n = max(16, int(round(total / spacing)))
        step = total / n
        out, i, acc = [], 0, 0.0
        for k in range(n):
            want = k * step
            while acc + segs[i] < want:
                acc += segs[i]
                i = (i + 1) % m
            t = (want - acc) / segs[i]
            a, b = pts[i], pts[(i + 1) % m]
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
        return out

    def _build(self):
        n = len(self.control)
        pts = []
        for i in range(n):
            p0 = self.control[(i - 1) % n]
            p1 = self.control[i]
            p2 = self.control[(i + 1) % n]
            p3 = self.control[(i + 2) % n]
            for s in range(cfg.SAMPLES_PER_SEGMENT):
                pts.append(_catmull_rom(p0, p1, p2, p3, s / cfg.SAMPLES_PER_SEGMENT))

        pts = self._smooth(pts, cfg.SMOOTH_PASSES)
        pts = self._resample(pts, cfg.SAMPLE_SPACING)
        self.center = pts
        m = len(pts)

        for i in range(m):
            nxt = pts[(i + 1) % m]
            prv = pts[(i - 1) % m]
            t = norm(sub(nxt, prv))
            self.tangent.append(t)
            self.normal.append((-t[1], t[0]))   # left-hand normal

        total = 0.0
        for i in range(m):
            self.arc.append(total)
            total += math.dist(pts[i], pts[(i + 1) % m])
        self.length = total

        for i in range(m):
            a = self.tangent[(i - 1) % m]
            b = self.tangent[(i + 1) % m]
            ang = abs(math.atan2(a[0] * b[1] - a[1] * b[0], a[0] * b[0] + a[1] * b[1]))
            ds = math.dist(pts[(i - 1) % m], pts[(i + 1) % m]) or 1e-6
            self.curvature.append(ang / ds)

        hw = self.half_width
        for i in range(m):
            nx, ny = self.normal[i]
            cx, cy = pts[i]
            self.left.append((cx + nx * hw, cy + ny * hw))
            self.right.append((cx - nx * hw, cy - ny * hw))

        cell = cfg.GRID_CELL
        for i, (x, y) in enumerate(pts):
            key = (int(x // cell), int(y // cell))
            self._grid.setdefault(key, []).append(i)

        if self._want_mask:
            self._build_mask()

        self.spacing = self.length / m
        xs = [p[0] for p in self.left] + [p[0] for p in self.right]
        ys = [p[1] for p in self.left] + [p[1] for p in self.right]
        pad = 60.0
        self.bounds = (min(xs) - pad, min(ys) - pad,
                       max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad)
        # curvature smoothed over ~120px, used to decide where kerbs belong
        k = self.curvature
        span = 4
        self.corner = [sum(k[(i + d) % m] for d in range(-span, span + 1)) / (2 * span + 1)
                       for i in range(m)]
        self.start_index = self._pick_start()
        i = self.start_index
        self.finish_line = (self.left[i], self.right[i])

    def _pick_start(self):
        """Put the start line on the longest straight.

        The grid forms up *behind* the line, so what matters is that the road
        is open through the samples leading into it - a start line halfway
        round a hairpin looks wrong and lines the cars up in the scenery.
        """
        if not self._want_mask:
            return 0
        m = len(self.center)
        fwd = [self.raycast(*self.center[i], *self.tangent[i]) for i in range(m)]
        run = max(6, int(260 / self.spacing))       # grid length, in samples
        best, best_i = -1.0, 0
        for i in range(m):
            score = min(fwd[(i - k) % m] for k in range(run))
            if score > best:
                best, best_i = score, i
        return best_i

    def _build_mask(self):
        """Rasterise the tarmac into a coarse bitmap.

        Sensors fire tens of thousands of point-in-road queries per second.
        Walking the spatial hash for each one is far too slow, so the road is
        stamped once into a flat bytearray and every later query is a single
        index lookup.
        """
        res = cfg.MASK_RES
        self.mask_res = res
        self.mask_w = int(cfg.WORLD_W // res) + 2
        self.mask_h = int(cfg.WORLD_H // res) + 2
        self.mask = bytearray(self.mask_w * self.mask_h)

        r_cells = int(self.half_width // res)
        disc = []
        for dy in range(-r_cells, r_cells + 1):
            for dx in range(-r_cells, r_cells + 1):
                if (dx * res) ** 2 + (dy * res) ** 2 <= self.half_width ** 2:
                    disc.append((dx, dy))

        mw, mh, mask = self.mask_w, self.mask_h, self.mask
        for k in range(0, len(self.center), 2):   # every other sample is plenty
            cx = int(self.center[k][0] // res)
            cy = int(self.center[k][1] // res)
            for dx, dy in disc:
                gx, gy = cx + dx, cy + dy
                if 0 <= gx < mw and 0 <= gy < mh:
                    mask[gy * mw + gx] = 1

    # ------------------------------------------------------------- queries --
    def _candidates(self, x, y, ring=1):
        cell = cfg.GRID_CELL
        cx, cy = int(x // cell), int(y // cell)
        out = []
        for gx in range(cx - ring, cx + ring + 1):
            for gy in range(cy - ring, cy + ring + 1):
                bucket = self._grid.get((gx, gy))
                if bucket:
                    out.extend(bucket)
        return out

    def nearest(self, x, y):
        """Return (index, distance) of the closest centreline sample."""
        best_i, best_d2 = -1, float("inf")
        ring = 1
        while ring <= 4:
            for i in self._candidates(x, y, ring):
                d2 = dist2(self.center[i], (x, y))
                if d2 < best_d2:
                    best_d2, best_i = d2, i
            if best_i >= 0:
                break
            ring += 1
        if best_i < 0:
            for i, p in enumerate(self.center):
                d2 = dist2(p, (x, y))
                if d2 < best_d2:
                    best_d2, best_i = d2, i
        return best_i, math.sqrt(best_d2)

    def on_track(self, x, y):
        """Fast tarmac test - one bitmap lookup."""
        gx = int(x) // self.mask_res
        gy = int(y) // self.mask_res
        if gx < 0 or gy < 0 or gx >= self.mask_w or gy >= self.mask_h:
            return False
        return self.mask[gy * self.mask_w + gx] == 1

    def signed_offset(self, x, y):
        """Lateral offset from the centreline; positive = left of travel."""
        i, _ = self.nearest(x, y)
        nx, ny = self.normal[i]
        dx, dy = x - self.center[i][0], y - self.center[i][1]
        return dx * nx + dy * ny, i

    def progress(self, x, y):
        """Position around the lap, 0..1, plus the centreline index."""
        i, _ = self.nearest(x, y)
        return self.arc[i] / self.length, i

    def raycast(self, x, y, dx, dy, max_range=cfg.SENSOR_RANGE, step=cfg.SENSOR_STEP):
        """March a ray until it leaves the tarmac. Returns distance in pixels.

        Inlined against the bitmap: this is the hottest loop in the game.
        """
        mask, mw, mh, res = self.mask, self.mask_w, self.mask_h, self.mask_res
        d = step
        while d < max_range:
            gx = int(x + dx * d) // res
            gy = int(y + dy * d) // res
            if gx < 0 or gy < 0 or gx >= mw or gy >= mh or not mask[gy * mw + gx]:
                return d
            d += step
        return max_range

    def heading_at(self, index):
        t = self.tangent[index % len(self.center)]
        return math.atan2(t[1], t[0])

    def sample_count(self):
        return len(self.center)

    # ------------------------------------------------------- starting grid --
    def grid_slots(self, count):
        """Poles laid out two-by-two behind the start line, on the tarmac."""
        m = len(self.center)
        slots = []
        for k in range(count):
            row = k // 2
            col = -1 if (k % 2 == 0) else 1
            back = 50 + row * cfg.GRID_ROW_GAP
            idx = self.start_index
            travelled = 0.0
            while travelled < back:
                nxt = (idx - 1) % m
                travelled += math.dist(self.center[idx], self.center[nxt])
                idx = nxt
            cx, cy = self.center[idx]
            nx, ny = self.normal[idx]
            off = col * cfg.GRID_COL_GAP
            slots.append(((cx + nx * off, cy + ny * off), self.heading_at(idx), idx))
        return slots
