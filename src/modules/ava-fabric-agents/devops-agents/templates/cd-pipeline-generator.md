# CD Pipeline Generator Template
**Used by:** ava-devops-cd agent (F7 DevOps)  
**Purpose:** Auto-generate multi-project CD pipeline YAML for any PROJECT_NAME

## Generation Flow

When agent runs with PROJECT_NAME (e.g., "Meu-ERP", "Projeto-X"):

1. Resolve paths:
   ```
   OUTPUT_BASE = projects/{PROJECT_NAME}/outputs/tobe/iac/cd
   SCRIPTS_DIR = ${OUTPUT_BASE}/scripts
   ```

2. Generate files:
   - `${OUTPUT_BASE}/azure-pipelines-cd.yml` — main pipeline
   - `${OUTPUT_BASE}/post-deploy-validation.yml` — inline post-deploy validation template (consumed from `functional-test-matrix.md`)
   - `${SCRIPTS_DIR}/run-post-deploy-validation.sh`
   - `${SCRIPTS_DIR}/post-swap-validate-and-rollback.sh`
   - `${SCRIPTS_DIR}/notify-webhook.sh`

3. Key variables to substitute at generation time:
   - `PROJECT_NAME` — resolved from project config
   - `$(projectOutputDir)` — set to `projects/{PROJECT_NAME}/outputs/tobe/iac/cd`
   - `$(scriptsDir)` — set to `${projectOutputDir}/scripts`

## Template Substitution Tokens

| Token | Resolved by | Example |
|-------|-------------|---------|
| `{PROJECT_NAME}` | Agent from project-config.yaml | `Meu-ERP` |
| `$(projectOutputDir)` | Pipeline variable (auto) | `projects/Meu-ERP/outputs/tobe/iac/cd` |
| `$(scriptsDir)` | Pipeline variable (auto) | `projects/Meu-ERP/outputs/tobe/iac/cd/scripts` |
| `cd-appservice-${{ parameters.environmentName }}` | VG per project+env | `cd-appservice-hml` |

## Dynamic Path Resolution

**Pipeline reads PROJECT_NAME from:**
- Environment variable: `PROJECT_NAME` (set by orchestrator/skill)
- Or: Prompt user if not set

**All script references use $(scriptsDir)** → no hardcoded project paths

**All Variable Groups follow pattern:** `cd-appservice-{environment}`
→ Must be created per environment (hml, prd) in Azure DevOps

## Multi-Project Execution

For new project "Projeto-X":

1. Create config: `projects/Projeto-X/context/project-config.yaml`
2. Run skill: `/ava-devops-cd` (triggers agent)
3. Agent generates:
   - `projects/Projeto-X/outputs/tobe/iac/cd/azure-pipelines-cd.yml`
   - All supporting scripts
4. Create Variable Group: `cd-appservice-hml` and `cd-appservice-prd`
5. In Azure DevOps: point new Release pipeline to generated YAML
6. Trigger from CI artifact (resource: ci pipeline)

## Post-Deploy Validation (Inline, per Wave)

The CD pipeline generates inline post-deploy validation from `functional-test-matrix.md` (artifact `ava-test-plan-tobe` v4.0.0). The legacy per-wave smoke suites (`smoke-suite-wave-{N}.yml`) have been eliminated.

### Discovery

Before generating the pipeline, the agent MUST:
1. Read `projects/{PROJECT_NAME}/outputs/tobe/docs/wave-plan.md` → extract wave count (N)
2. Verify existence of `projects/{PROJECT_NAME}/outputs/tobe/qa/functional-test-matrix.md`
3. If `functional-test-matrix.md` is missing → register `[MISSING INPUT: functional-test-matrix.md]` and BLOCK generation; instruct user to run `ava-test-plan-tobe` (trigger `TP`) first

### Pipeline Structure (per wave)

```yaml
# In azure-pipelines-cd.yml — for each wave N:
- stage: Deploy_Wave${N}
    # ... deploy to staging slot ...

- stage: PostDeployGate_Wave${N}
    dependsOn: Deploy_Wave${N}
    jobs:
      - job: InlineValidation
        steps:
          - script: |
              # Extrai do functional-test-matrix.md ≥ 1 cenário funcional por BC
              # e executa health-checks padrão (HTTP 200, health endpoint, readiness)
            displayName: 'Inline Post-Deploy Validation'
    # Output: postDeployGate = PASS | FAIL

- stage: ParityPerformance_Wave${N}
    dependsOn: PostDeployGate_Wave${N}
    condition: eq(dependencies.PostDeployGate_Wave${N}.outputs['InlineValidation.postDeployGate'], 'PASS')
    # Only runs if validation passes — validates parity + performance

- stage: Rollback_Wave${N}
    dependsOn: PostDeployGate_Wave${N}
    condition: failed()
    # Automatic rollback + notification
```

### GitHub Actions (when applicable)

```yaml
# In cd-workflow.yml — for each wave N:
post-deploy-gate-wave-${N}:
  needs: deploy-wave-${N}
  steps:
    - name: Inline Post-Deploy Validation
      run: |
        # health checks + cenários mínimos extraídos do functional-test-matrix.md
        scripts/run-post-deploy-validation.sh
  # Output: postDeployGate = PASS | FAIL

parity-performance-wave-${N}:
  needs: post-deploy-gate-wave-${N}
  if: needs.post-deploy-gate-wave-${N}.outputs.postDeployGate == 'PASS'
  uses: ./.github/workflows/parity-performance.yml
```

### Key variables

| Variable | Source | Purpose |
|----------|--------|---------|
| `postDeployGate` | Output of inline validation job | Gate — PASS allows parity/performance |
| `postDeployWebhookUrl` | Variable Group `cd-appservice-$(environmentName)` | Alert on validation failure |
| `deployStrategy` | Variable Group | Determines rollback type (canary=auto, else=manual) |

---

## Agent Implementation Notes

- Use template from `projects/Meu-ERP/outputs/tobe/iac/cd/azure-pipelines-cd.yml` as base
- Replace all hardcoded `projects/Meu-ERP` with template token `{PROJECT_NAME}`
- Ensure $(projectOutputDir) and $(scriptsDir) are defined in generated YAML
- Generate post-deploy-validation template once per project (reusable, sourced from `functional-test-matrix.md`)
- Scripts should use relative path via $(scriptsDir)
- Add validation that Variable Group exists before generating pipeline
- **MUST** read `wave-plan.md` to enumerate waves and generate one `PostDeployGate_Wave{N}` stage per wave
- **MUST** wire `postDeployGate` output as condition for parity/performance stages
- **MUST** include rollback stage conditioned on validation gate failure
