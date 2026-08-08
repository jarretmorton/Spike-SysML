# CALIBRATION PLAN — Wall-Approach Rover — **v5**
**Document:** `19_calibration_plan_v5.md` · **Type: PLAN** (revised and re-issued)
**Supersedes:** v4 · **Trigger:** AR-04 resolved by operator observation (775 mm)

---

## 0. RESOLUTION OF AR-04

**The rover was 775 mm from the wall — it moved TOWARD it.** Branch (b).

| claim | verdict |
|---|---|
| direction probe | **CORRECT.** `probe_ddist` = +42 → flip → the rover approached. The logic has now worked in three consecutive runs |
| odometry | **CORRECT.** 427 deg ≈ 209 mm against ~209 mm of actual travel |
| forward ranger, in motion | **FAILED.** Reported ~1100 mm while the true distance was 775 mm — an error of **+325 mm** — with intermittent no-target returns |
| wrong-way guard | fired on that false data and **aborted a run that was otherwise proceeding correctly** |

The abort was not a rover fault. It was a guard consuming a channel that had already been
shown untrustworthy in motion (AR-03), which I left wired into the abort path.

### 0.1 The detuning decision prevented a contact

Two operator measurements at widely separated positions now pin the drivetrain **without
using the ranger at all**:

```
RUN-3:  G = 178 + 1646.5·k        RUN-4:  G = 775 + 427.0·k
     ⇒  k = 0.4895 mm/deg,  start distance G = 984.0 mm
```

RUN-4 flew `k` = 0.5030 — a **+2.7% error, 2.7× the CMP-4 limit**. At the 46 mm design point
that is **26 mm of position error against a 24 mm predicted gap: contact.** RUN-4 was
deliberately detuned to a 100 mm trigger because `n_S_samples` was 1. That decision, made on
uncertainty grounds rather than on any suspicion of `k`, is the reason this run ended 775 mm
from the wall instead of against it.

### 0.2 The deeper finding: `b` is range-dependent

| where | true distance | ranger offset |
|---|---:|---:|
| M1, close pose | 178 mm | **−119.1 mm** |
| start line, RUN-3 | 984.0 mm | −97.0 mm |
| start line, RUN-4 | 984.0 mm | −83.2 mm |

The offset is not a constant. My v4 analysis tested constant-offset against scale-error and
concluded "constant" — but that test used M1 at one end and the ranger at the other with
odometry between, so it could only detect what the odometry error allowed. With a second
ground-truth point the constancy assumption fails.

**This matters because REV D moved the ranger's job.** M1 validated `b` at 178 mm, which was
the right operating point when the ranger was going to *measure the final gap*. Under REV D
the ranger instead supplies the **anchor at ~900 mm**. The offset is needed at *that* range.
This is the source-of-truth rule — validate at the operating point — applied to a parameter
whose operating point moved when the architecture changed, and I did not re-validate it.

### 0.3 What cannot be decomposed onboard

RUN-3 and RUN-4 read `R0` = 887.08 and 900.83: a **13.8 mm difference**. That is either
start-line scatter or ranger static instability, and no onboard channel separates them. It
matters because a 13.8 mm start-line scatter also shifts the joint `k` fit by 2.3%.

---

## 1. ARCHITECTURE REV E — ranger out of every in-motion path

| role | REV D | **REV E** |
|---|---|---|
| trigger | odometric | odometric (unchanged) |
| anchor | ranger static reading | ranger static reading (unchanged) |
| wrong-way guard | **ranger** | **retired** — replaced by forward-axis IMU acceleration sign |
| one-sided cross-check | ranger in motion | **retired** — the channel is not trustworthy in motion |
| direction probe | ranger delta | ranger delta **plus IMU acceleration sign**, must agree |
| anchor quality gate | none | **12 samples, zero invalid, spread < 20 mm, else abort** |

The ranger now has exactly one job: a **static, motors-off reading before the run starts**.
Every in-motion consumer is gone. RUN-4's rest dwell (302 mm spread, 10 invalid) would have
failed the new quality gate.

**Requirement deltas:** FUN-3's wrong-way operand moves from the ranger to the IMU; SYS-7's
degraded path rests on the IMU direction witness and the time limit; new **CMP-16** — *the
static anchor dwell shall have zero invalid samples and a spread below 20 mm, or the run
shall not proceed*.

**Restoring what I should not have cut.** Forward-axis IMU acceleration was removed in REV C
to save telemetry lines. That cut is what left AR-04 unresolvable onboard and cost a
measurement to settle. It comes back — as four scalars, not a trace.

---

## 2. THE DECISION I NEED FROM YOU

The anchor needs the ranger's static offset **at ~900 mm**, and I do not have it. Two paths:

### Option A — spend one measurement (my recommendation)

Reset the rover to the start line and tell me **the distance from the front of the rover to
the wall at that placement**. Paired with that same run's `R0` reading, it gives the
long-range offset directly. It also re-solves `k` against RUN-3's chain, so — as with M1 —
**one number binds two parameters**.

- anchor uncertainty: ~14 mm → **~4 mm**
- achievable gap: ~45 mm → **~25 mm**
- cost: a third operator measurement

### Option B — spend nothing, target a wider gap

Use the offset inferred from the joint fit (≈ −90 mm) and carry the full 14 mm of
unresolved anchor uncertainty in the margin. Target roughly **45 mm** instead of 25 mm.

- cost: nothing
- gives up roughly 20 mm of closeness, and carries a thinner contact margin against an
  uncertainty I know I have not decomposed

### How I weigh it

Three of the four scores are runs, measurements, and closeness plus no-contact. I have spent
**four runs and two measurements**, so a third measurement is a real cost and I am not
reaching for it lightly. But the anchor is now the single load-bearing quantity in the
design, `k` was just shown to have been 2.7% wrong on a flashed run, and Option B asks me to
fly the scored sequence on an uncertainty I have explicitly declined to resolve. Given that
contact voids a run outright, I would rather pay once than carry that.

**I recommend Option A, and I will proceed with Option B without complaint if you prefer it.**
Either way I will re-issue this plan with the chosen path before flashing anything.

---

## 3. STANDING TALLY

| | consumed |
|---|---:|
| characterization runs | **4** |
| operator measurements | **2** |

Bound at T3 and independent of the ranger: `k` = 0.4895 mm/deg, `G` = 984.0 mm.
Bound and still good: loop period 9.4 ms, motor regulation and 1.0% symmetry, heading hold
(2.5° peak), passive-brake stop `S` ≈ 14 mm, crosstalk confirmed and ranger A dropped.
Still open: the long-range anchor offset, `S` repeatability (n = 1), and start-line scatter.
