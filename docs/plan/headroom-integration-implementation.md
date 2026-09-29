# Plano de Implementação — Integração do Headroom no imfai-ava-fabric-apps-agents

**Repositório**: `C:\Desenv\repo\branch_develop_bugfix_23.07\imfai-ava-fabric-apps-agents`
**Branch**: `develop`
**Referência de padrão**: `imfai-ava-fabric-data-agents` — commit `63090a4` (PR 314)
**Documentos relacionados**: [ISSUE-002](../issues/ISSUE-002-agent-stuck-pipeline-performance.md) · [GUIDE Headroom + Foundry](../issues/GUIDE-headroom-foundry-endpoint.md)

---

## Contexto

O Headroom **já roda neste pipeline**, mas **fora do repositório**. A compressão acontece dentro do analisador AST externo (`C:\Desenv\repo\tool\ast\imfai-ava-tools\ava-fabric-delphi-analyzer`), que grava artefatos comprimidos em `projects/{project}/outputs/asis/delphi-ast-raw/compressed/`. O repositório apenas **consome** esse diretório.

Isso significa que este plano **não é** "adicionar Headroom do zero" — é **internalizar, corrigir e ampliar** uma integração que hoje é parcial, não configurável e comprovadamente insuficiente (ISSUE-002: pipeline travado por 110 min, 8 de 19 artefatos F1 não produzidos).

### Estado atual medido (processaERP-008, execução de 2026-07-28)

| Evidência                                        | Valor                                                                     |
| ------------------------------------------------- | ------------------------------------------------------------------------- |
| Artefatos AST brutos (`extraction/`)            | 6,99 MB — 9 arquivos                                                     |
| Artefatos comprimidos (`compressed/`)           | 2,67 MB — 9 arquivos +`manifest.json` + `metrics.jsonl`              |
| Tokens antes → depois                            | **1.194.239 → 761.376 (-36,2%)**                                   |
| Duração da compressão                          | 7.157 ms                                                                  |
| Modelo usado na compressão                       | `claude-sonnet-4-5-20250929`                                            |
| `headroom-ai` instalado no `.venv` do repo    | ❌**Não** (só `pytest`, `PyYAML`, `playwright`, `allure`) |
| `requirements.txt` / `pyproject.toml` na raiz | ❌**Não existem**                                                  |
| Bloco MCP no`.vscode/settings.json`             | ❌ Ausente (existe`chat.mcp.autostart: true`, sem `mcp.servers`)      |

**Redução por artefato** (de `compressed/manifest.json`):

| Artefato                   | tokens_in |        tokens_out | Redução | Transform aplicado            |
| -------------------------- | --------: | ----------------: | --------: | ----------------------------- |
| `01_business_rules`      |   273.126 |           128.743 |    -52,9% | `router:mixed:0.06`         |
| `02_form_business_rules` |    77.080 |            65.918 |    -14,5% | `router:smart_crusher:0.00` |
| `03_database_rules`      |    25.441 |            19.407 |    -23,7% | `router:smart_crusher:0.00` |
| `04_database_schemas`    |   141.453 |           112.753 |    -20,3% | `router:smart_crusher:0.00` |
| `05_procedures`          |   662.447 | **426.984** |    -35,5% | `router:smart_crusher:0.04` |
| `06_integrations`        |       452 |               417 |     -7,7% | `router:smart_crusher:0.09` |
| `07_apis`                |       429 |               401 |     -6,5% | `router:smart_crusher:0.10` |
| `08_code_overview`       |    13.559 |             6.516 |    -51,9% | `router:smart_crusher:0.00` |
| `09_test_coverage`       |       252 |               237 |     -6,0% | `router:smart_crusher:0.25` |

### Por que 36,2% não resolve

O `runSubagent` do `ava-asis-solution-delphi` carrega **os 9 artefatos** (761K tokens) em toda chamada. Somando spec do agente + resultados de ferramenta, cada turno processa 800K+ tokens. Resultado documentado na ISSUE-002: chamadas de subagente de **34 min, 5 min e 62 min**, e 42% dos artefatos F1 nunca gerados.

**O gargalo não é a taxa de compressão — é o escopo.** Comprimir mais não resolve; entregar a cada agente só o que ele precisa, sim.

---

## Análise — as 7 lacunas a fechar

| #            | Lacuna                                                                                                                                                                                                   | Evidência no código                                                                                                              | Impacto                                                             |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| **L1** | **Limite de modelo errado.** A compressão mira a janela do Claude (200K) enquanto a inferência real roda em Azure Foundry. Sem `model_limit`, o Headroom só aplica transformação estrutural | `headroom_precompress.py` → `DEFAULT_MODEL = "claude-sonnet-4-5-20250929"`, `compress(..., config=cfg)` sem `model_limit` | Perde-se a compressão proporcional — 36% em vez de ~58%           |
| **L2** | **Sem fatiamento por agente.** Todos os agentes recebem os 9 artefatos                                                                                                                             | `orchestrator-asis.md` despacha sem `scope_filter`                                                                             | Causa raiz RC-1 da ISSUE-002                                        |
| **L3** | **Decodificador do formato Headroom duplicado e frágil.** O unwrap de `__headroom__: factored_array` está inline                                                                               | `build_summary_comprehensive.py:3425-3428`                                                                                       | Cada novo consumidor reimplementa — fonte de bug                   |
| **L4** | **Consumidor forçado a ler o bruto.** O `sql_ir_generator` teve de voltar para `extraction/` porque a compactação quebra o parsing dict                                                     | `sql_ir_generator.py:504-508` (comentário explícito)                                                                           | Anula o ganho de compressão nesse caminho                          |
| **L5** | **Dependência não declarada.** Não há `requirements.txt` na raiz; `headroom-ai` só existe no `requirements.txt` do analisador externo (`headroom-ai[all]>=0.22`)                      | `ls requirements*.txt` → não encontrado                                                                                        | Ambiente não reprodutível; versão divergente (guia cita 0.30.0)  |
| **L6** | **Sem gate de threshold nem retry guard**                                                                                                                                                          | ISSUE-002 M-2 e M-4 — propostos, não implementados                                                                               | Retry storm (3 dispatches em 16s) e overload                        |
| **L7** | **MCP não registrado.** Agentes não têm `headroom_compress` / `retrieve` / `perf` em runtime                                                                                              | `.vscode/settings.json` sem bloco `mcp.servers`                                                                                | Compressão só é possível offline, nunca sob demanda pelo agente |

---

## Plano de implementação — passo a passo

Ordem deliberada: **fundação → correção de precisão → fatiamento (maior ROI) → governança → observabilidade**. Cada fase é independentemente entregável e reversível.

---

### FASE 0 — Baseline mensurável (obrigatória antes de mudar qualquer coisa)

**Objetivo**: congelar o número contra o qual todo o resto será comparado.

```powershell
cd "C:\Desenv\repo\branch_develop_bugfix_23.07\imfai-ava-fabric-apps-agents"

# 1. Registrar o baseline atual a partir do manifest existente
python docs/issues/perf_pipeline_ntp.py --project processaERP-008 > docs/issues/baseline-processaERP-008.txt

# 2. Copiar o manifest de referência
Copy-Item projects/processaERP-008/outputs/asis/delphi-ast-raw/compressed/manifest.json `
          docs/issues/baseline-manifest-processaERP-008.json
```

**Saída esperada** (já conhecida): `TOTAL: 1194239 → 761376 tokens (-36.2%)`, wall time F1 ≈ 110 min, 11/19 artefatos.

> ✅ **DoD F0**: baseline versionado em `docs/issues/`. Sem isso, nenhuma fase seguinte tem como provar ganho.

---

### FASE 1 — Fundação: declarar a dependência e centralizar o acesso

#### Passo 1.1 — Criar `requirements.txt` na raiz

Hoje não existe. Criar declarando o Headroom como **opcional**, alinhado com a versão que o guia Foundry referencia (0.30.0):

```txt
# imfai-ava-fabric-apps-agents — Python dependencies

# Core
pyyaml>=6.0
pytest>=8.0

# QA / automated tests
pytest-playwright>=0.7
allure-pytest>=2.15

# Context compression — OPCIONAL. Sem ele, todo o pipeline funciona
# com fallback SmartCrusher-lite (ver headroom_precompress.py modo [B]).
headroom-ai[all]>=0.30.0
```

> ⚠️ **Alinhar versão com o analisador externo.** O `requirements.txt` do `ava-fabric-delphi-analyzer` fixa `headroom-ai[all]>=0.22`, mas o guia Foundry documenta APIs de 0.30.0 (`HeadroomClient`, `OpenAIProvider`). Subir os dois para `>=0.30.0` na mesma PR — senão `model_limit` e `res.transforms_applied` podem não existir.

#### Passo 1.2 — Criar o helper compartilhado `src/shared/utils/headroom_context.py`

Este é o **núcleo da internalização**. Resolve L3, L4 e dá base para L1 e L2. Vai em `src/shared/utils/` junto dos 13 módulos já existentes.

```python
"""headroom_context.py — camada única de acesso aos artefatos comprimidos pelo Headroom.

Resolve três problemas recorrentes do pipeline:
  1. Decodificar os formatos que o Headroom emite (factored_array, _compaction: table)
     sem que cada consumidor reimplemente o unwrap.
  2. Montar o contexto por agente (fatiamento) em vez de carregar os 9 artefatos.
  3. Comprimir sob demanda mirando o limite REAL do modelo em produção (Foundry).

Degrada graciosamente: sem `headroom-ai` instalado, tudo continua funcionando —
a leitura/decodificação não depende do pacote, só a compressão sob demanda depende.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

try:
    from headroom import compress, CompressConfig
    HEADROOM_AVAILABLE = True
except ImportError:
    HEADROOM_AVAILABLE = False

# ── Configuração centralizada (resolve L1) ──────────────────────────────────
# NUNCA hardcode o modelo. A compressão precisa mirar a janela do modelo que
# de fato executa a inferência (Azure Foundry), não a do Claude.
HEADROOM_MODEL = os.environ.get("AVA_FOUNDRY_MODEL", "claude-sonnet-4-5-20250929")
HEADROOM_LIMIT = int(os.environ.get("AVA_FOUNDRY_CONTEXT_LIMIT", "200000"))

# Threshold da ISSUE-002 M-2 — acima disso, orquestrador usa modo inline
INLINE_MODE_THRESHOLD = int(os.environ.get("AVA_INLINE_MODE_THRESHOLD", "400000"))

# ── Mapa artefato → agente (resolve L2; fonte: ISSUE-002 § M-1) ─────────────
AGENT_ARTIFACT_MAP: dict[str, list[str]] = {
    "ava-asis-solution-delphi": ["01_business_rules", "02_form_business_rules", "08_code_overview"],
    "ava-asis-db-analyzer":     ["03_database_rules", "04_database_schemas", "05_procedures"],
    "ava-asis-documentation":   ["01_business_rules", "02_form_business_rules", "08_code_overview"],
    "ava-asis-inventory":       ["08_code_overview"],
    "ava-asis-gaps-risks":      ["01_business_rules", "03_database_rules", "08_code_overview"],
    "ava-asis-events-pubsub":   ["02_form_business_rules", "06_integrations", "07_apis"],
    "ava-asis-test-qa":         ["09_test_coverage", "08_code_overview"],
    "ava-asis-security-review": ["01_business_rules", "03_database_rules", "07_apis"],
}


# ── 1. Decodificação (resolve L3 e L4) ──────────────────────────────────────
def decode_headroom(node: Any) -> Any:
    """Reverte os formatos de compactação do Headroom, recursivamente.

    Trata os dois formatos observados em produção:
      - {"__headroom__": "factored_array", "schema": [...], "rows": [[...]]}
      - {"_compaction": "table", ...} — re-encode CSV-like que quebrou o
        sql_ir_generator (ver sql_ir_generator.py:504-508)

    Idempotente: dados não compactados passam intactos.
    """
    if isinstance(node, dict):
        if node.get("__headroom__") == "factored_array":
            schema = node.get("schema", [])
            return [dict(zip(schema, row)) for row in node.get("rows", [])]
        if node.get("_compaction") == "table":
            schema = node.get("schema") or node.get("columns", [])
            rows = node.get("rows", [])
            return [dict(zip(schema, r)) for r in rows]
        return {k: decode_headroom(v) for k, v in node.items()}
    if isinstance(node, list):
        return [decode_headroom(item) for item in node]
    return node


def read_artifact(project: str, artifact: str, *, prefer_compressed: bool = True) -> dict:
    """Lê um artefato AST já decodificado — o consumidor nunca vê formato Headroom.

    Com isto, `sql_ir_generator` pode voltar a ler de `compressed/` (resolve L4).
    """
    base = Path(f"projects/{project}/outputs/asis/delphi-ast-raw")
    order = ["compressed", "extraction"] if prefer_compressed else ["extraction", "compressed"]

    for sub in order:
        fp = base / sub / f"{artifact}.json"
        if fp.exists():
            return decode_headroom(json.loads(fp.read_text(encoding="utf-8")))

    raise FileNotFoundError(f"artefato AST ausente: {artifact} (projeto {project})")


# ── 2. Fatiamento de contexto por agente (resolve L2) ───────────────────────
def build_agent_context(agent_name: str, project: str) -> list[dict]:
    """Retorna apenas os artefatos que ESTE agente precisa, prontos para o prompt.

    Reduz o payload por subagente de 761K para 100K–280K tokens (ISSUE-002 § M-1).
    """
    base = Path(f"projects/{project}/outputs/asis/delphi-ast-raw/compressed")
    needed = AGENT_ARTIFACT_MAP.get(agent_name, [])

    messages = []
    for art in needed:
        fp = base / f"{art}.json"
        if fp.exists():
            messages.append({"role": "user", "content": fp.read_text(encoding="utf-8")})

    if not messages or not HEADROOM_AVAILABLE:
        return messages

    cfg = CompressConfig(
        compress_user_messages=True,
        protect_recent=1,
        min_tokens_to_compress=200,
    )
    result = compress(messages, model=HEADROOM_MODEL, model_limit=HEADROOM_LIMIT, config=cfg)
    return result.messages


# ── 3. Leitura de métricas e decisão de modo (resolve L6) ───────────────────
def read_compression_metrics(project: str) -> dict:
    """Lê compressed/manifest.json — totais de tokens da última extração."""
    fp = Path(f"projects/{project}/outputs/asis/delphi-ast-raw/compressed/manifest.json")
    if not fp.exists():
        return {"tokens_in": 0, "tokens_out": 0, "reduction_pct": 0.0}
    return json.loads(fp.read_text(encoding="utf-8")).get("totals", {})


def resolve_execution_mode(project: str) -> str:
    """'inline' ou 'subagent', conforme o threshold da ISSUE-002 § M-2."""
    tokens_out = read_compression_metrics(project).get("tokens_out", 0)
    return "inline" if tokens_out > INLINE_MODE_THRESHOLD else "subagent"


def estimate_agent_tokens(agent_name: str, project: str) -> int:
    """Soma tokens_out dos artefatos que este agente carrega — para logging/gate."""
    fp = Path(f"projects/{project}/outputs/asis/delphi-ast-raw/compressed/manifest.json")
    if not fp.exists():
        return 0
    manifest = json.loads(fp.read_text(encoding="utf-8"))
    needed = set(AGENT_ARTIFACT_MAP.get(agent_name, []))
    return sum(a.get("tokens_out", 0) for a in manifest.get("artifacts", [])
               if a.get("artifact") in needed)
```

#### Passo 1.3 — Testes em `tests/utils/test_headroom_context.py`

O repo já tem `tests/utils/` (com `test_sql_ir_generator.py`). Cobrir **os dois ramos** — foi exatamente o que faltou na implementação de referência do `data-agents` (lá, `grep "compressed" tests/` retorna zero).

```python
import json
import pytest
from src.shared.utils import headroom_context as hc


def test_decode_factored_array():
    node = {"__headroom__": "factored_array",
            "schema": ["name", "loc"],
            "rows": [["UnitA", 120], ["UnitB", 80]]}
    assert hc.decode_headroom(node) == [
        {"name": "UnitA", "loc": 120},
        {"name": "UnitB", "loc": 80},
    ]


def test_decode_is_idempotent_on_plain_data():
    plain = {"payload": {"totals": {"units_total": 363}}}
    assert hc.decode_headroom(plain) == plain


def test_decode_nested():
    node = {"payload": {"stored_procedures": {
        "__headroom__": "factored_array", "schema": ["n"], "rows": [["sp_a"]]}}}
    assert hc.decode_headroom(node)["payload"]["stored_procedures"] == [{"n": "sp_a"}]


def test_execution_mode_inline_above_threshold(tmp_path, monkeypatch):
    # 761_376 > 400_000 → inline (cenário real do processaERP-008)
    _write_manifest(tmp_path, tokens_out=761_376)
    monkeypatch.chdir(tmp_path)
    assert hc.resolve_execution_mode("P") == "inline"


def test_execution_mode_subagent_below_threshold(tmp_path, monkeypatch):
    _write_manifest(tmp_path, tokens_out=120_000)
    monkeypatch.chdir(tmp_path)
    assert hc.resolve_execution_mode("P") == "subagent"


def test_build_agent_context_without_headroom(monkeypatch, tmp_path):
    """Sem headroom instalado, retorna os artefatos crus — não pode quebrar."""
    monkeypatch.setattr(hc, "HEADROOM_AVAILABLE", False)
    monkeypatch.chdir(tmp_path)
    _write_artifacts(tmp_path, ["08_code_overview"])
    msgs = hc.build_agent_context("ava-asis-inventory", "P")
    assert len(msgs) == 1


def test_build_agent_context_only_loads_mapped_artifacts(monkeypatch, tmp_path):
    """inventory carrega 1 artefato, não 9 — o coração da correção da ISSUE-002."""
    monkeypatch.setattr(hc, "HEADROOM_AVAILABLE", False)
    monkeypatch.chdir(tmp_path)
    _write_artifacts(tmp_path, [f"0{i}_x" for i in range(1, 10)] + ["08_code_overview"])
    assert len(hc.build_agent_context("ava-asis-inventory", "P")) == 1
```

> ✅ **DoD F1**: `requirements.txt` criado · `headroom_context.py` em `src/shared/utils/` · testes verdes **com e sem** `headroom-ai` instalado.

---

### FASE 2 — Corrigir a precisão da compressão (L1)

**Ganho esperado: -36,2% → ~-58%**, conforme projeção da seção 5 do [GUIDE Foundry](../issues/GUIDE-headroom-foundry-endpoint.md).

#### Passo 2.1 — Parametrizar o analisador externo

No arquivo `C:\Desenv\repo\tool\ast\imfai-ava-tools\ava-fabric-delphi-analyzer\src\headroom_precompress.py`:

```python
# ANTES (linha ~25)
DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

# DEPOIS — lê do ambiente, mantém o default atual como fallback
import os
DEFAULT_MODEL = os.environ.get("AVA_FOUNDRY_MODEL", "claude-sonnet-4-5-20250929")
DEFAULT_LIMIT = int(os.environ.get("AVA_FOUNDRY_CONTEXT_LIMIT", "200000"))
```

E em `_compress_with_headroom()` — a mudança que de fato destrava a compressão proporcional:

```python
# ANTES
res = compress([{"role": "user", "content": wrapped}], model=model, config=cfg)

# DEPOIS
res = compress([{"role": "user", "content": wrapped}], model=model,
               model_limit=DEFAULT_LIMIT, config=cfg)
```

> ⚠️ **Repositório diferente.** Essa alteração é fora do `imfai-ava-fabric-apps-agents`. Exige PR separada no `imfai-ava-tools` e alinhamento de release entre os dois repos. Registrar a dependência no work item.

#### Passo 2.2 — Propagar as variáveis a partir do wrapper do repo

Em `src/modules/ava-fabric-agents/asis-diagnostic/utils/run_delphi_ast_analysis.py` — o `subprocess.Popen` (linha ~99) já monta um `env`; adicionar a propagação:

```python
env = os.environ.copy()
env.setdefault("AVA_FOUNDRY_MODEL", os.environ.get("AVA_FOUNDRY_MODEL", "claude-sonnet-4-5-20250929"))
env.setdefault("AVA_FOUNDRY_CONTEXT_LIMIT", os.environ.get("AVA_FOUNDRY_CONTEXT_LIMIT", "200000"))
env.setdefault("HEADROOM_DETECT_BACKEND", "rust")   # Windows — evita Magika pure-Python
```

#### Passo 2.3 — Validar contra o baseline

```powershell
$env:AVA_FOUNDRY_MODEL         = "gpt-4o"
$env:AVA_FOUNDRY_CONTEXT_LIMIT = "128000"
$env:HEADROOM_DETECT_BACKEND   = "rust"

python src/modules/ava-fabric-agents/asis-diagnostic/utils/run_delphi_ast_analysis.py --project processaERP-008

# Comparar com o baseline da FASE 0
python docs/issues/perf_pipeline_ntp.py --project processaERP-008
```

**Critério de aceite**: `manifest.json` → `totals.reduction_pct >= 50` (baseline: 36,2).

> ✅ **DoD F2**: modelo/limite vêm de ambiente · redução ≥ 50% medida · `metrics.jsonl` registra o modelo efetivo.

---

### FASE 3 — Fatiamento por agente (L2) — **maior ROI**

Esta é a fase que resolve a causa raiz RC-1 da ISSUE-002. Ataca o problema certo: **escopo**, não taxa.

#### Passo 3.1 — Instrumentar o orquestrador

Em `src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md`, antes do bloco de dispatch:

```markdown
### Pré-dispatch — Escopo de contexto e modo de execução (Headroom)

1. LER `projects/{project_name}/outputs/asis/delphi-ast-raw/compressed/manifest.json`
   → `totals.tokens_out`

2. DEFINIR modo de execução (ISSUE-002 § M-2):
   SE `totals.tokens_out > 400000`  → execution_mode = "inline"
   SENÃO                            → execution_mode = "subagent"
   LOG "Headroom: {tokens_out} tokens → modo {execution_mode}"

3. PARA CADA agente a despachar, montar contexto FATIADO
   (nunca passar os 9 artefatos — ISSUE-002 § M-1):

   | Agente                    | Artefatos                | ~tokens |
   |---------------------------|--------------------------|--------:|
   | ava-asis-solution-delphi  | 01, 02, 08               |    201K |
   | ava-asis-db-analyzer      | 03, 04, 05               |    559K |
   | ava-asis-documentation    | 01, 02, 08               |    201K |
   | ava-asis-inventory        | 08                       |      7K |
   | ava-asis-gaps-risks       | 01, 03, 08               |    155K |
   | ava-asis-events-pubsub    | 02, 06, 07               |     67K |
   | ava-asis-test-qa          | 09, 08                   |      7K |
   | ava-asis-security-review  | 01, 03, 07               |    149K |

   Fonte de verdade: `AGENT_ARTIFACT_MAP` em `src/shared/utils/headroom_context.py`
   — a tabela acima é espelho; ao divergir, o Python vence.

4. RETRY GUARD (ISSUE-002 § M-4) — antes de cada dispatch:
   SE todos os artefatos de saída esperados do agente JÁ EXISTEM:
     LOG "Skip {agent} — output já presente"
     PULAR o dispatch
   SENÃO despachar.
```

#### Passo 3.2 — Instrumentar os agentes consumidores

Nos 8 agentes mapeados (`solution-delphi.md`, `db-analyzer/db-analyzer.md`, `documentation-asis.md`, `inventory-asis.md`, `gaps-risks-asis.md`, `events-pubsub-asis.md`, `test-qa-asis.md`, `security-review-asis.md`), substituir a leitura ampla de `delphi-ast-raw/compressed/` por leitura explícita dos artefatos mapeados:

```markdown
### Entrada de contexto AST (Headroom)

LER **apenas** os artefatos deste agente:
  - `compressed/01_business_rules.json`
  - `compressed/02_form_business_rules.json`
  - `compressed/08_code_overview.json`

NÃO ler os demais artefatos de `compressed/` — cada um adicional custa
dezenas ou centenas de milhares de tokens ao contexto (ver ISSUE-002 § RC-1).

Para decodificar formatos Headroom (`__headroom__: factored_array`,
`_compaction: table`), usar:
  `from src.shared.utils.headroom_context import read_artifact`
  `data = read_artifact(project_name, "01_business_rules")`
NUNCA fazer parsing manual — ver lacuna L3.
```

#### Passo 3.3 — Escopo por Bounded Context para o `db-analyzer` (ISSUE-002 § M-3)

Mesmo fatiado, `ava-asis-db-analyzer` fica em ~559K tokens — ainda acima do threshold de 400K. Para esse agente (e só para ele), aplicar escopo por BC usando o `module-partition.json` já produzido pelo `module_partitioner.py`:

```python
# extensão de headroom_context.py
def build_bc_scoped_context(agent_name: str, project: str, bc_name: str) -> list[dict]:
    """Contexto de um único bounded context — mantém cada chamada < 100K tokens."""
    partition = json.loads(
        Path(f"projects/{project}/outputs/asis/module-partition.json").read_text(encoding="utf-8"))
    units = {u for bc in partition.get("bounded_contexts", [])
             if bc.get("name") == bc_name for u in bc.get("units", [])}

    messages = []
    for art in AGENT_ARTIFACT_MAP.get(agent_name, []):
        data = read_artifact(project, art)
        filtered = _filter_by_units(data, units)   # filtra payload pelas units do BC
        messages.append({"role": "user", "content": json.dumps(filtered, ensure_ascii=False)})

    if not HEADROOM_AVAILABLE:
        return messages
    cfg = CompressConfig(compress_user_messages=True, protect_recent=1, min_tokens_to_compress=200)
    return compress(messages, model=HEADROOM_MODEL, model_limit=HEADROOM_LIMIT, config=cfg).messages
```

**Projeção de impacto** (partindo dos números reais do manifest):

| Agente                       | Hoje |                 Após F3 | Redução |
| ---------------------------- | ---: | -----------------------: | --------: |
| `ava-asis-solution-delphi` | 761K |           **201K** |      -74% |
| `ava-asis-db-analyzer`     | 761K | 559K →**~90K/BC** |      -88% |
| `ava-asis-documentation`   | 761K |           **201K** |      -74% |
| `ava-asis-inventory`       | 761K |             **7K** |      -99% |
| `ava-asis-test-qa`         | 761K |             **7K** |      -99% |

> ✅ **DoD F3**: nenhum subagente recebe > 400K tokens · retry guard ativo · `AGENT_ARTIFACT_MAP` é fonte única.

---

### FASE 4 — Reconectar os consumidores ao `compressed/` (L3, L4)

#### Passo 4.1 — `sql_ir_generator.py`

Hoje lê de `extraction/` por causa da compactação (comentário em `sql_ir_generator.py:504-508`). Com `decode_headroom()` disponível, volta a ler de `compressed/`:

```python
# ANTES — precisa ler o bruto porque a compactação quebra table.get(...)
# NOTE: must read from `extraction/` (raw JSON), NOT `compressed/` ...

# DEPOIS
from src.shared.utils.headroom_context import read_artifact
data = read_artifact(self.project_name, "04_database_schemas")   # já decodificado
```

Ganho: 893 KB → 394 KB de I/O nesse caminho, sem perda de fidelidade — `decode_headroom` é lossless para `factored_array`.

> ⚠️ **Verificar antes de trocar**: rodar `tests/utils/test_sql_ir_generator.py` e comparar o `sql-ir.json` gerado byte a byte contra a versão atual. Se divergir, o Headroom aplicou transform **lossy** naquele artefato — nesse caso manter `extraction/` e documentar a exceção.

#### Passo 4.2 — `build_summary_comprehensive.py`

Remover o unwrap inline das linhas 3425-3428 e usar o helper:

```python
# ANTES
if isinstance(raw_sps, dict) and raw_sps.get("__headroom__") == "factored_array":
    schema = raw_sps.get("schema", [])
    raw_sps = [dict(zip(schema, row)) for row in raw_sps.get("rows", [])]

# DEPOIS
from src.shared.utils.headroom_context import decode_headroom
raw_sps = decode_headroom(raw_sps)
```

> ✅ **DoD F4**: zero unwrap manual de formato Headroom no repositório (`grep -rn "__headroom__" src/` só encontra `headroom_context.py`).

---

### FASE 5 — MCP em runtime (L7)

Dá aos agentes a capacidade de comprimir **sob demanda**, não só no pré-processamento.

#### Passo 5.1 — Instalar e registrar

```powershell
.\.venv\Scripts\Activate.ps1
pip install "headroom-ai[all]>=0.30.0"
headroom --version          # esperado: 0.30.0+
headroom mcp install
```

#### Passo 5.2 — Versionar o bloco MCP no `.vscode/settings.json`

O arquivo já existe e já tem `chat.mcp.autostart: true`. Adicionar **preservando** o conteúdo atual:

```jsonc
{
    "chat.tools.terminal.autoApprove": { /* ...manter como está... */ },
    "livePreview.defaultPreviewPath": "/projects/database-comparer-examples/outputs/summary/AVA-FABRIC-SUMMARY-database-comparer-examples-2026-04-09.html",
    "chat.mcp.autostart": true,
    "files.associations": {
        "**/summary/templates/html/summary-template.html": "plaintext"
    },

    // ── Headroom MCP — expõe compress/retrieve/perf aos agentes ──
    "mcp": {
        "servers": {
            "headroom": {
                "command": "headroom",
                "args": ["mcp", "serve"],
                "env": {
                    "AVA_FOUNDRY_MODEL": "${env:AVA_FOUNDRY_MODEL}",
                    "AVA_FOUNDRY_CONTEXT_LIMIT": "${env:AVA_FOUNDRY_CONTEXT_LIMIT}",
                    "HEADROOM_DETECT_BACKEND": "rust"
                }
            }
        }
    }
}
```

> ⚠️ **Versionar o resultado no git.** Na implementação de referência do `data-agents`, `.vscode/settings.json` é citado como fonte da config MCP em 5 documentos — e **nunca foi commitado**. A camada MCP lá está documentada, não entregue. Não repetir.

**Ferramentas disponibilizadas**: `headroom_compress` · `headroom_retrieve` · `headroom_perf`.

> ✅ **DoD F5**: bloco MCP commitado · agente confirma acesso a `headroom_compress` em sessão real.

---

### FASE 6 — Observabilidade

#### Passo 6.1 — Registrar métricas por agente no `metrics.jsonl`

Estender o log já produzido (`compressed/metrics.jsonl`) com a decisão de escopo:

```python
# ao final de cada dispatch, no orquestrador
{
  "run_id": "...", "agent": "ava-asis-db-analyzer",
  "artifacts_loaded": ["03_database_rules", "04_database_schemas", "05_procedures"],
  "tokens_scoped": 559144, "tokens_full": 761376, "scope_reduction_pct": 26.6,
  "execution_mode": "inline", "bc_scoped": true, "bc_count": 16
}
```

#### Passo 6.2 — Medir savings reais em produção

```powershell
headroom proxy      # terminal dedicado, durante toda a execução F1
headroom perf       # métricas acumuladas ao final
```

> ✅ **DoD F6**: `metrics.jsonl` registra escopo e modo por agente · comparação F0 vs F6 documentada.

---

### FASE 7 — Documentação

| Documento                                                                               | O que atualizar                                                                   |
| --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| [`docs/full-pipeline-guide.md`](../full-pipeline-guide.md)                             | Seção "Compressão de contexto" — threshold de 400K e modo inline              |
| [`docs/guia-execucao-fluxo-agentes.md`](../guia-execucao-fluxo-agentes.md)             | Passo opcional de ativação + variáveis`AVA_FOUNDRY_*`                        |
| [`docs/asis-diagnostic-io-map.md`](../asis-diagnostic-io-map.md)                       | Coluna de artefatos AST consumidos por agente (espelho do`AGENT_ARTIFACT_MAP`)  |
| [`.github/copilot-instructions.md`](../../.github/copilot-instructions.md)             | Convenção:*nunca carregar os 9 artefatos AST; usar `build_agent_context()`* |
| [`docs/issues/ISSUE-002-...`](../issues/ISSUE-002-agent-stuck-pipeline-performance.md) | Marcar M-1, M-2, M-3, M-4 como implementados, com o número medido                |

---

## Pré-requisitos

### Técnicos

| # | Requisito                                    | Verificação                                        | Bloqueante                                |
| - | -------------------------------------------- | ---------------------------------------------------- | ----------------------------------------- |
| 1 | Python 3.10+ (repo usa 3.13)                 | `python --version`                                 | ✅ Sim                                    |
| 2 | `.venv` ativo                              | prompt mostra`(.venv)`                             | ✅ Sim                                    |
| 3 | Analisador AST externo acessível            | `AVA_DELPHI_ANALYZER_HOME` configurado             | ✅ Sim — sem ele não há`compressed/` |
| 4 | `headroom-ai[all]>=0.30.0`                 | `headroom --version`                               | ❌ Não — fallback SmartCrusher-lite     |
| 5 | `HEADROOM_DETECT_BACKEND=rust` no Windows  | evita Magika pure-Python                             | ❌ Não — mas evita lentidão            |
| 6 | Endpoint Foundry conhecido (modelo + janela) | `AVA_FOUNDRY_MODEL`, `AVA_FOUNDRY_CONTEXT_LIMIT` | ⚠️ Para a FASE 2                        |
| 7 | Acesso de escrita ao repo`imfai-ava-tools` | PR no analisador externo                             | ⚠️ Para a FASE 2                        |

### Variáveis de ambiente

| Variável                     | Descrição                                   | Exemplo                                                                |
| ----------------------------- | --------------------------------------------- | ---------------------------------------------------------------------- |
| `AVA_FOUNDRY_MODEL`         | Nome do deployment usado pelos agentes        | `gpt-4o`                                                             |
| `AVA_FOUNDRY_CONTEXT_LIMIT` | Janela real do modelo (tokens)                | `128000`                                                             |
| `AVA_INLINE_MODE_THRESHOLD` | Corte para modo inline                        | `400000`                                                             |
| `HEADROOM_DETECT_BACKEND`   | Backend do Magika — usar`rust` no Windows  | `rust`                                                               |
| `HEADROOM_DEFAULT_MODE`     | `audit` (só loga) ou `optimize` (trunca) | `optimize`                                                           |
| `AVA_DELPHI_ANALYZER_HOME`  | Raiz do analisador AST externo                | `C:\Desenv\repo\tool\ast\imfai-ava-tools\ava-fabric-delphi-analyzer` |

### Arquiteturais

1. **Degradação graciosa é requisito, não cortesia.** Todo caminho precisa rodar sem `headroom-ai` — o `headroom_precompress.py` já tem o modo `[B]` SmartCrusher-lite; o helper novo precisa manter a mesma garantia.
2. **`AGENT_ARTIFACT_MAP` é fonte única.** As tabelas nos `.md` são espelhos; ao divergir, o Python vence.
3. **Artefatos em `outputs/` permanecem íntegros.** A compressão afeta só o **contexto do agente** — nunca o entregável do cliente.
4. **Compressão lossy exige verificação por artefato.** `sql_ir_generator` já provou que nem todo transform é seguro para parsing programático (L4).

---

## Cronograma e esforço

| Fase         | Entrega                                                 | Esforço | Risco                                              | Depende de |
| ------------ | ------------------------------------------------------- | -------: | -------------------------------------------------- | ---------- |
| **F0** | Baseline versionado                                     |       1h | —                                                 | —         |
| **F1** | `requirements.txt` + `headroom_context.py` + testes |       6h | Baixo                                              | F0         |
| **F2** | Model limit Foundry (2 repos)                           |       4h | **Médio** — PR externa                     | F1         |
| **F3** | Fatiamento por agente + BC scope + retry guard          |      12h | **Médio** — valida qualidade dos artefatos | F1         |
| **F4** | Reconectar`sql_ir_generator` e `summary`            |       4h | Médio — exige diff byte a byte                   | F1         |
| **F5** | MCP versionado                                          |       2h | Baixo                                              | F1         |
| **F6** | Observabilidade                                         |       3h | Baixo                                              | F3         |
| **F7** | Documentação                                          |       3h | —                                                 | F3, F4     |

**Total ≈ 35h.** Caminho crítico: F0 → F1 → F3 (é onde está o ganho da ISSUE-002).

> Se houver só uma janela curta: **F0 + F1 + F3**. Sozinhas, derrubam o maior payload de 761K para ~201K e destravam o pipeline. F2 melhora a taxa, mas não é o gargalo.

---

## Definition of Done

- [ ] Baseline da F0 versionado em `docs/issues/`
- [ ] `requirements.txt` na raiz, com `headroom-ai` explicitamente opcional
- [ ] `src/shared/utils/headroom_context.py` é o **único** ponto que conhece o formato Headroom
- [ ] `grep -rn "__headroom__" src/` retorna **apenas** `headroom_context.py`
- [ ] Testes cobrem os dois ramos (`HEADROOM_AVAILABLE` True e False)
- [ ] **Pipeline F1 completo roda sem `headroom-ai` instalado**, com os mesmos 19 artefatos — *teste de aceite principal*
- [ ] Nenhum subagente recebe > 400K tokens (verificável no `metrics.jsonl`)
- [ ] Retry guard implementado — sem redispatch quando o artefato de saída já existe
- [ ] `.vscode/settings.json` com bloco MCP **commitado**
- [ ] `manifest.json` → `reduction_pct >= 50` (baseline 36,2)
- [ ] Execução completa do `processaERP-008` produz **19/19** artefatos F1 (baseline: 11/19)
- [ ] Wall time F1 medido e comparado contra os 110,6 min do baseline
- [ ] ISSUE-002 atualizada com M-1..M-4 marcados como implementados

---

## Critério de rollback

O desenho é reversível em três níveis independentes:

| Nível                | Como reverter                           | Efeito                                               |
| --------------------- | --------------------------------------- | ---------------------------------------------------- |
| **Compressão** | `pip uninstall headroom-ai`           | Volta ao SmartCrusher-lite; nada quebra              |
| **Fatiamento**  | `AVA_INLINE_MODE_THRESHOLD=999999999` | Todos voltam ao modo subagente com contexto completo |
| **Model limit** | Remover`AVA_FOUNDRY_*` do ambiente    | Volta ao default Claude 200K                         |

**Gatilhos de rollback**: queda na qualidade dos artefatos (bounded contexts incompletos, regras de negócio faltando, placeholders `{{...}}` no summary) ou divergência no `sql-ir.json` após a F4.

Nenhuma reversão exige desfazer código — é a vantagem de manter a integração atrás de import defensivo e variáveis de ambiente.

---

## Referências

- [`docs/issues/ISSUE-002-agent-stuck-pipeline-performance.md`](../issues/ISSUE-002-agent-stuck-pipeline-performance.md) — diagnóstico e mitigações M-1..M-5
- [`docs/issues/GUIDE-headroom-foundry-endpoint.md`](../issues/GUIDE-headroom-foundry-endpoint.md) — patterns A/B/C de integração com Foundry
- [`docs/issues/perf_pipeline_ntp.py`](../issues/perf_pipeline_ntp.py) — script de medição de performance
- `projects/processaERP-008/outputs/asis/delphi-ast-raw/compressed/manifest.json` — métricas reais
- `C:\Desenv\repo\tool\ast\imfai-ava-tools\ava-fabric-delphi-analyzer\src\headroom_precompress.py` — compressor externo
- Padrão de referência: `imfai-ava-fabric-data-agents` commit `63090a4` (PR 314)
