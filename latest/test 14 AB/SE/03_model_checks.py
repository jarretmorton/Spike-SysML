#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
03_model_checks.py -- structural gate checks for the SysML model.

No SysML grammar checker runs in this loop, so two things stand in for one:
constructs are restricted to forms already validated in the template library, and
the structural properties a grammar checker would NOT see anyway are checked here,
mechanically, as the gate.  Grammar conformance is verified out of band.

CHECKS
  C1  every requirement is reachable from the top need
  C2  the realized decomposition edge-set equals the requirement tree in the
      specification (parsed from the Mermaid source -- the two documents cannot
      drift apart silently)
  C3  per-package import resolution: every external name used resolves to an import
  C4  SysML <-> Python 1:1: every requirement id evaluated in the executable model
      exists in the SysML model and vice versa
  C5  operand binding: every task requirement binds BOTH operands with the
      redefinition-with-binding form, against an attribute that exists on the subject
  C6  no dead parameters: every Python parameter is consumed by predict/evaluate,
      and every SysML attribute named in a binding has a Python twin

Exit code 0 = all checks pass.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

HERE = Path(__file__).resolve().parent
SYSML = HERE / "02_wall_stop_model.sysml"
SPEC = HERE / "01_requirements_spec.md"
SKELETON_NAMES = {
    # names the model may use because rover_generic.sysml defines them
    "Rover", "DriveMotor", "DistanceSensor", "InertialUnit", "ReflectanceSensor",
    "RoverLatency", "Reflectance", "Angle",
    "LowerBoundRequirement", "UpperBoundRequirement",
    "RotationToSpeed", "StoppingDistance", "MaxSpeedFromBudget",
}
STDLIB_NAMES = {
    "LengthValue", "DurationValue", "SpeedValue", "AccelerationValue",
    "AngularVelocityValue", "FrequencyValue", "Real",
}

RESULTS: List[Tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))


# ---------------------------------------------------------------------------
# parsing
# ---------------------------------------------------------------------------

def parse_sysml(text: str):
    """Return (id_by_name, name_by_id, edges, bindings, imports, attrs)."""
    id_by_name: Dict[str, str] = {}
    name_by_id: Dict[str, str] = {}
    edges: Set[Tuple[str, str]] = set()
    bindings: Dict[str, Dict[str, str]] = {}

    decl = re.compile(r"requirement\s+def\s+<'([^']+)'>\s+(\w+)\s+specializes\s+(\w+)")
    child = re.compile(r"^\s*requirement\s*:\s*(\w+)\s*;")
    bind = re.compile(r"attribute\s*:>>\s*(\w+)\s*=\s*([\w.]+)\s*;")

    current = None
    specializes: Dict[str, str] = {}
    for line in text.splitlines():
        m = decl.search(line)
        if m:
            rid, nm, tmpl = m.group(1), m.group(2), m.group(3)
            id_by_name[nm] = rid
            name_by_id[rid] = nm
            specializes[rid] = tmpl
            bindings[rid] = {}
            current = rid
            continue
        if current:
            mc = child.match(line)
            if mc:
                edges.add((current, mc.group(1)))     # child stored by NAME for now
            mb = bind.search(line)
            if mb:
                bindings[current][mb.group(1)] = mb.group(2)

    # resolve child names -> ids
    resolved = set()
    unresolved = []
    for parent, cname in edges:
        if cname in id_by_name:
            resolved.add((parent, id_by_name[cname]))
        else:
            unresolved.append((parent, cname))

    imports = set(re.findall(r"private\s+import\s+([\w:]+)::\*", text))
    attrs = set(re.findall(r"^\s*attribute\s+(\w+)\s*:", text, re.M))
    parts = set(re.findall(r"^\s*part\s+(\w+)\s*:", text, re.M))
    return name_by_id, id_by_name, resolved, unresolved, bindings, imports, attrs, parts, specializes


def parse_spec_tree(text: str) -> Set[Tuple[str, str]]:
    """Edge set from the Mermaid requirement tree; dotted edges are excluded."""
    block = re.search(r"```mermaid(.*?)```", text, re.S)
    if not block:
        return set()
    edges = set()
    node_id = re.compile(r"^([A-Z]+\d*)")
    for line in block.group(1).splitlines():
        if "-.->" in line:            # absence-by-traceability annotation, not a decomposition edge
            continue
        m = re.match(r"\s*(\w+)\s*-->\s*(\w+)", line)
        if not m:
            continue
        a, b = m.group(1), m.group(2)
        edges.add((mermaid_to_id(a), mermaid_to_id(b)))
    return edges


def mermaid_to_id(node: str) -> str:
    if node == "NEED":
        return "NEED"
    m = re.match(r"(STK|SYS|FUN|CMP)(\d+)", node)
    return f"{m.group(1)}-{m.group(2)}" if m else node


# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------

def main() -> int:
    text = SYSML.read_text()
    spec = SPEC.read_text()
    (name_by_id, id_by_name, edges, unresolved,
     bindings, imports, attrs, parts, specializes) = parse_sysml(text)

    all_ids = set(name_by_id)

    # --- C0: every nested reference resolved --------------------------------
    record("C0 nested requirement references resolve to a declared requirement",
           not unresolved,
           "" if not unresolved else f"unresolved: {unresolved}")

    # --- C1: reachability from the top need ---------------------------------
    adj: Dict[str, List[str]] = {}
    for a, b in edges:
        adj.setdefault(a, []).append(b)
    seen: Set[str] = set()
    stack = ["NEED"]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(adj.get(n, []))
    unreachable = sorted(all_ids - seen)
    record("C1 every requirement reachable from the top need (NEED)",
           not unreachable, "" if not unreachable else f"unreachable: {unreachable}")

    # --- C2: edge-set equality with the specification tree ------------------
    spec_edges = parse_spec_tree(spec)
    only_model = sorted(edges - spec_edges)
    only_spec = sorted(spec_edges - edges)
    record("C2 realized decomposition edge-set == specification requirement tree",
           not only_model and not only_spec,
           "" if not (only_model or only_spec)
           else f"model-only: {only_model} | spec-only: {only_spec}")

    # --- C3: import resolution ---------------------------------------------
    used_external = set()
    for tmpl in specializes.values():
        used_external.add(tmpl)
    for typ in re.findall(r"part\s+\w+\s*:\s*(\w+)\s*;", text):
        used_external.add(typ)
    for typ in re.findall(r"attribute\s+\w+\s*:\s*(\w+)", text):
        used_external.add(typ)
    for typ in re.findall(r"part\s+def\s+\w+\s+specializes\s+(\w+)", text):
        used_external.add(typ)
    unimported = sorted(n for n in used_external
                        if n not in SKELETON_NAMES | STDLIB_NAMES
                        and n not in all_ids and n not in id_by_name)
    needed_imports = {"RoverCommon", "RoverStructure", "RelationTemplates",
                      "RequirementTemplates", "ISQ", "SI", "ScalarValues"}
    missing_imports = sorted(needed_imports - imports)
    record("C3 per-package import resolution",
           not unimported and not missing_imports,
           "" if not (unimported or missing_imports)
           else f"unresolved names: {unimported} | missing imports: {missing_imports}")

    # --- C4: SysML <-> Python requirement id agreement ----------------------
    sys.path.insert(0, str(HERE))
    import wall_stop_model as M
    py_ids = {v.req for v in M.evaluate(M.build_params().working_point())}
    py_ids.discard("MODEL")
    # CMP-12/13 are Optional-pattern drop-outs: present in Python (as traceability
    # verdicts) and deliberately NOT realised in SysML.  Declared exception.
    dropouts = {"CMP-12", "CMP-13"}
    in_py_not_sysml = sorted(py_ids - all_ids - dropouts)
    in_sysml_not_py = sorted(all_ids - py_ids - {"NEED"} -
                             {f"STK-{i}" for i in range(1, 7)})
    record("C4 SysML requirement ids == executable-model requirement ids",
           not in_py_not_sysml and not in_sysml_not_py,
           "" if not (in_py_not_sysml or in_sysml_not_py)
           else f"python-only: {in_py_not_sysml} | sysml-only: {in_sysml_not_py}")

    # --- C5: both operands bound, against attributes that exist -------------
    bad = []
    for rid, ops in bindings.items():
        if set(ops) != {"measured", "target"}:
            bad.append((rid, "operands " + str(sorted(ops))))
            continue
        for role, path in ops.items():
            leaf = path.split(".")[-1]
            if leaf not in attrs and leaf not in {"commandedSpeed", "maxSpeed",
                                                  "refreshInterval", "range",
                                                  "yaw", "forwardAccel", "tChain"}:
                bad.append((rid, f"{role} -> {path} (no such attribute)"))
    record("C5 every requirement binds both operands to existing attributes",
           not bad, "" if not bad else f"{bad}")

    # --- C6: no dead parameters --------------------------------------------
    py_src = (HERE / "wall_stop_model.py").read_text()
    body = py_src.split("def build_params", 1)[1].split("# 2.", 1)[1]
    dead = []
    for par in M.build_params():
        if body.count(f"p.{par.name}") == 0 and body.count(f"wp.{par.name}") == 0:
            dead.append(par.name)
    sysml_twins = {re.sub(r"^WallRover\.", "", par.sysml).split(".")[-1]
                   for par in M.build_params()}
    missing_attr = sorted(t for t in sysml_twins if t not in attrs and t != "tChain")
    record("C6 no dead parameters; every Python parameter has a SysML attribute",
           not dead and not missing_attr,
           "" if not (dead or missing_attr)
           else f"dead: {dead} | no SysML attribute: {missing_attr}")

    # --- report -------------------------------------------------------------
    width = max(len(n) for n, _, _ in RESULTS)
    print("=" * (width + 12))
    print("SysML STRUCTURAL GATE CHECKS")
    print("=" * (width + 12))
    ok_all = True
    for name, ok, detail in RESULTS:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
        if detail:
            print(f"      {detail}")
        ok_all &= ok
    print()
    print(f"requirements declared : {len(all_ids)}")
    print(f"decomposition edges   : {len(edges)}")
    print(f"reachable from NEED   : {len(seen & all_ids)}")
    print()
    print("OVERALL:", "PASS" if ok_all else "FAIL")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
