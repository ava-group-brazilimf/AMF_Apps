"""Contrato de resposta dos coders — `src/shared/tools/f4_agent_result.py`.

A regra que estes testes fixam: o contrato é **evidência de execução**, nunca
autoridade de status. `implementation_status: completed` é uma afirmação do
modelo; `verified` continua saindo só do exit code real do build.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "shared" / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import f4_agent_result as contrato
import f4_routing


TASK = {"task_id": "T-010", "task_type": "backend", "target_stack": "dotnet",
        "verify_command": "dotnet build", "feature": "002-carrinho"}


@pytest.fixture()
def rota(tmp_path: Path):
    return f4_routing.resolve_route(TASK, "P", tmp_path)


def _resposta(payload: dict) -> str:
    return ("bla bla\n<!-- F4_RESULT -->\n```json\n"
            + json.dumps(payload) + "\n```\n<!-- /F4_RESULT -->\n")


def _payload(**overrides) -> dict:
    base = {
        "schema_version": "1.0.0",
        "task_id": "T-010",
        "task_type": "backend",
        "target_stack": "dotnet",
        "agent": "ava-stack-dotnet-backend",
        "implementation_status": "completed",
        "files_created": ["projects/P/outputs/tobe/source-code/backend/Cart.cs"],
        "files_modified": [],
        "local_checks": [{"command": "dotnet build", "exit_code": 0}],
        "acceptance_results": [{"criterion": "compila", "status": "passed"}],
    }
    base.update(overrides)
    return base


def test_extrai_e_valida_o_contrato(rota) -> None:
    resultado = contrato.parse(_resposta(_payload()), task=TASK, route=rota,
                               project="P")
    assert resultado.task_id == "T-010"
    assert resultado.claims_success is True
    assert resultado.files_outside_canonical == []
    assert resultado.parse_error == ""


def test_arquivo_fora_do_canonico_e_sinalizado(rota) -> None:
    payload = _payload(files_created=[
        "projects/P/outputs/tobe/source-code/dotnet/Cart.cs"])
    resultado = contrato.parse(_resposta(payload), task=TASK, route=rota,
                               project="P")
    assert resultado.files_outside_canonical == [
        "projects/P/outputs/tobe/source-code/dotnet/Cart.cs"]


def test_resultado_de_outra_task_e_recusado(rota) -> None:
    with pytest.raises(contrato.ContractError) as exc:
        contrato.validate(_payload(task_id="T-999"), task=TASK, route=rota,
                          project="P")
    assert exc.value.code == "CONTRACT007"


def test_status_invalido_e_recusado(rota) -> None:
    with pytest.raises(contrato.ContractError):
        contrato.validate(_payload(implementation_status="verified"),
                          task=TASK, route=rota, project="P")


def test_contrato_ausente_vira_diagnostico_e_nao_excecao(rota) -> None:
    """O build ainda decide; recusar por forma trocaria uma falha por outra."""
    resultado = contrato.parse("sem bloco nenhum", task=TASK, route=rota,
                               project="P")
    assert resultado.implementation_status == "failed"
    assert resultado.parse_error.startswith("CONTRACT002")


def test_contrato_ausente_com_strict_levanta(rota) -> None:
    with pytest.raises(contrato.ContractError):
        contrato.parse("sem bloco nenhum", task=TASK, route=rota, project="P",
                       strict=True)


def test_cerca_json_simples_e_aceita_como_tolerancia(rota) -> None:
    texto = "```json\n" + json.dumps(_payload()) + "\n```"
    resultado = contrato.parse(texto, task=TASK, route=rota, project="P")
    assert resultado.task_id == "T-010"


def test_template_do_contrato_nomeia_a_task_e_o_destino(rota) -> None:
    modelo = json.loads(contrato.contract_template("P", TASK, rota))
    assert modelo["task_id"] == "T-010"
    assert modelo["canonical_source_dir"] == "source-code/backend"
    assert modelo["agent"] == "ava-stack-dotnet-backend"
