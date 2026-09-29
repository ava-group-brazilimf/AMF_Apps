"""
Testes da flag `--agent` no lado do runner (`ava-pipeline-runner-cli.py`, specs/043).

O runner importa `msvcrt` no topo e monta estado global ao carregar — importá-lo
num teste não é viável. As funções sob teste são extraídas por AST e executadas
contra um namespace com o despacho e o console substituídos, mesmo recorte de
`test_runner_approval_gate.py`.

O que estes testes protegem
---------------------------
* **O modo interativo.** `_parse_cli([])` tem de devolver tudo `None`/`False`.
  Um default acidental em `--agent` transformaria toda execução sem argumentos
  num despacho avulso.
* **A precedência de `load_skill`.** `spec_path=None` cai no caminho original;
  com `spec_path`, lê aquele arquivo e ignora a heurística — que para
  `ava-tobe-migration-plan` carrega um doc do Playwright de `node_modules`.
* **O estado do runner.** O despacho avulso NÃO pode chamar
  `_save_runner_state`, `_write_status_html` nem `_write_remediation_report`:
  gravar estado de um passo só sobrescreveria a retomada de um run real.
  `write_execution_metrics` é a exceção deliberada: um despacho avulso consome
  tanta inferência quanto uma fase da esteira, e o relatório de métricas é
  próprio dele — não compartilha arquivo com a retomada.

    python -m pytest tests/tools/test_runner_agent_flag.py -q
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
import textwrap
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PY = REPO_ROOT / "ava-pipeline-runner-cli.py"

_FUNCOES = ("_parse_cli", "load_skill", "_listar_agentes_cli",
            "_despachar_agente_unico", "_agent_cli",
            # `_despachar_agente_unico` consulta o predicado para decidir o exit
            # code: fase SpecKit é non-blocking e sai 0 mesmo com val_ok=False.
            "_is_speckit_nonblocking", "_speckit_nonblocking_step")
_CONSTANTES = ("AGENT_SKILL_OVERRIDE", "CTX_SKILL",
               "SPECKIT_PHASE_PREFIX", "SPECKIT_AGENT_PREFIXES")


def _compilar() -> object:
    arvore = ast.parse(RUNNER_PY.read_text(encoding="utf-8"))
    corpo = [
        no for no in arvore.body
        if (isinstance(no, ast.FunctionDef) and no.name in _FUNCOES)
        or (isinstance(no, ast.Assign) and any(
            isinstance(alvo, ast.Name) and alvo.id in _CONSTANTES
            for alvo in no.targets))
        # constantes anotadas (`X: dict = {...}`) sao AnnAssign, nao Assign
        or (isinstance(no, ast.AnnAssign) and isinstance(no.target, ast.Name)
            and no.target.id in _CONSTANTES)
    ]
    encontradas = {no.name for no in corpo if isinstance(no, ast.FunctionDef)}
    assert encontradas == set(_FUNCOES), sorted(set(_FUNCOES) - encontradas)
    return compile(ast.Module(body=corpo, type_ignores=[]), "<runner>", "exec")


_CODIGO = _compilar()


class _Espiao:
    """Contador de chamadas — o que prova que o estado não foi tocado."""

    def __init__(self, retorno=None):
        self.chamadas: list[tuple] = []
        self.retorno = retorno

    def __call__(self, *a, **kw):
        self.chamadas.append((a, kw))
        # BaseException, nao Exception: KeyboardInterrupt e SystemExit ficam
        # de fora de `Exception` — foi assim que o SystemExit do runner
        # escapava do handler e matava o processo (ISSUE-004, D5).
        if isinstance(self.retorno, BaseException):
            raise self.retorno
        return self.retorno


@pytest.fixture
def ns(tmp_path):
    """Namespace novo por teste — `fn.__globals__ is ns`, então trocar uma
    chave redireciona todas as chamadas sem tocar nos call sites."""
    sys.path.insert(0, str(REPO_ROOT / "src" / "shared" / "tools"))
    import runner_agent_cli

    local: dict = {
        "argparse": argparse, "textwrap": textwrap, "json": json, "sys": sys,
        "time": time,
        "Path": Path, "WORKSPACE": REPO_ROOT,
        "BOLD": "", "DIM": "", "RESET": "", "RED": "", "YELLOW": "",
        "GREEN": "", "CYAN": "", "MAGENTA": "",
        "PIPELINE": [
            {"phase": "F2", "label": "TO-BE", "agent": "ava-tobe-orchestrator",
             "trigger": "SD"},
            {"phase": "F2b", "label": "DevOps Plan",
             "agent": "ava-devops-orchestrator", "trigger": "DP"},
            {"phase": "F5", "label": "DevOps Exec",
             "agent": "ava-devops-orchestrator", "trigger": "DE"},
        ],
        "DEPLOYMENT": "claude-sonnet-4-6",
        "PROVIDER": "anthropic",
        "ENDPOINT": "https://a", "ENDPOINT_OPENAI": "https://o",
        "API_KEY_FILE": tmp_path / "key",
        "SKILLS_PATH": tmp_path / "skills",
        "banner": lambda *a, **k: None,
        "list_projects": lambda: ["meu-erp-03", "nopcommerce-04"],
        "build_prompt": lambda ag, tg, pr, ft=None: (
            f"@{ag}" + (f" | {tg}" if tg else "") + f" project: {pr}"
            + (f" | feature: {ft}" if ft else "")),
        "preflight_step_inputs": lambda p, s: (True, "", []),
        "explain_failure": lambda s, e, p: f"FALHA TRATADA: {e}",
        "setup_headroom_mode": lambda p: ("https://hr", None),
        "headroom_proxy_url": lambda: "https://hr",
        "headroom_proxy_alive": lambda u: False,
        "_headroom_client_url": lambda u: u,
        "anthropic": type("M", (), {"Anthropic": staticmethod(
            lambda **kw: object())})(),
        "run_step": _Espiao({"val_ok": True, "artifacts": 3}),
        "_save_runner_state": _Espiao(),
        "_write_status_html": _Espiao(),
        "_write_remediation_report": _Espiao(),
        # Métricas do despacho avulso: gravadas, ao contrário do estado da
        # esteira. O espião guarda os kwargs para as asserções de contrato.
        "write_execution_metrics": _Espiao(None),
        "EXEC_MODE_MANUAL": "manual",
        "_phase_identity": lambda passo: str(
            passo.get("phase") or passo.get("agent") or "unknown"),
        "runner_agent_cli": runner_agent_cli,
        "AGENT_SKILL_OVERRIDE": {},
        "CTX_SKILL": 500_000,
    }
    (tmp_path / "key").write_text("chave-falsa", encoding="utf-8")
    exec(_CODIGO, local)
    return local


# ─── _parse_cli — o guardião do modo interativo ──────────────────────────────

def test_sem_argumentos_nada_e_ativado(ns):
    """O teste mais importante do arquivo: execução sem args continua interativa."""
    args = ns["_parse_cli"]([])
    assert args.agent is None
    assert args.project is None
    assert args.list_agents is False
    assert args.dry_run is False
    assert args.force_single is False


def test_agent_e_project_sao_lidos(ns):
    args = ns["_parse_cli"](["--agent", "ava-x", "-p", "proj"])
    assert args.agent == "ava-x"
    assert args.project == "proj"


def test_flags_longas_com_igual(ns):
    args = ns["_parse_cli"](["--agent=ava-x", "--project=proj", "--phase=F5"])
    assert (args.agent, args.project, args.phase) == ("ava-x", "proj", "F5")


# ─── load_skill — precedência ────────────────────────────────────────────────

def test_load_skill_sem_spec_path_nao_muda_de_caminho(ns, tmp_path):
    """`spec_path=None` é o caminho interativo — não pode ler nada novo."""
    ns["SKILLS_PATH"] = tmp_path / "skills"
    conteudo = ns["load_skill"]("agente-que-nao-existe")
    assert "spec_path" not in conteudo


def test_load_skill_com_spec_path_le_o_arquivo(ns, tmp_path):
    alvo = tmp_path / "spec.md"
    alvo.write_text("# spec canonica do agente", encoding="utf-8")
    assert ns["load_skill"]("qualquer", spec_path=str(alvo)) == "# spec canonica do agente"


def test_load_skill_spec_path_inexistente_degrada(ns, tmp_path):
    """Caminho ruim avisa e cai na heurística — nunca levanta."""
    conteudo = ns["load_skill"]("qualquer", spec_path=str(tmp_path / "nao-existe.md"))
    assert isinstance(conteudo, str)


def test_override_ganha_do_spec_path(ns, tmp_path):
    """AGENT_SKILL_OVERRIDE é curadoria explícita multi-arquivo; a spec única
    do registry é mais pobre para esses agentes."""
    curado = tmp_path / "curado.md"
    curado.write_text("conteudo curado", encoding="utf-8")
    outro = tmp_path / "outro.md"
    outro.write_text("conteudo do registry", encoding="utf-8")
    ns["AGENT_SKILL_OVERRIDE"] = {"ava-multi": [str(curado.relative_to(REPO_ROOT))
                                                if False else "curado.md"]}
    ns["WORKSPACE"] = tmp_path
    conteudo = ns["load_skill"]("ava-multi", spec_path=str(outro))
    assert "curado" in conteudo


# ─── _despachar_agente_unico ─────────────────────────────────────────────────

def _args(**kw):
    base = dict(agent=None, project=None, phase=None, trigger=None, feature=None,
                model=None, headroom=False, force_single=False, dry_run=False,
                list_agents=False, json=False)
    base.update(kw)
    return argparse.Namespace(**base)


def test_agent_sem_project_sai_2(ns, capsys):
    assert ns["_despachar_agente_unico"](_args(agent="ava-x")) == 2
    assert "exige -p" in capsys.readouterr().err


def test_projeto_inexistente_sai_2(ns, capsys):
    codigo = ns["_despachar_agente_unico"](_args(agent="ava-x", project="nao-existe"))
    assert codigo == 2
    assert "PROJETO NÃO ENCONTRADO" in capsys.readouterr().err


def test_ambiguo_sai_2_sem_despachar(ns, capsys):
    codigo = ns["_despachar_agente_unico"](
        _args(agent="ava-devops-orchestrator", project="meu-erp-03"))
    assert codigo == 2
    assert "AMBÍGUO" in capsys.readouterr().err
    assert ns["run_step"].chamadas == [], "resolveu errado e ainda assim despachou"


def test_dry_run_nao_despacha(ns):
    codigo = ns["_despachar_agente_unico"](
        _args(agent="ava-tobe-orchestrator", project="meu-erp-03", dry_run=True))
    assert codigo == 0
    assert ns["run_step"].chamadas == []


def test_caso_feliz_despacha_uma_vez_com_spec_path(ns):
    codigo = ns["_despachar_agente_unico"](
        _args(agent="ava-tobe-orchestrator", project="meu-erp-03"))
    assert codigo == 0
    assert len(ns["run_step"].chamadas) == 1
    passo = ns["run_step"].chamadas[0][0][1]
    assert passo["agent"] == "ava-tobe-orchestrator"
    assert passo["phase"] == "F2", "fase tem de vir do PIPELINE do runner"
    assert "spec_path" in passo


def test_excecao_no_run_step_vira_mensagem_tratada(ns, capsys):
    ns["run_step"] = _Espiao(RuntimeError("estourou"))
    codigo = ns["_despachar_agente_unico"](
        _args(agent="ava-tobe-orchestrator", project="meu-erp-03"))
    assert codigo == 1
    assert "FALHA TRATADA" in capsys.readouterr().err


def test_val_ok_falso_sai_1(ns):
    ns["run_step"] = _Espiao({"val_ok": False, "detail": "faltou artefato"})
    assert ns["_despachar_agente_unico"](
        _args(agent="ava-tobe-orchestrator", project="meu-erp-03")) == 1


def test_ctrl_c_sai_130(ns):
    ns["run_step"] = _Espiao(KeyboardInterrupt())
    assert ns["_despachar_agente_unico"](
        _args(agent="ava-tobe-orchestrator", project="meu-erp-03")) == 130


def test_provider_acompanha_o_modelo(ns):
    """Pulado o menu, PROVIDER ficaria velho e o payload iria para o endpoint
    errado. É falha silenciosa e cara."""
    ns["_despachar_agente_unico"](
        _args(agent="ava-tobe-orchestrator", project="meu-erp-03",
              model="luna-gpt-4o", dry_run=True))
    assert ns["PROVIDER"] == "openai"
    assert ns["DEPLOYMENT"] == "luna-gpt-4o"


# ─── Estado do runner — o que NÃO pode ser tocado ────────────────────────────

def test_despacho_avulso_nao_grava_estado_da_esteira(ns):
    ns["_despachar_agente_unico"](
        _args(agent="ava-tobe-orchestrator", project="meu-erp-03"))
    assert ns["_save_runner_state"].chamadas == [], \
        "sobrescreveria runner-state.json de um run real com uma esteira de 1 passo"
    assert ns["_write_status_html"].chamadas == []
    assert ns["_write_remediation_report"].chamadas == []


# ─── Métricas — o que TEM de ser gravado ─────────────────────────────────────

def test_despacho_avulso_grava_metricas_no_modo_manual(ns):
    """Uma execução avulsa custa inferência: o consumo precisa ficar registrado."""
    ns["_despachar_agente_unico"](
        _args(agent="ava-tobe-orchestrator", project="meu-erp-03"))
    chamadas = ns["write_execution_metrics"].chamadas
    assert len(chamadas) == 2, "esperado: uma gravação na largada, uma no fecho"

    (args_largada, kw_largada), (args_fecho, kw_fecho) = chamadas
    assert args_largada[0] == args_fecho[0] == "meu-erp-03"
    assert kw_largada["execution_mode"] == kw_fecho["execution_mode"] == "manual"
    # Mesmo id nas duas: é o mesmo run, e o arquivo é sobrescrito no lugar.
    assert kw_largada["execution_id"] == kw_fecho["execution_id"]

    # Largada: arquivo em disco antes do despacho, ainda sem fase nenhuma.
    assert kw_largada["execution_status"] == "running"
    assert kw_largada["exec_metrics"] == {}

    # Fecho: a fase aparece com as métricas reais devolvidas por run_step.
    assert kw_fecho["execution_status"] == "completed"
    assert list(kw_fecho["exec_metrics"]) == ["F2"]
    assert kw_fecho["executed"] == ["F2"]


@pytest.mark.parametrize("retorno,status,executado", [
    (RuntimeError("estourou"),                    "failed",                  False),
    (KeyboardInterrupt(),                         "interrupted",             False),
    ({"val_ok": False, "detail": "faltou"},       "completed_with_warnings", False),
    ({"val_ok": True, "artifacts": 1},            "completed",               True),
])
def test_metricas_gravadas_em_todo_desfecho(ns, retorno, status, executado):
    """Sucesso, reprovação, exceção e Ctrl+C — os quatro passam pelo `finally`."""
    ns["run_step"] = _Espiao(retorno)
    ns["_despachar_agente_unico"](
        _args(agent="ava-tobe-orchestrator", project="meu-erp-03"))
    chamadas = ns["write_execution_metrics"].chamadas
    assert len(chamadas) == 2
    kwargs = chamadas[-1][1]
    assert kwargs["execution_status"] == status
    assert kwargs["executed"] == (["F2"] if executado else [])
    assert kwargs["val_failed"] == ([] if executado else ["F2"])
    # A fase despachada nunca some do relatório, nem quando run_step estourou:
    # `phase_metrics: []` seria indistinguível de "nada foi executado".
    assert list(kwargs["exec_metrics"]) == ["F2"]


# ─── --list-agents ───────────────────────────────────────────────────────────

def test_listar_agentes_marca_ambiguo(ns, capsys):
    assert ns["_listar_agentes_cli"](_args(list_agents=True)) == 0
    assert "[ambíguo]" in capsys.readouterr().out
