import pathlib

p = pathlib.Path("src/modules/ava-fabric-agents/asis-diagnostic/shared/common-roles-security.md")
c = p.read_text(encoding="utf-8")

idx = c.find("securityReview")
end = c.find("---\n\n## @security-repository", idx)
old_block = c[idx:end]

lines = [
    'securityReview": [   \u2190 chave can\u00f4nica lida pelo template HTML',
    '    {',
    '      "id":               "SEC-{PROJECT}-NNN",',
    '      "vulnerability_type": "...",   \u2190 campo lido pelo template (r.vulnerability_type)',
    '      "sev":               "...",   \u2190 campo lido pelo template (r.sev) \u2014 lowercase: critical|high|medium|low|info',
    '      "owasp":             "...",',
    '      "cwe":               "...",',
    '      "desc":              "...",   \u2190 campo lido pelo template (r.desc)',
    '      "ev":                "...",   \u2190 campo lido pelo template (r.ev)',
    '      "source":            "...",',
    '      "count":             0',
    '    }',
    '  ]',
    '}',
    '```',
    '',
    '**Mapeamento de campos can\u00f4nicos \u2192 campos do template HTML:**',
    '',
    '| Campo do sub-agent JSON (`findings[]`) | Campo do `securityReview[]` (template) |',
    '|---|---|',
    '| `type` | `vulnerability_type` |',
    '| `severity` | `sev` (lowercase: `critical|high|medium|low|info`) |',
    '| `owasp` | `owasp` |',
    '| `cwe` | `cwe` |',
    '| `finding` | `desc` |',
    '| `evidences` | `ev` |',
    '| `source` | `source` |',
    '| `count` | `count` |',
    '',
    '> \u26d4 **PROIBIDO**: usar chave `"vulnerabilities"` em vez de `"securityReview"` \u2014 o template HTML l\u00ea exclusivamente `D.securityReview`.',
    '> \u26d4 **PROIBIDO**: copiar campos brutos (`type`, `severity`, `finding`, `evidences`) sem renomear para os nomes do template (`vulnerability_type`, `sev`, `desc`, `ev`).',
    '',
]
new_block = "\n".join(lines) + "\n"

c2 = c[:idx] + new_block + c[end:]
p.write_text(c2, encoding="utf-8")
print(f"P1 DONE")
