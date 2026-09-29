# Step 02 — Extração de Dados

## Objetivo

Ler e normalizar os dados de todos os artefatos descobertos no Step 01,
produzindo os objetos de dados que alimentarão o template HTML. O estado
renderizado por padrão deve ser em inglês; valores derivados de fonte devem
ser classificados como texto legível ou valor técnico protegido antes da
renderização. O seletor PT/EN e seus dicionários permanecem inalterados para
troca manual posterior.

## Ações

### 2.1 — KPIs quantitativos

```
Prioridade 1: Ler projects/{project_name}/outputs/asis/metrics.json
  → Extrair: total_files, text_files, total_loc, class_count,
             method_count, complex_methods, layer_count, module_count

Prioridade 2 (se JSON não existe): Bash/Grep nos arquivos .md
  → Grep "LOC" em inventory-report.md → total_loc
  → Bash: find projects/{project_name}/outputs/asis -name "*.pas" | wc -l → delphi_file_count
  → Grep "Tabelas:" em db-analysis-report.md → table_count
  → Grep "Telas:" em screen-navigation-map.md → screen_count

Nota — Screen Flow: o builder chama `parse_screen_artifacts(asis_dir)` que extrai
de `screen-navigation-map.md` (overview, narrativa, diagrama mermaid, inventário
de formulários, agrupamentos por módulo) e de `screen-rules.md` (regras por
form classificadas em Visibility / Enablement / Validation / Behavior). Todo o
conteúdo é serializado como `screenOverview`, `screenNarrative`, `screenMermaid`,
`screenForms`, `screenGroups`, `screenRules`, `screenRulesByForm` e
`screenRuleCategories` no `const D`, tornando o HTML autocontido (os MDs podem
ser removidos após o build sem impacto).

Para campos não encontrados → usar "N/D" como valor
```

### 2.2 — Risk Register

```
Prioridade 1: Ler projects/{project_name}/outputs/asis/risk-register.json
  → Parse direto como array de riscos

Prioridade 2 (se JSON não existe):
  Ler projects/{project_name}/outputs/asis/gaps-risks-report.md
  Grep linhas que seguem o padrão "| R-" → extrair ID, categoria, risco, severidade

  Ler projects/{project_name}/outputs/asis/security-map.md
  Grep findings de segurança → adicionar ao risk register com categoria "Segurança"

  Ler projects/{project_name}/outputs/asis/vulnerabilities.md
  Grep por "Crítico|Alto|Médio" → extrair vulnerabilidades

Normalizar para formato padrão:
  { id, category, risk, evidence, severity, action }
```

### 2.3 — Padrões arquiteturais

```
Prioridade 1: Ler projects/{project_name}/outputs/asis/pattern-classifications.json

Prioridade 2:
  Grep "Smart UI" em architecture-blueprint.md → contar ocorrências
  Grep "DataModule" → contar
  Grep "Two-Tier" → contar
  Grep "Business Logic" em db/business-logic-in-db.md → contar

Normalizar para:
  { name, occurrences, percentage, risk_level }

Para o estado padrão em inglês, normalize texto legível de padrões, descrições,
justificativas e trade-offs; preserve nomes técnicos, caminhos, URLs, ADRs,
acrônimos e referências exatas. Não altere os artefatos-fonte.
```

### 2.4 — Bounded Contexts

```
Ler projects/{project_name}/outputs/asis/bounded-context-map.md
Grep tabela de bounded contexts (linhas com "| ")
Extrair: nome, forms, units, risco

Se não existe → usar placeholder "{{BC_NAME}}" em 3 linhas
```

### 2.5 — Diagramas Mermaid

```
Para cada arquivo .mmd em projects/{project_name}/outputs/:
  Ler conteúdo → armazenar em DiagramMap[filename] = content

Arquivos alvo AS-IS (paths canônicos):
  - projects/{project_name}/outputs/asis/diagrams/c4-context.mmd
  - projects/{project_name}/outputs/asis/diagrams/c4-container.mmd
  - projects/{project_name}/outputs/asis/db/er-diagram.mmd

Arquivos alvo TO-BE (paths canônicos — TODOS residem em tobe/diagrams/):
  - projects/{project_name}/outputs/tobe/diagrams/migration-gantt.mmd → key: tobe_gantt
  - projects/{project_name}/outputs/tobe/diagrams/context-map.mmd    → key: tobe_context_map
  - projects/{project_name}/outputs/tobe/diagrams/security-architecture.mmd → key: tobe_security_arch
  - projects/{project_name}/outputs/tobe/diagrams/value-chain.mmd   → key: tobe_value_chain
  - projects/{project_name}/outputs/tobe/diagrams/mer-diagram-tobe.mmd → key: tobe_er_diagram
  - projects/{project_name}/outputs/tobe/diagrams/ (qualquer outro .mmd não listado acima)

ATENÇÃO: o arquivo migration-gantt.mmd está em tobe/diagrams/migration-gantt.mmd
  NÃO em tobe/migration-gantt.mmd (caminho incorreto — ignorar)

Se arquivo não existe → DiagramMap[key] = "(diagrama não disponível)"
```

### 2.6 — Dados TO-BE

```
Ler projects/{project_name}/outputs/tobe/docs/sizing-report.md
  ATENÇÃO: o arquivo usa tabelas Markdown com valores em negrito — NÃO há chaves literais
  como "total_sp" ou "total_fp". Extrair usando os padrões abaixo:

  total_fp:
    Grep "**TOTAL**" na tabela de Function Point Analysis (UFP)
    Capturar o valor após "TOTAL" e "UFP" — ex: "**TOTAL** | **243 UFP** | **100%**" → "243 UFP"
    Alternativa: grep "Total.*UFP" case-insensitive → capturar número + "UFP"

  total_sp:
    Grep "**TOTAL**" na tabela de Story Points por Bounded Context
    Capturar o valor ~N SP — ex: "**~1,141 SP**" → "~1.141 SP"
    Alternativa: grep "~[0-9,.]+ SP" → capturar primeiro match que inclua ~

  team_size:
    Grep tabela de Sprint Projection
    Capturar a opção de time recomendada (geralmente a de menor duração) — ex: "2 devs + 1 TL" ou "3 devs + 1 QA + 1 TL"
    Alternativa: grep "devs?" → capturar primeira ocorrência com contexto

  total_sprints:
    Grep tabela de Sprint Projection
    Capturar o valor de sprints para o time escolhido — ex: "~14 sprints" ou "~10 sprints"
    Alternativa: grep "~[0-9]+ sprint" → capturar primeiro match

  azure_cost:
    Grep tabela de Cost Estimate — linha de ambiente Produção
    Capturar o total mensal — ex: "**Monthly Total (USD)** | **~$925**" → "~$925"
    Alternativa: grep "Monthly Total.*USD" → capturar valor em $

  Se sizing-report.md não existe ou padrão não encontrado para algum campo → usar "N/D"

Ler projects/{project_name}/outputs/tobe/docs/wave-plan.md
  Grep linhas "| Wave" → extrair waves com módulos, duração, risco, feature flag

Ler projects/{project_name}/outputs/tobe/nuget-packages.md
  Grep linhas "| Package" → extrair lista de packages

Ler projects/{project_name}/outputs/tobe/docs/tech-framework-document.md
  Grep "Solution Structure" → extrair estrutura de pastas

Ler projects/{project_name}/outputs/tobe/value-chain-mapping.md
  Grep tabelas: "Module × Business Processes", "Cross-Module Value Flow", "Value Chain Improvements"
  Armazenar em tobe_data.value_chain = { modules: [...], flows: [...], improvements: [...] }
  Se não existe → tobe_data.value_chain = null
```

### 2.6b — TO-BE Architecture Patterns

```
Prioridade 1: Ler projects/{project_name}/outputs/tobe/patterns-applied.json
  → Parse como JSON: extrair array patterns[]
  → Para cada pattern → { pattern_name, layer, justification, reference_artifact, trade_offs[], adr_reference }

Se JSON não existe → tobe_patterns = [] (tabela renderiza mensagem fallback)
```

### 2.6a — Bounded Contexts TO-BE

```
Ler projects/{project_name}/outputs/tobe/bounded-context-map.md

Grep linhas "| BC-" ou "### BC-" → extrair bounded contexts TO-BE:
  Para cada BC → { n, resp, ul[], squadOwner, pattern, approved, _adr, _r }

Campos:
  n          → nome do Bounded Context
  resp       → responsabilidade principal (coluna "Responsabilidade")
  ul         → array de termos da Linguagem Ubíqua (split por ", ")
  squadOwner → squad responsável (coluna "Squad Owner")
  pattern    → padrão DDD/Arch (ex: "Clean Arch + CQRS + DDD")
  approved   → true se status "Accepted" ou "Aprovado"
  _adr       → referência ao ADR (ex: "ADR-001")
  _r         → nível de risco ("alto"|"medio"|"baixo")

Se arquivo não existe → tobebc = [] (renderBCMetrics usa D.bc como fallback)
```

### 2.7 — Regras de Negócio TO-BE

```
Ler projects/{project_name}/outputs/tobe/docs/regras-negocio.md

Extração 1 — Métricas (tabela "## Métricas"):
  Grep "Total de regras AS-IS" → tobebn.totalAsIs
  Grep "Regras preservadas"    → tobebn.preserved
  Grep "Regras corrigidas"     → tobebn.fixed
  Grep "Regras eliminadas"     → tobebn.eliminated
  Grep "Regras críticas endereçadas" → tobebn.critical
  Grep "Bounded Contexts que recebem regras" → tobebn.bcCount
  Grep "Cobertura AS-IS"       → tobebn.coverage

Extração 2 — Tabela de rastreabilidade (linhas "| RN-" ou "| RN-NEW-"):
  Para cada linha → { idAsIs, rule, bcTobe, decision, dddElement, impact }
  Normalizar decision: "Preserved" | "Fixed" | "Fixed (Critical)" | "Eliminated" | "Split"

Extração 3 — Seções por BC (padrão "### BC-{N} — {Name}"):
  Para cada BC → extrair { bc, squadOwner, rules: [{ id, rule, origin, ddd, enforcement }] }

Extração 4 — Regras novas (seção "## Regras Novas Introduzidas"):
  Para cada linha → { id, rule, bc, reason }

Se arquivo não existe → tobebn = {} (seção renderiza placeholder "fase não executada")
```

### 2.7 — Status de execução

```
Para cada agente → verificar AgentStatusMap (criado no Step 01)
Calcular:
  agents_ok  = count(status == "done")
  agents_err = count(status == "pending")
  exec_pct   = round(agents_ok / 41 * 100)
```

### 2.8 — Inventário de artefatos por agente

```
Para cada agente com status "done":
  Listar seus output files do ArtifactInventory
  Formatar como: { key: "nome_amigável", path: "caminho/relativo" }
```

### 2.9 — Consolidação de Security Review (OBRIGATÓRIO)

> ⚠️ **NUNCA ler apenas `security-findings.json`** — esse arquivo contém só 9 achados do orquestrador. A tabela consolidada lê **todos os 8 arquivos de agente**.

**Fontes a ler** em `projects/{project_name}/outputs/asis/security/`:

| Arquivo                       | Chave do array   | Nome do agente           |
| ----------------------------- | ---------------- | ------------------------ |
| `sast-asis.json`              | `findings`       | `sast-asis`              |
| `iast-asis.json`              | `findings`       | `iast-asis`              |
| `pt-pattern-asis.json`        | `findings`       | `pt-pattern-asis`        |
| `dependency-config-asis.json` | `findings`       | `dependency-config-asis` |
| `taint-asis.json`             | `findings`       | `taint-asis`             |
| `threat-model-asis.json`      | `findings`       | `threat-model-asis`      |
| `sbom.cyclonedx.json`         | `findings`       | `sbom`                   |
| `security-findings.json`      | `securityReview` | `security-findings`      |

`security-review-asis.json` é **excluído** — documento de sumário, sem `findings[]`.

**Algoritmo de consolidação G7:**

```
all_raw = []
Para cada (arquivo, chave_array, nome_agente) acima:
  Se arquivo existir:
    data = JSON.parse(arquivo)
    itens = data[chave_array] ou []
    Para cada item em itens:
      Normalizar para schema canônico v2:
        type      = item.type ou item.vulnerability_type ou item.category ou "Other"
        severity  = item.severity (CRITICAL|HIGH|MEDIUM|LOW|INFO)
        owasp     = item.owasp ou "A00:Other"
        cwe       = item.cwe ou "CWE-Other"
        reference = item.reference ou ""
        finding   = item.finding ou item.description ou item.title ou ""
        evidence  = item.evidence ou item.evidences ou ""
        source    = item.source ou nome_agente
        count     = len(evidence.split("|").filter(non-empty)) — RECOMPUTE sempre
      all_raw.append(item_normalizado)

merged = {}  (mapa de chave → item consolidado)
agent_slot_seen = {}  (rastreia ocorrências por (chave_base, agente))

Para cada item em all_raw:
  base_key = (item.reference.lower() ou item.cwe.lower(), item.owasp.upper(), item.cwe.upper())
  agent    = item.source
  slot     = (base_key, agent)
  occurrence = agent_slot_seen.get(slot, 0)
  agent_slot_seen[slot] = occurrence + 1

  — Se mesma (ref+owasp+cwe) PRIMEIRO vez desse agente → chave = base_key (permite cross-agent merge)
  — Se mesma (ref+owasp+cwe) ocorrência subsequente do MESMO agente → chave = base_key + (agent, N) (linha independente)
  key = base_key se occurrence == 0 senão base_key + (agent, occurrence)

  Se key não em merged:
    merged[key] = cópia do item
  Senão (cross-agent merge):
    existing = merged[key]
    — severity: manter a mais alta
    — type: união de tipos distintos separados por "+"
    — finding: manter o mais longo
    — source: união de nomes de agente separados por "+" (ordenados, distintos)
    — evidence: união de tokens "Arquivo - Linha N" distintos, separados por "|"
    — count: len(evidence.split("|").filter(non-empty)) — RECOMPUTE

securityReview = list(merged.values())
badge_total    = sum(row.count for row in securityReview)

findingsSummary = {
  total:    badge_total,
  critical: count(r.severity.upper() == "CRITICAL"),
  high:     count(r.severity.upper() == "HIGH"),
  medium:   count(r.severity.upper() == "MEDIUM"),
  low:      count(r.severity.upper() == "LOW"),
  info:     count(r.severity.upper() == "INFO"),
  gate:     "BLOCKED" se critical > 0 senão "APPROVED"
}
```

**Resultado esperado para Meu-ERP:** 33 linhas na tabela, badge = 68.

**Injetar em `summary-data.json`:**

```json
"securityReview":    [ ...array consolidado... ],
"findingsSummary":   { "total": 68, "critical": 10, ... }
```

**Substituição de placeholders no HTML (step 03):**

- `{{SECURITY_REVIEW_JSON}}` → `JSON.stringify(securityReview)`
- `{{FINDINGS_SUMMARY_JSON}}` → `JSON.stringify(findingsSummary)`

### 2.10 — Complexidade Ciclomática Top-10 (ccTop)

```
Prioridade 1: Ler projects/{project_name}/outputs/asis/metrics.json
  → Verificar se existe chave "complexity" com array "highest_cc_files"
  → Para cada item → { rank, file, method, cc }

Prioridade 2 — Síntese a partir de bounded_contexts (quando Prioridade 1 não existe):
  → bounded_contexts = metrics.json["bounded_contexts"] (array de BCs)
  → code_metrics = metrics.json["code_metrics"]
  → avg_cc  = code_metrics.cyclomatic_complexity_avg  (float)
  → max_cc  = code_metrics.cyclomatic_complexity_max  (float)
  → Para cada BC, calcular cc_estimado por interpolação linear:
       peso = bc.loc / total_loc_de_todos_bcs   (0..1)
       cc_estimado = avg_cc + peso * (max_cc - avg_cc)
       cc_estimado = round(cc_estimado, 1)
  → Ordenar BCs por cc_estimado DESC → pegar os top-10
  → Para cada BC → {
       rank:   posição (1, 2, 3, ...),
       file:   bc.name,
       method: "{bc.forms} forms / {bc.loc} LOC",
       cc:     cc_estimado
    }

Se bounded_contexts está vazio OU avg_cc == 0 → ccTop = []
```

Injetar em `summary-data.json`:

```json
"ccTop": [ { "rank": 1, "file": "...", "method": "...", "cc": 3.8 }, ... ]
```

### 2.11 — Tipos de Arquivo por Extensão (fileTypes)

```
Prioridade 1: Ler projects/{project_name}/outputs/asis/metrics.json
  → repository.pas_files  → contagem .pas
  → repository.dfm_files  → contagem .dfm
  → sql_metrics.total_scripts OU grep por .sql → contagem .sql
  → repository.other_files → contagem outros (.dll, .cfg, etc.)

Construir array:
  fileTypes = [
    { t: ".pas", q: <pas_files>,  dk: "ft-pas" },
    { t: ".dfm", q: <dfm_files>,  dk: "ft-dfm" },
    { t: ".sql", q: <sql_count>,  dk: "ft-sql" },
    { t: ".dll", q: 0,            dk: "ft-dll" },
    { t: ".cfg", q: <cfg_count>,  dk: "ft-cfg" },
  ]
  Onde q é sempre string (ex: "22", "0")

Se metrics.json não existe → fileTypes = [] (o template trata)
```

Injetar em `summary-data.json`:

```json
"fileTypes": [ { "t": ".pas", "q": "22", "dk": "ft-pas" }, ... ]
```

## Output deste Step

```json
{
  "project_context": { "name": "...", "technology": "...", "trace_id": "..." },
  "kpis": { "total_files": "...", "coverage": "...", ... },
  "risks": [{ "id": "R-01", "category": "...", ... }],
  "patterns": [{ "name": "...", "occurrences": "...", ... }],
  "bounded_contexts": [...],
  "ccTop": [{ "rank": 1, "file": "...", "method": "...", "cc": 3.8 }],
  "fileTypes": [{ "t": ".pas", "q": "22", "dk": "ft-pas" }],
  "diagrams": { "c4_context": "...", "er_diagram": "...", ... },
  "tobe_data": { "waves": [...], "packages": [...], "sizing": {...} },
  "agent_status": { "ava-asis-solution-delphi": "done", ... },
  "exec_summary": { "agents_ok": 28, "agents_err": 13, "exec_pct": 68 },
  "artifact_inventory": { "F1": [...], "F2": [...], ... }
}
```

Salvar em: `projects/{project_name}/outputs/summary/summary-data.json`

## Critério de Conclusão

- `summary-data.json` criado com pelo menos `project_context` e `agent_status`
- Pelo menos 1 KPI extraído (mesmo que "N/D")
- DiagramMap criado (mesmo que todos vazios)
