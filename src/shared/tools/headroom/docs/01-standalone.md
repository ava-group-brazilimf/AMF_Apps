# Guia 01 — Rodar o Headroom standalone

Modo independente: **não** exige projeto em `projects/`, artefato AST, agente ou
esteira rodando. Serve para validar a instalação, medir compressão, comprimir
arquivos avulsos e usar o proxy com qualquer cliente Anthropic/OpenAI-compatible.

Todos os comandos rodam **da raiz do repositório**.

---

## Pré-requisitos

| Item                                   | Verificar com                                                 | Mínimo                 |
| -------------------------------------- | ------------------------------------------------------------- | ----------------------- |
| Python                                 | `python --version`                                          | 3.10                    |
| Git                                    | `git --version`                                             | qualquer                |
| Fork presente                          | `Test-Path src/shared/tools/headroom/vendor/pyproject.toml` | `True`                |
| Rust*(opcional)*                     | `cargo --version`                                           | só para buildar o fork |
| Chave do Foundry*(só p/ o passo 5)* | `Test-Path .copilot-key`                                    | `True`                |

Se o fork estiver ausente:

```powershell
git subtree add --prefix src/shared/tools/headroom/vendor `
  https://github.com/headroomlabs-ai/headroom.git main --squash
```

---

## Passo 1 — Conferir o ponto de partida

```powershell
python src/shared/tools/headroom/headroom_tool.py doctor
```

Antes de instalar, a saída esperada é esta — com `venv isolado` e `cli headroom`
em aviso. Isso é normal:

```
🩺 Headroom doctor
   ✅ config                     model=claude-sonnet-4-6 limit=200000 enabled=True
   ✅ fork (vendor/)             src\shared\tools\headroom\vendor
   ⚠️  venv isolado               ausente — rode setup.ps1
   ⚠️  cli headroom               ausente no venv (usando PATH)
   ⚠️  motor (import headroom)    indisponível — compressão em passthrough
   ✅ fatias por agente          19 agentes em context_budget.AGENT_ARTIFACT_SLICE
   ⚠️  proxy                      127.0.0.1:8787 fora do ar
   ✅ upstream                   https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic
```

**Exit codes**: `0` tudo verde · `1` degradado (funciona, mas não plenamente) ·
`2` fork ausente (erro duro).

---

## Passo 2 — Instalar o venv isolado

```powershell
# Completo — inclui o extra [ml] (torch ≈ 3 GB)
.\src\shared\tools\headroom\setup.ps1

# Recomendado para começar — sem torch, muito mais rápido
.\src\shared\tools\headroom\setup.ps1 -SkipML
```

Linux/macOS:

```bash
bash src/shared/tools/headroom/setup.sh --skip-ml
```

O venv vai para `src/shared/tools/headroom/.venv` e **não** contamina o venv
principal do repositório.

### Fork editável × wheel PyPI

O `setup` detecta `cargo` e informa qual caminho tomou:

```
  modo   : fork EDITÁVEL (cargo encontrado — build via maturin)
```

Patches em `vendor/` valem imediatamente.

```
  modo   : wheel PyPI headroom-ai==0.33.0 (cargo ausente)
           O fork em ./vendor fica como referência/patch source.
```

Funciona igual, mas o que roda é o wheel pré-compilado. Para buildar o fork de
verdade, instale Rust em [https://rustup.rs](https://rustup.rs) e rode `setup.ps1 -Force`.

**Confirme:**

```powershell
python src/shared/tools/headroom/headroom_tool.py doctor
```

Agora `venv isolado`, `cli headroom` e `motor` devem estar ✅.

---

## Passo 3 — Usar a CLI sem proxy

Nada aqui precisa de rede ou do proxy no ar.

### 3.1 Ver a configuração efetiva

```powershell
python src/shared/tools/headroom/headroom_config.py
```

Imprime a config já resolvida (env > `project-config.yaml` > `headroom.yaml`).
Use antes de qualquer troubleshooting: mostra exatamente qual modelo, limite,
porta e upstream estão valendo.

### 3.2 Comprimir um arquivo

```powershell
 `
  --input caminho/para/arquivo.json -o comprimido.json
```

```
✅ arquivo.json: 14,994 → 5,049 tokens (-66.3%) → comprimido.json
   transforms: router:smart_crusher:0.02
```

Sem o motor instalado, degrada para passthrough com aviso em vez de falhar.

### 3.3 Decodificar um artefato comprimido

```powershell
python src/shared/tools/headroom/headroom_tool.py decode --input comprimido.json
python src/shared/tools/headroom/headroom_tool.py decode --input comprimido.json -o legivel.json
```

Reverte os dois formatos que a pré-compressão produz (string tabular do
SmartCrusher e `factored_array`). Se o artefato tiver sido **amostrado** pelo
motor de fallback, avisa no stderr quantas linhas se perderam.

### 3.4 Consultar a fatia de um agente

```powershell
python src/shared/tools/headroom/headroom_tool.py -p Meu-ERP slice `
  --agent ava-asis-db-analyzer
```

Este é o único subcomando que precisa de um projeto — mas degrada limpo se o
projeto não tiver artefatos AST ainda.

---

## Passo 4 — Subir o proxy standalone

Modo primeiro plano (Ctrl+C encerra):

```powershell
.\src\shared\tools\headroom\run_standalone.ps1
```

Opções:

```powershell
.\src\shared\tools\headroom\run_standalone.ps1 -Port 8788
.\src\shared\tools\headroom\run_standalone.ps1 -Project Meu-ERP   # aplica o bloco headroom: do projeto
```

Linux/macOS:

```bash
bash src/shared/tools/headroom/run_standalone.sh
bash src/shared/tools/headroom/run_standalone.sh --port 8788
```

Saída esperada:

```
=== Headroom proxy :: modo standalone ===
  escutando : http://127.0.0.1:8787
  upstream  : https://aif-imf-apps-prd-eus2-001.services.ai.azure.com/anthropic
  backend   : anthropic
  modo      : token
  log       : ...\.headroom\proxy-requests.jsonl
```

### Alternativa: em segundo plano

```powershell
python src/shared/tools/headroom/headroom_tool.py proxy start
python src/shared/tools/headroom/headroom_tool.py proxy status
python src/shared/tools/headroom/headroom_tool.py proxy stop
```

O PID fica em `.headroom/proxy.pid`. `proxy status` retorna exit `0` no ar,
`1` fora do ar — é o que o `copilot-cli-headroom.bat` consulta.

### Confirmar que subiu

Noutra aba:

```powershell
python src/shared/tools/headroom/headroom_tool.py proxy status
src\shared\tools\headroom\.venv\Scripts\headroom.exe doctor
```

---

## Passo 5 — Apontar um cliente para o proxy

Com o proxy do passo 4 no ar:

### Claude Code

```powershell
$env:ANTHROPIC_BASE_URL = "http://127.0.0.1:8787"
claude
```

### Cliente OpenAI-compatible

```powershell
$env:OPENAI_BASE_URL = "http://127.0.0.1:8787/v1"
```

### Copilot CLI

Use o guia [02](02-esteira-github-cli.md) — o `.bat` já faz tudo.

> **Autenticação**: o proxy encaminha o header de auth do cliente para o
> upstream. Ele **não** injeta credencial própria — a chave continua vindo de
> quem chama.

---

## Passo 6 — Medir a economia

```powershell
$H = "src\shared\tools\headroom\.venv\Scripts\headroom.exe"

& $H perf                      # últimos 7 dias
& $H perf --hours 24           # últimas 24h
& $H perf --format json        # relatório agregado em JSON
& $H savings                   # ledger acumulado
& $H savings --json
& $H dashboard                 # abre no navegador (exige proxy no ar)
```

> ⚠️ **Duas trilhas de log diferentes.** `headroom perf` lê de
> `~/.headroom/logs/proxy.log` (formato interno do headroom). O
> `HEADROOM_LOG_FILE` que configuramos em `headroom.yaml`
> (`.headroom/proxy-requests.jsonl`) é um JSONL **separado**, com uma linha por
> requisição — use-o para análise própria:

```powershell
Get-Content .headroom\proxy-requests.jsonl -Tail 5
```

---

## Passo 7 — Container (opcional)

```powershell
podman build -f src/shared/tools/headroom/Containerfile -t ava-headroom:latest .
podman-compose -f src/shared/tools/headroom/podman-compose.yml up -d
podman-compose -f src/shared/tools/headroom/podman-compose.yml logs -f
podman-compose -f src/shared/tools/headroom/podman-compose.yml down
```

O build **precisa rodar da raiz do repositório** (o contexto tem que enxergar
`vendor/`). O container instala Rust e builda o fork de verdade, roda como
usuário não-root (UID 10001) e publica **apenas** em `127.0.0.1:8787`.

O upstream vem de `ANTHROPIC_TARGET_API_URL` — copie `.env.example` para `.env`
na raiz antes de subir.

---

## Encerrar

```powershell
# primeiro plano
Ctrl+C

# segundo plano
python src/shared/tools/headroom/headroom_tool.py proxy stop

# container
podman-compose -f src/shared/tools/headroom/podman-compose.yml down
```

---

## Troubleshooting

| Sintoma                                           | Causa                                                            | Ação                                                                    |
| ------------------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------- |
| `Content detection using pure-Python backend…` | No Windows o detector nativo Magika/ONNX é recusado por padrão | Cosmético. Em Linux/container:`HEADROOM_DETECT_BACKEND=rust`           |
| `doctor` → `fork (vendor/)` em ⚠️ e exit 2 | Subtree ausente                                                  | Rode o`git subtree add` dos pré-requisitos                             |
| `setup.ps1` falha com erro de maturin/cargo     | Sem toolchain Rust                                               | Deixe cair no wheel PyPI, ou instale[https://rustup.rs](https://rustup.rs) |
| `run_standalone.ps1` → `venv ausente`        | Passo 2 não rodou                                               | `.\setup.ps1 -SkipML`                                                   |
| Porta 8787 ocupada                                | Outro proxy no ar                                                | `proxy status`, ou use `-Port 8788`                                   |
| `headroom perf` sem dados                       | Nenhuma requisição passou ainda, ou olhando a trilha errada    | Faça uma chamada real; confira`.headroom/proxy-requests.jsonl`         |
| `SSLV3_ALERT_BAD_RECORD_MAC`                    | HTTP/2 com streams cancelados                                    | Já mitigado — o proxy sobe com`--no-http2`                            |

---

## Próximo passo

[02 — Esteira + GitHub CLI](02-esteira-github-cli.md), para rodar os agentes com
compressão e métricas por agente.
