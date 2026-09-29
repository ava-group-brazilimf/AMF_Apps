# 🚀 Full Pipeline (FP) - Guia de Uso

## Visão Geral

O comando **Full Pipeline (FP)** executa o diagnóstico AS-IS completo end-to-end, garantindo que TODOS os artefatos necessários sejam criados e finalizando com a geração do Summary HTML interativo.

## Problema que Resolve

Anteriormente, o workflow AS-IS podia completar sem gerar `metrics.json` ou `risk-register.json` se os agents `ava-asis-inventory` ou `ava-asis-gaps-risks` falhassem silenciosamente.

Isto causava **placeholders vazios** no Summary HTML:
- ❌ Seção KPIs vazia
- ❌ Seção Riscos vazia  
- ❌ Agentes sem status
- ❌ File Explorer sem conteúdo

## Solução: Full Pipeline

O FP **garante** a criação dos artefatos críticos através de:

1. **Execução completa** dos 7 agents AS-IS
2. **Validação** de artefatos obrigatórios
3. **Geração de fallbacks** automática se necessário
4. **Summary HTML** com dados completos

---

## 📋 Fluxo Completo

```
┌─────────────────────────────────────────────────────────┐
│  @ava-asis-orchestrator | FP                            │
└─────────────────────────────────────────────────────────┘
                     ↓
        ┌────────────────────────┐
        │  FASE 1: Diagnóstico   │
        │  AS-IS (7 agents)      │
        └────────────────────────┘
                     ↓
            • ava-asis-solution-delphi
            • ava-asis-documentation
            • ava-asis-security-review (paralelo)
            • ava-asis-inventory (paralelo) ← gera metrics.json
            • ava-asis-db-analyzer (paralelo)
            • ava-asis-gaps-risks ← gera risk-register.json
                     ↓
        ┌────────────────────────┐
        │  FASE 2: Validação     │
        │  de Artefatos          │
        └────────────────────────┘
                     ↓
            ✅ metrics.json existe?
            ✅ risk-register.json existe?
            ✅ master-report.md existe?
                     ↓
        ┌────────────────────────┐
        │  FASE 3: Fallbacks     │
        │  (se necessário)       │
        └────────────────────────┘
                     ↓
            Se metrics.json ausente:
              → python generate_fallback_artifacts.py --type metrics
            
            Se risk-register.json ausente:
              → python generate_fallback_artifacts.py --type risks
                     ↓
        ┌────────────────────────┐
        │  FASE 4: Summary HTML  │
        │  (@ava-summary | GS)   │
        └────────────────────────┘
                     ↓
            • Pre-Step: Garantir artefatos
            • Step 01: Descoberta
            • Step 02: Extração de dados
            • Step 03: Build HTML (template v1.0)
            • Step 04: Validação
                     ↓
        ┌────────────────────────┐
        │  ✅ Summary HTML       │
        │  Completo Gerado       │
        └────────────────────────┘
```

---

## 🎯 Uso

### Sintaxe Básica

```
@ava-asis-orchestrator | FP
```

### Com Parâmetros

```
@ava-asis-orchestrator | FP | language: en | project: database-comparer-examples
```

```
/ava-asis-orchestrator | FP
```

---

## 📊 Artefatos Garantidos

Ao final do FP, os seguintes artefatos **sempre** estarão presentes:

```
projects/{project_name}/outputs/
├── asis/
│   ├── master-report.md                           ✅
│   ├── architecture-blueprint.md                  ✅
│   ├── bounded-context-map.md                     ✅
│   ├── inventory-report.md                        ✅
│   ├── complexity-map.md                          ✅
│   ├── gaps-risks-report.md                       ✅
│   ├── security-map.md                            ✅
│   ├── vulnerabilities.md                         ✅
│   ├── pattern-classifications.json               ✅
│   ├── metrics.json                               ✅ (GARANTIDO via fallback)
│   ├── risk-register.json                         ✅ (GARANTIDO via fallback)
│   ├── screen-flow-completeness.json              ✅ (v3 — assertion de completude)
│   ├── screen-flow-*.mmd                          ✅ (v3 — intermediários por BC)
│   └── db/
│       ├── schema-inventory.md                    ✅
│       ├── er-diagram.mmd                         ✅
│       └── ...
└── summary/
    ├── AVA-FABRIC-SUMMARY-{project}-{date}.html   ✅ (Template oficial v1.0)
    ├── summary-data.json                          ✅
    ├── index.md                                   ✅
    └── mermaid.min.js                             ✅
```

---

## ✅ Critérios de Sucesso

O FP é considerado bem-sucedido quando:

- [ ] Todos os 7 agents AS-IS executados
- [ ] `metrics.json` existe e é JSON válido
- [ ] `risk-register.json` existe e é JSON válido
- [ ] `master-report.md` exists e tamanho > 5 KB
- [ ] Summary HTML gerado com assinatura "AVA Fabric Summary Template v1.0"
- [ ] Summary HTML tamanho > 150 KB
- [ ] Placeholders não resolvidos < 50

---

## 🔧 Fallback Generators

### Script: `generate_fallback_artifacts.py`

**Localização**: `src/modules/ava-fabric-agents/asis-diagnostic/utils/generate_fallback_artifacts.py`

**Uso Manual** (se necessário):

```powershell
# Gerar metrics.json
python src/modules/ava-fabric-agents/asis-diagnostic/utils/generate_fallback_artifacts.py `
    --type metrics `
    --project database-comparer-examples

# Gerar risk-register.json
python src/modules/ava-fabric-agents/asis-diagnostic/utils/generate_fallback_artifacts.py `
    --type risks `
    --project database-comparer-examples

# Gerar ambos
python src/modules/ava-fabric-agents/asis-diagnostic/utils/generate_fallback_artifacts.py `
    --type all `
    --project database-comparer-examples
```

### Fallback: metrics.json

**Fonte de dados**:
- `master-report.md` (prioridade 1)
- `inventory-report.md` (prioridade 2)
- Glob direto no repositório (last resort)

**Métricas extraídas**:
- LOC total, por arquivo (.pas, .dfm, .dpr, .sql)
- Contagem de arquivos
- Classes, Forms, DataModules
- Métodos/Procedures/Functions
- Módulos e Layers

### Fallback: risk-register.json

**Fonte de dados**:
- `gaps-risks-report.md` (tabela de riscos)
- `master-report.md` (seção de riscos)
- `security-map.md` (vulnerabilidades)

**Extração**:
- Tabelas estruturadas (formato Markdown)
- Seções de texto com padrão "Risk:"
- Classificação automática P0/P1/P2/P3

---

## 🎨 Diferença no Summary HTML

### ❌ Antes (sem FP)

- Seção KPIs: `{{TOTAL_LOC}}` → placeholder não substituído
- Seção Riscos: tabela vazia
- Seção Agentes: sem cards de status
- File Explorer: sem conteúdo embutido

### ✅ Depois (com FP)

- Seção KPIs: **8,600 LOC**, **42 files**, **430 methods**
- Seção Riscos: **12 riscos** classificados (4 P0, 3 P1, 5 P2)
- Seção Agentes: **8/41 executados** com cards verdes
- File Explorer: **29 arquivos** com conteúdo embutido

---

## 📝 Exemplo de Execução

```
@ava-asis-orchestrator | FP | language: en

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 Full Pipeline — database-comparer-examples
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[FASE 1] Executando diagnóstico AS-IS...
  ✅ ava-asis-solution-delphi       (architecture-blueprint.md)
  ✅ ava-asis-documentation         (functional-requirements.md)  
  ✅ ava-asis-security-review       (security-map.md)
  ⚠️ ava-asis-inventory             (inventory-report.md, metrics.json AUSENTE)
  ✅ ava-asis-db-analyzer           (schema-inventory.md)
  ✅ ava-asis-gaps-risks            (gaps-risks-report.md, risk-register.json OK)

[FASE 2] Validando artefatos críticos...
  ✅ master-report.md (78 KB)
  ❌ metrics.json (AUSENTE)
  ✅ risk-register.json (12 KB)

[FASE 3] Gerando fallbacks...
  🔧 Gerando metrics.json...
     📊 LOC Total: 8600
     📊 Files: 42
  ✅ metrics.json gerado (3.2 KB)

[FASE 4] Gerando Summary HTML...
  📊 Step 01: 29 arquivos descobertos
  📊 Step 02: Métricas extraídas (12 KPIs, 12 riscos)
  🛠️ Step 03: HTML construído (template v1.0)
  ✅ Step 04: Validado (22 placeholders pendentes)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Full Pipeline Concluído!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 HTML: AVA-FABRIC-SUMMARY-database-comparer-examples-2026-04-14.html
📊 Tamanho: 179 KB
✅ Assinatura: AVA Fabric Summary Template v1.0
```

---

## � Modernização Parcial (Strangler Fig Pattern)

### Quando usar

Use `modernization_scope: partial` quando o time quer modernizar **apenas um ou
alguns bounded contexts** do sistema legado sem executar o pipeline completo.
Esse modo implementa o **Strangler Fig Pattern**: o novo sistema cresce ao lado
do legado, BC por BC, até que o legado possa ser desativado.

### Configuração

Em `projects/{PROJECT_NAME}/context/project-config.yaml`:

```yaml
modernization_scope: "partial"
target_modules: ["financeiro", "cadastro"]  # IDs dos BCs a modernizar
```

### O que muda no pipeline

1. **Passo 0.5** — antes de F1, o agente `ava-tobe-coexistence-strategy` é
   despachado automaticamente, gerando `coexistence-strategy.md` com as zonas
   de migração Z1/Z2/Z3.
2. **F3 (codegen)** — apenas os BCs em `target_modules` recebem geração de
   código. BCs fora da lista são ignorados com log `⏭ fora de target_modules`.
3. **F1, F2, F5, F7, F6** — executam normalmente (sem filtragem de BCs).

### Diagrama

```
project-config.yaml
  modernization_scope: "partial"
  target_modules: ["financeiro"]
         │
         ▼ Passo 0.5
  ┌─────────────────────────┐
  │ coexistence-strategy    │  → outputs/tobe/docs/coexistence-strategy.md
  └─────────────────────────┘
         │
         ▼ F1 → F2 → F3
  F3 codegen: SOMENTE "financeiro"
         │
         ▼
  ✅ Código gerado para 1 BC
  ⏭ Outros BCs: ignorados
```

### Passo a passo

**1. Configure o projeto:**

```yaml
# projects/Meu-ERP/context/project-config.yaml
modernization_scope: "partial"
target_modules: ["financeiro"]
```

**2. Execute o pipeline:**

```
@ava-master-orchestrator | FP
```

**3. Verifique o passo 0.5:**

O agente emite o bloco `PARTIAL MODERNIZATION MODE — PRE-FLIGHT` com
`DECISION: PROCEED` e invoca `ava-tobe-coexistence-strategy`.

**4. Verifique F3:**

No log do stack-orchestrator, cada BC fora de `target_modules` aparece
como `⏭ BC '...' fora de target_modules — ignorado.`

### Zonas de migração (coexistence strategy)

O `coexistence-strategy.md` gerado no passo 0.5 classifica os BCs em:

| Zona | Significado |
|------|-------------|
| Z1 | Modernizado no ciclo atual — já em `target_modules` |
| Z2 | Aguardando ciclo futuro — será modernizado depois |
| Z3 | Sem previsão de modernização — permanece legado |

### Graduating de parcial para completo

Quando todos os BCs prioritários estiverem modernizados, mude para:

```yaml
modernization_scope: "full"
# target_modules pode ser removido ou deixado como documentação
```

---

## 🧩 Particionamento de Módulos (Module Partitioner)

### Quando usar

Use `scope_modules != "all"` quando o pipeline deve analisar **apenas um
subconjunto de módulos** do repositório Delphi. Diferentemente do
`modernization_scope: partial` (que controla a **modernização** no F3+),
o `scope_modules` controla o **escopo de análise** no F1 AS-IS.

Caso de uso típico: o cliente quer entender apenas o módulo "Financeiro"
antes de tomar decisão de modernização parcial.

### Configuração

```yaml
# projects/{PROJECT_NAME}/context/project-config.yaml
scope_modules: ["financeiro", "vendas"]  # ou "all" para análise completa
```

### O que muda no pipeline

1. **Step 0.5 (Module Partitioning)** — após a extração AST (Step 0),
   o `ava-asis-solution-delphi` invoca automaticamente `module_partitioner.py`,
   que:
   a. Constrói grafo de dependências a partir das cláusulas `uses` dos `.pas`
   b. Executa o algoritmo **Leiden** (Traag et al., 2019) para detecção de
      comunidades — corrige bugs de resolução e comunidades desconexas do
      Louvain clássico
   c. Aplica resolução auto-tunada (<50 units → 0.5, 50-200 → 1.0, >200 → 1.5)
   d. Produz `module-partition.json` (mapeamento completo) e
      `scope-filter-manifest.json` (subset ativo)

2. **Override manual** — é possível forçar módulos via `module-override.json`:
   ```json
   {
     "modules": {
       "Financeiro": ["uFinanceiro.pas", "uContasPagar.pas"]
     }
   }
   ```
   Quando presente, o override **bypassa** o Leiden completamente.

3. **F1 AS-IS — Filtro nos agentes** — após Step 0.5, cada agente F1
   (`solution-delphi`, `inventory`, `test-qa`) filtra suas análises:
   - `solution-delphi`: filtra `payload.classes` por `included_units[]`
   - `inventory`: recalcula métricas a partir do subset
   - `test-qa`: mantém apenas testes cujos `source_ref.file` estão no escopo

### Diagrama

```
project-config.yaml
  scope_modules: ["financeiro", "vendas"]
         │
         ▼ F1 Step 0 (AST extraction)
  ┌─────────────────────────────┐
  │ 9 JSONs monolíticos         │
  └─────────────────────────────┘
         │
         ▼ Step 0.5 (Module Partitioner)
  ┌─────────────────────────────┐
  │ Leiden + auto-tune          │
  │ module-partition.json       │
  │ scope-filter-manifest.json  │
  └─────────────────────────────┘
         │
         ▼ F1 agentes
  Filtro por included_units[]
         │
         ▼
  ✅ Análise restrita aos módulos
  ⏭ Units fora do escopo: ignoradas
```

### Resolução e tuning

| Parâmetro | Descrição | Default |
|-----------|-----------|---------|
| `module_partitioner_resolution` | Override da resolução Leiden | `null` (auto-tune) |
| `module_override_file` | Caminho para override manual | `""` (desativado) |

Para lógica completa de auto-tune e override, ver
[module-partitioner-guide.md](../docs/module-partitioner-guide.md).

---

## �🆚 Comparação: SA vs FP

| Aspecto | SA (start-analysis) | FP (full-pipeline) |
|---------|---------------------|---------------------|
| Agents AS-IS | ✅ Sim | ✅ Sim |
| Master Report | ✅ Sim | ✅ Sim |
| Validação de artefatos | ❌ Não | ✅ Sim |
| Fallback generators | ❌ Não | ✅ Sim |
| Summary HTML | ⏭️ Opcional (manual) | ✅ Automático |
| Garantia de dados | ❌ Não | ✅ Sim |

**Recomendação**: Use **FP** para diagnóstico completo end-to-end com garantia de Summary HTML funcional.

---

## 🔗 Referências

- [orchestrator-asis.md](../src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md) — Trigger FP
- [summary-agent.md](../src/modules/ava-fabric-agents/summary/agents/summary-agent.md) — Pre-Step
- [generate_fallback_artifacts.py](../src/modules/ava-fabric-agents/asis-diagnostic/utils/generate_fallback_artifacts.py) — Script de fallback
- [workflow.md](../src/modules/ava-fabric-agents/summary/workflows/generate-summary/workflow.md) — Workflow Summary
