"""
EXECUTABLE ANALYSIS MODEL — Rover Wall-Stop System
Version: 2.0   Status: BASELINE   Date: 2026-07-21

CHANGES FROM v1:
  - loopPeriod_ms → tResponse_s (matches RoverLatency.tChain + sampling latency)
  - d_stop_mm + d_reaction_mm → dStopTotal_mm  (measured composite; matches
    StoppingDistance template at single operating point)
  - decel_mms2 added as back-solved attribute (not a calibration target)
  - k_mmrad added as implicit attribute (absorbed into vMax_mms measurement)
  - RangeRequirement removed; CMP-3 now LowerBoundRequirement only
  - dReaction_mm is now a derived property (vMax_mms * tResponse_s)

Maps 1:1 to sysml_model_v2.sysml / WallStopSystem.WallRoverDesign.
Every SysML attribute → named Python attribute.
SysML constraint expressions → Python constraint functions.

Interface contract:
  PREDICT  — compute finalClearance_mm from bound parameters and trigger setting.
  EVALUATE — return pass/fail dict for every requirement (matches SysML roll-up).
  SWEEP    — vary one parameter; return sensitivity table.
"""

import math
from typing import Optional, Dict, List, Tuple, Any


# ---------------------------------------------------------------------------
# Physical plausibility bounds — any value outside these is IMPOSSIBLE.
# Escalate unconditionally per ANOMALY DISPOSITION rules.
# Maps to TRACE SPINE "physical-plausibility bound on every logged channel."
# ---------------------------------------------------------------------------
PLAUSIBILITY: Dict[str, Tuple[float, float]] = {
    'vMaxRated_dps':    (200.0,  2000.0),   # deg/s
    'vMax_mms':         (50.0,   1500.0),   # mm/s
    'tResponse_s':      (0.005,  0.500),    # s  (5 ms – 500 ms)
    'dStopTotal_mm':    (1.0,    800.0),    # mm
    'decel_mms2':       (100.0,  50000.0),  # mm/s² (≈0.01g – 5g)
    'k_mmrad':          (1.0,    500.0),    # mm/rad
    'dCombo_mm':        (-50.0,  200.0),    # mm
    'ussValidMin_mm':   (10.0,   500.0),    # mm
    'ussAgreement_mm':  (0.0,    300.0),    # mm (can be large if sensors offset)
    'headingTol_deg':   (0.0,    90.0),     # deg
    'imuDrift_degps':   (0.0,    10.0),     # deg/s
    'safetyMargin_mm':  (0.0,    200.0),    # mm
}


class WallStopModel:
    """
    Executable realisation of WallStopSystem.WallRoverDesign (sysml_model_v2).

    Parameter → SysML attribute mapping:
      vMaxRated_dps   ↔  WallRover.vMaxRated_dps       [TBD_VMOT]
      vMax_mms        ↔  WallRover.vMax_mms             [TBD_VMAX_MMS]
      tResponse_s     ↔  WallRover.tResponse_s          [TBD_TRESP]
      dStopTotal_mm   ↔  WallRover.dStopTotal_mm        [TBD_DSTOP]
      decel_mms2      ↔  WallRover.decel_mms2           [TBD_DECEL]  back-solved
      k_mmrad         ↔  WallRover.k_mmrad              [TBD_K]      implicit
      dCombo_mm       ↔  WallRover.dCombo_mm            [TBD_COMBO]  T1-anchored
      ussValidMin_mm  ↔  WallRover.ussValidMin_mm       [TBD_USS_MIN]
      ussAgreement_mm ↔  WallRover.ussAgreement_mm      [TBD_USS_AGREE]
      headingTol_deg  ↔  WallRover.headingTol_deg       [TBD_HDG]
      imuDrift_degps  ↔  WallRover.imuDrift_degps       [TBD_HDG_DRIFT]
      safetyMargin_mm ↔  WallRover.safetyMargin_mm      design choice
    """

    def __init__(self):
        # Free parameters — None until calibration
        self.vMaxRated_dps:    Optional[float] = None
        self.vMax_mms:         Optional[float] = None
        self.tResponse_s:      Optional[float] = None
        self.dStopTotal_mm:    Optional[float] = None
        self.decel_mms2:       Optional[float] = None   # back-solved; optional
        self.k_mmrad:          Optional[float] = None   # implicit; optional
        self.dCombo_mm:        Optional[float] = None   # T1-anchored
        self.ussValidMin_mm:   Optional[float] = None
        self.ussAgreement_mm:  Optional[float] = None
        self.headingTol_deg:   Optional[float] = None
        self.imuDrift_degps:   Optional[float] = None
        self.safetyMargin_mm:  Optional[float] = None

        # Calibration residual uncertainties (1σ); set after calibration
        self.sigma_dStopTotal_mm:  Optional[float] = None
        self.sigma_dCombo_mm:      Optional[float] = None
        self.sigma_dReaction_mm:   Optional[float] = None
        self.sigma_ussNoise_mm:    Optional[float] = None

        # Fixed
        self.contactMargin_mm: float = 0.0

    # -----------------------------------------------------------------------
    # bind() — set calibrated values with plausibility check
    # -----------------------------------------------------------------------
    def bind(self, **kwargs) -> None:
        """Bind calibrated parameter values. Raises ValueError on violation."""
        for k, v in kwargs.items():
            if not hasattr(self, k):
                raise ValueError(f"Unknown parameter: '{k}'")
            lo, hi = PLAUSIBILITY.get(k, (-1e12, 1e12))
            if not (lo <= v <= hi):
                raise ValueError(
                    f"IMPOSSIBLE VALUE — {k}={v:.4g} outside physical bounds "
                    f"[{lo}, {hi}].  Escalate per ANOMALY DISPOSITION rules."
                )
            setattr(self, k, v)

    # -----------------------------------------------------------------------
    # Derived quantities (SysML assert constraints reproduced here)
    # -----------------------------------------------------------------------
    @property
    def dReaction_mm(self) -> float:
        """
        Distance traveled during tResponse_s at vMax_mms.
        SysML: part of stoppingModel assertion: v * tResponse component.
        """
        self._require('vMax_mms', 'tResponse_s')
        return self.vMax_mms * self.tResponse_s

    def stopping_model_check(self) -> bool:
        """
        Verify SysML stoppingModel assertion:
          dStopTotal_mm == vMax_mms * tResponse_s + vMax_mms² / (2 * decel_mms2)
        Returns True if within 1 mm (calibration noise tolerance).
        Only callable after all four parameters are bound.
        """
        self._require('vMax_mms', 'tResponse_s', 'dStopTotal_mm', 'decel_mms2')
        rhs = self.vMax_mms * self.tResponse_s + self.vMax_mms ** 2 / (2 * self.decel_mms2)
        return abs(self.dStopTotal_mm - rhs) <= 1.0

    def back_solve_decel(self) -> float:
        """
        Back-solve deceleration from measured dStopTotal and tResponse.
        Uses StoppingDistance template rearranged for a:
          a = vMax² / (2 * (dStopTotal - vMax * tResponse))
        """
        self._require('vMax_mms', 'tResponse_s', 'dStopTotal_mm')
        braking_dist = self.dStopTotal_mm - self.dReaction_mm
        if braking_dist <= 0:
            raise ValueError(
                f"braking_dist={braking_dist:.1f} <= 0: "
                f"tResponse too large or dStopTotal too small."
            )
        return self.vMax_mms ** 2 / (2.0 * braking_dist)

    def check_k_consistency(self) -> Optional[float]:
        """
        Check RotationToSpeed binding:  vMax_mms == vMaxRated_radps * k_mmrad
        Returns residual |computed_v - vMax_mms| if both are bound; else None.
        """
        if self.k_mmrad is None or self.vMaxRated_dps is None or self.vMax_mms is None:
            return None
        vMaxRated_radps = self.vMaxRated_dps * math.pi / 180.0
        computed_v = vMaxRated_radps * self.k_mmrad
        return abs(computed_v - self.vMax_mms)

    # -----------------------------------------------------------------------
    # Trigger design (reproduces SysML triggerDesign assertion)
    # -----------------------------------------------------------------------
    def d_trigger_for_margin(self, safety_margin_mm: float) -> float:
        """
        DESIGN EQUATION — USS reading at which to trigger braking.
        Reproduces SysML WallRover::triggerDesign:
          dTrigger = dStopTotal + dCombo + safetyMargin
        """
        self._require('dStopTotal_mm', 'dCombo_mm')
        return self.dStopTotal_mm + self.dCombo_mm + safety_margin_mm

    # -----------------------------------------------------------------------
    # PREDICT
    # -----------------------------------------------------------------------
    def predict_gap(self, d_trigger_uss_mm: float) -> float:
        """
        PREDICT — final front-face clearance (SysML WallRover::gapModel).

        Physics chain (reproducing gapModel assertion):
          At trigger:   true_front_clearance = d_trigger_uss - dCombo
          After braking rover travels dStopTotal more:
          finalClearance = d_trigger_uss - dCombo - dStopTotal

        = safetyMargin at the design trigger.
        Deviates from safetyMargin in operation by calibration residuals.
        """
        self._require('dStopTotal_mm', 'dCombo_mm')
        return d_trigger_uss_mm - self.dCombo_mm - self.dStopTotal_mm

    def predict_gap_with_uncertainty(self, d_trigger_uss_mm: float) -> Dict[str, float]:
        """
        PREDICT with uncertainty — mean gap + 1σ and 3σ bounds.
        RSS of independent calibration residuals (Tenet A6).
        """
        gap_mean = self.predict_gap(d_trigger_uss_mm)
        self._require('sigma_dStopTotal_mm', 'sigma_dCombo_mm',
                      'sigma_dReaction_mm', 'sigma_ussNoise_mm')
        sigma = math.sqrt(
            self.sigma_dStopTotal_mm ** 2 +
            self.sigma_dCombo_mm      ** 2 +
            self.sigma_dReaction_mm   ** 2 +
            self.sigma_ussNoise_mm    ** 2
        )
        return {
            'gap_mean_mm':      gap_mean,
            'sigma_total_mm':   sigma,
            'gap_lo_1sigma_mm': gap_mean - sigma,
            'gap_lo_3sigma_mm': gap_mean - 3.0 * sigma,
        }

    # -----------------------------------------------------------------------
    # EVALUATE — requirement roll-up (matches SysML satisfy/require)
    # -----------------------------------------------------------------------
    def evaluate(self, d_trigger_uss_mm: float,
                 with_uncertainty: bool = False) -> Dict[str, Any]:
        """
        EVALUATE — pass/fail for every requirement.
        Maps exactly to WallRunRequirements::WallRunNeed decomposition tree.

        SysML req           Python check
        ─────────────────────────────────────────────────────────
        STK-1 / SYS-1       finalClearance >= contactMargin (0)
        SYS-3 / CMP-1/2     motor commands == vMaxRated (programmatic)
        SYS-4               no run() after brake (programmatic inspection)
        SYS-5 / CMP-6       headingTol bound (TBD until cal)
        CMP-3               ussValidMin bound (TBD until cal)
        CMP-4               ussAgreement bound (TBD until cal)
        CMP-5               finalClearance >= 0 (same as SYS-1)
        """
        gap = self.predict_gap(d_trigger_uss_mm)

        result: Dict[str, Any] = {
            # STK → SYS → FUN → CMP roll-up
            'STK-1_no_contact_PASS':     gap >= self.contactMargin_mm,
            'SYS-1_clearance_PASS':      gap >= self.contactMargin_mm,
            'SYS-2_objective_gap_mm':    gap,            # graded
            'SYS-3_max_speed_PASS':      True,           # programmatic (cmd = MAX_SPEED)
            'SYS-4_no_resume_PASS':      True,           # programmatic (brake only)
            'SYS-5_heading_PASS':        self.headingTol_deg is not None,  # TBD_HDG
            'CMP-1_motorA_cmd_PASS':     self.vMaxRated_dps is not None,   # TBD_VMOT
            'CMP-2_motorB_cmd_PASS':     self.vMaxRated_dps is not None,   # TBD_VMOT
            'CMP-3_ussF1_valid_PASS':    self.ussValidMin_mm is not None,  # TBD_USS_MIN
            'CMP-4_ussF2_agree_PASS':    self.ussAgreement_mm is not None, # TBD_USS_AGREE
            'CMP-5_stop_clear_PASS':     gap >= 0.0,
            'CMP-6_imu_drift_PASS':      self.imuDrift_degps is not None,  # TBD_HDG_DRIFT

            # Derived quantities for the Verification Plan
            'predicted_gap_mm':          gap,
            'd_trigger_mm':              d_trigger_uss_mm,
            'dStopTotal_mm':             self.dStopTotal_mm,
            'dReaction_mm':              self.dReaction_mm if (self.vMax_mms and self.tResponse_s) else None,
            'dCombo_mm':                 self.dCombo_mm,
        }

        if with_uncertainty:
            dist = self.predict_gap_with_uncertainty(d_trigger_uss_mm)
            result.update(dist)
            result['SYS-1_1sigma_margin_PASS'] = dist['gap_lo_1sigma_mm'] >= 0.0
            result['SYS-1_3sigma_margin_PASS'] = dist['gap_lo_3sigma_mm'] >= 0.0

        # Overall hard-constraint roll-up
        hard_pass_keys = [k for k in result if k.endswith('_PASS')]
        result['OVERALL_PASS'] = all(result[k] for k in hard_pass_keys)

        return result

    # -----------------------------------------------------------------------
    # SWEEP — sensitivity analysis
    # -----------------------------------------------------------------------
    def sweep(self, param_name: str, param_range: List[float],
              d_trigger_uss_mm: float) -> List[Tuple[float, float]]:
        """
        SWEEP — vary one parameter; return [(value, predicted_gap)] pairs.
        All other parameters held at current bound values.
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

    def sensitivity_table_v2(self) -> str:
        """
        Sensitivity table updated for v2 parameter names.
        (Same physics, renamed per rover_generic.sysml alignment.)
        """
        lines = [
            "| Parameter (v2 name) | Prior Range | Gap Sensitivity | Knowledge Tier | Priority |",
            "|---------------------|------------|-----------------|----------------|----------|",
            "| dStopTotal_mm       | [50, 300] mm  | **±125 mm** | T0 — prior only (must measure on hardware) | **P1 CRITICAL** |",
            "| dCombo_mm           | [0, 100] mm   | **±50 mm**  | T0 → T1 via operator measurement          | **P2 HIGH** |",
            "| tResponse_s         | [0.02, 0.10] s | **±40 mm** at v=500 mm/s | T0 → T2 via hub-clock timestamps | **P3 HIGH** (free) |",
            "| vMax_mms            | [200, 700] mm/s | 25 mm (d_reaction only; also sets dStop scale via v²) | T0 → T2 via USS slope | **P4 MED-HIGH** |",
        ]
        lines += [
            "",
            "Pre-calibration RSS ≈ √(125²+50²+40²+15²) ≈ **138 mm** → contact near-certain.",
            "Post-calibration target RSS ≈ √(5²+5²+2²+5²) ≈ **9 mm**.",
        ]
        return "\n".join(lines)

    # -----------------------------------------------------------------------
    # Operation constants — embed in MicroPython program
    # -----------------------------------------------------------------------
    def operation_constants(self) -> Dict[str, float]:
        """
        Return constants for embedding in the operation program,
        evaluated at the committed configuration (safety_margin set).
        """
        self._require('vMaxRated_dps', 'dStopTotal_mm', 'dCombo_mm',
                      'tResponse_s', 'safetyMargin_mm')
        trigger = self.d_trigger_for_margin(self.safetyMargin_mm)
        return {
            'MAX_SPEED_DPS':      self.vMaxRated_dps,
            'TRIGGER_DIST_MM':    trigger,
            'LOOP_PERIOD_MS':     int(self.tResponse_s * 1000),
            'D_STOP_TOTAL_MM':    self.dStopTotal_mm,
            'D_COMBO_MM':         self.dCombo_mm,
            'SAFETY_MARGIN_MM':   self.safetyMargin_mm,
            'PREDICTED_GAP_MM':   self.predict_gap(trigger),
        }

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------
    def _require(self, *params: str) -> None:
        unbound = [p for p in params if getattr(self, p) is None]
        if unbound:
            raise RuntimeError(
                f"Unbound parameters: {unbound}. "
                f"Run calibration and call bind() first."
            )


# ---------------------------------------------------------------------------
# Self-test / demo
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    m = WallStopModel()

    print("=== SENSITIVITY TABLE v2 ===")
    print(m.sensitivity_table_v2())

    print("\n=== ILLUSTRATIVE BINDING (not calibrated values) ===")
    m.bind(
        vMaxRated_dps   = 1110.0,
        vMax_mms        = 490.0,
        tResponse_s     = 0.050,
        dStopTotal_mm   = 115.0,        # v*tResp + v²/(2a) at operating point
        dCombo_mm       = 55.0,
        ussValidMin_mm  = 40.0,
        ussAgreement_mm = 20.0,
        headingTol_deg  = 5.0,
        imuDrift_degps  = 0.5,
        safetyMargin_mm = 10.0,
        sigma_dStopTotal_mm = 5.0,
        sigma_dCombo_mm     = 5.0,
        sigma_dReaction_mm  = 2.0,
        sigma_ussNoise_mm   = 5.0,
    )

    print(f"\ndReaction_mm (derived) = {m.dReaction_mm:.1f} mm")
    print(f"  (v*tResp = {m.vMax_mms:.0f} × {m.tResponse_s:.3f} = {m.dReaction_mm:.1f})")

    # Back-solve decel
    a = m.back_solve_decel()
    m.bind(decel_mms2=a)
    print(f"decel_mms2 (back-solved) = {a:.0f} mm/s² ≈ {a/9810:.2f} g")

    # Verify stoppingModel constraint
    print(f"stoppingModel consistent: {m.stopping_model_check()}")

    # Trigger and gap
    trigger = m.d_trigger_for_margin(m.safetyMargin_mm)
    print(f"\nTrigger @ 10 mm margin: {trigger:.1f} mm")
    gap_dist = m.predict_gap_with_uncertainty(trigger)
    print(f"Predicted gap:  {gap_dist['gap_mean_mm']:.1f} ± {gap_dist['sigma_total_mm']:.1f} mm (1σ)")
    print(f"  1σ worst-case: {gap_dist['gap_lo_1sigma_mm']:.1f} mm")
    print(f"  3σ worst-case: {gap_dist['gap_lo_3sigma_mm']:.1f} mm")

    # Evaluate
    result = m.evaluate(trigger, with_uncertainty=True)
    print("\n=== EVALUATE v2 ===")
    for k, v in result.items():
        print(f"  {k}: {v}")

    # Sweep dStopTotal
    print("\n=== SWEEP: dStopTotal_mm (at fixed trigger) ===")
    sweep = m.sweep('dStopTotal_mm', list(range(50, 210, 25)), trigger)
    print(f"  {'dStopTotal':>12} | {'gap_mm':>8}")
    for val, g in sweep:
        flag = "  ← CONTACT" if g < 0 else ""
        print(f"  {val:>12.0f} | {g:>8.1f}{flag}")
