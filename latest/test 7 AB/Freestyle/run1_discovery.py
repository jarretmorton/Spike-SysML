# Run 1 — DISCOVERY (characterization)
# Probes ports A-F for device type, reads all ultrasonics statically to find the
# forward pair vs rear, reads each motor's max-speed limit, then runs two short
# go-and-return motor pulses while logging heading to distinguish translation
# from spin and find which command drives toward the wall. Stays near the start line.
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, ColorSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()

def emit(sensor, value):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n'
                 % (clock.time(), sensor, value))

ports = [("A", Port.A), ("B", Port.B), ("C", Port.C),
         ("D", Port.D), ("E", Port.E), ("F", Port.F)]

motors = []
ultras = []
colors = []

for name, p in ports:
    try:
        motors.append((name, Motor(p))); continue
    except Exception:
        pass
    try:
        ultras.append((name, UltrasonicSensor(p))); continue
    except Exception:
        pass
    try:
        colors.append((name, ColorSensor(p))); continue
    except Exception:
        pass

def read_all(phase):
    emit("heading", hub.imu.heading())
    emit("phase", phase)
    for nm, s in ultras:
        try:
            emit("dist_%s" % nm, s.distance())
        except Exception:
            emit("dist_%s" % nm, -1)

try:
    for nm, m in motors:
        try:
            emit("maxspeed_%s" % nm, m.control.limits()[0])
        except Exception:
            pass
    for nm, c in colors:
        try:
            emit("reflect_%s" % nm, c.reflection())
        except Exception:
            pass
    # static baseline ~0.8 s
    for i in range(16):
        read_all(0)
        wait(50)

    if len(motors) >= 2:
        m0 = motors[0][1]; m1 = motors[1][1]
        TS = 200
        wait(200)
        # Test A: (+,+) then return (-,-)
        m0.run(TS); m1.run(TS)
        for i in range(12):
            read_all(1); wait(50)
        m0.brake(); m1.brake(); wait(300)
        m0.run(-TS); m1.run(-TS)
        for i in range(12):
            read_all(2); wait(50)
        m0.brake(); m1.brake(); wait(500)
        # Test B: (+,-) then return (-,+)
        m0.run(TS); m1.run(-TS)
        for i in range(12):
            read_all(3); wait(50)
        m0.brake(); m1.brake(); wait(300)
        m0.run(-TS); m1.run(TS)
        for i in range(12):
            read_all(4); wait(50)
        m0.brake(); m1.brake(); wait(200)
finally:
    for nm, m in motors:
        try: m.brake()
        except Exception: pass
    stdout.write("MAP motors=%s ultra=%s color=%s\n" % (
        ",".join(n for n, _ in motors),
        ",".join(n for n, _ in ultras),
        ",".join(n for n, _ in colors)))
    stdout.write('{"event":"end"}\n')
