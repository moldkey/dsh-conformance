#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DSH Conformance Submission Validator (DSHIO/T 37)

Checks that a submission is COMPLETE and INTERNALLY CONSISTENT.
It does NOT check that the result is true. The submitter is responsible.

Usage:
    python3 validate.py                      # check all of results/
    python3 validate.py results/v0.2.2-rc.1/dsh-pet
    python3 validate.py --json               # machine-readable output
    python3 validate.py --changed <path>...  # check only these paths (CI)

Exit code: 0 = all passed, 1 = at least one failed
"""
import json
import os
import re
import sys

REQUIRED_STAGES = ["static", "install", "list", "config", "boot"]
PLUGIN_VERDICTS = [
    "pass",
    "install_failed",
    "config_failed",
    "installs_but_not_registered",
    "boot_failed",
]
FINGERPRINT_PARTS = ["dsh", "img", "node", "pnpm", "mem", "cpu"]
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
VER_RE = re.compile(r"^v\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
TESTER_REQUIRED = ["name", "url", "scope", "environment", "conflicts", "declaration"]
CONFLICT_REQUIRED = ["develops_plugins", "paid_by_author", "result_dependent_fees"]

# Supported baseline versions (current + 2 prior). Update when DSH releases.
SUPPORTED_BASELINES = {
    "v0.2.2-rc.1",
}


class Result:
    def __init__(self, path):
        self.path = path
        self.checks = []
        self.files = set()

    def ok(self, no, name, detail=""):
        self.checks.append((no, True, name, detail))

    def fail(self, no, name, detail=""):
        self.checks.append((no, False, name, detail))

    @property
    def passed(self):
        return all(c[1] for c in self.checks) and bool(self.checks)


def _read_yaml_simple(text):
    """极简 YAML 解析（只支持提交格式用到的子集）

    不引入 PyYAML 依赖，保证 Actions 里零安装即可运行。
    支持：key: value、嵌套缩进、列表 [a, b]、多行 >。
    """
    out = {}
    stack = [(0, out)]
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        raw = lines[i]
        i += 1
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()

        # 多行块 >
        if line.endswith(">") and ":" in line:
            key = line.split(":", 1)[0].strip()
            buf = []
            while i < len(lines):
                nxt = lines[i]
                if nxt.strip() and (len(nxt) - len(nxt.lstrip())) <= indent:
                    break
                buf.append(nxt.strip())
                i += 1
            while len(stack) > 1 and stack[-1][0] >= indent:
                stack.pop()
            stack[-1][1][key] = " ".join(x for x in buf if x)
            continue

        while len(stack) > 1 and stack[-1][0] > indent:
            stack.pop()
        if ":" not in line:
            # 列表项，忽略（简化处理）
            continue
        key, rest = line.split(":", 1)
        key = key.strip()
        rest = rest.strip()

        parent = stack[-1][1]
        if rest == "":
            child = {}
            parent[key] = child
            stack.append((indent + 1, child))
        else:
            if rest.startswith("[") and rest.endswith("]"):
                parent[key] = [x.strip() for x in rest[1:-1].split(",") if x.strip()]
            elif rest.lower() in ("true", "false"):
                parent[key] = rest.lower() == "true"
            elif (rest.startswith('"') and rest.endswith('"')) or \
                 (rest.startswith("'") and rest.endswith("'")):
                parent[key] = rest[1:-1]
            else:
                parent[key] = rest
    return out


def validate_dir(d):
    """Validate one submission directory. Returns Result."""
    r = Result(d)
    rel = d.replace("\\", "/").rstrip("/")

    # ── 1. 目录结构 results/v<ver>/<slug> ──
    parts = rel.split("/")
    if len(parts) < 3 or parts[-3] != "results":
        r.fail(1, "Directory is results/v<version>/<slug>/",
               "got: %s" % rel)
        return r
    ver_dir, slug = parts[-2], parts[-1]
    if not VER_RE.match(ver_dir):
        r.fail(1, "Version directory format",
               "%r is not v<major>.<minor>.<patch>[-pre]" % ver_dir)
    if not SLUG_RE.match(slug):
        r.fail(1, "Slug format",
               "%r must match [a-z0-9][a-z0-9._-]*" % slug)
    if all(c[1] for c in r.checks) or not r.checks:
        r.ok(1, "Directory structure", rel)

    # ── 2. 文件齐全 ──
    names = set(os.listdir(d)) if os.path.isdir(d) else set()
    r.files = names
    need = {"README.md", "result.json", "TESTER.yaml"}
    missing = need - names
    extra = names - need
    if missing:
        r.fail(2, "Required files present", "missing: " + ", ".join(sorted(missing)))
    else:
        r.ok(2, "Required files present")

    # ── 12. 无多余文件 ──
    if extra:
        r.fail(12, "No extra files", "extra: " + ", ".join(sorted(extra)))
    else:
        r.ok(12, "No extra files")

    # ── 3. result.json 合法 ──
    res = None
    p = os.path.join(d, "result.json")
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                res = json.load(f)
            r.ok(3, "result.json is valid JSON")
        except Exception as e:
            r.fail(3, "result.json is valid JSON", str(e)[:120])
    else:
        r.fail(3, "result.json is valid JSON", "file missing")

    if not isinstance(res, dict):
        return r

    # ── 11. 基准版本受支持 ──
    base = res.get("baseline_dsh") or ""
    want = ver_dir[1:] if ver_dir.startswith("v") else ver_dir
    if base != want:
        r.fail(11, "baseline_dsh matches directory",
               "dir=%r json=%r" % (ver_dir, base))
    elif ("v" + base) not in SUPPORTED_BASELINES:
        r.fail(11, "Baseline version is supported",
               "%r not in %s" % (base, sorted(SUPPORTED_BASELINES)))
    else:
        r.ok(11, "Baseline version is supported", base)

    # ── 4. 环境指纹 ──
    fp = res.get("fingerprint") or ""
    if not fp:
        r.fail(4, "Environment fingerprint", "missing")
    else:
        missing_parts = [k for k in FINGERPRINT_PARTS if (k + "=") not in fp]
        if missing_parts:
            r.fail(4, "Environment fingerprint",
                   "missing parts: " + ", ".join(missing_parts))
        else:
            r.ok(4, "Environment fingerprint", fp[:60] + ("…" if len(fp) > 60 else ""))

    # ── 5. 五阶段齐全 ──
    stages = res.get("stages") or {}
    absent = [s for s in REQUIRED_STAGES if s not in stages]
    if absent:
        r.fail(5, "All stages present", "missing: " + ", ".join(absent))
    else:
        r.ok(5, "All stages present")

    # ── 6. 无失败阶段 ──
    verdict = res.get("verdict") or ""
    if verdict not in PLUGIN_VERDICTS:
        r.fail(6, "Verdict is a known value", "got %r" % verdict)
    elif verdict != "pass":
        r.fail(6, "No failed stage",
               "verdict is %r — a non-passing result may be submitted, "
               "but must be marked; see SUBMISSION-FORMAT.md" % verdict)
    else:
        r.ok(6, "No failed stage", "pass")

    # ── 7. 重复运行 ──
    rep = res.get("repeat") or {}
    if not rep:
        r.fail(7, "Repeat run recorded", "missing repeat block")
    elif int(rep.get("count") or 0) < 2:
        r.fail(7, "Repeat run recorded",
               "count=%s, DSHIO/T 10 §7.4 requires 2" % rep.get("count"))
    elif not rep.get("consistent"):
        r.fail(7, "Repeat run consistent",
               "verdicts=%s" % rep.get("verdicts"))
    else:
        r.ok(7, "Repeat run consistent", "count=%s" % rep.get("count"))

    # ── 8/9. TESTER.yaml ──
    tp = os.path.join(d, "TESTER.yaml")
    tester = None
    if os.path.exists(tp):
        try:
            with open(tp, encoding="utf-8") as f:
                tester = _read_yaml_simple(f.read())
        except Exception as e:
            r.fail(8, "TESTER.yaml is readable", str(e)[:120])

    if isinstance(tester, dict):
        miss = [k for k in TESTER_REQUIRED if not tester.get(k)]
        if miss:
            r.fail(8, "TESTER.yaml required fields", "missing: " + ", ".join(miss))
        else:
            r.ok(8, "TESTER.yaml required fields")

        conf = tester.get("conflicts")
        if not isinstance(conf, dict):
            r.fail(9, "Conflict of interest declared", "conflicts block missing or invalid")
        else:
            cmiss = [k for k in CONFLICT_REQUIRED if k not in conf]
            if cmiss:
                r.fail(9, "Conflict of interest declared",
                       "missing keys: " + ", ".join(cmiss))
            else:
                r.ok(9, "Conflict of interest declared",
                     "develops_plugins=%s" % conf.get("develops_plugins"))
    elif not any(c[0] == 8 and not c[1] for c in r.checks):
        r.fail(8, "TESTER.yaml required fields", "file missing")

    # ── 10. README 说明复现 ──
    rp = os.path.join(d, "README.md")
    if os.path.exists(rp):
        body = open(rp, encoding="utf-8", errors="ignore").read()
        low = body.lower()
        body_low = body.lower()
        hints = sum(1 for k in ("dsh ", "command", "fingerprint", "格式",
                                "env", "install", "profile")
                    if k.lower() in body_low)
        if len(body.strip()) < 80:
            r.fail(10, "README explains reproduction", "too short")
        elif hints < 2:
            r.fail(10, "README explains reproduction",
                   "does not mention commands or environment")
        else:
            r.ok(10, "README explains reproduction")
    else:
        r.fail(10, "README explains reproduction", "file missing")

    return r


def find_submission_dirs(root="results"):
    out = []
    if not os.path.isdir(root):
        return out
    for ver in sorted(os.listdir(root)):
        vp = os.path.join(root, ver)
        if not os.path.isdir(vp):
            continue
        for slug in sorted(os.listdir(vp)):
            sp = os.path.join(vp, slug)
            if os.path.isdir(sp):
                out.append(sp)
    return out


def main():
    args = sys.argv[1:]
    as_json = "--json" in args
    args = [a for a in args if a != "--json"]

    targets = []
    if "--changed" in args:
        i = args.index("--changed")
        paths = args[i + 1:]
        seen = set()
        for p in paths:
            p = p.replace("\\", "/").strip()
            if not p.startswith("results/"):
                continue
            parts = p.split("/")
            if len(parts) >= 3:
                d = "/".join(parts[:3])
                if d not in seen:
                    seen.add(d)
                    targets.append(d)
    elif args:
        targets = [a for a in args if not a.startswith("-")]
    else:
        targets = find_submission_dirs()

    if not targets:
        print("No submissions found.")
        return 0

    results = [validate_dir(d) for d in targets]
    failed = [r for r in results if not r.passed]

    if as_json:
        print(json.dumps([{
            "path": r.path,
            "passed": r.passed,
            "checks": [{"no": c[0], "ok": c[1], "name": c[2], "detail": c[3]}
                       for c in r.checks],
        } for r in results], ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(("✓ " if r.passed else "✗ ") + r.path)
            for no, good, name, detail in r.checks:
                if not good:
                    print("    [%2d] ✗ %s" % (no, name))
                    if detail:
                        print("         %s" % detail)
        print()
        print("%d submission(s), %d passed, %d failed"
              % (len(results), len(results) - len(failed), len(failed)))

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
