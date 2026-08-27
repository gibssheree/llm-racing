"""Render every circuit so the shapes can actually be looked at."""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, '.')
import pygame
from llmrace import config as cfg
from llmrace.track import Track
from llmrace import render
from llmrace.tracks import PRESETS

pygame.init()
W, H = 660, 460
cols, rows = 3, 2
sheet = pygame.display.set_mode((W * cols, H * rows))
sheet.fill((12, 14, 18))
font = pygame.font.SysFont("Consolas", 17, bold=True)
small = pygame.font.SysFont("Consolas", 13)

for i, p in enumerate(PRESETS):
    t = Track(p.control)
    world = render.build_world(t)
    bx, by, bw, bh = t.bounds
    sc = min((W - 30) / bw, (H - 60) / bh)
    thumb = pygame.transform.smoothscale(world, (int(cfg.WORLD_W * sc), int(cfg.WORLD_H * sc)))
    ox = (i % cols) * W
    oy = (i // cols) * H
    sheet.blit(thumb, (ox + 15 - bx * sc, oy + 46 - by * sc),
               pygame.Rect(0, 0, 10000, 10000))
    pygame.draw.rect(sheet, (40, 46, 58), (ox + 6, oy + 6, W - 12, H - 12), 1)
    sheet.blit(font.render(p.name, True, (228, 232, 240)), (ox + 18, oy + 14))
    s = p.stats
    info = (f"{s['length']:.0f}px   minR {s['min_radius']:.0f}   "
            f"flat-out {s['flat_out']*100:.0f}%   {s['turns']} direction changes   "
            f"{p.laps} laps")
    sheet.blit(small.render(info, True, (140, 150, 166)), (ox + 18, oy + H - 26))

pygame.image.save(sheet, "shots/circuits.png")
print("wrote shots/circuits.png")
