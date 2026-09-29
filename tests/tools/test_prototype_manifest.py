"""Contratos do parser determinístico do protótipo (F3S / spec 039).

Cobrem os cenários 3, 4, 8, 9 e 11 do plano de correção da F3S, mais o
determinismo do cenário 10. O que estes testes travam, em uma frase: o protótipo
vira dado estruturado sem executar JavaScript, sem inventar comportamento e sem
depender da ordem de iteração de nada.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "shared" / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import prototype_manifest as pm  # noqa: E402

PROJECT_CONFIG = """
project_name: "P"
tobe_stack:
  backend_framework: "dotnet"
  backend_version: "10.0"
  backend_language: "csharp"
  frontend_framework: "angular"
  frontend_version: "17"
  frontend_language: "typescript"
"""

INDEX_HTML = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>Protótipo</title>
<style>
:root {
  --color-primary: #1565C0;
  --spacing-md: 16px;
  --font-size-base: 14px;
  --radius-sm: 4px;
}
body { background: var(--color-primary); margin: 0; }
.btn { padding: var(--spacing-md); border-radius: var(--radius-sm); }
.btn-primary { background: var(--color-primary); }
.data-table { width: 100%; font-size: var(--font-size-base); }
.modal-box { display: none; }
@media (max-width: 768px) { .sidebar { display: none; } }
</style></head>
<body>
<nav class="sidebar" role="navigation" aria-label="Menu principal">
  <a href="#screen-employees-list">Funcionários</a>
</nav>

<section class="screen active" id="screen-employees-list" aria-label="Lista de Funcionários">
  <h2>Lista de Funcionários</h2>
  <div class="toolbar">
    <button class="btn btn-primary" onclick="showScreen('employees-form')">Novo</button>
  </div>
  <table class="data-table" id="employees-table" aria-label="Lista de funcionários">
    <thead><tr><th>Código</th><th>Nome</th><th>Ações</th></tr></thead>
    <tbody><tr><td>1</td><td>Ana</td>
      <td><button class="btn" onclick="editEmployee(1)">Editar Ana</button></td></tr></tbody>
  </table>
  <div class="empty-state">Nenhum registro</div>
  <div class="loading-spinner"></div>
</section>

<section class="screen" id="screen-employees-form" aria-label="Cadastro de Funcionário">
  <h2>Cadastro de Funcionário</h2>
  <form id="form-employee" novalidate onsubmit="submitEmployee(event)">
    <label for="emp-name">Nome *</label>
    <input type="text" id="emp-name" name="nome" required maxlength="100"
           data-error-msg="Nome é obrigatório"/>
    <label for="emp-salary">Salário *</label>
    <input type="number" id="emp-salary" name="salario" required min="1"/>
    <div class="form-actions">
      <button type="submit" class="btn btn-primary" id="btn-save">Salvar</button>
      <button type="button" class="btn" onclick="showScreen('employees-list')">Voltar</button>
    </div>
  </form>
  <div class="modal-box" id="error-modal">
    <div class="alert-message">Erro ao salvar</div>
  </div>
</section>

<section class="screen" id="screen-about" aria-label="Sobre">
  <h2>Sobre</h2><p>Informações estáticas.</p>
</section>
<script>function showScreen(id){}</script>
</body></html>
"""

SCREEN_LIST = """# Prototype Screen List

| Screen | Bounded Context | API Endpoint | AS-IS Reference | Status |
|--------|----------------|--------------|-----------------|--------|
| Lista de Funcionários | BC-01 Employees | `GET /api/v1/employees` | frmList | included |
| Cadastro de Funcionário | BC-01 Employees | `POST /api/v1/employees` | frmEdit | included |
| Sobre | BC-09 Cross-Cutting | N/A | new screen | included |
"""


def build_project(root: Path, *, with_prototype: bool = True,
                  with_screen_list: bool = True,
                  with_config: bool = True) -> Path:
    project = root / "projects" / "P"
    (project / "context").mkdir(parents=True)
    (project / "outputs" / "tobe" / "prototype").mkdir(parents=True)
    if with_config:
        (project / "context" / "project-config.yaml").write_text(
            PROJECT_CONFIG, encoding="utf-8")
    if with_prototype:
        (project / "outputs" / "tobe" / "prototype" / "index.html").write_text(
            INDEX_HTML, encoding="utf-8")
    if with_screen_list:
        (project / "outputs" / "tobe" / "prototype" / "screen-list.md").write_text(
            SCREEN_LIST, encoding="utf-8")
    return project


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    build_project(tmp_path)
    return tmp_path


def test_extrai_telas_rotas_e_bounded_context(workspace: Path) -> None:
    manifest = pm.build_manifest("P", workspace)
    ids = [screen["screen_id"] for screen in manifest["screens"]]
    assert ids == ["SCR-ABOUT", "SCR-EMPLOYEES-FORM", "SCR-EMPLOYEES-LIST"]

    by_id = {screen["screen_id"]: screen for screen in manifest["screens"]}
    assert by_id["SCR-EMPLOYEES-LIST"]["bounded_context"] == "BC-01"
    assert by_id["SCR-EMPLOYEES-LIST"]["route"] == "/employees-list"
    assert by_id["SCR-EMPLOYEES-LIST"]["route_id"] == "RTE-EMPLOYEES-LIST"
    assert {route["route_id"] for route in manifest["routes"]} == {
        "RTE-ABOUT", "RTE-EMPLOYEES-FORM", "RTE-EMPLOYEES-LIST"}


def test_cenario_11_formulario_tabela_modal_navegacao_e_estados(workspace: Path) -> None:
    """Cada elemento vira dado próprio — não um bloco genérico de 'tela'."""
    manifest = pm.build_manifest("P", workspace)
    by_id = {screen["screen_id"]: screen for screen in manifest["screens"]}

    form_screen = by_id["SCR-EMPLOYEES-FORM"]
    form = form_screen["forms"][0]
    assert form["form_id"] == "FRM-FORM-EMPLOYEE"
    assert form["submit_action"] == "submitEmployee"
    fields = {field["name"]: field for field in form["fields"]}
    assert set(fields) == {"nome", "salario"}
    assert fields["nome"]["required"] is True
    assert fields["nome"]["label"] == "Nome *"
    rules = {rule["rule"]: rule for rule in fields["nome"]["validations"]}
    assert rules["maxlength"]["value"] == "100"
    assert rules["required"]["message"] == "Nome é obrigatório"

    list_screen = by_id["SCR-EMPLOYEES-LIST"]
    table = list_screen["tables"][0]
    assert table["table_id"] == "TBL-EMPLOYEES-TABLE"
    assert table["columns"] == ["Código", "Nome", "Ações"]
    assert "Editar Ana" in table["row_actions"]

    # Modal, navegação e estados
    assert any(component["kind"] == "modal"
               for component in form_screen["components"])
    assert "SCR-EMPLOYEES-FORM" in list_screen["navigation_targets"]
    assert {state["state"] for state in list_screen["states"]} >= {"loading", "empty"}


def test_botao_de_linha_de_tabela_nao_vira_componente(workspace: Path) -> None:
    """Linha de tabela é DADO DE EXEMPLO; `Editar Ana` não é um componente."""
    manifest = pm.build_manifest("P", workspace)
    every_component = {component["component_id"]
                       for screen in manifest["screens"]
                       for component in screen["components"]}
    assert not any("EDITAR-ANA" in cid for cid in every_component)
    # ...mas continua registrado como ação de linha da tabela.
    table = next(screen for screen in manifest["screens"]
                 if screen["screen_id"] == "SCR-EMPLOYEES-LIST")["tables"][0]
    assert "Editar Ana" in table["row_actions"]


def test_design_system_categoriza_tokens_e_breakpoints(workspace: Path) -> None:
    manifest = pm.build_manifest("P", workspace)
    design = manifest["design_system"]
    names = {token["token_id"]: token
             for key in ("colors", "typography", "spacing", "other_tokens")
             for token in design[key]}
    assert names["TOK-COLOR-PRIMARY"]["value"] == "#1565C0"
    assert names["TOK-COLOR-PRIMARY"] in design["colors"]
    assert names["TOK-FONT-SIZE-BASE"] in design["typography"]
    assert names["TOK-SPACING-MD"] in design["spacing"]
    assert names["TOK-RADIUS-SM"] in design["other_tokens"]
    assert [bp["max_width"] for bp in design["breakpoints"]] == ["768px"]
    assert any(pattern["base_class"] == "btn" and "btn-primary" in pattern["variants"]
               for pattern in design["component_patterns"])


def test_tokens_por_tela_sao_um_recorte_nao_o_catalogo(workspace: Path) -> None:
    """O recorte é o ponto: mandar todo o Design System para toda tela anula o gate."""
    manifest = pm.build_manifest("P", workspace)
    by_id = {screen["screen_id"]: set(screen["design_tokens"])
             for screen in manifest["screens"]}
    # `.data-table` usa --font-size-base; a tela de formulário não tem tabela.
    assert "TOK-FONT-SIZE-BASE" in by_id["SCR-EMPLOYEES-LIST"]
    assert "TOK-FONT-SIZE-BASE" not in by_id["SCR-ABOUT"]
    # `body` usa --color-primary: token global, herdado por todas.
    assert all("TOK-COLOR-PRIMARY" in tokens for tokens in by_id.values())


def test_cenario_3_tela_estatica_sem_api_tem_justificativa(workspace: Path) -> None:
    manifest = pm.build_manifest("P", workspace)
    about = next(screen for screen in manifest["screens"]
                 if screen["screen_id"] == "SCR-ABOUT")
    assert about["dynamic"] is False
    assert about["static_justification"]
    assert about["api_endpoints"] == []
    assert any(warning["code"] == "PM-007" and warning["severity"] == "info"
               for warning in manifest["warnings"])


def test_cenario_4_tela_dinamica_sem_endpoint_gera_warning(tmp_path: Path) -> None:
    """Formulário sem endpoint mapeado avisa — e não inventa operação."""
    project = build_project(tmp_path, with_screen_list=False)
    (project / "outputs" / "tobe" / "prototype" / "screen-list.md").write_text(
        "# Prototype Screen List\n\n"
        "| Screen | Bounded Context | API Endpoint | Status |\n"
        "|---|---|---|---|\n"
        "| Cadastro de Funcionário | BC-01 Employees | N/A | included |\n",
        encoding="utf-8")
    manifest = pm.build_manifest("P", tmp_path)
    form = next(screen for screen in manifest["screens"]
                if screen["screen_id"] == "SCR-EMPLOYEES-FORM")
    assert form["dynamic"] is True
    assert form["api_endpoints"] == []
    assert any(warning["code"] == "PM-008" for warning in manifest["warnings"])


def test_cenario_8_prototipo_ausente_nao_produz_conteudo_inventado(tmp_path: Path) -> None:
    build_project(tmp_path, with_prototype=False)
    with pytest.raises(pm.PrototypeManifestError, match="fonte obrigatória ausente"):
        pm.build_manifest("P", tmp_path)

    degraded = pm.build_manifest("P", tmp_path, strict=False)
    assert degraded["screens"] == []
    assert degraded["shared_components"] == []
    assert any(item["code"] == "PM-001" and item["severity"] == "error"
               for item in degraded["warnings"])


def test_project_config_ausente_e_erro_de_fonte(tmp_path: Path) -> None:
    build_project(tmp_path, with_config=False)
    with pytest.raises(pm.PrototypeManifestError, match="project-config.yaml"):
        pm.build_manifest("P", tmp_path)


def test_cenario_9_checksum_detecta_prototipo_alterado(workspace: Path) -> None:
    pm.write_manifest("P", workspace)
    assert pm.verify_checksum("P", workspace)["status"] == "ok"

    prototype = workspace / "projects" / "P" / pm.PROTOTYPE_REL
    prototype.write_text(INDEX_HTML + "<!-- editado depois -->", encoding="utf-8")
    result = pm.verify_checksum("P", workspace)
    assert result["status"] == "stale"
    assert result["expected"] != result["actual"]


def test_cenario_10_determinismo_entre_execucoes(workspace: Path) -> None:
    """Mesmas entradas ⇒ mesmo manifesto, exceto `generated_at` (não normativo)."""
    first = pm.build_manifest("P", workspace)
    second = pm.build_manifest("P", workspace)
    first.pop("generated_at")
    second.pop("generated_at")
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["prototype"]["checksum"] == second["prototype"]["checksum"]


def test_asset_externo_vira_dependencia_e_nao_e_baixado(tmp_path: Path) -> None:
    project = build_project(tmp_path)
    path = project / "outputs" / "tobe" / "prototype" / "index.html"
    path.write_text(
        INDEX_HTML.replace(
            "<body>",
            '<body><img src="https://cdn.example.com/logo.png" alt="logo"/>'),
        encoding="utf-8")
    manifest = pm.build_manifest("P", tmp_path)
    external = [asset for asset in manifest["prototype"]["assets"]
                if asset["scope"] == "external"]
    assert [asset["path"] for asset in external] == ["https://cdn.example.com/logo.png"]
    assert external[0]["checksum"] is None
    assert any(warning["code"] == "PM-030" for warning in manifest["warnings"])


def test_path_traversal_em_asset_e_recusado(tmp_path: Path) -> None:
    project = build_project(tmp_path)
    path = project / "outputs" / "tobe" / "prototype" / "index.html"
    path.write_text(
        INDEX_HTML.replace(
            "<body>", '<body><img src="../../../../../../etc/passwd"/>'),
        encoding="utf-8")
    manifest = pm.build_manifest("P", tmp_path)
    assert all("passwd" not in asset["path"]
               for asset in manifest["prototype"]["assets"])
    assert any(warning["code"] in {"PM-010", "PM-011"}
               for warning in manifest["warnings"])


def test_manifesto_conforma_ao_schema(workspace: Path) -> None:
    manifest = pm.write_manifest("P", workspace)
    assert pm.validate_manifest(manifest) == []
    on_disk = json.loads(pm.manifest_path("P", workspace).read_text(encoding="utf-8"))
    assert on_disk["schema_version"] == pm.SCHEMA_VERSION


def test_casamento_de_nome_tolera_conjugacao_mas_nao_confunde_entidade() -> None:
    """`Lista de X` casa com `Listar X`; `funcao` nunca casa com `funcionario`."""
    assert pm._name_similarity("Lista de Funcionários", "Listar Funcionários") == 1.0
    assert pm._name_similarity("Cadastro de Funcionário",
                               "Cadastrar / Editar Funcionário") == pytest.approx(2 / 3)
    assert pm._name_similarity("Lista de Funções", "Listar Funcionários") < 1.0
    assert not pm._tokens_equivalent("funcao", "funcionario")
    assert pm._tokens_equivalent("cadastro", "cadastrar")
