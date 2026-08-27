"""The game shell: window, menus, input, camera modes, render loop."""
import math

import pygame

from . import config as cfg
from . import hud, render
from .menu import Menu, Settings
from .race import Race, COUNTDOWN, FINISHED
from .track import Track
from .tracks import by_key as track_by_key
from .vec import clamp

MENU, RACING, RESULTS = "menu", "racing", "results"
CAM_CHASE, CAM_WIDE, CAM_MAP = 1.0, 0.62, 0.0   # 0.0 means "fit the whole circuit"
CAM_CYCLE = [CAM_CHASE, CAM_WIDE, CAM_MAP]
CAM_NAMES = ["chase", "wide", "circuit"]
# screen edges the HUD occupies: left panel, top clock, right minimap, tips
HUD_INSETS = (312, 52, 246, 44)
ZOOM_MIN, ZOOM_MAX, ZOOM_QUANTUM = 0.24, 1.0, 0.04
SURFACE_CACHE = 4          # scaled circuit copies kept in memory at once


class Game:
    def __init__(self, laps=None, entries=None, track_key=None):
        pygame.init()
        pygame.display.set_caption(cfg.TITLE)
        self.screen = pygame.display.set_mode((cfg.SCREEN_W, cfg.SCREEN_H))
        self.clock = pygame.time.Clock()
        self.fonts = hud.load_fonts()

        self.settings = Settings()
        if track_key:
            self.settings.track_key = track_key
            self.settings.laps = self.settings.track.laps
        if entries:
            self.settings.car_keys = [e.key for e in entries]
        if laps:
            self.settings.laps = laps

        self._tracks = {}
        self._worlds = {}
        self._scaled = {}
        self._scaled_order = []

        self.camera = render.Camera(cfg.SCREEN_W, cfg.SCREEN_H)
        self.overlay = pygame.Surface((cfg.SCREEN_W, cfg.SCREEN_H), pygame.SRCALPHA)

        self.menu = Menu(self.settings, self.start_race, self.quit)
        self.state = MENU
        self.running = True
        self.paused = False
        self.time_scale = 1.0
        self.cam_mode = 0
        self.cam_manual = False
        self.dragging = False
        self.drag_from = None
        self.focus = 0
        self.follow_leader = True
        self.race = None
        self.track = None
        self.world = None
        self.art = []
        self.skids = render.SkidMarks()
        self._prime(self.settings.track_key)

    # ------------------------------------------------------------ circuits --
    def _prime(self, key):
        """Build (and cache) a circuit and its pre-rendered surface."""
        if key not in self._tracks:
            self._tracks[key] = Track(track_by_key(key).control)
            self._worlds[key] = render.build_world(self._tracks[key])
        self.track = self._tracks[key]
        world = self._worlds[key]
        if world is not self.world:
            # the scaled copies belong to whichever circuit made them
            self._scaled.clear()
            self._scaled_order.clear()
            self.world = world

    def quit(self):
        self.running = False

    def start_race(self):
        self._prime(self.settings.track_key)
        self.race = Race(self.track, self.settings.entries(), laps=self.settings.laps)
        self.art = [render.CarArt(c.entry, i + 1) for i, c in enumerate(self.race.cars)]
        self.skids = render.SkidMarks()
        self.state = RACING
        self.paused = False
        self.focus = 0
        self.follow_leader = self.settings.leader_cam
        self.cam_manual = False
        self.cam_mode = 0
        self.camera.target_zoom = CAM_CHASE
        car = self.race.cars[0]
        self.camera.follow(car.x, car.y, 0, snap=True)

    def to_menu(self):
        self.state = MENU
        self.menu.go("main")

    # --------------------------------------------------------- focus / cam --
    def focused_car(self):
        if not self.race:
            return None
        if self.follow_leader and self.race.state != COUNTDOWN:
            return self.race.standings()[0]
        return self.race.cars[self.focus % len(self.race.cars)]

    def shift_focus(self, delta):
        self.follow_leader = False
        self.cam_manual = False
        self.focus = (self.focus + delta) % len(self.race.cars)

    def set_focus(self, i):
        if 0 <= i < len(self.race.cars):
            self.follow_leader = False
            self.cam_manual = False
            self.focus = i

    def car_at(self, pos):
        """Which car did the cursor land on, if any."""
        best, best_d = None, 26.0
        for i, car in enumerate(self.race.cars):
            sx, sy = self.camera.to_screen(car.x, car.y)
            d = math.hypot(sx - pos[0], sy - pos[1])
            if d < best_d:
                best, best_d = i, d
        return best

    # ---------------------------------------------------------------- input --
    def handle(self, event):
        if event.type == pygame.QUIT:
            self.running = False
            return
        if self.state == MENU:
            self.menu.handle(event)
            return
        if event.type == pygame.KEYDOWN:
            self.handle_key(event)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            hit = self.car_at(event.pos)
            if hit is not None:
                self.set_focus(hit)
            else:
                self.dragging = True
                self.drag_from = event.pos
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            # right click drops back to following whatever is being watched
            self.cam_manual = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            dx = event.pos[0] - self.drag_from[0]
            dy = event.pos[1] - self.drag_from[1]
            if not self.cam_manual and (abs(dx) + abs(dy)) > 3:
                self.cam_manual = True          # first real drag takes control
            if self.cam_manual:
                z = max(self.camera.zoom, 1e-3)
                self.camera.x -= dx / z
                self.camera.y -= dy / z
            self.drag_from = event.pos
        elif event.type == pygame.MOUSEWHEEL:
            self.zoom_at(pygame.mouse.get_pos(), event.y)

    def zoom_at(self, pos, notches):
        """Wheel zoom that keeps whatever is under the cursor under the cursor."""
        cam = self.camera
        before = cam.zoom
        target = clamp(before * (1.12 ** notches), ZOOM_MIN, ZOOM_MAX)
        target = round(target / ZOOM_QUANTUM) * ZOOM_QUANTUM
        if abs(target - before) < 1e-6:
            return
        wx = (pos[0] - cfg.SCREEN_W / 2 - cam.offset[0]) / before + cam.x
        wy = (pos[1] - cfg.SCREEN_H / 2 - cam.offset[1]) / before + cam.y
        self.cam_manual = True
        cam.target_zoom = target
        cam.zoom = target
        cam.x = wx - (pos[0] - cfg.SCREEN_W / 2 - cam.offset[0]) / target
        cam.y = wy - (pos[1] - cfg.SCREEN_H / 2 - cam.offset[1]) / target

    def handle_key(self, event):
        k = event.key
        # event.mod, not key.get_mods(): the modifier that matters is the one
        # held when this key went down
        mods = getattr(event, "mod", 0) or pygame.key.get_mods()
        if k == pygame.K_ESCAPE:
            self.to_menu()
        elif k == pygame.K_r:
            self.start_race()
        elif k == pygame.K_SPACE:
            self.paused = not self.paused
        elif k == pygame.K_c:
            self.cam_mode = (self.cam_mode + 1) % len(CAM_CYCLE)
            self.cam_manual = False
        elif k == pygame.K_f:
            self.cam_manual = not self.cam_manual
        elif k == pygame.K_v:
            self.settings.show_sensors = not self.settings.show_sensors
        elif k == pygame.K_t:
            self.settings.show_telemetry = not self.settings.show_telemetry
        elif k == pygame.K_l:
            self.follow_leader = not self.follow_leader
            if self.follow_leader:
                self.cam_manual = False
        elif k == pygame.K_TAB:
            self.shift_focus(-1 if (mods & pygame.KMOD_SHIFT) else 1)
        elif k in (pygame.K_RIGHT, pygame.K_RIGHTBRACKET, pygame.K_PERIOD):
            self.shift_focus(1)
        elif k in (pygame.K_LEFT, pygame.K_LEFTBRACKET, pygame.K_COMMA):
            self.shift_focus(-1)
        elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.time_scale = max(0.25, self.time_scale / 2)
        elif k in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
            self.time_scale = min(4.0, self.time_scale * 2)
        elif pygame.K_1 <= k <= pygame.K_9:
            self.set_focus(k - pygame.K_1)

    # --------------------------------------------------------------- update --
    def update(self, dt):
        if self.state == MENU:
            # show the chosen circuit whole behind the menu
            self._prime(self.settings.track_key)
            z, centre, _ = self.camera.fit(self.track.bounds, (0, 0, 0, 0))
            self.camera.target_zoom = round(z / ZOOM_QUANTUM) * ZOOM_QUANTUM
            self.camera.offset = (0.0, 0.0)
            self.camera.clamped = False
            self.camera.follow(centre[0], centre[1], dt)
            return
        if self.state == RACING and not self.paused:
            step = dt * self.time_scale
            # Never integrate one huge step: a stalled window must not teleport
            # cars straight through the barriers.
            while step > 1e-6:
                s = min(step, 1 / 60)
                self.race.update(s)
                step -= s
            if self.settings.show_skids:
                for car in self.race.cars:
                    self.skids.emit(car)
            if self.race.state == FINISHED:
                self.state = RESULTS

        cam = self.camera
        if self.cam_manual:
            cam.clamped = False
            cam.offset = (0.0, 0.0)
            cam.target_zoom = cam.zoom
            return

        zoom = CAM_CYCLE[self.cam_mode]
        car = self.focused_car()
        if zoom == 0.0:
            # whole-circuit view, centred in the gap between the HUD panels
            z, centre, offset = cam.fit(self.track.bounds, HUD_INSETS)
            cam.target_zoom = z
            cam.offset = offset
            cam.clamped = False
            cam.follow(centre[0], centre[1], dt)
        else:
            cam.target_zoom = zoom
            cam.offset = (0.0, 0.0)
            cam.clamped = True
            # look ahead of the car so the corner arrives before the car does
            lead = min(car.speed * 0.55, 200.0)
            cam.follow(car.x + math.cos(car.heading) * lead,
                       car.y + math.sin(car.heading) * lead, dt)

    # ----------------------------------------------------------------- draw --
    def _world_at(self, zoom):
        """One scaled copy of the circuit per zoom level, with a small cache.

        Free-cam zoom is quantised before it reaches here. Without that, easing
        through arbitrary zoom values would build a fresh multi-megabyte surface
        every single frame.
        """
        key = round(zoom / ZOOM_QUANTUM)
        if key not in self._scaled:
            if abs(zoom - 1.0) < 1e-3:
                self._scaled[key] = self.world
            else:
                w = max(1, int(cfg.WORLD_W * zoom))
                h = max(1, int(cfg.WORLD_H * zoom))
                self._scaled[key] = pygame.transform.smoothscale(self.world, (w, h))
            self._scaled_order.append(key)
            while len(self._scaled_order) > SURFACE_CACHE:
                old = self._scaled_order.pop(0)
                if self._scaled.get(old) is not self.world:
                    self._scaled.pop(old, None)
        return self._scaled[key]

    def draw(self):
        screen = self.screen
        # grass, not the panel colour: in the whole-circuit view the scaled
        # world does not reach every screen edge, and a hard seam is obvious
        screen.fill(cfg.C_GRASS_A)
        cam = self.camera
        z = cam.zoom
        screen.blit(self._world_at(z),
                    (-(cam.x * z - cfg.SCREEN_W / 2) + cam.offset[0],
                     -(cam.y * z - cfg.SCREEN_H / 2) + cam.offset[1]))

        if self.race:
            if self.settings.show_skids:
                self.skids.draw(screen, cam)
            focus = self.focused_car()
            if self.settings.show_sensors and z > 0.4 and self.state != MENU:
                self.overlay.fill((0, 0, 0, 0))
                render.draw_sensors(screen, focus, cam, self.overlay)
                screen.blit(self.overlay, (0, 0))
            for i, car in enumerate(self.race.cars):
                render.draw_car(screen, self.art[i], car, cam, highlight=(car is focus))

        if self.state == MENU:
            self.menu.draw(screen, self.fonts)
        else:
            self.draw_hud(self.focused_car())
        pygame.display.flip()

    def draw_hud(self, focus):
        screen, f = self.screen, self.fonts
        hud.draw_standings(screen, f, self.race, focus.entry.key)
        hud.draw_minimap(screen, f, self.race, focus.entry.key)
        if self.settings.show_telemetry:
            hud.draw_telemetry(screen, f, focus, self.race)

        r = f["big"].render(hud.fmt_time(self.race.time), True, cfg.C_TEXT)
        screen.blit(r, (cfg.SCREEN_W // 2 - r.get_width() // 2, 14))
        name = f["small"].render(self.settings.track.name, True, cfg.C_TEXT_DIM)
        screen.blit(name, (cfg.SCREEN_W // 2 - name.get_width() // 2, 44))

        if self.race.state == COUNTDOWN:
            hud.draw_countdown(screen, f, self.race)
        if self.paused and self.state != RESULTS:
            hud.draw_banner(screen, f, "PAUSED", "space to resume")
        if self.state == RESULTS:
            hud.draw_results(screen, f, self.race)

        cam_txt = "free" if self.cam_manual else CAM_NAMES[self.cam_mode]
        who = "leader" if self.follow_leader else focus.name
        bits = [f"cam {cam_txt}", f"watching {who}",
                "TAB / arrows / 1-9 focus", "drag + wheel free cam",
                "C camera", "L leader", "V vision", "T telemetry",
                "SPACE pause", "R restart", "ESC menu"]
        if self.time_scale != 1.0:
            bits.insert(0, f"x{self.time_scale:g}")
        r = f["tiny"].render("   ".join(bits), True, cfg.C_TEXT_DIM)
        screen.blit(r, (cfg.SCREEN_W // 2 - r.get_width() // 2, cfg.SCREEN_H - 22))

    # ----------------------------------------------------------------- loop --
    def run(self):
        while self.running:
            dt = self.clock.tick(cfg.FPS) / 1000.0
            for event in pygame.event.get():
                self.handle(event)
            self.update(min(dt, 0.05))
            self.draw()
        pygame.quit()
