---
name: migration-validation-gate
version: "1.4.0"
date: 2026-07-09
description: "Validation gate obrigatória para o Migration Plan Agent — 10 etapas de verificação (inclui 7.5 — Wave Model Structural Coherence) + Output Invariant antes de declarar plano concluído"
applies_to: ava-tobe-migration-plan
---

# Migration Plan — Validation Gate

> **Execute when**: Step 8 of the Execution Protocol, before declaring the migration plan complete.
> **Rule**: If any etapa fails → block delivery, fix, and re-execute before closing.

---

## Etapa 1 — T-Shirt Sizing Check

| # | Verificação | Artefato | Resultado esperado |
|---|---|---|---|
| 1.1 | Todas as 5 dimensões pontuadas para cada BC (ou `?` com justificativa documentada) | `tshirt-sizing-rationale.md` | Nenhuma célula vazia sem justificativa |
| 1.2 | `Dimensão determinante` declarada nominalmente para cada BC | `tshirt-sizing-rationale.md` | Coluna preenchida em 100% das linhas |
| 1.3 | T-shirt = max das 5 dimensões — amostrar 20% dos BCs e verificar manualmente | `tshirt-sizing-rationale.md` | Zero inconsistências na amostra |

## Etapa 2 — Integration Matrix Check

| # | Verificação | Artefato | Resultado esperado |
|---|---|---|---|
| 2.1 | Colunas `Dependências de entrada` e `Dependências de saída` separadas (não fundidas) | `integration-matrix.md` | Duas colunas distintas |
| 2.2 | `Wave sugerida` preenchida em todas as linhas | `integration-matrix.md` | Zero células vazias |
| 2.3 | Coupling Score = entrada + saída (verificar bidirecionalidade em amostra de 20%) | `integration-matrix.md` | Soma verificável pela fórmula canônica |

## Etapa 3 — Wave Plan Check

| # | Verificação | Artefato | Resultado esperado |
|---|---|---|---|
| 3.1 | Todas as waves têm `Tempo IA (h)`, `Tempo manual (h)` e `Tempo total (h)` derivados dos benchmarks | `wave-plan.md` | Zero células sem valor numérico |
| 3.2 | Cada item de gap-list tem `Motivo técnico`, `Responsável sugerido` com valor ∈ {`Dev`, `DevOps`, `QA`, `BA`, `Legal`, `Security`, `A definir até {data}`} e `Impacto se omitido` | `wave-plan.md` | 3 campos obrigatórios; branco = bloqueio; `A definir` sem data = bloqueio |
| 3.3 | Total de waves = 5. W0 wave_type=`foundation` e W4 wave_type=`cutover` (fixos). W1, W2, W3 com wave_type dinâmico ∈ {`domain_read`, `domain_write`, `domain_core`} — inferido do predominant_operation_type majoritário dos BCs alocados na wave (Leitura→domain_read, Escrita→domain_write, Core→domain_core; empate: Core > Escrita > Leitura). Nomes e BCs dinâmicos conforme wave-model.json. | `wave-plan.md` | N = 5; W0=foundation, W4=cutover (fixos); W1-W3 com wave_type válido (domain_read|domain_write|domain_core) coerente com predominant_operation_type dos BCs; qualquer divergência = bloqueio |
| 3.4 | W0 (`foundation`) tem T-shirt ≤ M (XS, S ou M) | `wave-plan.md` | `T-shirt W0 ∈ {XS, S, M}`; L ou XL = bloqueio |
| 3.5 | W4 (`cutover`) tem T-shirt ≤ M (XS, S ou M) | `wave-plan.md` | `T-shirt W4 ∈ {XS, S, M}`; L ou XL = bloqueio |

## Etapa 3.5 — Gantt Validation Check

> Verificar que o artefato `migration-gantt.mmd` segue o protocolo
> do Step 6.5 do Execution Protocol e é consistente com o `sizing-report.md` e `wave-model.json`.

| # | Verificação | Artefatos verificados | Resultado esperado |
|---|---|---|---|
| 3.6 | Número de sections/waves no `migration-gantt.mmd` = número de waves no `wave-model.json` | `migration-gantt.mmd` vs. `wave-model.json` | 5 sections (W0–W4); divergência = bloqueio |
| 3.7 | `wave_name` de cada section no Gantt = `wave_name` no `wave-model.json` | `migration-gantt.mmd` vs. `wave-model.json` | Nomes idênticos |
| 3.8 | Cada wave decomposta em 4 fases (análise/design, desenvolvimento, testes/homologação, deploy) | `migration-gantt.mmd` | 4 fases × 5 waves = 20 tarefas + milestones |
| 3.9 | Durações derivadas da cadeia `total_hours_wave ÷ (squad_size × hours_per_week)` com Fixed Parameters (squad=3, hours_per_week=40) | `migration-gantt.mmd` vs. `sizing-report.md` | Duração de cada wave = `ceil(total_hours ÷ 120)` semanas |
| 3.10 | Dependências inter-wave respeitam sequência W0→W1→W2→W3→W4 | `migration-gantt.mmd` | Todas as waves com `after w{N-1}-deploy` |
| 3.11 | Milestones Go/No-Go presentes após waves de domínio (W1–W3) | `migration-gantt.mmd` | ≥ 3 milestones Go/No-Go + 1 milestone final |
| 3.12 | Conteúdo Gantt embutido na seção "Cronograma Estimado" do `wave-plan.md` é idêntico ao `migration-gantt.mmd` | `wave-plan.md` vs. `migration-gantt.mmd` | Blocos Mermaid idênticos |
| 3.13 | Nenhuma data de calendário absoluta atribuída como propriedade da wave — durações são relativas (G-13). Data de início é placeholder para renderização | `migration-gantt.mmd` | Datas são placeholder; durações usam formato relativo (`Nd`, `Nw`) |

> **Se qualquer verificação falhar**: regenerar o artefato Gantt seguindo o protocolo do Step 6.5,
> usando `sizing-report.md` e `wave-model.json` como fontes autoritativas.
> Re-executar esta etapa até que todos os checks passem.

## Etapa 3.6 — Wave Plan Structural Integrity Check

> Verifica se `wave-plan.md` é um artefato bem formado, autocontido e alinhado ao
> template `wave-plan-executivo-template.md` e ao `wave-model.json`.
> Executar também o validador externo `src/shared/utils/verify_wave_plan.py`.

| # | Verificação | Artefato | Resultado esperado |
|---|---|---|---|
| 3.14 | `wave-plan.md` existe em disco com tamanho > 0 | `wave-plan.md` | arquivo presente e não vazio; ausência = bloqueio |
| 3.15 | Contém exatamente 5 waves identificadas (W0, W1, W2, W3, W4) com headers de nível 2 na forma canônica `## W{N} — {wave_name}` (ex.: `## W0 — Foundation`). É esta a forma que `speckit_wave_manifest.py` casa para reconciliar plan × modelo; `## Wave 0 …` **não** é reconhecido e faz a F3S ler o plano como se ele não tivesse waves | `wave-plan.md` | 5 headers de wave no formato `## W{N} — …`; divergência = bloqueio |
| 3.16 | W0 com `wave_type=foundation` e pelo menos 4 seções: propósito, entrada e saída, critérios de sucesso, definição de ready/go/no-go e dependências | `wave-plan.md` | seções W0 completas; falta = bloqueio |
| 3.17 | W1–W3 com 10 seções obrigatórias: objetivo, escopo, bounded contexts, dependências, infraestrutura, equipe e papéis, riscos e mitigações, critérios de aceite, Go/No-Go, timeline | `wave-plan.md` | todas as seções presentes por wave; falta em qualquer wave = bloqueio |
| 3.18 | W4 (`cutover`) com seção de rollback e validação pós-cutover | `wave-plan.md` | seções de rollback e validação presentes; falta = bloqueio |
| 3.19 | Contém Resumo Executivo no início com tabela totalizadora de waves | `wave-plan.md` | resumo executivo + tabela presentes; ausência = bloqueio |
| 3.20 | Bloco Mermaid `gantt` presente na seção "Cronograma Estimado" | `wave-plan.md` | bloco presente; ausência = bloqueio |
| 3.21 | Bloco Mermaid `flowchart` ou `graph` presente no Mapa de Dependências | `wave-plan.md` | bloco presente; ausência = bloqueio |
| 3.22 | Cada wave lista os mesmos BCs atribuídos no `wave-model.json` | `wave-plan.md` vs. `wave-model.json` | zero BCs ausentes/excedentes por wave; divergência = bloqueio |
| 3.23 | T-shirt e FP/SP por wave são consistentes com `wave-model.json` e `sizing-report.md` | `wave-plan.md` vs. `wave-model.json` / `sizing-report.md` | zero divergências; divergência = bloqueio |
| 3.24 | Nenhuma referência a calendário absoluto — apenas durações relativas e placeholder de início | `wave-plan.md` | nenhuma data real; presença = bloqueio |
| 3.25 | Validador externo `verify_wave_plan.py` retorna exit code 0 | `wave-plan.md` | `python src/shared/utils/verify_wave_plan.py --project {project_name}` retorna 0; falha = bloqueio |

> **Se qualquer verificação falhar**: corrigir `wave-plan.md` e/ou os artefatos-fonte (`wave-model.json`, `sizing-report.md`), reexecutar o agente `@ava-tobe-migration-plan` se necessário, e rodar novamente o `verify_wave_plan.py` até PASS.

## Etapa 4 — Output Contract Check

> **Nota de origem**: Os 13 arquivos do Output Contract são gerados em fases distintas do orquestrador:
> arquivos 1-3 e 13 na Fase 2.7 (trigger `WM`), arquivo 1 atualizado na Fase 3 (sizing), arquivos 4-12 na Fase 4 (invocação completa).
> Esta etapa valida que **todos os 13 existem em disco** independentemente de qual fase os gerou.

| # | Verificação | Resultado esperado |
|---|---|---|
| 4.1 | `ai-estimation-report.md`: tabela consolidada com linha **TOTAL** presente e somando todas as waves | Linha TOTAL com soma de Tempo IA, Manual e Total |
| 4.2 | `migration-executive-summary.md`: autocontido, sem referências cruzadas pendentes, leitura ≤ 2 minutos | Zero referências que exijam leitura de outro artefato |
| 4.3 | Verificar existência em disco e tamanho > 0 de cada um dos **13 arquivos obrigatórios** do Output Contract (tabela abaixo) | Todos os 13 com status `OK`; qualquer `FALTANDO` ou `VAZIO` = bloqueio |

### Checklist de Completude — 13 arquivos obrigatórios (fluxo padrão)

| # | Arquivo | Caminho esperado | Verificação |
|---|---|---|---|
| 1 | `wave-model.json` | `outputs/tobe/migration/wave-model.json` | existe + tamanho > 0 + JSON válido |
| 2 | `integration-matrix.md` | `outputs/tobe/docs/integration-matrix.md` | existe + tamanho > 0 |
| 3 | `tshirt-sizing-rationale.md` | `outputs/tobe/docs/tshirt-sizing-rationale.md` | existe + tamanho > 0 |
| 4 | `ai-estimation-report.md` | `outputs/tobe/docs/ai-estimation-report.md` | existe + tamanho > 0 |
| 5 | `manual-gap-list.md` | `outputs/tobe/docs/manual-gap-list.md` | existe + tamanho > 0 |
| 6 | `migration-executive-summary.md` | `outputs/tobe/docs/migration-executive-summary.md` | existe + tamanho > 0 |
| 7 | `migration-plan.md` | `outputs/tobe/docs/migration-plan.md` | existe + tamanho > 0 |
| 8 | `wave-plan.md` | `outputs/tobe/docs/wave-plan.md` | existe + tamanho > 0 |
| 9 | `ado-work-items.md` | `outputs/tobe/docs/ado-work-items.md` | existe + tamanho > 0 |
| 10 | `migration-gantt.mmd` | `outputs/tobe/diagrams/migration-gantt.mmd` | existe + tamanho > 0 |
| 11 | `migration-activity-plan.md` | `outputs/tobe/migration/migration-activity-plan.md` | existe + tamanho > 0 |
| 12 | `activity-dependency-graph.md` | `outputs/tobe/migration/activity-dependency-graph.md` | existe + tamanho > 0 |
| 13 | `migration-priority-matrix.md` | `outputs/tobe/migration/migration-priority-matrix.md` | existe + tamanho > 0 |

## Etapa 5 — Migration Activity Plan Check

| # | Verificação | Artefato | Resultado esperado |
|---|---|---|---|
| 5.1 | Todas as atividades possuem rastreabilidade (`BR-{N}` ou `ARCH-{componente}`) | `migration-activity-plan.md` | Zero atividades sem rastreabilidade |
| 5.2 | Todas as atividades classificadas em exatamente uma camada (Domain/App/Infra/UI) | `migration-activity-plan.md` | Zero atividades sem camada |
| 5.3 | Todas as atividades associadas a exatamente um BC | `migration-activity-plan.md` | Zero atividades sem BC |
| 5.4 | Todas as atividades possuem Tipo Operação (Leitura/Escrita/Core) | `migration-activity-plan.md` | Zero atividades sem tipo |
| 5.5 | Estratégia incremental respeitada: atividades Core não precedem Leitura no mesmo BC | `activity-dependency-graph.md` | Zero violações de sequência incremental |
| 5.6 | Priority Score calculado para todos os BCs com fórmula explícita | `migration-priority-matrix.md` | Zero BCs sem score |
| 5.7 | Grafo de dependências acíclico | `activity-dependency-graph.md` | Zero ciclos detectados |
| 5.8 | Pontuações dos 4 critérios correspondem aos indicadores da Rubrica de Pontuação Canônica — amostrar 30% dos BCs e verificar aderência | `migration-priority-matrix.md` | Zero pontuações sem correspondência com indicadores objetivos da rubrica |
| 5.9 | BCs com Tipo Operação `Leitura` posicionados em waves anteriores ou iguais a BCs de `Escrita`/`Core` do mesmo domínio funcional | `wave-plan.md` + `migration-activity-plan.md` | Zero violações de progressão Leitura → Escrita → Core entre waves |
| 5.10 | Valores `[INFERIDO]` documentados com justificativa na coluna de observações | `migration-priority-matrix.md` | Todo valor neutro (3) aplicado por ausência de dado está marcado como `[INFERIDO]` com referência ao artefato ausente |

## Etapa 5.5 — Backlog TO-BE Check (Input Herdado da Fase 2.5)

> Verificar que o `backlog-tobe.md` existe como input herdado da Fase 2.5 do orquestrador. Se ausente → **emitir alerta de re-execução da Fase 2.5** (NÃO executar Step 7.5 localmente — a geração é responsabilidade do orquestrador).

| # | Verificação | Artefato | Resultado esperado |
|---|---|---|---|
| 5.11 | `backlog-tobe.md` existe em disco com tamanho > 0 | `backlog-tobe.md` | Arquivo presente (gerado na Fase 2.5); se FALTANDO → re-executar Fase 2.5 do orquestrador |
| 5.12 | Todos os BCs do `bounded-context-map.md` TO-BE representados | `backlog-tobe.md` | Zero BCs ausentes |
| 5.13 | Cada user story tem rastreabilidade (≥ 1 BR/RF/ARCH) | `backlog-tobe.md` | Zero US sem rastreabilidade |
| 5.14 | Prioridade MoSCoW atribuída a 100% das US | `backlog-tobe.md` | Zero US sem MoSCoW |
| 5.15 | Seção técnica presente com IDs `US-TECH-{NNN}` e ≥ 1 US por cada um dos 6 domínios transversais | `backlog-tobe.md` | Seção existe + 6 domínios cobertos |
| 5.16 | Cobertura de regras de negócio ≥ 80% por BC | `backlog-tobe.md` | ≥ 80% de BRs cobertas por BC |

> Se `backlog-tobe.md` não existir (5.11 FAIL) → **EMITIR ALERTA**. O `backlog-tobe.md` é gerado na Fase 2.5 do orquestrador. Se ausente, re-executar `@ava-tobe-orchestrator` Fase 2.5 (trigger: backlog-tobe) e depois retornar a esta Validation Gate.

## Etapa 6 — Wave Cycle Refinement Check (apenas quando trigger WCR acionado)

| # | Verificação | Artefato | Resultado esperado |
|---|---|---|---|
| 6.1 | `wave-plan-refined.md` contém campos adicionais: CF, Fonte de ajuste, Desvio vs. original | `wave-plan-refined.md` | Campos presentes em todas as waves |
| 6.2 | `wcr-changelog.md` documenta todas as mudanças aplicadas | `wcr-changelog.md` | Zero mudanças não documentadas |
| 6.3 | Critérios de aceite marcados como `[VALIDADO]` pelo Requestor/Human SME | `wave-plan-refined.md` | Ao menos os critérios de Wave 1 validados |
| 6.4 | Calibration Factor documentado e aplicado consistentemente | `wave-plan-refined.md` | CF uniforme em todas as waves restantes |

## Etapa 7 — Wave Model Cross-Validation Check

> Executar **obrigatoriamente** para verificar que todos os artefatos derivados referenciam as mesmas waves que o `wave-model.json`.

| # | Verificação | Artefatos verificados | Resultado esperado |
|---|---|---|---|
| 7.1 | Número total de waves idêntico entre `wave-model.json` e cada artefato derivado | `wave-plan.md`, `migration-executive-summary.md`, `ai-estimation-report.md`, `ado-work-items.md`, `migration-gantt.mmd` | Zero divergências no número de waves |
| 7.2 | Composição de BCs por wave idêntica: cada wave nos artefatos derivados contém exatamente os mesmos BCs listados no `wave-model.json` | `wave-plan.md`, `ado-work-items.md` | Zero BCs ausentes ou excedentes em qualquer wave |
| 7.3 | T-shirt por wave idêntico entre modelo e artefatos derivados | `wave-plan.md`, `migration-executive-summary.md`, `ai-estimation-report.md` | Zero divergências de T-shirt |
| 7.4 | FP/SP por wave e por BC idênticos entre `wave-model.json` e `sizing-report.md`; horas derivadas nos artefatos consistentes via cadeia Fixed Parameters (FP × 1.8 = SP → SP ÷ 20 = Sprints → Sprints × 10 × 8 = Horas) | `wave-plan.md`, `ai-estimation-report.md`, `migration-executive-summary.md`, `sizing-report.md` | Zero divergências de FP/SP; horas derivadas coerentes com cadeia Fixed Parameters |
| 7.5 | `wave_ids_hash` do modelo corresponde ao hash recalculado a partir dos artefatos derivados | Todos os artefatos derivados listados em `cross_validation_checksums` | Hash match = PASS; hash mismatch = BLOQUEIO |
| 7.6 | `integration-matrix.md` coluna `Wave sugerida` corresponde à wave atribuída no modelo para cada BC | `integration-matrix.md` vs. `wave-model.json` | Zero divergências na coluna Wave sugerida |
| 7.7 | `manual-gap-list.md` coluna `Wave` referencia apenas waves existentes no modelo | `manual-gap-list.md` vs. `wave-model.json` | Zero referências a waves inexistentes |

> **Se qualquer verificação falhar**: identificar a divergência, atualizar o `wave-model.json` se o modelo está desatualizado OU regenerar o artefato derivado a partir do modelo se o artefato está incorreto. Re-executar a Etapa 7 até que todas as verificações passem.

---

## Etapa 7.5 — Wave Model Structural Coherence Check (BLOQUEANTE)

> A Etapa 7 confere o modelo **contra os derivados**. Esta confere o modelo **contra si mesmo** — a classe de
> defeito que a Etapa 7 não vê porque não há artefato divergente: os campos do próprio `wave-model.json` é que
> não se sustentam.
>
> **Caso medido** — `cadastro-funcionarios`, 2026-08-26. A F3S abortou a expansão com
> `wave-model.json waves[1] não declara bc_details para bounded_contexts='BC-02'`, **com todos os artefatos do
> gate de entrada presentes**. O modelo gravou `"bounded_contexts": ["BC-02"]` (ID textual) sem o `bc_details[]`
> que nomeia o BC. A Etapa 7 passou — plano e modelo concordavam sobre BC-02. O que não existia era o **nome**
> do BC, e código determinístico não inventa nome.

| # | Invariante | Resultado esperado |
|---|---|---|
| 7.5.1 | Todo item de `waves[].bounded_contexts[]` é **objeto** com `bc_id` e `bc_name` não vazios. Nenhum ID textual (`["BC-02"]`); `bc_details[]` ausente — seus campos absorvidos nos objetos | Zero itens textuais; zero `bc_name` vazio |
| 7.5.2 | Todo `bc_id` alocado tem definição no `bounded-context-map.md` | Zero referências órfãs |
| 7.5.3 | Nenhum `bc_id` aparece em mais de uma wave | Zero BCs duplicados entre waves |
| 7.5.4 | `wave_id` (`W{N}`) e `wave_number` (`{N}`) ambos presentes e concordantes; `tshirt` preenchido (grafia `tshirt`, não `tshirt_size`) | Zero waves com identidade parcial |
| 7.5.5 | `depends_on_waves[]` referencia apenas waves declaradas no modelo; nenhuma wave depende de si mesma | Zero dependências penduradas |
| 7.5.6 | `total_waves` == `len(waves)`; `summary.total_waves` idem; `total_fp`/`total_sp` == soma das waves quando preenchidos | Zero divergências de contagem/soma |
| 7.5.7 | `metadata.project_name` == projeto em execução (a guarda anti-artefato-de-outro-projeto do manifesto **não** lê `project_name` de primeiro nível) | Identidade declarada onde o leitor a jusante procura |
| 7.5.8 | Conjunto de wave ids e composição de BCs por wave idênticos aos headings `## W{N} — …` e às seções do `wave-plan.md` | Zero divergências plan × modelo |

### Veredito determinístico

O julgamento não é de leitura do agente — é da **mesma implementação que a F3S executa**:

```
python src/shared/tools/wave_model_consistency.py --project {project_name}
```

Exige `status: ok`. A tool valida 7.5.1–7.5.8 e fecha chamando o `build_manifest()` real do
`speckit_wave_manifest.py`: passar aqui significa que a F3S expande. Veredito persistido em
`outputs/tobe/migration/wave-model-consistency.json`.

Com `--fix` ela normaliza o que é mecânico (converte IDs textuais em objetos, resolve `bc_name` pelo
`bounded-context-map.md`, absorve e remove `bc_details`, preenche `wave_number`/`tshirt`/`depends_on_waves`,
corrige `total_waves`, promove `metadata.project_name`). O que exige julgamento — 7.5.2, 7.5.3, 7.5.8 — ela
**reprova e nomeia**, e a correção volta para o Step 4.7 do agente.

> **Se qualquer verificação falhar**: BLOQUEIO. Corrigir o `wave-model.json` **primeiro** (SSoT, G-17),
> regenerar os artefatos derivados a partir dele, e reexecutar as Etapas 7 e 7.5 até `status: ok`.
> Nunca ajustar o `wave-plan.md` para "casar" com um modelo incorreto.

---

## Formato do Relatório de Completude (obrigatório antes de encerrar)

O agente DEVE gerar este relatório inline antes de declarar o plano concluído:

```
## Relatório de Completude — Output Contract

| # | Arquivo | Status | Observação |
|---|---|---|---|
| 1 | wave-model.json | ✅ OK | — |
| 2 | integration-matrix.md | ✅ OK | — |
| 3 | tshirt-sizing-rationale.md | ✅ OK | — |
| 4 | ai-estimation-report.md | ✅ OK | — |
| 5 | manual-gap-list.md | ✅ OK | — |
| 6 | migration-executive-summary.md | ✅ OK | — |
| 7 | migration-plan.md | ✅ OK | — |
| 8 | wave-plan.md | ✅ OK | — |
| 9 | ado-work-items.md | ✅ OK | — |
| 10 | migration-gantt.mmd | ✅ OK | — |
| 11 | migration-activity-plan.md | ✅ OK | — |
| 12 | activity-dependency-graph.md | ✅ OK | — |
| 13 | migration-priority-matrix.md | ✅ OK | — |

**Resultado**: 13/13 arquivos presentes e com conteúdo. Plano de migração CONCLUÍDO.
```

> Se qualquer arquivo tiver status `❌ FALTANDO` ou `⚠️ VAZIO` → substituir "CONCLUÍDO" por "BLOQUEADO"; listar os arquivos pendentes e gerar ou solicitar geração antes de encerrar.
> **Nota**: O `backlog-tobe.md` é verificado separadamente na Etapa 5.5 como input herdado da Fase 2.5 do orquestrador.

---

## Output Invariant — Completion Report

A ÚLTIMA coisa emitida pela execução da Validation Gate DEVE ser o **Relatório de Completude** com todas as **13 linhas** preenchidas.

- **(1)** O relatório DEVE ser gerado a partir de **leituras reais em disco** (`Read` / `file_exists`) — proibido populá-lo a partir de memória, cache ou variáveis internas. Cada linha do relatório reflete o estado físico do arquivo no filesystem no momento da verificação.
- **(2)** Todas as **13 linhas** do checklist são **OBRIGATÓRIAS** e **indivisíveis** — emitir relatório parcial (< 13 linhas) ou omitir linhas com falha = violação do invariante.
- **(3)** SE resultado `< 13/13 OK` → emitir `DECISION: BLOCKED` e **interromper imediatamente**. Proibido declarar a fase concluída, avançar para o próximo agente ou emitir qualquer output adicional além da lista de arquivos pendentes.
- **(4)** SE resultado `= 13/13 OK` → emitir `DECISION: PROCEED` e **somente então** declarar a fase concluída.
- **(5)** Nenhum gatilho, instrução do usuário ou contexto de projeto pode suspender, adiar ou substituir a emissão do Relatório de Completude como bloco terminal da Validation Gate.
