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
MMPD = 0.529
BRAKEDIST = 15.0
GAP = 60.0
FLOOR = 80.0
SPEED = 1400

C = Motor(Port.C); D = Motor(Port.D)
A = UltrasonicSensor(Port.A); B = UltrasonicSensor(Port.B)

def rd(s):
    d = s.distance()
    return 9999 if d is None else d

sa = 0.0; sb = 0.0; n = 0
for i in range(6):
    sa += rd(A); sb += rd(B); n += 1
    wait(10)
avgA = sa / n; avgB = sb / n
D0 = avgA if avgA < avgB else avgB
L_trigger = D0 - GAP - BRAKEDIST

C0 = C.angle(); Dg0 = D.angle()
h0 = hub.imu.heading()

buf_t = []; buf_dm = []; buf_tr = []
last_rec = -1000
braked = False
brake_travel = 0.0
brake_reason = 0
brake_t = 0
maxsp = 0.0
last_ct = 0
last_ct_travel = 0.0
contact_flag = 0

C.run(FWD_C * SPEED); D.run(FWD_D * SPEED)
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
    if now - last_rec >= 12:
        buf_t.append(now); buf_dm.append(dmin); buf_tr.append(travel)
        last_rec = now
    if not braked:
        if now - last_ct >= 40:
            if travel > 150 and (travel - last_ct_travel) < 4:
                contact_flag = 1; brake_reason = 4
                C.brake(); D.brake(); braked = True; brake_travel = travel; brake_t = now
            last_ct = now
            last_ct_travel = travel
        if not braked and travel >= L_trigger:
            brake_reason = 1
            C.brake(); D.brake(); braked = True; brake_travel = travel; brake_t = now
        if not braked and dmin <= FLOOR:
            brake_reason = 2
            C.brake(); D.brake(); braked = True; brake_travel = travel; brake_t = now
        if not braked and travel >= (D0 - 30):
            brake_reason = 3
            C.brake(); D.brake(); braked = True; brake_travel = travel; brake_t = now
        if not braked and (now - t0) >= 3500:
            brake_reason = 5
            C.brake(); D.brake(); braked = True; brake_travel = travel; brake_t = now
    else:
        if (now - brake_t) >= 700:
            break
    wait(1)

C.brake(); D.brake()
wait(250)
sa = 0.0; sb = 0.0; n = 0
for i in range(6):
    sa += rd(A); sb += rd(B); n += 1
    wait(10)
fA = sa / n; fB = sb / n
f_reading = fA if fA < fB else fB
rotf = (FWD_C * (C.angle() - C0) + FWD_D * (D.angle() - Dg0)) / 2.0
final_travel = rotf * MMPD
max_mms = maxsp * MMPD
dhead = hub.imu.heading() - h0
predicted = D0 - final_travel
enc_brakedist_meas = final_travel - brake_travel

for _ in range(2):
    emit("R_D0", D0); emit("R_freading", f_reading)
    emit("R_finaltravel", final_travel); emit("R_predicted", predicted)
    emit("R_maxmms", max_mms); emit("R_dhead", dhead)
    emit("R_reason", brake_reason); emit("R_contact", contact_flag)
    emit("R_encbrake", enc_brakedist_meas); emit("R_fA", fA); emit("R_fB", fB)
    wait(5)

print("=== RUN4 ===")
print("D0=%d GAP=%d Ltrig=%d" % (int(D0), int(GAP), int(L_trigger)))
print("f_reading=%d predicted=%d final_travel=%d" % (int(f_reading), int(predicted), int(final_travel)))
print("max_mms=%d dhead=%d reason=%d contact=%d encbrake=%d" % (int(max_mms), int(dhead), brake_reason, contact_flag, int(enc_brakedist_meas)))
print("fA=%d fB=%d" % (int(fA), int(fB)))

N = len(buf_t)
step = 1 if N <= 15 else (N + 14) // 15
i = 0
while i < N:
    emit("s_t", buf_t[i]); emit("s_dm", buf_dm[i]); emit("s_tr", buf_tr[i])
    i += step

stdout.write('{"event":"end"}\n')
