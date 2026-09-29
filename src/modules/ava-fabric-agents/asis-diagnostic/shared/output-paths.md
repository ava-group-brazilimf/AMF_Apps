# Output Paths — AVA AS-IS Module

Contratos de path canônicos. Base: `projects/{project_name}/outputs/asis/`

---

## Orchestrator
| Artifact | Path |
|----------|------|
| Master Report | `asis/master-report.md` |

## Solution Agent (Delphi/VB)

> Delphi variant (`ava-asis-solution-delphi`, v2.1.1+) consumes 9 deterministic
> AST JSON artifacts under `asis/delphi-ast-raw/compressed/` (the token-optimized
> variant — not `extraction/`, which is pretty-printed/raw-fidelity only) as its
> primary knowledge source, including `09_test_coverage.json` (v2.1.0+, feeds the
> `NO_AUTOMATED_TEST_COVERAGE` Migration Readiness risk — see the agent's own
> `## Input Contract`) and generates `.mmd` diagrams only — no `.drawio`
> (consolidated `.drawio` views are synthesized downstream from `.mmd` by the
> Summary build). The VB6 variant (`ava-asis-solution-vb`) does not yet have
> AST tool integration and still generates `.drawio` natively — tracked as a
> separate follow-up.

| Artifact | Path |
|----------|------|
| Architecture Blueprint | `asis/architecture-blueprint.md` |
| Pattern Classifications | `asis/pattern-classifications.json` |
| Bounded Context Map | `asis/bounded-context-map.md` |
| Data Access Profile | `asis/data-access-profile.md` |
| VCL Lifecycle Map | `asis/vcl-lifecycle-map.md` |
| API Map | `asis/api-map.md` |
| Data Structure | `asis/db/data-structure.md` |
| Code Usage Analysis | `asis/code-usage-analysis.md` |
| File Export Dependencies | `asis/file-export-dependencies.md` |
| File Import Dependencies | `asis/file-import-dependencies.md` |
| External Dependencies | `asis/external-dependencies.md` |
| C4 Context | `asis/diagrams/c4-context.mmd` |
| C4 Container | `asis/diagrams/c4-container.mmd` |
| C4 Component | `asis/diagrams/c4-component.mmd` |
| Component Diagram | `asis/diagrams/component-diagram.mmd` |
| Sequence Diagrams | `asis/diagrams/diagrama-sequencia-{acao}-{modulo}.mmd` |
| C4 Context Drawio (VB6 only) | `asis/diagrams/c4-context.drawio` |
| C4 Container Drawio (VB6 only) | `asis/diagrams/c4-container.drawio` |
| C4 Component Drawio (VB6 only) | `asis/diagrams/c4-component.drawio` |
| Component Diagram Drawio (VB6 only) | `asis/diagrams/component-diagram.drawio` |
| Sequence Drawio (VB6 only) | `asis/diagrams/diagrama-sequencia-{acao}-{modulo}.drawio` |
| Consolidated Drawio (VB6 only) | `asis/diagrams/diagrama-componentes.drawio` |

## Business Rules Generator
| Artifact | Path |
|----------|------|
| Business Rules | `asis/docs/business-rules.md` (unificado — contém `## Functional Requirements` e `## Business Rules`) |
| Business Rules JSON | `asis/docs/business-rules.json` (espelho determinístico do artefato Markdown) |

## Documentation Agent
| Artifact | Path |
|----------|------|
| Value Chain | `asis/docs/value-chain.md` |
| Screen Navigation Map | `asis/docs/screen-navigation-map.md` |
| Screen Rules | `asis/docs/screen-rules.md` |
| Screen Flow | `asis/docs/screen-flow.mmd` |
| Prototype AS-IS | `asis/docs/prototype-asis/` |

## Security Orchestrator
| Artifact | Path |
|----------|------|
| Security Map | `asis/security-map.md` |
| Vulnerabilities | `asis/vulnerabilities.md` |
| Compliance Gaps | `asis/compliance-gaps.md` |
| Security Findings JSON | `asis/security/security-findings.json` |
| SBOM | `asis/security/SBOM.md` |
| SBOM CycloneDX | `asis/security/sbom.cyclonedx.json` |
| License Report | `asis/security/license-compliance-report.md` |
| IAC CICD Report | `asis/security/iac-cicd-security-report.md` |
| Asset Inventory | `asis/security/asset-inventory.md` |
| Hardening Checklist | `asis/security/hardening-checklist.md` |
| Taint Flow Report | `asis/security/taint-flow-report.md` |
| PT Pattern Correlation | `asis/security/pt-pattern-correlation.md` |
| Remediation Validation | `asis/security/remediation-validation.md` |
| Regression Plan | `asis/security/security-regression-plan.md` |
| Secret Mgmt Plan | `asis/security/secret-management-plan.md` |
| Supply Chain Risk | `asis/security/supply-chain-risk-report.md` |
| Attack Surface | `asis/security/attack-surface.md` |
| Threat Model STRIDE | `asis/security/threat-model-stride.md` |
| OWASP Coverage Matrix | `asis/security/owasp-coverage-matrix.md` |
| Runtime Security Validation | `asis/security/runtime-security-validation.md` |
| Privilege Matrix | `asis/security/privilege-matrix.md` |
| Remediation Backlog | `asis/security/remediation-backlog.md` |
| Executive Security Summary | `asis/security/executive-security-summary.md` |
| Technical Findings Report | `asis/security/technical-findings-report.md` |

## Security Sub-Agent JSONs
| Artifact | Path |
|----------|------|
| SAST JSON | `asis/security/sast-asis.json` |
| IAST JSON | `asis/security/iast-asis.json` |
| Threat Model JSON | `asis/security/threat-model-asis.json` |
| Taint JSON | `asis/security/taint-asis.json` |
| Dependency Config JSON | `asis/security/dependency-config-asis.json` |
| PT Pattern JSON | `asis/security/pt-pattern-asis.json` |
| Security Review JSON | `asis/security/security-review-asis.json` |

## Inventory Agent
| Artifact | Path |
|----------|------|
| Inventory Report | `asis/inventory-report.md` |
| Metrics JSON | `asis/metrics.json` |
| Complexity Map | `asis/complexity-map.md` |

## DB Analyzer
| Artifact | Path |
|----------|------|
| DB Analysis Report | `asis/db/db-analysis-report.md` |
| Schema Inventory | `asis/db/schema-inventory.md` |
| ER Diagram | `asis/db/er-diagram.mmd` |
| Stored Procedures Map | `asis/db/stored-procedures-map.md` |
| DB Quality Report | `asis/db/db-quality-report.md` |
| Business Logic in DB | `asis/db/business-logic-in-db.md` |
| DB Type | `asis/db/db-type.json` |

## Gaps & Risks Agent
| Artifact | Path |
|----------|------|
| Gaps Risks Report | `asis/gaps-risks-report.md` |
| Risk Register | `asis/risk-register.json` |
| Migration Risks Summary | `asis/migration-risks-summary.md` |

## Bridge FastQA Agent (`ava-asis-bridge-fastqa`)
| Artifact | Path |
|----------|------|
| Test Gaps | `asis/qa/test-gaps.md` |
| Test Plan | `asis/qa/test-plan.md` |
| Test Cases | `asis/qa/test-cases.md` |

## Events / Pub-Sub / Queues Agent (`ava-asis-events-pubsub`)
| Artifact | Path |
|----------|------|
| Events Inventory Report | `asis/events-pubsub-inventory.md` |
| Events Grid JSON | `asis/events-pubsub-grid.json` |
| Events Flow Diagram | `asis/diagrams/events-pubsub-flow.mmd` |
| Events Risk Summary | `asis/events-pubsub-risks.md` |

---

## Cross-Phase Artifacts (generated by AS-IS agents, output in TO-BE folder)

> Artefatos gerados por agentes AS-IS após execução de skills TO-BE.
> Dependêm de artefatos TO-BE já prontos e são escritos em `outputs/tobe/`.

| Artifact | Agent | Upstream Dependency | Path |
|----------|-------|---------------------|------|
| Residual Risk Register | `ava-asis-gaps-risks` (skill residual) | `tobe/risk-mitigation-plan.md` | `tobe/risk-register-residual.json` |
