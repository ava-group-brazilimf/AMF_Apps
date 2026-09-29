"""Testes da F5 (DevOps Execute) — manifesto fechado + laço Ralph Wiggum.

Motivação concreta e medida em produção::

    BadRequestError: Error code: 400 — invalid_request_error
    prompt is too long: 3924457 tokens > 1000000 maximum

A F5 declarava ``outputs/tobe/source-code`` — um DIRETÓRIO — como insumo
obrigatório. ``context_manifest._expand()`` expande diretório com ``rglob("*")``
e ``_resolve_declared()`` injeta o corpo de cada arquivo: com a F4 concluída,
isso é a aplicação inteira no prompt.

O que estes testes congelam:

* os insumos da F5 são exatamente três ARQUIVOS, nenhum diretório;
* ``outputs/tobe/source-code`` não é carregado — nem pelo manifesto, nem pelo
  payload que chega ao modelo;
* o laço sobre ``task-devops-progress.json`` respeita dependências, tentativas,
  limite global de iterações e ausência de progresso;
* ``prompt is too long`` reduz o contexto em vez de repetir o mesmo request;
* nenhuma outra fase ou agente muda de caminho.

Roda com o Python do repo::

    python -m pytest tests/tools/test_devops_ralph_loop.py -q
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_19 = REPO_ROOT / "ava-pipeline-runner-cli.py"
TOOLS = REPO_ROOT / "src" / "shared" / "tools"

sys.path.insert(0, str(TOOLS))

import devops_task_ledger as ledger      # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def runner():
    """O runner de produção, importado uma vez por módulo."""
    if not RUNNER_19.is_file():
        pytest.skip("ava-pipeline-runner-cli.py ausente neste checkout")
    spec = importlib.util.spec_from_file_location("runner19_sob_teste", RUNNER_19)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["runner19_sob_teste"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


DEVOPS_PLAN = """# Plano de DevOps

## Estratégia de IaC e infraestrutura
Terraform como ferramenta de infra, com sizing derivado do blueprint.

## Pipeline de CI
Build, teste e análise estática a cada push.

## Pipeline de CD
Deploy por ambiente, com validação pós-deploy.

## Containerização dos serviços
Docker para backend e frontend, compose por ambiente.

## Provisionamento na cloud Azure
Bicep + Terraform para os recursos gerenciados.

## Estimativa de custo mensal
Custo por ambiente, com teto aprovado.

## Observabilidade e monitoramento
Alertas, dashboards e health checks por serviço.

## Comparação de versões e paridade funcional
Relatório de paridade entre legado e TO-BE.

## Pacote de aprovação de release
Consolidação por wave.

## Estratégia de backup e disaster recovery
RPO de 1h, RTO de 4h.
"""

ENVIRONMENTS_PLAN = """# Plano de Ambientes

## Ambiente de desenvolvimento
Deploy contínuo a cada merge.

## Ambiente de homologação
Gate manual antes do deploy.

## Ambiente de produção
Janela de release semanal, rollback automatizado.
"""

PROJECT_CONFIG = """project_name: P
cloud_provider: azure
pipeline_mode: standard
legacy_technology: dotnet
"""


def _monta_projeto(raiz: Path, *, com_source_code: bool = True) -> Path:
    """Projeto de teste com os planos e — de propósito — um source-code gordo."""
    proj = raiz / "projects" / "P"
    (proj / "context").mkdir(parents=True, exist_ok=True)
    (proj / "context" / "project-config.yaml").write_text(PROJECT_CONFIG, encoding="utf-8")
    (proj / "context" / "shared-context.md").write_text(
        "PROSA-COMPARTILHADA-QUE-NAO-DEVE-ENTRAR\n" * 200, encoding="utf-8")

    devops = proj / "outputs" / "tobe" / "devops"
    devops.mkdir(parents=True, exist_ok=True)
    (devops / "devops-plan.md").write_text(DEVOPS_PLAN, encoding="utf-8")
    (devops / "environments-plan.md").write_text(ENVIRONMENTS_PLAN, encoding="utf-8")

    docs = proj / "outputs" / "tobe" / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "architecture-blueprint.md").write_text(
        "BLUEPRINT-QUE-NAO-DEVE-ENTRAR\n" * 500, encoding="utf-8")

    if com_source_code:
        for lado in ("backend", "frontend"):
            alvo = proj / "outputs" / "tobe" / "source-code" / lado
            alvo.mkdir(parents=True, exist_ok=True)
            for i in range(30):
                (alvo / f"Arquivo{i}.cs").write_text(
                    "CODIGO-FONTE-QUE-NAO-DEVE-ENTRAR " * 400, encoding="utf-8")
            (alvo / "package-lock.json").write_text(
                json.dumps({"deps": ["CODIGO-FONTE-QUE-NAO-DEVE-ENTRAR"] * 5000}),
                encoding="utf-8")
    return proj


def _planos() -> dict[str, str]:
    return {
        ledger.PLAN_INPUTS[0]: PROJECT_CONFIG,
        ledger.PLAN_INPUTS[1]: DEVOPS_PLAN,
        ledger.PLAN_INPUTS[2]: ENVIRONMENTS_PLAN,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  1–3 · Configuração dos insumos da F5
# ═══════════════════════════════════════════════════════════════════════════

def test_inputs_da_f5_sao_exatamente_os_tres_declarados(runner):
    passo = next(s for s in runner.PIPELINE if s["phase"] == "F5")
    caminhos = [i["path"] for i in passo["inputs"]["mandatory"]]
    assert caminhos == [
        "context/project-config.yaml",
        "outputs/tobe/devops/devops-plan.md",
        "outputs/tobe/devops/environments-plan.md",
    ]
    assert passo["inputs"].get("advisory") in (None, [])
    # `floor: []` é o que tira context/shared-context.md do piso do manifesto.
    assert passo["inputs"]["floor"] == []


def test_source_code_e_os_demais_proibidos_sumiram_dos_inputs(runner):
    passo = next(s for s in runner.PIPELINE if s["phase"] == "F5")
    declarados = [i["path"] for i in passo["inputs"]["mandatory"]]
    for proibido in runner.F5_DEVOPS_FORBIDDEN:
        assert not any(c == proibido or c.startswith(proibido + "/")
                       for c in declarados), f"{proibido} voltou aos inputs da F5"


def test_caminhos_usam_barra_e_nao_geram_escape_acidental(runner):
    """`"outputs\\tobe\\..."` num literal Python viraria TAB — o teste que pega isso."""
    for caminho in runner.F5_DEVOPS_INPUT_PATHS + runner.F5_DEVOPS_FORBIDDEN:
        assert "\\" not in caminho
        assert "\t" not in caminho
        assert "/" in caminho
    for caminho in ledger.PLAN_INPUTS + (ledger.PROGRESS_REL, ledger.DEVOPS_DIR_REL):
        assert "\\" not in caminho and "\t" not in caminho


def test_ava_pipeline_yaml_nao_declara_mais_o_diretorio_de_codigo():
    """A fonte de dados também precisa estar limpa, não só o override do runner."""
    yaml = pytest.importorskip("yaml")
    cfg = yaml.safe_load(
        (REPO_ROOT / "src" / "shared" / "data" / "ava-pipeline.yaml").read_text(
            encoding="utf-8"))
    passos = cfg["pipeline"]["steps"] if "pipeline" in cfg else cfg["steps"]
    f5 = next(s for s in passos if s.get("phase") == "F5")
    caminhos = [i["path"] if isinstance(i, dict) else i
                for i in (f5.get("inputs") or {}).get("mandatory") or []]
    assert "outputs/tobe/source-code" not in caminhos


def test_guard_recusa_diretorio_declarado(runner, tmp_path, monkeypatch):
    _monta_projeto(tmp_path)
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)
    passo = {"phase": "F5", "agent": "ava-devops-orchestrator", "trigger": "DE",
             "inputs": {"mandatory": [{"path": "outputs/tobe/source-code"},
                                      {"path": "outputs/tobe/devops/devops-plan.md"}]}}
    recusados = runner._assert_no_directory_inputs("P", passo)
    assert recusados == ["outputs/tobe/source-code"]


def test_manifesto_fechado_nao_expande_nenhum_diretorio(runner, tmp_path, monkeypatch):
    _monta_projeto(tmp_path)
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)
    passo = next(s for s in runner.PIPELINE if s["phase"] == "F5")
    assert runner._assert_no_directory_inputs("P", passo) == []


# ═══════════════════════════════════════════════════════════════════════════
#  4–5 · Criação e retomada do arquivo de progresso
# ═══════════════════════════════════════════════════════════════════════════

def test_criacao_inicial_do_task_devops_progress(tmp_path):
    _monta_projeto(tmp_path)
    progresso, novos = ledger.load_or_create("P", _planos(), repo_root=tmp_path)

    caminho = ledger.progress_path("P", tmp_path)
    assert caminho.is_file()
    assert caminho.as_posix().endswith("outputs/tobe/devops/task-devops-progress.json")
    assert progresso["tasks"] and novos
    em_disco = json.loads(caminho.read_text(encoding="utf-8"))
    assert em_disco["phase"] == "F5"
    assert em_disco["agent"] == "ava-devops-orchestrator"
    assert em_disco["trigger"] == "DE"


def test_toda_tarefa_tem_o_contrato_minimo(tmp_path):
    _monta_projeto(tmp_path)
    progresso, _ = ledger.load_or_create("P", _planos(), repo_root=tmp_path)
    obrigatorios = {"id", "title", "description", "source_plan", "dependencies",
                    "status", "attempts", "max_attempts", "started_at",
                    "completed_at", "result", "error", "output_artifacts"}
    for tarefa in progresso["tasks"]:
        assert obrigatorios <= set(tarefa), f"{tarefa['id']} sem campos do contrato"
        assert tarefa["status"] in ledger.STATUSES
        assert tarefa["max_attempts"] == ledger.MAX_ATTEMPTS


def test_tarefas_sao_derivadas_dos_planos(tmp_path):
    """Uma seção que só existe no plano deste projeto vira tarefa própria."""
    _monta_projeto(tmp_path)
    progresso, _ = ledger.load_or_create("P", _planos(), repo_root=tmp_path)
    titulos = " | ".join(t["title"] for t in progresso["tasks"]).casefold()
    assert "backup" in titulos            # veio de um cabeçalho do devops-plan
    assert all(t["source_plan"].startswith("outputs/tobe/devops/")
               or t["source_plan"].endswith(".md")
               for t in progresso["tasks"])


def test_retomada_preserva_completed_e_nao_duplica(tmp_path):
    _monta_projeto(tmp_path)
    progresso, _ = ledger.load_or_create("P", _planos(), repo_root=tmp_path)
    alvo = progresso["tasks"][0]
    ledger.mark_completed(alvo, "feito", ["outputs/tobe/iac/main.tf"])
    ledger.save_progress(ledger.progress_path("P", tmp_path), progresso)

    de_novo, novos = ledger.load_or_create("P", _planos(), repo_root=tmp_path)
    ids = [t["id"] for t in de_novo["tasks"]]
    assert len(ids) == len(set(ids)), "tarefa duplicada na retomada"
    assert novos == []
    preservada = next(t for t in de_novo["tasks"] if t["id"] == alvo["id"])
    assert preservada["status"] == ledger.STATUS_COMPLETED
    assert preservada["output_artifacts"] == ["outputs/tobe/iac/main.tf"]


def test_retomada_reabre_in_progress_de_run_interrompido(tmp_path):
    _monta_projeto(tmp_path)
    progresso, _ = ledger.load_or_create("P", _planos(), repo_root=tmp_path)
    ledger.mark_in_progress(progresso["tasks"][0])
    ledger.save_progress(ledger.progress_path("P", tmp_path), progresso)

    de_novo, _ = ledger.load_or_create("P", _planos(), repo_root=tmp_path)
    assert de_novo["tasks"][0]["status"] == ledger.STATUS_PENDING


def test_planos_novos_acrescentam_tarefas_sem_apagar_historico(tmp_path):
    _monta_projeto(tmp_path)
    planos = _planos()
    progresso, _ = ledger.load_or_create("P", planos, repo_root=tmp_path)
    ledger.mark_completed(progresso["tasks"][0], "ok", [])
    ledger.save_progress(ledger.progress_path("P", tmp_path), progresso)

    planos[ledger.PLAN_INPUTS[1]] += "\n## Rede e gateway de aplicação\nWAF na borda.\n"
    de_novo, novos = ledger.load_or_create("P", planos, repo_root=tmp_path)
    assert novos, "seção nova do plano não virou tarefa"
    assert de_novo["tasks"][0]["status"] == ledger.STATUS_COMPLETED


# ═══════════════════════════════════════════════════════════════════════════
#  6–7 · Dependências
# ═══════════════════════════════════════════════════════════════════════════

def _progresso_sintetico(tarefas: list[dict]) -> dict:
    return {"schema_version": ledger.SCHEMA_VERSION, "project": "P",
            "tasks": tarefas, "iterations": 0}


def test_execucao_respeita_a_ordem_de_dependencia():
    a = ledger.new_task("DEVOPS-001", "A", "", source_plan="p.md")
    b = ledger.new_task("DEVOPS-002", "B", "", source_plan="p.md",
                        dependencies=["DEVOPS-001"])
    prog = _progresso_sintetico([a, b])

    assert ledger.select_next_task(prog)["id"] == "DEVOPS-001"
    ledger.mark_in_progress(a)
    ledger.mark_completed(a, "ok", ["x"])
    assert ledger.select_next_task(prog)["id"] == "DEVOPS-002"


def test_dependencia_pulada_nao_impede_a_sucessora():
    a = ledger.new_task("DEVOPS-001", "A", "", source_plan="p.md")
    ledger.mark_skipped(a, "fora do escopo dos planos")
    b = ledger.new_task("DEVOPS-002", "B", "", source_plan="p.md",
                        dependencies=["DEVOPS-001"])
    assert ledger.select_next_task(_progresso_sintetico([a, b]))["id"] == "DEVOPS-002"


def test_dependencia_definitivamente_falha_bloqueia_a_sucessora():
    a = ledger.new_task("DEVOPS-001", "A", "", source_plan="p.md")
    a["attempts"] = ledger.MAX_ATTEMPTS
    ledger.mark_failed(a, error_type="Boom", message="estourou")
    b = ledger.new_task("DEVOPS-002", "B", "", source_plan="p.md",
                        dependencies=["DEVOPS-001"])
    prog = _progresso_sintetico([a, b])

    assert ledger.select_next_task(prog) is None
    bloqueados = ledger.mark_blocked_tasks(prog)
    assert bloqueados == ["DEVOPS-002"]
    assert b["status"] == ledger.STATUS_BLOCKED
    assert b["error"]["recoverable"] is False


def test_completed_nunca_e_reexecutada():
    a = ledger.new_task("DEVOPS-001", "A", "", source_plan="p.md")
    ledger.mark_completed(a, "ok", ["x"])
    assert ledger.select_next_task(_progresso_sintetico([a])) is None


# ═══════════════════════════════════════════════════════════════════════════
#  8–10 · Transições e tentativas
# ═══════════════════════════════════════════════════════════════════════════

def test_status_apos_sucesso():
    t = ledger.new_task("DEVOPS-001", "A", "", source_plan="p.md")
    ledger.mark_in_progress(t)
    assert t["status"] == ledger.STATUS_IN_PROGRESS and t["attempts"] == 1
    assert t["started_at"]

    ledger.mark_completed(t, "gerou 2 artefatos", ["a.tf", "b.tf"])
    assert t["status"] == ledger.STATUS_COMPLETED
    assert t["result"] == {"success": True, "summary": "gerou 2 artefatos"}
    assert t["error"] is None
    assert t["output_artifacts"] == ["a.tf", "b.tf"]
    assert t["completed_at"]


def test_status_apos_falha():
    t = ledger.new_task("DEVOPS-001", "A", "", source_plan="p.md")
    ledger.mark_in_progress(t)
    ledger.mark_failed(t, error_type="TimeoutError", message="sem resposta")
    assert t["status"] == ledger.STATUS_FAILED
    assert t["result"]["success"] is False
    assert t["error"] == {"type": "TimeoutError", "message": "sem resposta",
                          "recoverable": True}


def test_max_attempts_bloqueia_em_vez_de_retentar_para_sempre():
    t = ledger.new_task("DEVOPS-001", "A", "", source_plan="p.md")
    for _ in range(ledger.MAX_ATTEMPTS):
        ledger.mark_in_progress(t)
        ledger.mark_failed(t, error_type="Boom", message="x")
    assert t["attempts"] == ledger.MAX_ATTEMPTS
    assert t["status"] == ledger.STATUS_BLOCKED
    assert ledger.is_retryable(t) is False
    assert ledger.select_next_task(_progresso_sintetico([t])) is None


# ═══════════════════════════════════════════════════════════════════════════
#  11–13 · Assinatura, escrita atômica
# ═══════════════════════════════════════════════════════════════════════════

def test_assinatura_muda_com_o_estado_e_repete_sem_mudanca():
    t = ledger.new_task("DEVOPS-001", "A", "", source_plan="p.md")
    prog = _progresso_sintetico([t])
    antes = ledger.progress_signature(prog)
    assert ledger.progress_signature(prog) == antes      # idempotente

    ledger.mark_in_progress(t)
    assert ledger.progress_signature(prog) != antes


def test_escrita_atomica_valida_json_e_nao_deixa_tmp(tmp_path):
    alvo = tmp_path / "sub" / "task-devops-progress.json"
    ledger.atomic_write_json(alvo, {"a": 1})
    assert json.loads(alvo.read_text(encoding="utf-8")) == {"a": 1}
    assert list(alvo.parent.glob("*.tmp")) == []

    # Sobrescrever mantém o arquivo válido do começo ao fim.
    ledger.atomic_write_json(alvo, {"a": 2, "tasks": []})
    assert json.loads(alvo.read_text(encoding="utf-8"))["a"] == 2
    assert list(alvo.parent.glob("*.tmp")) == []


def test_escrita_atomica_recusa_payload_nao_serializavel(tmp_path):
    alvo = tmp_path / "p.json"
    ledger.atomic_write_json(alvo, {"ok": 1})
    with pytest.raises(TypeError):
        ledger.atomic_write_json(alvo, {"ruim": object()})
    # O arquivo anterior continua íntegro — nada foi substituído por lixo.
    assert json.loads(alvo.read_text(encoding="utf-8")) == {"ok": 1}
    assert list(alvo.parent.glob("*.tmp")) == []


def test_nenhum_segredo_e_persistido():
    t = ledger.new_task("DEVOPS-001", "A", "", source_plan="p.md")
    ledger.mark_in_progress(t)
    ledger.mark_failed(
        t, error_type="AuthError",
        message=("falha em Server=db;Password=Sup3rS3cr3t;  "
                 "api_key: sk-abcdef1234567890  "
                 "Authorization: Bearer eyJhbGciOi.JzdWIiOiIx.Ttk3sQ"),
        summary="password=hunter2")
    persistido = json.dumps(t, ensure_ascii=False)
    for segredo in ("Sup3rS3cr3t", "sk-abcdef1234567890", "hunter2",
                    "eyJhbGciOi.JzdWIiOiIx.Ttk3sQ"):
        assert segredo not in persistido, f"segredo vazou: {segredo}"
    assert "REDACTED" in persistido


# ═══════════════════════════════════════════════════════════════════════════
#  14–15 · Orçamento de contexto e prompt is too long
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("mensagem", [
    "prompt is too long: 3924457 tokens > 1000000 maximum",
    "This model's maximum context length is 128000 tokens",
    "context length exceeded",
    "input tokens exceed the configured limit",
    "Request too large for model",
])
def test_erros_de_excesso_de_contexto_sao_reconhecidos(mensagem):
    assert ledger.is_context_limit_error(RuntimeError(mensagem)) is True


def test_erro_transitorio_nao_e_confundido_com_excesso_de_contexto():
    assert ledger.is_context_limit_error(RuntimeError("connection reset")) is False


def test_orcamento_reserva_margem_abaixo_do_limite():
    orcamento = ledger.context_budget_tokens(1_000_000, 128_000)
    assert orcamento < 1_000_000 - 128_000, "o limite máximo está sendo usado inteiro"
    assert orcamento == int(1_000_000 * ledger.CTX_INPUT_SAFETY) - 128_000 - \
        ledger.CTX_RESERVE_TOKENS


def test_enforce_recusa_antes_de_enviar():
    grande = "x" * 5_000_000
    with pytest.raises(ledger.ContextBudgetExceeded) as exc:
        ledger.enforce_context_budget(grande, window=1_000_000, out_tokens=32_000,
                                      label="F5/DEVOPS-001")
    assert exc.value.estimated > exc.value.budget


def test_estimativa_e_conservadora():
    """4 chars/token é otimista para YAML e código — a estimativa usa 3."""
    assert ledger.CHARS_PER_TOKEN <= 3
    assert ledger.estimate_tokens("a" * 300) == 100


def test_extracao_dirigida_reduz_o_plano():
    tarefa = ledger.new_task("DEVOPS-002", "CI — pipeline de integração contínua",
                             "", source_plan="p.md")
    plano = DEVOPS_PLAN * 60                       # ~60KB
    trecho = ledger.plan_excerpt(tarefa, plano, limit=4_000)
    assert len(trecho) <= 4_200
    assert len(trecho) < len(plano)


def test_request_digest_distingue_contextos():
    a = ledger.request_digest("sys", "user")
    assert a == ledger.request_digest("sys", "user")
    assert a != ledger.request_digest("sys reduzido", "user")


# ═══════════════════════════════════════════════════════════════════════════
#  Validação de artefatos
# ═══════════════════════════════════════════════════════════════════════════

def test_tarefa_sem_artefato_nao_e_dada_por_concluida():
    t = ledger.new_task("DEVOPS-001", "A", "", source_plan="p.md",
                        output_globs=["outputs/tobe/iac/**"])
    ok, _, motivo = ledger.validate_task_artifacts(t, [], "P")
    assert ok is False and "nenhum artefato" in motivo


def test_artefato_fora_do_caminho_esperado_reprova():
    t = ledger.new_task("DEVOPS-001", "A", "", source_plan="p.md",
                        output_globs=["outputs/tobe/iac/**"])
    ok, _, motivo = ledger.validate_task_artifacts(
        t, ["projects/P/outputs/tobe/qa/x.md"], "P")
    assert ok is False and "fora dos caminhos esperados" in motivo


def test_artefato_no_caminho_esperado_aprova():
    t = ledger.new_task("DEVOPS-001", "A", "", source_plan="p.md",
                        output_globs=["outputs/tobe/iac/**"])
    ok, casados, _ = ledger.validate_task_artifacts(
        t, ["projects/P/outputs/tobe/iac/main.tf"], "P")
    assert ok is True and casados == ["outputs/tobe/iac/main.tf"]


# ═══════════════════════════════════════════════════════════════════════════
#  16–18 · Laço completo dentro do runner
# ═══════════════════════════════════════════════════════════════════════════

def _artefato_para(glob: str) -> str:
    caminho = glob.replace("/**", "/gerado.txt").replace("*", "1")
    return caminho


class _DispatchFalso:
    """Substitui `_dispatch_model`. Guarda todo prompt enviado, para inspeção."""

    def __init__(self, runner, tmp_path, *, comportamento=None):
        self.runner = runner
        self.tmp_path = tmp_path
        self.prompts: list[tuple[str, str]] = []
        self.comportamento = comportamento or (lambda tid, n: "ok")

    def __call__(self, client, *, system_prompt, user_prompt, out_tokens, phase,
                 ts_start, stream_guard, inp_tokens_estimate=0,
                 enforce_budget=False, budget_label=""):
        self.prompts.append((system_prompt, user_prompt))
        tid = user_prompt.rsplit("task:", 1)[1].strip()
        n = sum(1 for _, u in self.prompts if u.endswith(tid))
        acao = self.comportamento(tid, n)
        if isinstance(acao, Exception):
            raise acao
        if acao == "vazio":
            return "sem blocos FILE aqui", "end_turn", 100, 50

        progresso = json.loads(
            (self.tmp_path / "projects" / "P" / ledger.PROGRESS_REL)
            .read_text(encoding="utf-8"))
        tarefa = next(t for t in progresso["tasks"] if t["id"] == tid)
        globs = tarefa.get("output_globs") or ["outputs/tobe/devops/**"]
        rel = _artefato_para(globs[0])
        corpo = (f"<!-- FILE: projects/P/{rel} -->\n"
                 f"conteudo de {tid}\n"
                 f"<!-- /FILE -->\n")
        return corpo, "end_turn", 1_000, 200


@pytest.fixture
def loop_pronto(runner, tmp_path, monkeypatch):
    """Runner apontado para um projeto de teste, com o modelo substituído."""
    _monta_projeto(tmp_path)
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)
    monkeypatch.setattr(runner, "load_skill",
                        lambda agent, spec_path=None: f"# skill de {agent}\n")
    monkeypatch.setattr(runner, "status_heartbeat",
                        lambda *a, **k: None)
    passo = {"phase": "F5", "agent": "ava-devops-orchestrator", "trigger": "DE",
             "label": "DevOps Execute", "inputs": runner._f5_devops_inputs()}
    saida = tmp_path / "projects" / "P" / "outputs" / "pipeline_runner"
    saida.mkdir(parents=True, exist_ok=True)
    return runner, passo, saida, tmp_path, monkeypatch


def test_laco_executa_ate_o_fim_e_persiste_cada_transicao(loop_pronto):
    runner, passo, saida, tmp_path, monkeypatch = loop_pronto
    falso = _DispatchFalso(runner, tmp_path)
    monkeypatch.setattr(runner, "_dispatch_model", falso)

    metricas = runner._run_devops_execute_step(
        object(), passo, "P", saida, skill_content="skill",
        out_tokens=128_000, esperados=[], headroom_active=False)

    progresso = json.loads(
        (tmp_path / "projects" / "P" / ledger.PROGRESS_REL).read_text(encoding="utf-8"))
    executadas = [t for t in progresso["tasks"]
                  if t["status"] == ledger.STATUS_COMPLETED]

    assert executadas, "nenhuma tarefa concluída"
    assert all(t["completed_at"] and t["result"]["success"] and t["output_artifacts"]
               for t in executadas)
    assert metricas["val_ok"] is True
    assert metricas["devops_iterations"] == len(falso.prompts)
    assert metricas["artifacts"] == len(executadas)
    assert progresso["iterations"] == metricas["devops_iterations"]
    # Cada tarefa foi despachada UMA vez: `completed` não é reexecutada.
    ids = [u.rsplit("task:", 1)[1].strip() for _, u in falso.prompts]
    assert len(ids) == len(set(ids))


def test_payload_nao_contem_diretorio_nem_codigo_fonte(loop_pronto):
    """O critério de aceite central: nada de source-code no que vai ao modelo."""
    runner, passo, saida, tmp_path, monkeypatch = loop_pronto
    falso = _DispatchFalso(runner, tmp_path)
    monkeypatch.setattr(runner, "_dispatch_model", falso)

    runner._run_devops_execute_step(
        object(), passo, "P", saida, skill_content="skill",
        out_tokens=128_000, esperados=[], headroom_active=False)

    assert falso.prompts, "nenhum despacho aconteceu"
    for system_prompt, _ in falso.prompts:
        assert "CODIGO-FONTE-QUE-NAO-DEVE-ENTRAR" not in system_prompt
        assert "BLUEPRINT-QUE-NAO-DEVE-ENTRAR" not in system_prompt
        assert "PROSA-COMPARTILHADA-QUE-NAO-DEVE-ENTRAR" not in system_prompt
        # E cada chamada é pequena — a antiga estourava 1M tokens.
        assert ledger.estimate_tokens(system_prompt) < 200_000


def test_contexto_de_uma_tarefa_nao_carrega_a_resposta_da_anterior(loop_pronto):
    runner, passo, saida, tmp_path, monkeypatch = loop_pronto
    falso = _DispatchFalso(runner, tmp_path)
    monkeypatch.setattr(runner, "_dispatch_model", falso)

    runner._run_devops_execute_step(
        object(), passo, "P", saida, skill_content="skill",
        out_tokens=128_000, esperados=[], headroom_active=False)

    primeiro_id = falso.prompts[0][1].rsplit("task:", 1)[1].strip()
    for system_prompt, user_prompt in falso.prompts[1:]:
        assert f"conteudo de {primeiro_id}" not in system_prompt


def test_prompt_is_too_long_reduz_contexto_e_nao_repete_o_request(loop_pronto):
    runner, passo, saida, tmp_path, monkeypatch = loop_pronto

    def comportamento(tid, n):
        # A primeira tarefa estoura sempre; as demais passam.
        if tid == "DEVOPS-001":
            return RuntimeError("prompt is too long: 3924457 tokens > 1000000 maximum")
        return "ok"

    falso = _DispatchFalso(runner, tmp_path, comportamento=comportamento)
    monkeypatch.setattr(runner, "_dispatch_model", falso)

    metricas = runner._run_devops_execute_step(
        object(), passo, "P", saida, skill_content="skill",
        out_tokens=128_000, esperados=[], headroom_active=False)

    progresso = json.loads(
        (tmp_path / "projects" / "P" / ledger.PROGRESS_REL).read_text(encoding="utf-8"))
    falha = next(t for t in progresso["tasks"] if t["id"] == "DEVOPS-001")

    assert falha["status"] in (ledger.STATUS_FAILED, ledger.STATUS_BLOCKED)
    assert falha["error"]["type"] == "ContextLimitError"
    assert "REDACTED" not in falha["error"]["message"]
    assert falha["attempts"] <= falha["max_attempts"]
    assert falha["context_level"] >= 1, "o contexto não foi reduzido para a retentativa"

    # Nenhum request de DEVOPS-001 foi repetido byte a byte.
    enviados = [s for s, u in falso.prompts if u.endswith("DEVOPS-001")]
    assert len(enviados) == len(set(enviados)), "o mesmo request que falhou foi reenviado"
    # E a fase não morreu: reprova de forma controlada.
    assert metricas["val_ok"] is False
    assert "DEVOPS-001" in metricas["detail"]


class _ClienteQueNaoDeveSerChamado:
    """Qualquer toque em `messages.stream` reprova o teste."""

    def __init__(self):
        self.chamadas = 0
        cliente = self

        class _Messages:
            def stream(self, **kwargs):
                cliente.chamadas += 1
                raise AssertionError("messages.stream foi chamado com o prompt "
                                     "fora do orçamento de contexto")

        self.messages = _Messages()
        self.base_url = "https://exemplo.invalid"
        self.api_key = "x"


def test_dispatch_recusa_o_envio_antes_de_messages_stream(runner, monkeypatch):
    """O controle de tamanho roda ANTES de `client.messages.stream`."""
    monkeypatch.setattr(runner, "PROVIDER", "anthropic")
    monkeypatch.setattr(runner, "status_heartbeat", lambda *a, **k: None)
    cliente = _ClienteQueNaoDeveSerChamado()
    import datetime as _dt

    with pytest.raises(ledger.ContextBudgetExceeded):
        runner._dispatch_model(
            cliente, system_prompt="S" * 5_000_000, user_prompt="u",
            out_tokens=32_000, phase="F5", ts_start=_dt.datetime.now(),
            stream_guard=runner._StreamFloodGuard(),
            enforce_budget=True, budget_label="F5/DEVOPS-001")

    assert cliente.chamadas == 0, "um prompt fora do orçamento chegou ao modelo"


def test_dispatch_das_demais_fases_apenas_avisa_e_envia(runner, monkeypatch, capsys):
    """Não-regressão: fase existente fora do orçamento continua sendo enviada."""
    monkeypatch.setattr(runner, "PROVIDER", "anthropic")
    monkeypatch.setattr(runner, "status_heartbeat", lambda *a, **k: None)
    cliente = _ClienteQueNaoDeveSerChamado()
    import datetime as _dt

    with pytest.raises(AssertionError, match="messages.stream foi chamado"):
        runner._dispatch_model(
            cliente, system_prompt="S" * 5_000_000, user_prompt="u",
            out_tokens=32_000, phase="F4", ts_start=_dt.datetime.now(),
            stream_guard=runner._StreamFloodGuard())

    assert "CTX-BUDGET" in capsys.readouterr().out


def test_laco_reprova_a_fase_quando_nenhum_contexto_cabe(loop_pronto):
    """Contexto irredutível: a fase reprova sem despachar e sem explodir."""
    runner, passo, saida, tmp_path, monkeypatch = loop_pronto
    monkeypatch.setattr(runner, "load_skill",
                        lambda agent, spec_path=None: "S" * 4_000_000)
    monkeypatch.setattr(ledger, "MAX_ITERATIONS", 4)
    chamadas: list[str] = []

    def registra(client, *, system_prompt, user_prompt, **kw):
        chamadas.append(user_prompt)
        return "", "end_turn", 0, 0

    monkeypatch.setattr(runner, "_dispatch_model", registra)

    metricas = runner._run_devops_execute_step(
        object(), passo, "P", saida, skill_content="skill",
        out_tokens=128_000, esperados=[], headroom_active=False)

    assert chamadas == [], "um prompt fora do orçamento chegou ao modelo"
    assert metricas["val_ok"] is False


def test_limite_global_de_iteracoes_interrompe_o_laco(loop_pronto):
    runner, passo, saida, tmp_path, monkeypatch = loop_pronto
    monkeypatch.setattr(ledger, "MAX_ITERATIONS", 2)
    falso = _DispatchFalso(runner, tmp_path)
    monkeypatch.setattr(runner, "_dispatch_model", falso)

    metricas = runner._run_devops_execute_step(
        object(), passo, "P", saida, skill_content="skill",
        out_tokens=128_000, esperados=[], headroom_active=False)

    assert metricas["devops_iterations"] == 2
    assert len(falso.prompts) == 2


def test_ausencia_de_progresso_interrompe_o_laco(loop_pronto, monkeypatch):
    """Se o estado não muda entre duas iterações, o laço para em vez de girar."""
    runner, passo, saida, tmp_path, mp = loop_pronto
    falso = _DispatchFalso(runner, tmp_path)
    mp.setattr(runner, "_dispatch_model", falso)

    # A razão já existe em disco; a partir daqui nenhuma transição é gravada.
    # É o cenário patológico que o guard existe para cortar: o laço recarrega o
    # arquivo, encontra exatamente o mesmo estado da iteração anterior e para,
    # em vez de despachar a mesma tarefa até o teto global.
    ledger.load_or_create("P", _planos(), repo_root=tmp_path)
    mp.setattr(ledger, "save_progress", lambda caminho, progresso: caminho)

    metricas = runner._run_devops_execute_step(
        object(), passo, "P", saida, skill_content="skill",
        out_tokens=128_000, esperados=[], headroom_active=False)

    assert metricas["devops_iterations"] == 1
    assert len(falso.prompts) == 1
    assert "progresso" in metricas["devops_termination"]


def test_falha_da_f5_nao_levanta_e_permite_continuidade_no_modo_full(loop_pronto):
    """Requisito do modo full: a fase reprova, mas devolve — não explode."""
    runner, passo, saida, tmp_path, monkeypatch = loop_pronto
    falso = _DispatchFalso(runner, tmp_path,
                           comportamento=lambda tid, n: RuntimeError("boom"))
    monkeypatch.setattr(runner, "_dispatch_model", falso)

    metricas = runner._run_devops_execute_step(
        object(), passo, "P", saida, skill_content="skill",
        out_tokens=128_000, esperados=[], headroom_active=False)

    assert metricas["val_ok"] is False
    assert metricas["detail"]
    assert metricas["phase"] == "F5" and metricas["agent"] == "ava-devops-orchestrator"
    # Métricas preservadas: o laço principal usa estas chaves.
    for chave in ("inp_tokens", "out_max", "resp_tokens", "ctx_pct", "elapsed_s",
                  "artifacts", "artifacts_written", "started_ts", "ended_ts",
                  "contract_ok", "contract_total", "contract_missing"):
        assert chave in metricas, f"métrica existente removida: {chave}"


def test_metricas_por_tarefa_sao_coletadas(loop_pronto):
    runner, passo, saida, tmp_path, monkeypatch = loop_pronto
    monkeypatch.setattr(runner, "_dispatch_model", _DispatchFalso(runner, tmp_path))

    metricas = runner._run_devops_execute_step(
        object(), passo, "P", saida, skill_content="skill",
        out_tokens=128_000, esperados=[], headroom_active=False)

    assert metricas["devops_task_metrics"]
    primeira = metricas["devops_task_metrics"][0]
    for chave in ("phase", "agent", "task_id", "task_status", "attempt",
                  "start_time", "end_time", "duration_s", "input_files",
                  "output_artifacts", "error_type", "error_message",
                  "continuation_action", "estimated_input_tokens"):
        assert chave in primeira, f"métrica de tarefa ausente: {chave}"
    assert primeira["input_files"] == list(runner.F5_DEVOPS_INPUT_PATHS)
    # O dict inteiro precisa sobreviver à serialização de métricas do runner.
    json.dumps(runner._serialize_metrics(metricas), ensure_ascii=False)


def test_log_da_fase_e_gravado(loop_pronto):
    runner, passo, saida, tmp_path, monkeypatch = loop_pronto
    monkeypatch.setattr(runner, "_dispatch_model", _DispatchFalso(runner, tmp_path))

    runner._run_devops_execute_step(
        object(), passo, "P", saida, skill_content="skill",
        out_tokens=128_000, esperados=[], headroom_active=False)

    logs = list(saida.glob("F5_*.md"))
    assert logs, "log da fase não foi gravado"
    texto = logs[0].read_text(encoding="utf-8")
    assert "task-devops-progress.json" in texto
    assert "CODIGO-FONTE-QUE-NAO-DEVE-ENTRAR" not in texto


# ═══════════════════════════════════════════════════════════════════════════
#  Não-regressão das demais fases e agentes
# ═══════════════════════════════════════════════════════════════════════════

def test_apenas_a_tripla_f5_devops_de_entra_no_laco(runner):
    assert runner._is_f5_devops_step(
        {"phase": "F5", "agent": "ava-devops-orchestrator", "trigger": "DE"}) is True
    # Mesmo agente, outro momento: o planejamento (F2b/DP) segue no caminho comum.
    assert runner._is_f5_devops_step(
        {"phase": "F2b", "agent": "ava-devops-orchestrator", "trigger": "DP"}) is False
    assert runner._is_f5_devops_step(
        {"phase": "F5", "agent": "ava-devops-orchestrator", "trigger": "DP"}) is False
    assert runner._is_f5_devops_step(
        {"phase": "F5", "agent": "ava-qa-orchestrator", "trigger": "DE"}) is False
    assert runner._is_f5_devops_step(None) is False


def test_demais_passos_mantem_o_manifesto_declarado(runner):
    """O override da F5 não pode ter tocado no manifesto de ninguém mais."""
    f2a = next(s for s in runner.PIPELINE if s["phase"] == "F2a")
    caminhos = [i["path"] if isinstance(i, dict) else i
                for i in f2a["inputs"]["mandatory"]]
    assert "outputs/asis/architecture-blueprint.md" in caminhos

    f6 = next(s for s in runner.PIPELINE if s["phase"] == "F6")
    assert f6["inputs"].get("mandatory"), "F6 perdeu o manifesto"
    # A F6 recebeu o mesmo tratamento da F5 (piso enxuto + tier `exists`); o
    # detalhe dela é congelado em tests/tools/test_qa_ralph_loop.py.
    assert f6["inputs"]["floor"] == ["context/project-config.yaml"]

    f2a = next(s for s in runner.PIPELINE if s["phase"] == "F2a")
    assert "floor" not in f2a["inputs"], "F2a não deveria ter piso customizado"


def test_piso_padrao_do_context_manifest_segue_intacto():
    import context_manifest as cm
    assert cm._PROJECT_FLOOR == ("context/project-config.yaml",
                                 "context/shared-context.md")
    assert cm._floor_names(None) == cm._PROJECT_FLOOR
    assert cm._floor_names({"mandatory": ["a.md"]}) == cm._PROJECT_FLOOR
    assert cm._floor_names({"floor": []}) == ()
    assert cm._floor_names({"floor": ["context/project-config.yaml"]}) == \
        ("context/project-config.yaml",)


def test_floor_vazio_tira_o_shared_context_do_contexto(tmp_path):
    import context_manifest as cm
    _monta_projeto(tmp_path, com_source_code=False)
    cfg = {"context": {"file_chars": 100_000, "declared_body_chars": 100_000,
                       "declared_total_chars": 1_000_000},
           "execution": {"output_subdir": "outputs/pipeline_runner"}}
    entradas = {"floor": [],
                "mandatory": ["context/project-config.yaml",
                              "outputs/tobe/devops/devops-plan.md"]}
    res = cm.resolve("P", entradas, cfg, repo_root=tmp_path)
    texto = cm.render(res)
    assert res.blocked is False
    assert "PROSA-COMPARTILHADA-QUE-NAO-DEVE-ENTRAR" not in texto
    assert "Plano de DevOps" in texto
    # project-config entra UMA vez só, mesmo sendo piso e declarado.
    assert texto.count("cloud_provider: azure") == 1
