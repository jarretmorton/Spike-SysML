# VERIFICATION PLAN v1.0 — FROZEN

**Type:** plan · **PREDICTIONS ONLY** · **Frozen:** before the verification run, GATE B
**Committed configuration:** `10_rover_wallstop_LOCKED.py`, `MODE = "OP"`, unchanged hereafter

> This document's entire value is that it is written **before** the run. No integrated result may
> edit it. If the verification run falsifies it, I diagnose the responsible parameter, re-bind,
> re-run the model and issue **v2.0**; this version stays frozen as the record of what was predicted.

---

## 1. The predictive argument

Requirement → model → calibrated parameters → predicted performance → margin.

The stop is commanded by one arithmetic statement in the hot loop, and every term in it is now bound:

```
brake when   s  >=  o_bar + B_OFF - G_TARGET - psi_belief(v)
```

| Symbol | Meaning | Bound value | Tier |
|---|---|---|---|
| `s` | odometric travel, `k_eff * theta` | `k_eff` = 0.4858 mm/deg | T4 |
| `o_bar` | fused range offset `r + s(t − l_sensor)`, mean of 6 fresh samples | `l_sensor` = 66 ms | T4 |
| `B_OFF` | range → front-most-corner offset at the operational stop yaw | −29.83 mm | **T5** |
| `G_TARGET` | commanded clearance | **12.0 mm (frozen)** | design |
| `psi_belief` | post-command travel at `v` | 12.64 mm at 418 mm/s | T4 |

## 2. Frozen uncertainty budget (tenet A6 — RSS, never a guess)

| Contributor | σ (mm) | Where it comes from |
|---|---|---|
| ranger latency residual, `v·σ_ls` | 2.07 | sd of two independent latency estimates (62, 69 ms) |
| `b_offset` anchor | 1.54 | ruler 1.0 ⊕ static read noise 0.5 ⊕ yaw correction via `w_half` 1.06 |
| unmodelled model residual | 1.40 | **measured**: yaw-aware model vs approach 2's out-of-sample stop |
| trigger timing, `v·e_trig` | 0.63 | 1 ms wait granularity |
| brake travel run-to-run | 0.43 | sd of 3 events |
| heading/corner geometry | 0.35 | stop-yaw variation 0.33° |
| fused range-offset quantisation | 0.24 | 2 mm / √(12·6) |
| **RSS** | **3.06** | |
| **m_contact = 3σ** | **9.18** | |

## 3. THE FROZEN PREDICTION

Output of `wallstop_model.predict()` at the committed configuration:

| Quantity | Predicted |
|---|---|
| final clearance, front-most point to wall | **12.0 mm** |
| 3σ lower bound | **+2.8 mm** |
| 3σ upper bound | 21.2 mm |
| clearance at the brake command | 24.6 mm |
| reported forward range at rest | **41.8 mm** (vendor floor 40 mm — marginal) |
| cruise speed at the brake | 418 mm/s (860 deg/s, both wheels) |
| brake travel | 12.6 mm |
| approach duration | ~2.0 s |
| fresh ranger samples during the approach | ≥ 40 |
| trigger source | **1 (fused ranging)** — not the backstop |
| stop yaw | −8.0° ± 0.3° |
| `o_consistency` | **0 ± 5 mm** (was −20 mm before the latency correction) |
| wheel mismatch | < 1% |
| contact | **none** |

**Falsification criteria — any of these breaks this plan and forces v2.0:**

1. Contact.
2. Measured clearance outside **2.8 – 21.2 mm**.
3. `trigger_src` ≠ 1 (a backstop firing means the ranging chain did not).
4. `o_consistency` outside ±10 mm (the latency correction did not take).
5. `psi_odo` outside 12.64 ± 1.3 mm (3σ on n=3).
6. Stop yaw beyond ±3° of −8.0°.
7. `flags` ≠ 0 other than bit 256/512 recovered without effect.

## 4. Predicted requirement roll-up

| Req | Statement | Predicted | Basis |
|---|---|---|---|
| STK-0 | wall-approach need | **PASS** | roll-up of the below |
| SYS-1 | maximum approach speed | **PASS** | 860 deg/s common, both wheels regulated, no reduction anywhere in the loop — *subject to the amendment in §5* |
| SYS-2 | no wall contact | **PASS** | predicted 12.0 mm, 3σ lower bound +2.8 mm |
| SYS-3 | complete stop | **PASS** | 3 prior brake events all reached zero speed and held |
| SYS-4 | straight approach ≤ 5° | **PASS, thin** | stop yaw 8.04° is *absolute* skew, of which ~4° is an initial null residue and ~4° accumulated. **Predicted accumulated deviation ≤ 5°; absolute skew is not** |
| SYS-5 | clearance margin floor | **PASS** | 12.0 ≥ m_contact 9.18 |
| SYS-6 | configuration discovery | **PASS** | correct in both runs |
| SYS-7 | clearance reporting | **PASS on the odometric estimator** | static estimator may read invalid at 41.8 mm; both emitted |
| OBJ-1 | margin efficiency, `g_target ≤ 1.2·m_contact` | **FAIL by 0.99 mm** | 12.0 vs an 11.01 mm cap — **deliberate, see §5** |

## 5. Two things I am declaring rather than burying

**OBJ-1 is knowingly missed by 0.99 mm.** The cap says the target should not exceed 11.01 mm; I froze
12.0. Reason: the two largest σ terms rest on tiny samples — `σ_ls` on n=2 and `σ_psi` on n=3 — so the
budget itself is uncertain, and the scoring asymmetry is severe (contact on any of five runs costs far
more than 1 mm of gap on all five). I am trading a graded objective against a hard constraint and
saying so. If the verification run's `o_consistency` and `psi_odo` land inside their bands, the case
for 10–11 mm in a later revision strengthens — but the operation program does **not** change after
this gate.

**SYS-4 needs the amendment already flagged in AR-01 §5 and Plan v1.2 §4.** The rover holds a *relative*
heading well (accumulated deviation ~4°, wheel mismatch <1%) but starts up to 4° off square because the
yaw-null cannot do better, so absolute skew at the stop is ~8°. Read as absolute squareness, SYS-4 is
violated. Read as deviation accumulated during the approach — which is what the requirement's rationale
is about, and what actually threatens the echo — it passes. The 8° skew is not otherwise harmful because
`b_offset` was anchored by M1 *in the same skewed regime*, so it is absorbed; only the 0.33° run-to-run
variation enters the budget. **I need your ruling on both amendments before the scored runs**, since
GATE C closes these requirements.

## 6. The verification run

One run of `10_rover_wallstop_LOCKED.py`, bit-for-bit as it will be flashed for all five scored runs —
the verification run tests exactly what operates, with no configuration difference at all. Requested
`timeout_seconds` = 40 (approach ~2 s, dump ~15 s).

Then **M2**: the operator-measured gap after that run. That is the second and final outside-input
action of characterization, and it is what closes the objective on ground truth *at the operating point*
per GATE C. Without it the objective would ship on an unvalidated sensor chain — which is precisely how
the 18.6 mm latency bias nearly shipped.
