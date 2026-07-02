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
MMPD = 0.448
THRESH = 350.0

C = Motor(Port.C)
D = Motor(Port.D)
A = UltrasonicSensor(Port.A)
B = UltrasonicSensor(Port.B)

def rd(s):
    d = s.distance()
    return 9999 if d is None else d

sa = 0.0; sb = 0.0; n = 0
for i in range(6):
    sa += rd(A); sb += rd(B); n += 1
    wait(10)
avgA = sa / n; avgB = sb / n
D0 = avgA if avgA < avgB else avgB

C0 = C.angle(); Dg0 = D.angle()
h0 = hub.imu.heading()

buf_t = []; buf_dm = []; buf_tr = []
last_rec = -1000
prev_below = False
braked = False
brake_travel = 0.0; brake_dmin = 0.0; brake_t = 0
maxsp = 0.0

C.run(FWD_C * 1400); D.run(FWD_D * 1400)
t0 = clock.time()
while True:
    da = rd(A); db = rd(B)
    dmin = da if da < db else db
    rot = (FWD_C * (C.angle() - C0) + FWD_D * (D.angle() - Dg0)) / 2.0
    travel = rot * MMPD
    sp = C.speed()
    asp = sp if sp >= 0 else -sp
    if asp > maxsp:
        maxsp = asp
    now = clock.time()
    if now - last_rec >= 10:
        buf_t.append(now); buf_dm.append(dmin); buf_tr.append(travel)
        last_rec = now
    if not braked:
        below = dmin <= THRESH
        if below and prev_below:
            C.brake(); D.brake(); braked = True
            brake_travel = travel; brake_dmin = dmin; brake_t = now
        prev_below = below
        if (now - t0) >= 4000:
            C.brake(); D.brake(); braked = True
            brake_travel = travel; brake_dmin = dmin; brake_t = now
        if travel >= (D0 - 300):
            C.brake(); D.brake(); braked = True
            brake_travel = travel; brake_dmin = dmin; brake_t = now
    else:
        if (now - brake_t) >= 700:
            break
    wait(1)

C.brake(); D.brake()
wait(200)
sa = 0.0; sb = 0.0; n = 0
for i in range(6):
    sa += rd(A); sb += rd(B); n += 1
    wait(10)
fA = sa / n; fB = sb / n
f_dmin = fA if fA < fB else fB
rotf = (FWD_C * (C.angle() - C0) + FWD_D * (D.angle() - Dg0)) / 2.0
final_travel = rotf * MMPD

max_mms = maxsp * MMPD
dclose = brake_dmin - f_dmin
enc_brakedist = final_travel - brake_travel
dhead = hub.imu.heading() - h0

N = len(buf_t)
step = 1 if N <= 30 else (N + 29) // 30
i = 0
while i < N:
    emit("s_t", buf_t[i]); emit("s_dm", buf_dm[i]); emit("s_tr", buf_tr[i])
    i += step

for _ in range(2):
    emit("res_D0", D0); emit("res_avgA", avgA); emit("res_avgB", avgB)
    emit("res_maxmms", max_mms); emit("res_brake_dmin", brake_dmin)
    emit("res_f_dmin", f_dmin); emit("res_dclose", dclose)
    emit("res_brake_travel", brake_travel); emit("res_final_travel", final_travel)
    emit("res_encbrake", enc_brakedist); emit("res_dhead", dhead)
    emit("res_fA", fA); emit("res_fB", fB)
    wait(10)

print("=== RUN3 ===")
print("D0=%d avgA=%d avgB=%d" % (int(D0), int(avgA), int(avgB)))
print("max_mms=%d" % int(max_mms))
print("brake_dmin=%d f_dmin=%d dclose=%d" % (int(brake_dmin), int(f_dmin), int(dclose)))
print("brake_travel=%d final_travel=%d enc_brakedist=%d" % (int(brake_travel), int(final_travel), int(enc_brakedist)))
print("fA=%d fB=%d dhead=%d" % (int(fA), int(fB), int(dhead)))
stdout.write('{"event":"end"}\n')
