#!/usr/bin/env python3
"""
03_structural_check.py -- the gate the grammar cannot see (MODEL STRATEGY).

Parses wallrun_model.sysml and certifies three things about the formal roll-up:
  1. reachability : every requirement def is reachable from WallRunNeed
  2. edge-set     : the nested `requirement : Child` decomposition edges equal
                    the requirement-tree edges in the spec (§7), exactly
  3. resolution   : every referenced name resolves --
                    - each nested child is a defined requirement def
                    - each `specializes T` is an imported requirement template
                    - each operand binding `rover.attr` names a WallRover attribute
                    - the subject type WallRover is defined
Grammar conformance itself is verified out of band; this is the structural gate.
"""
import re, sys
from pathlib import Path

SRC = Path("/home/claude/record/wallrun_model.sysml").read_text()

# ---- strip line comments and doc/*...*/ blocks so they don't confuse parsing ----
def strip_comments(s: str) -> str:
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)   # block + doc comments
    s = re.sub(r"//[^\n]*", " ", s)                # line comments
    return s

CODE = strip_comments(SRC)

# ---- brace-matched body extraction ----
def bodies(code, keyword):
    """Yield (name, body_text) for each `keyword NAME ... { ... }` at any depth."""
    out = []
    for m in re.finditer(rf"\b{keyword}\s+(?:def\s+)?([A-Za-z_][\w]*)", code):
        name = m.group(1)
        brace = code.find("{", m.end())
        if brace == -1:
            continue
        depth, i = 0, brace
        while i < len(code):
            if code[i] == "{":
                depth += 1
            elif code[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        out.append((name, code[brace + 1:i]))
    return out

# ---- collect requirement defs, their headers (decl -> `{`) and bodies ----
req_defs = {}     # name -> body
req_headers = {}  # name -> header text between `requirement def NAME` and `{`
for m in re.finditer(r"\brequirement\s+def\s+([A-Za-z_]\w*)", CODE):
    name = m.group(1)
    brace = CODE.find("{", m.end())
    if brace == -1:
        continue
    header = CODE[m.end():brace]
    depth, i = 0, brace
    while i < len(CODE):
        if CODE[i] == "{":
            depth += 1
        elif CODE[i] == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    req_defs[name] = CODE[brace + 1:i]
    req_headers[name] = header

# ---- collect WallRover attributes and the part def body ----
part_bodies = dict(bodies(CODE, "part"))
wallrover_body = part_bodies.get("WallRover", "")
wallrover_attrs = set(re.findall(r"\battribute\s+(?:[:>]+\s*)?([A-Za-z_]\w*)\s*:", wallrover_body))
# also inherited-redefined parts (motors/rangers/floor) and inherited imu/latency
wallrover_parts = set(re.findall(r"\bpart\s+(?:[:>]+\s*)?([A-Za-z_]\w*)\s*:", wallrover_body))

# ---- decomposition edges: nested `requirement : Child` inside each def body ----
edges = set()
child_refs = {}
for name, body in req_defs.items():
    kids = re.findall(r"\brequirement\s*:\s*([A-Za-z_]\w*)", body)
    child_refs[name] = kids
    for k in kids:
        edges.add((name, k))

# ---- operand bindings and specializes, per def ----
specializes = {}
operand_refs = {}
for name, body in req_defs.items():
    sp = re.findall(r"\bspecializes\s+([A-Za-z_]\w*)", req_headers[name])
    specializes[name] = sp
    ops = re.findall(r":>>\s*(?:measured|target)\s*=\s*rover\.([A-Za-z_]\w*)", body)
    operand_refs[name] = ops

TEMPLATES = {"LowerBoundRequirement", "UpperBoundRequirement"}

# ============================ CHECK 1: reachability =========================
ROOT = "WallRunNeed"
adj = {}
for a, b in edges:
    adj.setdefault(a, []).append(b)
seen, stack = set(), [ROOT]
while stack:
    n = stack.pop()
    if n in seen:
        continue
    seen.add(n)
    stack.extend(adj.get(n, []))
unreached = set(req_defs) - seen
reach_ok = not unreached

# ============================ CHECK 2: edge-set =============================
# expected tree from the requirements spec §7
EXPECTED = {
    ("WallRunNeed", "NoContact"), ("WallRunNeed", "MaxSpeed"),
    ("WallRunNeed", "MinGap"), ("WallRunNeed", "FullStop"),
    ("WallRunNeed", "StraightTravel"),
    ("NoContact", "MinGapMargin"), ("NoContact", "SenseDistance"),
    ("NoContact", "DecideStop"),
    ("MaxSpeed", "DriveMax"),
    ("MinGapMargin", "StoppingCharacterized"), ("MinGapMargin", "EstimateGap"),
    ("FullStop", "MotorToRest"),
    ("StraightTravel", "MaintainHeading"),
    ("SenseDistance", "SensorResidual"), ("SenseDistance", "SensorMinRange"),
    ("DecideStop", "LatencyChain"),
    ("DriveMax", "MotorAtMax"),
    ("StoppingCharacterized", "GroundConstant"),
    ("MaintainHeading", "HeadingBounded"),
}
missing = EXPECTED - edges     # in spec, not in model
extra = edges - EXPECTED       # in model, not in spec
edge_ok = not missing and not extra

# ============================ CHECK 3: resolution ==========================
res_errors = []
# 3a: every nested child is a defined requirement def
for a, b in edges:
    if b not in req_defs:
        res_errors.append(f"child '{b}' (in {a}) is not a defined requirement def")
# 3b: every specializes is a known template
for name, sps in specializes.items():
    for s in sps:
        if s not in TEMPLATES:
            res_errors.append(f"{name} specializes unknown template '{s}'")
# 3c: every operand binding names a WallRover attribute
for name, ops in operand_refs.items():
    for a in ops:
        if a not in wallrover_attrs:
            res_errors.append(f"{name} binds rover.{a} -- not a WallRover attribute")
# 3d: WallRover part def exists
if "WallRover" not in part_bodies:
    res_errors.append("WallRover part def not found")
# 3e: bound requirements must actually bind BOTH measured and target
for name, body in req_defs.items():
    if specializes.get(name):   # specializes a bound template
        has_m = bool(re.search(r":>>\s*measured\s*=", body))
        has_t = bool(re.search(r":>>\s*target\s*=", body))
        if not (has_m and has_t):
            res_errors.append(f"{name} specializes a bound template but does not bind both operands")
res_ok = not res_errors

# =============================== REPORT =====================================
print("=" * 78)
print("STRUCTURAL CHECK -- wallrun_model.sysml")
print("=" * 78)
print(f"requirement defs found ({len(req_defs)}): {', '.join(sorted(req_defs))}")
print(f"WallRover attributes ({len(wallrover_attrs)}): {', '.join(sorted(wallrover_attrs))}")
print(f"WallRover parts: {', '.join(sorted(wallrover_parts))}")
print(f"decomposition edges: {len(edges)}")
print("-" * 78)

print(f"[1] reachability from {ROOT}: {'PASS' if reach_ok else 'FAIL'}")
if not reach_ok:
    print(f"    unreachable: {sorted(unreached)}")

print(f"[2] edge-set == spec tree: {'PASS' if edge_ok else 'FAIL'}")
if missing:
    print(f"    missing (spec, not model): {sorted(missing)}")
if extra:
    print(f"    extra (model, not spec):   {sorted(extra)}")

print(f"[3] name/import resolution: {'PASS' if res_ok else 'FAIL'}")
for e in res_errors:
    print(f"    - {e}")

# leaf constraint coverage vs the Python evaluate() keys (cross-view agreement)
BOUND = {n for n, s in specializes.items() if s}
print("-" * 78)
print(f"bound (constraint-bearing) requirements ({len(BOUND)}): {', '.join(sorted(BOUND))}")
AGG = sorted(set(req_defs) - BOUND)
print(f"aggregator/graded (no constraint): {', '.join(AGG)}")

# ---- CHECK 4: SysML roll-up == Python evaluate() pass/fail set -------------
# map SysML requirement-def name -> requirement ID used in wallrun_model.py
NAME_TO_ID = {
    "NoContact": "SYS-1", "MaxSpeed": "SYS-2", "MinGapMargin": "SYS-3b",
    "FullStop": "SYS-4", "StraightTravel": "SYS-5",
    "MotorAtMax": "CMP-1", "MotorToRest": "CMP-2", "SensorResidual": "CMP-3",
    "SensorMinRange": "CMP-4", "LatencyChain": "CMP-5", "HeadingBounded": "CMP-6",
    "GroundConstant": "CMP-7",
}
sysml_ids = {NAME_TO_ID[n] for n in BOUND if n in NAME_TO_ID}
unmapped = BOUND - set(NAME_TO_ID)
xview_ok = True
try:
    import wallrun_model as wm
    ev = wm.evaluate(wm._nominal_params())
    py_passfail = {k for k, v in ev.items()
                   if k not in ("ROLLUP",) and isinstance(v, dict)
                   and v.get("verdict") in ("PASS", "FAIL")}
    only_sysml = sysml_ids - py_passfail
    only_py = py_passfail - sysml_ids
    xview_ok = not only_sysml and not only_py and not unmapped
    print("-" * 78)
    print(f"[4] SysML bound-set == Python evaluate() pass/fail set: {'PASS' if xview_ok else 'FAIL'}")
    if unmapped:
        print(f"    bound SysML reqs with no ID mapping: {sorted(unmapped)}")
    if only_sysml:
        print(f"    in SysML, not Python: {sorted(only_sysml)}")
    if only_py:
        print(f"    in Python, not SysML: {sorted(only_py)}")
    if xview_ok:
        print(f"    both views evaluate exactly: {', '.join(sorted(sysml_ids))}")
        print(f"    (Python SYS-3 is graded/N-A; not a pass/fail node in either view)")
except Exception as e:
    xview_ok = False
    print(f"[4] cross-view check ERROR: {e}")

ok = reach_ok and edge_ok and res_ok and xview_ok
print("=" * 78)
print("STRUCTURAL GATE:", "PASS" if ok else "FAIL")
print("=" * 78)
sys.exit(0 if ok else 1)
