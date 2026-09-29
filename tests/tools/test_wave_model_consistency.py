"""Contract tests da reconciliação determinística do wave-model.json (F2d).

O caso que originou a tool está em `test_id_textual_sem_bc_details_e_o_defeito_da_f3s`:
o modelo declarava `bounded_contexts: ["BC-02"]` sem `bc_details[]`, e a F3S
abortou a expansão com todos os artefatos do gate de entrada presentes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "shared" / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import speckit_wave_manifest as manifest  # noqa: E402
import wave_model_consistency as coerencia  # noqa: E402


def _projeto(root: Path, model: dict, *, plan: str | None = None,
             bc_map: str | None = None) -> Path:
    project = root / "projects" / "P"
    outputs = project / "outputs"
    (outputs / "tobe" / "migration").mkdir(parents=True)
    (outputs / "tobe" / "docs" / "openapi").mkdir(parents=True)
    (outputs / "tobe" / "qa").mkdir(parents=True)
    (outputs / "asis" / "docs").mkdir(parents=True)

    (outputs / "tobe" / "migration" / "wave-model.json").write_text(
        json.dumps(model, ensure_ascii=False), encoding="utf-8")
    (outputs / "tobe" / "docs" / "wave-plan.md").write_text(
        plan if plan is not None else
        "# Wave Plan\n\n## W0 — Foundation\n\n### Scope\n- Plataforma\n\n"
        "## W1 — Role Management\n\n### Scope\n- BC-02: Role Management\n",
        encoding="utf-8")
    (outputs / "tobe" / "docs" / "bounded-context-map.md").write_text(
        bc_map if bc_map is not None else
        "# Bounded Context Map\n\n## BC-02: Role Management\n\nUpstream.\n",
        encoding="utf-8")
    return project


def _modelo_legado() -> dict:
    """O formato exato que quebrou a F3S: ID textual, sem bc_details."""
    return {
        "project_name": "P",
        "trace_id": "trace-wave",
        "total_waves": 2,
        "waves": [
            {"wave_id": "W0", "wave_name": "Foundation", "wave_type": "foundation",
             "tshirt_size": "M", "bounded_contexts": []},
            {"wave_id": "W1", "wave_name": "Role Management",
             "wave_type": "domain_write", "tshirt_size": "S",
             "bounded_contexts": ["BC-02"]},
        ],
    }


def test_id_textual_sem_bc_details_e_o_defeito_da_f3s(tmp_path: Path) -> None:
    """Antes do reparo o manifesto da F3S reprova — é o defeito reproduzido."""
    _projeto(tmp_path, _modelo_legado())
    with pytest.raises(manifest.ManifestError) as exc:
        manifest.build_manifest("P", tmp_path)
    assert "bc_details" in str(exc.value)


def test_diagnostico_nao_escreve_e_aponta_a_conversao(tmp_path: Path) -> None:
    project = _projeto(tmp_path, _modelo_legado())
    antes = (project / "outputs" / "tobe" / "migration" / "wave-model.json").read_text(
        encoding="utf-8")

    resultado = coerencia.analyze("P", tmp_path)

    assert resultado["status"] == "fixable"
    assert resultado["written"] is False
    assert any("convertido de ID textual" in item for item in resultado["fixes"])
    assert (project / "outputs" / "tobe" / "migration" / "wave-model.json").read_text(
        encoding="utf-8") == antes


def test_fix_resolve_o_nome_pelo_bc_map_e_a_f3s_expande(tmp_path: Path) -> None:
    project = _projeto(tmp_path, _modelo_legado())

    resultado = coerencia.analyze("P", tmp_path, fix=True)

    assert resultado["status"] == "ok", resultado["errors"]
    assert resultado["manifest_total_waves"] == 2

    gravado = json.loads(
        (project / "outputs" / "tobe" / "migration" / "wave-model.json").read_text(
            encoding="utf-8"))
    w1 = gravado["waves"][1]
    assert w1["bounded_contexts"] == [{"bc_id": "BC-02", "bc_name": "Role Management"}]
    assert "bc_details" not in w1
    assert w1["wave_number"] == 1 and w1["tshirt"] == "S"
    assert w1["depends_on_waves"] == ["W0"]
    # A guarda de projeto do manifesto só olha para `project`/`metadata.project_name`.
    assert gravado["metadata"]["project_name"] == "P"

    # O manifesto real — o mesmo que a F3S chama — expande a partir do disco.
    assert manifest.build_manifest("P", tmp_path)["total_waves"] == 2


def test_fix_e_idempotente(tmp_path: Path) -> None:
    _projeto(tmp_path, _modelo_legado())
    coerencia.analyze("P", tmp_path, fix=True)

    segunda = coerencia.analyze("P", tmp_path, fix=True)

    assert segunda["status"] == "ok"
    assert segunda["fixes"] == []


def test_bc_details_com_alias_name_e_absorvido(tmp_path: Path) -> None:
    """`name` é a grafia que agentes gravaram; o leitor a jusante só lê `bc_name`."""
    modelo = _modelo_legado()
    modelo["waves"][1]["bc_details"] = [{"bc_id": "BC-02", "name": "Role Management",
                                        "migration_strategy": "Strangler Fig"}]
    project = _projeto(tmp_path, modelo)

    resultado = coerencia.analyze("P", tmp_path, fix=True)

    assert resultado["status"] == "ok", resultado["errors"]
    w1 = json.loads(
        (project / "outputs" / "tobe" / "migration" / "wave-model.json").read_text(
            encoding="utf-8"))["waves"][1]
    assert w1["bounded_contexts"][0]["bc_name"] == "Role Management"
    assert w1["bounded_contexts"][0]["migration_strategy"] == "Strangler Fig"
    assert "bc_details" not in w1


def test_bc_details_orfao_e_erro_nao_reparo(tmp_path: Path) -> None:
    """Definição sem referência é o inverso do defeito — e igualmente incoerente."""
    modelo = _modelo_legado()
    modelo["waves"][1]["bc_details"] = [
        {"bc_id": "BC-02", "bc_name": "Role Management"},
        {"bc_id": "BC-09", "bc_name": "Fantasma"},
    ]
    _projeto(tmp_path, modelo)

    resultado = coerencia.analyze("P", tmp_path, fix=True)

    assert resultado["status"] == "error"
    assert resultado["written"] is False
    assert any("BC-09" in item for item in resultado["errors"])


def test_bc_sem_definicao_no_bc_map_reprova(tmp_path: Path) -> None:
    modelo = _modelo_legado()
    modelo["waves"][1]["bounded_contexts"] = ["BC-77"]
    _projeto(tmp_path, modelo,
             plan="# Wave Plan\n\n## W0 — Foundation\n\n## W1 — Role Management\n")

    resultado = coerencia.analyze("P", tmp_path, fix=True)

    assert resultado["status"] == "error"
    assert any("BC-77" in item for item in resultado["errors"])


def test_bc_repetido_em_wave_posterior_e_removido_da_composicao(tmp_path: Path) -> None:
    """A wave que MIGRA o BC é a primeira; as seguintes só o referenciam.

    Padrão medido em cadastro-funcionario-02: com 5 waves fixas e poucos BCs,
    sobra wave de domínio sem BC próprio, e o agente lhe dá escopo transversal
    relistando os BCs já migrados. `bounded_contexts[]` não significa "toca" e
    sim "migra": relistar faz duas features reivindicarem as mesmas âncoras e a
    F3S gerar spec/task duplicadas para o mesmo BC.
    """
    modelo = _modelo_legado()
    modelo["waves"][0]["bounded_contexts"] = ["BC-02"]   # W0 migra
    modelo["waves"][1]["bounded_contexts"] = ["BC-02"]   # W1 apenas referencia
    project = _projeto(tmp_path, modelo,
                       plan="# Wave Plan\n\n## W0 — Foundation\n\n## W1 — Role Management\n")

    resultado = coerencia.analyze("P", tmp_path, fix=True)

    assert resultado["status"] == "ok", resultado["errors"]
    assert any("removido(s) de bounded_contexts" in item for item in resultado["fixes"])

    waves = json.loads(
        (project / "outputs" / "tobe" / "migration" / "wave-model.json").read_text(
            encoding="utf-8"))["waves"]
    assert [c["bc_id"] for c in waves[0]["bounded_contexts"]] == ["BC-02"]
    assert waves[1]["bounded_contexts"] == []


def test_wave_sem_bc_proprio_gera_aviso_nao_erro(tmp_path: Path) -> None:
    """Ficar sem BC é sinal para revisão humana, não motivo para travar a fase."""
    modelo = _modelo_legado()
    modelo["waves"][0]["bounded_contexts"] = ["BC-02"]
    modelo["waves"][1]["bounded_contexts"] = ["BC-02"]
    _projeto(tmp_path, modelo,
             plan="# Wave Plan\n\n## W0 — Foundation\n\n## W1 — Role Management\n")

    resultado = coerencia.analyze("P", tmp_path, fix=True)

    assert resultado["status"] == "ok"
    assert any("sem Bounded Context próprio" in item for item in resultado["warnings"])


def test_composicao_divergente_do_wave_plan_reprova(tmp_path: Path) -> None:
    _projeto(tmp_path, _modelo_legado(),
             plan="# Wave Plan\n\n## W0 — Foundation\n\n## W1 — Role Management\n\n"
                  "### Scope\n- BC-05: Outro Contexto\n",
             bc_map="## BC-02: Role Management\n\n## BC-05: Outro Contexto\n")

    resultado = coerencia.analyze("P", tmp_path, fix=True)

    assert resultado["status"] == "error"
    assert any("wave-plan.md divergem" in item for item in resultado["errors"])


def test_total_waves_divergente_e_corrigido(tmp_path: Path) -> None:
    modelo = _modelo_legado()
    modelo["total_waves"] = 5
    _projeto(tmp_path, modelo)

    resultado = coerencia.analyze("P", tmp_path, fix=True)

    assert resultado["status"] == "ok", resultado["errors"]
    assert any("total_waves corrigido" in item for item in resultado["fixes"])


def test_modelo_de_outro_projeto_reprova(tmp_path: Path) -> None:
    modelo = _modelo_legado()
    modelo["metadata"] = {"project_name": "OutroProjeto"}
    _projeto(tmp_path, modelo)

    resultado = coerencia.analyze("P", tmp_path, fix=True)

    assert resultado["status"] == "error"
    assert any("OutroProjeto" in item for item in resultado["errors"])


def test_modelo_ausente_e_erro_nomeado(tmp_path: Path) -> None:
    (tmp_path / "projects" / "P" / "outputs").mkdir(parents=True)

    with pytest.raises(coerencia.ConsistencyError) as exc:
        coerencia.analyze("P", tmp_path)
    assert "wave-model.json ausente" in str(exc.value)


def test_forma_canonica_ja_correta_nao_gera_reparo(tmp_path: Path) -> None:
    modelo = {
        "metadata": {"project_name": "P", "trace_id": "trace-wave"},
        "total_waves": 2,
        "waves": [
            {"wave_id": "W0", "wave_number": 0, "wave_name": "Foundation",
             "wave_type": "foundation", "tshirt": "M", "bounded_contexts": [],
             "depends_on_waves": []},
            {"wave_id": "W1", "wave_number": 1, "wave_name": "Role Management",
             "wave_type": "domain_write", "tshirt": "S",
             "bounded_contexts": [{"bc_id": "BC-02", "bc_name": "Role Management"}],
             "depends_on_waves": ["W0"]},
        ],
    }
    _projeto(tmp_path, modelo)

    resultado = coerencia.analyze("P", tmp_path)

    assert resultado["status"] == "ok", resultado["errors"]
    assert resultado["fixes"] == []


def test_dependencies_vazio_e_declaracao_e_nao_lacuna(tmp_path: Path) -> None:
    """`dependencies: []` é o campo que o manifesto lê primeiro — não duplicar."""
    modelo = _modelo_legado()
    modelo["waves"][1]["dependencies"] = []
    project = _projeto(tmp_path, modelo)

    resultado = coerencia.analyze("P", tmp_path, fix=True)

    assert resultado["status"] == "ok", resultado["errors"]
    w1 = json.loads(
        (project / "outputs" / "tobe" / "migration" / "wave-model.json").read_text(
            encoding="utf-8"))["waves"][1]
    assert w1["dependencies"] == []
    assert "depends_on_waves" not in w1


def test_contrato_json_tem_precedencia_sobre_o_markdown(tmp_path: Path) -> None:
    """O `.json` do trigger BC é lido por json.load; o `.md` é o fallback."""
    project = _projeto(tmp_path, _modelo_legado(),
                       bc_map="## BC-02: Nome Desatualizado Do Markdown\n")
    (project / "outputs" / "tobe" / "docs" / "bounded-context-map.json").write_text(
        json.dumps({
            "schema_version": "1.0.0",
            "bounded_contexts": [{"bc_id": "BC-02", "bc_name": "Role Management"}],
        }, ensure_ascii=False), encoding="utf-8")

    resultado = coerencia.analyze("P", tmp_path, fix=True)

    assert resultado["status"] == "ok", resultado["errors"]
    assert resultado["waves"][1]["bounded_contexts"][0]["bc_name"] == "Role Management"


def test_a_definir_no_json_nao_vira_nome_de_bc(tmp_path: Path) -> None:
    """Default explícito do contrato é lacuna declarada, não nome."""
    project = _projeto(tmp_path, _modelo_legado())
    (project / "outputs" / "tobe" / "docs" / "bounded-context-map.json").write_text(
        json.dumps({"bounded_contexts": [{"bc_id": "BC-02", "bc_name": "A definir"}]}),
        encoding="utf-8")

    resultado = coerencia.analyze("P", tmp_path, fix=True)

    # Cai no markdown, que nomeia o BC de verdade.
    assert resultado["status"] == "ok", resultado["errors"]
    assert resultado["waves"][1]["bounded_contexts"][0]["bc_name"] == "Role Management"


def test_json_corrompido_degrada_para_o_markdown(tmp_path: Path) -> None:
    project = _projeto(tmp_path, _modelo_legado())
    (project / "outputs" / "tobe" / "docs" / "bounded-context-map.json").write_text(
        "{ isto não é json", encoding="utf-8")

    resultado = coerencia.analyze("P", tmp_path, fix=True)

    assert resultado["status"] == "ok", resultado["errors"]
    assert resultado["waves"][1]["bounded_contexts"][0]["bc_name"] == "Role Management"
