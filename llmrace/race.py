"""Race session logic. Deliberately free of pygame so it can run headless."""
from . import config as cfg
from .car import Car
from .drivers import ROSTER

COUNTDOWN, RUNNING, FINISHED = "countdown", "running", "finished"


class Race:
    def __init__(self, track, entries=None, laps=cfg.DEFAULT_LAPS, countdown=True):
        self.track = track
        self.entries = list(entries or ROSTER)
        self.total_laps = laps
        self.cars = []
        slots = track.grid_slots(len(self.entries))
        for i, entry in enumerate(self.entries):
            self.cars.append(Car(entry, track, slots[i], i))
        self.state = COUNTDOWN if countdown else RUNNING
        self.timer = cfg.COUNTDOWN_SECONDS if countdown else 0.0
        self.time = 0.0
        self.finish_order = []

    # ---------------------------------------------------------------- update --
    def update(self, dt):
        if self.state == COUNTDOWN:
            self.timer -= dt
            if self.timer <= 0.0:
                self.state = RUNNING
                self.timer = 0.0
            return
        if self.state == FINISHED:
            self.time += dt
            self._drive(dt)      # cool-down lap, cars keep rolling
            return

        self.time += dt
        self._drive(dt)

        for car in self.cars:
            if not car.finished and car.lap >= self.total_laps:
                car.finished = True
                car.finish_time = self.time
                self.finish_order.append(car)
        if all(c.finished for c in self.cars):
            self.state = FINISHED

        self._rank()

    def _drive(self, dt):
        cars = self.cars
        for car in cars:
            car.think(cars, dt)
        for car in cars:
            car.step(dt, self.time)
        n = len(cars)
        for i in range(n):
            for j in range(i + 1, n):
                Car.resolve_contact(cars[i], cars[j])

    def _rank(self):
        order = sorted(
            self.cars,
            key=lambda c: (c.finish_time if c.finished else 1e9, -c.race_progress()))
        for i, car in enumerate(order):
            car.race_position = i + 1
        self.order = order
        return order

    def standings(self):
        return sorted(self.cars, key=lambda c: c.race_position)

    def leader(self):
        return self.standings()[0]
