# VERIFICATION PLAN — v3 · **FROZEN**
**Document:** `25_verification_plan_v3.md` · **Type: PLAN**
**Supersedes:** v2 (retained unedited) · **Trail:** v1 falsified → v2 falsified → v3

---

## 1. v2 WAS FALSIFIED — and the cause was my own re-derivation

Measured gap **43 mm** against a predicted 32.1 mm.

| clause | predicted | measured | verdict |
|---|---|---|---|
| gap within [3.8, 60.4] mm | 32.1 mm | 43.0 mm | holds |
| estimate agrees to within 10 mm | ≤5 mm error | **12.05 mm** | **FAILS — SYS-8** |
| heading ≤ 5° | ≤5° | 2.32° | holds |
| no contact | — | none | holds |

**Same clause as v1.** The gap clause held again and I am again declining that exit.

### 1.1 Diagnosis — I moved the anchor for a bad reason

v2 moved the anchor from 1000 to **990** because RUN-3 and RUN-4, re-scaled on the RUN-5
value of `k`, appeared to have started at ~985 mm. I called that "start-line scatter is real"
and treated it as a measurement. **It was an artifact of my own arithmetic.**

RUN-3 was **45% slow creep**. Creep runs with less wheel slip, so its blended scale is
higher than the fast-approach scale:

| | scale |
|---|---:|
| RUN-3 blended (fast + creep) | 0.4992 mm/deg |
| fast approach only | **0.4907 mm/deg** |
| implied creep phase | 0.5098 mm/deg |

Applying a **fast-only `k` to a creep-heavy run** made RUN-3 look as though it had started
15 mm closer than it did. It hadn't. The start line has been ~1000 mm throughout.

Using the correct fast-profile scale, the two runs that share the **operation profile** —
single fast approach, no creep, no ranger — imply starts of **999.0 and 1001.0 mm**.

> **Start-line scatter is ~2 mm, not the 8.3 mm I "measured" in v2.** I inflated the
> dominant term in my own uncertainty budget by mixing two motion profiles, then hard-coded
> an anchor to match the inflated number. That is how a self-inflicted 12 mm bias got flashed.

### 1.2 What the two clean runs actually show

Fitting only `k` at G = 1000 across both:

| run | odo at rest | predicted gap | measured | residual |
|---|---:|---:|---:|---:|
| RUN-5 | 1930.0 deg | 53.0 mm | 52.0 mm | **+1.0 mm** |
| RUN-6 | 1952.5 deg | 42.0 mm | 43.0 mm | **−1.0 mm** |

**±1 mm across a 10 mm change in commanded stop distance.** And post-trigger travel was
**21.5 deg in both runs, identically** — `S` = 10.55 mm.

---

## 2. RE-DERIVED CONFIGURATION

| item | v2 | **v3** | why |
|---|---|---|---|
| anchor `G` | 990.0 | **1000.0** | the 990 was the artifact of §1.1 |
| `k` | 0.491192 | **0.49066** | fast-profile only, fitted across both operation-profile runs |
| `TRIG_GAP` | 44 mm | **32 mm** | solved from `E[gap] = TRIG − 12.16 ≥ 3σ_g` |

`gap = TRIG − k·(undershoot + 21.5 deg) = TRIG − 12.16 mm`, solved rather than tuned.

---

## 3. FROZEN PREDICTION — v3

| quantity | predicted |
|---|---:|
| **final gap, mean** | **19.8 mm** |
| σ_g | 4.0 mm |
| 3σ interval | **[7.9, 31.7] mm** |
| stop distance `S` | 10.55 mm (21.5 deg) |
| onboard estimate error | ≤ 4 mm |

σ budget: placement 3.0 ⊕ yaw-at-stop 2.0 ⊕ model residual 1.0 ⊕ `k` 1.0 ⊕ undershoot 0.9.

### 3.1 The falsifiable statement

> **The verification run will stop with a measured gap of 19.8 mm, within [7.9, 31.7] mm.
> The onboard estimate will agree with the measured gap to within 10 mm. Heading at the
> trigger will not exceed 5°. There will be no contact.**

### 3.2 Why 32 mm and not 28 mm

TRIG = 28 gives a 15.8 mm gap and a better score. I am not taking it. If the placement ever
returns to anything like 985 mm, TRIG = 28 leaves **0.8 mm** — inside the width of the
measurement itself. TRIG = 32 leaves 4.8 mm in that case and still predicts under 20 mm.
Two of my last two frozen predictions were falsified by a systematic I had not accounted
for; buying 4 mm of closeness against that history is a bad trade.

---

## 4. Pre-committed disposition — unchanged

| outcome | disposition |
|---|---|
| all four clauses hold | GATE C → operation, same program |
| any clause fails | falsified → diagnose → **v4** → re-run |
| contact | falsified; `TRIG_GAP` re-derived upward first |
| `trigger_reason` ≠ 1 | anomaly report, not a verification result |

**On the pattern.** This is the second re-derivation, and both failures were the anchor or
the scale. I am watching for the failure mode where each run simply re-fits the constant that
missed — chasing, not converging. The reason I do not think that is what is happening: v1→v2
changed `k` by 1.6% and the anchor by 10 mm on *contaminated* evidence, whereas v3 rests on
two runs of the **same profile as operation**, which agree to ±1 mm and share an identical
21.5 deg stop. If v3 falsifies, I will not issue a v4 with another re-fitted constant — I
will report that the system is not predictable to the required tolerance and re-open the
requirement instead.

---

## 5. Cost

Seventh run, fifth measurement. The overrun is real and it is mine: v2 spent a run and a
measurement to test an anchor I had derived by mixing motion profiles. The finding was worth
having, but it was available for free in the data I already held.
