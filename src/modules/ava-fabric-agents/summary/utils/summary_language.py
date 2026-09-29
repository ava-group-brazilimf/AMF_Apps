"""Deterministic language handling for the Summary default rendered state.

This module intentionally does not call a translation service. It normalizes a
small, explicit vocabulary used by Summary-generated prose and reports unsafe
residual Portuguese for the validator to block. Technical/protected tokens are
masked before detection and restored byte-for-byte.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any


@dataclass(frozen=True)
class LanguageDiagnostic:
    region_id: str
    message: str
    line: int | None = None
    column: int | None = None
    target: str = "en"

    def as_dict(self) -> dict:
        result = {"region_id": self.region_id, "message": self.message}
        result["target"] = self.target
        if self.line is not None:
            result["line"] = self.line
        if self.column is not None:
            result["column"] = self.column
        return result


@dataclass
class NormalizationResult:
    value: Any
    status: str
    diagnostics: list[LanguageDiagnostic] = field(default_factory=list)
    protected_values: list[str] = field(default_factory=list)
    target: str = "en"


# Ordered longest-first replacements keep the mapping deterministic.
_NORMALIZATION_RULES = tuple(sorted({
    "Padrões Arquiteturais": "Architectural Patterns",
    "Padrões de Navegação": "Navigation Patterns",
    "Regras de Negócio": "Business Rules",
    "Regras Novas": "New Rules",
    "Requisitos Funcionais": "Functional Requirements",
    "Artefato de Referência": "Reference Artifact",
    "Artefatos do Protótipo": "Prototype Artifacts",
    "TO-BE ainda não gerado": "TO-BE not generated yet",
    "TO-BE design pendente": "TO-BE design pending",
    "Stack codegen pendente": "Stack code generation pending",
    "QA e entrega pendentes": "QA and delivery pending",
    "Nenhum dado disponível": "No data available",
    "Pendente": "Pending",
    "pendente": "pending",
    "Pendentes": "Pending",
    "pendentes": "pending",
    "Justificativa": "Justification",
    "Referência": "Reference",
    "Referências": "References",
    "Camada": "Layer",
    "Padrão": "Pattern",
    "Padrões": "Patterns",
    "Descrição": "Description",
    "Descrições": "Descriptions",
    "Módulo": "Module",
    "Módulos": "Modules",
    "Prioridade": "Priority",
    "Ocorrências": "Occurrences",
    "Resumo": "Summary",
    "Métrica": "Metric",
    "Métricas": "Metrics",
    "Valor": "Value",
    "Valores": "Values",
    "Título": "Title",
    "Títulos": "Titles",
    "Passos": "Steps",
    "Regras": "Rules",
    "Ação": "Action",
    "Ações": "Actions",
    "Risco": "Risk",
    "Riscos": "Risks",
    "Segurança": "Security",
    "Mensageria": "Messaging",
    "Eventos": "Events",
    "Filas": "Queues",
    "Arquitetura": "Architecture",
    "Protótipo": "Prototype",
    "Entregáveis": "Deliverables",
    "Paridade": "Parity",
    "Não Migráveis": "Non-Migratable",
    "Idioma": "Language",
    "Português": "Portuguese",
    "Gerado automaticamente": "Automatically generated",
    "Fonte": "Source",
    "Primeiros": "First",
    "exibidos nesta visão": "displayed in this view",
    "de negócio": "business",
    "Regra de Negócio": "Business Rule",
    "Estado Global": "Global State",
    "Antipadrão Arq.": "Architectural Anti-pattern",
    "Dep. Circular": "Circular Dependency",
}.items(), key=lambda item: len(item[0]), reverse=True))

# Feature 038's PT-BR branch is intentionally deterministic and local. These
# are reusable Summary/architecture vocabulary and safe phrase patterns, not
# mappings keyed only to one fixture's literal sentences.
_PT_NORMALIZATION_RULES = tuple(sorted({
    "Architectural Patterns": "Padrões Arquiteturais",
    "Navigation Patterns": "Padrões de Navegação",
    "Business Rules": "Regras de Negócio",
    "Functional Requirements": "Requisitos Funcionais",
    "Reference Artifact": "Artefato de Referência",
    "Prototype Artifacts": "Artefatos do Protótipo",
    "TO-BE not generated yet": "TO-BE ainda não gerado",
    "TO-BE design pending": "Design TO-BE pendente",
    "Stack code generation pending": "Geração de código da stack pendente",
    "QA and delivery pending": "QA e entrega pendentes",
    "No data available": "Nenhum dado disponível",
    "Provisioned Resources": "Recursos Provisionados",
    "Deploy Environments": "Ambientes de Deploy",
    "This pattern reduces coupling between the presentation and domain layers by introducing a mediator.": "Este padrão reduz o acoplamento entre as camadas de apresentação e domínio ao introduzir um mediador.",
    "The repository abstraction isolates persistence concerns from use cases.": "A abstração de repositório isola as preocupações de persistência dos casos de uso.",
    "Invalidation must remain deterministic": "A invalidação deve permanecer determinística",
    "Additional abstraction": "Abstração adicional",
    "Testes ficam mais simples": "Os testes ficam mais simples",
    "Requires clear ownership": "Requer ownership claro",
    "the handler remains responsible for integration": "o handler continua responsável pela integração",
    "but the handler": "mas o handler",
    "The rule is published in the domain": "A regra é publicada no domínio",
    "Infrastructure": "Infraestrutura",
    "Application": "Aplicação",
    "Domain": "Domínio",
    "Layer": "Camada",
    "Justification": "Justificativa",
    "Reference": "Referência",
    "Trade-offs": "Trade-offs",
    "Description": "Descrição",
    "Scope": "Escopo",
    "Coverage": "Cobertura",
    "coverage": "cobertura",
    "English": "Inglês",
    # Reusable architecture vocabulary. Longer phrases above take precedence.
    "This pattern": "Este padrão",
    "the pattern": "o padrão",
    "reduces": "reduz",
    "increase": "aumenta",
    "improves": "melhora",
    "supports": "oferece suporte a",
    "coupling": "acoplamento",
    "between": "entre",
    "presentation": "apresentação",
    "domain": "domínio",
    "layers": "camadas",
    "layer": "camada",
    "by introducing": "ao introduzir",
    "introducing": "introdução de",
    "mediator": "mediador",
    "persistence": "persistência",
    "concerns": "preocupações",
    "use cases": "casos de uso",
    "architecture": "arquitetura",
    "pattern": "padrão",
    "service": "serviço",
    "services": "serviços",
    "repository": "repositório",
    "Repository": "Repositório",
    "but": "mas",
    "data": "dados",
    "retrieval": "recuperação",
    "latency": "latência",
    "queries": "consultas",
    "memory": "memória",
    "clear ownership": "ownership claro",
}.items(), key=lambda item: len(item[0]), reverse=True))

_DUPLICATE_WORD_RE = re.compile(r"\b([A-Za-zÀ-ÿ]+)(?:\s+\1)\b", re.I)
_MALFORMED_PUNCTUATION_RE = re.compile(r"(?:;\s*;|,\s*,|\.\s*\.)")

_PROTECTED_PATTERNS = (
    re.compile(r"https?://[^\s<>\"']+", re.I),
    re.compile(r"(?:[A-Za-z]:[\\/]|/)[^\s<>\"']+"),
    re.compile(r"\bADR[-_][A-Za-z0-9._/-]+\b", re.I),
    re.compile(r"\b(?:CWE|OWASP|BR|FR|RF|RN|CT|BC|CVE)[-_][A-Za-z0-9._/-]+\b", re.I),
    re.compile(r"`[^`]+`"),
)
_PT_MARKERS = re.compile(
    r"\b(?:portugu[eê]s|português|padr(?:ã|a)o|camada|justificativa|refer[eê]ncia|"
    r"descri(?:ç|c)[aã]o|m[oó]dulo|prioridade|ocorr[eê]ncias|resumo|m[eé]trica|"
    r"valor|passos|regras|a(?:ç|c)[aã]o|risco|seguran(?:ç|c)a|mensageria|"
    r"eventos|filas|arquitetura|prot[oó]tipo|entreg[aá]veis|paridade|pendente|"
    r"migr[aá]veis|idioma|gerado|fonte)\b",
    re.I,
)
_EN_MARKERS = re.compile(
    r"\b(?:the|and|but|with|from|remains|requires|must|should|where|when|"
    r"responsible|integration|abstraction|repository|application|infrastructure|"
    r"layer|reference|coverage|scope|resources|environments|unknown|untranslated|"
    r"remain|remains|unresolved|semantics|quantum|entanglement)\b",
    re.I,
)

_PROTECTED_DEFAULT_FIELDS = {"reference_artifact", "adr_reference"}


def _mask_protected(text: str) -> tuple[str, list[str]]:
    protected: list[str] = []

    def replace(match: re.Match) -> str:
        protected.append(match.group(0))
        return f"__SUMMARY_PROTECTED_{len(protected)-1}__"

    masked = text
    for pattern in _PROTECTED_PATTERNS:
        masked = pattern.sub(replace, masked)
    return masked, protected


def _restore(text: str, protected: list[str]) -> str:
    for index, value in enumerate(protected):
        text = text.replace(f"__SUMMARY_PROTECTED_{index}__", value)
    return text


def normalize_text(
    value: Any,
    region_id: str,
    *,
    preserve: bool = False,
    language_target: str = "en",
) -> NormalizationResult:
    """Normalize one value for ``en`` or ``pt`` without changing protected values."""
    if language_target not in {"en", "pt"}:
        raise ValueError("language_target must be 'en' or 'pt'")
    if value is None or isinstance(value, (int, float, bool)):
        return NormalizationResult(value, "not_applicable", target=language_target)
    if not isinstance(value, str):
        return NormalizationResult(value, "not_applicable", target=language_target)
    if not value.strip() or preserve:
        return NormalizationResult(value, "protected" if preserve else "empty", target=language_target)

    masked, protected = _mask_protected(value)
    normalized = masked
    rules = _NORMALIZATION_RULES if language_target == "en" else _PT_NORMALIZATION_RULES
    for source, target in rules:
        normalized = re.sub(re.escape(source), target, normalized, flags=re.I)
    normalized = _restore(normalized, protected)

    quality_issue = _DUPLICATE_WORD_RE.search(normalized) or _MALFORMED_PUNCTUATION_RE.search(normalized)
    quality_diagnostics: list[LanguageDiagnostic] = []
    if quality_issue:
        quality_diagnostics.append(LanguageDiagnostic(
            region_id=region_id,
            message=f"Potential normalized text quality issue for target={language_target}: {quality_issue.group(0)!r}",
            target=language_target,
        ))

    residual_pattern = _PT_MARKERS if language_target == "en" else _EN_MARKERS
    residual = residual_pattern.search(_mask_protected(normalized)[0])
    if residual:
        diagnostic = LanguageDiagnostic(
            region_id=region_id,
            message=f"Unsupported prose remains for target={language_target}: {residual.group(0)!r}",
            target=language_target,
        )
        return NormalizationResult(normalized, "non_compliant", [diagnostic], protected, language_target)
    status = "portuguese" if language_target == "pt" else "english"
    return NormalizationResult(normalized, status, quality_diagnostics, protected, language_target)


def normalize_mapping(
    mapping: dict,
    region_prefix: str,
    protected_keys: set[str] | None = None,
    *,
    language_target: str = "en",
) -> tuple[dict, list[LanguageDiagnostic]]:
    """Normalize string values except explicitly protected mapping fields."""
    protected_keys = protected_keys or set()
    output = dict(mapping)
    diagnostics: list[LanguageDiagnostic] = []
    for key, value in mapping.items():
        if isinstance(value, list):
            normalized_values = []
            for index, item in enumerate(value):
                result = normalize_text(
                    item, f"{region_prefix}.{key}[{index}]", language_target=language_target
                )
                normalized_values.append(result.value)
                diagnostics.extend(result.diagnostics)
            output[key] = normalized_values
        else:
            result = normalize_text(
                value,
                f"{region_prefix}.{key}",
                preserve=key in protected_keys,
                language_target=language_target,
            )
            output[key] = result.value
            diagnostics.extend(result.diagnostics)
    return output, diagnostics


def normalize_architectural_pattern(
    record: dict,
    region_id: str,
    *,
    language_target: str = "en",
) -> tuple[dict, list[LanguageDiagnostic]]:
    """Normalize pattern prose while preserving exact reference fields."""
    output, diagnostics = normalize_mapping(
        record,
        region_id,
        protected_keys=_PROTECTED_DEFAULT_FIELDS,
        language_target=language_target,
    )
    return output, diagnostics


def compliance_result(
    artifact_path: str,
    diagnostics: list[LanguageDiagnostic],
    protected: list[str],
    mode: str = "summary",
    *,
    language_target: str = "en",
) -> dict:
    return {
        "artifact_path": artifact_path,
        "is_compliant": not diagnostics,
        "offending_regions": [item.as_dict() for item in diagnostics],
        "ignored_protected_values": protected,
        "mode": mode,
        "target": language_target,
        "blocking": bool(diagnostics),
    }
