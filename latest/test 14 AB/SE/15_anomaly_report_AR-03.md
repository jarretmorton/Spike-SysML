# ANOMALY REPORT AR-03 — the ranger cannot track a closing wall
**Document:** `15_anomaly_report_AR-03.md` · **Type: REPORT** (static)
**Raised:** after RUN-3 (`run-20260805-211814`) · **Branch:** model-contradicting → escalate

---

## 1. First: what RUN-3 fixed

All four REV C changes verified on hardware.

| change | evidence | verdict |
|---|---|---|
| ranger A not constructed | `dwell_invalid` = **0** across 44 dwell samples, vs 15% dropouts in RUN-2 | **crosstalk CONFIRMED** — A was the interferer, and removing it cleaned B |
| regulated speed + measured-sign heading hold | heading peak **2.54°** (was 12.58°); `cruise_wL/wR` = 761.8 / 754.0 deg/s | **SYS-6 PASS**, CMP-1/2/3 PASS |
| passive braking | `S_odo` = **+22 deg**, positive; RUN-2's plugging gave −35.5 deg | **slip resolved** |
| telemetry budget | 45 lines, run completed in 11.7 s | **PASS** |

Parameters bound: `k` = **0.4986 mm/deg** (creep) cross-checked at **0.5066** (static endpoints,
1.6% apart — both endpoints lag-free, so odometry is trustworthy); `v_cruise` = **379 mm/s**;
`σ_n` ≈ **2.5–3.1 mm** consistently at 887 / 427 / 59 mm range (**CMP-8 PASS**);
motor symmetry **1.0%** against a 5% limit.

The rover finished at **58.9 mm reading, −0.34° heading** — square, at close range. The pose
M1 has been waiting two runs for.

---

## 2. The anomaly

`R_TRIG` = 600 mm. `d_trigger` = **473 mm**. The threshold was undershot by 127 mm — and
`R_TRIG` had been undershot by 119 mm in RUN-2 as well.

**My AR-02 explanation was wrong.** I attributed it to `min(A,B)` fusion falling back to the
faulty channel. RUN-3 has a single channel and no fusion, and the undershoot is unchanged.
That explanation is withdrawn.

The trace shows the real mechanism. Comparing what the ranger reports against the distance
derived from odometry (`887.08 − odo × 0.4986`):

| t (ms) | odo (deg) | derived true (mm) | reported (mm) | reported is stale by |
|---:|---:|---:|---:|---:|
| 3520 | 0 | 887.1 | 886 | 1 mm |
| 3886 | 172 | 801.3 | 818 | 17 mm |
| 4250 | 455 | 660.2 | 816 | **156 mm** |
| 4614 | 726 | 525.1 | 721 | **196 mm** |
| 4823 | 885.5 | 445.6 | ~473 (trigger) | 27 mm |
| 4890 | 908 | 434.3 | 443 | 9 mm |
| 5221 | 908 | 434.3 | 425 | −9 mm |

**The reported value falls up to 196 mm behind the truth while the rover is closing, then
snaps back within ~10 mm once it stops.** The sensor is accurate at rest and badly behind in
motion — the signature of heavy internal smoothing or a slow effective update, not a fixed
transport delay.

**Consequence: the value 600 was never reported.** The reading jumped from ~721 straight
past the threshold to ~473. The trigger did not fire late because of a timing bug; it fired
on the first value the sensor ever produced below 600, and that value was 127 mm below it.

FUN-2, the inter-sample extrapolator, was designed for exactly this and did not save it. It
extrapolates from the last *changed* reading, and with 2.5 mm of noise the value changes
almost every loop, so `last_t` resets continually and almost no extrapolation accumulates.
**FUN-2 is effectively disabled by sensor noise** — a design defect independent of the
sensor's behaviour.

### Why this is the most important finding so far

If the reported value crosses the threshold in jumps of order 127 mm, the crossing is
quantised by the jump, not by the loop. A uniform 127 mm band gives σ ≈ 127/√12 ≈ **37 mm**,
which forces a required clearance of ~110 mm at k_σ = 3. **The whole objective is set by
this number.** Every other σ in the budget is 2–5 mm.

### Bounding note

This rests on 7 dumped points, sampled every ~33rd buffered loop (~330 ms apart) — I am
looking at a 3 Hz view of the thing I need to characterise. The lag is real and large; its
*shape* is not resolved. I will not fit a sensor model to this.

---

## 3. RECOMMENDATION — invert the channel roles

Do not try to fix the ranger. Use each channel for what it is good at.

| channel | in motion | at rest |
|---|---|---|
| ranger B | lags up to 196 mm, jumps | accurate, σ ≈ 2.5 mm |
| odometry | high rate, no lag, incremental only | needs an anchor |

**Proposal: trigger on the odometric channel, anchored on the static pre-run `R0`.**
`distance_to_go = R0 − odo × k`, where `R0` is a 12-sample static dwell (lag-free, σ ≈ 3 mm)
and `k` is now bound to 1.6%. The ranger becomes the *validator and backstop* — plausibility,
staleness and a cross-check at rest — rather than the trigger.

Error budget for the odometric trigger over the ~450 mm approach: `k` uncertainty 1.6% ≈
7 mm, `R0` ≈ 3 mm, slip ≈ 7 mm (measured: odometry said 11 mm across the stop where the
lag-free endpoints say 18.3 mm) → **≈ 10 mm RSS, against ≈ 37 mm for the ranger trigger.**

It also shortens and stabilises the stop. With the ranger out of the trigger path, `S` loses
its lag term entirely: RUN-3's true post-trigger travel, from lag-free endpoints, is
**18.3 mm** (445.6 → 427.3), against `S_ranger` = 45.7 mm which carried ~28 mm of sensor lag.
Deceleration works out at ≈ 3990 mm/s², physically sensible for passive braking.

This is the hand-off the channel catalog anticipated — "where a channel's valid range is
bounded, plan the hand-off to an independent channel rather than extrapolating the bounded
one past its limit." I catalogued that for the ranger's *close-range floor*. It turns out to
bind on the ranger's *dynamic response* instead.

### Also required

- **FUN-2 must be repaired or retired.** Resetting on value-change makes it a no-op under
  noise. Under an odometric trigger it is unnecessary and should be retired rather than
  patched — the odometric estimate is already continuous and lag-free.
- **RUN-4 must measure the ranger's dynamics properly** — cheaply, as on-hub scalars rather
  than a dense trace: longest hold with an unchanged value, largest single-step jump, and
  number of changes across the approach. Four numbers settle what 7 undersampled points
  cannot, at four telemetry lines.

### Proposed next steps

1. **M1 now**, at the current pose — 58.9 mm reading, −0.34° heading. Requested in chat.
2. **RUN-4**: odometric trigger, ranger as validator, ranger-dynamics scalars, FUN-2 retired.
3. Calibration Plan v4 issued after M1, so `b` is bound before the plan is written.

Requirement impact: SYS-1/FUN-4 re-allocated to the odometric channel; FUN-2 retired;
CMP-4 (odometry scale) is promoted from cross-check to primary and its 2% limit becomes
load-bearing; the ranger retains SYS-8 (final-gap estimate) where it is strongest.
