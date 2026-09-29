# Quickstart: Validating Screen-Flow Completeness Assertion

**Version**: 1.0.0  
**Scope**: Local validation of the `screen-flow-completeness.json` assertion after `ava-asis-documentation` FT sub-skill runs.

---

## Prerequisites

- `jq` installed (or Python 3.11+ with `json` module)
- Project outputs generated: `projects/{PROJECT_NAME}/outputs/asis/docs/screen-flow.mmd`
- `projects/{PROJECT_NAME}/outputs/asis/.internal/form-registry.json` (or glob fallback used)

---

## 1. Check if the assertion file exists

```bash
ls projects/{PROJECT_NAME}/outputs/asis/docs/screen-flow-completeness.json
```

**Expected**: File exists with size > 0 bytes.  
**If missing**: The FT sub-skill did not run the assertion — agent instructions need review.

---

## 2. Read the assertion result

### Using `jq`

```bash
jq '.' projects/{PROJECT_NAME}/outputs/asis/docs/screen-flow-completeness.json
```

### Using Python

```python
import json
with open('projects/{PROJECT_NAME}/outputs/asis/docs/screen-flow-completeness.json') as f:
    data = json.load(f)
print(f"Status: {data['status']}")
print(f"Coverage: {data['coverage_pct']}% (threshold: {data['threshold_pct']}%)")
print(f"Nodes: {data['N_nodes']} / Registry: {data['N_registry']}")
if data.get('missing_forms'):
    print(f"Missing: {data['missing_forms']}")
```

---

## 3. Verify node count manually (spot-check)

```bash
python -c "
import re
with open('projects/{PROJECT_NAME}/outputs/asis/docs/screen-flow.mmd') as f:
    content = f.read()
# Count unique node IDs (explicit + implicit in edges)
# This is a simplified check; the agent uses the full protocol
nodes = set(re.findall(r'^\s*(\w+)\s*\[', content, re.MULTILINE))
edges = re.findall(r'(\w+)\s*-->', content)
print(f'Approximate nodes: {len(nodes | set(edges))}')
"
```

Compare to `N_nodes` in `screen-flow-completeness.json`. They should match closely.

---

## 4. Expected Outcomes

| Condition | Expected Result |
|---|---|
| `status == "PASS"` | ✅ `screen-flow.mmd` is acceptable; downstream processing can proceed |
| `status == "FAIL"` AND `retry_count < 3` | ⚠️ Retry triggered; check logs for `[FT-RETRY-{N}]` |
| `status == "FAIL"` AND `retry_count == 3` | 🚫 `human_gate_required = true`; manual intervention needed |
| `status == "SKIPPED"` | ℹ️ `form-registry.json` unavailable; assertion used glob fallback but still returned result |

---

## 5. Troubleshooting

### Coverage is 0%

- Check that `gen_screen_flow.py` was invoked (look for `[gen_screen_flow]` logs in pipeline output)
- Verify `form-registry.json` is not empty
- Check that `screen-flow.mmd` is not empty

### Missing forms list is suspiciously large

- Compare `missing_forms` against `form-registry.json` entries with `bounded_context == "Unclassified"`
- These are forms the BC classifier could not map; they may legitimately be absent from screen-flow.mmd if they have no navigation links
- Consider lowering threshold to 70% for highly fragmented legacy codebases

### Assertion file shows `retry_count: 3` but `status: "PASS"`

- This is expected if a retry succeeded — the final result is what matters
- The intermediate FAILs are logged in the pipeline observability system
