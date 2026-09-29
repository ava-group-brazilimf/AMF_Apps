"""
Testes do registro canônico de agentes e do gate de consistência (specs/032).

Roda com o Python do repo — não exige o venv da tool:
    python -m pytest tests/tools/test_agent_registry.py -q
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "shared" / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import agent_registry as reg  # noqa: E402


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ─── Varredura ───────────────────────────────────────────────────────────────

def test_varredura_encontra_a_esteira_inteira():
    records = reg.load()
    assert len(records) > 90, "varredura degradou — esperado ~105 arquivos de agente"
    assert len([r for r in records if r["dispatchable"]]) > 90


def test_nenhuma_fase_indefinida():
    """Todo módulo tem de estar em PHASE_BY_MODULE — `?` denuncia módulo novo."""
    orphans = {r["module"] for r in reg.load() if r["phase"] == "?"}
    assert not orphans, f"módulos sem fase mapeada: {sorted(orphans)}"


def test_sub_skills_nao_sao_despachaveis():
    """`agents/*/skills/*.md` são apoio, não agentes — ficam fora do catálogo."""
    skills = [r for r in reg.load() if "/skills/" in r["path"]]
    assert skills, "fixture sumiu: esperados os dialetos sob db-analyzer/skills/"
    assert all(not r["dispatchable"] for r in skills)
    catalogados = {e["agent"] for e in reg.catalog()}
    assert all(r["agent"] not in catalogados for r in skills)


def test_fases_seguem_a_constituicao_v140():
    """A emenda v1.4.0 trocou prototype/tech-stack e devops/deliverables.

    O `module.yaml` da raiz ficou com a numeração antiga; a Constituição vence.
    """
    assert reg.PHASE_BY_MODULE["prototype"] == "F3"
    assert reg.PHASE_BY_MODULE["tech-stack"] == "F4"
    assert reg.PHASE_BY_MODULE["devops-agents"] == "F6"
    assert reg.PHASE_BY_MODULE["deliverables"] == "F7"
    assert reg.PHASE_BY_MODULE["summary"] == "F8"
    assert reg.PHASE_BY_MODULE["master-orchestrator"] == ""


def test_frontmatter_parseado_com_e_sem_aspas():
    """Alguns agentes usam `name: "x"`, outros `name: x` — ambos valem."""
    assert reg.get("ava-stack-react-frontend") is not None   # com aspas
    assert reg.get("ava-qa-exploratory") is not None         # sem aspas


def test_frontmatter_sobrevive_a_bom_utf8(tmp_path, monkeypatch):
    """BOM de 3 bytes nao pode apagar um agente do catalogo.

    `_FRONTMATTER_RE` ancora no inicio absoluto do texto, entao um BOM impede o
    match e o arquivo sai da varredura em silencio. Aconteceu com
    `ava-summary-remediation`: sumiu do catalogo, `validate_plan` reprovou o
    step F8b, `run --all` passou a sair com exit 2, e a divergencia de versao
    dele ficou invisivel ao verificador de observabilidade. Cinco controles
    desligados por tres bytes.
    """
    corpo = '---\nname: "{}"\nversion: "1.0.0"\n---\n# corpo\n'
    raiz = tmp_path / "mod" / "agents"
    raiz.mkdir(parents=True)
    (raiz / "com-bom.md").write_text(corpo.format("ava-teste-bom"),
                                     encoding="utf-8-sig")
    (raiz / "sem-bom.md").write_text(corpo.format("ava-teste-limpo"),
                                     encoding="utf-8")

    monkeypatch.setattr(reg, "AGENTS_ROOT", tmp_path)
    # `_scan` resolve `path.relative_to(PROJECT_ROOT)`; sem mover a raiz
    # junto, o tmp_path fica fora dela e o teste morre antes da asserção.
    monkeypatch.setattr(reg, "PROJECT_ROOT", tmp_path)
    achados = {r["agent"] for r in reg.load(refresh=True)}
    assert "ava-teste-bom" in achados, "BOM voltou a esconder o agente"
    assert "ava-teste-limpo" in achados
    # Desfaz ANTES de recarregar: `_CACHE` e modulo-level, e um refresh com a
    # raiz ainda apontando para tmp_path envenena todos os testes seguintes.
    monkeypatch.undo()
    reg.load(refresh=True)


def test_agente_que_tinha_bom_esta_no_catalogo():
    """Regressao do caso concreto que motivou a correcao."""
    assert reg.get("ava-summary-remediation") is not None


def test_nenhum_agente_com_bom_no_repo():
    """O BOM deixou de ser fatal, mas continua divergencia — trave em zero."""
    com_bom = [p.name for p in reg.AGENTS_ROOT.rglob("agents/**/*.md")
               if p.read_bytes()[:3] == b"\xef\xbb\xbf"]
    assert not com_bom, f"arquivos com BOM UTF-8: {com_bom}"


# ─── Catálogo ────────────────────────────────────────────────────────────────

def test_catalogo_exclui_depreciados():
    depreciados = {r["agent"] for r in reg.load() if r["deprecated"]}
    catalogados = {e["agent"] for e in reg.catalog()}
    # `ava-asis-security-review` tem uma cópia viva e uma DEPRECATED: o id
    # permanece no catálogo, mas vindo do arquivo vivo.
    for agent in depreciados:
        vivos = [r for r in reg.load()
                 if r["agent"] == agent and not r["deprecated"] and r["dispatchable"]]
        if not vivos:
            assert agent not in catalogados


def test_catalogo_nao_tem_entradas_sinteticas():
    """As 7 linhas `ava-summary (F1..F7)` sumiram: existe um `ava-summary` real em F8."""
    agentes = [e["agent"] for e in reg.catalog()]
    assert not [a for a in agentes if "(" in a]
    assert "ava-summary" in agentes
    assert reg.get("ava-summary")["phase"] == "F8"


def test_catalogo_ordenado_por_fase():
    fases = [e["phase"] for e in reg.catalog()]
    indices = [reg.PHASE_ORDER.index(f) if f in reg.PHASE_ORDER else len(reg.PHASE_ORDER)
               for f in fases]
    assert indices == sorted(indices), "catálogo instável entre execuções"


def test_catalog_or_cai_para_o_fallback(monkeypatch):
    """Fora da árvore do repo, o observer continua com a lista estática."""
    monkeypatch.setattr(reg, "catalog", lambda: [])
    fallback = [{"agent": "x", "phase": "F1", "version": "1.0.0"}]
    assert reg.catalog_or(fallback) == fallback


def test_sem_ids_duplicados_vivos():
    """Duas cópias vivas do mesmo id colidiriam na chave do pipeline-run-state."""
    assert reg.duplicates() == {}


# ─── Integração com os consumidores ──────────────────────────────────────────

def test_ambos_os_catalogos_derivam_do_registry():
    """Antes de specs/032 as duas listas divergiam entre si e do disco."""
    esperado = reg.catalog()
    observer = _load(TOOLS_DIR / "pipeline_observer.py", "po_test")
    report = _load(TOOLS_DIR / "generate_observability_report.py", "gor_test")
    assert observer.AGENT_CATALOG == esperado
    assert report.AGENT_CATALOG == esperado
    assert len(esperado) > len(observer._STATIC_AGENT_CATALOG)


def test_f8_reconhecido_pelo_observer():
    """O summary emite `--phase F8`; antes o PHASE_ORDER parava em F7."""
    observer = _load(TOOLS_DIR / "pipeline_observer.py", "po_f8")
    assert "F8" in observer.PHASE_ORDER
    assert "F8" in observer.PHASE_NAMES


def test_ordem_de_fases_identica_no_registry_e_no_observer():
    """Os dois arquivos guardam a MESMA lista de fases — e já divergiram antes.

    O `pipeline_observer` mantém uma cópia de `PHASE_ORDER`/`PHASE_NAMES` por não
    poder importar o registry sem custo. Quem acrescentar uma fase precisa tocar
    os dois; este teste é o que garante isso, em vez de revisão manual.
    """
    observer = _load(TOOLS_DIR / "pipeline_observer.py", "po_ordem")
    assert observer.PHASE_ORDER == reg.PHASE_ORDER
    assert observer.PHASE_NAMES == reg.PHASE_NAMES


def test_f3s_do_speckit_entra_entre_o_prototipo_e_a_codegen():
    """A camada de planejamento roda depois da F3 e antes da F4 — spec 039.

    A posição é o contrato: gerar specs depois da codegen não teria sentido, e
    gerar antes do protótipo deixaria `spec-prototype.md` sem fonte.
    """
    assert reg.PHASE_BY_MODULE["speckit"] == "F3S"
    assert reg.PHASE_ORDER.index("F3") < reg.PHASE_ORDER.index("F3S") < reg.PHASE_ORDER.index("F4")
    assert reg.PHASE_NAMES["F3S"] == "SpecKit Planning"


# ─── Gate de consistência ────────────────────────────────────────────────────

def test_esteira_sem_violacoes():
    """E1–E6 em zero. Falhou aqui = alguém editou um agente à mão e errou."""
    verifier = _load(
        REPO_ROOT / "src" / "shared" / "utils" / "verify_agent_observability.py",
        "verifier_test")
    violations = verifier.collect_violations(reg, ignore=set())
    resumo = "\n".join(f"{v['check']} {v['agent']}: {v['detail']}" for v in violations)
    assert not violations, f"\n{resumo}"


def test_orquestradores_consolidam_a_economia():
    """Os 6 orquestradores têm de invocar `attribute` — é o que fecha a fase."""
    faltando = []
    for agent_id in sorted(reg.PHASE_ORCHESTRATORS):
        record = reg.get(agent_id)
        assert record is not None, f"orquestrador não encontrado: {agent_id}"
        text = (REPO_ROOT / record["path"]).read_text(encoding="utf-8")
        if "headroom_tool.py" not in text or "attribute" not in text:
            faltando.append(agent_id)
    assert not faltando, f"orquestradores sem consolidação Headroom: {faltando}"


def test_agentes_comuns_nao_reportam_metrics_a_mao():
    """O hook do `track` já grava; um `metrics` no .md duplicaria a contagem.

    Casa o subcomando na MESMA linha do script — `--type metrics` de outros
    utilitários não conta.
    """
    padrao = re.compile(r"headroom_tool\.py[^\n]*\bmetrics\b")
    duplicados = [
        record["agent"] for record in reg.load()
        if record["dispatchable"]
        and padrao.search((REPO_ROOT / record["path"]).read_text(encoding="utf-8"))
    ]
    assert not duplicados, f"agentes com `metrics` manual: {duplicados}"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
