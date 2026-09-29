Ready for review
Select text to add comments on the plan
master-orchestrator não despacha os sub-orquestradores lendo seus specs — extração AST pulada em F1
Contexto
O usuário reportou: /ava-asis-orchestrator | FP | {project} (standalone) executa corretamente o Step 0 de solution-delphi.md (extração AST determinística via run_ast_analysis.py). Mas master-orchestrator.md, ao despachar a mesma Fase 1 via @ava-asis-orchestrator | SA | FULL, produz um comportamento diferente: o agente pula a extração AST e lê o código-fonte manualmente arquivo por arquivo (Get-Content por .pas), gastando mais tokens/processamento — mesmo com ava_ast_analyzer_path corretamente configurado no project-config.yaml do projeto (confirmado, não é problema de config).

Causa raiz confirmada (2 agentes Explore, leitura direta dos arquivos):

master-orchestrator.md's Step 1.1 (agents/master-orchestrator.md:335-343) despacha @ava-asis-orchestrator como um bloco puramente declarativo — DISPATCH @agente + parâmetros
AWAIT — sem nenhuma instrução de Read do spec completo de orchestrator-asis.md antes disso. Esse é o padrão idêntico usado para todos os outros 23 pontos de dispatch do arquivo (F2 até F7) — não é uma falha isolada de F1.
O único lugar no repositório inteiro que já faz essa leitura obrigatória explícita antes de despachar é dispatch_bridge_fastqa() dentro do próprio orchestrator-asis.md ("Leia o spec em .../bridge-fastqa-asis.md" — Step A, gate de falha explícito). Esse é o padrão correto a replicar.
O mesmo gap existe um nível abaixo: orchestrator-asis.md's Step 3.1 (Wave 1, linha ~1800) despacha @{resolved_solution_agent} sem Read explícito de solution-{tech}.md. A execução standalone funciona hoje (contexto pequeno/focado favorece o julgamento implícito do LLM), mas é frágil pelo mesmo motivo.
Confirmado (Explore agent, leitura direta de orchestrator-asis.md): SA, SA | FULL e FP fluem pelo mesmo Step 3 DAG — não há branch que pule Step 0/AST por trigger. O bug não está na lógica de trigger de orchestrator-asis.md.
Achado colateral: ava-devops-cost-estimate (despachado em F6 Step 6.6) tem o arquivo devops-agents/agents/cost-estimate-agent.md no disco mas não está registrado em devops-agents/module.yaml — bug de registro separado (Article IV), corrigido de passagem.
Decisão do usuário: corrigir os 2 pontos (master→asis E asis→solution) e aplicar o mesmo hardening de leitura obrigatória em todas as fases do master-orchestrator (F1–F7, 24 pontos de dispatch), não só F1.

Decisão
1. Nova seção ## Dispatch Protocol em master-orchestrator.md
Um único guardrail global (evita repetir a explicação 24 vezes): antes de qualquer DISPATCH @agent-id, o LLM DEVE executar Read do .md completo do agente-alvo — nunca despachar/continuar a partir de conhecimento genérico do que aquele agente "deveria" fazer. Inclui o porquê (o bug relatado) como contexto.

2. Tabela ## Agent Team ganha coluna Spec File
Resolvida via module.yaml de cada módulo (grep já confirmou todos os 24 paths — ver tabela abaixo). Fonte única de verdade para os paths, em vez de duplicá-los em cada um dos 24 pontos de dispatch.

ID	Spec File
ava-asis-orchestrator	asis-diagnostic/agents/orchestrator-asis.md
ava-tobe-orchestrator	tobe-architecture/agents/orchestrator-tobe.md
ava-prototype	prototype/agents/prototype-agent.md
ava-stack-orchestrator	tech-stack/agents/orchestrator-stack.md
ava-qa-orchestrator	qa-agents/agents/qa-orchestrator-agent.md
ava-devops-{iac,ci,cd,containerize,iac-azure,cost-estimate,monitoring-observability,compare-version,package-approval}	devops-agents/agents/{iac,ci,cd,containerize,iac-azure,cost-estimate,monitoring-observability,compare-version,package-approval}-agent.md
ava-devops-iac-{aws,gcp,k8s-native}	🚧 STUB — mesmo tratamento dos stubs de solution (Read ainda obrigatório; o próprio arquivo se autodeclara STUB)
ava-deliverable-{tech-docs,migration-plan,security-compliance,test-evidence,code-templates,client-demo,packager}	deliverables/agents/{tech-docs,migration-plan-publisher,security-compliance,test-evidence,code-templates,client-demo,packager}-agent.md (migration-plan usa migration-plan-publisher.md, não migration-plan-agent.md)
(todos os paths acima relativos a src/modules/ava-fabric-agents/)

3. Cada um dos 24 pontos DISPATCH @agent-id ganha um prefixo curto e local
Sem renumerar os sub-steps existentes (baixo risco, sem churn) — o Read vira parte da MESMA linha numerada, não um novo sub-step:

1.1  ⛔ Read(src/modules/ava-fabric-agents/asis-diagnostic/agents/orchestrator-asis.md) OBRIGATÓRIO (ver § Dispatch Protocol) → DISPATCH @ava-asis-orchestrator
     Parâmetros obrigatórios:
       ...
Mesmo padrão aplicado nos 5 dispatches únicos de F1-F5, nos 9 de F6 (incluindo os 4 branches condicionais de cloud provider) e nos 7 de F7 — 24 pontos ao todo. Os dispatches de ava-summary (via Bash: python build_summary_comprehensive.py) não recebem esse tratamento — são execução determinística de script, não invocação de agente LLM, não têm o mesmo risco de "improviso".

4. Mesmo padrão em orchestrator-asis.md Step 3.1 (Wave 1)
- **3.1 — DISPATCH Phase A · Wave 1**: ... ⛔ Read({path resolvido via SOLUTION_AGENTS routing,
  ex: agents/solution-delphi.md}) OBRIGATÓRIO antes de invocar `@{resolved_solution_agent}` ...
5. Visibilidade dos logs (2º pedido do usuário)
Reforço explícito na nova ## Dispatch Protocol: a saída/checklists/progress que um agente despachado emitir (incluindo sub-dispatches internos, como o log em tempo real da extração AST na Wave 1 de F1, já implementado em specs/012) DEVE permanecer visível na sessão — nunca resumida para um único sinal final de conclusão. Isso deve resolver o sintoma diretamente, já que a causa raiz (spec nunca carregado) é a mesma razão pela qual o log em tempo real de solution-delphi.md nunca chegava a ser executado quando despachado via master-orchestrator.

6. Achado colateral corrigido
devops-agents/module.yaml: adicionar registro faltante de ava-devops-cost-estimate → agents/cost-estimate-agent.md.

7. Versionamento
master-orchestrator.md: 1.3.0 → 1.4.0 (MINOR — nova seção/protocolo, nenhum campo removido)
orchestrator-asis.md: 2.19.0 → 2.19.1 (PATCH — reforço de confiabilidade em Step 3.1, sem nova funcionalidade)
devops-agents/module.yaml: 1.0.0 → 1.0.1 (PATCH — registro de agente faltante)
Documentação via Spec Kit
Criar specs/013-master-orchestrator-mandatory-spec-read/ (spec.md, plan.md, tasks.md), mesmo formato consolidado usado em specs/011/specs/012. Cenários mínimos: (1) F1 via master-orchestrator agora lê orchestrator-asis.md e executa a extração AST corretamente; (2) Wave 1 de orchestrator-asis.md lê solution-{tech}.md antes de invocar; (3) demais 22 pontos de dispatch (F2-F7) recebem o mesmo hardening por consistência; (4) ava-devops-cost-estimate agora resolve corretamente via module.yaml.

Exclusões (fora de escopo, documentadas)
Não investigar se o mesmo padrão "dispatch sem Read" existe DENTRO de outros orquestradores (orchestrator-tobe.md→seus próprios sub-agentes, qa-orchestrator-agent.md→skills, etc.) — é o mesmo tipo de risco, mas não foi reportado como quebrado; fica como possível PBI futuro.
Não alterar o mecanismo de dispatch em si (nenhum SubAgent/Task tool introduzido) — mantém o padrão inline já estabelecido no repo, apenas torna a leitura do spec explícita e obrigatória.
Verificação
grep -c "⛔ Read(" master-orchestrator.md → 24 (um por DISPATCH @agent-id, excluindo os dispatches de ava-summary)
Conferir que nenhum sub-step foi renumerado (diff deve mostrar só a linha DISPATCH alterada em cada ponto, não uma reindexação)
grep -n "ava-devops-cost-estimate" em devops-agents/module.yaml → presente
Reler orchestrator-asis.md Step 3.1 após a edição e confirmar que o Read aparece antes de "invocar @{resolved_solution_agent}"
Simular mentalmente o cenário do usuário: master-orchestrator despachando F1 agora carrega orchestrator-asis.md por completo antes de "se tornar" esse agente, que por sua vez carrega solution-delphi.md antes de "se tornar" o agente de solução — a cadeia de leitura completa existe agora em todos os elos, igual ao invocador standalone