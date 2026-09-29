# Batch Write Protocol — AVA AS-IS Agents

Referenciado por `orchestrator-asis.md`, `solution-delphi.md`, `inventory-asis.md`,
`documentation-asis.md`, `gaps-risks-asis.md`.

> **Regra crítica de performance:** Todos os artefatos de um agente DEVEM ser escritos
> em **uma única chamada Bash** usando o padrão hashtable PowerShell abaixo.
> NUNCA fazer uma chamada por arquivo — isso multiplica o overhead de startup por N arquivos.

---

## ⛔ Anti-Pattern (PROIBIDO)

```
# ERRADO — N round-trips separados
Bash: Set-Content "outputs/asis/file1.md" -Value $content1
Bash: Set-Content "outputs/asis/file2.md" -Value $content2
...  # × N arquivos = N × overhead de startup
```

Sintoma: pipeline leva 30–40 min para 24 arquivos que poderiam ser gravados em ~2 min.

---

## ✅ Padrão Correto — Batch Único

Consolidar **todo** o output contract do agente em um único script PowerShell:

```powershell
# ── BATCH WRITE — {AgentName} ──────────────────────────────────────────
$base = "projects/{project_name}/outputs/asis"

$files = [ordered]@{
    "artifact1.md"           = @'
<conteúdo completo do artifact1>
'@
    "artifact2.json"         = @'
<conteúdo completo do artifact2>
'@
    "docs\artifact3.md"      = @'
<conteúdo completo do artifact3>
'@
    "diagrams\diagram.mmd"   = @'
<conteúdo completo do diagrama>
'@
}

# Escreve todos de uma vez
$ok = 0; $fail = 0
foreach ($entry in $files.GetEnumerator()) {
    $path = Join-Path $base $entry.Key
    $dir  = Split-Path $path -Parent
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    try {
        [System.IO.File]::WriteAllText($path, $entry.Value, [System.Text.Encoding]::UTF8)
        Write-Host "OK $($entry.Key) — $((Get-Item $path).Length) bytes"
        $ok++
    } catch {
        Write-Host "FAILED: $($entry.Key) — $_"
        $fail++
    }
}
Write-Host ""
Write-Host "=== Batch result: $ok written, $fail failed ==="
# ── END BATCH WRITE ────────────────────────────────────────────────────
```

**Executar via:**
```
Bash: powershell -NoProfile -ExecutionPolicy Bypass -Command "<script acima>"
```

---

## Regras

1. **Um batch por agente** — todos os artefatos do output contract em uma invocação.
2. **Criar subdiretórios automaticamente** — `New-Item -Force` antes de escrever.
3. **Verificar bytes após escrita** — `(Get-Item $path).Length` deve ser > 0.
4. **Arquivos `.mmd`** — validar sintaxe mermaid antes de incluir; se inválido, usar fallback seguro sem abortar o batch.
5. **Falha parcial** — continuar para os próximos arquivos; reportar `$fail` ao final; se `$fail > 0` acionar RetryProtocol apenas para os arquivos com falha.
6. **Encoding** — usar `[System.IO.File]::WriteAllText` com `UTF8` para garantir sem BOM.

---

## Estimativa de ganho de performance

| Abordagem                    | Chamadas Bash | Overhead total | Tempo (24 arquivos) |
|------------------------------|---------------|----------------|---------------------|
| 1 arquivo por Bash           | 24            | 24 × ~60s      | ~24 min             |
| Batch único (este protocolo) | **1**         | 1 × ~60s       | **~2 min**          |

---

## Integração com artifact_gate.py

Antes de montar o batch, checar `artifact_gate.py` uma única vez para o agente:

```
Bash: python src/modules/ava-fabric-agents/asis-diagnostic/utils/artifact_gate.py \
  --project {project_name} --agent {agent_id}
```

- `dispatch: false` + `reason: artifacts_present` → **pular batch inteiro** (artefatos já existem).
- `dispatch: true` + `artifacts_missing: [...]` → incluir **apenas os arquivos ausentes** no batch (não sobrescrever os existentes).

---

## Integração com Orchestrator

O `orchestrator-asis.md` NÃO deve usar `general-purpose` agents para persistência de arquivos.
Regra no orchestrator (ver `## Guardrails`):

```
FILE_PERSISTENCE_RULE: Quando um sub-agente precisa persistir artefatos em disco:
  - USAR: task agent (mode: sync) + Batch Write PowerShell (este protocolo)
  - NUNCA: general-purpose background agent para escrita de arquivos
  - NUNCA: Write tool acumulado (gerar todo o conteúdo em memória e escrever no final)
  Razão: general-purpose agents geram conteúdo in-context sem garantia de flush para disco.
```
