# Research: Compatibility Mermaid/C4 do Architecture Blueprint

## Escopo e evidência

- Baseline do renderer: bundle local `src/modules/ava-fabric-agents/summary/templates/html/mermaid.min.js`, declarado pelo Summary como Mermaid 11.14.0.
- Inicialização atual: `summary-template.html` carrega o bundle inline e chama `mermaid.initialize({ startOnLoad: false, securityLevel: 'loose' })` antes de `renderStaticDiagrams()`.
- Renderização atual: `renderMermaidSafely()` usa `mermaid.render(id, source)`; `renderStaticDiagrams()` renderiza cada `pre.mermaid` individualmente.
- Transporte atual: builder sanitiza o arquivo e injeta as fontes em `D.staticDiagrams`; a origem também é lida para os placeholders de Blueprint.
- O bundle contém tokens/gramática para `C4Context`, `C4Container`, `C4Component`, `C4Dynamic` e `C4Deployment`. Portanto, C4 não depende de plugin externo neste bundle, mas a presença de tokens não prova que toda construção emitida seja válida.
- O fixture atualmente presente em `projects/sophia/outputs/tobe/diagrams/architecture-blueprint.mmd` começa por `flowchart TB`; a evidência histórica de `C4Container` deve ser preservada como fixture separado para reproduzir a falha.
- A diferença entre o fixture histórico e o arquivo atual de Sophia é evidência relevante: o teste deve registrar o primeiro directive, hash e resultado de cada um, sem substituir um caso pelo outro.

## Decisões

### Decision 1 — Tratar C4 como dialeto nativo do bundle, não como extensão presumida

**Rationale:** o bundle distribuído contém lexer/parser C4. A validação deve verificar a versão efetivamente embutida e executar o mesmo `mermaid.render()` usado pelo HTML. Não se deve adicionar plugin ou inferir suporte apenas pela documentação.

**Alternatives considered:** instalar extensão/plugin C4; rejeitado porque altera o runtime sem evidência de necessidade e não representa o Summary autocontido.

O suporte deve ser confirmado em duas etapas: leitura de `mermaid.version` (ou API equivalente) no runtime carregado e `mermaid.render()` de fixture C4. A inspeção textual do bundle não é suficiente.

### Decision 2 — Usar duas camadas de validação

**Rationale:** uma validação estática detecta tipo, tokens, caracteres e regras de construção; uma validação dinâmica executa o bundle real. A validação dinâmica é a autoridade para publicação, pois captura incompatibilidades de parser e configuração.

**Alternatives considered:** somente regex/linter; rejeitado porque pode aceitar sintaxe que `mermaid.render()` rejeita.

### Decision 3 — Classificar a falha pela etapa que falha

Classificações obrigatórias:

- `INVALID_MERMAID`: parser rejeita fonte em um runtime conhecido e habilitado.
- `UNSUPPORTED_DIALECT`: tipo não reconhecido pelo bundle/configuração aceita.
- `UNSUPPORTED_C4_SYNTAX`: tipo C4 reconhecido, mas construção/keyword não é aceita.
- `RENDERER_CONFIGURATION_FAILURE`: bundle ausente, versão divergente, inicialização incompleta ou API indisponível.
- `MERMAID_VERSION_INCOMPATIBILITY`: fonte válida em outra versão, mas rejeitada no baseline configurado.
- `RENDERING_FAILURE`: validação/parser passa, mas renderização SVG falha por erro posterior do runtime/DOM.

A classificação pública usa `rootCause` em camelCase de campos, nunca `classification`. O relatório também contém `stage`, `confidence`, `construct`, `diagnosticEvidence` e `exactErrorMessage`.

### Decision 4 — Fazer a publicação depender do resultado dinâmico

**Rationale:** nenhum Blueprint obrigatório pode chegar ao HTML publicado sem renderização confirmada no mesmo Mermaid 11.14.0. Falha ou ausência de evidência é `BLOCKED`, não warning.

Ordem fechada: artefato → hashes/dialeto → probe de versão → probe C4 → validação estática → `mermaid.render()` → integridade → relatórios → decisão → promoção do HTML.

### Decision 5 — Não converter C4 silenciosamente

Conversão para `flowchart` só será permitida como transformação explícita, versionada e registrada com fonte, destino, regra aplicada e novo resultado de renderização. O default é regenerar ou bloquear.

### Decision 6 — Contrato público camelCase

JSON e Markdown compartilham o contrato definido em `data-model.md` e `contracts/blueprint-compatibility-report.schema.json`. Adapters internos podem usar `snake_case`, mas devem converter para `traceId`, `artifactPath`, `rendererVersion`, `rootCause`, `hashes` e demais campos antes da escrita.

### Decision 7 — Proveniência do produtor

O relatório registra o produtor identificado por metadados. Na ausência de metadados, usa o mapeamento documentado (`ava-asis-solution-delphi` para AS-IS e `ava-tobe-architecture-design` para TO-BE) com confiança média.

## Hipóteses a confirmar por testes

1. `C4Container` mínimo com `Person`, `Container`, `ContainerDb`, `System_Ext` e `Rel` renderiza no bundle local.
2. A falha histórica é causada por conteúdo específico (keyword, parâmetros, caracteres, escopo de boundary ou transformação), e não pela ausência geral do parser C4.
3. O resultado do bundle local e o resultado do arquivo HTML gerado são equivalentes quando a fonte e a configuração são iguais.
4. O fixture `flowchart` de Sophia continua renderizável após sanitização.
5. O runtime efetivamente carregado expõe uma versão verificável; caso contrário a publicação é bloqueada.

## Consequência

A implementação precisa criar fixtures mínimos por dialeto, um runner headless usando o bundle real, relatório JSON de compatibilidade e gate integrado antes da publicação do Summary. O teste deve preservar um caminho browser/HTML porque CLI ou parser isolado não comprova o comportamento do Summary.
