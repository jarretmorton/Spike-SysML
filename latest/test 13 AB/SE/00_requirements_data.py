#!/usr/bin/env python3
"""
requirements_data.py -- the AUTHORED requirement records.

The requirements specification is the source of truth for requirements (see
REQUIREMENTS METHOD). This module holds the authored records; the specification
document, the Mermaid tree, and the cross-view structural checks are all
generated from it, so the three views cannot silently disagree.

Fields
  id        STK / SYS / FUN / CMP / OBJ identifier
  sysml     the requirement def name in wall_rover.sysml
  level     STK | SYS | FUN | CMP | OBJ
  ears      Ubiquitous | State-driven | Event-driven | Optional | Unwanted | Objective
  stmt      the requirement text (EARS grammar)
  why       rationale (GtWR: rationale on every requirement)
  parent    parent id (None for the root need)
  derived   True if not literal in the task statement (GtWR rule 4)
  kind      constraint (hard, pass/fail) | objective (graded) | need
  template  RequirementTemplates shape specialised, if any
  method    verification method: test | analysis | inspection (or a combination)
  where     the activity that closes it: CAL-1 | VER | GATE-B analysis | GATE-C | OP
  tbd       TBD ids this requirement contains
  alloc     the element the requirement is allocated to (single effector at CMP)
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Req:
    id: str
    sysml: str
    level: str
    ears: str
    stmt: str
    why: str
    parent: Optional[str]
    derived: bool
    kind: str
    template: Optional[str]
    method: str
    where: str
    tbd: List[str] = field(default_factory=list)
    alloc: str = "WallRover"


REQS: List[Req] = [
    # ---------------- stakeholder level -------------------------------------
    Req("STK-0", "WallRunNeed", "STK", "Ubiquitous",
        "The rover shall perform a wall-approach run that ends in a full stop as "
        "close to the wall as achievable without contact, driving at maximum speed.",
        "The stakeholder need, taken verbatim from the task. It is a compound need "
        "and is therefore not verified directly: it is closed by the roll-up of "
        "STK-1 (the hard constraints) and STK-2 (the objective).",
        None, False, "need", None, "analysis+test", "GATE-C"),
    Req("STK-1", "SafeMaximumSpeedRun", "STK", "Ubiquitous",
        "The rover shall traverse from the start line to a complete stop at maximum "
        "drivetrain speed without contacting the wall.",
        "Separates the pass/fail part of the need from the graded part (GtWR rule 3). "
        "Verified by the conjunction of SYS-1..SYS-7.",
        "STK-0", False, "constraint", None, "test", "GATE-C"),
    Req("STK-2", "ClosestStopObjective", "STK", "Objective",
        "The rover should minimise the clearance between its front-most point and "
        "the wall at the full stop.",
        "The scored objective. Stated with 'should' and graded, never as a pass/fail "
        "constraint (GtWR rule 3); bridged to the hard constraint SYS-2 by the "
        "derived margin requirement SYS-5.",
        "STK-0", False, "objective", None, "analysis+test", "GATE-C"),

    # ---------------- system level ------------------------------------------
    Req("SYS-1", "MaximumApproachSpeed", "SYS", "State-driven",
        "While in the APPROACH state, the rover shall command both drive motors at "
        "a speed no less than the drivetrain's maximum achievable speed.",
        "The task forbids slowing down for safety margin. Stated as a command-side "
        "lower bound so that 'maximum speed' is a construction property of the "
        "program (verifiable by inspection) as well as a measured one.",
        "STK-1", False, "constraint", "LowerBoundRequirement", "inspection+test", "CAL-1"),
    Req("SYS-2", "NoWallContact", "SYS", "Unwanted",
        "The rover shall not contact the wall.",
        "The task's hard constraint. Contact is a pass/fail event, so it is stated "
        "as an Unwanted-behaviour requirement over the clearance channel with a "
        "zero floor, and cross-checked by an independent contact channel (CMP-19).",
        "STK-1", False, "constraint", "LowerBoundRequirement", "test", "GATE-C"),
    Req("SYS-3", "CompleteStop", "SYS", "Event-driven",
        "When the brake command is issued, the rover shall reach zero ground speed.",
        "The task requires a complete stop, not merely a slow-down; a run that "
        "rolls to a halt outside the observed window would not be a stop.",
        "STK-1", False, "constraint", None, "test", "CAL-1"),
    Req("SYS-4", "StraightApproach", "SYS", "Ubiquitous",
        "The rover shall not deviate from its initial heading by more than TBD-12 "
        "degrees during the approach.",
        "DERIVED. The task says drive straight at the wall; quantitatively, heading "
        "deviation converts a centre-line clearance into a smaller corner clearance "
        "and tilts the ranger's line of sight, so it must be bounded, not just "
        "observed.",
        "STK-1", True, "constraint", "UpperBoundRequirement", "test", "CAL-1", ["TBD-12"]),
    Req("SYS-5", "ClearanceMarginFloor", "SYS", "Ubiquitous",
        "The rover's predicted final clearance shall be no less than the derived "
        "no-contact margin m_contact.",
        "DERIVED margin requirement bridging the hard constraint SYS-2 and the "
        "objective STK-2 (GtWR rule 3). m_contact = z_conf * sigma_rss, the RSS of "
        "the independent uncertainty contributors (tenet A6) -- it is computed, "
        "never guessed, and it is what makes 'as close as possible' decidable.",
        "SYS-2", True, "constraint", "LowerBoundRequirement", "analysis", "GATE-B",
        ["TBD-16"]),
    Req("SYS-6", "ConfigurationDiscovery", "SYS", "Event-driven",
        "When the program starts, the rover shall determine the device type on every "
        "port it uses and the drivetrain sign convention before commanding motion.",
        "DERIVED. The task states the port map and direction conventions are unknown "
        "and must be determined; a wrong polarity would drive the rover backwards or "
        "spin it, so this gates all motion.",
        "STK-1", True, "constraint", None, "test", "CAL-1"),
    Req("SYS-7", "ClearanceReporting", "SYS", "Ubiquitous",
        "The rover shall report, for each run, an estimate of its final clearance "
        "with an uncertainty not exceeding TBD-14 millimetres.",
        "DERIVED. The operation close-out requires a per-run onboard estimate frozen "
        "before ground truth is disclosed, and the objective may only be closed on a "
        "channel whose accuracy has been validated -- both need a stated uncertainty.",
        "STK-1", True, "constraint", "UpperBoundRequirement", "test", "GATE-C", ["TBD-14"]),

    # ---------------- function level ----------------------------------------
    Req("FUN-1", "CruiseAtCeiling", "FUN", "Event-driven",
        "When the APPROACH state is entered, the rover shall accelerate to the "
        "commanded ceiling speed and hold it until the brake command.",
        "Allocates SYS-1 to the propulsion function and makes the cruise phase long "
        "enough that the stopping travel is calibrated at the speed it is used at.",
        "SYS-1", False, "constraint", "LowerBoundRequirement", "test", "CAL-1"),
    Req("FUN-2", "ClearanceEstimation", "FUN", "Ubiquitous",
        "The rover shall estimate the clearance from its front-most point to the "
        "wall continuously throughout the approach.",
        "The stop decision needs clearance, not raw range: the two differ by the "
        "ranger's mounting offset and bias, which is a separate calibrated quantity.",
        "SYS-2", False, "constraint", "UpperBoundRequirement", "test", "CAL-1"),
    Req("FUN-3", "StopPointComputation", "FUN", "Ubiquitous",
        "The rover shall compute the brake-command instant at which the predicted "
        "rest clearance equals the commanded target clearance.",
        "Makes the stop criterion an explicit prediction rather than a tuned "
        "threshold, so it can be verified against the model before the run and "
        "transfers unchanged from calibration to operation.",
        "SYS-2", False, "constraint", "LowerBoundRequirement", "analysis+test", "CAL-1"),
    Req("FUN-4", "BrakeActuation", "FUN", "Event-driven",
        "When the brake instant is reached, the rover shall apply maximum braking to "
        "both drive wheels.",
        "Allocates SYS-3 to the actuation function. Passive braking is chosen so the "
        "approach to rest is monotone: the final position equals the closest "
        "position, so the scored gap and the contact risk refer to the same point.",
        "SYS-3", False, "constraint", None, "test", "CAL-1"),
    Req("FUN-5", "FailSafeResponse", "FUN", "Event-driven",
        "When any monitored channel violates its stated plausibility bound, the "
        "rover shall brake immediately.",
        "DERIVED. Graded assurance (tenet A1): contact is the high-consequence "
        "outcome, so the primary range channel must not be single-string. Every "
        "fail-safe path errs toward braking early.",
        "SYS-2", True, "constraint", None, "test", "CAL-1"),
    Req("FUN-6", "HeadingMaintenance", "FUN", "Ubiquitous",
        "The rover shall command both drive wheels at equal speed throughout the "
        "approach.",
        "DERIVED. Equal commanded wheel speed is the open-loop means of meeting "
        "SYS-4 without introducing an uncalibrated steering gain (tenet A3); any "
        "residual veer is measured and carried as an uncertainty contributor.",
        "SYS-4", True, "constraint", None, "test", "CAL-1"),
    Req("FUN-7", "PortAndPolarityIdentification", "FUN", "Event-driven",
        "When the program starts, the rover shall identify the device type on each "
        "port and the motor sign pair that produces forward motion.",
        "Allocates SYS-6. Identification is done from onboard evidence so no "
        "operator input is consumed for it.",
        "SYS-6", True, "constraint", None, "test", "CAL-1"),
    Req("FUN-8", "TelemetryAndEstimate", "FUN", "Ubiquitous",
        "The rover shall report two independent estimates of its final clearance at "
        "each rest position.",
        "DERIVED from SYS-7 and cross-sourcing (GtWR rule 6 / tenet B1): two "
        "independent estimates make a disagreement visible, which is the only way "
        "an estimate error is detectable without spending operator measurements.",
        "SYS-7", True, "constraint", None, "test", "CAL-1"),

    # ---------------- component (single-effector) level ---------------------
    Req("CMP-1", "LeftMotorCeiling", "CMP", "Ubiquitous",
        "The left drive motor shall sustain an angular speed of at least TBD-1 "
        "degrees per second when commanded above its ceiling.",
        "Single-effector leaf of FUN-1: fixes what 'maximum' numerically is for this "
        "motor, and makes a weak or dragging motor visible as a unit failure.",
        "FUN-1", False, "constraint", "LowerBoundRequirement", "test", "CAL-1",
        ["TBD-1"], "MotorLeft"),
    Req("CMP-2", "RightMotorCeiling", "CMP", "Ubiquitous",
        "The right drive motor shall sustain an angular speed of at least TBD-1 "
        "degrees per second when commanded above its ceiling.",
        "Single-effector leaf of FUN-1, mirror of CMP-1. Verified separately so a "
        "one-sided fault cannot hide inside an average.",
        "FUN-1", False, "constraint", "LowerBoundRequirement", "test", "CAL-1",
        ["TBD-1"], "MotorRight"),
    Req("CMP-3", "AccelWithinRunway", "CMP", "Ubiquitous",
        "The drivetrain shall reach its ceiling speed within TBD-2 millimetres of "
        "travel from the start line.",
        "DERIVED feasibility leaf: if the ceiling is not reached before the brake "
        "point, the run is not at maximum speed and the stopping travel is "
        "calibrated at the wrong speed. Instantiates MaxSpeedFromBudget.",
        "FUN-1", True, "constraint", "UpperBoundRequirement", "analysis", "CAL-1",
        ["TBD-2"], "Drivetrain"),
    Req("CMP-4", "PrimaryRangerBias", "CMP", "Ubiquitous",
        "The primary forward ranger shall report the wall range with a fixed offset "
        "of TBD-3 millimetres relative to the rover's front-most point over the "
        "interval 40 mm to 1000 mm.",
        "Single-effector leaf of FUN-2 and the highest-leverage unobservable: no "
        "onboard channel can see where the bumper is relative to the sensor datum, "
        "so this TBD is bound by the one costed operator measurement.",
        "FUN-2", True, "constraint", None, "test", "CAL-1", ["TBD-3"], "RangerPrimary"),
    Req("CMP-5", "PrimaryRangerRefresh", "CMP", "Ubiquitous",
        "The primary forward ranger shall deliver a fresh sample at intervals not "
        "exceeding TBD-4 milliseconds.",
        "Bounds how stale the newest sample can be, which sets how far the rover "
        "moves between absolute updates. Split from staleness and quantisation so "
        "each is one verifiable claim (GtWR rule 1).",
        "FUN-2", True, "constraint", "UpperBoundRequirement", "test", "CAL-1",
        ["TBD-4"], "RangerPrimary"),
    Req("CMP-20", "PrimaryRangerStaleness", "CMP", "Ubiquitous",
        "The primary forward ranger shall report a range whose age does not exceed "
        "TBD-5 milliseconds at the instant it becomes readable.",
        "DERIVED. Staleness is a bias, not noise: at cruise it converts directly "
        "into millimetres of unseen travel, so it must be characterised and "
        "compensated rather than idealised away (tenet D2).",
        "FUN-2", True, "constraint", "UpperBoundRequirement", "test", "CAL-1",
        ["TBD-5"], "RangerPrimary"),
    Req("CMP-21", "PrimaryRangerQuantisation", "CMP", "Ubiquitous",
        "The primary forward ranger shall report range in steps not exceeding TBD-6 "
        "millimetres.",
        "DERIVED. A reporting artifact (tenet D1): the quantisation step, not the "
        "physical resolution, is what the estimator sees, and it sets the noise "
        "floor of the fused offset.",
        "FUN-2", True, "constraint", "UpperBoundRequirement", "test", "CAL-1",
        ["TBD-6"], "RangerPrimary"),
    Req("CMP-6", "OdometryScale", "CMP", "Ubiquitous",
        "The drive odometry shall report travel with a scale factor of TBD-7 "
        "millimetres of wall range per degree of wheel rotation.",
        "Single-effector leaf of FUN-2. The scale bundles wheel radius, gearing and "
        "slip, which is exactly why it is calibrated against the ranger rather than "
        "computed from nominal wheel geometry (tenet A3).",
        "FUN-2", True, "constraint", None, "test", "CAL-1", ["TBD-7"], "Drivetrain"),
    Req("CMP-7", "SecondaryRangerAgreement", "CMP", "Ubiquitous",
        "The secondary forward ranger shall agree with the primary ranger within "
        "TBD-8 millimetres, after removal of their fixed mounting difference, over "
        "the interval 40 mm to 1000 mm.",
        "DERIVED cross-source (GtWR rule 6). An independent ranger observing the "
        "same quantity is the fault-agnostic detector: a disagreement localises a "
        "fault without assuming which channel is wrong.",
        "FUN-2", True, "constraint", "UpperBoundRequirement", "test", "CAL-1",
        ["TBD-8"], "RangerSecondary"),
    Req("CMP-8", "TriggerTimingResolution", "CMP", "Ubiquitous",
        "The controller shall issue the brake command within TBD-9 milliseconds of "
        "the computed brake instant.",
        "DERIVED. Timing error converts to millimetres at cruise speed; a sub-loop "
        "wait is what keeps the trigger from inheriting the loop period as error.",
        "FUN-3", True, "constraint", "UpperBoundRequirement", "test", "CAL-1",
        ["TBD-9"], "Controller"),
    Req("CMP-9", "PlausibilityBounds", "CMP", "Ubiquitous",
        "The controller shall bound every logged channel by a stated physical range "
        "and shall flag any sample outside it.",
        "DERIVED. Makes physically impossible readings surface automatically, which "
        "is the trigger for unconditional escalation under ANOMALY DISPOSITION.",
        "FUN-5", True, "constraint", None, "inspection+test", "CAL-1", [], "Controller"),
    Req("CMP-10", "DeadReckonBackstop", "CMP", "Ubiquitous",
        "The controller shall brake unconditionally when odometric travel reaches "
        "the configured backstop distance.",
        "DERIVED. An independent, ranger-free stop path: it covers loss of echo and, "
        "set tight, it is what makes the first max-speed brake event safe before any "
        "stopping-travel calibration exists.",
        "FUN-5", True, "constraint", None, "test", "CAL-1", [], "Controller"),
    Req("CMP-11", "BrakeTravel", "CMP", "Ubiquitous",
        "Each drive motor shall arrest wheel rotation within TBD-10 millimetres of "
        "travel from the brake command at cruise speed.",
        "Single-effector leaf of FUN-4 and the second-highest-leverage parameter: it "
        "is measured directly at the operating point so no extrapolation enters the "
        "stop prediction (RelationTemplates::StoppingDistance guidance).",
        "FUN-4", True, "constraint", "UpperBoundRequirement", "test", "CAL-1",
        ["TBD-10"], "Drivetrain"),
    Req("CMP-22", "BrakeTravelRepeatability", "CMP", "Ubiquitous",
        "The travel from brake command to rest shall not vary by more than TBD-11 "
        "millimetres between runs at cruise speed.",
        "DERIVED. Run-to-run scatter, not the mean, is what the no-contact margin is "
        "made of (tenet A6); split from CMP-11 so each is one verifiable claim.",
        "FUN-4", True, "constraint", "UpperBoundRequirement", "test", "CAL-1",
        ["TBD-11"], "Drivetrain"),
    Req("CMP-12", "NoPostStopMotion", "CMP", "Unwanted",
        "The rover shall not move after reaching the full stop.",
        "DERIVED. The scored gap is measured by the operator some seconds after the "
        "run ends; creep or rollback between the stop and the measurement would make "
        "the onboard estimate and the ground truth refer to different positions.",
        "FUN-4", True, "constraint", None, "test", "CAL-1", [], "Drivetrain"),
    Req("CMP-13", "HeadingSensing", "CMP", "Ubiquitous",
        "The inertial unit shall report heading with a drift not exceeding TBD-12 "
        "degrees over the duration of one run.",
        "Single-effector leaf of FUN-6. The hub is power-cycled between runs so "
        "heading is always relative to the start pose; only within-run drift matters.",
        "FUN-6", True, "constraint", "UpperBoundRequirement", "test", "CAL-1",
        ["TBD-12"], "Imu"),
    Req("CMP-14", "WheelSpeedSymmetry", "CMP", "Ubiquitous",
        "The two drive motors shall maintain speeds within TBD-13 degrees per second "
        "of each other during cruise.",
        "DERIVED. Differential wheel speed is the mechanism behind heading "
        "deviation; measuring it separately from the IMU gives a second, independent "
        "view of straightness (cross-sourcing).",
        "FUN-6", True, "constraint", "UpperBoundRequirement", "test", "CAL-1",
        ["TBD-13"], "Drivetrain"),
    Req("CMP-15", "DeviceTypeIdentification", "CMP", "Event-driven",
        "When the program starts, the controller shall determine the device type "
        "present on each of the hub's six ports.",
        "Single-effector leaf of FUN-7: the port map is unknown a priori and every "
        "later channel depends on it.",
        "FUN-7", True, "constraint", None, "test", "CAL-1", [], "Controller"),
    Req("CMP-16", "DrivePolarityIdentification", "CMP", "Event-driven",
        "When the port map is known, the controller shall determine the pair of "
        "motor speed signs that moves the rover toward the wall.",
        "Single-effector leaf of FUN-7. Determined from the sign of the range change "
        "and the heading change under a short, low-speed probe, so no assumption "
        "about drivetrain mirroring is needed.",
        "FUN-7", True, "constraint", None, "test", "CAL-1", [], "Controller"),
    Req("CMP-17", "RestRangeEstimator", "CMP", "Ubiquitous",
        "The rover shall report a static-range clearance estimate at rest whenever "
        "the reported range is not less than TBD-15 millimetres.",
        "DERIVED. The static estimate is latency-free and therefore the most trusted "
        "onboard clearance channel, but it has a validity floor -- the condition is "
        "stated so the hand-off to the odometric estimate is planned, not improvised "
        "(CHARACTERIZATION METHOD 1).",
        "FUN-8", True, "constraint", "LowerBoundRequirement", "test", "CAL-1",
        ["TBD-15"], "RangerPrimary"),
    Req("CMP-18", "OdometricEstimator", "CMP", "Ubiquitous",
        "The rover shall report an odometric clearance estimate at every rest "
        "position, independent of the reported range at rest.",
        "DERIVED. Covers the range below the ranger's validity floor and provides "
        "the independent second estimate FUN-8 requires.",
        "FUN-8", True, "constraint", None, "test", "CAL-1", [], "Drivetrain"),
    Req("CMP-19", "ContactDetection", "CMP", "Ubiquitous",
        "The inertial unit shall report forward-axis acceleration throughout the "
        "brake phase at a rate sufficient to distinguish braking from an impact.",
        "DERIVED. Gives SYS-2 an onboard witness independent of the ranger and of "
        "the operator's observation: an impact is a distinctive acceleration "
        "transient, so 'no contact' is evidenced rather than assumed.",
        "FUN-8", True, "constraint", None, "test", "CAL-1", [], "Imu"),

    # ---------------- objective --------------------------------------------
    Req("OBJ-1", "MarginEfficiency", "OBJ", "Objective",
        "The commanded target clearance should not exceed the derived no-contact "
        "margin by more than a factor of TBD-17.",
        "DERIVED. Operationalises 'as close as possible': the smallest defensible "
        "target is the uncertainty-derived margin itself, so the objective is to "
        "leave no clearance beyond that margin. Below it we would be buying score "
        "with contact risk; above it we are giving away score for nothing.",
        "STK-2", True, "objective", "UpperBoundRequirement", "analysis", "GATE-B",
        ["TBD-16", "TBD-17"]),
]

# --- TBD register ---------------------------------------------------------
# id -> (quantity, model parameter, bound by, source-of-truth tier planned)
TBDS = {
    "TBD-1": ("minimum sustained wheel speed at the ceiling", "omega_cruise",
              "CAL-1 P4/P6 cruise plateau, per motor", "T4-onboard-multi"),
    "TBD-2": ("travel needed to reach ceiling speed", "a_accel",
              "CAL-1 P4 speed ramp", "T4-onboard-multi"),
    "TBD-3": ("primary ranger offset to the front-most point", "b_offset",
              "CAL-1 P8 static block + M1 operator measurement", "T5-external"),
    "TBD-4": ("ranger fresh-sample interval", "t_refresh",
              "CAL-1 P4 value-change interval histogram", "T4-onboard-multi"),
    "TBD-5": ("ranger sample staleness", "l_sensor",
              "CAL-1 P4/P6 dynamic-vs-static offset comparison", "T4-onboard-multi"),
    "TBD-6": ("ranger reported quantisation step", "q_range",
              "CAL-1 P2 static staircase + P4 trace", "T4-onboard-multi"),
    "TBD-7": ("odometry-to-range scale factor", "k_eff",
              "CAL-1 P2 static staircase regression", "T4-onboard-multi"),
    "TBD-8": ("primary-secondary ranger agreement", "d_agree",
              "CAL-1 P0/P2/P8 static blocks", "T4-onboard-multi"),
    "TBD-9": ("brake-command timing error", "e_trig",
              "CAL-1 P4 commanded vs achieved brake instant", "T4-onboard-multi"),
    "TBD-10": ("brake travel from command to rest at cruise", "psi_brake",
               "CAL-1 P4 and P6, odometry and ranger", "T4-onboard-multi"),
    "TBD-11": ("run-to-run scatter of brake travel", "sigma_psi",
               "CAL-1 P4 vs P6 (+ VER as a third sample)", "T4-onboard-multi"),
    "TBD-12": ("heading deviation limit and IMU drift", "psi_head / d_psi_head",
               "CAL-1 P4/P6 IMU yaw and differential odometry", "T4-onboard-multi"),
    "TBD-13": ("wheel-speed symmetry during cruise", "-- (encoder pair)",
               "CAL-1 P4/P6 per-motor speed traces", "T4-onboard-multi"),
    "TBD-14": ("allowed uncertainty of the reported clearance estimate", "sigma_est_limit",
               "design decision at GATE B, verified at GATE C", "T0-design"),
    "TBD-15": ("ranger validity floor", "r_min_valid",
               "CAL-1 P7 fine staircase into the near field", "T4-onboard-multi"),
    "TBD-16": ("no-contact margin", "m_contact",
               "computed at GATE B from the bound sigma contributors", "T4-onboard-multi"),
    "TBD-17": ("margin-efficiency factor", "k_obj",
               "design decision at GATE B", "T0-design"),
}

# --- elements ------------------------------------------------------------
ELEMENTS = {
    "MotorLeft": ("DriveMotor", "selected", "CMP-1"),
    "MotorRight": ("DriveMotor", "selected", "CMP-2"),
    "Drivetrain": ("composition of the two DriveMotors", "selected",
                   "CMP-3, CMP-6, CMP-11, CMP-22, CMP-12, CMP-14, CMP-18"),
    "RangerPrimary": ("DistanceSensor (forward)", "selected",
                      "CMP-4, CMP-5, CMP-20, CMP-21, CMP-17"),
    "RangerSecondary": ("DistanceSensor (forward)", "selected", "CMP-7"),
    "Imu": ("InertialUnit", "selected", "CMP-13, CMP-19"),
    "Controller": ("hub program", "selected", "CMP-8, CMP-9, CMP-10, CMP-15, CMP-16"),
    "RangerRear": ("DistanceSensor (rear)", "DROPPED", "none"),
    "FloorReflectance": ("ReflectanceSensor", "DROPPED", "none"),
}

DROP_RATIONALE = {
    "RangerRear": (
        "No requirement traces to it. It cannot observe the wall ahead, and the "
        "quantity it could otherwise serve -- travel from the start line -- is "
        "already covered by two better channels (the forward rangers absolutely, "
        "the odometry differentially) whose references are controlled, whereas "
        "whatever lies behind the rover is not. Dropped by traceability, and the "
        "drop is VERIFIED not assumed: CAL-1 logs it at low rate and the drop-out "
        "is confirmed only if its reported range increases while the forward ranges "
        "decrease (i.e. it is rear-facing and sees no wall ahead)."),
    "FloorReflectance": (
        "No requirement traces to it. The start position is fixed and squared by the "
        "operator, so no start-line detection function exists; reflectance observes "
        "no quantity in the clearance, speed, stop or heading chains. Dropped by "
        "traceability, VERIFIED by logging it in CAL-1 and confirming it carries no "
        "usable position information (uniform floor, no transition at the start line "
        "under the sensor)."),
}
