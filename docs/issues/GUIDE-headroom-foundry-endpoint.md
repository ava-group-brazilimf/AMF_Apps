# GUIDE — Using Headroom with Azure Foundry Endpoint

**Context**: processaERP-008 root cause (ISSUE-002) showed the pipeline gets stuck because
`headroom.compress()` runs **offline** with no awareness of the actual model endpoint —
it compresses to a fixed Anthropic model limit even though the live inference runs via
Azure Foundry. This guide shows how to wire Foundry as the endpoint for both compression
tuning and live `HeadroomClient` interception.

---

## 1. What Headroom Does Today (Offline Mode)

```
AST extractor (363 .pas files)
        ↓
headroom_precompress.py
  └─ headroom.compress(messages, model="claude-sonnet-4-5-20250929")
        ↓ offline — no network call
compressed/*.json   (761K → 761K tokens — only structural SmartCrusher applied)
        ↓
Agent reads compressed JSON as context  ←── ⚠️ still 761K tokens per subagent call
```

**Problem**: `headroom.compress()` in offline mode only applies structural transforms
(array factoring, schema deduplication). It does **not** call the model — so for 761K
tokens it provides only ~36% reduction (structural). To get **semantic compression**
(the real win — KV-cache-aware, relevance-based truncation) you need to tell Headroom
about the live model endpoint.

---

## 2. Integration Patterns

### Pattern A — `HeadroomClient` wrapping an OpenAI-compatible Azure Foundry client

This is the **recommended pattern** for the agents that dispatch live calls (orchestrator,
solution-delphi). Headroom intercepts every `chat.completions.create()` call and applies
context window management transparently.

```python
# headroom_foundry_client.py
from openai import AzureOpenAI
import headroom

# Step 1 — Create the raw Azure Foundry / Azure OpenAI client
raw_client = AzureOpenAI(
    api_key       = "YOUR_AZURE_API_KEY",           # or os.environ["AZURE_OPENAI_KEY"]
    azure_endpoint= "https://<your-resource>.openai.azure.com/",
    api_version   = "2024-12-01-preview",
)
# For Azure AI Foundry (non-Azure-OpenAI endpoint):
# from openai import OpenAI
# raw_client = OpenAI(
#     api_key  = "YOUR_FOUNDRY_KEY",
#     base_url = "https://<your-project>.services.ai.azure.com/models/",
# )

# Step 2 — Create the Headroom provider with Foundry model limits
# Tell Headroom the real context window of the deployed model
FOUNDRY_MODEL   = "gpt-4o"          # or "Meta-Llama-3-1-70B-Instruct" etc.
CONTEXT_LIMIT   = 128_000           # tokens — match your deployed model

provider = headroom.OpenAIProvider(context_limits={FOUNDRY_MODEL: CONTEXT_LIMIT})

# Step 3 — Wrap the raw client
client = headroom.HeadroomClient(
    original_client   = raw_client,
    provider          = provider,
    default_mode      = "optimize",          # "audit" (log only) | "optimize" (truncate)
    store_url         = "sqlite:///headroom_foundry.db",  # persistent metrics
)

# Step 4 — Use exactly like the normal openai client
response = client.chat.completions.create(
    model    = FOUNDRY_MODEL,
    messages = messages,           # Headroom trims context automatically
)
```

**What Headroom does in `optimize` mode**:

- Measures context size against `CONTEXT_LIMIT`
- Applies CacheAligner → ContentRouter → SmartCrusher pipeline
- Drops oldest messages first (keeping system prompt + recent turns)
- Logs savings to SQLite for the NTP script to read

---

### Pattern B — `headroom.compress()` with Foundry model name (standalone, no live call)

Use this when you want to pre-compress the AST artifacts before they enter the prompt,
using the **correct model name** so token counting is accurate for the deployed model.

```python
# In headroom_precompress.py — change DEFAULT_MODEL and add HEADROOM_MODEL_LIMITS
import os, json
from headroom import compress, CompressConfig

# Option 1: env var (no code change needed)
# Set before running the AST extractor:
#   $env:HEADROOM_MODEL_LIMITS = '{"openai":{"context_limits":{"gpt-4o":128000}}}'

# Option 2: explicit in code
FOUNDRY_MODEL = os.environ.get("AVA_FOUNDRY_MODEL", "gpt-4o")
FOUNDRY_LIMIT = int(os.environ.get("AVA_FOUNDRY_CONTEXT_LIMIT", "128000"))

def compress_artifact_for_foundry(raw_json: str) -> dict:
    """Compress a single artifact JSON targeting Foundry model limits."""
    wrapped = json.dumps([json.loads(raw_json)])  # wrap in array for SmartCrusher
    cfg = CompressConfig(
        compress_user_messages  = True,
        protect_recent          = 0,
        min_tokens_to_compress  = 100,
        target_ratio            = 0.5,   # aim for 50% of tokens (aggressive)
    )
    res = compress(
        [{"role": "user", "content": wrapped}],
        model       = FOUNDRY_MODEL,
        model_limit = FOUNDRY_LIMIT,
        config      = cfg,
    )
    content = res.messages[-1]["content"]
    parsed  = json.loads(content)
    return {
        "content"    : json.dumps(parsed[0]),
        "tokens_in"  : res.tokens_before,
        "tokens_out" : res.tokens_after,
        "transforms" : list(res.transforms_applied),
        "mode"       : f"headroom-foundry/{FOUNDRY_MODEL}",
    }
```

**Key difference from current code**: passing `model_limit=FOUNDRY_LIMIT` makes Headroom
apply proportional truncation — instead of preserving everything that fits in Claude's
200K window, it truncates to fit inside gpt-4o's 128K or the deployed model's real limit.

---

### Pattern C — BC-scoped compression (solves the 761K overload)

This is the **highest-value change** for processaERP-008.
Instead of passing all 9 artifacts to every agent subagent, compress only the
artifacts each agent needs.

```python
# bc_compress.py  — called once per BC before dispatching subagent
import json
from headroom import compress, CompressConfig
from pathlib import Path

# Artifact → agent mapping  (from ISSUE-002 Table § M-1)
AGENT_ARTIFACT_MAP = {
    "ava-asis-solution-delphi": ["01_business_rules", "02_form_business_rules", "08_code_overview"],
    "ava-asis-db-analyzer"    : ["03_database_rules",  "04_database_schemas",   "05_procedures"],
    "ava-asis-documentation"  : ["01_business_rules", "02_form_business_rules", "08_code_overview"],
    "ava-asis-inventory"      : ["08_code_overview"],
    "ava-asis-gaps-risks"     : ["01_business_rules", "03_database_rules",      "08_code_overview"],
}

def build_agent_context(agent_name: str, compressed_dir: str,
                        model: str = "gpt-4o", limit: int = 128_000) -> list[dict]:
    """Return a messages list with only the artifacts this agent needs, compressed."""
    needed = AGENT_ARTIFACT_MAP.get(agent_name, [])
    messages = []
    for art in needed:
        fp = Path(compressed_dir) / f"{art}.json"
        if fp.exists():
            messages.append({"role": "user", "content": fp.read_text()})

    if not messages:
        return messages

    cfg = CompressConfig(
        compress_user_messages = True,
        protect_recent         = 1,
        min_tokens_to_compress = 200,
    )
    result = compress(messages, model=model, model_limit=limit, config=cfg)
    return result.messages
```

**Token budget per agent** (estimated post-compression):

| Agent                    | Artifacts  | Raw tokens | After compress |
| ------------------------ | ---------- | ---------- | -------------- |
| ava-asis-solution-delphi | 01, 02, 08 | ~201K      | ~100K          |
| ava-asis-db-analyzer     | 03, 04, 05 | ~560K      | ~280K          |
| ava-asis-documentation   | 01, 02, 08 | ~201K      | ~100K          |
| ava-asis-inventory       | 08 only    | ~7K        | ~4K            |
| ava-asis-gaps-risks      | 01, 03, 08 | ~150K      | ~75K           |

→ Largest single call drops from **761K → ~280K** (ava-asis-db-analyzer).
→ solution-delphi drops from **761K → ~100K**, eliminating the 35-62 min gaps.

---

## 3. Environment Variables

| Variable                      | Description                                     | Example                                               |
| ----------------------------- | ----------------------------------------------- | ----------------------------------------------------- |
| `AZURE_OPENAI_KEY`          | Azure OpenAI / Foundry API key                  | `abc123...`                                         |
| `AZURE_OPENAI_ENDPOINT`     | Azure resource endpoint                         | `https://myresource.openai.azure.com/`              |
| `AZURE_OPENAI_API_VERSION`  | API version                                     | `2024-12-01-preview`                                |
| `AVA_FOUNDRY_MODEL`         | Model deployment name used by agents            | `gpt-4o`                                            |
| `AVA_FOUNDRY_CONTEXT_LIMIT` | Real context window of deployed model (tokens)  | `128000`                                            |
| `HEADROOM_MODEL_LIMITS`     | JSON override for Headroom model registry       | `'{"openai":{"context_limits":{"gpt-4o":128000}}}'` |
| `HEADROOM_DETECT_BACKEND`   | Force Magika backend (set`rust` on Windows)   | `rust`                                              |
| `HEADROOM_DEFAULT_MODE`     | `audit` (log only) or `optimize` (truncate) | `optimize`                                          |

---

## 4. Wiring Into `headroom_precompress.py`

The single line change needed in
`C:\Desenv\repo\tool\ast\imfai-ava-tools\ava-fabric-delphi-analyzer\headroom_precompress.py`:

```python
# BEFORE (line ~7)
DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

# AFTER — reads from env, falls back to claude
import os
DEFAULT_MODEL = os.environ.get("AVA_FOUNDRY_MODEL", "claude-sonnet-4-5-20250929")
DEFAULT_LIMIT = int(os.environ.get("AVA_FOUNDRY_CONTEXT_LIMIT", "200000"))
```

Then in `_compress_with_headroom()`:

```python
# BEFORE
res = compress([{"role": "user", "content": wrapped}], model=model, config=cfg)

# AFTER — pass model_limit so Headroom truncates to Foundry's real window
res = compress([{"role": "user", "content": wrapped}], model=model,
               model_limit=DEFAULT_LIMIT, config=cfg)
```

And in `precompress()`:

```python
# BEFORE
mf = precompress(a.in_dir, a.out, a.model)

# AFTER — pass FOUNDRY model and limit via CLI
ap.add_argument("--model-limit", type=int, default=DEFAULT_LIMIT)
```

---

## 5. Quick Test

```powershell
# Set Foundry env vars
$env:AVA_FOUNDRY_MODEL          = "gpt-4o"
$env:AVA_FOUNDRY_CONTEXT_LIMIT  = "128000"
$env:HEADROOM_DETECT_BACKEND    = "rust"      # Windows — avoid pure-Python Magika

# Run the NTP script — it will report the new token budget
python docs/issues/perf_pipeline_ntp.py --project processaERP-008

# Run compression manually against existing extraction
cd "C:\Desenv\repo\tool\ast\imfai-ava-tools\ava-fabric-delphi-analyzer"
python headroom_precompress.py `
    "C:\Desenv\repo\branch_develop_bugfix_23.07\imfai-ava-fabric-apps-agents\projects\processaERP-008\outputs\asis\delphi-ast-raw\extraction" `
    -o "C:\Desenv\repo\branch_develop_bugfix_23.07\imfai-ava-fabric-apps-agents\projects\processaERP-008\outputs\asis\delphi-ast-raw\compressed_foundry" `
    --model gpt-4o
```

Expected output with Foundry target:

```
   [1/9] 01_business_rules        128743 ->  64000 tok  (-50.3%)   ...
   [5/9] 05_procedures            426984 -> 100000 tok  (-76.5%)   ...
   TOTAL: 761376 -> ~320000 tokens  (-58%)
```

vs current output (no limit passed):

```
   TOTAL: 1194239 -> 761376 tokens  (-36.2%)
```

---

## 6. Expected Impact on processaERP-008

| Metric                   | Before (ISSUE-002) | After (Foundry + BC-scope) |
| ------------------------ | ------------------ | -------------------------- |
| Total compressed tokens  | 761,376            | ~320,000 (all artifacts)   |
| Tokens per subagent call | 761,376            | ~100K–280K (per BC)       |
| Largest gap (subagent)   | 62 min             | ~10–15 min (estimated)    |
| Wall time F1             | ~110 min           | ~30–40 min (estimated)    |
| F1 artifact completion   | 58% (11/19)        | 100% expected              |

---

## 7. References

- `C:\Desenv\repo\tool\ast\imfai-ava-tools\ava-fabric-delphi-analyzer\headroom_precompress.py`
- `docs/issues/ISSUE-002-agent-stuck-pipeline-performance.md`
- `docs/issues/perf_pipeline_ntp.py`
- Headroom 0.30.0 — `HeadroomClient`, `OpenAIProvider`, `headroom.compress()`
- Azure AI Foundry docs: `https://learn.microsoft.com/azure/ai-foundry/`
