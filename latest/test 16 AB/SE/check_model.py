"""
Structural checks on wall_stop.sysml.  Grammar conformance is verified out of
band; these are the checks grammar cannot see, and they are the gate:

  1. every requirement reachable from the top need (STK-1 / WallRunNeed)
  2. the realised decomposition edge-set == the requirement tree in the spec
     (encoded in wallstop_model.REQUIREMENTS -- the SysML and the executable
     model must be two views of ONE model)
  3. per-package import resolution (every `private import P::*` names a package
     that exists; the package dependency graph is acyclic)
  4. every `rover.<path>` operand binding resolves to a declared attribute or
     part of WallRover (or of one of its parts)
  5. every requirement def specialises a RequirementTemplates shape OR is a pure
     decomposition node with at least one child (no unbound-operand orphans)
"""
import re
import sys
import wallstop_model as M

SRC = "wall_stop.sysml"
GENERIC = "rover_generic.sysml"
src = open(SRC).read()
gen = open(GENERIC).read()

fails, warns = [], []

# ----------------------------------------------------------------- parse ----
# requirement defs:  requirement def <'ID'> Name [specializes Shape] {
RE_REQDEF = re.compile(
    r"requirement\s+def\s+<'([A-Z]+-\d+)'>\s+(\w+)"
    r"(?:\s+specializes\s+(\w+))?\s*\{")
RE_USAGE = re.compile(r"^\s*requirement\s*:\s*(\w+)\s*;", re.M)
RE_BIND = re.compile(r"attribute\s*:>>\s*(\w+)\s*=\s*rover\.([\w\.]+)\s*;")
RE_PKG = re.compile(r"^package\s+(\w+)\s*\{", re.M)
RE_IMPORT = re.compile(r"private\s+import\s+([\w:]+)::\*\s*;")

# split the file into requirement-def bodies by brace matching
def bodies(text):
    out = {}
    for m in RE_REQDEF.finditer(text):
        rid, name, shape = m.group(1), m.group(2), m.group(3)
        i = text.index("{", m.end() - 1)
        depth, j = 0, i
        while j < len(text):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out[name] = dict(id=rid, name=name, shape=shape, body=text[i + 1:j])
    return out

reqs = bodies(src)
by_id = {r["id"]: r for r in reqs.values()}
name_to_id = {n: r["id"] for n, r in reqs.items()}

# ------------------------------------------------- 1/2 edge set + reachability
edges = set()
for name, r in reqs.items():
    for child in RE_USAGE.findall(r["body"]):
        if child not in name_to_id:
            fails.append("nested `requirement : %s` in %s names no requirement def"
                         % (child, name))
            continue
        edges.add((r["id"], name_to_id[child]))

spec_edges = set()
for rid, parents, kind, text in M.REQUIREMENTS:
    for p in parents:
        spec_edges.add((p, rid))

only_model = edges - spec_edges
only_spec = spec_edges - edges
if only_model:
    fails.append("edges in SysML but not in the spec tree: %s" % sorted(only_model))
if only_spec:
    fails.append("edges in the spec tree but not in SysML: %s" % sorted(only_spec))

# reachability from the top need
adj = {}
for a, b in edges:
    adj.setdefault(a, set()).add(b)
seen, stack = set(), ["STK-1"]
while stack:
    n = stack.pop()
    if n in seen:
        continue
    seen.add(n)
    stack.extend(adj.get(n, ()))
declared = set(by_id)
unreachable = declared - seen
if unreachable:
    fails.append("requirements NOT reachable from STK-1: %s" % sorted(unreachable))
spec_ids = {r[0] for r in M.REQUIREMENTS}
if spec_ids != declared:
    fails.append("id set differs: SysML-only %s ; spec-only %s"
                 % (sorted(declared - spec_ids), sorted(spec_ids - declared)))

# cycles
def has_cycle():
    color = {}
    def dfs(n):
        color[n] = 1
        for m2 in adj.get(n, ()):
            if color.get(m2) == 1:
                return True
            if color.get(m2, 0) == 0 and dfs(m2):
                return True
        color[n] = 2
        return False
    return any(dfs(n) for n in declared if color.get(n, 0) == 0)
if has_cycle():
    fails.append("requirement decomposition contains a cycle")

# ------------------------------------------------------- 3 import resolution
pkgs_local = set(RE_PKG.findall(src))
pkgs_gen = set(RE_PKG.findall(gen))
EXTERNAL = {"ISQ", "SI", "ScalarValues"}          # SysML v2 standard library
known = pkgs_local | pkgs_gen | EXTERNAL

pkg_spans = []
for m in RE_PKG.finditer(src):
    pkg_spans.append((m.group(1), m.start()))
pkg_spans.append(("<eof>", len(src)))
dep = {}
for (pname, start), (_, end) in zip(pkg_spans, pkg_spans[1:]):
    body = src[start:end]
    imports = RE_IMPORT.findall(body)
    dep[pname] = set()
    for imp in imports:
        head = imp.split("::")[0]
        if head not in known:
            fails.append("package %s imports unresolved package %s" % (pname, head))
        if head in pkgs_local:
            dep[pname].add(head)

# acyclic package graph
color = {}
def pdfs(n):
    color[n] = 1
    for m2 in dep.get(n, ()):
        if color.get(m2) == 1:
            return True
        if color.get(m2, 0) == 0 and pdfs(m2):
            return True
    color[n] = 2
    return False
if any(pdfs(n) for n in dep if color.get(n, 0) == 0):
    fails.append("package import graph contains a cycle")

# --------------------------------------------------- 4 binding resolution ----
# collect declared attributes/parts of WallRover and of its part types
def decls(text, defname):
    m = re.search(r"part\s+def\s+%s[^\{]*\{" % defname, text)
    if not m:
        return set(), {}
    i = text.index("{", m.end() - 1)
    depth, j = 0, i
    while j < len(text):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                break
        j += 1
    body = text[i + 1:j]
    attrs = set(re.findall(r"^\s*attribute\s+(\w+)\s*[:=]", body, re.M))
    attrs |= set(re.findall(r"^\s*attribute\s+(\w+)\s*:", body, re.M))
    parts = dict(re.findall(r"^\s*part\s+(\w+)\s*:\s*(\w+)\s*;", body, re.M))
    return attrs, parts

wr_attrs, wr_parts = decls(src, "WallRover")
# WallRover specializes Rover -> inherits Rover's parts/attributes
rv_attrs, rv_parts = decls(gen, "Rover")
wr_attrs |= rv_attrs
inh = dict(re.findall(r"^\s*part\s+(\w+)\s*:\s*(\w+)\s*\[\*\];", gen, re.M))
wr_parts.update({k: v for k, v in rv_parts.items()})
wr_parts.update(inh)

type_attrs = {}
for t in set(wr_parts.values()):
    a, _ = decls(src, t)
    b, _ = decls(gen, t)
    ta = a | b
    # specialisation chains used here
    m = re.search(r"part\s+def\s+%s\s+specializes\s+(\w+)" % t, src)
    if m:
        pa, _ = decls(gen, m.group(1))
        pb, _ = decls(src, m.group(1))
        ta |= pa | pb
    type_attrs[t] = ta

nbind = 0
for name, r in reqs.items():
    for operand, path in RE_BIND.findall(r["body"]):
        nbind += 1
        if operand not in ("measured", "target"):
            fails.append("%s binds unknown template operand `%s`" % (name, operand))
        segs = path.split(".")
        if len(segs) == 1:
            if segs[0] not in wr_attrs:
                fails.append("%s binds rover.%s -- not declared on WallRover"
                             % (name, path))
        elif len(segs) == 2:
            p, a = segs
            if p not in wr_parts:
                fails.append("%s binds rover.%s -- %s is not a part of WallRover"
                             % (name, path, p))
            elif a not in type_attrs.get(wr_parts[p], set()):
                fails.append("%s binds rover.%s -- %s has no attribute %s"
                             % (name, path, wr_parts[p], a))
        else:
            fails.append("%s binds a path deeper than the model: rover.%s"
                         % (name, path))

# ------------------------------------ 5 shape / operand completeness ---------
SHAPES = {"LowerBoundRequirement", "UpperBoundRequirement"}
for name, r in reqs.items():
    kids = RE_USAGE.findall(r["body"])
    binds = {o for o, _ in RE_BIND.findall(r["body"])}
    if r["shape"]:
        if r["shape"] not in SHAPES:
            fails.append("%s specialises unknown shape %s" % (name, r["shape"]))
        if binds != {"measured", "target"}:
            fails.append("%s specialises %s but binds operands %s"
                         % (name, r["shape"], sorted(binds) or "none"))
    else:
        if binds:
            fails.append("%s binds operands but specialises no shape" % name)
        if not kids:
            fails.append("%s is neither a bound requirement nor a decomposition"
                         % name)
    if "subject rover : WallRover;" not in r["body"]:
        fails.append("%s declares no WallRover subject" % name)

# ---- kind agreement between the two views
for rid, parents, kind, text in M.REQUIREMENTS:
    shape = by_id.get(rid, {}).get("shape")
    exp = {"lower": "LowerBoundRequirement", "upper": "UpperBoundRequirement"}
    if kind in exp and shape != exp[kind]:
        fails.append("%s: spec kind '%s' but SysML shape '%s'" % (rid, kind, shape))
    if kind == "parent" and shape is not None:
        fails.append("%s: spec says decomposition-only but SysML specialises %s"
                     % (rid, shape))

# --------------------------------------------------------------- report -----
print("wall_stop.sysml structural check")
print("  packages ...................... %d (%s)" % (len(pkgs_local), ", ".join(sorted(pkgs_local))))
print("  requirement defs .............. %d" % len(reqs))
print("  decomposition edges ........... %d" % len(edges))
print("  operand bindings resolved ..... %d" % nbind)
print("  reachable from STK-1 .......... %d / %d" % (len(seen & declared), len(declared)))
print("  edge-set == spec tree ......... %s" % ("YES" if edges == spec_edges else "NO"))
print()
if warns:
    for w in warns:
        print("  WARN  " + w)
if fails:
    for f in fails:
        print("  FAIL  " + f)
    print("\nRESULT: %d structural defect(s)" % len(fails))
    sys.exit(1)
print("RESULT: all structural checks pass")
