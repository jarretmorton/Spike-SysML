# ANOMALY REPORT AR-01 — RUN-1 rotated instead of approaching
**Document:** `09_anomaly_report_AR-01.md` · **Type: REPORT** (static; not edited once written)
**Raised:** after RUN-1 (`run-20260805-204852`) · **Branch:** model-contradicting / physically impossible
**Classification per ANOMALY DISPOSITION: ESCALATE UNCONDITIONALLY**

---

## 1. Anomaly statement

RUN-1 reported a **composite stop distance of −1032 mm**. A negative stop distance is
physically impossible: it asserts the rover ended the run *farther from the wall than the
reading that triggered its stop*. Two further impossible or out-of-bound values accompanied
it:

| channel | value | why it is impossible or out of bound |
|---|---:|---|
| `S_ranger` = `d_T − r_rest` | **−1032.1 mm** | negative stop distance |
| `S_odometry` | **−18.4 mm** | negative travel between trigger and rest |
| `r_rest_fused` | **2000 mm** | rest reading exceeds the 903 mm start reading |
| `heading_at_rest` | **95.2°** | 19× the SYS-6 limit of 5° |
| `R0_pair_offset` | **−107.1 mm** | 3.6× the FUN-13 pair limit of 30 mm |

The impossible-reading rule applies: **an impossible reading is proof a load-bearing
assumption is false.** Asking the sensitivity ranking whether this is worth chasing would
be asking the model to adjudicate its own falsification. It is escalated regardless of
ranking.

**No contact with the wall occurred.** The rover did not reach the wall at any point.

---

## 2. Evidence

Telemetry, RUN-1 hot path (3646 → 3992 ms):

| t (ms) | fused range (mm) | heading (deg) | odometry (deg) |
|---:|---:|---:|---:|
| 3646 | 901 | 0.00 | 0 |
| 3768 | 908 | 5.28 | 15 |
| 3892 | 1014 | 31.50 | 81 |
| 3912 | **2000** | — | — |
| 3992 | 2000 | 66.93 (at 3998) | 161 |
| 4078 | 2000 | 84.32 (at 4058) | 135 |

`trigger_reason = 4` — the **wrong-way guard**, which fires when the rover has travelled
`ARM_DEG` without closing on anything. It fired 348 ms into the hot path, at 155 motor
degrees.

Discovery-phase evidence:

| channel | value |
|---|---|
| `port_kind` (A→F) | 2, 2, 1, 1, 2, 3 → rangers on **A, B, E**; motors on **C, D**; colour on **F** |
| `scan_range` | A 1024.8 · B 908.6 · E 2000.0 |
| `probe1_dheading` | **−23.19°** |
| `probe1_ddist` | **+100.0 mm** |
| resulting `sgn_left`, `sgn_right` | −1, −1 (**same sign**) |
| `yaw_axis_idx`, gravity axis | 2, 2 → hub is flat-mounted; `heading()` is the correct channel |

---

## 3. Root cause

**The relative-motor-polarity test used the wrong discriminator.**

RUN-1 detected "the motors are mirrored, so same-sign commands spin the rover" with:

```
if abs(dh) > 10 and abs(dd) < 10:   sgnR = -1
```

i.e. *large heading change **and** small range change*. The second conjunct is false in
reality. The probe produced `dh = −23.19°` **and** `dd = +100 mm`: the spin changed the
rangefinder reading by 100 mm, because rotating sweeps the beam across — and eventually
off — the flat wall. `abs(dd) < 10` failed, the spin went undetected, and control fell
through to the direction test:

```
if dd > 10:   sgnL = -sgnL;  sgnR = -sgnR
```

which read "+100 mm means we drove backwards" and flipped **both** signs. Flipping both
signs preserves the same-sign relationship, so the rover remained in the spin
configuration — now spinning the other way. Phase B then commanded a full-speed spin.

**The defective assumption:** *that a rotating rover's forward rangefinder reading stays
approximately constant.* It does not. For a flat wall the reading grows as `d/cos θ` and
then saturates at 2000 mm once the beam leaves the wall — visible in the trace as
901 → 1014 → 2000.

The heading channel was never wrong. It reported −23° at the probe and tracked the spin
faithfully to 95°. **The fault was reading the rangefinder to answer a question only the
IMU can answer** — a channel-provenance error (tenet D1), not a sensor failure.

### Why the trace shows a 100 mm step before the beam is lost

The fused channel is `min(A, B)`. At rest B (903) < A (1010), so the fused reading is B's.
At ~3809 ms, after roughly 14° of yaw, **B lost the wall** and the fused channel switched
to A — the 908 → 1003 step. At ~3912 ms, after roughly 35°, **A lost it too** and the
fused reading saturated. The step size, 95–107 mm, equals the pair offset. This is the
fusion rule behaving exactly as designed under a fault; it is not a second defect.

---

## 4. Secondary finding — FUN-13 violated (open)

`R0_a = 1010.5 mm`, `R0_b = 903.4 mm`, measured **before any motion**, from a 12-sample
static dwell each. The **107.1 mm split is real and pre-existing**, not an artifact of the
rotation. It exceeds FUN-13's 30 mm limit by 3.6×.

**FUN-13 verdict: FAIL (test).** Three candidate explanations, not yet distinguishable:

1. B is mounted ~107 mm further forward on the chassis than A.
2. One ranger is angled off-axis and is not measuring perpendicular distance to the wall.
3. One ranger is seeing something other than the wall.

**This matters more than it looks.** Under (1) the fusion rule is *correct* — B is nearer
the wall, so B's reading is the contact-relevant one and `min()` tracks the closest point,
exactly as intended, with the offset absorbed into `b`. Under (2) or (3) the trigger would
be anchored to a channel that does not track the wall, and no amount of calibration would
fix it.

**These are separable from data already planned, at zero extra cost:** during a valid
approach, a ranger that tracks the wall produces a reading linear in odometry with slope
−`k`; one that does not, will not. RUN-1 could not settle it only because it emitted the
fused channel and never the two rangers separately. **That is a logging gap, and it is
fixed in REV B.**

---

## 5. What RUN-1 nonetheless bound, and what was deliberately not spent

A failed run is not a wasted run, but it must not tempt anyone into eyeballing the
parameters it was supposed to measure (A3).

**Bound (T2, with evidence):**

| parameter | value | evidence |
|---|---:|---|
| `t_loop_s` | 10.18 ms | 34 hot-path samples over 346 ms |
| `omega_max_deg_s` | 1000 deg/s | `Motor.control.limits()` ceiling |
| `sigma_n_mm` | 3.68 mm | 12-sample static dwell at ~900 mm (ranger B) |
| `delta_AB_mm` | 107.1 mm | static pre-run dwell |
| `R0_mm` | 903.4 mm | fused static pre-run sample |

**Requirements closable on RUN-1 evidence:**

| req | verdict | evidence |
|---|---|---|
| CMP-11 loop period ≤ 25 ms | **PASS** (test) | 10.18 ms |
| CMP-12 rear ranger | **DROP** (traceability) | read 2000 at start, rest and creep — observes nothing |
| CMP-13 reflectance sensor | **DROP** (traceability) | 40 / 34 / 36 — serves no catalogued quantity |
| FUN-3 implausible-sample / wrong-way guard | **PASS** (test) | fired at 155 deg, prevented a runaway |
| FUN-12 safe termination + sentinel | **PASS** (test) | sentinel emitted on the abort path |
| FUN-13 forward-pair agreement | **FAIL** (test) | 107.1 mm > 30 mm |

**Still unbound, and deliberately so:** `k`, `a_decel`, `tau_sensor`, `t_chain`,
`T_refresh`, `r_floor`, `b_offset`, `u_b`, `theta_dev`, `sym_dev`, `e_odo`. No valid
translation occurred, so none of these has evidence. Model roll-up remains
**INDETERMINATE**.

**M1 was NOT spent.** The rover finished rotated ~490° and reading 2000 mm — not at a
close pose. A measurement there would have bound nothing. The costed measurement is
preserved for a run that reaches the operating point.

---

## 6. What worked

Worth recording, because the same architecture carries the scored runs:

- **The wrong-way guard did its job.** A full-speed spin was stopped 348 ms in, with the
  rover never approaching the wall. Protection did not depend on the ranger being right.
- **`min()` fusion failed safe.** When B lost the wall, the fused reading rose rather than
  falling, which cannot trigger an early stop.
- **The impossible-reading rule surfaced the fault immediately** rather than letting a
  −1032 mm value be averaged into a calibration constant.
- **Emitting scalars before the buffer dump** meant a failed run still yielded a complete
  diagnostic set.

---

## 7. Assessment of the pre-flight simulation

The simulator ran the program successfully and did **not** catch this. The reason is
instructive and is recorded rather than excused: the simulator modelled a rangefinder that
reports geometric distance regardless of heading, so in simulation a spin *did* leave the
reading unchanged — which made the defective condition `abs(dd) < 10` appear to work. **The
simulator shared the flight code's false assumption.**

A simulation can only falsify assumptions it does not itself hold. The correction is not
"trust simulation less" but "make the simulator's physics adversarial to the flight code's
assumptions": beam loss on yaw is now modelled, and the corrected polarity gate has been
negative-tested against a deliberately wrong hard-coded polarity.

---

## 8. RECOMMENDATION

**RETEST** — re-run the calibration with a corrected program (RUN-2, REV B). Not "ignore";
not "escalate to a higher-tier data source", because no operator measurement can substitute
for a valid approach. The cost is one program run.

### Corrections in REV B

| # | change | closes |
|---|---|---|
| A | Device map hard-coded from RUN-1 `port_kind` evidence, then **asserted** at startup | removes discovery risk from every later run |
| B | Relative polarity hard-coded to the **translating** configuration (RUN-1 proved same-sign spins). Only forward-vs-backward is probed, and the probe is **gated on heading**: `abs(dh) > 8° ⇒ abort`. A probe that yaws is not a translation, whatever the rangefinder says | the AR-01 root cause |
| C | New **in-loop gross-yaw guard** (`reason 6`) at 15°. SYS-6's 5° stays a verification criterion, not an in-loop trip, so marginal drift does not abort a good run | would have caught AR-01 ~200 ms earlier |
| D | Both forward rangers logged **separately** through the approach | settles FUN-13 and §4 from data, at no extra run |

### Validation of the fix, before flashing

- Nominal dry run: `trigger_reason = 1` (ranger trigger), no contact, sentinel present,
  78/260 buffer used, 168 telemetry lines, 8.8 s.
- **Negative test** — hard-coded polarity deliberately made wrong: probe measured 48.8° of
  yaw, `polarity_fail` raised, **the hot path was never entered**, no contact, sentinel
  emitted, 2.1 s. The gate fails safe.

### Proposed test/measurement plan (for review — costed only if approved)

1. **RUN-2**: flash and run REV B. No operator input during the run.
2. **M1** immediately afterwards, *only if* the run reaches its close pose: the shortest
   distance from any part of the rover to the wall. Unchanged from Calibration Plan §3.
3. No additional measurement is requested. The FUN-13 question is answered from RUN-2's
   own per-ranger traces, not by asking for a ruler.

### Residual risk accepted for RUN-2

`R_TRIG` stays at the conservative 600 mm — nothing has been learned about `S`, and with
`k` still spanning 0.35–0.80 mm/deg the worst-case prior stop distance is 384 mm. The
odometric backstop remains non-pre-emptive; protection is carried by the staleness guard,
the wrong-way guard, and now the gross-yaw guard.

---

## 9. Requirement impact

- **FUN-13 FAIL** is carried open into the Calibration Report and must be dispositioned
  before GATE B. It cannot be closed by asserting explanation (1) — that would be
  arbitrating between suspect channels, which the source-of-truth rule forbids.
- **SYS-6** is untested: the 95° observed is a fault signature, not a heading-drift
  measurement.
- The **Calibration Plan is revised and re-issued as v2**, per the plan/report discipline:
  a characterization run revealed something its current version did not anticipate.
