"""
EXECUTABLE ANALYSIS MODEL — Rover Wall-Stop System
Version: 1.0   Status: BASELINE   Date: 2026-07-21

Maps 1:1 to sysml_model_v1.sysml.  Every parameter, relation, and
requirement constraint in the SysML model appears here as a named
variable or function.  A mismatch between the SysML roll-up and the
Python evaluation is a defect to fix before the gate.

Interface contract (per process instructions):
  PREDICT  — compute performance quantities from bound parameters.
  EVALUATE — return pass/fail dict for each requirement.
  SWEEP    — vary one parameter over a range; return sensitivity table.

Parameters are left None until calibration binds them (uncalibrated,
not zeroed).  Call bind(**kwargs) to set calibrated values.

Trace spine:
  SysML attribute          Python attribute            Calibration source
  ─────────────────────────────────────────────────────────────────────
  vMaxRated_dps            self.vMaxRated_dps          Cal-Run-2
  vMaxRover_mms            self.vMaxRover_mms          Cal-Run-2
  dStop_mm                 self.dStop_mm               Cal-Run-2
  loopPeriod_ms            self.loopPeriod_ms          Cal-Run-2
  dReaction_mm             self.dReaction_mm           derived
  dCombo_mm                self.dCombo_mm              Verif-Run + T1 meas.
  ussValidMin_mm           self.ussValidMin_mm         Cal-Run-2
  ussAgreement_mm          self.ussAgreement_mm        Cal-Run-2
  headingTol_deg           self.headingTol_deg         Cal-Run-2
  imuDrift_dps_s           self.imuDrift_dps_s         Cal-Run-2
  finalClearance_mm        self.predict_gap(trigger)   model output
"""

import math
from typing import Optional, Dict, List, Tuple, Any


# ---------------------------------------------------------------------------
# Physical plausibility bounds (for anomaly detection).
# Any observed or predicted value outside these bounds is IMPOSSIBLE
# and must be escalated unconditionally per ANOMALY DISPOSITION rules.
# ---------------------------------------------------------------------------
PLAUSIBILITY = {
    'vMaxRated_dps':    (200.0,  2000.0),   # deg/s — SPIKE motors
    'vMaxRover_mms':    (50.0,   1500.0),   # mm/s
    'dStop_mm':         (1.0,    800.0),    # mm — can't stop in 0 mm; can't coast > 800mm
    'loopPeriod_ms':    (5.0,    500.0),    # ms
    'dReaction_mm':     (0.5,    200.0),    # mm
    'dCombo_mm':        (-50.0,  200.0),    # mm (can be negative if USS reads short)
    'ussValidMin_mm':   (10.0,   500.0),    # mm — sensor close-range validity
    'ussAgreement_mm':  (0.0,    100.0),    # mm
    'headingTol_deg':   (0.0,    90.0),     # deg
    'imuDrift_dps_s':   (0.0,    10.0),     # deg/s
}


class WallStopModel:
    """
    Executable realisation of the SysML WallStopSystem.WallRoverDesign.
    All parameters start as None (free); bind() sets calibrated values.
    """

    # -----------------------------------------------------------------------
    # Free parameters — None until calibration
    # -----------------------------------------------------------------------
    vMaxRated_dps:    Optional[float]   # [TBD_VMOT]       CMP-1/2
    vMaxRover_mms:    Optional[float]   # [TBD_VMAX_MMS]   SYS-3
    dStop_mm:         Optional[float]   # [TBD_DSTOP]      CMP-5
    loopPeriod_ms:    Optional[float]   # [TBD_LOOP]       CMP-5
    dCombo_mm:        Optional[float]   # [TBD_COMBO]      SYS-1/2 (T1 source)
    ussValidMin_mm:   Optional[float]   # [TBD_USS_MIN]    CMP-3
    ussAgreement_mm:  Optional[float]   # [TBD_USS_AGREE]  CMP-4
    headingTol_deg:   Optional[float]   # [TBD_HDG]        SYS-5
    imuDrift_dps_s:   Optional[float]   # [TBD_HDG_DRIFT]  CMP-6

    # Calibration residual uncertainties (1σ); set after calibration
    sigma_dStop_mm:     Optional[float]
    sigma_dCombo_mm:    Optional[float]
    sigma_dReaction_mm: Optional[float]
    sigma_uss_noise_mm: Optional[float]

    # -----------------------------------------------------------------------
    # Fixed parameters
    # -----------------------------------------------------------------------
    startDistance_mm: float = 1000.0   # nominal start distance [FIXED]
    contactMargin_mm: float = 0.0      # SYS-1 hard bound [FIXED]

    def __init__(self):
        # Free parameters
        self.vMaxRated_dps    = None
        self.vMaxRover_mms    = None
        self.dStop_mm         = None
        self.loopPeriod_ms    = None
        self.dCombo_mm        = None
        self.ussValidMin_mm   = None
        self.ussAgreement_mm  = None
        self.headingTol_deg   = None
        self.imuDrift_dps_s   = None
        # Uncertainty residuals (post-calibration)
        self.sigma_dStop_mm     = None
        self.sigma_dCombo_mm    = None
        self.sigma_dReaction_mm = None
        self.sigma_uss_noise_mm = None

    # -----------------------------------------------------------------------
    # bind() — sets calibrated values and checks plausibility
    # -----------------------------------------------------------------------
    def bind(self, **kwargs) -> None:
        """Bind calibrated parameter values.  Raises ValueError on invalid input."""
        for k, v in kwargs.items():
            if not hasattr(self, k):
                raise ValueError(f"Unknown parameter: '{k}'")
            lo, hi = PLAUSIBILITY.get(k, (-1e9, 1e9))
            if not (lo <= v <= hi):
                raise ValueError(
                    f"IMPOSSIBLE VALUE — {k}={v:.3f} outside physical bounds [{lo}, {hi}]. "
                    f"Escalate unconditionally per ANOMALY DISPOSITION rules."
                )
            setattr(self, k, v)

    # -----------------------------------------------------------------------
    # Derived quantities
    # -----------------------------------------------------------------------
    @property
    def dReaction_mm(self) -> float:
        """Distance traveled in one loop period at max speed (SysML: dReaction_mm)."""
        self._require_bound('vMaxRover_mms', 'loopPeriod_ms')
        return self.vMaxRover_mms * (self.loopPeriod_ms / 1000.0)

    def d_trigger_for_margin(self, safety_margin_mm: float) -> float:
        """
        DESIGN EQUATION — USS trigger distance for a given safety margin.
        SysML assert: dTrigger >= dStop + dReaction + dCombo + margin.
        """
        self._require_bound('dStop_mm', 'dCombo_mm')
        return self.dStop_mm + self.dReaction_mm + self.dCombo_mm + safety_margin_mm

    # -----------------------------------------------------------------------
    # PREDICT
    # -----------------------------------------------------------------------
    def predict_gap(self, d_trigger_uss_mm: float) -> float:
        """
        PREDICT — final front-face clearance from wall given the USS trigger setting.

        Physics chain:
          At trigger moment:
            true_front_clearance = d_trigger_uss - d_combo
          After braking (rover travels d_stop + d_reaction more):
            final_gap = true_front_clearance - d_stop - d_reaction
                      = d_trigger_uss - d_combo - d_stop - d_reaction

        SysML mapping:
          finalClearance_mm := d_trigger_uss - dCombo_mm - dStop_mm - dReaction_mm
        """
        self._require_bound('dStop_mm', 'dCombo_mm')
        return d_trigger_uss_mm - self.dCombo_mm - self.dStop_mm - self.dReaction_mm

    def predict_gap_distribution(self, d_trigger_uss_mm: float) -> Dict[str, float]:
        """
        PREDICT with uncertainty.  Returns mean gap + 1σ and 3σ bounds.
        Uses root-sum-square of independent calibration residuals.
        All sigma_* must be bound first.
        """
        gap_mean = self.predict_gap(d_trigger_uss_mm)
        self._require_bound('sigma_dStop_mm', 'sigma_dCombo_mm',
                            'sigma_dReaction_mm', 'sigma_uss_noise_mm')
        sigma_total = math.sqrt(
            self.sigma_dStop_mm    ** 2 +
            self.sigma_dCombo_mm   ** 2 +
            self.sigma_dReaction_mm** 2 +
            self.sigma_uss_noise_mm** 2
        )
        return {
            'gap_mean_mm':     gap_mean,
            'gap_1sigma_mm':   sigma_total,
            'gap_3sigma_mm':   3.0 * sigma_total,
            'gap_minus_1s_mm': gap_mean - sigma_total,   # worst-case 1σ
            'gap_minus_3s_mm': gap_mean - 3.0 * sigma_total,  # worst-case 3σ
        }

    # -----------------------------------------------------------------------
    # EVALUATE — requirement pass/fail roll-up
    # -----------------------------------------------------------------------
    def evaluate(self, d_trigger_uss_mm: float,
                 with_uncertainty: bool = False) -> Dict[str, Any]:
        """
        EVALUATE — return pass/fail for every requirement given trigger setting.
        Maps to the SysML satisfy/require roll-up.

        SysML requirement → Python check:
          SYS-1 (no contact): predicted_gap >= 0
          SYS-3 (max speed):  programmatic (inspection); always True here
          SYS-4 (no resume):  programmatic (inspection); always True here
          SYS-5 (heading):    headingTol_deg must be bound
          CMP-5 (d_stop):     d_trigger - d_combo - d_reaction >= 0 (rover stops in time)
        """
        gap = self.predict_gap(d_trigger_uss_mm)

        result = {
            # --- SYS requirements ---
            'SYS-1_no_contact_PASS':    gap >= self.contactMargin_mm,
            'SYS-2_objective_gap_mm':   gap,           # graded; no pass/fail
            'SYS-3_max_speed_PASS':     True,          # programmatic — command is max_speed
            'SYS-4_no_resume_PASS':     True,          # programmatic — brake only, no run() after
            'SYS-5_heading_PASS':       (self.headingTol_deg is not None),  # TBD until cal

            # --- CMP requirements (contributing checks) ---
            'CMP-1_motorA_speed_PASS':  (self.vMaxRated_dps is not None),   # TBD_VMOT
            'CMP-2_motorB_speed_PASS':  (self.vMaxRated_dps is not None),   # TBD_VMOT
            'CMP-3_ussF1_valid_PASS':   (self.ussValidMin_mm is not None),  # TBD_USS_MIN
            'CMP-4_ussF2_agree_PASS':   (self.ussAgreement_mm is not None), # TBD_USS_AGREE
            'CMP-5_stop_dist_PASS':     gap >= 0.0,
            'CMP-6_imu_drift_PASS':     (self.imuDrift_dps_s is not None),  # TBD_HDG_DRIFT

            # --- Derived quantities ---
            'predicted_gap_mm':         gap,
            'd_trigger_mm':             d_trigger_uss_mm,
            'd_stop_mm':                self.dStop_mm,
            'd_reaction_mm':            self.dReaction_mm,
            'd_combo_mm':               self.dCombo_mm,
        }

        if with_uncertainty:
            dist = self.predict_gap_distribution(d_trigger_uss_mm)
            result.update(dist)
            result['SYS-1_1sigma_margin_PASS'] = dist['gap_minus_1s_mm'] >= 0.0
            result['SYS-1_3sigma_margin_PASS'] = dist['gap_minus_3s_mm'] >= 0.0

        # Overall roll-up: ALL hard-constraint requirements must PASS
        hard_keys = [k for k in result if k.endswith('_PASS') and
                     k not in ('SYS-3_max_speed_PASS', 'SYS-4_no_resume_PASS')]
        result['OVERALL_PASS'] = all(result[k] for k in hard_keys)

        return result

    # -----------------------------------------------------------------------
    # SWEEP — sensitivity analysis
    # -----------------------------------------------------------------------
    def sweep(self, param_name: str, param_range: List[float],
              d_trigger_uss_mm: float) -> List[Tuple[float, float]]:
        """
        SWEEP — vary one parameter over param_range, compute resulting gap.
        Other parameters held at their currently bound values.
        Restores original value after sweep.

        Returns: list of (param_value, predicted_gap_mm) pairs.
        """
        if not hasattr(self, param_name):
            raise ValueError(f"Unknown parameter: '{param_name}'")
        original = getattr(self, param_name)
        results = []
        try:
            for v in param_range:
                setattr(self, param_name, v)
                try:
                    gap = self.predict_gap(d_trigger_uss_mm)
                    results.append((v, gap))
                except RuntimeError:
                    results.append((v, float('nan')))
        finally:
            setattr(self, param_name, original)
        return results

    def sensitivity_analysis(self) -> str:
        """
        Compute and format the required sensitivity table (GATE A / Section 0).

        Assumes PRIOR ranges; trigger is re-computed optimally for each sweep
        (i.e., the question is: 'if this parameter is actually X instead of
        nominal, how much does the TRUE final gap differ from our prediction?').

        The table answers: gap error = actual_gap - predicted_gap at optimal trigger.
        gap_error = -(param_actual - param_nominal) for each linear parameter.
        """

        # Prior assumptions (before any calibration)
        priors = {
            'dStop_mm':         dict(lo=50,   hi=300,  nom=150.0, unit='mm',
                                     desc='Stopping distance at v_max',
                                     tier='T0 (Prior only)',
                                     source='Unknown — must measure on hardware'),
            'dCombo_mm':        dict(lo=0,    hi=100,  nom=50.0,  unit='mm',
                                     desc='d_front_offset + uss_bias (combined)',
                                     tier='T0 (Prior only)',
                                     source='Unknown — requires T1 operator meas.'),
            'loopPeriod_ms':    dict(lo=20,   hi=100,  nom=50.0,  unit='ms',
                                     desc='Control loop period',
                                     tier='T0 (Prior — cheaply upgraded to T2 via timestamps)',
                                     source='Timestamp log in Cal-Run-2'),
            'vMaxRover_mms':    dict(lo=200,  hi=700,  nom=500.0, unit='mm/s',
                                     desc='Max rover speed',
                                     tier='T0 (Prior only)',
                                     source='USS slope fit in Cal-Run-2'),
        }

        nom_vmax  = priors['vMaxRover_mms']['nom']
        nom_loop  = priors['loopPeriod_ms']['nom']
        nom_dstop = priors['dStop_mm']['nom']
        nom_combo = priors['dCombo_mm']['nom']
        nom_react = nom_vmax * nom_loop / 1000.0  # = 25 mm at nom

        # Gap error when each parameter deviates from nominal (linear sensitivity = -1)
        rows = []
        for key, p in priors.items():
            rng = p['hi'] - p['lo']
            half_rng = rng / 2.0
            if key == 'loopPeriod_ms':
                # d_reaction = vMax * loop / 1000;  dg/d(loop) = -vMax/1000
                sens_per_unit = -nom_vmax / 1000.0   # mm gap per ms
                gap_excursion = abs(sens_per_unit) * rng
            elif key == 'vMaxRover_mms':
                # d_reaction = v * loop / 1000;  dg/d(v) = -loop/1000
                sens_per_unit = -nom_loop / 1000.0   # mm gap per mm/s
                gap_excursion = abs(sens_per_unit) * rng
                # Also: v affects d_stop (roughly d_stop ∝ v²); cannot quantify pre-calibration
                gap_excursion_note = f"{gap_excursion:.0f} mm (d_reaction only; also drives d_stop via v²)"
            else:
                sens_per_unit = -1.0                 # 1:1 for dStop and dCombo
                gap_excursion = abs(sens_per_unit) * rng

            if key == 'vMaxRover_mms':
                obj_sens = gap_excursion_note
            else:
                obj_sens = f"±{half_rng:.0f} mm"

            rows.append({
                'param': key,
                'desc': p['desc'],
                'range': f"[{p['lo']}, {p['hi']}] {p['unit']}",
                'obj_sens': obj_sens,
                'tier': p['tier'],
                'priority': '',
            })

        # Rank by gap excursion
        priority_map = {
            'dStop_mm':      'P1 — CRITICAL (±125 mm; must calibrate on hardware)',
            'dCombo_mm':     'P2 — HIGH (±50 mm; requires T1 operator measurement)',
            'loopPeriod_ms': 'P3 — HIGH (±40 mm at nom v; free from timestamp log)',
            'vMaxRover_mms': 'P4 — MEDIUM-HIGH (secondary via d_reaction; drives d_stop scale)',
        }
        for r in rows:
            r['priority'] = priority_map.get(r['param'], '—')

        # Format table
        header = (
            "| Parameter | Assumed Range | Obj./Margin Sensitivity | "
            "Knowledge Tier | Priority |\n"
            "|-----------|--------------|-------------------------|"
            "----------------|----------|\n"
        )
        body = ""
        for r in rows:
            body += (f"| {r['param']} | {r['range']} | {r['obj_sens']} | "
                     f"{r['tier']} | {r['priority']} |\n")

        footer = (
            "\n**RSS pre-calibration gap uncertainty:**  "
            "sqrt(125² + 50² + 40² + 15²) ≈ **138 mm**  (contact risk without calibration)\n"
            "**RSS post-calibration target:**  "
            "sqrt(5² + 5² + 2² + 5²) ≈ **9 mm**  (after binding all parameters)\n"
        )

        return header + body + footer

    # -----------------------------------------------------------------------
    # Operational program constants (for embedding in the operation program)
    # -----------------------------------------------------------------------
    def operation_constants(self, safety_margin_mm: float) -> Dict[str, float]:
        """
        Return the constants to embed in the operation MicroPython program,
        derived from the calibrated model.
        """
        self._require_bound('dStop_mm', 'dCombo_mm', 'vMaxRated_dps',
                            'loopPeriod_ms', 'vMaxRover_mms')
        return {
            'MAX_SPEED_DPS':    self.vMaxRated_dps,
            'TRIGGER_DIST_MM':  self.d_trigger_for_margin(safety_margin_mm),
            'LOOP_PERIOD_MS':   int(self.loopPeriod_ms),
            # Embedded for logging/telemetry only:
            'D_STOP_MM':        self.dStop_mm,
            'D_COMBO_MM':       self.dCombo_mm,
            'D_REACTION_MM':    self.dReaction_mm,
            'PREDICTED_GAP_MM': self.predict_gap(self.d_trigger_for_margin(safety_margin_mm)),
        }

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------
    def _require_bound(self, *params: str) -> None:
        unbound = [p for p in params if getattr(self, p) is None]
        if unbound:
            raise RuntimeError(
                f"Parameters not yet calibrated: {unbound}.  "
                f"Run the calibration program and call bind() first."
            )


# ---------------------------------------------------------------------------
# Self-test / demo
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    m = WallStopModel()

    print("=== SENSITIVITY TABLE (pre-calibration priors) ===")
    print(m.sensitivity_analysis())

    print("\n=== BINDING EXAMPLE (illustrative — not calibrated values) ===")
    m.bind(
        vMaxRated_dps   = 1110.0,
        vMaxRover_mms   = 490.0,
        dStop_mm        = 100.0,
        loopPeriod_ms   = 50.0,
        dCombo_mm       = 55.0,
        ussValidMin_mm  = 40.0,
        ussAgreement_mm = 20.0,
        headingTol_deg  = 5.0,
        imuDrift_dps_s  = 0.5,
        sigma_dStop_mm     = 5.0,
        sigma_dCombo_mm    = 5.0,
        sigma_dReaction_mm = 2.0,
        sigma_uss_noise_mm = 5.0,
    )

    trigger = m.d_trigger_for_margin(safety_margin_mm=0.0)
    print(f"\nTrigger at 0mm safety margin: {trigger:.1f} mm  (d_reaction={m.dReaction_mm:.1f}mm)")

    trigger_safe = m.d_trigger_for_margin(safety_margin_mm=10.0)
    print(f"Trigger at 10mm safety margin: {trigger_safe:.1f} mm")

    result = m.evaluate(trigger_safe, with_uncertainty=True)
    print("\n=== EVALUATE OUTPUT ===")
    for k, v in result.items():
        print(f"  {k}: {v}")

    print("\n=== SWEEP: dStop_mm sensitivity ===")
    sweep = m.sweep('dStop_mm', list(range(50, 310, 50)), d_trigger_uss_mm=trigger_safe)
    print(f"  {'dStop_mm':>10} | {'gap_mm':>10}")
    for val, gap in sweep:
        print(f"  {val:>10.1f} | {gap:>10.1f}")
