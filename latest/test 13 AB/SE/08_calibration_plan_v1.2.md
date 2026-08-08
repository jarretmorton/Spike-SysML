# CALIBRATION PLAN v1.2 — Wall-Approach Rover

**Type:** plan (forward-looking; revised and re-issued, prior versions retained) ·
**Supersedes:** v1.1 (GATE A, approved) · **Cause of revision:** CAL-1 / AR-01

v1.1 is retained unaltered as the record of what was planned before any hardware ran. This version
changes only what CAL-1 falsified. Section numbering follows v1.1; unchanged sections are named but
not restated.

---

## 0. Sensitivity analysis — what CAL-1 did to the ranking

The GATE A table ranked `psi_brake`, `k_eff`, `b_offset`, `a_brake` and `sigma_psi` at the top. Two
of those are now bound at T4, and the ranking has **changed shape**: the parameters that dominate
the budget now are not the ones the prior-box sweep pointed at, because the priors on the ranger and
the brake were pessimistic and the priors on *straightness* were optimistic.

| Parameter | GATE A prior | CAL-1 result | Tier | Effect on the budget |
|---|---|---|---|---|
| `k_eff` | 0.30 .. 0.85 mm/deg | **0.4858** | T4 | was #2 by leverage; now contributes ~0 |
| `q_range` | 1 .. 20 mm | **2 mm** | T4 | 1.18 → 0.24 mm |
| `t_refresh` | 10 .. 120 ms | **21.8 ms** | T4 | trigger phase no longer material |
| `psi_brake` | 1.8 .. 570 mm | **12.9 mm** | T3 (n=1) | was #1 by leverage; now small but single-sampled |
| `a_brake` | 900 .. 9000 mm/s² | **7425 mm/s²** | T3 | 0.76 g — far stronger than assumed |
| `psi_head` | 0 .. 6° | **25° over a full approach** | T4 | was priority 3; **is now the whole problem** |
| brake-phase yaw | not modelled | −8.3°, unresolved | — | **now the largest single term (8.7 mm)** |

**Current budget** (`wallstop_model.sigma_contributors`, CAL-1 values bound):

| Contributor | σ (mm) |
|---|---|
| ranger latency residual (v·σ_ls) — `l_sensor` still unbound | 2.19 |
| `b_offset` anchor (M1 not yet taken) | 2.00 |
| brake travel run-to-run (physics floor only, n=1) | 1.29 |
| heading / corner geometry (target, not yet demonstrated) | 1.05 |
| trigger timing | 0.66 |
| fused range-offset quantisation | 0.24 |
| **RSS** | **3.47 → m_contact = 10.4 mm** |
| *unresolved brake-phase yaw, if real* | *8.7 → RSS 9.33, m_contact 28.0 mm* |

So the objective is now plausibly a **~11 mm** target rather than the ~23 mm projected at GATE A —
**provided** the arc is fixed and the brake-phase yaw is resolved. Those two are what CAL-2 is for.
Note the model **refuses** to predict the operating point at all while `l_sensor` is unbound; that
refusal, not an assertion of mine, is why a second run is unavoidable.

## 1. Calibration input list — updated register

| Parameter | Status after CAL-1 | Bound by |
|---|---|---|
| `k_eff`, `omega_cruise`, `t_refresh`, `q_range`, `eps_scale`, `d_odo_drift`, `d_agree` | **bound**, T4 | CAL-1 |
| `psi_brake`, `a_brake`, `t_chain`, `a_accel`, `slip_brake` | bound, **T3, n=1** | CAL-1; confirm in CAL-2 |
| `l_sensor`, `sigma_ls` | **UNBOUND** — needs a clean approach with the wall in view | CAL-2/P4+P6 |
| `sigma_psi` | physics floor only (1.29 mm) | CAL-2 (2nd and 3rd brake events) |
| `psi_head`, `d_psi_head` | **falsified** (25°, not ≤5°) | CAL-2 with heading-hold |
| brake-phase yaw (new) | **unresolved**, dominant | CAL-2 brake-transient logging |
| `b_offset`, `sigma_b` | UNBOUND | **M1, after CAL-2** |
| `r_min_valid` | not exercised (staircase B ran on invalid data) | CAL-2/P7 |

## 2. Characterization method — changes

§2.1 channel catalog, §2.2 source-of-truth hierarchy: **unchanged**. Two lessons are recorded
against them rather than changing them:

- **A saturated channel is not a silent channel.** The rear ranger reading 2000 mm carries real
  information (it is not looking at the wall) and the classification logic must read it as evidence,
  not as a missing datum. Generalised: *no-echo is a state, not a distance* — `r ≥ 1900` is now
  rejected at every point in the program where a range is consumed.
- **Cross-sourcing worked exactly as advertised.** Nothing in the run announced "the rover is
  arcing". What surfaced was ranger-vs-odometer disagreement of +1030 mm against a ±15 mm bound.
  The fault-agnostic detector found a fault in neither channel but in a geometric assumption both
  depended on. That is the case B1 exists for.

§2.3 test-like-you-fly: unchanged in principle — one file, `MODE` switch, OP a strict subset. The
hot loop gains the heading-hold, which is therefore present in *both* modes.

§2.4 plausibility bounds: two new flag bits — `256` (no-echo run exceeded `N_BAD_MAX`), `512`
(no-echo while creeping, i.e. the floor guard is blind).

### CAL-2 phase design

| Phase | Change from CAL-1 | Purpose |
|---|---|---|
| P0 | unchanged | statics, IMU axis check |
| P1 | classification by saturation; two-pass tighter yaw-null | fix A6(i), 3.67° residual |
| P2 | staircase A **3 × 140 mm** | confirm `k_eff` linearity; k_eff already T4 |
| P3 | reverse requires a **valid** reading | fix blind reverse |
| P4 | max speed, **common 860 deg/s + heading-hold**, backstop **450 mm**, heading & per-motor angles logged through the brake | **`l_sensor`, brake-yaw, psi #2, SYS-4** |
| P5 | reverse | — |
| P6 | max speed, fused ranging trigger, `G_TARGET` 220 mm | rehearsal, psi #3 → `sigma_psi` |
| P7 | fine staircase, aborts on no-echo | `r_min_valid`, park at r ≈ 130 mm for M1 |
| P8 | unchanged | final statics |

**Safety.** Unchanged in method — the exact closed form of `backstop_worst_case`, not a corner
search. With `psi_brake` now *measured* at 12.9 mm rather than a prior spanning 570 mm, a 450 mm
backstop lands at ~480 mm of clearance even at 4× the measured stopping travel. P6's ranging trigger
now runs on a measured `psi`, not a prior, which is what makes a 220 mm target admissible.

## 3. Outside-input request — unchanged in substance, deferred by one run

Still **one measurement, M1**: the distance from the rover's front-most point to the wall, taken
after CAL-2 at the fine-staircase pose. Unchanged in purpose (it binds `b_offset`, the only
top-ranked parameter with no onboard channel) and unchanged in placement (at rest, at the operating
range). CAL-1 simply never reached that pose. M2, after the verification run, still belongs to
GATE B.

Spending M1 after CAL-1 instead would have anchored `b_offset` at 600 mm and 20° off-normal — a pose
the operation will never revisit, and a bias that would have shipped.

## 4. Verification support — one requirement needs re-derivation

**SYS-1 versus SYS-4 (see AR-01 §5).** "Maximum speed" read as "each motor at its own ceiling" is
not achievable simultaneously with "drive straight" on this vehicle. CAL-2 commands both wheels at
a common 860 deg/s — 418 mm/s, **4.6 % below** the CAL-1 average of 437 mm/s, and the fastest
straight-line speed the drivetrain has. This is a change to the **specification**, which governs,
so it is put to the reviewer explicitly rather than absorbed into the program:

> Proposed SYS-1 amendment: *While in the APPROACH state, the rover shall command both drive wheels
> at a common regulated speed no less than 97 % of the lower of the two motors' measured ceilings.*

If the reviewer prefers the literal reading, the consequence must be accepted: the rover cannot hold
a heading, the ranger loses the wall at ~15° off-normal, and no ranging-triggered stop is possible.

Everything else in §4 (unit verification mapping, roll-up structure, verification order) stands.

## 5. Risks and re-plan triggers — updated

| Risk | Re-plan trigger |
|---|---|
| Heading-hold under-corrects | residual yaw > 3° over P4 → increase `KP_TRIM` by the measured ratio, re-derive, re-issue |
| Heading-hold oscillates | trim saturates at ±8 % or heading sign reverses > 2× → drop to feed-forward trim at the measured 6.2 % |
| Brake-phase yaw proves **real** at ~8° | budget → m_contact ≈ 28 mm; the objective target rises accordingly. Not a failure, a fact to design to |
| Brake-phase yaw proves an **IMU artifact** | exclude from the budget on the odometric evidence; m_contact ≈ 10 mm |
| `psi` in P4/P6 disagrees with CAL-1's 12.9 mm by > 30 % | a T3 value is being contradicted by another T3 value → diagnose, do not average |
| Port B remains erratic | drop it to monitor-only by traceability; CMP-7 verified as "cross-check unavailable", stated not hidden |

## 6. Revision record

| Version | Change | Cause |
|---|---|---|
| v1.0 | initial issue | — |
| v1.1 | backstop 500 → 250 mm; exact closed form replaces corner heuristic; two-stage probe; OP slack backstop; monotone guard; reverse cap; staircase floors | pre-flash verification (all free, before any run) |
| **v1.2** | **this issue** — common regulated cruise + heading-hold; no-echo rejection throughout; classification by saturation; brake-transient heading/odometry logging; backstop 250 → 450 mm; staircase A shortened; tighter yaw-null; SYS-1 amendment proposed | **CAL-1 / AR-01: the rover arcs, the ranger loses the wall, and three impossible readings followed** |

**Scores so far:** 1 characterization run consumed, 0 outside-input actions.
