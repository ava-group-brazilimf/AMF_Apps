# Wave Cycle Refinement (WCR)

> Trigger: `WCR` — Refina o wave plan após PILOT e/ou feedback do Strategy Align.
> Produz `wave-plan-refined.md` com estimativas calibradas e sequência ajustada.

## Quando Acionar

O WCR é acionado quando **qualquer** das condições abaixo for verdadeira:
1. Um PILOT (wave de prova) foi executado e produziu métricas reais de esforço
2. O Requestor/Human SME forneceu feedback sobre priorização, sequência ou critérios de aceite
3. Novas regras de negócio ou requisitos funcionais foram descobertos após o wave plan inicial
4. Mudanças nos Bounded Contexts (split, merge, reordenação) foram identificadas

## Inputs do WCR

| # | Fonte | Path | Obrigatório |
|---|---|---|---|
| 1 | Wave Plan original | `projects/{project_name}/outputs/tobe/docs/wave-plan.md` | ✅ Sim |
| 2 | Migration Activity Plan | `projects/{project_name}/outputs/tobe/migration/migration-activity-plan.md` | ✅ Sim |
| 3 | Priority Matrix | `projects/{project_name}/outputs/tobe/migration/migration-priority-matrix.md` | ✅ Sim |
| 4 | PILOT Metrics (se executado) | `projects/{project_name}/outputs/tobe/migration/pilot-metrics.md` | ⚠️ Condicional |
| 5 | Strategy Align Feedback | `projects/{project_name}/outputs/tobe/migration/strategy-align-feedback.md` | ⚠️ Condicional |
| 6 | Business Rules (atualizado) | `projects/{project_name}/outputs/asis/docs/business-rules.md` | ✅ Sim |
| 7 | Functional Requirements (atualizado) | `projects/{project_name}/outputs/asis/docs/business-rules.md` (seção `## Functional Requirements`) | ✅ Sim |
| 8 | Bounded Context Map TO-BE | `projects/{project_name}/outputs/tobe/docs/bounded-context-map.md` | ✅ Sim |

## WCR Execution Protocol

### WCR Step 1 — Coleta de Evidências do PILOT

Se PILOT foi executado, extrair métricas reais:

| Métrica | Fonte | Uso no refinamento |
|---|---|---|
| Esforço real IA (h) | logs de execução do PILOT | Calibrar `Tempo IA (h)` no benchmark |
| Esforço real manual (h) | relatório de remediação | Calibrar `Tempo Manual (h)` |
| Gaps não previstos | gap-list pós-PILOT | Adicionar à `manual-gap-list.md` |
| Desvio de cobertura IA | % real vs. estimado | Ajustar fator de cobertura por T-shirt |
| Impedimentos encontrados | registro de impedimentos | Alimentar risk-mitigation-plan |

**Fator de calibração:**
```
Calibration Factor (CF) = Esforço Real PILOT / Esforço Estimado PILOT
```
- `CF ∈ [0.8, 1.2]` → estimativas válidas; aplicar CF como ajuste fino
- `CF < 0.8` → estimativas superestimadas; reduzir benchmarks proporcionalmente
- `CF > 1.2` → estimativas subestimadas; aumentar benchmarks proporcionalmente

Aplicar `CF` a TODAS as waves restantes (não executadas pelo PILOT).

### WCR Step 2 — Incorporação do Strategy Align Feedback

Processar feedback do Requestor/Human SME nos seguintes eixos:

| Eixo de feedback | Ação no wave plan |
|---|---|
| Reordenação de BCs | Ajustar sequência de waves respeitando dependências do grafo |
| Split de BC | Dividir wave; recalcular T-shirt e Priority Score dos sub-BCs |
| Merge de BCs | Consolidar waves; recalcular T-shirt (`max`) e Coupling Score |
| Alteração de criticidade | Recalcular Priority Score com novos valores de Domínio Crítico |
| Novas regras de negócio | Gerar novas atividades (Step A1); inserir nas waves adequadas |
| Remoção de escopo | Remover atividades; recalcular T-shirt se módulos mudaram |
| Alteração de critérios de aceite | Atualizar seção de critérios de aceite da wave afetada |

### WCR Step 3 — Recálculo de Estimativas

Para cada wave restante: aplicar `CF` aos benchmarks (IA × CF, Manual × CF). Atualizar `migration-priority-matrix.md`.

### WCR Step 4 — Validação de Consistência

| # | Verificação | Ação se falhar |
|---|---|---|
| 1 | Todas as atividades ainda possuem rastreabilidade (BR-{N} ou ARCH-{componente}) | Restaurar rastreabilidade ou justificar remoção |
| 2 | Grafo de dependências está acíclico (sem ciclos) | Resolver ciclo removendo dependência mais fraca |
| 3 | Estratégia incremental respeitada (Leitura → Escrita → Core) dentro de cada BC | Reordenar atividades |
| 4 | Wave count ∈ [3, 8] após ajustes | Aplicar algoritmo de split/consolidação |
| 5 | Wave 1 T-shirt ≤ M e Wave final T-shirt ≤ M | Reordenar módulos entre waves |

### WCR Step 5 — Geração do wave-plan-refined.md

Gerar `wave-plan-refined.md` com o mesmo schema do `wave-plan.md` original acrescido de:

| Campo adicional | Descrição |
|---|---|
| **Calibration Factor aplicado** | CF usado para ajustar estimativas (ou `1.0` se sem PILOT) |
| **Fonte de ajuste** | `PILOT` / `Strategy Align` / `Ambos` / `Baseline` |
| **Desvio vs. original** | Delta de esforço em relação ao wave-plan original: `+X%` ou `-X%` |
| **Critérios de aceite (revisados)** | Critérios validados pelo Requestor/Human SME (marcados como `[VALIDADO]`) |
| **Justificativa de reordenação** | Motivo para mudança de sequência (quando aplicável) |

## WCR Output Contract

```yaml
outputs:
  wave_plan_refined:      "projects/{project_name}/outputs/tobe/migration/wave-plan-refined.md"
  priority_matrix_refined: "projects/{project_name}/outputs/tobe/migration/migration-priority-matrix-refined.md"
  wcr_changelog:          "projects/{project_name}/outputs/tobe/migration/wcr-changelog.md"
```

## Template — `wcr-changelog.md`

```markdown
# Wave Cycle Refinement — Changelog

**Projeto**: {project_name} | **Data**: {data} | **Versão**: 1.0
**Fonte de ajuste**: PILOT / Strategy Align / Ambos

## Mudanças Aplicadas

| # | Tipo | Descrição | Wave afetada | Impacto no esforço |
|---|---|---|---|---|
| 1 | [Reorder/Split/Merge/NewActivity/RemoveScope/CriteriaUpdate] | [descrição] | Wave {N} | +X% / -X% |

## Calibration Summary (se PILOT disponível)

| Métrica | Estimado (original) | Real (PILOT) | CF | Aplicado a waves |
|---|---|---|---|---|
| Tempo IA (h) | Xh | Yh | CF | Waves {N}–{M} |
| Tempo Manual (h) | Xh | Yh | CF | Waves {N}–{M} |
```
