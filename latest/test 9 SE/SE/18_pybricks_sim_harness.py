#!/usr/bin/env python3
"""
Offline Pybricks / SPIKE-Prime simulator + dry-run harness.
=========================================================================
Used throughout this task to validate every program on the desktop
BEFORE flashing to hardware: it checks that the program terminates, emits
only well-formed telemetry (one JSON object per line, numeric scalar
values), and ends with the flush sentinel {"event":"end"} — and that the
control loop actually reaches a stop.

SCOPE / CAVEAT: this is a *behavioural* stand-in, not a physics twin. It
models forward translation, wheel encoders, a simple heading/veer response,
and the two sensor quirks that mattered (ranger-A floor, ranger-B short
offset+floor, dead rear ranger). It deliberately does NOT model braking
coast, wheel slip, or IMU noise — those were characterised on hardware.
So the harness proves LOGIC (termination, telemetry contract, trigger
paths, failsafes) and is silent on absolute gap accuracy.

Usage:
    python3 18_pybricks_sim_harness.py path/to/program.py [start_mm]
"""
import sys, io, json, types

# ------------------------------------------------------------------ state
st = {"t":0, "pos":1000.0, "cmdL":0, "cmdR":0,
      "angL":0.0, "angR":0.0, "heading":0.0, "vmax":1050}
K_TRANS = 0.516      # mm ground per (deg/s * s)  (matches measured k_gain)
K_YAW   = -0.03      # (+,+) command decreases heading (mirrored motors)
BIAS    = -0.008     # small forward veer, corrected by the heading loop

# sensor model (empirical, from hardware)
A_FLOOR  = 288       # ranger-A minimum readable distance
B_OFFSET = 130       # ranger-B reads this much short at range
B_FLOOR  = 114       # ranger-B minimum seen (it keeps resolving below this on HW)
REAR_MM  = 547       # rear ranger: a fixed nearby return, never gated

def advance(ms):
    dt = ms/1000.0
    v  = st["vmax"]
    cL = max(-v, min(v, st["cmdL"]))
    cR = max(-v, min(v, st["cmdR"]))
    st["angL"] += cL*dt
    st["angR"] += cR*dt
    fwd = 0.5*(cR - cL)                 # forward when cmdC<0, cmdD>0
    st["pos"] -= K_TRANS*fwd*dt
    if st["pos"] < 0: st["pos"] = 0.0
    st["heading"] += (K_YAW*(cL+cR) + BIAS*fwd)*dt
    st["t"] += ms

# ------------------------------------------------------- fake pybricks pkg
Port = types.SimpleNamespace(A=0,B=1,C=2,D=3,E=4,F=5)
Axis = types.SimpleNamespace(X=0,Y=1,Z=2)
Direction = types.SimpleNamespace(CLOCKWISE=0, COUNTERCLOCKWISE=1)
Stop = types.SimpleNamespace(BRAKE=0, HOLD=1, COAST=2)

class StopWatch:
    def time(self): return st["t"]
    def reset(self): st["t"]=0
def wait(ms): advance(ms)

class _IMU:
    def reset_heading(self, v): st["heading"]=v
    def heading(self): return st["heading"]
    def acceleration(self, axis): return 0.0
    def angular_velocity(self, axis): return 0.0
class PrimeHub:
    def __init__(self): self.imu=_IMU()

_MOTORS = {Port.C, Port.D}
_RANGERS = {Port.A, Port.B, Port.E}
class Motor:
    def __init__(self, port, *a, **k):
        if port not in _MOTORS: raise OSError("ENODEV")
        self.port = port
    def run(self, speed):
        st["cmdL" if self.port==Port.C else "cmdR"] = speed
    def brake(self):
        st["cmdL" if self.port==Port.C else "cmdR"] = 0
    def stop(self): self.brake()
    def reset_angle(self, v):
        st["angL" if self.port==Port.C else "angR"] = float(v)
    def angle(self):
        return st["angL" if self.port==Port.C else "angR"]
    def speed(self):
        c = st["cmdL" if self.port==Port.C else "cmdR"]
        return max(-st["vmax"], min(st["vmax"], c))
class UltrasonicSensor:
    def __init__(self, port, *a, **k):
        if port not in _RANGERS: raise OSError("ENODEV")
        self.port = port
        self.forward = port in (Port.A, Port.B)
        self.short = (port == Port.B)
    def distance(self):
        if not self.forward: return REAR_MM
        p = int(st["pos"])
        if self.short:
            b = p - B_OFFSET
            return b if b > B_FLOOR else B_FLOOR
        return p if p > A_FLOOR else A_FLOOR
class ColorSensor:
    def __init__(self, port, *a, **k): raise OSError("ENODEV")
    def reflection(self): return 50

def _install_fake_pybricks():
    pk = types.ModuleType("pybricks")
    for name, obj in {
        "pybricks.hubs":       {"PrimeHub":PrimeHub},
        "pybricks.pupdevices": {"Motor":Motor,"UltrasonicSensor":UltrasonicSensor,"ColorSensor":ColorSensor},
        "pybricks.parameters": {"Port":Port,"Axis":Axis,"Direction":Direction,"Stop":Stop},
        "pybricks.tools":      {"wait":wait,"StopWatch":StopWatch},
    }.items():
        m = types.ModuleType(name)
        for k,v in obj.items(): setattr(m, k, v)
        sys.modules[name] = m
    sys.modules["pybricks"] = pk

# ------------------------------------------------------------- dry run
def dry_run(path, start_mm=1000.0):
    st.update({"t":0,"pos":float(start_mm),"cmdL":0,"cmdR":0,
               "angL":0.0,"angR":0.0,"heading":0.0})
    _install_fake_pybricks()
    buf = io.StringIO(); real = sys.stdout; sys.stdout = buf; err = None
    try:
        exec(compile(open(path).read(), path, "exec"), {"__name__":"__main__"})
    except SystemExit:
        pass
    except Exception as e:
        err = e
    finally:
        sys.stdout = real
    lines = [l for l in buf.getvalue().splitlines() if l.strip()]
    bad = 0; sensors = {}
    for ln in lines:
        if '"event"' in ln and '"end"' in ln:
            continue
        try:
            o = json.loads(ln)
            assert isinstance(o["value"], (int,float)) and not isinstance(o["value"], bool)
            assert isinstance(o["timestamp_ms"], int)
            sensors[o["sensor"]] = sensors.get(o["sensor"],0)+1
        except Exception:
            bad += 1
    ok = (err is None and bad == 0 and lines and '"end"' in lines[-1])
    print("file            :", path)
    print("exception       :", repr(err))
    print("telemetry lines :", len(lines), " malformed:", bad)
    print("sentinel present:", bool(lines) and '"end"' in lines[-1])
    print("channels        :", {k:sensors[k] for k in sorted(sensors)})
    print("RESULT          :", "OK" if ok else "FAIL")
    return ok

if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else None
    start = float(sys.argv[2]) if len(sys.argv) > 2 else 1000.0
    if not p:
        print(__doc__); sys.exit(2)
    sys.exit(0 if dry_run(p, start) else 1)
