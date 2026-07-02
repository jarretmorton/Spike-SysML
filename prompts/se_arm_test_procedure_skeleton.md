# SE Arm Test Procedure (method v2) — SKELETON

**Purpose.** A repeatable operator procedure for running an SE-arm test under isolation. Two jobs:
(1) keep the run consistent (common prompt language, fixed apparatus); (2) enforce that the arm
**follows the procedure** — completeness/structural checks only, never steering the engineering.
The operator adds no information and makes no design choices; every gate decision is
**continue or stop**.

**Design note on the checks.** They are binary and reference the arm's *own* outputs
("every requirement ID has a verdict — Y/N"; "every parameter your sensitivity analysis flagged
high-leverage was validated against the top available source — Y/N"). That is process-enforcement,
not steering. Honest limit: a pure completeness checklist would have *passed* test 6, because it was
internally consistent while wrong — which is exactly why the impossible-reading escalation is an
unconditional rule in the prompt, not a checklist line.

---

## 1. Fixed apparatus (unchanged across all attempts)

- Model + configuration: `[fill: model, thinking on / moderate effort]`. Same as freestyle arm.
- Isolation: incognito, outside the active project; only `spike-prime-mcp` connected as a tool.
  **Web search OFF for BOTH arms** — the controlled isolation condition the capability ladder depends
  on (no run can retrieve the web's or another tier's answer). (The arm's in-session code execution —
  for telemetry analysis, charts, and the executable analysis model — is available to both arms and is
  not an added tool.)
- Hub power-cycled between **every** run (characterization and operation).
- Rover squared at the start line, ~1000 mm out; operator holds this constant.
- Scored outcomes recorded **externally**; never trust the arm's self-report.
- Transcript captured at the **end** of the session (incognito does not persist — capture before
  closing); artifacts gathered to the repo **as you go**.

---

## 2. Common prompt language (paste verbatim)

- SE arm delivered prompt = `task_core.md` fenced block **+** `se_arm_prompt.md` fenced block,
  ending at `Begin.` Full text, never a link.
- Freestyle arm delivered prompt = `task_core.md` **+** `freestyle_arm_prompt.md`. (Unchanged from
  v1 — freestyle is not re-run.)
- **Run kickoff (every run):** after the two fenced blocks, the operator's opening message is exactly
  **"Please read and execute these instructions."** — identical every run. Record the **run start
  time** when you send it (§7 timing).
- **Default advance = "continue":** the standard operator response to advance past a gate, to accept
  moving forward with the arm's recommendation, or to force the arm to pick among options it has
  presented. It carries no information and makes no design choice — it is the non-steering advance
  signal. Use it (not a substantive reply) wherever the checklists below say *continue*.

---

## 3. What costs and what does not (operator reference)

- **Unscored / unlimited:** analysis, simulation, model evaluation, document revision.
- **Counted — only when the rover is touched:** (a) a program flash-and-run (program-count score);
  (b) an operator measurement/observation (outside-input score).
- Record each costed action in the **external tracker** as it happens.

---

## 4. Per-gate operator checklists (binary)

Each gate: run the checks; if all pass, advance with **"continue"** (§2); if any check fails, act on
the **Fail** line. The operator supplies no content beyond "continue" — the checks reference the
arm's own outputs.

### GATE A — after spec + SysML model + executable model + Calibration Plan, before any flash
- [ ] All three Gate-A artifacts present: requirements spec (+ TBD register + tree), `.sysml` model,
      executable analysis model.
- [ ] Calibration Plan opens with the **sensitivity analysis** (parameters ranked; assumed ranges
      stated).
- [ ] Every effector either traces to a requirement or is explicitly dropped (absence by
      traceability).
- [ ] Characterization run design present (channel catalog, source-of-truth hierarchy,
      test-like-you-fly).
- **Fail → return to the arm with the gap; do not supply the answer.**

### GATE B — after Calibration Report + Verification Plan, before the verification run
- [ ] Calibration Report closes **every** CMP (unit) requirement with evidence and tier.
- [ ] Verification Plan's frozen prediction is the **executable model's output** at the committed
      configuration, with the roll-up result shown, and is frozen (no post-run editing).
- [ ] **Model-evaluation check passed** (§5).
- **Fail → return to the arm; if the model check fails, the arm re-derives and reissues.**

### GATE C — after the verification run + Verification Report, before the 5 scored runs
- [ ] Verification Report closes **every** requirement (STK / SYS / FUN / CMP) with method +
      evidence + verdict. Any ID without a verdict → **incomplete → reissue.**
- [ ] The **objective**'s verdict rests on operating-point ground-truth validation of its predicted
      gap — gathered wherever in characterization the arm judged best, distinct from the five
      operation close-out measurements, and completed before the scored runs.
- [ ] If the verification run **falsified** the frozen prediction: confirm the arm issued a NEW
      Verification Plan version and a NEW verification run + report — **not** an edit of the frozen
      plan and **not** a "reconcile-and-proceed" past a real falsification. *(This is the test-6
      rule: a failed Verification Report means the plan → run → report cycle is redone.)*
- **Fail → redo the verification cycle; do not proceed to scored runs.**

### OPERATION close-out — after all 5 scored runs
- [ ] Arm froze its per-run onboard estimates **before** receiving any measurement.
- [ ] Operator then supplied the 5 true gaps; Final Report carries predicted → estimated → measured
      + delta, and states plainly whether the Gate-C prediction held.

---

## 5. Model-evaluation check (EXPLICIT — the part to get right)

Goal: confirm the pre-run predictive argument actually evaluates to the numbers the arm claims —
first cheaply and always, then (recommended) with an independent tool that reads the real `.sysml`.

### Tier 1 — MANDATORY: run the executable analysis model (free, always available)
1. Take the executable model the arm delivered (the Python module) and the bound parameter values
   listed in the Verification Plan.
2. Run its **predict** and **satisfy/require evaluation** paths at that committed configuration.
3. Confirm the outputs match the frozen prediction in the Verification Plan **number for number**
   (predicted gap, margins, and each requirement's pass/fail).
4. If they do not match, the arm's prose and its model disagree → **reissue** (arithmetic or
   transcription error). Do not proceed.

*What Tier 1 catches:* an error between the written prediction and the model. *What it does not
catch:* an error shared by both the Python model and the `.sysml` (a common-mode modeling mistake) —
because the Python was written by the same arm. Tier 2 breaks that circularity.

### Tier 2 — validity check with the free Syside VS Code Editor (what you have)
The free Editor does **not** evaluate requirement satisfaction (true/false roll-up) — that lives in
Syside Automator/Cloud, which we do not have. But it does validate the model's **form**, and that is
a real, distinct check worth running: it certifies the formal argument is well-built even though it
cannot tell you the argument evaluates true.

1. Open the delivered `.sysml` in VS Code with the Syside Editor extension.
2. Confirm it validates clean — no unresolved references, no type/unit mismatches, no malformed
   constructs. This covers the "structural checks grammar cannot see" the SE prompt already asks for
   (every requirement reachable from the top need, decomposition edges matching the requirement tree,
   per-package import resolution).
3. Any validation error = a malformed formal model → **reissue** (independent of the numbers).

*This is free and unscored; nothing here touches the rover.*

### Residual risk to log (no independent satisfaction check available)
Tier 1 (Python) evaluates satisfaction; Tier 2 (free Editor) evaluates form. Neither is an
*independent* satisfaction check, because the Python roll-up was written by the same arm as the
`.sysml`. So a modeling error **common to both** the `.sysml` and the Python model — the same wrong
relation in both — would pass unnoticed. Record this as an accepted limitation of the current
tooling. Closing it later would require an evaluating Syside surface (Automator or Cloud) to
re-evaluate the `.sysml` roll-up independently and confirm it agrees with the Python. Until then, the
impossible-reading escalation rule in the prompt is the backstop against a wrong model reaching the
scored runs.

---

## 6. Anomaly gate (as-needed, any time after testing starts)

When the arm issues an **Anomaly Report**:
1. Read its branch classification (surprising-but-possible vs model-contradicting/impossible) and its
   recommendation (ignore / retest / escalate).
2. If it recommends a chase, review the proposed test/measurement plan.
3. Decide **continue or stop only**: **"continue"** to approve the proposed test (now costed) or to
   accept the arm's recommendation; decline to stop. Do not redesign it, do not add information.
4. Record any approved flash or measurement in the **external tracker** as it happens.
- During operation, a valid Anomaly Report recommendation is **halt**, never modify-and-continue.

---

## 7. End-of-session capture & logging

**Operator requests (after the Final Report):**
- **Surface artifacts:** ask the arm to present all code and plots from the session as downloadable
  artifacts, if not already provided — e.g. *"Please surface all code and plots from this session as
  downloadable artifacts, if not already provided."*
- **Retrospective:** ask using the standard wording — *"Please do a retrospective and let me know what
  additional systems engineering guidance would have helped you in this task. Don't ask for answers,
  just improved process."*

**Capture:**
- Transcript captured at the **end** of the session, before closing incognito. Artifacts gathered to
  the repo **as you go**.

**Record in the external tracker (per run):**
- Contact (Y/N), true gap per run, program-run count, outside-input count, any Anomaly Report +
  disposition.
- **Active time:** start time (noted at kickoff, §2) → end time at session finish, minus any pause
  time.
- **Transcript word count** — total words in the transcript, as a proxy for tokens.
- Fold the run into the campaign summary (the roll-up spreadsheet).

---

## Open items to fill before first use
- The fixed model/config string (§1). Operator utterances are now fixed in §2 (kickoff + "continue").
- The anomaly disagreement threshold (mirror whatever we set in the prompt — see edit-plan open
  micro-decision #1).
- Syside is the free VS Code Editor only → Tier-1 (Python) satisfaction check + Tier-2 (Editor)
  validity check; independent satisfaction cross-check unavailable, residual common-mode risk logged
  (§5).
