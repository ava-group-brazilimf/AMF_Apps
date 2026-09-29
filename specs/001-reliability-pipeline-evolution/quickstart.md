# Quickstart: Reliability Pipeline Evolution

**Purpose**: Validate that all feature requirements are working end-to-end.
**Date**: 2026-07-02

> **Prerequisites**:
> - Python 3.9+ installed
> - Repository cloned at `c:/_git/pbi_2272/imfai-ava-fabric-apps-agents`
> - `npm` available (for ESLint detection scenarios)

---

## Setup

```bash
cd c:/_git/pbi_2272/imfai-ava-fabric-apps-agents
```

---

## Scenario 1 — Podman Path Normalization (CA01, CA02)

Validate that `build_runner.py` emits runtime-correct paths.

```bash
# Docker path (MSYS2 format)
python src/shared/utils/build_runner.py --normalize-path "C:\\Users\\dev\\project"
# Expected: //c/Users/dev/project

# Podman path (native Windows format)
python src/shared/utils/build_runner.py --normalize-path "C:\\Users\\dev\\project" --runtime podman
# Expected: C:/Users/dev/project
```

**Pass criteria**: Docker output starts with `//`, Podman output starts with `C:/`.

---

## Scenario 2 — Node Version Override with Warning (RF03, RF04)

```bash
# Angular 17 + different Node version — should warn
python src/shared/utils/build_runner.py --image angular 17 --node-version 22
# Expected: image resolves to node:22-alpine + WARNING about version discrepancy

# Correct usage — matching framework/node
python src/shared/utils/build_runner.py --image angular 17 --node-version 20
# Expected: image resolves to node:20-alpine, no warning
```

**Pass criteria**: `--node-version` overrides framework-derived Node version; warning emitted when values diverge.

---

## Scenario 3 — CVE Policy Config Presence (CA05, CA17)

Validate that the template contains the `cve_policy` section:

```bash
grep -n "cve_policy\|zero_tolerance\|accepted_exceptions\|exceptions_allowed" \
  projects/_template/context/project-config.yaml
```

**Expected output** (at least these lines):

```
NNN:  cve_policy:
NNN:    mode: "zero_tolerance"
NNN:    accepted_exceptions: []
```

**Pass criteria**: all 3 lines present.

---

## Scenario 4 — CVE Policy Expiry Logic (CA06, CA07)

Inspect the build-validator agent for expired exception handling:

```bash
grep -n "expiry\|expired\|CVE_POLICY_MODE\|blocking" \
  src/modules/ava-fabric-agents/tech-stack/agents/build-validator-agent.md | head -20
```

**Expected**: lines showing:
- `expiry` field read from config
- Comparison `hoje > expiry` → treated as blocking
- `CVE_POLICY_MODE` variable assigned based on `mode` field

**Pass criteria**: all expiry comparison logic present in agent body.

---

## Scenario 5 — Lockfile Recovery Protocol (CA08, CA09, CA10)

Validate the build-fixer has the lockfile contract:

```bash
grep -n "lockfile_updated\|npm install\|package-lock.json\|PROIBIDO" \
  src/modules/ava-fabric-agents/tech-stack/agents/build-fixer-agent.md | head -15
```

**Expected**: lines showing:
- `lockfile_updated: boolean` in output contract
- `npm install` execution after `package.json` modification
- Guardrail: PROIBIDO retornar sem regenerar lockfile

Validate build-validator recovery dispatch:

```bash
grep -n "lockfile_updated\|out of sync\|new.*cycle\|fixer.*lockfile" \
  src/modules/ava-fabric-agents/tech-stack/agents/build-validator-agent.md | head -10
```

**Pass criteria**: both patterns present in respective agent files.

---

## Scenario 6 — ESLint Detection (CA11, CA12, CA13)

Validate build-validator detects both ESLint config formats:

```bash
grep -n "eslint.config.js\|eslintrc\|No ESLint config\|SKIP lint\|WARN" \
  src/modules/ava-fabric-agents/tech-stack/agents/build-validator-agent.md | grep -i eslint
```

**Expected**:
- Line matching `eslint.config.js` (flat config detection)
- Line matching `.eslintrc.*` (legacy config detection)
- Line with `SKIP lint` + `WARN "No ESLint config found"` when neither exists

**Pass criteria**: 3 distinct patterns found.

---

## Scenario 7 — Angular ESLint Scaffolding (CA14, CA15, CA16)

Validate angular agent generates ESLint scaffold:

```bash
# Check 7 ESLint dependencies
grep -c "angular-eslint\|typescript-eslint\|\"eslint\"" \
  src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md

# Check lint target in angular.json template
grep -n "angular-eslint/builder:lint\|lintFilePatterns" \
  src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md | head -5

# Check .eslintrc.json generation step
grep -n "2\.2\.1\|eslintrc.json\|plugin:@angular-eslint" \
  src/modules/ava-fabric-agents/tech-stack/agents/coder-angular-frontend.md | head -5
```

**Pass criteria**:
- ≥7 ESLint-related package references
- `@angular-eslint/builder:lint` present in `angular.json` template section
- Step 2.2.1 documents `.eslintrc.json` generation

---

## Scenario 8 — Node Version Guardrail in Build-Validator (CA03, CA04)

```bash
grep -n "node_version\|frontend_version.*node\|GUARDRAIL\|NUNCA usar.*frontend_version\|NODE_IMAGE" \
  src/modules/ava-fabric-agents/tech-stack/agents/build-validator-agent.md | head -10
```

**Expected**: explicit guardrail block preventing use of `frontend_version` to resolve `NODE_IMAGE`.

**Pass criteria**: guardrail text `NUNCA usar` or equivalent present alongside `node_version` usage.

---

## Full Validation Run

Run all scenarios in sequence:

```bash
echo "=== S1: Podman path ===" && \
  python src/shared/utils/build_runner.py --normalize-path "C:\\test" --runtime podman && \
echo "=== S2: Node version warning ===" && \
  python src/shared/utils/build_runner.py --image angular 17 --node-version 22 && \
echo "=== S3: CVE policy in template ===" && \
  grep -c "cve_policy" projects/_template/context/project-config.yaml && \
echo "=== S5: lockfile_updated in fixer ===" && \
  grep -c "lockfile_updated" src/modules/ava-fabric-agents/tech-stack/agents/build-fixer-agent.md && \
echo "=== S6: ESLint detection in validator ===" && \
  grep -c "eslint" src/modules/ava-fabric-agents/tech-stack/agents/build-validator-agent.md && \
echo "=== ALL DONE ==="
```

**Expected**: all commands return without errors; `grep -c` values ≥ 1 for each.
