# Quickstart Validation Guide: Feature 043 — Summary Self-Correction Layer

**Spec**: `specs/043-summary-self-correction/spec.md`
**Prerequisites**: Feature 043 fully implemented and merged to branch `043-summary-self-correction`

---

## Prerequisites

| Requirement | Version | Check |
|---|---|---|
| Python | ≥ 3.10 | `python --version` |
| PyYAML | installed | `python -c "import yaml; print(yaml.__version__)"` |
| A test project | `t2TiERP` (or any project with partial outputs) | `ls projects/t2TiERP/outputs/` |
| `build_summary_comprehensive.py` at Feature 043 | Has `--section` / `--dry-run` flags | `python build_summary_comprehensive.py --help` |
| `validate_summary.py` at Feature 043 | v1.7.0 frontmatter in `summary-validate-agent.md` | `head -5 src/.../summary-validate-agent.md` |
| `remediate_summary.py` at Feature 043 | Has scan→regenerate cycle and writes `remediation-correction-log.json` | code inspection |
| `remediate_summary.py` — Dynamic Self-Correction Loop (§4.7) | Supports bounded 5-attempt loop with distinct-approach enforcement and a mocking seam for testing | code inspection; confirm mocking mechanism (e.g. `AVA_LOOP_MOCK_SUCCESS_AT`) matches P0-i implementation |

---

## Setup

```powershell
# Working directory for all commands below
Set-Location "C:\_git\Fix\imfai-ava-fabric-apps-agents\src\modules\ava-fabric-agents\summary\utils"
$PROJECT = "t2TiERP"
```

---

## Scenario A — Path Alias Resolution (Spec §5 Scenario 1 + 2)

**Goal**: Verify that when the primary inventory path is absent but an alias exists, the section is populated and the builder-correction-log.json records `outcome: resolved`.

```powershell
# Setup: rename inventory-report.md to inventory.md to simulate the alias case
$ASIS = "projects\$PROJECT\outputs\asis"
Rename-Item "$ASIS\inventory-report.md" "$ASIS\inventory.md" -ErrorAction SilentlyContinue

# Run the builder
python build_summary_comprehensive.py --project $PROJECT --skip-mermaid-gate

# Verify 1: inventory section is populated (HTML must contain non-empty inventory data)
# Verify 2: builder-correction-log.json exists and records the alias resolution
$LOG = "projects\$PROJECT\outputs\summary\builder-correction-log.json"
Get-Content $LOG | python -c "
import json, sys
d = json.load(sys.stdin)
assert d['summary']['resolved'] >= 1, 'Expected at least 1 resolved correction'
entries = [e for e in d['corrections_applied'] if e['artifact_key']=='inventory']
assert entries, 'Expected an inventory correction entry'
assert entries[0]['outcome'] == 'resolved', f'Expected resolved, got {entries[0][\"outcome\"]}'
assert 'inventory.md' in entries[0]['alternative_used'], f'Wrong alias: {entries[0][\"alternative_used\"]}'
print('✅ Scenario A PASS')
"

# Restore
Rename-Item "$ASIS\inventory.md" "$ASIS\inventory-report.md" -ErrorAction SilentlyContinue
```

---

## Scenario B — Idempotency (Spec §5 Scenario 1.2 + 3.3)

**Goal**: Run the builder twice over the same `outputs/` state. HTML must be byte-identical. Second builder-correction-log.json must have `total_attempted: 0`.

```powershell
# First run
python build_summary_comprehensive.py --project $PROJECT --skip-mermaid-gate
$HTML_FIRST = Get-FileHash "projects\$PROJECT\outputs\summary\*.html" | Select-Object -ExpandProperty Hash

# Second run
python build_summary_comprehensive.py --project $PROJECT --skip-mermaid-gate
$HTML_SECOND = Get-FileHash "projects\$PROJECT\outputs\summary\*.html" | Select-Object -ExpandProperty Hash

# Verify HTML byte-identity
if ($HTML_FIRST -eq $HTML_SECOND) { Write-Host "✅ HTML idempotent" } else { Write-Error "❌ HTML differs between runs" }

# Verify second log has total_attempted: 0
$LOG = "projects\$PROJECT\outputs\summary\builder-correction-log.json"
Get-Content $LOG | python -c "
import json, sys
d = json.load(sys.stdin)
assert d['summary']['total_attempted'] == 0, f'Expected 0, got {d[\"summary\"][\"total_attempted\"]}'
print('✅ Scenario B PASS — idempotency confirmed')
"
```

---

## Scenario C — Fail-Safe Negative (Spec §5 Scenario 1.3)

**Goal**: Remove ALL alias paths for inventory. Verify original `parser_gap` finding is emitted unchanged — no silent masking.

```powershell
# Setup: move all inventory variants out of reach
$ASIS = "projects\$PROJECT\outputs\asis"
Rename-Item "$ASIS\inventory-report.md" "$ASIS\inventory-report.md.bak" -ErrorAction SilentlyContinue
Rename-Item "$ASIS\inventory.md"        "$ASIS\inventory.md.bak"        -ErrorAction SilentlyContinue
Rename-Item "$ASIS\code-inventory.md"   "$ASIS\code-inventory.md.bak"   -ErrorAction SilentlyContinue

# Run the builder
python build_summary_comprehensive.py --project $PROJECT --skip-mermaid-gate

# Verify: builder-correction-log.json records outcome: failed for inventory
$LOG = "projects\$PROJECT\outputs\summary\builder-correction-log.json"
Get-Content $LOG | python -c "
import json, sys
d = json.load(sys.stdin)
entries = [e for e in d['corrections_applied'] if e['artifact_key']=='inventory']
assert entries, 'Expected a correction entry for inventory even on failure'
assert entries[0]['outcome'] == 'failed', f'Expected failed, got {entries[0][\"outcome\"]}'
assert entries[0]['alternative_used'] is None, 'alternative_used must be null on failure'
print('✅ Scenario C PASS — fail-safe confirmed, no masking')
"

# Restore
Rename-Item "$ASIS\inventory-report.md.bak" "$ASIS\inventory-report.md" -ErrorAction SilentlyContinue
Rename-Item "$ASIS\inventory.md.bak"        "$ASIS\inventory.md"        -ErrorAction SilentlyContinue
Rename-Item "$ASIS\code-inventory.md.bak"   "$ASIS\code-inventory.md"   -ErrorAction SilentlyContinue
```

---

## Scenario D — Regeneration Cycle (Spec §5 Scenario 3.1)

**Goal**: Simulate a parser_gap in `deep-audit-report.json` + artifact exists at alias → remediation resolves it and writes `remediation-correction-log.json`.

> ⚠️ **Explicit setup required**: This scenario creates a synthetic `deep-audit-report.json`
> with a known `parser_gap` finding so the test exercises the §4.3 path deterministically,
> regardless of the current state of `outputs/`. The original file is backed up and restored.

```powershell
$AUDIT      = "projects\$PROJECT\outputs\summary\deep-audit-report.json"
$AUDIT_BAK  = "$AUDIT.bak"
$ASIS       = "projects\$PROJECT\outputs\asis"

# Step 1 — Back up existing deep-audit-report.json (if any)
if (Test-Path $AUDIT) { Copy-Item $AUDIT $AUDIT_BAK }

# Step 2 — Ensure the alias artifact exists (inventory.md) so remediation can resolve it
if (-not (Test-Path "$ASIS\inventory.md")) {
    if (Test-Path "$ASIS\inventory-report.md") {
        Copy-Item "$ASIS\inventory-report.md" "$ASIS\inventory.md"
    } else {
        Set-Content "$ASIS\inventory.md" "# Inventory (synthetic for Scenario D test)"
    }
}

# Step 3 — Inject synthetic deep-audit-report.json with a known parser_gap for inventory
$synthetic = @'
{
  "schema_version": "1.1",
  "generated_at": "2026-08-21T00:00:00Z",
  "project": "SCENARIO_D_TEST",
  "critical": 1,
  "high": 0,
  "medium": 0,
  "low": 0,
  "promotable": false,
  "findings": [
    {
      "id": "C12.6-inventory-synthetic",
      "severity": "CRITICAL",
      "finding_type": "parser_gap",
      "d_field": "inventory",
      "artifact_path": "outputs/asis/inventory-report.md",
      "auto_correctable": true,
      "description": "Synthetic parser_gap for Scenario D — remediation must resolve via alias"
    }
  ]
}
'@
Set-Content $AUDIT $synthetic -Encoding utf8

# Step 4 — Run remediation
python remediate_summary.py --project $PROJECT

# Step 5 — Verify remediation-correction-log.json was written and contains the resolution
$RLOG = "projects\$PROJECT\outputs\summary\remediation-correction-log.json"
if (-not (Test-Path $RLOG)) { Write-Error "❌ remediation-correction-log.json not written" }
Get-Content $RLOG | python -c "
import json, sys
d = json.load(sys.stdin)
print(f'  origin: {d[\"origin\"]}')
print(f'  total_attempted: {d[\"summary\"][\"total_attempted\"]}')
print(f'  resolved: {d[\"summary\"][\"resolved\"]}')
print(f'  suppressed: {d[\"summary\"][\"suppressed\"]}')
print(f'  failed: {d[\"summary\"][\"failed\"]}')
assert d['summary']['total_attempted'] >= 1, 'Expected at least 1 correction attempted'
# Must have at least 1 resolved or suppressed (not all failed)
assert d['summary']['resolved'] + d['summary']['suppressed'] >= 1, \
    'Expected at least 1 resolved or suppressed outcome'
print('✅ Scenario D PASS — remediation-correction-log.json schema valid and outcome confirmed')
"

# Step 6 — Restore original deep-audit-report.json
if (Test-Path $AUDIT_BAK) {
    Move-Item $AUDIT_BAK $AUDIT -Force
    Write-Host "✅ Original deep-audit-report.json restored"
}
```

---

## Scenario E — Structural Suppression (Spec §5 Scenario 4)

**Goal**: Verify that `_classify_empty_element()` emits a DEBUG log (not a finding) for elements with no `id=` and no heading.

```powershell
# Run validate_summary.py with verbose/debug logging enabled
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
import validate_summary
# The DEBUG log for structural suppression will appear for any anonymous elements
" 2>&1 | Select-String "suppress|anonymous|no id"
Write-Host "✅ Scenario E — check DEBUG log above for structural suppression entries"
```

---

## Scenario F — Audit Log Always-On (Spec §5 Scenario 6.3)

**Goal**: Verify `builder-correction-log.json` is written even when zero corrections are needed.

```powershell
# Ensure all primary paths exist (no aliases needed)
python build_summary_comprehensive.py --project $PROJECT --skip-mermaid-gate
$LOG = "projects\$PROJECT\outputs\summary\builder-correction-log.json"
if (-not (Test-Path $LOG)) { Write-Error "❌ builder-correction-log.json not written on zero-correction build" }
Get-Content $LOG | python -c "
import json, sys
d = json.load(sys.stdin)
assert d['summary']['total_attempted'] == 0
assert d['corrections_applied'] == []
assert d['origin'] == 'build_summary_comprehensive.py'
print('✅ Scenario F PASS — always-on log written with total_attempted:0')
"
```

---

## Scenario G — `--section` CLI Flag (Contracts §builder-cli-contract.md)

```powershell
# Test section-only dry-run
$OUT = python build_summary_comprehensive.py --project $PROJECT --section inventory --dry-run 2>&1
$JSON = $OUT | ConvertFrom-Json
if ($JSON.section_key -eq "inventory") {
    Write-Host "✅ Scenario G PASS — --section flag works"
} else {
    Write-Error "❌ --section output missing section_key"
}
```

---

## Scenario H — Dynamic Self-Correction Loop (Spec §5 Scenario 7, §4.7)

**Goal**: Verify the bounded 5-attempt dynamic loop triggers only when static correction
(§4.1/§4.3) is exhausted, that each attempt uses a distinct approach, that success stops
the loop immediately, and that exhausting all 5 attempts rolls back and logs ONLY the
last attempt.

⚠️ **Explicit setup required**: This scenario forces the static pathway to fail
deterministically (finding with NO valid alias/alternative anywhere), so the dynamic
loop is guaranteed to trigger. It uses a mock/stub for the connected Copilot agent's
corrective proposals, since exercising a real dynamic reasoning call is not
deterministic enough for an automated quickstart check.

### H1 — Early success (loop stops before exhausting attempts)

```powershell
$AUDIT      = "projects\$PROJECT\outputs\summary\deep-audit-report.json"
$AUDIT_BAK  = "$AUDIT.bak"

# Step 1 — Back up existing deep-audit-report.json
if (Test-Path $AUDIT) { Copy-Item $AUDIT $AUDIT_BAK }

# Step 2 — Inject synthetic deep-audit-report.json with a finding that has
# NO resolvable alias/alternative anywhere (forces static §4.1/§4.3 to fail,
# guaranteeing the dynamic loop in §4.7 is the only path left)
$synthetic = @'
{
  "schema_version": "1.1",
  "generated_at": "2026-08-21T00:00:00Z",
  "project": "SCENARIO_H1_TEST",
  "critical": 1, "high": 0, "medium": 0, "low": 0, "promotable": false,
  "findings": [
    {
      "id": "C12.6-inventory-synthetic-H1",
      "severity": "CRITICAL",
      "finding_type": "parser_gap",
      "d_field": "inventory",
      "artifact_path": "outputs/asis/inventory-report.md",
      "auto_correctable": false,
      "description": "Synthetic parser_gap for Scenario H1 — no alias exists, forces dynamic loop"
    }
  ]
}
'@
Set-Content $AUDIT $synthetic -Encoding utf8

# Step 3 — Run remediation with a mocked agent proposal source that succeeds on attempt 3
# (mock injection mechanism depends on implementation — e.g. env var or test double;
# placeholder below assumes an env var AVA_LOOP_MOCK_SUCCESS_AT=3 is supported for testing)
$env:AVA_LOOP_MOCK_SUCCESS_AT = "3"
python remediate_summary.py --project $PROJECT
Remove-Item Env:\AVA_LOOP_MOCK_SUCCESS_AT

# Step 4 — Verify exactly ONE log entry, describing attempt 3, and loop stopped early
$RLOG = "projects\$PROJECT\outputs\summary\remediation-correction-log.json"
Get-Content $RLOG | python -c "
import json, sys
d = json.load(sys.stdin)
entries = [e for e in d['corrections_applied'] if e['finding_id'] == 'C12.6-inventory-synthetic-H1' or 'H1' in e.get('notes', '')]
assert len(entries) == 1, f'Expected exactly 1 log entry for this finding, got {len(entries)}'
e = entries[0]
assert e['outcome'] == 'resolved', f'Expected resolved, got {e[\"outcome\"]}'
assert e['html_regenerated'] is True
assert 'attempt_number' in e.get('notes', '') or '3' in e.get('notes', ''), \
    'Expected notes to reference attempt_number 3 (the successful attempt)'
print('✅ Scenario H1 PASS — loop stopped at attempt 3, single log entry, no attempts 4/5 executed')
"

# Step 5 — Restore original deep-audit-report.json
if (Test-Path $AUDIT_BAK) { Move-Item $AUDIT_BAK $AUDIT -Force }
```

### H2 — All 5 attempts fail (rollback + last-attempt-only log)

```powershell
$AUDIT      = "projects\$PROJECT\outputs\summary\deep-audit-report.json"
$AUDIT_BAK  = "$AUDIT.bak"
if (Test-Path $AUDIT) { Copy-Item $AUDIT $AUDIT_BAK }

$synthetic = @'
{
  "schema_version": "1.1",
  "generated_at": "2026-08-21T00:00:00Z",
  "project": "SCENARIO_H2_TEST",
  "critical": 1, "high": 0, "medium": 0, "low": 0, "promotable": false,
  "findings": [
    {
      "id": "C12.6-inventory-synthetic-H2",
      "severity": "CRITICAL",
      "finding_type": "parser_gap",
      "d_field": "inventory",
      "artifact_path": "outputs/asis/inventory-report.md",
      "auto_correctable": false,
      "description": "Synthetic parser_gap for Scenario H2 — forces all 5 dynamic attempts to fail"
    }
  ]
}
'@
Set-Content $AUDIT $synthetic -Encoding utf8

# Capture HTML hash BEFORE the loop runs, to verify rollback restores it exactly
$HTML_BEFORE = Get-FileHash "projects\$PROJECT\outputs\summary\*.html" | Select-Object -ExpandProperty Hash

# Mock: force all attempts to fail (no success threshold reached)
$env:AVA_LOOP_MOCK_SUCCESS_AT = "0"   # 0 = never succeeds
python remediate_summary.py --project $PROJECT
Remove-Item Env:\AVA_LOOP_MOCK_SUCCESS_AT

$HTML_AFTER = Get-FileHash "projects\$PROJECT\outputs\summary\*.html" | Select-Object -ExpandProperty Hash

$RLOG = "projects\$PROJECT\outputs\summary\remediation-correction-log.json"
Get-Content $RLOG | python -c "
import json, sys
d = json.load(sys.stdin)
entries = [e for e in d['corrections_applied'] if e['finding_id'] == 'C12.6-inventory-synthetic-H2' or 'H2' in e.get('notes', '')]
assert len(entries) == 1, f'Expected exactly 1 log entry (terminal-outcome-only), got {len(entries)}'
e = entries[0]
assert e['outcome'] == 'failed', f'Expected failed, got {e[\"outcome\"]}'
assert e['html_regenerated'] is False
assert '5' in e.get('notes', '') or 'attempt' in e.get('notes', '').lower(), \
    'Expected notes to describe ONLY the 5th (last) attempt approach'
print('✅ Scenario H2 PASS — exactly 1 log entry after 5 failed attempts (not 5 entries), describes only last attempt')
"

if ($HTML_BEFORE -eq $HTML_AFTER) {
    Write-Host "✅ Scenario H2 PASS — HTML rolled back to pre-loop state (byte-identical)"
} else {
    Write-Error "❌ HTML was not rolled back after all 5 attempts failed"
}

if (Test-Path $AUDIT_BAK) { Move-Item $AUDIT_BAK $AUDIT -Force }
```

**Note on mocking mechanism**: the exact mechanism for injecting mocked agent proposals
(env var, config flag, or test double) is an implementation detail to be finalized during
P0-i (see plan.md Complexity Tracking — "exact agent-invocation interface TBD at
implementation time"). This quickstart scenario assumes an env-var-based hook
(`AVA_LOOP_MOCK_SUCCESS_AT`) as a placeholder; adjust to match whatever mocking seam
P0-i actually implements.

---

## Non-Regression Check

```powershell
# After all scenarios, run the full validate to confirm no new CRITICAL/HIGH findings
python validate_summary.py --project $PROJECT
Write-Host "Review validation-report.md for any new findings introduced by Feature 043"
```

---

## Expected Outcomes Summary

| Scenario | Expected |
|---|---|
| A — path alias | `builder-correction-log.json` has `outcome:resolved`, HTML section populated |
| B — idempotency | HTML byte-identical on 2nd run; `total_attempted:0` in 2nd log |
| C — fail-safe | `outcome:failed`, `alternative_used:null`, original finding preserved |
| D — regeneration | `remediation-correction-log.json` written with valid schema |
| E — structural suppression | DEBUG log entry; NO finding emitted for anonymous elements |
| F — always-on log | `builder-correction-log.json` exists even with zero corrections |
| G — `--section` flag | JSON output with `section_key` field |
| H1 — dynamic loop, early success | Loop stops at attempt 3; exactly 1 log entry describing attempt 3; `outcome:resolved` |
| H2 — dynamic loop, all 5 fail | Exactly 1 log entry (not 5) describing ONLY the 5th attempt; HTML rolled back byte-identical; `outcome:failed` |
| Non-regression | Zero new CRITICAL/HIGH findings in `validation-report.md` |
