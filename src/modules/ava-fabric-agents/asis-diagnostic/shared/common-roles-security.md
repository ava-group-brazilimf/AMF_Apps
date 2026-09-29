# Security Common Roles — AVA AS-IS
<!-- version: 1.6.0 -->

Common roles específicas para agentes de segurança do módulo `asis-diagnostic`.
Referenciadas pelo `security-orchestrator-asis.md` e pelos 7 sub-agents de security.

> **Fonte**: transcrito de `root/.github/agents/shared/CommonRolesSecurity.md`
> **Adaptações**: paths de output → `projects/{project_name}/outputs/asis/security/`; contexto legado (Delphi, VB6, COBOL).

<!-- changelog
### v1.6.0 — 2026-05-27
- μG5: @security-severity-levels — adicionado GUARDRAIL G5: range CVSS por nível nos headings (CRITICAL 9.0+, HIGH 7.0–8.9, MEDIUM 4.0–6.9, LOW 0.1–3.9, INFO 0.0); tabela de referência com exemplos canônicos + OWASP + CWE; regra de desempate CVSS prevalece sobre julgamento autônomo; NUNCA reusar score de execução anterior — recalcular por finding. Alcance: herdado pelos 7 sub-agents via import [CommonRolesSecurity].
### v1.5.0 — 2026-05-08
- μF1: @security-nuget-advisory-scanning — nova diretiva: scan NuGet/GHSA para pacotes SDK-style (.NET 6+). Cobre PackageReference, Directory.Packages.props (CPM), packages.lock.json. Inclui padrões de pacotes de observabilidade (OpenTelemetry.*) e mapeamento GHSA → CVSS → severity.
- μF2: @security-sbom-generation — adicionados .NET SDK-style (PackageReference, global.json, Directory.Packages.props) à tabela de fontes de componentes.
- μF3: @security-tools-standards — adicionados GitHub Advisory Database (GHSA), NuGet CLI audit e dotnet-outdated ao painel Dependency Scanning.
### v1.4.0 — 2026-05-08
- μR-R1: @security-parameter-inference-base — extrai os 5 campos comuns de Parameter Inference (preamble + trace_id + known_finding_ids + cobertura total + source.type + INVARIANTE) para diretiva compartilhada. Sub-agents mantêm apenas o bullet agent_chain específico.
- μR-R2: @security-mandatory-invariants-base — extrai os 6 bullets invariantes comuns de Mandatory Invariants (repository-path-resolution, focar-apenas, retornar-findings, hypothesis, prioridade, write-first-discipline). Sub-agents mantêm apenas bullets específicos.
- μR-R3: @security-completion-signal-step — extrai o bloco PASSO FINAL-3 idêntico nos 7 sub-agents para diretiva compartilhada.
### v1.3.0 — 2026-05-07
- μR-G1: @security-json-write-discipline — guardrail completo para geração de JSON: Atomic Write, proibição de APPEND, detecção de PENDING stub, tabela de sanitização de strings, schema validation. Referenciado pelo security-orchestrator e todos os 7 sub-agents.
### v1.2.0 — 2026-05-07
- μP4: @security-repository-path-resolution — regra compartilhada: todos sub-agents resolvem `repository_path` do input ou fallback para project-config.yaml ANTES do primeiro scan; ⛔ PROIBIDO iniciar análise sem `repository_path` resolvido.
### v1.1.0 — 2026-05-07
- μI3: @security-sub-agent-base-rules — `finding_id`→`id`, `description`→`finding`, `evidence`→`evidences`, `owasp_mapping`→`owasp`; ⛔ NUNCA usar campos legados; formato `SEC-{PROJECT}-{AGENT_PREFIX}-NNN`.
- μI2: @security-write-first-discipline PASSO 0 + FINAL-1 — path completo `projects/{project_name}/outputs/asis/security/{agent}-asis.json` obrigatório; ⛔ PROIBIDO omitir diretório.
- μI1: @security-leaf-io-contract Output — substituído schema legado (`finding_id`, `owasp_mapping`, `description`, `evidence`) pelo schema canônico JSON completo com todos os campos e tabela de prefixos por sub-agent.
- μI4: @security-reporting-format — nota explícita que o template Markdown é APENAS para relatórios humanos e NÃO substitui o JSON canônico obrigatório.
### v1.0.0 — baseline
-->

---

## @security-json-write-discipline

**Guardrail de Geração de JSON — Obrigatório em TODOS os Agentes de Security**

> ⚡ **INVARIANTE**: Todo arquivo JSON de security DEVE ser gerado com `Write` (REPLACE total).
> ⛔ **PROIBIDO**: APPEND em qualquer JSON de security — sempre substituir o arquivo inteiro.

### Regra 1 — Atomic Write (REPLACE total)

```
Para QUALQUER arquivo JSON de security:
  Tool: Write  ← SEMPRE (nunca Edit/Append)
  Conteúdo: objeto JSON COMPLETO e válido
  ⛔ PROIBIDO: escrever parcialmente e complementar depois
  ⛔ PROIBIDO: usar APPEND para adicionar findings a JSON existente
  ⛔ PROIBIDO: escrever dois objetos JSON separados no mesmo arquivo
```

### Regra 2 — Detecção e Substituição de PENDING stub

```
ANTES de qualquer Write final:
  IF arquivo existe em disco:
    Ler conteúdo
    IF contém "generated_at": "PENDING"  ← stub não substituído
      → REPLACE total obrigatório (Tool: Write com conteúdo completo)
    IF contém dois objetos JSON (texto após o primeiro "}")
      → REPLACE total obrigatório — nunca preservar arquivo malformado
```

### Regra 3 — Sanitização de strings antes de serializar

Aplicar a TODA string antes de incluir em JSON (campos: `finding`, `evidences`, `recommendation`, `business_impact`, `source`, qualquer texto livre):

| Sequência original | Substituir por | Motivo |
|---|---|---|
| `\n` (newline) | `\\n` | quebra string JSON |
| `\r` (carriage return) | `` (remover) | quebra string JSON |
| `\t` (tab) | ` ` (espaço) | mantém legibilidade |
| `"` (aspas duplas) | `\"` | fecha string prematuramente |
| `\` (barra invertida) | `\\` | escape inválido |
| caracteres de controle U+0000–U+001F | `` (remover) | JSON inválido |
| valor `null` ou `undefined` | `""` | campo obrigatório não pode ser nulo |
| string vazia `""` em campo obrigatório | `"—"` | fallback anti-vazio |

> ⚠️ **ORDEM obrigatória**: aplicar `\` → `"` → `\n` → `\r` → `\t` → control chars → null → empty.

### Regra 4 — Schema validation antes do Write

```
ANTES de escrever qualquer JSON:
  1. Verificar que o objeto resulta em JSON parseável (sem sintaxe quebrada)
  2. Campos obrigatórios não podem ser null, undefined ou "" (usar "—" como fallback)
  3. Arrays de findings nunca podem conter elementos null
  4. Campos numéricos (count, subtotal, total) devem ser inteiros ≥ 0
  5. "generated_at" NUNCA pode ser "PENDING" no Write final — SEMPRE timestamp real
```

### Regra 5 — Estrutura canônica de `security-findings.json`

O arquivo DEVE ser um **único objeto JSON** com a seguinte estrutura raiz:

```json
{
  "project_name": "string",
  "trace_id": "uuid",
  "generated_at": "ISO-8601 timestamp (NUNCA 'PENDING')",
  "generated_by": "ava-asis-security-orchestrator",
  "security_gate": "DIAGNOSTIC_COMPLETE|WITH_SYNTHESIS|WITH_GAPS|BLOCKED_ARTIFACTS",
  "total": <int>,
  "summary": { "critical": <int>, "high": <int>, "medium": <int>, "low": <int>, "info": <int> },
  "securityReview": [   ← chave canônica lida pelo template HTML
    {
      "id":               "SEC-{PROJECT}-NNN",
      "vulnerability_type": "...",   ← campo lido pelo template (r.vulnerability_type)
      "sev":               "...",   ← campo lido pelo template (r.sev) — lowercase: critical|high|medium|low|info
      "owasp":             "...",
      "cwe":               "...",
      "desc":              "...",   ← campo lido pelo template (r.desc)
      "ev":                "...",   ← campo lido pelo template (r.ev)
      "source":            "...",
      "count":             0
    }
  ]
}
```

**Mapeamento de campos canônicos → campos do template HTML:**

| Campo do sub-agent JSON (`findings[]`) | Campo do `securityReview[]` (template) |
|---|---|
| `type` | `vulnerability_type` |
| `severity` | `sev` (lowercase: `critical|high|medium|low|info`) |
| `owasp` | `owasp` |
| `cwe` | `cwe` |
| `finding` | `desc` |
| `evidences` | `ev` |
| `source` | `source` |
| `count` | `count` |

> ⛔ **PROIBIDO**: usar chave `"vulnerabilities"` em vez de `"securityReview"` — o template HTML lê exclusivamente `D.securityReview`.
> ⛔ **PROIBIDO**: copiar campos brutos (`type`, `severity`, `finding`, `evidences`) sem renomear para os nomes do template (`vulnerability_type`, `sev`, `desc`, `ev`).

---

## @security-repository-path-resolution

**Resolução de `repository_path` — Obrigatória em TODOS os Sub-Agents**

> ⚡ **INVARIANTE**: Todo sub-agent DEVE ter `repository_path` resolvido ANTES do PASSO 0 (STUB).
> ⛔ **PROIBIDO**: Iniciar qualquer análise, scan ou stub sem `repository_path` resolvido.

**Algoritmo de resolução (executar na ordem):**

```
1. IF repository_path presente no input do dispatch → usar diretamente (fonte canônica)
2. ELSE → ler de projects/{project_name}/context/project-config.yaml → campo `repository_path`
3. IF ainda ausente ou vazio → BLOCK: logar "REPOSITORY_PATH_UNRESOLVED" + aguardar re-dispatch
```

**Campos de contexto adicionais — resolução da mesma forma:**

| Campo | Fonte no input | Fallback (project-config.yaml) |
|---|---|---|
| `repository_path` | `repository_path` | campo `repository_path` |
| `legacy_technology` | `legacy_technology` | campo `legacy_technology` |
| `tech_stack[]` | `tech_stack[]` | derivar de `legacy_technology` (ex: delphi → ["Delphi 7", "ADODB", "VCL"]) |
| `business_domain` | `business_domain` | inferir do nome do projeto |
| `criticality` | `criticality` | default `HIGH` |
| `sensitive_data_types[]` | `sensitive_data_types[]` | inferir de `business_domain` (ERP/Financeiro → ["PII","PCI"]) |

**Invariantes:**
- `repository_path` é o único campo **bloqueante** — ausência impede scan
- Demais campos degradam graciosamente (análise genérica vs. específica por tecnologia)
- Sempre logar quais campos foram resolvidos via input vs. fallback no COMPLETION_SIGNAL

---

## @security-shared-rules

**Regras Compartilhadas para Todos os Security Sub-Agents**

**Hard Constraint:**
- Analisar apenas padrões de código, configurações e evidências observáveis
- NÃO executar exploits, payload delivery, scanning ativo ou simulação de ataque intrusiva
- NÃO executar testes de penetração ao vivo, exploit chains ou fuzzing
- A análise deve ser determinística e reproduzível apenas a partir dos artefatos

**Mandatory Traceability:**
Cada finding de segurança DEVE conter:
- `trace_id`: herdado da requisição pai (propagado por todo o fluxo)
- `requirement_ids`: requisitos vinculados quando aplicável
- `architecture_decision_ids`: decisões de arquitetura vinculadas quando aplicável
- `finding_id`: identificador único para rastreamento de remediação e validação de reteste

**Market Best Practices:**
- Manter findings reproduzíveis com evidências claras e ID/categoria da regra
- Mapear findings para OWASP/CWE quando possível para taxonomia padronizada
- Priorizar por severidade, exploitabilidade e contexto de impacto de negócio
- Fornecer orientação de correção com alternativas seguras por padrão
- Recomendar correções de mudança mínima primeiro, depois hardening estrutural
- Manter remediações em lotes pequenos orientados a release
- Distinguir bloqueadores de release de riscos residuais aceitáveis

**Quality Gates:**
- Cada finding inclui evidência de arquivo/símbolo/artefato e categoria de vulnerabilidade
- Findings incluem nível de confiança e notas de falso positivo quando aplicável
- Findings críticos/altos incluem recomendação clara de correção com responsável
- Severidade e impacto de negócio são explicitamente justificados
- Findings são acionáveis e rastreáveis ao código-fonte/configuração

**Definition of Done:**
- Todos os findings documentados nos artefatos canônicos AVA:
  - `projects/{project_name}/outputs/asis/security-map.md`
  - `projects/{project_name}/outputs/asis/vulnerabilities.md`
  - `projects/{project_name}/outputs/asis/compliance-gaps.md`
- Findings priorizados e com chaves de rastreabilidade
- Orientação de remediação prática e acionável
- Output pronto para decisão consolidada do `security-orchestrator-asis`

---

## @security-owasp-mapping

**Cobertura Total de Vulnerabilidades — OWASP, CWE e CVE**

> ⚠️ **INVARIANTE**: Cobrir TODAS as vulnerabilidades detectadas. Não restringir a um subconjunto fixo.
> Usar `N/A` apenas quando a categoria genuinamente não se aplica ao contexto legado analisado.

**OWASP — referência mínima:**
1. **A01:2021 - Broken Access Control**
   - Verificações de autorização ausentes
   - Referências diretas inseguras a objetos (IDOR)
   - Path traversal, forced browsing

2. **A02:2021 - Cryptographic Failures**
   - Algoritmos fracos/desatualizados
   - Segredos hardcoded, chaves expostas
   - Transmissão insegura de dados sensíveis

3. **A03:2021 - Injection**
   - SQL injection, NoSQL injection
   - OS command injection
   - LDAP, XPath injection

4. **A04:2021 - Insecure Design**
   - Threat modeling ausente
   - Padrões de segurança inadequados
   - Falhas de lógica de negócio

5. **A05:2021 - Security Misconfiguration**
   - Credenciais padrão
   - Interfaces admin expostas
   - Features desnecessárias habilitadas
   - Headers de segurança ausentes

6. **A06:2021 - Vulnerable and Outdated Components**
   - CVEs conhecidos em dependências
   - Bibliotecas não mantidas
   - Frameworks sem patch

7. **A07:2021 - Identification and Authentication Failures**
   - Políticas de senha fracas
   - Session fixation
   - MFA ausente
   - Vulnerabilidades a credential stuffing

8. **A08:2021 - Software and Data Integrity Failures**
   - Desserialização insegura
   - CI/CD sem verificações de integridade
   - Auto-update sem verificação

9. **A09:2021 - Security Logging and Monitoring Failures**
   - Logging insuficiente
   - Sem alertas para atividades suspeitas
   - Logs desprotegidos

10. **A10:2021 - Server-Side Request Forgery (SSRF)**
    - Redirecionamentos de URL não validados
    - Busca de recursos remotos sem validação

**Vulnerabilidades adicionais — cobertura obrigatória exibir todas:**
- Business logic flaws específicos do domínio legado
- Lógica de negócio embutida em stored procedures (risco crítico de migração)
- Credenciais hardcoded em formulários Delphi/VB6
- Comunicação inter-processo insegura (DDE, COM, ActiveX)
- Dados PII sem proteção — LGPD Arts. 46–48

**CWE — mapear quando aplicável, exibir todas:**
- CWE-79: Cross-site Scripting (XSS)
- CWE-89: SQL Injection
- CWE-20: Improper Input Validation
- CWE-78: OS Command Injection
- CWE-190: Integer Overflow
- CWE-352: Cross-Site Request Forgery (CSRF)
- CWE-434: Unrestricted Upload of File with Dangerous Type
- CWE-863: Incorrect Authorization
- CWE-94: Code Injection
- E outros conforme aplicável

**CVE — mapear quando componente com CVE conhecido for identificado:**
- Referenciar CVE ID + CVSS score + link NVD
- Prioridade: mesmo mapeamento de severidade da seção @security-severity-levels

---

## @security-severity-levels

**Padrões de Classificação de Severidade**

> ⛔ **GUARDRAIL G5 — SEVERITY CLASSIFICATION REFERENCE (OBRIGATÓRIO):**
> Sub-agents DEVEM consultar esta tabela ao atribuir `severity`. Em caso de ambiguidade, **CVSS score prevalece sobre julgamento autônomo**. NUNCA reusar score de execução anterior — recalcular por finding.
> **Regra de desempate entre execuções:** mesmo finding classificado diferente em iterações distintas → usar severity da iteração com maior CVSS score documentado.

| Severidade | CVSS v3.1 | Exemplo Canônico | OWASP | CWE |
|---|---|---|---|---|
| **CRITICAL** | 9.0 – 10.0 | SQL Injection exploitável remotamente sem autenticação | A03:2021 | CWE-89 |
| **HIGH** | 7.0 – 8.9 | Hardcoded password em arquivo de configuração | A07:2021 | CWE-798 |
| **MEDIUM** | 4.0 – 6.9 | Missing input validation em tela interna (sem acesso externo) | A03:2021 | CWE-20 |
| **LOW** | 0.1 – 3.9 | Log de stack trace sem dados sensíveis em ambiente interno | A09:2021 | CWE-209 |
| **INFO** | 0.0 | Configuração de segurança subótima sem exploitabilidade direta | — | — |

**CRITICAL (CVSS 9.0+):**
- Remote Code Execution (RCE)
- Bypass de autenticação
- Escalação de privilégios para admin
- Exposição direta de dados (credenciais, PII)
- SQL injection com acesso admin
- Impacto: Disrupção imediata de negócio, vazamento de dados, violação regulatória

**HIGH (CVSS 7.0–8.9):**
- SQL injection (escopo limitado)
- XSS com potencial de session hijacking
- Broken access control em recursos sensíveis
- Falhas criptográficas com exposição de chave
- SSRF com acesso à rede interna
- Impacto: Risco de segurança significativo, potencial vazamento de dados

**MEDIUM (CVSS 4.0–6.9):**
- Headers de segurança ausentes (CSP, HSTS)
- Políticas de senha fracas
- Divulgação de informação (stack traces, versões)
- Dependências inseguras (sem exploit ativo)
- Rate limiting ausente
- Impacto: Risco moderado, requer passos adicionais de exploit

**LOW (CVSS 0.1–3.9):**
- Mensagens de erro verbosas
- Melhores práticas de segurança ausentes
- Misconfigurações não críticas
- Divulgação de informação de baixo impacto
- Impacto: Risco imediato mínimo, melhoria de higiene de segurança

**INFO (CVSS 0.0):**
- Recomendações de segurança
- Sugestões de defesa em profundidade
- Melhorias de qualidade de código com implicações de segurança
- Impacto: Sem vulnerabilidade direta, hardening proativo

---

## @security-remediation-guidance

**Padrões de Orientação de Remediação**

**Estrutura de Recomendação de Correção:**
1. **Resumo**: Descrição em uma linha da correção
2. **Código Vulnerável**: Mostrar o padrão problemático
3. **Alternativa Segura**: Fornecer exemplo de código seguro
4. **Explicação**: Por que a correção funciona
5. **Referências**: Link para documentação, orientação OWASP
6. **Verificação**: Como testar a correção

**Prioridades de Remediação:**
- **IMMEDIATE** (CRITICAL): Deve corrigir antes do release
- **HIGH**: Corrigir no sprint atual
- **NORMAL**: Corrigir no próximo ciclo de release
- **LOW**: Backlog para melhoria futura

**Padrões de Código Seguro:**
- Usar queries parametrizadas — nunca concatenação de string para SQL
- Aplicar validação de input com allowlists, não blocklists
- Usar recursos de segurança fornecidos pelo framework (tokens CSRF, encoding de output)
- Aplicar princípio de menor privilégio
- Falhar com segurança — default deny, explicit allow
- Nunca confiar apenas em validação client-side

---

## @security-tools-standards

**Padrões de Integração de Ferramentas de Segurança**

**SAST (Static Application Security Testing):**
- SonarQube, Semgrep, CodeQL, Checkmarx
- Análise estática do código-fonte legado (Delphi Pascal, VB6, COBOL, SQL)
- Rastrear findings por arquivo/linha/regra

**IAST (Interactive Application Security Testing):**
- Análise baseada em logs de execução e traces disponíveis
- Detectar vulnerabilidades em runtime a partir de evidências existentes
- Análise sensível ao contexto legado

**Dependency Scanning:**
- OWASP Dependency-Check, Snyk, `dotnet-outdated`
- **NuGet:** `dotnet list package --vulnerable` (requer .NET SDK 6+); `nuget audit` (NuGet CLI 6.8+)
- **GitHub Advisory Database (GHSA):** `https://github.com/advisories?query=ecosystem%3Anuget` — fonte primária para pacotes NuGet
- **OSV Database:** `https://osv.dev` — fonte complementar para CVEs e GHSAs
- Verificar CVEs conhecidos em dependências (DLLs, componentes ActiveX, BPLs Delphi, pacotes NuGet)
- Monitorar bibliotecas desatualizadas/sem manutenção
- **Dependency Confusion:** verificar se pacotes internos não estão expostos em registries públicos

**Threat Modeling:**
- Metodologia STRIDE adaptada ao contexto legado
- Análise de superfície de ataque do sistema AS-IS
- Identificação de trust boundaries entre camadas legadas

**Penetration Testing Patterns:**
- Análise baseada em padrões (sem exploit ao vivo)
- Padrões comuns de vulnerabilidade em sistemas legados
- Análise de superfície de ataque
- Detecção de anti-padrões de segurança

---

## @security-reporting-format

**Formato Padrão de Relatório de Finding de Segurança**

```markdown
## Finding: [SEVERITY] [Título]

**Finding ID**: SEC-{project_name}-[NNN]
**Trace ID**: [trace_id]
**Iteration**: [N de max 6]
**Requirement IDs**: [requirement_ids se aplicável]
**Architecture Decision IDs**: [architecture_decision_ids se aplicável]

**Category**: [OWASP A0X / CWE-XXX / CVE-YYYY-NNNNN]
**Severity**: CRITICAL | HIGH | MEDIUM | LOW | INFO
**Confidence**: HIGH | MEDIUM | LOW
**CVSS Score**: [se aplicável]

**Location**:
- File: path/to/file.ext (ou stored procedure / view / form)
- Line: XX-YY
- Component: [nome do componente legado]

**Description**:
[Descrição clara da vulnerabilidade]

**Evidence**:
[Trecho de código ou configuração mostrando o problema]

**Impact**:
[Descrição do impacto de negócio e técnico]

**Exploit Scenario**:
[Como um atacante poderia explorar isso]

**Remediation**:
[Instruções passo a passo da correção]

**Secure Code Example**:
[Exemplo de código mostrando a correção]

**References**:
- OWASP: [link]
- CWE: [link]
- CVE: [link NVD se aplicável]

**Remediation Priority**: IMMEDIATE | HIGH | NORMAL | LOW
**Estimated Effort**: [horas/story points]
**Owner**: [equipe/desenvolvedor]
```

> ⚠️ **ESTE FORMATO É PARA RELATÓRIOS HUMANOS APENAS** (relatórios `.md` como `technical-findings-report.md`, `vulnerabilities.md`).
> ⛔ **NÃO substitui o JSON canônico do Output Contract** — cada sub-agent DEVE produzir o arquivo `{agent}-asis.json` com o schema canônico definido em `@security-leaf-io-contract`, independentemente deste template.

---

## @security-secrets-scanning

**Secrets Scanning — Obrigatório em TODOS os Perfis de Segurança**

**Objetivo:** Detectar segredos hardcoded, credenciais, tokens e dados sensíveis em código-fonte, arquivos de configuração e histórico de commits.

**Padrões Obrigatórios a Detectar:**

| Tipo de Padrão | Exemplos |
|---|---|
| Chaves de cloud provider | AWS `AKIA*`, GCP service account JSON, Azure connection strings com credenciais |
| Tokens de API SaaS | Stripe `sk_live_*`, Twilio auth tokens, SendGrid API keys, GitHub PATs |
| Segredos de auth | JWT signing secrets, OAuth client secrets, chaves de criptografia simétricas |
| Credenciais de banco | Connection strings com senhas, DSNs, MongoDB URIs com credenciais embutidas |
| Chaves privadas | Chaves RSA/EC codificadas em PEM, chaves privadas SSH |
| Segredos de infra | Terraform state com credenciais, Kubernetes secrets em YAML plano |
| Segredos de pipeline | Segredos hardcoded em configs CI/CD, arquivos `.env` commitados |
| Legado específico | Credenciais em INI/CFG Delphi, strings de conexão em `.dfm`, chaves no registro exportadas |

**Escopo de Scanning por Perfil:**
- **RAPID:** Apenas arquivos alterados (escopo git diff — rápido, direcionado)
- **STANDARD:** Todo o código-fonte e arquivos de configuração do projeto
- **DEEP:** Scan completo incluindo histórico git (detectar segredos mesmo se removidos em commit posterior)

**Mapeamento de Risco:**
- Segredo hardcoded em config de produção → **CRITICAL** · A02:2021 · CWE-798
- Chave privada ou client secret OAuth commitados → **CRITICAL**
- Credenciais de test/dev em arquivos de escopo produção → **HIGH**
- Credenciais comentadas (ainda legíveis) → **HIGH**
- Valores de exemplo correspondendo a padrões reais de credenciais → **MEDIUM**

**Orientação de Remediação (ordenada):**
1. Rotacionar/revogar a credencial exposta imediatamente — tratar como comprometida.
2. Mover segredo para variável de ambiente ou secrets manager.
3. Adicionar o arquivo/padrão ao `.gitignore`.
4. Reescrever histórico git para remover o segredo (`git filter-repo` ou BFG Repo Cleaner).
5. Habilitar pre-commit hooks (`gitleaks`, `detect-secrets`) para evitar vazamentos futuros.

---

## @security-nuget-advisory-scanning

**NuGet Advisory Scanning — Obrigatório quando stack .NET detectada**

**Objetivo:** Detectar pacotes NuGet com vulnerabilidades conhecidas em projetos .NET modernos (SDK-style, .NET 6+), correlacionando com GitHub Advisory Database (GHSA) e NVD/CVE.

### Fontes de Manifesto NuGet

| Arquivo | Descrição |
|---|---|
| `*.csproj` com `<PackageReference>` | Projetos SDK-style (.NET 6/7/8/9) |
| `packages.lock.json` | Lock file determinístico (gerado com `RestoreLockedMode=true`) |
| `Directory.Packages.props` | Central Package Management (CPM) — versões centralizadas |
| `global.json` | Pin de versão do SDK .NET |
| `packages.config` | Projetos .NET Framework legado |
| `NuGet.config` | Configuração de feeds: detectar feeds privados sem autenticação |
| `Directory.Build.props` | Propriedades compartilhadas: detectar versões de pacote herdadas |

### Padrões de Pacotes de Alto Risco (inspecionar sempre)

**Observabilidade e Telemetria:**
- `OpenTelemetry.*` — `OpenTelemetry.Api`, `OpenTelemetry.Sdk`, `OpenTelemetry.Exporter.*`, `OpenTelemetry.Instrumentation.*`
- `Serilog.*`, `NLog.*`, `log4net` — pacotes de logging com histórico de CVEs
- `Microsoft.Extensions.Logging.*`

**Serialização:**
- `Newtonsoft.Json`, `System.Text.Json`, `MessagePack`, `protobuf-net`

**Rede e HTTP:**
- `System.Net.Http.*`, `HttpClient`, `Grpc.*`, `RestSharp`

**Autenticação:**
- `Microsoft.Identity.*`, `IdentityServer.*`, `System.IdentityModel.Tokens.Jwt`

**ORM e Banco:**
- `Microsoft.EntityFrameworkCore.*`, `Dapper`, `Npgsql`, `Microsoft.Data.SqlClient`

**Infraestrutura:**
- `AWSSDK.*`, `Azure.Storage.*`, `Azure.Messaging.*`, `StackExchange.Redis`

### Procedimento de Scan NuGet

```
PASSO N.1 — Identificar todos os arquivos de manifesto NuGet no repo:
  Glob: **/*.csproj, **/packages.config, **/Directory.Packages.props,
        **/packages.lock.json, **/NuGet.config, **/global.json

PASSO N.2 — Extrair dependências com versão exata:
  PackageReference: <PackageReference Include="{name}" Version="{version}" />
  Directory.Packages.props: <PackageVersion Include="{name}" Version="{version}" />
  packages.config: <package id="{name}" version="{version}" />
  packages.lock.json: campo "resolved" por pacote

PASSO N.3 — Correlacionar com fontes de advisory (ordem de prioridade):
  1. GitHub Advisory Database (GHSA): https://github.com/advisories?query=ecosystem%3Anuget+{package_name}
  2. NVD/CVE: https://nvd.nist.gov/vuln/search?keyword={package_name}
  3. OSV Database: https://osv.dev/list?ecosystem=NuGet&q={package_name}
  4. Snyk Vulnerability DB: https://security.snyk.io/package/nuget/{package_name}

PASSO N.4 — Para cada advisory encontrado:
  - Verificar se a versão em uso está no range afetado
  - Extrair: GHSA-ID, CVE-ID (se mapeado), CVSS score, severity, affected_versions, patched_version
  - Gerar finding se versão em uso <= patched_version

PASSO N.5 — Classificar severity:
  CVSS 9.0–10.0 → CRITICAL (P0)
  CVSS 7.0–8.9  → HIGH    (P1)
  CVSS 4.0–6.9  → MEDIUM  (P2)
  CVSS 0.1–3.9  → LOW     (P3)
  Sem CVSS        → usar severity do GHSA advisory (critical/high/moderate/low → CRITICAL/HIGH/MEDIUM/LOW)
```

### Mapeamento GHSA → Schema Canônico

| Campo GHSA | Campo canônico do finding |
|---|---|
| GHSA-XXXX-XXXX-XXXX | `id` field suffix + `issue_ref` |
| CVE-YYYY-NNNNN (se presente) | `cwe` + `issue_ref` (prefer CVE link NVD) |
| severity: moderate | `severity: MEDIUM` |
| severity: critical | `severity: CRITICAL` |
| affected.ranges[].events[].introduced | `evidences` field (versão afetada) |
| fixed | `recommendation` ("Atualizar para versão X") |

**Template de `issue_ref` para GHSA:**
- Com CVE: `https://nvd.nist.gov/vuln/detail/CVE-YYYY-NNNNN`
- Sem CVE: `https://github.com/advisories/GHSA-XXXX-XXXX-XXXX`

### Exemplo: OpenTelemetry.Api 1.10.0

```
Pacote   : OpenTelemetry.Api
Versão   : 1.10.0
Advisory : https://github.com/advisories/ (GHSA moderado)
CVSS     : ~5.x (Moderate)
Severity : MEDIUM → P2
OWASP    : A06:2021
CWE      : CWE-1104 (Use of Unmaintained Third Party Components)
Finding  : OpenTelemetry.Api 1.10.0 contém vulnerabilidade moderada conhecida.
            Versão afetada: < {patched_version}. Atualizar para versão segura.
Recomend.: Atualizar OpenTelemetry.Api para a versão mais recente sem advisory ativo.
           Verificar OpenTelemetry.Sdk, Exporter.* e Instrumentation.* — mesmo ecossistema.
```

### Invariantes NuGet
- SEMPRE verificar pacotes transitivos via `packages.lock.json` quando disponível — não apenas diretos.
- Pacotes com GHSA moderado sem patch disponível → gerar finding com `"accepted_risk": true` e justificativa.
- Verificar feeds privados em `NuGet.config` — feeds sem HTTPS → finding de misconfiguração (CWE-319).
- Dependency confusion attack → verificar se pacotes internos estão registrados em feed público também.

---

## @security-sbom-generation

**SBOM (Software Bill of Materials) — Obrigatório nos Perfis STANDARD e DEEP**

**Objetivo:** Produzir inventário completo e auditável de todos os componentes de software diretos e transitivos, suas licenças e vulnerabilidades conhecidas.

**Formato SBOM:** CycloneDX (padrão OWASP — preferido) — JSON legível por máquina + sumário Markdown legível por humano.

**Campos Obrigatórios por Componente:**
- Nome, versão e tipo de componente (biblioteca / framework / aplicação)
- Package URL (PURL) para identificação inequívoca
- Identificador de licença (expressão SPDX)
- Referências cruzadas CVE/GHSA conhecidas
- Tipo de dependência: `direct` ou `transitive`
- Hash SHA-256 para verificação de integridade da cadeia de suprimentos

**Outputs Obrigatórios (paths AVA):**
- `projects/{project_name}/outputs/asis/security/SBOM.md` — sumário legível por humano
- `projects/{project_name}/outputs/asis/security/sbom.cyclonedx.json` — CycloneDX JSON legível por máquina

**Fontes de Componentes para Stack Legado e Moderno:**
| Stack | Arquivo de Manifesto / Lock |
|---|---|
| Delphi | `*.dproj`, `*.dpk`, referências BPL, componentes de terceiros |
| VB6 | `*.vbp`, referências OCX/ActiveX, DLLs de terceiros |
| COBOL | JCL com copybooks externos, módulos de terceiros |
| .NET Framework (legado) | `*.csproj` (antigo), `packages.config`, `packages.lock.json` |
| .NET SDK-style (moderno) | `*.csproj` com `<PackageReference>`, `Directory.Packages.props`, `packages.lock.json` |
| .NET CPM | `Directory.Packages.props` (Central Package Management) |
| .NET SDK pin | `global.json` |
| SQL Server | Dependências de SP externas, linked servers |

**Classificação de Risco de Licença:**
| Nível de Risco | Exemplos de Licença | Ação |
|---|---|---|
| 🔴 HIGH — bloqueador | GPL-2.0, GPL-3.0, AGPL-3.0 em produto proprietário | Bloquear release — revisão jurídica obrigatória |
| 🟡 MEDIUM — revisão | LGPL-2.1, MPL-2.0, EPL-2.0 | Revisar requisitos de linking antes do release |
| 🟢 LOW — permitido | MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC | Sem restrição |

---

## @security-sub-agent-base-rules

Regras base aplicadas por todos os security sub-agents do módulo `asis-diagnostic`:
- Herdar `trace_id` do `security-orchestrator-asis` — nunca gerar novo se já fornecido
- Receber `known_finding_ids[]` do orquestrador — focar apenas em findings com IDs não cobertos
- Retornar `findings[]` usando o **schema canônico JSON** (campo `id`, não `finding_id`; campo `finding`, não `description`; campo `evidences`, não `evidence`; campo `owasp`, não `owasp_mapping`) — formato: `SEC-{PROJECT}-{AGENT_PREFIX}-NNN` (ex: `SEC-MYERP-SAST-001`)
- APPEND/DEDUP nos artefatos canônicos — nunca sobrescrever findings de outras iterações ou sub-agents
- Registrar `source` (nome do sub-agent) em cada finding para rastreabilidade
- ⛔ **NUNCA usar campo `finding_id`** — o campo canônico é `id`
- ⛔ **NUNCA usar campo `description`** — o campo canônico é `finding`
- ⛔ **NUNCA usar campo `evidence`** — o campo canônico é `evidences`
- ⛔ **NUNCA usar campo `owasp_mapping`** — o campo canônico é `owasp`

---

## @security-all-rules

Todas as roles de segurança — aplicar todas:
`@common-roles:security-shared-rules` `@common-roles:security-owasp-mapping` `@common-roles:security-severity-levels` `@common-roles:security-remediation-guidance` `@common-roles:security-reporting-format` `@common-roles:security-secrets-scanning` `@common-roles:security-sbom-generation` `@common-roles:security-write-first-discipline`

---

## @security-write-first-discipline

**Write-First — Disciplina de Escrita Obrigatória para Todos os Security Sub-Agents**

> ⚡ **INVARIANTE CRÍTICA:** Nenhum sub-agent pode retornar ao orquestrador sem ter escrito TODOS os seus artefatos obrigatórios em disco. Análise sem escrita = execução inválida.

### Estrutura de Execução Obrigatória (todos os sub-agents)

```
PASSO 0 — STUB FIRST (ANTES da análise):
  → Tool: Write  projects/{project_name}/outputs/asis/security/{agent}-asis.json  com conteúdo stub:
    { "agent": "{agent}", "generated_at": "PENDING", "project": "{project_name}", "findings": [], "subtotal": 0 }
  ⛔ PROIBIDO: iniciar análise sem ter executado o PASSO 0
  ⛔ PROIBIDO: omitir o path completo — nunca escrever apenas {agent}-asis.json sem o diretório
  Objetivo: garantir rastreabilidade mesmo em falha parcial

PASSO 1–N — ANÁLISE (específico de cada sub-agent)

PASSO FINAL-1 — WRITE JSON DEFINITIVO:
  → Tool: Write  projects/{project_name}/outputs/asis/security/{agent}-asis.json  (substitui o stub — findings completos)
  ⛔ PROIBIDO: omitir o path completo — nunca escrever apenas {agent}-asis.json sem o diretório

PASSO FINAL-2 — WRITE ARTEFATOS MANDATÓRIOS:
  Para cada artefato OBRIGATÓRIO listado no Output Contract do sub-agent:
  → Tool: Write  {artefato}.md  (conteúdo completo ou "## Nota de Ausência de Evidência" se sem dados)
  ⛔ PROIBIDO: pular artefato OBRIGATÓRIO — gerar com seção de ausência quando sem dados
  ⛔ PROIBIDO: avançar para COMPLETION_SIGNAL sem ter completado TODOS os Writes deste passo

PASSO FINAL-3 — COMPLETION_SIGNAL:
  artifacts_generated[] DEVE listar todos os arquivos escritos nos PASSOS FINAL-1 e FINAL-2
  ⛔ PROIBIDO: artifacts_generated[] vazio
  ⛔ PROIBIDO: artifacts_generated[] omitindo qualquer artefato MANDATORY do sub-agent
  ⛔ PROIBIDO: emitir status: COMPLETED com artifacts_generated[] incompleto → usar status: FAILED
```

### Regra de "Nota de Ausência de Evidência"

Quando um artefato OBRIGATÓRIO não tem dados para preencher (ex: sem runtime evidence para `runtime-security-validation.md`):
- **GERAR O ARQUIVO de qualquer forma** com o seguinte template mínimo:
  ```markdown
  ## Nota de Ausência de Evidência
  **Agente:** {sub_agent_id}
  **Data:** {generated_at}
  **O que foi buscado:** {descrição do que foi analisado}
  **Por que não foi encontrado:** {razão técnica objetiva}
  **Impacto:** {consequência da ausência para a análise de segurança}
  ```
- Nunca omitir o arquivo — arquivo ausente = falha de DoD

---

## @security-orchestrator-signal-validation

**Validação de COMPLETION_SIGNAL pelo Orquestrador**

Ao receber COMPLETION_SIGNAL de qualquer sub-agent, o `security-orchestrator-asis` DEVE executar estas verificações **antes** de registrar o sub-agent como `completed`:

```
VERIFICAÇÃO 1 — sub_agent_id válido:
  sub_agent_id ∈ { "ava-asis-security-sast", "ava-asis-security-iast",
                   "ava-asis-security-threat-model", "ava-asis-security-taint",
                   "ava-asis-security-dependency-config", "ava-asis-security-pt-pattern",
                   "ava-asis-security-review" }
  FALHA → rejeitar sinal, registrar como INVALID

VERIFICAÇÃO 2 — artifacts_generated[] não está vazio:
  len(signal.artifacts_generated) > 0
  FALHA → registrar sub-agent como FAILED → retry (max 2x)

VERIFICAÇÃO 3 — JSON do sub-agent existe em disco com conteúdo real:
  path = "projects/{project_name}/outputs/asis/security/{agent}-asis.json"
  Verificar: arquivo existe E size > 100 bytes E NÃO contém "PENDING" em generated_at
  FALHA → registrar sub-agent como FAILED → retry (max 2x)

VERIFICAÇÃO 4 — artefato primary do sub-agent existe em disco:
  Artefatos primary obrigatórios por sub-agent:
    sast-asis              → privilege-matrix.md
    iast-asis              → runtime-security-validation.md
    threat-model-asis      → attack-surface.md + threat-model-stride.md
    taint-asis             → taint-flow-report.md
    dependency-config-asis → supply-chain-risk-report.md
    pt-pattern-asis        → remediation-backlog.md
    security-review-asis   → owasp-coverage-matrix.md
  Verificar: arquivo existe E size > 0
  FALHA → registrar sub-agent como FAILED → retry (max 2x)

APÓS 2 RETRIES FALHADOS:
  → sub_agent.status = FAILED_UNRECOVERABLE
  → Incluir em incomplete_artifacts[] do Consolidation Gate output
  → ⛔ NÃO bloquear gate indefinidamente — prosseguir com WARNING
  → security_gate = DIAGNOSTIC_COMPLETE_WITH_GAPS (em vez de DIAGNOSTIC_COMPLETE)
```

---

## @security-parameter-inference-base

**Inferência de Parâmetros — Base Compartilhada (todos os sub-agents)**

> ⚡ **Assessment completo sem espera humana.**
> Todos parâmetros são inferidos automaticamente e aplicados imediatamente.
> NUNCA pedir confirmação — execução imediata após receber dispatch do orquestrador.

**Auto-inicializar sem confirmação (campos comuns — todo sub-agent):**
- `trace_id` ausente → herdar do security-orchestrator-asis (NUNCA gerar novo se fornecido).
- `known_finding_ids[]` ausente → assumir `[]` (primeira iteração).
- Cobertura total — execução sempre completa e incondicional.
- `source.type` → inferir automaticamente do contexto disponível e aplicar imediatamente.

> ⚡ **INVARIANTE:** NUNCA aguardar resposta humana. Executar IMEDIATAMENTE o assessment completo.

> **Nota para o sub-agent:** Adicionar o bullet `agent_chain` específico do agente após esta diretiva:
> `- \`agent_chain\` ausente → inicializar como \`["{nome-do-agente}"]\` e prosseguir; presente → APPEND \`"{nome-do-agente}"\` ao chain recebido.`

---

## @security-mandatory-invariants-base

**Invariantes Obrigatórias — Base Compartilhada (todos os sub-agents)**

- `@common-roles:security-repository-path-resolution` — resolver `repository_path` do input ou project-config.yaml ANTES do PASSO 0. ⛔ PROIBIDO iniciar scan sem `repository_path` resolvido.
- Focar apenas em findings cujos `finding_id` NÃO estão em `known_finding_ids[]`.
- Retornar `findings[]` ao security-orchestrator-asis; nunca rotear diretamente para outro agente.
- `hypothesis: true` quando evidência ausente ou inferida — `finding` DEVE começar com `[Hipótese]`.
- Prioridade calculada: P0 = CRITICAL ou exploração ativa; P1 = HIGH sem exploração; P2 = MEDIUM; P3 = LOW/INFO/preventivo.
- `@common-roles:security-write-first-discipline` — SEMPRE aplicar. ⛔ **PROIBIDO**: retornar ao orquestrador sem ter escrito TODOS os artefatos obrigatórios.

---

## @security-completion-signal-step

**PASSO FINAL-3 — COMPLETION_SIGNAL (todos os sub-agents)**

**PASSO FINAL-3 — COMPLETION_SIGNAL** (emitir como última ação antes do retorno):
- Ver seção `## Completion Signal (OBRIGATÓRIO)` abaixo
- `artifacts_generated[]` DEVE listar TODOS os arquivos escritos nos PASSOS FINAL-1 e FINAL-2
- ⛔ PROIBIDO: retornar ao orquestrador sem emitir este sinal

---

## @security-leaf-io-contract

I/O padrão para sub-agents de segurança do módulo `asis-diagnostic`.

**Input (obrigatório):**
- `trace_id`: herdado do `security-orchestrator-asis`
- `agent_chain`: lista de agentes executados até aqui
- `known_finding_ids[]`: IDs de findings já descobertos nas iterações anteriores
- `project_name`: nome do projeto corrente

**Input (opcional):**
- `security_profile`: RAPID | STANDARD | DEEP *(deprecated desde v1.5.0 — ignorado; cobertura total incondicional)*
- `implementation.files_changed`: arquivos alterados (quando disponível)
- `detected_stack`: stack detectada

**Output (schema canônico JSON — OBRIGATÓRIO):**

> ⚡ **INVARIANTE:** O JSON de saída de cada sub-agent DEVE usar exclusivamente os campos canônicos abaixo.
> Campos legados (`finding_id`, `description`, `evidence`, `owasp_mapping`) são **PROIBIDOS** no JSON de saída.

```json
{
  "agent":        "{agent}-asis",
  "generated_at": "<Bash: python src/shared/utils/ntp_time.py>",
  "project":      "{project_name}",
  "findings": [{
    "id":              "SEC-{PROJECT}-{AGENT_PREFIX}-NNN",
    "type":            "Injection|Authentication|Authorization|Cryptography|Configuration|Dependency|Secrets|DataExposure|SessionMgmt|InputValidation|LogMonitoring|BusinessLogic|ThreatModel|TaintFlow|Compliance|Other",
    "severity":        "CRITICAL|HIGH|MEDIUM|LOW|INFO",
    "owasp":           "A0N:AAAA",
    "cwe":             "CWE-NNN",
    "issue_ref":       "https://cwe.mitre.org/data/definitions/{N}.html",
    "finding":         "Descrição objetiva ≥ 20 chars (NUNCA vazio)",
    "evidences":       "Arquivo - Linha N|Arquivo - Linha M",
    "source":          "{agent}-asis",
    "count":           1,
    "stride":          "S|T|R|I|D|E|N/A",
    "hypothesis":      false,
    "business_impact": "Descrição do impacto de negócio (nullable)",
    "effort":          "S|M|L",
    "owner_suggested": "squad-backend|security-team|devops",
    "priority":        "P0|P1|P2|P3",
    "recommendation":  "Texto acionável NUNCA vazio"
  }],
  "subtotal": 1
}
```

**Prefixos de `id` por sub-agent:**
| Sub-agent | Prefixo |
|---|---|
| sast-asis | `SAST` |
| iast-asis | `IAST` |
| threat-model-asis | `TM` |
| taint-asis | `TAINT` |
| dependency-config-asis | `DEP` |
| pt-pattern-asis | `PT` |
| security-review-asis | `REV` |

- `security.status`: PASSED | FAILED | PASSED_WITH_WARNINGS
- `agent_chain`: atualizado com este sub-agent
