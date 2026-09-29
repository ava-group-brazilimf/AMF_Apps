"""Contract checks for feature 039 prototype design input behavior."""
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
AGENT = REPO / "src/modules/ava-fabric-agents/prototype/agents/prototype-agent.md"
MODULE = REPO / "src/modules/ava-fabric-agents/prototype/module.yaml"


def test_agent_contract_and_severity_rules_are_present() -> None:
    text = AGENT.read_text(encoding="utf-8")
    assert 'version: "1.3.0"' in text
    assert "design-input-traceability.json" in text
    assert 'limitation_severity": "high|medium|low|none"' in text
    assert 'gate_impact": "blocks|warns|none"' in text
    assert 'source_integrity = \"failed\"' in text
    assert "todo conteúdo do" in text
    assert "client_required" not in text
    assert "arquivo binário `.fig`" in text


def test_module_lists_traceability_output() -> None:
    text = MODULE.read_text(encoding="utf-8")
    assert 'version: "1.3.0"' in text
    assert '"design-input-traceability.json"' in text


def test_traceability_invariants_are_documented() -> None:
    text = AGENT.read_text(encoding="utf-8")
    assert 'source` começar com `fallback-`' in text
    assert 'source` for `client`' in text or 'source` for `client`' in text
    assert "detected_file" in text and "used_file: null" in text
