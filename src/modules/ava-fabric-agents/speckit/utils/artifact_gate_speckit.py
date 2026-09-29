#!/usr/bin/env python3
"""
AVA Fabric — Gates da fase F3S (SpecKit Planning)
==================================================
Responde, de forma **determinística e sem custo de LLM**, às duas perguntas que
cercam a camada de planejamento:

    entrada — "Os insumos existem? Se não, não gere nada."
    saída   — "O planejamento fechou? Se não, a F4 não começa."

Por que o gate de saída existe
------------------------------
Hoje a F4 começa incondicionalmente. Foi assim que, em ``nopcommerce-02-cli-ava``,
140 arquivos foram gerados sem que blueprint, ADRs, OpenAPI, regras de negócio ou
protótipo tivessem chegado ao gerador — e o relatório da esteira declarou
``Build Status: ✅ PASS (Simulated)`` com o ``dotnet build`` real falhando.

Um gate que aceita afirmação não é gate. Este confere arquivos em disco e delega
o resto a duas suítes executáveis (``speckit_traceability`` e
``prototype_coverage``), que retornam exit code.

Fonte da verdade
----------------
Os itens conferidos **derivam de** ``src/shared/data/pipeline-dag/F3S.yaml`` —
blocos ``entry_gate`` e ``exit_gate``. Este módulo não guarda uma segunda cópia.

    ⚠️ Este repositório já pagou o preço de espelhos manuais: ``agent_registry.py``
    nasceu porque dois catálogos escritos à mão divergiram em 52 agentes, e o
    cabeçalho de ``pipeline-dag/F1.yaml`` avisa em voz alta contra virar "a quarta
    fonte de verdade". Aqui a lista é lida em runtime; ``tests/ava-fabric-agents/
    speckit/test_artifact_gate_speckit.py`` trava a ausência de divergência.

Uso
---
    python artifact_gate_speckit.py --project P --gate entry
    python artifact_gate_speckit.py --project P --gate exit --json
    python artifact_gate_speckit.py --project P --gate both
    python artifact_gate_speckit.py --list

Exit codes
----------
    0 — PASS    : gate aprovado
    1 — FAIL    : falta artefato, ou suíte reprovou por falha estrutural
    3 — SOFT_FAIL: só lacuna de cobertura — o runner pergunta ao operador
    2 — ERROR   : projeto inexistente, DAG ilegível, gate desconhecido
"""
from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

# .../src/modules/ava-fabric-agents/speckit/utils → parents[5] = raiz do repo
REPO_ROOT = Path(__file__).resolve().parents[5]
DAG_PATH = REPO_ROOT / "src" / "shared" / "data" / "pipeline-dag" / "F3S.yaml"

# Força UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

EXIT_PASS, EXIT_FAIL, EXIT_ERROR = 0, 1, 2
#: Espelha `Reporter.SOFT_FAIL_EXIT`: reprovou só por lacuna de cobertura.
#: O runner oferece aceite de risco neste código; em qualquer outro, aborta.
SOFT_FAIL_EXIT = 3

#: Bases de resolução de caminho de um item de gate.
_BASES = {
    "project": lambda root, proj: root / "projects" / proj,
    "speckit": lambda root, proj: root / "projects" / proj / "outputs" / "tobe" / "speckit",
    "workspace": lambda root, _p: root,
}

_DEFAULT_MIN_SIZE = 1  # byte — arquivo vazio nunca conta como entregue


def report_path(gate: str, project: str, repo: Path | None = None) -> Path:
    """Onde o veredito do gate fica em disco, para quem não viu o console."""
    return ((repo or REPO_ROOT) / "projects" / project / "outputs" / "tobe"
            / "speckit" / f"{gate}-gate-status.json")


def write_report(result: dict[str, Any], project: str,
                 repo: Path | None = None) -> "Path | None":
    """Persiste o veredito. Nunca levanta: relatório não derruba execução.

    A política de erro do `F3S.yaml` diz que uma tool que só imprime no console
    e sai com código != 0 "vira ruído: o runner segue em frente e o achado se
    perde". Com o nó marcado `on_fail: warn`, a esteira segue mesmo — então o
    achado PRECISA sobreviver ao scrollback, ou o aviso não serve para nada.
    """
    alvo = report_path(str(result.get("gate") or "exit"), project, repo)
    try:
        alvo.parent.mkdir(parents=True, exist_ok=True)
        payload = dict(result)
        payload["generated_at"] = datetime.datetime.now(
            datetime.timezone.utc).isoformat(timespec="seconds")
        payload["advisory"] = True   # o nó do DAG é `on_fail: warn`
        alvo.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        return alvo
    except OSError:
        return None


# ─── Leitura do DAG ──────────────────────────────────────────────────────────

def load_dag(path: Path | None = None) -> dict[str, Any]:
    """Lê o F3S.yaml. Sem pyyaml disponível, erro claro em vez de gate silencioso."""
    dag_path = path or DAG_PATH
    if not dag_path.is_file():
        raise SystemExit(f"ERRO: DAG da F3S não encontrado: {dag_path}")
    try:
        import yaml  # noqa: PLC0415 — dependência só deste caminho
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "ERRO: pyyaml é necessário para ler o F3S.yaml.\n"
            "      pip install -r src/shared/tools/requirements-pipeline.txt"
        ) from exc
    try:
        return yaml.safe_load(dag_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise SystemExit(f"ERRO: F3S.yaml ilegível: {exc}") from exc


def gate_items(gate: str, dag: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Itens declarados de um gate — a lista vive só no YAML."""
    data = dag if dag is not None else load_dag()
    bloco = data.get(f"{gate}_gate") or {}
    return list(bloco.get("items") or [])


def gate_suites(gate: str, dag: dict[str, Any] | None = None) -> list[str]:
    data = dag if dag is not None else load_dag()
    bloco = data.get(f"{gate}_gate") or {}
    return list(bloco.get("check_suites") or [])


EXTERNAL_F3S_DEPENDENCIES: list[dict[str, str]] = [
    {"path": "src/shared/data/reference-architecture.yaml", "base": "workspace"},
    {"path": "src/shared/data/pipeline-dag/F3S.yaml", "base": "workspace"},
    {"path": "src/shared/schemas/speckit-plan-graph.schema.json", "base": "workspace"},
    {"path": "src/shared/schemas/speckit-task-fragment.schema.json", "base": "workspace"},
    {"path": "projects/{project}/context/project-config.yaml", "base": "project"},
    {"path": "projects/{project}/outputs/tobe/docs/architecture-blueprint.md", "base": "project"},
    {"path": "projects/{project}/outputs/tobe/docs/tech-framework-document.md", "base": "project"},
    {"path": "projects/{project}/outputs/tobe/docs/architecture-decision-matrix.md", "base": "project"},
    {"path": "projects/{project}/outputs/tobe/docs/security-architecture.md", "base": "project"},
    {"path": "projects/{project}/outputs/tobe/docs/decisions/*.md", "base": "project"},
    {"path": "projects/{project}/outputs/asis/docs/business-rules.md", "base": "project"},
    {"path": "projects/{project}/outputs/tobe/prototype/index.html", "base": "project"},
    {"path": "projects/{project}/outputs/tobe/prototype/screen-list.md", "base": "project"},
    {"path": "projects/{project}/outputs/tobe/docs/wave-plan.md", "base": "project"},
    {"path": "projects/{project}/outputs/tobe/migration/wave-model.json", "base": "project"},
    {"path": "projects/{project}/outputs/tobe/docs/openapi/*.yaml", "base": "project"},
    {"path": "projects/{project}/outputs/tobe/qa/test-cases.md", "base": "project"},
]


def check_external_dependencies(project: str, root: Path | None = None) -> dict[str, Any]:
    """Valida a presença dos artefatos externos que a F3S exige antes de qualquer despacho.

    Artefatos gerados dentro de outputs/tobe/speckit/ não entram aqui: a própria F3S
    produz esses arquivos. O objetivo desta checagem é bloquear a fase quando faltam
    insumos upstream ou recursos de origem.
    """
    repo = root or REPO_ROOT
    items: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []

    for item in EXTERNAL_F3S_DEPENDENCIES:
        pattern = item["path"].replace("{project}", project)
        base = item["base"]
        candidates: list[Path] = []
        if base == "workspace":
            candidates = sorted((repo / pattern).parent.glob((repo / pattern).name)) if "*" in pattern else [repo / pattern]
        else:
            project_root = repo / "projects" / project
            if "*" in pattern:
                candidates = sorted(Path(project_root / pattern.replace("projects/" + project + "/", "")).parent.glob(pattern.split("/")[-1]))
            else:
                candidates = [project_root / pattern.replace(f"projects/{project}/", "")]

        if "*" in pattern and not candidates:
            # fallback para glob manual quando o path contém subpastas
            resolved = list(repo.glob(pattern))
            candidates = sorted(resolved)

        present = any(p.exists() and p.is_file() and p.stat().st_size > 0 for p in candidates)
        display_path = item["path"].replace("projects/{project}/", "")
        record = {
            "path": display_path,
            "resolved": str(candidates[0]) if candidates else str((repo / pattern).resolve()),
            "present": present,
            "produced_by": "insumo externo da F3S",
        }
        items.append(record)
        if not present:
            missing.append(record)

    # `WARN`, nunca `FAIL`. A F3S está em evolução e não pode interromper a
    # esteira por insumo de OUTRA fase. Um artefato upstream ausente é
    # informação — o agente registra a degradação no artefato de saída — e não
    # motivo para a fase inteira não rodar. Os artefatos que a F3S consome de si
    # mesma continuam sendo conferidos pelos itens de gate (`gate_items`), que
    # resolvem sob `outputs/tobe/speckit/`.
    status = "PASS" if not missing else "WARN"
    message = (
        f"{len(missing)} dependência(s) externa(s) ausente(s) — a F3S continua. "
        "Os agentes devem registrar a degradação no artefato de saída, "
        "nunca inventar o conteúdo."
        if missing else
        "Dependências externas da F3S validadas com sucesso."
    )
    return {
        "status": status,
        "missing": missing,
        "items": items,
        "message": message,
    }


# ─── Verificação ─────────────────────────────────────────────────────────────

def _resolve(item: dict[str, Any], project: str, root: Path) -> Path:
    base_fn = _BASES.get(str(item.get("base") or "project"), _BASES["project"])
    return base_fn(root, project) / str(item["path"]).replace("\\", "/")


def check_item(item: dict[str, Any], project: str, root: Path) -> dict[str, Any]:
    """Um item de gate contra o disco. Nunca levanta — devolve o veredito."""
    target = _resolve(item, project, root)
    result: dict[str, Any] = {
        "path": str(item.get("path")),
        "base": str(item.get("base") or "project"),
        # Propagado para o resultado porque a orientação de correção depende
        # dele: um artefato ausente se gera, uma decisão pendente se toma.
        "kind": str(item.get("kind") or ""),
        "produced_by": str(item.get("produced_by") or ""),
        "resolved": str(target),
        "present": False,
        "detail": "",
    }

    if str(item.get("kind") or "") == "any_file":
        candidates = [
            _resolve({"path": path, "base": item.get("base") or "project"}, project, root)
            for path in (item.get("paths") or [])
        ]
        present = [path for path in candidates if path.is_file() and path.stat().st_size > 0]
        result["present"] = bool(present)
        result["detail"] = (
            f"fonte encontrada: {present[0]}" if present
            else "nenhuma alternativa presente: " + ", ".join(str(path) for path in candidates)
        )
        return result

    if str(item.get("kind") or "") == "human_approval":
        # Presença de arquivo não é conformidade. Medido em nopcommerce-04
        # (2026-08-21): a F4 foi liberada com dois blockers CRITICAL porque este
        # gate só conferia que `compliance-status.json` existia.
        #
        # O estado vem de `speckit_compliance_gate.gate_status()` — importado, e
        # não reimplementado, para que o algoritmo do fingerprint não passe a
        # existir em duas cópias que podem divergir em silêncio.
        try:
            # REPO_ROOT (onde este código vive) para ACHAR o módulo; `root` (a
            # raiz de dados, que os testes apontam para um tmp) só para LER o
            # projeto. Em produção são o mesmo caminho, e usar `root` para os
            # dois funcionava por coincidência.
            sys.path.insert(0, str(REPO_ROOT / "src" / "shared" / "tools"))
            import speckit_compliance_gate  # noqa: PLC0415
            estado = speckit_compliance_gate.gate_status(project, root)
        except Exception as exc:  # noqa: BLE001
            result["detail"] = f"não foi possível avaliar a aprovação: {exc}"
            return result
        result["present"] = estado["state"] in ("approved", "auto_acknowledged",
                                                "not_required")
        result["detail"] = f"{estado['state']} — {estado['detail']}"
        return result

    if str(item.get("kind") or "") == "manifest_features":
        manifest_item = {"path": str(item.get("manifest") or ""), "base": "project"}
        manifest_path = _resolve(manifest_item, project, root)
        if not manifest_path.is_file():
            result["detail"] = f"manifesto ausente: {manifest_item['path']}"
            return result
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            result["detail"] = f"manifesto inválido: {exc}"
            return result
        features = manifest.get("features") if isinstance(manifest, dict) else None
        if not isinstance(features, list) or not features:
            result["detail"] = "manifesto sem features[]"
            return result

        expected = {str(feature.get("feature") or "") for feature in features}
        expected.discard("")
        actual = {path.name for path in target.iterdir() if path.is_dir()} \
            if target.is_dir() else set()
        missing: list[str] = []
        for feature in features:
            name = str(feature.get("feature") or "")
            required = ["spec.md"]
            if feature.get("codegen"):
                required.extend([
                    "plan.md", "plan-graph.json", "task-fragment.json", "tasks.md",
                ])
            missing.extend(
                f"{name}/{artifact}" for artifact in required
                if not (target / name / artifact).is_file()
                or (target / name / artifact).stat().st_size == 0
            )
        # ── Scaffolds da fase de stack ───────────────────────────────────────
        # Histórico: `f4s_scaffold_injector.py` já criou features próprias
        # `000-scaffold-<stack>`, e esta isenção existia para elas não serem
        # reprovadas como "pastas fora do manifesto". O injetor mudou: hoje ele
        # enriquece a feature W0 Foundation, que consta do manifesto como
        # qualquer outra. Nenhum diretório `000-scaffold-*` é produzido.
        #
        # A isenção continua por compatibilidade com projetos gerados antes da
        # mudança — mas sem exigir artefato de pasta que ninguém cria mais.
        # Diretório legado presente é tolerado; ausente é o caso normal.
        scaffolds = {name for name in actual if name.startswith("000-scaffold-")}

        extra = sorted(actual - expected - scaffolds)
        result["present"] = bool(expected) and not missing and not extra
        details = [f"{len(expected)} feature(s) esperadas"]
        if scaffolds:
            details.append(f"{len(scaffolds)} scaffold(s) F4S")
        if missing:
            details.append(f"faltando: {', '.join(missing[:8])}")
        if extra:
            details.append(f"pastas fora do manifesto: {', '.join(extra[:8])}")
        result["detail"] = " · ".join(details)
        return result

    if str(item.get("kind") or "") == "json_field":
        if not target.is_file():
            result["detail"] = "arquivo ausente"
            return result
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            result["detail"] = f"JSON inválido: {exc}"
            return result
        field = str(item.get("field") or "")
        expected = item.get("expected")
        actual = data.get(field) if isinstance(data, dict) else None
        result["present"] = actual == expected
        result["detail"] = f"{field}={actual!r}, esperado {expected!r}"
        return result

    if str(item.get("kind") or "") == "dir" or item.get("min_count"):
        min_count = int(item.get("min_count") or 1)
        if not target.is_dir():
            result["detail"] = "diretório ausente"
            return result
        arquivos = [p for p in target.rglob("*") if p.is_file() and p.stat().st_size > 0]
        result["present"] = len(arquivos) >= min_count
        result["detail"] = f"{len(arquivos)} arquivo(s), mínimo {min_count}"
        return result

    if not target.is_file():
        result["detail"] = "arquivo ausente"
        return result

    tamanho = target.stat().st_size
    minimo = int(item.get("min_size") or _DEFAULT_MIN_SIZE)
    result["present"] = tamanho >= minimo
    result["detail"] = f"{tamanho} bytes, mínimo {minimo}"
    return result


def run_suite(suite: str, project: str, root: Path) -> dict[str, Any]:
    """Executa uma suíte de check e devolve o exit code real — nunca uma alegação."""
    cmd = [sys.executable, "-m", "src.shared.checks", "--project", project, "--suite", suite]
    try:
        proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=600)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"suite": suite, "status": "ERROR", "exit_code": None, "detail": str(exc)}
    # Exit 3 = a suíte reprovou, mas só por lacuna de cobertura. Ver
    # `Reporter.SOFT_FAIL_EXIT`. O gate distingue para não confundir "faltou
    # cobrir um caso de teste" com "o grafo está quebrado".
    if proc.returncode == 0:
        estado = "PASS"
    elif proc.returncode == SOFT_FAIL_EXIT:
        estado = "SOFT_FAIL"
    else:
        estado = "FAIL"
    return {
        "suite": suite,
        "status": estado,
        "exit_code": proc.returncode,
        "detail": (proc.stdout or proc.stderr or "").strip()[-1500:],
    }


def run_gate(gate: str, project: str, root: Path | None = None,
             dag: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = root or REPO_ROOT
    # Insumo externo ausente vira AVISO anexado ao veredito, não mais um
    # retorno antecipado com `status: FAIL`. Antes, a falta de um artefato de
    # outra fase (ex.: `outputs/asis/docs/business-rules.md`) reprovava o gate
    # antes de conferir um único artefato do próprio SpecKit.
    external = check_external_dependencies(project, repo)
    external_missing = list(external.get("missing") or [])

    data = dag if dag is not None else load_dag()
    itens = [check_item(i, project, repo) for i in gate_items(gate, data)]
    faltando = [i for i in itens if not i["present"]]

    suites: list[dict[str, Any]] = []
    if not faltando:
        # Só roda as suítes quando os artefatos existem — reprovar duas vezes
        # pelo mesmo motivo não ajuda ninguém a corrigir.
        suites = [run_suite(s, project, repo) for s in gate_suites(gate, data)]

    # A espinha é imutável depois da F3S. Se o traceability.json mudou depois do
    # `--init` do razão, o razão está descrevendo outra realidade — uma task pode
    # ter perdido a proveniência no meio da execução.
    checksum_ok = True
    if gate == "exit" and not faltando:
        try:
            from src.shared.tools import task_ledger  # noqa: PLC0415
            checksum_ok = task_ledger.checksum_matches(project, repo)
        except Exception:  # noqa: BLE001 — ausência do razão já é pega pelos itens
            checksum_ok = True

    reprovadas = [s for s in suites if s["status"] == "FAIL"]
    so_cobertura = [s for s in suites if s["status"] == "SOFT_FAIL"]
    if faltando or reprovadas or not checksum_ok:
        status = "FAIL"          # artefato ausente, suíte estrutural ou checksum
    elif so_cobertura:
        status = "SOFT_FAIL"     # só lacuna de cobertura — decisão do operador
    else:
        status = "PASS"
    bloco = (data.get(f"{gate}_gate") or {})
    # suites_on_fail: warn → suite failures are informational; only missing
    # artifacts and checksum drift block the gate.
    suites_block = str(bloco.get("suites_on_fail") or "").lower() != "warn"
    if not suites_block and not faltando and checksum_ok and (reprovadas or so_cobertura):
        status = "PASS"
    return {
        "gate": gate,
        "project": project,
        "status": status,
        "on_fail": bloco.get("on_fail"),
        "suites_advisory": not suites_block and bool(reprovadas or so_cobertura),
        "items": itens,
        "missing": faltando,
        "check_suites": suites,
        "traceability_checksum_ok": checksum_ok,
        # Insumo de outra fase que não está em disco. Informativo por decisão:
        # nunca entra em `missing`, nunca muda `status`.
        "external_missing": external_missing,
        "external_message": external["message"] if external_missing else "",
    }


# ─── Saída legível ───────────────────────────────────────────────────────────

def _print(result: dict[str, Any]) -> None:
    icone = {"PASS": "✅", "SOFT_FAIL": "⚠️"}.get(result["status"], "❌")
    print(f"\n  {icone} Gate {result['gate']} da F3S — {result['status']} "
          f"(projeto {result['project']})")
    for item in result["items"]:
        marca = "OK  " if item["present"] else "FALTA"
        print(f"    [{marca}] {item['path']}  ({item['detail']})")
        if not item["present"] and item["produced_by"]:
            print(f"             produzido por: {item['produced_by']}")
    for suite in result["check_suites"]:
        marca = ("OK  " if suite["status"] == "PASS" else ("AVISO" if result.get("suites_advisory") else { "SOFT_FAIL": "COBERT"}.get(suite["status"], "FALTA")))
        print(
            f"    [{marca}] suíte {suite['suite']} (exit {suite['exit_code']})"
            + (
                " [informativo — não bloqueia]"
                if result.get("suites_advisory") and suite["status"] != "PASS"
                else ""
            )
        )
    if result.get("traceability_checksum_ok") is False:
        print("    [FALTA] traceability.json mudou depois do --init do razão — "
              "a espinha deveria ser imutável após a F3S")
    if result["status"] != "PASS":
        acao = {"abort_f3s": "a F3S não deve rodar",
                "block_f4": "a F4 NÃO está liberada"}.get(str(result["on_fail"]), "")
        if acao:
            print(f"\n    → {acao}.")
        # Decisão pendente não é artefato ausente: dizer "gere-o" manda o
        # operador procurar um arquivo para produzir quando o que falta é ele
        # decidir. Os dois casos são separados para que a instrução sirva.
        pendencia_humana = [item for item in result.get("missing") or []
                            if str(item.get("kind") or "") == "human_approval"]
        ausentes = [item for item in result.get("missing") or []
                    if str(item.get("kind") or "") != "human_approval"]
        if pendencia_humana:
            print("\n    → Falta a DECISÃO do operador sobre os achados de conformidade.")
            print("      Reveja outputs/tobe/speckit/compliance-report.md e registre:")
            print("        python src/shared/tools/speckit_compliance_gate.py \\")
            print("            -p <projeto> --approve --name \"<Nome>\" --role \"<Papel>\"")
            print("      Ou reexecute a F3S a partir da wave6c para decidir pelo runner.")
        if ausentes:
            print("\n    → Artefatos externos obrigatórios ausentes. Gere-os antes de continuar a F3S.")
            for item in ausentes:
                print(f"      - {item['path']} (esperado em {item['resolved']})")
        if result.get("message"):
            print(f"\n    → {result['message']}")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="artifact_gate_speckit.py",
        description="Gates de entrada e saída da fase F3S — determinísticos, sem LLM.")
    parser.add_argument("--project", "-p", help="nome do projeto sob projects/")
    parser.add_argument("--gate", choices=["entry", "exit", "both"], default="both")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report", action="store_true",
                        help="persiste o veredito em outputs/tobe/speckit/"
                             "{gate}-gate-status.json (o console some, o achado não)")
    parser.add_argument("--warn", action="store_true",
                        help="reprovação vira aviso e o exit code continua 0 — "
                             "o gate é informativo e não interrompe a esteira")
    parser.add_argument("--list", action="store_true",
                        help="lista os itens declarados no F3S.yaml e sai")
    args = parser.parse_args(argv)

    if args.list:
        dag = load_dag()
        for gate in ("entry", "exit"):
            print(f"\n  {gate}_gate — {len(gate_items(gate, dag))} item(ns), "
                  f"{len(gate_suites(gate, dag))} suíte(s)")
            for item in gate_items(gate, dag):
                print(f"    - {item.get('path')}"
                      f"{'  [' + item['base'] + ']' if item.get('base') else ''}")
            for suite in gate_suites(gate, dag):
                print(f"    * suíte: {suite}")
        return EXIT_PASS

    if not args.project:
        parser.error("--project é obrigatório (ou use --list)")
    if not (REPO_ROOT / "projects" / args.project).is_dir():
        print(f"ERRO: projeto não encontrado: projects/{args.project}", file=sys.stderr)
        return EXIT_ERROR

    dag = load_dag()
    # Dependência externa ausente NÃO interrompe mais a tool. Antes havia aqui
    # um retorno antecipado com `EXIT_FAIL` que impedia até de conferir os
    # artefatos que a própria F3S produz. Agora é aviso, e o gate segue.
    external = check_external_dependencies(args.project, REPO_ROOT)
    if external["status"] != "PASS" and not args.json:
        print(f"\n⚠️  {external['message']}")
        for item in external["missing"]:
            print(f"  - {item['path']} (esperado em {item['resolved']})")

    gates = ["entry", "exit"] if args.gate == "both" else [args.gate]
    resultados = [run_gate(g, args.project, REPO_ROOT, dag) for g in gates]

    if args.json:
        print(json.dumps(resultados if len(resultados) > 1 else resultados[0],
                         ensure_ascii=False, indent=2))
    else:
        for r in resultados:
            _print(r)

    if args.report:
        for r in resultados:
            destino = write_report(r, args.project)
            if destino:
                print(f"\n  📄 Veredito do gate {r['gate']}: "
                      f"{destino.relative_to(REPO_ROOT).as_posix()}")

    if all(r["status"] == "PASS" for r in resultados):
        return EXIT_PASS

    if args.warn:
        # Gate informativo: o veredito continua verdadeiro em `--json` e no
        # relatório, mas o exit code é 0. Enquanto a camada SpecKit está em
        # evolução, nenhum gate dela pode interromper a esteira nem alterar o
        # exit code final do pipeline.
        print("\n" + "─" * 72)
        print(f"⚠️  Gate check completed with warnings — {args.project}")
        for r in resultados:
            if r["status"] != "PASS":
                faltas = ", ".join(i["path"] for i in (r.get("missing") or [])[:4])
                print(f"   gate {r['gate']}: {r['status']}"
                      + (f" — {faltas}" if faltas else ""))
        print("   Pipeline execution will continue. Exit Code: 0")
        print("─" * 72)
        return EXIT_PASS

    # Só lacuna de cobertura em todos os gates: devolve o código negociável,
    # para o runner poder oferecer a decisão em vez de abortar sozinho.
    if all(r["status"] in ("PASS", "SOFT_FAIL") for r in resultados):
        return SOFT_FAIL_EXIT
    return EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
