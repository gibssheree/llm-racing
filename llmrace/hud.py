"""Broadcast-style overlay: standings, telemetry, minimap, flag screens."""
import math

import pygame

from . import config as cfg
from .vec import clamp

PANEL_BG = (18, 21, 28)
PANEL_EDGE = (46, 52, 66)
GOOD = (86, 200, 130)
WARN = (240, 176, 72)
BAD = (232, 92, 92)


def load_fonts():
    def pick(size, bold=False):
        for name in ("Consolas", "DejaVu Sans Mono", "Courier New"):
            try:
                f = pygame.font.SysFont(name, size, bold=bold)
                if f:
                    return f
            except Exception:
                pass
        return pygame.font.Font(None, size)
    return {
        "tiny": pick(12), "small": pick(14), "body": pick(16),
        "bold": pick(16, True), "big": pick(24, True),
        "huge": pick(64, True), "mega": pick(96, True),
    }


def fmt_time(t):
    if t is None:
        return "--:--.---"
    m = int(t // 60)
    s = t - m * 60
    return f"{m}:{s:06.3f}" if m else f"{s:.3f}"


def fmt_gap(t):
    if t is None:
        return "--"
    return f"+{t:.2f}" if t >= 0 else f"{t:.2f}"


def panel(screen, rect, alpha=214, radius=8):
    surf = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(surf, (*PANEL_BG, alpha), surf.get_rect(), border_radius=radius)
    pygame.draw.rect(surf, (*PANEL_EDGE, 255), surf.get_rect(), 1, border_radius=radius)
    screen.blit(surf, rect.topleft)


def bar(screen, rect, frac, color, bg=(38, 42, 52)):
    pygame.draw.rect(screen, bg, rect, border_radius=3)
    w = int(rect.width * clamp(frac, 0.0, 1.0))
    if w > 0:
        pygame.draw.rect(screen, color, (rect.x, rect.y, w, rect.height), border_radius=3)


# ------------------------------------------------------------- leaderboard --
ROW_H = 30


def draw_standings(screen, fonts, race, focus_key, x=14, y=14, w=286):
    cars = race.standings()
    h = 30 + len(cars) * ROW_H + 8
    rect = pygame.Rect(x, y, w, h)
    panel(screen, rect)

    screen.blit(fonts["bold"].render("CLASSIFICATION", True, cfg.C_TEXT), (x + 12, y + 8))
    lap_txt = f"LAP {min(race.total_laps, max(1, cars[0].display_lap))}/{race.total_laps}"
    r = fonts["small"].render(lap_txt, True, cfg.C_ACCENT)
    screen.blit(r, (x + w - 12 - r.get_width(), y + 10))

    leader = cars[0]
    for i, car in enumerate(cars):
        ry = y + 30 + i * ROW_H
        if car.entry.key == focus_key:
            pygame.draw.rect(screen, (34, 42, 58), (x + 5, ry - 2, w - 10, ROW_H - 2),
                             border_radius=5)
        pygame.draw.rect(screen, car.color, (x + 10, ry + 4, 5, ROW_H - 12), border_radius=2)
        pos = fonts["bold"].render(f"{car.race_position}", True, cfg.C_TEXT)
        screen.blit(pos, (x + 22, ry + 4))
        name = fonts["body"].render(car.name[:17], True,
                                    cfg.C_TEXT if not car.finished else GOOD)
        screen.blit(name, (x + 42, ry + 4))

        if car.finished:
            txt, col = "FIN", GOOD
        elif car is leader:
            txt, col = "LEADER", cfg.C_ACCENT
        else:
            # Gap in laps if lapped, otherwise an estimated time gap.
            # Converted at a single reference pace for the whole field: using
            # each car's own instantaneous speed made the column jump around
            # and put bigger gaps above smaller ones.
            dl = leader.race_progress() - car.race_progress()
            if dl >= 1.0:
                txt, col = f"+{int(dl)}L", cfg.C_TEXT_DIM
            else:
                txt = f"+{dl * race.track.length / race.reference_pace():4.1f}"
                col = cfg.C_TEXT_DIM
        g = fonts["small"].render(txt, True, col)
        screen.blit(g, (x + w - 12 - g.get_width(), ry + 6))


# ----------------------------------------------------------------- minimap --
def draw_minimap(screen, fonts, race, focus_key, size=210, pad=14):
    x = cfg.SCREEN_W - size - pad
    y = pad
    rect = pygame.Rect(x, y, size, size)
    panel(screen, rect)

    track = race.track
    bx, by, bw, bh = track.bounds
    inner = size - 26
    sc = min(inner / bw, inner / bh)
    ox = x + (size - bw * sc) / 2 - bx * sc
    oy = y + (size - bh * sc) / 2 - by * sc

    def to_map(wx, wy):
        return (ox + wx * sc, oy + wy * sc)

    pts = [to_map(*p) for p in track.center[::3]]
    pygame.draw.lines(screen, (70, 76, 90), True, pts, max(2, int(track.half_width * sc)))
    pygame.draw.lines(screen, (44, 48, 58), True, pts, 1)
    s = to_map(*track.center[track.start_index])
    pygame.draw.circle(screen, cfg.C_LINE, (int(s[0]), int(s[1])), 3)

    for car in race.standings()[::-1]:
        mx, my = to_map(car.x, car.y)
        r = 5 if car.entry.key == focus_key else 4
        pygame.draw.circle(screen, (10, 12, 16), (int(mx), int(my)), r + 1)
        pygame.draw.circle(screen, car.color, (int(mx), int(my)), r)


# --------------------------------------------------------------- telemetry --
def draw_telemetry(screen, fonts, car, race, x=14, w=286):
    """What the focused model's brain is doing right now."""
    d = car.driver
    ch = car.entry.chassis
    h = 236
    y = cfg.SCREEN_H - h - 14
    rect = pygame.Rect(x, y, w, h)
    panel(screen, rect)

    pygame.draw.rect(screen, car.color, (x + 10, y + 10, 5, 30), border_radius=2)
    screen.blit(fonts["bold"].render(car.name, True, cfg.C_TEXT), (x + 24, y + 10))
    screen.blit(fonts["tiny"].render(car.entry.vendor.upper(), True, cfg.C_TEXT_DIM),
                (x + 24, y + 28))

    cy = y + 50
    kmh = car.speed * 3.6 / cfg.PX_PER_M
    screen.blit(fonts["big"].render(f"{kmh:5.0f}", True, cfg.C_TEXT), (x + 12, cy))
    screen.blit(fonts["tiny"].render("KM/H", True, cfg.C_TEXT_DIM), (x + 74, cy + 10))
    tgt = d.target_speed * 3.6 / cfg.PX_PER_M
    screen.blit(fonts["small"].render(f"target {tgt:.0f}", True, cfg.C_ACCENT), (x + 118, cy + 6))

    cy += 32
    bar(screen, pygame.Rect(x + 12, cy, w - 24, 5), car.speed / ch.top_speed, car.color)

    cy += 16
    for label, val, col in (("THR", d.throttle, GOOD),
                            ("BRK", d.brake, BAD),
                            ("SLIP", clamp(car.slip_ratio * 2.2, 0, 1), WARN)):
        screen.blit(fonts["tiny"].render(label, True, cfg.C_TEXT_DIM), (x + 12, cy))
        bar(screen, pygame.Rect(x + 48, cy + 2, w - 76, 7), val, col)
        cy += 16

    # steering, drawn as a centred deflection
    screen.blit(fonts["tiny"].render("STEER", True, cfg.C_TEXT_DIM), (x + 12, cy))
    sb = pygame.Rect(x + 48, cy + 2, w - 76, 7)
    pygame.draw.rect(screen, (38, 42, 52), sb, border_radius=3)
    mid = sb.x + sb.width // 2
    sw = int(sb.width / 2 * clamp(d.steer, -1, 1))
    if sw:
        pygame.draw.rect(screen, cfg.C_ACCENT,
                         (min(mid, mid + sw), sb.y, abs(sw), sb.height), border_radius=3)
    pygame.draw.line(screen, (120, 128, 145), (mid, sb.y - 2), (mid, sb.bottom + 2))
    cy += 22

    # the raw sensor vector - this is literally the network's input layer
    screen.blit(fonts["tiny"].render("VISION", True, cfg.C_TEXT_DIM), (x + 12, cy))
    n = d.vision.count
    bw = (w - 24) / n
    top = cy + 14
    for i in range(n):
        v = clamp(d.vision.rival_raw[i] / d.vision.expected[i], 0.0, 1.0)
        bh = int(28 * v)
        bx = int(x + 12 + i * bw)
        col = BAD if d.vision.blocked[i] else (86, 152, 210)
        pygame.draw.rect(screen, (32, 36, 46), (bx, top, int(bw) - 2, 28))
        pygame.draw.rect(screen, col, (bx, top + 28 - bh, int(bw) - 2, bh))
    cy = top + 34

    state = "RECOVERING" if d.recovering else ("REVERSING" if car.reversing else "RACING")
    col = WARN if state != "RACING" else cfg.C_TEXT_DIM
    screen.blit(fonts["tiny"].render(state, True, col), (x + 12, cy))
    lap = f"LAST {fmt_time(car.last_lap)}   BEST {fmt_time(car.best_lap)}"
    r = fonts["tiny"].render(lap, True, cfg.C_TEXT_DIM)
    screen.blit(r, (x + w - 12 - r.get_width(), cy))


# ------------------------------------------------------------ flag screens --
def draw_countdown(screen, fonts, race):
    t = race.timer
    lights = 5 - int(clamp((cfg.COUNTDOWN_SECONDS - t) / (cfg.COUNTDOWN_SECONDS / 5), 0, 5))
    cx = cfg.SCREEN_W // 2
    cy = 120
    for i in range(5):
        on = i >= lights
        col = (208, 46, 46) if on else (46, 30, 32)
        pygame.draw.circle(screen, col, (cx - 128 + i * 64, cy), 22)
        pygame.draw.circle(screen, (16, 18, 24), (cx - 128 + i * 64, cy), 22, 3)
    if t < 0.6:
        r = fonts["huge"].render("GO", True, GOOD)
        screen.blit(r, (cx - r.get_width() // 2, cy + 40))


def draw_banner(screen, fonts, text, sub=None, y=None):
    r = fonts["huge"].render(text, True, cfg.C_TEXT)
    y = y if y is not None else cfg.SCREEN_H // 2 - 90
    x = cfg.SCREEN_W // 2 - r.get_width() // 2
    box = pygame.Rect(x - 30, y - 16, r.get_width() + 60, r.get_height() + (52 if sub else 26))
    panel(screen, box, alpha=230)
    screen.blit(r, (x, y))
    if sub:
        s = fonts["body"].render(sub, True, cfg.C_TEXT_DIM)
        screen.blit(s, (cfg.SCREEN_W // 2 - s.get_width() // 2, y + r.get_height() + 6))


def draw_results(screen, fonts, race):
    w, rows = 620, len(race.cars)
    h = 108 + rows * 30
    x = cfg.SCREEN_W // 2 - w // 2
    y = cfg.SCREEN_H // 2 - h // 2
    panel(screen, pygame.Rect(x, y, w, h), alpha=242)
    screen.blit(fonts["big"].render("RACE RESULT", True, cfg.C_TEXT), (x + 24, y + 18))
    hdr = f"{'POS':<5}{'MODEL':<22}{'VENDOR':<13}{'TIME':>11}{'BEST':>11}"
    screen.blit(fonts["small"].render(hdr, True, cfg.C_TEXT_DIM), (x + 24, y + 54))
    winner = race.standings()[0]
    for i, car in enumerate(race.standings()):
        ry = y + 76 + i * 30
        pygame.draw.rect(screen, car.color, (x + 24, ry + 4, 5, 18), border_radius=2)
        if car is winner:
            result = fmt_time(car.finish_time)
        elif car.finish_time and winner.finish_time:
            result = fmt_gap(car.finish_time - winner.finish_time)
        else:
            # still running when the race was called
            behind = winner.race_progress() - car.race_progress()
            result = f"+{int(behind)}L" if behind >= 1.0 else "NOT CLSF"
        cells = (f"{car.race_position:<5}{car.name:<22}{car.entry.vendor:<13}"
                 f"{result:>11}{fmt_time(car.best_lap):>11}")
        screen.blit(fonts["body"].render(cells, True, cfg.C_TEXT), (x + 38, ry + 3))
    tip = "R restart    ESC quit"
    r = fonts["small"].render(tip, True, cfg.C_TEXT_DIM)
    screen.blit(r, (x + w // 2 - r.get_width() // 2, y + h - 26))
