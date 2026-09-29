# SpecKit — Guia de Desenvolvimento de Agentes IMFAI

> **Versão**: 1.0.0 | **Atualizado**: 2026-06-22  
> Baseado em spec-kit v0.11.1 — <https://github.com/github/spec-kit>

---

## O que é o SpecKit?

O SpecKit é um toolkit de **Spec-Driven Development (SDD)** — desenvolvimento dirigido por especificação. Dentro do IMFAI, ele governa o processo de **criar, modificar e evoluir agentes** da fábrica de migração.

A ideia central é: antes de tocar qualquer arquivo `.md` de agente, você especifica o que vai fazer, planeja como fazer e gera uma lista de tarefas rastreável. O código (neste caso, o corpo do agente em Português) é a última coisa a ser escrita — não a primeira.

```
Especificação (/speckit.specify)
        ↓
   Plano (/speckit.plan)
        ↓
   Tarefas (/speckit.tasks)
        ↓
Implementação (/speckit.implement)
```

---

## Quando usar o SpecKit

| Situação | Usar SpecKit? |
|---|---|
| Adicionar um novo agente a qualquer fase (F1–F8) | ✅ Sempre |
| Modificar comportamento ou contrato de saída de um agente existente | ✅ Sempre |
| Corrigir bug em instruções de agente (bump PATCH) | ✅ Recomendado |
| Criar nova fase/módulo inteiro | ✅ Sempre |
| Alterar apenas comentários ou formatação | ❌ Não necessário |

---

## Configuração

O SpecKit já está instalado e configurado neste repositório. Para usar no VS Code com GitHub Copilot:

1. Abra a pasta `imfai-ava-fabric-apps-agents/` como raiz do workspace
2. Inicie uma conversa com o Copilot no modo agente
3. Os comandos `/speckit.*` já estão disponíveis

Para verificar:
```powershell
$env:PATH = "C:\Users\<usuario>\.local\bin;$env:PATH"
specify version   # deve exibir 0.11.1
specify preset resolve spec-template  # deve exibir "(top layer from: project override)"
```

---

## Comandos disponíveis

| Comando | Propósito |
|---|---|
| `/speckit.specify` | Define um novo agente ou descreve uma mudança em um agente existente |
| `/speckit.plan` | Gera o plano de implementação com verificação das gates da constituição |
| `/speckit.tasks` | Gera a lista de tarefas no formato IMFAI de 7 categorias |
| `/speckit.implement` | Executa as tarefas geradas |
| `/speckit.clarify` | Faz perguntas estruturadas para eliminar ambiguidades antes do planejamento |
| `/speckit.analyze` | Verifica consistência entre spec, plano e tarefas |
| `/speckit.checklist` | Gera checklist de qualidade com base no contexto do spec e plano |
| `/speckit.constitution` | Exibe ou atualiza a constituição do projeto |

---

## Fluxo completo — exemplo prático

### Exemplo 1: Novo agente (agente de verificação GDPR no F1)

#### Passo 1 — Especificação

```
/speckit.specify Adicionar agente de verificação GDPR ao F1 que escaneia
o código-fonte legado em busca de padrões de dados pessoais (CPF, e-mail, IBAN)
e adiciona os achados ao risk register
```

O Copilot vai:
- Ler a constituição em `.specify/memory/constitution.md`
- Criar `specs/001-gdpr-pii-scanner/spec.md` usando o template IMFAI
- Criar `specs/001-gdpr-pii-scanner/checklists/requirements.md`

**O que verificar no `spec.md` gerado:**

```markdown
## 1. Agent Identity
| Agent ID    | ava-asis-gdpr-pii              |  ← segue ava-{fase}-{papel}
| Phase       | F1                             |
| Module      | asis-diagnostic                |  ← mapeado da constituição
| Change Type | new-agent                      |
| Skill       | ava-asis-gdpr-pii              |
| Dispatch    | user-facing via SKILL.md       |

## 2. Agent Frontmatter
name: "ava-asis-gdpr-pii"
description: |
  [em Português + frases de ativação]   ← Artigo V
allowed-tools: Read, Glob, Grep         ← F1 análise = somente leitura

## 3. Output Contract
outputs:
  pii_findings: "projects/{project_name}/outputs/asis/..."  ← minúsculo
```

#### Passo 2 — Plano

```
/speckit.plan
```

O Copilot executa o script `.specify/scripts/powershell/setup-plan.ps1` que copia o template de plano IMFAI para `specs/001-gdpr-pii-scanner/plan.md`, depois preenche todas as seções com conteúdo concreto.

**O que verificar no `plan.md` gerado:**

- `## Constitution Check` com todos os 11 artigos verificados (`[x]`)
- Artigo IX marcado como N/A para agentes LLM prompt
- `## 2. Phase Placement` mostrando a sequência real: `F1 -> ava-summary -> F2 -> ...`
- `## 5. module.yaml Impact` apontando para `src/modules/ava-fabric-agents/asis-diagnostic/module.yaml` (não o raiz)
- Todos os caminhos de saída em minúsculo: `projects/{project_name}/outputs/asis/`

#### Passo 3 — Tarefas

```
/speckit.tasks
```

**O que verificar no `tasks.md` gerado:**

```markdown
## Category 1 — Agent Frontmatter & Contract Definition
- [ ] **1.1** Criar src/modules/ava-fabric-agents/asis-diagnostic/agents/gdpr-pii-asis.md
- [ ] **1.2** Escrever frontmatter: name, version, description (PT), allowed-tools
- [ ] **1.3** Escrever ## Contrato de Saída com paths em {project_name} minúsculo
- [ ] **1.5** Criar .github/skills/ava-asis-gdpr-pii/SKILL.md

## Category 2 — Agent Behavior & Instructions
## Category 3 — Shared Schema Updates  [SKIP se sem mudanças de schema]
## Category 4 — Module Registration
## Category 5 — Quality Gate Checklists
## Category 6 — Acceptance Validation
## Category 7 — Documentation & Catalog Update
```

As tarefas usam numeração `N.N` (não T001), sem labels `[US1]`, e a Categoria 3 é pulada quando não há mudanças de schema.

---

### Exemplo 2: Modificar agente existente

Quando a mudança é num agente que já existe, o SpecKit adapta o fluxo automaticamente.

```
/speckit.specify Estender o agente ava-asis-inventory para contar também
interfaces e classes abstratas no código Delphi
```

**Diferenças que o Copilot aplica automaticamente:**

| Campo | Novo agente | Agente existente |
|---|---|---|
| `Change Type` | `new-agent` | `modify-existing` |
| `Agent ID` | Novo ID | ID existente (ex: `ava-asis-inventory`) |
| `Version` | `1.0.0` | `1.3.0 → 1.4.0` (bump MINOR) |
| Categoria 4 (module.yaml) | Incluída | **N/A** — entrada já existe |
| Tarefa 1.5 (SKILL.md) | Incluída | **N/A** — SKILL.md já existe |

O callout aparece automaticamente no spec:

```markdown
> **Change Type is `modify-existing`**:
> - Arquivo a modificar: src/modules/.../inventory-asis.md
> - Version bump: MINOR (1.3.0 → 1.4.0)
> - module.yaml entry already exists — Category 4 tasks are N/A
> - SKILL.md already exists — Category 1.5 is N/A
```

---

## Regras da Constituição (resumo)

O arquivo `.specify/memory/constitution.md` é lido automaticamente pelo Copilot em cada comando. Ele define 11 artigos:

| Artigo | Regra |
|---|---|
| I | Nenhum agente pode ter versões de tecnologia hardcoded |
| II | Frontmatter: apenas `name`, `version`, `description` (PT), `allowed-tools` |
| III | Sequência do pipeline: F1→F2→F3→F4→F5→F6→F7 com `ava-summary` entre cada fase |
| IV | Registro no `module.yaml` **de nível de módulo** (não o raiz) |
| V | Corpo do agente deve ser escrito em **Português Brasileiro** |
| VI | Cenários BDD obrigatórios: nominal, edge case, gate de qualidade |
| VII | F1 sempre inclui sub-pipeline de segurança |
| VIII | `trace_id` propagado sem modificação |
| IX | Clean Architecture (N/A para agentes LLM prompt) |
| X | Versionamento SemVer — MAJOR muda contrato, MINOR adiciona, PATCH corrige |
| XI | Separação SKILL.md / agent `.md` — user-facing ou interno |

### Campos corretos de frontmatter

```yaml
---
name: "ava-asis-gdpr-pii"          # ava-{fase}-{papel} | ^ava-[a-z0-9-]+$
version: "1.0.0"
description: |
  Descrição em Português do que o agente faz.
  Ativa com: "frase 1", "frase 2", "frase 3".
allowed-tools: Read, Glob, Grep    # Apenas ferramentas Claude Code válidas
---
```

**NÃO incluir no frontmatter**: `phase`, `module`, `inputs`, `outputs`, `dependencies`.

### Localização correta do Contrato de Saída

O contrato de saída fica no **corpo do agente** (não no frontmatter):

```markdown
## Contrato de Saída
```yaml
outputs:
  relatorio_pii: "projects/{project_name}/outputs/asis/gdpr-pii-findings.md"
  risk_entries:  "projects/{project_name}/outputs/asis/risk-register.json"
```
```

Use sempre `{project_name}` em **minúsculas**.

---

## Mapeamento de fases e módulos

| Fase | Módulo | Pasta |
|---|---|---|
| F1 — AS-IS Diagnostic | `asis-diagnostic` | `src/modules/ava-fabric-agents/asis-diagnostic/` |
| F2 — TO-BE Architecture | `tobe-architecture` | `src/modules/ava-fabric-agents/tobe-architecture/` |
| F3 — Prototype | `prototype` | `src/modules/ava-fabric-agents/prototype/` |
| F4 — Stack / Codegen | `tech-stack` | `src/modules/ava-fabric-agents/tech-stack/` |
| F5 — QA | `qa-agents` | `src/modules/ava-fabric-agents/qa-agents/` |
| F6 — DevOps | `devops-agents` | `src/modules/ava-fabric-agents/devops-agents/` |
| F7 — Deliverables | `deliverables` | `src/modules/ava-fabric-agents/deliverables/` |
| F8 — Summary | `summary` | `src/modules/ava-fabric-agents/summary/` |

### `allowed-tools` por fase

| Tipo de agente | Tools recomendadas |
|---|---|
| F1 — análise (somente leitura) | `Read, Glob, Grep, Bash` |
| F2 — design (escreve docs) | `Read, Write, Edit` |
| F3 — protótipo (escreve) | `Read, Write, Edit` |
| F4 — codegen (escreve código) | `Read, Write, Edit, Bash` |
| F5 — QA (escreve + executa) | `Read, Write, Edit, Bash, Glob` |
| F6/F7 — entrega/deploy | `Read, Write, Edit` |
| F8 — summary (build script) | `Read, Write, Edit, Bash` |

---

## Estrutura dos artefatos gerados

Cada execução do `/speckit.specify` cria uma pasta em `specs/NNN-nome-da-feature/`:

```
specs/
└── 001-gdpr-pii-scanner/
    ├── spec.md              ← Especificação do agente (IMFAI template)
    ├── plan.md              ← Plano de implementação (gerado por /speckit.plan)
    ├── tasks.md             ← Lista de tarefas 7 categorias (gerado por /speckit.tasks)
    ├── research.md          ← Decisões técnicas e pesquisa
    ├── data-model.md        ← Modelo de dados / entidades
    ├── quickstart.md        ← Cenários de validação rápida
    ├── contracts/
    │   └── agent-contract.md  ← Contrato formal do agente
    └── checklists/
        ├── requirements.md    ← Checklist de requisitos (gerado pelo /speckit.specify)
        └── pre-impl.md        ← Checklist pré-implementação (gerado pelo /speckit.checklist)
```

> **Nota**: A pasta `specs/` está no `.gitignore`. Os artefatos são de trabalho (work-in-progress) e não são versionados. Quando a implementação for concluída, o que fica no repositório são os próprios arquivos do agente (`*.md` em `src/modules/`), o `module.yaml` atualizado e o `CHANGELOG.md`.

---

## Padrão de corpo do agente

O corpo do agente (após o frontmatter) deve seguir este padrão em Português:

```markdown
# AVA — [Nome do Agente] Agent

## Papel & Persona
[Descrição em PT-BR do papel do agente na fábrica de migração]

## Habilidades
### [Habilidade 1]
- **[Sub-habilidade]**: [descrição]

## Pré-flight Check (OBRIGATÓRIO)
[Verificação de pré-condições antes de qualquer execução]

## Contrato de Saída
```yaml
outputs:
  artefato: "projects/{project_name}/outputs/{fase}/arquivo.md"
```

## [Instruções específicas do agente]
[Passos numerados e determinísticos em Português]

## Notas de Segurança
[Referência ao Artigo VII da constituição]

## Lógica de Gate de Qualidade
[Regras de scoring de risco e condições para human_gate_required: true]
```

---

## Padrão do SKILL.md

Para agentes user-facing, criar `.github/skills/ava-{fase}-{papel}/SKILL.md`:

```markdown
---
name: ava-{fase}-{papel}
description: >
  [Descrição curta em PT-BR + frases de ativação]
---

Determine o PROJECT_NAME antes de executar:
1. Leia `projects/_template/context/project-config.yaml` → campo `project_name`
2. Se não existir, pergunte ao usuário: "Qual é o nome do projeto? (ex: Meu-ERP)"
3. Use esse PROJECT_NAME para todos os caminhos: `projects/{PROJECT_NAME}/`

Antes de iniciar, leia:
`projects/{PROJECT_NAME}/context/agent-task-config.yaml`
`projects/{PROJECT_NAME}/context/shared-context.md`

Leia e siga as instruções do agente em:
`src/modules/ava-fabric-agents/{modulo}/agents/{arquivo}.md`
```

---

## Registro no module.yaml de módulo

Ao criar um novo agente, adicionar entrada no `module.yaml` **do módulo** (não o raiz):

```yaml
# src/modules/ava-fabric-agents/asis-diagnostic/module.yaml
agents:
  # ... entradas existentes ...
  - id: ava-asis-gdpr-pii           # [NOVO]
    file: agents/gdpr-pii-asis.md
    skill: ava-asis-gdpr-pii        # omitir se for agente interno
```

Fazer também o bump de versão do módulo (campo `version` no topo do arquivo):
- Novo agente user-facing → bump **MINOR** (ex: `1.6.0 → 1.7.0`)
- Novo agente interno → bump **MINOR**
- Bug fix em agente existente → bump **PATCH** (ex: `1.7.0 → 1.7.1`)

---

## Perguntas frequentes

**P: Os specs devem ser versionados com o código?**  
R: Não neste projeto — a pasta `specs/` está no `.gitignore`. O que fica no repositório são os artefatos finais (arquivos `.md` do agente, `module.yaml`, `CHANGELOG.md`).

**P: O corpo do agente pode estar em Inglês?**  
R: Não. O Artigo V da constituição exige Português Brasileiro para todo o corpo do agente. O spec (planejamento) pode estar em Inglês, mas o agente implementado deve estar em PT-BR.

**P: Posso usar `/speckit.specify` sem a flag `--integration copilot`?**  
R: O SpecKit já foi inicializado com Copilot. Basta usar os slash commands diretamente no chat do Copilot com o workspace `imfai-ava-fabric-apps-agents/` aberto.

**P: Como atualizar o SpecKit?**  
```powershell
$env:PATH = "C:\Users\<usuario>\.local\bin;$env:PATH"
specify self check    # verifica se há atualização disponível
specify self upgrade  # atualiza para a versão mais recente
```

**P: O que fazer se o spec gerado usa template genérico (seções como `## Requirements` e `FR-001`)?**  
R: Isso indica que o Copilot usou o template stock do SpecKit em vez do override IMFAI. Verifique se `.specify/templates/spec-template.md` tem o conteúdo correto (deve começar com `## 1. Agent Identity`). Se necessário, delete o `spec.md` gerado e rode `/speckit.specify` novamente.

**P: E se a fase do agente não estiver clara na descrição?**  
R: O Copilot usa o mapeamento de fases da constituição (seção "Project Reference") para inferir a fase correta. Se ainda assim ficar ambíguo, rode `/speckit.clarify` antes do `/speckit.plan` para resolver a ambiguidade.

---

## Arquivos de referência

| Arquivo | Propósito |
|---|---|
| `.specify/memory/constitution.md` | 11 artigos que governam todo o desenvolvimento de agentes |
| `.specify/templates/spec-template.md` | Template IMFAI de especificação (Agent Identity, Frontmatter, Output Contract) |
| `.specify/templates/plan-template.md` | Template IMFAI de plano (Constitution Check, Phase Placement, module.yaml diff) |
| `.specify/templates/tasks-template.md` | Template IMFAI de tarefas (7 categorias, validação via test-determinism) |
| `.specify/templates/checklist-template.md` | Template de checklist com itens de conformidade constitucional |
| `src/shared/data/reference-architecture.yaml` | Fonte canônica de tecnologias — jamais usar versões hardcoded |
| `projects/_template/context/project-config.yaml` | Template de configuração de projeto |
| `projects/test-determinism/` | Projeto de referência para validação de agentes na Categoria 6 |
