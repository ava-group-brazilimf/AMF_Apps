Ready for review
Select text to add comments on the plan
Config-driven AST analyzer path + live execution log for solution-delphi
Contexto
O agente ava-asis-solution-delphi reportou AST extraction failed — analyzer environment not configured e caiu em modo degradado (Glob/Grep/Read). Investigando a causa raiz: em solution-delphi.md:280-282, o comando Bash que invoca a extração AST contém um placeholder nunca resolvido:

Bash: python <ava-fabric-apps-agents>/.../run_ast_analysis.py \
  --project {project_name} --ava-analyzer-path {ava_ast_analyzer_path configurado}
{ava_ast_analyzer_path configurado} é texto literal — nunca foi conectado a nenhuma fonte real (nem env var, nem project-config.yaml). O script `run_ast_analysis.py` já suporta `--ava-analyzer-path` como CLI arg com fallback para environment mappings / env vars (`ava_ast_analyzers.*` / `AVA_AST_ANALYZER_HOME`) — o bug está inteiramente na instrução do agente, não no script.

Adicionalmente, o script hoje usa subprocess.run(..., capture_output=True) (linha 86-91): a saída do processo filho (run_pipeline.py/ava_ast_cli.exe, que pode levar até 30 min — timeout=1800) fica totalmente bloqueada até o fim — nada é mostrado ao usuário durante a execução, só um resumo final ou os últimos 2000 caracteres do stderr em caso de falha. Isso é exatamente o tipo de "travamento aparente" já corrigido no orquestrador nesta mesma sessão — aqui o problema é análogo, só que no nível do agente solution-delphi.

O usuário pediu, especificamente: (1) mover a configuração do path do analyzer para project-config.yaml em vez de depender de variável de ambiente; (2) replicar no template e no projeto Meu-ERP-007-AST-LLM-AS-IS-Orchestrator (path real do usuário: C:\Desenv\repo\tool\ava-fabric-delphi-analyzer — confirmado existente, com src/run_pipeline.py e bin/ava_ast_cli.exe); (3) o agente deve exibir o log de acompanhamento da execução da tool para o usuário.

Decisão
1. Novo campo ava_ast_analyzer_path em project-config.yaml
Adicionado logo após repository_path (mesmo padrão de path absoluto, mesmo estilo de comentário) em:

projects/_template/context/project-config.yaml (linha 6, com default "")
projects/Meu-ERP-007-AST-LLM-AS-IS-Orchestrator/context/project-config.yaml (valor real: "C:\\Desenv\\repo\\tool\\ava-fabric-delphi-analyzer")
2. solution-delphi.md Step 0 — resolver o path do config, não de placeholder morto
Ler ava_ast_analyzer_path de context/project-config.yaml (mesmo padrão já documentado na linha "Config:" do ## Input Contract, que passa a incluir este campo).
Construir o comando Bash condicionalmente: SE ava_ast_analyzer_path não-vazio → `--ava-analyzer-path "{ava_ast_analyzer_path}"`; SE vazio/ausente → omitir a flag, deixando `resolve_analyzer_path()` cair nos mapeamentos padrão (`ava_ast_analyzers.*`, `AVA_AST_ANALYZER_HOME`) sem quebrar nada.
Isso substitui o placeholder morto por uma resolução real, documentada e testável.
3. Log de acompanhamento em tempo real
Duas mudanças complementares — nenhuma sozinha resolve o problema:

run_ast_analysis.py: trocar subprocess.run(capture_output=True) por subprocess.Popen com leitura linha-a-linha do stdout (stderr redirecionado para o mesmo stream), imprimindo (flush=True) cada linha assim que chega — preservando o timeout de 1800s via checagem manual de deadline — e acumulando as linhas para gravar em run_ast_analysis.log ao final (mesmo path de log de hoje). Sem essa mudança, a saída do processo filho fica presa em memória até o fim independente de qualquer coisa que o agente faça.
solution-delphi.md Step 0: instruir explicitamente a invocar este Bash com run_in_background: true e usar a ferramenta Monitor para acompanhar e exibir a saída ao usuário em tempo real até a conclusão — é o único mecanismo do harness que realmente permite "acompanhamento" de um processo longo (uma chamada Bash síncrona já bloqueia o agente até o processo terminar, streaming ou não).
4. Versionamento
solution-delphi.md: 2.1.1 → 2.2.0 (MINOR — corrige bug de placeholder + comportamento aditivo de log em tempo real, nenhum campo de contrato removido).
module.yaml (asis-diagnostic): 1.8.0 → 1.8.1 (PATCH — nenhum novo agente registrado).
Arquivos a alterar
projects/_template/context/project-config.yaml — novo campo ava_ast_analyzer_path
projects/Meu-ERP-007-AST-LLM-AS-IS-Orchestrator/context/project-config.yaml — mesmo campo, valor real do usuário
src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md — Step 0 (resolução do path + run_in_background/Monitor), linha "Config:" do Input Contract, frontmatter version
src/modules/ava-fabric-agents/asis-diagnostic/utils/run_ast_analysis.py — streaming real do subprocess (Popen + loop de leitura com flush) em vez de capture_output=True
src/modules/ava-fabric-agents/asis-diagnostic/module.yaml — bump de versão
Documentação via Spec Kit
Criar specs/012-solution-delphi-ast-analyzer-config-path/ (spec.md, plan.md, tasks.md), seguindo o mesmo formato consolidado usado em specs/011 (Summary/Constitution Check/Technical Context/Implementation Phases/Complexity Tracking/Test Strategy para o plan.md; 7 categorias fixas para tasks.md).

Verificação
grep -c "AVA_.*_ANALYZER_HOME configurado" em solution-delphi.md → 0 (placeholder morto eliminado)
grep -n "ava_ast_analyzer_path" confirma presença nos 2 arquivos de config + no Step 0 do agente
Ler run_ast_analysis.py após a edição e confirmar que nenhuma linha do processo filho fica presa até o fim — o loop de leitura imprime (flush=True) assim que cada linha chega
python -m py_compile run_ast_analysis.py — confirma que a mudança de subprocess não quebra a sintaxe
Simular mentalmente o cenário do usuário: config com ava_ast_analyzer_path preenchido → comando Bash resultante usa esse valor, sem placeholder; ausência do campo → comando omite a flag e cai no fallback de env var existente, sem regressão