# Guia de Comandos — `ava-pipeline-runner-cli.py`

> **Escopo**: todos os comandos de execução da esteira AVA Fabric por **etapa**, por **grupo de fases** e
> por **agente avulso**, mais as tools determinísticas que rodam fora do fluxo de agentes.
>
> **Fonte**: gerado a partir das tabelas `PIPELINE` e `PHASE_GROUPS` de `ava-pipeline-runner-cli.py` e do
> `agent_registry`. Ao alterar aquelas tabelas, atualize este documento.
>
> Todos os comandos são relativos à **raiz do repositório**. As aspas em `"ava-pipeline-runner-cli.py"` são
> obrigatórias — o nome do arquivo tem espaço.

---

## 1. As três formas de invocar

| Forma               | Quando usar                                    | Interativo? |
| ------------------- | ---------------------------------------------- | ----------- |
| `--phase <ETAPA>` | rodar**uma etapa** da esteira            | não        |
| `--agent <ID>`    | rodar**um agente**, da esteira ou avulso | não        |
| sem flags           | escolher projeto, modo e fases pelo menu       | sim         |

```bash
# Uma etapa, direto
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --phase F4S

# Um agente, direto
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --agent ava-tobe-migration-plan

# Menu interativo (esteira completa ou seleção de fases)
python "ava-pipeline-runner-cli.py"
```

> ⚠️ **`--phase` aceita ETAPA, não GRUPO.** `--phase F2` responde que `F2` é um grupo e lista as etapas
> `F2a`…`F2d`. Grupos só rodam pelo menu interativo — o caminho não-interativo não grava `runner-state.json`
> nem o status HTML, e rodar quatro etapas sem esse rastro daria a impressão de ter executado a fase inteira
> sem o registro que a esteira exige.

---

## 2. Comandos por etapa — as 24 etapas, na ordem de execução

Substitua `cadastro-funcionarios` pelo seu projeto.

### Referência rápida — copiar e colar

Todas as 24 etapas na ordem da esteira. **22 rodam direto**; `F3S` e `F4` têm fan-out e são recusadas como
passo único (ver as seções delas).

```bash
P=cadastro-funcionarios

python "ava-pipeline-runner-cli.py" -p $P --phase F0     # AST Extraction (determinístico)
python "ava-pipeline-runner-cli.py" -p $P --phase F1     # AS-IS Diagnostic (orquestrador)
python "ava-pipeline-runner-cli.py" -p $P --phase F1a    # AS-IS Inventory
python "ava-pipeline-runner-cli.py" -p $P --phase F1b    # AS-IS Architecture & Bounded Contexts
python "ava-pipeline-runner-cli.py" -p $P --phase F1c    # AS-IS Database Analysis
python "ava-pipeline-runner-cli.py" -p $P --phase F1d    # AS-IS Documentation (Business Rules)
python "ava-pipeline-runner-cli.py" -p $P --phase F1e    # AS-IS Security Review
python "ava-pipeline-runner-cli.py" -p $P --phase F1f    # AS-IS Gaps & Risks
python "ava-pipeline-runner-cli.py" -p $P --phase F2a    # TO-BE Solution Design
python "ava-pipeline-runner-cli.py" -p $P --phase F2b    # DevOps Plan
python "ava-pipeline-runner-cli.py" -p $P --phase F2c    # QA Test Plan & Strategy
python "ava-pipeline-runner-cli.py" -p $P --phase F2d    # Coerência do wave model (determinístico)
python "ava-pipeline-runner-cli.py" -p $P --phase F3     # Prototype
#                                    --phase F3S    ← FAN-OUT: use o menu ou --feature
python "ava-pipeline-runner-cli.py" -p $P --phase F4S    # Scaffold determinístico
#                                    --phase F4     ← FAN-OUT: use o menu
python "ava-pipeline-runner-cli.py" -p $P --phase F5     # DevOps Execute
python "ava-pipeline-runner-cli.py" -p $P --phase F6     # QA Execution
python "ava-pipeline-runner-cli.py" -p $P --phase S1     # Summary — Generate
python "ava-pipeline-runner-cli.py" -p $P --phase S2     # Summary — Remediation
python "ava-pipeline-runner-cli.py" -p $P --phase S3     # Summary — Validate
python "ava-pipeline-runner-cli.py" -p $P --phase S4     # Summary — Final
python "ava-pipeline-runner-cli.py" -p $P --phase FC     # Containerize
python "ava-pipeline-runner-cli.py" -p $P --phase FP     # Podman Run (depende de FC)
```

> Verificado com `--dry-run` em `cadastro-funcionarios`: as 22 etapas acima resolvem agente, trigger e
> prompt sem menu; `F3S` e `F4` respondem `AGENTE COM FAN-OUT — INFORME O ESCOPO`.

### F0 — Extração AST (pré-requisito determinístico da F1)

```bash
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --phase F0
```

|              |                                                                         |
| ------------ | ----------------------------------------------------------------------- |
| agente       | `_ast_extractor` (subprocess, não é LLM)                            |
| trigger      | —                                                                      |
| observação | pular não bloqueia: os agentes F1 degradam para análise pattern-based |

### F1 — AS-IS Diagnostic (orquestrador — roda a fase inteira)

```bash
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --phase F1
```

|         |                           |
| ------- | ------------------------- |
| agente  | `ava-asis-orchestrator` |
| trigger | `FP`                    |

### F1a–F1f — AS-IS por agente especializado

```bash
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --phase F1a   # AS-IS Inventory
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --phase F1b   # Architecture & Bounded Contexts
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --phase F1c   # Database Analysis
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --phase F1d   # Documentation (Business Rules)
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --phase F1e   # Security Review
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --phase F1f   # Gaps & Risks
```

| Etapa   | Agente                       | Trigger |
| ------- | ---------------------------- | ------- |
| `F1a` | `ava-asis-inventory`       | —      |
| `F1b` | `ava-asis-solution-delphi` | —      |
| `F1c` | `ava-asis-db-analyzer`     | —      |
| `F1d` | `ava-asis-documentation`   | —      |
| `F1e` | `ava-asis-security-review` | —      |
| `F1f` | `ava-asis-gaps-risks`      | —      |

> `F1b` é resolvido pela `legacy_technology` do projeto. Para legado que não seja Delphi, use o agente de
> solução correspondente como avulso (`ava-asis-solution-java`, `-cobol`, `-dotnet`, `-vbnet`,
> `-visualbasic`, `-powerbuilder`).

### F2a–F2d — TO-BE Architecture

```bash
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --phase F2a   # TO-BE Solution Design
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --phase F2b   # DevOps Plan
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --phase F2c   # QA Test Plan & Strategy
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --phase F2d   # Coerência do wave model
```

| Etapa   | Agente                      | Trigger | Tipo                           |
| ------- | --------------------------- | ------- | ------------------------------ |
| `F2a` | `ava-tobe-orchestrator`   | `SD`  | agente                         |
| `F2b` | `ava-devops-orchestrator` | `DP`  | agente                         |
| `F2c` | `ava-qa-orchestrator`     | `TPT` | agente                         |
| `F2d` | `wave-model-consistency`  | —      | **tool determinística** |

> **F2d** normaliza e valida o `wave-model.json` contra o `wave-plan.md` e o bounded-context-map, e fecha
> chamando o `build_manifest()` real da F3S. Passar na F2d significa que a F3S expande. `on_fail: warn` — o
> achado aparece no console e em `outputs/tobe/migration/wave-model-consistency.json`, sem travar a fase.

### F3 — Protótipo

```bash
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --phase F3
```

|         |                   |
| ------- | ----------------- |
| agente  | `ava-prototype` |
| trigger | —                |

### F3S — SpecKit (constitution → specs → plans → tasks) · **fan-out**

```bash
# ✅ pelo menu interativo — é onde o fan-out por wave é expandido
python "ava-pipeline-runner-cli.py"

# ✅ uma feature por vez, sem menu
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --agent ava-speckit-orchestrator --feature 001-w0-foundation

# ❌ recusado: "AGENTE COM FAN-OUT — INFORME O ESCOPO"
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --phase F3S
```

|             |                                                                      |
| ----------- | -------------------------------------------------------------------- |
| agente      | `ava-speckit-orchestrator`                                         |
| trigger     | `SK`                                                               |
| DAG interno | `src/shared/data/pipeline-dag/F3S.yaml` (fonte única do despacho) |

> **Fan-out.** A F3S roda uma vez por migration wave; despachá-la como passo único é modo de falha medido —
> gerou 26 artefatos numa resposta de 68.170 tokens com skill de 8 KB, violando o contrato de seis agentes.
> O runner recusa e lista as features disponíveis. `--force-single` despacha mesmo assim, reproduzindo o
> defeito.
>
> Gate de entrada duro. Se ele reprovar por wave model incoerente, rode a **F2d** antes de tentar de novo.

### F4S — Scaffold determinístico (pré-requisito da F4)

```bash
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --phase F4S
```

|         |                                                                        |
| ------- | ---------------------------------------------------------------------- |
| agente  | `scaffold-runner` (**tool determinística**)                   |
| trigger | —                                                                     |
| ordem   | frontend → verify → backend → verify → baseline git → gate humano |

> `ava-stack-orchestrator` (F4) só despacha coder se esta etapa tiver registrado aprovação explícita.

### F4 — Tech Stack Generation · **fan-out**

```bash
# ✅ pelo menu interativo — expande um despacho por task
python "ava-pipeline-runner-cli.py"

# ❌ recusado: "AGENTE COM FAN-OUT — INFORME O ESCOPO"
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --phase F4
```

|                |                               |
| -------------- | ----------------------------- |
| agente         | `ava-stack-orchestrator`    |
| trigger        | `SG`                        |
| pré-requisito | aprovação registrada na F4S |

> **Fan-out.** Roda uma vez por task do razão SpecKit. Sem tasks compiladas, o runner diz exatamente isso e
> aponta a F3S como a fase que as produz.

### F5 — DevOps Execute

```bash
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --phase F5
```

|         |                             |
| ------- | --------------------------- |
| agente  | `ava-devops-orchestrator` |
| trigger | `DE`                      |

### F6 — QA Execution

```bash
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --phase F6
```

|         |                         |
| ------- | ----------------------- |
| agente  | `ava-qa-orchestrator` |
| trigger | `QE`                  |

### S1–S4 — Summary

```bash
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --phase S1   # Generate
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --phase S2   # Remediation
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --phase S3   # Validate
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --phase S4   # Final (regeneração limpa)
```

| Etapa  | Agente                      | Trigger | Pré-requisito          |
| ------ | --------------------------- | ------- | ----------------------- |
| `S1` | `ava-summary`             | `SAS` | —                      |
| `S2` | `ava-summary-remediation` | —      | HTML unificado da S1    |
| `S3` | `ava-summary-validate`    | —      | HTML unificado da S1/S2 |
| `S4` | `ava-summary`             | `SAS` | S1–S3                  |

### FC / FP — Containerização e execução local

```bash
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --phase FC   # Dockerfiles + docker-compose
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --phase FP   # Podman Run (depende de FC)
```

| Etapa  | Agente                      | Trigger |
| ------ | --------------------------- | ------- |
| `FC` | `ava-devops-containerize` | —      |
| `FP` | `ava-devops-podman-run`   | —      |

---

## 3. Grupos de fases — apenas pelo menu interativo

```bash
python "ava-pipeline-runner-cli.py"
#   Selecione o projeto ... cadastro-funcionarios
#   Modo de execução ...... 2   (Por Fase)
#   Números das fases ..... <n>
```

| Grupo   | Etapas                                 | Descrição                                      |
| ------- | -------------------------------------- | ------------------------------------------------ |
| `F0`  | F0                                     | AST Extraction (pré-requisito)                  |
| `F1`  | F1                                     | AS-IS Diagnostic (orquestrador)                  |
| `F1S` | F1a · F1b · F1c · F1d · F1e · F1f | AS-IS Specialized Agents                         |
| `F2`  | F2a · F2b · F2c · F2d               | TO-BE Architecture                               |
| `F3`  | F3                                     | Prototype                                        |
| `F3S` | F3S                                    | SpecKit                                          |
| `F4S` | F4S                                    | Scaffold determinístico                         |
| `F4`  | F4                                     | Tech Stack Generation (exige aprovação da F4S) |
| `F5`  | F5                                     | DevOps Execute                                   |
| `F6`  | F6                                     | QA Execution                                     |
| `SU`  | S1 · S2 · S3 · S4                   | Summary completo                                 |
| `FC`  | FC                                     | Containerize                                     |
| `FP`  | FP                                     | Podman Run                                       |

Para rodar um grupo sem menu, encadeie as etapas:

```bash
for fase in F2a F2b F2c F2d; do
  python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --phase $fase || break
done
```

---

## 4. Esteira completa

```bash
python "ava-pipeline-runner-cli.py"
#   Selecione o projeto ... cadastro-funcionarios
#   Modo de execução ...... 1   (Full)
```

Ordem executada: `F0 → F1 → F1a…F1f → F2a → F2b → F2c → F2d → F3 → F3S → F4S → F4 → F5 → F6 → S1…S4`.
`FC` e `FP` ficam fora do Full — são pós-entrega.

Retomar um run interrompido: **não há flag `--resume`**. Rode o runner sem flags e, detectado estado
anterior do projeto, ele pergunta antes de qualquer execução:

```
⚠️  Execução anterior detectada
    Projeto: cadastro-funcionarios
    Último passo: 7/24 · Executados: 6 · Pulados: 1 · Abortados: 0
Deseja retomar de onde parou? [S]im / [N]ão (recomeçar):
```

> A mensagem de `Ctrl-C` do runner ainda diz "Retome com `--resume`". A flag não existe — é a pergunta acima
> que retoma.

---

## 5. Agentes da esteira — invocação avulsa

Os 21 executáveis por `--agent` sem precisar de mais nada:

```bash
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --agent ava-asis-inventory
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --agent ava-tobe-orchestrator
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --agent ava-prototype
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --agent ava-speckit-orchestrator
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --agent ava-stack-orchestrator
```

| Agente                       | Etapa(s) |
| ---------------------------- | -------- |
| `_ast_extractor`           | F0       |
| `ava-asis-orchestrator`    | F1       |
| `ava-asis-inventory`       | F1a      |
| `ava-asis-solution-delphi` | F1b      |
| `ava-asis-db-analyzer`     | F1c      |
| `ava-asis-documentation`   | F1d      |
| `ava-asis-security-review` | F1e      |
| `ava-asis-gaps-risks`      | F1f      |
| `ava-tobe-orchestrator`    | F2a      |
| `wave-model-consistency`   | F2d      |
| `ava-prototype`            | F3       |
| `ava-speckit-orchestrator` | F3S      |
| `scaffold-runner`          | F4S      |
| `ava-stack-orchestrator`   | F4       |
| `ava-devops-containerize`  | FC       |
| `ava-devops-podman-run`    | FP       |
| `ava-summary-remediation`  | S2       |
| `ava-summary-validate`     | S3       |

### Agentes ambíguos — exigem `--phase` para desempatar

Três agentes aparecem em mais de uma etapa. Sem `--phase`, o runner recusa e mostra as opções.

```bash
# ava-devops-orchestrator — F2b (plano) ou F5 (execução)
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --agent ava-devops-orchestrator --phase F2b
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --agent ava-devops-orchestrator --phase F5

# ava-qa-orchestrator — F2c (plano) ou F6 (execução)
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --agent ava-qa-orchestrator --phase F2c
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --agent ava-qa-orchestrator --phase F6

# ava-summary — S1 (generate) ou S4 (final)
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --agent ava-summary --phase S1
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --agent ava-summary --phase S4
```

---

## 6. Agentes avulsos do registry (93)

Não estão na esteira: rodam sob demanda, sem trigger próprio, e o contexto vem pelo caminho legado de
`load_context`. Padrão:

```bash
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --agent <ID>
```

> ⚠️ **A fase abaixo é a do MÓDULO, não a da esteira.** É informativa e nunca validada — os agentes de QA,
> por exemplo, aparecem como `F5` no registry mas rodam em `F2c`/`F6` na esteira. Para saber os triggers de
> um agente, leia o `## Triggers / Menu` da spec dele em
> `src/modules/ava-fabric-agents/<módulo>/agents/`.

### AS-IS (módulo F1)

```
ava-asis-bridge-fastqa                ava-asis-security-iast
ava-asis-business-rules-generator     ava-asis-security-orchestrator
ava-asis-events-pubsub                ava-asis-security-pt-pattern
ava-asis-gap-migration-analyzer       ava-asis-security-sast
ava-asis-security-dependency-config   ava-asis-security-taint
ava-asis-security-threat-model
```

Agentes de solução por tecnologia legada (escolha o da `legacy_technology` do projeto):

```
ava-asis-solution-cobol      ava-asis-solution-java         ava-asis-solution-visualbasic
ava-asis-solution-dotnet     ava-asis-solution-powerbuilder ava-asis-solution-vbnet
```

### TO-BE (módulo F2)

```
ava-coder-dotnet                        ava-tobe-coexistence-strategy
ava-developer-guide-tobe                ava-tobe-database-design
ava-docs-tobe                           ava-tobe-database-policy
ava-dotnet-nuget-policy                 ava-tobe-designer-system
ava-tobe-adr                            ava-tobe-measure-size
ava-tobe-architecture-decision-matrix   ava-tobe-migration-plan
ava-tobe-architecture-design            ava-tobe-risk-mitigation
ava-tobe-architecture-technical         ava-tobe-security-design
ava-tobe-azure-infra-estimator          ava-tobe-security-review
ava-tobe-spec                           ava-tobe-sql-schema-to-mer
ava-tobe-user-journeys
```

Dois com triggers verificados e de uso frequente:

```bash
# ava-tobe-architecture-design — sequência obrigatória CB → BC → TD
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --agent ava-tobe-architecture-design --trigger CB
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --agent ava-tobe-architecture-design --trigger BC
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --agent ava-tobe-architecture-design --trigger TD

# ava-tobe-migration-plan — produz wave-model.json e derivados
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --agent ava-tobe-migration-plan
```

> `CB` → `architecture-blueprint.md` · `BC` → `bounded-context-map.md` **e** `bounded-context-map.json`
> · `TD` → os 5 diagramas C4/classe/sequência. Há gate executável entre `BC` e `TD`.

### SpecKit (módulo F3S)

```
ava-speckit-compliance    ava-speckit-planning         ava-speckit-specification
ava-speckit-constitution  ava-speckit-prototype-spec   ava-speckit-tasks
```

Agentes por feature exigem `--feature`:

```bash
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --agent ava-speckit-specification \
  --feature 002-w1-role-management
```

### Stack / codegen (módulo F4)

```
ava-f4s-codegen-agent        ava-stack-docs-researcher    ava-stack-python-backend
ava-stack-angular-frontend   ava-stack-dotnet-backend     ava-stack-react-frontend
ava-stack-blazor-frontend    ava-stack-go-backend         ava-stack-vue-frontend
ava-stack-build-fixer        ava-stack-java-backend
ava-stack-build-validator    ava-stack-node-backend
```

### QA (módulo F5)

```
ava-qa-behavior-mapping        ava-qa-evidence-capture           ava-qa-scenario-generator
ava-qa-bridge-fastqa-tobe      ava-qa-exploratory                ava-qa-script-generator
ava-qa-contract-test-generator ava-qa-frontend-test-generator    ava-qa-test-case-generator
ava-qa-db-integrity-test       ava-qa-gaps-requirements          ava-test-plan-tobe
ava-qa-defect-identifier
```

### DevOps / IaC (módulo F6)

```
ava-build-cycle-iac       ava-devops-iac              ava-devops-iac-k8s-native
ava-devops-cd             ava-devops-iac-aws          ava-devops-monitoring-observability
ava-devops-ci             ava-devops-iac-azure        ava-devops-package-approval
ava-devops-compare-version ava-devops-iac-gcp
ava-devops-cost-estimate
```

### Deliverables (módulo F7)

```
ava-deliverable-client-demo            ava-deliverable-security-compliance
ava-deliverable-code-templates         ava-deliverable-strategy-align
ava-deliverable-migration-plan         ava-deliverable-tech-docs
ava-deliverable-package-approval-doc   ava-deliverable-test-evidence
ava-deliverable-packager               ava-requestor-inspection
```

### Orquestrador mestre

```bash
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --agent ava-master-orchestrator
```

Lista sempre atualizada, direto da fonte:

```bash
python "ava-pipeline-runner-cli.py" --list-agents
```

---

## 7. Flags

| Flag                       | Efeito                                                                  |
| -------------------------- | ----------------------------------------------------------------------- |
| `-p`, `--project NOME` | projeto em`projects/`. Obrigatório com `--phase` e `--agent`     |
| `--phase ID`             | etapa a executar; com`--agent`, desempata agente em mais de uma etapa |
| `--agent ID`             | roda só este agente (da esteira ou avulso do registry)                 |
| `--trigger T`            | trigger do prompt; sem ele sai`@agente project: X`                    |
| `--feature F`            | feature do SpecKit, para agente que roda por feature                    |
| `--model ID`             | deployment do Foundry; sem ele usa o default                            |
| `--headroom`             | sobe o proxy headroom antes do despacho                                 |
| `--force-single`         | despacha agente com fan-out como passo único (não recomendado)        |
| `--dry-run`              | resolve o passo e mostra o prompt,**sem gastar inferência**      |
| `--list-agents`          | lista os agentes despacháveis e sai                                    |
| `--json`                 | emite o resultado do despacho em JSON                                   |

**Exit codes**: `0` ok · `1` etapa falhou · `2` erro de configuração · `130` abortado.

Ensaiar antes de gastar inferência:

```bash
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --phase F2a --dry-run
```

---

## 8. Tools determinísticas — fora do fluxo de agentes

Não consomem inferência. Úteis para diagnosticar sem re-rodar uma fase.

### Coerência do wave model (o mesmo da F2d)

```bash
# diagnóstico — não escreve nada
python src/shared/tools/wave_model_consistency.py --project cadastro-funcionarios

# aplica as correções mecânicas
python src/shared/tools/wave_model_consistency.py --project cadastro-funcionarios --fix
```

### Gates da F3S

```bash
python src/modules/ava-fabric-agents/speckit/utils/artifact_gate_speckit.py \
       --project cadastro-funcionarios --gate entry

python src/modules/ava-fabric-agents/speckit/utils/artifact_gate_speckit.py \
       --project cadastro-funcionarios --gate exit
```

### Manifesto de waves da F3S

```bash
python src/shared/tools/speckit_wave_manifest.py --project cadastro-funcionarios
```

### Scaffold da F4S, direto

```bash
# fase inteira
python src/shared/tools/scaffold_runner.py --project cadastro-funcionarios --json

# decisão do gate humano sem terminal
python src/shared/tools/scaffold_runner.py --project cadastro-funcionarios --approve
python src/shared/tools/scaffold_runner.py --project cadastro-funcionarios --reject

# o que fazer quando um componente reprova (sem terminal; default = abort)
python src/shared/tools/scaffold_runner.py --project cadastro-funcionarios \
       --on-component-failure continue

# regenerar por cima do que existe
python src/shared/tools/scaffold_runner.py --project cadastro-funcionarios --eforce
```

### Wrappers de agente

```bash
python src/shared/tools/generate_agent_wrappers.py --check     # CI: exit 1 se houver drift
python src/shared/tools/generate_agent_wrappers.py --phase F2  # regenera só uma fase
```

---

## 9. Receitas

**Destravar a F3S quando ela reprova por wave model incoerente**

```bash
python src/shared/tools/wave_model_consistency.py --project cadastro-funcionarios --fix
python src/modules/ava-fabric-agents/speckit/utils/artifact_gate_speckit.py \
       --project cadastro-funcionarios --gate entry
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --phase F3S
```

**Regerar só o mapa de bounded contexts TO-BE**

```bash
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --agent ava-tobe-architecture-design --trigger BC
python src/shared/tools/wave_model_consistency.py --project cadastro-funcionarios --fix
```

**Refazer o Summary do zero**

```bash
for fase in S1 S2 S3 S4; do
  python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --phase $fase || break
done
```

**Ver o que uma etapa faria, sem gastar inferência**

```bash
python "ava-pipeline-runner-cli.py" -p cadastro-funcionarios --phase F4 --dry-run
```

---

## 10. Caminhos longos no Windows — contornado automaticamente

A F4S gera caminhos .NET fundos: o nome do projeto entra **duas vezes** em cada caminho (pasta + arquivo).
Medido em `cadastro-funcionarios`, o `.csproj` mais fundo tem **267 chars** contra o limite clássico de 260.

Acima do limite o Windows **mente em vez de falhar**: `Path.is_file()` devolve `False` para arquivo que
existe. O gerador conclui "não existe", manda `dotnet new` recriar, e o `dotnet new` — que enxerga o arquivo
— recusa sobrescrever com `exit 73`. O sintoma nunca menciona comprimento de caminho.

**Não é preciso fazer nada.** Generator e verifier detectam o estouro e geram através de uma raiz curta
temporária (`subst` numa letra livre: `Z:`, `Y:`, `X:`…), removida ao fim da chamada. Os arquivos nascem no
caminho real, com os nomes de sempre — a saída é idêntica com ou sem contorno. O relatório JSON registra:

```
"path_workaround": "verificado atraves da raiz curta Z: (subst) — caminhos acima de
                    MAX_PATH neste Windows. Correcao definitiva: LongPathsEnabled=1."
```

Só reprova se **nenhuma** letra de unidade estiver livre — e aí a mensagem lista as quatro saídas.

### Correção definitiva (recomendada)

Verificar:

```powershell
Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' LongPathsEnabled
```

Habilitar — exige admin + reinício, resolve para toda a esteira e dispensa o contorno:

```powershell
Set-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' LongPathsEnabled 1
```

Sem admin: mover o repositório para uma raiz mais curta (ex.: `C:\ava\`).

> ⚠️ **Ao mexer em código que roda sob o contorno**: `Path.resolve()` **desfaz** o mapeamento `subst` e
> devolve o caminho longo, apagando o contorno sem erro nenhum. Dentro do bloco, trate a raiz curta como
> absoluta e não a normalize. Detalhes em `src/shared/tools/short_path_root.py`.

### Por que `subst` e não junction

Medido nas duas: `mklink /J` **não** resolve — o motor de templates do `dotnet new` canonicaliza o reparse
point de volta para o alvo longo. `subst` resolve, porque `GetFullPath` não desfaz o mapeamento DosDevice.
Nenhum dos dois exige administrador.

---

## Documentos relacionados

| Documento                                                           | Assunto                                                                                 |
| ------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| [`guia-ava-pipeline-cli.md`](guia-ava-pipeline-cli.md)             | CLI declarativo`ava-pipeline` (front-end alternativo — `--phase` aceita grupo lá) |
| [`guia-execucao-agente-avulso.md`](guia-execucao-agente-avulso.md) | despacho de agente isolado, em profundidade                                             |
| [`guia-execucao-fluxo-agentes.md`](guia-execucao-fluxo-agentes.md) | fluxo fase a fase, com insumos e saídas                                                |
| [`fase-scaffold.md`](fase-scaffold.md)                             | F4S: ordem, gates e estado                                                              |
| [`speckit-guia.md`](speckit-guia.md)                               | F3S: constitution → specs → plans → tasks                                            |
| [`guia-waves-migracao.md`](guia-waves-migracao.md)                 | wave model e artefatos derivados da F2                                                  |
| [`agents-catalog.md`](agents-catalog.md)                           | catálogo completo dos agentes                                                          |
