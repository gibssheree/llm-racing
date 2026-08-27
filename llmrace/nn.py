"""A small hand-rolled feed-forward network.

Deliberately dependency-free and tiny: every car runs one of these every
frame, and the evolutionary tuner in ``train.py`` mutates the flat weight
vector directly.
"""
import math
import random


def tanh(x):
    if x > 20:
        return 1.0
    if x < -20:
        return -1.0
    return math.tanh(x)


def sigmoid(x):
    if x > 20:
        return 1.0
    if x < -20:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


class MLP:
    """inputs -> tanh(hidden) -> linear(outputs)."""

    def __init__(self, n_in, n_hidden, n_out):
        self.n_in, self.n_hidden, self.n_out = n_in, n_hidden, n_out
        self.w1 = [[0.0] * n_in for _ in range(n_hidden)]
        self.b1 = [0.0] * n_hidden
        self.w2 = [[0.0] * n_hidden for _ in range(n_out)]
        self.b2 = [0.0] * n_out

    # ------------------------------------------------------------ forward --
    def forward(self, x):
        h = []
        for row, bias in zip(self.w1, self.b1):
            acc = bias
            for wi, xi in zip(row, x):
                acc += wi * xi
            h.append(tanh(acc))
        out = []
        for row, bias in zip(self.w2, self.b2):
            acc = bias
            for wi, hi in zip(row, h):
                acc += wi * hi
            out.append(acc)
        self.hidden = h
        return out

    # ------------------------------------------------ (de)serialise / tune --
    def flatten(self):
        flat = []
        for row in self.w1:
            flat.extend(row)
        flat.extend(self.b1)
        for row in self.w2:
            flat.extend(row)
        flat.extend(self.b2)
        return flat

    def load_flat(self, flat):
        k = 0
        for row in self.w1:
            for i in range(len(row)):
                row[i] = flat[k]
                k += 1
        for i in range(len(self.b1)):
            self.b1[i] = flat[k]
            k += 1
        for row in self.w2:
            for i in range(len(row)):
                row[i] = flat[k]
                k += 1
        for i in range(len(self.b2)):
            self.b2[i] = flat[k]
            k += 1
        return self

    def clone(self):
        m = MLP(self.n_in, self.n_hidden, self.n_out)
        m.load_flat(self.flatten())
        return m

    def jitter(self, rng, amount):
        """Small seeded perturbation - this is what makes two models with the
        same recipe still drive slightly differently."""
        flat = self.flatten()
        flat = [v + rng.gauss(0.0, amount) for v in flat]
        return self.load_flat(flat)

    def to_dict(self):
        return {"n_in": self.n_in, "n_hidden": self.n_hidden,
                "n_out": self.n_out, "weights": self.flatten()}

    @classmethod
    def from_dict(cls, d):
        return cls(d["n_in"], d["n_hidden"], d["n_out"]).load_flat(d["weights"])
