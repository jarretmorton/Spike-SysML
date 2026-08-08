# operation_locked — THE LOCKED PROGRAM
# Flashed unchanged before each of the five scored operation runs.
# (The hub is power-cycled between runs, which wipes the program, so it was
#  re-flashed identically each time.)
#
# Run ids:
#   1  run-20260806-101238    gap 145 mm    backstop stop, sensor B reading ~14% low
#   2  run-20260806-101756    gap 148 mm    backstop stop, sensor B reading ~14% low
#   3  run-20260806-102053    gap  29 mm    clean trigger, S = 54.4
#   4  run-20260806-102411    gap  24 mm    clean trigger, S = 54.1
#   5  run-20260806-102554    gap  27 mm    clean trigger, S = 53.0
#
# Result: 5/5 no contact. Trigger fired at 93.0 / 94.1 / 94.4 mm on the three
# healthy runs -- a 1.4 mm spread.
#
# CONTROL LAW
#   fire the brake when   d_est - S(v) <= TARGET
# Every approach is at the same maximum speed, so sensor lag, loop period,
# braking and slide collapse into one empirical constant S, measured end to end
# on a single sensor channel in char3.
#
# d_est is odometry-propagated from a gated anchor: a new reading is accepted
# only if it BOTH changed AND agrees with dead reckoning within TOL. This is what
# makes the stop immune to the sensor's 80-125 ms stalls.
#
# KNOWN DEFECT (see report section 8): the start-of-run range gate is
# 600 < b0 < 1300, which accepted 892 mm on runs 1 and 2 where healthy runs read
# ~1018. A gate of 950-1100 with a re-read on failure would have caught the
# sensor fault before the rover committed to a bad datum -- worth ~120 mm of
# closeness on 40% of the runs.
#
# NOTE: inline comments below were added for readability when this was written
# into the report; the flashed source was otherwise identical.

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()

BUF = []
BUFMAX = 2000

def lg(n, v):
    if len(BUF) < BUFMAX:
        BUF.append((clock.time(), n, float(v)))

def dump():
    global BUF
    b = BUF
    BUF = []
    for i in range(len(b)):
        e = b[i]
        stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%.2f}\n' % (e[0], e[1], e[2]))

MMPD = 0.489      # mm of travel per motor degree
F0 = -1           # forward polarity, motor on port C
F1 = 1            # forward polarity, motor on port D
TS = 1.0          # heading sign convention
KS = 0.090        # S(v) = KS * v
SMIN = 30.0
SMAX = 60.0
TARGET = 50.0     # desired settled sensor reading
FLOOR = 28.0      # dead-reckoned safety floor
KOFF = 11.0       # sensor face -> frontmost point of rover
SNOM = 57.0       # nominal S, used only for the fallback estimate
KP = 1.8
KD = 0.10
CAP = 16.0        # max steering differential, % duty
TOL = 60.0        # anchor acceptance gate

m0 = None
m1 = None
uB = None


def dmm():
    x = uB.distance()
    if x <= 0:
        return -1.0
    return float(x)


def medB(n):
    vals = []
    for i in range(n):
        x = dmm()
        if x > 0:
            vals.append(x)
        wait(20)
    if not vals:
        return -1.0
    vals.sort()
    return vals[len(vals) // 2]


def enc():
    return (F0 * m0.angle() + F1 * m1.angle()) * 0.5 * MMPD


def vel():
    return (F0 * m0.speed() + F1 * m1.speed()) * 0.5 * MMPD


def hd():
    try:
        return hub.imu.heading()
    except Exception:
        return 0.0


def drive(duty, corr):
    d0 = duty + corr
    d1 = duty - corr
    if d0 > 100: d0 = 100
    if d0 < -100: d0 = -100
    if d1 > 100: d1 = 100
    if d1 < -100: d1 = -100
    m0.dc(F0 * d0)
    m1.dc(F1 * d1)


def drive_max(corr):
    # hold the faster wheel at 100% and trim the other, so steering
    # never costs approach speed
    if corr > CAP: corr = CAP
    if corr < -CAP: corr = -CAP
    if corr >= 0:
        d0 = 100.0
        d1 = 100.0 - 2.0 * corr
    else:
        d0 = 100.0 + 2.0 * corr
        d1 = 100.0
    m0.dc(F0 * d0)
    m1.dc(F1 * d1)


def halt():
    m0.brake()
    m1.brake()


def main():
    global m0, m1, uB
    wait(700)
    try:
        hub.imu.reset_heading(0)
    except Exception:
        pass
    try:
        m0 = Motor(Port.C)
        m1 = Motor(Port.D)
        uB = UltrasonicSensor(Port.B)   # ONLY this sensor: avoids crosstalk
    except Exception:
        lg("ABORT_ports", 1)
        return
    try:
        m0.reset_angle(0)
        m1.reset_angle(0)
    except Exception:
        pass

    b0 = medB(9)
    lg("B_startline", b0)
    if b0 < 600 or b0 > 1300:
        lg("ABORT_range", b0)
        return

    # creep test: confirm we are pointed at the wall before going to full speed
    e0 = enc()
    drive(30, 0)
    wait(300)
    halt()
    wait(500)
    b1 = medB(7)
    moved = enc() - e0
    lg("creep_dB", b1 - b0)
    lg("creep_enc", moved)
    if not (b1 > 0 and (b0 - b1) > 8 and moved > 8):
        lg("ABORT_creep", 1)
        return

    e_start = enc()
    d_start = medB(7)
    lg("op_B_start", d_start)
    anchor_d = d_start
    anchor_e = e_start
    last_raw = d_start
    maxmm = d_start - FLOOR
    t0 = clock.time()
    tl1 = 0
    tl2 = 0
    vf = 0.0
    n_loop = 0
    n_fresh = 0
    fired = 0
    reason = 0
    d_fire = 0.0
    raw_fire = 0.0
    e_fire = 0.0
    v_fire = 0.0
    stale_mm = 0.0
    hp = hd()
    tp = t0
    while True:
        t = clock.time()
        if t - t0 > 6000:
            reason = 3
            break
        raw = dmm()
        ee = enc()
        d_est = anchor_d - (ee - anchor_e)
        n_loop += 1
        # re-anchor only on a reading that both changed and agrees with odometry
        if raw > 0 and raw != last_raw and abs(raw - d_est) < TOL:
            anchor_d = raw
            anchor_e = ee
            last_raw = raw
            d_est = raw
            n_fresh += 1
        v = vel()
        vf = 0.7 * vf + 0.3 * v
        per = 60
        if d_est < 700:
            per = 20
        if t - tl1 >= per:
            if raw > 0:
                lg("usB", raw)
            lg("enc_mm", ee - e_start)
            lg("est_mm", d_est)
            tl1 = t
        h = hd()
        if t - tl2 >= 100:
            lg("head_deg", h)
            tl2 = t
        if (ee - e_start) > maxmm:
            reason = 2
            break
        if d_est <= FLOOR:
            reason = 1
            break
        s = KS * vf
        if s < SMIN: s = SMIN
        if s > SMAX: s = SMAX
        if d_est - s <= TARGET:
            fired = 1
            d_fire = d_est
            raw_fire = last_raw
            e_fire = ee
            v_fire = vf
            stale_mm = ee - anchor_e
            break
        dt = t - tp
        hdot = 0.0
        if dt >= 25:
            hdot = (h - hp) * 1000.0 / dt
            hp = h
            tp = t
        drive_max(-(KP * h + KD * hdot) * TS)
        wait(4)
    halt()
    t_stop = clock.time()
    if not fired:
        d_fire = anchor_d - (enc() - anchor_e)
        raw_fire = last_raw
        e_fire = enc()
        v_fire = vf
        stale_mm = enc() - anchor_e
    while clock.time() - t_stop < 900:
        r = dmm()
        if r > 0:
            lg("usB", r)
        lg("enc_mm", enc() - e_start)
        wait(40)
    e_rest = enc()

    vals = []
    for i in range(15):
        x = dmm()
        if x > 0:
            vals.append(x)
        wait(20)
    nv = len(vals)
    if nv > 0:
        vals.sort()
        b_rest = vals[nv // 2]
    else:
        b_rest = -1.0

    lg("op_fired", fired)
    lg("op_reason", reason)
    lg("op_B_fire_est", d_fire)
    lg("op_B_fire_raw", raw_fire)
    lg("op_stale_mm", stale_mm)
    lg("op_v_fire", v_fire)
    lg("op_B_rest", b_rest)
    lg("op_n_valid", nv)
    lg("op_enc_after", e_rest - e_fire)
    lg("op_head_end", hd())
    lg("op_freshfrac", 100.0 * n_fresh / n_loop)
    tot = e_rest - e_start
    if tot > 200:
        lg("op_enc_total", tot)

    fb = d_fire - SNOM - KOFF
    lg("op_gap_fallback", fb)
    if b_rest > 0 and b_rest < d_fire + 20:
        lg("op_S_true", d_fire - b_rest)
        lg("op_gap_est", b_rest - KOFF)
    else:
        lg("op_S_true", -1.0)
        lg("op_gap_est", fb)
    dump()


try:
    main()
except Exception as ex:
    lg("EXC", 1)
finally:
    try:
        m0.stop()
        m1.stop()
    except Exception:
        pass
    dump()
    stdout.write('{"event":"end"}\n')
