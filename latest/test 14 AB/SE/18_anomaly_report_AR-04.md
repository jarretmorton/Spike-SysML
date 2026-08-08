# ANOMALY REPORT AR-04 — RUN-4 aborted; direction and ranger cannot both be right
**Document:** `18_anomaly_report_AR-04.md` · **Type: REPORT** (static)
**Raised:** after RUN-4 (`run-20260805-214915`) · **Branch:** physically impossible → escalate

---

## 1. What happened

The wrong-way guard fired at 404 motor degrees — 215 mm of travel, roughly 800 mm short of
the wall. **No contact.** This is the third time a guard has stopped a run before damage.

| channel | value |
|---|---:|
| `R0_b` (static, 12 samples, spread 11 mm) | 900.83 mm |
| `R0_true` = `R0_b − b` | 1019.96 mm |
| `trigger_reason` | **4 — wrong-way guard** |
| `odo_rest_deg` | 427 deg → 215 mm of travel |
| `r_rest_b` | 996.67 mm, **spread 302 mm**, 10 invalid samples |
| `k_static` | **−0.224 mm/deg** — negative, impossible |
| `heading_max` | 1.66° — heading hold fine |
| `rng_jump_max_mm` | **146 mm** in a single step |
| `rng_hold_max / mean` | 83 ms / 24 ms |

Buffered trace (time, reported range, odometry):

```
3520   899   0        3772   856    86       4024   884   279
4220     0 426        4342  1096   427       4462     0   427       4582  1104  427
```

`0` is the invalid-sample placeholder. The reading falls 43 mm, rises 28 mm, drops out,
then flickers between ~1100 mm and no-target.

---

## 2. The contradiction

Odometry says the rover travelled **215 mm in the commanded direction**. The ranger ends at
**~1100 mm**, having started at **~900 mm** — 200 mm *further away*.

Two readings of the same data, and they demand opposite fixes:

| | prediction for the final reading | observed ~1096–1104 |
|---|---:|---|
| **(a) rover drove backwards** — direction probe wrong | 1020 + 215 = 1235 mm true → **1116 mm** reported | matches within 15 mm |
| **(b) rover drove forwards, ranger faulty** | 1020 − 215 = 805 mm true → **686 mm** reported | off by 418 mm |

On final-value grounds (a) is far better supported. But three things cut the other way:

- The flip logic is **identical to RUN-3**, where `probe_ddist` = +33 produced a flip and the
  rover verifiably approached — confirmed independently by M1, which measured 178 mm after
  ~820 mm of travel toward the wall.
- The **first** trace step falls 43 mm, which is what approaching looks like. Though the
  ~400 ms ranger lag can produce exactly that: the reading is still catching up *downward*
  from the probe's undo motion while the rover has already set off in the other direction.
- The rest dwell has a **302 mm spread with 10 invalid samples**, so the ranger is
  demonstrably misbehaving in this run regardless. Its minimum (~802 mm) leans toward (a);
  its maximum (~1104 mm) toward (b).

**Odometry cannot break the tie.** `dth` is computed as `0.5·(sgnL·aL + sgnR·aR)`, so its sign
is *slaved to the same `sgnL`/`sgnR` decision under test. It reports "moved in the commanded
direction" and is silent on whether that direction faces the wall. The forward IMU axis
would be independent, but RUN-4 does not log it — accelerometer logging was cut when the
telemetry budget was tightened in REV C. **That cut is what leaves this ambiguous**, and it
is my error: I removed a cross-source channel to save lines and lost the one signal that
would have arbitrated here.

Per the source-of-truth rule this is a disagreement to escalate, not to arbitrate. Choosing
(a) means rewriting the direction probe; choosing (b) means the forward ranger is failing
and the anchor for the whole REV D architecture is unsound. Guessing wrong costs at least
one more run and possibly sends the design in the wrong direction entirely.

---

## 3. RECOMMENDATION — escalate to external ground truth, one number

**Ask the operator for the rover's current distance from the wall.** It is decisive:

| observed now | verdict | consequence |
|---|---|---|
| **≈ 800 mm** | rover moved **toward** the wall → **branch (b)**: the ranger is failing intermittently | the static anchor is unsound; REV D needs a different anchor, or the ranger needs replacing |
| **≈ 1230 mm** | rover moved **away** → **branch (a)**: the direction probe is defective | rewrite the probe to use an independent channel; ranger behaviour is "merely" laggy as already characterised |

### Why spend a measurement rather than a run

Both are scored, so this is a real trade and I want to be explicit about it. A re-run would
cost one run and might not resolve anything — if the ranger flakes again the same ambiguity
returns, and I would have spent a run to learn nothing. The operator observation resolves it
with certainty, and it additionally quantifies the ranger's error at a known true distance,
which a re-run would not.

I am also not asking for it as a diagnostic convenience. **It is load-bearing for the
architecture**: branch (b) invalidates the static anchor that REV D's entire trigger rests
on, and I should not fly another run on an anchor I have reason to doubt.

### Regardless of branch, RUN-5 will restore what should not have been cut

- **Forward-axis IMU acceleration logged again**, as the independent direction witness. Four
  scalars, not a trace: sign of mean forward acceleration during the probe and during the
  first 300 ms of the hot path.
- **Direction probe hardened**: confirm with two independent channels (ranger delta *and*
  IMU acceleration sign) and abort if they disagree, rather than trusting the ranger alone.
- **Anchor validated before use**: require the 12-sample static dwell to have spread below a
  threshold and zero invalid samples before the run is allowed to proceed; abort otherwise.
  RUN-4's rest dwell would have failed such a check.

---

## 4. Standing tally

Four characterization runs, one measurement. RUN-4 bound nothing — its only products are
this contradiction and a further confirmation that the guard architecture is sound. The
wrong-way guard has now caught a full-speed spin (RUN-1) and this abort, both without
contact.
