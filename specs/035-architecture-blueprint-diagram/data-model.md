# Data Model — Architecture Blueprint Quality

## `BlueprintArtifactRecord`

| Field                  | Type                                                               | Required | Description                                     |
| ---------------------- | ------------------------------------------------------------------ | -------: | ----------------------------------------------- |
| `projectName`          | string                                                             |      yes | Lowercase project identifier.                   |
| `phase`                | enum(`ASIS`, `TOBE`)                                               |      yes | Architecture lifecycle owning the artifact.     |
| `expectedPath`         | string                                                             |      yes | Canonical path required by the owning contract. |
| `discoveredPath`       | string or null                                                     |      yes | Actual discovered path, or null when absent.    |
| `generatingAgent`      | string                                                             |      yes | Responsible agent ID.                           |
| `agentExecutionStatus` | enum(`EXECUTED`, `NOT_EXECUTED`, `UNKNOWN`)                        |      yes | Whether the responsible agent ran.              |
| `generationStatus`     | enum(`SUCCEEDED`, `FAILED`, `NOT_ATTEMPTED`, `INSUFFICIENT_INPUT`) |      yes | Result of producing the artifact.               |
| `artifactStatus`       | enum(`PRESENT`, `MISSING`, `EMPTY`, `INVALID`, `UNREGISTERED`)     |      yes | Discovery and source integrity state.           |
| `renderingStatus`      | enum(`SUCCEEDED`, `FAILED`, `NOT_ATTEMPTED`, `UNAVAILABLE`)        |      yes | Browser/render validation result.               |
| `gateStatus`           | enum(`PASS`, `BLOCKED`, `WARN`)                                    |      yes | Publication decision for this record.           |
| `traceId`              | string                                                             |      yes | Unchanged workflow trace identifier.            |
| `findings`             | array of `BlueprintFinding`                                        |      yes | Categorized evidence and remediation.           |

## `BlueprintFinding`

| Field              | Type                                                                              | Required | Description                                                                                                                     |
| ------------------ | --------------------------------------------------------------------------------- | -------: | ------------------------------------------------------------------------------------------------------------------------------- |
| `code`             | enum                                                                              |      yes | `MISSING_INPUT`, `AGENT_NOT_EXECUTED`, `GENERATION_FAILED`, `MISSING_ARTIFACT`, `DISCOVERY_FAILED`, `RENDERING_FAILED`, `PASS`. |
| `severity`         | enum(`ERROR`, `WARNING`, `INFO`)                                                  |      yes | Publication impact.                                                                                                             |
| `stage`            | enum(`INPUT`, `EXECUTION`, `GENERATION`, `DISCOVERY`, `RENDERING`, `PUBLICATION`) |      yes | Failure stage.                                                                                                                  |
| `message`          | string                                                                            |      yes | Human-readable explanation.                                                                                                     |
| `expectedArtifact` | string                                                                            |      yes | Canonical expected path.                                                                                                        |
| `actualArtifact`   | string or null                                                                    |      yes | Discovered path or null.                                                                                                        |
| `generatingAgent`  | string                                                                            |      yes | Owner responsible for remediation.                                                                                              |
| `remediation`      | string                                                                            |      yes | Next action without inventing architecture.                                                                                     |

## Invariants

1. A `PASS` record requires a present, non-empty, valid Mermaid artifact, `agentExecutionStatus=EXECUTED`, `generationStatus=SUCCEEDED`, and `renderingStatus=SUCCEEDED`.
2. `MISSING_ARTIFACT` and `AGENT_NOT_EXECUTED` are distinct findings.
3. `GENERATION_FAILED` and `RENDERING_FAILED` are distinct findings.
4. A non-null `discoveredPath` must be an actual file and must not replace `expectedPath` silently.
5. A placeholder string is never a valid artifact and always results in `INVALID`/`GENERATION_FAILED`.
6. Any `ERROR` finding for a required Blueprint sets `gateStatus=BLOCKED`.
7. `traceId` is propagated without mutation.
