"""Contexto mínimo por task — `src/shared/tools/f4_task_context.py`.

Medido em `cadastro-funcionarios-04`: o manifesto global da F4 injetava 659 KB
(~169k tokens) por despacho, e o fan-out repetia isso em 218 tasks. Destes,
460 KB eram `specs/*/spec.md`, `plan.md` e `tasks.md` de TODAS as features.

Estes testes protegem o corte: a task recebe a feature dela, os alvos dela, o
erro dela — e o protótipo, quando é frontend (o `index.html` é o artefato que
nunca chegava ao gerador de código).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "shared" / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import f4_routing
import f4_task_context


def _task(**campos) -> dict:
    base = {
        "task_id": "T-010",
        "title": "Implementa carrinho",
        "feature": "002-carrinho",
        "spec_id": "SPEC-002",
        "group": "G-CART",
        "task_type": "backend",
        "target_stack": "dotnet",
        "priority": "P1",
        "migration_wave_id": "W1",
        "migration_wave_order": 1,
        "verify_command": "dotnet build",
        "acceptance": ["dotnet build sem erro"],
        "target_files": ["backend/src/Domain/Cart.cs"],
        "depends_on": ["T-001"],
        "backend_dependencies": [],
        "attempts": 0,
        "api_ops": [],
        "screen_id": None,
        "rule_ids": [],
    }
    base.update(campos)
    return base


#: Documentos reais têm dezenas de KB; com fixture de 20 bytes nenhum orçamento
#: entra em jogo e o teste de níveis mediria só o tamanho dos cabeçalhos.
def _recheio(titulo: str, marcador: str, secoes: int = 40) -> str:
    partes = [f"# {titulo}", "", marcador, ""]
    for i in range(secoes):
        partes += [f"## Secao {i}", "", "linha de conteudo " * 40, ""]
    return "\n".join(partes)


def _projeto(tmp_path: Path) -> Path:
    tobe = tmp_path / "projects" / "P" / "outputs" / "tobe"
    speckit = tobe / "speckit"
    (speckit / "specs" / "002-carrinho").mkdir(parents=True)
    (speckit / "specs" / "009-outra").mkdir(parents=True)
    (speckit / "constitution.md").write_text(
        _recheio("Constituicao", "## Carrinho\nregras do carrinho"), encoding="utf-8")
    (speckit / "specs" / "002-carrinho" / "spec.md").write_text(
        _recheio("Spec do carrinho", "conteudo-do-carrinho"), encoding="utf-8")
    (speckit / "specs" / "002-carrinho" / "plan.md").write_text(
        _recheio("Plano do carrinho", "plano-do-carrinho"), encoding="utf-8")
    (speckit / "specs" / "009-outra" / "spec.md").write_text(
        _recheio("Spec de OUTRA feature", "conteudo-de-outra-feature"),
        encoding="utf-8")

    docs = tobe / "docs"
    docs.mkdir(parents=True)
    (docs / "architecture-blueprint.md").write_text(
        _recheio("Blueprint", "bounded contexts"), encoding="utf-8")
    (docs / "tech-framework-document.md").write_text(
        _recheio("Tech Framework", "padroes tecnicos"), encoding="utf-8")

    proto = tobe / "prototype"
    proto.mkdir(parents=True)
    (proto / "index.html").write_text(
        "<html><body><section id='scr-cart'>tela do carrinho</section></body></html>",
        encoding="utf-8")
    (proto / "screen-list.md").write_text("# Telas\n- scr-cart\n", encoding="utf-8")
    (proto / "design-tokens.json").write_text('{"cor": "#fff"}', encoding="utf-8")

    for componente in ("frontend", "backend"):
        destino = tobe / "source-code" / componente
        destino.mkdir(parents=True)
        (destino / "Existente.cs").write_text("// ja existe", encoding="utf-8")
    return tmp_path


def _contexto(tmp_path: Path, task: dict, **kwargs) -> str:
    rota = f4_routing.resolve_route(task, "P", tmp_path)
    return f4_task_context.build("P", task, rota, repo_root=tmp_path, **kwargs)


def test_contexto_traz_a_feature_da_task(tmp_path: Path) -> None:
    _projeto(tmp_path)
    texto = _contexto(tmp_path, _task())
    assert "conteudo-do-carrinho" in texto
    assert "specs/002-carrinho/spec.md" in texto


def test_contexto_nao_traz_as_specs_das_outras_features(tmp_path: Path) -> None:
    """O corte que vale 460 KB por despacho."""
    _projeto(tmp_path)
    texto = _contexto(tmp_path, _task())
    assert "conteudo-de-outra-feature" not in texto
    assert "009-outra" not in texto


def test_contexto_traz_task_alvos_e_aceite(tmp_path: Path) -> None:
    _projeto(tmp_path)
    texto = _contexto(tmp_path, _task())
    assert "T-010" in texto
    assert "backend/src/Domain/Cart.cs" in texto
    assert "dotnet build sem erro" in texto
    assert "source-code/backend" in texto


def test_contexto_proibe_diretorio_por_stack(tmp_path: Path) -> None:
    _projeto(tmp_path)
    texto = _contexto(tmp_path, _task())
    assert "source-code/dotnet" in texto and "NUNCA use" in texto, (
        "a regra tem de estar escrita no prompt, com o caminho proibido nomeado")


def test_contexto_traz_a_arvore_existente(tmp_path: Path) -> None:
    _projeto(tmp_path)
    texto = _contexto(tmp_path, _task())
    assert "Existente.cs" in texto


def test_prototipo_chega_ao_coder_de_frontend(tmp_path: Path) -> None:
    """`index.html` é o artefato que nunca chegava ao gerador de código."""
    _projeto(tmp_path)
    tarefa = _task(task_id="T-011", task_type="frontend", target_stack="angular",
                   screen_id="scr-cart", verify_command="")
    texto = _contexto(tmp_path, tarefa)
    assert "prototype/index.html" in texto
    assert "tela do carrinho" in texto
    assert "design-tokens.json" in texto


def test_prototipo_nao_e_injetado_em_task_de_backend(tmp_path: Path) -> None:
    _projeto(tmp_path)
    texto = _contexto(tmp_path, _task())
    assert "tela do carrinho" not in texto
    assert "prototype/index.html" in texto, "o caminho continua referenciado"


def test_erro_da_tentativa_anterior_entra_no_contexto(tmp_path: Path) -> None:
    _projeto(tmp_path)
    tarefa = _task(attempts=1, evidence={"command": "dotnet build", "exit_code": 1,
                                         "log_path": "GENERATION_LOG.md",
                                         "recorded_at": "2026-08-30T00:00:00Z"})
    texto = _contexto(tmp_path, tarefa, attempt=2,
                      failure_context="CS0246: type not found")
    assert "TENTATIVA ANTERIOR" in texto
    assert "CS0246" in texto


def test_niveis_de_contexto_reduzem_o_tamanho(tmp_path: Path) -> None:
    _projeto(tmp_path)
    tarefa = _task()
    tamanhos = [len(_contexto(tmp_path, tarefa, level=nivel)) for nivel in (0, 1, 2)]
    assert tamanhos[0] >= tamanhos[1] >= tamanhos[2]


def test_dependencias_entram_como_resumo_nunca_como_corpo(tmp_path: Path) -> None:
    _projeto(tmp_path)
    ledger = [{"task_id": "T-001", "status": "verified", "title": "Base",
               "files_written": ["backend/src/Domain/Base.cs"]}]
    texto = _contexto(tmp_path, _task(), ledger_tasks=ledger)
    assert "T-001" in texto and "verified" in texto
    assert "Base.cs" in texto


def test_contexto_da_task_e_uma_fracao_do_manifesto_global(tmp_path: Path) -> None:
    """Guarda-corpo de orçamento: contexto por task não pode inchar sem alarme."""
    _projeto(tmp_path)
    assert len(_contexto(tmp_path, _task())) < 120_000
