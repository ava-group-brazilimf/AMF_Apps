# Priority Framework — Rubrica de Pontuação Canônica

> Priorização multidimensional: Priority Score determina sequência lógica (ver G-13 sobre waves ≠ timeframes).

## Critérios de Priorização (aplicados em ordem de peso decrescente)

| # | Critério | Peso | Escala | Descrição |
|---|---|---|---|---|
| 1 | **Domínio Crítico** | 4 | 1–5 (5 = mais crítico) | BCs que sustentam operações core do negócio — ver Rubrica Canônica abaixo |
| 2 | **Risco Transacional** | 3 | 1–5 (1 = baixo risco) | Risco de inconsistência transacional durante e após migração — ver Rubrica Canônica abaixo |
| 3 | **Valor de Negócio** | 3 | 1–5 (5 = maior valor) | Impacto positivo mensurável que a migração do BC trará ao negócio — ver Rubrica Canônica abaixo |
| 4 | **Complexidade Funcional** | 2 | 1–5 (1 = menor complexidade) | Quantidade e interdependência de regras de negócio e fluxos condicionais — ver Rubrica Canônica abaixo |

## Rubrica de Pontuação Canônica (OBRIGATÓRIA — Fonte Única de Verdade)

> Rubricas canônicas e fixas (ver G-15, D-1, D-4, D-5). Pontuações derivadas exclusivamente dos artefatos de entrada; dado ausente → valor neutro **3** + `[INFERIDO]`.

### Critério 1 — Domínio Crítico (peso 4)

Mede o quanto o Bounded Context sustenta operações **vitais** para a continuidade do negócio.

| Pontuação | Classificação | Indicadores objetivos |
|---|---|---|
| **5** | Vital | BC de faturamento, pagamento, compliance regulatório, autenticação/autorização, ou qualquer BC cuja indisponibilidade **interrompe receita ou gera penalidade legal**. Presença obrigatória de pelo menos UM: processo financeiro, SLA contratual, obrigação regulatória (LGPD, SOX, BACEN). |
| **4** | Alto | BC de operações primárias voltadas ao cliente (gestão de pedidos, onboarding, catálogo de produtos/serviços). Indisponibilidade **degrada diretamente** a experiência do cliente ou impede vendas. |
| **3** | Médio | BC de operações internas (gestão de estoque, relatórios gerenciais, gestão de força de trabalho). Indisponibilidade causa **impacto operacional interno** sem afetar diretamente o cliente final. |
| **2** | Baixo | BC de funções de suporte (notificações, preferências de usuário, logging aplicativo). Indisponibilidade causa **inconveniência** mas não impede operações. |
| **1** | Mínimo | BC de funções utilitárias/auxiliares (conteúdo estático, cache management, health checks). Indisponibilidade **não tem impacto perceptível** no negócio. |

> **Regra de desempate**: Se o BC possui **qualquer** regra de negócio classificada como `criticidade: alta` em `business-rules.md` → pontuação mínima = 3.

### Critério 2 — Valor de Negócio (peso 3)

Mede o impacto **positivo** que a migração do BC trará para o negócio.

| Pontuação | Classificação | Indicadores objetivos |
|---|---|---|
| **5** | Transformacional | Migração habilita **nova fonte de receita**, elimina risco regulatório crítico, ou é pré-requisito para lançamento de produto/serviço. Evidência: BC referenciado em OKRs estratégicos ou roadmap de produto. |
| **4** | Alto | Migração melhora significativamente a **satisfação/retenção de clientes** ou habilita integrações de alto valor. Evidência: BC associado a métricas de NPS, churn ou conversão. |
| **3** | Moderado | Migração produz **ganho de eficiência operacional** mensurável (redução de tempo de processamento, eliminação de trabalho manual). Evidência: processo manual documentado no AS-IS que será automatizado. |
| **2** | Incremental | Migração resulta em **redução de custo interno** (infra, manutenção, licenciamento). Benefício real mas sem impacto direto em métricas de negócio externas. |
| **1** | Técnico | Migração é **puramente técnica** (modernização de stack, debt reduction). Sem métrica de negócio diretamente afetada. |

> **Regra de desempate**: Se o BC está referenciado em `business-rules.md` (seção `## Functional Requirements`) com `prioridade: alta` → pontuação mínima = 3.

### Critério 3 — Complexidade Funcional (peso 2, invertido na fórmula)

Mede a **quantidade e interdependência** de regras de negócio, fluxos condicionais e validações do BC. **Menor complexidade = score mais alto na fórmula** (migrar primeiro os BCs mais simples).

| Pontuação | Classificação | Indicadores objetivos |
|---|---|---|
| **1** | Mínima | ≤ 5 regras de negócio, CRUD simples, sem fluxos condicionais, sem máquinas de estado. Operações atômicas e independentes. |
| **2** | Baixa | 6–15 regras de negócio, condicionais simples (if/else linear), poucas validações de campo. Sem dependência entre regras. |
| **3** | Moderada | 16–30 regras de negócio, fluxos condicionais com 2–3 níveis de profundidade, múltiplas validações cross-field. Algumas regras interdependentes. |
| **4** | Alta | 31–50 regras de negócio, fluxos condicionais complexos, máquinas de estado, validações de negócio com dependências cross-BC. |
| **5** | Muito Alta | > 50 regras de negócio, fluxos heavily interdependentes, sagas multi-step, workflows com compensação, regras com lógica temporal. |

> **Fonte de dados**: Contar regras em `business-rules.md` filtrando pelo BC. Se `business-rules.md` estiver ausente → usar contagem de `Regras de negócio mapeadas` do T-Shirt Sizing Framework. As faixas numéricas (≤5, 6–15, 16–30, 31–50, >50) são **fixas e invioláveis** — idênticas às faixas do T-Shirt Sizing para a dimensão "Regras de negócio".

### Critério 4 — Risco Transacional (peso 3, invertido na fórmula)

Mede o **risco de inconsistência de dados** durante e após a migração. **Menor risco = score mais alto na fórmula** (migrar primeiro os BCs com menor risco transacional).

| Pontuação | Classificação | Indicadores objetivos |
|---|---|---|
| **1** | Mínimo | Operações **read-only** (queries, consultas, relatórios). Sem alteração de estado. Sem transações. Tipo Operação predominante: `Leitura`. |
| **2** | Baixo | Escrita simples em **recurso único** (single-entity CRUD). Transação local em uma única tabela/collection. Rollback trivial. |
| **3** | Moderado | Escrita em **múltiplas entidades** dentro do mesmo BC. Transação local multi-tabela. Rollback viável com compensação simples. |
| **4** | Alto | Escrita **cross-BC** ou chamadas a APIs externas com side-effects. Transações compensatórias necessárias. Feature flag insuficiente para rollback completo. |
| **5** | Crítico | **Transações distribuídas**, operações financeiras, sagas com múltiplos participantes, eventual consistency com janela de inconsistência. Rollback requer orquestração complexa. |

> **Regra de classificação automática**: Se o BC tem `Tipo Operação` predominantemente `Leitura` em `migration-activity-plan.md` → Risco Transacional máximo = 2. Se predominantemente `Core` → Risco Transacional mínimo = 4.

## Exemplo de Pontuação Determinística

> Exemplo genérico (project-agnostic) para ilustrar como aplicar a rubrica de forma consistente.

| BC | Domínio Crítico | Valor de Negócio | Complexidade Funcional | Risco Transacional | Priority Score | Prioridade |
|---|---|---|---|---|---|---|
| BC-Consultas | 3 (operações internas) | 3 (eficiência operacional) | 1 (≤5 regras, CRUD) | 1 (read-only) | (3×4)+((6-1)×3)+(3×3)+((6-1)×2) = 12+15+9+10 = **46** | **P0** |
| BC-Cadastro | 4 (cliente-facing) | 4 (retenção de clientes) | 2 (6–15 regras) | 2 (single-entity CRUD) | (4×4)+((6-2)×3)+(4×3)+((6-2)×2) = 16+12+12+8 = **48** | **P0** |
| BC-Financeiro | 5 (faturamento) | 5 (receita direta) | 4 (31–50 regras) | 5 (transações distribuídas) | (5×4)+((6-5)×3)+(5×3)+((6-4)×2) = 20+3+15+4 = **42** | **P1** |
| BC-Sagas | 5 (compliance) | 4 (regulatório) | 5 (>50 regras) | 5 (sagas multi-step) | (5×4)+((6-5)×3)+(4×3)+((6-5)×2) = 20+3+12+2 = **37** | **P1** |

> **Design intencional**: a fórmula favorece BCs de baixa complexidade e baixo risco primeiro, validando o pipeline antes de abordar módulos críticos.

## Faixas de Prioridade

| Faixa | Score | Prioridade | Ação |
|---|---|---|---|
| 46–60 | Alta | **P0** | Migrar primeiro — domínio crítico, baixo risco, alta maturidade funcional |
| 31–45 | Média-Alta | **P1** | Migrar em sequência após P0; tipicamente módulos de leitura/consulta |
| 16–30 | Média | **P2** | Migrar após validação de P0 e P1; módulos de escrita e integração |
| 0–15 | Baixa | **P3** | Migrar por último; processamento crítico, sagas, módulos core complexos |

## Estratégia Incremental Obrigatória

> Progressão intra-BC: `Leitura → Escrita → Core` (ver G-12). Enforcement intra-domínio: ver G-16.

## Schema obrigatório — `migration-priority-matrix.md`

```markdown
| BC | Domínio Crítico (1–5) | Risco Transacional (1–5) | Valor de Negócio (1–5) | Complexidade Funcional (1–5) | Priority Score | Prioridade | Wave Sugerida | Observações |
|---|---|---|---|---|---|---|---|---|
| BC-{N} | [valor] | [valor] | [valor] | [valor] | [score] | P{0-3} | Wave {N} | [INFERIDO] se valor neutro aplicado; indicador da rubrica que justifica a pontuação |
```

> **Coluna Observações**: OBRIGATÓRIA. Para cada critério pontuado, registrar o indicador objetivo da Rubrica Canônica que justifica o valor atribuído. Se o dado não foi encontrado nos artefatos de entrada, registrar: `"[INFERIDO] Dado ausente em {artefato} — valor neutro 3 aplicado"`. Esta coluna é a principal ferramenta de auditoria para garantir consistência entre gerações.

**Salvar em:** `projects/{project_name}/outputs/tobe/migration/migration-priority-matrix.md`
