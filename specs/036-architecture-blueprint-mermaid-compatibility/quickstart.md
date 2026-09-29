# Quickstart de validação

## Pré-requisitos

- Python conforme o ambiente do repositório.
- Node.js/npm disponível para o runner headless, ou runtime browser usado pelos testes existentes.
- Bundle local em `src/modules/ava-fabric-agents/summary/templates/html/mermaid.min.js`.
- Fixture AS-IS e fixture TO-BE disponíveis em `projects/{project_name}/outputs/**/diagrams/architecture-blueprint.mmd`.

## Cenários obrigatórios

1. **Flowchart compatível** — validar e renderizar o Blueprint AS-IS de Sophia; resultado esperado: `ALLOW`.
2. **C4 mínimo compatível** — renderizar fixture com `C4Container`, `Person`, `Container`, `ContainerDb`, `System_Ext` e `Rel`; resultado esperado: suporte explícito e `ALLOW` se o bundle efetivamente renderizar.
3. **Matriz C4** — testar suporte nativo, plugin ausente, suporte desabilitado, keyword não suportada e construct malformado; cada caso deve receber `rootCause` distinto.
4. **C4 inválido** — alterar uma keyword/parâmetro; resultado esperado: `INVALID_MERMAID` ou `UNSUPPORTED_C4_SYNTAX` e `BLOCK`.
5. **Dialeto desconhecido** — usar cabeçalho não reconhecido; resultado esperado: `UNSUPPORTED_DIALECT` e `BLOCK`.
6. **Configuração/versionamento** — remover bundle, impedir leitura de `mermaid.version` ou alterar versão; resultado esperado: `RENDERER_CONFIGURATION_FAILURE` ou `MERMAID_VERSION_INCOMPATIBILITY` e `BLOCK`.
7. **Falha de renderização** — fonte que passa no parser, mas falha no SVG/DOM; resultado esperado: `RENDERING_FAILURE` e `BLOCK`.
8. **Integridade de transporte** — comparar todos os hashes do objeto `hashes`; qualquer divergência não registrada deve produzir `SOURCE_INTEGRITY_MISMATCH` e bloquear.
9. **Sophia atual versus histórico** — executar o fixture histórico `C4Container` e ler o arquivo real `projects/sophia/outputs/tobe/diagrams/architecture-blueprint.mmd`; registrar separadamente se o arquivo atual começa com `flowchart`.

## Fluxo de execução planejado

1. Ler o artefato e computar `hashes.rawArtifact`.
2. Detectar dialeto/constructs, carregar o bundle exato do Summary e extrair `mermaid.version`.
3. Executar probe C4 e validação estática; depois chamar `mermaid.render()` com a fonte observada.
4. Computar os seis checkpoints de `hashes` e comparar integridade.
5. Gerar `blueprint-compatibility-report.json` e `blueprint-compatibility-report.md` com campos camelCase.
6. Validar o relatório contra `contracts/blueprint-compatibility-report.schema.json`.
7. Avaliar `publicationAllowed`; somente `true` permite escrever/promover o HTML client-facing.
8. Inspecionar o HTML gerado: nenhum Blueprint obrigatório pode exibir `Syntax error in text` ou `mermaid version 11.14.0`.

## Resultado esperado

A publicação só pode prosseguir quando AS-IS e TO-BE exigidos tiverem validação estática, parsing dinâmico, SVG renderizado, transporte íntegro, versão baseline extraída do runtime e relatório camelCase válido. Qualquer resultado ausente ou inconclusivo é `BLOCK`; artefatos diagnósticos bloqueados devem ser marcados como não publicados.
