# Modelo de dados: Compatibilidade do Blueprint Mermaid

## `BlueprintCompatibilityReport` — contrato público

Todos os campos deste contrato usam **camelCase**. Qualquer representação interna em `snake_case` deve ser tratada como adapter interno e convertida antes da escrita dos relatórios JSON/Markdown.

| Campo                    | Tipo         | Obrigatório | Regra                                              |
| ------------------------ | ------------ | ----------: | -------------------------------------------------- |
| `traceId`                | string       |         sim | Identificador propagado sem mutação                |
| `projectName`            | string       |         sim | Projeto ativo                                      |
| `artifactPath`           | string       |         sim | Caminho relativo do `.mmd`                         |
| `diagramId`              | string       |         sim | Identificador estável do Blueprint                 |
| `rendererVersion`        | string       |         sim | Versão extraída do runtime Mermaid carregado       |
| `rendererSource`         | string       |         sim | Bundle/path efetivamente carregado pelo Summary    |
| `detectedDialect`        | string       |         sim | `flowchart`, `C4Container` ou outro tipo detectado |
| `c4Detected`             | boolean      |         sim | Indica constructs/dialeto C4                       |
| `c4SupportedByRenderer`  | boolean/null |         sim | Resultado do probe real de capacidade C4           |
| `staticValidationStatus` | enum         |         sim | `PASS`, `FAIL`, `INCONCLUSIVE`                     |
| `runtimeRenderStatus`    | enum         |         sim | `PASS`, `FAIL`, `NOT_RUN`                          |
| `rootCause`              | enum         |         sim | Classificação pública canônica                     |
| `stage`                  | enum         |         sim | Estágio em que a causa foi determinada             |
| `confidence`             | enum         |         sim | `HIGH`, `MEDIUM`, `LOW`                            |
| `construct`              | string       |         sim | Construct afetado ou string vazia                  |
| `diagnosticEvidence`     | object       |         sim | Erro exato, linha/coluna, probe e configuração     |
| `hashes`                 | object       |         sim | Hashes SHA-256 de todos os checkpoints             |
| `exactErrorMessage`      | string       |         sim | Mensagem original do renderer, se houver           |
| `recommendedFix`         | string       |         sim | Ação de remediação                                 |
| `publicationAllowed`     | boolean      |         sim | Só `true` com todos os gates aprovados             |

### Campos de proveniência do produtor

Quando disponíveis, o relatório também deve conter `producingAgent`, `producingAgentRole`, `sourceContractPath`, `artifactContractPath`, `generationPhase` e `artifactRole`.

| Artefato        | `producingAgent`               | Caminho esperado                                   | Fase |
| --------------- | ------------------------------ | -------------------------------------------------- | ---- |
| AS-IS Blueprint | `ava-asis-solution-delphi`     | `outputs/asis/diagrams/architecture-blueprint.mmd` | F1   |
| TO-BE Blueprint | `ava-tobe-architecture-design` | `outputs/tobe/diagrams/architecture-blueprint.mmd` | F2   |

Se a origem não estiver registrada em metadados, usar o mapeamento acima e registrar `confidence: MEDIUM` em `diagnosticEvidence`.

## Hash checkpoints

```json
"hashes": {
    "rawArtifact": "sha256...",
    "sanitizedContent": "sha256...",
    "staticDiagrams": "sha256...",
    "renderAllDiagramsInput": "sha256...",
    "renderStaticDiagramsInput": "sha256...",
    "rendererInput": "sha256..."
}
```

Todo hash é SHA-256. Hash ausente, mutação não documentada ou divergência não explicada produz `rootCause: SOURCE_INTEGRITY_MISMATCH` ou `EVIDENCE_UNAVAILABLE` e `publicationAllowed: false`.

## Root cause e estágios

`rootCause` permitido: `VALID_MERMAID`, `INVALID_MERMAID`, `UNSUPPORTED_DIALECT`, `UNSUPPORTED_C4_SYNTAX`, `RENDERER_CONFIGURATION_FAILURE`, `MERMAID_VERSION_INCOMPATIBILITY`, `RENDERING_FAILURE`, `SOURCE_INTEGRITY_MISMATCH`, `EVIDENCE_UNAVAILABLE`.

`stage` permitido: `STATIC_VALIDATION`, `RUNTIME_VERSION_PROBE`, `C4_CAPABILITY_PROBE`, `RUNTIME_RENDER`, `SOURCE_INTEGRITY`, `PUBLICATION_GATE`, `SUMMARY_SMOKE_TEST`.

## Matriz de capacidade C4

| Caso                                              | Classificação                                             |
| ------------------------------------------------- | --------------------------------------------------------- |
| C4 nativo disponível e `mermaid.render()` passa   | `VALID_MERMAID`                                           |
| Plugin/extensão necessário e não carregado        | `RENDERER_CONFIGURATION_FAILURE` ou `UNSUPPORTED_DIALECT` |
| C4 existe, mas está desabilitado na inicialização | `RENDERER_CONFIGURATION_FAILURE`                          |
| Keyword C4 não suportada                          | `UNSUPPORTED_DIALECT` ou `UNSUPPORTED_C4_SYNTAX`          |
| Construct C4 malformado                           | `INVALID_MERMAID` ou `UNSUPPORTED_C4_SYNTAX`              |
| Runtime não inicializa                            | `RENDERER_CONFIGURATION_FAILURE`                          |
| Versão real diverge do baseline                   | `MERMAID_VERSION_INCOMPATIBILITY`                         |

C4 nunca é considerado suportado apenas por inspeção textual do bundle; exige probe de runtime e teste real com `mermaid.render()`.

# Modelo de dados: Compatibilidade do Blueprint Mermaid

## `BlueprintCompatibilityReport`

| Campo                  | Tipo        | Obrigatório | Regra                                                   |
| ---------------------- | ----------- | ----------: | ------------------------------------------------------- |
| `schema_version`       | string      |         sim | Versão do contrato do relatório                         |
| `project_name`         | string      |         sim | Identidade do projeto ativo                             |
| `trace_id`             | string      |         sim | Propagado sem mutação                                   |
| `artifact_path`        | string      |         sim | Caminho relativo do `.mmd`                              |
| `artifact_role`        | enum        |         sim | `asis` ou `tobe`                                        |
| `source_sha256`        | string      |         sim | Hash da fonte validada                                  |
| `sanitized_sha256`     | string/null |         sim | Hash após sanitização documentada                       |
| `source_unchanged`     | boolean     |         sim | Comparação origem → transporte                          |
| `diagram_type`         | enum/string |         sim | Tipo detectado pela primeira diretiva                   |
| `dialect`              | enum        |         sim | `flowchart`, `c4`, outro suportado ou `unknown`         |
| `mermaid_version`      | string      |         sim | Versão efetiva do bundle/runtime                        |
| `bundle_path`          | string      |         sim | Bundle usado no teste                                   |
| `configuration`        | object      |         sim | `startOnLoad`, `securityLevel` e flags relevantes       |
| `static_validation`    | enum        |         sim | `PASS` ou `FAIL`                                        |
| `dynamic_validation`   | enum        |         sim | `PASS` ou `FAIL`                                        |
| `render_validation`    | enum        |         sim | `PASS` ou `FAIL`                                        |
| `classification`       | enum        |         sim | Uma das classificações definidas em `research.md`       |
| `constructs`           | array       |         sim | Keywords detectadas e status por construct              |
| `diagnostics`          | array       |         sim | Mensagem, linha/coluna, estágio e evidência             |
| `publication_decision` | enum        |         sim | `ALLOW` somente com todos os checks PASS; senão `BLOCK` |
| `generated_at`         | datetime    |         sim | Timestamp UTC                                           |

## Invariantes

1. `publication_decision = ALLOW` exige `static_validation = PASS`, `dynamic_validation = PASS`, `render_validation = PASS`, versão efetiva igual ao baseline e integridade de transporte verdadeira.
2. Ausência de versão, bundle, resultado dinâmico ou evidência de renderização implica `BLOCK`.
3. `C4Container` exige resultado explícito para cada constructo encontrado; não pode ser classificado apenas como `VALID_MERMAID` sem avaliação C4.
4. Hashes devem permitir comparar arquivo, conteúdo sanitizado, `D.staticDiagrams` e fonte passada a `mermaid.render()`.
5. `source_unchanged = false` não é falha automaticamente se houver transformação registrada; a fonte transformada precisa ser revalidada. Transformação não registrada implica `BLOCK`.

## `RootCauseClassification`

```text
stage: DETECTION | STATIC_PARSE | RUNTIME_INIT | DYNAMIC_PARSE | SVG_RENDER | TRANSPORT | PUBLICATION
classification: INVALID_MERMAID | UNSUPPORTED_DIALECT | UNSUPPORTED_C4_SYNTAX |
                RENDERER_CONFIGURATION_FAILURE | MERMAID_VERSION_INCOMPATIBILITY |
                RENDERING_FAILURE | VALID_MERMAID
confidence: HIGH | MEDIUM | LOW
```
