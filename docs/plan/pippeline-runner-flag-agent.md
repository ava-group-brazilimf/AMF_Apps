
Ready for review
Select text to add comments on the plan
Plano — flag --agent no ava-pipeline-runner-cli.py
Context
Hoje o ava-pipeline-runner-cli.py (5.530 linhas) é 100% interativo: nenhum argparse, nove prompts em sequência, e safe_input usa msvcrt.getwch(), que ignora stdin — nem por pipe dá para automatizar. Para rodar um único agente, o operador precisa navegar o menu e executar a fase inteira, gastando inferência em tudo que já estava pronto.

Isso apareceu de forma concreta várias vezes nesta investigação: regerar só o F3S:planning:003, ou só o ava-tobe-migration-plan de um projeto sem wave-model.json, exigiu percorrer o menu e responder P (pular) dezenas de vezes.

Resultado pretendido: python "ava-pipeline-runner-cli.py" --agent ava-tobe-migration-plan -p meu-erp-03 despacha aquele agente e só ele, sem prompt algum, e qualquer falha vira mensagem tratada com causa raiz e comando de correção.

Decisões já tomadas com o usuário:

Agente com fan-out (F3S por feature, F4 por task) recusa o despacho avulso, salvo com --feature/--task-id.
Escopo restrito a --agent e -p (mais --dry-run, --list-agents, --json). Rodar sem argumentos continua idêntico.
A correção do BOM no agent_registry entra junto, como pré-requisito.
Achado que define o desenho
pipeline_plan.build_plan() não serve como fonte do passo. Era a minha suposição inicial e está errada: os namespaces de fase divergem entre o runner e o ava-pipeline.yaml.

Agente	PIPELINE do runner	ava-pipeline.yaml
ava-summary	S1, S4	F8a, F8c, F8d
ava-summary-remediation	S2	F8b
ava-summary-validate	S3	ausente
_ast_extractor	F0	ausente
ava-devops-containerize / ava-devops-podman-run	FC / FP	ausentes
E run_step faz curto-circuito por string exata de fase — verificado:

3462:    if agent == "_ast_extractor":
3471:    if phase in ("S1", "S4"):      → _run_summary_generate_standalone (builder determinístico)
3491:    elif phase == "S2":
3502:    elif phase == "S3":
Despachar --agent ava-summary com a fase F8a vinda do YAML pula o builder determinístico e queima uma inferência de 128k tokens para produzir o que um script Python produz de graça. Falha silenciosa e cara.

→ A resolução usa o PIPELINE do próprio runner como tier 1. agent_registry entra só no ramo avulso.

Ambiguidade real (verificada nos 22 passos / 19 agentes do PIPELINE):

Agente	Fases	Triggers
ava-devops-orchestrator	F2b, F5	DP, DE
ava-qa-orchestrator	F2c, F6	TPT, QE
ava-summary	S1, S4	SAS, SAS
Sem default defensável — exige --phase para desempatar.

Arquivos
Arquivo	Papel
src/shared/tools/runner_agent_cli.py	novo — resolução, validação e construtores de mensagem. Importável, sem msvcrt, sem anthropic
ava-pipeline-runner-cli.py	9 enxertos cirúrgicos (E1–E9)
src/shared/tools/agent_registry.py	correção do BOM (linha 195)
tests/tools/test_runner_agent_cli.py	novo — import direto
tests/tools/test_runner_agent_flag.py	novo — extração AST
docs/guia-execucao-agente-avulso.md	novo — guia de uso
specs/043-runner-single-agent-cli/	novo — spec.md, plan.md, tasks.md
O módulo separado existe por testabilidade: o runner importa msvcrt no topo e monta estado global no import (_INPUTS_APLICADOS = _apply_declared_inputs(PIPELINE), linha 429), então tudo que ficar lá só é testável por extração AST. resolver_passo recebe pipeline como parâmetro — o runner passa seu PIPELINE, os testes passam uma lista sintética.

Implementação, em ordem causal

1. Pré-requisito — BOM no agent_registry
   agent_registry.py:195 lê com encoding="utf-8" e :101 casa \A---. Um BOM UTF-8 impede o match do frontmatter e o agente some do catálogo. Verificado: exatamente 1 arquivo afetado, summary-remediation-agent.md.

Efeito em cascata: ava-summary-remediation não entra em catalog() → validate_plan() reprova o step F8b → ava_pipeline run --all sai com exit 2; e --agent degradaria em silêncio para a heurística justamente onde o determinismo é o ponto.

Correção: encoding="utf-8-sig". Uma linha, commit separado e primeiro, com teste.

2. load_skill aceita spec_path (E2, E3)
   load_skill (1113–1203) não usa o registry — acha o agente por heurística de substring e escolhe o maior arquivo candidato. Defeito já documentado em docs/guia-ava-pipeline-cli.md:2734: "pode carregar o agente errado". Para --agent isso é fatal: resolveríamos o agente certo e carregaríamos o skill de outro.

Nova precedência 0.5, entre o override e o wrapper:

0. AGENT_SKILL_OVERRIDE       (workflow multi-parte, curadoria explícita)
   0.5  spec_path do registry      ← novo, só quando o chamador resolveu o agente
1. .github/skills/{agent}/SKILL.md se > 2 KB
2. heurística de substring    (legado — preservada)
3. stub
   Assinatura: load_skill(agent_name, spec_path=None). Chamadas em 3537 e 5179 passam step.get("spec_path"). Como nenhum passo de PIPELINE tem a chave, o modo interativo é bit-idêntico.

Não remover a heurística — é o caminho do modo interativo e de todo passo expandido.

3. src/shared/tools/runner_agent_cli.py
   Padrão _main(argv=None) -> int + raise SystemExit(_main()), como as demais ferramentas.

class AgentCLIError(Exception):          # carrega bloco formatado + exit code

def resolver_provider(deployment) -> str
def resolver_passo(pipeline, project, agent, *, phase=None, trigger=None,
                   feature=None, repo_root=None) -> dict
def validar_passo(passo) -> list[str]
def listar_agentes(pipeline) -> str
def explicar_agente_desconhecido(...) -> str
def explicar_agente_ambiguo(...)     -> str
def explicar_projeto_inexistente(...) -> str
def explicar_fanout_avulso(...)      -> str
def _main(argv=None) -> int          # resolução seca: --dry-run / --list-agents
Resolução em três tiers:

Esteira — [s for s in pipeline if s["agent"] == agent]. Um match → passo canônico, com phase/trigger/label corretos e o inputs que _apply_declared_inputs injetou no import. Vários matches sem --phase → AgentCLIError com a tabela fase/trigger.
Avulso — agent_registry.get(agent) → dict com phase do módulo, trigger=None, inputs={}, ad_hoc=True. Mesmo shape que _expand_ledger_phase já produz.
Desconhecido — AgentCLIError com difflib.get_close_matches sobre a união de esteira e registry (110 ids). O PlanError de build_plan só lista a esteira; ava-tobe-migration-plan mora no registry.
Enriquecimento comum: spec_path (como str, não Path), module, version do registry. Validação reusa pipeline_plan.validate_plan([Step]) — monta um Step descartável, precedente já existente em 5183-5188.

4. Enxertos no runner (E1, E8, E9)
   if __name__ == "__main__":
   _args = _parse_cli()
   if _args.list_agents: sys.exit(_listar_agentes_cli(_args))
   if _args.agent:       sys.exit(_despachar_agente_unico(_args))
   main(project_preselecionado=_args.project)
   Flags: --agent, -p/--project, --phase, --trigger, --feature, --model, --headroom, --force-single, --dry-run, --list-agents, --json. Nenhum posicional; argv vazio devolve tudo None/False.

Verificado que nenhum .bat/.ps1 invoca o runner — adicionar argparse não quebra wrapper que passe argumento solto.

_despachar_agente_unico não chama main(). Enfiar nove if args.agent: numa função de 750 linhas é o caminho para regredir o modo interativo. A função nova replica só o setup que run_step exige:

Prompt	No modo --agent
requisitos	roda, avisa, segue
modelo	pulado — DEPLOYMENT = args.model or DEPLOYMENT; PROVIDER = resolver_provider(...)
projeto	args.project, validado contra list_projects()
retomada	pulado e proibido (§ Estado)
AST	pulado
modo/confirmação/fases	N/A — auto_mode = True
ask_permission	auto=True → devolve "S" em 3091
Pegadinha do PROVIDER: o global (linha 170) só é corrigido dentro de _select_model_interactive (975/999). Pulado o menu, run_step toma o ramo errado em 3575 e manda payload Anthropic para endpoint OpenAI. resolver_provider espelha o teste que o runner já usa em 4960/4981; imprimir deployment e provider sempre.

Estado — não tocar. _save_runner_state, _write_status_html, _finalize_runner_state e _write_remediation_report ficam fora do caminho novo. Um _save_runner_state com active_steps=[passo_avulso] sobrescreveria o runner-state.json de um run real com uma esteira de um passo só. O que é escrito: o log que run_step já grava em 3660-3674.

Setup mínimo: output_dir.mkdir(parents=True, exist_ok=True) (obrigatório — run_step escreve sem criar), API key, client. Headroom só com --headroom; sem ele aproveita o proxy se estiver vivo e cai direto se não — run_step reativa sozinho em 3514-3532.

5. Tratamento de erro
   Formato único, o de explicar_fase_nao_expandida (1572-1682), que já provou funcionar: moldura → CAUSA RAIZ → COMO CORRIGIR → COMANDO. Construtores puros no módulo novo, testáveis por igualdade de string.

Falha	Exit	Mensagem
--agent sem -p	2	exige -p/--project + exemplo
projeto inexistente	2	lista list_projects() + difflib (meu-erp-3 → meu-erp-03)
agente desconhecido	2	difflib sobre esteira ∪ registry + comando do registry
agente ambíguo	2	tabela fase/trigger + --phase F5 pronto para copiar
deprecado / spec ausente	2	saída de validate_plan
fan-out sem escopo	2	explicar_fanout_avulso
insumo obrigatório ausente	1	preflight_step_inputs + format_missing (já nomeia o produced_by)
exceção em run_step	1	explain_failure — traceback + _ROOT_CAUSES + próximo passo
Ctrl+C	130	"Interrompido."
Fan-out (decisão do usuário): F3S tenta _expand_dag_phases; agente com foreach no ava-pipeline.yaml tenta _expand_ledger_phase. Sem escopo e sem --force-single, recusa citando a evidência medida (ava-pipeline.yaml:180-184: skill de 8 KB, 68.170 tokens, 26 artefatos numa resposta, contratos de seis agentes violados) e lista as features/tasks disponíveis.

Insumo ausente diverge da esteira de propósito: lá ele degrada (_degrade_phase, 5127-5140) para não travar as sucessoras; aqui não há sucessora, e despachar sem insumo só produz alucinação — então recusa. Comentar a divergência no código.

Para agente ad-hoc, avisar explicitamente que inputs={} leva ao contexto legado e que val_ok=True não é evidência (sem contrato, validate_phase_artifacts aprova tudo).

6. Documentação
   docs/guia-execucao-agente-avulso.md — padrão dos guias do repo: H1 + blockquote de metadados (escopo, executável, substitui), --- entre blocos, seções numeradas, tabela de parâmetros, blocos ``powershell com comentários numerados, pt-BR. specs/043-runner-single-agent-cli/{spec,plan,tasks}.md — formato interno: spec.md com # Agent Specification:, cabeçalho **Feature Branch** / **Created** / **Status** / **Change Type**, ## Problem Statement, ## User Stories (### US1 — Como operador, quero…), ## Acceptance Scenarios (BDD) em ``gherkin com palavras em português, ## Out of Scope; plan.md abrindo por ## Constitution Check; tasks.md com ## 1. Governança e IDs T-NNN saltando de dezena por seção.
   Entrada no CHANGELOG.md.
   Verificação

# 1. Pré-requisito

python -m pytest tests/tools/test_agent_registry.py -q
python src/shared/tools/agent_registry.py --agent ava-summary-remediation   # antes: vazio

# 2. Módulo novo, isolado — fecha esta etapa verde antes de tocar no runner

python -m pytest tests/tools/test_runner_agent_cli.py -q
python src/shared/tools/runner_agent_cli.py --agent ava-tobe-migration-plan -p meu-erp-03 --dry-run

# 3. Runner

python -m pytest tests/tools/test_runner_agent_flag.py -q
python "ava-pipeline-runner-cli.py" --list-agents
python "ava-pipeline-runner-cli.py" --agent ava-tobe-migration-plan -p meu-erp-03 --dry-run
python "ava-pipeline-runner-cli.py" --agent ava-tobe-migration-plan -p meu-erp-03      # gasta inferência

# 4. Ramos de erro (todos exit 2, nenhum gasta inferência)

python "ava-pipeline-runner-cli.py" --agent ava-tobe-migration-plna -p meu-erp-03   # sugestão
python "ava-pipeline-runner-cli.py" --agent ava-devops-orchestrator -p meu-erp-03   # ambíguo → --phase
python "ava-pipeline-runner-cli.py" --agent ava-speckit-specification -p meu-erp-03 # fan-out → --feature
python "ava-pipeline-runner-cli.py" --agent ava-tobe-migration-plan -p projeto-que-nao-existe

# 5. REGRESSÃO — o modo interativo tem de continuar idêntico

python "ava-pipeline-runner-cli.py"
Testes que travam os riscos:

resolver_passo(PIPELINE_real, ..., "ava-summary", phase="S1")["phase"] == "S1" — nunca F8a. É o teste que impede alguém "simplificar" trocando tudo por build_plan.
_parse_cli([]).agent is None — protege o modo interativo.
load_skill("x", spec_path=None) cai na precedência original; com spec_path devolve aquele arquivo; com agente em AGENT_SKILL_OVERRIDE, a precedência 0 ganha.
Dublês de _save_runner_state / _write_status_html / _write_remediation_report registram zero chamadas no caminho novo.
PROVIDER vira "openai" com --model luna-*.
Fora de escopo
--task-id — arrasta task_ledger.start, verify_task_step e o ramo de verificação de build (5218-5273): superfície maior que a feature inteira. Sem ele, --agent ava-f4s-codegen-agent cai na recusa de fan-out, que é o comportamento correto.
--phase, --yes, --from, subcomandos — decisão do usuário de manter o escopo estrito.
Propagar spec_path em _expand_dag_phases e _expand_ledger_phase, o que eliminaria a heurística da esteira inteira. Registrar como follow-up.
Regressão pendente de terceiros: o guard de exit code do on_fail: confirm sumiu numa reescrita recente (hoje ~5217 testa só on_fail == "confirm", sem o returncode), o que permite aceitar risco sobre falha estrutural. Registrar, não corrigir aqui.
