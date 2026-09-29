# Guia de Execucao do Fluxo de Agentes — AVA Fabric

> Documento de referencia para execucao completa da esteira de **127 agentes** organizados em **9 fases** (F1, F2, F3, F3S, F4, F5, F6, F7, F8), distribuidas em **13 etapas** de esteira e **8 grupos** de execucao.
>
> **Fontes de verdade deste documento** (nao editar este guia sem reconferir):
>
> | O que                                 | Fonte                                                                                                                                 |
> | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
> | Ordem da esteira                      | [src/shared/data/ava-pipeline.yaml](../src/shared/data/ava-pipeline.yaml) → `pipeline.steps`                                        |
> | Catalogo de agentes / fase por modulo | [src/shared/tools/agent_registry.py](../src/shared/tools/agent_registry.py) (`python src/shared/tools/agent_registry.py`)            |
> | Numeracao das fases                   | `.specify/memory/constitution.md` § Project Reference (emenda v1.4.0)                                                              |
> | Sub-fases de cada orquestrador        | O proprio`.md` do orquestrador em `src/modules/ava-fabric-agents/{modulo}/agents/`                                                |
> | DAG deterministico F1 / F3S           | [src/shared/data/pipeline-dag/F1.yaml](../src/shared/data/pipeline-dag/F1.yaml) · [F3S.yaml](../src/shared/data/pipeline-dag/F3S.yaml) |
>
> Ultima reconciliacao: 2026-08-18.

---

## Indice

1. [Pre-requisitos](#1-pre-requisitos)
2. [Configuracao do Projeto](#2-configuracao-do-projeto)
3. [Visao Geral do Fluxo](#3-visao-geral-do-fluxo)
4. [Formas de Execucao (CLI x Agentes)](#4-formas-de-execucao-cli-x-agentes)
5. [F1 — Diagnostico AS-IS](#5-f1--diagnostico-as-is)
6. [F2 — Arquitetura TO-BE (F2a)](#6-f2--arquitetura-to-be-f2a)
7. [F2b — DevOps Plan (Momento 1)](#7-f2b--devops-plan-momento-1)
8. [F2c — QA Test Plan &amp; Strategy (Momento 1)](#8-f2c--qa-test-plan--strategy-momento-1)
9. [F3 — Prototipo](#9-f3--prototipo)
10. [F3S — SpecKit Planning](#10-f3s--speckit-planning)
11. [F4 — Stack / Geracao de Codigo](#11-f4--stack--geracao-de-codigo)
12. [F5 (esteira) — DevOps Execute (Momento 2)](#12-f5-esteira--devops-execute-momento-2)
13. [F6 (esteira) — QA Quality Execute (Momento 2)](#13-f6-esteira--qa-quality-execute-momento-2)
14. [F7 — Entregaveis](#14-f7--entregaveis)
15. [F8 — Summary](#15-f8--summary)
16. [Fluxo Completo Passo a Passo](#16-fluxo-completo-passo-a-passo)
17. [Shared Context, Observabilidade e Rastreabilidade](#17-shared-context-observabilidade-e-rastreabilidade)
18. [Execucao de Agentes Individuais](#18-execucao-de-agentes-individuais)
19. [Troubleshooting](#19-troubleshooting)
20. [Referencia Rapida — Todos os Agentes por Fase](#20-referencia-rapida--todos-os-agentes-por-fase)
21. [Sumario de Quantidades](#21-sumario-de-quantidades)

---

## 1. Pre-requisitos

| Requisito                                     | Descricao                                                                                       |
| --------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| **Python 3.11+**                        | Executa o CLI`ava-pipeline.bat`, as tools deterministicas (AST, gates, ledger) e os checks    |
| **GitHub Copilot CLI / Claude Code**    | Motor de inferencia para os agentes (`engine: sdk` ou `engine: copilot`)                    |
| **Git**                                 | Repositorio do AVA Fabric clonado localmente                                                    |
| **Repositorio legado**                  | Codigo-fonte do sistema legado acessivel no disco                                               |
| **VPN corporativa**                     | Necessaria para o endpoint privado do Azure AI Foundry (`aif-imf-apps-prd-eus2-001`)          |
| **Arquivo `.copilot-key`**            | Chave do Foundry na raiz do repo (nao commitar — esta no`.gitignore`)                        |
| **Proxy Headroom** (opcional)           | Compressao de contexto;`pipeline.proxy.mode: auto` degrada com aviso se ausente               |
| **Acesso ao banco de dados** (opcional) | Para analise de schema pelo`ava-asis-db-analyzer` (SQL Server, Oracle, MySQL, MariaDB)        |
| **Toolchain local** (F4)                | .NET SDK / JDK / Node / Go conforme`tobe_stack` — exigido pelo `ava-stack-build-validator` |
| **Podman ou Docker** (F5)               | Para`ava-devops-containerize` e `ava-devops-podman-run`                                     |

---

## 2. Configuracao do Projeto

### Passo 1 — Criar o diretorio do projeto

```bash
cp -r projects/_template projects/{NOME-DO-PROJETO}
```

Exemplo:

```bash
cp -r projects/_template projects/Meu-ERP
```

### Passo 2 — Preencher o arquivo de configuracao

Edite `projects/{NOME-DO-PROJETO}/context/project-config.yaml`:

```yaml
project_name: "Meu-ERP"                 # Identificador unico (kebab-case, sem espacos)
repository_path: "/caminho/do/repo"     # Caminho absoluto do repositorio legado
legacy_technology: "delphi"             # delphi | vb6 | vbnet | dotnet | java | cobol | powerbuilder
scope_modules: "all"                    # "all" ou lista: ["financeiro", "cadastro"]
modernization_scope: "full"             # full | partial (partial aciona coexistence-strategy)
language: "pt"                          # pt | en — idioma dos artefatos
client_name: "Nome do Cliente"
sponsor_name: "Nome do Sponsor"
focal_point_name: "Nome do Focal Point"

security_enabled_asis: true             # liga o ava-asis-security-orchestrator (7 sub-agentes) na F1
timing_benchmark_enabled: true          # liga a captura NTP e os blocos MACRO/MICRO de timing
pipeline_mode: "full"                   # full | build-cycle | generic
cloud_provider: "azure"                 # azure | aws | gcp | k8s-native

tobe_stack:
  backend_framework: "dotnet"           # dotnet | spring-boot | fastapi | gin | nestjs
  backend_version: "10"
  frontend_framework: "angular"         # angular | react | vue | blazor
  frontend_version: "17"

pipeline:                               # opcional — sobrescreve src/shared/data/ava-pipeline.yaml
  execution:
    engine: "sdk"
    confirm: "manual"
```

**Campos obrigatorios**: `project_name`, `repository_path`, `legacy_technology`.

### Passo 3 — Verificar a estrutura criada

```
projects/Meu-ERP/
├── context/
│   ├── project-config.yaml    ← configuracao preenchida
│   ├── ConfigStack.yaml       ← stack resolvida (tobe_stack.*), lida pela F4
│   └── shared-context.md      ← estado compartilhado (auto-atualizado)
└── outputs/                   ← sera populado pelos agentes
```

### Passo 4 — Diagnostico de ambiente

```bash
ava-pipeline.bat doctor -p Meu-ERP
```

---

## 3. Visao Geral do Fluxo

### 3.1 — Os dois eixos de numeracao (divergencia intencional)

> ⚠️ **NAO "corrigir".** O repositorio tem **dois eixos** de numeracao de fase, deliberadamente diferentes:
>
> | Eixo                                       | O que numera                        | F5                  | F6                      | F7                          |
> | ------------------------------------------ | ----------------------------------- | ------------------- | ----------------------- | --------------------------- |
> | **Esteira** (`ava-pipeline.yaml`)  | ordem de execucao dos passos do CLI | DevOps Execute      | QA Execution            | *(nao existe na esteira)* |
> | **Registry** (`agent_registry.py`) | modulo de origem do agente          | modulo`qa-agents` | modulo`devops-agents` | modulo`deliverables`      |
>
> `pipeline_plan.validate_plan()` valida apenas que o agente existe, e despachavel e nao esta depreciado — **nunca** que `step.phase == registry.phase`. Ver `tests/tools/test_pipeline_plan.py`.
>
> Este guia usa o **eixo da esteira** nas secoes 5–15 e o **eixo do registry** na secao 20 (catalogo).

### 3.2 — Ordem da esteira (13 etapas · 8 grupos)

```
 #   Etapa  Agente                     Trigger  Rotulo
 1.  F1     ava-asis-orchestrator      FP       AS-IS Diagnostic — Full Pipeline
 2.  F2a    ava-tobe-orchestrator      SD       TO-BE Architecture — Solution Design
 3.  F2b    ava-devops-orchestrator    DP       DevOps Plan
 4.  F2c    ava-qa-orchestrator        TPT      QA — Test Plan & Strategy
 5.  F3     ava-prototype              —        Prototype
 6.  F3S    ava-speckit-orchestrator   SK       SpecKit — Constitution, Specs, Plans & Tasks
 7.  F4     ava-stack-orchestrator     SG       Tech Stack — Stack Generation
 8.  F5     ava-devops-orchestrator    DE       DevOps Execute
 9.  F6     ava-qa-orchestrator        QE       QA — Quality Execute
10.  F8a    ava-summary                SAS      Summary — Generate
11.  F8b    ava-summary-remediation    —        Summary — Remediation
12.  F8c    ava-summary                SV       Summary — Validate
13.  F8d    ava-summary                SAS      Summary — Final
```

`--phase` aceita a **etapa** (`F2b`) ou o **grupo** (`F2`). Grupos: `F1`, `F2`, `F3`, `F3S`, `F4`, `F5`, `F6`, `F8`.

### 3.3 — Diagrama macro

```
                        ┌──────────────────────────────┐
                        │  ava-master-orchestrator     │  (transversal)
                        └──────────────┬───────────────┘
                                       ▼
F1  AS-IS Diagnostic ──────► 28 agentes (1 orq + 1 sub-orq seguranca + 7 sec + 4 db)
         │                   Fases A(W1,W2) · B · C · D + Consistency Gate + Human Gate
         ▼
F2a TO-BE Architecture ────► 22 agentes · Fases 0-Pre → 7 (22 sub-fases, 6 gates)
         │
         ├─► F2b DevOps Plan (DP)          ── 1 orq + azure-infra-estimator
         └─► F2c QA Test Plan (TPT)        ── 1 orq + ava-test-plan-tobe
         ▼
F3  Prototipo ─────────────► 1 agente (ava-prototype)
         ▼
F3S SpecKit Planning ──────► 7 agentes · waves 0,1,2,3,4,5,5a,5b,6,7
         │                   Gate de saida libera a F4
         ▼
F4  Stack / Codegen ───────► 24 agentes (14 registry + 10 build-cycle) · Steps 0→10
         ▼
F5  DevOps Execute (DE) ───► 15 agentes · 13 dispatches sequenciais
         ▼
F6  QA Quality Execute ────► 14 agentes · GR→BM→FTM→TS→TC→AS→DBI→CT→FT→FQ→ET+EC→PT→RS
         ▼
F7  Entregaveis ───────────► 10 agentes (7 no pipeline do master-orchestrator)
         ▼
F8  Summary ───────────────► 3 agentes · SAS → Remediation → SV → SAS final
```

### Regra principal

> Cada fase depende da anterior. Execute **na ordem da esteira**.
> Dentro de cada fase, o **orquestrador** coordena a execucao dos sub-agentes automaticamente e
> **le obrigatoriamente o `.md` do agente-alvo** antes de cada dispatch (`Dispatch Protocol`).

---

## 4. Formas de Execucao (CLI x Agentes)

### 4.1 — CLI `ava-pipeline.bat` (recomendado)

Fonte unica de modelo, endpoint, proxy e ordem: `src/shared/data/ava-pipeline.yaml`.

```bash
ava-pipeline.bat list --phases                 # mostra a ordem da esteira
ava-pipeline.bat doctor -p Meu-ERP             # diagnostico de ambiente
ava-pipeline.bat run -p Meu-ERP --all --dry-run
ava-pipeline.bat run -p Meu-ERP --all          # esteira completa (13 passos)
ava-pipeline.bat run -p Meu-ERP --phase F2 --yes   # grupo inteiro
ava-pipeline.bat run -p Meu-ERP --phase F2b --yes  # etapa unica
```

Precedencia de configuracao (forte → fraco):

1. flags do CLI (`--model`, `--engine`, `--via-proxy`, …)
2. variaveis de ambiente (`AVA_PIPELINE_*` / `AVA_FOUNDRY_*`)
3. `projects/{project}/context/project-config.yaml` → bloco `pipeline:`
4. `src/shared/data/ava-pipeline.yaml`
5. `_FALLBACK_DEFAULTS` em `pipeline_config.py`

### 4.2 — Invocacao direta do agente (Claude Code / Copilot)

O prompt enviado pelo CLI e `@{agent} | {trigger} | project: {P}`. Na sessao interativa vale o mesmo formato:

```
@ava-asis-orchestrator | FP | project: Meu-ERP
@ava-tobe-orchestrator | SD | project: Meu-ERP
```

Onde existir skill correspondente em `.github/skills/`, o atalho `/nome-do-agente` tambem funciona
(81 skills publicadas para 111 agentes `ava-*` em `.github/agents/`).

### 4.3 — `ava-master-orchestrator` (pipeline agentico)

Executa F1→F7 em sequencia, chamando `ava-summary` ao fim de **cada** fase.

| Codigo | Workflow      | Descricao                                                     |
| ------ | ------------- | ------------------------------------------------------------- |
| `FP` | full-pipeline | Executa F1→F2→F2.5→F3→F4→F5→F6→F7 em sequencia         |
| `SR` | status-report | Agent Registry + fase atual + tempo parcial                   |
| `RS` | resume        | Retomar a partir de uma fase (`RS \| resume_from_phase: F4`) |
| `HG` | human-gate    | Acionar gate de aprovacao humana manual                       |

> ℹ️ O `ava-master-orchestrator` v1.4.0 **ainda nao inclui a F3S**. Para a esteira com SpecKit,
> use o CLI (`ava-pipeline.bat`), que e a fonte de verdade da ordem.

---

## 5. F1 — Diagnostico AS-IS

### Objetivo

Analisar o sistema legado completo: codigo (via AST deterministico), banco de dados, integracoes,
seguranca, regras de negocio, qualidade e riscos.

### Como executar

```bash
ava-pipeline.bat run -p Meu-ERP --phase F1 --yes
```

```
@ava-asis-orchestrator | FP | project: Meu-ERP
```

### Triggers / Menu — `ava-asis-orchestrator` (v2.24.0)

| Codigo        | Workflow             | Descricao                                                                |
| ------------- | -------------------- | ------------------------------------------------------------------------ |
| `SA`        | start-analysis       | Inicia a analise AS-IS via DAG event-driven                              |
| `SA \| FULL` | start-analysis-clean | **Clean Start**: reset do workspace + SA DAG                       |
| `SR`        | status-report        | Progresso da esteira + Agent Completion Registry                         |
| `MR`        | master-report        | Gera o AS-IS Master Report final                                         |
| `HG`        | human-gate           | Aciona o gate de aprovacao humana                                        |
| `FP`        | full-pipeline        | **Full Pipeline**: SA DAG + validacao de artefatos + fallback HTML |

### Sub-fases (DAG event-driven)

| Sub-fase                      | Gatilho                                                               | Agentes despachados                                                                                                                                                                                                                                               |
| ----------------------------- | --------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **A · Wave 1**         | imediato                                                              | `ava-asis-solution-{legacy_technology}` (bloqueia Wave 2) · `ava-asis-security-orchestrator` (se `security_enabled_asis: true`, independente do gate)                                                                                                      |
| **Solution Agent Gate** | `status=completed AND artifacts_confirmed=true`                     | OPEN → Wave 2 · HALT se`failed` apos 4 retries ou `implementation_status=STUB`                                                                                                                                                                              |
| **Context Budget Gate** | antes do 1o dispatch da Wave 2                                        | `evaluate_context_budget()` — define `ast_artifact_slice[]` por agente e `execution_mode` (`inline` >400K · `bc_scoped` >700K)                                                                                                                        |
| **A · Wave 2**         | `on(solution ✓)` — 1 unica chamada de `artifact_gate.py --wave` | `ava-asis-inventory` · `ava-asis-db-analyzer` · `ava-asis-events-pubsub` · `ava-asis-documentation (FT)` · `ava-asis-documentation (VC)` · `ava-asis-business-rules-generator` (condicional) · `ava-asis-gaps-risks` (progressive enrichment) |
| **B**                   | `on(FT ✓)`                                                         | `ava-asis-documentation (RT)` — Screen Rules                                                                                                                                                                                                                   |
| **B**                   | `on(BRG ✓)`                                                        | `ava-asis-documentation (PR)` — Prototipos AS-IS (non-blocking)                                                                                                                                                                                                |
| **B**                   | `on(BRG ✓)`                                                        | `ava-asis-bridge-fastqa` — PBI + QA Pipeline (non-blocking)                                                                                                                                                                                                    |
| **B**                   | `on(Phase A ALL ✓)`                                                | `ava-asis-gap-migration-analyzer`                                                                                                                                                                                                                               |
| **C**                   | `on(Phase A ALL ✓ + RT ✓ + BRG ✓)`                               | Core Docs Ready Gate (consolidacao)                                                                                                                                                                                                                               |
| **D**                   | `on(gaps-risks ✓ + gap-migration ✓)`                              | Final Consistency Gate (7 checks em paralelo) → Master Report → Timing → Human Gate                                                                                                                                                                            |

### Sub-agentes de Seguranca (`ava-asis-security-orchestrator` v3.3.0 — SEMPRE 7/7)

| Sub-agente          | Skill ID                                | Artefatos obrigatorios                                                                                 |
| ------------------- | --------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| SAST                | `ava-asis-security-sast`              | `security-map.md` (OWASP), `vulnerabilities.md`, `privilege-matrix.md`                           |
| IAST                | `ava-asis-security-iast`              | `vulnerabilities.md`, `runtime-security-validation.md`                                             |
| Threat Model        | `ava-asis-security-threat-model`      | `asset-inventory.md`, `attack-surface.md`, `threat-model-stride.md`, `hardening-checklist.md`  |
| Taint               | `ava-asis-security-taint`             | `taint-flow-report.md`                                                                               |
| Dependency & Config | `ava-asis-security-dependency-config` | `SBOM.md`, `supply-chain-risk-report.md`, `sbom.cyclonedx.json`, `iac-cicd-security-report.md` |
| PT Pattern          | `ava-asis-security-pt-pattern`        | `pt-pattern-correlation.md`, `remediation-and-regression.md`, `remediation-backlog.md`           |
| Security Review     | `ava-asis-security-review`            | `security-map.md`, `vulnerabilities.md`, `owasp-coverage-matrix.md`                              |

> Loop de descoberta iterativo: iteracao 1 despacha os 7; a partir da 2, apenas os `candidates`
> (`status != finalized`). Um sub-agente e `finalized` quando converge (delta = 0 em 3 iteracoes consecutivas).

### Sub-agentes de Banco (`ava-asis-db-analyzer` v1.7.0)

| Sub-skill            | Engine     |
| -------------------- | ---------- |
| `ava-db-sqlserver` | SQL Server |
| `ava-db-oracle`    | Oracle     |
| `ava-db-mysql`     | MySQL      |
| `ava-db-mariadb`   | MariaDB    |

### Agentes de Solucao por tecnologia legada (roteamento)

| `legacy_technology` | Agente                                      | Status                     |
| --------------------- | ------------------------------------------- | -------------------------- |
| `delphi`            | `ava-asis-solution-delphi` (v2.8.3)       | ✅                         |
| `dotnet`            | `ava-asis-solution-dotnet` (v2.1.0)       | ✅                         |
| `vbnet`             | `ava-asis-solution-vbnet` (v2.0.0)        | ✅ alias legado            |
| `vb6`               | `ava-asis-solution-visualbasic` (v1.3.0)  | ✅                         |
| `java`              | `ava-asis-solution-java` (v2.2.0)         | ✅                         |
| `cobol`             | `ava-asis-solution-cobol` (v0.1.0)        | 🚧 STUB — HALT da esteira |
| `powerbuilder`      | `ava-asis-solution-powerbuilder` (v0.1.0) | 🚧 STUB — HALT da esteira |

### Gate humano

Apos o Final Consistency Gate:

- **Consistency Gate = ALL PASS + zero failed + `risk_level != critical`** → gate humano **pulado**
- **WARN/BLOCK ou `risk_level = critical`** → para e solicita mitigacao/aprovacao

### Artefatos gerados

```
projects/{PROJECT}/outputs/asis/
├── master-report.md
├── architecture-blueprint.md
├── bounded-context-map.md
├── inventory-report.md
├── complexity-map.md
├── gaps-risks-report.md
├── gap-list.md
├── risk-register.json
├── pattern-classifications.json
├── api-map.md
├── data-structure.md
├── form-registry.json
├── ast-raw/{language}/compressed/*.json   ← 01..10 (extracao deterministica)
├── diagrams/
│   ├── c4-context.mmd · c4-container.mmd · c4-component.mmd
│   └── sequence-*.mmd
├── docs/
│   ├── value-chain.md
│   ├── business-rules.md · business-rules.json
│   ├── behavior-catalog.json
│   ├── screen-navigation-map.md · screen-rules.md
│   └── prototype-asis/
├── db/
│   ├── db-analysis-report.md
│   ├── schema-inventory.md
│   ├── business-logic-in-db.md
│   └── er-diagram.mmd
├── integrations/
│   └── events-pubsub-report.md
└── security/
    ├── security-map.md · vulnerabilities.md · privilege-matrix.md
    ├── asset-inventory.md · attack-surface.md · threat-model-stride.md
    ├── taint-flow-report.md · owasp-coverage-matrix.md
    ├── SBOM.md · sbom.cyclonedx.json · supply-chain-risk-report.md
    ├── pt-pattern-correlation.md · remediation-backlog.md
    ├── executive-security-summary.md · technical-findings-report.md
    └── security-findings.json
```

---

## 6. F2 — Arquitetura TO-BE (F2a)

### Objetivo

Definir a arquitetura TO-BE (stack resolvida de `tobe_stack.*`) com base no diagnostico AS-IS:
ADRs, blueprint C4, bounded contexts, banco, seguranca, sizing, waves de migracao, OpenAPI,
documentacao, jornadas e design system.

### Pre-requisitos (inputs mandatorios declarados na esteira)

| Artefato                                        | Produzido por                                  |
| ----------------------------------------------- | ---------------------------------------------- |
| `outputs/asis/architecture-blueprint.md`      | `ava-asis-solution-{legacy_technology}` (F1) |
| `outputs/asis/bounded-context-map.md`         | `ava-asis-solution-{legacy_technology}` (F1) |
| `outputs/asis/docs/business-rules.md`         | `ava-asis-documentation` (F1)                |
| `outputs/asis/db/db-analysis-report.md`       | `ava-asis-db-analyzer` (F1)                  |
| `src/shared/data/reference-architecture.yaml` | repositorio                                    |

### Como executar

```bash
ava-pipeline.bat run -p Meu-ERP --phase F2a --yes
```

```
@ava-tobe-orchestrator | SD | project: Meu-ERP
```

### Sub-fases (22 fases numeradas + 6 gates)

| Fase                    | Agente                                                                          | O que produz                                                                                 |
| ----------------------- | ------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| **0-Pre**         | `ava-tobe-architecture-decision-matrix`                                       | `architecture-decision-matrix.md` — matriz de decisao pre-ADR                             |
| **0**             | `ava-tobe-adr`                                                                | `docs/decisions/ADR-*.md`                                                                  |
| *Gate 0→1*           | —                                                                              | Validacao de consistencia ADR ×`project-config.yaml`                                      |
| **1**             | `ava-tobe-architecture-design` (`CB` → `BC` → `TD`)                   | `architecture-blueprint.md`, `bounded-context-map.md`, `context-map.mmd`, diagramas C4 |
| *Inter-trigger Gate*  | —                                                                              | Entre`BC` e `TD`: confirma `bounded-context-map.md` + `context-map.mmd` em disco     |
| **1.4**           | `ava-tobe-database-policy`                                                    | `sql-strategy` / politica de banco TO-BE                                                   |
| **1.5**           | `ava-tobe-database-design` (+ `ava-tobe-sql-schema-to-mer`)                 | Modelo de dados TO-BE, MER                                                                   |
| **1.6**           | `ava-tobe-security-design`                                                    | `security-architecture.md`                                                                 |
| **2**             | `ava-tobe-architecture-technical` (`SS`,`NP`,`CS`,`QG`,`TF`,`PA`) | `tech-framework-document.md`                                                               |
| **2.5**           | `ava-tobe-migration-plan` (`backlog-tobe`)                                  | `backlog-tobe.md` (preliminar)                                                             |
| *Gate 2.5→3*         | —                                                                              | Backlog TO-BE obrigatorio antes do sizing                                                    |
| **2.7**           | `ava-tobe-migration-plan` (`WM`)                                            | `wave-model.json` — composicao de waves, T-shirt, scores                                  |
| **3**             | `ava-tobe-measure-size`                                                       | `sizing-report.md` + atualiza `wave-model.json` com FP/SP                                |
| **4**             | `ava-tobe-migration-plan`                                                     | `gap-list`, `wave-plan.md`, Gantt, ADO items, estimation report, activity plan           |
| *Gate 4-A / 4-B*      | —                                                                              | Pre-requisitos executaveis + verificacao executavel do`wave-plan.md`                       |
| **4.2**           | `ava-tobe-migration-plan` (`WCR`)                                           | Wave Cycle Refinement (condicional, pos-PILOT)                                               |
| **4.3**           | `ava-tobe-coexistence-strategy`                                               | `coexistence-strategy.md` (AS-IS ↔ TO-BE)                                                 |
| **4.5**           | `ava-tobe-risk-mitigation`                                                    | Plano de mitigacao de riscos                                                                 |
| **4.6**           | `ava-asis-gaps-risks` (skill residual)                                        | Registro de riscos residuais aceitos                                                         |
| **4.61**          | `ava-tobe-spec` (openapi-spec-tobe)                                           | `docs/openapi/bcNN-*.yaml` — design-first por BC                                          |
| **5**             | `ava-docs-tobe`                                                               | `api-map.md`, documentacao TO-BE                                                           |
| **5.1**           | `ava-developer-guide-tobe`                                                    | `wiki/developer-guide.md`                                                                  |
| **5.2**           | `ava-docs-tobe` (`RN`)                                                      | `regras-negocio.md` — AS-IS → TO-BE                                                      |
| **6**             | `ava-tobe-user-journeys` (`GJ`)                                             | `user-journeys-report.md` + mirror `docs/user-journeys.md`                               |
| **6.5**           | `ava-tobe-designer-system`                                                    | `design-system.md` — catalogo de Design System                                            |
| **7**             | `ava-readiness-gate`                                                          | Readiness Gate (Wave 1 — pre-Build Cycle)                                                   |
| *Gate F2→F3*         | `ava-requestor-inspection`                                                    | Requestor Inspection & Validation                                                            |
| *Gate 7→Build Cycle* | —                                                                              | Migration Design Checklist                                                                   |
| **Step F1**       | `ava-deliverable-strategy-align`                                              | Strategy Align (sessao PM-led)                                                               |
| **Step F2**       | `ava-deliverable-package-approval-doc`                                        | Package Approval Document (sign-off do SME)                                                  |
| **8**             | —                                                                              | Registro de Observabilidade (obrigatorio)                                                    |

**Agentes de apoio da F2 tambem registrados no modulo**: `ava-coder-dotnet`, `ava-dotnet-nuget-policy`,
`ava-tobe-security-review`, `ava-tobe-azure-infra-estimator` (usado em F2b).

### Protocolo de gates

Todos os gates seguem o **Non-Blocking Gate Protocol** (substitui HARD STOP): a fase dependente e
registrada como `SKIPPED` com motivo, e a esteira prossegue com as fases nao-dependentes.
Excecoes explicitas: Solution Agent Gate (F1) e o gate de saida da F3S.

### Artefatos gerados

```
projects/{PROJECT}/outputs/tobe/
├── architecture-blueprint.html
├── diagrams/
│   ├── architecture-blueprint.mmd · c4-context.mmd · c4-container.mmd · c4-component.mmd
│   ├── class-diagram.mmd · seq-arquitetural-tobe.mmd · context-map.mmd · migration-gantt.mmd
│   └── mer-tobe.mmd
├── migration/
│   └── wave-model.json
└── docs/
    ├── architecture-blueprint.md · bounded-context-map.md
    ├── architecture-decision-matrix.md
    ├── tech-framework-document.md
    ├── security-architecture.md
    ├── database-design.md · database-policy.md
    ├── sizing-report.md · migration-plan.md · wave-plan.md · backlog-tobe.md
    ├── coexistence-strategy.md · risk-mitigation-plan.md
    ├── regras-negocio.md · api-map.md · user-journeys.md · design-system.md
    ├── openapi/bcNN-*.yaml
    ├── decisions/ADR-*.md
    └── wiki/developer-guide.md
```

---

## 7. F2b — DevOps Plan (Momento 1)

### Objetivo

**Nao executa nada.** Decide a estrategia de infraestrutura e gera os planos + o esqueleto minimo
de wave 1 necessario para desbloquear o `readiness-gate` em projetos `build-cycle`.

### Como executar

```bash
ava-pipeline.bat run -p Meu-ERP --phase F2b --yes
```

```
@ava-devops-orchestrator | DP | project: Meu-ERP
```

### Sub-fases

| Passo            | Conteudo                                                                                                                                           |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Step 0** | Pre-flight (obrigatorio em ambos os momentos)                                                                                                      |
| **1.1**    | Le`architecture-blueprint.md` → `hosting_platform`, `database_engine`, `cache`, `api_gateway`, `observability`, `architecture_mode` |
| **1.2**    | Le`docs/decisions/ADR-*.md`                                                                                                                      |
| **DP-1**   | `ava-tobe-azure-infra-estimator` — dimensionamento de infra Azure                                                                               |
| **DP-2**   | `ava-build-cycle-iac` (condicional: `pipeline_mode == "build-cycle"`) — esqueleto wave 1                                                      |

### Artefatos gerados

```
projects/{PROJECT}/outputs/tobe/devops/
├── devops-plan.md
├── environments-plan.md
└── infra-sizing.md
```

---

## 8. F2c — QA Test Plan & Strategy (Momento 1)

### Objetivo

Planejamento de qualidade — separado da execucao (que roda na F6 da esteira), espelhando o par
`DP`/`DE` do DevOps.

### Como executar

```bash
ava-pipeline.bat run -p Meu-ERP --phase F2c --yes
```

```
@ava-qa-orchestrator | TPT | project: Meu-ERP
```

### Pre-condition Gate (TPT)

1. `project-config.yaml` existe
2. `bounded-context-map.md` (F2) existe com ≥ 1 Bounded Context
3. `wave-plan.md` (Fase 3 da F2) existe

### Sub-agente

| Agente                          | O que produz                                                                                           |
| ------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `ava-test-plan-tobe` (v5.1.0) | `qa/test-plan.md`, `qa/test-cases.md`, `tests/functional-test-matrix.md`, `qa/gap-analysis.md` |

> Os artefatos do `TPT` sao consumidos pelo `ava-devops-cd` na esteira DevOps.

---

## 9. F3 — Prototipo

### Objetivo

Gerar prototipo navegavel HTML para demonstracao ao cliente, com design tokens e rastreabilidade
por tela.

### Pre-requisitos

| Artefato                                                                                      | Produzido por                                         |
| --------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| `outputs/asis/docs/business-rules.md`                                                       | `ava-asis-documentation` (F1)                       |
| `outputs/tobe/docs/bounded-context-map.md`                                                  | `ava-tobe-architecture-design` (F2, trigger `BC`) |
| *(advisory)* `api-map.md`, `openapi/*.yaml`, `design-system.md`, `user-journeys.md` | F2                                                    |

### Como executar

```bash
ava-pipeline.bat run -p Meu-ERP --phase F3 --yes
```

```
@ava-prototype project: Meu-ERP
```

### Sub-fases internas (`ava-prototype` v1.3.0)

1. Registro de execucao (entrada)
2. Pre-Flight Check — verificacao de artefatos
3. Ingestao deterministica da fonte de design do cliente (Figma) + `design-input-traceability.json`
4. Protocolo de selecao do BC inicial
5. Extracao de design tokens com precedencia do Figma (4 passos) → `design-tokens.json`
6. Geracao de telas com layout do cliente + regras de consistencia com o Design System
7. Heuristicas Nielsen-Norman (H1–H10) + validacao de formularios + padroes de mensagem de erro
8. Rastreabilidade por tela → `screen-list.md` (RNF04: limite de telas por invocacao)
9. Protocolo de handoff para `ava-stack-orchestrator`
10. Registro de execucao (saida)

### Artefatos gerados

```
projects/{PROJECT}/outputs/tobe/prototype/
├── index.html                       ← Prototipo navegavel
├── screen-list.md
├── design-tokens.json
├── design-input-traceability.json
├── figma-spec.md
├── demo-script.md
└── assets/
```

---

## 10. F3S — SpecKit Planning

> Camada de planejamento deterministica introduzida pela `specs/039`, entre o prototipo e a
> geracao de codigo. **O gate de saida desta fase e o que libera a F4.**

### Objetivo

Transformar os artefatos TO-BE em constituicao, especificacoes por wave, planos de codegen, tasks
e um grafo global de rastreabilidade — tudo ancorado e verificavel, sem atribuicao por similaridade textual.

### Como executar

```bash
ava-pipeline.bat run -p Meu-ERP --phase F3S --yes
```

```
@ava-speckit-orchestrator | SK | project: Meu-ERP
```

### Triggers / Menu — `ava-speckit-orchestrator` (v3.0.0)

| Codigo | Descricao                                                |
| ------ | -------------------------------------------------------- |
| `SK` | Roda a F3S completa — gate de entrada ate gate de saida |
| `GC` | So a constituicao                                        |
| `GS` | So as especificacoes                                     |
| `GL` | So os planos                                             |
| `GT` | So as tasks e a rastreabilidade                          |
| `AC` | So a auditoria de conformidade                           |
| `GG` | So os gates, sem gerar nada — custo zero de inferencia  |

### Sub-fases (waves de `F3S.yaml` — fonte unica do fan-out)

| Wave             | Depende de | Bloqueante | Conteudo                                                                                                |
| ---------------- | ---------- | ---------- | ------------------------------------------------------------------------------------------------------- |
| **wave0**  | —         | ✅         | `speckit-entry-gate` — `artifact_gate_speckit.py --gate entry`                                     |
| **wave1**  | wave0      | ✅         | `ava-speckit-constitution` (`GC`) → `constitution.md`                                            |
| **wave2**  | wave1      | ✅         | `speckit-wave-manifest` — `speckit_wave_manifest.py` (manifesto deterministico por migration wave) |
| **wave3**  | wave2      | —         | `ava-speckit-specification` (`GS`) — **1 por entrada do manifesto** (fan-out)                |
| **wave4**  | wave3      | —         | `ava-speckit-planning` (`GL`) — **1 por spec com `codegen=true`**                          |
| **wave5**  | wave4      | —         | `ava-speckit-tasks` (`GT`) — **1 por plano** → `specs/{feature}/task-fragment.json`       |
| **wave5a** | wave5      | ✅         | `f4s-scaffold-inject` — injecao de specs de scaffold por `target_stack`                            |
| **wave5b** | wave5a     | ✅         | `speckit-task-compile` · `speckit-ledger-init` · `speckit-dependency-checks`                    |
| **wave6**  | wave5b     | —         | `ava-speckit-compliance` (`AC`)                                                                     |
| **wave7**  | wave6      | ✅         | `speckit-exit-gate` — `artifact_gate_speckit.py --gate exit`                                       |

### Steps do orquestrador (mapeamento 1:1 com as waves)

| Step | Acao                                                                                                                                     |
| ---- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| 0    | Gate de entrada (obrigatorio)                                                                                                            |
| 1    | wave1 · Constituicao                                                                                                                    |
| 2    | wave2 · Manifesto deterministico por migration wave                                                                                     |
| 3    | wave3 · Especificacoes por migration wave                                                                                               |
| 4    | wave4 · Planos de codegen                                                                                                               |
| 5    | wave5 · Tasks                                                                                                                           |
| 6    | Compilar o grafo global —`speckit_task_compiler.py compile` (ciclo / ref ausente / ownership ambiguo ⇒ exit 2 e **hard stop**) |
| 7    | Razao de progresso —`task_ledger.py --init` cria `tasks-progress.json`                                                                 |
| 8    | Checks deterministicos —`python -m src.shared.checks --suite speckit_traceability` (CHK-SK-016..018)                                  |
| 9    | wave6 · Conformidade                                                                                                                    |
| 10   | Gate de saida (obrigatorio)                                                                                                              |
| 11   | Registro de Observabilidade (obrigatorio)                                                                                                |

> ⚠️ `ava-speckit-prototype-spec` (v2.0.0) e o 7o agente do modulo — gera a spec do prototipo
> quando a wave correspondente exige rastreabilidade tela→spec.

### Artefatos gerados

```
projects/{PROJECT}/outputs/tobe/speckit/
├── constitution.md
├── execution-log.json
├── wave-manifest.json
├── traceability.json          ← v4, escrito SOMENTE pelo compilador
├── tasks-progress.json           ← razao de progresso, escrito SOMENTE pelo task_ledger
├── compliance-report.md
└── specs/
    └── {feature}/
        ├── spec.md
        ├── plan.md · plan-graph.json
        ├── tasks.md · task-fragment.json
        └── checklist.md
```

---

## 11. F4 — Stack / Geracao de Codigo

### Objetivo

Gerar o codigo completo de backend e frontend a partir das specs/plans/tasks da F3S, com validacao
de build deterministica.

### Como executar

```bash
ava-pipeline.bat run -p Meu-ERP --phase F4 --yes
```

```
@ava-stack-orchestrator | SG | project: Meu-ERP
```

### Fan-out por ledger

A F4 despacha **um `ava-f4s-codegen-agent` por grupo de tasks** do razao de progresso
(`tasks-progress.json`), mapeado por `target_stack` (`dotnet`, `spring-boot`, `fastapi`, `gin`,
`nestjs`, `angular`, `react`, `vue`, `blazor`). Sem `tasks-progress.json` em disco, o passo degrada
para despacho unico.

### Triggers / Menu — `ava-stack-orchestrator` (v1.8.0)

| Codigo | Descricao                                        |
| ------ | ------------------------------------------------ |
| `SG` | Start full stack generation (backend + frontend) |
| `BG` | Backend only                                     |
| `FG` | Frontend only                                    |
| `CV` | Contract validation (backend ↔ frontend)        |
| `SR` | Status report                                    |

### Sub-fases

| Step             | Conteudo                                                                                  |
| ---------------- | ----------------------------------------------------------------------------------------- |
| **0**      | Pre-flight (obrigatorio, antes de qualquer geracao)                                       |
| 0.1              | Le`project-config.yaml`                                                                 |
| 0.2              | Aplica resolucao de overrides                                                             |
| 0.3b             | Resolve o roster de agentes de`effective_config` (ConfigStack.yaml)                     |
| 0.3c             | Le`modernization_scope` e `target_modules`                                            |
| 0.4              | Determina o roster completo por`effective_config` + `pipeline_mode`                   |
| 0.5              | Checa pre-requisitos por validacao deterministica de caminhos                             |
| 0.5.1            | Checa o readiness gate                                                                    |
| 0.6              | Emite o Pre-Flight Report                                                                 |
| 0.7              | Se`prereqs_gate ❌` ou `readiness_gate ❌` → **STOP**, nao gera nada           |
| 0.9              | Build Runner Detection (pre-codegen — informativo + consentimento do usuario)            |
| **1**      | Recebe o Solution Blueprint aprovado + inicializa timing (NTP)                            |
| **1.5**    | `ava-stack-docs-researcher` → `docs-research-bundle.md` (cache de 24h)               |
| **2**      | Extrai bounded contexts e API surface (+ BC Filter Check por`target_modules`)           |
| **3**      | Gera**backend** por bounded context (paralelo por BC)                               |
| **4**      | Contrato de API (OpenAPI) — resolvido pelo proprio coder backend, por BC                 |
| **5**      | Gera**frontend** consumindo os contratos                                            |
| **5.5**    | ⛔ Post-Codegen Scaffold Verification (bloqueante) —`verify_scaffold.py` por manifesto |
| **6**      | Valida consistencia entre contratos backend ↔ frontend                                   |
| **6a**     | 🔨 Build Validation (Backend) —`ava-stack-build-validator`                             |
| **7**      | Aciona AG-07 para geracao de testes                                                       |
| **8 / 8a** | 🔨 Build Validation (Frontend) —`ava-stack-build-validator`                            |
| **9**      | Captura timestamps finais (NTP)                                                           |
| **10**     | ⛔ Timing Output (passo final obrigatorio)                                                |

### Roteamento de agentes coder

**Backend** (`tobe_stack.backend_framework`):

| Valor           | Agente                                | Status  |
| --------------- | ------------------------------------- | ------- |
| `dotnet`      | `ava-stack-dotnet-backend` (v3.0.0) | ✅      |
| `spring-boot` | `ava-stack-java-backend` (v2.1.0)   | ✅      |
| `fastapi`     | `ava-stack-python-backend` (v2.1.0) | ✅      |
| `gin`         | `ava-stack-go-backend` (v2.1.0)     | ✅      |
| `nestjs`      | `ava-stack-node-backend` (v0.1.0)   | 🚧 STUB |

**Frontend** (`tobe_stack.frontend_framework`):

| Valor                   | Agente                                      | Status                  |
| ----------------------- | ------------------------------------------- | ----------------------- |
| `angular`             | `ava-stack-angular-frontend` (v4.0.0)     | ✅                      |
| `blazor`              | `ava-stack-blazor-frontend` (v1.0.0)      | ✅                      |
| `react`               | `ava-stack-react-frontend` (v3.0.0)       | ✅                      |
| `react` (build-cycle) | `ava-build-cycle-react-scaffold` (v1.0.0) | ✅                      |
| `vue`                 | `ava-stack-vue-frontend` (v1.0.0)         | ✅                      |
| `svelte`              | `ava-stack-svelte-frontend`               | 🚧 STUB (nao publicado) |

**Cross-cutting (reliability pipeline)**:

| Agente                        | Responsabilidade                                           | Posicao                    |
| ----------------------------- | ---------------------------------------------------------- | -------------------------- |
| `ava-stack-docs-researcher` | Pesquisa docs atualizadas de pacotes/frameworks            | Step 1.5                   |
| `ava-stack-build-validator` | Compilacao + lint + CVE scan deterministicos               | Step 6a / 8a               |
| `ava-stack-build-fixer`     | Sub-agente de correcao de erros de compilacao              | interno ao build-validator |
| `ava-f4s-codegen-agent`     | Executor por grupo de tasks do ledger (fan-out da esteira) | Steps 3 e 5                |

### Sub-agentes de Build Cycle (`tech-stack/templates/` — 10)

| Agente                               | Escopo                 |
| ------------------------------------ | ---------------------- |
| `ava-build-cycle-dotnet-scaffold`  | Scaffold .NET          |
| `ava-build-cycle-cqrs`             | CQRS / MediatR         |
| `ava-build-cycle-efcore`           | EF Core / persistencia |
| `ava-build-cycle-minimal-apis`     | Minimal APIs           |
| `ava-build-cycle-angular`          | Scaffold Angular       |
| `ava-build-cycle-ngrx`             | NgRx                   |
| `ava-build-cycle-react-scaffold`   | Scaffold React         |
| `ava-build-cycle-java-scaffold`    | Scaffold Java          |
| `ava-build-cycle-java-persistence` | Persistencia Java      |
| `ava-build-cycle-python-scaffold`  | Scaffold Python        |

**Manifestos de scaffold** (`src/shared/data/scaffold-manifests/`): `angular`, `react`, `blazor`, `dotnet`.
Sem manifesto para `{frontend_framework}` → o gate 5.5 e pulado com WARNING, nunca HARD STOP.

### Artefatos gerados

```
projects/{PROJECT}/outputs/tobe/source-code/
├── backend/
│   ├── {Module}/
│   │   ├── Domain/           ← Entities, ValueObjects, Events
│   │   ├── Application/      ← Commands, Queries, Handlers, Validators
│   │   ├── Infrastructure/   ← Persistence, Repositories, EF Core
│   │   └── API/              ← Controllers, Minimal APIs
│   └── openapi/{bc}.yaml
├── frontend/                 ← app Angular / React / Vue / Blazor
└── security/
    └── SecurityComplianceReport-Consolidated.md
```

---

## 12. F5 (esteira) — DevOps Execute (Momento 2)

> ⚠️ **F5 na esteira = DevOps.** No registry, `F5` e o modulo `qa-agents`. Ver [§3.1](#31--os-dois-eixos-de-numeracao-divergencia-intencional).

### Objetivo

Infraestrutura como codigo, containerizacao, pipelines CI/CD, observabilidade, custo e paridade
legado × migrado — seguindo o plano do Momento 1.

### Pre-requisitos

| Artefato                               | Produzido por                                     |
| -------------------------------------- | ------------------------------------------------- |
| `outputs/tobe/source-code`           | `ava-stack-orchestrator` (F4)                   |
| `outputs/tobe/devops/devops-plan.md` | `ava-devops-orchestrator` (F2b, trigger `DP`) |

### Como executar

```bash
ava-pipeline.bat run -p Meu-ERP --phase F5 --yes
```

```
@ava-devops-orchestrator | DE | project: Meu-ERP
```

### Sub-fases (13 dispatches sequenciais + pre-flight)

| Ordem            | Agente                                  | Modo                                                      |
| ---------------- | --------------------------------------- | --------------------------------------------------------- |
| **Step 0** | —                                      | Pre-flight (obrigatorio)                                  |
| 2.0              | —                                      | Verifica`devops-plan.md` (ausente → WARN + defaults)   |
| 1                | `ava-devops-iac`                      | sequencial                                                |
| 2                | `ava-devops-ci`                       | sequencial                                                |
| 3                | `ava-devops-cd`                       | sequencial                                                |
| 4                | `ava-devops-containerize`             | sequencial                                                |
| 5                | `ava-devops-iac-azure`                | condicional:`cloud_provider == "azure"`                 |
| 6                | `ava-devops-iac-aws`                  | 🚧 STUB — condicional:`cloud_provider == "aws"`        |
| 7                | `ava-devops-iac-gcp`                  | 🚧 STUB — condicional:`cloud_provider == "gcp"`        |
| 8                | `ava-devops-iac-k8s-native`           | 🚧 STUB — condicional:`cloud_provider == "k8s-native"` |
| 9                | `ava-devops-cost-estimate`            | sequencial                                                |
| 10               | `ava-devops-monitoring-observability` | sequencial                                                |
| 11               | `ava-devops-compare-version`          | sequencial — produz`parity-test-report.md`             |
| 12               | `ava-devops-package-approval`         | sequencial                                                |
| 13               | `ava-build-cycle-iac`                 | condicional:`pipeline_mode == "build-cycle"`            |
| —               | `ava-devops-podman-run`               | avulso — execucao local dos containers                   |

> ℹ️ `ava-devops-iac` e `ava-build-cycle-iac` sao **mutuamente exclusivos**. Em `build-cycle`,
> o `ava-build-cycle-iac` roda no Momento 1 e o `ava-devops-iac` e pulado no Momento 2.

### Artefatos gerados

```
projects/{PROJECT}/outputs/tobe/
├── source-code/
│   ├── backend/Dockerfile · .dockerignore
│   ├── frontend/Dockerfile · .dockerignore · nginx.conf
│   ├── docker-compose.yml
│   ├── docker-compose.staging.yml
│   └── docker-compose.prod.yml
└── iac/
    ├── terraform/ · bicep/
    ├── containers/containerization-report.md
    ├── ci/*.yml · cd/*.yml
    ├── monitoring/observability-plan.md
    ├── cost/cost-estimate-report.md
    ├── parity/parity-test-report.md
    └── approval/package-approval.md
```

---

## 13. F6 (esteira) — QA Quality Execute (Momento 2)

> ⚠️ **F6 na esteira = QA.** No registry, `F6` e o modulo `devops-agents`. Ver [§3.1](#31--os-dois-eixos-de-numeracao-divergencia-intencional).

### Objetivo

Executar toda a esteira de qualidade sobre o codigo gerado e o ambiente provisionado.

### Pre-requisitos

| Artefato                          | Produzido por                                  |
| --------------------------------- | ---------------------------------------------- |
| `outputs/tobe/source-code`      | `ava-stack-orchestrator` (F4)                |
| `outputs/tobe/qa/test-cases.md` | `ava-qa-orchestrator` (F2c, trigger `TPT`) |
| `outputs/tobe/qa/test-plan.md`  | `ava-qa-orchestrator` (F2c, trigger `TPT`) |

### Como executar

```bash
ava-pipeline.bat run -p Meu-ERP --phase F6 --yes
```

```
@ava-qa-orchestrator | QE | project: Meu-ERP
```

> ⛔ Use `QE`, **nao** `TPT`. Repetir `TPT` aqui roda o planejamento de novo e a esteira de
> execucao nunca dispara. `QS` e alias **depreciado** de `QE`.

### Pre-condition Gate (QE) — 4 passos

1. `bounded-context-map.md` (F2) existe
2. Planejamento concluido (Momento 1 — `TPT`)
3. Esteira de codigo concluida (F4 Stack)
4. Esteira DevOps Momento 2 concluida (`DE`)
   4b. `parity-test-report.md` presente (WARNING, nao bloqueia)

Falha → `DEFERRED` (precisa reinvocar depois que as dependencias existirem).

### Sub-fases — cadeia interna do `QE`

```
GR → BM → FTM → TS → TC → AS → DBI → CT → FT → FQ → ET + EC → PT → RS
```

| Trigger | Agente                                             | O que faz                                                                                     |
| ------- | -------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `GR`  | `ava-qa-gaps-requirements`                       | Gaps de requisitos + testabilidade arquitetural (anti-patterns, DI, acoplamento)              |
| `BM`  | `ava-qa-behavior-mapping`                        | Behavior mapping                                                                              |
| `FTM` | `ava-qa-test-case-generator`                     | Functional Test Matrix — rastreabilidade RF → cenarios de aceite ⛔ gate proprio            |
| `TS`  | `ava-qa-bridge-fastqa-tobe` (Momento 1)          | Test scenarios BDD Gherkin (`.feature`) — absorveu o extinto `ava-qa-scenario-generator` |
| `TC`  | `ava-qa-test-case-generator`                     | Casos de teste detalhados                                                                     |
| `AS`  | `ava-qa-script-generator`                        | Automation scripts (xUnit, Playwright, k6)                                                    |
| `DBI` | `ava-qa-db-integrity-test`                       | Migrations, constraints PK/FK/UK, indices, equivalencia de SPs ⛔ gate proprio                |
| `CT`  | `ava-qa-contract-test-generator`                 | Consumer-driven contracts (PactNet) Front↔Back e inter-BC ⛔ gate proprio                    |
| `FT`  | `ava-qa-frontend-test-generator`                 | Jest + Angular Testing Library (components, services, stores) ⛔ gate proprio                 |
| `FQ`  | `ava-qa-bridge-fastqa-tobe` (Momento 2)          | Exploratorios live (POISED/VADER) + automacao Playwright/TS ⛔ gate proprio                   |
| `ET`  | `ava-qa-exploratory`                             | Teste exploratorio autonomo (paralelo a automacao)                                            |
| `EC`  | `ava-qa-evidence-capture`                        | Captura de evidencias (continuo)                                                              |
| `PT`  | *(artefato do `ava-devops-compare-version`)*   | Parity Test — verificacao de disponibilidade do`parity-test-report.md`                     |
| `RS`  | `ava-qa-script-generator` (`mode: regression`) | Regression Suite derivada da paridade                                                         |
| —      | `ava-qa-defect-identifier`                       | Classifica defeitos durante a execucao                                                        |

> ⚠️ **`PT` → `RS` sao etapas terminais obrigatorias**: qualquer trigger que produza artefatos QA
> executa `PT` e `RS` ao final, sem trigger explicito.

### Artefatos gerados

```
projects/{PROJECT}/outputs/qa/
├── quality-strategy.md
├── qa-master-report.md
├── functional-test-matrix.md
├── evidence-capture-report.md
├── parity-dashboard.md
├── gaps-requirements/ · behavior-mapping/
├── test-case-generator/ · script-generator/
├── db-integrity/ · contract-tests/ · frontend-tests/
├── exploratory/ · evidence-capture/ · defect-identifier/
└── regression/

projects/{PROJECT}/outputs/tobe/tests/
├── features/{feature-name}.feature
└── functional-test-matrix.md
```

---

## 14. F7 — Entregaveis

> ℹ️ A F7 **nao existe como etapa do CLI** (`ava-pipeline.yaml` nao tem passo F7). Ela e executada
> pelo `ava-master-orchestrator` (Step 7) ou invocando os agentes diretamente.

### Objetivo

Consolidar todos os artefatos em um pacote de entrega rastreavel para o cliente.

### Como executar

```
@ava-deliverable-packager project: Meu-ERP
```

### Sub-agentes (7 no pipeline + 3 avulsos)

| Ordem | Agente                                   | O que faz                                                  |
| ----- | ---------------------------------------- | ---------------------------------------------------------- |
| 1     | `ava-deliverable-tech-docs`            | Documentacao tecnica final                                 |
| 2     | `ava-deliverable-migration-plan`       | Plano de migracao publicavel                               |
| 3     | `ava-deliverable-security-compliance`  | Relatorio de seguranca e compliance                        |
| 4     | `ava-deliverable-test-evidence`        | Pacote de evidencias de teste                              |
| 5     | `ava-deliverable-code-templates`       | Templates de codigo reutilizaveis                          |
| 6     | `ava-deliverable-client-demo`          | Material de apresentacao e demo                            |
| 7     | `ava-deliverable-packager`             | Empacota, indexa, gera checksums e verifica integridade    |
| —    | `ava-deliverable-strategy-align`       | Strategy Align — sessao PM-led (invocado na F2, Step F1)  |
| —    | `ava-deliverable-package-approval-doc` | Package Approval Document — sign-off do SME (F2, Step F2) |
| —    | `ava-requestor-inspection`             | Requestor Inspection & Validation (Gate F2→F3)            |

### Skills do `ava-deliverable-packager`

Completeness Checker · Index Generator · Package Assembler · Delivery Report Generator ·
Checksum Generator (SHA256 `.hash` por artefato) · Index Integrity Verifier.

### Pre-conditions (gate obrigatorio)

| Diretorio         | Acao se ausente/vazio                                                |
| ----------------- | -------------------------------------------------------------------- |
| `outputs/asis/` | ❌ BLOCKED — executar`@ava-asis-orchestrator`                     |
| `outputs/tobe/` | ❌ BLOCKED — executar`@ava-tobe-orchestrator`                     |
| `outputs/qa/`   | ⚠️ WARNING — prosseguir sem cobertura QA (registrar no relatorio) |

### Protocolo de Integridade do Indice

1. Verificar artefatos orfaos (arquivo existe, mas nao esta no indice)
2. Verificar links quebrados (link no indice, mas arquivo nao existe)
3. Gerar tabela de integridade do indice
4. Gate de falha
5. Registro de Observabilidade (obrigatorio)

### Artefatos gerados

```
projects/{PROJECT}/outputs/deliverables/
├── wave-{N}-package/
├── wave-{N}-index.md
├── wave-{N}-delivery-report.md
├── tech-docs/
├── migration-plan/
├── security-compliance-report.md · security-compliance-summary.json
├── test-evidence/
├── code-templates/
├── client-demo/
├── package-approval-document.md
└── *.hash                       ← SHA256 por artefato
```

---

## 15. F8 — Summary

### Objetivo

Gerar o relatorio HTML interativo consolidando TODOS os artefatos de todas as fases, remediar
lacunas e validar contra 101 regras de nao-regressao.

### Como executar

```bash
ava-pipeline.bat run -p Meu-ERP --phase F8 --yes
```

### Sub-fases (4 etapas da esteira)

| Etapa         | Agente                               | Trigger | O que faz                                                          |
| ------------- | ------------------------------------ | ------- | ------------------------------------------------------------------ |
| **F8a** | `ava-summary` (v1.8.2)             | `SAS` | Gera o HTML consolidado                                            |
| **F8b** | `ava-summary-remediation` (v1.4.2) | —      | Remedia lacunas e placeholders detectados                          |
| **F8c** | `ava-summary-validate` (v1.4.1)    | `SV`  | Auditoria de nao-regressao — 101 regras, exit 1 bloqueia promocao |
| **F8d** | `ava-summary`                      | `SAS` | Regenera o HTML final apos a remediacao                            |

### Triggers / Menu — `ava-summary`

| Codigo  | Workflow            | Quando usar                                               |
| ------- | ------------------- | --------------------------------------------------------- |
| `GS`  | generate-summary    | Summary completo (todos os outputs disponiveis)           |
| `SAS` | summary-asis-only   | Summary parcial — apenas fase AS-IS                      |
| `STO` | summary-tobe-only   | Summary parcial — apenas fase TO-BE                      |
| `SI`  | summary-independent | Independente — aponta para qualquer diretorio de outputs |
| `PR`  | preview-report      | Preview do HTML no terminal (links e estrutura)           |
| `VD`  | validate-data       | Validar completude dos dados antes de gerar               |
| `UP`  | update-summary      | Atualizar summary existente com novos artefatos           |

> ⚠️ **Aviso do trigger `GS`**: o Summary consome os entregaveis de F7 para preencher o menu
> _Entregaveis_. Execute `@ava-deliverable-packager` **antes** de `@ava-summary GS`.

### Sub-fases internas do `ava-summary`

| Step               | Conteudo                                                                         |
| ------------------ | -------------------------------------------------------------------------------- |
| **0**        | Leitura obrigatoria de artefatos por fase (antes do Step 1)                      |
| **Pre-Step** | Garantir artefatos criticos                                                      |
| **1**        | Contexto e descoberta (Discovery & Inventory)                                    |
| **2**        | Extracao de dados (Data Extraction + D.* Field Schemas + Data Source Mapping)    |
| **3**        | Construcao do HTML (Template Engine + Blueprint compatibility gate para Mermaid) |
| **4**        | Validacao e entrega                                                              |
| **5**        | Registro de Observabilidade (obrigatorio)                                        |
| Hook               | Validation Gate obrigatorio pos-geracao (`ava-summary-validate`)               |

### Modos de execucao

| Modo | Trigger      | Descricao                                                 |
| ---- | ------------ | --------------------------------------------------------- |
| 1    | *(padrao)* | Apos workflow completo — le todos os outputs disponiveis |
| 2    | `SAS`      | Apos AS-IS apenas — demais secoes como "Nao executado"   |
| 3    | `STO`      | Apos TO-BE — assume AS-IS como input existente           |
| 4    | `SI`       | Independente — qualquer diretorio de outputs             |

### Caracteristicas do relatorio HTML

- **Autocontido**: CSS, JS e Mermaid.js embutidos inline
- **Bilingue**: PT/EN com seletor de idioma
- **Interativo**: navegacao por fases, filtros, graficos
- **Rastreavel**: inclui `trace_id` e timestamp NTP
- **Degradacao graceful**: secoes ausentes marcadas como "Pending"
- **Blueprint compatibility gate**: `mermaid.render()` e probado antes de publicar; falha ou
  resultado inconclusivo bloqueia a publicacao

### Artefatos gerados

```
projects/{PROJECT}/outputs/summary/
├── summary.html            ← Relatorio HTML interativo
├── summary-data.json       ← Dados estruturados
├── validation-report.md · validation-report.json
├── remediation-report.md
└── index.md                ← Indice dos artefatos
```

---

## 16. Fluxo Completo Passo a Passo

### 16.1 — Execucao rapida via CLI (recomendado)

```bash
# 1. Criar projeto
cp -r projects/_template projects/Meu-ERP

# 2. Editar configuracao
#    → Preencher projects/Meu-ERP/context/project-config.yaml

# 3. Diagnostico
ava-pipeline.bat doctor -p Meu-ERP

# 4. Simular
ava-pipeline.bat run -p Meu-ERP --all --dry-run

# 5. Executar a esteira completa (13 passos)
ava-pipeline.bat run -p Meu-ERP --all
```

Ou fase a fase:

```bash
ava-pipeline.bat run -p Meu-ERP --phase F1  --yes   # AS-IS Diagnostic
ava-pipeline.bat run -p Meu-ERP --phase F2a --yes   # TO-BE Architecture
ava-pipeline.bat run -p Meu-ERP --phase F2b --yes   # DevOps Plan
ava-pipeline.bat run -p Meu-ERP --phase F2c --yes   # QA Test Plan
ava-pipeline.bat run -p Meu-ERP --phase F3  --yes   # Prototipo
ava-pipeline.bat run -p Meu-ERP --phase F3S --yes   # SpecKit Planning
ava-pipeline.bat run -p Meu-ERP --phase F4  --yes   # Stack / Codegen
ava-pipeline.bat run -p Meu-ERP --phase F5  --yes   # DevOps Execute
ava-pipeline.bat run -p Meu-ERP --phase F6  --yes   # QA Quality Execute
ava-pipeline.bat run -p Meu-ERP --phase F8  --yes   # Summary (F8a→F8d)
```

### 16.2 — Execucao via agentes (Claude Code / Copilot)

```
@ava-asis-orchestrator     | FP  | project: Meu-ERP    ← F1  (aguardar gate)
@ava-tobe-orchestrator     | SD  | project: Meu-ERP    ← F2a (aguardar gate)
@ava-devops-orchestrator   | DP  | project: Meu-ERP    ← F2b
@ava-qa-orchestrator       | TPT | project: Meu-ERP    ← F2c
@ava-prototype                   | project: Meu-ERP    ← F3
@ava-speckit-orchestrator  | SK  | project: Meu-ERP    ← F3S (gate de saida libera F4)
@ava-stack-orchestrator    | SG  | project: Meu-ERP    ← F4
@ava-devops-orchestrator   | DE  | project: Meu-ERP    ← F5
@ava-qa-orchestrator       | QE  | project: Meu-ERP    ← F6
@ava-deliverable-packager        | project: Meu-ERP    ← F7
@ava-summary               | GS  | project: Meu-ERP    ← F8
```

### 16.3 — Diagrama de execucao completo

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          INICIO DO PROJETO                               │
│  1. cp -r projects/_template projects/{PROJECT}                          │
│  2. Preencher project-config.yaml   3. ava-pipeline.bat doctor           │
└──────────────────────────┬───────────────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  F1: @ava-asis-orchestrator | FP                        28 agentes       │
│  Wave 1: solution-{tech} ─┬─ security-orchestrator (7 sub-agentes)       │
│            │              │                                              │
│      [Solution Agent Gate] + [Context Budget Gate]                       │
│            ▼                                                             │
│  Wave 2: inventory · db-analyzer (4 sub-skills) · events-pubsub ·        │
│          doc:FT · doc:VC · brg:* · gaps-risks                            │
│  Fase B: doc:RT · doc:PR · bridge-fastqa · gap-migration-analyzer        │
│  Fase C: Core Docs Ready Gate                                            │
│  Fase D: Consistency Gate (7 checks) → Master Report → [GATE HUMANO]     │
└──────────────────────────┬───────────────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  F2a: @ava-tobe-orchestrator | SD                       22 agentes       │
│  0-Pre → 0 → [Gate 0→1] → 1 → 1.4 → 1.5 → 1.6 → 2 → 2.5 → [Gate 2.5→3]   │
│  → 2.7 → 3 → 4 [Gate 4-A/4-B] → 4.2 → 4.3 → 4.5 → 4.6 → 4.61             │
│  → 5 → 5.1 → 5.2 → 6 → 6.5 → 7 → [Gate F2→F3] → [Gate Build Cycle]       │
└────────────┬─────────────────────────────────────────┬───────────────────┘
             ▼                                         ▼
┌────────────────────────────┐          ┌──────────────────────────────────┐
│ F2b: @ava-devops-orch | DP │          │ F2c: @ava-qa-orch | TPT          │
│ azure-infra-estimator      │          │ ava-test-plan-tobe               │
└────────────┬───────────────┘          └──────────────┬───────────────────┘
             └──────────────────┬──────────────────────┘
                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  F3: @ava-prototype                                      1 agente        │
│  index.html · screen-list.md · design-tokens.json                        │
└──────────────────────────┬───────────────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  F3S: @ava-speckit-orchestrator | SK                     7 agentes       │
│  wave0 gate → wave1 constitution → wave2 manifest → wave3 specs (fan-out)│
│  → wave4 plans → wave5 tasks → wave5a scaffold-inject                    │
│  → wave5b compile+ledger+checks → wave6 compliance → wave7 EXIT GATE     │
└──────────────────────────┬───────────────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  F4: @ava-stack-orchestrator | SG                       24 agentes       │
│  Step 0 pre-flight → 1.5 docs-researcher → 2 BCs → 3 backend (par. BC)   │
│  → 4 OpenAPI → 5 frontend → 5.5 scaffold verify → 6 contratos            │
│  → 6a/8a build-validator (+ build-fixer) → 7 testes → 10 timing          │
└──────────────────────────┬───────────────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  F5: @ava-devops-orchestrator | DE                      15 agentes       │
│  iac → ci → cd → containerize → iac-{cloud} → cost → monitoring          │
│  → compare-version → package-approval → build-cycle-iac                  │
└──────────────────────────┬───────────────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  F6: @ava-qa-orchestrator | QE                          14 agentes       │
│  GR→BM→FTM→TS→TC→AS→DBI→CT→FT→FQ→ET+EC→PT→RS                             │
└──────────────────────────┬───────────────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  F7: @ava-deliverable-packager                          10 agentes       │
│  tech-docs → migration-plan → security-compliance → test-evidence        │
│  → code-templates → client-demo → packager (checksums + integridade)     │
└──────────────────────────┬───────────────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  F8: F8a summary → F8b remediation → F8c validate → F8d summary final    │
│  Relatorio HTML interativo autocontido, bilingue e rastreavel            │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 17. Shared Context, Observabilidade e Rastreabilidade

### shared-context.md

Arquivo central lido e atualizado por **todos os agentes**:

```
projects/{PROJECT}/context/shared-context.md
```

**Funcoes**:

- Registra status de cada fase (Pending / In Progress / Completed / Failed / Skipped / Deferred)
- Lista outputs disponiveis para agentes downstream
- Armazena decisoes arquiteturais (ADRs)
- Propagado automaticamente — **nao editar manualmente**

### trace_id

UUID unico gerado no inicio da esteira, propagado por todos os agentes e incluido em todos os
relatorios. Permite rastreabilidade completa de ponta a ponta.

### Registro de Observabilidade (obrigatorio)

Todo agente encerra com um bloco de observabilidade:

```bash
python src/shared/tools/pipeline_observer.py -p {project_name} track \
  --agent {agent_id} --phase {phase} --version {version}
```

A versao declarada aqui **deve** bater com o `version:` do frontmatter —
`verify_agent_observability.py` reprova as divergencias. A consolidacao da economia do proxy
Headroom tambem e obrigatoria ao fim de cada orquestrador.

### Timing (NTP)

Com `timing_benchmark_enabled: true`, cada orquestrador captura timestamps reais via
`python src/shared/utils/ntp_time.py` e emite blocos **MACRO** (por fase) e **MICRO** (por agente).
⛔ Nunca usar o clock do LLM.

### Ledger de tasks (F3S → F4)

`tasks-progress.json` e a razao de progresso da geracao de codigo. E escrito **apenas** por
`task_ledger.py` e pelo wrapper de passo da F4 — nunca por agente.

### `artifacts_confirmed` e medido, nunca declarado

Somente `artifact_gate.py` verificando bytes em disco pode marcar `artifacts_confirmed: true`.
A mensagem de conclusao do agente (`↳ ✅`) **nao e evidencia**.

### agent-task-config.yaml

Para projetos ja iniciados, substitui o `project-config.yaml` com estado de execucao em runtime.
Gerado automaticamente pelo primeiro orquestrador.

---

## 18. Execucao de Agentes Individuais

Qualquer agente pode ser executado isoladamente, sem passar pelo orquestrador:

```
@ava-asis-solution-delphi        project: Meu-ERP   ← so analise de codigo Delphi
@ava-asis-db-analyzer            project: Meu-ERP   ← so analise de banco
@ava-asis-security-orchestrator  project: Meu-ERP   ← so o assessment de seguranca (7 sub-agentes)
@ava-tobe-architecture-design | CB | project: Meu-ERP
@ava-tobe-adr                    project: Meu-ERP
@ava-speckit-constitution | GC | project: Meu-ERP
@ava-stack-build-validator       project: Meu-ERP
@ava-qa-orchestrator | TS |      project: Meu-ERP   ← so cenarios BDD Gherkin
@ava-devops-containerize         project: Meu-ERP
@ava-summary | SI |              project: Meu-ERP
```

**Importante**:

- Agentes individuais dependem do `project-config.yaml` e de outputs de fases anteriores.
- Triggers isolados de QA (`GR`, `BM`, `TS`, `TC`, `AS`, `ET`, `EC`) servem para **reprocessar um
  artefato pontual** — **nao substituem** o `QE`.
- Executar um agente fora do orquestrador deixa o `shared-context.md` dessincronizado; rode o
  orquestrador da fase para reconciliar.

---

## 19. Troubleshooting

### Agente nao encontra o projeto

**Causa**: `project_name` vazio ou `project-config.yaml` nao preenchido.
**Solucao**: verificar `projects/{PROJECT}/context/project-config.yaml`.

### Agente falha por falta de outputs anteriores

**Causa**: fase anterior nao executada.
**Solucao**: executar as fases na ordem da esteira. `ava-pipeline.bat list --phases` mostra a ordem.

### F1 interrompe com HALT no Solution Agent Gate

**Causa**: o agente de solucao falhou apos 4 retries **ou** `implementation_status == STUB`
(`cobol`, `powerbuilder`).
**Solucao**: para tecnologias STUB nao ha caminho automatico — a Wave 2 e as fases B/C/D nunca sao
despachadas por design.

### Wave 2 da F1 rodou serializada (`DISPATCH_SERIALIZATION`)

**Causa**: guard chamado N vezes (`should_dispatch()` intercalado) em vez de 1 chamada de wave.
**Solucao**: usar `artifact_gate.py --project {p} --wave phase_a_wave2 --json` em **uma** chamada.

### Diretorios criados e vazios em `outputs/asis/docs/`

**Causa**: agente despachado como background agent `general-purpose` — gera conteudo em contexto
sem flush para disco.
**Solucao**: persistencia sempre sincrona (`task` com `mode: sync` ou `execution_mode: inline`),
via BatchWriteProtocol em uma unica chamada `Bash`.

### Gate humano bloqueia a execucao

**Causa**: riscos criticos identificados ou Consistency Gate com WARN/BLOCK.
**Solucao**: revisar `gaps-risks-report.md`, definir mitigacoes e aprovar manualmente.

### F3S para com exit 2 no compilador

**Causa**: ciclo no grafo, referencia cross-feature ausente ou ownership ambiguo.
**Solucao**: corrigir as ancoras (`BR-*`, `operationId`, `US-*`, `TC-*`) nas specs/plans. O
compilador nao atribui por similaridade textual — a ancora precisa ser verificavel.

### F4 gera codigo sem ter visto o blueprint / prototipo

**Causa**: bloco `inputs.mandatory` do passo F4 removido do `ava-pipeline.yaml`.
**Solucao**: nao remover. Esse bloco e a correcao do defeito central da `specs/039` (prototipo 13%,
regras 17%, APIs 14%, build FALHA quando ausente).

### F4 para no Post-Codegen Scaffold Verification

**Causa**: o coder reportou COMPLETED mas faltam arquivos obrigatorios do manifesto.
**Solucao**: rodar `verify_scaffold.py --manifest {stack}` e reexecutar o coder. Se nao existir
manifesto para o framework, o gate e pulado com WARNING (nunca HARD STOP).

### F6 (QA) cai em `DEFERRED`

**Causa**: `QE` disparado antes da F4 (Stack) e da F5 (DevOps `DE`).
**Solucao**: concluir F4 e F5 e **reinvocar** `QE`.

### `TPT` nao gerou `evidence-capture-report.md` / `parity-dashboard.md`

**Causa**: esses 3 artefatos so existem apos um `QE` concluido com sucesso.
**Solucao**: rodar `QE` (nao `TPT`).

### Summary mostra secoes como "Pending"

**Causa**: artefatos esperados nao encontrados.
**Solucao**: verificar as fases anteriores. O summary usa degradacao graceful.

### Summary bloqueia por `publicationAllowed: false`

**Causa**: Blueprint compatibility gate — `Syntax error in text` ou falha de runtime do Mermaid.
**Solucao**: ler o compatibility report, distinguir `rootCause` de `stage` e corrigir o `.mmd`
de origem. Artefato ausente e diagnostico de fronteira upstream, nao falha de compatibilidade.

### Menu "Entregaveis" do Summary vazio

**Causa**: `outputs/deliverables/` vazio ou ausente.
**Solucao**: executar `@ava-deliverable-packager` antes de `@ava-summary GS`.

### Proxy Headroom nao respondeu — esteira rodou sem compressao

**Causa**: venv da tool nao resolvido antes do `python` do PATH.
**Solucao**: `prefer_tool_venv: true` no `ava-pipeline.yaml`; para abortar em vez de degradar,
usar `pipeline.proxy.mode: require`.

### `agent_registry` acusa agente ausente

**Causa**: frontmatter malformado (texto antes do bloco `---`) — o parser exige `---` na 1a linha.
**Solucao**: corrigir o frontmatter. Foi exatamente o que tirou `ava-summary` e
`ava-summary-validate` do registro (por isso o CLI emite `⚠️ F8a: agente 'ava-summary' ausente do agent_registry`).

---

## 20. Referencia Rapida — Todos os Agentes por Fase

> Eixo do **registry** (modulo de origem). Legenda: **ORQ** orquestrador · **STUB** nao implementado ·
> **DEPR** depreciado · **sub** sub-skill nao despachavel diretamente.

### F1 — AS-IS Diagnostic (29 arquivos · 28 ativos)

| Agente                                  | Versao | Flags | Funcao                                                   |
| --------------------------------------- | ------ | ----- | -------------------------------------------------------- |
| `ava-asis-orchestrator`               | 2.24.0 | ORQ   | Coordena o diagnostico AS-IS (DAG event-driven)          |
| `ava-asis-solution-delphi`            | 2.8.3  |       | Analise AST de codigo Delphi                             |
| `ava-asis-solution-dotnet`            | 2.1.0  |       | Analise AST de codigo .NET                               |
| `ava-asis-solution-vbnet`             | 2.0.0  |       | Analise VB.NET (alias legado de solution-dotnet)         |
| `ava-asis-solution-visualbasic`       | 1.3.0  |       | Analise VB6                                              |
| `ava-asis-solution-java`              | 2.2.0  |       | Analise AST de codigo Java                               |
| `ava-asis-solution-cobol`             | 0.1.0  | STUB  | Analise COBOL                                            |
| `ava-asis-solution-powerbuilder`      | 0.1.0  | STUB  | Analise PowerBuilder                                     |
| `ava-asis-documentation`              | 3.3.0  |       | Value Chain, Screen Flow, Screen Rules, Prototipos AS-IS |
| `ava-asis-inventory`                  | 1.6.1  |       | Inventario quantitativo: LOC, classes, complexidade      |
| `ava-asis-db-analyzer`                | 1.7.0  |       | Tabelas, procedures, ERD, logica de negocio no banco     |
| `ava-db-sqlserver`                    | 1.2.0  | sub   | Conector SQL Server do db-analyzer                       |
| `ava-db-oracle`                       | 1.2.0  | sub   | Conector Oracle do db-analyzer                           |
| `ava-db-mysql`                        | 1.2.0  | sub   | Conector MySQL do db-analyzer                            |
| `ava-db-mariadb`                      | 1.2.0  | sub   | Conector MariaDB do db-analyzer                          |
| `ava-asis-events-pubsub`              | 1.2.1  |       | Integracoes, eventos e pub/sub                           |
| `ava-asis-business-rules-generator`   | 1.0.0  |       | `business-rules.md` a partir do AST                    |
| `ava-asis-gaps-risks`                 | 1.4.0  |       | Riscos e gaps priorizados (progressive enrichment)       |
| `ava-asis-gap-migration-analyzer`     | 1.1.0  |       | GAP List de migracao                                     |
| `ava-asis-bridge-fastqa`              | 4.1.0  |       | Ponte PBI + QA Pipeline (FastQA)                         |
| `ava-asis-security-orchestrator`      | 3.3.0  | ORQ   | Coordena os 7 sub-agentes de seguranca                   |
| `ava-asis-security-sast`              | 2.2.0  |       | SAST — OWASP, privilege matrix                          |
| `ava-asis-security-iast`              | 2.2.0  |       | IAST — validacao de seguranca em runtime                |
| `ava-asis-security-threat-model`      | 2.2.0  |       | STRIDE, asset inventory, attack surface                  |
| `ava-asis-security-taint`             | 2.2.0  |       | Taint analysis / fluxo de dados                          |
| `ava-asis-security-dependency-config` | 2.3.0  |       | SBOM, CVEs, supply chain, IaC/CI-CD                      |
| `ava-asis-security-pt-pattern`        | 2.3.0  |       | Correlacao com pentest, remediation backlog              |
| `ava-asis-security-review`            | 2.3.0  |       | Revisao de seguranca, OWASP coverage matrix              |
| `ava-asis-security-review`            | 1.4.0  | DEPR  | Versao antiga em`agents/security-review-asis.md`       |

### F2 — TO-BE Architecture (22)

| Agente                                    | Versao | Flags | Funcao                                                           |
| ----------------------------------------- | ------ | ----- | ---------------------------------------------------------------- |
| `ava-tobe-orchestrator`                 | 2.10.0 | ORQ   | Coordena a arquitetura TO-BE (fases 0-Pre → 7)                  |
| `ava-tobe-architecture-decision-matrix` | 1.1.0  |       | Matriz de decisao pre-ADR (fase 0-Pre)                           |
| `ava-tobe-adr`                          | 1.2.0  |       | Geracao de ADRs (fase 0)                                         |
| `ava-tobe-architecture-design`          | 1.2.0  |       | Blueprint C4, bounded contexts, diagramas (fase 1)               |
| `ava-tobe-database-policy`              | 1.0.1  |       | Politica de banco / sql-strategy (fase 1.4)                      |
| `ava-tobe-database-design`              | 1.0.0  |       | Modelo de dados TO-BE (fase 1.5)                                 |
| `ava-tobe-sql-schema-to-mer`            | 1.0.0  |       | Geracao de MER a partir do schema SQL                            |
| `ava-tobe-security-design`              | 2.0.0  |       | Arquitetura de seguranca TO-BE (fase 1.6)                        |
| `ava-tobe-architecture-technical`       | 1.0.0  |       | Tech framework, patterns, quality gates (fase 2)                 |
| `ava-tobe-migration-plan`               | 1.4.0  |       | Backlog, wave model, wave plan, Gantt, WCR (fases 2.5/2.7/4/4.2) |
| `ava-tobe-measure-size`                 | 1.1.0  |       | Function points, story points, T-shirt (fase 3)                  |
| `ava-tobe-coexistence-strategy`         | 1.2.0  |       | Coexistencia AS-IS ↔ TO-BE (fase 4.3)                           |
| `ava-tobe-risk-mitigation`              | 1.0.0  |       | Plano de mitigacao de riscos (fase 4.5)                          |
| `ava-tobe-spec`                         | 1.1.0  |       | OpenAPI design-first por BC (fase 4.61)                          |
| `ava-docs-tobe`                         | 1.2.0  |       | Documentacao TO-BE + regras de negocio (fases 5 / 5.2)           |
| `ava-developer-guide-tobe`              | 1.1.1  |       | Guia do desenvolvedor (fase 5.1)                                 |
| `ava-tobe-user-journeys`                | 1.0.1  |       | Jornadas do usuario + BDD (fase 6)                               |
| `ava-tobe-designer-system`              | 1.0.1  |       | Catalogo de Design System (fase 6.5)                             |
| `ava-tobe-azure-infra-estimator`        | 1.2.0  |       | Dimensionamento de infra Azure (usado na F2b)                    |
| `ava-tobe-security-review`              | 1.0.0  |       | Revisao de seguranca do desenho TO-BE                            |
| `ava-coder-dotnet`                      | 1.0.0  |       | Scaffolding .NET base                                            |
| `ava-dotnet-nuget-policy`               | 1.0.0  |       | Politica de pacotes NuGet                                        |

### F3 — Prototype (1)

| Agente            | Versao | Funcao                                                 |
| ----------------- | ------ | ------------------------------------------------------ |
| `ava-prototype` | 1.3.0  | Prototipo HTML navegavel + design tokens + screen-list |

### F3S — SpecKit Planning (7)

| Agente                         | Versao | Flags | Funcao                                           |
| ------------------------------ | ------ | ----- | ------------------------------------------------ |
| `ava-speckit-orchestrator`   | 3.0.0  | ORQ   | Coordena as waves 0→7 da F3S                    |
| `ava-speckit-constitution`   | 1.0.0  |       | `constitution.md` (wave1, trigger `GC`)      |
| `ava-speckit-specification`  | 2.0.0  |       | Spec por migration wave (wave3,`GS`)           |
| `ava-speckit-planning`       | 4.0.0  |       | Plano de codegen por spec (wave4,`GL`)         |
| `ava-speckit-tasks`          | 4.0.0  |       | `task-fragment.json` por plano (wave5, `GT`) |
| `ava-speckit-compliance`     | 1.1.0  |       | Auditoria de conformidade (wave6,`AC`)         |
| `ava-speckit-prototype-spec` | 2.0.0  |       | Spec do prototipo (rastreabilidade tela→spec)   |

### F4 — Stack / Codegen (14 registry + 10 build-cycle = 24)

| Agente                               | Versao | Flags | Funcao                                                     |
| ------------------------------------ | ------ | ----- | ---------------------------------------------------------- |
| `ava-stack-orchestrator`           | 1.8.0  | ORQ   | Coordena a geracao de codigo (Steps 0→10)                 |
| `ava-f4s-codegen-agent`            | 0.1.0  |       | Executor por grupo de tasks do ledger (fan-out)            |
| `ava-stack-dotnet-backend`         | 3.0.0  |       | Backend .NET — Clean Architecture, CQRS, MediatR, EF Core |
| `ava-stack-java-backend`           | 2.1.0  |       | Backend Java / Spring Boot                                 |
| `ava-stack-python-backend`         | 2.1.0  |       | Backend Python / FastAPI                                   |
| `ava-stack-go-backend`             | 2.1.0  |       | Backend Go / Gin                                           |
| `ava-stack-node-backend`           | 0.1.0  | STUB  | Backend Node / NestJS                                      |
| `ava-stack-angular-frontend`       | 4.0.0  |       | Frontend Angular — standalone components, NgRx, MSAL      |
| `ava-stack-react-frontend`         | 3.0.0  |       | Frontend React                                             |
| `ava-stack-vue-frontend`           | 1.0.0  |       | Frontend Vue                                               |
| `ava-stack-blazor-frontend`        | 1.0.0  |       | Frontend Blazor                                            |
| `ava-stack-docs-researcher`        | 1.0.0  |       | Pesquisa de docs atualizadas (Step 1.5)                    |
| `ava-stack-build-validator`        | 2.3.0  |       | Compilacao + lint + CVE scan (Steps 6a/8a)                 |
| `ava-stack-build-fixer`            | 1.1.0  |       | Correcao de erros de compilacao (sub-agente)               |
| `ava-build-cycle-dotnet-scaffold`  | 1.0.0  |       | Scaffold .NET (build-cycle)                                |
| `ava-build-cycle-cqrs`             | 1.0.0  |       | CQRS / MediatR (build-cycle)                               |
| `ava-build-cycle-efcore`           | 1.1.0  |       | EF Core / persistencia (build-cycle)                       |
| `ava-build-cycle-minimal-apis`     | 1.0.0  |       | Minimal APIs (build-cycle)                                 |
| `ava-build-cycle-angular`          | 1.0.0  |       | Scaffold Angular (build-cycle)                             |
| `ava-build-cycle-ngrx`             | 1.0.0  |       | NgRx (build-cycle)                                         |
| `ava-build-cycle-react-scaffold`   | 1.0.0  |       | Scaffold React (build-cycle)                               |
| `ava-build-cycle-java-scaffold`    | 1.0.0  |       | Scaffold Java (build-cycle)                                |
| `ava-build-cycle-java-persistence` | 1.0.0  |       | Persistencia Java (build-cycle)                            |
| `ava-build-cycle-python-scaffold`  | 1.0.0  |       | Scaffold Python (build-cycle)                              |

### F5 (registry) — QA Agents (14)

| Agente                             | Versao | Flags | Funcao                                                     |
| ---------------------------------- | ------ | ----- | ---------------------------------------------------------- |
| `ava-qa-orchestrator`            | 2.1.2  | ORQ   | Coordena QA — Momento 1 (`TPT`) e Momento 2 (`QE`)    |
| `ava-test-plan-tobe`             | 5.1.0  |       | Test plan TO-BE + functional test matrix (Momento 1)       |
| `ava-qa-gaps-requirements`       | 1.0.1  |       | Gaps de requisitos + testabilidade arquitetural (`GR`)   |
| `ava-qa-behavior-mapping`        | 1.0.0  |       | Behavior mapping (`BM`)                                  |
| `ava-qa-bridge-fastqa-tobe`      | 2.0.1  |       | Cenarios BDD (`TS`) + exploracao/automacao (`FQ`)      |
| `ava-qa-test-case-generator`     | 1.0.0  |       | Casos de teste (`TC`) e functional test matrix (`FTM`) |
| `ava-qa-script-generator`        | 1.6.1  |       | Automation scripts (`AS`) e regression suite (`RS`)    |
| `ava-qa-db-integrity-test`       | 1.3.0  |       | Migrations, constraints, indices, SPs (`DBI`)            |
| `ava-qa-contract-test-generator` | 1.1.0  |       | Consumer-driven contracts / PactNet (`CT`)               |
| `ava-qa-frontend-test-generator` | 1.1.0  |       | Jest + Angular Testing Library (`FT`)                    |
| `ava-qa-exploratory`             | 2.0.0  |       | Teste exploratorio autonomo (`ET`)                       |
| `ava-qa-evidence-capture`        | 2.1.0  |       | Captura de evidencias (`EC`)                             |
| `ava-qa-defect-identifier`       | 1.0.0  |       | Classificacao de defeitos                                  |
| `ava-qa-scenario-generator`      | 2.1.0  |       | Cenarios BDD Gherkin (absorvido pelo bridge no`TS`)      |

### F6 (registry) — DevOps (15)

| Agente                                  | Versao | Flags | Funcao                                                                                    |
| --------------------------------------- | ------ | ----- | ----------------------------------------------------------------------------------------- |
| `ava-devops-orchestrator`             | 1.0.0  | ORQ   | Coordena DevOps —`DP` (plano) e `DE` (execucao)                                      |
| `ava-devops-iac`                      | 1.0.0  |       | Infraestrutura como codigo (generico)                                                     |
| `ava-devops-ci`                       | 1.4.0  |       | Pipeline CI (GitHub Actions / Azure DevOps)                                               |
| `ava-devops-cd`                       | 1.0.0  |       | Pipeline CD com blue-green / canary                                                       |
| `ava-devops-containerize`             | 1.0.1  |       | Dockerfiles multi-stage + docker-compose (dev/staging/prod)                               |
| `ava-devops-iac-azure`                | 2.6.0  |       | IaC Azure — Terraform + Bicep (AKS/App Service, SQL, Redis, Key Vault, AppInsights, ACR) |
| `ava-devops-iac-aws`                  | 1.0.0  | STUB  | IaC AWS                                                                                   |
| `ava-devops-iac-gcp`                  | 1.0.0  | STUB  | IaC GCP                                                                                   |
| `ava-devops-iac-k8s-native`           | 1.0.0  | STUB  | IaC Kubernetes nativo                                                                     |
| `ava-devops-cost-estimate`            | 1.0.0  |       | Estimativa de custo de infraestrutura                                                     |
| `ava-devops-monitoring-observability` | 1.0.0  |       | Monitoramento e observabilidade                                                           |
| `ava-devops-compare-version`          | 1.0.0  |       | Testes comparativos legado × migrado (`parity-test-report.md`)                         |
| `ava-devops-package-approval`         | 1.0.0  |       | Fluxo de aprovacao de releases                                                            |
| `ava-devops-podman-run`               | 1.1.0  |       | Execucao local dos containers via Podman                                                  |
| `ava-build-cycle-iac`                 | 1.0.0  |       | IaC esqueleto wave-1 (`pipeline_mode: build-cycle`)                                     |

### F7 — Deliverables (10)

| Agente                                   | Versao | Funcao                                                  |
| ---------------------------------------- | ------ | ------------------------------------------------------- |
| `ava-deliverable-packager`             | 1.0.0  | Empacota, indexa, gera checksums e verifica integridade |
| `ava-deliverable-tech-docs`            | 1.0.0  | Documentacao tecnica final                              |
| `ava-deliverable-migration-plan`       | 1.0.0  | Plano de migracao publicavel                            |
| `ava-deliverable-security-compliance`  | 1.1.0  | Relatorio de seguranca e compliance                     |
| `ava-deliverable-test-evidence`        | 1.0.0  | Pacote de evidencias de teste                           |
| `ava-deliverable-code-templates`       | 1.0.0  | Templates de codigo reutilizaveis                       |
| `ava-deliverable-client-demo`          | 1.0.0  | Material de apresentacao e demo                         |
| `ava-deliverable-strategy-align`       | 1.0.0  | Strategy Align — sessao PM-led (F2, Step F1)           |
| `ava-deliverable-package-approval-doc` | 1.0.0  | Package Approval Document — sign-off SME (F2, Step F2) |
| `ava-requestor-inspection`             | 1.0.0  | Requestor Inspection & Validation (Gate F2→F3)         |

### F8 — Summary (3)

| Agente                      | Versao | Funcao                                            |
| --------------------------- | ------ | ------------------------------------------------- |
| `ava-summary`             | 1.8.2  | Relatorio HTML interativo consolidado (F8a / F8d) |
| `ava-summary-remediation` | 1.4.2  | Remediacao de lacunas e placeholders (F8b)        |
| `ava-summary-validate`    | 1.4.1  | Auditoria de nao-regressao — 101 regras (F8c)    |

> ⚠️ `ava-summary` e `ava-summary-validate` **nao aparecem** no `agent_registry` por frontmatter
> malformado (texto antes do bloco `---`). O CLI emite aviso mas executa normalmente.

### Transversais (2)

| Agente                      | Versao | Flags | Funcao                                                     |
| --------------------------- | ------ | ----- | ---------------------------------------------------------- |
| `ava-master-orchestrator` | 1.4.0  | ORQ   | Pipeline agentico F1→F7 com Summary a cada fase           |
| `ava-readiness-gate`      | 1.0.0  |       | Gate de readiness compartilhado (F2 fase 7, F4 Step 0.5.1) |

---

## 21. Sumario de Quantidades

### 21.1 — Agentes por fase

| Fase            | Modulo                |       Agentes | Orquestradores |           Sub-agentes / skills |       Stubs | Depreciados |
| --------------- | --------------------- | ------------: | -------------: | -----------------------------: | ----------: | ----------: |
| **F1**    | `asis-diagnostic`   |  **29** |              2 |     11 (7 seguranca + 4 banco) |           2 |           1 |
| **F2**    | `tobe-architecture` |  **22** |              1 |                             — |           0 |           0 |
| **F3**    | `prototype`         |   **1** |              0 |                             — |           0 |           0 |
| **F3S**   | `speckit`           |   **7** |              1 |                             — |           0 |           0 |
| **F4**    | `tech-stack`        |  **24** |              1 | 10 build-cycle + 1 build-fixer |           1 |           0 |
| **F5**    | `qa-agents`         |  **14** |              1 |                             — |           0 |           0 |
| **F6**    | `devops-agents`     |  **15** |              1 |                             — |        3 ¹ |           0 |
| **F7**    | `deliverables`      |  **10** |              0 |                             — |           0 |           0 |
| **F8**    | `summary`           |   **3** |              0 |                             — |           0 |           0 |
| **—**    | transversais          |   **2** |              1 |                             — |           0 |           0 |
| **TOTAL** |                       | **127** |    **8** |                   **21** | **6** | **1** |

¹ `ava-devops-iac-aws`, `ava-devops-iac-gcp` e `ava-devops-iac-k8s-native` sao declarados
🚧 STUB na tabela de roteamento do `ava-devops-orchestrator` (o frontmatter nao carrega a flag).

**Agentes ativos** (excluindo o depreciado): **126**.

### 21.2 — Reconciliacao com as fontes

| Fonte                                         |                                       Contagem | Diferenca para 127 |
| --------------------------------------------- | ---------------------------------------------: | ------------------ |
| `python src/shared/tools/agent_registry.py` |                114 arquivos (110 despachaveis) | −13               |
| `.github/agents/*.agent.md`                 | 121 (111`ava-*` + 10 `speckit.*` upstream) | —                 |
| `.github/skills/`                           |                           81 skills publicadas | —                 |

**Os 13 agentes fora do `agent_registry`** (o registry so varre `**/agents/**/*.md` com frontmatter na 1a linha):

| Agente                                      | Motivo                                                |
| ------------------------------------------- | ----------------------------------------------------- |
| `ava-summary` · `ava-summary-validate` | Frontmatter malformado (texto antes do`---`)        |
| `ava-build-cycle-*` (10)                  | Vivem em`tech-stack/templates/`, nao em `agents/` |
| `ava-readiness-gate`                      | Vive em`shared/`, nao em `agents/`                |

### 21.3 — Fases e sub-fases

| Nivel                                     |     Quantidade | Detalhe                                                                                                                   |
| ----------------------------------------- | -------------: | ------------------------------------------------------------------------------------------------------------------------- |
| **Fases da esteira** (grupos)       |    **8** | F1, F2, F3, F3S, F4, F5, F6, F8                                                                                           |
| **Etapas da esteira** (`--phase`) |   **13** | F1, F2a, F2b, F2c, F3, F3S, F4, F5, F6, F8a, F8b, F8c, F8d                                                                |
| **Fases do registry** (modulos)     |    **9** | F1, F2, F3, F3S, F4, F5, F6, F7, F8                                                                                       |
| Sub-fases F1                              |    **6** | Phase A (Wave 1, Wave 2), Phase B, Phase C, Phase D + Consistency Gate                                                    |
| Gates F1                                  |    **5** | Solution Agent Gate · Context Budget Gate · Dispatch Guard · Core Docs Ready · Final Consistency                      |
| Sub-fases F2                              |   **22** | 0-Pre, 0, 1, 1.4, 1.5, 1.6, 2, 2.5, 2.7, 3, 4, 4.2, 4.3, 4.5, 4.6, 4.61, 5, 5.1, 5.2, 6, 6.5, 7                           |
| Gates F2                                  |    **6** | 0→1 · inter-trigger BC/TD · 2.5→3 · 4-A/4-B · F2→F3 · 7→Build Cycle                                              |
| Steps extras F2                           |    **2** | Step F1 Strategy Align · Step F2 Package Approval                                                                        |
| Sub-fases F2b (DevOps Plan)               |    **2** | Step 0 pre-flight · Momento 1 (DP)                                                                                       |
| Sub-fases F2c (QA Plan)                   |    **2** | Pre-condition Gate (TPT) · Test Plan TO-BE                                                                               |
| Sub-fases F3 (Prototipo)                  |   **10** | Registro → pre-flight → ingestao Figma → BC inicial → tokens → telas → UX → rastreabilidade → handoff → registro |
| Waves F3S                                 |   **10** | wave0, 1, 2, 3, 4, 5, 5a, 5b, 6, 7                                                                                        |
| Steps F3S                                 |   **12** | Step 0 a Step 11                                                                                                          |
| Sub-fases F4                              |   **11** | Step 0 (0.1–0.9) + Steps 1, 1.5, 2, 3, 4, 5, 5.5, 6, 6a, 7, 8/8a, 9, 10                                                  |
| Sub-fases F5 (DevOps DE)                  |   **14** | Step 0 pre-flight + 13 dispatches                                                                                         |
| Sub-fases F6 (QA QE)                      |   **14** | GR, BM, FTM, TS, TC, AS, DBI, CT, FT, FQ, ET, EC, PT, RS                                                                  |
| Gates F6                                  |    **7** | QE, TPT, FTM, DBI, CT, FT, FQ                                                                                             |
| Sub-fases F7                              |    **7** | 7 dispatches sequenciais (+3 agentes avulsos)                                                                             |
| Sub-fases F8                              |    **4** | F8a Generate · F8b Remediation · F8c Validate · F8d Final                                                              |
| **Total de sub-fases documentadas** | **~124** | soma das linhas acima                                                                                                     |

### 21.4 — Triggers por orquestrador

| Orquestrador                       |        Triggers | Codigos                                                                                                                                            |
| ---------------------------------- | --------------: | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ava-master-orchestrator`        |               4 | `FP`, `SR`, `RS`, `HG`                                                                                                                     |
| `ava-asis-orchestrator`          |               6 | `SA`, `SA\|FULL`, `SR`, `MR`, `HG`, `FP`                                                                                                |
| `ava-tobe-orchestrator`          |    2 principais | `SD`, `FR` (+ triggers internos `CB`, `BC`, `TD`, `WM`, `WCR`, `RN`, `GJ`, `SS`, `NP`, `CS`, `QG`, `TF`, `PA`)       |
| `ava-speckit-orchestrator`       |               7 | `SK`, `GC`, `GS`, `GL`, `GT`, `AC`, `GG`                                                                                             |
| `ava-stack-orchestrator`         |               5 | `SG`, `BG`, `FG`, `CV`, `SR`                                                                                                             |
| `ava-qa-orchestrator`            | 3 + 14 isolados | `TPT`, `QE`, `QS` (depr.) + `GR`, `BM`, `TS`, `TC`, `FTM`, `DBI`, `CT`, `FT`, `AS`, `ET`, `EC`, `FQ`, `PT`, `RS` |
| `ava-devops-orchestrator`        |               2 | `DP`, `DE`                                                                                                                                     |
| `ava-asis-security-orchestrator` |              — | dispatch incondicional 7/7 sub-agentes                                                                                                             |
| `ava-summary`                    |               7 | `GS`, `SAS`, `STO`, `SI`, `PR`, `VD`, `UP`                                                                                           |
| **TOTAL**                    |    **50** |                                                                                                                                                    |

### 21.5 — Resumo executivo

```
┌────────────────────────────────────────────────────────────────┐
│  AVA FABRIC — NUMEROS DA ESTEIRA                               │
├────────────────────────────────────────────────────────────────┤
│  Agentes (arquivos)              127   (126 ativos, 1 depr.)   │
│  Agentes despachaveis            110   (agent_registry)        │
│  Orquestradores                    8   (7 de fase + 1 seguranca)│
│  Sub-agentes / sub-skills         21   (7 sec + 4 db + 10 BC)  │
│  Stubs                             6   (2 F1 + 1 F4 + 3 F6)    │
│  Depreciados                       1                           │
├────────────────────────────────────────────────────────────────┤
│  Fases (grupos da esteira)         8   F1 F2 F3 F3S F4 F5 F6 F8│
│  Etapas da esteira (--phase)      13                           │
│  Fases do registry (modulos)       9   F1..F8 + F3S            │
│  Sub-fases documentadas         ~124                           │
│  Gates                            18   (5 F1 + 6 F2 + 7 F6)    │
│  Triggers totais                  50                           │
├────────────────────────────────────────────────────────────────┤
│  Skills publicadas (.github)      81                           │
│  Agentes publicados (.github)    121   (111 ava-* + 10 speckit)│
└────────────────────────────────────────────────────────────────┘
```

---

## Comandos de verificacao

Sempre que este guia parecer divergir do repositorio, reconfira com as fontes:

```bash
# Catalogo canonico de agentes (tabela legivel)
python src/shared/tools/agent_registry.py

# JSON completo
python src/shared/tools/agent_registry.py --json

# Um agente especifico
python src/shared/tools/agent_registry.py --agent ava-qa-exploratory

# Ordem da esteira
ava-pipeline.bat list --phases

# Diagnostico de ambiente do projeto
ava-pipeline.bat doctor -p Meu-ERP
```
