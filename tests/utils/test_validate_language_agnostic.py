"""
Testes do lint de neutralidade de linguagem (specs/033).

O alvo contratual desta spec é `AGENTS.md`: ele é herdado por **todos** os agentes,
em todas as fases, para qualquer linguagem legada. Uma constante de tecnologia ali
contamina a esteira inteira.

Os wrappers em `.github/agents/` herdam a `description` da spec canônica, e várias
delas já nomeiam tecnologia (`ava-qa-behavior-mapping` cita Delphi,
`ava-tobe-designer-system` cita Angular). Essa dívida está mapeada em
`specs/033-agent-isolation-context-engineering/spec.md` § 7 como follow-on — por
isso o lint roda em `--report` sobre os wrappers e em `--strict` sobre o AGENTS.md.

    python -m pytest tests/utils/test_validate_language_agnostic.py -q
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "src" / "shared" / "utils" / "validate_language_agnostic.py"

_spec = importlib.util.spec_from_file_location("validate_language_agnostic", MODULE_PATH)
lint = importlib.util.module_from_spec(_spec)
sys.modules["validate_language_agnostic"] = lint
_spec.loader.exec_module(lint)


# ─── O contrato desta spec ───────────────────────────────────────────────────

def test_agents_md_nao_tem_nenhuma_constante_de_tecnologia():
    """Gate duro: `AGENTS.md` serve delphi, java, .net e o que vier."""
    violacoes = lint.scan(lint.iter_files(["AGENTS.md"]))
    assert not violacoes, (
        "AGENTS.md nomeia tecnologia — resolva por `legacy_technology`: "
        f"{[(v['line'], v['technology']) for v in violacoes]}"
    )


def test_corpo_gerado_dos_wrappers_e_neutro():
    """A dívida herdada vive na `description` (linha 3). O corpo — que é o que
    este projeto gera — não pode introduzir tecnologia nova."""
    arquivos = lint.iter_files([".github/agents"])
    fora_da_description = [
        v for v in lint.scan(arquivos)
        if v["line"] > 3 and not str(v["path"]).endswith("speckit.agent-context.update.agent.md")
    ]
    assert not fora_da_description, (
        "corpo gerado de wrapper nomeia tecnologia: "
        f"{[(v['path'], v['line'], v['technology']) for v in fora_da_description]}"
    )


# ─── Comportamento do lint ───────────────────────────────────────────────────

def test_allowlist_isenta_agente_de_tecnologia_especifica():
    """`ava-asis-solution-delphi` **precisa** nomear a linguagem dele."""
    assert lint.is_allowlisted(".github/agents/ava-asis-solution-delphi.agent.md")
    assert lint.is_allowlisted(".github/agents/speckit.plan.agent.md")
    assert not lint.is_allowlisted(".github/agents/ava-asis-inventory.agent.md")
    assert not lint.is_allowlisted("AGENTS.md")


def test_placeholder_de_runtime_nao_e_violacao(tmp_path):
    """`ast-raw/{language}/` é resolução em runtime, não constante."""
    alvo = tmp_path / "amostra.md"
    alvo.write_text(
        "Leia `outputs/asis/ast-raw/{language}/compressed/`.\n"
        "Resolva por `project-config.yaml -> legacy_technology`.\n",
        encoding="utf-8",
    )
    assert not lint.scan([alvo])


def test_deteccao_nao_casa_dentro_de_palavra(tmp_path):
    """`javascript` não é `java`; `.NET` isolado é."""
    alvo = tmp_path / "amostra.md"
    alvo.write_text("Use javascript e typescript.\n", encoding="utf-8")
    assert not lint.scan([alvo])

    alvo.write_text("Gera projeto .NET com EF Core.\n", encoding="utf-8")
    achados = {v["technology"] for v in lint.scan([alvo])}
    assert "dotnet" in achados and "efcore" in achados


def test_detecta_tecnologia_legada_em_regra_geral(tmp_path):
    alvo = tmp_path / "amostra.md"
    alvo.write_text("Todo agente deve varrer os arquivos Delphi (.pas).\n", encoding="utf-8")
    achados = {v["technology"] for v in lint.scan([alvo])}
    assert "delphi" in achados and "pascal" in achados
