"""Drive every menu screen and the race off-screen, and save what they look like."""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, '.')
import pygame
from llmrace.game import Game, MENU, RACING, RESULTS
from llmrace import menu as M

os.makedirs("shots", exist_ok=True)
g = Game()


def snap(name):
    g.update(1 / 60)
    g.draw()
    pygame.image.save(g.screen, f"shots/{name}.png")
    print("  ->", name)


def click(pos):
    g.handle(pygame.event.Event(pygame.MOUSEMOTION, pos=pos))
    g.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))


def key(k, mod=0):
    g.handle(pygame.event.Event(pygame.KEYDOWN, key=k, mod=mod))


print("main menu"); snap("ui_main")

print("track picker")
click(g.menu.widgets[1].rect.center)          # CIRCUIT
assert g.menu.screen == M.TRACKS, g.menu.screen
snap("ui_tracks")
click(g.menu.widgets[2].rect.center)          # pick 'technical'
assert g.settings.track_key == "technical", g.settings.track_key
assert g.menu.screen == M.MAIN
print("  selected:", g.settings.track_key, g.settings.laps, "laps")

print("grid picker")
click(g.menu.widgets[2].rect.center)          # GRID
assert g.menu.screen == M.GRID
for i in range(5):                            # try to remove five cars
    click(g.menu.widgets[i].rect.center)
print("  cars left:", len(g.settings.car_keys), "| notice:", g.menu.notice)
assert len(g.settings.car_keys) == M.MIN_CARS
snap("ui_grid")
click(g.menu.widgets[7].rect.center)          # ENTER ALL
assert len(g.settings.car_keys) == 7
click(g.menu.widgets[8].rect.center)          # DONE

print("settings")
click(g.menu.widgets[3].rect.center)          # SETTINGS
assert g.menu.screen == M.SETTINGS
st = g.menu.widgets[0]
before = g.settings.laps
click(st.plus.center); click(st.plus.center)
assert g.settings.laps == before + 2, g.settings.laps
click(g.menu.widgets[3].rect.center)          # toggle tyre marks
assert g.settings.show_skids is False
click(g.menu.widgets[3].rect.center)
snap("ui_settings")
key(pygame.K_ESCAPE)
assert g.menu.screen == M.MAIN
print("  laps:", g.settings.laps, "skids:", g.settings.show_skids)

print("race")
click(g.menu.widgets[0].rect.center)          # START RACE
assert g.state == RACING
for _ in range(int(6.0 * 60)):
    g.update(1 / 60)
print(f"  circuit={g.settings.track.name} cars={len(g.race.cars)} t={g.race.time:.1f}s")
snap("ui_race")

print("focus keys")
g.follow_leader = True
start = g.focused_car().name
key(pygame.K_TAB)
assert not g.follow_leader
a = g.focused_car().name
key(pygame.K_TAB)
b = g.focused_car().name
key(pygame.K_TAB, pygame.KMOD_LSHIFT)
c = g.focused_car().name
assert c == a, (a, b, c)
key(pygame.K_3)
d = g.focused_car().name
assert d == g.race.cars[2].name
key(pygame.K_RIGHT); e1 = g.focused_car().name
key(pygame.K_LEFT); e2 = g.focused_car().name
assert e2 == d
print(f"  leader={start} tab->{a} tab->{b} shift-tab->{c} '3'->{d} arrows ok")

print("mouse free cam")
cx, cy = g.camera.x, g.camera.y
g.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(700, 400), button=1))
g.handle(pygame.event.Event(pygame.MOUSEMOTION, pos=(600, 340), buttons=(1, 0, 0)))
g.update(1 / 60)
assert g.cam_manual, "drag should take camera control"
moved = abs(g.camera.x - cx) + abs(g.camera.y - cy)
assert moved > 20, moved
g.handle(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(600, 340), button=1))
print(f"  drag moved camera {moved:.0f}px, manual={g.cam_manual}")

z0 = g.camera.zoom
g.handle(pygame.event.Event(pygame.MOUSEWHEEL, y=-4, x=0))
g.update(1 / 60)
z1 = g.camera.zoom
g.handle(pygame.event.Event(pygame.MOUSEWHEEL, y=8, x=0))
g.update(1 / 60)
z2 = g.camera.zoom
assert z1 < z0 and z2 > z1, (z0, z1, z2)
print(f"  wheel zoom {z0:.2f} -> {z1:.2f} -> {z2:.2f} (cached surfaces: {len(g._scaled)})")
snap("ui_freecam")

# clicking a car should grab focus and drop free cam
target = g.race.cars[4]
pos = g.camera.to_screen(target.x, target.y)
g.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(int(pos[0]), int(pos[1])), button=1))
assert g.focused_car() is target, g.focused_car().name
assert not g.cam_manual
print(f"  clicked {target.name} -> focused, free cam released")

key(pygame.K_c); assert not g.cam_manual
key(pygame.K_c); key(pygame.K_c)
print(f"  camera cycle back to mode {g.cam_mode}")

print("escape to menu, switch circuit, race again")
key(pygame.K_ESCAPE)
assert g.state == MENU
click(g.menu.widgets[1].rect.center)
click(g.menu.widgets[0].rect.center)          # first circuit
assert g.settings.track_key == "autodrome"
click(g.menu.widgets[0].rect.center)          # START
old_world = id(g.world)
g.update(1 / 60); g.draw()
print(f"  now on {g.settings.track.name}, scaled cache reset to {len(g._scaled)}")

print("run to the flag")
guard = 0
while g.state != RESULTS and guard < 60 * 400:
    g.update(1 / 60); guard += 1
snap("ui_results")
print(f"  finished in {g.race.time:.2f}s")
for c in g.race.standings():
    print(f"   P{c.race_position} {c.name:18s} {c.finish_time:7.2f}s best {c.best_lap:5.2f}s")
pygame.quit()
print("\nALL CHECKS PASSED")
