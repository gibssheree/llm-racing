"""Tiny 2D vector helpers (plain tuples, no allocation-heavy classes)."""
import math


def add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def mul(a, s):
    return (a[0] * s, a[1] * s)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def length(a):
    return math.hypot(a[0], a[1])


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def dist2(a, b):
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return dx * dx + dy * dy


def norm(a):
    l = math.hypot(a[0], a[1])
    if l < 1e-9:
        return (0.0, 0.0)
    return (a[0] / l, a[1] / l)


def rot(a, ang):
    c, s = math.cos(ang), math.sin(ang)
    return (a[0] * c - a[1] * s, a[0] * s + a[1] * c)


def from_angle(ang, scale=1.0):
    return (math.cos(ang) * scale, math.sin(ang) * scale)


def clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


def lerp(a, b, t):
    return a + (b - a) * t


def angle_diff(a, b):
    """Shortest signed difference a - b, wrapped to [-pi, pi]."""
    d = (a - b + math.pi) % (2 * math.pi) - math.pi
    return d
