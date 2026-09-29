"""
Testes das suítes de check da F3S — `speckit_traceability` e `prototype_coverage`.

O teste central deste arquivo é `test_ancora_inventada_reprova`. A auditoria de
`nopcommerce-02-cli-ava` encontrou a matriz de rastreabilidade gerada pela
esteira marcando **as 15 linhas AS-IS→TO-BE→TC como ✅ para classes que não
existiam no código gerado** — "a matriz é um falso positivo integral".

Uma matriz que se auto-declara completa não vale nada. O que vale é o check
reabrir o arquivo-fonte e procurar a âncora. Se a verificação de âncora parar de
funcionar, o repositório volta ao estado auditado sem que ninguém perceba — por
isso ela tem teste próprio.

Roda com o Python do repo:
    python -m pytest tests/ava-fabric-agents/speckit/test_speckit_check_suites.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.shared.checks.context import CheckContext  # noqa: E402
from src.shared import checks as checks_module  # noqa: E402
from src.shared.checks.reporter import Reporter  # noqa: E402
from src.shared.checks.suites.prototype_coverage import PrototypeCoverageSuite  # noqa: E402
from src.shared.checks.suites.speckit_traceability import (  # noqa: E402
    SpeckitTraceabilitySuite,
)


# ─── Fixture: um projeto sintético completo e coerente ───────────────────────

BUSINESS_RULES = """# Regras de Negócio AS-IS

## BR-CART-001 — Quantidade mínima no carrinho
A quantidade de um item precisa ser inteira e maior que zero.

## BR-PRICE-001 — Desconto por faixa
Pedidos com 10 ou mais unidades recebem 5% de desconto.
"""

OPENAPI = """openapi: 3.1.0
info:
  title: Cart
paths:
  /api/v1/cart:
    get:
      operationId: getCart
  /api/v1/cart/items:
    post:
      operationId: addCartItem
"""

TEST_CASES = """# Casos de Teste

| ID | Cenário |
|---|---|
| TC-CART-003 | Adicionar item ao carrinho |
"""

SCREEN_LIST = """## Warnings

| Artefato | Consequência |
|---|---|
| `outputs/tobe/docs/api-map.md` | Mapeamento tela→endpoint pode ser impreciso |

# Prototype Screen List

| Screen | Bounded Context | API Endpoint | Status |
|---|---|---|---|
| Carrinho de Compras | Orders | `GET /api/v1/cart` | included |
"""

INDEX_HTML = """<!DOCTYPE html>
<html lang="pt-BR"><body>
<section class="screen active" id="screen-carrinho-de-compras" aria-label="Carrinho">
  <h1>Carrinho de Compras</h1>
  <form id="form-carrinho"><input name="quantidade" required min="1"></form>
  <!-- Prototype metadata
    Screen : Carrinho de Compras
    API    : GET /api/v1/cart
  -->
</section>
</body></html>
"""

DESIGN_TOKENS = json.dumps({
    "schema_version": "1.0",
    "colors": {"primary": "#1565C0"},
    "layout": {"sidebar_width": "240px"},
})

SPEC_PROTOTYPE = """# Especificação do Protótipo

## 1. Visão Geral

Avisos herdados da fonte: `outputs/tobe/docs/api-map.md` ausente — mapeamento
tela para endpoint pode ser impreciso.

## 2. Inventário de Telas

#### SCREEN-001 — Carrinho de Compras

| Campo | Valor |
|---|---|
| `screen_id` | `screen-carrinho-de-compras` |
| Rota | `/cart` |

- Chamadas de API: `GET /api/v1/cart`

## 5. Formulários e Validação

Formulário `form-carrinho`: campo quantidade obrigatório, inteiro >= 1.

## 8. UX e Acessibilidade

| Token | Valor | Alvo |
|---|---|---|
| primary | #1565C0 | $color-primary |
| sidebar_width | 240px | $layout-sidebar-width |

## 9. Cenários de Teste

| ID | Tela | Cenário |
|---|---|---|
| TC-CART-003 | screen-carrinho-de-compras | Adicionar item |

## Context

Especificação do protótipo navegável.

## Input

`index.html`, `screen-list.md`, `design-tokens.json`.

## Processing

Extração conforme P2C §2.

## Output

Telas, rotas, componentes e cenários.

## Examples

Tela `screen-carrinho-de-compras` → rota `/cart`.

## Failure Modes

Fonte ausente ⇒ BLOQUEADO.
"""

TASKS_MD = """# Tasks — visão humana derivada de traceability.json

| Task ID | Título | Grupo | Stack | Arquivo alvo |
|---|---|---|---|---|
| T-CART-004 | Implementar o agregado Cart | G-CART-DOMAIN | dotnet | Domain/Orders/Cart.cs |
"""


def _traceability(anchor: str = "BR-CART-001") -> dict:
    return {
        "schema_version": "4.0.0",
        "project": "P",
        "trace_id": "t-1",
        "generated_at": "2026-08-12T00:00:00Z",
        "constitution": "outputs/tobe/speckit/constitution.md",
        "total_tasks": 1,
        "graph_checksum": "a" * 64,
        "dependency_edges": [],
        "execution_order": ["T-CART-004"],
        "execution_waves": [["T-CART-004"]],
        "entries": [{
            "task_id": "T-CART-004",
            "title": "Implementar carrinho",
            "spec_id": "SPEC-BR-014",
            "plan_id": "PLAN-BR-001",
            "feature": "001-w1-orders",
            "group": "G-CART-DOMAIN",
            "migration_wave_id": "W1",
            "migration_wave_order": 1,
            "task_type": "backend",
            "target_stack": "dotnet",
            "source_refs": [{
                "artifact": "outputs/asis/docs/business-rules.md",
                "anchor": anchor,
            }],
            "rule_ids": ["BR-CART-001", "BR-PRICE-001"],
            "api_ops": ["GET /api/v1/cart", "POST /api/v1/cart/items"],
            "test_ids": ["TC-CART-003"],
            "screen_id": "screen-carrinho-de-compras",
            "target_files": ["backend/src/Domain/Orders/Cart.cs"],
            "action": "create",
            "depends_on": [],
            "backend_dependencies": [],
            "acceptance": ["dotnet build sem erro"],
            "verify_command": "dotnet build",
            "priority": "P2",
            "story_points": 1,
            "topological_rank": 0,
            "execution_wave": 0,
        }],
    }


@pytest.fixture
def projeto(tmp_path: Path, monkeypatch) -> CheckContext:
    root = tmp_path
    out = root / "projects" / "P" / "outputs"

    (out / "asis" / "docs").mkdir(parents=True)
    (out / "asis" / "docs" / "business-rules.md").write_text(BUSINESS_RULES, encoding="utf-8")

    (out / "tobe" / "docs" / "openapi").mkdir(parents=True)
    (out / "tobe" / "docs" / "openapi" / "bc01.yaml").write_text(OPENAPI, encoding="utf-8")
    (out / "tobe" / "qa").mkdir(parents=True)
    (out / "tobe" / "qa" / "test-cases.md").write_text(TEST_CASES, encoding="utf-8")

    proto = out / "tobe" / "prototype"
    proto.mkdir(parents=True)
    (proto / "screen-list.md").write_text(SCREEN_LIST, encoding="utf-8")
    (proto / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (proto / "design-tokens.json").write_text(DESIGN_TOKENS, encoding="utf-8")

    # Layout SpecKit: uma pasta por feature, com o trio spec/plan/tasks dentro.
    sk = out / "tobe" / "speckit"
    feature = sk / "specs" / "001-w1-orders"
    feature.mkdir(parents=True)
    (sk / "constitution.md").write_text("# Constituição\n" + "x" * 500, encoding="utf-8")
    (feature / "spec.md").write_text(SPEC_PROTOTYPE, encoding="utf-8")
    (feature / "plan.md").write_text("# Plano\n" + "x" * 500, encoding="utf-8")
    (feature / "plan-graph.json").write_text("{}", encoding="utf-8")
    (feature / "task-fragment.json").write_text("{}", encoding="utf-8")
    (feature / "tasks.md").write_text(TASKS_MD, encoding="utf-8")
    (sk / "wave-spec-manifest.json").write_text(json.dumps({
        "features": [{
            "feature": "001-w1-orders", "wave_id": "W1", "codegen": True,
            "sources": [{
                "source_id": "prototype",
                "artifact": "outputs/tobe/prototype/screen-list.md",
                "anchors": ["Carrinho de Compras"],
            }],
        }],
    }), encoding="utf-8")
    (sk / "traceability.json").write_text(json.dumps(_traceability()), encoding="utf-8")

    monkeypatch.setattr(CheckContext, "REPO_ROOT", root)
    return CheckContext("P")


def _run(suite_cls, ctx) -> dict[str, bool]:
    reporter = Reporter(verbose=False)
    suite_cls(ctx).run(reporter)
    return {r.name.split()[0]: r.passed for r in reporter._results}


def test_json_out_relativo_resolve_no_projeto_sem_prefixo_duplicado(tmp_path, monkeypatch):
    class SuiteStub:
        def __init__(self, ctx):
            self.ctx = ctx

        def run(self, reporter):
            reporter.record("stub", "CHK-STUB-001", True)

    root = tmp_path
    project_dir = root / "projects" / "P"
    project_dir.mkdir(parents=True)
    monkeypatch.setattr(CheckContext, "REPO_ROOT", root)
    monkeypatch.setitem(checks_module._SUITES, "stub", SuiteStub)

    checks_module.run_checks_detailed(
        "P", suite="stub", json_out="outputs/tobe/speckit/checks-report.json"
    )

    expected = project_dir / "outputs" / "tobe" / "speckit" / "checks-report.json"
    duplicated = project_dir / "projects" / "P" / "outputs" / "tobe" / "speckit" / "checks-report.json"
    assert expected.is_file()
    assert not duplicated.exists()


def test_json_out_absoluto_preserva_destino(tmp_path, monkeypatch):
    class SuiteStub:
        def __init__(self, ctx):
            self.ctx = ctx

        def run(self, reporter):
            reporter.record("stub", "CHK-STUB-001", True)

    root = tmp_path
    (root / "projects" / "P").mkdir(parents=True)
    absolute_target = tmp_path / "external" / "checks-report.json"
    monkeypatch.setattr(CheckContext, "REPO_ROOT", root)
    monkeypatch.setitem(checks_module._SUITES, "stub-absolute", SuiteStub)

    checks_module.run_checks_detailed(
        "P", suite="stub-absolute", json_out=absolute_target
    )

    assert absolute_target.is_file()


# ─── speckit_traceability ────────────────────────────────────────────────────

def test_projeto_coerente_passa_nos_checks_de_conteudo(projeto):
    r = _run(SpeckitTraceabilitySuite, projeto)
    for chk in ("CHK-SK-001", "CHK-SK-002", "CHK-SK-003", "CHK-SK-004",
                "CHK-SK-005", "CHK-SK-006", "CHK-SK-007", "CHK-SK-008",
                "CHK-SK-009", "CHK-SK-010", "CHK-SK-016", "CHK-SK-017",
                "CHK-SK-018"):
        assert r[chk] is True, f"{chk} deveria passar no projeto coerente"


def test_dependencia_inexistente_reprova(projeto):
    trace = _traceability()
    trace["entries"][0]["depends_on"] = ["T-INEXISTENTE-001"]
    (projeto.outputs_dir / "tobe" / "speckit" / "traceability.json").write_text(
        json.dumps(trace), encoding="utf-8")

    r = _run(SpeckitTraceabilitySuite, projeto)
    assert r["CHK-SK-016"] is False
    assert r["CHK-SK-017"] is False
    assert r["CHK-SK-018"] is False


def test_dependencia_backend_de_frontend_inconsistente_reprova(projeto):
    trace = _traceability()
    backend = trace["entries"][0]
    backend["task_type"] = "backend"
    backend["backend_dependencies"] = []
    frontend = dict(backend)
    frontend.update({
        "task_id": "T-CART-UI-001",
        "task_type": "frontend",
        "target_files": ["frontend/src/cart/cart.page.ts"],
        "depends_on": ["T-CART-004"],
        "backend_dependencies": [],
    })
    trace["entries"].append(frontend)
    (projeto.outputs_dir / "tobe" / "speckit" / "traceability.json").write_text(
        json.dumps(trace), encoding="utf-8")

    r = _run(SpeckitTraceabilitySuite, projeto)

    assert r["CHK-SK-016"] is False
    assert r["CHK-SK-017"] is True


def test_ciclo_reprova(projeto):
    trace = _traceability()
    second = dict(trace["entries"][0])
    second["task_id"] = "T-CART-005"
    second["target_files"] = ["backend/src/Domain/Orders/CartItem.cs"]
    trace["entries"][0]["depends_on"] = ["T-CART-005"]
    second["depends_on"] = ["T-CART-004"]
    trace["entries"].append(second)
    (projeto.outputs_dir / "tobe" / "speckit" / "traceability.json").write_text(
        json.dumps(trace), encoding="utf-8")

    r = _run(SpeckitTraceabilitySuite, projeto)
    assert r["CHK-SK-016"] is True
    assert r["CHK-SK-017"] is False
    assert r["CHK-SK-018"] is False


def test_ordem_persistida_divergente_reprova(projeto):
    trace = _traceability()
    trace["execution_order"] = ["T-FANTASMA-001"]
    trace["execution_waves"] = [["T-FANTASMA-001"]]
    (projeto.outputs_dir / "tobe" / "speckit" / "traceability.json").write_text(
        json.dumps(trace), encoding="utf-8")

    r = _run(SpeckitTraceabilitySuite, projeto)
    assert r["CHK-SK-018"] is False


def test_ancora_inventada_reprova(projeto):
    """O check que separa rastreabilidade verificável de narrativa.

    A entrada afirma proveniência numa regra que não existe no arquivo-fonte —
    exatamente a forma do falso positivo que a auditoria encontrou.
    """
    (projeto.outputs_dir / "tobe" / "speckit" / "traceability.json").write_text(
        json.dumps(_traceability(anchor="BR-INEXISTENTE-999")), encoding="utf-8")
    r = _run(SpeckitTraceabilitySuite, projeto)
    assert r["CHK-SK-006"] is False


def test_arquivo_fonte_inexistente_reprova(projeto):
    trace = _traceability()
    trace["entries"][0]["source_refs"][0]["artifact"] = "outputs/asis/docs/nao-existe.md"
    (projeto.outputs_dir / "tobe" / "speckit" / "traceability.json").write_text(
        json.dumps(trace), encoding="utf-8")
    r = _run(SpeckitTraceabilitySuite, projeto)
    assert r["CHK-SK-006"] is False


def test_task_sem_linha_de_rastreabilidade_reprova(projeto):
    trace = _traceability()
    trace["entries"] = []
    (projeto.outputs_dir / "tobe" / "speckit" / "traceability.json").write_text(
        json.dumps(trace), encoding="utf-8")
    r = _run(SpeckitTraceabilitySuite, projeto)
    assert r["CHK-SK-005"] is False


def test_regra_de_negocio_sem_task_reprova(projeto):
    trace = _traceability()
    trace["entries"][0]["rule_ids"] = ["BR-CART-001"]  # BR-PRICE-001 fica órfã
    (projeto.outputs_dir / "tobe" / "speckit" / "traceability.json").write_text(
        json.dumps(trace), encoding="utf-8")
    r = _run(SpeckitTraceabilitySuite, projeto)
    assert r["CHK-SK-007"] is False


def test_operacao_de_api_sem_task_reprova(projeto):
    trace = _traceability()
    trace["entries"][0]["api_ops"] = ["GET /api/v1/cart"]  # falta o POST
    (projeto.outputs_dir / "tobe" / "speckit" / "traceability.json").write_text(
        json.dumps(trace), encoding="utf-8")
    r = _run(SpeckitTraceabilitySuite, projeto)
    assert r["CHK-SK-008"] is False


def test_caso_de_teste_sem_task_reprova(projeto):
    trace = _traceability()
    trace["entries"][0]["test_ids"] = []
    (projeto.outputs_dir / "tobe" / "speckit" / "traceability.json").write_text(
        json.dumps(trace), encoding="utf-8")
    r = _run(SpeckitTraceabilitySuite, projeto)
    assert r["CHK-SK-009"] is False


def test_alvo_que_e_diretorio_reprova(projeto):
    trace = _traceability()
    trace["entries"][0]["target_files"] = ["backend/src/Domain/Orders/"]
    (projeto.outputs_dir / "tobe" / "speckit" / "traceability.json").write_text(
        json.dumps(trace), encoding="utf-8")
    r = _run(SpeckitTraceabilitySuite, projeto)
    assert r["CHK-SK-010"] is False


def test_razao_ausente_reprova_e_orienta(projeto):
    r = _run(SpeckitTraceabilitySuite, projeto)
    assert r["CHK-SK-011"] is False, "tasks-progress.json ainda não foi criado"


def test_verified_sem_evidencia_reprova(projeto):
    """RC-02 da auditoria: `PASS (Simulated)` com o build real falhando."""
    (projeto.outputs_dir / "tobe" / "speckit" / "tasks-progress.json").write_text(json.dumps({
        "schema_version": "1.0.0", "project": "P", "trace_id": "t-1",
        "traceability_checksum": "x",
        "tasks": [{"task_id": "T-CART-004", "spec_id": "SPEC-BR-014",
                   "group": "G-CART-DOMAIN", "target_stack": "dotnet",
                   "status": "verified", "attempts": 1, "evidence": None}],
    }), encoding="utf-8")
    r = _run(SpeckitTraceabilitySuite, projeto)
    assert r["CHK-SK-011"] is True, "os ids batem"
    assert r["CHK-SK-012"] is False, "'verified' sem exit code não pode passar"


def test_verified_com_exit_code_real_passa(projeto):
    (projeto.outputs_dir / "tobe" / "speckit" / "tasks-progress.json").write_text(json.dumps({
        "schema_version": "1.0.0", "project": "P", "trace_id": "t-1",
        "traceability_checksum": "x",
        "tasks": [{"task_id": "T-CART-004", "spec_id": "SPEC-BR-014",
                   "group": "G-CART-DOMAIN", "target_stack": "dotnet",
                   "status": "verified", "attempts": 1,
                   "evidence": {"command": "dotnet build", "exit_code": 0,
                                "recorded_at": "2026-08-12T00:00:00Z"}}],
    }), encoding="utf-8")
    r = _run(SpeckitTraceabilitySuite, projeto)
    assert r["CHK-SK-012"] is True


# ─── prototype_coverage ──────────────────────────────────────────────────────

def test_prototipo_coerente_passa(projeto):
    r = _run(PrototypeCoverageSuite, projeto)
    for chk in ("CHK-PROTO-001", "CHK-PROTO-002", "CHK-PROTO-003",
                "CHK-PROTO-004", "CHK-PROTO-005", "CHK-PROTO-006", "CHK-PROTO-007"):
        assert r[chk] is True, f"{chk} deveria passar no protótipo coerente"


def test_tela_ausente_da_spec_reprova(projeto):
    """O mecanismo exato que deixou 7 de 15 telas fora do código gerado."""
    lista = (projeto.outputs_dir / "tobe" / "prototype" / "screen-list.md")
    lista.write_text(SCREEN_LIST + "| Checkout | Orders | `POST /api/v1/orders` | included |\n",
                     encoding="utf-8")
    r = _run(PrototypeCoverageSuite, projeto)
    assert r["CHK-PROTO-001"] is False


def test_secao_de_warnings_nao_e_confundida_com_inventario(projeto):
    """P2C §2.1: tudo acima de `# Prototype Screen List` é warning, não tela."""
    r = _run(PrototypeCoverageSuite, projeto)
    assert r["CHK-PROTO-001"] is True, (
        "a linha de warning `outputs/tobe/docs/api-map.md` não pode ser lida como tela")


def test_tela_sem_task_reprova(projeto):
    trace = _traceability()
    trace["entries"][0]["screen_id"] = None
    (projeto.outputs_dir / "tobe" / "speckit" / "traceability.json").write_text(
        json.dumps(trace), encoding="utf-8")
    r = _run(PrototypeCoverageSuite, projeto)
    assert r["CHK-PROTO-003"] is False


def test_token_nao_mapeado_reprova(projeto):
    """`design-tokens.json` não referenciado por nenhum arquivo do frontend foi
    um dos achados da auditoria."""
    (projeto.outputs_dir / "tobe" / "prototype" / "design-tokens.json").write_text(
        json.dumps({"colors": {"primary": "#1565C0", "tertiary": "#FF0000"}}),
        encoding="utf-8")
    r = _run(PrototypeCoverageSuite, projeto)
    assert r["CHK-PROTO-005"] is False


def test_endpoint_fora_do_contrato_reprova(projeto):
    spec = projeto.outputs_dir / "tobe" / "speckit" / "specs" / "001-w1-orders" / "spec.md"
    spec.write_text(SPEC_PROTOTYPE + "\n- Chamada extra: `DELETE /api/v1/inventado`\n",
                    encoding="utf-8")
    r = _run(PrototypeCoverageSuite, projeto)
    assert r["CHK-PROTO-006"] is False


def test_warning_nao_propagado_reprova(projeto):
    spec = projeto.outputs_dir / "tobe" / "speckit" / "specs" / "001-w1-orders" / "spec.md"
    spec.write_text(SPEC_PROTOTYPE.replace(
        "Avisos herdados da fonte: `outputs/tobe/docs/api-map.md` ausente — mapeamento\n"
        "tela para endpoint pode ser impreciso.", "Sem avisos."), encoding="utf-8")
    r = _run(PrototypeCoverageSuite, projeto)
    assert r["CHK-PROTO-007"] is False


# ─── Defeitos expostos pela primeira execução real da F3S ────────────────────
# Cada teste abaixo trava um defeito medido em `nopcommerce-02-cli-ava`, dos dois
# lados: o que o agente produziu fora do contrato, e o que a suíte media errado.

def test_chave_raiz_errada_nomeia_a_causa(projeto):
    """A execução real emitiu a raiz como `tasks`, não `entries`.

    O carregamento tolerante devolvia `[]` e a suíte dizia "nenhuma task",
    escondendo 175 tasks válidas atrás de um erro estrutural mudo.
    """
    trace = _traceability()
    trace["tasks"] = trace.pop("entries")
    (projeto.outputs_dir / "tobe" / "speckit" / "traceability.json").write_text(
        json.dumps(trace), encoding="utf-8")
    reporter = Reporter(verbose=False)
    SpeckitTraceabilitySuite(projeto).run(reporter)
    r013 = next(x for x in reporter._results if x.name.startswith("CHK-SK-013"))
    assert r013.passed is False
    assert "entries" in r013.detail and "tasks" in r013.detail


def test_campo_que_sustenta_o_fan_out_ausente_reprova(projeto):
    """Sem `group`/`target_stack` a F4 não expande — a task não pode ser despachada."""
    trace = _traceability()
    del trace["entries"][0]["target_stack"]
    (projeto.outputs_dir / "tobe" / "speckit" / "traceability.json").write_text(
        json.dumps(trace), encoding="utf-8")
    r = _run(SpeckitTraceabilitySuite, projeto)
    assert r["CHK-SK-013"] is False


def test_v2_sem_campo_de_execucao_reprova_schema(projeto):
    trace = _traceability()
    trace["schema_version"] = "2.0.0"
    trace.update({
        "total_tasks": 1,
        "graph_checksum": "a" * 64,
        "dependency_edges": [],
        "execution_order": ["T-CART-004"],
        "execution_waves": [["T-CART-004"]],
    })
    (projeto.outputs_dir / "tobe" / "speckit" / "traceability.json").write_text(
        json.dumps(trace), encoding="utf-8")

    r = _run(SpeckitTraceabilitySuite, projeto)

    assert r["CHK-SK-013"] is False, "v2 exige verify_command/rank/wave e demais campos"


def test_v2_sem_fragmento_estruturado_reprova_completude(projeto):
    trace = _traceability()
    trace["schema_version"] = "2.0.0"
    trace.update({
        "total_tasks": 1, "graph_checksum": "a" * 64, "dependency_edges": [],
        "execution_order": ["T-CART-004"], "execution_waves": [["T-CART-004"]],
    })
    (projeto.outputs_dir / "tobe" / "speckit" / "traceability.json").write_text(
        json.dumps(trace), encoding="utf-8")
    (projeto.outputs_dir / "tobe" / "speckit" / "specs" / "001-w1-orders"
     / "task-fragment.json").unlink()

    r = _run(SpeckitTraceabilitySuite, projeto)

    assert r["CHK-SK-004"] is False


def test_task_id_fora_do_padrao_reprova(projeto):
    """A execução real usou `TASK-BR-001` contra o `T-XXX-000` do schema."""
    trace = _traceability()
    trace["entries"][0]["task_id"] = "TASK-BR-001"
    (projeto.outputs_dir / "tobe" / "speckit" / "traceability.json").write_text(
        json.dumps(trace), encoding="utf-8")
    r = _run(SpeckitTraceabilitySuite, projeto)
    assert r["CHK-SK-013"] is False


def test_contagem_declarada_divergente_reprova(projeto):
    """`total_tasks: 157` com 175 entradas — número afirmado contra número contado."""
    trace = _traceability()
    trace["total_tasks"] = 99
    (projeto.outputs_dir / "tobe" / "speckit" / "traceability.json").write_text(
        json.dumps(trace), encoding="utf-8")
    r = _run(SpeckitTraceabilitySuite, projeto)
    assert r["CHK-SK-005"] is False


def test_seis_secoes_do_readiness_gate_ausentes_reprovam(projeto):
    """0 de 7 specs tinham as 6 seções — o C2 continuaria reprovando a wave."""
    spec = projeto.outputs_dir / "tobe" / "speckit" / "specs" / "001-w1-orders" / "spec.md"
    spec.write_text(spec.read_text(encoding="utf-8").replace("## Failure Modes", "## Modos de Falha"),
                    encoding="utf-8")
    r = _run(SpeckitTraceabilitySuite, projeto)
    assert r["CHK-SK-014"] is False, "traduzir o heading também reprova o C2"


def test_tabela_de_tasks_divergente_do_json_reprova(projeto):
    feature = projeto.outputs_dir / "tobe" / "speckit" / "specs" / "001-w1-orders"
    (feature / "tasks.md").write_text(
        "| Task ID |\n|---|\n| T-FANTASMA-001 |\n", encoding="utf-8")
    r = _run(SpeckitTraceabilitySuite, projeto)
    assert r["CHK-SK-015"] is False


def test_ancora_nao_passa_sem_dados(projeto):
    """O passe vazio: um check anti-falso-positivo que passava com zero entradas."""
    (projeto.outputs_dir / "tobe" / "speckit" / "traceability.json").write_text(
        json.dumps({"schema_version": "1.0.0", "project": "P", "trace_id": "t",
                    "generated_at": "2026-08-13T00:00:00Z", "entries": []}),
        encoding="utf-8")
    r = _run(SpeckitTraceabilitySuite, projeto)
    assert r["CHK-SK-006"] is False, "verificação sem dado não é verificação"
    assert r["CHK-SK-010"] is False


def test_screen_list_com_h1_antes_dos_warnings_e_lido(projeto):
    """O arquivo real do `ava-prototype` põe o H1 primeiro e os Warnings depois.

    Fatiar pelo H1 fazia a tabela de warnings virar inventário, e 15 telas
    válidas eram reportadas como "nenhuma tela `included`".
    """
    lista = projeto.outputs_dir / "tobe" / "prototype" / "screen-list.md"
    lista.write_text(
        "# Prototype Screen List\n\n"
        "## Warnings\n\n"
        "| Artefato | Impacto |\n|---|---|\n"
        "| `outputs/tobe/docs/api-map.md` | Mapeamento impreciso |\n\n"
        "---\n\n"
        "| Screen | Bounded Context | API Endpoint | Status |\n|---|---|---|---|\n"
        "| Carrinho de Compras | Orders | `GET /api/v1/cart` | included |\n",
        encoding="utf-8")
    r = _run(PrototypeCoverageSuite, projeto)
    assert r["CHK-PROTO-001"] is True, "a tela deve ser encontrada mesmo com o H1 antes"


def test_base_path_do_openapi_nao_gera_falso_positivo(projeto):
    """A spec escreve `/api/v1/cart`; o contrato declara `/cart` sob `servers.url`.

    Comparar cru dava 17/17 falsos positivos em endpoints corretos.
    """
    contrato = projeto.outputs_dir / "tobe" / "docs" / "openapi" / "bc01.yaml"
    contrato.write_text(
        'openapi: 3.1.0\n'
        'servers:\n  - url: "https://api.exemplo.com/api/v1"\n'
        'paths:\n  /cart:\n    get:\n      operationId: getCart\n'
        '  /cart/items:\n    post:\n      operationId: addCartItem\n',
        encoding="utf-8")
    r = _run(PrototypeCoverageSuite, projeto)
    assert r["CHK-PROTO-006"] is True, "o base path do servidor precisa ser removido"
