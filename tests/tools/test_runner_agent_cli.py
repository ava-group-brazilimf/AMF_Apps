"""
Testes da resolução de agente avulso do runner (specs/043).

O que estes testes congelam
---------------------------
1. **A fase vem da esteira do runner, nunca do `ava-pipeline.yaml`.** Os dois
   namespaces divergem (`ava-summary` é `S1`/`S4` no runner e `F8a`/`F8c`/`F8d`
   no YAML) e `run_step` faz curto-circuito por string exata de fase. Resolver
   pelo YAML pularia o builder determinístico do Summary e queimaria uma
   inferência de 128k tokens para produzir o que um script Python já produz.
   `test_resolver_preserva_a_fase_do_runner` é o que impede alguém
   "simplificar" trocando tudo por `pipeline_plan.build_plan`.

2. **Agente ambíguo não recebe default.** `ava-devops-orchestrator` aparece em
   F2b (`DP`) e F5 (`DE`); escolher por conta própria rodaria o passo errado
   em silêncio.

3. **`spec_path` sai do registry.** Sem ele, `load_skill` cai na heurística de
   substring, que para `ava-tobe-migration-plan` carrega um doc do Playwright
   de dentro de `node_modules` — verificado.

    python -m pytest tests/tools/test_runner_agent_cli.py -q
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "shared" / "tools"
RUNNER_PY = REPO_ROOT / "ava-pipeline-runner-cli.py"
sys.path.insert(0, str(TOOLS_DIR))

import runner_agent_cli as cli  # noqa: E402


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def pipeline_real() -> list[dict]:
    """A lista `PIPELINE` literal do runner, extraída por AST.

    Sem importar o runner: ele puxa `msvcrt` no topo e monta estado global no
    import. `ast.literal_eval` basta porque `PIPELINE` é literal puro.
    """
    arvore = ast.parse(RUNNER_PY.read_text(encoding="utf-8"))
    for no in arvore.body:
        if (isinstance(no, ast.Assign)
                and any(getattr(a, "id", "") == "PIPELINE" for a in no.targets)):
            return ast.literal_eval(no.value)
    pytest.fail("PIPELINE não encontrada no runner")


@pytest.fixture
def pipeline_sintetico() -> list[dict]:
    return [
        {"phase": "F1", "label": "AS-IS", "agent": "ava-asis-orchestrator",
         "trigger": "FP"},
        {"phase": "F2b", "label": "DevOps Plan", "agent": "ava-devops-orchestrator",
         "trigger": "DP"},
        {"phase": "F5", "label": "DevOps Execute", "agent": "ava-devops-orchestrator",
         "trigger": "DE"},
    ]


# ─── Provider ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("deployment,esperado", [
    ("claude-sonnet-4-6", "anthropic"),
    ("CLAUDE-OPUS", "anthropic"),
    ("luna-gpt-4o", "openai"),
    ("gpt-4o", "openai"),
    ("", "openai"),
])
def test_resolver_provider(deployment, esperado):
    """Pulado o menu de modelo, o global PROVIDER fica velho e run_step manda
    payload Anthropic para endpoint OpenAI. Esta função é o antídoto."""
    assert cli.resolver_provider(deployment) == esperado


# ─── Tier 1 — esteira do runner ──────────────────────────────────────────────

def test_tier1_preserva_fase_trigger_e_label(pipeline_sintetico):
    passo = cli.resolver_passo(pipeline_sintetico, "proj", "ava-asis-orchestrator")
    assert passo["phase"] == "F1"
    assert passo["trigger"] == "FP"
    assert passo["ad_hoc"] is False


def test_resolver_preserva_a_fase_do_runner(pipeline_real):
    """REGRESSÃO CENTRAL — a fase é a do runner, não a do ava-pipeline.yaml.

    No YAML `ava-summary` é F8a/F8c/F8d. Se `phase` voltar como F8a, `run_step`
    não casa `phase in ("S1","S4")`, pula `_run_summary_generate_standalone` e
    gasta 128k tokens à toa.
    """
    passo = cli.resolver_passo(pipeline_real, "proj", "ava-summary", phase="S1")
    assert passo["phase"] == "S1", "fase veio do ava-pipeline.yaml — F8a mata o builder"
    assert passo["phase"] != "F8a"

    remediation = cli.resolver_passo(pipeline_real, "proj", "ava-summary-remediation")
    assert remediation["phase"] == "S2"


def test_agente_ambiguo_recusa_sem_phase(pipeline_sintetico):
    with pytest.raises(cli.AgentCLIError) as exc:
        cli.resolver_passo(pipeline_sintetico, "proj", "ava-devops-orchestrator")
    bloco = exc.value.bloco
    assert exc.value.exit_code == cli.EXIT_CONFIG
    assert "F2b" in bloco and "F5" in bloco
    assert "--phase" in bloco


def test_agente_ambiguo_resolve_com_phase(pipeline_sintetico):
    passo = cli.resolver_passo(pipeline_sintetico, "proj",
                               "ava-devops-orchestrator", phase="F5")
    assert passo["phase"] == "F5"
    assert passo["trigger"] == "DE"


def test_phase_invalida_lista_as_validas(pipeline_sintetico):
    with pytest.raises(cli.AgentCLIError) as exc:
        cli.resolver_passo(pipeline_sintetico, "proj",
                           "ava-devops-orchestrator", phase="F9")
    assert "F2b" in exc.value.bloco and "F5" in exc.value.bloco


# ─── Tier 2 — avulso pelo registry ───────────────────────────────────────────

def test_tier2_avulso_traz_spec_do_registry():
    passo = cli.resolver_passo([], "proj", "ava-tobe-migration-plan")
    assert passo["ad_hoc"] is True
    assert passo["trigger"] is None
    assert passo["inputs"] == {}
    assert passo["phase"] == "F2"
    assert passo["spec_path"].endswith("migration-plan-tobe.md")
    assert isinstance(passo["spec_path"], str), "Path no dict quebra serialização"
    assert "node_modules" not in passo["spec_path"]


def test_trigger_explicito_sobrescreve():
    passo = cli.resolver_passo([], "proj", "ava-tobe-migration-plan", trigger="WM")
    assert passo["trigger"] == "WM"


def test_feature_entra_no_passo():
    passo = cli.resolver_passo([], "proj", "ava-tobe-migration-plan",
                               feature="002-w1-core-read")
    assert passo["feature"] == "002-w1-core-read"


def test_agente_que_tinha_bom_resolve():
    """Sem a correção de `utf-8-sig` no registry, este agente não existia."""
    passo = cli.resolver_passo([], "proj", "ava-summary-remediation")
    assert passo["spec_path"].endswith("summary-remediation-agent.md")


# ─── Tier 3 — desconhecido ───────────────────────────────────────────────────

def test_agente_desconhecido_sugere_o_certo():
    with pytest.raises(cli.AgentCLIError) as exc:
        cli.resolver_passo([], "proj", "ava-tobe-migration-plna")
    bloco = exc.value.bloco
    assert "ava-tobe-migration-plan" in bloco
    assert "CAUSA RAIZ" in bloco


# ─── Validação ───────────────────────────────────────────────────────────────

def test_validar_passo_aprova_passo_completo():
    assert cli.validar_passo(cli.resolver_passo([], "p", "ava-tobe-migration-plan")) == []


@pytest.mark.parametrize("faltante", ["phase", "label", "agent"])
def test_validar_passo_reprova_campo_que_run_step_acessa_por_colchete(faltante):
    passo = cli.resolver_passo([], "p", "ava-tobe-migration-plan")
    passo.pop(faltante)
    assert any(faltante in p for p in cli.validar_passo(passo))


def test_validar_passo_reprova_trigger_ausente():
    passo = cli.resolver_passo([], "p", "ava-tobe-migration-plan")
    del passo["trigger"]
    assert any("trigger" in p for p in cli.validar_passo(passo))


# ─── Fan-out ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("passo,esperado", [
    ({"agent": "ava-speckit-specification", "phase": "F3S"}, "feature"),
    ({"agent": "ava-f4s-codegen-agent", "phase": "F4"}, "task"),
    ({"agent": "ava-tobe-migration-plan", "phase": "F2"}, ""),
])
def test_detectar_fanout(passo, esperado):
    assert cli.detectar_fanout(passo) == esperado


def test_mensagem_de_fanout_cita_a_evidencia_e_o_comando():
    passo = {"agent": "ava-speckit-specification", "phase": "F3S"}
    bloco = cli.explicar_fanout_avulso(passo, "meu-erp-03",
                                       ["001-w0-foundation", "002-w1-core-read"],
                                       "feature")
    assert "68.170" in bloco, "a evidência medida some e a recusa vira opinião"
    assert "--feature 001-w0-foundation" in bloco
    assert "--force-single" in bloco


def test_mensagem_de_fanout_sem_escopo_instrui_a_fase_produtora():
    bloco = cli.explicar_fanout_avulso({"agent": "x", "phase": "F3S"},
                                       "p", [], "feature")
    assert "manifesto de waves" in bloco


# ─── Mensagens ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("bloco", [
    cli.explicar_projeto_inexistente("meu-erp-3", ["meu-erp-03", "nopcommerce-04"]),
    cli.explicar_agente_desconhecido("xpto", [], "p"),
    cli.explicar_agente_ambiguo("a", [{"phase": "F1", "trigger": "T", "label": "L"}], "p"),
    cli.explicar_passo_invalido("a", ["problema"], "p"),
])
def test_toda_mensagem_tem_causa_raiz(bloco):
    assert "CAUSA RAIZ" in bloco


def test_projeto_inexistente_sugere_o_parecido():
    bloco = cli.explicar_projeto_inexistente("meu-erp-3", ["meu-erp-03", "outro"])
    assert "-p meu-erp-03" in bloco


def test_listar_agentes_marca_os_ambiguos(pipeline_sintetico):
    saida = cli.listar_agentes(pipeline_sintetico)
    assert "ava-devops-orchestrator" in saida
    assert "[ambíguo]" in saida


# ─── CLI ─────────────────────────────────────────────────────────────────────

def test_main_projeto_inexistente_sai_2(capsys):
    assert cli._main(["--agent", "ava-tobe-migration-plan",
                      "-p", "projeto-que-nao-existe"]) == cli.EXIT_CONFIG
    assert "PROJETO NÃO ENCONTRADO" in capsys.readouterr().err


def test_main_agente_desconhecido_sai_2(capsys):
    projetos = sorted(p.name for p in (REPO_ROOT / "projects").iterdir() if p.is_dir())
    assert cli._main(["--agent", "nao-existe-mesmo", "-p", projetos[0]]) == cli.EXIT_CONFIG
    assert "AGENTE DESCONHECIDO" in capsys.readouterr().err
