# Tasks: Headroom Context Compression — Tool + Proxy Interceptor

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)
`[P]` = paralelizável (arquivos disjuntos). Status real da entrega.

---

## Category 1 — Fork, venv e contrato da tool *(bloqueia todo o resto)*

- [x] **1.1** Spike da CLI: `headroom --help`, `proxy --help`, `wrap copilot --help`,
      `doctor --help`, assinatura de `compress()`. Registrar em `research.md` §1.
      **Bloqueante** — o prompt de origem assumia `--upstream` e `headroom stats`,
      que não existem.
- [x] **1.2** `git subtree add --prefix src/shared/tools/headroom/vendor
      https://github.com/headroomlabs-ai/headroom.git main --squash`
      → 2.193 arquivos, 60,5 MB, `headroom-ai` 0.33.0.
- [x] **1.3** `requirements.txt` com `headroom-ai[proxy,mcp,ml,code,memory,otel]==0.33.0`
      (versão **pinada** à do vendor), `pyyaml`, `pytest`.
- [x] **1.4** `setup.ps1` + `setup.sh`: venv isolado, checagem de Python ≥ 3.10,
      detecção de `cargo` (fork editável) com fallback para wheel PyPI da mesma
      versão, flag `-SkipML` / `--skip-ml` (torch ≈ 3 GB), `-Force` / `--force`.
- [x] **1.5** `.gitignore`: ignorar `src/shared/tools/headroom/.venv/` e `.headroom/`;
      trocar `.vscode` por `.vscode/*` + `!.vscode/settings.json` + `!.vscode/mcp.json`;
      negar `!.env.example`. Verificar com `git check-ignore -v`.

## Category 2 — Configuração *(Artigo I — nada hardcoded)*

- [x] **2.1** `headroom.yaml`: defaults da tool (modelo, `context_limit`, bloco
      `proxy`, `compress`, `observability`, `fallback_on_error`).
- [x] **2.2** `headroom_config.py`: `load_config()` com merge recursivo
      env > `project-config.yaml` > `headroom.yaml`; `metrics_path()`,
      `proxy_log_path()`, `proxy_env()`, `venv_python()`, `venv_headroom()`.
      Env malformada emite aviso e mantém a camada de baixo.
- [x] **2.3** `proxy_env()` emite `ANTHROPIC_TARGET_API_URL` (**não** existe
      `--upstream`), `HEADROOM_HOST/PORT/BACKEND/MODE/LOG_FILE`, `TELEMETRY=off`.
- [x] **2.4** Bloco `headroom:` comentado em
      `projects/_template/context/project-config.yaml`, no mesmo estilo do bloco
      `context_budget_*` que a spec 030 introduziu. Inteiramente opcional.
- [x] **2.5** `.env.example` na raiz documentando todas as variáveis, sem valores
      sensíveis. A chave continua em `.copilot-key`.

## Category 3 — Domínio: decodificação e fatia *(o núcleo)*

- [x] **3.1** Determinar empiricamente o formato de saída do SmartCrusher —
      cabeçalho `[N]{k:t,…}` + CSV RFC 4180. Sonda em `research.md` §3.
- [x] **3.2** `decode_table_string()` com `csv.reader` (obrigatório: há newline
      dentro de campo citado) + `_parse_table_header()` + `_coerce_cell()`
      cobrindo `string · int · float · bool · json` e o sufixo `?`.
- [x] **3.3** `_decode_factored_array()` para o formato do motor fallback.
- [x] **3.4** `decode_headroom()` recursivo, idempotente, passthrough seguro;
      `decode_report()` expondo `rows_dropped` quando `sampled: true`.
- [x] **3.5** [P] `resolve_compressed_dir()` / `resolve_extraction_dir()` /
      `read_artifact()` / `read_artifact_payload()` com fallback compressed↔extraction.
- [x] **3.6** [P] `read_compression_metrics()` e `estimate_agent_tokens()` lendo
      `manifest.artifacts[].tokens_out`.
- [x] **3.7** `AGENT_ARTIFACT_SLICE` **importado** de `context_budget.py` via
      `importlib.util.spec_from_file_location`. **Não** criar `AGENT_ARTIFACT_MAP`.
- [x] **3.8** `build_agent_context()` devolvendo só a fatia do agente, com
      `known_agent` sinalizando agente fora do mapa.
- [x] **3.9** `HEADROOM_AVAILABLE` por import defensivo, com tentativa extra via
      `sys.path.insert(VENDOR_DIR)`.
- [x] **3.10** Validar roundtrip `compress()` → `decode_headroom()` com 520 linhas
      (vírgula, aspas, newline, nulo, JSON aninhado, float, bool) → 0 diferenças.

## Category 4 — Interface: CLI e MCP

- [x] **4.1** `headroom_tool.py` no padrão do repo: `argparse` + **dispatch dict**,
      `print()`/`sys.exit` (sem `logging`), guard UTF-8 no `__main__`, BRZ (`-03:00`).
- [x] **4.2** Subcomandos `slice`, `decode`, `compress`, `metrics`, `stats`,
      `doctor`, `proxy {start|stop|status}`. Exit `0` OK · `1` degradado · `2` erro.
- [x] **4.3** `metrics` faz append em
      `projects/{p}/outputs/observability/headroom-metrics.jsonl`, reusando o
      idioma de `pipeline_observer._write_agent_metrics`.
- [x] **4.4** `proxy start` sobe destacado (`CREATE_NEW_PROCESS_GROUP` no Windows,
      `start_new_session` no POSIX) com PID em `.headroom/proxy.pid`.
- [x] **4.5** [P] `mcp_server.py` (FastMCP, stdio) com `headroom_slice`,
      `headroom_retrieve`, `headroom_decode`, `headroom_compress`, `headroom_stats`.

## Category 5 — Interceptação *(invariantes I1 e I3)*

- [x] **5.1** `copilot-cli-headroom.bat`: cópia de `copilot-cli-v1.bat` com
      `COPILOT_PROVIDER_BASE_URL` → `http://127.0.0.1:8787` e
      `ANTHROPIC_TARGET_API_URL` → endpoint real. Todo o resto preservado.
- [x] **5.2** Degradação: se `proxy status` falhar, usa o endpoint direto,
      imprime `headroom compression=no` e **inicia a sessão mesmo assim** (I5).
- [x] **5.3** [P] `run_standalone.ps1` / `.sh`: proxy em primeiro plano, sem
      projeto nem esteira (I1). Config obtida de `headroom_config.py --env`.
- [x] **5.4** [P] `.vscode/mcp.json` com `ava-headroom` e `ava-headroom-cli`
      (caminhos `Scripts/` do Windows).
- [x] **5.5** `.vscode/settings.json`: **merge**, preservando as 4 chaves
      existentes. Acrescenta `github.copilot.advanced`,
      `terminal.integrated.env.windows`, `files.exclude`, `search.exclude` e
      auto-approve dos subcomandos de leitura da tool.
- [x] **5.6** [P] `Containerfile` (multi-stage, instala Rust e builda o **fork**,
      UID não-root, healthcheck) + `podman-compose.yml` publicando só em
      `127.0.0.1`.

## Category 6 — Reconexão dos consumidores *(gaps L3 / L4)*

- [x] **6.1** `build_summary_comprehensive.py`: remover o unwrap inline de
      `factored_array` (4 linhas) e chamar `decode_headroom`. Import defensivo com
      no-op de fallback.
- [x] **6.2** `sql_ir_generator.py`: novo `_load_ast()` — `extraction/` preferido
      (o gerador precisa de 100% das entidades; o fallback amostra), `compressed/`
      decodificado como fallback. Substituir os 3 `_load_json(self.ast_dir / …)`.
- [x] **6.3** Substituir o `NOTE` obsoleto que justificava o retorno ao raw pela
      explicação do comportamento atual.
- [x] **6.4** Confirmar zero regressão: `pytest tests/utils/ -q` → 28 passed.
- [x] **6.5** Confirmar IV2: `grep -rn "__headroom__" src/ --exclude-dir=vendor`
      casa só em `headroom_context.py`.

## Category 7 — Instrumentação dos agentes *(Artigo X)*

- [x] **7.1** Levantar o estado atual de versão nos 3 lugares (frontmatter,
      literal `--version` do `track`, dois `AGENT_CATALOG`) antes de editar.
      *Achado: drift pré-existente em `inventory` (1.5.0/1.4.0/1.4.0),
      `documentation` (3.0.0/3.0.0/1.6.0) e `db-analyzer` (1.5.0/1.5.0/1.4.0).*
- [x] **7.2** Inserir `### Step 1.1 — Registro de Compressão Headroom` após o
      Step 1 em: `solution-delphi.md`, `inventory-asis.md`,
      `db-analyzer/db-analyzer.md`, `events-pubsub-asis.md`,
      `documentation-asis.md`. Comando **literal inline**, com o `agent_id` já
      substituído — nunca `@referência`.
- [x] **7.3** Bump MINOR nos 5, sincronizando frontmatter e literal `--version`.
- [x] **7.4** Sincronizar `AGENT_CATALOG` em `pipeline_observer.py` **e**
      `generate_observability_report.py`; adicionar a entrada ausente de
      `ava-asis-events-pubsub`.
- [x] **7.5** Reverificar consistência tripla nos 5 agentes tocados e confirmar
      que os catálogos ainda carregam (`AGENT_CATALOG` = 56 entradas).
- [x] **7.6** **Não** instrumentar `solution-{vb,vbnet,cobol,powerbuilder}` nem os
      agentes de consolidação — documentado em spec.md §7.

## Category 8 — Testes, documentação e catálogo

- [x] **8.1** `tests/tools/test_headroom_context.py` — 22 testes: decodificação
      dos dois formatos, CSV RFC 4180, nullable/json, recusa de não-tabular,
      idempotência, passthrough, IV1 (incl. guarda contra `AGENT_ARTIFACT_MAP`),
      precedência de config, `ANTHROPIC_TARGET_API_URL`, IV3, métricas.
- [x] **8.2** `specs/031-headroom-context-compression-proxy/`: `spec.md`,
      `plan.md`, `tasks.md`, `research.md`, `quickstart.md`.
- [x] **8.3** `src/shared/tools/headroom/README.md` — instalação, config, CLI,
      proxy, MCP, container, manutenção do fork, troubleshooting.
- [x] **8.4** Linha da tool na tabela `## Files` de `src/shared/tools/README.md`
      (é assim que uma tool é "registrada" neste repo).

---

## Completion Checklist

- [x] `pytest tests/tools/ -q` → 22 passed
- [x] `pytest tests/utils/ -q` → 28 passed
- [x] `grep -rn "__headroom__" src/ --exclude-dir=vendor` → só `headroom_context.py`
- [x] `grep -rn "AGENT_ARTIFACT_MAP" src/` → vazio
- [x] `headroom_tool.py doctor` roda sem o venv da tool e reporta degradação
- [x] `headroom_tool.py -p X slice --agent ava-asis-db-analyzer` devolve a fatia
      de `context_budget.AGENT_ARTIFACT_SLICE`
- [x] `metrics` + `stats` gravam e agregam o JSONL do projeto
- [x] Consistência tripla nos 5 agentes tocados
- [x] `git check-ignore` confirma `.env.example` / `.vscode/mcp.json` versionáveis
      e `.venv/` / `.headroom/` ignorados
- [ ] **Manual** — `quickstart.md` passos 3, 6 e 7 (setup do venv, proxy no ar,
      sessão real do Copilot CLI). Exigem rede, download de dependências e a
      chave do Foundry; não executados nesta entrega.
