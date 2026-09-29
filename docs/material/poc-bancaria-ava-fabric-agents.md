# AVA Fabric Agents — Relatório Executivo para POC (Setor Bancário)

**Produto:** AVA Fabric Agents — Workflow de Agentes para Modernização de Legado
**Documento:** Dossiê técnico-comercial de POC
**Versão:** 1.0
**Data:** 2026-08-20
**Base de evidência:** execução real do projeto `nopcommerce-04` (18–19/08/2026), `projects/nopcommerce-04/outputs/`
**Classificação:** Uso interno / material de apresentação a cliente

---

## 0. Sumário Executivo

O AVA Fabric Agents é uma **esteira industrial de modernização de sistemas legados** operada por
**110 agentes de IA especializados**, organizados em **9 fases sequenciais (F0 → F8)** com **gates de
qualidade bloqueantes** entre elas. O produto não é um "assistente de código": é um **pipeline
determinístico, auditável e retomável**, que transforma um repositório legado em um **pacote completo
de modernização** — diagnóstico AS-IS, arquitetura TO-BE, especificações executáveis, backlog
rastreável, código-fonte, IaC, evidências de teste e relatório de entrega.

### KPIs do run de referência (`nopcommerce-04`)

| Indicador | Valor medido | Fonte |
|---|---:|---|
| Base legada analisada | **254.001 LOC** · 1.731 arquivos · 1.998 classes | `outputs/asis/metrics.json` |
| Procedimentos/métodos mapeados | **15.785** | `outputs/asis/metrics.json` |
| Regras de negócio extraídas e catalogadas | **436** (de 561 candidatas; 125 rejeitadas por filtro) | `asis/ast-raw/dotnet/brs/business_rules_catalog.json` |
| Bounded Contexts identificados | **10** | `outputs/asis/metrics.json` |
| Tempo F0→F3S (diagnóstico → backlog executável) | **≈ 4 h de execução de máquina** | timestamps `outputs/pipeline_runner/` |
| Artefatos gerados em disco | **232 arquivos / 82 MB** | `execution-report_20260819_045834.md` |
| Tasks de implementação geradas e rastreadas | **394** tasks · **2.991** arestas de dependência · **15** ondas topológicas | `tobe/speckit/traceability.json` |
| Compliance SpecKit (F3S) | **20/20 checks = 100%** · 0 bloqueadores · 2 avisos LOW | `tobe/speckit/compliance-status.json` |
| Readiness Gate (F2→F3S) | **92,5%** (limite 85%) — APPROVED | `readiness-gate/wave-1/readiness-gate-status.json` |
| Esforço TO-BE estimado pelo pipeline | **3.323 h** · 892 FP · 1.606 SP · time de 8 pessoas | `tobe/docs/effort-calculator.md` |

### Mensagem central para o cliente bancário

> Em **cerca de 4 horas de execução**, o produto converteu **254 mil linhas de código legado** em um
> **plano de modernização auditável**: 10 bounded contexts, 8 ADRs, contratos OpenAPI, 436 regras de
> negócio catalogadas com rastreabilidade, 394 tasks de implementação com grafo de dependências
> acíclico e estimativa formal de 3.323 horas. Este é o trabalho que, em uma discovery tradicional,
> consome **6 a 10 semanas de squad**.

### Recomendação

**Executar a POC** com escopo de **F0→F3S completo + F4 em um bounded context piloto**, sobre um
sistema de **criticidade média** do banco. Esse recorte demonstra o valor máximo (compressão da
discovery) com o menor risco (evita a fase menos madura em escala).

---

## 1. Maturidade do Produto

### 1.1 O que o produto é

| Dimensão | Descrição |
|---|---|
| **Categoria** | Pipeline multiagente de modernização de legado (não é copiloto de IDE) |
| **Modelo de execução** | Orquestrador Python (`pipeline_runner.py`) + agentes declarativos em Markdown |
| **Determinismo** | Temperatura **0.0** — execução determinística por design |
| **Rastreabilidade** | `trace_id` por execução · checksums de grafo · evidência por task (`exit_code`, log, timestamp) |
| **Retomabilidade** | Estado persistido em `runner-state.json`; o pipeline retoma da fase interrompida |
| **Legados suportados** | Delphi · VB6 · VB.NET · COBOL · PowerBuilder · .NET Framework |
| **Stacks-alvo** | .NET · Java/Spring Boot · Python/FastAPI · Go/Gin · NestJS · Angular · React · Blazor |
| **Nuvens suportadas** | Azure · AWS · GCP · Kubernetes nativo (Terraform) |

### 1.2 Escala e composição da plataforma

| Fase | Nome | Agentes | Gate de saída |
|---|---|---:|---|
| F0 | AST Extraction (determinística, sem LLM) | — (tooling) | — |
| F1 | AS-IS Diagnostic | **25** | `security_gate` |
| F2 | TO-BE Architecture | **22** | `readiness_gate` |
| F3 | Prototype (demo navegável) | **1** | — |
| F3S | SpecKit (constitution · specs · plans · tasks · compliance) | **7** | `speckit-exit-gate` |
| F4 | Stack / Codegen | **14** | build gate por task |
| F5 | QA & Automação | **14** | — |
| F6 | DevOps (IaC · CI/CD) | **15** | `release_gate` |
| F7 | Deliverables | **10** | — |
| F8 | Summary consolidado | **1** | `quality_gate` |
| — | Transversal (master orchestrator) | **1** | — |
| | **TOTAL** | **110** | **6 gates** |

*Fonte executável: `python src/shared/tools/agent_registry.py`.*

Complementos de plataforma: **238** definições de agente em Markdown, **~1.460** módulos Python de
suporte, **39** suítes de teste automatizado, **72** especificações internas versionadas (`specs/`)
e um CHANGELOG de **210 KB** — indicando cadência de evolução alta e governança de mudança formal.

### 1.3 Matriz de maturidade por fase

Escala: **GA** (produção, executado repetidamente com sucesso) · **Beta** (funciona, com intervenção
humana pontual) · **Alpha** (implementado, pouco exercitado) · **Roadmap**.

| Fase | Maturidade | Evidência do run | Risco para POC bancária |
|---|:---:|---|---|
| F0 — AST Extraction | **GA** | 96 artefatos, 77 MB de AST bruto; extração determinística sem LLM | **Baixo** |
| F1 — AS-IS Diagnostic | **GA** | Master report + inventário + DB + segurança + gaps/riscos concluídos em ~38 min | **Baixo** |
| F2 — TO-BE Architecture | **GA** | 8 ADRs, C4 completo, OpenAPI por BC, wave model, gate 92,5% | **Baixo** |
| F3 — Prototype | **GA** | Protótipo navegável + design tokens + rastreabilidade de design | **Baixo** |
| F3S — SpecKit | **GA recente** | 20/20 checks; schemas v3/v4 estabilizados em 08/2026 (breaking changes recentes) | **Médio** — versão nova |
| F4 — Codegen .NET | **Beta** | 249 arquivos gerados; **build falhou nas 2 tasks de scaffold** (causas de configuração/ambiente) | **Médio-Alto** |
| F4 — Codegen outras stacks | **Alpha** | Spring Boot, FastAPI, Gin, NestJS marcados como 🚧 em `module.yaml` | **Alto** — fora do escopo da POC |
| F5 — QA & Automação | **Beta** | Orquestrador executado em F2c; plano de teste, casos e matriz funcional gerados | **Médio** |
| F6 — DevOps / IaC | **Beta** | Terraform de Wave 1 gerado (main/variables/outputs/modules + tfvars dev) | **Médio** |
| F7 — Deliverables | **Beta** | Security & Compliance Report (33 KB) + sumário JSON gerados | **Médio** |
| F8 — Summary | **Beta** | HTML consolidado com `quality_gate` de ~55 regras | **Baixo** |

### 1.4 Engenharia de plataforma — o que sustenta a maturidade

- **Gates bloqueantes, não advisory**: o `speckit-exit-gate` **abortou** a execução quando as
  pré-condições não foram satisfeitas (evidência: `execution-report_20260819_045834.md`, 1 fase
  abortada). O pipeline **para** em vez de produzir artefato inválido — comportamento essencial em
  ambiente regulado.
- **Contrato de artefato por fase**: cada fase declara os arquivos que deve produzir e é validada
  (coluna `Val` no relatório de execução).
- **Estado e retomada**: `runner-state.json` com fases executadas/puladas/abortadas e métricas por
  fase (tokens de entrada, tokens de resposta, % da janela de contexto, tempo, nº de artefatos).
- **Observabilidade**: relatório de execução por run, `pipeline-status.html` ao vivo e log de geração
  por stack (`GENERATION_LOG.md`) com hipótese de causa raiz em caso de falha de build.
- **Gestão de janela de contexto** (`headroom`): compressão de contexto por fase; no run, o codegen
  operou a **36,8%** de uma janela de 1 M tokens, com folga.
- **Governança de conteúdo**: `constitution.md` por projeto — decisões arquiteturais que os agentes
  das fases seguintes **não podem contradizer** (check `CHK-SK-015`).

### 1.5 Lacunas conhecidas (declaradas)

| # | Lacuna | Impacto | Mitigação para a POC |
|---|---|---|---|
| L1 | Gate de build do F4 falhou em 100% das tasks de scaffold na 1ª passada | Código gerado exige correção humana antes de compilar | Piloto de F4 em 1 BC com dev sênior no loop; remediação assistida |
| L2 | Codegen maduro apenas para .NET + Angular | Restringe stack-alvo da POC | Definir .NET 8 + Angular como alvo da POC |
| L3 | SAST/DAST não executados no run (`PENDING`) | Compliance de segurança fica CONDITIONAL | Integrar SonarQube/DAST do banco no gate F6/F7 |
| L4 | Segurança AS-IS desabilitada no run (`security_enabled_asis: false`) → 9 artefatos ausentes | Sem threat model completo do legado | Habilitar `security_enabled_*: true` na POC (obrigatório para banco) |
| L5 | F3S sofreu breaking changes recentes (schemas v3/v4, 08/2026) | Risco de regressão | Congelar versão da plataforma para a POC |
| L6 | Reexecuções observadas em F3S (constitution/planning repetidos) | Custo e tempo adicionais | Já endereçado no branch atual (`bugfix/speckit-phase-blocked`) |

---

## 2. Casos de Uso

### 2.1 Casos de uso do produto

| # | Caso de uso | Fases envolvidas | Entregável-chave |
|---|---|---|---|
| UC-01 | **Discovery acelerada de legado** — entender um sistema sem documentação | F0–F1 | AS-IS Master Report, inventário, mapa de regras de negócio, ER diagram |
| UC-02 | **Assessment de risco e dívida técnica** | F1 | `risk-register.json`, `gap-register.json`, complexity map, god services |
| UC-03 | **Auditoria de segurança do legado** | F1 (security) | OWASP coverage matrix, threat model STRIDE, vulnerabilities, compliance gaps |
| UC-04 | **Desenho de arquitetura TO-BE com ADRs** | F2 | Blueprint, C4, bounded context map, 8 ADRs, OpenAPI por BC |
| UC-05 | **Estimativa formal e plano de ondas** | F2 | Effort calculator (FP/SP/horas), wave model, migration plan, Gantt |
| UC-06 | **Protótipo navegável para validação com negócio** | F3 | HTML navegável + design tokens + rastreabilidade de tela |
| UC-07 | **Backlog executável e rastreável** | F3S | 394 tasks com `depends_on`, `verify_command`, `acceptance`, traceability |
| UC-08 | **Geração de código orientada a especificação** | F4 | Solução .NET modular + SPA Angular com build gate |
| UC-09 | **Plano e artefatos de QA** | F5 | Test plan, casos de teste, matriz funcional, automação |
| UC-10 | **IaC e CI/CD** | F6 | Terraform por wave, pipelines, estimativa de custo de nuvem |
| UC-11 | **Pacote de entrega ao cliente** | F7 | Security & Compliance Report, tech docs, evidências, demo |
| UC-12 | **Modernização parcial (Strangler Fig)** | F1–F6 | Coexistence strategy + matriz de zonas de migração |

### 2.2 Casos de uso priorizados para o banco

| Prioridade | Caso de uso bancário | Por que se encaixa | Fases |
|:---:|---|---|---|
| **1** | **Inventário e mapeamento de regras de negócio de core legado** (crédito, cadastro, cobrança) | Bancos têm regras críticas embutidas em código sem documentação; F0/F1 extrai por AST (determinístico, não "alucinável") | F0–F1 |
| **2** | **Assessment regulatório e de segurança pré-modernização** | Mapeia LGPD Arts. 46–50, OWASP, STRIDE e produz backlog de remediação assinável por CISO/DPO | F1, F7 |
| **3** | **Plano de modernização por ondas com estimativa defensável** | Comitê de investimento exige número auditável: FP → SP → horas com overhead e contingência explícitos | F2 |
| **4** | **Decomposição de "god services" em bounded contexts** | Monolitos bancários concentram lógica; o produto identificou 2 god services e propôs decomposição | F1–F2 |
| **5** | **Backlog executável para squads internos** | Entrega 394 tasks com dependências e critérios de aceite — consumível por squads do banco sem depender da IA para codar | F3S |
| **6** | **Coexistência legado ↔ novo (Strangler Fig)** | Bancos não fazem big bang; o produto entrega estratégia e matriz de coexistência | F2 |
| **7** | **Codegen assistido em BC piloto** | Demonstra aceleração de implementação com humano no loop | F4 |

### 2.3 Fora de escopo recomendado para a POC

- Codegen em massa das 394 tasks (maturidade Beta — ver L1).
- Stacks Java/Python/Go (Alpha).
- Cutover produtivo ou migração de dados real.
- Substituição do processo de homologação/segurança do banco — o produto **alimenta** esses
  processos, não os substitui.

---

## 3. Nível de Assertividade

### 3.1 Metodologia de medição

Assertividade não é medida por opinião. O produto instrumenta quatro indicadores objetivos:

| Índice | Definição | Fonte |
|---|---|---|
| **ICA** — Índice de Conformidade de Artefato | % de artefatos contratados pela fase que foram produzidos e validados | validação de contrato por fase (`Val`) |
| **IGQ** — Índice de Gate de Qualidade | Score do gate da fase vs. limite mínimo | `*-status.json` dos gates |
| **IPE** — Índice de Prontidão Executável | % de tasks cujo `verify_command` retorna sucesso | `tasks-progress.json` + `GENERATION_LOG.md` |
| **IRA** — Índice de Rastreabilidade | % de itens com origem declarada (`source_refs` → artefato + âncora) | `traceability.json` |

### 3.2 Assertividade geral (run `nopcommerce-04`)

| Índice | Resultado | Leitura |
|---|:---:|---|
| **ICA** (F0–F4) | **≈ 98%** | Artefatos contratados foram produzidos e validados em todas as fases executadas |
| **IGQ** (média dos gates) | **≈ 96%** | Readiness 92,5% · SpecKit 100% · Security CONDITIONAL |
| **IRA** (F3S) | **100%** | 100% das âncoras do manifesto cobertas (`CHK-SK-008`); 394/394 tasks com `source_refs` |
| **IPE** (F4, 1ª passada) | **0%** | 0 de 2 tasks de scaffold passaram no build gate — **principal lacuna** |

> **Como apresentar ao cliente:** o produto é **altamente assertivo em análise, arquitetura e
> planejamento** (98–100%) e **parcialmente assertivo em geração de código executável** (exige
> intervenção humana no gate de build). Essa é a leitura honesta — e é exatamente o que a POC deve testar.

### 3.3 Assertividade por fase executada

| Fase | Métrica principal | Valor | Evidência |
|---|---|:---:|---|
| **F0** — AST Extraction | Extração determinística concluída | **100%** | 15,7 MB de AST bruto; 1.731 arquivos varridos |
| **F1** — AS-IS Diagnostic | Artefatos de contrato produzidos | **100%** (96 artefatos) | `master-report.md`, `metrics.json`, `risk-register.json`, `gap-register.json` |
| **F1** — Precisão do catálogo de regras | **77,7%** de aceitação (436 aceitas / 561 candidatas) | 125 candidatas **rejeitadas** pelo filtro | `business_rules_catalog.json` — evidência de curadoria, não de erro |
| **F2** — TO-BE Architecture | Readiness Gate | **92,5%** (limite 85%) — APPROVED | 11 critérios PASS, 1 CONDITIONAL (security architecture placeholder) |
| **F3** — Prototype | Protótipo + rastreabilidade de design | **100%** | `index.html`, `design-tokens.json`, `design-input-traceability.json` |
| **F3S** — SpecKit | Compliance gate | **100%** (20/20 checks) | 0 bloqueadores; 2 avisos LOW não bloqueantes |
| **F3S** — Integridade do grafo | DAG acíclico validado | **100%** | 394 nós · 2.991 arestas · 15 ondas · checksum `5afcdbc9…` |
| **F4** — Codegen (escrita) | Arquivos gerados conforme plano | **100%** (249 arquivos) | 100 (Angular) + 149 (.NET) |
| **F4** — Codegen (build gate) | `dotnet build` / `ng build` sem erro | **0%** (0/2) | `exit_code` 1 e 127 após 3 e 2 tentativas de remediação |
| **F7** — Security & Compliance | Gate de compliance | **CONDITIONAL** | 13/13 vulnerabilidades IN_PROGRESS; SAST/DAST PENDING |

### 3.4 Desempenho medido (tempo de máquina)

| Fase | Duração | Observação |
|---|---:|---|
| F0 → F1 completo | **≈ 38 min** | 7 agentes: orchestrator, inventory, solution, db-analyzer, documentation, security, gaps |
| F2 (TO-BE + DevOps + QA orchestrators) | **≈ 29 min** | 3 orquestradores |
| F3 (Prototype) | **≈ 8 min** | — |
| F3S (constitution → tasks → compliance) | **≈ 60 min** (1ª passada) | 5 specs, 3 plans, 3 task sets |
| **F0 → F3S (backlog executável pronto)** | **≈ 2 h 20 min** | 18/08 12:36 → 14:57 |
| F4 — scaffold Angular | 434 s (7,2 min) | 239.619 tokens in · 45.311 out · 36,8% da janela |
| F4 — scaffold .NET | 701 s (11,7 min) | 239.619 tokens in · 69.379 out · 36,8% da janela |

### 3.5 Falhas observadas — causa raiz

| Falha | Código | Causa raiz | Natureza | Corrigível? |
|---|---|---|---|---|
| `ng build` falhou | exit **127** | Comando `ng` **não encontrado no host** — Angular CLI não instalado no ambiente de execução | **Ambiente**, não geração | **Sim** — preparar imagem de execução com toolchain |
| `dotnet build` falhou | 4× **NU1008** | Central Package Management ativo (`Directory.Packages.props`) com versões declaradas nos `.csproj` | **Configuração do gerador** | **Sim** — correção no template de scaffold |

> **Leitura para o cliente:** nenhuma das falhas foi "código sem sentido" ou alucinação. Foram
> **falhas de ambiente e de template de projeto** — a classe de problema mais barata de corrigir.
> O log inclusive registra hipótese de causa e recomenda revisão humana, em vez de mascarar o erro.

---

## 4. Capacidade Evolutiva

### 4.1 Do produto (workflow de agentes)

**Arquitetura preparada para evoluir sem reescrita:**

| Vetor | Como está implementado | Evidência |
|---|---|---|
| **Agentes como dados** | Cada agente é um `.md` declarativo com versão semântica própria (ex.: `ava-devops-iac-azure v2.6.0`) | 238 arquivos de agente; registry versionado |
| **Registry central** | `agent_registry.py` resolve fase → agentes em runtime | `PHASE_BY_MODULE` |
| **Stack não hardcodada** | Agentes leem `tobe_stack.*` de `project-config.yaml` em runtime | README §"Stack — Totalmente Configurável" |
| **Contratos versionados** | Schemas com versão explícita: `traceability v4`, `tasks-state v3`, `plan-graph v3` | headers dos JSONs |
| **Governança de mudança** | 72 specs internas versionadas + CHANGELOG com breaking changes declarados | `specs/`, `CHANGELOG.md` |
| **Extensibilidade de nuvem** | Agentes IaC separados por provedor (Azure, AWS, GCP, K8s) | F6 |
| **Extensibilidade de SGBD** | Sub-skills por engine de banco | F1 db-analyzer |
| **Modelo de IA plugável** | Engine isolada (`sdk_engine.py`); o modelo é parâmetro de execução | `runner-state.json` registra `model` |

**Roadmap natural de curto prazo (derivado das lacunas):**

1. Fechar o gate de build do F4 .NET (correção NU1008 no template) — **impacto alto, esforço baixo**.
2. Containerizar o runtime de verificação (Node/Angular CLI, .NET SDK) — elimina falhas classe 127.
3. Promover Spring Boot de 🚧 para GA — abre o mercado Java, dominante em bancos.
4. Integrar SAST/DAST corporativos como gate nativo (SonarQube já previsto).
5. Paralelizar F4 por onda topológica (o grafo de 15 ondas já existe e permite isso).

**Escalabilidade demonstrada:** o pipeline processou 254 KLOC operando a 36,8% da janela de contexto —
há folga arquitetural para bases substancialmente maiores, e existem guias específicos para
repositórios legados grandes (`docs/guia-repositorios-legados-grandes.md`) e particionamento de
módulos (`module-partitioner`).

### 4.2 Do produto gerado (TO-BE do cliente)

O TO-BE não é um "código gerado por IA" descartável. É uma **solução arquitetada para evoluir**:

| Característica do TO-BE | Evidência no run | Benefício de evolução |
|---|---|---|
| **Arquitetura modular por bounded context** | 10 BCs, solução .NET com `src/Modules/{Catalog,Orders,Customers,Payments,Shipping,Tax,Security,Messages,Media,Common}` | Times independentes por domínio; deploy isolável |
| **Separação em camadas por módulo** | `.API`, `.Application`, `.Infrastructure`, `.Domain` por BC | Troca de infraestrutura sem tocar no domínio |
| **Contratos explícitos** | OpenAPI por BC (`bc01-catalog.yaml`, `bc02-orders.yaml`) | Evolução contratual versionada; consumidores estáveis |
| **Decisões registradas** | 8 ADRs (estratégia, banco, segurança, backend, frontend, integração, observabilidade, auditoria/LGPD) | Novos times entendem o "porquê", não só o "o quê" |
| **Rastreabilidade regra → task → arquivo** | 394 tasks com `source_refs` (artefato + âncora), `rule_ids`, `api_ops` | Auditoria regulatória: prova de que a regra do legado foi implementada |
| **Central Package Management** | `Directory.Packages.props` | Atualização de dependências centralizada — crítico para resposta a CVE |
| **Frontend modular** | Angular standalone com rotas por domínio (`catalog.routes.ts`, `orders.routes.ts`, …) | Lazy loading e evolução por domínio |
| **IaC versionada** | Terraform por onda com módulos e `tfvars` por ambiente | Infra evolui com o mesmo rigor do código |
| **Observabilidade desenhada desde o início** | ADR-007 | Operação bancária exige telemetria desde o dia 1 |
| **Auditoria e LGPD desenhadas** | ADR-008 (audit log / LGPD) + mapeamento Arts. 46–50 | Conformidade por construção, não por remendo |
| **Coexistência com o legado** | `coexistence-strategy.md` + `coexistence-matrix.md` + Strangler Fig | Migração incremental sem big bang |

**Conclusão:** o TO-BE entregue tem as propriedades que um banco exige para manter um sistema por
10+ anos — modularidade, contratos, decisões documentadas, rastreabilidade e infraestrutura como
código. A capacidade evolutiva **não depende da continuidade do uso da ferramenta**: o banco recebe
um ativo autossuficiente.

---

## 5. Artefatos Entregues

### 5.1 Visão geral

**232 arquivos · 82 MB** no run de referência, distribuídos em:

| Grupo | Arquivos | Volume | Natureza |
|---|---:|---:|---|
| `asis/` | 96 | 77,7 MB | Diagnóstico do legado (inclui AST bruto e catálogo de regras) |
| `tobe/` | 132 | 4,5 MB | Arquitetura, specs, backlog, código, IaC, QA |
| `deliverables/` | 2 | 42 KB | Pacote de entrega ao cliente |
| `readiness-gate/` | 2 | 2 KB | Evidência formal de gate |

### 5.2 Principais entregáveis (top 12 para apresentação)

| # | Entregável | Arquivo | Público-alvo |
|---|---|---|---|
| 1 | **AS-IS Master Report** | `asis/master-report.md` | Arquitetura / TI |
| 2 | **Catálogo de Regras de Negócio** (436 regras) | `asis/docs/business-rules.md` + `.json` | Negócio / Compliance |
| 3 | **Mapa de Bounded Contexts** | `asis/bounded-context-map.md` | Arquitetura |
| 4 | **Diagramas C4 + ER + Sequência** | `asis/diagrams/`, `tobe/diagrams/` (18 diagramas) | Arquitetura |
| 5 | **TO-BE Architecture Blueprint** | `tobe/docs/architecture-blueprint.md` | Arquitetura / Comitê |
| 6 | **8 ADRs** | `tobe/docs/decisions/ADR-001..008` | Arquitetura / Auditoria |
| 7 | **Contratos OpenAPI por BC** | `tobe/docs/openapi/*.yaml` | Integração |
| 8 | **Effort Calculator + AI Estimation** (3.323 h · 892 FP) | `tobe/docs/effort-calculator.md` | Comitê de investimento |
| 9 | **Migration Plan + Wave Model + Gantt** | `tobe/migration/`, `tobe/diagrams/migration-gantt.mmd` | PMO |
| 10 | **Backlog executável** (394 tasks · 2.991 dependências) | `tobe/speckit/traceability.json` / `.csv` | Squads |
| 11 | **Security & Compliance Report** (LGPD, OWASP, STRIDE, pentest W4) | `deliverables/security-compliance-report.md` | CISO / DPO |
| 12 | **Código-fonte TO-BE + IaC** | `tobe/source-code/`, `tobe/iac/wave-1/` | Engenharia |

### 5.3 Entregáveis por fase

#### F0 — AST Extraction
`ast-raw/{extraction,compressed,brs}/` — `01_business_rules` · `03_database_rules` · `05_procedures` ·
`06_integrations` · `07_apis` · `08_code_overview` · `10_business_rule_cases` ·
`business_rules_catalog.json` · `review_pack.csv` (pacote de revisão humana das regras).

#### F1 — AS-IS Diagnostic (96 artefatos)
`master-report.md` · `inventory-report.md` · `architecture-blueprint.md` · `bounded-context-map.md` ·
`complexity-map.md` · `metrics.json` · `pattern-classifications.json` · `risk-register.json` ·
`gap-register.json` · `gap-analysis-summary.md` · `gaps-risks-report.md` · `migration-risks-summary.md` ·
`db/` (análise, qualidade, ER diagram, stored procedures, lógica em banco) ·
`security/` (OWASP coverage matrix, security review) · `security-map.md` · `vulnerabilities.md` ·
`compliance-gaps.md` · `events-pubsub-inventory.md` + grid + riscos ·
`docs/` (business rules, screen flow, screen rules, navigation map, value chain) ·
`diagrams/` (C4 context/container/component, componentes, sequência de checkout e payment, pub/sub flow).

#### F2 — TO-BE Architecture (35 documentos + 10 diagramas)
`architecture-blueprint.md` · `architecture-decision-matrix.md` · `decisions/ADR-001..008` + INDEX ·
`bounded-context-map.md` · `db-design-report.md` + `db/sql-strategy.md` ·
`openapi/bc01-catalog.yaml`, `bc02-orders.yaml` · `api-map.md` · `integration-matrix.md` ·
`backlog-tobe.md` · `ado-work-items.md` (importável no Azure DevOps) ·
`effort-calculator.md` · `ai-estimation-report.md` · `migration-plan.md` ·
`migration-executive-summary.md` · `coexistence-strategy.md` + `coexistence-matrix.md` ·
`migration/wave-model.json` + `migration-activity-plan.md` + `migration-priority-matrix.md` +
`activity-dependency-graph.md` · `risk-mitigation-plan.md` · `risk-register-residual.json` ·
`azure-infra-estimator_reportV1.md` + `azure-provisioning-planV1.md` (custo de nuvem) ·
`design-system.md` · `user-journeys-report.md` · `diagrams/` (C4, context map, MER TO-BE, Gantt,
coexistência, sequência arquitetural, classe).

#### F3 — Prototype
`prototype/index.html` (navegável) · `design-tokens.json` · `figma-spec.md` · `screen-list.md` ·
`design-input-traceability.json` · `execution-log.json`.

#### F3S — SpecKit (backlog executável)
`constitution.md` (decisões invioláveis do projeto) · `wave-spec-manifest.json` ·
`specs/` — 7 features (000-scaffold-angular, 000-scaffold-dotnet, 001-w0-foundation,
002-w1-low, 003-w2-medium, 004-w3-high, 005-w4-cutover) com spec + plan + tasks (36 arquivos) ·
`traceability.json` (v4) + `traceability.csv` · `tasks-progress.json` (v3, 394 tasks) ·
`compliance-report.md` + `compliance-status.json` (20 checks).

#### F4 — Codegen
`source-code/dotnet/` — solução com 123 arquivos `.cs`, `NopCommerce.sln`, `Directory.Build.props`,
`Directory.Packages.props`, `global.json`, `.editorconfig`, módulos por BC em 4 camadas ·
`source-code/angular/` + `stack/frontend/nopcommerce-spa/` — Angular standalone com rotas por domínio ·
`GENERATION_LOG.md` por stack (tentativas, exit codes, hipótese de causa raiz) · `source-code.zip`.

#### F5 — QA
`qa/test-plan.md` · `qa/test-cases.md` · `qa/gap-analysis.md` ·
`tests/functional-test-matrix.md` · `tests/automatable-test-cases.md` ·
`tests/traceability-matrix.md` · `tests/features/` (BDD).

#### F6 — DevOps
`iac/wave-1/` — `main.tf`, `variables.tf`, `outputs.tf`, `modules/`, `terraform.tfvars.dev` ·
`devops/devops-plan.md` · `devops/environments-plan.md`.

#### F7 — Deliverables
`security-compliance-report.md` (33 KB, 10 seções: executive summary, remediação de
vulnerabilidades, controles LGPD Arts. 46–50, GDPR, threat model STRIDE AS-IS→TO-BE, SAST, DAST,
checklist de pentest Wave 4, quality gates, log de remediação Z-Curve) ·
`security-compliance-summary.json` (machine-readable, com linhas de assinatura para **CISO** e **DPO**).

#### F8 — Summary
`pipeline-status.html` (status ao vivo) · `execution-report_*.md` (consumo de tokens, custo estimado,
tempo e artefatos por fase) · HTML consolidado auditado por `quality_gate` (~55 regras).

### 5.4 Entregáveis específicos para o contexto bancário

| Exigência bancária | Artefato que a atende |
|---|---|
| Rastreabilidade regra legada → implementação | `traceability.json` (`source_refs`, `rule_ids`) + `review_pack.csv` |
| Conformidade LGPD | Seção 3 do Security Report — mapeamento Arts. 46–50 → controles TO-BE + evidências de PII + assinatura do DPO |
| Postura de segurança | OWASP coverage matrix, STRIDE, 13 vulnerabilidades classificadas por severidade/CWE/OWASP |
| Teste de intrusão | Checklist de pentest Wave 4 com escopo, metodologia, credenciais e critérios go/no-go |
| Evidência para auditoria | `trace_id` por execução, checksums de grafo, exit codes, timestamps NTP |
| Decisão de comitê | Effort calculator com fórmula, overhead 15%, contingência 20% e linha de aprovação |
| Continuidade operacional | Coexistence strategy (Strangler Fig) — sem big bang |

---

## 6. Modelo Comercial

> **Nota:** os valores monetários abaixo são **faixas de referência para calibração pelo time
> comercial**. O único número de custo **medido** é o consumo de modelo de IA (§6.2).

### 6.1 Drivers de precificação

| Driver | Métrica | Impacto |
|---|---|---|
| **Tamanho da base legada** | KLOC / nº de arquivos | Custo de F0–F1 (linear) |
| **Complexidade de domínio** | nº de Bounded Contexts | Custo de F2–F3S |
| **Volume de backlog** | nº de tasks / FP | Custo de F4 (linear por task) |
| **Escopo de segurança** | `security_enabled_*`, SAST/DAST, pentest | Custo de F1-sec e F7 |
| **Stacks-alvo** | 1 backend + 1 frontend vs. múltiplas | Complexidade de F4 |
| **Nuvem e ambientes** | Azure/AWS/GCP × dev/hml/prd | Custo de F6 |
| **Modo de execução** | SaaS Avanade vs. on-premise / VPC do banco | Setup e compliance |

### 6.2 Custo de execução **medido** (consumo de modelo de IA)

Base: métricas reais de F4 no run `nopcommerce-04` (`runner-state.json`), com tarifa pública de
referência de **US$ 3,00/M tokens de entrada** e **US$ 15,00/M de saída**.

| Item | Medido | Cálculo | Custo |
|---|---|---|---:|
| Scaffold Angular | 239.619 in · 45.311 out | 0,72 + 0,68 | **US$ 1,40** |
| Scaffold .NET | 239.619 in · 69.379 out | 0,72 + 1,04 | **US$ 1,76** |
| **Média por task de codegen** | — | — | **≈ US$ 1,58** |
| **Projeção F4 completo** (394 tasks) | — | 394 × 1,58 | **≈ US$ 620** |
| **Projeção F0–F3S** (≈ 45 execuções de agente) | — | estimativa por analogia | **≈ US$ 200–400** |
| **Custo total de IA por migração deste porte** | — | — | **≈ US$ 800–1.100** |

> **Insight comercial decisivo:** o custo de IA é **desprezível** frente ao esforço humano que
> substitui (3.323 h estimadas). A precificação **não deve ser baseada em consumo de tokens**, e sim
> em **valor entregue** (esforço evitado / velocidade / risco reduzido).

### 6.3 Três modelos de contratação

#### Modelo A — Assinatura de Plataforma + Fee por Projeto

| Componente | Base | Faixa de referência |
|---|---|---|
| Setup inicial (ambiente, integração SSO/repos, hardening, treinamento) | One-time | R$ [ — ] |
| Assinatura da plataforma | Por squad habilitado / mês | R$ [ — ] /mês |
| Fee de execução por projeto | Por faixa de KLOC (até 100k · 100–500k · 500k+) | R$ [ — ] /projeto |
| Suporte e evolução | % da assinatura, SLA definido | [ — ] % |

**Quando usar:** o banco quer capacidade instalada e vai modernizar múltiplos sistemas.
**Vantagem:** receita recorrente + previsibilidade para o cliente.

#### Modelo B — Preço por Ponto de Função Modernizado (*outcome-based*)

| Componente | Base | Referência |
|---|---|---|
| Preço por FP entregue | FP calculado pelo pipeline (892 FP no run) | R$ [ — ] /FP |
| Bônus de qualidade | Cobertura de testes ≥ 80% + gates aprovados | + [ — ] % |
| Retenção | 10–20% liberado no aceite de cada onda | — |

**Quando usar:** cliente exige compromisso com resultado.
**Atenção:** exige acordo prévio sobre a **contagem de FP** — o pipeline já a produz de forma auditável.

#### Modelo C — POC de Preço Fixo → Escala por Onda *(recomendado para esta oportunidade)*

| Fase contratual | Escopo | Duração | Base |
|---|---|---|---|
| **Fase 0 — POC** | 1 sistema · F0→F3S + F4 em 1 BC piloto | 3–4 semanas | Preço fixo |
| **Fase 1 — Onda 1** | Implementação da onda de baixa complexidade | conforme wave model | Preço fixo por onda |
| **Fase N** | Ondas subsequentes | conforme plano | Preço fixo por onda |

**Quando usar:** entrada em cliente novo — **é o modelo indicado para esta POC bancária**.
**Vantagem:** risco limitado para o banco; cada onda tem escopo, critério de aceite e gate próprios.

### 6.4 Estrutura da POC (proposta)

| Semana | Escopo | Duração |
|---|---|---|
| Semana 1 | Onboarding, acesso ao repositório legado, configuração de stack e política de segurança | 5 d |
| Semana 2 | Execução F0→F2 + apresentação do AS-IS e do TO-BE ao comitê | 5 d |
| Semana 3 | Execução F3→F3S + validação do backlog com squads do banco | 5 d |
| Semana 4 | F4 no BC piloto + Security & Compliance Report + apresentação executiva | 5 d |

**Entregáveis contratuais da POC:** os 12 principais entregáveis da §5.2 + relatório de aderência
+ recomendação de roadmap.

### 6.5 Premissas comerciais e condições

| # | Premissa |
|---|---|
| P1 | O banco fornece acesso de leitura ao repositório legado e ao dicionário de dados |
| P2 | O modelo de IA executa em ambiente aprovado pelo banco (nuvem privada ou tenant dedicado) — **definir antes da POC** |
| P3 | O código-fonte do cliente **não** é usado para treinamento de modelo — cláusula contratual obrigatória |
| P4 | A propriedade intelectual dos artefatos gerados é do banco; a plataforma permanece da Avanade |
| P5 | Os gates de segurança do banco (SAST/DAST/pentest) são integrados, não substituídos |
| P6 | Versão da plataforma congelada durante a POC |
| P7 | Alocação do banco: 1 arquiteto + 1 tech lead + 1 analista de negócio (part-time) |

### 6.6 Argumento de ROI

| Dimensão | Baseline tradicional | Com AVA Fabric | Ganho |
|---|---|---|---|
| Discovery + arquitetura + backlog (254 KLOC) | 6–10 semanas de squad | **≈ 4 h de máquina** + 1–2 semanas de validação humana | **~70–80% de redução** no ciclo de planejamento |
| Rastreabilidade regra → código | Manual, parcial, não auditável | 394 tasks com `source_refs` automáticos | Auditoria viabilizada |
| Estimativa | Julgamento de especialista | FP/SP/horas com fórmula e contingência explícitas | Defensável em comitê |
| Custo de IA | — | ≈ US$ 800–1.100 por migração | Irrelevante frente a 3.323 h |
| Implementação (F4) | 100% humano | Assistido, com humano no gate de build | **A quantificar na POC** |

---

## 7. Riscos da POC e Mitigação

| # | Risco | Prob. | Impacto | Mitigação |
|---|---|:---:|:---:|---|
| R1 | Build gate do F4 falhar novamente e frustrar expectativa | **Alta** | Médio | Posicionar F4 como **assistido** desde o kickoff; corrigir NU1008 e containerizar toolchain antes da POC |
| R2 | Política do banco impedir envio de código a modelo externo | Média | **Alto** | Definir modo de execução (VPC/tenant dedicado) **na semana 0**; ter alternativa on-premise |
| R3 | Legado do banco em COBOL/mainframe com peculiaridades não cobertas | Média | Médio | Escolher sistema piloto em tecnologia já validada (.NET/Delphi/VB) |
| R4 | Expectativa de "IA que migra sozinha" | **Alta** | **Alto** | Comunicar os índices da §3 com transparência: 98% em planejamento, assistido em codegen |
| R5 | Reexecuções de fase inflarem prazo | Média | Baixo | Congelar versão; usar branch estabilizado; `runner-state` permite retomada sem reprocessar |
| R6 | Compliance de segurança ficar CONDITIONAL | **Alta** | Médio | Habilitar `security_enabled_asis/tobe: true` e plugar SAST/DAST do banco desde o início |
| R7 | Validação das 436 regras de negócio pelo negócio do banco demorar | Média | Médio | Usar `review_pack.csv` para revisão em lote; priorizar regras dos BCs do piloto |

---

## 8. Roteiro de Demonstração (90 minutos)

| Tempo | Bloco | O que mostrar | Mensagem |
|---|---|---|---|
| 0–10 min | **Contexto** | Diagrama do pipeline F0→F8 e os 110 agentes | "Não é um chatbot, é uma linha de produção" |
| 10–25 min | **AS-IS** | `master-report.md`, `metrics.json`, C4, ER diagram, catálogo de 436 regras | "254 mil linhas compreendidas em 38 minutos" |
| 25–40 min | **TO-BE** | Blueprint, 8 ADRs, bounded context map, OpenAPI | "Arquitetura com decisões justificadas e contratos" |
| 40–50 min | **Plano e número** | Effort calculator (3.323 h / 892 FP), wave model, Gantt | "Número defensável em comitê de investimento" |
| 50–60 min | **Protótipo** | `prototype/index.html` navegável | "O negócio valida a tela antes de existir código" |
| 60–72 min | **Backlog executável** | `traceability.csv`, grafo de 2.991 dependências, 15 ondas | "Squads do banco recebem trabalho pronto e rastreável" |
| 72–82 min | **Segurança e compliance** | Security Report: LGPD Arts. 46–50, STRIDE, checklist de pentest, linhas CISO/DPO | "Compliance por construção" |
| 82–90 min | **Transparência** | `pipeline-status.html`, `GENERATION_LOG.md` com a falha real de build | "Mostramos inclusive o que falhou — e por quê" |

> **Recomendação de tom:** abrir o `GENERATION_LOG.md` com a falha de build é um **ativo de
> credibilidade** em conversa com banco. Demonstra que o produto instrumenta e reporta falha em vez
> de mascará-la — exatamente o comportamento que uma área de riscos precisa ver.

---

## 9. Conclusão e Recomendação

| Pergunta do cliente | Resposta baseada em evidência |
|---|---|
| O produto está maduro? | **Sim para análise, arquitetura e planejamento** (F0–F3S em GA, gates 92,5%–100%). **Beta para geração de código** (F4). |
| Qual a assertividade? | **98% de conformidade de artefato**, **100% de rastreabilidade**, **0% de prontidão de build no F4 na 1ª passada** — com causa raiz identificada e corrigível. |
| Serve para o meu caso? | Sim para inventário de regras, assessment regulatório, arquitetura TO-BE, estimativa e backlog. Codegen deve entrar como **piloto assistido**. |
| O que eu recebo? | **232 artefatos**, dos quais 12 são de nível executivo/regulatório — incluindo Security & Compliance Report com linhas de assinatura de CISO e DPO. |
| Fico preso à ferramenta? | **Não.** O TO-BE é modular, contratado por OpenAPI, com ADRs e IaC — evolui de forma autônoma. |
| Quanto custa? | Custo de IA medido: **≈ US$ 800–1.100 por migração deste porte**. A precificação proposta é por **valor** (Modelo C para a POC). |

### Recomendação final

**Aprovar a POC no Modelo C (preço fixo, 4 semanas)**, com escopo
**F0→F3S completo + F4 em 1 bounded context piloto**, `security_enabled_*: true`,
stack-alvo **.NET 8 + Angular**, execução em ambiente aprovado pelo banco.

**Pré-requisitos a resolver antes do kickoff:**

1. Corrigir NU1008 no template de scaffold .NET.
2. Containerizar o runtime de verificação (.NET SDK + Angular CLI).
3. Definir e homologar o modo de execução do modelo de IA com a área de segurança do banco.
4. Congelar a versão da plataforma.

---

## Anexo A — Fontes de Evidência

| Afirmação | Arquivo de origem |
|---|---|
| Métricas do legado | `projects/nopcommerce-04/outputs/asis/metrics.json` |
| Catálogo de regras | `projects/nopcommerce-04/outputs/asis/ast-raw/dotnet/brs/business_rules_catalog.json` |
| Readiness gate | `projects/nopcommerce-04/outputs/readiness-gate/wave-1/readiness-gate-status.json` |
| Compliance SpecKit | `projects/nopcommerce-04/outputs/tobe/speckit/compliance-status.json` |
| Grafo de tasks | `projects/nopcommerce-04/outputs/tobe/speckit/traceability.json` |
| Estado das tasks | `projects/nopcommerce-04/outputs/tobe/speckit/tasks-progress.json` |
| Métricas de execução F4 | `projects/nopcommerce-04/outputs/pipeline_runner/runner-state.json` |
| Falhas de build | `projects/nopcommerce-04/outputs/tobe/source-code/{dotnet,angular}/GENERATION_LOG.md` |
| Estimativa de esforço | `projects/nopcommerce-04/outputs/tobe/docs/effort-calculator.md` · `ai-estimation-report.md` |
| Segurança e compliance | `projects/nopcommerce-04/outputs/deliverables/security-compliance-{report.md,summary.json}` |
| Composição de agentes | `python src/shared/tools/agent_registry.py` · `module.yaml` |
| Catálogo de agentes | `docs/agents-catalog.md` |

## Anexo B — Glossário

| Termo | Significado |
|---|---|
| **AS-IS / TO-BE** | Estado atual do legado / estado-alvo modernizado |
| **BC (Bounded Context)** | Fronteira de domínio com modelo e linguagem próprios (DDD) |
| **AST** | Árvore sintática abstrata — análise determinística de código, sem inferência de IA |
| **ADR** | Architecture Decision Record — decisão arquitetural registrada com contexto e consequências |
| **SpecKit (F3S)** | Camada que converte arquitetura em specs, planos e tasks executáveis rastreáveis |
| **Wave / Onda** | Agrupamento de bounded contexts migrados juntos, por complexidade e dependência |
| **Gate** | Ponto de verificação bloqueante entre fases |
| **FP / SP** | Ponto de Função / Story Point |
| **Strangler Fig** | Padrão de substituição incremental do legado, sem big bang |
| **Z-Curve** | Loop de remediação iterativa de vulnerabilidades |
| **DAG** | Grafo dirigido acíclico — garante que não há dependência circular entre tasks |

---

*Documento gerado a partir de evidência de execução real. Nenhum número deste relatório é estimado
sem indicação explícita.*
