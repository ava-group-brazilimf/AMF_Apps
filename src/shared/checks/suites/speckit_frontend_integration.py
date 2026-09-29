"""
suites/speckit_frontend_integration.py
======================================
Cobertura do protótipo, das APIs e do elo entre os dois, sobre o planejamento da
F3S — antes da F4 começar a gerar código.

O que esta suíte cobre e a `prototype_coverage` não
---------------------------------------------------
A `prototype_coverage` valida a `spec-prototype.md` contra o protótipo: ela
pergunta "a especificação registrou a tela?". Esta pergunta é outra: **"existe
TAREFA, com arquivo alvo e dono, para cada tela, componente, token, rota,
operação de API e integração?"** — e é essa a que faltava.

A diferença não é acadêmica. Na auditoria de `nopcommerce-02-cli-ava`, 7 de 15
telas não chegaram ao código e apenas 2 ficaram fiéis ao protótipo. A causa foi
que o agente de frontend nunca recebeu o layout como entrada obrigatória, e
nenhum gate exigia que ele existisse no plano. Um plano sem task de tela produz
código sem tela, e a F4 não tem como inventar o que não lhe pediram.

Fontes (todas determinísticas, nenhuma parseia prosa de LLM)
    outputs/tobe/speckit/prototype-implementation-manifest.json   telas/componentes/tokens
    outputs/tobe/speckit/wave-spec-manifest.json                  escopo por wave
    outputs/tobe/speckit/traceability.json                        tasks compiladas
    outputs/tobe/prototype/index.html                             checksum
    context/project-config.yaml                                   stack

Checks aplicados
  PROTOTYPE-SCREEN-COVERAGE      toda tela de wave codegen tem task de frontend
  PROTOTYPE-COMPONENT-COVERAGE   todo componente obrigatório tem arquivo/task
  DESIGN-SYSTEM-COVERAGE         todo token e componente compartilhado tem owner
  ROUTE-COVERAGE                 toda rota tem task de configuração
  API-OPERATION-COVERAGE         todo operationId em escopo tem task backend
  FRONTEND-API-CLIENT-COVERAGE   toda API consumida por tela tem client frontend
  FRONTEND-BACKEND-INTEGRATION   toda tela dinâmica tem task de integração
  E2E-COVERAGE                   todo fluxo crítico tem task end-to-end
  SOURCE-REF-INTEGRITY           toda referência aponta para artefato e âncora reais
  VERIFY-PROFILE-VALIDITY        todo comando/perfil é compatível com a stack
  SINGLE-CREATE-OWNER            cada arquivo tem no máximo um create
  PROTOTYPE-CHECKSUM-CONSISTENCY o protótipo não mudou depois do planejamento

Severidade e política
---------------------
Estes checks reprovam LACUNA DE PLANEJAMENTO, que é lacuna de qualidade: eles
são `blocking=False`, como `CHK-SK-007/009`, e o `exit_gate` da F3S já declara
`suites_on_fail: warn`. O que eles NÃO fazem é sumir: o relatório estruturado
vai para `frontend-integration-checks.json` com evidência e ação recomendada por
achado, porque a política do F3S.yaml é explícita — "uma tool que só imprime no
console e sai com código != 0 vira ruído".

Uso (standalone):
    python -m src.shared.checks --project Meu-ERP --suite speckit_frontend_integration
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Sequence

if TYPE_CHECKING:
    from src.shared.checks.context import CheckContext
    from src.shared.checks.reporter import Reporter

SUITE = "speckit_frontend_integration"

REPO_ROOT = Path(__file__).resolve().parents[4]
_TOOLS = REPO_ROOT / "src" / "shared" / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

#: Relatório estruturado. Mesmo papel de `checks-report.json`: sobreviver ao
#: subprocess que rodou a suíte, para que o agente de compliance e o exit gate
#: possam reagir a um achado determinístico.
REPORT_REL = "outputs/tobe/speckit/frontend-integration-checks.json"

#: `work_kind` que satisfazem cada eixo de cobertura. Um único lugar: espalhar
#: isso por 12 checks foi como `ARTIFACT_CONTRACTS` virou a terceira fonte de
#: verdade que o F3S.yaml alerta contra.
_SCREEN_KINDS = frozenset({
    "frontend_page", "frontend_layout", "frontend_component", "frontend_route",
    "frontend_form", "frontend_validation", "frontend_state",
    "frontend_integration", "frontend_api_client",
})
_COMPONENT_KINDS = frozenset({
    "design_system", "frontend_component", "frontend_layout", "frontend_form",
})
_ROUTE_KINDS = frozenset({"frontend_route", "frontend_page"})
_BACKEND_KINDS = frozenset({
    "backend_api_contract", "backend_api_implementation", "backend_domain",
    "backend_persistence",
})
_CLIENT_KINDS = frozenset({"frontend_api_client", "frontend_integration"})
_INTEGRATION_KINDS = frozenset({"frontend_integration"})
_E2E_KINDS = frozenset({"end_to_end_test"})


def _anchor_resolves(anchor: str, content: str) -> bool:
    """Delega ao resolvedor canônico do compilador.

    Reimplementar isto como `anchor in content` produziu 92 falsos negativos na
    primeira execução: `#5.1-nomenclatura` é o SLUG de `## 5.1 Nomenclatura`, e
    a string literal não existe no arquivo. O repositório já tem um resolvedor
    que conhece essa regra e é o mesmo que CHK-SK-006 usa — ter dois seria
    garantir que os dois checks discordassem sobre a mesma âncora.
    """
    import speckit_task_compiler

    return speckit_task_compiler._ancora_resolve(
        anchor, content, speckit_task_compiler._headings_slug(content))


class SpeckitFrontendIntegrationSuite:
    """Gates de cobertura protótipo → tarefas → API → integração → e2e."""

    def __init__(self, ctx: "CheckContext") -> None:
        self.ctx = ctx
        self.findings: list[dict[str, Any]] = []

    # ── Infra ────────────────────────────────────────────────────────────────
    def _read_json(self, relative: str) -> dict[str, Any] | None:
        path = self.ctx.project_dir / relative
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _record(self, reporter: "Reporter", check_id: str, passed: bool, *,
                message: str, severity: str = "warning",
                items: Sequence[str] = (), task_ids: Sequence[str] = (),
                features: Sequence[str] = (), waves: Sequence[str] = (),
                evidence: str = "", action: str = "",
                blocking: bool = False) -> None:
        self.findings.append({
            "check_id": check_id,
            "status": "pass" if passed else ("fail" if severity == "error" else "warn"),
            "severity": "info" if passed else severity,
            "feature": sorted(set(features)),
            "wave": sorted(set(waves)),
            "task_ids": sorted(set(task_ids))[:64],
            "affected_items": sorted(set(items))[:64],
            "evidence": evidence,
            "recommended_action": "" if passed else action,
        })
        detail = evidence if not passed else message
        reporter.record(SUITE, f"{check_id} {message}", passed, detail,
                        blocking=blocking)

    # ── Execução ─────────────────────────────────────────────────────────────
    def run(self, reporter: "Reporter") -> None:
        prototype = self._read_json(
            "outputs/tobe/speckit/prototype-implementation-manifest.json")
        waves = self._read_json("outputs/tobe/speckit/wave-spec-manifest.json")
        traceability = self._read_json("outputs/tobe/speckit/traceability.json")

        if prototype is None:
            # Ausência do manifesto NÃO é "tudo certo". Reprovar uma vez, com a
            # ação, é mais honesto que 12 checks vazios passando.
            self._record(
                reporter, "PROTOTYPE-SCREEN-COVERAGE", False, severity="error",
                message="manifesto do protótipo ausente",
                evidence="outputs/tobe/speckit/prototype-implementation-manifest.json "
                         "não existe",
                action="execute src/shared/tools/prototype_manifest.py -p "
                       f"{self.ctx.project} (wave2 da F3S)")
            self._flush()
            return
        if traceability is None:
            self._record(
                reporter, "PROTOTYPE-SCREEN-COVERAGE", False, severity="error",
                message="traceability.json ausente",
                evidence="a F3S não compilou o grafo de tasks",
                action="execute speckit_task_compiler.py compile")
            self._flush()
            return

        entries = list(traceability.get("entries") or [])
        features = {item["feature"]: item
                    for item in (waves or {}).get("features", [])}

        self._screens(reporter, prototype, features, entries)
        self._components(reporter, prototype, features, entries)
        self._design_system(reporter, prototype, entries)
        self._routes(reporter, prototype, features, entries)
        self._api_operations(reporter, features, entries)
        self._api_clients(reporter, features, entries)
        self._integration(reporter, prototype, features, entries)
        self._e2e(reporter, prototype, features, entries)
        self._source_refs(reporter, entries)
        self._verify_profiles(reporter, entries)
        self._single_create_owner(reporter, entries)
        self._checksum(reporter, traceability)
        self._flush()

    def _flush(self) -> None:
        target = self.ctx.project_dir / REPORT_REL
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "suite": SUITE,
            "project": self.ctx.project,
            "total": len(self.findings),
            "failed": sum(1 for item in self.findings if item["status"] != "pass"),
            "findings": self.findings,
        }
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")

    # ── Helpers de escopo ────────────────────────────────────────────────────
    @staticmethod
    def _codegen_screens(prototype: dict[str, Any],
                         features: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Telas atribuídas a uma wave de codegen. Fora disso não há o que cobrar."""
        if not features:
            return {screen["screen_id"]: screen
                    for screen in prototype.get("screens") or []}
        in_scope: set[str] = set()
        for feature in features.values():
            if not feature.get("codegen"):
                continue
            slice_ = feature.get("prototype") or {}
            in_scope.update(entry["screen_id"] for entry in slice_.get("screens") or [])
        return {screen["screen_id"]: screen
                for screen in prototype.get("screens") or []
                if screen["screen_id"] in in_scope}

    @staticmethod
    def _covered(entries: Iterable[dict[str, Any]], field: str,
                 kinds: frozenset[str] | None = None) -> dict[str, list[str]]:
        """`id → task_ids` que o cobrem, opcionalmente filtrando por `work_kind`."""
        covered: dict[str, list[str]] = {}
        for entry in entries:
            if kinds is not None and str(entry.get("work_kind") or "") not in kinds:
                continue
            for value in entry.get(field) or []:
                covered.setdefault(str(value), []).append(str(entry.get("task_id")))
        return covered

    # ── Checks ───────────────────────────────────────────────────────────────
    def _screens(self, reporter, prototype, features, entries) -> None:
        screens = self._codegen_screens(prototype, features)
        covered = self._covered(entries, "screen_ids", _SCREEN_KINDS)
        # `work_kind` é opcional em planos 3.0.0: sem ele, qualquer task de
        # frontend que cite a tela conta. Exigir a taxonomia nova de um projeto
        # legado transformaria migração em reprovação em massa.
        loose = self._covered((e for e in entries
                               if str(e.get("task_type")) == "frontend"), "screen_ids")
        missing = sorted(sid for sid in screens
                         if not covered.get(sid) and not loose.get(sid))
        self._record(
            reporter, "PROTOTYPE-SCREEN-COVERAGE", not missing,
            severity="error",
            message=f"toda tela de wave codegen tem task de frontend "
                    f"({len(screens) - len(missing)}/{len(screens)})",
            items=missing,
            waves=[screens[sid].get("bounded_context") or "" for sid in missing],
            evidence=(f"telas sem nenhuma task de frontend: {', '.join(missing[:10])}"
                      if missing else f"{len(screens)} tela(s) cobertas"),
            action="planeje página, componentes, rota e estados da tela no "
                   "plan-graph.json, com screen_ids preenchido")

    def _components(self, reporter, prototype, features, entries) -> None:
        screens = self._codegen_screens(prototype, features)
        # Só componentes ESTRUTURAIS são cobrados. Um botão dentro de um
        # formulário não é uma unidade de código própria em nenhuma das stacks
        # suportadas, e exigir uma task por botão faria o gate reprovar sempre —
        # um gate que nunca passa é um gate que se aprende a ignorar.
        required = {
            component["component_id"]
            for screen in screens.values()
            for component in screen.get("components") or []
            if component.get("required")
        } | {component["component_id"]
             for component in prototype.get("shared_components") or []
             if component.get("required")}
        covered = self._covered(entries, "component_ids")
        missing = sorted(required - set(covered))
        self._record(
            reporter, "PROTOTYPE-COMPONENT-COVERAGE", not missing,
            message=f"todo componente do protótipo tem arquivo/task "
                    f"({len(required) - len(missing)}/{len(required)})",
            items=missing,
            evidence=(f"componentes sem task: {', '.join(missing[:10])}"
                      if missing else f"{len(required)} componente(s) cobertos"),
            action="declare component_ids nos arquivos do plan-graph.json que "
                   "implementam cada componente")

    def _design_system(self, reporter, prototype, entries) -> None:
        catalogue = prototype.get("design_system") or {}
        tokens = {token["token_id"]
                  for key in ("colors", "typography", "spacing", "other_tokens")
                  for token in catalogue.get(key) or []}
        shared = {component["component_id"]
                  for component in prototype.get("shared_components") or []
                  if component.get("required")}
        token_owner = self._covered(entries, "design_tokens")
        component_owner = self._covered(entries, "component_ids")
        orphan_tokens = sorted(tokens - set(token_owner))
        orphan_shared = sorted(shared - set(component_owner))

        missing = orphan_tokens + orphan_shared
        self._record(
            reporter, "DESIGN-SYSTEM-COVERAGE", not missing,
            message=f"tokens e componentes compartilhados têm owner "
                    f"({len(tokens) + len(shared) - len(missing)}/"
                    f"{len(tokens) + len(shared)})",
            items=missing,
            evidence=(f"{len(orphan_tokens)} token(s) e {len(orphan_shared)} "
                      f"componente(s) compartilhado(s) sem owner: "
                      f"{', '.join(missing[:10])}" if missing else
                      "Design System integralmente atribuído"),
            action="a wave foundation (owns_shared_components=true no "
                   "wave-spec-manifest.json) deve criar os tokens e os "
                   "componentes compartilhados, declarando design_tokens e "
                   "component_ids nos arquivos do plano")

    def _routes(self, reporter, prototype, features, entries) -> None:
        screens = self._codegen_screens(prototype, features)
        required = {route["route_id"] for route in prototype.get("routes") or []
                    if route.get("screen_id") in screens}
        covered = self._covered(entries, "route_ids")
        missing = sorted(required - set(covered))
        self._record(
            reporter, "ROUTE-COVERAGE", not missing,
            message=f"toda rota em escopo tem task de configuração "
                    f"({len(required) - len(missing)}/{len(required)})",
            items=missing,
            evidence=(f"rotas sem task: {', '.join(missing[:10])}" if missing
                      else f"{len(required)} rota(s) cobertas"),
            action="planeje a configuração de rota (work_kind frontend_route) "
                   "com route_ids preenchido, ou justifique a ausência na spec")

    def _api_operations(self, reporter, features, entries) -> None:
        required: set[str] = set()
        for feature in features.values():
            if not feature.get("codegen"):
                continue
            for source in feature.get("sources") or []:
                if str(source.get("source_id")) in {"api", "api-operations"}:
                    required.update(str(item) for item in source.get("anchors") or [])
        backend = self._covered(
            (e for e in entries if str(e.get("task_type")) == "backend"), "api_ops")
        missing = sorted(required - set(backend))
        self._record(
            reporter, "API-OPERATION-COVERAGE", not missing,
            severity="error",
            message=f"todo operationId em escopo tem task backend "
                    f"({len(required) - len(missing)}/{len(required)})",
            items=missing,
            evidence=(f"operações sem task backend: {', '.join(missing[:10])}"
                      if missing else f"{len(required)} operação(ões) cobertas"),
            action="planeje contrato, modelos, validação, handler, caso de uso, "
                   "domínio, persistência e testes de cada operationId")

    def _api_clients(self, reporter, features, entries) -> None:
        consumed: dict[str, list[str]] = {}
        for feature in features.values():
            slice_ = feature.get("prototype") or {}
            for screen in slice_.get("screens") or []:
                for operation in screen.get("api_ops") or []:
                    consumed.setdefault(operation, []).append(screen["screen_id"])
        clients = self._covered(
            (e for e in entries if str(e.get("task_type")) == "frontend"), "api_ops")
        missing = sorted(set(consumed) - set(clients))
        self._record(
            reporter, "FRONTEND-API-CLIENT-COVERAGE", not missing,
            severity="error",
            message=f"toda API consumida por tela tem client frontend "
                    f"({len(consumed) - len(missing)}/{len(consumed)})",
            items=missing,
            evidence=(f"operações consumidas por tela sem client frontend: "
                      f"{', '.join(missing[:10])}" if missing else
                      f"{len(consumed)} operação(ões) com client"),
            action="planeje o service/client de API (work_kind "
                   "frontend_api_client) com api_ops preenchido")

    def _integration(self, reporter, prototype, features, entries) -> None:
        screens = self._codegen_screens(prototype, features)
        dynamic = {sid for sid, screen in screens.items() if screen.get("dynamic")}
        integrated = self._covered(entries, "screen_ids",
                                   _INTEGRATION_KINDS | _CLIENT_KINDS)
        missing = sorted(dynamic - set(integrated))
        justified = [sid for sid in missing
                     if screens[sid].get("static_justification")]
        real = [sid for sid in missing if sid not in justified]
        self._record(
            reporter, "FRONTEND-BACKEND-INTEGRATION", not real,
            severity="error",
            message=f"toda tela dinâmica tem task de integração "
                    f"({len(dynamic) - len(real)}/{len(dynamic)})",
            items=real,
            evidence=(f"telas dinâmicas sem work_kind frontend_integration/"
                      f"frontend_api_client: {', '.join(real[:10])}" if real else
                      f"{len(dynamic)} tela(s) dinâmica(s) integradas"),
            action="planeje a task que liga a tela ao operationId: mapeamento de "
                   "request, loading, sucesso, vazio, validação e erro")

    def _e2e(self, reporter, prototype, features, entries) -> None:
        screens = self._codegen_screens(prototype, features)
        critical = {flow["flow_id"] for flow in prototype.get("flows") or []
                    if flow.get("critical")
                    and all(sid in screens for sid in flow.get("screens") or [])}
        covered = self._covered(entries, "flow_ids", _E2E_KINDS)
        loose = self._covered(entries, "flow_ids")
        missing = sorted(sid for sid in critical
                         if not covered.get(sid) and not loose.get(sid))
        self._record(
            reporter, "E2E-COVERAGE", not missing,
            message=f"todo fluxo crítico tem task end-to-end "
                    f"({len(critical) - len(missing)}/{len(critical)})",
            items=missing,
            evidence=(f"fluxos sem task e2e: {', '.join(missing[:10])}" if missing
                      else f"{len(critical)} fluxo(s) crítico(s) cobertos"),
            action="planeje um teste end-to-end por fluxo crítico (work_kind "
                   "end_to_end_test) com flow_ids preenchido, dependendo das "
                   "tasks de frontend e backend do fluxo")

    def _source_refs(self, reporter, entries) -> None:
        """Toda âncora aponta para artefato existente. Reabrindo o arquivo.

        Complementa CHK-SK-006, que já reabre o arquivo-fonte: aqui a checagem é
        de EXISTÊNCIA do artefato, que é o modo de falha novo — um plano pode
        agora citar `prototype-implementation-manifest.json`, e uma referência a
        um manifesto que não foi gerado passaria despercebida pelo check antigo.
        """
        missing_artifacts: dict[str, list[str]] = {}
        missing_anchors: dict[str, list[str]] = {}
        cache: dict[str, str | None] = {}
        for entry in entries:
            refs = list(entry.get("source_refs") or []) + \
                list(entry.get("prototype_refs") or [])
            for ref in refs:
                artifact = str(ref.get("artifact") or "")
                anchor = str(ref.get("anchor") or "")
                if not artifact:
                    continue
                if artifact not in cache:
                    path = self.ctx.project_dir / artifact
                    cache[artifact] = (
                        path.read_text(encoding="utf-8", errors="replace")
                        if path.is_file() else None)
                content = cache[artifact]
                if content is None:
                    missing_artifacts.setdefault(artifact, []).append(
                        str(entry.get("task_id")))
                elif anchor and not _anchor_resolves(anchor, content):
                    missing_anchors.setdefault(f"{artifact}#{anchor}", []).append(
                        str(entry.get("task_id")))
        broken = sorted(missing_artifacts) + sorted(missing_anchors)
        self._record(
            reporter, "SOURCE-REF-INTEGRITY", not broken,
            severity="error",
            message="toda referência aponta para artefato e âncora existentes",
            items=broken,
            task_ids=[tid for ids in
                      list(missing_artifacts.values()) + list(missing_anchors.values())
                      for tid in ids],
            evidence=(f"{len(missing_artifacts)} artefato(s) inexistente(s) e "
                      f"{len(missing_anchors)} âncora(s) não encontrada(s): "
                      f"{', '.join(broken[:8])}" if broken else
                      f"{len(cache)} artefato(s) verificados"),
            action="use apenas artefatos e âncoras que existem; regere o plano "
                   "da feature em vez de citar referência inventada")

    def _verify_profiles(self, reporter, entries) -> None:
        import verify_profiles

        try:
            import prototype_manifest
            stack_config = prototype_manifest.load_target_stack(self.ctx.project_dir)
        except Exception:  # noqa: BLE001 — degradar; a stack é conferida por outro check
            stack_config = {}
        bad: list[str] = []
        task_ids: list[str] = []
        for entry in entries:
            profile = str(entry.get("verify_profile") or "")
            stack = str(entry.get("target_stack") or "")
            if profile and profile not in verify_profiles.PROFILES:
                bad.append(f"{entry.get('task_id')}: perfil {profile!r} inválido")
                task_ids.append(str(entry.get("task_id")))
                continue
            result = verify_profiles.normalize(
                entry.get("verify_command") or "", stack=stack,
                task_type=str(entry.get("task_type") or ""),
                work_kind=str(entry.get("work_kind") or ""),
                verify_profile=profile, project_dir=self.ctx.project_dir,
                config=stack_config, repo_root=REPO_ROOT)
            if not result["compatible"]:
                bad.append(f"{entry.get('task_id')}: "
                           f"{(entry.get('verify_command') or '')[:48]}")
                task_ids.append(str(entry.get("task_id")))
        self._record(
            reporter, "VERIFY-PROFILE-VALIDITY", not bad,
            message=f"todo comando de verificação é compatível com a stack "
                    f"({len(entries) - len(bad)}/{len(entries)})",
            items=bad[:20], task_ids=task_ids,
            evidence=(f"{len(bad)} task(s) com comando incompatível: "
                      f"{'; '.join(bad[:6])}" if bad else
                      "todos os comandos resolvem pelo perfil da stack"),
            action="declare verify_profile no plan-graph.json; "
                   "verify_profiles.PROFILES lista os aceitos")

    def _single_create_owner(self, reporter, entries) -> None:
        creators: dict[str, list[str]] = {}
        for entry in entries:
            if str(entry.get("action")) != "create":
                continue
            if str(entry.get("ownership_status") or "OWNER") != "OWNER":
                continue
            creators.setdefault(str(entry.get("target_file")), []).append(
                str(entry.get("task_id")))
        duplicated = {path: ids for path, ids in creators.items() if len(ids) > 1}
        self._record(
            reporter, "SINGLE-CREATE-OWNER", not duplicated,
            severity="error",
            message=f"cada arquivo tem no máximo um create "
                    f"({len(creators) - len(duplicated)}/{len(creators)})",
            items=sorted(duplicated),
            task_ids=[tid for ids in duplicated.values() for tid in ids],
            evidence=(f"arquivos com mais de um create resolvido como OWNER: "
                      f"{', '.join(sorted(duplicated)[:8])}" if duplicated else
                      f"{len(creators)} arquivo(s) com dono único"),
            action="mantenha create em uma única wave e converta as demais para "
                   "action: update no plan-graph.json")

    def _checksum(self, reporter, traceability) -> None:
        import prototype_manifest

        result = prototype_manifest.verify_checksum(self.ctx.project, REPO_ROOT)
        planned = str(traceability.get("prototype_checksum") or "")
        ok = result["status"] == "ok" and (not planned or planned == result["actual"])
        self._record(
            reporter, "PROTOTYPE-CHECKSUM-CONSISTENCY", ok,
            severity="error",
            message="o protótipo corresponde ao checksum registrado",
            evidence=(f"status={result['status']}; manifesto="
                      f"{(result['expected'] or '-')[:23]}…; disco="
                      f"{(result['actual'] or '-')[:23]}…; traceability="
                      f"{(planned or '-')[:23]}…"),
            action="regere o manifesto do protótipo e reexecute o planejamento "
                   "da F3S — as âncoras das tasks apontam para conteúdo que mudou")
