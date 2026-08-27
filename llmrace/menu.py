"""Front-end screens: main menu, track picker, grid picker, settings."""
import pygame

from . import config as cfg
from . import ui
from .drivers import ROSTER
from .tracks import PRESETS, preview_points, by_key as track_by_key

MAIN, TRACKS, GRID, SETTINGS = "main", "tracks", "grid", "settings"
MIN_CARS = 4


class Settings:
    """Everything the front end can change. The Game reads this to build a race."""

    def __init__(self):
        self.track_key = PRESETS[0].key
        self.car_keys = [e.key for e in ROSTER]
        self.laps = PRESETS[0].laps
        self.show_sensors = True
        self.show_telemetry = True
        self.show_skids = True
        self.leader_cam = True

    @property
    def track(self):
        return track_by_key(self.track_key)

    def entries(self):
        return [e for e in ROSTER if e.key in self.car_keys]


def draw_track_shape(screen, control, box, colour, width=3, fill_bg=True):
    """Fit a circuit outline into `box`."""
    pts = preview_points(control)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    bw = max(1.0, max(xs) - min(xs))
    bh = max(1.0, max(ys) - min(ys))
    pad = 14
    sc = min((box.width - pad * 2) / bw, (box.height - pad * 2) / bh)
    ox = box.x + (box.width - bw * sc) / 2 - min(xs) * sc
    oy = box.y + (box.height - bh * sc) / 2 - min(ys) * sc
    if fill_bg:
        pygame.draw.rect(screen, (22, 26, 33), box, border_radius=6)
    scaled = [(ox + x * sc, oy + y * sc) for x, y in pts]
    pygame.draw.lines(screen, (52, 58, 70), True, scaled, width + 6)
    pygame.draw.lines(screen, colour, True, scaled, width)
    pygame.draw.circle(screen, (232, 234, 240), (int(scaled[0][0]), int(scaled[0][1])), 4)


class Menu:
    def __init__(self, settings, on_start, on_quit):
        self.s = settings
        self.on_start = on_start
        self.on_quit = on_quit
        self.screen = MAIN
        self.widgets = []
        self.notice = ""
        self.build()

    # ------------------------------------------------------------- plumbing --
    def go(self, screen):
        self.screen = screen
        self.notice = ""
        self.build()

    def build(self):
        self.widgets = []
        getattr(self, "_build_" + self.screen)()
        if self.screen != MAIN:
            # top right, clear of the content: the circuit grid runs the full
            # width of the screen and a bottom-left button sat on top of it
            self.widgets.append(ui.Button((cfg.SCREEN_W - 176, 30, 136, 42),
                                          "BACK", lambda: self.go(MAIN), tip="esc"))

    def handle(self, event):
        if event.type == pygame.MOUSEMOTION:
            for w in self.widgets:
                w.hover(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for w in self.widgets:
                if w.click(event.pos):
                    return True
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE and self.screen != MAIN:
                self.go(MAIN)
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.screen == MAIN:
                self.on_start()
                return True
        return False

    def draw(self, screen, fonts):
        veil = pygame.Surface((cfg.SCREEN_W, cfg.SCREEN_H), pygame.SRCALPHA)
        veil.fill((8, 10, 14, 205))
        screen.blit(veil, (0, 0))
        getattr(self, "_draw_" + self.screen)(screen, fonts)
        for w in self.widgets:
            w.draw(screen, fonts)
        if self.notice:
            r = fonts["small"].render(self.notice, True, ui.BAD)
            screen.blit(r, (cfg.SCREEN_W // 2 - r.get_width() // 2, cfg.SCREEN_H - 64))

    @staticmethod
    def _heading(screen, fonts, title, sub):
        screen.blit(fonts["big"].render(title, True, ui.TEXT), (40, 34))
        screen.blit(fonts["small"].render(sub, True, ui.DIM), (40, 64))
        pygame.draw.line(screen, ui.EDGE, (40, 88), (cfg.SCREEN_W - 40, 88))

    # ----------------------------------------------------------- main menu --
    def _build_main(self):
        cx = cfg.SCREEN_W // 2
        y = 250
        n = len(self.s.car_keys)
        self.widgets += [
            ui.Button((cx - 170, y, 340, 60), "START RACE", self.on_start, primary=True,
                      sub=f"{n} cars   {self.s.laps} laps   {self.s.track.name}"),
            ui.Button((cx - 170, y + 76, 165, 52), "CIRCUIT", lambda: self.go(TRACKS),
                      sub=self.s.track.name),
            ui.Button((cx + 5, y + 76, 165, 52), "GRID", lambda: self.go(GRID),
                      sub=f"{n} of {len(ROSTER)} entered"),
            ui.Button((cx - 170, y + 138, 165, 52), "SETTINGS", lambda: self.go(SETTINGS),
                      sub=f"{self.s.laps} laps"),
            ui.Button((cx + 5, y + 138, 165, 52), "QUIT", self.on_quit),
        ]

    def _draw_main(self, screen, fonts):
        cx = cfg.SCREEN_W // 2
        t = fonts["mega"].render(cfg.TITLE, True, ui.TEXT)
        screen.blit(t, (cx - t.get_width() // 2, 92))
        sub = "every car is a different language model - its own engine, grip and driving brain"
        r = fonts["body"].render(sub, True, ui.DIM)
        screen.blit(r, (cx - r.get_width() // 2, 178))

        box = pygame.Rect(cfg.SCREEN_W - 300, 250, 240, 190)
        draw_track_shape(screen, self.s.track.control, box, ui.ACCENT)
        r = fonts["small"].render(self.s.track.name, True, ui.TEXT)
        screen.blit(r, (box.centerx - r.get_width() // 2, box.bottom + 10))

        x, y = 60, 262
        screen.blit(fonts["small"].render("ON THE GRID", True, ui.DIM), (x, y - 24))
        for e in self.s.entries():
            pygame.draw.rect(screen, e.color, (x, y + 3, 6, 16), border_radius=2)
            pygame.draw.rect(screen, e.accent, (x, y + 3, 6, 6), border_radius=2)
            screen.blit(fonts["body"].render(e.name, True, ui.TEXT), (x + 16, y))
            if getattr(e, "submitted", False):
                mark = fonts["tiny"].render("model-designed", True, ui.OK)
                screen.blit(mark, (x + 24 + fonts["body"].size(e.name)[0], y + 3))
            y += 26

    # -------------------------------------------------------- track picker --
    def _build_tracks(self):
        # six circuits do not fit across the screen, so lay them out in a grid
        per_row = 3
        w, h, gap = 400, 300, 22
        rows = (len(PRESETS) + per_row - 1) // per_row
        for i, p in enumerate(PRESETS):
            col, row = i % per_row, i // per_row
            wide = min(per_row, len(PRESETS) - row * per_row)
            total = wide * w + (wide - 1) * gap
            x0 = cfg.SCREEN_W // 2 - total // 2
            y0 = (cfg.SCREEN_H - 110 - rows * h - (rows - 1) * gap) // 2 + 110
            self.widgets.append(
                ui.Hotspot((x0 + col * (w + gap), y0 + row * (h + gap), w, h),
                           self._pick_track(p.key)))

    def _pick_track(self, key):
        def go():
            self.s.track_key = key
            self.s.laps = track_by_key(key).laps
            self.go(MAIN)
        return go

    def _draw_tracks(self, screen, fonts):
        self._heading(screen, fonts, "CIRCUIT",
                      f"{len(PRESETS)} layouts, each one favouring a different kind of car")
        for w, p in zip(self.widgets, PRESETS):
            r = w.rect
            chosen = p.key == self.s.track_key
            if chosen or w.hot:
                pygame.draw.rect(screen, ui.FILL_ON if chosen else ui.FILL_HOT, r,
                                 border_radius=7)
            pygame.draw.rect(screen, ui.ACCENT if chosen else (ui.EDGE_ON if w.hot else ui.EDGE),
                             r, 2 if chosen else 1, border_radius=7)
            draw_track_shape(screen, p.control,
                             pygame.Rect(r.x + 12, r.y + 12, r.width - 24, 176),
                             ui.ACCENT if chosen else (150, 158, 175))
            screen.blit(fonts["bold"].render(p.name, True, ui.TEXT), (r.x + 16, r.y + 198))
            line, ly = "", r.y + 220
            for word in p.blurb.split():
                trial = (line + " " + word).strip()
                if fonts["tiny"].size(trial)[0] > r.width - 32:
                    screen.blit(fonts["tiny"].render(line, True, ui.DIM), (r.x + 16, ly))
                    line, ly = word, ly + 15
                else:
                    line = trial
            screen.blit(fonts["tiny"].render(line, True, ui.DIM), (r.x + 16, ly))
            st = p.stats or {}
            facts = f"{p.laps} laps   {st.get('length', 0)/1000:.1f}k px"
            screen.blit(fonts["tiny"].render(facts, True,
                                             ui.ACCENT if chosen else ui.FAINT),
                        (r.x + 16, r.bottom - 40))
            shape = (f"{st.get('turns', 0)} direction changes   "
                     f"{st.get('flat_out', 0)*100:.0f}% flat out")
            screen.blit(fonts["tiny"].render(shape, True, ui.FAINT),
                        (r.x + 16, r.bottom - 24))

    # --------------------------------------------------------- grid picker --
    def _build_grid(self):
        for i, e in enumerate(ROSTER):
            self.widgets.append(
                ui.Hotspot((150, 128 + i * 52, cfg.SCREEN_W - 300, 46),
                           self._toggle_car(e.key)))
        self.widgets.append(ui.Button((cfg.SCREEN_W - 350, cfg.SCREEN_H - 74, 140, 44),
                                      "ENTER ALL", self._all_cars))
        self.widgets.append(ui.Button((cfg.SCREEN_W - 190, cfg.SCREEN_H - 74, 150, 44),
                                      "DONE", lambda: self.go(MAIN), primary=True))

    def _all_cars(self):
        self.s.car_keys = [e.key for e in ROSTER]
        self.notice = ""

    def _toggle_car(self, key):
        def go():
            keys = self.s.car_keys
            if key in keys:
                if len(keys) <= MIN_CARS:
                    self.notice = f"a race needs at least {MIN_CARS} cars"
                    return
                keys.remove(key)
            else:
                keys.append(key)
            self.notice = ""
        return go

    def _draw_grid(self, screen, fonts):
        self._heading(screen, fonts, "GRID",
                      f"click to enter or withdraw a model - minimum {MIN_CARS}, "
                      f"currently {len(self.s.car_keys)}")
        # right-aligned stat columns, pushed far enough right that the
        # tagline in the middle of each row has somewhere to live
        cols = [("PWR", 858), ("TOP", 920), ("BRK", 982), ("GRIP", 1048),
                ("STEER", 1118), ("EYES", 1202)]
        tag_limit = 858 - 64 - 344 - 150
        for label, cx in cols:
            r = fonts["tiny"].render(label, True, ui.FAINT)
            screen.blit(r, (cx - r.get_width(), 108))
        for w, e in zip(self.widgets, ROSTER):
            r = w.rect
            on = e.key in self.s.car_keys
            bg = ui.FILL_ON if on else (22, 25, 32)
            if w.hot:
                bg = ui.shade(bg, 1.45)
            pygame.draw.rect(screen, bg, r, border_radius=7)
            pygame.draw.rect(screen, ui.ACCENT if on else (ui.EDGE_ON if w.hot else ui.EDGE),
                             r, 2 if on else 1, border_radius=7)
            box = pygame.Rect(r.x + 14, r.centery - 10, 20, 20)
            pygame.draw.rect(screen, ui.OK if on else (30, 34, 42), box, border_radius=4)
            pygame.draw.rect(screen, ui.OK if on else ui.EDGE, box, 1, border_radius=4)
            if on:
                pygame.draw.lines(screen, (14, 18, 22), False,
                                  [(box.x + 5, box.centery), (box.x + 9, box.bottom - 6),
                                   (box.right - 4, box.y + 5)], 2)
            pygame.draw.rect(screen, e.color, (r.x + 46, r.centery - 11, 6, 22),
                             border_radius=2)
            pygame.draw.rect(screen, e.accent, (r.x + 46, r.centery - 11, 6, 7),
                             border_radius=2)
            fg = ui.TEXT if on else ui.FAINT
            screen.blit(fonts["bold"].render(e.name, True, fg), (r.x + 64, r.centery - 9))
            if getattr(e, "submitted", False):
                # this car's numbers came from the model itself, not the factory
                badge = fonts["tiny"].render("DESIGNED BY THE MODEL", True, ui.OK)
                screen.blit(badge, (r.x + 64, r.centery + 8))
            screen.blit(fonts["tiny"].render(e.vendor, True, ui.DIM if on else ui.FAINT),
                        (r.x + 252, r.centery - 6))
            tag = e.tagline
            if fonts["tiny"].size(tag)[0] > tag_limit:
                words = tag.split()
                tag = ""
                for word in words:
                    trial = (tag + " " + word).strip()
                    if fonts["tiny"].size(trial + " ...")[0] > tag_limit:
                        break
                    tag = trial
                tag += " ..."
            screen.blit(fonts["tiny"].render(tag, True, ui.DIM if on else ui.FAINT),
                        (r.x + 344, r.centery - 6))
            ch = e.chassis
            vals = [str(ch.power), str(ch.top_speed), str(ch.brake), str(ch.grip),
                    f"{ch.steer_rate:.2f}", f"{e.sensor_count}x{int(e.sensor_range)}"]
            for (label, cx), v in zip(cols, vals):
                t = fonts["body"].render(v, True, fg)
                screen.blit(t, (cx - t.get_width(), r.centery - 8))

    # ------------------------------------------------------------ settings --
    def _build_settings(self):
        x = cfg.SCREEN_W // 2 - 300
        y = 150
        s = self.s

        def setter(name):
            return lambda v: setattr(s, name, v)

        self.widgets += [
            ui.Stepper((x, y, 600, 52), "Race distance", lambda: s.laps,
                       setter("laps"), 1, 50, 1, lambda v: f"{v} laps"),
            ui.Toggle((x, y + 66, 600, 52), "Sensor overlay",
                      lambda: s.show_sensors, setter("show_sensors"),
                      "draw the focused car's vision fan"),
            ui.Toggle((x, y + 132, 600, 52), "Telemetry panel",
                      lambda: s.show_telemetry, setter("show_telemetry"),
                      "speed, pedals, steering and the raw network inputs"),
            ui.Toggle((x, y + 198, 600, 52), "Tyre marks",
                      lambda: s.show_skids, setter("show_skids"),
                      "leave rubber where a car is sliding"),
            ui.Toggle((x, y + 264, 600, 52), "Follow the leader",
                      lambda: s.leader_cam, setter("leader_cam"),
                      "off keeps the camera on whichever car you pick"),
        ]

    def _draw_settings(self, screen, fonts):
        self._heading(screen, fonts, "SETTINGS", "applies to the next race you start")
