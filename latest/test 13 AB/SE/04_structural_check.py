#!/usr/bin/env python3
"""
structural_check.py -- the GATE structural checks, run on the emitted model text.

No SysML grammar checker runs in this loop, so two things stand in for one:
constructs are restricted to the validated set (enforced by the assembler), and
the structural properties a grammar checker could not see anyway are checked here.
Grammar conformance is verified out of band, after the run.

Checks performed (each fails loudly):
  1  requirement ID sets agree across the three views: authored spec dataset,
     wall_rover.sysml, wallstop_model.py REQUIREMENTS
  2  the realised decomposition edge-set (nested `requirement : X` usages) equals
     the authored requirement tree
  3  every requirement def is reachable from the need claimed by `satisfy`
  4  every requirement def declares a subject
  5  operand binding completeness: a requirement specialising a bound template
     binds BOTH operands, each to an attribute declared on the subject; and no
     requirement binds operands without specialising a template
  6  per-package import resolution: every `private import P::*` resolves to a
     package defined in the generic file, this file, or the SysML standard library
  7  parameter spine 1:1 in BOTH directions between the SysML attributes and the
     executable model's parameters / derived quantities
  8  template names referenced exist in RequirementTemplates
  9  short names are unique
 10  A3 audit: nothing that calibration must bind is carrying a value yet
"""

import importlib.util
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
STDLIB_PKGS = {"ISQ", "SI", "ScalarValues", "Real"}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


rd = load("requirements_data", HERE / "requirements_data.py")
wm = load("wallstop_model", HERE / "wallstop_model.py")

GEN = (HERE / "rover_generic.sysml").read_text()
TASK = (HERE / "wall_rover.sysml").read_text()

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))


# ---------------------------------------------------------------- parse ----
def strip_docs(text):
    return re.sub(r"doc\s*/\*.*?\*/", "", text, flags=re.S)


body = strip_docs(TASK)

req_defs = {}   # short name -> dict(name, template, subject, children, operands)
for m in re.finditer(r"requirement def <'([^']+)'>\s+(\w+)(\s+specializes\s+(\w+))?\s*\{", body):
    rid, nm, _, tmpl = m.groups()
    # capture the block by brace matching
    i = m.end() - 1
    depth, j = 0, i
    while j < len(body):
        if body[j] == "{":
            depth += 1
        elif body[j] == "}":
            depth -= 1
            if depth == 0:
                break
        j += 1
    block = body[i:j]
    req_defs[rid] = dict(
        sysml=nm, template=tmpl,
        subject=bool(re.search(r"subject\s+rover\s*:\s*WallRover\s*;", block)),
        children=re.findall(r"requirement\s*:\s*(\w+)\s*;", block),
        operands=dict(re.findall(r"attribute\s*:>>\s*(\w+)\s*=\s*rover\.(\w+)\s*;", block)),
    )

name2id = {v["sysml"]: k for k, v in req_defs.items()}
attrs = set(re.findall(r"^\s*attribute\s+(\w+)\s*:\s*\w+\s*;", body, flags=re.M))
gen_pkgs = set(re.findall(r"^package\s+(\w+)\s*\{", GEN, flags=re.M))
task_pkgs = set(re.findall(r"^package\s+(\w+)\s*\{", TASK, flags=re.M))
imports = set(re.findall(r"private import\s+([\w:]+?)::\*\s*;", body))
templates_avail = set(re.findall(r"requirement def\s+(\w+)\s*\{", GEN))
satisfied = re.findall(r"satisfy requirement\s*:\s*([\w:]+)\s*;", body)

# ---------------------------------------------------------------- 1 ----
spec_ids = {r.id for r in rd.REQS}
model_ids = set(wm.REQUIREMENTS)
check("1a spec IDs == SysML IDs", spec_ids == set(req_defs),
      f"spec-only={sorted(spec_ids - set(req_defs))} sysml-only={sorted(set(req_defs) - spec_ids)}")
check("1b spec IDs == executable-model IDs", spec_ids == model_ids,
      f"spec-only={sorted(spec_ids - model_ids)} model-only={sorted(model_ids - spec_ids)}")
check("1c requirement def names agree spec<->SysML",
      all(req_defs[r.id]["sysml"] == r.sysml for r in rd.REQS if r.id in req_defs))
check("1d requirement def names agree spec<->executable model",
      all(wm.REQUIREMENTS[r.id]["sysml"] == r.sysml for r in rd.REQS if r.id in wm.REQUIREMENTS))

# ---------------------------------------------------------------- 2 ----
authored_edges = {(r.parent, r.id) for r in rd.REQS if r.parent}
sysml_edges = {(pid, name2id[c]) for pid, d in req_defs.items() for c in d["children"]
               if c in name2id}
check("2 realised decomposition edge-set == authored tree", authored_edges == sysml_edges,
      f"missing={sorted(authored_edges - sysml_edges)} extra={sorted(sysml_edges - authored_edges)}")
model_edges = {(v["parent"], k) for k, v in wm.REQUIREMENTS.items() if v["parent"]}
check("2b executable-model edge-set == authored tree", authored_edges == model_edges,
      f"diff={sorted(authored_edges ^ model_edges)}")

# ---------------------------------------------------------------- 3 ----
roots = [s.split("::")[-1] for s in satisfied]
check("3a design claims exactly one top need with satisfy", len(satisfied) == 1, str(satisfied))
reach, stack = set(), [name2id[r] for r in roots if r in name2id]
while stack:
    cur = stack.pop()
    if cur in reach:
        continue
    reach.add(cur)
    stack += [name2id[c] for c in req_defs[cur]["children"] if c in name2id]
check("3b every requirement reachable from the claimed need", reach == set(req_defs),
      f"unreachable={sorted(set(req_defs) - reach)}")

# ---------------------------------------------------------------- 4 ----
check("4 every requirement def declares subject rover : WallRover",
      all(d["subject"] for d in req_defs.values()),
      f"missing={[k for k, d in req_defs.items() if not d['subject']]}")

# ---------------------------------------------------------------- 5 ----
bad_bind, bad_attr, orphan_ops = [], [], []
for rid, d in req_defs.items():
    if d["template"] in ("LowerBoundRequirement", "UpperBoundRequirement"):
        if set(d["operands"]) != {"measured", "target"}:
            bad_bind.append(rid)
        for a in d["operands"].values():
            if a not in attrs:
                bad_attr.append((rid, a))
    elif d["operands"]:
        orphan_ops.append(rid)
check("5a bound templates bind BOTH operands", not bad_bind, str(bad_bind))
check("5b every operand resolves to a declared subject attribute", not bad_attr, str(bad_attr))
check("5c no operands bound without specialising a template", not orphan_ops, str(orphan_ops))
n_lb = sum(1 for d in req_defs.values() if d["template"] == "LowerBoundRequirement")
n_ub = sum(1 for d in req_defs.values() if d["template"] == "UpperBoundRequirement")
hdr = re.search(r"LowerBoundRequirement\s+--\s+instantiated \((\d+) times\)", TASK)
hdr2 = re.search(r"UpperBoundRequirement\s+--\s+instantiated \((\d+) times\)", TASK)
spec_lb = sum(1 for r in rd.REQS if r.template == "LowerBoundRequirement")
spec_ub = sum(1 for r in rd.REQS if r.template == "UpperBoundRequirement")
check("5d template instantiation counts agree: header / SysML / spec",
      (int(hdr.group(1)), int(hdr2.group(1))) == (n_lb, n_ub) == (spec_lb, spec_ub),
      f"header=({hdr.group(1)},{hdr2.group(1)}) sysml=({n_lb},{n_ub}) spec=({spec_lb},{spec_ub})")

# ---------------------------------------------------------------- 6 ----
unresolved = {i for i in imports if i.split("::")[0] not in (gen_pkgs | task_pkgs | STDLIB_PKGS)}
check("6 every private import resolves", not unresolved, str(sorted(unresolved)))

# ---------------------------------------------------------------- 7 ----
spine_refs = {p.sysml_ref for p in wm.PARAMS.values()} | set(wm.DERIVED_SYSML)
declared = attrs
check("7a every executable-model parameter has a SysML attribute",
      spine_refs <= declared, f"missing in SysML={sorted(spine_refs - declared)}")
check("7b every SysML attribute maps to an executable-model quantity",
      declared <= spine_refs, f"unmapped in SysML={sorted(declared - spine_refs)}")

# ---------------------------------------------------------------- 8 ----
used_tmpl = {d["template"] for d in req_defs.values() if d["template"]}
check("8 referenced templates exist in RequirementTemplates", used_tmpl <= templates_avail,
      f"unknown={sorted(used_tmpl - templates_avail)}")

# ---------------------------------------------------------------- 9 ----
check("9 short names unique", len(name2id) == len(req_defs))

# --------------------------------------------------------------- 10 ----
should_be_free = [p.name for p in wm.PARAMS.values()
                  if p.kind == "free" and p.bound and p.tier == "T2-prior"]
check("10 A3 audit: nothing bound from a prior tier", not should_be_free, str(should_be_free))
n_free = sum(1 for p in wm.PARAMS.values() if p.kind in ("free", "environment") and not p.bound)

# ---------------------------------------------------------------- report --
w = max(len(n) for n, _, _ in results)
print("=" * (w + 30))
print("STRUCTURAL CHECK -- wall_rover.sysml / requirements_data.py / wallstop_model.py")
print("=" * (w + 30))
fails = 0
for n, ok, detail in results:
    print(f"  {n:<{w}}  {'PASS' if ok else 'FAIL'}" + (f"   {detail}" if not ok else ""))
    fails += (not ok)
print("-" * (w + 30))
print(f"  {len(req_defs)} requirement defs, {len(authored_edges)} decomposition edges, "
      f"{len(declared)} spine attributes, {n_free} parameters still free")
print(f"  {len(results) - fails}/{len(results)} checks pass")
sys.exit(1 if fails else 0)
