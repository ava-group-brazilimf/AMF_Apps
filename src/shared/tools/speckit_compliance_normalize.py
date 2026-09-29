#!/usr/bin/env python3
"""Deterministic normalizer for the F3S compliance gate artifact.

Root cause this tool exists for
--------------------------------
`ava-speckit-compliance` (wave6) is an LLM agent. Its spec
(`speckit/agents/compliance-agent.md`) mandates writing
`outputs/tobe/speckit/compliance-status.json` with schema
`{verdict, constitution_items, findings[], ...}`. Measured in production
(`nopcommerce-04-cli-ava`, 2026-08-19): the agent instead wrote
`compliance-summary.json` with an unrelated ad-hoc schema
(`result`, `recommendation`, `blocking_issues`, `metrics.*`,
`constitution_compliance.*`) — the schema used by the unrelated F7 agent
`ava-deliverable-security-compliance`. The post-step validator correctly
flagged the missing declared output, and the deterministic exit gate
(`artifact_gate_speckit.py --gate exit`) correctly blocked F4 because
`compliance-status.json` never existed on disk.

Re-running the agent burns inference with no guarantee the deviation won't
repeat — instructions already told it the exact path and schema and it
deviated anyway. This tool closes the gap deterministically: it looks for
the canonical file first (no-op if valid), then for known deviant
filenames/schemas, and remaps them into the canonical contract.

Measured again (`nopcommerce-04`, 2026-08-21, 731k tokens of inference): the
agent produced *substantive and correct* analysis but wrote it to
`outputs/deliverables/speckit-compliance-{report.md,summary.json}` — a
directory this tool did not search. It exited 1, nothing was written, and
745k tokens of real work sat on disk unusable. Two consequences, both fixed
here:

* The search now covers `outputs/deliverables/` and the rest of the project's
  `outputs/` tree, not just `outputs/tobe/speckit/`.
* **The artifacts are ALWAYS written.** Exiting without producing the file
  left the reader with nothing to read and the phase with nothing to show.
  When no agent output is recoverable anywhere, this tool synthesizes both
  artifacts from the deterministic evidence already on disk
  (`checks-report.json`, `compile-warnings.json`, `repair-issues.json`,
  `traceability.json`) and stamps `verdict: BLOCKED` with explicit
  provenance. Fail-safe, never fail-silent: the file says plainly that the
  agent did not deliver and what is missing.

This tool NEVER invents findings content. Every finding it emits is either
copied from the agent's own output or derived from a deterministic report
file, and each one carries the source it came from.

Usage:
    python src/shared/tools/speckit_compliance_normalize.py --project PROJECT
    python src/shared/tools/speckit_compliance_normalize.py --project PROJECT --json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]

# Força UTF-8 no Windows - mesma guarda de src/shared/checks/cli.py.
# Sem ela qualquer mensagem acentuada estoura UnicodeEncodeError no console
# cp1252 e a tool morre por um detalhe de terminal, não por um defeito real.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


CANONICAL_NAME = "compliance-status.json"
CANONICAL_REPORT = "compliance-report.md"
REQUIRED_KEYS = ("verdict", "constitution_items", "findings")
ALLOWED_VERDICTS = ("APPROVED", "APPROVED_WITH_FINDINGS", "BLOCKED")

# result/recommendation/compliance_gate (deviant schemas) -> canonical verdict.
# Ordem importa: o primeiro token contido na string vence, então os mais
# específicos vêm antes (CONDITIONAL_PROCEED antes de PROCEED).
_VERDICT_MAP = (
    ("NON_COMPLIANT", "BLOCKED"),
    ("BLOCKED", "BLOCKED"),
    ("REJECTED", "BLOCKED"),
    ("FAIL", "BLOCKED"),
    ("COMPLIANT_WITH_WARNINGS", "APPROVED_WITH_FINDINGS"),
    ("APPROVED_WITH_FINDINGS", "APPROVED_WITH_FINDINGS"),
    ("CONDITIONAL_PROCEED", "APPROVED_WITH_FINDINGS"),
    ("PROCEED_WITH_CONDITIONS", "APPROVED_WITH_FINDINGS"),
    ("CONDITIONAL", "APPROVED_WITH_FINDINGS"),
    ("APPROVED_FOR_F4", "APPROVED_WITH_FINDINGS"),
    ("WARNING", "APPROVED_WITH_FINDINGS"),
    ("COMPLIANT", "APPROVED"),
    ("APPROVED", "APPROVED"),
    ("PASS", "APPROVED"),
)

# Nomes que o agente já foi observado escrevendo em vez do canônico, na ordem
# de preferência. Testados primeiro em outputs/tobe/speckit/, depois nos
# demais diretórios de saída do projeto.
_KNOWN_DEVIANT_NAMES = (
    "compliance-summary.json",
    "speckit-compliance-status.json",
    "speckit-compliance-summary.json",
    "compliance-result.json",
    "compliance_status.json",
)

# `ava-deliverable-security-compliance` (F7) grava security-compliance-*.json
# no MESMO diretório de deliverables. Confundir os dois trocaria o veredito da
# F3S pelo de outra fase — daí a exclusão explícita, e não um glob otimista.
_FOREIGN_PREFIXES = ("security-compliance",)

# Diretórios varridos, na ordem. O primeiro artefato reconhecível vence.
_SEARCH_SUBDIRS = (
    Path("outputs") / "tobe" / "speckit",
    Path("outputs") / "deliverables",
    Path("outputs") / "tobe",
    Path("outputs"),
)


def _project_dir(project: str, repo_root: Path) -> Path:
    return repo_root / "projects" / project


def _speckit_dir(project: str, repo_root: Path) -> Path:
    return _project_dir(project, repo_root) / "outputs" / "tobe" / "speckit"


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def _is_valid_canonical(data: dict[str, Any] | None) -> bool:
    if data is None:
        return False
    if not all(key in data for key in REQUIRED_KEYS):
        return False
    if data.get("verdict") not in ALLOWED_VERDICTS:
        return False
    return isinstance(data.get("findings"), list)


def _is_foreign(path: Path) -> bool:
    return any(path.name.startswith(prefix) for prefix in _FOREIGN_PREFIXES)


def _find_deviant_source(project_dir: Path, speckit_dir: Path) -> Path | None:
    """Localiza o JSON de conformidade escrito pelo agente, onde quer que esteja.

    Antes só `speckit_dir` era varrido; o agente escreveu em
    `outputs/deliverables/` e a tool declarou "nada encontrado" com o artefato
    a dois diretórios de distância.
    """
    for subdir in _SEARCH_SUBDIRS:
        base = project_dir / subdir
        if not base.is_dir():
            continue
        for name in _KNOWN_DEVIANT_NAMES:
            candidate = base / name
            if candidate.is_file() and candidate.name != CANONICAL_NAME:
                return candidate
        others = sorted(
            p for p in base.glob("*compliance*.json")
            if p.name != CANONICAL_NAME and not _is_foreign(p)
        )
        if others:
            return others[0]
    return None


def _find_report_source(project_dir: Path, speckit_dir: Path,
                        json_source: Path | None) -> Path | None:
    """Localiza o relatório humano correspondente.

    O canônico só vence se for substantivo E não for mais antigo que o do
    agente: num re-run, o relatório da execução anterior fica no caminho
    canônico e mascararia o novo, deixando o operador lendo a análise errada
    sem nenhum sinal disso.
    """
    canonical = speckit_dir / CANONICAL_REPORT
    externo: Path | None = None

    if json_source is not None:
        sibling = json_source.with_name(
            json_source.name.replace("summary", "report").replace("status", "report")
        ).with_suffix(".md")
        if sibling.is_file():
            externo = sibling
    if externo is None:
        for subdir in _SEARCH_SUBDIRS:
            base = project_dir / subdir
            if not base.is_dir():
                continue
            found = sorted(p for p in base.glob("*compliance*report*.md")
                           if not _is_foreign(p) and p != canonical)
            if found:
                externo = found[0]
                break

    canonico_util = canonical.is_file() and canonical.stat().st_size > 200
    if canonico_util and externo is not None:
        return externo if externo.stat().st_mtime > canonical.stat().st_mtime else canonical
    if canonico_util:
        return canonical
    return externo


def _map_verdict(source: dict[str, Any]) -> str:
    if source.get("verdict") in ALLOWED_VERDICTS:
        return str(source["verdict"])
    for field in ("result", "recommendation", "compliance_gate", "status"):
        raw = str(source.get(field) or "").upper()
        if not raw:
            continue
        for token, verdict in _VERDICT_MAP:
            if token in raw:
                return verdict
    # Forma não reconhecida: fail-safe, não aprova em silêncio.
    return "BLOCKED"


_COUNT_PAIRS = (
    ("principles_covered", "principles_total"),
    ("mandatory_decisions_traced", "mandatory_decisions_total"),
    ("constraints_enforced", "constraints_total"),
    ("architectural_principles_compliant", "architectural_principles_total"),
    ("binding_decisions_compliant", "binding_decisions_total"),
    ("constraints_compliant", "constraints_total"),
)


def _constitution_counts(source: dict[str, Any]) -> tuple[int, int]:
    """(total, honrados) a partir de qualquer uma das formas já observadas."""
    for container in (source.get("metrics"), source.get("constitution_compliance")):
        if not isinstance(container, dict):
            continue
        total = honored = 0
        # `constraints_total` aparece em dois pares (`_enforced` e
        # `_compliant`, nomes usados por schemas diferentes). Contá-lo uma vez
        # por par inflava o denominador — 50/70 onde o certo era 50/50.
        consumidos: set[str] = set()
        for honored_key, total_key in _COUNT_PAIRS:
            if total_key not in container or total_key in consumidos:
                continue
            if honored_key not in container:
                continue
            consumidos.add(total_key)
            total += int(container.get(total_key) or 0)
            honored += int(container.get(honored_key) or 0)
        if total:
            return total, honored
    # Forma tabular: {item: "PASS"|"FAIL"}. Só chaves cujo valor é veredito.
    table = source.get("constitution_compliance")
    if isinstance(table, dict) and table:
        vereditos = {k: v for k, v in table.items()
                     if isinstance(v, str) and v.upper() in ("PASS", "FAIL")
                     and k != "status"}
        if vereditos:
            honored = sum(1 for v in vereditos.values() if v.upper() == "PASS")
            return len(vereditos), honored
    return 0, 0


def _verdict_rule_check(verdict: str, findings: list[dict[str, Any]]) -> dict[str, Any]:
    """Confere o veredito contra a regra documentada em compliance-agent.md.

    "Ao menos um achado alto → BLOCKED". O veredito do agente é preservado —
    é o julgamento que este artefato existe para carregar, e não é meu para
    sobrescrever. Mas quando ele contradiz a própria regra da spec, isso vira
    um campo explícito em vez de uma inconsistência silenciosa no JSON.
    """
    graves = [item["id"] for item in findings
              if str(item.get("severity") or "").lower() in ("critical", "high")]
    coerente = not graves or verdict == "BLOCKED"
    return {
        "rule": "compliance-agent.md — ao menos um achado alto ⇒ BLOCKED",
        "high_or_critical_findings": graves,
        "agent_verdict": verdict,
        "consistent": coerente,
        "note": "" if coerente else (
            f"o agente reportou {verdict} carregando {len(graves)} achado(s) "
            f"de severidade alta/crítica ({', '.join(graves)}). O veredito do "
            f"agente foi preservado; revise antes de liberar a F4."
        ),
    }


def _finding(idx: int, severity: str, summary: str, evidence: str,
             artifact: str, remediation: str, ref: str = "N/A") -> dict[str, Any]:
    return {
        "id": f"NORM-{idx:03d}",
        "severity": severity,
        "constitution_ref": ref,
        "summary": summary,
        "evidence": evidence,
        "artifact": artifact,
        "remediation": remediation,
    }


def _build_findings(source: dict[str, Any], report_rel: str) -> list[dict[str, Any]]:
    """Findings a partir do conteúdo REAL do agente — nada é inventado."""
    existing = source.get("findings")
    if isinstance(existing, list) and existing:
        return existing

    findings: list[dict[str, Any]] = []

    # Blockers nomeados. `edge_cases.critical_blocker_details` e `blocked_by`
    # descrevem o MESMO conjunto com campos diferentes (e nem sempre ambos
    # existem), então os dois são lidos e deduplicados pelo id — sem isso o
    # mesmo blocker aparecia duas vezes, uma delas com o dict cru impresso
    # como se fosse texto.
    por_id: dict[str, dict[str, Any]] = {}
    ordem: list[str] = []

    def _absorve(item: Any, origem: str) -> None:
        if isinstance(item, str):
            chave, dados = item, {"finding": item}
        elif isinstance(item, dict):
            chave = str(item.get("id") or item.get("description")
                        or item.get("finding") or f"{origem}:{len(ordem)}")
            dados = item
        else:
            return
        if chave not in por_id:
            ordem.append(chave)
            por_id[chave] = {"origem": origem, **dados}
        else:
            # Segunda fonte para o mesmo blocker: completa campos vazios.
            for key, value in dados.items():
                por_id[chave].setdefault(key, value)

    edge = source.get("edge_cases")
    if isinstance(edge, dict):
        for item in edge.get("critical_blocker_details") or []:
            _absorve(item, "edge_cases")
    for item in source.get("blocked_by") or []:
        _absorve(item, "blocked_by")

    for chave in ordem:
        dados = por_id[chave]
        texto = str(dados.get("finding") or dados.get("description") or chave)
        evidencia = [f"id={dados['id']}"] if dados.get("id") else []
        for rotulo, campo in (("wave", "wave_blocked"), ("categoria", "category"),
                              ("impacto", "impact"), ("fonte", "evidence")):
            if dados.get(campo):
                evidencia.append(f"{rotulo}={dados[campo]}")
        remediacao = (f"responsável: {dados['owner']}" if dados.get("owner")
                      else "resolver antes de liberar a F4")
        if dados.get("justification"):
            remediacao += f" · justificativa registrada: {dados['justification']}"
        findings.append(_finding(
            len(findings) + 1,
            str(dados.get("severity") or "critical").lower(),
            texto, " · ".join(evidencia) or f"listado em {dados['origem']}",
            report_rel, remediacao,
        ))

    # Condições de aprovação: acionáveis, com texto próprio, mas NÃO são
    # achados de severidade alta — são o que falta para o veredito subir de
    # condicional para aprovado. Classificá-las como alta faria toda aprovação
    # condicional parecer reprovação.
    for item in source.get("conditions_for_approved") or []:
        findings.append(_finding(
            len(findings) + 1, "medium", str(item),
            "listado em conditions_for_approved pelo agente de conformidade",
            report_rel, str(item),
        ))

    if findings:
        return findings

    # Só contagens, sem texto: aponta para o relatório em vez de adivinhar.
    warnings = int(source.get("warnings") or 0)
    blocking = int(source.get("blocking_issues") or 0)
    if warnings + blocking == 0:
        return []
    return [_finding(
        1, "high" if blocking else "low",
        "Achados reportados pelo agente em schema não-canônico, sem texto estruturado.",
        f"Contagem original: warnings={warnings}, blocking_issues={blocking}",
        report_rel,
        "Revisar a seção de Avisos/Achados de compliance-report.md.",
    )]


# ── Fallback determinístico ──────────────────────────────────────────────────
# Usado quando NADA do agente é recuperável. Não fabrica um veredito favorável:
# monta o quadro a partir dos relatórios que já existem em disco e reprova.

def _evidence_from_disk(speckit_dir: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    checks = _read_json(speckit_dir / "checks-report.json")
    for result in (checks or {}).get("results", []) or []:
        if isinstance(result, dict) and result.get("passed") is False:
            findings.append(_finding(
                len(findings) + 1, "high",
                str(result.get("name") or "check reprovado"),
                str(result.get("detail") or ""),
                "outputs/tobe/speckit/checks-report.json",
                "corrigir a lacuna apontada pelo check e re-executar a suíte",
            ))

    compile_warnings = _read_json(speckit_dir / "compile-warnings.json")
    for warning in (compile_warnings or {}).get("warnings", []) or []:
        if not isinstance(warning, dict):
            continue
        findings.append(_finding(
            len(findings) + 1, "medium",
            f"[{warning.get('code', '?')}] {warning.get('message', '')}",
            f"origem: {warning.get('owner', '?')}",
            "outputs/tobe/speckit/compile-warnings.json",
            str(warning.get("fix") or "ver compile-warnings.json"),
        ))

    repair = _read_json(speckit_dir / "repair-issues.json")
    for issue in (repair or {}).get("warnings", []) or []:
        findings.append(_finding(
            len(findings) + 1, "low", str(issue),
            "reparo determinístico de fragments",
            "outputs/tobe/speckit/repair-issues.json",
            "corrigir a spec/plano de origem e regerar a feature",
        ))
    return findings


def _fallback_status(project: str, speckit_dir: Path,
                     reason: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    findings = _evidence_from_disk(speckit_dir)
    trace = _read_json(speckit_dir / "traceability.json") or {}
    findings.insert(0, _finding(
        0, "critical",
        "ava-speckit-compliance não entregou um artefato de conformidade utilizável.",
        reason,
        "outputs/pipeline_runner/",
        "re-executar a fase F3S:compliance; os achados abaixo vêm dos relatórios "
        "determinísticos e NÃO substituem a análise de conformidade do agente.",
    ))
    for index, item in enumerate(findings):
        item["id"] = f"NORM-{index:03d}"
    status = {
        "schema_version": "1.0.0",
        "project": project,
        "trace_id": str(trace.get("trace_id") or "unknown"),
        "verdict": "BLOCKED",
        "constitution_items": 0,
        "items_honored": 0,
        "findings": findings,
        "contradictions": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "_normalized_by": "speckit_compliance_normalize.py",
        "_normalized_from": "fallback (evidência determinística em disco)",
        "_normalized_at": datetime.now(timezone.utc).isoformat(),
        "_normalization_reason": reason,
        "_agent_output_recovered": False,
    }
    return status, findings


def _render_report(project: str, status: dict[str, Any], source_note: str) -> str:
    """Relatório humano mínimo — usado quando o agente não deixou um .md."""
    # `.get` em tudo: este renderizador também recebe um canônico escrito por
    # outra mão, que satisfaz REQUIRED_KEYS sem trazer os campos opcionais.
    # Um KeyError aqui derrubaria a única coisa que a tool promete — gravar.
    verdict = str(status.get("verdict") or "BLOCKED")
    findings = status.get("findings") or []
    lines = [
        f"# Relatório de Conformidade — {project}",
        "",
        f"> **Gerado por** `speckit_compliance_normalize.py` (determinístico).",
        f"> {source_note}",
        "",
        f"- **Veredito:** `{verdict}`",
        f"- **Itens da constituição:** {status.get('items_honored', 0)}"
        f"/{status.get('constitution_items', 0)}",
        f"- **Achados:** {len(findings)}",
        f"- **Gerado em:** {status.get('generated_at', '—')}",
        "",
    ]
    if verdict == "BLOCKED":
        lines += [
            "## ⛔ Este relatório NÃO substitui a análise do agente",
            "",
            "O conteúdo abaixo é derivado dos relatórios determinísticos já em",
            "disco. Ele descreve o que se sabe por verificação de código, não a",
            "análise de julgamento que `ava-speckit-compliance` deveria produzir.",
            "Re-execute a fase `F3S:compliance` antes de tratar a conformidade",
            "como avaliada.",
            "",
        ]
    if not findings:
        lines += ["## Achados", "", "Nenhum achado registrado.", ""]
        return "\n".join(lines)

    lines += ["## Achados", ""]
    por_severidade: dict[str, list[dict[str, Any]]] = {}
    for item in findings:
        por_severidade.setdefault(str(item.get("severity") or "info"), []).append(item)
    for severity in ("critical", "high", "medium", "low", "info"):
        grupo = por_severidade.get(severity)
        if not grupo:
            continue
        lines += [f"### {severity.upper()} ({len(grupo)})", ""]
        for item in grupo:
            lines.append(f"- **{item.get('id', '—')}** — {item.get('summary', '')}")
            if item.get("evidence"):
                lines.append(f"  - evidência: {item['evidence']}")
            if item.get("artifact"):
                lines.append(f"  - fonte: `{item['artifact']}`")
            if item.get("remediation"):
                lines.append(f"  - correção: {item['remediation']}")
        lines.append("")
    return "\n".join(lines)


def _carry_approval(previous: dict[str, Any] | None,
                    new_status: dict[str, Any],
                    speckit_dir: Path) -> None:
    """Transporta a assinatura humana para o artefato reescrito, in-place.

    `normalize()` reescreve `compliance-status.json` INTEIRO. Sem isto, rodar a
    wave6b de novo apagaria a decisão registrada na wave6c — o gate viraria
    teatro: assina, e o passo seguinte limpa.

    A assinatura só continua valendo se o fingerprint dos achados não mudou.
    Quando muda, ela é rebaixada para `expired` em vez de descartada: quem
    auditar precisa ver que houve uma decisão e por que ela deixou de cobrir o
    conteúdo atual.
    """
    aprovacao = (previous or {}).get("approval")
    if not isinstance(aprovacao, dict) or not aprovacao:
        return
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        import speckit_compliance_gate as gate  # noqa: PLC0415
        atual = gate.fingerprint(new_status, speckit_dir)
    except Exception:  # noqa: BLE001 — sem o gate disponível, preserva como veio
        new_status["approval"] = aprovacao
        return

    if str(aprovacao.get("approved_fingerprint") or "") == atual:
        new_status["approval"] = aprovacao
        return

    new_status["approval"] = {
        **aprovacao,
        "status": "expired",
        "expired_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "expired_reason": (
            "os achados mudaram desde esta decisão — a assinatura não cobre o "
            "conteúdo atual do compliance-status.json"
        ),
        "previous_status": aprovacao.get("status"),
        "current_fingerprint": atual,
    }


def normalize(project: str, repo_root: Path | None = None) -> dict[str, Any]:
    """Garante `compliance-status.json` e `compliance-report.md` em disco.

    Retorna sempre com os dois arquivos gravados. `status` distingue o caminho
    percorrido; `verdict` diz o que o conteúdo afirma.
    """
    repo = repo_root or REPO_ROOT
    project_dir = _project_dir(project, repo)
    speckit_dir = _speckit_dir(project, repo)
    canonical_path = speckit_dir / CANONICAL_NAME
    report_path = speckit_dir / CANONICAL_REPORT
    report_rel = f"outputs/tobe/speckit/{CANONICAL_REPORT}"
    speckit_dir.mkdir(parents=True, exist_ok=True)

    source_path = _find_deviant_source(project_dir, speckit_dir)
    report_source = _find_report_source(project_dir, speckit_dir, source_path)

    # O relatório humano é materializado no caminho canônico sempre que houver
    # um de origem — inclusive quando o JSON já é válido, porque o agente
    # frequentemente acerta um e erra o outro.
    report_copied_from = None
    if report_source is not None and report_source != report_path:
        _write_atomic(report_path, _read_text(report_source))
        report_copied_from = str(report_source.relative_to(project_dir))

    canonical_data = _read_json(canonical_path) if canonical_path.is_file() else None
    if _is_valid_canonical(canonical_data):
        if not report_path.is_file():
            _write_atomic(report_path, _render_report(
                project, canonical_data,
                "compliance-status.json já era válido; o agente não deixou relatório."))
        # Mesmo sem nada a normalizar, a assinatura pode ter deixado de cobrir o
        # conteúdo — basta o traceability.json ter mudado. Sem esta passagem, os
        # dois caminhos desta função discordariam sobre o mesmo fato: um
        # rebaixaria para `expired`, o outro deixaria `approved` no arquivo.
        # (O gate de saída recomputa e reprova de qualquer forma; o que está em
        # jogo aqui é o arquivo não mentir para quem o lê.)
        antes = json.dumps(canonical_data.get("approval") or {}, sort_keys=True)
        _carry_approval(canonical_data, canonical_data, speckit_dir)
        expirou = json.dumps(canonical_data.get("approval") or {}, sort_keys=True) != antes
        if expirou:
            _write_atomic(canonical_path,
                          json.dumps(canonical_data, ensure_ascii=False, indent=2) + "\n")
        return {
            "status": "OK",
            "action": "approval_expired" if expirou else "none",
            "verdict": canonical_data.get("verdict"),
            "detail": (f"{CANONICAL_NAME} já é válido, mas a aprovação registrada "
                       f"não cobre mais o conteúdo atual — marcada como expirada."
                       if expirou else
                       f"{CANONICAL_NAME} já é válido — nenhuma ação necessária."),
            "path": str(canonical_path),
            "report": str(report_path),
            "report_copied_from": report_copied_from,
        }

    source = _read_json(source_path) if source_path is not None else None

    if source is None:
        motivo = (
            f"{CANONICAL_NAME} ausente/inválido e nenhum JSON de conformidade "
            f"reconhecível foi encontrado em {project_dir / 'outputs'}."
            if source_path is None else
            f"{source_path.name} encontrado mas não é JSON válido."
        )
        status, _ = _fallback_status(project, speckit_dir, motivo)
        _carry_approval(canonical_data, status, speckit_dir)
        _write_atomic(canonical_path,
                      json.dumps(status, ensure_ascii=False, indent=2) + "\n")
        if report_source is None:
            _write_atomic(report_path, _render_report(
                project, status,
                "Nenhum relatório do agente foi encontrado; conteúdo derivado "
                "dos relatórios determinísticos."))
        return {
            "status": "FALLBACK",
            "action": "synthesized",
            "verdict": status["verdict"],
            "detail": (f"{motivo} Artefatos gravados a partir da evidência "
                       f"determinística, com verdict=BLOCKED."),
            "path": str(canonical_path),
            "report": str(report_path),
            "findings": len(status["findings"]),
        }

    total, honored = _constitution_counts(source)
    normalized = {
        "schema_version": "1.0.0",
        "project": source.get("project") or source.get("project_name") or project,
        "trace_id": source.get("trace_id") or "unknown",
        "verdict": _map_verdict(source),
        "constitution_items": total,
        "items_honored": honored,
        "findings": _build_findings(source, report_rel),
        "contradictions": source.get("contradictions") or [],
        "generated_at": source.get("generated_at") or datetime.now(timezone.utc).isoformat(),
        "_normalized_by": "speckit_compliance_normalize.py",
        "_normalized_from": str(source_path.relative_to(project_dir)),
        "_normalized_at": datetime.now(timezone.utc).isoformat(),
        "_normalization_reason": (
            "ava-speckit-compliance escreveu um arquivo/schema não-canônico; "
            "ver src/modules/ava-fabric-agents/speckit/agents/compliance-agent.md"
        ),
        "_agent_output_recovered": True,
    }
    normalized["_verdict_rule_check"] = _verdict_rule_check(
        normalized["verdict"], normalized["findings"])
    _carry_approval(canonical_data, normalized, speckit_dir)
    _write_atomic(canonical_path,
                  json.dumps(normalized, ensure_ascii=False, indent=2) + "\n")
    if not report_path.is_file():
        _write_atomic(report_path, _render_report(
            project, normalized,
            f"Derivado de `{normalized['_normalized_from']}`; o agente não "
            f"deixou um relatório em markdown."))

    return {
        "status": "OK",
        "action": "normalized",
        "verdict": normalized["verdict"],
        "detail": (f"{CANONICAL_NAME} reconstruído a partir de "
                   f"{normalized['_normalized_from']} "
                   f"(verdict={normalized['verdict']}, "
                   f"findings={len(normalized['findings'])})."),
        "path": str(canonical_path),
        "report": str(report_path),
        "report_copied_from": report_copied_from,
        "source": str(source_path),
        "verdict_rule_consistent": normalized["_verdict_rule_check"]["consistent"],
        "verdict_rule_note": normalized["_verdict_rule_check"]["note"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-p", "--project", required=True)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    result = normalize(args.project)

    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        icon = {"OK": "✅", "FALLBACK": "⚠️"}.get(result["status"], "❌")
        print(f"\n  {icon} speckit-compliance-normalize — {result['status']}")
        print(f"    {result['detail']}")

    if result["status"] == "FALLBACK":
        # Banner no stderr: a esteira segue (exit 0, os artefatos existem), mas
        # o operador precisa saber que a conformidade NÃO foi avaliada.
        print("\n" + "─" * 72, file=sys.stderr)
        print("⚠️  COMPLIANCE NÃO AVALIADA PELO AGENTE", file=sys.stderr)
        print(f"   {result['detail']}", file=sys.stderr)
        print(f"   Artefatos gravados mesmo assim: {result['path']}", file=sys.stderr)
        print(f"                                   {result['report']}", file=sys.stderr)
        print("   CORREÇÃO: re-execute a fase F3S:compliance. O veredito atual é",
              file=sys.stderr)
        print("   BLOCKED por ausência de análise, não por reprovação.", file=sys.stderr)
        print("─" * 72, file=sys.stderr)

    # Exit 0 em FALLBACK também: os artefatos EXISTEM e o veredito registrado é
    # BLOCKED. Sair != 0 aqui devolveria o pipeline ao estado que esta tool
    # existe para eliminar — fase sem artefato nenhum para o operador ler.
    return 0 if result["status"] in ("OK", "FALLBACK") else 1


if __name__ == "__main__":
    sys.exit(main())
