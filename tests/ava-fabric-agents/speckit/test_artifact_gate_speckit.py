"""
Testes dos gates da F3S — `speckit/utils/artifact_gate_speckit.py`.

O invariante que estes testes protegem é de processo, não de código: **o gate não
pode guardar uma segunda cópia da lista de artefatos**. Ele deriva de
`src/shared/data/pipeline-dag/F3S.yaml` em runtime.

Este repositório já pagou o preço do espelho manual: `agent_registry.py` existe
porque dois catálogos escritos à mão divergiram em 52 agentes, e o cabeçalho de
`pipeline-dag/F1.yaml` avisa explicitamente contra virar "a quarta fonte de
verdade". Um `grep` por lista literal de artefato dentro do módulo do gate é a
forma barata de garantir que ninguém "otimize" isso depois.

Roda com o Python do repo:
    python -m pytest tests/ava-fabric-agents/speckit/test_artifact_gate_speckit.py -q
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
GATE_PY = (
    REPO_ROOT / "src" / "modules" / "ava-fabric-agents"
    / "speckit" / "utils" / "artifact_gate_speckit.py"
)
DAG_PY = REPO_ROOT / "src" / "shared" / "data" / "pipeline-dag" / "F3S.yaml"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


gate = _load(GATE_PY, "artifact_gate_speckit_under_test")


# ─── Ancoragem ───────────────────────────────────────────────────────────────

def test_repo_root_e_ancorado_no_arquivo_e_nao_no_cwd():
    assert gate.REPO_ROOT == REPO_ROOT
    assert (gate.REPO_ROOT / "projects").is_dir()


def test_dag_path_aponta_para_o_f3s_yaml():
    assert gate.DAG_PATH == DAG_PY
    assert gate.DAG_PATH.is_file()


# ─── A regra da fonte única ──────────────────────────────────────────────────

def test_gate_nao_guarda_lista_propria_de_artefatos():
    """Nenhum caminho de artefato da F3S literal dentro do módulo do gate.

    Se este teste falhar, alguém copiou a lista do YAML para o Python e criou o
    sétimo espelho manual do repositório. Corrija removendo a cópia, não o teste.
    """
    fonte = GATE_PY.read_text(encoding="utf-8")
    # A docstring cita caminhos como evidência; só o código é inspecionado.
    corpo = fonte.split('"""', 2)[-1]
    # Caminho de artefato do projeto — a forma que uma lista copiada teria.
    # Menção a um nome de arquivo em mensagem de diagnóstico é legítima; o que
    # não pode existir é `outputs/...` literal, que só faria sentido numa cópia
    # da tabela do YAML.
    caminhos = re.findall(r'["\']outputs/[A-Za-z0-9_\-/.]+["\']', corpo)
    assert not caminhos, (
        f"lista de artefatos duplicada no gate: {sorted(set(caminhos))}. "
        f"A fonte é {DAG_PY.relative_to(REPO_ROOT)} — leia de lá em runtime."
    )


def test_itens_do_gate_vem_do_yaml():
    dag = gate.load_dag()
    entry = gate.gate_items("entry", dag)
    exit_ = gate.gate_items("exit", dag)
    assert entry and exit_, "os dois gates precisam declarar itens"
    caminhos_entry = {i["path"] for i in entry}
    caminhos_exit = {i["path"] for i in exit_}
    # entrada olha para os insumos; saída, para os produtos
    assert any(p.startswith("outputs/tobe/") for p in caminhos_entry)
    assert all(p.startswith("outputs/tobe/speckit/") for p in caminhos_exit)


def test_todo_item_declara_quem_o_produz():
    """Mensagem de gate sem produtor obriga o operador a adivinhar."""
    dag = gate.load_dag()
    sem_produtor = [
        f"{g}:{i['path']}"
        for g in ("entry", "exit")
        for i in gate.gate_items(g, dag)
        if not i.get("produced_by")
    ]
    assert not sem_produtor, f"itens sem `produced_by`: {sem_produtor}"
    traceability = next(
        item for item in gate.gate_items("exit", dag)
        if item["path"].endswith("traceability.json")
    )
    assert "speckit_task_compiler.py" in traceability["produced_by"]


def test_gate_de_saida_delega_as_tres_suites():
    """O gate não reimplementa rastreabilidade — ele chama quem já a verifica.

    A terceira suíte cobre o eixo que faltava: protótipo → tarefa → API →
    integração → e2e. Delegar continua sendo a regra; o gate não ganhou lógica
    própria, ganhou mais um delegado.
    """
    dag = gate.load_dag()
    assert set(gate.gate_suites("exit", dag)) == {
        "speckit_traceability", "prototype_coverage", "speckit_frontend_integration"}
    assert gate.gate_suites("entry", dag) == []


def test_preflight_externo_avisa_mas_nao_bloqueia():
    """Insumo de OUTRA fase ausente é aviso, não reprovação da F3S.

    Regra invertida de propósito: a camada SpecKit está em evolução e é
    non-blocking. Antes, a falta de um artefato upstream (ex.:
    `outputs/asis/docs/business-rules.md`) fazia `run_gate` retornar `FAIL`
    ANTES de conferir um único artefato do próprio SpecKit — a fase inteira era
    reprovada por algo que ela não produz. O achado continua visível em
    `missing`; o que mudou é a consequência.
    """
    projeto = Path("/tmp/does-not-exist")
    result = gate.check_external_dependencies("P", projeto)
    assert result["status"] == "WARN"
    assert result["status"] != "FAIL"
    assert any(item["path"] == "outputs/asis/docs/business-rules.md"
               for item in result["missing"])
    assert "continua" in result["message"].lower()


def test_gate_nao_reprova_por_dependencia_externa(projeto_exit: Path):
    """O veredito do gate ignora insumo externo — só olha o que a F3S produz."""
    resultado = gate.run_gate("exit", "P", projeto_exit, gate.load_dag())
    # O projeto de teste não tem NENHUM insumo externo em disco.
    assert resultado["external_missing"], "o cenário não exercita insumo ausente"
    # ...e mesmo assim nenhum deles entrou em `missing`, que é o que decide.
    externos = {i["path"] for i in resultado["external_missing"]}
    declarados = {i["path"] for i in resultado["missing"]}
    assert externos.isdisjoint(declarados)
    assert all(p.startswith("outputs/tobe/speckit/") for p in declarados), (
        "o gate só pode reprovar por artefato do próprio diretório do SpecKit")


def test_on_fail_declara_a_consequencia():
    dag = gate.load_dag()
    assert dag["entry_gate"]["on_fail"] == "abort_f3s"
    assert dag["exit_gate"]["on_fail"] == "block_f4"


def _no_de_tool(dag: dict, tool_id: str) -> dict:
    for wave in dag.get("waves") or []:
        for tool in wave.get("tools") or []:
            if tool.get("id") == tool_id:
                return tool
    raise AssertionError(f"nó de tool ausente no F3S.yaml: {tool_id}")


def test_exit_gate_avisa_em_vez_de_reprovar():
    """O nó `speckit-exit-gate` era o único sem `on_fail`, e a omissão doía.

    Sem a chave, `ava_pipeline.run_tool_step` levanta `RuntimeError` e o
    operador lê "❌ tool reprovou — corrija a causa ANTES de confiar nas fases
    seguintes": linguagem de bloqueio numa esteira que, pela POLÍTICA DE ERRO no
    topo do `F3S.yaml`, continua sempre. Medido em `nocommerce-01`, os 7
    artefatos estruturais estavam presentes e o que "faltava" era ESTADO —
    inclusive uma decisão humana pendente, que não é erro.
    """
    no = _no_de_tool(gate.load_dag(), "speckit-exit-gate")
    assert no.get("on_fail") == "warn"
    # `--report` anda junto: a política exige que o achado sobreviva ao console.
    assert "--report" in no["command"]


def test_todo_no_de_tool_da_f3s_e_non_blocking():
    """Nenhuma tool da camada SpecKit pode interromper a esteira.

    Enquanto a F3S está em evolução, `on_fail: warn` é obrigatório em TODOS os
    nós — inclusive nos dois gates. O `speckit-exit-gate` era o único sem a
    chave, e a omissão produzia "❌ tool reprovou" numa esteira que continua
    sempre; depois o `speckit-entry-gate` entrou na mesma regra.
    """
    dag = gate.load_dag()
    sem_chave = [t["id"] for w in dag.get("waves") or []
                 for t in w.get("tools") or [] if t.get("on_fail") != "warn"]
    assert sem_chave == [], f"nó(s) de tool que ainda bloqueiam: {sem_chave}"


def test_os_dois_gates_saem_com_zero():
    """`--warn` nos dois gates: nenhum deles altera o exit code do pipeline."""
    dag = gate.load_dag()
    for tool_id in ("speckit-entry-gate", "speckit-exit-gate"):
        comando = _no_de_tool(dag, tool_id)["command"]
        assert "--warn" in comando, f"{tool_id} ainda pode sair != 0"
        assert "--report" in comando, f"{tool_id} não persiste o veredito"


def test_warn_forca_exit_zero_mesmo_reprovando(projeto_exit: Path, monkeypatch,
                                               capsys):
    """O veredito continua FAIL no relatório; só o exit code vira 0."""
    monkeypatch.setattr(gate, "REPO_ROOT", projeto_exit)
    sem_warn = gate.main(["--project", "P", "--gate", "exit"])
    com_warn = gate.main(["--project", "P", "--gate", "exit", "--warn", "--report"])
    saida = capsys.readouterr().out

    assert sem_warn != gate.EXIT_PASS, "o cenário precisa reprovar sem --warn"
    assert com_warn == gate.EXIT_PASS
    assert "Exit Code: 0" in saida
    # A verdade sobrevive: o relatório persistido continua dizendo FAIL.
    gravado = json.loads(
        gate.report_path("exit", "P", projeto_exit).read_text(encoding="utf-8"))
    assert gravado["status"] == "FAIL"


@pytest.fixture
def projeto_exit(tmp_path: Path) -> Path:
    """Projeto mínimo para o gate de saída rodar. Reprova — é o cenário real."""
    speckit = tmp_path / "projects" / "P" / "outputs" / "tobe" / "speckit"
    speckit.mkdir(parents=True)
    (speckit / "constitution.md").write_text("# constituicao\n", encoding="utf-8")
    return tmp_path


def test_relatorio_do_gate_e_persistido(projeto_exit: Path):
    """`on_fail: warn` só serve se o achado sobreviver ao scrollback."""
    resultado = gate.run_gate("exit", "P", projeto_exit, gate.load_dag())
    destino = gate.write_report(resultado, "P", projeto_exit)

    assert destino is not None and destino.is_file()
    assert destino.as_posix().endswith(
        "outputs/tobe/speckit/exit-gate-status.json")
    gravado = json.loads(destino.read_text(encoding="utf-8"))
    assert gravado["gate"] == "exit"
    assert gravado["advisory"] is True
    assert gravado["generated_at"]
    assert gravado["status"] == resultado["status"]


def test_exit_code_real_continua_sendo_propagado(projeto_exit: Path,
                                                 monkeypatch, capsys):
    """A tool segue dizendo a verdade; quem decide a consequência é o DAG.

    Silenciar o exit code aqui esconderia a reprovação de quem chama a tool
    direto (CI, operador). O `on_fail: warn` age no nó, não no veredito.
    """
    monkeypatch.setattr(gate, "REPO_ROOT", projeto_exit)
    codigo = gate.main(["--project", "P", "--gate", "exit", "--report"])
    capsys.readouterr()
    assert codigo in (gate.EXIT_PASS, gate.SOFT_FAIL_EXIT, gate.EXIT_FAIL)
    assert gate.report_path("exit", "P", projeto_exit).is_file()


# ─── check_item ──────────────────────────────────────────────────────────────

@pytest.fixture
def projeto(tmp_path: Path) -> Path:
    proj = tmp_path / "projects" / "P" / "outputs" / "tobe" / "speckit"
    (proj / "specs").mkdir(parents=True)
    (proj / "constitution.md").write_text("# constituicao\n", encoding="utf-8")
    (proj / "specs" / "spec-api.md").write_text("# api\n", encoding="utf-8")
    (proj / "vazio.md").write_text("", encoding="utf-8")
    return tmp_path


def test_arquivo_presente_e_nao_vazio(projeto: Path):
    r = gate.check_item({"path": "constitution.md", "base": "speckit"}, "P", projeto)
    assert r["present"] is True


def test_arquivo_vazio_nao_conta_como_entregue(projeto: Path):
    """Artefato de 0 byte é ausência com nome — o gate não pode aceitá-lo."""
    r = gate.check_item({"path": "vazio.md", "base": "speckit"}, "P", projeto)
    assert r["present"] is False


def test_arquivo_ausente_reporta_produtor(projeto: Path):
    r = gate.check_item(
        {"path": "traceability.json", "base": "speckit",
         "produced_by": "speckit_task_compiler.py (determinístico, não é agente)"}, "P", projeto)
    assert r["present"] is False
    assert "speckit_task_compiler.py" in r["produced_by"]


def test_diretorio_com_min_count(projeto: Path):
    ok = gate.check_item(
        {"path": "specs", "base": "speckit", "kind": "dir", "min_count": 1}, "P", projeto)
    assert ok["present"] is True
    falta = gate.check_item(
        {"path": "specs", "base": "speckit", "kind": "dir", "min_count": 7}, "P", projeto)
    assert falta["present"] is False, "7 specs são exigidas; 1 não pode passar"


def test_features_sao_validadas_contra_manifesto(projeto: Path):
    speckit = projeto / "projects" / "P" / "outputs" / "tobe" / "speckit"
    manifest = {
        "features": [
            {"feature": "001-foundation", "codegen": False},
            {"feature": "002-orders", "codegen": True},
        ]
    }
    (speckit / "wave-spec-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    foundation = speckit / "specs" / "001-foundation"
    orders = speckit / "specs" / "002-orders"
    foundation.mkdir()
    orders.mkdir()
    (foundation / "spec.md").write_text("# foundation", encoding="utf-8")
    for artifact in ("spec.md", "plan.md", "plan-graph.json", "task-fragment.json", "tasks.md"):
        (orders / artifact).write_text("{}", encoding="utf-8")
    (speckit / "specs" / "spec-api.md").unlink()

    item = {
        "path": "outputs/tobe/speckit/specs", "kind": "manifest_features",
        "manifest": "outputs/tobe/speckit/wave-spec-manifest.json",
    }
    result = gate.check_item(item, "P", projeto)
    assert result["present"] is True

    (orders / "tasks.md").unlink()
    result = gate.check_item(item, "P", projeto)
    assert result["present"] is False
    assert "002-orders/tasks.md" in result["detail"]


def test_base_workspace_resolve_da_raiz(projeto: Path):
    (projeto / "src").mkdir()
    (projeto / "src" / "x.yaml").write_text("a: 1\n", encoding="utf-8")
    r = gate.check_item({"path": "src/x.yaml", "base": "workspace"}, "P", projeto)
    assert r["present"] is True


def test_gate_aceita_wave_model_ou_wave_plan(projeto: Path):
    item = {
        "path": "wave definition", "kind": "any_file",
        "paths": [
            "outputs/tobe/migration/wave-model.json",
            "outputs/tobe/docs/wave-plan.md",
        ],
    }
    result = gate.check_item(item, "P", projeto)
    assert result["present"] is False

    plan = projeto / "projects" / "P" / "outputs" / "tobe" / "docs" / "wave-plan.md"
    plan.parent.mkdir(parents=True)
    plan.write_text("# Wave Plan", encoding="utf-8")
    result = gate.check_item(item, "P", projeto)
    assert result["present"] is True


def test_gate_reprova_quando_falta_item_e_nao_roda_as_suites(projeto: Path):
    """Reprovar duas vezes pelo mesmo motivo não ajuda ninguém a corrigir."""
    dag = {"exit_gate": {"on_fail": "block_f4",
                         "items": [{"path": "traceability.json", "base": "speckit"}],
                         "check_suites": ["speckit_traceability"]}}
    r = gate.run_gate("exit", "P", projeto, dag)
    assert r["status"] == "FAIL"
    assert r["missing"]
    assert r["check_suites"] == [], "suíte não deve rodar com artefato faltando"


# ─── kind: human_approval ────────────────────────────────────────────────────
# Presença de arquivo não é conformidade. Medido em nopcommerce-04
# (2026-08-21): a F4 foi liberada com dois blockers CRITICAL porque este gate só
# conferia que `compliance-status.json` existia.

_ITEM_APROVACAO = {
    "path": "outputs/tobe/speckit/compliance-status.json",
    "kind": "human_approval",
    "produced_by": "speckit-compliance-gate (F3S, wave6c) + decisão do operador",
}


def _com_compliance(raiz: Path, status: dict, *, checksum: str = "abc") -> None:
    speckit = raiz / "projects" / "P" / "outputs" / "tobe" / "speckit"
    speckit.mkdir(parents=True, exist_ok=True)
    (speckit / "compliance-status.json").write_text(json.dumps(status), encoding="utf-8")
    (speckit / "traceability.json").write_text(
        json.dumps({"graph_checksum": checksum}), encoding="utf-8")


def _base(verdict="BLOCKED", findings=None) -> dict:
    return {"verdict": verdict, "constitution_items": 3, "items_honored": 1,
            "findings": findings if findings is not None
            else [{"id": "F-1", "severity": "critical", "summary": "grave"}]}


def _assinatura(raiz: Path, decisao: str, **kwargs) -> None:
    sys.path.insert(0, str(REPO_ROOT / "src" / "shared" / "tools"))
    import speckit_compliance_gate as gate_tool  # noqa: PLC0415
    gate_tool.record("P", decisao, repo_root=raiz, **kwargs)


def test_aprovacao_pendente_reprova_o_item(tmp_path: Path):
    _com_compliance(tmp_path, _base())

    r = gate.check_item(_ITEM_APROVACAO, "P", tmp_path)

    assert r["present"] is False
    assert r["kind"] == "human_approval"
    assert "pending" in r["detail"]


def test_aprovacao_nominal_libera_o_item(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AVA_NTP_FORCE_FAIL", "1")   # não depende de rede
    _com_compliance(tmp_path, _base())
    _assinatura(tmp_path, "approved", name="Rafael", role="Tech Lead")

    r = gate.check_item(_ITEM_APROVACAO, "P", tmp_path)

    assert r["present"] is True
    assert "Rafael" in r["detail"]


def test_reconhecimento_automatico_libera_mas_diz_que_ninguem_revisou(
        tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AVA_NTP_FORCE_FAIL", "1")
    _com_compliance(tmp_path, _base())
    _assinatura(tmp_path, "auto_acknowledged", runner_mode="auto")

    r = gate.check_item(_ITEM_APROVACAO, "P", tmp_path)

    assert r["present"] is True
    assert "auto_acknowledged" in r["detail"]


def test_recusa_reprova_o_item(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AVA_NTP_FORCE_FAIL", "1")
    _com_compliance(tmp_path, _base())
    _assinatura(tmp_path, "rejected", name="Ana", role="QA")

    r = gate.check_item(_ITEM_APROVACAO, "P", tmp_path)

    assert r["present"] is False
    assert "rejected" in r["detail"]


def test_assinatura_expirada_reprova_o_item(tmp_path: Path, monkeypatch):
    """Assinatura antiga não cobre achado novo."""
    monkeypatch.setenv("AVA_NTP_FORCE_FAIL", "1")
    _com_compliance(tmp_path, _base())
    _assinatura(tmp_path, "approved", name="Rafael", role="Tech Lead")

    speckit = tmp_path / "projects" / "P" / "outputs" / "tobe" / "speckit"
    status = json.loads((speckit / "compliance-status.json").read_text(encoding="utf-8"))
    status["findings"].append({"id": "F-9", "severity": "critical", "summary": "novo"})
    (speckit / "compliance-status.json").write_text(json.dumps(status), encoding="utf-8")

    r = gate.check_item(_ITEM_APROVACAO, "P", tmp_path)

    assert r["present"] is False
    assert "expired" in r["detail"]


def test_projeto_sem_achado_critico_nao_exige_decisao(tmp_path: Path):
    """O gate não pode pedir assinatura onde não há o que assinar."""
    _com_compliance(tmp_path, _base(verdict="APPROVED", findings=[]))

    r = gate.check_item(_ITEM_APROVACAO, "P", tmp_path)

    assert r["present"] is True
    assert "not_required" in r["detail"]


def test_item_de_aprovacao_orienta_a_decidir_e_nao_a_gerar_arquivo(capsys):
    """Dizer "gere-o" manda procurar arquivo quando o que falta é decidir."""
    gate._print({
        "gate": "exit", "project": "P", "status": "FAIL", "on_fail": "block_f4",
        "items": [], "check_suites": [], "traceability_checksum_ok": True,
        "missing": [{**_ITEM_APROVACAO, "resolved": "/x", "present": False,
                     "detail": "pending"}],
    })

    saida = capsys.readouterr().out
    assert "Falta a DECISÃO do operador" in saida
    assert "Artefatos externos obrigatórios ausentes" not in saida
