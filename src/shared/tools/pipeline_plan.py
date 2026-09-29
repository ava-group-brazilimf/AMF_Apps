#!/usr/bin/env python3
"""
AVA Fabric — CLI da esteira · Montagem do plano de execução
============================================================
Expande ``pipeline.steps`` do ``ava-pipeline.yaml`` no plano executável,
aplicando os seletores do CLI (``--phase``, ``--agent``, ``--from``) e
enriquecendo cada passo com o ``spec_path`` real vindo do ``agent_registry``.

Por que o registry entra aqui
-----------------------------
O runner antigo achava a spec do agente por heurística de substring sobre
``rglob("*.md")``, escolhendo o **maior arquivo** entre os candidatos — podia
carregar o agente errado sem avisar. O ``agent_registry`` é a fonte canônica e
entrega o caminho exato de cada um dos ~107 agentes.

⚠️ Divergência intencional entre os dois eixos de "fase"
--------------------------------------------------------
``step.phase`` é ETAPA DA ESTEIRA (ordem de execução). ``registry.phase`` é o
MÓDULO do agente. Eles divergem de propósito::

    esteira F5 = DevOps Execute   ·  registry F5 = módulo qa-agents
    esteira F6 = QA Execution     ·  registry F6 = módulo devops-agents

``validate_plan`` valida só existência/despachabilidade/deprecação do agente —
**nunca** ``step.phase == registry.phase``. Ver tests/tools/test_pipeline_plan.py.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# SCRIPT_DIR = src/shared/tools → parents: shared, src, repo
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(SCRIPT_DIR))

import agent_registry  # noqa: E402
import dependency_graph  # noqa: E402
import f4_routing  # noqa: E402
import speckit_wave_manifest  # noqa: E402

#: Teto de execução, em segundos, de um passo ``kind: tool`` que não declare
#: ``timeout_s`` no DAG.
#:
#: É um LIMITE MÁXIMO DE SEGURANÇA — a fronteira entre "está demorando" e "não
#: vai voltar" — e não uma estimativa. Deliberadamente NÃO deriva de quantidade
#: de bounded contexts, de projetos, de comandos ou de tamanho de repositório: o
#: plano é montado antes de qualquer um desses números existir, e uma conta
#: dessas só transfere o chute para outro lugar. Quem precisa de mais tempo
#: declara ``timeout_s`` no próprio nó.
#:
#: 900s era o valor anterior, embutido no runner. Ele matava a F4S de
#: `nopcommerce-02` aos 835s de trabalho REAL, com a árvore já gerada e o
#: verifier ainda por rodar — o passo morria sem veredito nem log.
DEFAULT_TOOL_TIMEOUT_S = 3600


def resolve_tool_timeout_s(value: Any = None, *,
                           fallback: Any = None,
                           label: str = "") -> int:
    """Teto efetivo de um passo, na ordem: nó do DAG → fallback → default.

    Valor inválido (zero, negativo, não-numérico) não derruba a esteira e não
    passa silenciosamente: avisa no stderr e cai no default seguro. Um typo no
    DAG não pode virar `timeout=0` — que em `Popen.wait` mata o passo na hora.
    """
    for candidato in (value, fallback):
        if candidato is None or candidato == "":
            continue
        try:
            segundos = int(candidato)
        except (TypeError, ValueError):
            segundos = 0
        if segundos > 0 and not isinstance(candidato, bool):
            return segundos
        onde = f"{label}: " if label else ""
        print(f"  ⚠️  {onde}timeout_s inválido ({candidato!r}) — usando o default "
              f"de {DEFAULT_TOOL_TIMEOUT_S}s", file=sys.stderr)
        return DEFAULT_TOOL_TIMEOUT_S
    return DEFAULT_TOOL_TIMEOUT_S


@dataclass
class Step:
    """Um passo da esteira, já resolvido contra o registry."""
    phase: str                      # etapa da esteira: F1, F2a, F5, F8c...
    group: str                      # grupo endereçável por --phase: F1, F2, F8...
    agent: str
    trigger: str | None
    label: str
    spec_path: Path | None = None   # caminho real da spec (do registry)
    module: str = ""
    version: str = ""
    registry_phase: str = ""        # fase do MÓDULO — informativa, nunca validada
    ad_hoc: bool = False            # agente fora da esteira, pedido por --agent
    # Manifesto de contexto — `{mandatory: [...], advisory: [...]}`. Vazio = o
    # passo usa o caminho legado de injeção (ver context_manifest.py).
    inputs: dict[str, Any] = field(default_factory=dict)
    # Fan-out declarado — `{source, agent_from, agent_map}`. Vazio = passo único.
    foreach: dict[str, Any] = field(default_factory=dict)
    # Preenchidos na expansão do fan-out, em tempo de execução.
    task_group: str = ""
    target_stack: str = ""
    feature: str = ""               # pasta de feature do SpecKit: `002-w1-core-read`
    kind: str = "agent"              # `agent` ou `tool` determinístico
    command: list[str] = field(default_factory=list)
    wave: str = ""
    on_fail: str = ""                 # vazio=blocking; warn=registra e continua
    # Teto de execução do passo, em segundos. `None` = usa DEFAULT_TOOL_TIMEOUT_S.
    # Declarado por nó no DAG; ver `resolve_tool_timeout_s`. Nunca calculado a
    # partir de bounded contexts ou de qualquer outra métrica do projeto.
    timeout_s: int | None = None
    task_id: str = ""
    remediation_context: str = ""     # contexto de remediação passado ao agente

    @property
    def prompt(self) -> str:
        """Comando de invocação — idêntico ao formato do runner original."""
        return self._prompt_for("{PROJECT}")

    def _prompt_for(self, project: str) -> str:
        ref = f"@{self.agent}"
        # `feature:` só aparece em passos vindos do fan-out por DAG — é como o
        # agente sabe qual fonte lhe cabe quando o mesmo id é despachado N vezes.
        sufixo = f" | feature: {self.feature}" if self.feature else ""
        if self.trigger:
            return f"{ref} | {self.trigger} | project: {project}{sufixo}"
        return f"{ref} project: {project}{sufixo}"

    def build_prompt(self, project: str) -> str:
        prompt = self._prompt_for(project)
        if self.remediation_context:
            prompt += f"\n\nREMEDIATION CONTEXT (attempt to fix the build):\n{self.remediation_context}"
        return prompt

    def as_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase, "group": self.group, "agent": self.agent,
            "trigger": self.trigger, "label": self.label,
            "spec_path": str(self.spec_path.relative_to(REPO_ROOT)) if self.spec_path else None,
            "module": self.module, "version": self.version,
            "registry_phase": self.registry_phase, "ad_hoc": self.ad_hoc,
            "inputs": self.inputs, "kind": self.kind, "command": self.command,
            "wave": self.wave, "on_fail": self.on_fail,
            "timeout_s": self.timeout_s,
            "feature": self.feature, "task_group": self.task_group,
            "target_stack": self.target_stack, "task_id": self.task_id,
            "remediation_context": self.remediation_context,
        }


class PlanError(Exception):
    """Erro de configuração do plano — o CLI converte em exit 2."""


# ─── Construção ──────────────────────────────────────────────────────────────

def declared_steps(cfg: dict[str, Any]) -> list[Step]:
    """Os passos declarados no YAML, na ordem exata, sem filtro."""
    raw = cfg.get("steps") or []
    if not raw:
        raise PlanError(
            "nenhum passo declarado em `pipeline.steps` — "
            "confira src/shared/data/ava-pipeline.yaml (e se pyyaml está instalado)"
        )
    steps: list[Step] = []
    for i, item in enumerate(raw, 1):
        if not isinstance(item, dict) or not item.get("agent") or not item.get("phase"):
            raise PlanError(f"passo #{i} inválido em `pipeline.steps`: {item!r} "
                            f"(exige ao menos `phase` e `agent`)")
        steps.append(Step(
            phase=str(item["phase"]),
            group=str(item.get("group") or item["phase"]),
            agent=str(item["agent"]),
            trigger=item.get("trigger") or None,
            label=str(item.get("label") or item["agent"]),
            inputs=_parse_inputs(item.get("inputs"), item["phase"]),
            foreach=dict(item.get("foreach") or {}),
        ))
    dupes = _duplicate_phases(steps)
    if dupes:
        raise PlanError(f"`phase` duplicada em `pipeline.steps`: {', '.join(dupes)} — "
                        f"cada etapa precisa de um id único para ser endereçável por --phase")
    return steps


def dag_steps(phase: str, repo_root: Path | None = None,
              project: str | None = None, *,
              strict: bool = True) -> list[dict[str, Any]]:
    """Passos declarados em ``pipeline-dag/{phase}.yaml``, na ordem das waves.

    Existe porque uma fase multi-agente despachada como passo único vira teatro:
    o motor SDK carrega **apenas** o ``spec_path`` do orquestrador e proíbe tools,
    então os corpos dos sub-agentes — onde moram os contratos de formato — nunca
    entram em contexto.

    Medido na primeira execução real da F3S: skill de 8KB (só o orquestrador),
    68.170 tokens de saída, 26 artefatos em uma resposta. Os seis corpos de agente
    não foram carregados, e o resultado divergiu de todos os contratos que eles
    declaram — schema da rastreabilidade, seções obrigatórias, padrão de id.

    Devolve dicts (não ``Step``) para servir também ao ``ava-pipeline-runner-cli.py``,
    que trabalha com a tabela ``PIPELINE`` em dicionários. A ordem vive só no YAML.
    """
    root = repo_root or REPO_ROOT
    dag = root / "src" / "shared" / "data" / "pipeline-dag" / f"{phase}.yaml"
    if not dag.is_file():
        return []
    try:
        import yaml  # noqa: PLC0415
        data = yaml.safe_load(dag.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001 — degradar, nunca quebrar (IV3)
        return []

    waves = data.get("waves") or []
    try:
        wave_plan = dependency_graph.analyze(waves, id_field="id")
    except dependency_graph.DependencyGraphError as exc:
        raise PlanError(f"DAG {phase} inválido: {exc}") from exc
    waves_by_id = {str(wave["id"]): wave for wave in waves}
    waves = [waves_by_id[wave_id] for wave_id in wave_plan.order]
    manifest_features: list[dict[str, Any]] = []
    if phase == "F3S" and project:
        try:
            manifest_features = speckit_wave_manifest.build_manifest(
                project, root, strict=strict)["features"]
        except speckit_wave_manifest.ManifestError as exc:
            raise PlanError(f"F3S sem manifesto de waves válido: {exc}") from exc

    # Compatibilidade para DAGs que ainda declaram features diretamente.
    static_features = [
        {"feature": str(agent["feature"]), "codegen": True}
        for wave in waves for agent in (wave.get("agents") or []) if agent.get("feature")
    ]

    passos: list[dict[str, Any]] = []
    for wave in waves:
        if wave.get("implemented") is False:
            continue
        foreach = wave.get("foreach")
        if isinstance(foreach, dict) and foreach.get("source") == "wave_manifest":
            candidates = manifest_features
            if foreach.get("codegen_only"):
                candidates = [item for item in candidates if item.get("codegen")]
            repeat = [str(item["feature"]) for item in candidates]
        elif foreach:
            repeat = [str(item["feature"]) for item in static_features]
        else:
            repeat = [None]
        for feature_da_wave in repeat:
            for agente in wave.get("agents") or []:
                if not agente.get("id"):
                    continue
                feature = str(feature_da_wave or agente.get("feature")
                              or agente.get("source_id") or "")
                sufixo = feature or agente["id"].removeprefix("ava-speckit-")
                papel = agente["id"].removeprefix("ava-speckit-")
                passos.append({
                    "phase": f"{phase}:{papel}:{sufixo}" if wave.get("foreach")
                             else f"{phase}:{sufixo}",
                    "group": phase,
                    "agent": agente["id"],
                    "trigger": agente.get("trigger"),
                    "feature": feature,
                    "wave": wave.get("id", ""),
                    "label": _dag_label(phase, agente, feature),
                    "inputs": _resolver_feature(agente.get("inputs") or {}, feature),
                    "kind": "agent",
                    "command": [],
                    "outputs": _resolver_outputs(agente, feature),
                    "output_base": str(data.get("output_base") or ""),
                    # Sem isto, `pipeline_runner.load_skill` cai na busca
                    # HEURÍSTICA por substring, que ordena os candidatos por
                    # (nível, TAMANHO) e escolhe o maior. Medido em
                    # `cadastro-funcionarios-04`: `ava-speckit-compliance`
                    # casava em nível 1 pelo sufixo "compliance" e carregava
                    # `deliverables/agents/security-compliance-agent.md` (27KB)
                    # em vez de `speckit/agents/compliance-agent.md` (14KB) —
                    # o agente de segurança da F7. O passo então gravava
                    # `outputs/deliverables/security-compliance-*` e o contrato
                    # da F3S (`compliance-report.md`, `compliance-status.json`)
                    # ficava vazio. O registry já sabia o caminho certo; só
                    # ninguém o consultava neste caminho de expansão.
                    "spec_path": _spec_path_do_registry(agente["id"], root),
                })
        for tool in wave.get("tools") or []:
            tool_id = str(tool.get("id") or "")
            command = tool.get("command") or []
            if not tool_id or not isinstance(command, list) or not command:
                raise PlanError(f"{phase}:{wave.get('id')}: tool inválida: {tool!r}")
            passos.append({
                "phase": f"{phase}:tool:{tool_id}",
                "group": phase,
                "agent": tool_id,
                "trigger": None,
                "feature": "",
                "wave": wave.get("id", ""),
                "label": f"{phase} — tool · {tool_id}",
                "inputs": {},
                "kind": "tool",
                "command": [str(part) for part in command],
                "outputs": [],
                "output_base": str(data.get("output_base") or ""),
                # Política de falha da tool. Vazio = aborta a fase (padrão).
                # "confirm" = mostra o relatório e pergunta ao operador se segue
                # assumindo o risco; ele pode cancelar para corrigir antes.
                "on_fail": str(tool.get("on_fail") or ""),
                # Teto por nó. Ausente = default global (ver
                # DEFAULT_TOOL_TIMEOUT_S); nenhum nó existente precisa declarar.
                "timeout_s": tool.get("timeout_s"),
                # Marca a tool cujo resultado exige DECISÃO humana antes de a
                # fase seguinte ser liberada. O runner lê a chave, lê o
                # relatório que a tool gravou e conduz o prompt — a tool nunca
                # pergunta nada por conta própria.
                "requires_approval": bool(tool.get("requires_approval")),
            })
    return passos


def _spec_path_do_registry(agent_id: str, root: Path) -> str:
    """Caminho canônico da spec do agente, do registry. `""` se desconhecido.

    Devolve string relativa à raiz do repo — `dag_steps` entrega dicts, e um
    `Path` absoluto não sobreviveria à serialização do runner-state.
    Degradar para `""` mantém o comportamento anterior (busca heurística) para
    agente fora do registry, em vez de trocar um defeito por outro.
    """
    try:
        entry = agent_registry.get(agent_id)
    except Exception:  # noqa: BLE001 — registry indisponível nunca derruba o plano
        return ""
    if not entry or not entry.get("path"):
        return ""
    caminho = root / str(entry["path"])
    return str(entry["path"]) if caminho.is_file() else ""


def _resolver_outputs(agent: dict[str, Any], feature: str) -> list[str]:
    raw = agent.get("outputs")
    if raw is None:
        raw = agent.get("output")
    values = raw if isinstance(raw, list) else ([raw] if raw else [])
    return [str(value).replace("{feature}", feature) for value in values]


def _resolver_feature(inputs: dict[str, Any], feature: str) -> dict[str, Any]:
    """Substitui `{feature}` nos caminhos declarados da wave."""
    if not feature:
        return inputs
    resolvido: dict[str, Any] = {}
    for tier, itens in inputs.items():
        novos = []
        for item in itens or []:
            if isinstance(item, str):
                novos.append(item.replace("{feature}", feature))
            elif isinstance(item, dict):
                copia = dict(item)
                copia["path"] = str(copia.get("path", "")).replace("{feature}", feature)
                novos.append(copia)
        resolvido[tier] = novos
    return resolvido


def _dag_label(phase: str, agente: dict[str, Any], feature: str) -> str:
    papel = agente["id"].removeprefix("ava-speckit-").replace("-", " ")
    return f"{phase} — {papel}" + (f" · {feature}" if feature else "")


def expand_foreach(steps: list[Step], project: str) -> list[Step]:
    """Expande passos com `foreach:` em um passo por grupo de tasks.

    É o que tira o orçamento de saída do caminho crítico. Na execução auditada, a
    F4 foi **um** despacho: 624.278 tokens de entrada, 82.878 de saída contra um
    teto de 128.000, e 140 arquivos em uma resposta. O resultado foi uma fatia
    vertical mínima apresentada como implementação completa (RC-01).

    Aqui cada grupo declarado no plano vira uma chamada com a sua própria fatia,
    despachando o agente coder **real** da stack — que sob o motor SDK nunca era
    carregado, porque só o `spec_path` do orquestrador entrava no contexto.

    Sem razão de progresso em disco, o passo é mantido como estava: degradar com
    aviso, nunca inventar uma expansão vazia (IV3).
    """
    if not any(s.foreach for s in steps):
        return steps

    try:
        import task_ledger  # noqa: PLC0415 — só este caminho depende do razão
    except ImportError:  # pragma: no cover
        return steps

    expandidos: list[Step] = []
    for step in steps:
        if not step.foreach:
            expandidos.append(step)
            continue

        # Fan-out por DAG: um despacho por agente declarado nas waves da fase.
        if str(step.foreach.get("source")) == "dag":
            try:
                declarados = dag_steps(step.phase, project=project)
            except PlanError:
                # Em full pipeline, F2 ainda não produziu wave-model.json quando
                # o plano inicial é montado. O runner expande este placeholder
                # novamente quando alcança a F3S, depois dos produtores upstream.
                if step.phase == "F3S":
                    expandidos.append(step)
                    continue
                raise
            if not declarados:
                print(f"  ⚠️  {step.phase}: pipeline-dag/{step.phase}.yaml ausente ou vazio — "
                      f"passo mantido como despacho único", file=sys.stderr)
                expandidos.append(step)
                continue
            for d in declarados:
                candidate = Step(
                    phase=d["phase"], group=d["group"], agent=d["agent"],
                    trigger=d["trigger"], label=d["label"],
                    inputs=_parse_inputs(d["inputs"], d["phase"]),
                    feature=d["feature"],
                    kind=d.get("kind", "agent"), command=list(d.get("command") or []),
                    wave=d.get("wave", ""), on_fail=d.get("on_fail", ""),
                    timeout_s=d.get("timeout_s"),
                )
                expandidos.append(_enrich(candidate))
            continue

        # Fail-closed: razão ausente/ilegível NÃO vira despacho único. Esse
        # fallback é o defeito original (624k tokens de entrada, 140 arquivos
        # numa resposta), não a rede de proteção contra ele.
        try:
            task_ledger.ensure_enriched(project)
            task_ledger.validate(project)
            tasks = [
                task for task in task_ledger.execution_order(project)
                if task.get("status") not in {"verified", "blocked", "skipped"}
            ]
        except task_ledger.LedgerError as exc:
            raise PlanError(
                f"{step.phase}: fan-out por task impossível — {exc}\n"
                f"      A fase não é degradada para despacho único: sem o razão, "
                f"um único prompt teria de gerar o sistema inteiro."
            ) from exc

        if not tasks:
            # Nada pendente é conclusão, não motivo para um despacho monolítico.
            print(f"  ℹ️  {step.phase}: nenhuma task pendente no razão — "
                  f"passo removido do plano", file=sys.stderr)
            continue

        for task in tasks:
            # O agente vem do roteador determinístico (`f4_routing`), não de um
            # `agent_map` no YAML: o mapa apontava todas as stacks para o mesmo
            # agente genérico e os coders reais nunca eram carregados.
            try:
                rota = f4_routing.resolve_route(task, project)
            except f4_routing.RoutingError as exc:
                raise PlanError(
                    f"{step.phase}: {exc}\n"
                    f"      Roteamento é fail-closed: nenhuma task cai em agente "
                    f"genérico por omissão."
                ) from exc
            feature = str(task.get("feature") or "")
            expandidos.append(_enrich(Step(
                phase=f"{step.phase}:{task['task_id']}",
                group=step.group,
                agent=rota.agent,
                trigger=step.trigger,
                label=f"{step.label} — {task['task_id']} · {task['group']}",
                # Contexto estreitado para a feature DESTA task: sem isto cada
                # despacho carrega `specs/*/spec.md` de todas as features.
                inputs=_narrow_inputs(step.inputs, feature),
                task_group=task["group"],
                target_stack=rota.target_stack,
                feature=feature,
                task_id=task["task_id"],
            )))
    return expandidos


def _narrow_inputs(inputs: dict[str, Any], feature: str) -> dict[str, Any]:
    """Troca os globs `speckit/specs/*` pela feature da task.

    Medido em `cadastro-funcionarios-04`: `specs/*/spec.md` + `plan.md` +
    `tasks.md` somam 460 KB dos 659 KB do manifesto da F4, e a task precisa de
    UMA feature. Sem `feature` conhecida o manifesto fica como está — estreitar
    para o vazio seria pior que estreitar demais.
    """
    if not feature or not inputs:
        return dict(inputs)
    resolvido: dict[str, Any] = {}
    for tier, itens in inputs.items():
        if not isinstance(itens, list):
            resolvido[tier] = itens
            continue
        novos: list[Any] = []
        for item in itens:
            caminho = item.get("path", "") if isinstance(item, dict) else str(item)
            trocado = str(caminho).replace("speckit/specs/*/", f"speckit/specs/{feature}/")
            if isinstance(item, dict):
                copia = dict(item)
                copia["path"] = trocado
                novos.append(copia)
            else:
                novos.append(trocado)
        resolvido[tier] = novos
    return resolvido


def expand_runtime_dag(step: Step, project: str) -> list[Step]:
    """Expand a deferred DAG step after its upstream artifacts exist."""
    if str(step.foreach.get("source")) != "dag":
        return [step]
    declared = dag_steps(step.phase, project=project)
    if not declared:
        raise PlanError(f"{step.phase}: DAG não produziu passos executáveis")
    result: list[Step] = []
    for item in declared:
        candidate = Step(
            phase=item["phase"], group=item["group"], agent=item["agent"],
            trigger=item["trigger"], label=item["label"],
            inputs=_parse_inputs(item["inputs"], item["phase"]),
            feature=item["feature"], kind=item.get("kind", "agent"),
            command=list(item.get("command") or []), wave=item.get("wave", ""),
            on_fail=item.get("on_fail", ""), timeout_s=item.get("timeout_s"),
        )
        result.append(_enrich(candidate))
    return result


def _parse_inputs(raw: Any, phase: Any) -> dict[str, Any]:
    """Valida o bloco ``inputs:`` de um passo — ver context_manifest.py.

    Ausente ⇒ ``{}``, e o passo cai no caminho legado de injeção de contexto.
    Malformado ⇒ ``PlanError``: um manifesto que ninguém consegue ler é pior que
    manifesto nenhum, porque dá falsa sensação de garantia.
    """
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise PlanError(f"`inputs` do passo {phase} precisa ser um mapa com "
                        f"`mandatory:` e/ou `advisory:` — recebido {type(raw).__name__}")

    parsed: dict[str, Any] = {}

    # `floor:` sobrepõe o piso de contexto do passo (ver `context_manifest.
    # _floor_names`). `floor: []` remove o piso inteiro — é como a F5 tira
    # `context/shared-context.md` do prompt sem mexer no piso da esteira toda.
    if "floor" in raw:
        piso = raw.get("floor")
        if piso is not None and not isinstance(piso, list):
            raise PlanError(f"`inputs.floor` do passo {phase} precisa ser uma lista "
                            f"de caminhos (ou `[]` para remover o piso)")
        if isinstance(piso, list) and any(not isinstance(x, str) for x in piso):
            raise PlanError(f"`inputs.floor` do passo {phase} só aceita strings "
                            f"de caminho relativas a projects/{{project}}/")
        parsed["floor"] = list(piso or [])

    # `exists:` confere presença e população SEM injetar corpo (ver
    # `context_manifest._resolve_exists`). É como a F6 valida "a F4 rodou?" sem
    # despejar `outputs/tobe/source-code` inteiro no prompt.
    for tier in ("mandatory", "advisory", "exists"):
        entries = raw.get(tier)
        if entries is None:
            continue
        if not isinstance(entries, list):
            raise PlanError(f"`inputs.{tier}` do passo {phase} precisa ser uma lista")
        for entry in entries:
            if isinstance(entry, str):
                continue
            if isinstance(entry, dict) and entry.get("path"):
                continue
            raise PlanError(
                f"item inválido em `inputs.{tier}` do passo {phase}: {entry!r} — "
                f"use uma string de caminho ou um mapa com a chave `path`")
        parsed[tier] = entries

    unknown = set(raw) - {"mandatory", "advisory", "floor", "exists"}
    if unknown:
        raise PlanError(f"chave desconhecida em `inputs` do passo {phase}: "
                        f"{', '.join(sorted(unknown))} — só `mandatory`, `advisory`, "
                        f"`exists` e `floor` existem")
    return parsed


def _duplicate_phases(steps: list[Step]) -> list[str]:
    seen: set[str] = set()
    dupes: list[str] = []
    for s in steps:
        if s.phase in seen and s.phase not in dupes:
            dupes.append(s.phase)
        seen.add(s.phase)
    return dupes


def _enrich(step: Step) -> Step:
    """Anexa spec_path/module/version do registry. Silencioso se ausente —
    quem reprova é validate_plan(), com mensagem única e acionável."""
    if step.kind == "tool":
        return step
    entry = agent_registry.get(step.agent)
    if entry:
        step.spec_path = REPO_ROOT / entry["path"]
        step.module = entry.get("module", "")
        step.version = entry.get("version", "")
        step.registry_phase = entry.get("phase", "")
    return step


def build_plan(cfg: dict[str, Any], phases: list[str] | None = None,
               agent: str | None = None, start_at: str | None = None) -> list[Step]:
    """Monta o plano aplicando os seletores, sempre na ordem declarada.

    - ``phases`` casa contra ``phase`` **ou** ``group`` (``F2`` → os três passos
      da F2; ``F2b`` → só o DevOps Plan). A ordem é a do YAML, não a de digitação.
    - ``agent`` filtra os passos da esteira com aquele agente. Um agente que não
      está na esteira vira um passo avulso, sem trigger — é assim que se roda um
      agente isolado (``--agent ava-asis-inventory``).
    - ``start_at`` corta o prefixo pela posição na lista.
    """
    steps = declared_steps(cfg)

    if agent:
        matched = [s for s in steps if s.agent == agent]
        if matched:
            steps = matched
        else:
            entry = agent_registry.get(agent)
            if not entry:
                known = sorted({s.agent for s in declared_steps(cfg)})
                raise PlanError(
                    f"agente desconhecido: {agent!r}\n"
                    f"      Não está na esteira nem no agent_registry.\n"
                    f"      Agentes da esteira: {', '.join(known)}\n"
                    f"      Lista completa: python src/shared/tools/agent_registry.py"
                )
            steps = [Step(phase=entry.get("phase") or "?", group=entry.get("phase") or "?",
                          agent=agent, trigger=None,
                          label=f"{agent} (avulso, fora da esteira)", ad_hoc=True)]

    if phases:
        wanted = {p.strip() for p in phases if p.strip()}
        steps = [s for s in steps if s.phase in wanted or s.group in wanted]
        if not steps:
            raise PlanError(
                f"nenhum passo casa com --phase {', '.join(sorted(wanted))}\n"
                f"      Etapas válidas: python src/shared/tools/ava_pipeline.py list --phases"
            )

    if start_at:
        ids = [s.phase for s in steps]
        if start_at not in ids:
            groups = [s.group for s in steps]
            if start_at not in groups:
                raise PlanError(f"--from {start_at!r} não é uma etapa do plano ({', '.join(ids)})")
            idx = groups.index(start_at)
        else:
            idx = ids.index(start_at)
        steps = steps[idx:]

    return [_enrich(s) for s in steps]


def validate_plan(steps: list[Step]) -> list[str]:
    """Coerência com o agent_registry. Devolve a lista de problemas.

    Valida **só** a identidade do agente. NÃO compara ``step.phase`` com
    ``registry.phase``: a numeração da esteira e a dos módulos divergem de
    propósito (F5/F6 trocados) — ver docstring do módulo.
    """
    problems: list[str] = []
    for s in steps:
        if s.kind == "tool":
            if not s.command:
                problems.append(f"{s.phase}: tool {s.agent!r} sem command")
            continue
        entry = agent_registry.get(s.agent)
        if entry is None:
            problems.append(f"{s.phase}: agente {s.agent!r} ausente do agent_registry")
            continue
        if entry.get("deprecated"):
            problems.append(f"{s.phase}: agente {s.agent!r} está deprecado")
        if not entry.get("dispatchable"):
            problems.append(f"{s.phase}: agente {s.agent!r} não é despachável "
                            f"(stub ou sub-skill)")
        if s.spec_path and not s.spec_path.is_file():
            problems.append(f"{s.phase}: spec não encontrada em {entry.get('path')}")
    return problems


def format_table(steps: list[Step]) -> str:
    """Render legível da esteira, usado por `list --phases` e pelo --dry-run."""
    w_ph = max((len(s.phase) for s in steps), default=5)
    w_ag = max((len(s.agent) for s in steps), default=10)
    w_tr = max((len(s.trigger or "—") for s in steps), default=3)
    lines = []
    for i, s in enumerate(steps, 1):
        lines.append(f"  {i:>2}. {s.phase:<{w_ph}}  {s.agent:<{w_ag}}  "
                     f"{(s.trigger or '—'):<{w_tr}}  {s.label}")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    import json

    import pipeline_config

    ap = argparse.ArgumentParser(description="Expande e valida o plano da esteira")
    ap.add_argument("-p", "--project")
    ap.add_argument("--phase", action="append", default=None)
    ap.add_argument("--agent")
    ap.add_argument("--from", dest="start_at")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    phases = [p for raw in (args.phase or []) for p in raw.split(",")]
    try:
        plan = build_plan(pipeline_config.load_config(args.project),
                          phases or None, args.agent, args.start_at)
    except PlanError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    issues = validate_plan(plan)
    if args.json:
        print(json.dumps({"steps": [s.as_dict() for s in plan], "problems": issues},
                         indent=2, ensure_ascii=False))
    else:
        print(format_table(plan))
        for p in issues:
            print(f"  ⚠️  {p}", file=sys.stderr)
    raise SystemExit(2 if issues else 0)
