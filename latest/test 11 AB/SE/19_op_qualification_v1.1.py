#!/usr/bin/env python3
# qualify_op.py - OP-WAR v1.0 qualification against the AS-BUILT plant model.
# Plant2 extends the R-CAL mock with everything run 2 taught us:
# per-sensor update intervals, motor-command application lag (the 41 ms
# onset), B low-glitch injection at speed, A dropout bursts, as-built
# parameter ranges centered on the Gate B bindings, BLE 0.3-2.5 kB/s.
import sys
import json
import random
import mockbricks


class Plant2(mockbricks.Plant):
    def __init__(self, seed, scen=None):
        scen = scen or {}
        super().__init__(seed, scen)
        r = self.r
        # as-built ranges (Gate B bindings +/- residuals)
        self.k = scen.get('k', r.uniform(0.55, 0.72))
        c0 = r.uniform(900, 1010)
        mm = scen.get('ceil_mismatch', r.uniform(-0.07, 0.07))
        self.ceils = [c0, c0 * (1.0 + mm)]
        self.ceil = (self.ceils[0] + self.ceils[1]) / 2.0
        self.a_brake = r.uniform(5500.0, 12000.0)
        self.a_run_slew = r.uniform(900.0, 2600.0)
        self.o = list(scen.get('o', (r.uniform(40.0, 90.0),
                                     r.uniform(-60.0, -30.0))))
        self.tau = r.uniform(3.0, 18.0)
        self.Us = [r.uniform(26.0, 40.0), r.uniform(16.0, 26.0), 60.0]
        self.snext = [r.uniform(0, self.Us[j]) for j in range(3)]
        self.noise = r.uniform(0.5, 2.5)
        self.drift_deg_per_m = r.uniform(-1.5, 1.5)
        self.skidyaw = r.uniform(2.0, 30.0) * (1 if r.random() < 0.5 else -1)
        self.yaw_max = 0.0
        self.yaw_at_brake = None
        self.gap0 = scen.get('gap0', r.uniform(900.0, 1100.0))
        self.gap = self.gap0
        self.hist = [self.gap] * 300
        self.min_gap = self.gap
        self.cmd_lag = r.uniform(28.0, 55.0)      # ms, mode-change latency
        self.pend = []                            # (t_apply, idx, mode, tgt)
        self.glitch_p = scen.get('glitch_p', r.uniform(0.0, 0.05))
        self.a_drop_p = scen.get('a_drop_p', r.uniform(0.0, 0.05))
        self.a_drop_left = 0
        self.b_dead_below = scen.get('b_dead_below', -1)  # reading floor fault
        self.half_track = r.uniform(60.0, 100.0)    # mm; AR-003: R-VER yaw-rate pins ~70
        self.ble = scen.get('ble', r.uniform(0.3, 2.5))   # bytes per ms

    # command latency: queue mode changes
    def cmd(self, idx, mode, tgt=0.0):
        self.pend.append((self.t + self.cmd_lag, idx, mode, tgt))

    def step(self, ms):
        self.frac += ms
        while self.frac >= 1.0:
            self.frac -= 1.0
            for p in list(self.pend):
                if self.t >= p[0]:
                    self.mode[p[1]] = p[2]
                    self.tgt[p[1]] = p[3]
                    self.pend.remove(p)
            dt = 0.001
            for i in (0, 1):
                m = self.mode[i]
                if m == 'run':
                    d = self.tgt[i] - self.w[i]
                    mx = self.a_run_slew * dt
                    if d > mx:
                        d = mx
                    if d < -mx:
                        d = -mx
                    self.w[i] += d
                else:
                    if m == 'hold':
                        dec = (self.a_brake / self.k) * dt
                    elif m == 'brake':
                        dec = (0.6 * self.a_brake / self.k) * dt
                    else:
                        dec = (250.0 / self.k) * dt
                    if self.w[i] > dec:
                        self.w[i] -= dec
                    elif self.w[i] < -dec:
                        self.w[i] += dec
                    else:
                        self.w[i] = 0.0
                self.ang[i] += self.w[i] * dt
            v = self.vfwd()
            self.acc = 0.05 * ((v - self.lastv) / dt) + 0.95 * self.acc
            self.lastv = v
            self.gap -= v * dt
            self.yaw += ((self.sg[0] * self.w[0] - self.sg[1] * self.w[1])
                         * self.k * dt / (2.0 * self.half_track)) * 57.2958
            self.yaw += self.drift_deg_per_m * (v * dt / 1000.0)
            if (self.mode[0] == 'hold' and self.mode[1] == 'hold'
                    and (abs(self.w[0]) + abs(self.w[1])) > 100):
                self.yaw += self.skidyaw * dt
            ya = self.yaw if self.yaw >= 0 else -self.yaw
            if ya > self.yaw_max:
                self.yaw_max = ya
            if self.yaw_at_brake is None and self.mode[0] == 'hold' and abs(self.w[0]) > 200:
                self.yaw_at_brake = self.yaw
            if self.gap < self.min_gap:
                self.min_gap = self.gap
            if self.gap <= 0.0 and not self.contact:
                self.contact = True
                self.gap = 0.0
                self.w = [0.0, 0.0]
            self.t += 1.0
            self.hist.append(self.gap)
            if len(self.hist) > 300:
                self.hist.pop(0)
            for j in range(3):
                if self.t >= self.snext[j]:
                    self.snext[j] = self.t + self.Us[j]
                    if abs(self.yaw) > self.yaw_lose:
                        self.sv[j] = 2000
                        continue
                    if j == 2:
                        val = 2000.0
                    else:
                        idx = len(self.hist) - 1 - int(self.tau)
                        if idx < 0:
                            idx = 0
                        g = self.hist[idx]
                        if g < self.rmin:
                            if self.floor_mode == 'garbage':
                                val = self.r.uniform(25, 1900)
                            elif self.floor_mode == 'high':
                                val = 2000
                            else:
                                val = self.rmin + self.r.gauss(0, 3 * self.noise)
                        else:
                            val = g + self.o[j] + self.r.gauss(0, self.noise)
                        moving = abs(self.w[0]) > 200 or abs(self.w[1]) > 200
                        if j == 1:
                            if self.b_dead_below > 0 and val < self.b_dead_below:
                                val = 2000
                            elif moving and self.r.random() < self.glitch_p:
                                val -= self.r.uniform(60, 180)
                        if j == 0:
                            if self.a_drop_left > 0:
                                self.a_drop_left -= 1
                                val = 2000
                            elif moving and self.r.random() < self.a_drop_p:
                                self.a_drop_left = self.r.randint(1, 3)
                                val = 2000
                        if self.r.random() < self.noecho_p:
                            val = 2000
                    iv = int(round(val))
                    if iv < 20:
                        iv = 20
                    if iv > 2000:
                        iv = 2000
                    self.sv[j] = iv


def install2(plant):
    mods = mockbricks.install(plant)
    pup = mods['pybricks.pupdevices']
    OldMotor = pup.Motor

    class Motor2(OldMotor):
        def run(self, sp):
            c = plant.ceils[self.mi]
            if sp > c:
                sp = c
            if sp < -c:
                sp = -c
            plant.cmd(self.mi, 'run', float(sp))

        def hold(self):
            plant.cmd(self.mi, 'hold')

        def stop(self):
            plant.cmd(self.mi, 'coast')

    pup.Motor = Motor2

    class Out2:
        def write(self, s):
            moving = any(plant.mode[i] == 'run' and abs(plant.w[i]) > 20
                         for i in (0, 1))
            plant.writes.append((plant.t, moving))
            plant.out.append(s)
            plant.step(len(s) / plant.ble)
    mods['usys'].stdout = Out2()
    return mods


SRC = open('/home/claude/op_v11.py').read()
CODE = compile(SRC, 'op_v1.py', 'exec')
ASBUILT_MAP = ['U', 'U', 'M', 'M', 'U', 'C']


def run_one(seed, scen):
    scen = dict(scen)
    scen.setdefault('devmap', list(ASBUILT_MAP))
    scen.setdefault('signs', (-1, 1))
    plant = Plant2(seed, scen)
    # AS-BUILT identity is a calibrated physical fact: map ports to plant
    # devices in scan order of the scenario devmap (identity for as-built).
    dm = scen['devmap']
    us = [i for i, c in enumerate(dm) if c == 'U']
    mo = [i for i, c in enumerate(dm) if c == 'M']
    plant.port_sensor = {p: i for i, p in enumerate(us)}
    plant.port_motor = {p: i for i, p in enumerate(mo)}
    mods = install2(plant)
    saved = {k: sys.modules.get(k) for k in mods}
    sys.modules.update(mods)
    err = None
    try:
        exec(CODE, {'__name__': 'op'})
    except BaseException as e:
        err = repr(e)
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
    text = ''.join(plant.out)
    recs = {}
    sentinel = False
    for ln in text.split('\n'):
        ln = ln.strip()
        if not ln:
            continue
        try:
            o = json.loads(ln)
        except ValueError:
            recs.setdefault('_badline', []).append(1)
            continue
        if o.get('event') == 'end':
            sentinel = True
        elif 'sensor' in o:
            recs.setdefault(o['sensor'], []).append(o['value'])
    return plant, recs, sentinel, err


def check(plant, recs, sentinel, err, expect):
    fails = []
    if plant.contact:
        fails.append('CONTACT min=%.1f' % plant.min_gap)
    if not sentinel:
        fails.append('NO-SENTINEL')
    if any(mv for _, mv in plant.writes):
        fails.append('HOT-WRITES')
    if err:
        fails.append('TOPLEVEL:' + err)
    if expect == 'ok':
        if recs.get('run.ok', [0])[-1:] != [1.0]:
            fails.append('no run.ok')
        g = plant.gap
        if not (2.0 <= g <= 100.0):
            fails.append('final gap %.1f' % g)
        if plant.yaw_at_brake is not None and abs(plant.yaw_at_brake) > 3.5:
            fails.append('yaw at brake %.1f' % plant.yaw_at_brake)
        if plant.yaw_max > 10.0:
            fails.append('yaw max %.1f' % plant.yaw_max)
        dm = recs.get('dh_max_x10', [None])[-1]
        if dm is None:
            fails.append('no dh_max note')
        cf = recs.get('est.c_final', [-1])[-1]
        if cf <= 0:
            fails.append('no estimate')
        elif abs(cf - g) > 46.0:
            fails.append('est err %.1f (cf=%.0f g=%.1f)' % (cf - g, cf, g))
        if recs.get('op.dump_ms', [1e9])[-1] > 26000:
            fails.append('dump %.0f' % recs['op.dump_ms'][-1])
        if recs.get('hold_s', [0])[-1] < 2.0:
            fails.append('hold %.1f s' % recs.get('hold_s', [0])[-1])
    elif expect == 'abort':
        if recs.get('run.abort', [0])[-1:] != [1.0]:
            fails.append('no abort flag')
    return fails


def main():
    scens = [('nom-%03d' % s, s, {}, 'ok') for s in range(1, 201)]
    scens += [
        ('b-dead-below-150', 9001, {'b_dead_below': 150.0}, 'ok'),
        ('b-dead-below-260', 9002, {'b_dead_below': 260.0}, 'ok'),
        ('glitch-storm', 9003, {'glitch_p': 0.14}, 'ok'),
        ('a-dead', 9004, {'a_drop_p': 0.9}, 'ok'),
        ('slow-ble', 9005, {'ble': 0.30}, 'ok'),
        ('floor-garbage', 9006,
         {'floor': 'garbage', 'force': {'rmin': 80.0}}, 'ok'),
        ('census-wrong', 9007,
         {'devmap': ['U', 'M', 'M', 'U', 'U', 'C']}, 'abort'),
        ('short-start', 9008, {'gap0': 902.0}, 'ok'),
        ('long-start', 9009, {'gap0': 1098.0}, 'ok'),
        ('fast-heavy-drift', 9010,
         {'force': {'drift_deg_per_m': -4.5, 'k': 0.72}}, 'ok'),
    ]
    npass = nfail = 0
    softn = []
    gaps = []
    esterr = []
    rows = []
    for name, seed, scen, expect in scens:
        plant, recs, sentinel, err = run_one(seed, scen)
        fails = check(plant, recs, sentinel, err, expect)
        hard = [f for f in fails if f.startswith(('CONTACT','NO-SENTINEL','HOT','TOPLEVEL','no abort','no run.ok','no estimate','no dh_max','yaw'))]
        soft = [f for f in fails if f not in hard]
        if not hard and expect == 'ok':
            gaps.append(plant.gap)
            cf = recs.get('est.c_final', [-1])[-1]
            if cf > 0:
                esterr.append(cf - plant.gap)
            if soft:
                softn.append((name, soft))
        if hard:
            nfail += 1
            rows.append((name, hard + soft, plant))
        else:
            npass += 1
    print('OP QUALIFICATION: %d PASS / %d HARD-FAIL of %d | soft-tail breaches: %d (budget <=4)'
          % (npass, nfail, len(scens), len(softn)))
    for nm, sf in softn[:6]:
        print('  soft %-14s %s' % (nm, '; '.join(sf)))
    if gaps:
        gaps.sort()
        print('final gap: min %.1f  p10 %.1f  med %.1f  p90 %.1f  max %.1f mm'
              % (gaps[0], gaps[len(gaps)//10], gaps[len(gaps)//2],
                 gaps[9*len(gaps)//10], gaps[-1]))
    if esterr:
        esterr.sort()
        print('onboard estimate error: med %.1f  |p95| %.1f mm'
              % (esterr[len(esterr)//2],
                 max(abs(esterr[len(esterr)//20]), abs(esterr[19*len(esterr)//20]))))
    for name, fails, plant in rows[:10]:
        print('FAIL %-18s k=%.2f v=%.0f a=%.0f o=(%.0f,%.0f) tau=%.0f gl=%.2f '
              '-> min=%.1f gap=%.1f | %s'
              % (name, plant.k, plant.ceil * plant.k, plant.a_brake,
                 plant.o[0], plant.o[1], plant.tau, plant.glitch_p,
                 plant.min_gap, plant.gap, '; '.join(fails)))
    return 0 if (nfail == 0 and len(softn) <= 4) else 1


if __name__ == '__main__':
    sys.exit(main())
