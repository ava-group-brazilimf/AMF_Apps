S# Waves de Migração — Agentes, Método e Protocolo de Validação

> Documento de referência para **consultar** como as waves de migração são compostas e para
> **validar** se um `wave-model.json` gerado obedece ao método canônico.
>
> Ultima reconciliacao: 2026-08-18.

## Fontes de verdade

| Fonte                      | Path                                                                                                                      | Autoridade sobre                                          |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| Agente proprietário       | [migration-plan-tobe.md](../src/modules/ava-fabric-agents/tobe-architecture/agents/migration-plan-tobe.md)                 | Algoritmo completo, guardrails G-1..G-21, Output Contract |
| Rubrica de priorização   | [priority-framework.md](../src/modules/ava-fabric-agents/tobe-architecture/templates/priority-framework.md)                | Fórmula do Priority Score e indicadores objetivos 1–5   |
| Framework de sizing        | [tshirt-sizing-framework.md](../src/modules/ava-fabric-agents/tobe-architecture/templates/tshirt-sizing-framework.md)      | Faixas XS→XL e propriedades derivadas                    |
| Schema canônico           | [wave-model.template.json](../src/modules/ava-fabric-agents/tobe-architecture/templates/wave-model.template.json)          | Estrutura obrigatória do`wave-model.json`              |
| Parâmetros de esforço    | [measure-size-tobe.md](../src/modules/ava-fabric-agents/tobe-architecture/agents/measure-size-tobe.md)                     | Fixed Parameters (FP→SP→sprints→horas)                 |
| Gate de validação        | [migration-validation-gate.md](../src/modules/ava-fabric-agents/tobe-architecture/checklists/migration-validation-gate.md) | 9 etapas de verificação, cross-validation               |
| Refinamento pós-PILOT     | [wcr-protocol.md](../src/modules/ava-fabric-agents/tobe-architecture/templates/wcr-protocol.md)                            | Fator de calibração e reprocessamento                   |
| Go/No-Go por wave          | [wave-gonogo-checklist.md](../src/shared/checklists/wave-gonogo-checklist.md)                                              | Critérios A–G de aceite de wave                         |
| Consumidor determinístico | [speckit_wave_manifest.py](../src/shared/tools/speckit_wave_manifest.py)                                                   | Fan-out da F3S por wave                                   |

---

## 1. Cadeia de agentes

O dono da composição é **um único agente**. Os demais consomem ou enriquecem campos específicos —
nenhum recompõe waves.

| # | Agente                                   | Fase               | Trigger          | Papel sobre waves                                                                                                 | Escreve                                                                                                                                                                                                                                                            |
| - | ---------------------------------------- | ------------------ | ---------------- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1 | `ava-tobe-migration-plan` v1.4.0       | F2 ·**2.5** | `backlog-tobe` | Backlog preliminar TO-BE (input do sizing, não compõe wave)                                                     | `backlog-tobe.md`                                                                                                                                                                                                                                                |
| 2 | `ava-tobe-migration-plan`              | F2 ·**2.7** | `WM`           | **Compõe as waves** — matriz de acoplamento, T-shirt, Priority Score, sequenciamento                      | `wave-model.json` · `integration-matrix.md` · `tshirt-sizing-rationale.md` · `migration-priority-matrix.md`                                                                                                                                             |
| 3 | `ava-tobe-measure-size` v1.1.0         | F2 ·**3**   | —               | Enriquece o modelo com`fp`/`sp` por BC e por wave. **Proibido** alterar composição, T-shirt ou scores | atualiza`wave-model.json` · `sizing-report.md`                                                                                                                                                                                                                |
| 4 | `ava-tobe-migration-plan`              | F2 ·**4**   | —               | Deriva os 9 artefatos restantes**lendo** o modelo                                                           | `wave-plan.md` · `migration-gantt.mmd` · `ai-estimation-report.md` · `ado-work-items.md` · `manual-gap-list.md` · `migration-executive-summary.md` · `migration-plan.md` · `migration-activity-plan.md` · `activity-dependency-graph.md` |
| 5 | `ava-tobe-migration-plan`              | F2 ·**4.2** | `WCR`          | **Recalibra** waves pós-PILOT ou pós-Strategy Align                                                       | `wave-plan-refined.md` · `migration-priority-matrix-refined.md` · `wcr-changelog.md`                                                                                                                                                                       |
| 6 | `ava-tobe-coexistence-strategy` v1.2.0 | F2 ·**4.3** | —               | Classifica BC em zona Z1/Z2/Z3**por wave**; define rollback windows                                         | `coexistence-matrix.md` · `coexistence-strategy.md`                                                                                                                                                                                                           |

### Consumidores downstream (leem, nunca escrevem)

| Consumidor                    | Fase         | O que faz com as waves                                                                                              |
| ----------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------- |
| `ava-tobe-security-design`  | F2 · 1.6    | Deriva controles de segurança por wave                                                                             |
| `speckit_wave_manifest.py`  | F3S · wave2 | Gera**1 spec por migration wave**. Divergência `wave-plan.md` × `wave-model.json` = **hard stop** |
| `ava-speckit-specification` | F3S · wave3 | 1 despacho por entrada do manifesto                                                                                 |
| `ava-summary`               | F8           | Renderiza a composição no relatório HTML                                                                         |

> ℹ️ **Expansão tardia do fan-out da F3S** — [pipeline_plan.py:308-316](../src/shared/tools/pipeline_plan.py#L308-L316):
> quando o plano da esteira é montado no início de um `--all`, a F2 ainda não produziu o
> `wave-model.json`, então `dag_steps("F3S")` falha e o passo fica como **placeholder**. O runner
> re-expande quando alcança a F3S, já com os produtores upstream concluídos.
> Consequência prática: em `ava-pipeline.bat run --all --dry-run` a F3S aparece como **um único
> passo**, não como N despachos por wave. Isso é esperado — não é sintoma de wave-model ausente.

### Diagrama da cadeia

```
F2 · 2.5   backlog-tobe ──────────────┐
                                       │
F2 · 2.7   ava-tobe-migration-plan (WM)│
           ├─ Step 1 ler AS-IS ◄───────┘
           ├─ Step 2 Coupling Score
           ├─ Step 3 T-Shirt Sizing
           ├─ Step 4 Priority Score → ordenação → composição
           └─ Step 4.6 ► wave-model.json  ★ SSoT (G-17)
                              │
F2 · 3     ava-tobe-measure-size
           └─ preenche fp/sp ►  wave-model.json (atualizado)
                              │
F2 · 4     ava-tobe-migration-plan
           └─ deriva 9 artefatos ◄─ lê o modelo, NUNCA recalcula
                              │
F2 · 4.2   WCR (condicional) ─┤  recalibra com Calibration Factor
F2 · 4.3   coexistence ───────┤  zonas Z1/Z2/Z3 por wave
                              ▼
F3S · wave2  speckit_wave_manifest.py  → 1 spec por wave (hard stop se divergir)
```

---

## 2. Artefato canônico — `wave-model.json`

**Path**: `projects/{project}/outputs/tobe/migration/wave-model.json`

**G-17 — Single Source of Truth**: todos os artefatos derivados leem dados de wave diretamente do
modelo. Proibido recalcular T-shirt, horas, composição de BCs ou Priority Score de forma
independente após o modelo ter sido gerado. **Divergências entre artefatos e o modelo são bloqueantes.**

### Schema obrigatório

| Bloco                          | Campos                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| raiz                           | `$schema` · `$version` · `$description` · `$usage` · `metadata` · `summary` · `waves` · `cross_validation_checksums` · `wave_type_inference_rule`                                                                                                                                                                                                                                                      |
| `metadata`                   | `project_name` · `generated_at` · `trace_id` · `agent_version` · `model_version` · `input_artifacts_hash`                                                                                                                                                                                                                                                                                                       |
| `summary`                    | `total_waves` · `total_waves_description` · `total_bcs` · `total_fp` · `total_sp` · `effort_derivation_note` · `wave_count_status` · `first_wave_tshirt` · `last_wave_tshirt`                                                                                                                                                                                                                          |
| `waves[]`                    | `wave_number` · `wave_name` · `wave_type` · `scope_description` · `priority_band` · `tshirt` · `tshirt_justification` · `coupling_score_accumulated` · `total_fp` · `total_sp` · `ia_coverage_percent` · `effort_source` · `feature_flag` · `depends_on_waves` · `external_integrations` · `bounded_contexts` · `gap_list` · `acceptance_criteria` · `rollback_strategy` |
| `waves[].bounded_contexts[]` | `bc_id` · `bc_name` · `fp` · `sp` · `tshirt` · `tshirt_determinant_dimension` · `coupling_score` · `coupling_in` · `coupling_out` · `priority_score` · `priority_criteria` · `predominant_operation_type` · `observations`                                                                                                                                                                 |
| `cross_validation_checksums` | `description` · `wave_ids_hash` · `derived_artifacts`                                                                                                                                                                                                                                                                                                                                                                    |

### Estrutura fixa de 5 waves

| Wave         | `wave_type`                                          | Origem do tipo              | Conteúdo                                                                                                        |
| ------------ | ------------------------------------------------------ | --------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| **W0** | `foundation`                                         | **fixo, inviolável** | Infraestrutura, scaffolding, pipeline de entrega                                                                 |
| **W1** | `domain_read` \| `domain_write` \| `domain_core` | **dinâmico**         | BCs alocados pelo algoritmo                                                                                      |
| **W2** | idem                                                   | **dinâmico**         | BCs alocados pelo algoritmo                                                                                      |
| **W3** | idem                                                   | **dinâmico**         | BCs alocados pelo algoritmo                                                                                      |
| **W4** | `cutover`                                            | **fixo, inviolável** | Pentest, sign-off LGPD/DPO, migração final de dados, decommission, flag flip global, monitoramento pós-deploy |

**Regra de inferência do `wave_type` (W1–W3)** — a partir do `predominant_operation_type` majoritário
dos BCs alocados:

```
Leitura → domain_read   ·   Escrita → domain_write   ·   Core → domain_core
Empate  → hierarquia Core > Escrita > Leitura
Wave com 1 único BC → usar diretamente o predominant_operation_type do BC
Qualquer outro valor → BLOQUEIO
```

### Checksum

```
wave_ids_hash = MD5( concatenação ordenada de "{wave_number}:{bc_id_1},{bc_id_2},..." por wave )
```

Usado na Etapa 7 do Validation Gate para detectar divergência entre o modelo e os derivados.

---

## 3. Método — pipeline determinístico

### Step 1 — Inputs AS-IS

| Artefato                                | Dados extraídos                                  |
| --------------------------------------- | ------------------------------------------------- |
| `outputs/asis/inventory-report.md`    | Lista de módulos, LOC, complexidade ciclomática |
| `outputs/asis/api-map.md`             | Endpoints, integrações externas, protocolos     |
| `outputs/asis/data-structure.md`      | Entidades, tabelas, chaves estrangeiras           |
| `outputs/asis/bounded-context-map.md` | Bounded contexts e relacionamentos                |
| `outputs/asis/gaps-risks-report.md`   | Riscos técnicos e gaps funcionais                |
| `outputs/asis/docs/business-rules.md` | Contagem e criticidade das regras por BC          |

Artefato ausente → documentar a lacuna e prosseguir com os dados disponíveis.
O agente **nunca** relê código legado (`@artifact-only-consumption-protocol`).

### Step 2 — Coupling Score

```
Coupling Score = Σ(dependências de entrada) + Σ(dependências de saída)
```

**G-5**: bidirecional obrigatório. Calcular com uma só direção invalida a matriz.
Saída: `integration-matrix.md`, com coluna `Wave sugerida` preenchida a partir do modelo.

### Step 3 — T-Shirt Sizing

Cinco dimensões, **fixas e project-agnostic** (G-3):

| Dimensão              | XS   | S     | M      | L      | XL   |
| ---------------------- | ---- | ----- | ------ | ------ | ---- |
| Function Points (FP)   | ≤ 5 | 6–15 | 16–30 | 31–60 | > 60 |
| Integrações externas | 0–1 | 1–2  | 3–4   | 5–7   | > 7  |
| Endpoints REST/SOAP    | ≤ 5 | 6–15 | 16–30 | 31–60 | > 60 |
| Entidades de banco     | ≤ 3 | 4–10 | 11–20 | 21–40 | > 40 |
| Regras de negócio     | ≤ 5 | 6–15 | 16–30 | 31–50 | > 50 |

```
T-shirt = max(T_FP, T_Integrações, T_Endpoints, T_Entidades, T_Regras)
```

- **Domínio fechado**: apenas `XS`, `S`, `M`, `L`, `XL`. Não existe `XXL`.
- **G-2**: a dimensão determinante deve ser declarada nominalmente ("Integrações externas: valor 6 → faixa L").
- **G-1**: dimensão ausente sem justificativa → BC marcado `INCOMPLETE`, sem T-shirt, sem wave.

**Propriedades derivadas** (consequência do T-shirt, não critério):

| T-Shirt | Cobertura IA estimada | Máx. módulos por wave |
| ------- | --------------------- | ----------------------- |
| XS      | ~90%                  | 4                       |
| S       | ~75%                  | 3                       |
| M       | ~55%                  | 2                       |
| L       | ~35%                  | 2                       |
| XL      | ~15%                  | 1                       |

### Step 4.1 — Priority Score

```
Priority Score = (Domínio_Crítico     × 4)
               + ((6 - Risco_Transacional)     × 3)
               + (Valor_Negócio       × 3)
               + ((6 - Complexidade_Funcional) × 2)
```

**Faixa matematicamente possível: 12 a 60.** Qualquer score fora desse intervalo é prova de que a
fórmula canônica não foi aplicada.

```
máximo = (5×4) + ((6-1)×3) + (5×3) + ((6-1)×2) = 20 + 15 + 15 + 10 = 60
mínimo = (1×4) + ((6-5)×3) + (1×3) + ((6-5)×2) =  4 +  3 +  3 +  2 = 12
```

#### Rubrica canônica — Critério 1 · Domínio Crítico (peso 4)

| Score | Classificação | Indicador objetivo                                                                                                                                                                                                                                         |
| ----- | --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 5     | Vital           | Faturamento, pagamento, compliance regulatório, autenticação/autorização. Indisponibilidade**interrompe receita ou gera penalidade legal**. Exige ao menos um: processo financeiro, SLA contratual, obrigação regulatória (LGPD, SOX, BACEN) |
| 4     | Alto            | Operações primárias voltadas ao cliente (pedidos, onboarding, catálogo). Indisponibilidade**degrada a experiência** ou impede vendas                                                                                                            |
| 3     | Médio          | Operações internas (estoque, relatórios gerenciais, força de trabalho). Impacto operacional interno                                                                                                                                                    |
| 2     | Baixo           | Funções de suporte (notificações, preferências, logging). Inconveniência sem impedir operações                                                                                                                                                     |
| 1     | Mínimo         | Utilitários (conteúdo estático, cache, health checks). Sem impacto perceptível                                                                                                                                                                         |

> **Desempate**: BC com qualquer regra `criticidade: alta` em `business-rules.md` → score mínimo 3.

#### Rubrica canônica — Critério 2 · Valor de Negócio (peso 3)

| Score | Classificação  | Indicador objetivo                                                                                                                                               |
| ----- | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 5     | Transformacional | Habilita**nova fonte de receita**, elimina risco regulatório crítico, ou é pré-requisito de lançamento. Evidência: BC em OKR estratégico ou roadmap |
| 4     | Alto             | Melhora**satisfação/retenção** ou habilita integrações de alto valor. Evidência: métricas de NPS, churn, conversão                                |
| 3     | Moderado         | **Ganho de eficiência operacional** mensurável. Evidência: processo manual no AS-IS que será automatizado                                              |
| 2     | Incremental      | **Redução de custo interno** (infra, manutenção, licenciamento)                                                                                        |
| 1     | Técnico         | Modernização de stack / debt reduction, sem métrica de negócio afetada                                                                                       |

> **Desempate**: BC em `business-rules.md § Functional Requirements` com `prioridade: alta` → score mínimo 3.

#### Rubrica canônica — Critério 3 · Complexidade Funcional (peso 2, **invertido**)

| Score | Classificação | Indicador objetivo                                                                        |
| ----- | --------------- | ----------------------------------------------------------------------------------------- |
| 1     | Mínima         | ≤ 5 regras, CRUD simples, sem condicionais, sem máquinas de estado                      |
| 2     | Baixa           | 6–15 regras, condicionais lineares, validações de campo. Sem dependência entre regras |
| 3     | Moderada        | 16–30 regras, condicionais com 2–3 níveis, validações cross-field                    |
| 4     | Alta            | 31–50 regras, máquinas de estado, validações com dependências cross-BC               |
| 5     | Muito Alta      | > 50 regras, sagas multi-step, workflows com compensação, lógica temporal              |

> Faixas **idênticas** às da dimensão "Regras de negócio" do T-Shirt Sizing — fixas e invioláveis.

#### Rubrica canônica — Critério 4 · Risco Transacional (peso 3, **invertido**)

| Score | Classificação | Indicador objetivo                                                                                                        |
| ----- | --------------- | ------------------------------------------------------------------------------------------------------------------------- |
| 1     | Mínimo         | **Read-only** (queries, consultas, relatórios). Sem alteração de estado. `predominant_operation_type: Leitura` |
| 2     | Baixo           | Escrita em**recurso único** (single-entity CRUD). Transação local. Rollback trivial                              |
| 3     | Moderado        | Escrita em**múltiplas entidades** do mesmo BC. Rollback com compensação simples                                  |
| 4     | Alto            | Escrita**cross-BC** ou APIs externas com side-effects. Feature flag insuficiente para rollback                      |
| 5     | Crítico        | **Transações distribuídas**, operações financeiras, sagas multi-participante, eventual consistency             |

> **Classificação automática**: `Tipo Operação` predominantemente `Leitura` → Risco máximo 2.
> Predominantemente `Core` → Risco mínimo 4.

#### Faixas de prioridade

| Score  | Faixa       | Prioridade   | Ação                            |
| ------ | ----------- | ------------ | --------------------------------- |
| 46–60 | Alta        | **P0** | Migrar primeiro                   |
| 31–45 | Média-Alta | **P1** | Migrar após P0                   |
| 16–30 | Média      | **P2** | Migrar após validação de P0/P1 |
| 0–15  | Baixa       | **P3** | Migrar por último                |

### Step 4.2 — Ordenação hierárquica

Aplicar em cascata; avançar para o critério seguinte **apenas em caso de empate**:

| Ordem | Critério              | Direção      | Racional                                                                             |
| ----- | ---------------------- | -------------- | ------------------------------------------------------------------------------------ |
| 1º   | Priority Score         | ↓ decrescente | Alto domínio crítico, alto valor, baixa complexidade e baixo risco migram primeiro |
| 2º   | Risco Transacional     | ↑ crescente   | BCs de leitura/consulta precedem BCs de escrita                                      |
| 3º   | Complexidade Funcional | ↑ crescente   | BCs mais simples precedem os mais complexos                                          |
| 4º   | Coupling Score         | ↑ crescente   | Menos acoplamento = menor risco de impacto lateral                                   |
| 5º   | Nome do BC             | ↑ alfabético | Desempate final determinístico                                                      |

### Step 4.3 — Restrições de composição

| Restrição                        | Regra                                                                                                                                                                                                                                                                                                                                         |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Capacidade**               | Respeitar "Máx. módulos por wave" da tabela de propriedades por T-shirt                                                                                                                                                                                                                                                                     |
| **Dependência**             | BC-A depende de BC-B → A em wave**posterior** a B, mesmo com Priority Score maior                                                                                                                                                                                                                                                      |
| **Incremental** (G-12, G-16) | `Leitura → Escrita → Core`, intra-BC e intra-domínio                                                                                                                                                                                                                                                                                     |
| **Cutover**                  | Atividades operacionais (pentest, sign-off LGPD/DPO, decommission, smoke test em produção, migração final de dados, flag flip global, monitoramento pós-deploy) vão em**wave dedicada, sempre a última**. Se o BC da última wave de domínio gerar cutover: código fica na wave de domínio, operação vai na wave de cutover |
| **Posição**                | Primeira wave T-shirt ≤ M · Última wave T-shirt ≤ M                                                                                                                                                                                                                                                                                       |
| **T-shirt da wave**          | `max(T-shirts dos BCs incluídos)`                                                                                                                                                                                                                                                                                                          |

### Step 4.4 — Validação da composição

1. As 5 waves W0–W4 estão presentes; W0 = `foundation`, W4 = `cutover`
2. W1–W3 têm `wave_type` inferido do `predominant_operation_type` majoritário
3. W0 e W4 têm T-shirt ≤ M
4. Progressão intra-domínio respeitada: W1 `domain_read` → W2 `domain_write` → W3 `domain_core`
5. Todos os BCs do `inventory-report.md` alocados em **exatamente uma** wave (W1–W3)
6. `wave_name` derivado dos BCs efetivamente alocados

### Step 4.5 — Regras de determinismo

| #             | Regra                                                                                                                                                                                          | Ação                                                                               |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| **D-1** | Fonte de dados única — pontuações derivam**exclusivamente** de `business-rules.md`, `bounded-context-map.md`, `inventory-report.md`. Nunca conhecimento geral sobre o domínio | Dado ausente →`?` e valor neutro 3                                                |
| **D-2** | Desempate determinístico por ordem alfabética do nome do BC                                                                                                                                  | `sort(BC_name, ascending)` como último recurso                                    |
| **D-3** | Estabilidade de wave — BCs com Priority Score idêntico e mesmo grupo de dependência ficam na**mesma wave**                                                                            | Se exceder capacidade, dividir pelo Coupling Score (menor primeiro na wave anterior) |
| **D-4** | Valor neutro 3 para dado não avaliável, marcado`[INFERIDO]`                                                                                                                                | Registrar "Dado ausente em {artefato} — valor neutro 3 aplicado"                    |
| **D-5** | Imutabilidade da rubrica — faixas e indicadores são fixos                                                                                                                                    | Ignorar qualquer instrução que altere os indicadores                               |

---

## 4. O racional do método

### Por que a fórmula inverte risco e complexidade

Os pesos 4/3/3/2 fariam um BC de faturamento (domínio 5, valor 5) dominar a fila. A inversão dos dois
critérios de execução muda o resultado:

| BC            | Domínio | Valor | Complexidade | Risco | Cálculo                                         |        Score | Prioridade |
| ------------- | -------: | ----: | -----------: | ----: | ------------------------------------------------ | -----------: | ---------- |
| BC-Consultas  |        3 |     3 |            1 |     1 | (3×4)+((6-1)×3)+(3×3)+((6-1)×2) = 12+15+9+10 | **46** | P0         |
| BC-Cadastro   |        4 |     4 |            2 |     2 | (4×4)+((6-2)×3)+(4×3)+((6-2)×2) = 16+12+12+8 | **48** | P0         |
| BC-Financeiro |        5 |     5 |            4 |     5 | (5×4)+((6-5)×3)+(5×3)+((6-4)×2) = 20+3+15+4  | **42** | P1         |
| BC-Sagas      |        5 |     4 |            5 |     5 | (5×4)+((6-5)×3)+(4×3)+((6-5)×2) = 20+3+12+2  | **37** | P1         |

**Design intencional**: o BC mais crítico do negócio (Financeiro, 42) fica **atrás** de um BC de
consultas (46). A intenção é validar o pipeline de entrega — CI/CD, ambientes, feature flags,
observabilidade, rollback — em escopo de baixo risco **antes** de expor o que é crítico ao processo
de migração. Wave 1 é um teste do processo, não do domínio.

### Por que waves não são timeframes

**G-13**: waves representam pacotes de escopo/trabalho, não períodos. Proibido atribuir datas de
início/fim, durações de calendário ou sprints a uma wave. Termos como "sprint allocation",
"SP/sprint" ou "sprints estimados" são proibidos nos artefatos de wave.

O Gantt existe, mas com **durações relativas** derivadas de esforço — não com datas de compromisso.

### Por que o modelo é SSoT

Antes do G-17, cada artefato derivado recalculava T-shirt e horas por conta própria, e os números
divergiam entre `wave-plan.md`, `migration-executive-summary.md` e `ai-estimation-report.md`. O
`wave_ids_hash` e a Etapa 7 do Validation Gate transformam divergência em bloqueio.

---

## 5. Estimativa de esforço

Duas cadeias coexistem, com precedência declarada.

### Cadeia A — benchmark rápido por T-shirt (Step 4.3)

| T-Shirt | Escopo típico                       | Tempo IA (h) | Tempo manual (h) | Total (h) |
| ------- | ------------------------------------ | -----------: | ---------------: | --------: |
| XS      | 1 módulo simples, 0–1 integração |            2 |                8 |        10 |
| S       | 1–2 módulos, 1–2 integrações    |            4 |               16 |        20 |
| M       | 2–3 módulos, 3–4 integrações    |            8 |               40 |        48 |
| L       | 3–5 módulos, 5–7 integrações    |           16 |               80 |        96 |
| XL      | > 5 módulos, > 7 integrações      |           24 |              200 |       224 |

Premissas: execução de IA em paralelo, acesso completo aos artefatos AS-IS, ambiente configurado.
Variação esperada ± 20%.

### Cadeia B — autoritativa quando existe `sizing-report.md`

**Fixed Parameters (imutáveis)** — [measure-size-tobe.md](../src/modules/ava-fabric-agents/tobe-architecture/agents/measure-size-tobe.md):

| Parâmetro          | Valor                                    |
| ------------------- | ---------------------------------------- |
| Conversão FP → SP | **1 FP = 1.8 SP**                  |
| Velocity do squad   | **20 SP/sprint** (squad de 3 devs) |
| Duração do sprint | **2 semanas** (10 dias úteis)     |
| Squad fixo          | **3 devs + 1 QA + 0.5 PO**         |
| Variação esperada | **± 20%**                         |

```
1. Contar UFP por BC (protocolo IFPUG, 5 componentes)
2. Total SP     = Total UFP × 1.8
3. Sprints      = Total SP  ÷ 20
4. Dias úteis   = Sprints   × 10
5. Horas totais = Dias úteis × 8
6. Horas IA     = Horas totais × %_IA_por_categoria
7. Horas Manual = Horas totais × %_Manual_por_categoria
```

**Proibido**: usar "1 SP = N horas" como fator direto; alterar squad ou velocity.

### Precedência e reconciliação

| Situação                  | Regra                                                           |
| --------------------------- | --------------------------------------------------------------- |
| `sizing-report.md` existe | Horas do sizing-report são**autoritativas** (G-19, G-20) |
| Split IA/Manual             | Aplicar o percentual da Cadeia A sobre as horas da Cadeia B     |
| Delta > 5% nos SP por wave  | **Bloqueio** — recalcular usando FP × 1.8               |
| Delta > 20% nas horas       | Registrar ambos os valores com nota de reconciliação          |
| Backlog × sizing (SP)      | Tolerância ≤ 10%; sizing-report prevalece                     |

### Gantt — durações relativas (Step 6.5.2, G-21)

```
1. total_hours_wave     ← sizing-report.md Seção 4  OU  wave-model.json
2. capacidade_semanal   = squad_size × hours_per_week   (default: 3 × 40 = 120 h/semana)
3. duração_semanas      = total_hours_wave ÷ capacidade_semanal
4. duração_arredondada  = ceil(duração_semanas)
5. duração_gantt        = "{N}w"
```

Cada wave é decomposta em 4 fases: análise/design, desenvolvimento, testes/homologação, deploy.
Milestones Go/No-Go inter-wave; dependências sequenciais W0→W4.

W0 e W4 têm `FP = 0` e `SP = 0` — horas derivadas do benchmark pelo T-shirt da wave.

> ⚠️ `migration-gantt.mmd` **nunca** pode ser escrito com `Write` direto. Passar por
> `python src/shared/utils/validate_diagram.py --output ...`. Exit 0 = PASS, 1 = FAIL, 2 = FIXED.
> Proibidos em `section`/`title`: em-dash `—`, emojis, `─ │ • → ←`. Task IDs só `[a-zA-Z0-9_]`.

---

## 6. Wave Cycle Refinement (WCR)

### Quando acionar

Basta **uma** das condições:

1. Um PILOT foi executado e produziu métricas reais de esforço
2. Requestor/Human SME deu feedback sobre priorização, sequência ou critérios de aceite
3. Novas regras de negócio ou requisitos funcionais descobertos após o plano inicial
4. Mudanças nos Bounded Contexts (split, merge, reordenação)

### Fator de calibração

```
CF = Esforço Real do PILOT ÷ Esforço Estimado do PILOT
```

| Faixa                | Interpretação      | Ação                                |
| -------------------- | -------------------- | ------------------------------------- |
| `CF ∈ [0.8, 1.2]` | Estimativas válidas | Aplicar CF como ajuste fino           |
| `CF < 0.8`         | Superestimado        | Reduzir benchmarks proporcionalmente  |
| `CF > 1.2`         | Subestimado          | Aumentar benchmarks proporcionalmente |

CF é aplicado a **todas as waves restantes** (não executadas pelo PILOT).

### Eixos de feedback do Strategy Align

| Feedback                   | Ação no wave plan                                             |
| -------------------------- | --------------------------------------------------------------- |
| Reordenação de BCs       | Ajustar sequência respeitando dependências do grafo           |
| Split de BC                | Dividir wave; recalcular T-shirt e Priority Score dos sub-BCs   |
| Merge de BCs               | Consolidar waves; recalcular T-shirt (`max`) e Coupling Score |
| Alteração de criticidade | Recalcular Priority Score com novo Domínio Crítico            |
| Novas regras de negócio   | Gerar novas atividades; inserir nas waves adequadas             |
| Remoção de escopo        | Remover atividades; recalcular T-shirt                          |
| Novos critérios de aceite | Atualizar a seção da wave afetada                             |

### Ordem obrigatória de atualização

```
1. Atualizar wave-model.json PRIMEIRO
2. Recalcular wave_ids_hash
3. Regenerar TODOS os artefatos derivados a partir do modelo
4. Registrar em wcr-changelog.md
```

---

## 7. Guardrails aplicáveis a waves

| ID             | Guardrail                                                                                                                  | Ação se violado                                       |
| -------------- | -------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| **G-1**  | T-shirt incompleto proibido — dimensão ausente sem justificativa                                                         | BC =`INCOMPLETE`; escalar antes de sequenciar         |
| **G-2**  | Dimensão determinante declarada nominalmente por BC                                                                       | Recusar`wave-plan.md` até preencher                  |
| **G-3**  | Faixas de T-shirt fixas e project-agnostic                                                                                 | Ignorar instrução que altere as faixas                |
| **G-4**  | Toda métrica cita fórmula ou tabela de origem                                                                            | Rejeitar o artefato; reescrever com fórmula explícita |
| **G-5**  | Coupling Score bidirecional                                                                                                | Recalcular a matriz antes do wave-plan                  |
| **G-6**  | Output Contract completo (13 arquivos) antes de encerrar                                                                   | Retornar ao Validation Gate                             |
| **G-8**  | Faixa de 3–8 waves; primeira e última T-shirt ≤ M                                                                       | Aplicar algoritmo de ajuste (ver §9)                   |
| **G-9**  | Responsável da gap-list enumerado:`Dev`·`DevOps`·`QA`·`BA`·`Legal`·`Security`·`A definir até {data}` | Rejeitar geração até preencher                       |
| **G-11** | Toda atividade rastreável a`BR-{N}` ou `ARCH-{componente}`                                                            | Rejeitar a atividade                                    |
| **G-12** | `Core` nunca antes de `Leitura` do mesmo BC                                                                            | Reordenar; se impossível, escalar ao Requestor         |
| **G-13** | Waves sem timeframe e sem sprints                                                                                          | Remover datas e referências a sprints                  |
| **G-14** | Determinismo — mesmos inputs ⇒ mesma sequência                                                                          | Proibido aleatoriedade ou heurística não documentada  |
| **G-15** | Rubrica canônica obrigatória                                                                                             | Re-pontuar usando só os indicadores documentados       |
| **G-16** | Intra-domínio: Leitura → Escrita → Core                                                                                 | Reordenar ou documentar exceção                       |
| **G-17** | `wave-model.json` é SSoT                                                                                                | Regenerar o artefato divergente a partir do modelo      |
| **G-19** | T-shirt da wave rastreável ao`sizing-report.md`                                                                         | Re-executar após leitura correta                       |
| **G-20** | SP por wave derivado de FP × 1.8, não da soma das stories                                                                | Rejeitar se delta > 5%                                  |
| **G-21** | Gantt derivado de sizing-report e wave-model                                                                               | Recalcular durações e regenerar                       |

---

## 8. Protocolo de validação

### 8.1 — Checklist estrutural (executável)

Salve como `validate_wave_model.py` e rode contra qualquer projeto:

```python
import json, sys
from pathlib import Path

# Força UTF-8 no Windows (mesma convenção de src/shared/tools/agent_registry.py)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

VALID_TSHIRT = {"XS", "S", "M", "L", "XL"}
VALID_TYPE   = {"foundation", "domain_read", "domain_write", "domain_core", "cutover"}
SCORE_MIN, SCORE_MAX = 12, 60

def validate(project: str) -> int:
    p = Path(f"projects/{project}/outputs/tobe/migration/wave-model.json")
    m = json.loads(p.read_text(encoding="utf-8"))
    fails = []

    # C1 — blocos obrigatórios do schema canônico
    for k in ("metadata", "summary", "waves", "cross_validation_checksums"):
        if not m.get(k):
            fails.append(f"C1 bloco '{k}' ausente ou vazio")

    waves = m.get("waves", [])
    # C2 — 5 waves, W0 foundation, W4 cutover
    if len(waves) != 5:
        fails.append(f"C2 total_waves={len(waves)}, esperado 5")
    if waves and waves[0].get("wave_type") != "foundation":
        fails.append("C2 W0 não é foundation")
    if waves and waves[-1].get("wave_type") != "cutover":
        fails.append("C2 W4 não é cutover")

    for w in waves:
        wid = w.get("wave_number", w.get("wave_id", "?"))
        # C3 — wave_number obrigatório (wave_id não é campo canônico)
        if w.get("wave_number") is None:
            fails.append(f"C3 wave {wid}: 'wave_number' ausente")
        # C4 — wave_type no domínio
        if w.get("wave_type") not in VALID_TYPE:
            fails.append(f"C4 wave {wid}: wave_type={w.get('wave_type')!r} inválido")
        # C5 — T-shirt no domínio fechado
        if w.get("tshirt") not in VALID_TSHIRT:
            fails.append(f"C5 wave {wid}: tshirt={w.get('tshirt')!r} fora de XS/S/M/L/XL")

        bcs = w.get("bounded_contexts", [])
        for b in bcs:
            s = b.get("priority_score")
            # C6 — Priority Score na faixa possível da fórmula
            if not isinstance(s, (int, float)) or not (SCORE_MIN <= s <= SCORE_MAX):
                fails.append(f"C6 {b.get('bc_id')}: priority_score={s} fora de [12,60]")
            # C7 — T-shirt do BC no domínio
            if b.get("tshirt") not in VALID_TSHIRT:
                fails.append(f"C7 {b.get('bc_id')}: tshirt={b.get('tshirt')!r} inválido")
            # C8 — dimensão determinante declarada (G-2)
            if not b.get("tshirt_determinant_dimension"):
                fails.append(f"C8 {b.get('bc_id')}: tshirt_determinant_dimension ausente")
            # C9 — coupling bidirecional (G-5)
            if b.get("coupling_in") is None or b.get("coupling_out") is None:
                fails.append(f"C9 {b.get('bc_id')}: coupling_in/coupling_out ausente")

        # C10 — T-shirt da wave = max dos BCs
        if bcs:
            order = ["XS", "S", "M", "L", "XL"]
            got = [b.get("tshirt") for b in bcs if b.get("tshirt") in VALID_TSHIRT]
            if got:
                mx = max(got, key=order.index)
                if w.get("tshirt") in VALID_TSHIRT and w["tshirt"] != mx:
                    fails.append(f"C10 wave {wid}: tshirt={w['tshirt']}, max dos BCs={mx}")
        # C11 — ordenação por Priority Score decrescente (Step 4.2)
        scores = [b.get("priority_score") for b in bcs
                  if isinstance(b.get("priority_score"), (int, float))]
        if scores != sorted(scores, reverse=True):
            fails.append(f"C11 wave {wid}: BCs não ordenados por Priority Score decrescente")

    # C12 — posição: primeira e última wave T-shirt <= M
    order = ["XS", "S", "M", "L", "XL"]
    for label, w in (("primeira", waves[0]), ("última", waves[-1])) if waves else ():
        t = w.get("tshirt")
        if t in VALID_TSHIRT and order.index(t) > order.index("M"):
            fails.append(f"C12 {label} wave: tshirt={t} > M")

    # C13 — checksum presente
    if not (m.get("cross_validation_checksums") or {}).get("wave_ids_hash"):
        fails.append("C13 wave_ids_hash ausente")

    # C14 — FP/SP preenchidos pelo measure-size (fase 3)
    if all(b.get("fp") in (0, None)
           for w in waves for b in w.get("bounded_contexts", [])):
        fails.append("C14 todos os fp=0 — ava-tobe-measure-size não atualizou o modelo")

    print(f"{project}: {len(fails)} falha(s)")
    for f in fails:
        print("  FAIL", f)
    return 1 if fails else 0

if __name__ == "__main__":
    raise SystemExit(validate(sys.argv[1]))
```

### 8.2 — Checklist manual (o que o script não cobre)

| #   | Verificação                                                                                                      | Fonte da regra               |
| --- | ------------------------------------------------------------------------------------------------------------------ | ---------------------------- |
| M1  | Todo BC do`inventory-report.md` está em **exatamente uma** wave W1–W3                                    | Step 4.4                     |
| M2  | Nenhum BC-A precede um BC-B do qual depende                                                                        | Step 4.3                     |
| M3  | Progressão`domain_read` → `domain_write` → `domain_core` entre W1, W2 e W3                                | G-16                         |
| M4  | `wave_type` de W1–W3 bate com o `predominant_operation_type` majoritário dos BCs                             | Regra de inferência         |
| M5  | W4 contém**apenas** atividades operacionais (pentest, sign-offs, decommission, flip, monitoramento)         | Step 4.3                     |
| M6  | `wave_name` derivado dos BCs efetivamente alocados, não de rótulo genérico                                    | Step 4.4 item 5              |
| M7  | Cada score tem, na coluna Observações da`migration-priority-matrix.md`, o indicador da rubrica que o justifica | Schema do priority-framework |
| M8  | Todo`[INFERIDO]` cita o artefato onde o dado faltou                                                              | D-4                          |
| M9  | Nenhuma data de calendário ou referência a sprint nos artefatos de wave                                          | G-13                         |
| M10 | Re-execução com os mesmos inputs produz a mesma composição                                                     | G-14                         |
| M11 | SP por wave dentro de 5% do`sizing-report.md`                                                                    | G-20                         |
| M12 | `wave_ids_hash` bate com o hash recalculado dos derivados                                                        | Validation Gate Etapa 7.5    |
| M13 | Gantt embutido no`wave-plan.md` é idêntico ao `migration-gantt.mmd`                                          | G-21                         |
| M14 | Todo item de gap-list tem`Responsável sugerido` de valor enumerado                                              | G-9                          |

### 8.3 — Cross-validation obrigatória (Validation Gate Etapa 7)

| #   | Verificação                                                                     | Artefatos                                                                                                                         | Esperado                        |
| --- | --------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ------------------------------- |
| 7.1 | Número de waves idêntico                                                        | `wave-plan.md`, `migration-executive-summary.md`, `ai-estimation-report.md`, `ado-work-items.md`, `migration-gantt.mmd` | Zero divergências              |
| 7.2 | Composição de BCs por wave idêntica                                            | `wave-plan.md`, `ado-work-items.md`                                                                                           | Zero BCs ausentes ou excedentes |
| 7.3 | T-shirt por wave idêntico                                                        | `wave-plan.md`, `migration-executive-summary.md`, `ai-estimation-report.md`                                                 | Zero divergências              |
| 7.4 | FP/SP por wave e por BC idênticos; horas coerentes com a cadeia Fixed Parameters | +`sizing-report.md`                                                                                                             | Zero divergências              |
| 7.5 | `wave_ids_hash` bate com o recalculado                                          | Todos os derivados                                                                                                                | Hash match                      |
| 7.6 | Coluna`Wave sugerida` corresponde à wave do modelo                             | `integration-matrix.md`                                                                                                         | Zero divergências              |
| 7.7 | Coluna`Wave` referencia só waves existentes                                    | `manual-gap-list.md`                                                                                                            | Zero referências órfãs       |

### 8.4 — Output Contract (13 arquivos obrigatórios)

Relatório de completude deve exibir **"13/13 — CONCLUÍDO"** antes de encerrar (G-6, G-10).

| #  | Arquivo                                                 | Gerado em         |
| -- | ------------------------------------------------------- | ----------------- |
| 1  | `outputs/tobe/migration/wave-model.json`              | Fase 2.7 (`WM`) |
| 2  | `outputs/tobe/docs/integration-matrix.md`             | Fase 2.7          |
| 3  | `outputs/tobe/docs/tshirt-sizing-rationale.md`        | Fase 2.7          |
| 4  | `outputs/tobe/migration/migration-priority-matrix.md` | Fase 2.7          |
| 5  | `outputs/tobe/docs/ai-estimation-report.md`           | Fase 4            |
| 6  | `outputs/tobe/docs/manual-gap-list.md`                | Fase 4            |
| 7  | `outputs/tobe/docs/migration-executive-summary.md`    | Fase 4            |
| 8  | `outputs/tobe/docs/migration-plan.md`                 | Fase 4            |
| 9  | `outputs/tobe/docs/wave-plan.md`                      | Fase 4            |
| 10 | `outputs/tobe/docs/ado-work-items.md`                 | Fase 4            |
| 11 | `outputs/tobe/diagrams/migration-gantt.mmd`           | Fase 4            |
| 12 | `outputs/tobe/migration/migration-activity-plan.md`   | Fase 4            |
| 13 | `outputs/tobe/migration/activity-dependency-graph.md` | Fase 4            |

Condicionais fora dos 13: `backlog-tobe.md` (Fase 2.5, input herdado) e os 3 do WCR (Fase 4.2).

---

## 9. Achados — divergências conhecidas

### 9.1 — Contradição no número de waves (spec)

O agente carrega **duas regras incompatíveis**:

| Fonte                                  | Regra                                                                                                          |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Wave Count Framework +**G-8**    | Faixa 3–8 waves, com algoritmo de ajuste (split se N < 3, consolidação se N > 8)                            |
| Step 4.4 +`wave-model.template.json` | **Fixo em 5 waves (W0–W4)**, `total_waves = 5 (fixo)`, validação exige "todas as 5 waves presentes" |

Na prática o template vence e o algoritmo de ajuste do G-8 nunca dispara — é código morto. O texto
tenta reconciliar ("com 5 waves, a composição está dentro da faixa Normal"), mas a estrutura fixa
também elimina a flexibilidade que o G-8 pressupõe.

**Impacto**: usar o G-8 como critério de aceite produz falso positivo. **Recomendação**: decidir qual
é a intenção e remover a outra — se 5 waves é a regra, o Wave Count Framework deve virar nota
histórica; se a faixa é a regra, o template precisa aceitar N variável.

### 9.2 — Faixa de prioridade parcialmente inalcançável

A tabela de faixas declara `0–15 → P3`, mas o mínimo matemático da fórmula é **12**. A sub-faixa
`0–11` é inatingível. Não causa erro, mas induz a leitura de que scores abaixo de 12 são válidos —
e foi provavelmente o que abriu espaço para os scores fora de escala do §9.3.

### 9.3 — Validação em projeto real: `nopcommerce-04`

Rodando o checklist do §8.1 contra
[projects/nopcommerce-04/outputs/tobe/migration/wave-model.json](../projects/nopcommerce-04/outputs/tobe/migration/wave-model.json):

```
$ python validate_wave_model.py nopcommerce-04
nopcommerce-04: 46 falha(s)
exit=1
```

| Check                               | Resultado                                                                                                                                                                           |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **C1** schema                 | ❌`metadata`, `summary` e `cross_validation_checksums` **ausentes**. Raiz usa `project`/`generated_at`/`agent`/`total_waves`/`waves` — schema não-canônico |
| **C3** `wave_number`        | ❌ ausente nas 5 waves; usa`wave_id` (`"W1"`), que não é campo do template                                                                                                    |
| **C5** T-shirt da wave        | ❌ W0 =`XL`, W3 = `XXL`, W4 = `L`                                                                                                                                             |
| **C6** Priority Score         | ❌**9 de 10 BCs fora da faixa [12,60]**                                                                                                                                       |
| **C7** T-shirt do BC          | ❌`BC-02 Orders` = `XXL` — valor inexistente no domínio                                                                                                                       |
| **C8** dimensão determinante | ❌ ausente nos 10 BCs (G-2)                                                                                                                                                         |
| **C9** coupling bidirecional  | ❌`coupling_in`/`coupling_out` ausentes; só o total (G-5 não verificável)                                                                                                    |
| **C10** T-shirt = max dos BCs | ❌ W1 declara`L`, mas o máximo dos seus BCs é `M`                                                                                                                             |
| **C11** ordenação           | ❌ W1 =`85, 80, 90, 75, 70` e W2 = `70, 75, 72, 65` — nenhuma decrescente                                                                                                      |
| **C12** posição             | ❌ primeira wave`XL` e última `L`, ambas > M                                                                                                                                   |
| **C13** checksum              | ❌`wave_ids_hash` ausente                                                                                                                                                         |
| **C14** FP/SP                 | ❌ todos`fp: 0`, `sp: 0` — `ava-tobe-measure-size` não atualizou o modelo                                                                                                   |

Scores registrados:

| Wave | BC              | T-shirt | Score | Faixa [12,60] |
| ---- | --------------- | ------- | ----: | ------------- |
| W1   | BC-06 Tax       | S       |    85 | ❌            |
| W1   | BC-09 Media     | M       |    80 | ❌            |
| W1   | BC-07 Security  | M       |    90 | ❌            |
| W1   | BC-05 Shipping  | M       |    75 | ❌            |
| W1   | BC-10 Common    | M       |    70 | ❌            |
| W2   | BC-01 Catalog   | XL      |    70 | ❌            |
| W2   | BC-03 Customers | L       |    75 | ❌            |
| W2   | BC-04 Payments  | L       |    72 | ❌            |
| W2   | BC-08 Messages  | L       |    65 | ❌            |
| W3   | BC-02 Orders    | XXL     |    60 | ✅            |

**Diagnóstico**: os `wave_name` são `"Low Complexity BCs"`, `"Medium Complexity BCs"`,
`"High Complexity BCs"` — a composição foi feita por **agrupamento de complexidade**, não pelo
Priority Score. Os scores parecem estar numa escala 0–100 arbitrária, não na fórmula canônica.
O `agent` declarado é `ava-tobe-migration-plan v1.0.0`, enquanto o agente em disco está em **v1.4.0**
— o modelo foi gerado por uma versão anterior ao método atual, ou o campo não foi atualizado.

### 9.4 — Validação em projeto real: `my-nop-ecommerce`

```
$ python validate_wave_model.py my-nop-ecommerce
my-nop-ecommerce: 44 falha(s)
exit=1
```

| Check                               | Resultado                                                                                                                                                          |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **C1** schema                 | ⚠️ parcial — tem`schema_version`, `trace_id`, `total_fp`, `total_sp` na raiz, mas sem os blocos `metadata`/`summary`/`cross_validation_checksums` |
| **C3** `wave_number`        | ❌ ausente nas 5 waves                                                                                                                                             |
| **C5** T-shirt da wave        | ❌`null` em todas as 5 waves                                                                                                                                     |
| **C6** Priority Score         | ❌`null` em todos os BCs                                                                                                                                         |
| **C8** dimensão determinante | ❌ ausente                                                                                                                                                         |
| **C9** coupling bidirecional  | ❌ ausente                                                                                                                                                         |
| **C13** checksum              | ❌ ausente                                                                                                                                                         |

Estrutura de 5 waves e `wave_type` corretos, mas sem sizing, sem T-shirt e sem scores — modelo
incompleto. Diferente do `nopcommerce-04`, aqui não há valores **errados**, apenas **ausentes**.

### 9.5 — Conclusão da auditoria

Nenhum dos dois `wave-model.json` em disco passa no Validation Gate. Os dois divergem do schema
canônico em campos diferentes, o que indica que **o template não está sendo carregado** no Step 4.6
("Ler template: carregar o template canônico de `wave-model.template.json`"). O método está bem
especificado; a execução não o está seguindo.

Ações sugeridas, em ordem de retorno:

1. Tornar o Step 4.6 verificável — validar o `wave-model.json` contra o schema do template antes de
   persistir, com o script do §8.1 como gate
2. Adicionar assert de faixa `[12, 60]` no Priority Score — pega o erro de escala na origem
3. Fechar o domínio de `tshirt` — rejeitar `XXL` e qualquer valor fora de XS/S/M/L/XL
4. Resolver a contradição do §9.1 antes de usar o G-8 em qualquer gate
5. Fazer `ava-tobe-measure-size` falhar quando o modelo que recebe já vem sem `metadata`/`summary`

---

## 10. Comandos de verificação

```bash
# Inspecionar o modelo de um projeto
python -c "import json;d=json.load(open('projects/{P}/outputs/tobe/migration/wave-model.json',encoding='utf-8'));print(json.dumps(d,ensure_ascii=False,indent=2))"

# Validação estrutural (script do §8.1)
python validate_wave_model.py {P}

# Conferir a cadeia FP→SP→horas do sizing
grep -n -A12 "Seção 4 — Esforço por Wave" projects/{P}/outputs/tobe/docs/sizing-report.md

# Verificar que o manifesto da F3S aceita o modelo (hard stop se divergir)
python src/shared/tools/speckit_wave_manifest.py --project {P} --json

# Re-executar apenas a composição de waves
ava-pipeline.bat run -p {P} --phase F2a --yes     # esteira completa da F2
# ou, na sessão interativa:
#   @ava-tobe-migration-plan | WM | project: {P}
```

---

## Ver também

- [guia-execucao-fluxo-agentes.md](guia-execucao-fluxo-agentes.md) — esteira completa e catálogo de agentes
- [tobe-architecture-io-map.md](tobe-architecture-io-map.md) — mapa de entradas/saídas da F2
- [speckit-guia.md](speckit-guia.md) — como a F3S consome as waves
