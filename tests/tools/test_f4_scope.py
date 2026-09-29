"""Escopo por tipo de task e reconciliação de artefatos — `f4_scope.py`.

Cobre os cenários 5, 8 e 11 da correção da F4, todos vindos de defeito real em
`cadastro-funcionario-03`:

* 5 — task Terraform escreve em `infra/terraform/`: caminho **autorizado**,
  rastreado e incluído no commit (antes era recusado por "fora do canônico", e
  o agente empurrava os `.tf` para `backend/infra/terraform/`);
* 8 — artefato declarado em `frontend/app/angular.json` aparece em
  `frontend/angular.json`: caminho alternativo válido, não ausência;
* 11 — arquivo não relacionado alterado durante a task: fora do commit, com
  motivo registrado, sem descartar a alteração em silêncio.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "shared" / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import f4_scope


def _task(**campos) -> dict:
    base = {
        "task_id": "T-001", "title": "Task", "task_type": "backend",
        "target_stack": "dotnet", "verify_command": "dotnet build",
        "target_files": ["backend/global.json"],
    }
    base.update(campos)
    return base


# ─── Classificação ───────────────────────────────────────────────────────────

def test_task_de_terraform_e_infra_mesmo_rotulada_como_backend() -> None:
    """`T-W0-TF-001` chegava como `backend` e o `.tf` ia parar em backend/."""
    tarefa = _task(task_id="T-W0-TF-001",
                   title="Criar infra/terraform/main.tf com provider Azure",
                   task_type="backend", target_stack="dotnet",
                   verify_command="terraform validate infra/terraform",
                   target_files=["infra/terraform/main.tf"])
    classificacao = f4_scope.classify(tarefa)
    assert classificacao.kind == f4_scope.KIND_INFRA
    assert classificacao.overridden is True
    assert classificacao.declared_type == "backend"


def test_verify_command_de_terraform_classifica_como_infra() -> None:
    tarefa = _task(target_files=[], verify_command="terraform plan")
    assert f4_scope.classify(tarefa).kind == f4_scope.KIND_INFRA


def test_task_de_backend_continua_backend() -> None:
    assert f4_scope.classify(_task()).kind == f4_scope.KIND_BACKEND


def test_infra_nao_bloqueia_a_esteira() -> None:
    assert f4_scope.is_blocking(f4_scope.KIND_INFRA) is False
    assert f4_scope.is_blocking(f4_scope.KIND_BACKEND) is True
    assert f4_scope.is_blocking(f4_scope.KIND_FRONTEND) is True


# ─── Cenário 5 — infra/** é caminho válido ───────────────────────────────────

def test_infra_terraform_e_caminho_autorizado() -> None:
    tarefa = _task(task_id="T-TF", target_files=["infra/terraform/main.tf"],
                   verify_command="terraform validate")
    for caminho in ("infra/terraform/main.tf",
                    "infra/terraform/variables.tf",
                    "infra/terraform/modules/app-service/main.tf"):
        assert f4_scope.is_allowed(caminho, f4_scope.KIND_INFRA, tarefa), caminho


def test_artefatos_de_terraform_entram_no_commit() -> None:
    tarefa = _task(task_id="T-TF", target_files=["infra/terraform/main.tf"],
                   verify_command="terraform validate")
    gerados = ["infra/terraform/main.tf", "infra/terraform/variables.tf",
               "infra/terraform/modules/app-service/main.tf"]
    rec = f4_scope.reconcile(tarefa, changed=gerados, kind=f4_scope.KIND_INFRA)
    assert set(rec.to_commit) == set(gerados)
    assert rec.excluded == []
    assert rec.missing == []


def test_backend_nao_pode_escrever_em_infra_sem_declarar() -> None:
    """O caminho oposto: task de backend não vira dona de `infra/` por acidente."""
    rec = f4_scope.reconcile(_task(), changed=["infra/terraform/main.tf"],
                             kind=f4_scope.KIND_BACKEND)
    assert rec.to_commit == []
    assert rec.excluded[0]["path"] == "infra/terraform/main.tf"
    assert "escopo" in rec.excluded[0]["reason"]


# ─── Cenário 8 — caminho alternativo válido ──────────────────────────────────

def test_caminho_alternativo_nao_e_ausencia() -> None:
    tarefa = _task(task_id="T-W0-FE-001", task_type="frontend",
                   target_stack="angular", verify_command="",
                   target_files=["frontend/cadastro-funcionario-app/angular.json"])
    rec = f4_scope.reconcile(tarefa, changed=["frontend/angular.json"],
                             kind=f4_scope.KIND_FRONTEND)
    assert rec.to_commit == ["frontend/angular.json"]
    assert rec.missing == [], "caminho diferente não é artefato ausente"
    assert rec.alternative_paths == [{
        "declared": "frontend/cadastro-funcionario-app/angular.json",
        "actual": "frontend/angular.json"}]
    assert rec.artifacts[0]["classification"] == f4_scope.ALTERNATIVE_PATH


def test_alvo_que_nao_apareceu_em_lugar_nenhum_e_ausencia() -> None:
    rec = f4_scope.reconcile(_task(), changed=[], kind=f4_scope.KIND_BACKEND)
    assert rec.missing == ["backend/global.json"]
    assert rec.artifacts[0]["classification"] == f4_scope.EXPECTED_BUT_MISSING


# ─── Cenário 11 — arquivo não relacionado ────────────────────────────────────

def test_arquivo_de_outro_componente_fica_fora_do_commit_com_motivo() -> None:
    rec = f4_scope.reconcile(_task(), kind=f4_scope.KIND_BACKEND,
                             changed=["backend/global.json",
                                      "frontend/src/app/app.component.ts"])
    assert rec.to_commit == ["backend/global.json"]
    assert len(rec.excluded) == 1
    assert rec.excluded[0]["path"] == "frontend/src/app/app.component.ts"
    assert rec.excluded[0]["reason"]
    # A alteração continua registrada: nada é descartado em silêncio.
    fora = [a for a in rec.artifacts
            if a["classification"] == f4_scope.OUTSIDE_SCOPE]
    assert fora and fora[0]["path"] == "frontend/src/app/app.component.ts"


def test_artefato_de_build_e_segredo_nunca_entram_no_commit() -> None:
    rec = f4_scope.reconcile(_task(), kind=f4_scope.KIND_BACKEND,
                             changed=["backend/bin/App.dll",
                                      "backend/appsettings.Development.json",
                                      "backend/global.json"])
    assert rec.to_commit == ["backend/global.json"]
    motivos = {item["path"]: item["reason"] for item in rec.excluded}
    assert "sensivel" in motivos["backend/appsettings.Development.json"]
    assert "build" in motivos["backend/bin/App.dll"]


def test_normalizacao_aceita_caminho_absoluto_do_agente() -> None:
    assert f4_scope.normalize(
        "projects/P/outputs/tobe/source-code/backend/global.json"
    ) == "backend/global.json"
    assert f4_scope.normalize(
        r"projects\P\outputs\tobe\source-code\infra\terraform\main.tf"
    ) == "infra/terraform/main.tf"


def test_gitignore_na_raiz_e_escopo_compartilhado() -> None:
    tarefa = _task(task_id="T-GI", target_files=[".gitignore"])
    rec = f4_scope.reconcile(tarefa, changed=[".gitignore"],
                             kind=f4_scope.KIND_BACKEND)
    assert rec.to_commit == [".gitignore"]
    assert rec.excluded == []
