Ready for review
Select text to add comments on the plan
Plano: Guardrail "Artifact-Only" + Gate de Aprovação para o Pipeline TO-BE (F2)
Contexto
Foi reportado que, ao invocar orchestrator-tobe.md (F2), os agentes despachados acabam relendo o código legado completo novamente, tornando a esteira TO-BE lenta e cara em tokens. A esteira AS-IS (F1) já passou por uma otimização equivalente — specs/010-asis-agents-ast-artifact-consumption — tornando-a determinística e produzindo artefatos (outputs/asis/**) prontos para consumo por LLM, exatamente para que a F2 nunca precise reler o legado.

Investigação direta nos arquivos confirmou a causa raiz mais provável, com um precedente histórico idêntico já documentado:

docs/tobe-architecture-io-map.md (auditoria já existente) conclui em sua §3 que, no texto estático dos specs, nenhum dos 20 agentes de tobe-architecture/agents/ declara leitura de repository_path ou código legado — mas sua §4 documenta 15 bugs de path (arquivos referenciados em locais errados ou nunca produzidos por nenhum agente). Isso significa que, em runtime, vários artefatos declarados como entrada simplesmente não existem no path esperado.
specs/013-master-orchestrator-mandatory-spec-read é o precedente exato: quando orchestrator-asis.md era despachado via master-orchestrator.md, o sub-agente "improvisava" e caía para leitura manual de código-fonte completo — causa raiz: o DISPATCH @agent-id não instruía a IA a fazer Read() do .md completo do sub-agente antes de invocá-lo, então ela assumia o papel do sub-agente a partir de conhecimento genérico, não do spec literal. A correção foi um prefixo ⛔ Read(...) em todos os pontos de despacho. A própria spec 013, em sua seção de Exclusions, já apontava orchestrator-tobe.md → seus sub-despachos internos como o próximo PBI natural — nunca foi corrigido lá.
Confirmado por grep direto: os 25 pontos Invocar \agente.md`emorchestrator-tobe.mdnão têm nenhum prefixo⛔ Read(...)` — exatamente o mesmo gap da spec 013, agora plausivelmente causando o mesmo sintoma (agente improvisa releitura de legado quando um input declarado está ausente, em vez de seguir literalmente seu próprio Input Contract).
orchestrator-tobe.md já contém, no "Gate 0→1", um padrão forte de "detectar problema → parar → reportar ao usuário → aguardar decisão" (bloco 🚫 PROIBIÇÃO ABSOLUTA, relatório estruturado com trace_id/tabela, opções A/B/C, "aguardar ação do usuário"). Vários outros agentes (ex. test-plan-tobe.md) já têm uma convenção parcial ([MISSING INPUT: x]) mas nenhum chega a parar e aguardar aprovação explícita do usuário — hoje eles ou degradam silenciosamente ("continuar com...") ou dão HARD STOP sem relatório estruturado nem opções. coder-dotnet.md (guardrail G-9) é o único agente com um comportamento próximo do desejado.
O objetivo desta spec é generalizar esses três padrões já existentes e comprovados no próprio repositório — nunca inventar convenção nova — para fechar o gap real: (a) proibir releitura de código legado/fonte completo, (b) garantir que a IA sempre leia o spec completo do sub-agente antes de despachá-lo (fechando o mesmo gap que a spec 013 já corrigiu em outros orquestradores), e (c) parar e pedir aprovação do usuário quando um artefato obrigatório estiver ausente, em vez de improvisar.

Decisões de escopo confirmadas com o usuário:

Incluir a correção do "Dispatch Protocol" (prefixo ⛔ Read(...) nos 25 pontos de despacho) — é a causa raiz mais provável e mirror direto da spec 013.
Corrigir 2 bugs de path inequívocos (§4.4, §4.8-parcial do io-map) e rebaixar 2 de obrigatório para não-bloqueante (§4.6, §4.7) por apontarem para arquivos que estruturalmente não existem. Os demais 11 bugs do io-map ficam como exclusão explícita (PBI futuro).
Incluir como correção colateral: registrar no module.yaml os 7 agentes já despachados mas nunca registrados (violação Artigo IV), e introduzir version: nos 9 arquivos de agente que não têm esse campo (violação Artigo II) — ambos mecânicos, baixo risco, mesmo padrão que a spec 013 já aplicou como correção colateral em devops-agents/module.yaml.
Entregável: nova spec speckit specs/016-tobe-artifact-only-guardrail/
Seguir exatamente a convenção já usada em specs/010 e specs/013 (validada lendo os dois): spec.md (## 1. Agent Identity → ## 2. Problem Statement → ## 3. Decision → ## 4. User Scenarios (Given-When-Then) → ## 5. Quality Gate Requirements → ## 6. Dependencies → ## 7. Exclusions → ## 8. Assumptions → ## Success Criteria), plan.md (## Summary → ## Constitution Check → ## Technical Context → ## Implementation Phases → ## Complexity Tracking → ## Test Strategy), tasks.md (## Category N — <nome> com checkboxes N.M, terminando em ## Completion Checklist). Número de spec: 016 (próximo disponível — atual mais alto é 015-summary-remediation-agent).

Mudanças de conteúdo (o que vai dentro dos arquivos de agente)
1. Novo arquivo compartilhado — src/modules/ava-fabric-agents/shared/artifact-only-consumption-protocol.md
Segue a convenção já usada por shared/governance-apps.md / shared/backend-context-protocol.md (referenciado como [@artifact-only-consumption-protocol](../../shared/artifact-only-consumption-protocol.md) a partir de cada agente consumidor, mesmo padrão da linha 98 de orchestrator-tobe.md). Duas seções:

## 1. Proibição de Releitura de Código Legado — proibição explícita de Read/Glob em qualquer arquivo sob repository_path (lido de project-config.yaml) ou extensões .pas/.dfm/.dpr; proibição de leitura em massa da árvore outputs/tobe/source-code/** (mantendo as 3 exceções já legítimas hoje: escrita de Directory.Packages.props, escrita de README.md por módulo, checagem pontual de existência de docker-compose.yml); regra positiva — todo contexto necessário vem de artefatos já gerados em outputs/asis/** e outputs/tobe/**, conforme declarado no próprio Input Contract de cada agente. Prioridade sobre conhecimento genérico do domínio (mesmo framing de severidade de governance-apps.md).
## 2. Procedimento de Escalonamento — Artefato Obrigatório Ausente — generaliza o formato do Gate 0→1 e a tag [MISSING INPUT: x] já usada em test-plan-tobe.md, sem inventar vocabulário novo:
Input não-bloqueante ausente → [FONTE AUSENTE] {arquivo} — CONFIDENCE: LOW, log visível, pipeline continua (comportamento já existente, agora padronizado).
Input bloqueante ausente → novo relatório estruturado ⛔ [ARTIFACT GATE FAILED] com trace_id, projeto, fase, agente afetado, artefato ausente, path esperado, produzido por; opções A (fornecer manualmente e reexecutar) / B (pular com confiança degradada — só quando o artefato não for estruturalmente fundamental, ex. nunca para project-config.yaml ou bounded-context-map.md) / C (abortar e reportar ao PM); termina em "Aguardando decisão do usuário — NUNCA prosseguir automaticamente nem inventar o conteúdo do artefato ausente."
2. tobe-architecture/agents/orchestrator-tobe.md (2.3.0 → 2.4.0, MINOR)
Nova seção ## Dispatch Protocol (logo após ## Agent Team Gerenciado), adaptada de master-orchestrator.md:201-227: antes de qualquer Invocar \{arquivo}.md`, executar Read() completo do arquivo-alvo e seguir seus Steps literalmente — nunca improvisar. Cobre explicitamente os 2 despachos cross-module (@ava-asis-gaps-risks, @ava-stack-docs-researcher) e o {resolved_coder_agent}` dinâmico.
Prefixo ⛔ Read({path}) OBRIGATÓRIO (ver § Dispatch Protocol) → em todos os 25 pontos Invocar (linhas ~106 a ~1622), sem renumerar nada — mesmo padrão da spec 013 (linha alterada, sem reindexação).
Linha de referência ao novo @artifact-only-consumption-protocol perto de ## Canonical Inputs.
Correção de path §4.4 do io-map: outputs/tobe/migration-plan.md → outputs/tobe/docs/migration-plan.md na tabela de input da Fase 4.5.
Os blocos HARD STOP existentes (Fase 4.2, 4.3, 4.5) ganham uma cláusula apontando para o novo formato de relatório de escalonamento em vez de "interromper" genérico.
3. tobe-architecture/module.yaml (1.3.0 → 1.3.1, PATCH)
Adicionar as 7 entradas ausentes (adr-tobe.md, coder-dotnet.md, coexistence-strategy-tobe.md, designer-system-tobe.md, risk-mitigation-tobe.md, user-journeys-tobe.md, e confirmar a 7ª durante implementação — todas já confirmadas como despachadas por orchestrator-tobe.md via grep de Invocar). Não adicionar dotnet-nuget-policy.md (é um include estilo shared/, não um agente despachado — sua ausência de version: fica registrada como observação fora de escopo, não corrigida aqui).

4. Os 20 arquivos de agente dispatados por orchestrator-tobe.md
Lista: architecture-decision-matrix-tobe.md, adr-tobe.md, architecture-design-tobe.md, database-policy-tobe.md, database-design-tobe.md, security-design-tobe.md, architecture-technical-tobe.md, migration-plan-tobe.md, measure-size-tobe.md, coexistence-strategy-tobe.md, risk-mitigation-tobe.md, openapi-spec-tobe.md, coder-dotnet.md, docs-tobe.md, developer-guide-tobe.md, test-plan-tobe.md, user-journeys-tobe.md, designer-system-tobe.md, azure-infra-estimator-tobe.md.

Para cada um, mudança mecânica e pequena:

Uma linha de referência a @artifact-only-consumption-protocol perto do ## Input Contract / ## Input Sources.
Cada cláusula existente de "input obrigatório ausente → interromper" ganha um ponteiro para o novo formato de relatório de escalonamento (Seção 2 do protocolo compartilhado) em vez de texto solto — sem reescrever as tabelas de Input Contract existentes.
Nos 9 arquivos sem version: no frontmatter (database-policy-tobe.md, database-design-tobe.md, architecture-technical-tobe.md, risk-mitigation-tobe.md, openapi-spec-tobe.md, coder-dotnet.md, docs-tobe.md, user-journeys-tobe.md, designer-system-tobe.md), introduzir version: "1.0.0".
Correções extras bundladas em 2 desses arquivos:
risk-mitigation-tobe.md: path §4.4 (mesma correção do item 2).
azure-infra-estimator-tobe.md: path §4.8-parcial — outputs/tobe/sizing-report.md → outputs/tobe/docs/sizing-report.md no Step 1 "Read Priority".
test-plan-tobe.md: rebaixar architecture-technical.md de ✅ obrigatório para ❌ não-bloqueante (§4.6 do io-map — arquivo nunca é produzido por nenhum agente).
designer-system-tobe.md: verificar e, se necessário, rebaixar outputs/asis/docs/screen-flow.md (§4.7 do io-map) para não-bloqueante pelo mesmo motivo.
5. docs/tobe-architecture-io-map.md
Atualizar §3 (conclusão passa a declarar a proibição como imposta, não apenas observada) e as entradas §4.4/§4.6/§4.7/§4.8 com nota "Corrigido em specs/016". Sem bump de versão (é documentação, não agente).

6. CHANGELOG.md
Entrada nova descrevendo o guardrail + gate de aprovação (padrão já usado nas entradas anteriores do arquivo, ex. "Add Summary Remediation Agent").

Fases de implementação (para plan.md)
Criar o arquivo compartilhado artifact-only-consumption-protocol.md (nada mais depende dele até existir).
Endurecer orchestrator-tobe.md (Dispatch Protocol + 25 prefixos ⛔ Read + referência ao protocolo + correção de path §4.4 + cláusulas de HARD STOP apontando pro novo relatório).
Registrar os 7 agentes ausentes em module.yaml (pode rodar em paralelo à fase 2).
Aplicar a mudança mecânica nos 20 arquivos de agente (referência ao protocolo compartilhado + ponteiro nas cláusulas de bloqueio + introduzir version: nos 9 sem esse campo); tratar com atenção extra os 3 arquivos que carregam uma segunda mudança (risk-mitigation-tobe.md, azure-infra-estimator-tobe.md, test-plan-tobe.md, designer-system-tobe.md).
Sincronizar docs/tobe-architecture-io-map.md (§3/§4) e CHANGELOG.md.
Verificação: checagens baseadas em grep/contagem (ver abaixo) + trace manual de um cenário bloqueante e um não-bloqueante para confirmar que o texto renderiza como esperado.
Cenários BDD para spec.md (Artigo VI)
Nominal: artefato obrigatório presente → agente lê apenas os artefatos declarados no seu Input Contract, nunca toca repository_path nem lê outputs/tobe/source-code/ em massa.
Artefato bloqueante ausente: gate ⛔ [ARTIFACT GATE FAILED] dispara com o relatório estruturado completo (trace_id, fase, artefato, path, opções A/B/C) e a esteira aguarda decisão do usuário — sem estimar, sem reler legado.
Dispatch Protocol: antes de qualquer Invocar, o orquestrador já leu o .md completo do sub-agente; seus logs internos permanecem visíveis na sessão (não resumidos).
Artefato não-bloqueante ausente: log [FONTE AUSENTE] ... CONFIDENCE: LOW visível, sem parar a esteira.
Critérios de sucesso / verificação
grep -c "⛔ Read(" em orchestrator-tobe.md → 25.
grep -c "artifact-only-consumption-protocol" → presente em orchestrator-tobe.md + nos 20 arquivos de agente.
module.yaml: os 7 IDs previamente ausentes agora presentes em agents:.
grep -c "version:" nos 9 arquivos antes sem esse campo → 1 cada.
grep -c "ast-raw/[a-z]+/extraction\|repository_path" dentro de qualquer novo texto adicionado → 0 (garantindo que o guardrail não referencia acidentalmente paths legados).
Balanceamento de fences markdown em todos os arquivos tocados (mesmo checklist estrutural usado em specs/010).
Nenhum campo de Input/Output Contract existente removido (apenas adição/anotação) — SemVer MINOR/PATCH consistente com a tabela acima.
Observações fora de escopo (documentar em spec.md §7 Exclusions)
Os 11 bugs restantes do io-map §4 (ambiguidade .NET coder §4.1, ownership do build validator §4.2, fases sem seção dedicada §4.3, etc.) — ficam para PBI futuro.
Ambiguidade {resolved_coder_agent} para .NET (§4.1) não é resolvida — o novo ⛔ Read(...) só é tão bom quanto o path já resolvido pelo CODER_AGENTS map existente.
dotnet-nuget-policy.md — falta de version: e localização não-padrão ficam registradas, não corrigidas.