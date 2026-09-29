"""O contrato da F3S no runner vem do DAG da fase, nunca de uma lista à mão.

Defeito que originou estes testes: `PHASE_ARTIFACT_CONTRACT["F3S"]` era um
espelho manual do `pipeline-dag/F3S.yaml` e divergiu dele. Exigia
`checks-report.json` (produzido com `on_fail: warn`, legitimamente ausente
quando a suíte degrada) e `ava-agents-progress.txt` (log narrativo, não condição
de saída). Nenhum dos dois está no `exit_gate` — e a fase era reprovada
(`val_ok=False`) por não os encontrar.

O `F3S.yaml` abre declarando que o gate LÊ aquele arquivo em runtime e que não
há segunda cópia a manter. Estes testes travam essa promessa no runner também.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PY = REPO_ROOT / "ava-pipeline-runner-cli.py"
DAG_PATH = REPO_ROOT / "src" / "shared" / "data" / "pipeline-dag" / "F3S.yaml"


@pytest.fixture(scope="module")
def runner():
    sys.path.insert(0, str(REPO_ROOT / "src" / "shared" / "tools"))
    spec = importlib.util.spec_from_file_location("runner19_contract", RUNNER_PY)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="module")
def dag() -> dict:
    return yaml.safe_load(DAG_PATH.read_text(encoding="utf-8"))


def _exit_gate_esperado(dag: dict) -> list[str]:
    esperado: list[str] = []
    for item in (dag.get("exit_gate") or {}).get("items") or []:
        if item.get("kind") == "human_approval":
            continue
        caminho = str(item.get("path") or "")
        relativo = caminho.removeprefix("outputs/")
        if relativo and relativo not in esperado:
            esperado.append(relativo)
    return esperado


def test_contrato_f3s_e_exatamente_o_exit_gate_do_dag(runner, dag):
    assert runner.PHASE_ARTIFACT_CONTRACT["F3S"]["required"] == _exit_gate_esperado(dag)


@pytest.mark.parametrize("artefato", ["ava-agents-progress.txt", "checks-report.json"])
def test_artefato_fora_do_exit_gate_nao_e_obrigatorio(runner, dag, artefato):
    """Os dois casos concretos do defeito, travados nominalmente.

    Ambos são produzidos pela F3S — `ava-agents-progress.txt` pelo
    `speckit_output_reconciler.py` e `checks-report.json` pela suíte de checks —
    mas nenhum é CONDIÇÃO DE SAÍDA. Produzir não é o mesmo que ser obrigatório
    para aprovar a fase, e confundir os dois foi o defeito.
    """
    assert artefato not in "\n".join(_exit_gate_esperado(dag)), (
        f"{artefato} entrou no exit_gate do DAG — se isso for intencional, "
        "este teste deve ser reescrito junto")
    assert not any(artefato in item
                   for item in runner.PHASE_ARTIFACT_CONTRACT["F3S"]["required"])


def test_aprovacao_humana_nao_vira_arquivo_obrigatorio(runner, dag):
    """`kind: human_approval` é decisão registrada dentro de um artefato que já
    consta na lista — contá-lo de novo criaria uma exigência duplicada."""
    aprovacoes = [item for item in (dag.get("exit_gate") or {}).get("items") or []
                  if item.get("kind") == "human_approval"]
    assert aprovacoes, "fixture desatualizada: o exit_gate não declara human_approval"
    requeridos = runner.PHASE_ARTIFACT_CONTRACT["F3S"]["required"]
    assert len(requeridos) == len(set(requeridos)), "há caminho duplicado no contrato"


def test_inputs_da_f3s_vem_do_entry_gate_do_dag(runner, dag):
    """O manifesto de insumos da F3S sai do DAG, não do `ava-pipeline.yaml`."""
    runner._apply_declared_inputs(runner.PIPELINE)
    passo = next(item for item in runner.PIPELINE if item["phase"] == "F3S")
    obtidos = {entrada["path"] for entrada in passo["inputs"]["mandatory"]}

    esperados = {str(item["path"]) for item in (dag.get("entry_gate") or {}).get("items") or []
                 if item.get("kind") != "any_file" and item.get("path")}
    assert obtidos == esperados


def test_entry_gate_any_file_nao_vira_insumo_obrigatorio(runner, dag):
    """`kind: any_file` declara ALTERNATIVAS — nenhuma obrigatória sozinha.

    A definição de waves aceita `wave-model.json` OU `wave-plan.md`. Tratar
    qualquer uma como obrigatória reprovaria um projeto que legitimamente só tem
    a outra.
    """
    alternativas = [item for item in (dag.get("entry_gate") or {}).get("items") or []
                    if item.get("kind") == "any_file"]
    assert alternativas, "fixture desatualizada: o entry_gate não declara any_file"

    runner._apply_declared_inputs(runner.PIPELINE)
    passo = next(item for item in runner.PIPELINE if item["phase"] == "F3S")
    obtidos = {entrada["path"] for entrada in passo["inputs"]["mandatory"]}
    for item in alternativas:
        for caminho in item.get("paths") or []:
            assert str(caminho) not in obtidos


def test_dag_ausente_degrada_sem_quebrar(runner):
    """Fase sem `pipeline-dag/{phase}.yaml` devolve None em vez de estourar."""
    assert runner._dag_da_fase("FASE_QUE_NAO_EXISTE") is None
