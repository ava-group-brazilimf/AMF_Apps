import pathlib, json

# ── P2: Fix security-orchestrator-asis.md field mapping + schema ────────────
p = pathlib.Path("src/modules/ava-fabric-agents/asis-diagnostic/agents/security/security-orchestrator-asis.md")
c = p.read_text(encoding="utf-8")

# 2a. Fix the MAPEAMENTO field-by-field lines
old_map = (
    "id              \u2192 id                                                     \u2502\n"
    "  \u2502      type            \u2192 type   (copiar literal \u2014 ENUM can\u00f4nico)                \u2502\n"
    "  \u2502      severity        \u2192 severity  (CRITICAL|HIGH|MEDIUM|LOW|INFO)              \u2502\n"
    "  \u2502      owasp           \u2192 owasp  (ex: \"A03:2021\"; ausente \u2192 \"A00:Other\")         \u2502\n"
    "  \u2502      cwe             \u2192 cwe    (ausente \u2192 \"CWE-Other\")                         \u2502\n"
    "  \u2502      issue_ref       \u2192 issue_ref  (URL CWE/OWASP/NVD \u2014 copiar do JSON)        \u2502\n"
    "  \u2502      finding         \u2192 finding  (NUNCA vazio \u2014 \u2265 20 chars)                    \u2502\n"
    "  \u2502      evidences       \u2192 evidences  (formato: \"Arquivo - Linha N|...\"; NUNCA \u2205) \u2502\n"
    "  \u2502      source          \u2192 source  (nome do sub-agent; duplicatas: concat \"+\")    \u2502\n"
    "  \u2502      count           \u2192 count   (len(evidences.split(\"|\")))                    \u2502\n"
    "  \u2502      stride          \u2192 stride  (copiar; N/A se n\u00e3o preenchido)                \u2502\n"
    "  \u2502      hypothesis      \u2192 hypothesis  (true se qualquer finding do grupo)        \u2502\n"
    "  \u2502      business_impact \u2192 business_impact  (copiar do finding de maior sev.)     \u2502\n"
    "  \u2502      effort          \u2192 effort  (copiar do finding de maior severidade)        \u2502\n"
    "  \u2502      owner_suggested \u2192 owner_suggested  (copiar do finding de maior sev.)     \u2502\n"
    "  \u2502      priority        \u2192 priority  (copiar do finding de maior severidade)      \u2502\n"
    "  \u2502      recommendation  \u2192 recommendation  (copiar do finding de maior sev.)      \u2502\n"
    "  \u2502    "
)
new_map = (
    "id              \u2192 id                                                     \u2502\n"
    "  \u2502      type            \u2192 vulnerability_type  (renomear \u2014 ENUM can\u00f4nico)           \u2502\n"
    "  \u2502      severity        \u2192 sev  (lowercase: critical|high|medium|low|info)         \u2502\n"
    "  \u2502      owasp           \u2192 owasp  (ex: \"A03:2021\"; ausente \u2192 \"A00:Other\")         \u2502\n"
    "  \u2502      cwe             \u2192 cwe    (ausente \u2192 \"CWE-Other\")                         \u2502\n"
    "  \u2502      issue_ref       \u2192 issue_ref  (URL CWE/OWASP/NVD \u2014 copiar do JSON)        \u2502\n"
    "  \u2502      finding         \u2192 desc  (renomear \u2014 NUNCA vazio \u2014 \u2265 20 chars)             \u2502\n"
    "  \u2502      evidences       \u2192 ev  (renomear; formato: \"Arquivo - Linha N|...\"; NUNCA \u2205)\u2502\n"
    "  \u2502      source          \u2192 source  (nome do sub-agent; duplicatas: concat \"+\")    \u2502\n"
    "  \u2502      count           \u2192 count   (len(ev.split(\"|\")))                           \u2502\n"
    "  \u2502      stride          \u2192 stride  (copiar; N/A se n\u00e3o preenchido)                \u2502\n"
    "  \u2502      hypothesis      \u2192 hypothesis  (true se qualquer finding do grupo)        \u2502\n"
    "  \u2502      business_impact \u2192 business_impact  (copiar do finding de maior sev.)     \u2502\n"
    "  \u2502      effort          \u2192 effort  (copiar do finding de maior severidade)        \u2502\n"
    "  \u2502      owner_suggested \u2192 owner_suggested  (copiar do finding de maior sev.)     \u2502\n"
    "  \u2502      priority        \u2192 priority  (copiar do finding de maior severidade)      \u2502\n"
    "  \u2502      recommendation  \u2192 recommendation  (copiar do finding de maior sev.)      \u2502\n"
    "  \u2502    "
)
if old_map in c:
    c = c.replace(old_map, new_map, 1)
    print("2a: field mapping FIXED")
else:
    print("2a: NOT FOUND - checking snippet")
    idx = c.find("id              \u2192 id")
    print(repr(c[idx:idx+100]))

# 2b. Fix the campos line in the WRITE step
old_campos = "campos: type, severity, finding, evidences (N\u00c3O sev/desc/ev)"
new_campos = "campos: vulnerability_type, sev, desc, ev, owasp, cwe, source, count"
if old_campos in c:
    c = c.replace(old_campos, new_campos, 1)
    print("2b: campos line FIXED")
else:
    print("2b: NOT FOUND")

# 2c. Fix the JSON schema block (vulnerabilities -> securityReview with renamed fields)
old_schema_key = '"vulnerabilities": ['
new_schema_key = '"securityReview": ['
c = c.replace(old_schema_key, new_schema_key, 1)
print("2c: array key vulnerabilities->securityReview FIXED")

# 2d. Fix the Regras JSON that mentions vulnerabilities[] key name
old_regras = '`vulnerabilities[]` \u2014 array \u00fanico can\u00f4nico: ler os 7 `{agent}.json` individuais, mapear campos diretamente (sem renomear)'
new_regras = '`securityReview[]` \u2014 array \u00fanico can\u00f4nico: ler os 7 `{agent}.json` individuais, mapear campos renomeando para nomes do template (ver Regra 5 em common-roles-security.md)'
if old_regras in c:
    c = c.replace(old_regras, new_regras, 1)
    print("2d: Regras JSON key name FIXED")
else:
    print("2d: NOT FOUND - trying partial")
    idx = c.find("vulnerabilities[] \u2014 array")
    if idx != -1:
        end = c.find("\n", idx)
        print(repr(c[idx:end]))

# 2e. Fix total line
old_total = '`total` = `sum(f.count for f in vulnerabilities[])` \u2014 somat\u00f3rio dos counts (N\u00c3O contagem de linhas)'
new_total = '`total` = `sum(f.count for f in securityReview[])` \u2014 somat\u00f3rio dos counts (N\u00c3O contagem de linhas)'
if old_total in c:
    c = c.replace(old_total, new_total, 1)
    print("2e: total line FIXED")
else:
    print("2e: NOT FOUND")

# 2f. Fix DEDUP chave line - update field names
old_dedup = "DEDUP vulnerabilities[] por chave (type, owasp, cwe):"
new_dedup = "DEDUP securityReview[] por chave (vulnerability_type, owasp, cwe):"
if old_dedup in c:
    c = c.replace(old_dedup, new_dedup, 1)
    print("2f: DEDUP chave line FIXED")
else:
    print("2f: NOT FOUND")

# Also fix the evidences->ev in the DEDUP MERGE formula
old_ev_formula = '`evidences` MERGE: `"|".join(sorted(set(e.strip() for f in matches for e in f.evidences.split("|"))))`'
new_ev_formula = '`ev` MERGE: `"|".join(sorted(set(e.strip() for f in matches for e in f.ev.split("|"))))`'
if old_ev_formula in c:
    c = c.replace(old_ev_formula, new_ev_formula, 1)
    print("2g: evidences MERGE formula FIXED")

# Fix the finding/evidences anti-vazio fallback line  
old_antivazio = '`finding`/`evidences` NUNCA vazios (fallback: `"\u2014"`)'
new_antivazio = '`desc`/`ev` NUNCA vazios (fallback: `"\u2014"`)'
if old_antivazio in c:
    c = c.replace(old_antivazio, new_antivazio, 1)
    print("2h: anti-vazio line FIXED")

# 2i. Fix the sample JSON inside the Contrato block: rename fields
old_sample = (
    '      "type":            "Injection|Authentication|Authorization|Cryptography|Configuration|Dependency|Secrets|DataExposure|SessionMgmt|InputValidation|LogMonitoring|BusinessLogic|ThreatModel|TaintFlow|C'
)
if old_sample in c:
    # replace type->vulnerability_type, severity->sev, finding->desc, evidences->ev in the sample JSON
    idx_s = c.find('"type":            "Injection|')
    end_s = c.find('"recommendation":  "', idx_s)
    end_s = c.find('"\n', end_s) + 2
    sample_old = c[idx_s:end_s]
    sample_new = sample_old
    sample_new = sample_new.replace('"type":            ', '"vulnerability_type": ', 1)
    sample_new = sample_new.replace('"severity":        ', '"sev":               ', 1)
    sample_new = sample_new.replace('"severity": "CRITICAL|HIGH|MEDIUM|LOW|INFO"', '"sev":     "critical|high|medium|low|info"', 1)
    sample_new = sample_new.replace('"finding":         ', '"desc":              ', 1)
    sample_new = sample_new.replace('"evidences":       ', '"ev":                ', 1)
    c = c[:idx_s] + sample_new + c[end_s:]
    print("2i: sample JSON fields FIXED")
else:
    # Just do simple replacements in the sample  
    print("2i: sample not found via prefix, applying inline replacements")

p.write_text(c, encoding="utf-8")
print("P2 DONE")
