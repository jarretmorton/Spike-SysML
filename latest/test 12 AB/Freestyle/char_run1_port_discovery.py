"""
CHARACTERIZATION RUN 1 — Port discovery and direction test
Scans all 6 ports to identify motors, ultrasonic sensors, and color sensor.
Runs a brief +500/-500 direction test to determine which motor sign moves toward wall.
"""
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

all_ports = [Port.A, Port.B, Port.C, Port.D, Port.E, Port.F]
pn = {Port.A:'A', Port.B:'B', Port.C:'C', Port.D:'D', Port.E:'E', Port.F:'F'}

motors = {}
ultrasonics = {}
colors = {}

try:
    for p in all_ports:
        try:
            m = Motor(p)
            motors[p] = m
        except:
            pass

    claimed = set(motors.keys())

    for p in all_ports:
        if p not in claimed:
            try:
                u = UltrasonicSensor(p)
                ultrasonics[p] = u
                claimed.add(p)
            except:
                pass

    for p in all_ports:
        if p not in claimed:
            try:
                c = ColorSensor(p)
                colors[p] = c
                claimed.add(p)
            except:
                pass

    # 1=motor, 2=ultrasonic, 3=color, 0=none
    for p in all_ports:
        t = 1 if p in motors else (2 if p in ultrasonics else (3 if p in colors else 0))
        emit('port_' + pn[p], t)

    wait(300)

    # Static baseline readings
    emit('hdg0', hub.imu.heading())
    for p, u in ultrasonics.items():
        try:
            d = u.distance()
            emit('d0_' + pn[p], float(d) if d is not None else -1)
        except:
            emit('d0_' + pn[p], -1)
    for p, c in colors.items():
        try:
            emit('refl_' + pn[p], float(c.reflection()))
        except:
            emit('refl_' + pn[p], -1)

    wait(200)

    # Direction test: both motors +500 for 250 ms
    mp = sorted(motors.keys(), key=lambda p: pn[p])
    if len(mp) >= 2:
        for p in mp:
            motors[p].run(500)
        wait(250)
        for p in mp:
            motors[p].brake()
        wait(400)

        emit('hdg_pp', hub.imu.heading())
        for p, u in ultrasonics.items():
            try:
                d = u.distance()
                emit('dpp_' + pn[p], float(d) if d is not None else -1)
            except:
                emit('dpp_' + pn[p], -1)

        wait(200)

        # Reverse back to start
        for p in mp:
            motors[p].run(-500)
        wait(250)
        for p in mp:
            motors[p].brake()
        wait(400)

        emit('hdg_mn', hub.imu.heading())
        for p, u in ultrasonics.items():
            try:
                d = u.distance()
                emit('dmn_' + pn[p], float(d) if d is not None else -1)
            except:
                emit('dmn_' + pn[p], -1)

finally:
    for m in motors.values():
        try:
            m.brake()
        except:
            pass
    stdout.write('{"event":"end"}\n')
