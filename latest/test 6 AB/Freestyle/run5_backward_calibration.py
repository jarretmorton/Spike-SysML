from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()

def emit(s, v):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n' % (clock.time(), s, float(v)))

FWD_C = -1
FWD_D = 1
SPEED = 1400
ROT_TARGET = 1200.0

C = Motor(Port.C); D = Motor(Port.D)
A = UltrasonicSensor(Port.A); B = UltrasonicSensor(Port.B)

def rd(s):
    d = s.distance()
    return 9999 if d is None else d

sa = 0.0; sb = 0.0; n = 0
for i in range(8):
    sa += rd(A); sb += rd(B); n += 1
    wait(10)
A0 = sa / n; B0 = sb / n

C0 = C.angle(); Dg0 = D.angle()

buf_t = []; buf_a = []; buf_rot = []
last_rec = -1000
maxsp = 0.0

C.run(-FWD_C * SPEED); D.run(-FWD_D * SPEED)
t0 = clock.time()
while True:
    a = rd(A)
    rot = (FWD_C * (C.angle() - C0) + FWD_D * (D.angle() - Dg0)) / 2.0
    backdeg = -rot
    sp = C.speed(); asp = sp if sp >= 0 else -sp
    if asp > maxsp:
        maxsp = asp
    now = clock.time()
    if now - last_rec >= 15:
        buf_t.append(now); buf_a.append(a); buf_rot.append(backdeg)
        last_rec = now
    if backdeg >= ROT_TARGET:
        C.brake(); D.brake(); break
    if (now - t0) >= 4000:
        C.brake(); D.brake(); break
    wait(1)

C.brake(); D.brake()
wait(300)
sa = 0.0; sb = 0.0; n = 0
for i in range(8):
    sa += rd(A); sb += rd(B); n += 1
    wait(10)
A1 = sa / n; B1 = sb / n
rotf = (FWD_C * (C.angle() - C0) + FWD_D * (D.angle() - Dg0)) / 2.0
backdeg_final = -rotf
dA = A1 - A0
mmpd = dA / backdeg_final if backdeg_final != 0 else 0.0
max_mms_est = maxsp * mmpd

for _ in range(2):
    emit("R_A0", A0); emit("R_A1", A1); emit("R_B0", B0); emit("R_B1", B1)
    emit("R_backdeg", backdeg_final); emit("R_dA", dA)
    emit("R_mmpd_x1000", mmpd * 1000.0); emit("R_maxmms", max_mms_est)
    wait(5)

print("=== RUN5 backcal ===")
print("A0=%d A1=%d dA=%d backdeg=%d" % (int(A0), int(A1), int(dA), int(backdeg_final)))
print("B0=%d B1=%d" % (int(B0), int(B1)))
print("mmpd_x1000=%d maxmms=%d" % (int(mmpd * 1000), int(max_mms_est)))

N = len(buf_t)
step = 1 if N <= 10 else (N + 9) // 10
i = 0
while i < N:
    emit("s_t", buf_t[i]); emit("s_a", buf_a[i]); emit("s_rot", buf_rot[i])
    i += step

stdout.write('{"event":"end"}\n')
