#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
08_run1_bindings.py -- what RUN-1 legitimately bound, with evidence and tier.

RUN-1 failed its primary purpose (the rover rotated instead of approaching, so no
valid approach, stop, or scale data exists).  It did not fail completely.  This
module binds ONLY what the run actually evidenced, and leaves everything else
unbound -- the point of A3 is that a failed run must not tempt anyone into
eyeballing the parameters it was supposed to measure.

Run id: run-20260805-204852
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wall_stop_model as M

RUN = "RUN-1 (run-20260805-204852)"


def apply(p: M.Params) -> M.Params:
    # --- loop period -------------------------------------------------------
    # 34 hot-path samples spanning 3646 -> 3992 ms  =>  10.18 ms/loop
    p.bind("t_loop_s", (3992 - 3646) / 34 / 1000.0, 2,
           RUN + ": 34 hot-path buffer samples over 346 ms")

    # --- motor ceiling -----------------------------------------------------
    # Reported by the motor controller itself, not inferred from a plateau.
    # The cruise-plateau confirmation (CMP-1/2) is still outstanding.
    p.bind("omega_max_deg_s", 1000.0, 2,
           RUN + ": Motor.control.limits() speed ceiling")

    # --- ranger noise at ~900 mm ------------------------------------------
    # 12-sample static dwell: ranger A range 5 mm, ranger B range 12 mm.
    # For n=12 the range-to-sigma factor is 3.26.  Fusion is min(), and the
    # 107 mm pair offset means the fused channel IS ranger B, so the fused
    # noise is B's.  Bound at ONE range only -- CMP-8 needs the trigger and
    # rest ranges too, so this does not close it.
    p.bind("sigma_n_mm", 12.0 / 3.26, 2,
           RUN + ": 12-sample static dwell at ~900 mm (ranger B, the fused channel)")

    # --- forward-pair offset ----------------------------------------------
    # A = 1010.5 mm, B = 903.4 mm at rest, BEFORE any motion.
    p.bind("delta_AB_mm", 107.1, 2,
           RUN + ": static pre-run dwell, A 1010.5 vs B 903.4 mm")

    # --- start range -------------------------------------------------------
    p.bind("R0_mm", 903.4, 2, RUN + ": fused static pre-run sample")
    return p


UNBOUND_BY_DESIGN = {
    "k_mm_per_deg": "no valid translation occurred -- the rover rotated",
    "a_decel_mm_s2": "no valid approach, so no valid stop window",
    "tau_sensor_s": "requires the acceleration ramp against a tracked wall",
    "t_chain_s": "lumped into S; no valid S",
    "T_refresh_s": "trace contaminated by the wall passing out of the beam",
    "r_floor_mm": "creep never approached the wall",
    "b_offset_mm": "M1 deliberately NOT spent -- the rover did not reach a close pose",
    "u_b_mm": "depends on M1",
    "theta_dev_deg": "the 95 deg observed is a fault signature, not a drift measurement",
    "sym_dev_deg_s": "no valid straight-line cruise",
    "e_odo_mm": "no valid odometry-vs-ranger comparison",
}


def main():
    p = apply(M.build_params())
    print("=" * 74)
    print("PARAMETER STATE AFTER RUN-1")
    print("=" * 74)
    print("BOUND:")
    for par in p:
        if par.value is not None:
            print(f"  {par.name:<18} = {par.value:<10.4g} {M.TIER_NAMES[par.tier]}")
            print(f"      evidence: {par.evidence}")
    print()
    print(f"STILL UNBOUND: {len(p.unbound())} of {len(p.names())}")
    for n in p.unbound():
        why = UNBOUND_BY_DESIGN.get(n, "")
        if why:
            print(f"  {n:<18} {why}")
    print()
    print("ROLL-UP:", M.rollup(M.evaluate(p)))
    print()
    print("Requirements RUN-1 can close on its own evidence:")
    print("  CMP-11 loop period 10.18 ms <= 25 ms                    PASS (test)")
    print("  CMP-12 rear ranger reads 2000 at start/rest/creep       DROP (traceability)")
    print("  CMP-13 reflectance serves no quantity                   DROP (traceability)")
    print("  FUN-3  wrong-way guard fired at 155 deg, no contact     PASS (test)")
    print("  FUN-12 sentinel emitted on the abort path               PASS (test)")
    print("  FUN-13 pair offset 107.1 mm > 30 mm limit               FAIL (test)")


if __name__ == "__main__":
    main()
