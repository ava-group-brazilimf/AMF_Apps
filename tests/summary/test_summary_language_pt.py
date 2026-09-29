"""Focused Phase 2 tests for deterministic PT-BR Summary normalization."""
from __future__ import annotations

import json
import sys
import re
from pathlib import Path

UTILS = Path(__file__).resolve().parents[2] / "src" / "modules" / "ava-fabric-agents" / "summary" / "utils"
sys.path.insert(0, str(UTILS))

from summary_language import (
    normalize_architectural_pattern,
    normalize_text,
)


FIXTURE = Path(__file__).parent / "fixtures" / "038-portuguese-manual-view" / "project"
PATTERNS = json.loads(
    (FIXTURE / "outputs" / "tobe" / "patterns-applied.json").read_text(encoding="utf-8")
)["patterns"]


def test_english_default_is_backward_compatible() -> None:
    omitted = normalize_text("Padrão de referência", "default")
    explicit = normalize_text("Padrão de referência", "default", language_target="en")
    assert omitted.value == explicit.value
    assert omitted.status == explicit.status == "english"
    assert omitted.target == explicit.target == "en"


def test_fixture_patterns_normalize_to_portuguese_deterministically() -> None:
    results = [normalize_architectural_pattern(p, "pattern", language_target="pt") for p in PATTERNS]
    assert results[0][0]["justification"] == "A estratégia de cache reduz a latência das consultas repetidas."
    assert results[0][0]["trade_offs"] == ["Maior consumo de memória", "A invalidação deve permanecer determinística"]
    assert results[1][0]["justification"].startswith("A abstração de repositório")
    assert results[1][0]["trade_offs"] == ["Abstração adicional", "Os testes ficam mais simples"]
    assert "o handler continua responsável" in results[2][0]["justification"]
    assert results[0] == results[0]
    assert [normalize_architectural_pattern(p, "pattern", language_target="pt") for p in PATTERNS] == results


def test_no_consecutive_duplicate_words_in_fixture_pt_output() -> None:
    duplicate = re.compile(r"\b([A-Za-zÀ-ÿ]+)\s+\1\b", re.I)
    for pattern in PATTERNS:
        normalized, _ = normalize_architectural_pattern(pattern, "pattern", language_target="pt")
        prose = [normalized["pattern_name"], normalized["layer"], normalized["justification"], *normalized["trade_offs"]]
        assert not any(duplicate.search(value) for value in prose if isinstance(value, str))


def test_unseen_architecture_sentence_uses_reusable_vocabulary() -> None:
    source = "This pattern reduces coupling between the presentation and domain layers by introducing a mediator."
    result = normalize_text(source, "unseen", language_target="pt")
    assert result.status == "portuguese"
    assert result.value == "Este padrão reduz o acoplamento entre as camadas de apresentação e domínio ao introduzir um mediador."


def test_empty_null_numeric_and_non_text_values_are_not_invented() -> None:
    for target in ("en", "pt"):
        assert normalize_text(None, "null", language_target=target).value is None
        assert normalize_text(17, "number", language_target=target).value == 17
        assert normalize_text("", "empty", language_target=target).value == ""
        assert normalize_text({"code": "X"}, "object", language_target=target).value == {"code": "X"}


def test_unsafe_pt_text_has_targeted_diagnostic() -> None:
    result = normalize_text("Quantum entanglement semantics remain unresolved.", "unsafe", language_target="pt")
    assert result.status == "non_compliant"
    assert result.diagnostics
    assert result.diagnostics[0].target == "pt"
    assert "target=pt" in result.diagnostics[0].message


def test_protected_fixture_values_remain_byte_for_byte_identical_for_both_targets() -> None:
    for pattern in PATTERNS:
        for target in ("en", "pt"):
            normalized, _ = normalize_architectural_pattern(pattern, "pattern", language_target=target)
            assert normalized["reference_artifact"] == pattern["reference_artifact"]
            assert normalized["adr_reference"] == pattern["adr_reference"]

    protected = "See `FeatureHandler.Validate()` at C:\\src\\Feature.pas and https://example.test/api; ADR-005-caching-strategy.md; OWASP-A01; MyProperName."
    for target in ("en", "pt"):
        result = normalize_text(protected, "protected", language_target=target)
        assert "`FeatureHandler.Validate()`" in result.value
        assert "C:\\src\\Feature.pas" in result.value
        assert "https://example.test/api" in result.value
        assert "ADR-005-caching-strategy.md" in result.value
        assert "OWASP-A01" in result.value
        assert set(result.protected_values) >= {
            "C:\\src\\Feature.pas",
            "ADR-005-caching-strategy.md",
            "OWASP-A01",
        }
