"""
Testes do manifesto de contexto — `src/shared/tools/context_manifest.py`.

O defeito que este módulo existe para corrigir (spec 039 §2 P-1): `load_context`
injetava o corpo dos N primeiros artefatos em ordem alfabética de
`sorted(outputs.rglob("*"))`. Medido em `nopcommerce-02-cli-ava`, os 60 injetados
eram 100% AS-IS — nenhum artefato `tobe/` chegava ao gerador de código, e
`prototype/index.html` **nunca** era elegível porque `.html` estava fora da
allowlist de sufixos.

Os testes abaixo congelam os dois lados do contrato:

* o caminho **declarado** entrega exatamente o que foi declarado, na ordem
  declarada, incluindo `.html`, e reprova antes de gastar inferência quando falta
  um insumo obrigatório;
* o caminho **legado** (passo sem `inputs:`) continua idêntico ao de hoje — a
  migração é opt-in, passo a passo, e nenhuma etapa existente muda de
  comportamento sozinha.

Roda com o Python do repo:
    python -m pytest tests/tools/test_context_manifest.py -q
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PY = REPO_ROOT / "src" / "shared" / "tools" / "context_manifest.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    # `@dataclass` sob `from __future__ import annotations` resolve os tipos via
    # `sys.modules[cls.__module__]` — o módulo precisa estar registrado antes do exec.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


cm = _load(MODULE_PY, "context_manifest_under_test")


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def projeto(tmp_path: Path) -> Path:
    """Um projeto mínimo com a mesma forma de árvore da esteira real."""
    root = tmp_path
    proj = root / "projects" / "P"
    (proj / "context").mkdir(parents=True)
    (proj / "context" / "project-config.yaml").write_text(
        "project_name: P\n", encoding="utf-8")
    (proj / "context" / "shared-context.md").write_text(
        "# contexto compartilhado\n", encoding="utf-8")

    docs = proj / "outputs" / "tobe" / "docs"
    docs.mkdir(parents=True)
    (docs / "architecture-blueprint.md").write_text("# blueprint\n", encoding="utf-8")
    (docs / "api-map.md").write_text("# api map\n", encoding="utf-8")
    (docs / "openapi").mkdir()
    (docs / "openapi" / "bc01-catalog.yaml").write_text("openapi: 3.1.0\n", encoding="utf-8")
    (docs / "openapi" / "bc02-orders.yaml").write_text("openapi: 3.1.0\n", encoding="utf-8")

    proto = proj / "outputs" / "tobe" / "prototype"
    proto.mkdir(parents=True)
    (proto / "index.html").write_text(
        "<section class=\"screen\" id=\"screen-cart\"></section>\n", encoding="utf-8")
    (proto / "screen-list.md").write_text("# Prototype Screen List\n", encoding="utf-8")

    (root / "src" / "shared" / "data").mkdir(parents=True)
    (root / "src" / "shared" / "data" / "reference-architecture.yaml").write_text(
        "stacks: {}\n", encoding="utf-8")
    return root


def _cfg(**context_overrides):
    ctx = {"declared_body_chars": 200_000, "declared_total_chars": 2_000_000,
           "max_artifact_bodies": 3, "artifact_body_chars": 20_000,
           "max_artifacts": 500, "file_chars": 500_000}
    ctx.update(context_overrides)
    return {"context": ctx, "execution": {"output_subdir": "outputs/pipeline_runner"}}


# ─── Caminho declarado ───────────────────────────────────────────────────────

def test_insumo_obrigatorio_ausente_e_reportado(projeto: Path):
    """O defeito nunca mais pode passar em silêncio: falta ⇒ o passo não roda."""
    res = cm.resolve("P", {"mandatory": ["outputs/tobe/docs/regras-negocio.md"]},
                     _cfg(), repo_root=projeto)
    assert [m.pattern for m in res.missing_mandatory] == ["outputs/tobe/docs/regras-negocio.md"]
    assert res.blocked is True


def test_insumo_advisory_ausente_nao_bloqueia(projeto: Path):
    res = cm.resolve("P", {"advisory": ["outputs/tobe/prototype/figma-spec.md"]},
                     _cfg(), repo_root=projeto)
    assert res.blocked is False
    assert [m.pattern for m in res.missing_advisory] == ["outputs/tobe/prototype/figma-spec.md"]
    assert res.missing_mandatory == []


def test_ordem_de_declaracao_e_preservada(projeto: Path):
    """A ordem é a de declaração, nunca a do filesystem — era a raiz do defeito."""
    declarado = ["outputs/tobe/docs/api-map.md",
                 "outputs/tobe/docs/architecture-blueprint.md"]
    res = cm.resolve("P", {"mandatory": declarado}, _cfg(), repo_root=projeto)
    assert [i.rel for i in res.included] == [
        "projects/P/outputs/tobe/docs/api-map.md",
        "projects/P/outputs/tobe/docs/architecture-blueprint.md",
    ]
    # e o inverso também vale — não há reordenação escondida
    res2 = cm.resolve("P", {"mandatory": list(reversed(declarado))}, _cfg(), repo_root=projeto)
    assert [i.rel for i in res2.included] == [
        "projects/P/outputs/tobe/docs/architecture-blueprint.md",
        "projects/P/outputs/tobe/docs/api-map.md",
    ]


def test_glob_expande_ordenado_e_conta_como_presente(projeto: Path):
    res = cm.resolve("P", {"mandatory": ["outputs/tobe/docs/openapi/*.yaml"]},
                     _cfg(), repo_root=projeto)
    assert res.missing_mandatory == []
    assert [Path(i.rel).name for i in res.included] == ["bc01-catalog.yaml", "bc02-orders.yaml"]


def test_glob_sem_correspondencia_e_insumo_ausente(projeto: Path):
    res = cm.resolve("P", {"mandatory": ["outputs/tobe/docs/decisions/ADR-*.md"]},
                     _cfg(), repo_root=projeto)
    assert res.blocked is True


def test_html_declarado_e_injetado(projeto: Path):
    """Regressão direta do defeito: `.html` estava fora da allowlist de sufixos,
    então `prototype/index.html` não podia chegar ao coder por construção."""
    res = cm.resolve("P", {"mandatory": ["outputs/tobe/prototype/index.html"]},
                     _cfg(), repo_root=projeto)
    assert res.missing_mandatory == []
    assert "screen-cart" in cm.render(res)


def test_binario_declarado_e_recusado_com_aviso(projeto: Path):
    (projeto / "projects" / "P" / "outputs" / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    res = cm.resolve("P", {"advisory": ["outputs/logo.png"]}, _cfg(), repo_root=projeto)
    assert res.included == []
    assert any("binário" in w for w in res.warnings)


def test_base_workspace_resolve_da_raiz_do_repo(projeto: Path):
    res = cm.resolve("P", {"mandatory": [
        {"path": "src/shared/data/reference-architecture.yaml", "base": "workspace"}]},
        _cfg(), repo_root=projeto)
    assert res.missing_mandatory == []
    assert res.included[0].rel == "src/shared/data/reference-architecture.yaml"


def test_mensagem_de_erro_nomeia_produtor_e_caminho(projeto: Path):
    res = cm.resolve("P", {"mandatory": [
        {"path": "outputs/tobe/docs/regras-negocio.md",
         "produced_by": "ava-docs-tobe (F2, trigger RN)"}]},
        _cfg(), repo_root=projeto)
    msg = cm.format_missing(res, phase="F4", agent="ava-stack-orchestrator", project="P")
    assert "regras-negocio.md" in msg
    assert "ava-docs-tobe" in msg
    assert "F4" in msg and "ava-stack-orchestrator" in msg


def test_caminho_fora_do_projeto_e_recusado(projeto: Path):
    segredo = projeto / "segredo.txt"
    segredo.write_text("nao vaze", encoding="utf-8")
    res = cm.resolve("P", {"advisory": ["../../segredo.txt"]}, _cfg(), repo_root=projeto)
    assert res.included == []
    assert any("fora" in w for w in res.warnings)


def test_truncamento_por_item_e_explicito(projeto: Path):
    grande = projeto / "projects" / "P" / "outputs" / "grande.md"
    grande.write_text("x" * 5_000, encoding="utf-8")
    res = cm.resolve("P", {"mandatory": ["outputs/grande.md"]},
                     _cfg(declared_body_chars=1_000), repo_root=projeto)
    texto = cm.render(res)
    assert "truncado" in texto
    assert len(res.included[0].body) <= 1_000


def test_item_duplicado_entra_uma_vez_so(projeto: Path):
    res = cm.resolve("P", {"mandatory": ["outputs/tobe/docs/api-map.md"],
                           "advisory": ["outputs/tobe/docs/api-map.md"]},
                     _cfg(), repo_root=projeto)
    assert len(res.included) == 1


def test_config_do_projeto_entra_sempre(projeto: Path):
    """`project-config.yaml` e `shared-context.md` são o piso de todo passo."""
    res = cm.resolve("P", {"mandatory": ["outputs/tobe/docs/api-map.md"]},
                     _cfg(), repo_root=projeto)
    texto = cm.render(res)
    assert "project-config.yaml" in texto
    assert "shared-context.md" in texto


# ─── Caminho legado (passo sem `inputs:`) ────────────────────────────────────

def test_passo_sem_inputs_usa_o_comportamento_legado(projeto: Path):
    res = cm.resolve("P", None, _cfg(), repo_root=projeto)
    assert res.declared is False
    assert res.blocked is False
    assert "Artefatos já existentes em outputs/" in cm.render(res)


def test_legado_respeita_o_teto_de_corpos(projeto: Path):
    res = cm.resolve("P", {}, _cfg(max_artifact_bodies=2), repo_root=projeto)
    assert res.declared is False
    assert len(res.included) == 2


def test_legado_continua_sem_injetar_html(projeto: Path):
    """Documenta a fronteira: o defeito só se corrige declarando `inputs:`.
    Mudar o fallback silenciosamente alteraria etapas que ninguém revisou."""
    res = cm.resolve("P", None, _cfg(max_artifact_bodies=50), repo_root=projeto)
    assert all(not i.rel.endswith(".html") for i in res.included)
