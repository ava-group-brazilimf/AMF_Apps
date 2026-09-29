---
template_id: migration-gantt-mermaid
agent: ava-tobe-migration-plan
version: "1.1.1"
date: 2026-06-05
description: "Template canônico Mermaid Gantt para migration-gantt.mmd — regras de sintaxe, derivação de durações e exemplo de referência"
---

# Migration Gantt — Mermaid Template

> **Load when**: executing Step 6.5 of the Execution Protocol, when generating `migration-gantt.mmd`.

## Regras de Sintaxe (erros comuns causam falha silenciosa de renderização)

- **`dateFormat YYYY-MM-DD`** é OBRIGATÓRIO como primeira diretiva após `gantt`
- **IDs de tarefa**: obrigatórios e únicos — ex: `w1-design`, `w2-dev` — sem espaços
- **Datas relativas** (`after <id>`): só usar com ID âncora explícito declarado anteriormente
- **Status de tarefa**: `done`, `active`, `crit`, ou omitido — nunca texto livre
- **Nomes de section**: texto simples sem caracteres `{`, `}`, `:` fora de strings
- **`excludes weekends`**: opcional, colocar antes das sections

## Derivação de Durações (cadeia obrigatória — Step 6.5.2)

> As durações no Gantt são derivadas dos dados do `sizing-report.md` e `wave-model.json`,
> usando os Fixed Parameters do `measure-size-tobe.md` (IMUTÁVEIS).

```
1. total_hours_wave     = ler do sizing-report.md (Seção 4) ou wave-model.json (total_hours)
2. capacidade_semanal   = squad_size × hours_per_week = 3 × 40 = 120 h/semana
3. duração_semanas      = total_hours_wave ÷ 120
4. duração_arredondada  = ceil(duração_semanas)
5. duração_gantt        = "{duração_arredondada}w"
```

**Decomposição em fases por wave:**

| Fase | % da duração | ID pattern | Descrição |
|---|---|---|---|
| Análise e design | 15% | `w{N}-design` | Revisão de requisitos, design detalhado |
| Desenvolvimento | 50% | `w{N}-dev` | Implementação, code review, integração |
| Testes e homologação | 25% | `w{N}-qa` | Testes unitários, integração, aceite |
| Deploy e validação | 10% | `w{N}-deploy` | Deploy, smoke tests, feature flag flip |

> Aplicar `ceil()` por fase para garantir ≥ 1d. Converter semanas em dias (`Nd`) para fases.

**Milestones obrigatórios:**
- Após W1–W3: `Go/No-Go Gate W{N}` — duração `0d`, posicionado `after w{N}-deploy`
- Após W4: `Migration Complete` — duração `0d`, posicionado `after w4-deploy`

> **G-13 Reconciliação**: a data de início é placeholder para renderização Mermaid. As durações
> são relativas, derivadas do esforço estimado. O Gantt NÃO atribui datas fixas às waves.

## Template canônico

```mermaid
gantt
    title Plano de Migração — {project_name}
    dateFormat YYYY-MM-DD
    excludes weekends

    section {wave_name}
        Análise e design         :done,    w0-design,  {start_date}, {N}d
        Desenvolvimento          :done,    w0-dev,     after w0-design, {N}d
        Testes e homologação     :done,    w0-qa,      after w0-dev, {N}d
        Deploy W0                :done,    w0-deploy,  after w0-qa, {N}d

    section {wave_name}
        Análise e design         :active,  w1-design,  after w0-deploy, {N}d
        Desenvolvimento          :active,  w1-dev,     after w1-design, {N}d
        Testes e homologação     :crit,    w1-qa,      after w1-dev, {N}d
        Deploy W1                :         w1-deploy,  after w1-qa, {N}d
        Go/No-Go Gate W1         :milestone, w1-gate,  after w1-deploy, 0d

    section {wave_name}
        Análise e design         :         w2-design,  after w1-deploy, {N}d
        Desenvolvimento          :         w2-dev,     after w2-design, {N}d
        Testes e homologação     :         w2-qa,      after w2-dev, {N}d
        Deploy W2                :         w2-deploy,  after w2-qa, {N}d
        Go/No-Go Gate W2         :milestone, w2-gate,  after w2-deploy, 0d

    section {wave_name}
        Análise e design         :         w3-design,  after w2-deploy, {N}d
        Desenvolvimento          :         w3-dev,     after w3-design, {N}d
        Testes e homologação     :         w3-qa,      after w3-dev, {N}d
        Deploy W3                :         w3-deploy,  after w3-qa, {N}d
        Go/No-Go Gate W3         :milestone, w3-gate,  after w3-deploy, 0d

    section {wave_name}
        Análise e design         :         w4-design,  after w3-deploy, {N}d
        Desenvolvimento          :         w4-dev,     after w4-design, {N}d
        Testes e homologação     :crit,    w4-qa,      after w4-dev, {N}d
        Deploy W4                :         w4-deploy,  after w4-qa, {N}d
        Migration Complete       :milestone, w4-done,  after w4-deploy, 0d
```

> **Substituir placeholders**: `{project_name}`, `{wave_name}` (do wave-model.json),
> `{start_date}` (do project-config.yaml ou data corrente), `{N}d` (dias derivados da
> decomposição de fases × duração total da wave conforme Step 6.5.3).
>
> ⛔ O valor de `{wave_name}` DEVE ser copiado **literalmente** do campo `wave_name`
> do `wave-model.json`, que já contém o prefixo "W{N} — ".
> PROIBIDO abreviar, truncar ou reformatar o nome.
> Exemplo: se wave-model.json tem
> `"wave_name": "W1 — Core Domain — Auth + CustomerSupplier + FinancialMasterData"`,
> a section será:
> `section W1 — Core Domain — Auth + CustomerSupplier + FinancialMasterData`.
