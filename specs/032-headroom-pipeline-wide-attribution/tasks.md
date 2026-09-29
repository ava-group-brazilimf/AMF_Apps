# Tasks: Headroom — Atribuição em Toda a Esteira

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)
`[P]` = paralelizável. Status real da entrega.

---

## Category 1 — Registro canônico *(bloqueia todo o resto)*

- [x] **1.1** Inventariar os 105 arquivos de agente: id, versão, fase, presença do bloco
      `track` e uniformidade do texto-âncora. *Achado: âncora idêntica em só 81/105 —
      é o que inviabiliza a edição em massa.*
- [x] **1.2** `agent_registry.py`: varredura de `**/agents/**/*.md`, frontmatter sem
      exigir pyyaml, fase por `PHASE_BY_MODULE` (Constituição v1.4.0).
- [x] **1.3** `_is_dispatchable()` exclui `agents/*/skills/*.md` (4 sub-skills).
- [x] **1.4** `catalog()` sem depreciados e ordenado por fase; `catalog_or()` com
      fallback para execução fora da árvore do repo.
- [x] **1.5** `duplicates()` ignora depreciados — `ava-asis-security-review` tem uma
      cópia viva e uma `1.4.0-DEPRECATED`; só duas cópias **vivas** colidiriam.

## Category 2 — Gate de consistência *(antes da correção, não depois)*

- [x] **2.1** `verify_agent_observability.py` com E1–E6 e `--json`/`--agent`/`--ignore`.
- [x] **2.2** Rodar e capturar a linha de base: **51 violações**
      (3×E1 · 6×E2 · 31×E3 · 3×E4 · 7×E5 · 1×E6).

## Category 3 — Correção do drift *(frontmatter = fonte de verdade)*

- [x] **3.1** E5 primeiro: 7 agentes ganham `version:` adotando o valor que o bloco já
      reportava em runtime — é o número que os relatórios históricos usaram.
- [x] **3.2** E1: `--agent` correto nos 3 de QA que reportavam `ava-asis-db-analyzer`.
- [x] **3.3** E2: `--phase` correto em 6 agentes (2× F3→F4, 1× F7→F6, 3× F1→F5).
- [x] **3.4** E3: `--version` alinhado ao frontmatter em 31 agentes.
- [x] **3.5** E4: seção de observabilidade sintetizada em `security-review-tobe`,
      `test-plan-tobe` e `orchestrator-devops` (os 3 sem bloco).
- [x] **3.6** Revalidar: **51 → 0**.

## Category 4 — Catálogo único

- [x] **4.1** `pipeline_observer`: literal → `_STATIC_AGENT_CATALOG`;
      `AGENT_CATALOG = _load_agent_catalog()` via registry, import defensivo.
- [x] **4.2** [P] Mesmo em `generate_observability_report` (que também alimenta
      `_populate_pipeline_agents.py`).
- [x] **4.3** `PHASE_ORDER` e `PHASE_NAMES` ganham **F8** — os 3 agentes de summary
      emitem F8 e ficavam fora de ordenação.
- [x] **4.4** As 7 linhas sintéticas `ava-summary (F1..F7)` somem; fica o `ava-summary`
      real em F8. Resultado: **56 → 100** entradas, idênticas nos dois consumidores.
- [x] **4.5** `module.yaml` da raiz alinhado à Constituição v1.4.0 + contagens do registry.

## Category 5 — Hook do auto-reporte *(cobre 98 agentes, 1 arquivo)*

- [x] **5.1** `_write_headroom_metric()` em `pipeline_observer`, chamado por `cmd_track`.
- [x] **5.2** Grava `source: "self-report"` com identidade, tokens e duração; os campos
      de compressão ficam `None` — **o agente não sabe o tamanho pré-compressão**, e
      inventar seria pior que admitir a lacuna.
- [x] **5.3** Silencioso por design: sem a tool, `track` segue normal (IV3).
- [x] **5.4** `metrics` manual passa a marcar `source: "manual"`.

## Category 6 — Atribuição pelo proxy

- [x] **6.1** `_parse_epoch()` tratando `Z`, offset explícito e naive com fuso por
      contexto (proxy=UTC, observer=BRZ).
- [x] **6.2** `_read_proxy_log()` tolerante a aliases, descartando linhas sem tempo ou
      sem tokens — o esquema do headroom não é contratual.
- [x] **6.3** `_agent_windows()` reconstruindo `[fim − duração, fim]`, porque `cmd_track`
      grava `start == end`.
- [x] **6.4** `attribute_requests()` — função pura: exclusivo integral, sobreposto `1/N`
      rotulado `ambiguous`, órfão em `__unattributed__`.
- [x] **6.5** `cmd_attribute` com `--phase`, `--dry-run`, `--json`.
- [x] **6.6** `cmd_stats` agregando por `source`, separando estimado × medido.

## Category 7 — Orquestradores

- [x] **7.1** Bloco `### Consolidação da Economia Headroom` nos 6 orquestradores.
      Nenhum usa a âncora canônica (4 na variante B, 1 na E, 1 sem seção) — **edições à
      mão, não script**.
- [x] **7.2** `master-orchestrator` roda `attribute` sem `--phase` (esteira inteira) após
      o `finalize`, mais `stats`.
- [x] **7.3** Trim do Step 1.1 nos 5 agentes: sai o `metrics` (duplicaria com 5.1), fica
      o `slice`. Bump PATCH nos 5.

## Category 8 — Testes, CI e documentação

- [x] **8.1** `tests/tools/test_agent_registry.py` — 15 testes.
- [x] **8.2** [P] `tests/tools/test_headroom_attribution.py` — 18 testes, incluindo
      conservação de tokens e o ponta-a-ponta UTC×BRZ.
- [x] **8.3** `.azure-pipelines/validate-agent-observability.yml` (CHK-01..04),
      disparado por `**/agents/**` e pelas ferramentas de observabilidade.
- [x] **8.4** `specs/032-headroom-pipeline-wide-attribution/`.
- [x] **8.5** Atualizar `src/shared/tools/headroom/README.md`, `docs/02-esteira-github-cli.md`
      e a tabela `## Files` de `src/shared/tools/README.md`.

---

## Completion Checklist

- [x] `pytest tests/ -q` → **83 passed**, 6 skipped (era 50)
- [x] `verify_agent_observability.py` → **0** violações em 101 agentes
- [x] Ambos os `AGENT_CATALOG` = **100** entradas idênticas
- [x] 6 orquestradores invocam `attribute`; **0** agentes invocam `metrics` à mão
- [x] `attribute` conserva tokens e rotula ambiguidade
- [x] `track` grava `agent-events.jsonl` **e** `headroom-metrics.jsonl`
- [x] `stats` separa `self-report` de `proxy`
- [ ] **Manual** — execução real de uma fase pelo `copilot-cli-headroom.bat`, comparando
      `headroom perf` com a soma atribuída. Exige o proxy no ar, a chave do Foundry e uma
      esteira real; não executado nesta entrega (ver quickstart §7).
