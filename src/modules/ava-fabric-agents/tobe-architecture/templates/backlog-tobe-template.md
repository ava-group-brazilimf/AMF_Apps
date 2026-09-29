---
template_id: backlog-tobe
agent: ava-tobe-migration-plan
version: "1.0.0"
date: 2026-06-02
description: "Especificação completa do Backlog Preliminar TO-BE — regras de geração de user stories, critérios MoSCoW, domínios técnicos e schema obrigatório de saída"
---

# Backlog TO-BE — Template & Generation Rules

> **Load when**: executing Steps B2–B5 of the Backlog TO-BE Protocol.
> Contains: regras de geração de user stories por BC, critérios MoSCoW, domínios de US técnicas, checklist de pendências e schema obrigatório de `backlog-tobe.md`.

---

## Step B2 — Gerar User Stories por Bounded Context

Para cada BC encontrado no `bounded-context-map.md` TO-BE:

0. **Rastreabilidade de BCs absorvidos/eliminados**: Ler a seção `### Rastreabilidade de BCs Eliminados/Absorvidos` do `bounded-context-map.md` TO-BE (gerada no BC Consolidation Review). Para cada BC AS-IS com decisão **Merge into X**, verificar que **todas** as funcionalidades listadas na coluna "Funcionalidades migradas" estejam representadas por user stories no BC TO-BE absorvente. Se alguma funcionalidade de BC eliminado/absorvido não tiver US correspondente, registrar na seção `## Pendências e Lacunas` com tipo `Gap de cobertura (BC absorvido)` e impacto `Funcionalidade de {BC eliminado} sem rastreabilidade no backlog TO-BE`.
0.1. **Representação explícita de BCs absorvidos no backlog**: Para cada BC AS-IS com decisão **Merge into X**, criar uma seção visível no backlog com o formato:
    ```markdown
    ## BC-{NN} — {NomeOriginal} (Absorvido → BC-{XX} {NomeAbsorvente})
    > **Decisão arquitetural**: BC-{NN} foi absorvido por BC-{XX} conforme
    > Consolidation Review (bounded-context-map.md §1).
    > As funcionalidades de BC-{NN} estão cobertas pelas seguintes user stories
    > em BC-{XX}:
    | Funcionalidade migrada | User Story correspondente | Status |
    |---|---|---|
    | {funcionalidade 1} | US-{BCXX}-{NNN} | ✅ Coberta |
    | {funcionalidade 2} | US-{BCXX}-{NNN} | ✅ Coberta |
    | {funcionalidade 3} | US-{BCXX}-{NNN} | ✅ Coberta |
    ```
    Esta seção NÃO gera user stories novas com ID `US-BC{NN}-{NNN}`
    (o BC absorvido não tem stories próprias). Serve exclusivamente para
    rastreabilidade AS-IS → TO-BE e para satisfazer critérios que exijam
    representação de todos os BCs AS-IS no backlog.
1. Identificar todas as regras de negócio (`BR-{N}`) e requisitos funcionais (`RF-{N}`) associados ao BC
2. Decompor cada regra/requisito em uma ou mais user stories no formato:
   `Como [papel], quero [ação] para [valor de negócio]`
3. Atribuir ID sequencial: `US-{BC_ID}-{NNN}` (ex.: `US-BC01-001`)
4. Mapear rastreabilidade explícita: cada US DEVE referenciar ≥ 1 `BR-{N}` ou `RF-{N}`
5. Identificar a entidade de banco de dados principal associada (da fonte 8 — Database Design TO-BE)
6. Atribuir prioridade MoSCoW conforme critérios abaixo

### Critérios de Atribuição MoSCoW

| Prioridade | Critério | Indicadores |
|---|---|---|
| **Must** | Regra de negócio com `criticidade: alta` OU requisito funcional com `prioridade: alta` OU funcionalidade core do BC (Aggregate Root, transação principal) | Sem esta US o BC não pode operar |
| **Should** | Regra de negócio com `criticidade: média` OU fluxo secundário documentado OU validação de negócio importante | Funcionalidade esperada mas com workaround possível |
| **Could** | Regra de negócio com `criticidade: baixa` OU funcionalidade de conveniência OU relatório/consulta não-crítica | Agrega valor mas pode ser adiada |
| **Won't (this phase)** | Funcionalidade explicitamente fora de escopo OU dependência de sistema externo não disponível OU funcionalidade legada sem equivalente TO-BE | Documentada para rastreabilidade mas não implementada nesta fase |

> **Regra de derivação**: se a criticidade/prioridade não está explícita nos artefatos de entrada → derivar da classificação de Domínio Crítico do BC (rubrica do Priority Framework): DC ≥ 4 → Must (default); DC = 3 → Should; DC ≤ 2 → Could.

---

## Step B3 — Gerar User Stories Técnicas / Não-Funcionais

Gerar user stories para os seguintes domínios transversais (não associadas a um BC específico):

| Domínio | Exemplos de user stories |
|---|---|
| **Autenticação e Autorização** | Integração Azure AD/Entra ID, SSO, RBAC, token management |
| **Infraestrutura e CI/CD** | Pipeline de build, deploy automatizado, ambientes (dev/staging/prod), IaC |
| **Migração de Dados** | Scripts de migração, mapeamento de dados legado → novo schema, validação pós-migração |
| **Observabilidade** | Logging estruturado, health checks, métricas de negócio, alertas |
| **Segurança e Compliance** | LGPD, auditoria, criptografia de dados sensíveis, pentest |
| **Performance** | Cache, otimização de queries, load testing, SLAs |

ID pattern: `US-TECH-{NNN}` (ex.: `US-TECH-001`)

Rastreabilidade: referenciar componente arquitetural (`ARCH-{componente}`) ou requisito não-funcional (`RNF-{N}`) quando disponível nos artefatos de entrada.

> **Cobertura mínima obrigatória**: cada um dos 6 domínios transversais listados
> acima DEVE ter **≥ 1 user story** no backlog. Se algum domínio não tiver US,
> gerar ao menos uma US genérica com `CONFIDENCE: LOW` e registrar na seção
> Pendências para validação pelo PM.
>
> Verificação: antes de finalizar Step B3, iterar sobre os 6 domínios e
> confirmar que cada um está representado por ≥ 1 `US-TECH-{NNN}`.
> Se a verificação falhar → gerar a US faltante antes de prosseguir.

---

## Step B4 — Identificar Pendências e Lacunas

1. Listar user stories com `CONFIDENCE: LOW` (derivadas de fontes ausentes)
2. Listar regras de negócio sem user story correspondente (gaps de cobertura)
3. Listar requisitos funcionais sem user story correspondente
4. Identificar itens que requerem validação com o PM ou cliente
5. Registrar fontes de entrada ausentes e seu impacto no backlog

---

## Step B5 — Schema Obrigatório de `backlog-tobe.md`

Gerar o arquivo com a seguinte estrutura obrigatória:

```markdown
# Backlog Preliminar TO-BE

**Projeto**: {project_name}
**Data de geração**: {data}
**Trace ID**: {trace_id}
**Agente**: ava-tobe-migration-plan v{version}
**Fase do pipeline**: Backlog TO-BE (pré-wave planning)
**PM responsável**: {pm_name}

---

## Resumo Executivo

| BC | Total US | Must | Should | Could | Won't | Cobertura BR (%) | Cobertura RF (%) |
|---|---|---|---|---|---|---|---|
| BC-{NN}: {nome} | X | X | X | X | X | X% | X% |
| ... | ... | ... | ... | ... | ... | ... | ... |
| **TOTAL** | **X** | **X** | **X** | **X** | **X** | **X%** | **X%** |

> Cobertura BR = (BRs com ≥ 1 US associada / total BRs do BC) × 100
> Cobertura RF = (RFs com ≥ 1 US associada / total RFs do BC) × 100
>
> **BCs absorvidos no Resumo Executivo**: incluir uma linha para cada BC AS-IS
> com decisão Merge/Eliminate. Coluna `Total US` = `0 (absorbed)`. Coluna `Notas`
> = lista das US do BC absorvente que cobrem as funcionalidades migradas.
> Incluir TAMBÉM uma linha na tabela "Mapa de Correlação BC → BR → RF"
> com referência cruzada ao BC absorvente.

---

## BC-NN: {Nome do BC}

| ID | User Story | Regra de Negócio (ref) | Entidade BD | Prioridade (MoSCoW) | Notas |
|---|---|---|---|---|---|
| US-{BC}-{NNN} | Como [papel], quero [ação] para [valor de negócio] | BR-{N}, RF-{N} | {entidade} | Must/Should/Could/Won't | [notas] |

(repetir para cada BC)

---

## User Stories Técnicas / Não-Funcionais

| ID | User Story | Componente (ref) | Prioridade (MoSCoW) | Notas |
|---|---|---|---|---|
| US-TECH-{NNN} | Como [papel], quero [ação] para [valor de negócio] | ARCH-{componente} ou RNF-{N} | Must/Should/Could/Won't | [notas] |

---

## Pendências e Lacunas

| # | Tipo | Descrição | Impacto | Ação requerida | Responsável |
|---|---|---|---|---|---|
| 1 | [Fonte ausente / Gap de cobertura / Validação necessária] | [descrição] | [impacto no backlog] | [ação] | PM / BA / Dev / A definir |
```

> **Validação aritmética obrigatória (executar antes de salvar)**:
> 1. Calcular `SP_epics = soma da coluna SP da tabela de Epics`
> 2. Calcular `SP_waves = soma dos subtotais de cada seção "Wave N Subtotal"`
> 3. Calcular `SP_distribution = soma da coluna SP da tabela Story Point Distribution`
> 4. ASSERT: `SP_epics == SP_waves == SP_distribution`
> 5. Se qualquer divergência → corrigir a tabela derivada para refletir o valor fonte (Epics é a fonte primária)

**Salvar em:** `projects/{project_name}/outputs/tobe/docs/backlog-tobe.md`
