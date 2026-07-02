# ============================================================
# LOCKED OPERATIONAL PROGRAM
# Run UNCHANGED for all five scored operation runs.
# Encoder dead-reckoning stop; sensor A sampled once at the
# start as a coarse distance reference; hard brake triggered
# purely on encoder travel to leave the sensor mount ~100 mm
# from the wall (front bumper ~= 45 mm at the ~55 mm offset).
# ============================================================
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()

def emit(s, v):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n' % (clock.time(), s, float(v)))

FWD_C = -1          # forward = C negative, D positive
FWD_D = 1
MMPD = 0.484        # mm of travel per degree of wheel rotation
BRAKEDIST = 14.0    # mm coasted after brake() from full speed
T_AMOUNT = 100.0    # target sensor-mount distance to wall (mm)
A_OFFSET = 55.0     # sensor-mount-to-bumper offset (mm), for reporting only
SPEED = 1400        # commanded (saturates to true max)

C = Motor(Port.C); D = Motor(Port.D)
A = UltrasonicSensor(Port.A); B = UltrasonicSensor(Port.B)

def rd(s):
    d = s.distance()
    return 9999 if d is None else d

# --- start reference: average sensor A (reliable at ~1 m) ---
sa = 0.0; n = 0; amn = 99999.0; amx = 0.0
for i in range(12):
    a = rd(A)
    sa += a; n += 1
    if a < amn: amn = a
    if a > amx: amx = a
    wait(12)
A0 = sa / n
Ltrig = A0 - T_AMOUNT - BRAKEDIST     # encoder-travel trigger
BACKSTOP = A0 - 75.0                  # emergency: never travel past this

C0 = C.angle(); Dg0 = D.angle()
h0 = hub.imu.heading()

buf_t = []; buf_a = []; buf_tr = []
last_rec = -1000
braked = False; brake_travel = 0.0; brake_reason = 0; brake_t = 0
maxsp = 0.0
last_ct = 0; last_ct_tr = 0.0; contact = 0

# --- full-speed run at the wall ---
C.run(FWD_C * SPEED); D.run(FWD_D * SPEED)
t0 = clock.time()
while True:
    a = rd(A)
    rot = (FWD_C * (C.angle() - C0) + FWD_D * (D.angle() - Dg0)) / 2.0
    travel = rot * MMPD
    sp = C.speed(); asp = sp if sp >= 0 else -sp
    if asp > maxsp: maxsp = asp
    now = clock.time()
    if now - last_rec >= 12:                       # buffer, don't emit (BLE is slow)
        buf_t.append(now); buf_a.append(a); buf_tr.append(travel)
        last_rec = now
    if not braked:
        if now - last_ct >= 40:                    # wheel-stall contact detection
            if travel > 150 and (travel - last_ct_tr) < 4:
                contact = 1; brake_reason = 4
                C.brake(); D.brake(); braked = True; brake_travel = travel; brake_t = now
            last_ct = now; last_ct_tr = travel
        if not braked and travel >= Ltrig:         # PRIMARY: encoder trigger
            brake_reason = 1
            C.brake(); D.brake(); braked = True; brake_travel = travel; brake_t = now
        if not braked and travel >= BACKSTOP:      # emergency backstop
            brake_reason = 3
            C.brake(); D.brake(); braked = True; brake_travel = travel; brake_t = now
        if not braked and (now - t0) >= 3500:      # time cap
            brake_reason = 5
            C.brake(); D.brake(); braked = True; brake_travel = travel; brake_t = now
    else:
        if (now - brake_t) >= 700:
            break
    wait(1)

C.brake(); D.brake()
wait(250)
# --- final reads + onboard estimate ---
sa = 0.0; n = 0; fmn = 99999.0; fmx = 0.0
for i in range(12):
    a = rd(A)
    sa += a; n += 1
    if a < fmn: fmn = a
    if a > fmx: fmx = a
    wait(12)
Afin = sa / n
rotf = (FWD_C * (C.angle() - C0) + FWD_D * (D.angle() - Dg0)) / 2.0
final_travel = rotf * MMPD
amount_final = A0 - final_travel            # encoder estimate of mount distance
pred_bumper = amount_final - A_OFFSET       # onboard gap estimate
max_mms = maxsp * MMPD
dhead = hub.imu.heading() - h0
encbrake = final_travel - brake_travel

for _ in range(2):                          # summary first (survives BLE cutoff)
    emit("R_A0", A0); emit("R_A0min", amn); emit("R_A0max", amx)
    emit("R_finaltravel", final_travel); emit("R_amountfinal", amount_final)
    emit("R_predbump", pred_bumper); emit("R_Afin", Afin)
    emit("R_maxmms", max_mms); emit("R_dhead", dhead)
    emit("R_reason", brake_reason); emit("R_contact", contact)
    emit("R_encbrake", encbrake)
    wait(5)

print("=== OP RUN ===")
print("A0=%d [%d-%d] Ltrig=%d" % (int(A0), int(amn), int(amx), int(Ltrig)))
print("final_travel=%d amount_final=%d pred_bumper=%d Afin=%d" % (int(final_travel), int(amount_final), int(pred_bumper), int(Afin)))
print("max_mms=%d dhead=%d reason=%d contact=%d encbrake=%d" % (int(max_mms), int(dhead), brake_reason, contact, int(encbrake)))

N = len(buf_t)
step = 1 if N <= 12 else (N + 11) // 12
i = 0
while i < N:
    emit("s_t", buf_t[i]); emit("s_a", buf_a[i]); emit("s_tr", buf_tr[i])
    i += step

stdout.write('{"event":"end"}\n')
