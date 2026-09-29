"""Testes do gerador determinístico de scaffold Angular (spec 042).

Cobertura central: a árvore gerada nunca referencia arquivo que não existe — que é a
classe de defeito (B1/B6) responsável por o scaffold anterior não compilar.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "shared" / "tools"))

import f4s_angular_scaffold as scaffold  # noqa: E402


BLUEPRINT = """\
# Architecture Blueprint

## 1. Architecture Summary

| Item | Valor |
|---|---|
| Bounded contexts | 2 (Identity, DataManagement) |

## 3. Bounded Context Map — TO-BE

| # | AS-IS Context | TO-BE Module | Changes | Risk |
|---|--------------|-------------|---------|------|
| 1 | Authentication | **Identity** | JWT | Medium |
| 2 | Data Browsing | **DataManagement** | REST | Low |

## 4. API Surface Design
"""


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    """Workspace mínimo com um projeto válido."""
    project = tmp_path / "projects" / "demo"
    (project / "context").mkdir(parents=True)
    (project / "outputs" / "tobe" / "docs").mkdir(parents=True)
    (project / "context" / "project-config.yaml").write_text(
        'project_name: "Demo App"\ntobe_stack:\n  frontend_version: "17"\n',
        encoding="utf-8",
    )
    (project / "outputs" / "tobe" / "docs" / "architecture-blueprint.md").write_text(
        BLUEPRINT, encoding="utf-8"
    )
    return tmp_path


# ─── nomenclatura ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("raw", "kebab", "pascal", "camel", "title"),
    [
        ("DataManagement", "data-management", "DataManagement", "dataManagement",
         "Data Management"),
        ("Identity", "identity", "Identity", "identity", "Identity"),
        ("contas-a-pagar", "contas-a-pagar", "ContasAPagar", "contasAPagar",
         "Contas A Pagar"),
        # `to_title` preserva a sigla — "Meu ERP" é o rótulo que vai para a UI.
        ("Meu_ERP", "meu-erp", "MeuErp", "meuErp", "Meu ERP"),
    ],
)
def test_conversoes_de_nome(raw, kebab, pascal, camel, title):
    assert scaffold.to_kebab(raw) == kebab
    assert scaffold.to_pascal(raw) == pascal
    assert scaffold.to_camel(raw) == camel
    assert scaffold.to_title(raw) == title


# ─── extração de bounded contexts ───────────────────────────────────────────────


def test_extract_bcs_pela_tabela_do_context_map():
    assert scaffold.extract_bcs(BLUEPRINT) == ["Identity", "DataManagement"]


def test_extract_bcs_cai_para_a_linha_de_resumo():
    texto = "| Bounded contexts | 3 (Vendas, Estoque, Fiscal) |\n"
    assert scaffold.extract_bcs(texto) == ["Vendas", "Estoque", "Fiscal"]


def test_extract_bcs_pela_tabela_bounded_contexts_tobe_com_name():
    texto = """\
## 4. Bounded Contexts TO-BE

| BC | Name | Domain Type |
|----|------|-------------|
| BC-01 | Catalog | Core Domain |
| BC-02 | Orders | Core Domain |
"""
    assert scaffold.extract_bcs(texto) == ["Catalog", "Orders"]


def test_extract_bcs_pelo_mapa_detalhado_com_headings_bc():
    texto = """\
# Bounded Context Map

## BC-01: Accounts Payable (Contas a Pagar)
## BC-02: Accounts Receivable (Contas a Receber)
## BC-03: Banks & Current Accounts
"""
    assert scaffold.extract_bcs(texto) == [
        "Accounts Payable (Contas a Pagar)",
        "Accounts Receivable (Contas a Receber)",
        "Banks & Current Accounts",
    ]


def test_extract_bcs_ignora_shared_kernel():
    texto = """\
## Bounded Context Map

| # | AS-IS | TO-BE Module |
|---|-------|--------------|
| 1 | x | **Vendas** |
| 2 | y | **Shared Kernel** |
"""
    assert scaffold.extract_bcs(texto) == ["Vendas"]


def test_extract_bcs_sem_nada_reconhecivel_devolve_vazio():
    assert scaffold.extract_bcs("# Documento sem contextos\n") == []


def test_bc_indeterminavel_reprova(workspace: Path):
    blueprint = (workspace / "projects" / "demo" / "outputs" / "tobe" / "docs"
                 / "architecture-blueprint.md")
    blueprint.write_text("# Sem contextos\n", encoding="utf-8")
    with pytest.raises(scaffold.ScaffoldError, match="bounded context"):
        scaffold.scaffold(project="demo", workspace=workspace)


def test_override_de_bcs_dispensa_o_blueprint(workspace: Path):
    result = scaffold.scaffold(project="demo", workspace=workspace,
                               bcs_override="vendas,estoque")
    assert result["bcs"] == ["vendas", "estoque"]


# ─── resolução de versão ────────────────────────────────────────────────────────


def test_major_nao_suportado_reprova_sem_escrever_nada(workspace: Path):
    config = workspace / "projects" / "demo" / "context" / "project-config.yaml"
    config.write_text('project_name: "Demo"\ntobe_stack:\n  frontend_version: "42"\n',
                      encoding="utf-8")
    app_root = workspace / "out"

    with pytest.raises(scaffold.ScaffoldError, match="major 42 não é suportado"):
        scaffold.scaffold(project="demo", workspace=workspace, app_root=app_root)

    assert not (app_root / "angular.json").exists()


def test_versao_ausente_cai_para_o_default(workspace: Path):
    config = workspace / "projects" / "demo" / "context" / "project-config.yaml"
    config.write_text('project_name: "Demo"\n', encoding="utf-8")
    result = scaffold.scaffold(project="demo", workspace=workspace)
    versions = scaffold.load_versions()
    assert result["angular_major"] == str(versions["default_major"])


@pytest.mark.parametrize("raw", ["17", "17.3", "^17.3.0", "v17"])
def test_formatos_de_versao_aceitos(raw):
    versions = scaffold.load_versions()
    assert scaffold.resolve_major({"tobe_stack": {"frontend_version": raw}},
                                  versions) == "17"


# ─── renderização ───────────────────────────────────────────────────────────────


def test_render_substitui_tokens():
    assert scaffold.render("olá %%nome%%", {"nome": "mundo"}, "t") == "olá mundo"


def test_render_reprova_token_nao_resolvido():
    with pytest.raises(scaffold.ScaffoldError, match="token não resolvido %%falta%%"):
        scaffold.render("%%falta%%", {"outro": "x"}, "t")


def test_render_preserva_interpolacao_do_angular():
    """O delimitador do gerador não pode colidir com a interpolação do Angular."""
    saida = scaffold.render("<h1>{{ title }}</h1> %%app_title%%",
                            {"app_title": "Demo"}, "t")
    assert saida == "<h1>{{ title }}</h1> Demo"


# ─── geração completa ───────────────────────────────────────────────────────────


def test_gera_arvore_completa(workspace: Path):
    result = scaffold.scaffold(project="demo", workspace=workspace)
    root = Path(result["app_root"])

    assert result["status"] == "PASS"
    assert result["app_name"] == "demo-app"
    assert result["bcs"] == ["identity", "data-management"]

    obrigatorios = [
        "angular.json", "package.json", "tsconfig.json",
        "tsconfig.app.json", "tsconfig.spec.json", ".gitignore",
        "src/index.html", "src/main.ts", "src/styles.scss", "src/favicon.ico",
        "src/app/app.component.ts", "src/app/app.config.ts", "src/app/app.routes.ts",
        "src/environments/environment.ts", "src/environments/environment.prod.ts",
    ]
    for rel in obrigatorios:
        assert (root / rel).is_file(), f"ausente: {rel}"

    for bc in ("identity", "data-management"):
        assert (root / "src/app/features" / bc / f"{bc}.routes.ts").is_file()
        assert (root / "src/app/features" / bc / f"{bc}-home.component.ts").is_file()


def test_arquivos_json_gerados_sao_validos(workspace: Path):
    result = scaffold.scaffold(project="demo", workspace=workspace)
    root = Path(result["app_root"])
    for rel in ("angular.json", "package.json", "tsconfig.json",
                "tsconfig.app.json", "tsconfig.spec.json"):
        json.loads((root / rel).read_text(encoding="utf-8"))


def test_nenhum_token_sobra_na_arvore(workspace: Path):
    result = scaffold.scaffold(project="demo", workspace=workspace)
    root = Path(result["app_root"])
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix == ".ico":
            continue
        texto = path.read_text(encoding="utf-8", errors="replace")
        assert not scaffold.TOKEN_RE.search(texto), f"token remanescente em {path}"


def test_tsconfig_app_nao_usa_extends(workspace: Path):
    """Guardrail B1/B2: o builder esbuild falha com `extends` relativo."""
    result = scaffold.scaffold(project="demo", workspace=workspace)
    cfg = json.loads((Path(result["app_root"]) / "tsconfig.app.json")
                     .read_text(encoding="utf-8"))
    assert "extends" not in cfg
    assert cfg["files"] == ["src/main.ts"]


def test_angular_json_referencia_apenas_arquivos_existentes(workspace: Path):
    """Regressão de B1 e B6 — a raiz do bug original.

    `angular.json` apontava para `tsconfig.app.json` e `tsconfig.spec.json` que nunca
    foram gerados, e o `ng build` morria antes de compilar uma linha.
    """
    result = scaffold.scaffold(project="demo", workspace=workspace)
    root = Path(result["app_root"])
    cfg = json.loads((root / "angular.json").read_text(encoding="utf-8"))
    architect = cfg["projects"][result["app_name"]]["architect"]

    referenciados: list[str] = []
    for target in architect.values():
        options = target.get("options", {})
        for key in ("tsConfig", "index", "browser", "proxyConfig"):
            if key in options:
                referenciados.append(options[key])
        referenciados.extend(options.get("assets", []))
        referenciados.extend(s for s in options.get("styles", [])
                             if not s.startswith("@"))
        for cfg_name in target.get("configurations", {}).values():
            for replacement in cfg_name.get("fileReplacements", []):
                referenciados.extend([replacement["replace"], replacement["with"]])

    assert referenciados, "nenhum caminho extraído — o teste perderia o propósito"
    for rel in referenciados:
        assert (root / rel).is_file(), f"angular.json referencia arquivo ausente: {rel}"


def test_angular_json_declara_polyfills_e_build_target(workspace: Path):
    """Regressão de B4 e B5."""
    result = scaffold.scaffold(project="demo", workspace=workspace)
    cfg = json.loads((Path(result["app_root"]) / "angular.json")
                     .read_text(encoding="utf-8"))
    architect = cfg["projects"][result["app_name"]]["architect"]

    assert architect["build"]["options"]["polyfills"] == ["zone.js"]
    for serve_cfg in architect["serve"]["configurations"].values():
        assert "buildTarget" in serve_cfg


def test_rotas_apontam_para_arquivos_existentes(workspace: Path):
    result = scaffold.scaffold(project="demo", workspace=workspace)
    root = Path(result["app_root"])
    rotas = (root / "src/app/app.routes.ts").read_text(encoding="utf-8")
    for bc in result["bcs"]:
        assert f"./features/{bc}/{bc}.routes" in rotas
        assert (root / "src/app/features" / bc / f"{bc}.routes.ts").is_file()


def test_package_json_traz_a_matriz_do_major(workspace: Path):
    result = scaffold.scaffold(project="demo", workspace=workspace)
    pkg = json.loads((Path(result["app_root"]) / "package.json")
                     .read_text(encoding="utf-8"))
    esperado = scaffold.load_versions()["majors"]["17"]
    assert pkg["dependencies"] == esperado["dependencies"]
    assert pkg["devDependencies"] == esperado["devDependencies"]
    # NgRx e MSAL entram com o código que os usa, não no esqueleto.
    assert not [d for d in pkg["dependencies"] if d.startswith(("@ngrx/", "@azure/"))]


# ─── idempotência ───────────────────────────────────────────────────────────────


def test_segunda_execucao_preserva_edicoes(workspace: Path):
    primeiro = scaffold.scaffold(project="demo", workspace=workspace)
    root = Path(primeiro["app_root"])
    rotas = root / "src/app/app.routes.ts"
    rotas.write_text("// editado pelo agente\n", encoding="utf-8")

    segundo = scaffold.scaffold(project="demo", workspace=workspace)

    assert rotas.read_text(encoding="utf-8") == "// editado pelo agente\n"
    assert "src/app/app.routes.ts" in segundo["files_skipped"]
    assert segundo["files_written"] == []


def test_force_sobrescreve(workspace: Path):
    primeiro = scaffold.scaffold(project="demo", workspace=workspace)
    rotas = Path(primeiro["app_root"]) / "src/app/app.routes.ts"
    rotas.write_text("// editado\n", encoding="utf-8")

    segundo = scaffold.scaffold(project="demo", workspace=workspace, force=True)

    assert "Routes" in rotas.read_text(encoding="utf-8")
    assert "src/app/app.routes.ts" in segundo["files_written"]


def test_arquivo_faltante_e_recriado_sem_force(workspace: Path):
    primeiro = scaffold.scaffold(project="demo", workspace=workspace)
    alvo = Path(primeiro["app_root"]) / "tsconfig.app.json"
    alvo.unlink()

    segundo = scaffold.scaffold(project="demo", workspace=workspace)

    assert alvo.is_file()
    assert segundo["files_written"] == ["tsconfig.app.json"]


# ─── CLI ────────────────────────────────────────────────────────────────────────


def test_cli_json_em_sucesso(workspace: Path, capsys):
    code = scaffold.main(["--project", "demo", "--workspace", str(workspace), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["status"] == "PASS"


def test_cli_exit_2_em_projeto_inexistente(workspace: Path, capsys):
    code = scaffold.main(["--project", "nao-existe", "--workspace", str(workspace),
                          "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 2
    assert payload["status"] == "ERROR"
