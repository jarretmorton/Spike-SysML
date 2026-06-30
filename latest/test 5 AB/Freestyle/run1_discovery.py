# Run 1 — Static discovery.
# Maps every port to its device, identifies forward vs rear ultrasonics,
# finds the color sensor, and determines the straight-line motor sign pair.
# No fast motion: short, slow pulses only; rover stays ~1 m from the wall.

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, ColorSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()

def emit(sensor, value):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n' % (clock.time(), sensor, value))

ports = [("A", Port.A), ("B", Port.B), ("C", Port.C),
         ("D", Port.D), ("E", Port.E), ("F", Port.F)]
motors, ultras, colors = [], [], []
code = {"motor":1.0, "ultrasonic":2.0, "color":3.0, "none":0.0}
pidx = {"A":1.0,"B":2.0,"C":3.0,"D":4.0,"E":5.0,"F":6.0}

try:
    for nm, p in ports:
        dev = "none"
        try:
            m = Motor(p); motors.append((nm, m)); dev = "motor"
        except Exception:
            try:
                s = UltrasonicSensor(p); ultras.append((nm, s)); dev = "ultrasonic"
            except Exception:
                try:
                    c = ColorSensor(p); colors.append((nm, c)); dev = "color"
                except Exception:
                    dev = "none"
        emit("port_"+nm, code[dev])

    wait(200)

    fwd = []
    for nm, s in ultras:
        try: d = s.distance()
        except Exception: d = -1.0
        emit("usStat_"+nm, d)
        if 600 < d < 1400:
            fwd.append((nm, s))

    for nm, c in colors:
        try: r = c.reflection()
        except Exception: r = -1.0
        emit("refl_"+nm, r)

    emit("heading_start", hub.imu.heading())
    emit("num_fwd", float(len(fwd)))
    emit("num_motors", float(len(motors)))

    def fdist():
        best = 5000.0
        for nm, s in fwd:
            try:
                d = s.distance()
                if 0 < d < best: best = d
            except Exception: pass
        return best

    if len(motors) >= 2:
        nA, mA = motors[0]
        nB, mB = motors[1]
        emit("motorA_port", pidx[nA])
        emit("motorB_port", pidx[nB])
        mA.reset_angle(0); mB.reset_angle(0)

        emit("t1_h_before", hub.imu.heading()); emit("t1_d_before", fdist())
        mA.run(200); mB.run(200); wait(350); mA.brake(); mB.brake(); wait(500)
        emit("t1_h_after", hub.imu.heading()); emit("t1_d_after", fdist())
        emit("t1_angA", mA.angle()); emit("t1_angB", mB.angle())

        mA.reset_angle(0); mB.reset_angle(0); wait(300)

        emit("t2_h_before", hub.imu.heading()); emit("t2_d_before", fdist())
        mA.run(200); mB.run(-200); wait(350); mA.brake(); mB.brake(); wait(500)
        emit("t2_h_after", hub.imu.heading()); emit("t2_d_after", fdist())
        emit("t2_angA", mA.angle()); emit("t2_angB", mB.angle())
finally:
    for _, m in motors:
        try: m.brake()
        except Exception: pass
    stdout.write('{"event":"end"}\n')
