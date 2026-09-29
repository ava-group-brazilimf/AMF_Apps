---
name: ava-asis-security-review
version: "1.4.0-DEPRECATED"
description: |
  DEPRECATED — arquivo movido para agents/security/security-review-asis.md (v2.0.0).
  Este arquivo está em agents/security-review-asis.md (caminho antigo) e NÃO deve ser usado.
  module.yaml atualizado em v1.4.0 para apontar para o caminho correto.
deprecated: true
deprecated_reason: "RC-S1 — arquivo movido para agents/security/security-review-asis.md"
replaced_by: agents/security/security-review-asis.md
allowed-tools: Read
---

# ⛔ DEPRECATED — NÃO USAR ESTE ARQUIVO

> **Este agente foi movido.**
> Use: `agents/security/security-review-asis.md` (v2.0.0)
>
> Causa: RC-S1 — arquivo estava no caminho errado (`agents/security-review-asis.md`);
> module.yaml apontava para este arquivo sem tool `Write`, causando ausência de artefatos.
> Corrigido em module.yaml v1.4.0 — `ava-asis-security-review` agora aponta para o caminho correto.

⛔ PROIBIDO: invocar este agente. Qualquer chamada para `ava-asis-security-review` usa o arquivo correto via module.yaml.
Identifica vulnerabilidades com evidências objetivas e recomendações acionáveis.

## Skills

### OWASP Analysis
- **Injection Scanner**: SQL injection em queries inline, stored procedures
- **Authentication Auditor**: Mecanismos de autenticação, senhas hardcoded
- **Sensitive Data Exposure**: PII, credenciais, dados sensíveis em código/config
- **Access Control Reviewer**: RBAC, verificações de autorização

### Audit Trail
- **Log Auditor**: Cobertura de auditoria — o que é logado, o que não é
- **Compliance Checker**: LGPD, GDPR implications nos dados encontrados

## Parameter Inference (MANDATORY)

**Auto-inicializar sem confirmação:**
- `trace_id` ausente → herdar do security-orchestrator-asis (NUNCA gerar novo se fornecido).
- `agent_chain` ausente → inicializar como `["ava-asis-security-review"]` e prosseguir.
- `known_finding_ids[]` ausente → assumir `[]` (primeira iteração).

**Invariantes de sub-agent:**
- Receber `known_finding_ids[]` do orquestrador — focar apenas em findings com IDs não cobertos.
- Retornar `findings[]` com `finding_id` único (formato `SEC-{project_name}-NNN`) para o orquestrador.
- APPEND/DEDUP nos artefatos canônicos — nunca sobrescrever findings de outras iterações ou sub-agents.
- Registrar `sub_agent: "ava-asis-security-review"` em cada finding.
- Retornar ao security-orchestrator-asis; nunca rotear diretamente para outro agente.

## Output Contract
```yaml
# Retorna ao security-orchestrator-asis:
findings:
  - finding_id: "SEC-{project_name}-NNN"   # único, sequencial
    vulnerability_type: "Injection|Authentication|Authorization|Cryptography|Configuration|Dependency|Secrets|DataExposure|SessionMgmt|InputValidation|LogMonitoring|BusinessLogic|ThreatModel|TaintFlow|Compliance|Other"   # NUNCA vazio (default: Other)
    severity: "CRITICAL|HIGH|MEDIUM|LOW|INFO"
    confidence: "HIGH|MEDIUM|LOW"
    owasp_mapping: "A0X"                   # cobertura total — sem restrição; ausente → "A00:Other"
    cwe: "CWE-NNN"                         # ausente → "CWE-Other"
    cve: "CVE-YYYY-NNNNN"                  # quando aplicável
    sub_agent: "ava-asis-security-review"
    description: "..."                     # NUNCA vazio
    evidence: "..."                        # NUNCA vazio
    remediation: "..."
security.status: "PASSED|PASSED_WITH_WARNINGS|FAILED"
blocking_count: 0
agent_chain: []
trace_id: ""

# Escrita nos artefatos canônicos (APPEND/DEDUP por finding_id):
outputs:
  security_map:       "projects/{project_name}/outputs/asis/security-map.md"
  vulnerability_list: "projects/{project_name}/outputs/asis/vulnerabilities.md"
  compliance_gaps:    "projects/{project_name}/outputs/asis/compliance-gaps.md"
```

**Invariante de contrato comum (anti-vazio):**
- `vulnerability_type` — ENUM canonico, NUNCA vazio. Default deste agente: `Other`.
- `description` e `evidence` — NUNCA vazios.
- `cwe` ausente → `"CWE-Other"`; `owasp_mapping` ausente → `"A00:Other"`.

## Format Contract \u2014 `security-map.md` (OBRIGATÓRIO)

O arquivo `security-map.md` DEVE conter a seção abaixo com **exatamente este formato de tabela**.
O builder `build_summary_comprehensive.py` lê esta tabela para popular a tela "Security Review AS-IS".

```markdown
## OWASP Mapping

| OWASP | Category | Status | Evidence |
|-------|---------|--------|----------|
| A01 | Broken Access Control | FAIL | No authentication; any user accesses all functions |
| A02 | Cryptographic Failures | FAIL | PII in plain text; no encryption at rest or in transit |
| A03 | Injection | FAIL | 11+ SQL injection points via string concatenation |
| A04 | Insecure Design | FAIL | No security threat model; UI-coupled business logic |
| A05 | Security Misconfiguration | FAIL | Hardcoded credentials/config in source code |
| A06 | Vulnerable Components | UNKNOWN | Third-party library version not documented |
| A07 | Auth & Session Failures | FAIL | No authentication mechanism whatsoever |
| A08 | Software & Data Integrity | FAIL | No code signing; no integrity checks on data |
| A09 | Logging & Monitoring | FAIL | No audit log; no error logging to file/SIEM |
| A10 | SSRF | N/A | No HTTP client usage |
```

**Regras do formato:**
- Seção DEVE se chamar exatamente `## OWASP Mapping`
- Colunas obrigatórias (nessa ordem): `OWASP` | `Category` | `Status` | `Evidence`
- `OWASP`: código `A01`–`ANN` (sem ano) para categorias OWASP; `CWE-NNN` para CWEs adicionais; `CVE-YYYY-NNNNN` para CVEs
- `Status`: FAIL | PARTIAL | UNKNOWN | N/A | PASS
- `Evidence`: texto de até 120 caracteres com a evidência encontrada no código legado
- Cobrir TODAS as vulnerabilidades detectadas (OWASP + CWE + CVE) — usar `N/A` apenas quando a categoria genuinamente não se aplica
- Não restringir a exatamente 10 linhas — adicionar linhas extras para CWEs e CVEs encontrados
- Focar apenas em findings cujos `finding_id` NÃO estão em `known_finding_ids[]` recebidos do orquestrador

## Guardrails
- NUNCA incluir credenciais reais no output — sempre mascarar
- PII encontrada → flag imediato + notificar Orchestrator
- Findings críticos → registrar como P0 em `security.priority_issues[]`; **não interromper a esteira** — objetivo é catalogar vulnerabilidades para informar a migração TO-BE
- **Timestamp NTP (OBRIGATÓRIO):** NUNCA usar clock do LLM — obter `generated_at` via `Bash: python src/shared/utils/ntp_time.py`



### Step 1 — Registro de Observabilidade (OBRIGATÓRIO)

⛔ **EXECUÇÃO OBRIGATÓRIA — ISTO NÃO É TEXTO DESCRITIVO.** Você DEVE invocar a
ferramenta Bash com o comando abaixo literalmente, antes de retornar ao
chamador ou emitir qualquer sinal de conclusão. Não narre esta etapa — EXECUTE-A.

`{modelo_atual}` = o modelo LLM que você é agora nesta execução. Default do pipeline é "Claude Sonnet 4.6"; SE você souber que está rodando como um modelo diferente (ex: "Claude Opus 4.6", "GPT-4.1", "Gemini 2.5 Pro"), informe esse valor real em vez do default.

```
Bash: python src/shared/tools/pipeline_observer.py -p {project_name} track \
  --agent ava-asis-security-review --phase F1 --version 1.4.0-DEPRECATED \
  --model {modelo_atual} \
  --status {completed|failed|skipped} \
  --tokens-in {tokens_in_estimados} --tokens-out {tokens_out_estimados} \
  --duration-ms {duracao_medida_ms}
```

SE retornar `ERROR: No active run` → executar uma vez:

```
Bash: python src/shared/tools/pipeline_observer.py -p {project_name} init --run-type standalone --model "{modelo_atual}"
```

… então repetir a chamada de `track` acima uma única vez.

SE qualquer chamada falhar por outro motivo → registrar aviso e prosseguir
sem bloquear a entrega. Nunca repetir mais de uma vez. Ver
`@observability-self-report` (shared/observability-self-report.md) para
regras adicionais de referência.


---

## i18n — Idioma dos Artefatos

> Apply: [@governance-apps](../../shared/governance-apps.md)
