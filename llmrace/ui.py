"""A very small immediate-mode widget kit - just enough for the menus.

Widgets are plain objects with a rect, a draw() and a click test. The screen
that owns them keeps the state; nothing here knows about the game.
"""
import pygame

from . import config as cfg

TEXT = (226, 230, 238)
DIM = (138, 147, 163)
FAINT = (92, 99, 114)
ACCENT = (108, 176, 255)
OK = (86, 200, 130)
BAD = (232, 92, 92)
FILL = (30, 35, 45)
FILL_HOT = (44, 52, 68)
FILL_ON = (38, 62, 92)
EDGE = (58, 66, 82)
EDGE_ON = (108, 176, 255)


def shade(color, k):
    return tuple(max(0, min(255, int(c * k))) for c in color)


class Widget:
    def __init__(self, rect, on_click=None, enabled=True, tip=None):
        self.rect = pygame.Rect(rect)
        self.on_click = on_click
        self.enabled = enabled
        self.hot = False
        self.tip = tip

    def hover(self, pos):
        self.hot = self.enabled and self.rect.collidepoint(pos)
        return self.hot

    def click(self, pos):
        if self.enabled and self.rect.collidepoint(pos) and self.on_click:
            self.on_click()
            return True
        return False


class Hotspot(Widget):
    """A clickable region that draws nothing.

    Used where the screen paints its own row or card: a Button would happily
    fill its rect and bury that artwork.
    """

    def draw(self, screen, fonts):
        return


class Button(Widget):
    def __init__(self, rect, label, on_click=None, primary=False, enabled=True,
                 sub=None, tip=None):
        super().__init__(rect, on_click, enabled, tip)
        self.label = label
        self.primary = primary
        self.sub = sub

    def draw(self, screen, fonts):
        r = self.rect
        if not self.enabled:
            bg, edge, fg = (24, 27, 34), (44, 48, 58), FAINT
        elif self.primary:
            bg = shade(ACCENT, 0.42 if not self.hot else 0.58)
            edge, fg = ACCENT, TEXT
        else:
            bg = FILL_HOT if self.hot else FILL
            edge, fg = (EDGE_ON if self.hot else EDGE), TEXT
        pygame.draw.rect(screen, bg, r, border_radius=7)
        pygame.draw.rect(screen, edge, r, 1, border_radius=7)
        f = fonts["bold"] if self.primary else fonts["body"]
        t = f.render(self.label, True, fg)
        ty = r.centery - t.get_height() // 2 - (7 if self.sub else 0)
        screen.blit(t, (r.centerx - t.get_width() // 2, ty))
        if self.sub:
            s = fonts["tiny"].render(self.sub, True, DIM if self.enabled else FAINT)
            screen.blit(s, (r.centerx - s.get_width() // 2, ty + t.get_height() + 1))


class Stepper(Widget):
    """A value with - and + on either side."""

    def __init__(self, rect, label, get, set_, lo, hi, step=1, fmt=str):
        super().__init__(rect)
        self.label, self.get, self.set = label, get, set_
        self.lo, self.hi, self.step, self.fmt = lo, hi, step, fmt
        self.minus = pygame.Rect(rect[0] + rect[2] - 74, rect[1] + 4, 30, rect[3] - 8)
        self.plus = pygame.Rect(rect[0] + rect[2] - 34, rect[1] + 4, 30, rect[3] - 8)
        self._hot = None

    def hover(self, pos):
        self._hot = ("-" if self.minus.collidepoint(pos)
                     else "+" if self.plus.collidepoint(pos) else None)
        self.hot = self._hot is not None
        return self.hot

    def click(self, pos):
        v = self.get()
        if self.minus.collidepoint(pos):
            self.set(max(self.lo, v - self.step))
            return True
        if self.plus.collidepoint(pos):
            self.set(min(self.hi, v + self.step))
            return True
        return False

    def draw(self, screen, fonts):
        r = self.rect
        pygame.draw.rect(screen, FILL, r, border_radius=7)
        pygame.draw.rect(screen, EDGE, r, 1, border_radius=7)
        screen.blit(fonts["body"].render(self.label, True, TEXT), (r.x + 14, r.centery - 8))
        val = fonts["bold"].render(self.fmt(self.get()), True, ACCENT)
        screen.blit(val, (r.x + r.width - 96 - val.get_width(), r.centery - 8))
        for box, sign in ((self.minus, "-"), (self.plus, "+")):
            hot = (self._hot == sign)
            pygame.draw.rect(screen, FILL_HOT if hot else (24, 28, 36), box, border_radius=5)
            pygame.draw.rect(screen, EDGE_ON if hot else EDGE, box, 1, border_radius=5)
            t = fonts["bold"].render(sign, True, TEXT)
            screen.blit(t, (box.centerx - t.get_width() // 2, box.centery - t.get_height() // 2))


class Toggle(Widget):
    def __init__(self, rect, label, get, set_, sub=None):
        super().__init__(rect)
        self.label, self.get, self.set, self.sub = label, get, set_, sub

    def click(self, pos):
        if self.rect.collidepoint(pos):
            self.set(not self.get())
            return True
        return False

    def draw(self, screen, fonts):
        r = self.rect
        on = self.get()
        pygame.draw.rect(screen, FILL_HOT if self.hot else FILL, r, border_radius=7)
        pygame.draw.rect(screen, EDGE_ON if self.hot else EDGE, r, 1, border_radius=7)
        screen.blit(fonts["body"].render(self.label, True, TEXT), (r.x + 14, r.centery - 8))
        if self.sub:
            screen.blit(fonts["tiny"].render(self.sub, True, DIM), (r.x + 14, r.centery + 8))
        sw = pygame.Rect(r.right - 62, r.centery - 11, 46, 22)
        pygame.draw.rect(screen, shade(OK, 0.5) if on else (36, 40, 50), sw, border_radius=11)
        pygame.draw.rect(screen, OK if on else EDGE, sw, 1, border_radius=11)
        knob = sw.right - 13 if on else sw.x + 13
        pygame.draw.circle(screen, TEXT if on else DIM, (knob, sw.centery), 8)
