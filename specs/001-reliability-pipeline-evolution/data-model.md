# Data Model: Reliability Pipeline Evolution

**Phase**: 1 — Design
**Date**: 2026-07-02
**Spec**: [spec.md](./spec.md)

---

## Entities Modified

This PBI adds or extends the following configuration schema fields.
No domain entities (C# classes) are modified — all changes are in YAML config files.

---

### Entity: `project-config.yaml → quality_gates.cve_policy`

**Status**: NEW (not present in current template)
**Location**: `projects/_template/context/project-config.yaml`, under `quality_gates`
**Consumed by**: `ava-stack-build-validator` Step F3.5

```yaml
cve_policy:
  mode: string                 # "zero_tolerance" | "exceptions_allowed"
                               # Default (when absent): "zero_tolerance"
  accepted_exceptions:         # list — empty list = zero_tolerance behaviour
    - cve_id: string           # Required. CVE identifier (e.g. "CVE-2024-12345")
      package: string          # Required. Package name as reported by npm audit / govulncheck
      reason: string           # Required. Human-readable justification
      expiry: string           # Required when mode=exceptions_allowed. ISO date "YYYY-MM-DD"
                               # An exception past its expiry date is treated as blocking.
```

**Validation rules**:
- `mode` must be one of `["zero_tolerance", "exceptions_allowed"]`; absent = `"zero_tolerance"`
- When `mode == "zero_tolerance"`, `accepted_exceptions` is ignored
- When `mode == "exceptions_allowed"`, each entry with `expiry < today` is treated as a blocking CVE
- `expiry` without a value = no expiration (exception is permanent while `mode == "exceptions_allowed"`)

---

### Entity: `project-config.yaml → tobe_stack.node_version` (existing — verify present)

**Status**: EXISTING (already at `node_version: "22"` in template)
**Location**: `projects/_template/context/project-config.yaml`, under `tobe_stack`
**Consumed by**: `ava-stack-build-validator` Step B0.3, `build_runner.py --image node {version}`

```yaml
tobe_stack:
  node_version: string         # Node.js major version for Docker/Podman image
                               # Independent of frontend_version (Angular, React, Vue major)
                               # Example: Angular 17 → node_version: "20"
                               #          Angular 18+ → node_version: "22"
```

**Validation rules**:
- Must be a numeric string (e.g. `"20"`, `"22"`) — not a range or semver
- Different from `frontend_version` — build-validator enforces this separation

---

### Entity: `build-fixer-agent.md → fix_result` output (existing — verify present)

**Status**: EXISTING (already in `build-fixer-agent.md` v1.1.0 output contract)

```yaml
fix_result:
  status: string               # "RESOLVED" | "PARTIAL" | "UNRESOLVABLE"
  files_modified: [string]     # MUST include "package-lock.json" if package.json was modified
  lockfile_updated: boolean    # true  → package.json was modified AND npm install was run
                               # false → package.json was NOT modified in this fix cycle
  ...existing_fields...
```

**Consumed by**: `ava-stack-build-validator` Step F3 lockfile recovery logic.

---

## State Transitions

### CVE Policy Mode State Machine

```
project-config.yaml loaded
         │
         ▼
quality_gates.cve_policy.mode?
         │
    ┌────┴────────────────────────────┐
    │ "zero_tolerance" (default)      │ "exceptions_allowed"
    ▼                                 ▼
Any CVE high/critical          Load accepted_exceptions[]
       │                               │
       ▼                          For each entry:
    FAIL                      expiry < today? → blocking
                              expiry ≥ today? → allowed
                                     │
                              remaining_blocking > 0?
                              ├─ YES → FAIL
                              └─ NO  → PASS (with warning log)
```

### Lockfile Recovery State Machine

```
npm ci runs
    │
    ▼
Exit code 0? → PASS (Step F3 continues)
    │
    ▼ (exit code ≠ 0)
Error contains "out of sync"?
    │
    ├─ NO  → normal fix cycle
    └─ YES → dispatch build-fixer with explicit instruction:
             "regenerate package-lock.json via npm install"
                     │
                     ▼
             fix_result.lockfile_updated?
             ├─ true  → retry npm ci
             └─ false → new fix cycle (max 5 total)
```
