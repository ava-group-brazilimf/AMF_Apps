# Data Model / Change Manifest: Bridge FastQA AST Simplification

**Feature**: 023-bridge-fastqa-ast-simplification
**Phase**: 1 — Exact change manifest per file

---

## A. `src/modules/ava-fabric-agents/asis-diagnostic/agents/bridge-fastqa-asis.md`

**Change type**: Full file replacement (v3.3.0 → v4.0.0)

The file is large (~1400 lines). The following subsections define every section that changes and how. Sections not listed here remain unchanged.

---

### A1 — Frontmatter

**Replace** the entire frontmatter block:

```diff
- version: "3.3.0"
- date: "2026-06-23"
- description: |
-   Bridge Agent entre o pipeline AS-IS e o ecossistema FastQA.
-   Gera um documento PBI local (PBI-{N}.md) a partir dos artefatos AS-IS já produzidos,
-   permitindo alimentar o pipeline FastQA em modo offline (sem Azure DevOps / sem MCP).
-   Elemento 1: PBI Generator — converte functional-requirements + business-rules em
-   documento PBI compatível com @fastqa:load_pbi (Modo B — Documentação Local).
-   Elemento 2: FastQA Pipeline — orquestra sequencialmente load_pbi → identify_gaps →
-   estimate_effort → analyze_requirements → map_behaviors, produzindo artefatos de QA.
-   Elemento 3: Test Design & Plan — executa ac_scope_analysis → test_case_with_fastqa
-   (Step by Step) → validate_scenarios → azdo_create_test_plan (local), gerando
-   casos de teste validados e um Test Plan estruturado como artefato local.
+ version: "4.0.0"
+ date: "2026-07-19"
+ description: |
+   Bridge Agent entre o pipeline AS-IS e o ecossistema FastQA.
+   Gera um documento PBI local (PBI-{N}.md) a partir dos artefatos AST brutos
+   (01_business_rules.json, 02_form_business_rules.json, 03_database_rules.json),
+   orquestra um pipeline FastQA enxuto (load_pbi → identify_gaps →
+   analyze_requirements → map_behaviors → test_case_with_fastqa) e produz
+   o Test Plan local (5 seções) derivado diretamente dos artefatos AST.
+   Ativa com: "gerar PBI para FastQA", "bridge FastQA", "criar PBI local",
+   "generate FastQA PBI", "bridge to FastQA", "create local PBI".
```

---

### A2 — Core Responsibilities

**Replace** the three bullet points under "Elemento 1 — PBI Generator":

```diff
- Ler artefatos obrigatórios (functional-requirements, business-rules) do AS-IS
- Enriquecer com artefatos opcionais (screen-rules, screen-navigation, value-chain, bounded-context-map)
+ Ler os três artefatos AST obrigatórios: 01_business_rules.json, 02_form_business_rules.json,
+   03_database_rules.json — buscados primeiro em compressed/, depois em extraction/ (hard stop se ausentes)
+ Não utilizar artefatos de documentação (functional-requirements.md, business-rules.md) nem opcionais
+   (screen-rules.md, screen-navigation-map.md, value-chain.md, bounded-context-map.md)
```

**Replace** the bullet points under "Elemento 2 — FastQA Pipeline Orchestration":

```diff
- Executar @fastqa:estimate_effort para estimar esforço e planejar massa de dados
+ (removido — @fastqa:estimate_effort não é mais executado)
```

**Replace** the bullet points under "Elemento 3 — Test Design & Plan":

```diff
- Executar @fastqa:ac_scope_analysis para classificar criticidade dos Critérios de Aceite e definir escopo de testes
- Executar @fastqa:validate_scenarios para validar cobertura, qualidade e rastreabilidade dos casos gerados
- Executar @fastqa:azdo_create_test_plan em modo local para gerar artefato de Test Plan estruturado (sem Azure DevOps)
+ Executar @fastqa:test_case_with_fastqa em formato Step by Step (português, escopo total) para gerar casos de teste
+ Executar @fastqa:azdo_create_test_plan em modo local para gerar artefato de Test Plan com 5 seções (sem Azure DevOps)
```

---

### A3 — Input Contract

**Replace** entire Input Contract section:

```diff
## Input Contract

Paths relativos a `projects/{project_name}/outputs/asis/`:

### Obrigatórios (BLOCKING — sem eles o agente NÃO executa)

- ### Obrigatórios (BLOCKING — sem eles o agente NÃO executa)
-
- | Artefato | Path | Uso |
- |----------|------|-----|
- | Functional Requirements | `docs/functional-requirements.md` | Fonte primária de FRs → User Stories e módulos |
- | Business Rules | `docs/business-rules.md` | Fonte primária de BRs → Critérios de Aceite |
-
- ### Opcionais (enriquecimento — ausência NÃO bloqueia)
-
- | Artefato | Path | Uso |
- |----------|------|-----|
- | Screen Rules | `docs/screen-rules.md` | Regras de tela → complementa Critérios de Aceite |
- | Screen Navigation Map | `docs/screen-navigation-map.md` | Fluxo de navegação → módulos e dependências |
- | Value Chain | `docs/value-chain.md` | Cadeia de valor → descrição de alto nível |
- | Bounded Context Map | `bounded-context-map.md` | Contextos delimitados → módulos a migrar |
+ ### Artefatos AST (BLOCKING — hard stop se ausentes em ambos os caminhos)
+
+ | Artefato | Conteúdo | Uso no PBI |
+ |----------|----------|-----------|
+ | `01_business_rules.json` | Regras de negócio: cálculos, validações, lógica no código | Critérios de Aceite (BR-NNN) + §2 Unit Test Scope |
+ | `02_form_business_rules.json` | Regras de tela/forms: campos, event_handlers, propriedades | Módulos (forms[].form_name) + §2 Validators |
+ | `03_database_rules.json` | Operações de banco: insert/update/delete por tabela | Critérios de Aceite (DBR-NNN) + §3 Integration Test Scope |
+
+ **Resolução de caminhos (ordem obrigatória):**
+ 1. `projects/{project_name}/outputs/asis/delphi-ast-raw/compressed/{arquivo}.json`
+ 2. `projects/{project_name}/outputs/asis/delphi-ast-raw/extraction/{arquivo}.json`
+ 3. Se ausente em ambos → **HARD STOP** — emitir erro bloqueante e encerrar sem gerar nenhum output
+
+ > ⚠️ Os artefatos de documentação derivados (`functional-requirements.md`, `business-rules.md`,
+ > `screen-rules.md`, `screen-navigation-map.md`, `value-chain.md`, `bounded-context-map.md`)
+ > **NÃO são mais utilizados por este agente**. Não ler, não referenciar.
```

---

### A4 — Output Contract

**Remove** three rows from the "Elemento 2 — FastQA Pipeline" output table:

```diff
- | Effort Estimation | `fastqa/manual_test/estimate_effort/PBI-{N}_planning.md` | `@fastqa:estimate_effort` | ✅ |
```

**Remove** three rows from "Elemento 3 — Test Design & Plan" output table:

```diff
- | AC Scope Analysis | `fastqa/manual_test/requirements_analysis/PBI-{N}_ac_scope.md` | `@fastqa:ac_scope_analysis` | ✅ |
- | Validation Report | `fastqa/manual_test/test_cases/PBI-{N}_validation_report.md` | `@fastqa:validate_scenarios` | ✅ |
```

---

### A5 — Dependency Gate (PROCEDURE validate_inputs)

**Replace** entire `validate_inputs` procedure:

```diff
- PROCEDURE validate_inputs(project_name):
-   base = "projects/{project_name}/outputs/asis/"
-   fr_path = base + "docs/functional-requirements.md"
-   br_path = base + "docs/business-rules.md"
-   missing = []
-   IF NOT file_exists(fr_path) OR file_size(fr_path) == 0:
-     missing.append("docs/functional-requirements.md")
-   IF NOT file_exists(br_path) OR file_size(br_path) == 0:
-     missing.append("docs/business-rules.md")
-   IF missing is NOT empty:
-     Emitir: ⛔ BLOCKED ...
-     PARAR.
-   RETURN OK
+ PROCEDURE validate_ast_inputs(project_name):
+   compressed = "projects/{project_name}/outputs/asis/delphi-ast-raw/compressed/"
+   extraction  = "projects/{project_name}/outputs/asis/delphi-ast-raw/extraction/"
+   ast_files   = ["01_business_rules.json", "02_form_business_rules.json", "03_database_rules.json"]
+   resolved    = {}
+   missing     = []
+
+   FOR each f in ast_files:
+     IF file_exists(compressed + f) AND file_size(compressed + f) > 0:
+       resolved[f] = compressed + f   # prefere compressed/ (token-otimizado)
+     ELSE IF file_exists(extraction + f) AND file_size(extraction + f) > 0:
+       resolved[f] = extraction + f   # fallback para extraction/
+     ELSE:
+       missing.append(f)
+
+   IF missing is NOT empty:
+     Emitir:
+     ┌──────────────────────────────────────────────────────────────────────────┐
+     │ ⛔ HARD STOP — ava-asis-bridge-fastqa v4.0.0                             │
+     │                                                                          │
+     │  Artefatos AST obrigatórios não encontrados em nenhum dos caminhos:      │
+     │  {missing}                                                               │
+     │                                                                          │
+     │  Caminhos verificados:                                                   │
+     │  1. {compressed}                                                         │
+     │  2. {extraction}                                                         │
+     │                                                                          │
+     │  Agente upstream responsável: ava-asis-solution-delphi (Step 0)          │
+     │  Comando para executar: @ava-asis-solution-delphi | SA                   │
+     │                                                                          │
+     │  Nenhum output será gerado até que os artefatos AST estejam disponíveis. │
+     └──────────────────────────────────────────────────────────────────────────┘
+     PARAR. NÃO gerar nenhum output.
+
+   RETURN resolved   # dict { filename: resolved_path }
```

---

### A6 — Step 1 (Validate Inputs)

**Replace** step 1.2:

```diff
- 2. Executar `validate_inputs(project_name)` — se BLOCKED → parar
+ 2. Executar `validate_ast_inputs(project_name)` — se HARD STOP → parar
+    Armazenar dict `resolved_paths` para uso nos steps seguintes
```

---

### A7 — Step 2 (Read Mandatory Artifacts) — COMPLETE REPLACEMENT

```diff
- ### Step 2 — Read Mandatory Artifacts
-
- 1. Ler `projects/{project_name}/outputs/asis/docs/functional-requirements.md` → extrair todos os `FR-NNN` com módulo, descrição e prioridade
- 2. Ler `projects/{project_name}/outputs/asis/docs/business-rules.md` → extrair todos os `BR-NNN` com domínio/módulo, regra e prioridade
+ ### Step 2 — Read AST Artifacts
+
+ Para cada arquivo em `resolved_paths` (do Step 1):
+
+ 1. Ler `resolved_paths["01_business_rules.json"]`:
+    - Extrair `payload.rules.schema[]` (array de nomes de campo)
+    - Extrair `payload.rules.rows[]` — cada row é um array posicional indexado por schema
+    - Mapear: `id` → BR-NNN, `unit` → módulo, `target` → campo afetado, `expression` → cálculo/validação
+    - Armazenar lista `business_rules[]`
+
+ 2. Ler `resolved_paths["02_form_business_rules.json"]`:
+    - Extrair `payload.forms.schema[]` e `payload.forms.rows[]`
+    - Mapear: `form_name` → nome do formulário, `fields[]` → lista de campos com `event_handlers`
+    - Filtrar fields onde `event_handlers` não está vazio → `form_event_handlers[]`
+    - Armazenar lista `forms[]` + `form_event_handlers[]`
+
+ 3. Ler `resolved_paths["03_database_rules.json"]`:
+    - Extrair `payload.rules.schema[]` e `payload.rules.rows[]`
+    - Mapear: `id` → DBR-NNN, `operation` → insert/update/delete, `tables[]` → tabelas afetadas
+    - Armazenar lista `db_rules[]`
```

---

### A8 — Step 3 (Read Optional Artifacts) — DELETED ENTIRELY

Remove entire "Step 3 — Read Optional Artifacts (enriquecimento)" section.

---

### A9 — Step 5 (Compose PBI Document) — UPDATE CONTENT DERIVATION

**Replace** items 3 and 4 in "Step 5 — Compose PBI Document":

```diff
- 3. **Descrição Detalhada:**
-    - Visão de alto nível do sistema (de `value-chain.md` se disponível)
-    - Módulos identificados (de `functional-requirements.md` — módulos dos FRs)
-    - Se `bounded-context-map.md` disponível → usar BCs como módulos
+ 3. **Descrição Detalhada:**
+    - Módulos identificados a partir dos form_names de `02_form_business_rules.json`
+    - Tabela de módulos: cada `form_name` único → uma linha com nome e tipo (TForm)
+    - Contagem de regras de negócio: N business_rules, M db_rules, P forms

- 4. **Critérios de Aceite:**
-    - Para CADA `FR-NNN` com prioridade HIGH ou que tenha `BR-NNN` associado → gerar cenário BDD
-    - Formato: `Dado/Quando/Então` com rastreabilidade `(Fonte: FR-NNN, BR-NNN)`
-    - Se `screen-rules.md` disponível → enriquecer cenários com validações de tela
-    - Agrupar cenários por módulo/funcionalidade
-    - Mínimo: 1 cenário por FR de alta prioridade
-    - Máximo: 30 cenários no total (se houver mais FRs, consolidar por módulo)
+ 4. **Critérios de Aceite:**
+    Três fontes de cenários:
+    a) Para CADA entrada em `business_rules[]` (01_business_rules.json):
+       → Cenário `Dado/Quando/Então` derivado de `target` e `expression`
+       → Rastreabilidade: `(Fonte: BR-NNN)`
+    b) Para CADA par `table × operation` único em `db_rules[]` (03_database_rules.json):
+       → Cenário descrevendo a mudança de estado esperada no banco
+       → Rastreabilidade: `(Fonte: DBR-NNN)`
+    c) Para CADA entrada em `form_event_handlers[]` (02_form_business_rules.json):
+       → Cenário descrevendo a interação de campo com event handler
+       → Rastreabilidade: `(Fonte: form: {form_name})`
+    Máximo 30 cenários total; se exceder → consolidar por módulo/form_name
+    Não usar FRs, BRs documentais ou regras de tela como fonte

- 5. **Dependências:**
-    - De `bounded-context-map.md` → dependências entre BCs
-    - De `screen-navigation-map.md` → fluxos que cruzam módulos
-    - De `business-rules.md` → pré-condições que implicam dependência
- 6. **Notas Técnicas:**
-    - `repository_path` e `legacy_technology` do config
-    - Tabela de BRs consolidadas (top 20 por relevância)
+ 5. **Dependências:**
+    - Derivar das tabelas em `db_rules[]` que aparecem em múltiplos módulos
+    - Formulários em `forms[]` que referenciam o mesmo prefixo de `unit` nos business_rules[]
+ 6. **Notas Técnicas:**
+    - `repository_path` e `legacy_technology` do config
+    - Contagens: {len(business_rules)} regras de negócio (BR), {len(db_rules)} regras de banco (DBR),
+      {len(forms)} formulários ({total_fields} campos), {len(form_event_handlers)} event handlers
```

---

### A10 — PBI Template — Acceptance Criteria section

**Replace** the template block `## ✅ Critérios de Aceite`:

```diff
- {Para cada regra de negócio (BR-NNN) e requisito funcional (FR-NNN) relevante,
- gerar um cenário no formato Dado/Quando/Então (BDD). Agrupar por módulo/funcionalidade.
- Cada cenário DEVE ter rastreabilidade ao BR-NNN ou FR-NNN de origem.}
-
- ### Cenário N: {título descritivo} (Fonte: {BR-NNN / FR-NNN})
-
- **Dado** que {pré-condição extraída do artefato},
- **Quando** {ação do usuário derivada do FR/BR},
- **Então** {resultado esperado com validação objetiva}.
+ {Cenários gerados a partir dos artefatos AST. Três fontes possíveis:}
+
+ ### Cenário N: {título descritivo} (Fonte: BR-NNN)
+
+ **Dado** que o usuário está no módulo {unit},
+ **Quando** ocorre {target} com os valores necessários,
+ **Então** o sistema aplica {expression} e o resultado está correto.
+
+ ### Cenário N: {título descritivo} (Fonte: DBR-NNN)
+
+ **Dado** que os pré-requisitos para a operação {operation} em {tables[0]} estão satisfeitos,
+ **Quando** a operação é executada,
+ **Então** a tabela {tables[0]} reflete o estado esperado.
+
+ ### Cenário N: {título descritivo} (Fonte: form: {form_name})
+
+ **Dado** que o usuário está no formulário {form_name},
+ **Quando** o campo {field_name} dispara o evento {event_handler},
+ **Então** o comportamento esperado é executado corretamente.
```

---

### A11 — Element 2 header description

**Replace** the sequential pipeline description:

```diff
- > **Sequência obrigatória (pipeline serial — cada step depende do anterior):**
- > ```
- > load_pbi → identify_gaps → estimate_effort → analyze_requirements → map_behaviors
- > ```
+ > **Sequência obrigatória (pipeline serial — cada step depende do anterior):**
+ > ```
+ > load_pbi → identify_gaps → analyze_requirements → map_behaviors
+ > ```
```

---

### A12 — Step 10 (estimate_effort) — DELETED ENTIRELY

Remove entire "Step 10 — Estimate Effort (`@fastqa:estimate_effort`)" section including:
- Dispatch block
- Instruções ao agente
- Validação pós-execução (PROCEDURE validate_estimate_effort)

---

### A13 — Renumber steps 11→10 and 12→11

**Step 11 → Step 10 (analyze_requirements)**:
- Rename heading `### Step 11 — Analyze Requirements` → `### Step 10 — Analyze Requirements`
- In the Dispatch block, remove the `testPlanning` input (no longer available)
- In "Passagem de contexto", remove the Step 10 reference
- In `validate_analyze_requirements`, update `Step 12` back-reference to `Step 11`

**Step 12 → Step 11 (map_behaviors)**:
- Rename heading `### Step 12 — Map Behaviors` → `### Step 11 — Map Behaviors`
- In `validate_map_behaviors`, update `Step 12` references throughout

---

### A14 — Step 13 → Step 12 (Element 2 Checkpoint)

- Rename heading `### Step 13 — Element 2 Checkpoint` → `### Step 12 — Element 2 Checkpoint`
- Update the PROCEDURE's step number references: "Step 11 e Step 12" → "Step 10 e Step 11"

---

### A15 — Element 3 header description

**Replace** the sequential pipeline description:

```diff
- > **Sequência obrigatória (pipeline serial):**
- > ```
- > ac_scope_analysis → test_case_with_fastqa → validate_scenarios → azdo_create_test_plan (local)
- > ```
+ > **Sequência obrigatória (pipeline serial):**
+ > ```
+ > test_case_with_fastqa → azdo_create_test_plan (local)
+ > ```
```

---

### A16 — Step 14 (ac_scope_analysis) — DELETED ENTIRELY

Remove entire "Step 14 — AC Scope Analysis (`@fastqa:ac_scope_analysis`)" section.

---

### A17 — Step 15 → Step 13 (test_case_with_fastqa)

- Rename heading `### Step 15 — Generate Test Cases` → `### Step 13 — Generate Test Cases`
- Remove `behaviorsFile` reference to `ac_scope.md` in dispatch (keep `behaviors_path`)
- Remove the `PBI-{N}_ac_scope.md` lookup line from Instruções ao agente
- Update `validate_test_cases` to reference "Step 14" → "Step 14" (now Step 14 is test plan)

---

### A18 — Step 16 (validate_scenarios) — DELETED ENTIRELY

Remove entire "Step 16 — Validate Scenarios (`@fastqa:validate_scenarios`)" section.

---

### A19 — Step 17 → Step 14 (Test Plan) — TEMPLATE REPLACEMENT

- Rename heading `### Step 17 — Create Test Plan` → `### Step 14 — Create Test Plan`
- Update description comment from "v3.0.0" to "v4.0.0"

**Replace "Geração de Conteúdo por Seção"** table:

```diff
- 1. Ler `bounded-context-map.md` + `business-rules.md` → §2 Unit Test Scope (Domain + Validators)
- 2. Ler `functional-requirements.md` → §2 Application Layer + §3 API Integration Tests
- 3. Ler `db/schema-inventory.md` → §3 Repository Tests + §8 Seed Data
- 4. Ler `value-chain.md` + `screen-navigation-map.md` + `ac_scope.md` → §5 E2E Tests
- 5. Ler `security-findings.json` (se disponível) → §3 Security Integration Tests
- 6. Ler `pattern-classifications.json` + `bounded-context-map.md` → §4 Architecture Tests
- 7. Ler `metrics.json` → §7 Load Test Plan (volumetria) + §8 Test Data (scaling)
+ 1. Ler `resolved_paths["01_business_rules.json"]` → §2 Unit Test Scope (Domain: cálculos BR-NNN; Validators: validações)
+ 2. Ler `resolved_paths["02_form_business_rules.json"]` → §2 Unit Test Scope (Validators: event handlers por form_name)
+ 3. Ler `resolved_paths["03_database_rules.json"]` → §3 Integration Test Scope (Repository: operations por tabela)
+ 4. Todas as três fontes → §4 Test Coverage Map (tabela de rastreabilidade BR-NNN / DBR-NNN)
+ 5. Fixo → §1 Test Strategy e §5 Test Quality Gates (sem dependência de artefatos)
```

**Replace entire test-plan.md template** (from ````markdown` to closing ` ```` `) with new 5-section template:

```markdown
# Test Plan — {project_name} (AS-IS Migration)

**Project**: {project_name}
**Phase**: F1 — AS-IS Diagnostic (Bridge FastQA)
**PBI Origem**: PBI-{N}
**Legacy Technology**: {legacy_technology}
**Generated**: {data_atual_ISO}

---

## 1. Test Strategy — Pyramid

| Layer | % | Tool | Focus |
|---|---|---|---|
| Unit | 60% | {A definir na fase TO-BE} | Domain logic, business rules (BR-NNN), form validators — paridade com {legacy_technology} |
| Integration | 25% | {A definir na fase TO-BE} | Repository implementations, DB mappings (DBR-NNN), cross-module flows |
| E2E | 15% | {A definir na fase TO-BE} | Critical user journeys via UI — derivados após TO-BE |

**Total coverage gate**: ≥ 80% line coverage on Domain + Application layers.

---

## 2. Unit Test Scope

### Domain Layer — Business Rules

{Para cada entrada em 01_business_rules.json:}

| Rule ID | Unit | Method | Target | Key Test |
|---------|------|--------|--------|----------|
| {BR-NNN} | {unit} | {method} | {target} | {expression} → resultado correto; valor inválido → erro |

### Validators — Form Event Handlers

{Para cada field com event_handlers não vazio em 02_form_business_rules.json:}

| Form | Field | Event | Key Test |
|------|-------|-------|----------|
| {form_name} | {field_name} | {event_handler} | Campo dispara handler → comportamento esperado |

---

## 3. Integration Test Scope — Repository Tests

{Para cada par tabela × operação em 03_database_rules.json:}

| Rule ID | Operation | Table | Key Test |
|---------|-----------|-------|----------|
| {DBR-NNN} | {operation} | {tables[0]} | {operation} em {tables[0]} persiste corretamente; rollback em erro |

---

## 4. Test Coverage Map (Traceability)

| Rule ID | Type | Module | Test Category | Test Description |
|---------|------|--------|---------------|-----------------|
| {BR-NNN} | business_rule | {unit} | Unit — Domain | {target} = {expression} |
| {DBR-NNN} | db_operation | {tables[0]} | Integration — Repository | {operation} on {tables[0]} |
| form:{form_name} | event_handler | {form_name} | Unit — Validator | {event} triggered on {field} |

---

## 5. Test Quality Gates (CI Pipeline)

| Gate | Threshold | Failure Action |
|------|-----------|----------------|
| Unit test coverage (Domain) | ≥ 80% | Build fails |
| Integration test failures | 0 | Build fails |
| BR coverage (BRs traced to tests / Total BRs) | 100% | Release blocked |
| DBR coverage (DBRs traced to tests / Total DBRs) | 100% | Release blocked |

---

*Generated by ava-asis-bridge-fastqa v4.0.0 + FastQA Pipeline (local artifact — no Azure DevOps)*
```

**Replace "Regras de Preenchimento do Template"** table:

```diff
- | Header (project, phase, PBI, legacy tech) | `project-config.yaml` (`project_name`, `legacy_technology`) |
- | §1 Test Strategy — Pyramid | Fixo (proporções 60/25/15). Ferramentas marcadas "A definir na fase TO-BE". |
- | §2 Unit Test Scope — Domain | `bounded-context-map.md` × `business-rules.md` (BR-NNN → cenários de teste) |
- | §2 Unit Test Scope — Application | `functional-requirements.md` (FR-NNN → Services/Handlers) |
- | §2 Unit Test Scope — Validators | `screen-rules.md` + `business-rules.md` (validações de campo) |
- | §3 Integration — Repositories | `db/schema-inventory.md` + `bounded-context-map.md` |
- | §3 Integration — API | `functional-requirements.md` (FR de alta prioridade → endpoints REST) |
- | §3 Integration — Security | `security/security-findings.json` + BRs de segurança |
- | §4 Architecture Tests | `bounded-context-map.md` + `pattern-classifications.json` |
- | §5 E2E Tests | `value-chain.md` + `screen-navigation-map.md` + `ac_scope.md` |
- | §6 Smoke Test Suite | Fixo (health, auth, primary query, DB, cache, audit) |
- | §7 Load Test Plan | FRs de alta volumetria + `metrics.json` |
- | §8 Test Data Management | `business-rules.md` + `db/schema-inventory.md` + `metrics.json` |
- | §9 Test Quality Gates | Fixo (thresholds CI/CD: coverage ≥80%, 0 violations, 0 failures) |
+ | Header (project, phase, PBI, legacy tech) | `project-config.yaml` (`project_name`, `legacy_technology`) |
+ | §1 Test Strategy — Pyramid | Fixo (proporções 60/25/15). Ferramentas marcadas "A definir na fase TO-BE". |
+ | §2 Unit Test Scope — Domain | `01_business_rules.json` (business_rules[] → tabela BR-NNN × unit × method × target × expression) |
+ | §2 Unit Test Scope — Validators | `02_form_business_rules.json` (form_event_handlers[] → tabela form × field × event) |
+ | §3 Integration — Repositories | `03_database_rules.json` (db_rules[] → tabela DBR-NNN × operation × tables[0]) |
+ | §4 Test Coverage Map | Todas as três fontes → tabela unificada de rastreabilidade por Rule ID |
+ | §5 Test Quality Gates | Fixo (BR coverage 100%, DBR coverage 100%, unit ≥80%, integration 0 falhas) |
```

**Update validate_test_plan** — required sections check:

```diff
- required_sections = ["## 1. Test Strategy", "## 2. Unit Test Scope", "## 3. Integration Test Scope",
-                      "## 4. Architecture Tests", "## 5. E2E Tests", "## 6. Smoke Test Suite",
-                      "## 7. Load Test Plan", "## 8. Test Data Management", "## 9. Test Quality Gates"]
+ required_sections = ["## 1. Test Strategy", "## 2. Unit Test Scope",
+                      "## 3. Integration Test Scope",
+                      "## 4. Test Coverage Map", "## 5. Test Quality Gates"]
```

---

### A20 — Step 17b → Step 15 (Publish QA Artifacts)

- Rename heading `### Step 17b` → `### Step 15`
- Remove the `gap_analysis` copy block — this artifact is still produced by identify_gaps (Step 9) so copy is kept
- No other content changes in this step

---

### A21 — Step 18 → Step 16 (Completion Signal)

- Rename heading `### Step 18 — Emit Completion Signal` → `### Step 16 — Emit Completion Signal`

**Remove** three lines from the completion signal template:

```diff
-   Effort Estimate:  fastqa/manual_test/estimate_effort/PBI-{N}_planning.md  [{status_step10}]
...
-   AC Scope:         fastqa/manual_test/requirements_analysis/PBI-{N}_ac_scope.md [{status_step14}]
...
-   Validation:       fastqa/manual_test/test_cases/PBI-{N}_validation_report.md [{status_step16}]
```

**Update** pipeline trace in completion signal:

```diff
- Pipeline: load_pbi → identify_gaps → estimate_effort → analyze_requirements →
-           map_behaviors → ac_scope_analysis → test_case_with_fastqa →
-           validate_scenarios → create_test_plan (local)
+ Pipeline: load_pbi → identify_gaps → analyze_requirements → map_behaviors →
+           test_case_with_fastqa → create_test_plan (local)
```

---

### A22 — Observability section — version update

```diff
- Bash: python src/shared/tools/pipeline_observer.py -p {project_name} track \
-   --agent ava-asis-bridge-fastqa --phase F1 --version 3.3.0 \
+ Bash: python src/shared/tools/pipeline_observer.py -p {project_name} track \
+   --agent ava-asis-bridge-fastqa --phase F1 --version 4.0.0 \
```

---

### A23 — Guardrails — update input references

**Replace** guardrails that reference removed inputs/steps:

```diff
- ⛔ **NUNCA** inventar FRs/BRs. Todo cenário DEVE ter rastreabilidade a um `FR-NNN` ou `BR-NNN` real do artefato-fonte.
+ ⛔ **NUNCA** inventar regras de negócio. Todo cenário DEVE ter rastreabilidade a um `BR-NNN` (01_business_rules.json), `DBR-NNN` (03_database_rules.json) ou `form:{form_name}` (02_form_business_rules.json) real.

- ⛔ **NUNCA** gravar arquivos em `projects/{project_name}/outputs/` **exceto** no diretório `outputs/asis/qa/`...
+ ⛔ **NUNCA** gravar arquivos em `projects/{project_name}/outputs/` **exceto** no diretório `outputs/asis/qa/`... (unchanged)

- ⛔ **NUNCA** emitir `↳ ✅ [ava-asis-bridge-fastqa]` sem que TODOS os 3 Elementos tenham sido executados (Steps 1-7 + Steps 8-13 + Steps 14-18). Um `test-plan.md` genérico de < 5KB sem as 9 seções do template...
+ ⛔ **NUNCA** emitir `↳ ✅ [ava-asis-bridge-fastqa]` sem que TODOS os 3 Elementos tenham sido executados (Steps 1-7 + Steps 8-12 + Steps 13-16). Um `test-plan.md` genérico de < 3KB sem as 5 seções do template é **evidência de execução incompleta**...

- ⛔ **NUNCA** gerar o artefato `qa/test-plan.md` como ... Formatos resumidos são rejeitados pelo `Post-Completion Artifact Verification` do orquestrador (size_threshold: 5000 bytes).
+ ⛔ **NUNCA** gerar o artefato `qa/test-plan.md` como ... Formatos resumidos são rejeitados pelo `Post-Completion Artifact Verification` do orquestrador (size_threshold: 3000 bytes).
```

**Remove** guardrails specific to eliminated steps (estimate_effort, ac_scope_analysis, validate_scenarios in Elemento 2 and 3 sections).

---

### A24 — FastQA Integration Notes — pipeline diagrams

**Replace** Element 2 pipeline diagram:

```diff
- Step 8:  @fastqa:load_pbi ──────────────► pbi.current
- Step 9:  @fastqa:identify_gaps ─────────► gap_analysis/PBI-{N}_gaps
- Step 10: @fastqa:estimate_effort ───────► estimate_effort/PBI-{N}_plan
- Step 11: @fastqa:analyze_requirements ──► requirements_analysis/
-             │                              PBI-{N}_requirements
-             │ (BLOCKING gate)
- Step 12: @fastqa:map_behaviors ─────────► behavior_analysis/
-                                             PBI-{N}_behaviors
+ Step 8:  @fastqa:load_pbi ──────────────► pbi.current
+ Step 9:  @fastqa:identify_gaps ─────────► gap_analysis/PBI-{N}_gaps
+             │
+ Step 10: @fastqa:analyze_requirements ──► requirements_analysis/
+             │                              PBI-{N}_requirements
+             │ (BLOCKING gate)
+ Step 11: @fastqa:map_behaviors ─────────► behavior_analysis/
+                                             PBI-{N}_behaviors
```

**Replace** Element 3 pipeline diagram:

```diff
- Step 14: @fastqa:ac_scope_analysis ─────► requirements_analysis/
-             │                              PBI-{N}_ac_scope
- Step 15: @fastqa:test_case_with_fastqa ─► test_cases/{func}/
-             │                              PBI-{N}.md (Step by Step)
- Step 16: @fastqa:validate_scenarios ────► test_cases/
-             │                              PBI-{N}_validation_report
- Step 17: Test Plan (local) ─────────────► test_cases/
-                                             PBI-{N}_test_plan.md
+ Step 13: @fastqa:test_case_with_fastqa ─► test_cases/{func}/
+             │                              PBI-{N}.md (Step by Step)
+ Step 14: Test Plan (local) ─────────────► test_cases/
+                                             PBI-{N}_test_plan.md
```

**Replace** Fluxo de Dados table — remove rows for deleted steps and renumber:

```diff
Remove rows:
- | 10 | `estimate_effort` | `pbi.current` | `estimate_effort/PBI-{N}_planning.md` | WARNING |
- | 14 | `ac_scope_analysis` | `PBI-{N}.md` + Step 12 | `requirements_analysis/PBI-{N}_ac_scope.md` | WARNING |
- | 16 | `validate_scenarios` | Step 15 + Step 12 | `test_cases/PBI-{N}_validation_report.md` | WARNING |

Update renumbered rows:
- | 11 | `analyze_requirements` → | 10 |
- | 12 | `map_behaviors` → | 11 |
- | 13 | Element 2 Checkpoint → | 12 |
- | 15 | `test_case_with_fastqa` → | 13 |
- | 17 | Test Plan (local) → | 14 |
```

---

## B. `src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md`

### B1a — artifact_contracts.ava-asis-bridge-fastqa.external_mandatory

Remove three lines from the `external_mandatory.files` list:

```diff
     external_mandatory:
       base: "fastqa/manual_test/"
       files:
         - "US/PBI-*.md"                                        # min_count: 1
         - "gap_analysis/PBI-*_gaps.md"                         # min_count: 1 — Step 9
-        - "estimate_effort/PBI-*_planning.md"                  # min_count: 1 — Step 10
         - "requirements_analysis/PBI-*_requirements.md"        # min_count: 1 — Step 11
         - "behavior_analysis/PBI-*_behaviors.md"               # min_count: 1 — Step 12
-        - "requirements_analysis/PBI-*_ac_scope.md"            # min_count: 1 — Step 14
         - "test_cases/**/PBI-*.md"                             # min_count: 1 — Step 15
-        - "test_cases/PBI-*_validation_report.md"              # min_count: 1 — Step 16
         - "test_cases/PBI-*_test_plan.md"                      # min_count: 1 — Step 17
```

### B1b — dispatch_bridge_fastqa() Step C — version and step count

```diff
-     "Execute o ava-asis-bridge-fastqa v3.1.0 completo (3 Elementos, 18 Steps)
+     "Execute o ava-asis-bridge-fastqa v4.0.0 completo (3 Elementos, 16 Steps)
```

### B1c — size_threshold comment and value

```diff
     size_threshold:
-      "qa/test-plan.md": 5000   # mínimo 5KB — rejeitar placeholders genéricos < 5KB que indicam execução incompleta
+      "qa/test-plan.md": 3000   # mínimo 3KB — rejeitar placeholders genéricos < 3KB (lean 5-section template); indicam execução incompleta
```

---

## C. `docs/asis-diagnostic-io-map.md`

### C1a — bridge-fastqa Inputs section

**Replace** the inputs block:

```diff
- **Inputs**: mandatory (blocking) `asis/docs/functional-requirements.md`, `asis/docs/business-rules.md` (documentation); optional `asis/docs/screen-rules.md` ⬜, `asis/docs/screen-navigation-map.md` ⬜, `asis/docs/value-chain.md` ⬜, `asis/bounded-context-map.md` ⬜; config `context/project-config.yaml`
+ **Inputs (v4.0.0)**: three AST JSON files (BLOCKING — hard stop if absent from both paths):
+   - `asis/delphi-ast-raw/compressed/01_business_rules.json` (primary) or `asis/delphi-ast-raw/extraction/01_business_rules.json` (fallback)
+   - `asis/delphi-ast-raw/compressed/02_form_business_rules.json` (primary) or `asis/delphi-ast-raw/extraction/02_form_business_rules.json` (fallback)
+   - `asis/delphi-ast-raw/compressed/03_database_rules.json` (primary) or `asis/delphi-ast-raw/extraction/03_database_rules.json` (fallback)
+   - `context/project-config.yaml` (`project_name`, `legacy_technology`)
+   > ⚠️ Deprecated inputs (no longer used): `functional-requirements.md`, `business-rules.md`, `screen-rules.md`, `screen-navigation-map.md`, `value-chain.md`, `bounded-context-map.md`
```

### C1b — bridge-fastqa Outputs section

**Remove** three eliminated artifacts from the outputs list:

```diff
-   - `fastqa/manual_test/estimate_effort/PBI-{N}_planning.md`
```

```diff
-   - `fastqa/manual_test/requirements_analysis/PBI-*_ac_scope.md`
```

```diff
-   - `fastqa/manual_test/test_cases/PBI-*_validation_report.md`
```

### C1c — §5 Cross-Agent Consumption table

**Replace** the bridge-fastqa row:

```diff
- | `ava-asis-bridge-fastqa` | documentation (2 mandatory + 4 optional) | blocking on the mandatory pair |
+ | `ava-asis-bridge-fastqa` | AST JSON artifacts (3 mandatory — `compressed/` primary, `extraction/` fallback; hard stop if absent from both) | hard-blocking on all three |
```
