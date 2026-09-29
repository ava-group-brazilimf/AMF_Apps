Ready for review
Select text to add comments on the plan
Plano: Agente de Remediação Summary (ava-summary-remediation)
Contexto
O ava-summary gera o HTML executivo consolidando todos os artefatos de outputs/. Hoje, ao final do pipeline, o HTML frequentemente exibe cards zerados/N/D, tabelas vazias, colunas quebradas (Risk ID R-???) e elementos de UI obsoletos (Componentes FCID, Artefatos AG-10, Rules Categories, etc.), porque:

Vários parsers em build_summary_comprehensive.py têm fallbacks que nem sempre encontram dados (formato de origem diferente do esperado) e retornam 0/"N/D" — e o template renderiza esse valor literal sem nenhum tratamento (renderKPIs() não tem lógica de "ocultar se vazio").
Alguns elementos da UI (Componentes FCID, Artefatos AG-10, cards DDD do BC TO-BE, Rules Categories/Screen Rules) nunca deveriam ter existido e precisam ser removidos do template permanentemente.
D.tobebn (Regras de Negócio TO-BE) depende de tobe/docs/regras-negocio.md, que é uma fonte distinta de D.bizRules (AS-IS) — quando ausente, a tabela fica vazia mesmo as regras já tendo sido capturadas no AS-IS.
Não existe hoje nenhum agente que rode de forma independente, após o pipeline (master-orchestrator, orquestradores individuais, ou o próprio ava-summary), para auditar e reparar um summary já gerado — sobretudo para projetos legados ou com artefatos incompletos.
Existe um rascunho de spec anexado pelo usuário (summary (1).md) que já descreve um modo FS — Fix Summary como trigger dentro do próprio ava-summary (@summary FS {project}), com um Phase 0–7 bem detalhado (auditoria, resolução de artefatos ausentes via 7 regras, síntese de diagramas faltantes, sanitização Mermaid, reconciliação de segurança, rebuild, re-validação). O pedido atual do usuário generaliza isso: quer um agente novo e independente (ava-summary-remediation, arquivo .md próprio + SKILL.md próprio), e adiciona ~21 problemas concretos de exibição que devem ser cobertos pelas regras de validação/remediação.

Decisões de arquitetura (confirmadas com o usuário)
Fix permanente + agente de reparo. As correções dos ~21 problemas (ocultar cards zerados, remover elementos obsoletos, corrigir fallback de Regras de Negócio TO-BE) são aplicadas uma vez, na base — summary-template.html (funções de render) e build_summary_comprehensive.py (parsers/fallbacks) — para que todo summary novo já nasça correto, sem depender de execução manual do agente. O novo ava-summary-remediation reaproveita o design do modo FS do anexo, mas como ferramenta de reparo idempotente para summaries já gerados (HTML legado) ou projetos com artefatos ausentes/malformados — não recria a lógica de supressão a cada execução.
Coluna Risk ID: remover. A tabela de Riscos deixa de exibir a coluna ID (R-???); mantém categoria/descrição/severidade/ação/evidência.
Nova categoria dedicada no validador: C11 — Content Completeness & UI Cleanup. As ~15 novas regras de guarda de regressão entram como C11.1–C11.15 em validate_summary.py, mantendo as categorias C1–C9 existentes intocadas (nota: doc já tem um C10 "fantasma" documentado em summary-validate-agent.md mas nunca implementado em código — fora de escopo, não mexer nele nesta feature, apenas não colidir o número).
Documentação via SpecKit
Criar specs/015-summary-remediation-agent/ (próximo número livre — 014-remover-geracao-drawio-tobe é o mais recente) seguindo os templates de .specify/templates/overrides/ já usados no repo:

spec.md — Change Type: new-agent (agente) combinado com uma seção narrativa Functional Changes by Component (mesmo padrão usado no spec 014 para as mudanças em arquivos existentes). Seções: 1. Agent Identity (ava-summary-remediation, F8/Summary, skill ava-summary-remediation, dispatch user-facing) → 2. Agent Frontmatter → 3. Output Contract (validation-report.md, .json, e o HTML remediado sobrescrevendo o summary atual) → Functional Changes by Component (tabela com as ~21 correções, ver seção "Tabela de rastreabilidade" abaixo) → 4. User Scenarios (Given-When-Then: nominal = summary legado com dados incompletos → agente audita, resolve, reconstrói, revalida; edge = projeto sem nenhum artefato ausente → agente roda e não altera nada, idempotente; gate = template base ausente → agente aborta com erro claro) → 5. Quality Gate Requirements → 6. Dependencies (ava-summary, validate_summary.py) → 7. Exclusions (não re-executa agentes upstream, não sobrescreve artefatos existentes em outputs/) → 8. Assumptions → Success Criteria.
plan.md — Summary/Constitution Check/Technical Context → Phase Placement (roda depois de ava-summary, standalone, não faz parte da cadeia F1→F7) → Agent File Structure (skill + agent) → module.yaml Impact (diff) → Implementation Phases (Phase 0 Frontmatter → 1 Body/Fases do script → 2 Gate Logic → 3 BDD → 4 Registro) → Test Strategy.
tasks.md — estrutura IMFAI de 7 categorias (Category 1 Frontmatter, 2 Behavior, 3 Schema — SKIP, 4 Module Registration, 5 Quality Gate Checklists, 6 Acceptance Validation, 7 Documentation).
Tabela de rastreabilidade (problema → mecanismo de fix → arquivo)
#	Problema (texto do usuário)	Mecanismo	Arquivo principal
1–4	KPI Classes/Métodos/Complexidade/Endpoints = 0	Investigar parser + ocultar tile se 0	build_summary_comprehensive.py (parsers L3106–3118) + renderKPIs() no template
5–6	Tabelas BD / Volume BD Insert = N/D	Ocultar tile se N/D (Volume BD Insert não tem fonte — fica sempre oculto até existir parser)	renderKPIs()
7	Telas e Forms = 0	Ocultar tile se 0	renderKPIs()
8	Componentes (FCID)	Remover tile do array estático D.kpis	summary-template.html L2291
9	Risk ID quebrado R-???	Remover coluna ID da tabela	renderRisks() template L3200-3213
10	Identified Patterns vazio	Ocultar card se D.patterns vazio/zerado	renderPatterns()
11	Bounded Context Map (Forms/Units/LOC) vazio	Ocultar colunas/linha se zeradas	renderBC() + parse_bounded_contexts()
12	Functional Requirements vazio	Ocultar submenu inteiro se D.funcReqs vazio	nav-render + parse_func_reqs()
13	Business Rules (Rules Mapping) vazio	Ocultar submenu inteiro se D.bizRules vazio	nav-render + parse_biz_rules()
14a	Screen Flow Overview: infos de agente	Remover cards de metadado de execução	Screen Flow overview render
14b	Card "Rules Categories"	Remover card	summary-template.html
14c	Card + aba "Screen Rules"	Remover card e tab	summary-template.html + parse_screen_rules()
15a	Inventory & Metrics: cards vazios	Ocultar se zerado/N-D	Inventory render
15b	Tabela Complexidade (Inventory)	Remover tabela	summary-template.html
16	Test Baselines: "Tests existentes" vazio	Ocultar tabela se vazia	build_test_map() + render
17a-c	Banco de Dados AS-IS: cards/Schema/SPs vazios	Ocultar se vazio	_parse_schema_subsections() + render
18a	screen-rules: metadado de agente exibido	Remover metadado do conteúdo exibido	Content Embedder / Deliverable Viewer
18b	value-chain nos Entregáveis	Remover da classificação de Deliverables	build_summary_comprehensive.py L5817 (classifyDeliverable)
19	"Artefatos AG-10" (Blueprint C4)	Remover card	summary-template.html L1529
20	Cards Aprovados/DDD/Squad + tabela "BCs Refinados"	Remover cards e tabela	renderBCMetrics()/renderTOBEBCDetail() + template L1574/1589
21	Regras de Negócio TO-BE vazio	Fallback: se tobe/docs/regras-negocio.md ausente, popular D.tobebn a partir de D.bizRules (AS-IS)	parse_tobebn()
Cada linha acima ganha: (a) o fix permanente no builder/template, (b) uma regra de guarda em validate_summary.py (C11.1–C11.15, mapeamento 1:1 aproximado agrupando os itens correlatos), e (c) cobertura pelo script de remediação para HTML já gerado antes do fix.

Arquivos novos
specs/015-summary-remediation-agent/{spec.md,plan.md,tasks.md}
src/modules/ava-fabric-agents/summary/agents/summary-remediation-agent.md — novo agente, frontmatter name: ava-summary-remediation, version: 1.0.0, date, allowed-tools: Read, Write, Edit, Glob, Grep, Bash. Corpo em pt-BR, reaproveitando a estrutura de fases do anexo summary (1).md (Phase 0 Audit → Phase 1 Artifact Resolution 7 regras → Phase 2 Diagram Synthesis → Phase 3 Mermaid Sanitization → Phase 4 Security Reconciliation → Phase 5 Content/UI Guards (novo — aplica os 21 itens quando o HTML foi gerado por uma versão antiga do builder) → Phase 6 Rebuild → Phase 7 Re-validate + Fix Report). Guardrail explícito: só escreve em outputs/ quando o arquivo alvo não existe (mesma exceção documentada no anexo), nunca sobrescreve artefato existente.
.github/skills/ava-summary-remediation/SKILL.md — mesmo padrão de ava-summary/SKILL.md: resolve project_name, lê agent-task-config.yaml/shared-context.md, delega para o agente .md acima.
src/modules/ava-fabric-agents/summary/utils/remediate_summary.py — script Python que implementa as Phases 0–7 do agente (reaproveita funções já existentes de validate_summary.py — sanitize_mmd, _try_auto_fix — e de build_summary_comprehensive.py onde fizer sentido, evitando duplicar lógica de parsing).
Arquivos modificados
src/modules/ava-fabric-agents/summary/templates/html/summary-template.html — remoções incondicionais (itens 8, 14b, 14c, 15b, 19, 20) e lógica condicional de ocultação em renderKPIs(), renderPatterns(), renderBC(), renderRisks() (remove coluna ID), e nas funções/nav-render de Functional Requirements, Business Rules, Test Baselines, Banco de Dados AS-IS.
src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py — fallback de parse_tobebn() para D.bizRules (item 21); ajustes pontuais nos parsers de KPI/patterns/BC apontados na tabela onde a causa raiz for parsing (não apenas exibição); remoção de value-chain da classificação de Deliverables (item 18b).
src/modules/ava-fabric-agents/summary/utils/validate_summary.py — nova categoria C11 (15 checks) mais funções de fix quando aplicável (seguindo o padrão _fix_c* já existente), e atualização do CHECKS catalog / contagem total de regras.
src/modules/ava-fabric-agents/summary/module.yaml — registra ava-summary-remediation (file: agents/summary-remediation-agent.md, skill: ava-summary-remediation).
.github/copilot-instructions.md — nova linha na tabela ### F8 — Summary.
src/modules/ava-fabric-agents/summary/agents/summary-validate-agent.md — atualizar contagem de regras (de "~55" para o total real após C11) e catálogo de categorias; não mexer no C10 fantasma (fora de escopo).
CHANGELOG.md — entrada nova documentando o agente e as correções de exibição.
Plano de verificação (3 níveis, conforme guardrail já em uso no módulo)
Nível 1 — Unit: python build_summary_comprehensive.py --project Meu-ERP (ou outro projeto de teste disponível em projects/) → verificar ✅ SUCESSO! e abrir o HTML; confirmar visualmente que os 21 itens da tabela de rastreabilidade estão corretos (cards zerados ocultos, elementos obsoletos ausentes, Regras de Negócio TO-BE populada).
Nível 2 — Validação: python validate_summary.py --project {project} → exit 0, validation-report.md sem erros, novas regras C11.* aparecem no relatório e passam.
Nível 3 — Remediação standalone: rodar @ava-summary-remediation {project} (ou python remediate_summary.py --project {project}) contra um summary já gerado antes do fix (ou um projeto com artefatos deliberadamente incompletos) e confirmar que o relatório de fix mostra itens corrigidos, o HTML final passa em C11, e nenhum arquivo em outputs/ pré-existente foi sobrescrito.
Confirmar CA02 (independência de stack/projeto): repetir passo 1–2 em pelo menos dois projetos de teste com stacks/tecnologias diferentes para garantir que nenhuma correção depende de nome de projeto ou stack hardcoded.
Observações / riscos
O D.kpis/render de KPI é hoje um array estático no template com placeholders {{X}} substituídos por string — a ocultação condicional precisa ser feita em JS (renderKPIs()), comparando o valor renderizado ("0"/"N/D") contra uma lista de chaves elegíveis à ocultação (Classes, Métodos, Complexidade, Endpoints, Tabelas BD, Volume BD Insert, Telas/Forms) — não ocultar KPIs onde 0 é um valor legítimo (ex.: não aplicável a todos os 14 tiles, só aos 7 listados pelo usuário).
Volume BD Insert não tem fonte de dados hoje (confirmado: sempre "N/D" hardcoded no builder) — a correção aqui é só a ocultação; não há escopo para criar um novo parser de volume de INSERT nesta feature.
Doc/código já tem drift conhecido (contagem "~55 regras", categoria C10 fantasma) — plano inclui corrigir a contagem total mas não implementa C10; deixar registrado no CHANGELOG como debt conhecido, não bloqueia esta feature.