# ANOMALY REPORT AR-01 — CAL-1 (run-20260729-195903)

**Type:** report (static; free analysis) · **Raised:** after characterization run 1 of 1 ·
**Operator actions consumed:** 0 · **Program runs consumed:** 1

---

## 1. What happened

CAL-1 completed all eight phases without contact and without damage. The rover ended ~600 mm
from the wall, yawed ~20°. It bound two parameters well, one provisionally, and **failed to bind
the three that matter most**, because the rover does not drive in a straight line: it drives along
a ~1961 mm arc, and by the end of a full approach the forward ranger no longer sees the wall.

## 2. The anomalies, and which branch each falls in

| # | Observation | Bound violated | Branch |
|---|---|---|---|
| **A1** | `r_rest_1` = 1851 mm > `r_static_1` = 1042 mm, after 262 mm of *forward* travel | a rest reading farther than the trigger reading | **IMPOSSIBLE** → unconditional escalation |
| **A2** | `o_consistency_1` = +1030 mm | \|Δ\| ≤ 15 mm (plan §2.4) | **IMPOSSIBLE** → unconditional escalation |
| **A3** | Port B rose 787 → 880 mm while the rover closed 124 mm on the wall (staircase A step 0→1) | forward range must not increase while approaching | **IMPOSSIBLE** → unconditional escalation |
| **A4** | Systematic arc: −2.92°/100 mm at cruise, −3.04°/100 mm at creep speed | SYS-4 (≤5° over the approach) | possible, but it is the **root cause** of A1–A3 |
| **A5** | A further −8.3° of apparent yaw across the brake transient, with the rover stationary after ~13 mm | none absolutely; 5.9°/s of gyro drift is implausible | possible, **not separable** with CAL-1's channels |
| **A6** | Approach 2 aborted at t = +1 ms; ranger classification inconclusive (`flags` = 64) | — | **program defects**, not physics |

## 3. Diagnosis

**A1–A3 have one cause.** The two drive motors were both commanded `run(10000)`, i.e. each to
*its own* ceiling. Their ceilings differ: `theta_l` = 519° against `theta_r` = 552° over the same
pass, a **6.2 % mismatch**. With the measured `k_eff` = 0.4858 mm/deg and a 121 mm track that is
exactly the observed −2.92°/100 mm, so the arc is fully explained with no residual:

| Quantity | Value |
|---|---|
| Wheel-rotation mismatch | 6.2 % (872 vs 928 deg/s) |
| Arc radius | 1961 mm |
| Yaw over a full 850 mm approach | **25°** |
| Lateral offset over that approach | **181 mm** |

An ultrasonic ranger against a flat wall is specular: past roughly 10–15° off-normal the echo
returns away from the transducer. At 25° there is no echo, which is precisely what the trace
shows — clean tracking for 590 ms and 163 mm, then a jump to 1022 mm, then 2000 mm (no-echo).
A1, A2 and A3 are therefore not sensor faults; they are the geometric consequence of the arc, and
they falsify the load-bearing assumption behind the whole ranging chain: *that the rover points at
the wall*.

**A6 are two coding defects the run exposed.** (i) Ranger classification used a 2-vs-1 *sign*
majority; the rear ranger faces an open room, saturates at 2000 mm and so has zero delta, landing
in neither sign bucket — the test gave up and fell back to port order (which happened to be
correct). (ii) The no-echo value 2000 was fed straight into the range-offset estimator, so the
o-drift guard added at GATE A tripped on its first sample and killed approach 2 at t = +1 ms. The
guard was right to fire on an 87 mm jump; it was wrong to be shown one.

**A5 is the one genuinely open question.** −8.3° in 1.4 s while stationary is either real
asymmetric braking or an IMU artifact from the 0.76 g stop. CAL-1 logged **no heading and no
per-motor angles inside the brake transient**, so the two cannot be separated. This matters
because it is now the largest term in the error budget:

| Budget | σ_RSS | m_contact = 3σ |
|---|---|---|
| With A5 excluded | 3.47 mm | **10.4 mm** |
| With A5 real (8.3° corner swing = 8.7 mm) | 9.33 mm | **28.0 mm** |

Resolving A5 is worth roughly 18 mm of final gap — more than every other open parameter combined.

## 4. What CAL-1 did establish

| Parameter | Value | Tier | Basis |
|---|---|---|---|
| `k_eff` | **0.4858 mm/deg** | T4-onboard-multi | 6-point regression over 620 mm, slope −0.9935, residuals ±6.3 mm → 55.7 mm wheel |
| `omega_cruise` | 900 deg/s (437 mm/s) | T4-onboard-multi | ~250 ms plateau |
| `t_refresh` | **21.8 ms** | T4-onboard-multi | 37 fresh samples in 808 ms |
| `q_range` | **2 mm** | T4-onboard-multi | min nonzero step between fresh samples |
| `psi_brake` | 12.9 mm at cruise | T3-onboard-single | θ 509.5 → 536.0°; **one event, no cross-check** |
| `a_brake` | 7425 mm/s² (0.76 g) | T3-onboard-single | back-solved |

The ranger is markedly better than assumed (2 mm quantisation, not 10; 22 ms refresh, not 50) and
the brake is far stronger (12.9 mm of stopping travel, not 70). Both make the objective *easier*
than the GATE A projection — if the rover can be made to drive straight.

**Still unbound:** `l_sensor` (the dynamic-vs-static comparison needs a clean approach),
`sigma_psi` (needs ≥2 brake events), `b_offset` (needs M1, and the rover never reached the
operating range), `r_min_valid` (staircase B ran on invalid data), `psi_head`.

## 5. A requirements-level consequence

SYS-1 currently reads "command both drive motors at no less than the drivetrain's maximum
achievable speed". CAL-1 shows that requirement, read literally, **contradicts SYS-4**: commanding
each motor to its own ceiling guarantees a 6.2 % differential and therefore an arc. Running the
faster wheel harder does not add forward speed, it adds rotation. The defensible reading is
*maximum straight-line speed* — both wheels at a common regulated speed just below the slower
ceiling (860 deg/s, 418 mm/s, 4.6 % below the CAL-1 average). This needs an amendment to the
requirements specification, which is the source of truth; it is flagged here rather than made
silently.

## 6. RECOMMENDATION

**RETEST — one further characterization run (CAL-2), no operator measurement yet.**

Not "ignore": three impossible readings and the objective's dominant parameter is unbound.
Not "escalate to a higher-tier source": ground truth cannot fix a rover that arcs away from the
wall, and spending M1 now would anchor `b_offset` at a pose the operation will never revisit. The
escalation the rules demand is satisfied in the two ways that actually address a falsified
assumption — **fix the assumption** (drive straight) and **add the missing independent channel**
(heading and per-motor angles inside the brake transient, which is what separates A5).

### Proposed CAL-2, for review

Same file, same hot loop, twelve traceable changes — every one caused by an observation above:

| Change | Caused by |
|---|---|
| Common regulated cruise `OMEGA_RUN` = 860 deg/s for both wheels | A4 root cause |
| IMU heading-hold, subtractive trim, `KP_TRIM` = 1.0 %/deg **derived** from the measured arc response | A4 residual |
| Reject `r ≥ 1900` as no-echo everywhere: estimator, o-drift guard, creep floor, reverse target | A1, A2, A6(ii) |
| Classify rangers by **saturation at the start line**, not sign majority | A6(i) |
| Heading + per-motor angles logged **inside** the brake transient | **A5 — the point of the run** |
| o-drift guard: valid samples only, 80 mm, 3 consecutive | A6(ii) |
| Backstop 250 → 450 mm (psi is now measured, so a longer cruise is safe) | binds `l_sensor` |
| Staircase A 5×120 → 3×140 mm (k_eff already T4) | pays for the above |
| Tighter two-pass yaw-null, both values reported | 3.67° residual |
| Creep aborts on no-echo instead of stepping blind | staircase B stepped 181 mm blind |

Safety of CAL-2 by the exact closed form, with `psi_brake` now measured rather than a prior: a
450 mm backstop lands at ~480 mm of clearance even at 4× the measured stopping travel.

**M1 is still requested after CAL-2**, at the fine-staircase pose — unchanged in purpose, but now
reachable, because the rover will be pointing at the wall.
