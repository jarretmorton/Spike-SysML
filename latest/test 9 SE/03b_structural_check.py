"""
structural_check.py -- stands in for the out-of-band grammar checker.

Verifies the three structural properties the model-strategy section names:
  (1) every requirement is reachable from the top need (WallRunNeed);
  (2) the realised decomposition edge-set (parsed from `requirement : X`
      usages in the SysML) matches the intended requirement tree;
  (3) per-package imports resolve to a package defined in the two source files.

Parses lightly with regex -- enough to certify structure, not to grammar-check.
"""
import re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
GENERIC = ROOT / "rover_generic.sysml"          # copied alongside for the check
TAILORED = ROOT / "WallRunModel.sysml"

# ---- intended requirement tree (from the requirements spec) ----
INTENDED = {
    "WallRunNeed": ["SYS1_NoContact", "SYS2_GapObjective", "SYS2M_MarginBridge",
                    "SYS3_MaxSpeed", "SYS4_CompleteStop", "SYS5_Straight",
                    "SYS6_TriggerInRange", "SYS7_FitsRunway"],
    "SYS1_NoContact": ["FUN_Sense", "FUN_Decide"],
    "SYS2_GapObjective": [],
    "SYS2M_MarginBridge": [],
    "SYS3_MaxSpeed": ["FUN_Drive"],
    "SYS4_CompleteStop": ["FUN_Brake"],
    "SYS5_Straight": ["FUN_Heading"],
    "SYS6_TriggerInRange": ["CMP_DST2_LowerRange", "CMP_DST2_UpperRange"],
    "SYS7_FitsRunway": [],
    "FUN_Sense": ["CMP_DST1_Staleness"],
    "FUN_Decide": ["CMP_LAT1_Latency"],
    "FUN_Drive": ["CMP_DRV1_MaxSpeed"],
    "FUN_Brake": ["CMP_DRV2_Brake", "CMP_IMU2_Accel"],
    "FUN_Heading": ["CMP_IMU1_Heading"],
    "CMP_DST1_Staleness": [], "CMP_DST2_LowerRange": [], "CMP_DST2_UpperRange": [],
    "CMP_DRV1_MaxSpeed": [], "CMP_DRV2_Brake": [], "CMP_IMU1_Heading": [],
    "CMP_IMU2_Accel": [], "CMP_LAT1_Latency": [],
}

def parse_realised(text):
    """Return {reqdef_name: [child usage names]} from the SysML source.

    Splits on `requirement def <name>` blocks (brace-matched) and collects the
    identifiers used in `requirement : Child;` usages inside each block.
    """
    edges = {}
    # find each 'requirement def [<'id'>] Name {' and brace-match its body
    for m in re.finditer(r"requirement\s+def\s+(?:<'[^']*'>\s+)?(\w+)\s*(?::>\s*[\w:]+\s*)?\{", text):
        name = m.group(1)
        i = m.end() - 1  # at the opening brace
        depth, j = 0, i
        while j < len(text):
            if text[j] == "{": depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0: break
            j += 1
        body = text[i+1:j]
        # child usages: 'requirement : Child'  (exclude the 'requirement def' lines)
        kids = re.findall(r"requirement\s*:\s*(\w+)", body)
        edges[name] = kids
    return edges

def parse_imports(text):
    return set(re.findall(r"import\s+([\w:]+)::\*", text))

def parse_packages(*texts):
    pkgs = set()
    for t in texts:
        pkgs |= set(re.findall(r"package\s+(\w+)\s*\{", t))
    return pkgs

def main():
    gen = GENERIC.read_text() if GENERIC.exists() else ""
    tai = TAILORED.read_text()

    # (2) edge-set match
    realised = parse_realised(tai)
    ok_edges = True
    print("== (2) EDGE-SET MATCH (realised vs intended) ==")
    for parent, kids in INTENDED.items():
        got = realised.get(parent, None)
        if got is None:
            print(f"  MISSING def: {parent}"); ok_edges = False; continue
        if sorted(got) != sorted(kids):
            print(f"  EDGE MISMATCH {parent}: intended {sorted(kids)} got {sorted(got)}")
            ok_edges = False
    # any realised def not in intended?
    for parent in realised:
        if parent not in INTENDED:
            print(f"  EXTRA def not in intended tree: {parent}"); ok_edges = False
    print("  edges OK" if ok_edges else "  edges FAILED")

    # (1) reachability from WallRunNeed
    print("== (1) REACHABILITY from WallRunNeed ==")
    seen, stack = set(), ["WallRunNeed"]
    while stack:
        n = stack.pop()
        if n in seen: continue
        seen.add(n)
        stack += INTENDED.get(n, [])
    all_nodes = set(INTENDED) | {c for v in INTENDED.values() for c in v}
    unreached = all_nodes - seen
    print(f"  nodes: {len(all_nodes)}, reachable: {len(seen)}")
    print("  all reachable" if not unreached else f"  UNREACHABLE: {unreached}")

    # (3) import resolution
    print("== (3) IMPORT RESOLUTION ==")
    pkgs = parse_packages(gen, tai) | {
        # standard-library packages assumed present (out-of-band)
        "ISQ", "SI", "ScalarValues"
    }
    imports = parse_imports(tai)
    ok_imp = True
    for imp in sorted(imports):
        head = imp.split("::")[0]
        status = "ok" if head in pkgs else "UNRESOLVED"
        if status != "ok": ok_imp = False
        print(f"  import {imp:26s} -> {status}")
    print("  imports OK" if ok_imp else "  imports FAILED")

    ok = ok_edges and not unreached and ok_imp
    print("\nSTRUCTURAL CHECK:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
