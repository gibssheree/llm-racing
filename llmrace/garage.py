"""Load, validate and apply cars designed by outside language models.

A submission is one JSON object per entrant in garage/<key>.json, exactly as
the model replied to its brief. Anything invalid is reported and skipped - a
bad submission never silently becomes a car.
"""
import copy
import json
import os

from . import spec

GARAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "garage")


def parse(raw):
    """Accept the JSON as sent, including a stray markdown fence."""
    if isinstance(raw, dict):
        return raw
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        text = text.rsplit("```", 1)[0]
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        text = text[start:end + 1]
    return json.loads(text)


def upgrade(values):
    """Convert a submission written against an older spec version.

    Only distances measured in world pixels move. A car's *relative* choice -
    where it sat inside the allowed band - is preserved exactly, so this is a
    unit conversion rather than an edit to anyone's design.
    """
    got = int(values.get("spec_version", 1) or 1)
    if got >= spec.SPEC_VERSION:
        return values
    out = dict(values)
    if "sensor_range" in out:
        try:
            out["sensor_range"] = round(float(out["sensor_range"])
                                        * spec.LEGACY_SENSOR_SCALE)
        except (TypeError, ValueError):
            pass
    out["spec_version"] = spec.SPEC_VERSION
    return out


def validate(values):
    """Return (clean values, list of problems). Problems mean 'do not race it'."""
    values = upgrade(values)
    problems = []
    clean = {}
    for p in spec.PARAMS:
        if p.name not in values:
            problems.append(f"missing field: {p.name}")
            continue
        try:
            v = float(values[p.name])
        except (TypeError, ValueError):
            problems.append(f"{p.name}: {values[p.name]!r} is not a number")
            continue
        if p.choices:
            if int(round(v)) not in p.choices:
                problems.append(f"{p.name}: {v:g} must be one of "
                                f"{', '.join(str(c) for c in p.choices)}")
                continue
            v = int(round(v))
        elif not (p.lo - 1e-9 <= v <= p.hi + 1e-9):
            problems.append(f"{p.name}: {v:g} is outside {p.lo:g}..{p.hi:g}")
            continue
        clean[p.name] = v

    cost = spec.total_cost(clean) if not problems else spec.total_cost(clean)
    if cost > spec.BUDGET + spec.TOLERANCE:
        problems.append(f"over budget: {cost:.1f} points spent, "
                        f"limit is {spec.BUDGET:.0f}")
    return clean, problems, cost


def apply_values(entry, values, car_name=None, tagline=None):
    """Return a copy of `entry` rebuilt from a submission."""
    e = copy.deepcopy(entry)
    for obj in (e.chassis, e.brain, e.temper):
        for name in list(vars(obj)):
            if name in values:
                setattr(obj, name, values[name])
    e.sensor_count = int(values["sensor_count"])
    e.sensor_range = float(values["sensor_range"])
    if car_name:
        e.name = str(car_name)[:22]
    if tagline:
        e.tagline = str(tagline)[:62]
    e.submitted = True
    return e


def load_all(directory=GARAGE_DIR):
    """{key: (values, meta, problems, cost)} for every file in the garage."""
    out = {}
    if not os.path.isdir(directory):
        return out
    for fn in sorted(os.listdir(directory)):
        if not fn.endswith(".json"):
            continue
        key = fn[:-5]
        path = os.path.join(directory, fn)
        try:
            with open(path, encoding="utf-8") as fh:
                raw = parse(fh.read())
        except Exception as exc:                      # noqa: BLE001
            out[key] = ({}, {}, [f"could not read {fn}: {exc}"], 0.0)
            continue
        values, problems, cost = validate(raw)
        meta = {k: raw.get(k) for k in ("car_name", "tagline", "reasoning")}
        out[key] = (values, meta, problems, cost)
    return out


def apply_to(roster, directory=GARAGE_DIR, quiet=True):
    """Swap in every valid submission. Returns the keys that were replaced."""
    swapped = []
    subs = load_all(directory)
    for i, entry in enumerate(roster):
        record = subs.get(entry.key)
        if not record:
            continue
        values, meta, problems, _ = record
        if problems:
            if not quiet:
                print(f"[garage] {entry.key}: skipped - {problems[0]}")
            continue
        roster[i] = apply_values(entry, values, meta.get("car_name"),
                                 meta.get("tagline"))
        swapped.append(entry.key)
    return swapped
