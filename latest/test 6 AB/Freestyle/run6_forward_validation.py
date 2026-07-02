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
MMPD = 0.484
BRAKEDIST = 14.0
A_OFFSET = 44.0
GAP = 140.0
SPEED = 1400

C = Motor(Port.C); D = Motor(Port.D)
A = UltrasonicSensor(Port.A); B = UltrasonicSensor(Port.B)

def rd(s):
    d = s.distance()
    return 9999 if d is None else d

sa = 0.0; n = 0; amn = 99999.0; amx = 0.0; sb = 0.0
for i in range(12):
    a = rd(A); b = rd(B)
    sa += a; sb += b; n += 1
    if a < amn: amn = a
    if a > amx: amx = a
    wait(12)
A0 = sa / n; B0 = sb / n
bumper_start = A0 - A_OFFSET
Ltrig = bumper_start - GAP - BRAKEDIST

C0 = C.angle(); Dg0 = D.angle()
h0 = hub.imu.heading()

buf_t = []; buf_a = []; buf_tr = []
last_rec = -1000
braked = False; brake_travel = 0.0; brake_reason = 0; brake_t = 0
maxsp = 0.0
last_ct = 0; last_ct_tr = 0.0; contact = 0

C.run(FWD_C * SPEED); D.run(FWD_D * SPEED)
t0 = clock.time()
while True:
    a = rd(A)
    rot = (FWD_C * (C.angle() - C0) + FWD_D * (D.angle() - Dg0)) / 2.0
    travel = rot * MMPD
    sp = C.speed(); asp = sp if sp >= 0 else -sp
    if asp > maxsp: maxsp = asp
    now = clock.time()
    if now - last_rec >= 12:
        buf_t.append(now); buf_a.append(a); buf_tr.append(travel)
        last_rec = now
    if not braked:
        if now - last_ct >= 40:
            if travel > 150 and (travel - last_ct_tr) < 4:
                contact = 1; brake_reason = 4
                C.brake(); D.brake(); braked = True; brake_travel = travel; brake_t = now
            last_ct = now; last_ct_tr = travel
        if not braked and travel >= Ltrig:
            brake_reason = 1
            C.brake(); D.brake(); braked = True; brake_travel = travel; brake_t = now
        if not braked and travel >= (bumper_start - 20):
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
sa = 0.0; n = 0; fmn = 99999.0; fmx = 0.0; sb = 0.0
for i in range(12):
    a = rd(A); b = rd(B)
    sa += a; sb += b; n += 1
    if a < fmn: fmn = a
    if a > fmx: fmx = a
    wait(12)
Afin = sa / n; Bfin = sb / n
rotf = (FWD_C * (C.angle() - C0) + FWD_D * (D.angle() - Dg0)) / 2.0
final_travel = rotf * MMPD
pred_bumper = bumper_start - final_travel
max_mms = maxsp * MMPD
dhead = hub.imu.heading() - h0
encbrake = final_travel - brake_travel

for _ in range(2):
    emit("R_A0", A0); emit("R_A0min", amn); emit("R_A0max", amx)
    emit("R_Afin", Afin); emit("R_Afinmin", fmn); emit("R_Afinmax", fmx)
    emit("R_bstart", bumper_start); emit("R_finaltravel", final_travel)
    emit("R_predbump", pred_bumper); emit("R_maxmms", max_mms)
    emit("R_dhead", dhead); emit("R_reason", brake_reason)
    emit("R_contact", contact); emit("R_encbrake", encbrake)
    emit("R_B0", B0); emit("R_Bfin", Bfin)
    wait(5)

print("=== RUN6 val ===")
print("A0=%d [%d-%d] bstart=%d Ltrig=%d" % (int(A0), int(amn), int(amx), int(bumper_start), int(Ltrig)))
print("Afin=%d [%d-%d] pred_bumper=%d final_travel=%d" % (int(Afin), int(fmn), int(fmx), int(pred_bumper), int(final_travel)))
print("max_mms=%d dhead=%d reason=%d contact=%d encbrake=%d" % (int(max_mms), int(dhead), brake_reason, contact, int(encbrake)))
print("B0=%d Bfin=%d" % (int(B0), int(Bfin)))

N = len(buf_t)
step = 1 if N <= 12 else (N + 11) // 12
i = 0
while i < N:
    emit("s_t", buf_t[i]); emit("s_a", buf_a[i]); emit("s_tr", buf_tr[i])
    i += step

stdout.write('{"event":"end"}\n')
