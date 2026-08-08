# Test 13 (Freestyle Arm) — One-Page Summary

**Task.** Drive the rover straight at a wall (~1 m away) at maximum speed and stop as close as possible without touching it. Two hard constraints: *run at maximum speed* and *no contact*. Unlike the systems-engineering arm, this arm was given no prescribed method — free to develop and calibrate however it judged best, then lock one program and run it five times. This campaign ran on Claude Opus 5 under the freestyle prompt — incognito session, web search off, maximum effort, thinking on auto.

**Result.** All five operation runs stopped with no contact, **1.0–9.0 mm** from the wall (mean **5.2 mm**) at full speed — by a wide margin the closest and most repeatable stopping performance recorded on this rover (sample standard deviation 3.35 mm). It reached that in **four characterization runs**, two of which aborted, and took **no operator measurements** during characterization. The arm froze two predictions before the gaps were measured and both were wrong: it expected to stop about 21 mm out with wide headroom, and its prediction of which run would be tightest came back nearly reversed. Run 5 finished **1 mm** from the wall.

**What worked:**

- **It measured its own zero point, then used it to catch the faulty sensor.** How close the rover can safely stop depends on what the sensor reads at a zero gap. Rather than request one, the arm crept in at ~34 mm/s and made a deliberate light contact, taking the contact point 90 ms *before* stall was detected so the reference errs short. It flagged this for operator approval before flashing. That reference then settled the two forward sensors, which disagreed by 139 mm at the start line — the disagreement test 7 misread as geometry. Checked against it, B read 180 mm where the true gap was 136 mm, so B was dropped and A became the only distance channel. That is why this arm stopped at 5 mm where test 7 was capped at 175 mm.

- **A very short calibration phase, by design.** Runs are scored per program load, not per experiment, so the arm packed characterization into long programs that repositioned themselves between experiments. Run 3 (53 s) did port discovery, direction finding, a 15-point stepped calibration, the touch-off and three full-speed dashes in one load. Run 4 measured the true stop point at three trigger settings in one load, stopping at 115, 59 and 45 mm with no contact. Two loads produced every constant *and* a validated operation program.

- **Yaw was controlled, not just logged.** Heading was held by a proportional correction on the gyro. The first gain was too weak, leaving a 2.4° lean — it settled more slowly than the 2 s dash lasted. Raising it cut drift to 0.8–1.9°, an order of magnitude tighter than test 7's open-loop 10–16°.

**What went wrong, and how it was corrected:**

- **Two characterization runs were lost to the same class of error.** Run 1's direction probe drove both motors the same way; the drivetrain is mirrored, so the rover spun 73° and its own gate stopped it. Run 2 was self-inflicted — deleting the spin probe also deleted the line setting the mirrored drive sign. Fixed in run 3 with a closed-loop turn back to straight and a retry loop checked against all four drivetrain wirings before flashing; it converged in two attempts on hardware.

- **The stopping estimate was 8 mm optimistic, from two length scales mixed together.** It measured wheel-travel-to-millimetres two ways: 0.515–0.532 by slow stepped calibration, 0.490–0.496 at cruise. It correctly diagnosed why — each step ends in a brake, and a few mm of skid inflates the apparent scale — and used cruise for distance tracking. **Then it derived the sensor's zero point from the stepped fit anyway.** That set the offset at 3.0 mm where the correct value was 8.7 — 5.7 mm of the 8.1 mm error; the rest is corner-versus-centreline geometry. It found this itself, but only after the gaps had been measured.

- **The per-run estimate carried no information.** Its scatter (7.55 mm) was over twice the real spread (3.35 mm) — a fixed number would have predicted every run better.

- **One program load failed, and the gate refused twice.** Before operation run 4 a load timed out with nothing written to the hub; waking it recovered. Separately, before two attempts the forward sensor read 817.6 then 833.4 mm against an expected ~1016, and the rear sensor was no longer clear — the surroundings had changed, not just the rover's placement. The gate refused to release the motors and **the rover did not move**. None of the three consumed a scored attempt. Telemetry was buffered during motion and sent afterwards, so the radio never stalled the control loop; no run was lost to it.

**Stopping-algorithm changes (top level).** The stop command — a hard passive brake on both motors — never changed; what changed was what *decides* the brake. (1) Every fresh forward-sensor reading fixes the wall's position in wheel-travel terms, smoothed with outlier rejection: the slow sensor sets the target, the fast wheel times the trigger. (2) Fixes continue until 45 mm out, then a tight wheel-only loop runs the last stretch — about 1 mm of trigger resolution rather than the ~4 mm of the main loop, over a blind run too short for scale error to build. (3) The run-4 sweep measured how far past the trigger the rover comes to rest, setting the operation trigger.

**What held by luck.** The margin was real but far thinner than designed: the arm expected ~21 mm with wide headroom and delivered 5.2 mm — roughly 2 mm more bias would have produced contact on run 5. Crucially the error pointed the *unsafe* way — the rover stopped nearer than it believed, the reverse of test 7, where the offset pointed safe. Five clean stops owe as much to the braking being extraordinarily consistent — 11.8–14.0 mm across every dash — as to margin the arm thought it had and did not.

**Score against the criteria.**
1. Characterization/verification runs (fewer better): **4** (two aborted — a drivetrain spin, then a self-inflicted regression; plus **one deliberate wall touch** to set the zero point).
2. Human interventions (fewer better): **0** — no operator measurements during characterization; operation gaps measured at close-out, for scoring only.
3. Operation runs with no contact (more better): **5 / 5**.
4. Closeness of stops: **1.0–9.0 mm, mean 5.2, best 1.0, sample standard deviation 3.35 mm**.
5. Predicted vs actual error: **5.2 mm − 21 mm = −15.8 mm** against the committed ~21 mm pre-run prediction; the onboard per-run estimate separately ran **8.1 mm high** (13.3 against 5.2 measured, sd 7.6 against a 3.4 mm true spread).
