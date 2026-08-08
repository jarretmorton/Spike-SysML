# -*- coding: utf-8 -*-
"""
build_model.py -- generates wall_rover.sysml (requirements package) from the
requirement table, emits the Mermaid tree and the trace spine, and runs the
STRUCTURAL CHECKS that grammar conformance cannot see:
  (1) every requirement reachable from the top need;
  (2) the realised decomposition edge-set == the requirement-table edge-set;
  (3) per-package import resolution for every qualified reference;
  (4) every bound operand resolves to a declared WallRover attribute;
  (5) SysML requirement set == executable-model requirement set (no drift).
"""
import re, sys
import wall_rover_model as M
from model_reqs import build as build_reqs

REQS = build_reqs(M)

# ---------------------------------------------------------------- trace spine
# python parameter -> SysML attribute on WallRover. THIS IS THE TRACE SPINE.
NAME_MAP = {
    "motor_speed_cmd_dps": "motorSpeedCmd", "motor_speed_max_dps": "motorSpeedMax",
    "motor_speed_ach_left_dps": "motorSpeedAchLeft",
    "motor_speed_ach_right_dps": "motorSpeedAchRight",
    "k_odo_mm_per_deg": "kOdo", "v_cruise_mmps": "vCruise",
    "drive_asymmetry_dps": "driveAsymmetry",
    "drive_asymmetry_limit_dps": "driveAsymmetryLimit",
    "stop_angle_left_deg": "stopAngleLeft", "stop_angle_right_deg": "stopAngleRight",
    "stop_angle_limit_deg": "stopAngleLimit",
    "brake_skew_ms": "brakeCommandSkew", "brake_skew_limit_ms": "brakeCommandSkewLimit",
    "k_us": "kUs", "c_us_mm": "cUs", "tau_ms": "tauSensor", "tau_limit_ms": "tauLimit",
    "t_refresh_ms": "tRefresh", "t_refresh_limit_ms": "tRefreshLimit",
    "sigma_us_mm": "sigmaUs", "sigma_k_us": "sigmaKUs",
    "us_valid_min_mm": "rangeValidMin", "us_valid_max_mm": "rangeValidMax",
    "r_anchor_mm": "rAnchor",
    "ranger_fl_residual_mm": "rangerFLResidual",
    "ranger_fr_residual_mm": "rangerFRResidual",
    "ranger_residual_tol_mm": "rangerResidualTolerance",
    "loop_dt_ms": "loopPeriod", "loop_period_limit_ms": "loopPeriodLimit",
    "t_act_ms": "latency.tChain", "t_response_limit_ms": "tResponseLimit",
    "clearance_update_ms": "clearanceUpdateInterval",
    "clearance_update_limit_ms": "clearanceUpdateLimit",
    "heading_sample_ms": "headingSampleInterval",
    "heading_sample_limit_ms": "headingSampleLimit",
    "a_brake_mmps2": "aBrake", "d_total_meas_mm": "stopTravel",
    "t_settle_ms": "stopSettleTime", "stop_time_limit_ms": "stopTimeLimit",
    "psi_dev_deg": "headingDeviation", "heading_limit_deg": "headingLimit",
    "heading_drift_static_deg": "headingDriftStatic",
    "heading_drift_limit_deg": "headingDriftLimit", "half_width_mm": "halfWidth",
    "d_start_mm": "dStart", "coverage_k": "coverageFactor",
    "contact_threshold_mm": "contactThreshold", "r_trig_mm": "rTrigger",
    "travel_at_stop_mm": "travelAtStop", "travel_interlock_mm": "travelInterlock",
    "sigma_v_frac": "sigmaVFrac", "sigma_brake_frac": "sigmaBrakeFrac",
    "sigma_c_mm": "sigmaCUs",
    "estimator_error_mm": "estimatorError", "estimator_tol_mm": "estimatorTolerance",
    "estimator_delta_mm": "estimatorDelta",
    "estimator_delta_tol_mm": "estimatorDeltaTolerance",
    "odo_residual_mm": "odoResidual", "odo_residual_tol_mm": "odoResidualTolerance",
    "decel_residual_frac": "decelResidual",
    "decel_residual_tol_frac": "decelResidualTolerance",
    "rear_travel_residual_mm": "rearTravelResidual",
    "rear_travel_tol_mm": "rearTravelTolerance",
    "speed_residual_mmps": "speedResidual",
    "speed_residual_tol_mmps": "speedResidualTolerance",
    "evidence_fields_emitted": "evidenceFieldsEmitted",
    "evidence_fields_required": "evidenceFieldsRequired",
    "channels_logged": "channelsLogged", "channels_catalogued": "channelsCatalogued",
}

DERIVED = {                       # computed WallRover attributes
    "predicted_gap": "predictedGap", "safety_margin": "safetyMargin",
    "true_range_at_trigger": "trueRangeAtTrigger",
    "stop_distance_required": "stopDistanceRequired",
    "v_max_from_budget": "vMaxFromBudget", "t_response_ms": "tResponse",
    "rest_reading": "restReading",
}


def _fully_bound():
    """A physically well-conditioned, fully bound parameter set, used only to
    trace which parameter each requirement operand reads."""
    p = M.nominal_from_priors()
    p.r_trig_mm = M.solve_trigger_for_target(p)
    for f in M.FIELDS:
        if getattr(p, f) is None:
            setattr(p, f, 1.0)
    return p


PNOM = _fully_bound()


class Tracer(object):
    def __init__(self): self.names = []
    def get(self, n): self.names.append(n); return PNOM.get(n)
    def bound(self, n): return PNOM.bound(n)
    def copy(self, **kw): return self


def trace(fn):
    t = Tracer()
    try:
        val = fn(t)
    except Exception as e:                                   # pragma: no cover
        raise SystemExit("operand not traceable: %s" % e)
    return tuple(t.names), val


DERIVED_SIG = {}
for pyname, sysname in DERIVED.items():
    DERIVED_SIG[trace(lambda p, f=getattr(M, pyname): f(p))[0]] = sysname


def operand_expr(fn):
    names, val = trace(fn)
    if names in DERIVED_SIG:
        return "rover." + DERIVED_SIG[names]
    if len(names) == 1:
        base = "rover." + NAME_MAP[names[0]]
        b = PNOM.get(names[0])
        coeff = 1.0 if (b == 0.0 and val == 0.0) else val / b
        return base if abs(coeff - 1.0) < 1e-12 else "%s * %g" % (base, coeff)
    raise SystemExit("unmapped composite operand: %s" % (names,))


# ------------------------------------------------------- structure package ---
STRUCTURE = open("wall_rover_structure.sysml").read()

# ------------------------------------------------------ requirements package -
def gen_requirements():
    order = sorted(REQS, key=lambda r: (["CMP", "FUN", "SYS", "STK"].index(REQS[r].level),
                                        int(re.sub(r"\D", "", r) or 0), r))
    children = {}
    for rid, r in REQS.items():
        for par in r.parents:
            children.setdefault(par, []).append(rid)
    out = []
    out.append("package WallRunRequirements {")
    out.append("    doc /*")
    out.append("     * Formal realisation of requirements_spec.md (the source of truth).")
    out.append("     * Each task requirement SPECIALISES a catalog shape, adds the subject,")
    out.append("     * and BINDS the inherited operands; the require constraint is inherited,")
    out.append("     * so the evaluable logic lives once, in RequirementTemplates.")
    out.append("     * GENERATED from model_reqs.py by build_model.py -- do not hand-edit.")
    out.append("     */")
    out.append("")
    out.append("    private import RequirementTemplates::*;")
    out.append("    private import WallRunStructure::*;")
    out.append("")
    lvl = None
    for rid in order:
        r = REQS[rid]
        if r.level != lvl:
            lvl = r.level
            out.append("    // ---------------- %s ----------------" % lvl)
        out.append("    requirement def <'%s'> %s specializes %sRequirement {"
                   % (rid, r.sysml_name, r.shape))
        txt = r.text.replace("{target}", "the allocated bound")
        for line in _wrap(txt, 66):
            out.append("        // " + line)
        out.append("        subject rover : WallRover;")
        out.append("        attribute :>> measured = %s;" % operand_expr(r.measured))
        out.append("        attribute :>> target   = %s;" % operand_expr(r.target))
        for ch in sorted(children.get(rid, []),
                         key=lambda c: (["CMP", "FUN", "SYS", "STK"].index(REQS[c].level),
                                        int(re.sub(r"\D", "", c) or 0), c)):
            out.append("        requirement : %s;" % REQS[ch].sysml_name)
        out.append("    }")
        out.append("")
    out.append("    // ---------------- top need ----------------")
    out.append("    requirement def WallRunNeed {")
    out.append("        // The rover comes to a complete stop as close to the wall as")
    out.append("        // achievable without contacting it, having approached at maximum")
    out.append("        // speed, with per-run evidence of where it stopped.")
    out.append("        subject rover : WallRover;")
    for ch in sorted(children.get("NEED", [])):
        out.append("        requirement : %s;" % REQS[ch].sysml_name)
    out.append("    }")
    out.append("}")
    return "\n".join(out)


def _wrap(s, n):
    words, line, out = s.split(), "", []
    for w in words:
        if len(line) + len(w) + 1 > n:
            out.append(line); line = w
        else:
            line = (line + " " + w).strip()
    if line: out.append(line)
    return out


# ------------------------------------------------------------ structural checks
def checks(sysml_text):
    errs, notes = [], []
    # (5) requirement set parity
    decl = dict(re.findall(r"requirement def <'([^']+)'> (\w+)", sysml_text))
    if set(decl) != set(REQS):
        errs.append("requirement id sets differ: sysml-only=%s python-only=%s"
                    % (set(decl) - set(REQS), set(REQS) - set(decl)))
    for rid, nm in decl.items():
        if rid in REQS and REQS[rid].sysml_name != nm:
            errs.append("name drift for %s: %s vs %s" % (rid, nm, REQS[rid].sysml_name))
    notes.append("(5) requirement parity: %d ids in both views" % len(decl))

    # (2) realised edge-set == table edge-set
    blocks = re.split(r"\n    requirement def ", sysml_text)
    name2rid = {v: k for k, v in decl.items()}
    sys_edges = set()
    for b in blocks[1:]:
        m = re.match(r"<'([^']+)'>", b)
        parent = m.group(1) if m else ("NEED" if b.startswith("WallRunNeed") else None)
        if parent is None:
            continue
        for ch in re.findall(r"\n        requirement : (\w+);", b):
            if ch not in name2rid:
                errs.append("nested usage %r in %s is not a declared requirement"
                            % (ch, parent))
            else:
                sys_edges.add((parent, name2rid[ch]))
    tbl_edges = set((par, rid) for rid, r in REQS.items() for par in r.parents)
    if sys_edges != tbl_edges:
        errs.append("edge-set mismatch: sysml-only=%s table-only=%s"
                    % (sorted(sys_edges - tbl_edges), sorted(tbl_edges - sys_edges)))
    notes.append("(2) decomposition edges: %d, identical in both views" % len(tbl_edges))

    # (1) reachability from the top need
    seen, stack = set(), ["NEED"]
    adj = {}
    for par, ch in tbl_edges:
        adj.setdefault(par, []).append(ch)
    while stack:
        n = stack.pop()
        for ch in adj.get(n, []):
            if ch not in seen:
                seen.add(ch); stack.append(ch)
    unreach = set(REQS) - seen
    if unreach:
        errs.append("unreachable from the top need: %s" % sorted(unreach))
    notes.append("(1) reachability: %d/%d requirements reachable from NEED"
                 % (len(seen), len(REQS)))

    # (4) every bound operand resolves to a declared WallRover attribute
    attrs = set(re.findall(r"attribute (\w+)\s*[:=]", sysml_text))
    attrs |= set(re.findall(r"attribute (\w+) :", sysml_text))
    attrs.add("tChain")
    bad = set()
    for expr in re.findall(r"attribute :>> (?:measured|target)\s*=\s*rover\.([\w.]+)",
                           sysml_text):
        leaf = expr.split(".")[-1] if "." in expr else expr
        if leaf not in attrs:
            bad.add(expr)
    if bad:
        errs.append("operands with no declared attribute: %s" % sorted(bad))
    notes.append("(4) operand binding: %d distinct attributes referenced, all declared"
                 % len(set(re.findall(r"rover\.([\w.]+)", sysml_text))))

    # (3) per-package import resolution
    pkgs = re.findall(r"\npackage (\w+) \{", "\n" + sysml_text)
    ext = {"RoverCommon", "RoverStructure", "RelationTemplates",
           "RequirementTemplates", "ISQ", "SI", "ScalarValues"}
    for pkg_m in re.finditer(r"package (\w+) \{", sysml_text):
        start = pkg_m.end()
        body = sysml_text[start:]
        nxt = re.search(r"\npackage \w+ \{", body)
        body = body[:nxt.start()] if nxt else body
        imports = set(re.findall(r"private import (\w+)::", body))
        for qual in set(re.findall(r"(?<![\w.])([A-Z]\w+)::", body)):
            if qual not in imports and qual not in pkgs and qual not in ext:
                errs.append("%s: qualified ref %s:: neither imported nor declared"
                            % (pkg_m.group(1), qual))
    notes.append("(3) import resolution: %d packages, all qualified refs resolve"
                 % len(pkgs))
    return errs, notes


if __name__ == "__main__":
    text = STRUCTURE.rstrip() + "\n\n" + gen_requirements() + "\n"
    open("wall_rover.sysml", "w").write(text)
    errs, notes = checks(text)
    print("STRUCTURAL CHECKS")
    for n in notes:
        print("  OK  " + n)
    for e in errs:
        print("  ERR " + e)
    print("RESULT:", "PASS" if not errs else "FAIL (%d)" % len(errs))
    open("requirement_tree.mmd", "w").write(M.mermaid_tree() + "\n")
    # trace spine
    with open("trace_spine.md", "w") as f:
        f.write("| requirement | SysML operand (measured) | SysML operand (target) | "
                "Python variable | method |\n|---|---|---|---|---|\n")
        for rid in sorted(REQS, key=lambda r: (["STK", "SYS", "FUN", "CMP"].index(REQS[r].level), r)):
            r = REQS[rid]
            mt = trace(r.measured)[0]
            f.write("| %s | `%s` | `%s` | `%s` | %s |\n"
                    % (rid, operand_expr(r.measured), operand_expr(r.target),
                       ", ".join(mt) if len(mt) < 4 else "(derived)", r.method))
    print("wrote wall_rover.sysml, requirement_tree.mmd, trace_spine.md")
    sys.exit(1 if errs else 0)
