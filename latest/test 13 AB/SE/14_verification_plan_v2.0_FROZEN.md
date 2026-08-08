# VERIFICATION PLAN v2.0 — FROZEN

**Type:** plan · **PREDICTIONS ONLY** · **Frozen:** before verification run 2
**Supersedes:** v1.0, which stays frozen and unedited as the record of a prediction that was falsified
**Committed configuration:** `13_rover_wallstop_LOCKED_v2.py`, `MODE = "OP"`

---

## 1. Why v1.0 was falsified

| v1.0 criterion | Predicted | VER-1 actual | Verdict |
|---|---|---|---|
| 1 contact | none | none | held |
| 2 clearance 2.8–21.2 mm | 12.0 mm | **31 mm (M2)** | **FALSIFIED** |
| 3 `trigger_src` = 1 | 1 | 1 | held |
| 4 `o_consistency` ±10 mm | 0 ± 5 | +6.57 | held |
| 5 `psi_odo` 12.64 ± 1.3 mm | 12.64 | **12.63** | held |
| 6 stop yaw −8.0° ± 3° | −8.0° | **−0.83°** | **FALSIFIED** |
| 7 `flags` clean | 0 | 0 | held |

Five of seven held, two failed, and criterion 6 caused criterion 2.

**Root cause: a parameter bound in the wrong context.** I derived the operational stop yaw (8.04°)
from CAL-2's approaches — but those ran *after* staircases and reverses that had drifted the heading
to −4° before the approach began. The operation program goes straight from the yaw-null to the
approach and stays square, ending at −0.83°. So `b_offset`'s yaw correction was 7.9 mm of pure error,
in the safe direction. I enforced test-like-you-fly on the control loop and then violated it in the
parameter binding, which is the harder half to see.

**Secondary: the two T5 anchors disagree.** M1 (11.11° yaw) implies `b_perp` = −21.04 mm; M2 (0.83°)
implies −16.13 mm. A 4.9 mm gap between two external measurements is a discrepancy to diagnose, not
average. `w_half` cannot explain it. The likely cause is a **lateral** sensor offset — yawing
translates a laterally mounted ranger by `x_s·sin ψ`, and `x_s ≈ 30 mm` gives 5.8 mm at 11°, the right
magnitude. My yaw model has no such term. It is **recorded, not fitted**: at the operational yaw of
0.8° every yaw term vanishes, so the operation does not depend on getting it right. M2 is therefore
the operational anchor and M1 is demoted to the cross-check that exposed the gap.

## 2. Re-derivation — two constants, both re-bound from data

| Parameter | v1.0 | v2.0 | Basis |
|---|---|---|---|
| `B_OFF` | −29.83 mm | **−17.00 mm** | M2 at the operational pose and yaw: `G − r` = 31 − 48. No yaw model required. **T5** |
| `L_SENSOR` | 66 ms | **50 ms** | VER-1's residual o-bias of +6.57 mm at 417 mm/s. An *effective* staleness — true latency plus odometric drift over the 985 mm operational approach — bound at the operating point, the only place it must be right. **T4** |
| `G_TARGET` | 12.0 mm | **14.0 mm** | forced by the honest budget below |

No arithmetic in the program changed. Three constants, each traced to a measurement.

## 3. Frozen budget

`σ` of the o-bias is now **4.01 mm**, not 2.07: the three available estimates of effective staleness
are 50, 62 and 69 ms, and their spread is real rather than noise, because approach length and phase
history differ between them. Only one of the three (50 ms) was taken in the operational configuration,
so n=1 there and the spread is the honest proxy.

| Contributor | σ (mm) |
|---|---|
| o-bias / effective staleness | **4.01** |
| `b_offset` anchor M2 (no yaw term now) | 1.20 |
| yaw sensitivity of `b` (0.48 mm/deg × 1.5°) | 0.72 |
| trigger timing | 0.63 |
| brake travel (4 samples, sd 0.35) | 0.35 |
| quantisation | 0.24 |
| **RSS** | **4.31** |
| **m_contact = 3σ** | **12.9** |

SYS-5 floor 12.9 mm, OBJ-1 cap 15.5 mm → **`G_TARGET` = 14.0 mm satisfies both**. Unlike v1.0, which
knowingly missed OBJ-1, this configuration is inside every requirement.

## 4. THE FROZEN PREDICTION

| Quantity | Predicted |
|---|---|
| final clearance, front-most point to wall | **14.0 mm** |
| 3σ band | **1.1 – 26.9 mm** |
| reported forward range at rest | **31 mm** — *below the 40 mm vendor floor* |
| stop yaw | **−0.8° ± 1.5°** |
| `trigger_src` | 1 (fused ranging) |
| `psi_odo` | 12.64 ± 1.05 mm |
| `o_consistency` | 0 ± 6 mm |
| cruise speed at brake | 417 mm/s |
| wheel mismatch | < 1% |
| `flags` | 0 |
| contact | none |

**Falsification criteria for v2.0:** contact · measured clearance outside 1.1–26.9 mm ·
`trigger_src` ≠ 1 · `o_consistency` outside ±12 mm · `psi_odo` outside 12.64 ± 1.05 mm ·
stop yaw beyond ±4° of −0.8° · any flag other than 256/512 recovered without effect.

## 5. A predicted requirement failure I am declaring in advance

**CMP-17 will FAIL.** At a 14 mm clearance the reported range at rest is ~31 mm, **below** the 40 mm
vendor validity floor. VER-1 already sat at 48 and 41 mm — at the edge — and v2.0 goes under it. So
the static estimator is predicted to return an invalid or clipped reading, and SYS-7 closes on the
**odometric** estimator alone, which needs no rest reading. Both are still emitted so the close-out
can state which was used and whether the static one degraded as predicted.

This is a real limitation of the sensor, not a defect in the design, and it is the price of a 14 mm
target on a rover whose ranger sits 17 mm behind its bumper. I would rather predict it and be right
than discover it in the scored runs.

## 6. The run

One run of `13_rover_wallstop_LOCKED_v2.py`, bit-for-bit as it will be flashed for all five scored
runs. `timeout_seconds` = 40.

**No further operator measurement is requested.** GATE C's requirement — that the objective be closed
on ground truth at the operating point — is already met by **M2**: taken at the operational pose, yaw
and configuration, and it is the anchor this prediction rests on. VER-2 tests whether the re-derivation
transfers; it does not need its own ruler, and asking for one would spend a third measurement to
confirm arithmetic I can already check onboard. If VER-2's onboard estimate lands outside the frozen
band, that is a falsification and I will say so — the estimator's bias was measured at this exact pose,
so it has no room to hide a systematic the way v1.0's did.
