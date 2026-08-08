#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
05_sim_harness.py -- a host-side stand-in for the Pybricks runtime.

Purpose: execute the flight program against a simulated rover so that syntax
errors, name errors, buffer overruns, unreachable branches, run-duration blowouts
and trigger-logic mistakes are found by FREE ANALYSIS rather than by burning a
scored hardware run.

It is NOT a validated physics model and nothing it produces binds any parameter.
Its only claims are about the PROGRAM: that it runs to completion, respects its
buffers, terminates on the intended branch, and emits a well-formed telemetry
stream ending in the sentinel.

Ground truth used by the simulation is deliberately set AWAY from the prior mid,
so that a program which only works at the prior mid is exposed.
"""

from __future__ import annotations

import io
import math
import random
import sys
import types

# ---------------------------------------------------------------- simulated truth
TRUTH = dict(
    omega_ceiling=1000.0,    # deg/s
    accel_limit=3000.0,      # deg/s^2 (set by the program)
    k=0.55,                  # mm/deg
    a_brake_mm=3000.0,       # mm/s^2 under plugging
    a_coast_mm=1400.0,       # mm/s^2 under passive brake
    tau=0.040,               # s ranger transport lag
    refresh=0.030,           # s ranger refresh
    noise=3.0,               # mm 1-sigma
    bA=25.0,                 # mm ranger-A offset  (r = g + b)
    bB=35.0,                 # mm ranger-B offset
    floor=40.0,              # mm ranger validity floor (clamps below this)
    g0=1000.0,               # mm true starting gap
    yaw_rate_bias=0.6,       # deg/s of drift while driving straight
    mirrored=True,           # right motor is mounted mirrored
)

random.seed(7)


class World:
    def __init__(self):
        self.t = 0.0                 # s
        self.g = TRUTH["g0"]         # true gap, mm
        self.heading = 0.0
        self.head_ref = 0.0
        self.hist = [(0.0, TRUTH["g0"])]
        self.motors = []
        self.contact = False

    def step(self, dt):
        for m in self.motors:
            m._step(dt)
        if len(self.motors) >= 2:
            w = 0.5 * (self.motors[0]._fwd() + self.motors[1]._fwd())
            spin = (self.motors[0]._fwd() - self.motors[1]._fwd())
        else:
            w, spin = 0.0, 0.0
        v = w * TRUTH["k"]
        self.g -= v * dt
        if self.g <= 0.0:
            self.g = 0.0
            self.contact = True
        self.heading += (spin * TRUTH["k"] / 120.0) * dt * 57.3
        if abs(v) > 1.0:
            self.heading += TRUTH["yaw_rate_bias"] * dt
        self.t += dt
        self.hist.append((self.t, self.g))

    def gap_at(self, t_past):
        for (tt, gg) in reversed(self.hist):
            if tt <= t_past:
                return gg
        return self.hist[0][1]


W = World()
COST = 0.0004        # s of wall time charged per device read (loop overhead)


def charge(sec=COST):
    W.step(sec)


# ------------------------------------------------------------------ fake modules
class Port:
    A, B, C, D, E, F = "A", "B", "C", "D", "E", "F"


LAYOUT = {"A": "motor", "B": "ultrasonic", "C": "motor",
          "D": "ultrasonic", "E": "ultrasonic", "F": "color"}
CLAIMED = set()


class _Control:
    def __init__(self):
        self.lim = [TRUTH["omega_ceiling"], 1000.0, 100.0]

    def limits(self, speed=None, acceleration=None, torque=None):
        if acceleration is not None:
            self.lim[1] = acceleration
            TRUTH["accel_limit"] = acceleration
        if speed is not None:
            self.lim[0] = speed
        return tuple(self.lim)


class Motor:
    def __init__(self, port):
        if LAYOUT.get(port) != "motor":
            raise OSError(19, "ENODEV")
        if port in CLAIMED:
            raise OSError(16, "EBUSY")
        CLAIMED.add(port)
        self.port = port
        self.mirror = -1.0 if (TRUTH["mirrored"] and port == "C") else 1.0
        self.w = 0.0            # deg/s in the motor's own sign convention
        self.ang = 0.0
        self.mode = "brake"
        self.cmd = 0.0
        self.control = _Control()
        W.motors.append(self)

    # forward-referenced wheel rate (physical, sign-corrected)
    def _fwd(self):
        return self.w * self.mirror

    def _step(self, dt):
        if self.mode == "run":
            tgt = max(-TRUTH["omega_ceiling"], min(TRUTH["omega_ceiling"], self.cmd))
            dw = TRUTH["accel_limit"] * dt
            self.w += max(-dw, min(dw, tgt - self.w))
        elif self.mode == "dc":
            a = TRUTH["a_brake_mm"] / TRUTH["k"] * dt
            tgt = math.copysign(TRUTH["omega_ceiling"], self.cmd)
            self.w += max(-a, min(a, tgt - self.w))
        else:  # brake
            a = TRUTH["a_coast_mm"] / TRUTH["k"] * dt
            if abs(self.w) <= a:
                self.w = 0.0
            else:
                self.w -= math.copysign(a, self.w)
        self.ang += self.w * dt

    def run(self, speed):
        charge(); self.mode = "run"; self.cmd = speed

    def dc(self, duty):
        charge(); self.mode = "dc"; self.cmd = duty

    def brake(self):
        charge(); self.mode = "brake"

    def stop(self):
        charge(); self.mode = "brake"

    def angle(self):
        charge(); return int(self.ang)

    def speed(self):
        charge(); return int(self.w)


class UltrasonicSensor:
    def __init__(self, port):
        if LAYOUT.get(port) != "ultrasonic":
            raise OSError(19, "ENODEV")
        if port in CLAIMED:
            raise OSError(16, "EBUSY")
        CLAIMED.add(port)
        self.port = port
        self.rear = (port == "E")
        self.b = TRUTH["bA"] if port == "B" else TRUTH["bB"]
        self._last_t = -1.0
        self._last_v = 0

    def distance(self):
        charge()
        if self.rear:
            return 2000
        grid = math.floor((W.t - TRUTH["tau"]) / TRUTH["refresh"]) * TRUTH["refresh"]
        if grid != self._last_t:
            self._last_t = grid
            g = W.gap_at(grid)
            r = g + self.b + random.gauss(0.0, TRUTH["noise"])
            if r < TRUTH["floor"]:
                r = TRUTH["floor"]
            self._last_v = int(round(r))
        return self._last_v


class ColorSensor:
    def __init__(self, port):
        if LAYOUT.get(port) != "color":
            raise OSError(19, "ENODEV")
        CLAIMED.add(port)

    def reflection(self):
        charge(); return 42


class _IMU:
    def heading(self):
        charge(); return W.heading - W.head_ref

    def reset_heading(self, v=0.0):
        W.head_ref = W.heading - v

    def acceleration(self):
        charge(); return (0.0, 0.0, 9810.0)

    def angular_velocity(self):
        charge()
        if len(W.motors) >= 2:
            spin = (W.motors[0]._fwd() - W.motors[1]._fwd()) * TRUTH["k"] / 120.0 * 57.3
        else:
            spin = 0.0
        return (0.0, 0.0, spin)


class PrimeHub:
    def __init__(self, **kw):
        self.imu = _IMU()


class StopWatch:
    def __init__(self):
        self.t0 = W.t

    def time(self):
        return int((W.t - self.t0) * 1000.0)


def wait(ms):
    remaining = ms / 1000.0
    while remaining > 0:
        dt = min(0.001, remaining)
        W.step(dt)
        remaining -= dt


def install():
    pk = types.ModuleType("pybricks")
    for name, attrs in (
        ("pybricks.hubs", {"PrimeHub": PrimeHub}),
        ("pybricks.pupdevices", {"Motor": Motor, "UltrasonicSensor": UltrasonicSensor,
                                 "ColorSensor": ColorSensor}),
        ("pybricks.parameters", {"Port": Port}),
        ("pybricks.tools", {"StopWatch": StopWatch, "wait": wait}),
    ):
        m = types.ModuleType(name)
        m.__dict__.update(attrs)
        sys.modules[name] = m
    sys.modules["pybricks"] = pk
    us = types.ModuleType("usys")
    us.stdout = io.StringIO()
    sys.modules["usys"] = us
    return us


def run(path):
    us = install()
    src = open(path).read()
    g = {"__name__": "__main__"}
    exc = None
    try:
        exec(compile(src, path, "exec"), g)
    except Exception as e:                      # noqa: BLE001
        exc = e
    out = us.stdout.getvalue()
    return out, exc, g


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "04_run1_program.py"
    out, exc, g = run(path)
    lines = [l for l in out.splitlines() if l.strip()]
    print("=" * 70)
    print("DRY RUN:", path)
    print("=" * 70)
    if exc:
        print("!! EXCEPTION:", type(exc).__name__, exc)
    print("simulated wall time : %.2f s" % W.t)
    print("telemetry lines     :", len(lines))
    print("ends with sentinel  :", lines[-1] if lines else "(none)")
    print("CONTACT WITH WALL   :", W.contact)
    print("final true gap      : %.1f mm" % W.g)
    print("buffer used         :", g.get("n"), "of", g.get("NBUF"))
    print()
    keep = ("trigger_reason", "d_trigger", "r_rest_fused", "S_ranger", "S_odometry",
            "heading_at_trigger", "creep_reason", "creep_r_fused", "creep2_d_trigger",
            "R0_fused", "sgn_left", "sgn_right", "samples_buffered", "yaw_axis_idx")
    import json
    for l in lines:
        try:
            d = json.loads(l)
        except Exception:
            continue
        if d.get("sensor") in keep:
            print("  %-20s %10.2f   @%6d ms" % (d["sensor"], d["value"], d["timestamp_ms"]))
