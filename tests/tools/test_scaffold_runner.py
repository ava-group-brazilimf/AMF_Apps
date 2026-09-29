"""Integração da fase de scaffold: ordem, falhas, gate e retomada.

Generator e verifier reais são substituídos por stubs em disco (limites
externos: SDK .NET e Angular CLI). O que estes testes exercitam é o CONTRATO do
runner — ordem frontend→backend, bloqueio de coder, transições de estado,
baseline só com os dois compilando — que é onde os defeitos moravam.

Os builds de verdade ficam em `test_scaffold_generators_integration.py`.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "src" / "shared" / "tools"
sys.path.insert(0, str(TOOLS))

import scaffold_runner as sr  # noqa: E402
import scaffold_state as st  # noqa: E402

CONFIG = """\
project_name: "P"
tobe_stack:
  frontend_framework: "angular"
  frontend_version: "17"
  backend_framework: "dotnet"
  backend_version: "8.0"
"""


def _stub(path: Path, *, sucesso: bool, escreve: Path | None = None,
          payload_extra: str = "") -> None:
    """Gera um script Python que imita um generator/verifier do repo."""
    escrita = ""
    if escreve is not None:
        escrita = (
            f"    alvo = Path(r'{escreve}')\n"
            "    alvo.mkdir(parents=True, exist_ok=True)\n"
            "    (alvo / 'marker.txt').write_text('x', encoding='utf-8')\n"
        )
    path.write_text(
        "import json, sys\n"
        "from pathlib import Path\n"
        "def main():\n"
        f"{escrita}"
        "    payload = {"
        f"'success': {sucesso!r}, 'status': {'\"PASS\"' if sucesso else '\"ERROR\"'}, "
        "'errors': []" + ("" if sucesso else ", 'error': 'stub falhou'") +
        (", " + payload_extra if payload_extra else "") +
        ", 'warnings': [], 'files_written': ['a'], 'files_skipped': []}\n"
        "    print(json.dumps(payload))\n"
        f"    return {0 if sucesso else 1}\n"
        "raise SystemExit(main())\n",
        encoding="utf-8")


@pytest.fixture()
def bancada(tmp_path: Path, monkeypatch):
    """Workspace com scaffolds falsos apontando para stubs dentro da allowlist."""
    ws = tmp_path / "ws"
    projeto = ws / "projects" / "P"
    (projeto / "context").mkdir(parents=True)
    (projeto / "outputs" / "tobe").mkdir(parents=True)
    (projeto / "context" / "project-config.yaml").write_text(CONFIG, encoding="utf-8")

    tobe = projeto / "outputs" / "tobe"
    scaffolds = tmp_path / "scaffolds"
    scaffolds.mkdir()
    stubs = TOOLS / "_test_stubs"
    stubs.mkdir(exist_ok=True)
    templates = REPO_ROOT / "src" / "shared" / "templates"

    criados: list[Path] = []

    def montar(componente: str, stack: str, *, gerar_ok=True, verificar_ok=True):
        gen = stubs / f"_stub_gen_{componente}.py"
        ver = stubs / f"_stub_ver_{componente}.py"
        destino = tobe / "source-code" / componente
        _stub(gen, sucesso=gerar_ok, escreve=destino if gerar_ok else None)
        _stub(ver, sucesso=verificar_ok,
              payload_extra="'build_status': 'succeeded', 'restore_status': 'succeeded'"
              if verificar_ok else "'build_status': 'failed'")
        criados.extend([gen, ver])
        tpl = "angular-scaffold" if componente == "frontend" else "dotnet-scaffold"
        (scaffolds / f"{stack}-scaffold.md").write_text(
            "---\n"
            f"component_type: {componente}\n"
            f"stack: {stack}\n"
            f"generator: src/shared/tools/_test_stubs/{gen.name}\n"
            f"verifier: src/shared/tools/_test_stubs/{ver.name}\n"
            f"template_path: src/shared/templates/{tpl}\n"
            "---\n\n# stub\n", encoding="utf-8")

    monkeypatch.setattr(sr, "SCAFFOLDS_DIR", scaffolds)
    assert templates.is_dir()
    yield {"ws": ws, "projeto": projeto, "tobe": tobe, "montar": montar}

    for arquivo in criados:
        arquivo.unlink(missing_ok=True)
    try:
        stubs.rmdir()
    except OSError:
        pass


def _rodar(bancada, **kw):
    """Roda a fase em modo estrito por padrão (approval_timeout_s=0).

    A política de produção aprova sozinha após 60s. Nos testes que exercitam
    OUTRA coisa — ordem, falhas, baseline, retomada — a aprovação automática
    só embaralharia o que está sendo verificado. Os testes do gate em si
    passam o prazo explicitamente.
    """
    kw.setdefault("approval_timeout_s", 0)
    return sr.run_scaffold_phase("P", bancada["ws"], interactive=False, **kw)


# ── Ordem e caminhos ───────────────────────────────────────────────────────

def test_frontend_e_gerado_antes_do_backend(bancada, monkeypatch):
    """CA-001 / RF-002 — a ordem é do código, não da interpretação."""
    bancada["montar"]("frontend", "angular")
    bancada["montar"]("backend", "dotnet")

    ordem: list[str] = []
    original = sr.run_component

    def espiao(*args, **kwargs):
        ordem.append(kwargs["component_type"])
        return original(*args, **kwargs)

    monkeypatch.setattr(sr, "run_component", espiao)
    _rodar(bancada)
    assert ordem == ["frontend", "backend"]


def test_cada_componente_escreve_no_caminho_canonico(bancada):
    """CA-017 / CA-019 — nada em source-code/{stack}."""
    bancada["montar"]("frontend", "angular")
    bancada["montar"]("backend", "dotnet")
    _rodar(bancada)

    source = bancada["tobe"] / "source-code"
    assert (source / "frontend" / "marker.txt").is_file()
    assert (source / "backend" / "marker.txt").is_file()
    assert not (source / "angular").exists()
    assert not (source / "dotnet").exists()


def test_task_state_registra_componente_stack_e_caminho(bancada):
    """CA-005 / CA-023 / CA-024."""
    bancada["montar"]("frontend", "angular")
    bancada["montar"]("backend", "dotnet")
    _rodar(bancada)

    estado = st.load_state(bancada["projeto"], "P")
    frente = estado["tasks"]["T-SCAFFOLD-FRONTEND-001"]
    fundo = estado["tasks"]["T-SCAFFOLD-BACKEND-001"]
    assert frente["component_type"] == "frontend" and frente["stack"] == "angular"
    assert frente["output_path"] == "source-code/frontend"
    assert fundo["component_type"] == "backend" and fundo["stack"] == "dotnet"
    assert fundo["output_path"] == "source-code/backend"
    assert frente["status"] == fundo["status"] == st.COMPLETED


# ── Falhas ─────────────────────────────────────────────────────────────────

def test_falha_no_frontend_impede_o_backend(bancada):
    """CA-011 — não adianta compilar metade do sistema."""
    bancada["montar"]("frontend", "angular", verificar_ok=False)
    bancada["montar"]("backend", "dotnet")

    saida = _rodar(bancada)

    assert saida["coders_released"] is False
    assert "backend" not in saida["components"]
    assert not (bancada["tobe"] / "source-code" / "backend" / "marker.txt").exists()
    estado = st.load_state(bancada["projeto"], "P")
    assert estado["tasks"]["T-SCAFFOLD-FRONTEND-001"]["status"] == st.FAILED
    assert "T-SCAFFOLD-BACKEND-001" not in estado["tasks"]


def test_falha_no_backend_preserva_frontend_e_nao_cria_baseline(bancada):
    """CA-012."""
    bancada["montar"]("frontend", "angular")
    bancada["montar"]("backend", "dotnet", verificar_ok=False)

    saida = _rodar(bancada)

    assert saida["coders_released"] is False
    assert (bancada["tobe"] / "source-code" / "frontend" / "marker.txt").is_file()
    assert not (bancada["tobe"] / "source-code" / ".git").exists()
    assert saida["baseline"] is None
    estado = st.load_state(bancada["projeto"], "P")
    assert estado["tasks"]["T-SCAFFOLD-FRONTEND-001"]["status"] == st.COMPLETED
    assert estado["tasks"]["T-SCAFFOLD-BACKEND-001"]["status"] == st.FAILED


def test_limite_de_tres_tentativas(bancada):
    """RF-011 — depois da última, falha controlada; sem gate e sem coder."""
    bancada["montar"]("frontend", "angular", verificar_ok=False)
    bancada["montar"]("backend", "dotnet")

    saida = _rodar(bancada)

    estado = st.load_state(bancada["projeto"], "P")
    assert estado["tasks"]["T-SCAFFOLD-FRONTEND-001"]["attempts"] == sr.MAX_ATTEMPTS == 3
    assert saida["approval"] is None
    assert saida["coders_released"] is False


def test_generator_que_falha_nao_avanca_para_verificacao(bancada):
    bancada["montar"]("frontend", "angular", gerar_ok=False)
    bancada["montar"]("backend", "dotnet")

    _rodar(bancada)

    registro = st.load_state(bancada["projeto"], "P")["tasks"]["T-SCAFFOLD-FRONTEND-001"]
    assert registro["status"] == st.FAILED
    assert registro["verification_status"] == "not_reached"


# ── Gate humano ────────────────────────────────────────────────────────────

def test_modo_estrito_sem_decisao_fica_em_espera(bancada):
    """`approval_timeout_s=0` preserva o bloqueio por ausência de resposta."""
    bancada["montar"]("frontend", "angular")
    bancada["montar"]("backend", "dotnet")

    saida = _rodar(bancada, approval_timeout_s=0)

    assert saida["approval"]["status"] == st.AWAITING_USER_APPROVAL
    assert saida["coders_released"] is False
    assert not sr.coders_released("P", bancada["ws"])


def test_execucao_sem_terminal_aprova_automaticamente(bancada):
    """Política vigente: esteira automática despacha os coders sozinha.

    Inverte o CA-009 original a pedido explícito. O que a implementação
    preserva é a RASTREABILIDADE: fica gravado que a decisão foi automática.
    """
    bancada["montar"]("frontend", "angular")
    bancada["montar"]("backend", "dotnet")

    saida = _rodar(bancada, approval_timeout_s=60)

    assert saida["approval"]["status"] == st.APPROVED
    assert saida["coders_released"] is True
    assert sr.coders_released("P", bancada["ws"])


def test_aprovacao_automatica_e_distinguivel_de_decisao_humana(bancada):
    """Auditoria precisa separar "alguém revisou" de "o prazo venceu"."""
    bancada["montar"]("frontend", "angular")
    bancada["montar"]("backend", "dotnet")

    _rodar(bancada, approval_timeout_s=60)
    automatica = st.load_state(bancada["projeto"], "P")["approval"]

    assert automatica["status"] == st.APPROVED
    assert automatica["auto_approved"] is True
    assert automatica["decided_by"] == "non-interactive"
    assert automatica["user"] is None, (
        "decisão automática não pode ser atribuída a uma pessoa")
    assert "automaticamente" in (automatica.get("note") or "")


def test_decisao_humana_registra_autor_e_nao_marca_auto(bancada):
    bancada["montar"]("frontend", "angular")
    bancada["montar"]("backend", "dotnet")

    _rodar(bancada, decision="approve")
    registro = st.load_state(bancada["projeto"], "P")["approval"]

    assert registro["decided_by"] == "user"
    assert registro["auto_approved"] is False
    assert registro["user"]


def test_aprovacao_automatica_nunca_rejeita_sozinha(bancada):
    """O automatismo só aprova. Rejeição continua exigindo ato explícito."""
    bancada["montar"]("frontend", "angular")
    bancada["montar"]("backend", "dotnet")

    saida = _rodar(bancada, approval_timeout_s=60)
    assert saida["approval"]["status"] != st.REJECTED


def test_aprovacao_explicita_libera_os_coders(bancada):
    """CA-006 / CA-007."""
    bancada["montar"]("frontend", "angular")
    bancada["montar"]("backend", "dotnet")

    saida = _rodar(bancada, decision="approve")

    assert saida["approval"]["status"] == st.APPROVED
    assert saida["coders_released"] is True
    assert sr.coders_released("P", bancada["ws"])


def test_rejeicao_bloqueia_e_e_resultado_controlado(bancada):
    """CA-008 / RF-010 — rejeição não é falha técnica."""
    bancada["montar"]("frontend", "angular")
    bancada["montar"]("backend", "dotnet")

    saida = _rodar(bancada, decision="reject")

    assert saida["approval"]["status"] == st.REJECTED
    assert saida["coders_released"] is False
    assert saida["success"] is True
    estado = st.load_state(bancada["projeto"], "P")
    assert estado["downstream"]["status"] == st.BLOCKED
    # Scaffolds preservados.
    assert (bancada["tobe"] / "source-code" / "frontend" / "marker.txt").is_file()


# ── Baseline ───────────────────────────────────────────────────────────────

def test_baseline_contem_os_dois_componentes(bancada):
    """CA-013 / CA-025."""
    bancada["montar"]("frontend", "angular")
    bancada["montar"]("backend", "dotnet")

    saida = _rodar(bancada, decision="approve")

    assert saida["baseline"]["commit_sha"]
    raiz = bancada["tobe"] / "source-code"
    listado = subprocess.run(["git", "ls-files"], cwd=str(raiz),
                             capture_output=True, text=True, check=False).stdout
    assert "frontend/marker.txt" in listado
    assert "backend/marker.txt" in listado


def test_baseline_e_recusado_com_diretorio_legado_de_tecnologia(bancada):
    """CA-025 — commitar `source-code/angular/` congelaria a duplicidade."""
    bancada["montar"]("frontend", "angular")
    bancada["montar"]("backend", "dotnet")
    legado = bancada["tobe"] / "source-code" / "angular"
    legado.mkdir(parents=True)
    (legado / "old.ts").write_text("//", encoding="utf-8")

    saida = _rodar(bancada)

    assert saida["baseline"]["error"]
    assert "angular" in saida["baseline"]["error"]
    assert saida["coders_released"] is False


def test_repositorio_existente_preserva_historico(bancada):
    bancada["montar"]("frontend", "angular")
    bancada["montar"]("backend", "dotnet")
    raiz = bancada["tobe"] / "source-code"
    raiz.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=str(raiz), capture_output=True, check=False)
    (raiz / "PREEXISTENTE.md").write_text("antes", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=str(raiz), capture_output=True, check=False)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-m", "anterior"], cwd=str(raiz),
                   capture_output=True, check=False)

    saida = _rodar(bancada, decision="approve")

    assert saida["baseline"]["existing_repo"] is True
    log = subprocess.run(["git", "log", "--oneline"], cwd=str(raiz),
                         capture_output=True, text=True, check=False).stdout
    assert "anterior" in log, "histórico anterior destruído"
    assert len(log.strip().splitlines()) >= 2


# ── Retomada / idempotência ────────────────────────────────────────────────

def test_retomada_reaproveita_scaffold_valido_e_reapresenta_o_gate(bancada):
    """CA-010 — não recria o que está válido; volta a pedir a decisão."""
    bancada["montar"]("frontend", "angular")
    bancada["montar"]("backend", "dotnet")
    primeira = _rodar(bancada)
    assert primeira["approval"]["status"] == st.AWAITING_USER_APPROVAL

    segunda = _rodar(bancada)

    assert segunda["components"]["frontend"]["reused"] is True
    assert segunda["components"]["backend"]["reused"] is True
    assert segunda["approval"]["status"] == st.AWAITING_USER_APPROVAL
    assert segunda["coders_released"] is False


def test_artefato_apagado_forca_regeneracao(bancada):
    """RF-012 — estado sozinho não basta."""
    bancada["montar"]("frontend", "angular")
    bancada["montar"]("backend", "dotnet")
    _rodar(bancada)

    import shutil
    shutil.rmtree(bancada["tobe"] / "source-code" / "frontend")

    segunda = _rodar(bancada)
    assert segunda["components"]["frontend"]["reused"] is False
    assert (bancada["tobe"] / "source-code" / "frontend" / "marker.txt").is_file()


def test_aprovacao_nao_e_reapresentada_apos_aprovada(bancada):
    bancada["montar"]("frontend", "angular")
    bancada["montar"]("backend", "dotnet")
    _rodar(bancada, decision="approve")

    segunda = _rodar(bancada)
    assert segunda["approval"]["status"] == st.APPROVED
    assert segunda["coders_released"] is True


# ── Configuração ───────────────────────────────────────────────────────────

def test_stack_sem_scaffold_determinístico_falha_sem_gerar(bancada):
    bancada["montar"]("frontend", "angular")
    # backend `dotnet` sem arquivo de scaffold
    saida = _rodar(bancada)
    assert saida["coders_released"] is False
    assert any("backend" in erro for erro in saida["errors"])


def test_config_sem_framework_falha_antes_de_qualquer_escrita(bancada):
    (bancada["projeto"] / "context" / "project-config.yaml").write_text(
        "project_name: P\ntobe_stack:\n  backend_framework: dotnet\n", encoding="utf-8")
    with pytest.raises(sr.ScaffoldRunnerError, match="frontend_framework"):
        _rodar(bancada)
    assert not (bancada["tobe"] / "source-code").exists()


def test_blueprint_de_outro_projeto_reprova_antes_do_scaffold(bancada):
    blueprint = bancada["projeto"] / "outputs" / "tobe" / "architecture-blueprint.md"
    blueprint.write_text(
        "> **Project**: outro-projeto\n\n"
        "## Bounded Contexts TO-BE\n\n"
        "| BC | Name |\n|----|------|\n| BC-01 | Catalog |\n",
        encoding="utf-8",
    )

    with pytest.raises(sr.ScaffoldRunnerError, match="outro-projeto"):
        sr.resolve_bounded_contexts(bancada["projeto"])
