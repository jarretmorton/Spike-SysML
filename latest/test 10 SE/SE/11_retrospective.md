# Retrospective — Wall-Approach Rover
## What additional systems-engineering guidance would have helped

**Document type:** Retrospective (process improvement) · **Scope:** the gated V&V effort that
produced a 5/5 no-contact, 35.6 mm-mean result in 6 characterization/verification runs + 5
operation runs.

---

## The through-line

My process was rigorous going *forward* — requirements → SysML → executable model → gated
verification → lock — but thin on **characterizing the ground I was standing on before building on
it**. Almost every wasted run traces to trusting a component I had never actually validated: a
sensor, the actuator's operating envelope, or the telemetry link. Guidance that forces that
validation up front would have roughly halved the run count and eliminated the most dangerous
failure (stops that looked like 50 mm but were really 166 mm).

The improvements below are ordered by leverage.

---

## 1. Ground-truth the primary measurement channel *before* closing any loop on it; separate accuracy from precision

The plan validated the objective against ground truth only **at the operating point, at the very
end**. That was too late. The `us1` sensor was perfectly *repeatable* and completely *wrong* — it
read 116 mm short — and I spent three runs optimizing against it before the single operator
measurement exposed it.

- **Repeatability tells you nothing about whether a channel measures the quantity you care about.**
  Precision and accuracy are different axes; the plan conflated them.
- A coarse check at the very start (rover at a known standoff, record what *every* channel reads,
  compare to the tape) costs almost nothing and catches a gross offset in the first minute.
- **Guidance:** require every objective-bearing channel to be tied to an external reference
  *before* it is trusted for control — not after the design is built around it.

## 2. Do an observability analysis at the outset

I spent real analysis cycles trying to separate **brake skid vs sensor bias vs ultrasonic lag** —
three effects that are fundamentally indistinguishable from onboard sensors alone.

- **Guidance:** for each unknown, ask up front "what combination of sensors makes this
  observable?" Unknowns that are external-truth-only should be flagged as such immediately, rather
  than chased with more runs.

## 3. Treat the actuator envelope as a first-class calibration item; model the plant's nonlinearities

I modeled the stopping kinematics but not **motor saturation** or **left/right asymmetry**. As a
result "command maximum speed" silently produced a 20° veer, and my first steering fix did
*literally nothing* because it operated in the saturated region where extra command has no effect.

- **Guidance:** characterize max speed, the saturation point, dead-band, and drivetrain asymmetry
  *before* designing any controller, and represent the plant as a **saturating, asymmetric** system
  rather than a linear one. Both the problem and the fix (back off to ~97% so a wheel can be slowed
  to steer) then appear immediately instead of over two runs.

## 4. Treat the instrumentation pipeline as a budgeted interface (like mass or power)

I over-logged against a ~6-line/second telemetry link, blew the timeout, and lost a run's braking
data and its flush sentinel.

- **Guidance:** a single dry run to measure the link's **bandwidth and latency**, plus an explicit
  **telemetry budget** in the plan. Instrumentation is a system component with hard limits, not a
  free observation layer.

## 5. Do a requirements-interaction analysis before the build, not during it

The conflict between **maximum speed** and a **straight approach** is structural — you cannot steer
a saturated differential drive — and it should have appeared in an interaction matrix as a known
tension with a pre-planned trade, rather than being discovered by veering into three runs.

- **Guidance:** build an N² / requirements-interaction matrix and pre-commit the trade (e.g.
  "hold ~97% of max to retain steering authority") at planning time.

## 6. Plan runs for information value; order them by risk

I iterated reactively. Each run was individually justified, but I did not design each to **falsify
the maximum number of assumptions at once**, and I had **no pre-committed decision tree** ("if this
run shows X, do Y").

- **Guidance:** "run the cheapest test that could invalidate the most downstream work first." That
  heuristic puts the sensor ground-truth check and the actuator-envelope check at the very front,
  where they protect everything after them. Pair each planned run with its decision tree.

## 7. Cost the two scarce resources jointly

The plan told me to minimize **operator measurements**, so I hoarded them — and paid in
**characterization runs**, which were equally scarce.

- **Guidance:** a joint cost model where a measurement and a run each carry a price, and you spend
  whichever buys more information. The early ground-truth measurement then becomes an obvious
  purchase instead of something to defer.

---

## What to keep unchanged

The discipline was right; it simply needed to be aimed at the sensors, actuators, and
instrumentation as hard as it was aimed at the requirements and the math. Keep:

- The **gate structure** with frozen, versioned **plans** and static **reports**.
- **Freezing a numeric prediction before each verification run** ("argue before you run").
- **Locking exactly what was verified** for the scored runs (test-like-you-fly).
- **Refusing to feel it out at the wall** — the gated, predict-then-verify approach is what caught
  the wrong drive direction, the 20° veer, and the 116 mm sensor offset before any of them became a
  crash or a confident wrong answer.

---

## One-line summary

Extend the same rigor already applied to requirements and analysis **backward onto the plant and
the instrumentation**: ground-truth every objective-bearing channel first, model the actuator's
saturation and asymmetry, budget the telemetry link, and order runs by how much downstream work
they can invalidate.
