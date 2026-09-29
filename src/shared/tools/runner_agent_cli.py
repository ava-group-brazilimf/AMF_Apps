#!/usr/bin/env python3
"""Resolução e diagnóstico do despacho de um agente avulso pelo runner.

Por que este módulo existe separado do ``ava-pipeline-runner-cli.py``
----------------------------------------------------------------
O runner importa ``msvcrt`` no topo e monta estado global no import
(``_INPUTS_APLICADOS = _apply_declared_inputs(PIPELINE)``). Nada dele é
importável num teste sem extração por AST. Tudo o que dá para decidir sem tocar
no console mora aqui: resolução de agente, validação do passo e os construtores
das mensagens de erro — funções puras, testáveis por igualdade de string.

Por que a esteira do runner é a fonte, e não ``pipeline_plan.build_plan``
-------------------------------------------------------------------------
Porque os namespaces de fase divergem, e ``run_step`` faz curto-circuito por
STRING EXATA de fase::

    3462:  if agent == "_ast_extractor":
    3471:  if phase in ("S1", "S4"):   -> builder determinístico, sem LLM
    3491:  elif phase == "S2":
    3502:  elif phase == "S3":

===========================  ==================  =================
agente                       PIPELINE do runner  ava-pipeline.yaml
===========================  ==================  =================
ava-summary                  S1, S4              F8a, F8c, F8d
ava-summary-remediation      S2                  F8b
ava-summary-validate         S3                  (ausente)
_ast_extractor               F0                  (ausente)
ava-devops-containerize      FC                  (ausente)
===========================  ==================  =================

Resolver ``ava-summary`` pelo YAML devolveria a fase ``F8a``; ``run_step`` não
casaria ``("S1","S4")``, pularia ``_run_summary_generate_standalone`` e queimaria
uma inferência de 128k tokens para produzir o que um script Python produz de
graça. O teste ``test_resolver_preserva_a_fase_do_runner`` trava isso.

Uso standalone (resolução seca, zero inferência)::

    python src/shared/tools/runner_agent_cli.py --agent ava-tobe-migration-plan -p meu-erp-03
"""
from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

EXIT_OK, EXIT_FAILED, EXIT_CONFIG, EXIT_ABORTED = 0, 1, 2, 130

_LARGURA = 74


class AgentCLIError(Exception):
    """Falha de resolução — carrega o bloco já formatado e o exit code."""

    def __init__(self, bloco: str, exit_code: int = EXIT_CONFIG):
        super().__init__(bloco)
        self.bloco = bloco
        self.exit_code = exit_code


# ─── Moldura das mensagens ───────────────────────────────────────────────────
# Mesmo formato de `explicar_fase_nao_expandida` no runner, que já provou
# funcionar: moldura, CAUSA RAIZ, COMO CORRIGIR, COMANDO. Texto puro, sem ANSI —
# quem imprime decide a cor, e o teste compara string.

def _moldura(titulo: str, corpo: list[str]) -> str:
    linhas = ["=" * _LARGURA, f"  {titulo}", "=" * _LARGURA]
    linhas.extend(corpo)
    linhas.append("=" * _LARGURA)
    return "\n".join(linhas)


def _secao(titulo: str, linhas: list[str]) -> list[str]:
    return ["", f"  {titulo}"] + [f"    {linha}" for linha in linhas]


# ─── Provider ────────────────────────────────────────────────────────────────

def resolver_provider(deployment: str) -> str:
    """Espelha o teste que o próprio runner já faz em ``main()``.

    O global ``PROVIDER`` só é corrigido dentro de ``_select_model_interactive``.
    Pulado o menu, ``run_step`` tomaria o ramo errado e mandaria payload
    Anthropic para endpoint OpenAI — falha silenciosa e cara.
    """
    return "anthropic" if (deployment or "").lower().startswith("claude") else "openai"


# ─── Catálogo ────────────────────────────────────────────────────────────────

def _registry():
    """O registry é opcional: sem ele, o tier 2 some e o tier 1 continua de pé."""
    try:
        import agent_registry
        return agent_registry
    except Exception:                                     # noqa: BLE001
        return None


def _universo(pipeline: list[dict]) -> list[str]:
    """União dos agentes da esteira e do registry — 111 ids hoje."""
    nomes = {str(s.get("agent") or "") for s in pipeline}
    reg = _registry()
    if reg:
        try:
            nomes |= {r["agent"] for r in reg.load()}
        except Exception:                                 # noqa: BLE001
            pass
    nomes.discard("")
    return sorted(nomes)


def sugerir(alvo: str, universo: list[str], n: int = 3) -> list[str]:
    return difflib.get_close_matches(alvo, universo, n=n, cutoff=0.6)


def listar_agentes(pipeline: list[dict]) -> str:
    """Agentes da esteira (com fase e trigger) e o resto do catálogo."""
    da_esteira: dict[str, list[str]] = {}
    for passo in pipeline:
        agente = str(passo.get("agent") or "")
        if not agente:
            continue
        marca = str(passo.get("phase"))
        if passo.get("trigger"):
            marca += f"/{passo['trigger']}"
        da_esteira.setdefault(agente, []).append(marca)

    linhas = ["Agentes da esteira (fase e trigger próprios):", ""]
    for agente in sorted(da_esteira):
        sufixo = "   [ambíguo]" if len(da_esteira[agente]) > 1 else ""
        linhas.append(f"  {agente:<38} {', '.join(da_esteira[agente])}{sufixo}")

    reg = _registry()
    if reg:
        try:
            fora = sorted({r["agent"] for r in reg.catalog()} - set(da_esteira))
        except Exception:                                 # noqa: BLE001
            fora = []
        if fora:
            linhas += ["", f"Avulsos do agent_registry ({len(fora)}) — sem trigger, "
                           "contexto pelo caminho legado:", ""]
            linhas += [f"  {agente}" for agente in fora]
    linhas += ["", "Agente [ambíguo] exige --phase para desempatar."]
    return "\n".join(linhas)


# ─── Mensagens de erro ───────────────────────────────────────────────────────

def explicar_projeto_inexistente(project: str, disponiveis: list[str]) -> str:
    corpo = [f"  projeto : {project}"]
    corpo += _secao("CAUSA RAIZ",
                    [f"Não existe projects/{project}/ neste repositório."])
    perto = sugerir(project, disponiveis)
    if perto:
        corpo += _secao("VOCÊ QUIS DIZER", [f"-p {p}" for p in perto])
    corpo += _secao("PROJETOS DISPONÍVEIS", disponiveis or ["(nenhum)"])
    return _moldura("PROJETO NÃO ENCONTRADO", corpo)


def explicar_agente_desconhecido(agent: str, pipeline: list[dict],
                                 project: str) -> str:
    universo = _universo(pipeline)
    corpo = [f"  agente  : {agent}", f"  projeto : {project}"]
    corpo += _secao("CAUSA RAIZ", [
        "Este id não está na esteira do runner nem no agent_registry.",
        f"O catálogo conhece {len(universo)} agentes."])
    perto = sugerir(agent, universo)
    if perto:
        corpo += _secao("VOCÊ QUIS DIZER", [f"--agent {p}" for p in perto])
    corpo += _secao("COMO LISTAR", [
        'python "ava-pipeline-runner-cli.py" --list-agents',
        "python src/shared/tools/agent_registry.py --catalog"])
    return _moldura("AGENTE DESCONHECIDO", corpo)


def explicar_agente_ambiguo(agent: str, candidatos: list[dict],
                            project: str) -> str:
    corpo = [f"  agente  : {agent}", f"  projeto : {project}"]
    corpo += _secao("CAUSA RAIZ", [
        "Este agente aparece em mais de uma etapa da esteira, com trigger",
        "diferente em cada uma. Não há default defensável — escolher por conta",
        "própria rodaria o passo errado em silêncio."])
    corpo += _secao("ONDE ELE APARECE", [
        f"{str(c.get('phase')):<6} trigger={str(c.get('trigger')):<8} "
        f"{c.get('label', '')}" for c in candidatos])
    corpo += _secao("COMO CORRIGIR", [
        f'python "ava-pipeline-runner-cli.py" --agent {agent} -p {project} '
        f"--phase {candidatos[0].get('phase')}"])
    return _moldura("AGENTE AMBÍGUO — INFORME --phase", corpo)


def explicar_fase_invalida(agent: str, phase: str, candidatos: list[dict],
                           project: str) -> str:
    corpo = [f"  agente  : {agent}", f"  --phase : {phase}"]
    corpo += _secao("CAUSA RAIZ",
                    [f"{agent} não aparece na etapa {phase} da esteira."])
    corpo += _secao("FASES VÁLIDAS PARA ESTE AGENTE",
                    [str(c.get("phase")) for c in candidatos])
    corpo += _secao("COMO CORRIGIR", [
        f'python "ava-pipeline-runner-cli.py" --agent {agent} -p {project} '
        f"--phase {candidatos[0].get('phase')}"])
    return _moldura("FASE INVÁLIDA PARA O AGENTE", corpo)


def explicar_passo_invalido(agent: str, problemas: list[str],
                            project: str) -> str:
    corpo = [f"  agente  : {agent}", f"  projeto : {project}"]
    corpo += _secao("CAUSA RAIZ", problemas)
    corpo += _secao("COMO INSPECIONAR", [
        f"python src/shared/tools/agent_registry.py --agent {agent}"])
    return _moldura("AGENTE NÃO DESPACHÁVEL", corpo)


def explicar_fanout_avulso(passo: dict, project: str, escopos: list[str],
                           rotulo: str) -> str:
    agent = str(passo.get("agent"))
    flag = "--feature" if rotulo == "feature" else "--task-id"
    corpo = [f"  agente  : {agent}", f"  fase    : {passo.get('phase')}"]
    corpo += _secao("CAUSA RAIZ", [
        f"{agent} roda uma vez por {rotulo} — a esteira o expande em N despachos.",
        "Despachá-lo como passo único é modo de falha medido: a F3S assim gerou",
        "26 artefatos numa resposta de 68.170 tokens com skill de 8 KB, violando",
        "o contrato de seis agentes (ava-pipeline.yaml:180-184)."])
    if escopos:
        visiveis = escopos[:12]
        corpo += _secao(f"{rotulo.upper()}S DISPONÍVEIS", visiveis)
        if len(escopos) > 12:
            corpo.append(f"    … mais {len(escopos) - 12}")
        corpo += _secao("COMO CORRIGIR", [
            f'python "ava-pipeline-runner-cli.py" --agent {agent} -p {project} '
            f"{flag} {escopos[0]}"])
    else:
        corpo += _secao("COMO CORRIGIR", [
            f"Nenhum {rotulo} disponível ainda — rode antes a fase que produz o",
            "manifesto de waves (F3S) ou o razão de tasks (compilador SpecKit)."])
    corpo += _secao("ASSUMIR O RISCO", [
        "--force-single despacha mesmo assim, reproduzindo o defeito acima."])
    return _moldura("AGENTE COM FAN-OUT — INFORME O ESCOPO", corpo)


# ─── Resolução ───────────────────────────────────────────────────────────────

def resolver_passo(pipeline: list[dict], project: str, agent: str, *,
                   phase: str | None = None, trigger: str | None = None,
                   feature: str | None = None) -> dict[str, Any]:
    """Devolve o dict de passo pronto para ``run_step``.

    Três tiers, nesta ordem — ver o docstring do módulo para o porquê de a
    esteira do runner vir primeiro.
    """
    candidatos = [s for s in pipeline if s.get("agent") == agent]

    if candidatos:
        # Tier 1 — esteira do runner: fase, trigger e inputs canônicos.
        if phase:
            exatos = [s for s in candidatos if s.get("phase") == phase]
            if not exatos:
                raise AgentCLIError(
                    explicar_fase_invalida(agent, phase, candidatos, project))
            escolhido = exatos[0]
        elif len(candidatos) > 1:
            raise AgentCLIError(
                explicar_agente_ambiguo(agent, candidatos, project))
        else:
            escolhido = candidatos[0]
        passo = dict(escolhido)
        passo["ad_hoc"] = False
    else:
        reg = _registry()
        entry = reg.get(agent) if reg else None
        if entry is None:
            # Tier 3 — desconhecido.
            raise AgentCLIError(
                explicar_agente_desconhecido(agent, pipeline, project))
        # Tier 2 — avulso pelo registry. Mesmo shape que `_expand_ledger_phase`
        # já produz; `inputs={}` leva ao contexto legado, e isso é declarado ao
        # operador em vez de fingido.
        passo = {
            "phase": phase or entry.get("phase") or "AVULSO",
            "label": f"{agent} (avulso — módulo {entry.get('module') or '?'})",
            "agent": agent,
            "trigger": None,
            "inputs": {},
            "kind": "agent",
            "ad_hoc": True,
        }

    if trigger:
        passo["trigger"] = trigger
    passo.setdefault("trigger", None)
    if feature:
        passo["feature"] = feature

    # Enriquecimento comum: spec canônica do registry, que faz `load_skill`
    # pular a heurística de substring. Sem isto, `ava-tobe-migration-plan`
    # carrega um doc do Playwright de dentro de node_modules — verificado.
    reg = _registry()
    entry = reg.get(agent) if reg else None
    if entry:
        passo["spec_path"] = str(REPO_ROOT / entry["path"])    # str, nunca Path
        passo["module"] = entry.get("module", "")
        passo["version"] = entry.get("version", "")
        passo["registry_phase"] = entry.get("phase", "")
    return passo


def validar_passo(passo: dict) -> list[str]:
    """Predicados que impedem o despacho. Lista vazia = pode ir."""
    problemas: list[str] = []
    agent = str(passo.get("agent") or "")

    # `run_step` acessa estes por colchete — ausência vira KeyError, e o de
    # `label` só estoura DEPOIS de a inferência inteira ter sido gasta.
    for campo in ("phase", "label", "agent"):
        if not passo.get(campo):
            problemas.append(f"passo sem `{campo}` — run_step falharia ao acessá-lo")
    if "trigger" not in passo:
        problemas.append("passo sem a chave `trigger` — run_step acessa por colchete")

    reg = _registry()
    entry = reg.get(agent) if reg else None
    if entry:
        if entry.get("deprecated"):
            problemas.append(f"{agent} está marcado DEPRECATED no registry")
        if not entry.get("dispatchable", True):
            problemas.append(f"{agent} não é despachável (sub-skill de outro agente)")
        if not (REPO_ROOT / entry["path"]).is_file():
            problemas.append(f"spec declarada no registry não existe: {entry['path']}")
    return problemas


def detectar_fanout(passo: dict) -> str:
    """Qual escopo o agente exige: ``feature``, ``task`` ou vazio.

    A esteira expande estes agentes em N despachos; um despacho único reproduz
    um modo de falha já medido. Ver ``explicar_fanout_avulso``.
    """
    agente = str(passo.get("agent") or "")
    fase = str(passo.get("phase") or "")
    if fase == "F3S" or agente.startswith("ava-speckit-"):
        return "feature"
    if fase == "F4" or "codegen" in agente:
        return "task"
    return ""


def escopos_disponiveis(project: str, rotulo: str,
                        repo_root: Path | None = None) -> list[str]:
    """Features do manifesto de waves, ou task_ids prontos no razão."""
    raiz = repo_root or REPO_ROOT
    try:
        if rotulo == "feature":
            import speckit_wave_manifest
            manifesto = speckit_wave_manifest.build_manifest(project, raiz)
            return [str(f["feature"]) for f in manifesto.get("features") or []]
        if rotulo == "task":
            import task_ledger
            return [str(t["task_id"]) for t in task_ledger.ready_tasks(project)]
    except Exception:                                     # noqa: BLE001
        # Ausência de manifesto/razão é informação, não exceção: a mensagem de
        # fan-out já instrui a rodar a fase que os produz.
        return []
    return []


# ─── CLI de resolução seca ───────────────────────────────────────────────────

def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python src/shared/tools/runner_agent_cli.py",
        description="resolve um agente em passo de execução — sem gastar inferência")
    parser.add_argument("--agent", metavar="ID", required=True,
                        help="id do agente (esteira ou agent_registry)")
    parser.add_argument("-p", "--project", metavar="NOME", required=True)
    parser.add_argument("--phase", metavar="ID",
                        help="desempata agente presente em mais de uma etapa")
    parser.add_argument("--trigger", metavar="T")
    parser.add_argument("--feature", metavar="F")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    projetos = REPO_ROOT / "projects"
    disponiveis = sorted(p.name for p in projetos.iterdir()
                         if p.is_dir()) if projetos.is_dir() else []
    if args.project not in disponiveis:
        print(explicar_projeto_inexistente(args.project, disponiveis),
              file=sys.stderr)
        return EXIT_CONFIG

    # Sem o runner à mão a esteira fica vazia, então só o ramo avulso é
    # exercitado aqui. O tier 1 é coberto pelo runner e pelos testes.
    try:
        passo = resolver_passo([], args.project, args.agent, phase=args.phase,
                               trigger=args.trigger, feature=args.feature)
    except AgentCLIError as exc:
        print(exc.bloco, file=sys.stderr)
        return exc.exit_code

    problemas = validar_passo(passo)
    if problemas:
        print(explicar_passo_invalido(args.agent, problemas, args.project),
              file=sys.stderr)
        return EXIT_CONFIG

    if args.json:
        print(json.dumps(passo, ensure_ascii=False, indent=2))
    else:
        for chave in ("phase", "agent", "trigger", "label", "spec_path",
                      "module", "version", "ad_hoc"):
            if chave in passo:
                print(f"  {chave:<15} {passo[chave]}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(_main())
