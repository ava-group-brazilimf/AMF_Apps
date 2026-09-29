"""Testes da F6 (QA Execute) — manifesto fechado, agregação de avisos e laço.

Motivação concreta e medida em produção::

    BadRequestError: Error code: 400 — invalid_request_error
    prompt is too long: 3958957 tokens > 1000000 maximum

A F6 declarava ``outputs/tobe/source-code`` — um DIRETÓRIO com 40.468 arquivos
no ``meu-erp-03``. Havia **dois** amplificadores:

1. a expansão injetava corpos até esgotar os 2 MB de orçamento;
2. esgotado o orçamento, ``context_manifest`` anexava **um aviso por arquivo
   recusado** — 40.097 linhas / 7,5 MB, 3,8× mais que os corpos protegidos.

O que estes testes congelam:

* recusas são agregadas por motivo, com teto próprio de caracteres;
* diretório de build (`bin/`, `obj/`, `node_modules/`) nunca entra na expansão;
* o tier ``exists`` confere presença sem injetar conteúdo;
* só DBI, CT e FT recebem código, e por glob estreito;
* o laço respeita dependências, tentativas, ciclos, teto de iterações e
  ausência de progresso, e continua após falha não bloqueante.

Roda com o Python do repo::

    python -m pytest tests/tools/test_qa_ralph_loop.py -q
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

import context_manifest as cm      # noqa: E402
import qa_task_ledger as ledger    # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def runner():
    if not RUNNER_19.is_file():
        pytest.skip("ava-pipeline-runner-cli.py ausente neste checkout")
    spec = importlib.util.spec_from_file_location("runner19_qa_sob_teste", RUNNER_19)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["runner19_qa_sob_teste"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


MARCA_CODIGO = "CODIGO-FONTE-QUE-NAO-DEVE-ENTRAR"
MARCA_PROSA = "PROSA-COMPARTILHADA-QUE-NAO-DEVE-ENTRAR"
MARCA_BUILD = "ARTEFATO-DE-BUILD-QUE-NAO-DEVE-ENTRAR"

PROJECT_CONFIG = "project_name: P\nlegacy_technology: dotnet\nbackend_port: 5099\n"
BCM = "# Bounded Context Map\n\n## BC-01 Vendas\nEscopo.\n\n## BC-02 Estoque\nEscopo.\n"
TEST_PLAN = ("# Plano de Testes TO-BE\n\n## Escopo\nCobertura por bounded context.\n"
             "## Critérios de entrada e saída\nDefinidos.\n")
TEST_CASES = "# Casos de Teste\n\n## TC-001\nPassos.\n\n## TC-002\nPassos.\n"
FTM = "# Matriz Funcional\n\n| RF | BC | Cenário |\n|---|---|---|\n| RF-01 | BC-01 | x |\n"


def _monta_projeto(raiz: Path, *, com_codigo: bool = True,
                   com_frontend: bool = True, arquivos_build: int = 0) -> Path:
    proj = raiz / "projects" / "P"
    (proj / "context").mkdir(parents=True, exist_ok=True)
    (proj / "context" / "project-config.yaml").write_text(PROJECT_CONFIG, encoding="utf-8")
    (proj / "context" / "shared-context.md").write_text(
        MARCA_PROSA + "\n" * 5 + (MARCA_PROSA + "\n") * 200, encoding="utf-8")

    docs = proj / "outputs" / "tobe" / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "bounded-context-map.md").write_text(BCM, encoding="utf-8")
    (docs / "openapi").mkdir(exist_ok=True)
    (docs / "openapi" / "vendas.yaml").write_text("openapi: 3.0.0\n", encoding="utf-8")

    qa = proj / "outputs" / "tobe" / "qa"
    qa.mkdir(parents=True, exist_ok=True)
    (qa / "test-plan.md").write_text(TEST_PLAN, encoding="utf-8")
    (qa / "test-cases.md").write_text(TEST_CASES, encoding="utf-8")
    (qa / "functional-test-matrix.md").write_text(FTM, encoding="utf-8")

    asis = proj / "outputs" / "asis" / "docs"
    asis.mkdir(parents=True, exist_ok=True)
    (asis / "business-rules.json").write_text('{"rules": []}', encoding="utf-8")
    (asis / "behavior-catalog.json").write_text('{"behaviors": []}', encoding="utf-8")
    (asis / "schema-inventory.md").write_text("# Schema\n", encoding="utf-8")

    # F5 concluída (Passo 4 do gate)
    devops = proj / "outputs" / "tobe" / "devops"
    devops.mkdir(parents=True, exist_ok=True)
    (devops / "task-devops-progress.json").write_text('{"tasks": []}', encoding="utf-8")

    if com_codigo:
        sc = proj / "outputs" / "tobe" / "source-code"
        sc.mkdir(parents=True, exist_ok=True)
        (sc / "README.md").write_text("# Source code gerado pela F4\n", encoding="utf-8")

        backend = sc / "backend" / "src" / "Vendas"
        (backend / "Controllers").mkdir(parents=True, exist_ok=True)
        (backend / "Migrations").mkdir(parents=True, exist_ok=True)
        (backend / "Controllers" / "VendasController.cs").write_text(
            "public class VendasController {}\n", encoding="utf-8")
        (backend / "Migrations" / "20260101_Init.cs").write_text(
            "public partial class Init {}\n", encoding="utf-8")
        for i in range(20):
            (backend / f"Servico{i}.cs").write_text(
                MARCA_CODIGO + " " * 4 + "x" * 500, encoding="utf-8")

        if com_frontend:
            fe = sc / "frontend" / "src" / "app"
            fe.mkdir(parents=True, exist_ok=True)
            (fe / "vendas.component.ts").write_text(
                "export class VendasComponent {}\n", encoding="utf-8")
            for i in range(10):
                (fe / f"util{i}.ts").write_text(MARCA_CODIGO + "\n" * 20,
                                                encoding="utf-8")

        for i in range(arquivos_build):
            destino = sc / "backend" / ("node_modules" if i % 2 else "bin") / f"p{i}"
            destino.mkdir(parents=True, exist_ok=True)
            (destino / f"f{i}.js").write_text(MARCA_BUILD * 40, encoding="utf-8")
    return proj


def _cfg(**over):
    ctx = {"file_chars": 500_000, "declared_body_chars": 50_000,
           "declared_total_chars": 200_000}
    ctx.update(over)
    return {"context": ctx, "execution": {"output_subdir": "outputs/pipeline_runner"}}


# ═══════════════════════════════════════════════════════════════════════════
#  1–5 · Agregação de avisos em context_manifest (correção global)
# ═══════════════════════════════════════════════════════════════════════════

def test_milhares_de_recusas_nao_geram_milhares_de_linhas(tmp_path):
    """O defeito exato: 40.097 avisos, 7,5 MB, dentro do prompt."""
    base = tmp_path / "projects" / "P" / "outputs" / "grande"
    base.mkdir(parents=True)
    for i in range(3_000):
        (base / f"a{i:05d}.md").write_text("x" * 500, encoding="utf-8")

    res = cm.resolve("P", {"mandatory": ["outputs/grande"]},
                     _cfg(declared_total_chars=20_000), repo_root=tmp_path)
    bloco = cm.render_warnings(res)

    assert res.skipped_counts[cm._R_BUDGET] > 2_000
    # A amostra por motivo é o teto — não uma linha por arquivo.
    assert len(res.warnings) <= 6 * len(res.skipped_counts) + 4
    assert len(bloco) <= cm._WARN_CHARS_MAX
    assert "3.000" in bloco or "2." in bloco          # o total aparece agregado
    texto = cm.render(res)
    assert texto.count("orçamento de contexto esgotado") < 20


def test_resumo_traz_censo_por_categoria(tmp_path):
    base = tmp_path / "projects" / "P" / "outputs" / "mix"
    base.mkdir(parents=True)
    for i in range(40):
        (base / f"doc{i}.md").write_text("y" * 2_000, encoding="utf-8")
    (base / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    res = cm.resolve("P", {"mandatory": ["outputs/mix"]},
                     _cfg(declared_total_chars=10_000), repo_root=tmp_path)
    censo = cm.context_census(res)

    assert censo["files_discovered"] == 41
    assert censo["files_considered"] == 41
    assert censo["files_injected"] >= 1
    assert censo["files_skipped"] >= 1
    assert cm._R_BINARY in res.skipped_counts
    assert cm._R_BUDGET in res.skipped_counts
    bloco = cm.render_warnings(res)
    assert "descobertos" in bloco and "ignorados" in bloco


def test_teto_de_warnings_e_independente_do_orcamento_de_corpos(tmp_path):
    base = tmp_path / "projects" / "P" / "outputs" / "muitos"
    base.mkdir(parents=True)
    for i in range(1_500):
        (base / f"n{i:05d}.md").write_text("z" * 200, encoding="utf-8")

    res = cm.resolve("P", {"mandatory": ["outputs/muitos"]},
                     _cfg(declared_total_chars=5_000), repo_root=tmp_path)
    censo = cm.context_census(res)

    assert censo["body_chars"] <= 5_000
    assert censo["warning_chars"] <= cm._WARN_CHARS_MAX
    # O prompt inteiro não pode ser dominado pela contabilidade das recusas.
    assert censo["warning_chars"] < censo["total_chars"]


def test_diretorio_de_build_nunca_entra_na_expansao(tmp_path):
    _monta_projeto(tmp_path, arquivos_build=200)
    res = cm.resolve("P", {"mandatory": ["outputs/tobe/source-code"]},
                     _cfg(), repo_root=tmp_path)
    texto = cm.render(res)

    assert MARCA_BUILD not in texto
    assert res.skipped_counts.get(cm._R_BUILD, 0) >= 200
    assert not any("node_modules" in i.rel or "/bin/" in i.rel for i in res.included)


def test_glob_explicito_nao_e_filtrado_por_build(tmp_path):
    """Quem escreve o glob decide o escopo — o filtro é só da expansão de dir."""
    _monta_projeto(tmp_path, arquivos_build=4)
    res = cm.resolve("P", {"advisory": ["outputs/tobe/source-code/backend/bin/*/*.js"]},
                     _cfg(), repo_root=tmp_path)
    assert res.included, "glob explícito foi filtrado indevidamente"


# ═══════════════════════════════════════════════════════════════════════════
#  6 · Tier `exists` — verificação sem leitura
# ═══════════════════════════════════════════════════════════════════════════

def test_exists_confere_sem_injetar_conteudo(tmp_path):
    _monta_projeto(tmp_path, arquivos_build=50)
    res = cm.resolve("P", {"floor": [], "exists": list(ledger.PRECONDITION_EXISTS)},
                     _cfg(), repo_root=tmp_path)
    texto = cm.render(res)

    assert res.blocked is False
    assert res.included == [], "o tier `exists` injetou corpo"
    assert len(res.verified) == 3
    assert MARCA_CODIGO not in texto
    assert MARCA_BUILD not in texto
    assert "outputs/tobe/source-code/backend/**" in texto


def test_exists_reprova_diretorio_vazio(tmp_path):
    _monta_projeto(tmp_path, com_frontend=False)
    (tmp_path / "projects" / "P" / "outputs" / "tobe" / "source-code"
     / "frontend").mkdir(parents=True, exist_ok=True)

    res = cm.resolve("P", {"floor": [], "exists": list(ledger.PRECONDITION_EXISTS)},
                     _cfg(), repo_root=tmp_path)
    assert res.blocked is True
    assert any("frontend" in m.pattern for m in res.missing_mandatory)


def test_exists_reprova_diretorio_so_com_build(tmp_path):
    """Pasta cheia de `bin/` não é código gerado — é lixo de compilação."""
    _monta_projeto(tmp_path, com_frontend=False)
    fe = tmp_path / "projects/P/outputs/tobe/source-code/frontend/node_modules/x"
    fe.mkdir(parents=True)
    (fe / "a.js").write_text("dep", encoding="utf-8")

    res = cm.resolve("P", {"floor": [], "exists": ["outputs/tobe/source-code/frontend/**"]},
                     _cfg(), repo_root=tmp_path)
    assert res.blocked is True


# ═══════════════════════════════════════════════════════════════════════════
#  7–9 · Globs estreitos por sub-agente
# ═══════════════════════════════════════════════════════════════════════════

def test_apenas_tres_tarefas_declaram_codigo():
    com_codigo = [t["id"] for t in ledger.TASK_BACKBONE if t.get("sourceCodeGlobs")]
    assert com_codigo == ["QA-007", "QA-008", "QA-009"]
    for modelo in ledger.TASK_BACKBONE:
        for glob in modelo.get("sourceCodeGlobs") or []:
            assert glob != "outputs/tobe/source-code/**"
            assert not glob.rstrip("/").endswith("source-code")


@pytest.mark.parametrize("tid,esperado,proibido", [
    ("QA-007", "Migrations/20260101_Init.cs", "Servico0.cs"),
    ("QA-008", "Controllers/VendasController.cs", "Servico0.cs"),
    ("QA-009", "vendas.component.ts", "Servico0.cs"),
])
def test_globs_estreitos_pegam_o_alvo_e_nada_mais(runner, tmp_path, monkeypatch,
                                                  tid, esperado, proibido):
    _monta_projeto(tmp_path, arquivos_build=30)
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)
    modelo = next(t for t in ledger.TASK_BACKBONE if t["id"] == tid)
    tarefa = ledger.new_task(modelo)

    fatia, censo = runner._qa_read_code_slice("P", tarefa)

    assert esperado.rsplit("/", 1)[-1] in fatia
    assert proibido not in fatia
    assert MARCA_CODIGO not in fatia
    assert MARCA_BUILD not in fatia
    assert censo["files_injected"] <= ledger.TASK_CODE_FILES
    assert censo["chars"] <= ledger.TASK_CODE_CHARS


def test_tarefa_sem_glob_nao_le_codigo_algum(runner, tmp_path, monkeypatch):
    _monta_projeto(tmp_path)
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)
    tarefa = ledger.new_task(next(t for t in ledger.TASK_BACKBONE if t["id"] == "QA-001"))
    fatia, censo = runner._qa_read_code_slice("P", tarefa)
    assert fatia == "" and censo["files_matched"] == 0


# ═══════════════════════════════════════════════════════════════════════════
#  10–11 · Planejamento e retomada
# ═══════════════════════════════════════════════════════════════════════════

def test_criacao_inicial_do_task_qa_progress(tmp_path):
    _monta_projeto(tmp_path)
    progresso, novos = ledger.load_or_plan("P", ledger.PLANNING_INPUTS,
                                           repo_root=tmp_path)
    caminho = ledger.progress_path("P", tmp_path)

    assert caminho.is_file()
    assert caminho.as_posix().endswith("outputs/tobe/qa/task-qa-progress.json")
    assert len(progresso["tasks"]) == len(ledger.TASK_BACKBONE) == len(novos)
    em_disco = json.loads(caminho.read_text(encoding="utf-8"))
    assert em_disco["phase"] == "F6" and em_disco["trigger"] == "QE"
    assert em_disco["planningCompletedAt"]


def test_toda_tarefa_tem_o_contrato_minimo(tmp_path):
    _monta_projeto(tmp_path)
    progresso, _ = ledger.load_or_plan("P", ledger.PLANNING_INPUTS, repo_root=tmp_path)
    obrigatorios = {
        "id", "sequence", "title", "description", "category", "subAgent", "status",
        "priority", "mandatory", "blocking", "dependencies", "inputArtifacts",
        "sourceCodeGlobs", "executionCommand", "expectedResult", "actualResult",
        "retryCount", "maxRetries", "startedAt", "completedAt", "lastUpdatedAt",
        "error", "errorType", "evidence", "outputArtifacts", "warning", "nextAction",
    }
    for tarefa in progresso["tasks"]:
        assert obrigatorios <= set(tarefa), f"{tarefa['id']} sem campos do contrato"
        assert tarefa["status"] in ledger.STATUSES


def test_retomada_preserva_passed_e_nao_duplica(tmp_path):
    _monta_projeto(tmp_path)
    progresso, _ = ledger.load_or_plan("P", ledger.PLANNING_INPUTS, repo_root=tmp_path)
    alvo = progresso["tasks"][0]
    ledger.mark_passed(alvo, actual="ok", artifacts=["outputs/tobe/qa/gap-analysis.md"])
    ledger.save_progress(ledger.progress_path("P", tmp_path), progresso)

    de_novo, novos = ledger.load_or_plan("P", ledger.PLANNING_INPUTS, repo_root=tmp_path)
    ids = [t["id"] for t in de_novo["tasks"]]
    assert len(ids) == len(set(ids)) and novos == []
    preservada = next(t for t in de_novo["tasks"] if t["id"] == alvo["id"])
    assert preservada["status"] == ledger.STATUS_PASSED
    assert preservada["outputArtifacts"] == ["outputs/tobe/qa/gap-analysis.md"]


def test_retomada_reabre_in_progress(tmp_path):
    _monta_projeto(tmp_path)
    progresso, _ = ledger.load_or_plan("P", ledger.PLANNING_INPUTS, repo_root=tmp_path)
    ledger.mark_in_progress(progresso["tasks"][0])
    ledger.save_progress(ledger.progress_path("P", tmp_path), progresso)

    de_novo, _ = ledger.load_or_plan("P", ledger.PLANNING_INPUTS, repo_root=tmp_path)
    assert de_novo["tasks"][0]["status"] == ledger.STATUS_READY


# ═══════════════════════════════════════════════════════════════════════════
#  12–18 · Dependências, retries, ciclos, corrupção
# ═══════════════════════════════════════════════════════════════════════════

def _prog(tarefas):
    return {"schemaVersion": ledger.SCHEMA_VERSION, "project": "P",
            "tasks": tarefas, "iterations": 0}


def _t(tid, seq, deps=(), **kw):
    base = {"id": tid, "sequence": seq, "dependencies": list(deps)}
    base.update(kw)
    return ledger.new_task(base)


def test_dependencia_falha_bloqueia_apenas_quem_depende():
    a = _t("QA-001", 1)
    a["retryCount"] = a["maxRetries"]
    ledger.mark_failed(a, error_type="Boom", error="estourou")
    b = _t("QA-002", 2, ["QA-001"])
    independente = _t("QA-009", 9)
    prog = _prog([a, b, independente])

    # A independente continua elegível mesmo com QA-001 reprovada.
    assert ledger.select_next_task(prog)["id"] == "QA-009"
    bloqueados = ledger.mark_blocked_tasks(prog)
    assert bloqueados == ["QA-002"]
    assert independente["status"] == ledger.STATUS_PENDING


def test_bloqueio_propaga_em_cascata():
    a = _t("QA-001", 1)
    a["retryCount"] = a["maxRetries"]
    ledger.mark_failed(a, error_type="Boom", error="x")
    b = _t("QA-002", 2, ["QA-001"])
    c = _t("QA-003", 3, ["QA-002"])
    prog = _prog([a, b, c])

    assert set(ledger.mark_blocked_tasks(prog)) == {"QA-002", "QA-003"}


def test_ressalva_satisfaz_dependencia():
    a = _t("QA-001", 1)
    ledger.mark_warning(a, actual="parcial", warning="sem paridade")
    b = _t("QA-002", 2, ["QA-001"])
    assert ledger.select_next_task(_prog([a, b]))["id"] == "QA-002"


def test_retry_limitado_e_desfecho_por_obrigatoriedade():
    obrigatoria = _t("QA-001", 1, mandatory=True)
    for _ in range(ledger.MAX_RETRIES):
        ledger.mark_in_progress(obrigatoria)
        ledger.mark_failed(obrigatoria, error_type="Boom", error="x")
    assert obrigatoria["status"] == ledger.STATUS_FAILED
    assert ledger.is_retryable(obrigatoria) is False

    opcional = _t("QA-050", 50, mandatory=False)
    for _ in range(ledger.MAX_RETRIES):
        ledger.mark_in_progress(opcional)
        ledger.mark_failed(opcional, error_type="Boom", error="x")
    assert opcional["status"] == ledger.STATUS_WARNING
    assert opcional["warning"]


def test_passed_nunca_e_reexecutada():
    a = _t("QA-001", 1)
    ledger.mark_passed(a, actual="ok", artifacts=["x"])
    assert ledger.select_next_task(_prog([a])) is None


def test_dependencia_circular_e_detectada():
    a = _t("QA-001", 1, ["QA-002"])
    b = _t("QA-002", 2, ["QA-001"])
    ciclos = ledger.find_cycles(_prog([a, b]))
    assert ciclos and set(ciclos[0]) == {"QA-001", "QA-002"}
    assert ledger.find_cycles(_prog([_t("QA-001", 1), _t("QA-002", 2, ["QA-001"])])) == []


def test_json_corrompido_e_recuperado_do_backup(tmp_path):
    _monta_projeto(tmp_path)
    caminho = ledger.progress_path("P", tmp_path)
    progresso, _ = ledger.load_or_plan("P", ledger.PLANNING_INPUTS, repo_root=tmp_path)
    ledger.mark_passed(progresso["tasks"][0], actual="ok", artifacts=["a"])
    ledger.save_progress(caminho, progresso)      # gera o .bak
    ledger.save_progress(caminho, progresso)      # .bak agora tem o estado bom

    caminho.write_text('{"tasks": [ISTO NAO E JSON', encoding="utf-8")
    recuperado = ledger.read_progress(caminho)

    assert recuperado is not None
    assert recuperado.get("recovered_from_backup") is True
    assert any(t["status"] == ledger.STATUS_PASSED for t in recuperado["tasks"])
    assert ledger.read_progress(caminho, allow_backup=False) is None


def test_escrita_atomica_nao_deixa_tmp_e_versiona(tmp_path):
    _monta_projeto(tmp_path)
    caminho = ledger.progress_path("P", tmp_path)
    progresso, _ = ledger.load_or_plan("P", ledger.PLANNING_INPUTS, repo_root=tmp_path)
    ledger.save_progress(caminho, progresso)

    assert json.loads(caminho.read_text(encoding="utf-8"))["tasks"]
    assert caminho.with_suffix(caminho.suffix + ".bak").is_file()
    assert list(caminho.parent.glob("*.tmp")) == []


def test_nenhum_segredo_no_arquivo_de_progresso():
    t = _t("QA-001", 1)
    ledger.mark_in_progress(t)
    ledger.mark_failed(t, error_type="AuthError",
                       error="Server=db;Password=Sup3rS3cr3t; token: ghp_ABCDEFGHIJKLMNOPQRST")
    persistido = json.dumps(t, ensure_ascii=False)
    assert "Sup3rS3cr3t" not in persistido
    assert "ghp_ABCDEFGHIJKLMNOPQRST" not in persistido
    assert "REDACTED" in persistido


# ═══════════════════════════════════════════════════════════════════════════
#  Gate QE
# ═══════════════════════════════════════════════════════════════════════════

def test_gate_passa_com_tudo_no_lugar(runner, tmp_path, monkeypatch):
    _monta_projeto(tmp_path)
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)
    ok, bloqueios, avisos = runner._qa_precondition_gate("P")
    assert ok is True and bloqueios == []
    # parity-test-report.md ausente é WARNING, nunca bloqueio (Passo 4b).
    assert any("parity-test-report" in a for a in avisos)


def test_gate_bloqueia_sem_readme_do_source_code(runner, tmp_path, monkeypatch):
    _monta_projeto(tmp_path)
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)
    (tmp_path / "projects/P/outputs/tobe/source-code/README.md").unlink()
    ok, bloqueios, _ = runner._qa_precondition_gate("P")
    assert ok is False and any("README.md" in b for b in bloqueios)


def test_gate_bloqueia_com_frontend_vazio(runner, tmp_path, monkeypatch):
    _monta_projeto(tmp_path, com_frontend=False)
    (tmp_path / "projects/P/outputs/tobe/source-code/frontend").mkdir(parents=True)
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)
    ok, bloqueios, _ = runner._qa_precondition_gate("P")
    assert ok is False and any("frontend" in b for b in bloqueios)


def test_gate_nao_le_o_conteudo_do_source_code(runner, tmp_path, monkeypatch, capsys):
    _monta_projeto(tmp_path, arquivos_build=50)
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)
    runner._qa_precondition_gate("P")
    saida = capsys.readouterr().out
    assert MARCA_CODIGO not in saida and MARCA_BUILD not in saida


# ═══════════════════════════════════════════════════════════════════════════
#  Laço completo dentro do runner
# ═══════════════════════════════════════════════════════════════════════════

def _artefato_para(glob: str) -> str:
    return glob.replace("/**", "/gerado.md").replace("*", "1")


class _DispatchFalso:
    """Substitui `_dispatch_model`. Guarda todo prompt enviado, para inspeção."""

    def __init__(self, tmp_path, *, comportamento=None):
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
            return "sem blocos FILE", "end_turn", 100, 50

        progresso = json.loads(
            (self.tmp_path / "projects" / "P" / ledger.PROGRESS_REL)
            .read_text(encoding="utf-8"))
        tarefa = next(t for t in progresso["tasks"] if t["id"] == tid)
        rel = _artefato_para((tarefa.get("outputGlobs") or ["outputs/tobe/qa/**"])[0])
        return (f"<!-- FILE: projects/P/{rel} -->\nconteudo de {tid}\n<!-- /FILE -->\n",
                "end_turn", 1_000, 200)


@pytest.fixture
def loop_pronto(runner, tmp_path, monkeypatch):
    _monta_projeto(tmp_path, arquivos_build=40)
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)
    monkeypatch.setattr(runner, "load_skill",
                        lambda agent, spec_path=None: f"# skill de {agent}\n")
    monkeypatch.setattr(runner, "status_heartbeat", lambda *a, **k: None)
    # Nenhum componente no ar: portas fechadas em 127.0.0.1 na faixa sondada.
    monkeypatch.setattr(runner, "_qa_runtime_state",
                        lambda project, required: {c: "indisponível (teste)"
                                                   for c in required})
    passo = {"phase": "F6", "agent": "ava-qa-orchestrator", "trigger": "QE",
             "label": "QA — Quality Execute", "inputs": runner._f6_qa_inputs()}
    saida = tmp_path / "projects" / "P" / "outputs" / "pipeline_runner"
    saida.mkdir(parents=True, exist_ok=True)
    return runner, passo, saida, tmp_path, monkeypatch


def _executa(runner, passo, saida, **kw):
    return runner._run_qa_execute_step(
        object(), passo, "P", saida, skill_content="skill",
        out_tokens=128_000, esperados=[], headroom_active=False, **kw)


def test_laco_percorre_o_plano_e_persiste_cada_transicao(loop_pronto):
    runner, passo, saida, tmp_path, mp = loop_pronto
    falso = _DispatchFalso(tmp_path)
    mp.setattr(runner, "_dispatch_model", falso)

    metricas = _executa(runner, passo, saida)
    progresso = json.loads((tmp_path / "projects/P" / ledger.PROGRESS_REL)
                           .read_text(encoding="utf-8"))
    aprovadas = [t for t in progresso["tasks"] if t["status"] == ledger.STATUS_PASSED]

    assert aprovadas, "nenhuma tarefa aprovada"
    assert all(t["completedAt"] and t["outputArtifacts"] for t in aprovadas)
    # Uma iteração pode terminar sem despacho: tarefa que exige runtime
    # indisponível é pulada sem gastar inferência.
    puladas = [t for t in progresso["tasks"] if t["status"] == ledger.STATUS_SKIPPED]
    assert metricas["qa_iterations"] == len(falso.prompts) + len(puladas)
    assert progresso["iterations"] == metricas["qa_iterations"]
    assert progresso["terminationReason"]
    # Cada tarefa despachada UMA vez: `passed` não é reexecutada.
    ids = [u.rsplit("task:", 1)[1].strip() for _, u in falso.prompts]
    assert len(ids) == len(set(ids))


def test_payload_nunca_contem_o_source_code_inteiro(loop_pronto):
    """Critério de aceite central da F6."""
    runner, passo, saida, tmp_path, mp = loop_pronto
    falso = _DispatchFalso(tmp_path)
    mp.setattr(runner, "_dispatch_model", falso)

    _executa(runner, passo, saida)

    assert falso.prompts
    for system_prompt, _ in falso.prompts:
        assert MARCA_CODIGO not in system_prompt
        assert MARCA_BUILD not in system_prompt
        assert MARCA_PROSA not in system_prompt
        assert ledger.estimate_tokens(system_prompt) < 200_000


def test_apenas_dbi_ct_ft_recebem_codigo_no_prompt(loop_pronto):
    runner, passo, saida, tmp_path, mp = loop_pronto
    falso = _DispatchFalso(tmp_path)
    mp.setattr(runner, "_dispatch_model", falso)

    _executa(runner, passo, saida)

    com_codigo = {u.rsplit("task:", 1)[1].strip()
                  for s, u in falso.prompts if "Fatia de código desta tarefa" in s}
    assert com_codigo <= {"QA-007", "QA-008", "QA-009"}
    assert com_codigo, "nenhuma tarefa recebeu a fatia de código esperada"


def test_tarefa_que_exige_runtime_indisponivel_e_pulada(loop_pronto):
    """Não executado nunca é apresentado como sucesso."""
    runner, passo, saida, tmp_path, mp = loop_pronto
    falso = _DispatchFalso(tmp_path)
    mp.setattr(runner, "_dispatch_model", falso)

    _executa(runner, passo, saida)
    progresso = json.loads((tmp_path / "projects/P" / ledger.PROGRESS_REL)
                           .read_text(encoding="utf-8"))
    fq = next(t for t in progresso["tasks"] if t["id"] == "QA-010")

    assert fq["status"] == ledger.STATUS_SKIPPED
    assert "NÃO executado" in (fq["actualResult"] or "")
    assert "suba a aplicação" in (fq["nextAction"] or "")
    # E o sub-agente nunca foi chamado para ela.
    assert not any(u.endswith("QA-010") for _, u in falso.prompts)


def test_backend_no_ar_e_frontend_fora(runner, tmp_path, monkeypatch):
    _monta_projeto(tmp_path)
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)
    import socket as _socket
    servidor = _socket.socket()
    servidor.bind(("127.0.0.1", 0))
    servidor.listen(1)
    porta = servidor.getsockname()[1]
    (tmp_path / "projects/P/context/project-config.yaml").write_text(
        f"project_name: P\nbackend_port: {porta}\nfrontend_port: 1\n", encoding="utf-8")
    try:
        estado = runner._qa_runtime_state("P", ["backend", "frontend"])
    finally:
        servidor.close()

    assert estado["backend"].startswith("em execução")
    assert estado["frontend"].startswith("indisponível")


def test_falha_nao_bloqueante_nao_para_as_independentes(loop_pronto):
    runner, passo, saida, tmp_path, mp = loop_pronto

    def comportamento(tid, n):
        if tid == "QA-007":                       # DBI falha sempre
            return RuntimeError("dotnet ef nao encontrado")
        return "ok"

    falso = _DispatchFalso(tmp_path, comportamento=comportamento)
    mp.setattr(runner, "_dispatch_model", falso)

    metricas = _executa(runner, passo, saida)
    progresso = json.loads((tmp_path / "projects/P" / ledger.PROGRESS_REL)
                           .read_text(encoding="utf-8"))
    por_id = {t["id"]: t for t in progresso["tasks"]}

    assert por_id["QA-007"]["status"] == ledger.STATUS_FAILED
    assert por_id["QA-007"]["retryCount"] == ledger.MAX_RETRIES
    # CT e FT não dependem de DBI — continuaram.
    assert por_id["QA-008"]["status"] == ledger.STATUS_PASSED
    assert por_id["QA-009"]["status"] == ledger.STATUS_PASSED
    # FQ depende de DBI — bloqueada, não executada.
    assert por_id["QA-010"]["status"] == ledger.STATUS_BLOCKED
    assert metricas["val_ok"] is False and "QA-007" in metricas["detail"]


def test_falha_bloqueante_encerra_a_fase(loop_pronto):
    runner, passo, saida, tmp_path, mp = loop_pronto
    falso = _DispatchFalso(tmp_path,
                           comportamento=lambda tid, n: RuntimeError("boom"))
    mp.setattr(runner, "_dispatch_model", falso)

    # Marca a primeira tarefa como bloqueante antes de executar.
    progresso, _ = ledger.load_or_plan("P", ledger.PLANNING_INPUTS, repo_root=tmp_path)
    progresso["tasks"][0]["blocking"] = True
    ledger.save_progress(ledger.progress_path("P", tmp_path), progresso)

    metricas = _executa(runner, passo, saida)
    assert "bloqueante" in metricas["qa_termination"]
    assert metricas["val_ok"] is False


def test_limite_global_de_iteracoes(loop_pronto):
    runner, passo, saida, tmp_path, mp = loop_pronto
    mp.setattr(ledger, "MAX_ITERATIONS", 3)
    falso = _DispatchFalso(tmp_path)
    mp.setattr(runner, "_dispatch_model", falso)

    metricas = _executa(runner, passo, saida)
    assert metricas["qa_iterations"] == 3
    assert "limite global" in metricas["qa_termination"]


def test_ausencia_de_progresso_interrompe(loop_pronto):
    runner, passo, saida, tmp_path, mp = loop_pronto
    falso = _DispatchFalso(tmp_path)
    mp.setattr(runner, "_dispatch_model", falso)
    ledger.load_or_plan("P", ledger.PLANNING_INPUTS, repo_root=tmp_path)
    mp.setattr(ledger, "save_progress", lambda caminho, progresso: caminho)

    metricas = _executa(runner, passo, saida)
    assert metricas["qa_iterations"] == 1
    assert "progresso" in metricas["qa_termination"]


def test_dependencia_circular_reprova_antes_de_despachar(loop_pronto):
    runner, passo, saida, tmp_path, mp = loop_pronto
    falso = _DispatchFalso(tmp_path)
    mp.setattr(runner, "_dispatch_model", falso)
    progresso, _ = ledger.load_or_plan("P", ledger.PLANNING_INPUTS, repo_root=tmp_path)
    progresso["tasks"][0]["dependencies"] = ["QA-002"]
    ledger.save_progress(ledger.progress_path("P", tmp_path), progresso)

    metricas = _executa(runner, passo, saida)
    assert falso.prompts == [], "despachou com o grafo cíclico"
    assert "circular" in metricas["detail"]


def test_gate_bloqueado_nao_despacha(loop_pronto):
    runner, passo, saida, tmp_path, mp = loop_pronto
    falso = _DispatchFalso(tmp_path)
    mp.setattr(runner, "_dispatch_model", falso)
    (tmp_path / "projects/P/outputs/tobe/qa/test-plan.md").unlink()

    metricas = _executa(runner, passo, saida)
    assert falso.prompts == []
    assert metricas["val_ok"] is False and "gate QE" in metricas["detail"]


def test_relatorios_e_metricas_de_contexto(loop_pronto):
    runner, passo, saida, tmp_path, mp = loop_pronto
    mp.setattr(runner, "_dispatch_model", _DispatchFalso(tmp_path))

    metricas = _executa(runner, passo, saida)
    qa = tmp_path / "projects/P/outputs/tobe/qa"

    resumo = (qa / "test-execution-summary.md").read_text(encoding="utf-8")
    assert "tarefas planejadas" in resumo
    assert "Não executadas" in resumo          # não apresenta pendente como sucesso
    resultados = json.loads((qa / "test-results.json").read_text(encoding="utf-8"))
    assert resultados["counts"]["total"] == len(ledger.TASK_BACKBONE)

    primeira = metricas["qa_task_metrics"][0]
    for chave in ("task_id", "task_status", "attempt", "start_time", "end_time",
                  "duration_s", "input_files", "source_code_globs",
                  "output_artifacts", "error_type", "continuation_action",
                  "estimated_input_tokens"):
        assert chave in primeira
    assert any(k.startswith("ctx_") for k in primeira)
    json.dumps(runner._serialize_metrics(metricas), ensure_ascii=False)


def test_execucao_interrompida_e_retomada(loop_pronto):
    """Metade das tarefas roda, o processo cai, a retomada não refaz o que passou."""
    runner, passo, saida, tmp_path, mp = loop_pronto
    mp.setattr(ledger, "MAX_ITERATIONS", 4)
    primeiro = _DispatchFalso(tmp_path)
    mp.setattr(runner, "_dispatch_model", primeiro)
    _executa(runner, passo, saida)

    feitas = {u.rsplit("task:", 1)[1].strip() for _, u in primeiro.prompts}
    assert len(feitas) == 4

    mp.setattr(ledger, "MAX_ITERATIONS", 80)
    segundo = _DispatchFalso(tmp_path)
    mp.setattr(runner, "_dispatch_model", segundo)
    _executa(runner, passo, saida)

    refeitas = {u.rsplit("task:", 1)[1].strip() for _, u in segundo.prompts}
    assert refeitas.isdisjoint(feitas), "tarefa aprovada foi reexecutada na retomada"

    progresso = json.loads((tmp_path / "projects/P" / ledger.PROGRESS_REL)
                           .read_text(encoding="utf-8"))
    aprovadas = [t["id"] for t in progresso["tasks"]
                 if t["status"] == ledger.STATUS_PASSED]
    assert feitas <= set(aprovadas)


# ═══════════════════════════════════════════════════════════════════════════
#  Não-regressão
# ═══════════════════════════════════════════════════════════════════════════

def test_inputs_da_f6_nao_declaram_o_diretorio_de_codigo(runner):
    passo = next(s for s in runner.PIPELINE if s["phase"] == "F6")
    injetados = [i["path"] if isinstance(i, dict) else i
                 for tier in ("mandatory", "advisory")
                 for i in passo["inputs"].get(tier) or []]
    for proibido in runner.F6_QA_FORBIDDEN:
        assert not any(c == proibido or c.startswith(proibido + "/")
                       for c in injetados), f"{proibido} voltou aos inputs da F6"
    assert passo["inputs"]["exists"], "o tier `exists` sumiu do manifesto"
    assert runner._assert_no_directory_inputs.__doc__


def test_ava_pipeline_yaml_f6_esta_limpo():
    yaml = pytest.importorskip("yaml")
    cfg = yaml.safe_load((REPO_ROOT / "src/shared/data/ava-pipeline.yaml")
                         .read_text(encoding="utf-8"))
    passos = cfg["pipeline"]["steps"] if "pipeline" in cfg else cfg["steps"]
    f6 = next(s for s in passos if s.get("phase") == "F6")
    injetados = [i["path"] if isinstance(i, dict) else i
                 for tier in ("mandatory", "advisory")
                 for i in (f6.get("inputs") or {}).get(tier) or []]
    assert "outputs/tobe/source-code" not in injetados
    assert (f6["inputs"].get("exists"))


def test_apenas_a_tripla_f6_qa_qe_entra_no_laco(runner):
    assert runner._is_f6_qa_step(
        {"phase": "F6", "agent": "ava-qa-orchestrator", "trigger": "QE"}) is True
    # Mesmo agente no planejamento (F2c/TPT) segue o caminho comum.
    assert runner._is_f6_qa_step(
        {"phase": "F2c", "agent": "ava-qa-orchestrator", "trigger": "TPT"}) is False
    assert runner._is_f6_qa_step(
        {"phase": "F6", "agent": "ava-qa-orchestrator", "trigger": "TPT"}) is False
    assert runner._is_f6_qa_step(
        {"phase": "F6", "agent": "ava-devops-orchestrator", "trigger": "QE"}) is False
    assert runner._is_f6_qa_step(None) is False


def test_f5_e_demais_fases_seguem_intactas(runner):
    f5 = next(s for s in runner.PIPELINE if s["phase"] == "F5")
    assert [i["path"] for i in f5["inputs"]["mandatory"]] == [
        "context/project-config.yaml",
        "outputs/tobe/devops/devops-plan.md",
        "outputs/tobe/devops/environments-plan.md"]
    f2a = next(s for s in runner.PIPELINE if s["phase"] == "F2a")
    caminhos = [i["path"] if isinstance(i, dict) else i
                for i in f2a["inputs"]["mandatory"]]
    assert "outputs/asis/architecture-blueprint.md" in caminhos
    assert "exists" not in f2a["inputs"]


def test_caminhos_usam_barra(runner):
    todos = (runner.F6_QA_EXISTS + runner.F6_QA_MANDATORY + runner.F6_QA_ADVISORY
             + runner.F6_QA_FORBIDDEN + ledger.PLANNING_INPUTS
             + (ledger.PROGRESS_REL, ledger.BACKUP_REL, ledger.QA_DIR_REL))
    for caminho in todos:
        assert "\\" not in caminho and "\t" not in caminho and "/" in caminho
    for modelo in ledger.TASK_BACKBONE:
        for glob in (modelo.get("sourceCodeGlobs") or []) + list(modelo.get("outputGlobs") or []):
            assert "\\" not in glob and "\t" not in glob
