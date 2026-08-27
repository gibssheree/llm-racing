"""Race session logic. Deliberately free of pygame so it can run headless."""
from . import config as cfg
from .car import Car
from .drivers import ROSTER

COUNTDOWN, RUNNING, FINISHED = "countdown", "running", "finished"

# Once the winner is home, the rest get this long to complete the lap before
# the race is called. Without it a single car in trouble hangs the session.
FLAG_GRACE = 45.0


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
        self.flag_time = None

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
                if self.flag_time is None:
                    self.flag_time = self.time

        if all(c.finished for c in self.cars):
            self.state = FINISHED
        elif (self.flag_time is not None
              and self.time - self.flag_time > self.flag_grace()):
            # called on time: whoever is still out is classified where they lie
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

    def flag_grace(self):
        """How long the stragglers get after the winner is home.

        Enough to finish the lap they are on, so a long race does not call the
        flag on a car that is simply a lap down rather than in trouble.
        """
        best = min((c.best_lap for c in self.cars if c.best_lap), default=None)
        return max(FLAG_GRACE, (best or 30.0) * 1.6)

    def reference_pace(self):
        """One representative speed for the whole field, in px/s.

        Time gaps have to be converted from distance at a *shared* pace, or a
        car that happens to be braking shows a larger gap than one further back
        on the straight.
        """
        best = min((c.best_lap for c in self.cars if c.best_lap), default=None)
        if best:
            return self.track.length / best
        moving = [c.speed for c in self.cars if not c.finished]
        return max(60.0, sum(moving) / len(moving)) if moving else 300.0
