Ready for review
Select text to add comments on the plan
Gate de aprovação humana na F3S (SpecKit)
Context
A F3S hoje termina sem que ninguém decida nada. O run de nopcommerce-04 (2026-08-21) fechou com verdict: APPROVED_WITH_FINDINGS carregando dois blockers CRITICAL — CMK do Always Encrypted não definido (EDGE-W0-002) e tecnologia de feature flags não escolhida (EDGE-W0-005) — e o exit gate liberou a F4 assim mesmo, porque ele só confere presença de arquivo. O _verdict_rule_check que adicionamos registrou a incoerência no JSON, mas nada a levou até uma pessoa.

Depois das correções desta sessão o pipeline nunca trava: erro degrada, a fase fica como executada e a pendência vai para o relatório de remediação. Isso resolveu o travamento silencioso, mas criou a ponta solta oposta — um achado crítico atravessa a esteira inteira sem que ninguém tome ciência.

Este plano fecha essa ponta: quando houver achado crítico ou relevante, o operador é avisado e decide; ao seguir, fica registrado no próprio arquivo de compliance quem aprovou, em que papel e quando.

Decisões tomadas com o usuário:

Decisão	Escolha
Critério de disparo	verdict=BLOCKED OU finding critical/high OU _verdict_rule_check.consistent == false
Modo manual	Pergunta e espera. "Não" para a F3S — única exceção intencional ao "erro nunca trava fase"
Modo automático	Pergunta Nome/Papel opcionalmente, com timeout. Estourou o tempo, segue sem travar nada
Sem aprovador informado	status: "auto_acknowledged", sem nome — não afirma que alguém revisou
Validade da aprovação	Expira quando os achados mudam (atrelada a fingerprint)
A assimetria é deliberada: em manual há uma pessoa a quem perguntar e a decisão dela vale; em automático não há, e inventar um aprovador seria pior do que registrar honestamente que ninguém revisou.

1. Nova tool determinística: src/shared/tools/speckit_compliance_gate.py
Segue o padrão já estabelecido nas outras tools da F3S: persiste em disco, não depende do stdout, e o runner lê o arquivo. Isso evita capturar saída de subprocess e mantém o achado auditável.

Modos:

--evaluate (padrão) — lê compliance-status.json, classifica, calcula o fingerprint, grava outputs/tobe/speckit/compliance-gate.json, imprime o painel legível. Sempre exit 0.
--approve --name "..." --role "..." [--comments "..."] — revalida o fingerprint e grava a assinatura nominal.
--acknowledge --mode auto — grava o reconhecimento automático sem nome.
--reject --name "..." --role "..." — grava a recusa.
--status — só consulta, para scripts e para o exit gate.
Fingerprint — sha256 sobre (id, severity, summary) ordenados dos findings bloqueantes + o graph_checksum do traceability.json. É o que faz a aprovação expirar: regerar specs/tasks muda o checksum, muda o fingerprint, e o gate pergunta de novo. Sem isso uma assinatura antiga cobriria conteúdo que ninguém viu.

Bloco de aprovação gravado dentro de compliance-status.json. Reusa o vocabulário de src/shared/schemas/wave-approval.schema.json (reviewer, reviewer_role, approved_at, status) — o repo já tem esse vocabulário para aprovação humana de wave; inventar outro criaria dois dialetos para a mesma coisa. O enum ganha dois estados que o caso da F3S exige:

status	Significado	Exit gate
approved	pessoa informou Nome e Papel	PASS
auto_acknowledged	modo automático, ninguém informou	PASS
rejected	pessoa recusou	FAIL
pending	ainda não avaliado	FAIL
expired	achados mudaram desde a assinatura	FAIL
"approval": {
  "status": "approved",
  "reviewer": "Rafael Almeida",
  "reviewer_role": "Tech Lead",
  "comments": "",
  "approved_at": "2026-08-21T11:40:00-03:00",
  "approved_at_source": "a.st1.ntp.br",
  "ntp_fallback": false,
  "runner_mode": "manual",
  "approved_fingerprint": "sha256:…",
  "blockers_acknowledged": ["NORM-001", "NORM-002", "NORM-003"]
}
Em auto_acknowledged, reviewer e reviewer_role ficam vazios e entra "note": "execução automática — nenhuma pessoa informou aprovação; os blockers abaixo seguiram sem revisão". Quem ler o arquivo depois distingue à primeira vista uma revisão de um seguimento automático.

O timestamp vem de ntp_time.resolve() em src/shared/utils/ntp_time.py, que já devolve (timestamp, houve_fallback, servidor). Registrar a fonte é o que separa uma data auditável de um datetime.now() que qualquer relógio desajustado falsifica — e o módulo já foi escrito exatamente para tornar esse fallback audível.

Além do bloco no JSON, append em approval-log.jsonl: uma reaprovação não pode apagar a assinatura anterior.

2. Preservar a assinatura no normalizador
speckit_compliance_normalize.py reescreve compliance-status.json inteiro. Do jeito que está, rodar a wave6b de novo apagaria a aprovação.

Em normalize(), ler o approval existente antes de gravar e carregá-lo adiante — mantendo-o quando o fingerprint ainda bate, rebaixando para expired com o motivo quando não bate. Sem esse cuidado o gate vira teatro: assina, e o passo seguinte limpa.

3. DAG: nova wave6c em src/shared/data/pipeline-dag/F3S.yaml
Entre a wave6b (normalização) e a wave7 (exit gate) — precisa do compliance-status.json já canônico e precisa decidir antes de a F4 ser liberada.

- id: wave6c
  depends_on: [wave6b]
  blocking: true
  implemented: true
  tools:
    - id: speckit-compliance-gate
      requires_approval: true     # o runner lê esta chave e conduz o prompt
      on_fail: warn
      command: ["{python}", "src/shared/tools/speckit_compliance_gate.py",
                "--project", "{project}", "--evaluate", "--json"]
Atualizar também o cabeçalho de política do F3S.yaml: a exceção ("um 'Não' humano em modo manual é a única coisa que trava a esteira; o modo automático nunca trava") precisa estar escrita ao lado da regra que ela excepciona.

4. Propagar requires_approval — src/shared/tools/pipeline_plan.py
dag_steps() monta o dict do passo com uma lista fixa de chaves (~linha 246, onde on_fail é lido). Uma chave nova no YAML não chega ao runner sem ser adicionada ali. Uma linha, ao lado de on_fail.

5. Runner — ava-pipeline-runner-cli.py
safe_input_timeout(prompt, timeout_s) — novo, irmão de safe_input
safe_input (~linha 40) usa msvcrt.getwch(), que bloqueia para sempre. A versão com prazo faz laço de msvcrt.kbhit() contra um deadline de time.monotonic() e devolve None no estouro.

Detalhe que decide se a coisa é usável: o prazo vale só até a primeira tecla. Quem começou a digitar não pode ter o nome cortado no meio por um cronômetro. Depois do primeiro caractere, o comportamento é o de safe_input. O prompt mostra a contagem regressiva.

_solicitar_aprovacao(project, gate_data, auto_mode)
Irmã de _confirmar_risco (~linha 1210), mesmo formato de painel.

Imprime os blockers: id, severidade, resumo, evidência, remediação — nos dois modos. Dar ciência é o ponto; o modo só muda o que acontece depois.
Mostra a incoerência de veredito quando houver.
Manual: pergunta [S]im / [N]ão, sem prazo.
"S" → coleta Name e Role com validação (não vazio, ≥ 2 caracteres, reprompt até válido) → --approve.
"N" → --reject → esteira para.
Automático: oferece Nome e Papel com timeout de 30 s, um campo de cada vez.
Preenchidos → --approve com runner_mode: "auto".
Timeout, vazio, ou sem console → --acknowledge --mode auto e segue.
EOFError/KeyboardInterrupt → em manual, False (como já faz _confirmar_risco); em automático, reconhece e segue.
Hook no laço de execução
Depois que um passo kind == "tool" com requires_approval executa, ler compliance-gate.json. Se requires_approval e não houver aprovação válida, chamar _solicitar_aprovacao.

Aprovado / reconhecido → _mark_executed, segue.
Recusado (só possível em manual) → aborted.append(phase), _write_status_html, _save_runner_state(..., idx) — idx, não idx + 1, para o passo ser reavaliado na retomada — e break.
Este é o único caminho que volta a atribuir bloqueio. O comentário em _abort_pipeline (~linha 4632) diz hoje que nenhum caminho de erro trava — precisa registrar a exceção, senão o próximo leitor conclui que é regressão e "conserta".

Registrar via _record_degradation nos três desfechos (aprovado com blockers, reconhecido automaticamente, recusado), para que apareça no remediation-report.json e no banner de retomada.

6. Exit gate — artifact_gate_speckit.py
check_item() já despacha por kind (any_file, manifest_features, dir). Adicionar kind: "human_approval": lê o compliance-status.json apontado, present = True quando approval.status ∈ {approved, auto_acknowledged} e o approved_fingerprint bate com o atual. O detail nomeia quem assinou e quando — ou diz que seguiu em modo automático sem revisão, ou o que falta.

Novo item em exit_gate.items do F3S.yaml:

- path: "outputs/tobe/speckit/compliance-status.json"
  kind: human_approval
  produced_by: "speckit-compliance-gate (F3S, wave6c) + decisão do operador"
7. Contrato do agente
Em src/modules/ava-fabric-agents/speckit/agents/compliance-agent.md, o Output Contract ganha o bloco approval como campo escrito pelo gate, nunca pelo agente. Sem isso o agente eventualmente vai preenchê-lo sozinho — é o mesmo padrão de desvio que já produziu o compliance-summary.json em outputs/deliverables/.

8. Documentação
8.1 Spec via SpecKit — specs/042-speckit-compliance-approval-gate/
Segue a convenção das specs 039–041 (spec.md + plan.md + tasks.md), com o mesmo cabeçalho de 041-runner-output-contract-enforcement: Feature Branch, Created, Status, Change Type, Origem.

spec.md — Change Type: modify-existing + new-tool, sem agente novo.

Problem Statement: o exit gate confere presença de arquivo, não conteúdo. O run de 2026-08-21 liberou a F4 com dois blockers CRITICAL e um veredito que contradiz a regra da própria spec do agente. Ninguém foi perguntado.
User Stories:
US1 — como operador, quero ser avisado dos achados críticos antes de a F4 ser liberada, para decidir com conhecimento em vez de descobrir na F4.
US2 — como responsável técnico, quero que minha decisão de seguir fique registrada com meu nome, papel e data no próprio artefato de conformidade.
US3 — como operador de execução automática, quero que a esteira nunca pare, e que o arquivo diga honestamente que ninguém revisou.
US4 — como auditor, quero que uma assinatura deixe de valer quando os artefatos mudam, para que ela nunca cubra conteúdo que ninguém viu.
Requirements: critério de disparo; enum de status; campos obrigatórios da assinatura; regra de expiração por fingerprint; comportamento por modo.
Acceptance: os seis cenários da seção Verificação, um a um.
plan.md — Constitution Check (a política "erro nunca trava fase" e a exceção que esta spec introduz, com a justificativa: recusa humana é decisão, não erro) e Architecture (divisão tool/runner e por que o prompt vive no runner: safe_input lê via msvcrt e o subprocess da tool não tem a decisão de auto_mode).

tasks.md — categorias numeradas no padrão da 041: 1. Governança · 2. Tool de gate · 3. Preservação da assinatura · 4. DAG e propagação · 5. Runner e entrada com prazo · 6. Exit gate · 7. Verificação · 8. Documentação.

8.2 Documento de design — docs/plan/speckit-compliance-approval-gate.md
Mesmo formato de docs/plan/speckit-planning-layer.md: Context → evidência medida → decisão → mecanismo → verificação. É o documento que explica por que o gate existe, com os números do incidente real (verdict: APPROVED_WITH_FINDINGS sobre EDGE-W0-002 e EDGE-W0-005, 731k tokens de análise gravados no diretório errado, exit gate PASS mesmo assim).

Cobre o que a spec não cobre por ser mais estreita:

a tabela de decisão dos quatro modos (manual S/N, auto com e sem dados);
por que auto_acknowledged é um estado próprio e não approved com reviewer: "AUTO" — a distinção entre revisão e carimbo tem de sobreviver na leitura do arquivo, não só na intenção de quem escreveu;
por que o timestamp vem do NTP e não de datetime.now();
o limite honesto: rodando sempre em automático, o gate é aviso e registro de auditoria, não barreira. Quem depende da barreira roda em manual. Isso precisa estar escrito, senão o gate é lido como garantia que ele não dá.
8.3 Índice
docs/agents-catalog.md e CHANGELOG.md recebem a entrada da 042, como as specs anteriores fizeram.

Arquivos
Arquivo	Mudança
src/shared/tools/speckit_compliance_gate.py	novo — avaliação, fingerprint, assinatura
src/shared/tools/speckit_compliance_normalize.py	preservar/expirar approval
src/shared/data/pipeline-dag/F3S.yaml	wave6c, item de exit gate, nota de política
src/shared/tools/pipeline_plan.py	propagar requires_approval
ava-pipeline-runner-cli.py	safe_input_timeout + _solicitar_aprovacao + hook
src/modules/.../utils/artifact_gate_speckit.py	kind: human_approval
src/modules/.../agents/compliance-agent.md	documentar o bloco
specs/042-speckit-compliance-approval-gate/	novo — spec.md, plan.md, tasks.md
docs/plan/speckit-compliance-approval-gate.md	novo — documento de design
docs/agents-catalog.md, CHANGELOG.md	entrada da 042
Verificação
nopcommerce-04 já está no estado exato que dispara o gate — 3 findings critical/high e _verdict_rule_check.consistent == false. Serve como fixture real, sem precisar fabricar cenário.

1. Avaliação dispara e o exit gate fecha a F4

python src/shared/tools/speckit_compliance_gate.py --project nopcommerce-04 --evaluate --json
# espera: requires_approval=true, 3 blockers, exit 0
python src/modules/ava-fabric-agents/speckit/utils/artifact_gate_speckit.py \
    --project nopcommerce-04 --gate exit
# espera: FAIL — aprovação ausente  (hoje passa; deve passar a reprovar)
2. Assinatura nominal libera

python src/shared/tools/speckit_compliance_gate.py --project nopcommerce-04 \
    --approve --name "Rafael Almeida" --role "Tech Lead"
python src/modules/ava-fabric-agents/speckit/utils/artifact_gate_speckit.py \
    --project nopcommerce-04 --gate exit          # espera: PASS
Conferir em compliance-status.json: reviewer, reviewer_role, approved_at com offset -03:00 e approved_at_source nomeando o servidor NTP.

3. Reconhecimento automático também libera

python src/shared/tools/speckit_compliance_gate.py --project nopcommerce-04 \
    --acknowledge --mode auto
# exit gate: PASS, com detail dizendo que seguiu sem revisão humana
4. Expiração — reexecutar speckit_task_compiler.py compile (muda o graph_checksum), rodar --evaluate de novo e confirmar que a aprovação aparece como expired e o exit gate volta a reprovar.

5. Modo automático não trava — rodar o runner na opção 2 sem tocar no teclado e cronometrar: o prompt aparece, expira em 30 s, a esteira segue e termina na wave7 com auto_acknowledged. Depois repetir digitando Nome e Papel dentro do prazo e confirmar assinatura nominal.

6. Prompt manual — runner na opção 1 até a wave6c: "N" (esteira para, estado salvo, rejected gravado), "S" com nome vazio (reprompt), "S" válido (segue e assina).

Testes automatizados

tests/ava-fabric-agents/speckit/test_speckit_compliance_gate.py (novo): disparo nos três gatilhos; ausência de disparo quando limpo; estabilidade e invalidação do fingerprint; assinatura nominal completa; auto_acknowledged sem nome; --approve recusado quando o fingerprint mudou; append no approval-log.jsonl; fallback de NTP registrado.
test_speckit_compliance_normalize.py: aprovação sobrevive à re-normalização com mesmo fingerprint; vira expired quando muda.
test_artifact_gate_speckit.py: kind: human_approval nos cinco estados.
test_pipeline_plan.py: wave6c na ordem esperada e requires_approval chegando ao passo — o teste de ordem das tools já existe e é o lugar natural.
Smoke de _solicitar_aprovacao e safe_input_timeout no padrão de extração por AST já usado nesta sessão, com o teclado mockado: manual S/N, nome vazio, auto com timeout, auto com dados dentro do prazo.
Rodar ao final: python -m pytest tests/tools tests/ava-fabric-agents -q. Baseline atual: 16 falhas pré-existentes não relacionadas — o número não pode subir.

7. Documentação confere com o código — a spec 042 e o docs/plan/speckit-compliance-approval-gate.md são escritos depois da implementação passar na verificação, e os comandos que eles citam são copiados dos que realmente rodaram aqui. Documentação escrita antes do código descreve a intenção; escrita depois, descreve o que existe — e é a segunda que serve a quem for manter isto.