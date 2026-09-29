"""A barra de progresso mede ENTREGA, não o gate de reprovação da fase.

O dashboard exibia `1/1 · 100%` para toda fase porque o denominador era o
`required` de `PHASE_ARTIFACT_CONTRACT` — lista curta, com só o que bloqueia a
fase seguinte. O `ava-asis-db-analyzer` promete 7 artefatos no seu próprio
`## Output Contract` e o denominador conhecia 1: a barra fechava 100% no
primeiro arquivo gravado e ficava lá.

Três propriedades sustentam a correção e são o que estes testes travam:

1. O denominador vem do contrato de SAÍDA do agente (skill + `outputs` do DAG +
   `required` da fase), não do gate.
2. O numerador sobe DURANTE o streaming — os artefatos só vão para o disco no
   fim do passo, então quem mede o progresso em voo é o texto recebido.
3. Passo sem contrato conhecido continua "sem contrato": nunca 0% nem 100%
   inventado.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PY = REPO_ROOT / "ava-pipeline-runner-cli.py"

# Skill sintético no dialeto YAML — como `db-analyzer.md` declara.
SKILL_YAML = """\
# ava-teste-db

## Input Contract
```yaml
inputs:
  ast: "projects/{project_name}/outputs/asis/ast-raw/index.json"
```

## Output Contract
```yaml
outputs:
  db_type:          "projects/{project_name}/outputs/asis/db/db-type.json"
  schema_inventory: "projects/{project_name}/outputs/asis/db/schema-inventory.md"
  er_diagram:       "projects/{project_name}/outputs/asis/db/er-diagram.mmd"
```

## Output Verification
Conferir os 3 artefatos em disco antes de reportar `completed`.
"""

# Skill sintético no dialeto TABELA — como `documentation-asis.md` declara.
SKILL_TABELA = """\
## Output Contract

Todos os paths são relativos a `projects/{project_name}/outputs/`.

| # | Artefato | Path completo | Obrigatório |
|---|----------|---------------|-------------|
| 1 | `value-chain.md` | `asis/docs/value-chain.md` | Sim |
| 2 | `screen-flow.mmd` | `asis/docs/screen-flow.mmd` | Sim |
| 3 | `prototype-asis/` | `asis/docs/prototype-asis/` | Sim |

Gerar timestamps via `src/shared/utils/ntp_time.py`.
"""

# A tabela de lookup do orquestrador descreve o contrato dos OUTROS agentes, em
# paths relativos a `outputs/asis/`. Não é a entrega DELE.
SKILL_ORQUESTRADOR = """\
### Artifact Output Contract per Agent

Base: `projects/{project_name}/outputs/asis/`

```yaml
artifact_contracts:
  ava-asis-inventory:
    mandatory:
      - "inventory-report.md"
      - "metrics.json"
```

## Output Contract
```yaml
outputs:
  master_report: "projects/{project_name}/outputs/asis/master-report.md"
  report_status: "complete" | "partial"
```
"""


@pytest.fixture(scope="module")
def runner():
    sys.path.insert(0, str(REPO_ROOT / "src" / "shared" / "tools"))
    spec = importlib.util.spec_from_file_location("runner19_progresso", RUNNER_PY)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _stream(*paths: str, aberto: str = "") -> str:
    """Texto de resposta com N blocos FILE fechados e, opcionalmente, um aberto."""
    corpo = "".join(f"<!-- FILE: {p} -->\nconteudo\n<!-- /FILE -->\n" for p in paths)
    if aberto:
        corpo += f"<!-- FILE: {aberto} -->\nconteudo parcial sem fechamento"
    return corpo


# ── 1. Denominador ──────────────────────────────────────────────────────────

def test_denominador_vem_do_output_contract_do_agente(runner):
    """O contrato do agente, não o `required` da fase, dita o total."""
    esperados = runner.expected_artifacts("FX", {}, SKILL_YAML)
    assert esperados == [
        "outputs/asis/db/db-type.json",
        "outputs/asis/db/schema-inventory.md",
        "outputs/asis/db/er-diagram.mmd",
    ]


def test_contrato_declarado_em_tabela_markdown_tambem_e_lido(runner):
    """Nem todo agente declara em YAML — `documentation-asis.md` usa tabela."""
    esperados = runner.expected_artifacts("FX", {}, SKILL_TABELA)
    assert esperados == [
        "outputs/asis/docs/value-chain.md",
        "outputs/asis/docs/screen-flow.mmd",
        "outputs/asis/docs/prototype-asis",
    ]


def test_tabela_de_lookup_do_orquestrador_nao_entra_no_denominador(runner):
    """`### Artifact Output Contract per Agent` é contrato dos OUTROS agentes.

    Casá-la punha `outputs/inventory-report.md` (path mal normalizado, de outro
    agente) no denominador da F1, que então nunca fecharia.
    """
    esperados = runner.expected_artifacts("FX", {}, SKILL_ORQUESTRADOR)
    assert esperados == ["outputs/asis/master-report.md"]


def test_outputs_do_dag_e_required_da_fase_somam_ao_contrato(runner):
    step = {"output_base": "outputs/speckit",
            "outputs": ["specs/003-w2/plan.md", "specs/003-w2/tasks.md"]}
    esperados = runner.expected_artifacts("FX", step, SKILL_YAML)
    assert esperados[-2:] == ["outputs/speckit/specs/003-w2/plan.md",
                              "outputs/speckit/specs/003-w2/tasks.md"]
    assert len(esperados) == 5


def test_saida_de_nome_variavel_fica_fora_do_denominador(runner):
    """Glob não é item contável: o número depende do projeto e travaria a barra."""
    skill = SKILL_YAML.replace(
        '  er_diagram:       "projects/{project_name}/outputs/asis/db/er-diagram.mmd"',
        '  er_diagram:       "projects/{project_name}/outputs/asis/db/er-diagram-*.mmd"')
    assert all("*" not in e for e in runner.expected_artifacts("FX", {}, skill))


def test_mesmo_artefato_em_duas_grafias_conta_uma_vez(runner):
    """`db/x.md` e `x.md` são o mesmo artefato para o matcher — e para o total."""
    skill = SKILL_YAML.replace(
        '  er_diagram:       "projects/{project_name}/outputs/asis/db/er-diagram.mmd"',
        '  er_diagram:       "projects/{project_name}/outputs/asis/db-type.json"')
    esperados = runner.expected_artifacts("FX", {}, skill)
    assert len(esperados) == 2


# ── 2. Progresso durante o streaming ────────────────────────────────────────

def test_barra_sobe_a_cada_artefato_concluido(runner):
    esperados = runner.expected_artifacts("FX", {}, SKILL_YAML)
    entregues = ["projects/P/outputs/asis/db/db-type.json",
                 "projects/P/outputs/asis/db/schema-inventory.md",
                 "projects/P/outputs/asis/db/er-diagram.mmd"]
    vistos = []
    fracoes = []
    for art in entregues:
        vistos.append(art)
        fracoes.append(runner.progresso_contrato(
            runner.artefatos_concluidos_no_stream(_stream(*vistos)), esperados))
    assert fracoes == [(1, 3), (2, 3), (3, 3)]


def test_artefato_ainda_aberto_nao_conta(runner):
    """Contar o bloco em escrita jogaria a barra a 100% no início do último."""
    esperados = runner.expected_artifacts("FX", {}, SKILL_YAML)
    texto = _stream("projects/P/outputs/asis/db/db-type.json",
                    aberto="projects/P/outputs/asis/db/schema-inventory.md")
    assert runner.progresso_contrato(
        runner.artefatos_concluidos_no_stream(texto), esperados) == (1, 3)


def test_entrega_fora_do_contrato_sobe_nos_dois_lados(runner):
    """Orquestrador declara 1 saída e grava dezenas (os sub-agentes gravam nele).

    O extra entra no numerador E no denominador: a barra anda, mas só fecha 100%
    quando o contrato inteiro está entregue.
    """
    esperados = runner.expected_artifacts("FX", {}, SKILL_ORQUESTRADOR)
    texto = _stream("projects/P/outputs/tobe/docs/decisions/ADR-001.md",
                    "projects/P/outputs/tobe/docs/decisions/ADR-002.md")
    assert runner.progresso_contrato(
        runner.artefatos_concluidos_no_stream(texto), esperados) == (2, 3)
    texto += _stream("projects/P/outputs/asis/master-report.md")
    assert runner.progresso_contrato(
        runner.artefatos_concluidos_no_stream(texto), esperados) == (3, 3)


def test_agente_que_erra_a_pasta_ainda_marca_entrega(runner):
    """A barra mede entrega; quem mede o lugar certo é o gate (`required_ok`)."""
    esperados = runner.expected_artifacts("FX", {}, SKILL_YAML)
    texto = _stream("projects/P/outputs/asis/db-type.json")   # sem o `db/`
    assert runner.progresso_contrato(
        runner.artefatos_concluidos_no_stream(texto), esperados) == (1, 3)


# ── 3. Sem contrato continua sem contrato ───────────────────────────────────

def test_passo_sem_contrato_nao_vira_zero_nem_cem(runner):
    assert runner.progresso_contrato(["projects/P/outputs/x.md"], []) == (0, 0)
    assert runner.expected_artifacts("FX", {}, "") == []


def test_passo_expandido_nao_herda_contrato_de_fim_de_fase(runner):
    """`F3S:planning:003-…` é passo intermediário: o contrato da F3S é de FIM."""
    fase = "F3S"
    if not (runner.PHASE_ARTIFACT_CONTRACT.get(fase) or {}).get("required"):
        pytest.skip("F3S sem contrato derivado do DAG neste checkout")
    assert runner.expected_artifacts(f"{fase}:planning:003-w2", {}, "") == []
    assert runner.expected_artifacts(fase, {}, "") != []


# ── 4. O contrato em voo não pode ligar o dashboard sozinho ─────────────────

def test_contrato_em_voo_nao_liga_o_heartbeat_no_despacho_avulso(runner, monkeypatch):
    """`--agent` não popula `_RUN_CTX` — e o contrato do passo não pode mudar isso.

    Pendurar o contrato no `_RUN_CTX` fazia o dict deixar de ser vazio, o guard
    `if not _RUN_CTX` parava de valer, e cada batida de 3s varria a resposta
    inteira por regex para morrer num KeyError engolido pelo try.
    """
    monkeypatch.setattr(runner, "_RUN_CTX", {})
    monkeypatch.setattr(runner, "_CONTRATO_EM_VOO",
                        {"phase": "F1c", "paths": ["outputs/asis/db/x.md"]})
    monkeypatch.setattr(runner, "_last_heartbeat", 0.0)

    chamou = []
    monkeypatch.setattr(runner, "_write_status_html",
                        lambda *a, **k: chamou.append(True))
    runner.status_heartbeat("F1c", None, _stream("a.md"), force=True)

    assert runner._RUN_CTX == {}      # o passo não pode sujar o sinal de dashboard
    assert chamou == []               # e o heartbeat sai no guard, sem varrer nada


def test_contrato_de_outro_passo_nao_pinta_a_barra(runner, monkeypatch):
    """Passo TOOL roda depois de um agente: não pode herdar o contrato dele."""
    monkeypatch.setattr(runner, "_CONTRATO_EM_VOO",
                        {"phase": "F1c", "paths": ["outputs/asis/db/x.md"]})
    monkeypatch.setattr(runner, "_last_heartbeat", 0.0)
    monkeypatch.setattr(runner, "_RUN_CTX", {
        "project": "P", "steps": [], "executed": [], "skipped": [], "aborted": [],
    })

    vistos = {}
    monkeypatch.setattr(runner, "_write_status_html",
                        lambda *a, **k: vistos.update(k.get("live") or {}))
    runner.status_heartbeat("F2d", None, _stream("outputs/asis/db/x.md"),
                            force=True)

    assert (vistos["art_ok"], vistos["art_total"]) == (0, 0)   # "sem contrato"


# ── 5. Validação em disco ───────────────────────────────────────────────────

def test_validacao_em_disco_conta_o_contrato_sem_alargar_o_gate(runner, tmp_path,
                                                               monkeypatch):
    """`ok` continua decidido só pelo `required` — alargar reprovaria por opcional."""
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)
    outputs = tmp_path / "projects" / "P" / "outputs" / "asis" / "db"
    outputs.mkdir(parents=True)
    (outputs / "db-type.json").write_text("{}", encoding="utf-8")
    (outputs / "schema-inventory.md").write_text("# inv", encoding="utf-8")

    esperados = runner.expected_artifacts("FX", {}, SKILL_YAML)
    val = runner.validate_phase_artifacts("FX", "P", [], expected=esperados)

    assert (val["expected_ok"], val["expected_total"]) == (2, 3)
    assert val["expected_missing"] == ["outputs/asis/db/er-diagram.mmd"]
    assert val["ok"] is True          # nenhum `required` de fase para "FX"


def test_artefato_vazio_nao_conta_como_entregue(runner, tmp_path, monkeypatch):
    """Bloco truncado grava arquivo inútil — contá-lo mentiria na barra."""
    monkeypatch.setattr(runner, "WORKSPACE", tmp_path)
    outputs = tmp_path / "projects" / "P" / "outputs" / "asis" / "db"
    outputs.mkdir(parents=True)
    (outputs / "db-type.json").write_text("", encoding="utf-8")

    esperados = runner.expected_artifacts("FX", {}, SKILL_YAML)
    val = runner.validate_phase_artifacts("FX", "P", [], expected=esperados)
    assert val["expected_ok"] == 0
