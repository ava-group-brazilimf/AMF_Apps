#!/usr/bin/env python3
"""Gate de aprovação humana da F3S — avalia achados e registra a assinatura.

Por que este gate existe
------------------------
O gate de saída da F3S (`artifact_gate_speckit.py --gate exit`) confere
PRESENÇA de arquivo, não conteúdo. Medido em `nopcommerce-04` (2026-08-21): a
F4 foi liberada com `verdict: APPROVED_WITH_FINDINGS` carregando dois blockers
CRITICAL — CMK do Always Encrypted não definido (EDGE-W0-002) e tecnologia de
feature flags não escolhida (EDGE-W0-005) — e com o `_verdict_rule_check`
acusando que o próprio veredito contradiz a regra da spec do agente
(`compliance-agent.md`: "ao menos um achado alto ⇒ BLOCKED"). O JSON registrou
tudo. Nada levou aquilo até uma pessoa.

Esta tool fecha a lacuna: classifica os achados, e quando há algo crítico ou
relevante o operador é avisado e decide. Ao seguir, ficam gravados no próprio
`compliance-status.json` QUEM aprovou, EM QUE PAPEL e QUANDO.

Divisão de responsabilidade
---------------------------
Esta tool **avalia e registra**; ela nunca pergunta nada. O prompt vive no
`pipeline_runner`, que é quem sabe se a execução é manual ou automática e já
tem a leitura de teclado (`safe_input`, via `msvcrt`). A comunicação entre os
dois é por arquivo — `compliance-gate.json` —, o mesmo padrão das demais tools
da F3S: nada depende de capturar stdout de subprocess, e o achado fica
auditável em disco.

Política de bloqueio
--------------------
`--evaluate` **sempre sai com 0**: avaliar não é reprovar. Quem bloqueia é o
gate de saída, ao ler o estado da aprovação. Isso preserva a política do
pipeline ("erro nunca trava fase") — a única coisa que trava a esteira é uma
recusa humana explícita em modo manual, e essa decisão é tomada pelo runner.

Expiração
---------
A assinatura é atrelada a um fingerprint dos achados + o `graph_checksum` do
`traceability.json`. Regerar specs/tasks muda o checksum, muda o fingerprint, e
a aprovação vira `expired`. Sem isso uma assinatura antiga cobriria conteúdo
que ninguém viu — que é justamente o que este gate existe para impedir.

Uso:
    python src/shared/tools/speckit_compliance_gate.py -p PROJ --evaluate --json
    python src/shared/tools/speckit_compliance_gate.py -p PROJ --approve \
        --name "Rafael Almeida" --role "Tech Lead"
    python src/shared/tools/speckit_compliance_gate.py -p PROJ --acknowledge --mode auto
    python src/shared/tools/speckit_compliance_gate.py -p PROJ --reject \
        --name "Rafael Almeida" --role "Tech Lead"
    python src/shared/tools/speckit_compliance_gate.py -p PROJ --status --json
"""
from __future__ import annotations

import argparse
import hashlib
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

STATUS_NAME = "compliance-status.json"
GATE_NAME = "compliance-gate.json"
LOG_NAME = "approval-log.jsonl"

#: Severidades que exigem ciência humana antes de liberar a F4.
BLOCKING_SEVERITIES = ("critical", "high")

#: Estados em que a F4 pode seguir. `auto_acknowledged` é estado PRÓPRIO, e não
#: `approved` com `reviewer: "AUTO"`, de propósito: quem ler o arquivo depois
#: precisa distinguir "uma pessoa revisou" de "passou batido em execução
#: automática" na primeira olhada, não na interpretação de um campo de nome.
PASSING_STATES = ("approved", "auto_acknowledged")
ALL_STATES = ("approved", "auto_acknowledged", "rejected", "pending", "expired",
              "not_required")


def _speckit_dir(project: str, repo_root: Path) -> Path:
    return repo_root / "projects" / project / "outputs" / "tobe" / "speckit"


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _write_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    tmp.replace(path)


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _trusted_timestamp() -> tuple[str, bool, str | None]:
    """``(timestamp, houve_fallback, servidor)`` — hora NTP quando disponível.

    Reusa `src/shared/utils/ntp_time.py`, que já existe justamente para tornar
    o fallback AUDÍVEL: um `datetime.now()` num registro de auditoria é
    indistinguível de um relógio desajustado ou adulterado. Gravar a fonte é o
    que separa uma data verificável de um carimbo.

    Só é chamado nos modos de GRAVAÇÃO. `--evaluate` roda em todo run do
    pipeline e não pode pagar até 24s de timeout de rede por isso.
    """
    try:
        sys.path.insert(0, str(REPO_ROOT / "src" / "shared" / "utils"))
        import ntp_time  # noqa: PLC0415
        return ntp_time.resolve()
    except Exception:  # noqa: BLE001 — rede indisponível não pode impedir o registro
        return datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z"), True, None


# ── Classificação ────────────────────────────────────────────────────────────

def blocking_findings(status: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in (status.get("findings") or [])
            if isinstance(item, dict)
            and str(item.get("severity") or "").lower() in BLOCKING_SEVERITIES]


def triggers(status: dict[str, Any]) -> list[dict[str, str]]:
    """Motivos pelos quais este projeto precisa de ciência humana.

    Os três gatilhos são independentes de propósito. Confiar só no veredito do
    agente foi exatamente o que deixou passar o run de 2026-08-21: ele reportou
    `APPROVED_WITH_FINDINGS` sobre dois blockers CRITICAL.
    """
    motivos: list[dict[str, str]] = []
    verdict = str(status.get("verdict") or "")
    if verdict == "BLOCKED":
        motivos.append({
            "code": "VERDICT_BLOCKED",
            "detail": "o agente de conformidade reprovou a camada de planejamento",
        })
    graves = blocking_findings(status)
    if graves:
        motivos.append({
            "code": "HIGH_SEVERITY_FINDINGS",
            "detail": f"{len(graves)} achado(s) de severidade "
                      f"{'/'.join(BLOCKING_SEVERITIES)}: "
                      + ", ".join(str(f.get("id")) for f in graves[:6]),
        })
    rule = status.get("_verdict_rule_check")
    if isinstance(rule, dict) and rule.get("consistent") is False:
        motivos.append({
            "code": "VERDICT_RULE_INCONSISTENT",
            "detail": str(rule.get("note") or
                          "o veredito contradiz a regra da spec do agente"),
        })
    return motivos


def fingerprint(status: dict[str, Any], speckit_dir: Path) -> str:
    """Impressão digital do que está sendo aprovado.

    Cobre TODOS os achados (não só os graves) e o `graph_checksum` do
    `traceability.json`. Qualquer mudança de conteúdo invalida a assinatura —
    que é o comportamento pedido: "expira quando os achados mudam".
    """
    achados = sorted(
        (str(item.get("id") or ""), str(item.get("severity") or ""),
         str(item.get("summary") or ""))
        for item in (status.get("findings") or []) if isinstance(item, dict)
    )
    trace = _read_json(speckit_dir / "traceability.json") or {}
    material = json.dumps({
        "verdict": status.get("verdict"),
        "findings": achados,
        "graph_checksum": trace.get("graph_checksum"),
    }, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


# ── Estado ───────────────────────────────────────────────────────────────────

def gate_status(project: str, repo_root: Path | None = None) -> dict[str, Any]:
    """Estado atual do gate. Só lê — nunca grava, nunca pergunta.

    É a fonte única consultada pelo gate de saída (`kind: human_approval`), para
    que o algoritmo do fingerprint não exista em duas cópias que possam divergir.
    """
    repo = repo_root or REPO_ROOT
    speckit = _speckit_dir(project, repo)
    status_path = speckit / STATUS_NAME
    resultado: dict[str, Any] = {
        "project": project,
        "state": "pending",
        "requires_approval": False,
        "triggers": [],
        "blockers": [],
        "fingerprint": "",
        "approval": {},
        "detail": "",
    }

    status = _read_json(status_path)
    if status is None:
        resultado["state"] = "pending"
        resultado["detail"] = (f"{STATUS_NAME} ausente ou inválido — a fase de "
                               f"conformidade não produziu artefato legível")
        return resultado

    motivos = triggers(status)
    atual = fingerprint(status, speckit)
    aprovacao = status.get("approval") if isinstance(status.get("approval"), dict) else {}
    resultado.update({
        "requires_approval": bool(motivos),
        "triggers": motivos,
        "blockers": blocking_findings(status),
        "fingerprint": atual,
        "approval": aprovacao,
        "verdict": status.get("verdict"),
    })

    if not motivos:
        resultado["state"] = "not_required"
        resultado["detail"] = ("nenhum achado crítico, veredito coerente — "
                               "aprovação humana não é exigida")
        return resultado

    registrado = str(aprovacao.get("status") or "")
    assinado = str(aprovacao.get("approved_fingerprint") or "")

    if registrado in PASSING_STATES:
        if assinado == atual:
            resultado["state"] = registrado
            quem = aprovacao.get("reviewer") or "(sem revisor nomeado)"
            resultado["detail"] = (
                f"{registrado} por {quem} em {aprovacao.get('approved_at', '?')}"
            )
        else:
            resultado["state"] = "expired"
            resultado["detail"] = (
                "os achados mudaram desde a aprovação — a assinatura anterior "
                "não cobre o conteúdo atual; é preciso decidir de novo"
            )
        return resultado

    if registrado == "rejected":
        if assinado == atual:
            resultado["state"] = "rejected"
            resultado["detail"] = (
                f"recusado por {aprovacao.get('reviewer', '?')} em "
                f"{aprovacao.get('approved_at', '?')}"
            )
        else:
            # Os achados mudaram desde a recusa: a decisão anterior era sobre
            # outro conteúdo. Voltar para `pending` é o que permite reavaliar
            # sem exigir que alguém desfaça a recusa à mão.
            resultado["state"] = "pending"
            resultado["detail"] = ("houve recusa anterior, mas sobre outros "
                                   "achados — reavaliação necessária")
        return resultado

    resultado["state"] = "pending"
    resultado["detail"] = (f"{len(motivos)} motivo(s) exigem ciência humana e "
                           f"nenhuma decisão foi registrada")
    return resultado


# ── Avaliação (wave6c) ───────────────────────────────────────────────────────

def evaluate(project: str, repo_root: Path | None = None) -> dict[str, Any]:
    """Classifica e materializa `compliance-gate.json`. Nunca reprova."""
    repo = repo_root or REPO_ROOT
    speckit = _speckit_dir(project, repo)
    speckit.mkdir(parents=True, exist_ok=True)
    estado = gate_status(project, repo)
    payload = {
        "project": project,
        "generated_at": _now_utc(),
        "state": estado["state"],
        "requires_approval": estado["requires_approval"],
        "decision_pending": estado["state"] in ("pending", "expired"),
        "verdict": estado.get("verdict"),
        "fingerprint": estado["fingerprint"],
        "triggers": estado["triggers"],
        "blockers": estado["blockers"],
        "approval": estado["approval"],
        "detail": estado["detail"],
    }
    _write_atomic(speckit / GATE_NAME, payload)
    return payload


# ── Registro da decisão ──────────────────────────────────────────────────────

def record(project: str, decision: str, *, name: str = "", role: str = "",
           comments: str = "", runner_mode: str = "manual",
           expect_fingerprint: str = "",
           repo_root: Path | None = None) -> dict[str, Any]:
    """Grava a decisão em `compliance-status.json` e no log append-only.

    `decision` ∈ {approved, auto_acknowledged, rejected}.
    """
    if decision not in ("approved", "auto_acknowledged", "rejected"):
        raise ValueError(f"decisão inválida: {decision!r}")

    repo = repo_root or REPO_ROOT
    speckit = _speckit_dir(project, repo)
    status_path = speckit / STATUS_NAME
    status = _read_json(status_path)
    if status is None:
        return {"status": "REFUSED", "detail":
                f"{STATUS_NAME} ausente ou inválido — nada a assinar. "
                f"Execute a F3S até a wave6b antes de registrar uma decisão."}

    atual = fingerprint(status, speckit)
    if expect_fingerprint and expect_fingerprint != atual:
        # Guarda contra assinar às cegas: o operador viu um conjunto de achados
        # e, entre ver e decidir, o conteúdo mudou. Assinar aqui registraria
        # ciência de algo que a pessoa não leu.
        return {"status": "REFUSED", "detail":
                "os achados mudaram entre a exibição e a decisão — "
                "reavalie antes de assinar", "expected": expect_fingerprint,
                "current": atual}

    if decision in ("approved", "rejected") and not (name.strip() and role.strip()):
        return {"status": "REFUSED", "detail":
                "nome e papel são obrigatórios para aprovar ou recusar — "
                "uma assinatura anônima não registra responsabilidade"}

    timestamp, ntp_fallback, servidor = _trusted_timestamp()
    estado = gate_status(project, repo)
    aprovacao: dict[str, Any] = {
        "status": decision,
        "reviewer": name.strip(),
        "reviewer_role": role.strip(),
        "comments": comments.strip(),
        "approved_at": timestamp,
        "approved_at_source": servidor or "relógio local (NTP indisponível)",
        "ntp_fallback": ntp_fallback,
        "runner_mode": runner_mode,
        "approved_fingerprint": atual,
        "blockers_acknowledged": [str(f.get("id")) for f in estado["blockers"]],
        "triggers_acknowledged": [t["code"] for t in estado["triggers"]],
    }
    if decision == "auto_acknowledged":
        aprovacao["note"] = (
            "execução automática — nenhuma pessoa informou aprovação; os "
            "blockers listados seguiram para a F4 sem revisão humana"
        )

    status["approval"] = aprovacao
    _write_atomic(status_path, status)

    # Append-only: uma reaprovação não pode apagar a assinatura anterior.
    try:
        with (speckit / LOG_NAME).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"recorded_at": _now_utc(), **aprovacao},
                                    ensure_ascii=False) + "\n")
    except OSError:
        pass  # o log é histórico; sua falha não invalida a decisão gravada

    evaluate(project, repo)
    return {
        "status": "OK",
        "decision": decision,
        "reviewer": aprovacao["reviewer"],
        "reviewer_role": aprovacao["reviewer_role"],
        "approved_at": timestamp,
        "approved_at_source": aprovacao["approved_at_source"],
        "ntp_fallback": ntp_fallback,
        "fingerprint": atual,
        "path": str(status_path),
    }


# ── Saída legível ────────────────────────────────────────────────────────────

def render_panel(payload: dict[str, Any]) -> str:
    """Painel dos achados. Impresso nos DOIS modos — dar ciência é o ponto."""
    if not payload.get("requires_approval"):
        return ("\n  ✅ Gate de conformidade — nenhum achado crítico; "
                "aprovação humana não é exigida.")
    linhas = [
        "",
        "═" * 72,
        "  ⚠️  CIÊNCIA NECESSÁRIA ANTES DE LIBERAR A F4",
        f"  Projeto: {payload['project']}   ·   Veredito: {payload.get('verdict')}",
        "═" * 72,
        "",
        "  Motivos:",
    ]
    for motivo in payload.get("triggers") or []:
        linhas.append(f"    • [{motivo['code']}] {motivo['detail']}")
    blockers = payload.get("blockers") or []
    if blockers:
        linhas += ["", f"  Achados de severidade alta/crítica ({len(blockers)}):"]
        for item in blockers:
            linhas.append(f"    ─ {item.get('id')} [{item.get('severity')}] "
                          f"{item.get('summary')}")
            if item.get("evidence"):
                linhas.append(f"        evidência: {item['evidence']}")
            if item.get("remediation"):
                linhas.append(f"        correção:  {item['remediation']}")
    linhas += [
        "",
        f"  Estado: {payload['state']} — {payload['detail']}",
        "  Detalhe completo: outputs/tobe/speckit/compliance-report.md",
        "═" * 72,
    ]
    return "\n".join(linhas)


# ── CLI ──────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="speckit_compliance_gate.py",
        description="Gate de aprovação humana da F3S — avalia e registra.")
    parser.add_argument("-p", "--project", required=True)
    parser.add_argument("--json", action="store_true", dest="as_json")

    modo = parser.add_mutually_exclusive_group()
    modo.add_argument("--evaluate", action="store_true",
                      help="classifica os achados e grava compliance-gate.json (padrão)")
    modo.add_argument("--status", action="store_true",
                      help="só consulta o estado, sem gravar nada")
    modo.add_argument("--approve", action="store_true",
                      help="registra aprovação nominal (exige --name e --role)")
    modo.add_argument("--acknowledge", action="store_true",
                      help="registra seguimento automático, sem revisor nomeado")
    modo.add_argument("--reject", action="store_true",
                      help="registra recusa (exige --name e --role)")

    parser.add_argument("--name", default="", help="nome de quem decide")
    parser.add_argument("--role", default="", help="papel de quem decide")
    parser.add_argument("--comments", default="")
    parser.add_argument("--mode", default="manual", choices=["manual", "auto"],
                        help="modo de execução do runner, registrado na assinatura")
    parser.add_argument("--fingerprint", default="",
                        help="fingerprint visto pelo operador; se divergir do "
                             "atual, a decisão é recusada")
    args = parser.parse_args(argv)

    if args.status:
        resultado = gate_status(args.project)
        print(json.dumps(resultado, ensure_ascii=False, indent=2) if args.as_json
              else render_panel({**resultado, "project": args.project}))
        return 0

    if args.approve or args.acknowledge or args.reject:
        decisao = ("approved" if args.approve
                   else "auto_acknowledged" if args.acknowledge else "rejected")
        resultado = record(
            args.project, decisao, name=args.name, role=args.role,
            comments=args.comments, runner_mode=args.mode,
            expect_fingerprint=args.fingerprint,
        )
        if args.as_json:
            print(json.dumps(resultado, ensure_ascii=False, indent=2))
        elif resultado["status"] == "OK":
            quem = (f"{resultado['reviewer']} ({resultado['reviewer_role']})"
                    if resultado["reviewer"] else "execução automática, sem revisor")
            print(f"\n  ✅ Decisão registrada: {decisao} — {quem}")
            print(f"     em {resultado['approved_at']} "
                  f"(fonte: {resultado['approved_at_source']})")
        else:
            print(f"\n  ❌ Decisão NÃO registrada — {resultado['detail']}",
                  file=sys.stderr)
        # Exit 2 só nos modos de gravação: aqui não há fase de pipeline sendo
        # marcada, e uma recusa silenciosa de registro seria pior que ruidosa.
        return 0 if resultado["status"] == "OK" else 2

    payload = evaluate(args.project)
    print(json.dumps(payload, ensure_ascii=False, indent=2) if args.as_json
          else render_panel(payload))
    # SEMPRE 0: avaliar não é reprovar. Quem bloqueia é o gate de saída.
    return 0


if __name__ == "__main__":
    sys.exit(main())
