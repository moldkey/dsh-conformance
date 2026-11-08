# Submission Format

**Format version:** 1
**Governed by:** DSHIO/T 37—2026
**Validator:** [`validate.py`](validate.py)

---

## Directory layout

```
results/
  v<baseline-dsh-version>/
    <plugin-slug>/
      README.md
      result.json
      TESTER.yaml
```

Example:

```
results/
  v0.2.2-rc.1/
    dsh-pet/
      README.md
      result.json
      TESTER.yaml
```

### Directory naming

| Part | Rule |
|---|---|
| `v<baseline-dsh-version>` | Exact DSH version from `dsh --version`, including pre-release (`v0.2.2-rc.1`). Not a range. |
| `<plugin-slug>` | Lowercase. `@scope/pkg` → `scope-pkg`. `pkg` → `pkg`. Characters: `a-z0-9._-` only. |

**One plugin version per directory.** Different versions of the same plugin are different submissions.

---

## 1. `result.json`

The **full raw output** of a test run. Not a summary, not a reformatted excerpt.

### Required top-level fields

| Field | Type | Notes |
|---|---|---|
| `plugin` | string | npm package name, e.g. `@scope/dsh-foo` |
| `version` | string | Exact plugin version tested |
| `tested_at` | string | `YYYY-MM-DD HH:MM:SS`, local time with UTC offset noted in `timezone` |
| `timezone` | string | e.g. `+08:00` |
| `baseline_dsh` | string | Must equal the directory version |
| `standard` | string | `DSHIO/T 20` and `DSHIO/T 21` must both appear |
| `fingerprint` | string | Environment fingerprint (see below) |
| `stages` | object | Keys: `static`, `install`, `list`, `config`, `boot` |
| `verdict` | string | One of the five verdicts in DSHIO/T 00 §3.5.3 |
| `repeat` | object | `{"count": 2, "verdicts": ["...","..."], "consistent": true}` |

### Environment fingerprint

Must follow DSHIO/T 21 §5.2:

```
dsh=<version>;img=<image>@<digest>;node=<node>;pnpm=<pnpm>;mem=<mem>;cpu=<cpu>;perm=<permissions>
```

Every component is required except `perm`, which is recommended.

### Stage records

Each stage object must include at minimum:

```json
{
  "exit": 0,
  "duration": 3.4,
  "stdout": "...",
  "stderr": "..."
}
```

Raw stdout/stderr may be truncated, but the truncation must be marked:

```json
"stdout_truncated": true,
"stdout_bytes_total": 481203
```

### Verdict values

| Verdict | Meaning |
|---|---|
| `pass` | All executed stages passed |
| `install_failed` | T1 or T2 failed |
| `config_failed` | T3 command failed |
| `installs_but_not_registered` | T3 passed but the entry never reached the config tree |
| `boot_failed` | T4 failed |

---

## 2. `TESTER.yaml`

Describes **who ran the test** and **what conflicts of interest exist**.

```yaml
# Identity
name: deepseekbase.com
url: https://deepseekbase.com
contact: no-reply@deepseekbase.com

# What you cover
scope:
  stages: [T0, T1, T2, T3, T4]
  plugin_types: [tool, service, ui, integration, config]

# Environment you ran on
environment:
  image: dsh-sandbox:5.0
  image_digest: sha256:d90b02baef228bb105d4817d1a7d23bdd6aec24f463cc7bc3d1fbb2e5af45c10
  node: "24.11.1"
  pnpm: "9.15.9"
  mem: 768m
  cpu: 1

# Conflict of interest — REQUIRED
conflicts:
  develops_plugins: true
  plugin_scope: "@liangjiehappy/*"
  paid_by_author: false
  result_dependent_fees: false
  notes: "The operator of deepseekbase.com also develops the @liangjiehappy/* plugin series."

# Self-declaration
declaration: >
  This tester self-declares conformance with DSHIO/T 36 and accepts sole
  responsibility for the accuracy of the results it submits.
```

All `conflicts` fields are **required**. If a field does not apply, set it to `false` or `""` — do not omit it.

---

## 3. `README.md`

Human-readable reproduction instructions. Must contain:

1. The plugin name and version
2. The exact DSH version used
3. The commands run
4. Approximate total duration
5. Any deviation from DSHIO/T 21 (if none, say so explicitly)
6. What a reader would need to reproduce

Minimum content:

```markdown
# <plugin> <version>

Tested on DSH <version> under DSHIO/T 21 conditions.

## Commands

    dsh plugin --profile web add <plugin>
    dsh plugin --profile web list
    dsh --profile web --dump-config
    dsh --profile web

## Environment

(fingerprint)

## Duration

~N seconds total.

## Deviations

None.
```

---

## What gets rejected

| Rejection | Reason |
|---|---|
| Missing any of the three files | Incomplete |
| `result.json` is a summary, not raw output | Not auditable |
| Fingerprint does not match DSHIO/T 21 format | Not comparable |
| Only one run recorded | Not reproducible per DSHIO/T 10 §7.4 |
| `TESTER.yaml` conflicts section empty | Responsible party unclear |
| Version is a range, not exact | Ambiguous |
| Extra files in the directory | Unclear what was reviewed |

---

## Amending a submission

Results are immutable once merged. To correct:

1. Open a new PR that **deletes** the old directory
2. Add the corrected directory in the same PR
3. Explain the correction in the PR body

The git history preserves the original. That is the point.

---

## Bulk submissions

If you have many results (e.g. you tested hundreds of plugins), you may:

1. Submit them one PR at a time, or
2. Submit a `snapshots/<date>.json` file that points to a downloadable archive, and open PRs for individual results over time

**A `snapshot` is not a conformance result.** It is a pointer. Individual results still need individual directories to be verifiable.

---

## Questions

Open an issue. Or read the standard: [DSHIO/T 37](https://dshio.org/37/).
