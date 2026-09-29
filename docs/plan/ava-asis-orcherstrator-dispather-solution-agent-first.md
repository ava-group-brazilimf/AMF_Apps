Ready for review
Select text to add comments on the plan
Correção: ava-asis-orchestrator deve despachar o agente de solução primeiro (Wave 1→Wave 2)
Contexto
Hoje orchestrator-asis.md (v2.18.1) despacha 8 agentes da Phase A simultaneamente — incluindo o agente de solução (solution-{legacy_technology}, único que faz leitura via AST e produz os artefatos estruturais canônicos: architecture-blueprint.md, pattern-classifications.json, bounded-context-map.md + 6 diagramas .mmd) — junto com test-qa, inventory, db-analyzer, events-pubsub, doc:FT, doc:VC (e security*), todos "lendo código-fonte diretamente" em paralelo (dispatch_schedule.phase_a.mode: immediate).

Essa paralelização é incorreta: o spec 010-asis-agents-ast-artifact-consumption (Implemented) já conectou 5 desses agentes para preferir os artefatos AST do solution agent quando disponíveis, mas documentou honestamente essa limitação como uma race condition não resolvida (§3.3): "Fixing the Phase A race would require reordering orchestrator-asis.md's own dispatch phases — explicitly out of scope". shared/retry-protocol.md já assume implicitamente essa ordem (solution-{tech} é chamado ali de "predecessor de documentation", com regra "Wave 1 antes de Wave 2") — mas isso só vale hoje durante retry, nunca no dispatch inicial. Esta correção fecha essa lacuna: torna o dispatch inicial consistente com a ordem que o próprio retry-protocol já pressupõe, e adiciona um gate de interrupção obrigatória quando o agente de solução falha.

Confirmado com o usuário: agentes STUB (cobol/vbnet/powerbuilder) também devem interromper a esteira (não apenas falha real); security-orchestrator permanece na Wave 1, em paralelo com o solution agent (sem dependência dos artefatos AST, confirmado no spec 010 §Exclusions — sem sobreposição); mantém a política padrão de 4 retentativas antes de declarar falha.

Decisão
Dividir a atual "Phase A" em duas waves (nomenclatura alinhada a shared/retry-protocol.md, que já usa "Wave 1"/"Wave 2"):

Wave 1 (imediata): solution-{legacy_technology} + security-orchestrator (se security_enabled_asis: true) — únicos sem dependência dos artefatos do solution agent.
Gate: evaluate_solution_gate() — aberto somente quando status=completed AND artifacts_confirmed=true para o solution agent.
Gate OPEN → despachar Wave 2: test-qa, inventory, db-analyzer, events-pubsub, doc:FT, doc:VC (reaproveita o mesmo padrão on_event trigger já usado em phase_b.rules, ex.: { trigger: "FT✓", dispatch: doc:RT }).
Gate HALT (solution agent failed após esgotar as 4 retentativas padrão, ou implementation_status == STUB) → interromper toda a esteira imediatamente: NÃO despachar Wave 2, nem Phase B/C/D; emitir banner ⛔ PIPELINE INTERROMPIDO distinguindo as duas causas (falha real vs. tecnologia não suportada/STUB); pipeline termina em estado HALTED, sem emitir o bloco completo ⏱ Execução Concluída (mesmo precedente de Step 0.2 / Step 1, que também usam PARAR sem esse bloco) — em vez disso, um snapshot mínimo do Agent Completion Registry (o que já rodou/estava rodando, ex. security em paralelo).
Isso é uma exceção explícita à política padrão de guardrail ("esgotar retries → marcar FAILED, continuar pipeline") — só se aplica ao agente de solução, por ser pré-requisito estrutural dos demais.

Alterações em orchestrator-asis.md
## Agent Team Gerenciado (tabela, ~L50-73): atualizar coluna "Execução" — solution/security ficam "⚡ Wave 1 — Imediato"; test-qa/inventory/db-analyzer/events-pubsub/doc:FT/doc:VC passam a "🔗 Wave 2 — on(solution✓)".
Diagrama ASCII do DAG (~L74-120): redesenhar o bloco Phase A em duas waves + ramo ⛔ HALT.
dispatch_schedule YAML (~L140-189): dividir phase_a em phase_a_wave1 (mode: immediate; solution-{legacy_technology}, security*) e phase_a_wave2 (mode: on_event; regra { trigger: "solution✓", dispatch: [test-qa, inventory, db-analyzer, events-pubsub, doc:FT, doc:VC], blocking: true }).
Nova seção ## Solution Agent Gate (OBRIGATÓRIO — Wave 1 → Wave 2): define evaluate_solution_gate() (modelo em ## Phase A ALL ✓ — Definição Formal), a lógica OPEN/HALT descrita acima, e o texto exato do banner de interrupção (dois casos: falha real / STUB).
## Streaming COLLECT Protocol: novo branch — quando X == resolved_solution_agent atinge estado terminal, chamar evaluate_solution_gate() (em vez de tratá-lo como mais um agente de evaluate_phase_a_all() solto); despachar Wave 2 ou executar o HALT.
## Guardrails: nova regra documentando a exceção (solution agent não segue a política padrão de "continuar pipeline" ao esgotar retries) + "NUNCA despachar Wave 2 antes do Solution Agent Gate abrir".
## Reasoning Approach Step 3.1: reescrever para descrever as duas waves em vez de "invocar 7 agentes em sequência de dispatch, sem processar output de nenhum".
## Progress Tracker: ajustar a descrição do item phase-a para refletir o gate de duas waves (mantém os 8 itens fixos).
Frontmatter: bump de versão 2.18.1 → 2.19.0 (MINOR — novo passo de orquestração, nenhum campo renomeado, consistente com o precedente do spec 008 para master-orchestrator 1.2.0→1.3.0).
Alterações em arquivos relacionados
shared/retry-protocol.md: reconciliar a lista de "Wave 1" (hoje: solution+test-qa+security+inventory+db-analyzer, desatualizada — falta events-pubsub, e doc:FT/VC nunca apareceram ali) para bater com a nova Wave 1 real (solution + security) e Wave 2 real (test-qa, inventory, db-analyzer, events-pubsub, doc:FT, doc:VC) — hoje esse arquivo já usa a terminologia "Wave 1/Wave 2" e "predecessor→successor" só durante retry; passa a ser verdade também no dispatch inicial.
docs/agents-catalog.md (~L47, L61): remove a afirmação desatualizada "dispara os 7 sub-agentes em paralelo" — refletir o novo modelo de duas waves.
module.yaml (asis-diagnostic, opcional): bump 1.7.0 → 1.8.0 (MINOR, nenhum agente novo registrado).
Documentação via Spec Kit
Criar specs/011-asis-orchestrator-solution-first-dispatch/ seguindo o formato do precedente mais próximo (specs/008-pipeline-phase-order-correction, também uma correção de ordem de dispatch), usando os templates em .specify/templates/overrides/:

spec.md: seções 1. Agent Identity, 2. Problem Statement (a race condition documentada e não resolvida em specs/010), 3. Decision (Wave 1/Wave 2 + gate HALT), 4. Functional Changes by Component, 5. User Scenarios (Given-When-Then) — cobrindo no mínimo: (a) fluxo feliz Wave1→gate OPEN→Wave2; (b) falha real do solution agent após 4 retries → HALT com alerta; (c) projeto STUB (cobol/vbnet/powerbuilder) → HALT com alerta de tecnologia não suportada; (d) security roda em paralelo na Wave 1 sem esperar o gate — 6. Quality Gate Requirements, 7. Dependencies (referencia specs/010 como pré-requisito conceitual), 8. Exclusions (não altera os 6 agentes já wireados por specs/010 — eles continuam com sua própria lógica de fallback, que passa a ser inofensiva pois o artefato sempre existirá antes deles rodarem), 9. Assumptions, Success Criteria.
plan.md: Constitution Check (Article III — sequenciamento; Article X — versionamento MINOR), demais seções conforme .specify/templates/overrides/plan-template.md.
tasks.md: 7 categorias fixas (Frontmatter, Behavior, Schema — SKIP, Module Registration — SKIP, Quality Gate Checklists, Acceptance Validation, Documentation), numeração N.N.
Status do spec: Implemented só depois que as edições em orchestrator-asis.md estiverem concluídas e verificadas (mesma convenção dos specs 008/010).

Verificação
Reler orchestrator-asis.md após as edições e confirmar que não há mais nenhuma menção a "8 dispatches simultâneos" ou "Phase A imediato" para os 6 agentes da Wave 2.
Grep por solution✓ para confirmar que o novo trigger aparece exatamente onde o gate é avaliado e onde a Wave 2 é despachada.
Simular os 3 cenários (sucesso, falha real esgotando retries, STUB) mentalmente contra o texto final e confirmar que cada um produz a saída esperada (Wave 2 despachada / banner HALT com a causa certa).
Grep em docs/agents-catalog.md por "7 sub-agentes em paralelo" — deve retornar zero após a correção.
Conferir que shared/retry-protocol.md e o novo dispatch_schedule não se contradizem mais quanto à composição de Wave 1/Wave 2.