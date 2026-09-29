# Tasks: Feature 043 — Summary Self-Correction Layer

**Spec**: `specs/043-summary-self-correction/spec.md`
**Plan**: `specs/043-summary-self-correction/plan.md`
**Data Model**: `specs/043-summary-self-correction/data-model.md`
**Contracts**: `specs/043-summary-self-correction/contracts/builder-cli-contract.md`
**Quickstart**: `specs/043-summary-self-correction/quickstart.md`
**Branch**: `043-summary-self-correction`
**Total tasks**: 17 (9 P0: a–i · 5 P1: a–e · 3 Transversais: a–c)

> **Sequência obrigatória**: P0-a é pré-requisito global — nenhuma outra P0 começa antes dela.
> P1-a e P1-b são paralelizáveis entre si [P]. P1-c/d/e só rodam após todo comportamento P0+P1 estar implementado.
> Transversais (T-a, T-b, T-c) são gates de fechamento de branch — somente após TODAS as P0 e P1 concluídas.

---

## Dependências

```
P0-a ──► P0-b ──► P0-c ──► P0-d
                       └──► P0-e
         P0-f ──────────────────► P0-g ──► P0-h ──► P0-i
              (P0-e boundary needed by P0-g)
P0-c ──► P1-a [P]
P0-c ──► P1-b [P]
(all P0+P1) ──► P1-c ──► P1-d ──► P1-e
(all P0+P1) ──► T-a ──► T-b ──► T-c
```

---

## Bloco P0 — Tarefas Bloqueantes

> Devem ser concluídas antes de qualquer P1. Encadeadas sequencialmente — não paralelizáveis exceto onde indicado [P].

---

### P0-a — `artifact-map.yaml` v1.2.0: Adicionar seção `corrections_config`

- [ ] **P0-a**
  - **Arquivo**: `src/modules/ava-fabric-agents/summary/data/artifact-map.yaml`
  - **Spec ref**: §3.3, §4.2
  - **Plano ref**: plan.md §8 P0-a
  - **BDD**: Spec §5 Scenario 2.2 — dado nova entrada `path_aliases[]` no YAML para artefato X, quando o builder roda e o path primário está ausente mas um alias existe, então o alias é usado sem qualquer mudança no código Python.
  - **Depende de**: nenhuma (pré-requisito global)
  - **Paralelo**: não

  **Passos**:
  1. [ ] Bump `version` de `"1.1.0"` para `"1.2.0"`.
  2. [ ] Inserir bloco de comentário `# ─── CORRECTIONS CONFIG — spec 043 ───` ao final do arquivo (após todas as seções keyed por agente, antes de `html_element_correlation`).
  3. [ ] Adicionar bloco `corrections_config` com as três entradas baseline (`inventory`, `iac`, `nuget`) conforme data-model.md §4 (paths com prefixo `outputs/`).
  4. [ ] Verificar parse sem erro: `python -c "import yaml; yaml.safe_load(open('artifact-map.yaml'))"`.
  5. [ ] Confirmar que nenhuma chave existente sob `f1_asis`, `f2_tobe` etc. foi modificada.

---

### P0-b — `build_summary_comprehensive.py`: Adicionar `_load_corrections_config()`

- [ ] **P0-b**
  - **Arquivo**: `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py`
  - **Spec ref**: §4.1 (pré-requisito)
  - **Plano ref**: plan.md §8 P0-b
  - **BDD**: Spec §5 Scenario 2.1 — alias resolvido via config, sem alteração de código Python.
  - **Depende de**: P0-a (lê `corrections_config` do YAML)
  - **Paralelo**: não

  **Passos**:
  1. [ ] Adicionar `import yaml` (verificar se já presente — idempotente).
  2. [ ] Adicionar constante `_CORRECTIONS_CONFIG_PATH` seguindo o mesmo padrão de `_ARTIFACT_MAP_PATH` em `validate_summary.py`.
  3. [ ] Implementar `_load_corrections_config() -> dict` que lê APENAS `corrections_config.artifacts` do YAML. Retorna `{}` em qualquer erro (fail-safe — sem propagação de exceção).
  4. [ ] Confirmar que o dict `ARTIFACT_MAP` existente (linha 226) **não foi modificado** — é out-of-scope (§8 Exclusions do plan.md).

---

### P0-c — `build_summary_comprehensive.py`: Loop de retry genérico (§4.1)

- [ ] **P0-c**
  - **Arquivo**: `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py`
  - **Spec ref**: §4.1
  - **Plano ref**: plan.md §8 P0-c
  - **BDD**: Spec §5 Scenarios 1.1 (alias resolvido), 1.2 (idempotência), 1.3 (fail-safe), 6.1 (log completo).
  - **Depende de**: P0-b
  - **Paralelo**: não

  **Passos**:
  1. [ ] Implementar `_apply_retry_loop(artifact_key, parser_fn, outputs_dir, log_entries) -> tuple[result, str|None, str|None]` retornando `(result, alternative_used, artifact_map_rule)`.
  2. [ ] Implementar os 4 steps de §4.1 na ordem:
     - STEP 1: executar parser primário — se não-vazio, retornar imediatamente (sem entrada no log).
     - STEP 2: tentar cada `path_aliases[]` em ordem — primeiro arquivo existente em disco ganha → resolve + log entry.
     - STEP 3: tentar cada `alternatives[]` — primeiro não-vazio ganha → resolve + log entry.
     - STEP 4: todos esgotados → emitir finding `parser_gap` + log entry `outcome: failed`.
  3. [ ] Substituir os três blocos ad-hoc de fallback por chamadas a `_apply_retry_loop()`:
     - `parse_inventory_bc_breakdown()` L826–830
     - `_parse_nuget_packages()` L4728–4738
     - `_parse_iac_resources()` L5720–5726 (atenção: `iac` usa `alternatives[]` com `candidate_roots`, não `path_aliases[]`)
  4. [ ] Confirmar que STEP 2 e STEP 3 são read-only em relação a `outputs/` — nenhuma escrita intermediária.

---

### P0-d — `build_summary_comprehensive.py`: Writer de `builder-correction-log.json` (§3.1a)

- [ ] **P0-d**
  - **Arquivo**: `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py`
  - **Spec ref**: §3.1a, §4.1
  - **Plano ref**: plan.md §8 P0-d
  - **BDD**: Spec §5 Scenario 6.1 (N correções → N entradas), Scenario 6.3 (zero correções → arquivo existe com `total_attempted:0`).
  - **Depende de**: P0-c
  - **Paralelo**: não

  **Passos**:
  1. [ ] Adicionar `import uuid`.
  2. [ ] Em `build_summary_html()`: gerar `build_run_id = str(uuid.uuid4())` no início.
  3. [ ] Manter lista `_builder_correction_log: list[dict]` ao longo do build — cada chamada a `_apply_retry_loop()` appenda quando uma correção é tentada.
  4. [ ] Escrever `builder-correction-log.json` em `projects/{project_name}/outputs/summary/` ao fim de `build_summary_html()` — sempre (overwrite, nunca append).
  5. [ ] Garantir escrita mesmo quando `corrections_applied == []` (garantia always-on).
  6. [ ] Calcular: `total_attempted = len(corrections_applied)`, `resolved = count('resolved')`, `failed = count('failed')`.
  7. [ ] Quando `--section` ativo: NÃO escrever o log (runs section-only não são builds completos).
  8. [ ] Quando `--dry-run` ativo sem `--section`: NÃO escrever nenhum arquivo, incluindo o log.
  9. [ ] Validar schema contra data-model.md §1.

---

### P0-e — `build_summary_comprehensive.py`: Ativação do flag `auto_correctable` (§4.6)

- [ ] **P0-e**
  - **Arquivo**: `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py`
  - **Spec ref**: §4.6
  - **Plano ref**: plan.md §8 P0-e
  - **BDD**: Spec §5 Scenario 1.1 (implícito — `auto_correctable=true` quando alias existe em disco).
  - **Depende de**: P0-c
  - **Paralelo**: não

  **Passos**:
  1. [ ] Quando o builder emite finding `missing_artifact`, definir `auto_correctable = True` SE E SOMENTE SE: a chave do artefato existe em `corrections_config.artifacts` E pelo menos um alias em `path_aliases[]` resolve para arquivo existente em disco no momento da emissão do finding.
  2. [ ] Quando `auto_correctable` não pode ser determinado (chave ausente, sem aliases, aliases inexistentes em disco): definir `auto_correctable = False` (fail-safe — comportamento pré-043 inalterado).
  3. [ ] Confirmar: o builder é o ÚNICO componente que define `auto_correctable`. O `validate_summary.py` apenas propaga — NÃO recalcula (boundary spec §1).

---

### P0-f — `build_summary_comprehensive.py`: Flags CLI `--section`, `--dry-run`, `--artifact` (§9)

- [ ] **P0-f**
  - **Arquivo**: `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py`
  - **Spec ref**: §9 (Assumption — flag não existe, deve ser adicionada)
  - **Plano ref**: plan.md §8 P0-f
  - **BDD**: Quickstart Scenario G (`--section` flag → JSON output com `section_key`).
  - **Depende de**: nenhuma P0 anterior (independente de P0-c/d/e)
  - **Paralelo**: não (mas pode ser desenvolvida em paralelo com P0-d/P0-e se necessário — não há dependência de código, apenas de teste: P0-g exige P0-f pronto)

  **Passos**:
  1. [ ] Adicionar ao bloco `argparse`:
     - `--section KEY`: roda apenas o parser de KEY; output para stdout (JSON); sem escrita de HTML.
     - `--dry-run`: executa build completo mas suprime todas as escritas de arquivo.
     - `--artifact PATH`: usar junto com `--section` apenas; passa path já resolvido diretamente, bypassando `_apply_retry_loop()`.
  2. [ ] Em `main()`: passar `args.section`, `args.dry_run`, `args.artifact` para `build_summary_html()`.
  3. [ ] Validar: se `args.artifact` definido e `args.section` é None → exit 2.
  4. [ ] Quando `--section` ativo:
     - Carregar `corrections_config.artifacts[key]`; exit 2 se key não encontrada.
     - Se `--artifact` fornecido: usar path diretamente (skip `_apply_retry_loop()`); exit non-zero se path inexistente.
     - Caso contrário: executar `_apply_retry_loop(key, ...)`.
     - Print JSON para stdout per `contracts/builder-cli-contract.md`.
     - Exit 0 em resolved, 1 em failed.
     - NÃO escrever HTML nem `builder-correction-log.json`.
  5. [ ] Quando `--dry-run` sem `--section`: rodar todos os parsers normalmente, suprimir todas as escritas ao fim.
  6. [ ] Confirmar compatibilidade retroativa: zero callers existentes passam `--section` (research R-01 confirmado).

---

### P0-g — `remediate_summary.py`: Ciclo scan→regenerate→validate (§4.3)

- [ ] **P0-g**
  - **Arquivo**: `src/modules/ava-fabric-agents/summary/utils/remediate_summary.py`
  - **Spec ref**: §4.3
  - **Plano ref**: plan.md §8 P0-g
  - **BDD**: Spec §5 Scenario 3.1 (regeneração resolve gap), Scenario 3.2 (rollback em regressão), Scenario 3.3 (idempotência — 2ª run `total_attempted:0`).
  - **Depende de**: P0-f (remediação invoca o builder via flags `--section`/`--artifact`), P0-e boundary (builder já define `auto_correctable`)
  - **Paralelo**: não

  **Passos**:
  1. [ ] Substituir o `continue` na linha 908 (que skipava findings `auto_correctable=True`) pelo ciclo §4.3:
     - **STEP 1**: Ler `deep-audit-report.json`; filtrar findings `parser_gap`/`missing_artifact` com `artifact_path is not None`.
     - **STEP 2**: Para cada finding, verificar se artefato existe em `f.artifact_path` OU qualquer alias em `corrections_config` (`resolved_path` = path que resolveu):
       - Se não encontrado em nenhum lugar: `outcome: failed`, `html_regenerated: false`, `html_section_repopulated: false`; preservar finding; continue.
       - Se encontrado: verificar HTML atual para `f.d_field`:
         - SE `f.auto_correctable == True` E seção HTML de `f.d_field` está **não-vazia** (alias já foi usado na última build — finding é stale): → suprimir finding de `validation-report.json`; log `outcome: suppressed`, `html_regenerated: false`; continue (SEM regeneração).
         - SENÃO (seção vazia ou `auto_correctable == false` — regeneração necessária): → invocar `build_summary_comprehensive.py --project <name> --section=<f.d_field> --artifact=<resolved_path> --dry-run --skip-mermaid-gate`; se exit 0 e stdout não-vazio: commit (marcar para rebuild completo), `auto_correctable: true`, log `outcome: resolved`, `html_regenerated: true`; senão: preservar finding, log `outcome: failed`.
     - **STEP 3**: Se qualquer `html_regenerated: true`: executar build completo, re-validar; se nova CRITICAL/HIGH: rollback HTML, `outcome: failed`, `notes: "regression detected"`.
     - **STEP 4**: Escrever `remediation-correction-log.json` (P0-h).
  2. [ ] Atualizar comentário obsoleto na linha 908 para refletir o novo comportamento.
  3. [ ] Confirmar: `MAX_REMEDIATION_ATTEMPTS` aplica-se ao loop EXTERNO — o ciclo §4.3 é uma única passagem atômica sem retry interno.
  4. [ ] Toda supressão de findings de `validation-report.json` acontece AQUI e apenas aqui (boundary spec §1).
  5. [ ] Usar `--artifact <resolved_path>` (não apenas `--section`) ao invocar o builder — evita segundo pass do retry-loop interno.

---

### P0-h — `remediate_summary.py`: Writer de `remediation-correction-log.json` (§3.1b)

- [ ] **P0-h**
  - **Arquivo**: `src/modules/ava-fabric-agents/summary/utils/remediate_summary.py`
  - **Spec ref**: §3.1b
  - **Plano ref**: plan.md §8 P0-h
  - **BDD**: Spec §5 Scenario 3.3 (2ª run `total_attempted:0`), Scenario 6.2 (N_r + N_s entradas).
  - **Depende de**: P0-g
  - **Paralelo**: não

  **Passos**:
  1. [ ] Ao fim do ciclo §4.3 (P0-g STEP 4): escrever `remediation-correction-log.json` em `projects/{project_name}/outputs/summary/` (overwrite, nunca append).
  2. [ ] Gerar `remediation_run_id = str(uuid.uuid4())`.
  3. [ ] Calcular: `total_attempted = len(corrections_applied)`, `resolved = count('resolved')`, `suppressed = count('suppressed')`, `failed = count('failed')`.
  4. [ ] Schema per data-model.md §2.
  5. [ ] Confirmar discriminador de `outcome`: `suppressed` SOMENTE quando artefato encontrado E seção HTML não-vazia em scan time (finding stale). `html_regenerated` DEVE ser `false` quando `outcome == "suppressed"` e `true` quando `outcome == "resolved"` (VR-09, data-model.md §5).

---

### P0-i — `remediate_summary.py`: Dynamic Self-Correction Loop (§4.7) ⚠️

- [ ] **P0-i**
  - **Arquivos**: `src/modules/ava-fabric-agents/summary/utils/remediate_summary.py`, `src/modules/ava-fabric-agents/summary/agents/summary-remediation-agent.md`
  - **Spec ref**: §4.7 (novo), Q4
  - **Plano ref**: plan.md §8 P0-i, §9 Complexity Tracking
  - **BDD**: Spec §5 Scenario 7.1 (máx 5 tentativas distintas), 7.2 (sucesso para loop + 1 entrada no log), 7.3 (todas falham → rollback + log apenas da última tentativa), 7.4 (invocação de tool/agente permitida). Quickstart Scenarios H1 e H2.
  - **Depende de**: P0-g (trigger point: STEP 2 resolveria para `outcome: failed`), P0-h (log writer)
  - **Paralelo**: não
  - ⚠️ **Alta incerteza de esforço** — diferente das demais P0 (Python determinístico), depende de interface com agente Copilot conectado. Mecanismo exato de invocação TBD (ver plan.md Complexity Tracking: *"exact agent-invocation interface TBD at implementation time"*).

  **Sub-itens obrigatórios**:
  1. [ ] **Mecanismo de trigger**: quando STEP 2 do ciclo P0-g resolveria para `outcome: failed` (artefato não encontrado via nenhum alias OU dry-run falhou), invocar o Dynamic Self-Correction Loop ao invés de escrever imediatamente a entrada `failed`.
  2. [ ] **Orchestration wrapper**: implementar o loop como wrapper de orquestração limitado — cada iteração delega ao agente Copilot conectado para propor UMA ação corretiva, dado: (a) detalhes do finding (`d_field`, `artifact_path`, `finding_type`), (b) lista de abordagens já tentadas e falhadas nesta instância do loop (em memória, por instância — não persistir em disco até terminação).
  3. [ ] **Regra de abordagem distinta**: rejeitar/skip qualquer abordagem proposta que duplique uma já tentada nessa mesma instância do loop; exigir abordagem materialmente diferente.
  4. [ ] **Limite de 5 tentativas**: atualizar `MAX_REMEDIATION_ATTEMPTS` para `5`, governando especificamente este loop (spec §9 Assumption). Após cada tentativa: invocar builder → re-validar.
     - Se validação mostra zero novas CRITICAL/HIGH e seção populada: SUCESSO — parar loop imediatamente. Escrever exatamente UMA entrada no `remediation-correction-log.json`: `outcome: resolved`, `notes` descrevendo abordagem bem-sucedida + `attempt_number`.
     - Se validação mostra regressão ou seção vazia: rollback para estado pré-tentativa; incrementar contador; continuar com próxima tentativa (distinta) se contador < 5.
  5. [ ] **Log terminal-only**: se contador chega a 5 sem sucesso → rollback final para estado HTML pré-loop. Escrever exatamente UMA entrada: `outcome: failed`, `notes` descrevendo APENAS a 5ª (última) abordagem — NÃO logar tentativas 1–4 individualmente.
  6. [ ] **Seam de teste**: implementar mecanismo de mock (ex.: env var `AVA_LOOP_MOCK_SUCCESS_AT`) para permitir validação determinística em Scenarios H1/H2 do quickstart.md sem depender de reasoning real do agente.
  7. [ ] **Agent body (Portuguese)**: atualizar `summary-remediation-agent.md` (ver também P1-d) com seção dedicada em PT-BR descrevendo as regras operacionais do loop:
     - Quando acionar o loop dinâmico (§4.1/§4.3 esgotaram opções estáticas).
     - Regra de "abordagem distinta" (nunca repetir tentativa já feita nesta execução).
     - Limite rígido de 5 tentativas.
     - Regra de log (uma entrada única: vencedora OU apenas a última se todas falharem).
     - Permissão explícita de acionar outras ferramentas/agentes DURANTE o loop (exceção pontual — spec §8).
     - Comportamento de rollback seguro ao fim das 5 tentativas.
  8. [ ] **Exceção de dispatch**: confirmar que P0-c e P0-g permanecem estritamente self-contained — apenas P0-i tem acesso a invocação de agentes upstream (spec §8).
  9. [ ] **Vincular aos testes de mock**: plan.md §10 ("dynamic loop bounded + early success") + quickstart.md Scenarios H1/H2.

---

## Bloco P1 — Qualidade (não bloqueantes para P0, mas obrigatórios para ship)

> P1-a e P1-b são paralelizáveis entre si [P]. P1-c, P1-d, P1-e devem ser as últimas antes das Transversais.

---

### P1-a — `validate_summary.py`: DEBUG log para supressão estrutural (§4.4) [P]

- [ ] **P1-a**
  - **Arquivo**: `src/modules/ava-fabric-agents/summary/utils/validate_summary.py`
  - **Spec ref**: §4.4
  - **Plano ref**: plan.md §8 P1-a
  - **BDD**: Spec §5 Scenario 4.1 (nenhum finding emitido + entrada de DEBUG log).
  - **Depende de**: P0-c (retry loop já existente)
  - **Paralelo**: [P] pode rodar em paralelo com P1-b
  - **Observação**: supressão em `_classify_empty_element()` L3377 já existe (research R-04) — apenas o DEBUG log está faltando.

  **Passos**:
  1. [ ] Adicionar `import logging` no topo do arquivo (verificar se já presente).
  2. [ ] Inserir ANTES do `return None` existente na linha 3377:
     ```python
     logging.debug(
         "C12.6/C12.7 structural suppression: element has no id= and no heading ancestor "
         "(element type: %s). Suppressing to avoid false-positive. "
         "Spec 043 §4.4.",
         "table" if "tbody" in element_html.lower() else "list"
     )
     ```
  3. [ ] Confirmar: `return None` existente permanece inalterado. O log de DEBUG NÃO aparece em `deep-audit-report.json` (spec §4.4 explícito).
  4. [ ] Branch heading-present (heading is not None): INALTERADA — comportamento existente preservado (spec §8 Exclusions).

---

### P1-b — `artifact-map.yaml` + `build_summary_comprehensive.py`: Deduplicação de stub (§4.5) [P]

- [ ] **P1-b**
  - **Arquivos**: `src/modules/ava-fabric-agents/summary/data/artifact-map.yaml`, `src/modules/ava-fabric-agents/summary/utils/build_summary_comprehensive.py`
  - **Spec ref**: §4.5
  - **Plano ref**: plan.md §8 P1-b
  - **BDD**: Spec §5 Scenario 5.1 (stub substituído por dados reais), Scenario 5.2 (2ª passagem do parser é no-op).
  - **Depende de**: P0-c (retry loop)
  - **Paralelo**: [P] pode rodar em paralelo com P1-a

  **Passos**:
  1. [ ] Verificar que `default_empty_value: []` está definido para as três entradas baseline em `corrections_config.artifacts` (feito em P0-a).
  2. [ ] Implementar `_write_section_data(D, section_key, real_data, corrections_config_entry)` em `build_summary_comprehensive.py`:
     - Se `D[section_key] == default_empty_value` → substituir pelo dado real.
     - Se `D[section_key] is not None` e `!= default_empty_value` → DEBUG log "já populado; skip" (idempotente).
     - Caso contrário → primeira escrita normal.
  3. [ ] Substituir atribuições bare `D[section_key] = parser_result` dentro do retry loop (P0-c) por chamadas a `_write_section_data()`.
  4. [ ] Confirmar: detecção de stub SOMENTE por `== default_empty_value`. NENHUMA sentinel string como `"__STUB__"` (spec §4.5 constraint explícito).

---

### P1-c — `summary-validate-agent.md`: Bump para v1.7.0

- [ ] **P1-c**
  - **Arquivo**: `src/modules/ava-fabric-agents/summary/agents/summary-validate-agent.md`
  - **Spec ref**: §2.1, §1
  - **Plano ref**: plan.md §8 P1-c
  - **BDD**: N/A (mudança de metadados)
  - **Depende de**: todo comportamento P0 e P1 implementado (description deve refletir a realidade)
  - **Paralelo**: não

  **Passos**:
  1. [ ] Substituir `version: "1.6.0"` por `version: "1.7.0"`.
  2. [ ] Substituir bloco `description` pelo texto de spec §2.1 (Portuguese — inclui descrição de propagação de `auto_correctable`).
  3. [ ] `allowed-tools`: inalterado (`Read, Bash, Glob, Grep, Write`).
  4. [ ] Corpo do agente (instruções em PT-BR): atualizar referência de versão de 1.6.0 para 1.7.0; adicionar parágrafo descrevendo comportamento de propagação de `auto_correctable` per §1.

---

### P1-d — `summary-remediation-agent.md`: Bump para v1.8.0

- [ ] **P1-d**
  - **Arquivo**: `src/modules/ava-fabric-agents/summary/agents/summary-remediation-agent.md`
  - **Spec ref**: §2.2, §1, §4.7
  - **Plano ref**: plan.md §8 P1-d
  - **BDD**: N/A (mudança de metadados) — mas corpo §4.7 é crítico para runtime do Dynamic Loop (não é apenas cosmético).
  - **Depende de**: P1-c (após validate-agent atualizado, por ordem de coerência), P0-i (corpo do loop deve ser completo e correto antes do bump)
  - **Paralelo**: não

  **Passos**:
  1. [ ] Substituir `version: "1.7.0"` por `version: "1.8.0"`.
  2. [ ] Substituir bloco `description` pelo texto de spec §2.2 (Portuguese — inclui ciclo §4.3 E capacidade do loop dinâmico §4.7).
  3. [ ] `allowed-tools`: inalterado (`Read, Write, Edit, Glob, Grep, Bash`).
  4. [ ] Corpo do agente: atualizar referência de versão; adicionar seção descrevendo o ciclo scan→regenerate, os dois logs e o comportamento de rollback.
  5. [ ] **NOVA seção PT-BR obrigatória** (instruction set runtime para §4.7):
     - Quando acionar o loop dinâmico.
     - Regra de abordagem distinta (nunca repetir tentativa já feita nesta execução).
     - Limite de 5 tentativas substituindo `MAX_REMEDIATION_ATTEMPTS` anterior.
     - Regra de log terminal-only (uma entrada por finding).
     - Permissão explícita de acionar ferramentas/agentes durante o loop (exceção pontual).
     - Comportamento de rollback seguro.

---

### P1-e — `module.yaml`: Bump para v1.7.0

- [ ] **P1-e**
  - **Arquivo**: `src/modules/ava-fabric-agents/summary/module.yaml`
  - **Spec ref**: §1 (version bumps)
  - **Plano ref**: plan.md §8 P1-e
  - **BDD**: N/A (mudança de metadados)
  - **Depende de**: P1-d (última tarefa antes das Transversais)
  - **Paralelo**: não

  **Passos**:
  1. [ ] Substituir `version: "1.6.0"` por `version: "1.7.0"`. Nenhuma outra alteração.

---

## Bloco T — Tarefas Transversais (gates de fechamento de branch)

> Somente após TODAS as P0 e P1 concluídas. A feature branch só pode ser fechada quando T-a, T-b e T-c passarem — incluindo Scenarios H1/H2 (Patch 11) como extensão obrigatória de T-a/T-b para cobrir o Dynamic Self-Correction Loop.

---

### T-a — Teste de idempotência

- [ ] **T-a**
  - **Spec ref**: §4.1 (garantia de idempotência), §10 (critérios de sucesso)
  - **Plano ref**: plan.md §8 T-a
  - **BDD**: Spec §5 Scenario 1.2, Scenario 3.3. **Extensão obrigatória**: Quickstart Scenario B + Scenarios H1/H2 (Dynamic Loop).
  - **Depende de**: todas as P0 e P1 concluídas
  - **Definition of Done**: quickstart.md Scenario B passa + Scenarios H1/H2 passam.

  **Passos**:
  1. [ ] Executar builder 2× sobre o mesmo estado de `outputs/`. Comparar HTML com `Get-FileHash`. Confirmar que 2º `builder-correction-log.json` tem `total_attempted:0`.
  2. [ ] Executar remediação 2× sobre o mesmo estado. Confirmar que 2º `remediation-correction-log.json` tem `total_attempted:0`.
  3. [ ] Executar Scenario H1 (quickstart.md): loop para na tentativa 3; exatamente 1 entrada no log; `outcome: resolved`.
  4. [ ] Executar Scenario H2 (quickstart.md): 1 entrada no log após 5 tentativas falhadas; HTML rollback byte-identical; `outcome: failed`.

---

### T-b — Teste negativo fail-safe

- [ ] **T-b**
  - **Spec ref**: §4.1 STEP 4, §10 (critérios de sucesso)
  - **Plano ref**: plan.md §8 T-b
  - **BDD**: Spec §5 Scenario 1.3. **Extensão obrigatória**: Quickstart Scenario C + Scenario H2 (todos os 5 falham).
  - **Depende de**: T-a concluído
  - **Definition of Done**: quickstart.md Scenario C passa + Scenario H2 passa.

  **Passos**:
  1. [ ] Remover TODOS os aliases e alternatives do disco (não do YAML). Executar builder.
  2. [ ] Verificar finding `parser_gap` emitido inalterado.
  3. [ ] Verificar `builder-correction-log.json` com `outcome: failed` e `alternative_used: null`.
  4. [ ] Executar quickstart.md Scenario C para confirmação formal.

---

### T-c — Teste de não-regressão

- [ ] **T-c**
  - **Spec ref**: §4.3 STEP 3, §10 (critérios de sucesso)
  - **Plano ref**: plan.md §8 T-c
  - **BDD**: §10 "No regressions". **Definition of Done**: quickstart.md Non-Regression Check passa.
  - **Depende de**: T-b concluído
  - **Definition of Done**: quickstart.md Non-Regression Check passa (zero novas CRITICAL/HIGH).

  **Passos**:
  1. [ ] Executar `validate_summary.py` sobre estado de projeto conhecido-bom ANTES de Feature 043.
  2. [ ] Aplicar Feature 043. Executar `validate_summary.py` novamente.
  3. [ ] Diff de `validation-report.json` counts CRITICAL/HIGH. Zero novas findings devem aparecer.
  4. [ ] Documentar em `CHANGELOG.md`.

---

## Referências cruzadas

| Documento | Seções relevantes |
|---|---|
| `spec.md` | §1 (boundaries), §2.1/§2.2 (frontmatter), §3.1a/§3.1b (schemas), §4.1–§4.7 (comportamentos), §5 (BDD), §8 (exclusions), §9 (assumptions) |
| `plan.md` | §4 (files changed), §5 (module.yaml), §6 (observability), §7 (schemas), §8 (implementation tasks), §9 (complexity tracking), §10 (test strategy) |
| `data-model.md` | §1 (builder-correction-log schema), §2 (remediation-correction-log schema), §3 (field constraints), §4 (corrections_config YAML baseline), §5 (validation rules VR-01–VR-09) |
| `contracts/builder-cli-contract.md` | `--section`, `--artifact`, `--dry-run` contract |
| `quickstart.md` | Scenarios A–H + Non-Regression Check |
