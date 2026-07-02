from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()

def emit(s, v):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n' % (clock.time(), s, float(v)))

C = Motor(Port.C)
D = Motor(Port.D)
A = UltrasonicSensor(Port.A)
B = UltrasonicSensor(Port.B)

def dA_read():
    d = A.distance()
    return -1 if d is None else d

def dB_read():
    d = B.distance()
    return -1 if d is None else d

emit("phase", 1)
for i in range(6):
    t0 = clock.time()
    d = dA_read()
    dt = clock.time() - t0
    emit("readA_ms", dt)
    emit("distA", d)

emit("phase", 2)
sa = 0; ca = 0; sb = 0; cb = 0
for i in range(4):
    t0 = clock.time(); da = dA_read(); ea = clock.time() - t0
    t1 = clock.time(); db = dB_read(); eb = clock.time() - t1
    emit("readA_ms", ea); emit("readB_ms", eb)
    emit("distA", da); emit("distB", db)
    if da >= 0:
        sa += da; ca += 1
    if db >= 0:
        sb += db; cb += 1
D0A = sa / ca if ca else -1
D0B = sb / cb if cb else -1

emit("phase", 3)
fc = 1
fd = -1
C0 = C.angle(); Dg0 = D.angle()
h0 = hub.imu.heading()
C.run(fc * 400); D.run(fd * 400)
t0 = clock.time()
try:
    while True:
        dc = (C.angle() - C0) * fc
        dd = (D.angle() - Dg0) * fd
        rot = (dc + dd) / 2.0
        emit("rot_deg", rot)
        emit("heading", hub.imu.heading())
        if (clock.time() - t0) >= 700:
            break
        if rot >= 500 or rot <= -500:
            break
        wait(5)
finally:
    C.brake(); D.brake()
wait(400)
C1 = C.angle(); Dg1 = D.angle()
h1 = hub.imu.heading()

emit("phase", 4)
sa = 0; ca = 0; sb = 0; cb = 0
for i in range(4):
    da = dA_read(); db = dB_read()
    emit("distA", da); emit("distB", db)
    if da >= 0:
        sa += da; ca += 1
    if db >= 0:
        sb += db; cb += 1
D1A = sa / ca if ca else -1
D1B = sb / cb if cb else -1

fwd_rot = ((C1 - C0) * fc + (Dg1 - Dg0) * fd) / 2.0
avg_change = 0.0; nch = 0
if D0A >= 0 and D1A >= 0:
    avg_change += (D0A - D1A); nch += 1
if D0B >= 0 and D1B >= 0:
    avg_change += (D0B - D1B); nch += 1
avg_change = avg_change / nch if nch else 0.0
dhead = h1 - h0

if avg_change > 20:
    FWD_C = fc; FWD_D = fd; dirc = 1
elif avg_change < -20:
    FWD_C = -fc; FWD_D = -fd; dirc = -1
else:
    FWD_C = fc; FWD_D = fd; dirc = 0

mm_per_deg = (abs(avg_change) / abs(fwd_rot)) if fwd_rot != 0 else 0.0

for _ in range(3):
    emit("res_D0A", D0A); emit("res_D0B", D0B)
    emit("res_D1A", D1A); emit("res_D1B", D1B)
    emit("res_fwd_rot", fwd_rot)
    emit("res_avg_change", avg_change)
    emit("res_dhead", dhead)
    emit("res_mmdeg_x1000", mm_per_deg * 1000.0)
    emit("res_FWD_C", FWD_C); emit("res_FWD_D", FWD_D)
    emit("res_dir", dirc)
    wait(10)

print("=== RUN2 ===")
print("D0A=%d D0B=%d offsetAB=%d" % (int(D0A), int(D0B), int(D0A - D0B)))
print("D1A=%d D1B=%d" % (int(D1A), int(D1B)))
print("fwd_rot_deg=%d avg_change_mm=%d dHead=%d" % (int(fwd_rot), int(avg_change), int(dhead)))
print("mm_per_deg_x1000=%d" % int(mm_per_deg * 1000))
print("FORWARD C=%+d D=%+d dir=%d" % (FWD_C, FWD_D, dirc))

stdout.write('{"event":"end"}\n')
