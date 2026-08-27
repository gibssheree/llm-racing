"""Render frames off-screen so the look can be checked without a window."""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, '.')
import pygame
from llmrace.game import Game, RACING


def shoot(name, seconds, setup=None):
    g = Game(laps=3)
    if setup:
        setup(g)
    g.start()
    steps = int(seconds * 60)
    for _ in range(steps):
        g.update(1 / 60)
        for c in g.race.cars:
            g.skids.emit(c)
    g.draw()
    out = f"shots/{name}.png"
    pygame.image.save(g.screen, out)
    print("wrote", out, "| race t=%.1fs state=%s" % (g.race.time, g.race.state))
    pygame.quit()


if __name__ == "__main__":
    os.makedirs("shots", exist_ok=True)
    def menu(g):
        g.draw()
        pygame.image.save(g.screen, "shots/menu.png")
        print("wrote shots/menu.png")
    g = Game(laps=3); menu(g); pygame.quit()

    shoot("start", 4.2)
    shoot("mid", 14.0)
    def wide(g): g.cam_mode = 1
    shoot("wide", 22.0, wide)
    def overview(g): g.cam_mode = 2
    shoot("overview", 30.0, overview)
