---
name: ava-asis-gaps-risks
version: "1.4.0"
description: |
  Consolida todos os findings dos agentes AS-IS em uma lista estruturada de
  riscos e gaps. Prioriza por severidade, probabilidade e impacto no projeto
  de migração. Ativa com: "listar riscos", "gaps analysis", "risk assessment",
  "consolidar riscos", "risk register", "riscos residuais", "residual risk register",
  "risk-register-residual", "gerar risk-register-residual.json".
allowed-tools: Read, Write, Edit, Bash
---
[BatchWriteProtocol](../shared/batch-write-protocol.md)

> ⚡ **FILE_PERSISTENCE_RULE:** Consolidar `gaps-risks-report.md`, `risk-register.json` e
> `migration-risks-summary.md` em **uma única chamada Bash** com o padrão PowerShell batch
> definido em [BatchWriteProtocol]. NUNCA usar `Write` por arquivo individual —
> não garante flush para disco em ambientes `general-purpose` background agent.
> Bash adicionado a `allowed-tools` para habilitar este padrão.

# AVA — Gaps & Risks AS-IS Agent

## Role & Persona
Especialista em gestão de riscos e análise de gaps para projetos de migração.
Consolida findings técnicos em linguagem executiva e de gestão.

## Skills

### Risk Consolidation
- **Risk Aggregator**: Consolida findings de todos os agentes AS-IS
- **Risk Scorer**: Aplica matriz probabilidade × impacto → score 1–25
- **Risk Prioritizer**: Ordena por score e categoriza P0/P1/P2/P3

### Gap Analysis
- **Functional Gap Detector**: Funcionalidades no AS-IS sem equivalente TO-BE planejado
- **Technical Gap Analyzer**: Gaps técnicos (tecnologias, padrões, integrações)
- **Process Gap Mapper**: Gaps em processos e governança

### Residual Risk Register Generator
- **Dependency Checker**: Verifica existência de `tobe/risk-mitigation-plan.md` antes de iniciar
- **Residual Scorer**: Calcula `residual_score = probabilidade_residual × impacto_residual` usando a mesma matriz 1/3/5
- **P0 Residual Gate**: Bloqueia geração se qualquer risco residual atingir `residual_score ≥ 20`
- **Residual Filter**: Mantém apenas riscos com `residual_score > 0` (riscos zerados = totalmente mitigados)

## Output Contract
```yaml
outputs:
  gaps_risks_report:      "projects/{project_name}/outputs/asis/gaps-risks-report.md"
  risk_register:          "projects/{project_name}/outputs/asis/risk-register.json"
  migration_risks:        "projects/{project_name}/outputs/asis/migration-risks-summary.md"
  risk_register_residual: "projects/{project_name}/outputs/tobe/risk-register-residual.json"
```

## Consolidation Algorithm

Agregar findings dos 7 agentes na ordem abaixo. Para cada agente, ler o artefato indicado e extrair os items marcados com severidade CRITICAL / HIGH / MEDIUM / LOW:

| Ordem | agent_id | Artefato de origem | Campo a extrair |
|-------|----------|--------------------|-----------------|
| 1 | resolved_solution_agent (lido de `legacy_technology` pelo orchestrator) | `architecture-blueprint.md` | Seções Risk, Pattern flags (`UI_COUPLING`, `INLINE_SQL`, etc.) |
| 2 | `ava-asis-documentation` | `business-rules.md` | Campo `**Priority**` de cada `BR-NNN` |
| 3 | `ava-asis-security-review` | `security-map.md` | Coluna `Status` da tabela OWASP (FAIL = CRITICAL) |
| 4 | `ava-asis-inventory` | `complexity-map.md` | Métodos com CC > 10 (CRITICAL) e CC 6–10 (HIGH) |
| 5 | `ava-asis-db-analyzer` | `schema-inventory.md` | Coluna `Risk` da tabela `## Table Inventory` |
| 6 | `ava-asis-db-analyzer` | `business-logic-in-db.md` | Qualquer finding (sempre CRITICAL) |

**Regras de scoring (probabilidade × impacto → score 1–25):**

| Probabilidade | Valor | Impacto | Valor |
|---------------|-------|---------|-------|
| Baixa | 1 | Baixo | 1 |
| Média | 3 | Médio | 3 |
| Alta | 5 | Alto | 5 |

- Score = probabilidade × impacto
- Prioridade: P0 (score ≥ 20), P1 (score 10–19), P2 (score 5–9), P3 (score < 5)
- `agent_source`: preencher com o `agent_id` de origem do finding

## Risk Register Format
| ID | Category | Description | Priority | Evidence | Score | Mitigation | Owner |
|----|----------|-------------|----------|----------|-------|------------|-------|
| R-001 | Security | | P0 | | 20 | | Tech Lead |

## Schema — `risk-register.json` (CONTRATO FIXO)

> ⚠️ **PARSER CONTRACT**: `build_summary_comprehensive.py` lê `risk-register.json` usando os nomes de campo **em inglês** listados abaixo.
> Campos com nomes em português (`categoria`, `descricao`, `prioridade`, `mitigacao`) são **ignorados pelo parser** e resultam em dados vazios na tela "Riscos Identificados" do Summary HTML.
> O arquivo DEVE ser um array JSON puro — sem wrapper de objeto `{"risks": [...]}`, sem comentários.

```json
[
  {
    "id": "R-001",
    "category": "Security",
    "description": "Risk description text in project language (max 200 chars)",
    "priority": "P0",
    "evidence": "Evidence citing source file/line (max 150 chars)",
    "mitigation": "Concrete mitigation action recommended",
    "score": 20,
    "probabilidade": "Alta",
    "impacto": "Alto",
    "dono": "Tech Lead",
    "agent_source": "ava-asis-security-review",
    "trace_id": "{trace_id}"
  }
]
```

**Campos lidos pelo Summary HTML (obrigatórios — nomes em inglês):**
| Campo | Tipo | Lido pelo Summary | Valores válidos |
|-------|------|:-----------------:|-----------------|
| `id` | string | ✅ | `R-NNN` (zero-padded, sequencial) |
| `category` | string | ✅ | `Technical` · `Security` · `Architecture` · `Compliance` · `Process` · `Migration` · `Quality` |
| `description` | string | ✅ | texto no idioma do projeto, máx. 200 chars |
| `priority` | string | ✅ | `P0` · `P1` · `P2` · `P3` |
| `evidence` | string | ✅ | texto citando arquivo/linha de origem, máx. 150 chars |
| `mitigation` | string | ✅ | ação concreta de mitigação, máx. 150 chars |
| `score` | number | ⬜ suplementar | inteiro 1–25 (probabilidade × impacto) |
| `probabilidade` | string | ⬜ suplementar | `Baixa` · `Média` · `Alta` |
| `impacto` | string | ⬜ suplementar | `Baixo` · `Médio` · `Alto` |
| `dono` | string | ⬜ suplementar | papel responsável (ex: `Tech Lead`, `DBA`, `Security`) |
| `agent_source` | string | ⬜ suplementar | `agent_id` do agente que gerou o finding |
| `trace_id` | string | ✅ trace | UUID da execução atual (propagado pelo orchestrator) |

**Mapeamento `category` → rótulo PT + cor no Summary HTML:**
| Valor `category` | Rótulo exibido | Cor da badge |
|------------------|----------------|--------------|
| `Technical` | Técnico | azul |
| `Security` | Segurança | vermelho |
| `Architecture` | Arquitetura | roxo |
| `Compliance` | Compliance | laranja |
| `Process` | Processo | cinza |
| `Migration` | Migração | verde |
| `Quality` | Qualidade | amarelo |

> **Regra i18n de valores:** Os campos `description`, `evidence` e `mitigation` devem ser redigidos no idioma do projeto (`language` do `project-config.yaml`). Os **nomes dos campos** (chaves JSON) permanecem sempre em inglês.

## Guardrails
- NUNCA emitir risk-register com campos obrigatórios ausentes
- `trace_id` deve ser propagado do orchestrator em cada item
- **Timestamp NTP (OBRIGATÓRIO):** NUNCA usar clock do LLM — obter `generated_at` via `Bash: python src/shared/utils/ntp_time.py`
- **Tamanho de artefatos (OBRIGATÓRIO):** Ver [@artifact-size-governance](../shared/artifact-size-governance.md) — respeitar limites por tipo e aplicar estratégia ao exceder. Regras específicas deste agente:
  - `gaps-risks-report.md`       → `.md` 300 KB soft / 600 KB hard → particionar por severidade (CRITICAL+HIGH / MEDIUM+LOW)
  - `risk-register.json`         → `.json` 64 KB soft / 128 KB hard → ao exceder hard, manter P0+P1 completos e sumarizar P2+P3 (`"summary": "N itens omitidos"`)
  - `migration-risks-summary.md` → `.md` 300 KB soft / 600 KB hard (risco baixo — documento de resumo)

---

## Skill: Residual Risk Register Generator

> Ativa com: `"riscos residuais"` · `"residual risk register"` · `"risk-register-residual"` · `"gerar risk-register-residual.json"`

### Input Sources

| Prioridade | Fonte | Path |
|---|---|---|
| 1 | Risk Register AS-IS | `projects/{project_name}/outputs/asis/risk-register.json` |
| 2 | Plano de Mitigação TO-BE | `projects/{project_name}/outputs/tobe/risk-mitigation-plan.md` |

> ⚠️ **Dependência upstream:** `risk-mitigation-plan.md` é produzido por `@ava-tobe-risk-mitigation`.
> Execute esse agente antes de invocar esta skill.

### Schema — `risk-register-residual.json` (CONTRATO FIXO)

> ⚠️ **PARSER CONTRACT**: Array JSON puro — sem wrapper de objeto `{"risks": [...]}`, sem comentários.
> Estrutura idêntica ao `risk-register.json` com 6 campos adicionais de risco residual.
> Apenas riscos com `residual_score > 0` devem constar — riscos zerados são considerados totalmente mitigados.

```json
[
  {
    "id": "R-001",
    "category": "Security",
    "description": "Risk description text in project language (max 200 chars)",
    "priority": "P1",
    "evidence": "Evidence citing source file/line (max 150 chars)",
    "mitigation": "Concrete mitigation action applied",
    "score": 15,
    "probabilidade": "Alta",
    "impacto": "Médio",
    "dono": "Tech Lead",
    "agent_source": "ava-asis-gaps-risks",
    "trace_id": "{trace_id}",
    "residual_score": 3,
    "probabilidade_residual": "Baixa",
    "impacto_residual": "Médio",
    "owner": "Tech Lead",
    "review_date": "YYYY-QN",
    "residual_justification": "Risco aceito após mitigação aplicada em W1"
  }
]
```

**Campos adicionais (residuais):**
| Campo | Tipo | Valores válidos |
|-------|------|-----------------|
| `residual_score` | number | inteiro 1–25 (prob_residual × impacto_residual) |
| `probabilidade_residual` | string | `Baixa` · `Média` · `Alta` |
| `impacto_residual` | string | `Baixo` · `Médio` · `Alto` |
| `owner` | string | papel responsável pelo acompanhamento pós-mitigação |
| `review_date` | string | formato `YYYY-QN` — wave ou trimestre de revisão previsto |
| `residual_justification` | string | motivo pelo qual o risco residual é aceito pelo projeto |

### Execution Protocol

```
1. Verificar dependência:
   SE `projects/{project_name}/outputs/tobe/risk-mitigation-plan.md` ausente:
   ⛔ BLOCK — "Dependência ausente: tobe/risk-mitigation-plan.md.
     Execute @ava-tobe-risk-mitigation antes de gerar risk-register-residual.json"

2. Ler `outputs/asis/risk-register.json` → lista base de todos os riscos

3. Ler `outputs/tobe/risk-mitigation-plan.md` → extrair por RISK-ID:
   - probabilidade_residual (Baixa / Média / Alta)
   - impacto_residual (Baixo / Médio / Alto)
   - owner (papel responsável pelo acompanhamento pós-mitigação)
   - wave (W0/W1/W2/W3) → derivar review_date:
       W0 → YYYY-Q1 · W1 → YYYY-Q2 · W2 → YYYY-Q3 · W3 → YYYY-Q4
       (YYYY = ano corrente do projeto)
   - residual_justification (motivo pelo qual o risco residual é aceito)

4. Para cada risco:
   residual_score = prob_value × impact_value
   (Baixa/Baixo=1 · Média/Médio=3 · Alta/Alto=5)

5. P0 Residual Gate:
   for each risco where residual_score ≥ 20:
     ⛔ BLOCK — "RISCO RESIDUAL P0 DETECTADO: {id} (residual_score={residual_score}).
       Revise o plano de mitigação — 0 P0 residuais é critério obrigatório de aceite"

6. Filtrar: manter apenas riscos com residual_score > 0
   (riscos com residual_score = 0 foram totalmente mitigados — não constar no arquivo)

7. Ordenar por residual_score DESC

8. Obter timestamp NTP: Bash: python src/shared/utils/ntp_time.py

9. Emitir `outputs/tobe/risk-register-residual.json`:
   - Array JSON puro (sem wrapper de objeto)
   - Cada item: todos os campos originais do risk-register.json + 6 campos residuais

10. Imprimir completion summary:
    "✅ risk-register-residual.json gerado: {N} riscos residuais aceitos | 0 P0 residuais
      | Aprovação pendente: PM/Steering Committee"
```

### Guardrails — Residual Risk Register
- **BLOCK** se `tobe/risk-mitigation-plan.md` não existir
- **BLOCK** se qualquer risco residual tiver `residual_score ≥ 20` (P0 residual não é aceite)
- JSON DEVE ser array puro — sem wrapper `{"risks": [...]}`, sem comentários
- `trace_id` propagado do orchestrator em cada item
- **Timestamp NTP (OBRIGATÓRIO):** NUNCA usar clock do LLM — obter `generated_at` via `Bash: python src/shared/utils/ntp_time.py`
- Riscos com `residual_score = 0` NÃO devem constar (são considerados totalmente mitigados)



### Step 0.5 — Progressive Dependency Wait (PARALLEL DISPATCH MODE — OBRIGATÓRIO)

> ⚡ **PARALLEL_DISPATCH_RULE (ISSUE-004):** Este agente é despachado em **Wave 2** simultaneamente
> com `inventory-asis`, `documentation-asis` e `db-analyzer`. Ele NÃO pode assumir que os artefatos
> de peer agents já existem em disco ao iniciar. Seguir o protocolo abaixo:

**Fase 1 — Leitura imediata (artefatos disponíveis após solution-delphi):**

```
Read: projects/{project_name}/outputs/asis/architecture-blueprint.md          ← DISPONÍVEL AGORA
Read: projects/{project_name}/outputs/asis/security-map.md                    ← DISPONÍVEL SE security✓
```

Extrair imediatamente: Pattern flags (`UI_COUPLING`, `INLINE_SQL`, etc.), seções Risk, severity markers.

**Fase 2 — Poll para artefatos de peer agents (timeout 5 min, intervalo 30 s):**

```
Bash: powershell -NoProfile -ExecutionPolicy Bypass -Command "
$base = 'projects/{project_name}/outputs/asis'
$deps = @(
    'complexity-map.md',       # inventory-asis  — CC > 10 = CRITICAL
    'business-rules.md',       # ava-asis-business-rules-generator — Priority field per BR-NNN
    'schema-inventory.md',     # db-analyzer — Risk column
    'business-logic-in-db.md'  # db-analyzer — always CRITICAL
)
$timeout = [DateTime]::Now.AddMinutes(5)
$ready = @{}
while ([DateTime]::Now -lt $timeout) {
    foreach ($dep in $deps) {
        $p = Join-Path $base $dep
        if (-not $ready.ContainsKey($dep) -and (Test-Path $p) -and (Get-Item $p).Length -gt 100) {
            $ready[$dep] = $true
            Write-Host ('✅ READY: ' + $dep + ' (' + (Get-Item $p).Length + ' bytes)')
        }
    }
    if ($ready.Count -eq $deps.Count) { Write-Host 'ALL DEPS READY'; break }
    $missing = $deps | Where-Object { -not $ready.ContainsKey($_) }
    Write-Host ('⏳ Waiting for: ' + ($missing -join ', ') + ' — ' + [Math]::Round(($timeout - [DateTime]::Now).TotalSeconds) + 's left')
    Start-Sleep -Seconds 30
}
$ready.GetEnumerator() | ForEach-Object { Write-Host ('FINAL: ' + $_.Key + ' = ' + $_.Value) }
Write-Host ('DEPS_READY: ' + $ready.Count + '/' + $deps.Count)
"
```

**Após o poll:**
- Para cada dep com `READY=true` → executar `Read: projects/{project_name}/outputs/asis/{dep}` e extrair findings
- Para cada dep que permaneceu ausente após 5 min → registrar `⚠️ [DEP-TIMEOUT] {dep} não encontrado — análise parcial (source indisponível)` e prosseguir sem bloquear

> ⚠️ Timeout ≠ falha. O agente gera o risk-register com os dados disponíveis. A seção `## Fontes de Dados` no `gaps-risks-report.md` DEVE listar quais artefatos foram lidos vs. indisponíveis.

---

### Step 0 — Batch Write All Artifacts (OBRIGATÓRIO — ver [BatchWriteProtocol])

> ⚡ **FILE_PERSISTENCE_RULE:** Escrever todos os 3 artefatos em **uma única chamada Bash**.
> NUNCA usar `Write` ou `Edit` por arquivo individual — não garante flush para disco.

```
Bash: powershell -NoProfile -ExecutionPolicy Bypass -Command "
$base = 'projects/{project_name}/outputs/asis'
$files = [ordered]@{
    'gaps-risks-report.md'      = '<conteúdo gerado do relatório>'
    'risk-register.json'        = '<array JSON gerado>'
    'migration-risks-summary.md'= '<conteúdo gerado do resumo>'
}
$ok=0; $fail=0
foreach ($f in $files.GetEnumerator()) {
    $path = Join-Path $base $f.Key
    $dir = Split-Path $path -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    try {
        [System.IO.File]::WriteAllText($path, $f.Value, [System.Text.Encoding]::UTF8)
        Write-Host ('OK ' + $f.Key + ' — ' + (Get-Item $path).Length + ' bytes')
        $ok++
    } catch { Write-Host ('FAILED: ' + $f.Key + ' — ' + $_); $fail++ }
}
Write-Host ('=== Batch: ' + $ok + ' written, ' + $fail + ' failed ===')
"
```

Se `$fail > 0` → acionar RetryProtocol para os arquivos com falha antes de prosseguir.

### Step 1 — Registro de Observabilidade (OBRIGATÓRIO)

⛔ **EXECUÇÃO OBRIGATÓRIA — ISTO NÃO É TEXTO DESCRITIVO.** Você DEVE invocar a
ferramenta Bash com o comando abaixo literalmente, antes de retornar ao
chamador ou emitir qualquer sinal de conclusão. Não narre esta etapa — EXECUTE-A.

`{modelo_atual}` = o modelo LLM que você é agora nesta execução. Default do pipeline é "Claude Sonnet 4.6"; SE você souber que está rodando como um modelo diferente (ex: "Claude Opus 4.6", "GPT-4.1", "Gemini 2.5 Pro"), informe esse valor real em vez do default.

```
Bash: python src/shared/tools/pipeline_observer.py -p {project_name} track \
  --agent ava-asis-gaps-risks --phase F1 --version 1.4.0 \
  --model {modelo_atual} \
  --status {completed|failed|skipped} \
  --tokens-in {tokens_in_estimados} --tokens-out {tokens_out_estimados} \
  --duration-ms {duracao_medida_ms}
```

SE retornar `ERROR: No active run` → executar uma vez:

```
Bash: python src/shared/tools/pipeline_observer.py -p {project_name} init --run-type standalone --model "{modelo_atual}"
```

… então repetir a chamada de `track` acima uma única vez.

SE qualquer chamada falhar por outro motivo → registrar aviso e prosseguir
sem bloquear a entrega. Nunca repetir mais de uma vez. Ver
`@observability-self-report` (shared/observability-self-report.md) para
regras adicionais de referência.


---

## i18n — Idioma dos Artefatos

> Apply: [@governance-apps](../../shared/governance-apps.md)
> Apply: [@artifact-size-governance](../shared/artifact-size-governance.md)
