#!/usr/bin/env python3
"""Consolida plan-graphs e task-fragments do SpecKit em traceability v4.

⚠️ **"compile" aqui e consolidacao LOGICA do plano de tasks.** Esta ferramenta
nao compila codigo da aplicacao, nao invoca toolchain, nao produz binario e nao
executa build. A F3S e exclusivamente etapa de PLANEJAMENTO: le specs, planos e
fragments, resolve dependencias e ownership, e grava rastreabilidade e o estado
inicial de progresso. Compilar codigo e responsabilidade da F4. O nome do
arquivo e mantido por compatibilidade com o DAG e com os comandos existentes.

Politica de erro: defeito SEMANTICO do plano (ownership disputado, ciclo de
dependencia, cobertura incompleta) e recuperavel — vira aviso estruturado e a
consolidacao segue. Exit != 0 fica reservado a falha TECNICA que impeca ler ou
gravar. Nenhuma inconsistencia de planejamento pode descartar tasks integras:
medido em `cadastro-funcionarios-04`, 31 conflitos de ownership derrubavam 218
tasks validas e produziam placeholder em vez de artefato.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(SCRIPT_DIR))

import dependency_graph  # noqa: E402
import prototype_manifest  # noqa: E402
import verify_profiles  # noqa: E402

#: Versões de `plan-graph.json` / `task-fragment.json` aceitas. A 3.1.0 só
#: ACRESCENTA campos opcionais, então ler as duas com o mesmo código não é
#: tolerância — é o contrato: um projeto planejado antes desta mudança compila
#: sem conversão e sem perder nada (§17 do briefing).
ACCEPTED_SCHEMA_VERSIONS = ("3.0.0", "3.1.0")

#: Campos que o PLANO é autoridade e o fragment apenas recopia. Centralizados
#: aqui porque a lista cresceu com o vínculo ao protótipo, e mantê-la espalhada
#: por três funções foi o que fez `produces`/`consumes` divergirem antes.
PLAN_OWNED_LIST_FIELDS = (
    "produces", "consumes", "screen_ids", "component_ids", "route_ids",
    "design_tokens", "flow_ids", "api_ops", "rule_ids", "test_ids",
)

#: Gramática canônica dos tokens de contrato. Cada prefixo tem um formato de
#: sufixo previsível, e é isso que permite validar `consumes` sem produtor
#: contra o catálogo real de operações, telas e componentes — em vez de aceitar
#: qualquer string que a LLM inventar.
TOKEN_PREFIXES: dict[str, str] = {
    "api-contract": "operationId",
    "api-implementation": "operationId",
    "api-client": "operationId",
    "screen": "SCR",
    "component": "CMP",
    "route": "RTE",
    "design-token": "TOK",
    "test:e2e": "FLW",
    "contract": "free",
    "artifact": "free",
}

#: Sufixos que são identificadores do manifesto do protótipo: preservam o caixa
#: alta. `contract:`/`artifact:` continuam totalmente minúsculos, como antes.
_ID_TOKEN_PREFIXES = frozenset({
    "screen", "component", "route", "design-token", "test:e2e",
})

# Força UTF-8 no Windows — mesma guarda de src/shared/checks/cli.py.
# Sem ela, `render_diagnosis()` estourava UnicodeEncodeError no console cp1252
# ao imprimir qualquer achado acentuado, e o `except Exception` do main()
# convertia o crash de console num exit 0. Resultado medido em produção
# (nopcommerce-04, 2026-08-21): o gate da wave4a reportou ✅ sem ter validado
# nada, e os 3 erros P002 que ele encontrara só apareceram três passos adiante.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


class CompilerError(ValueError):
    """Raised when structured F3S inputs cannot produce a safe global graph."""


# ── Coletor de avisos ────────────────────────────────────────────────────────
# Política do pipeline: defeito de dado recuperável NUNCA trava a fase. Ele é
# degradado de forma determinística, registrado aqui e materializado em
# `compile-warnings.json` junto do caminho de correção. O que antes matava a
# compilação inteira — e fazia `tasks.md`/`traceability.json` sequer existirem —
# agora vira linha de relatório, e a F3S segue produzindo os artefatos que
# consegue produzir.
_WARNINGS: list[dict[str, str]] = []

# Um target declarado como diretório vira este placeholder. O agente de planning
# escreve `.../Migrations/` querendo dizer "crie a pasta"; materializar o
# placeholder preserva a intenção sem inventar um arquivo de código.
_DIR_PLACEHOLDER = ".gitkeep"


def _warn(code: str, owner: str, message: str, fix: str) -> None:
    entry = {"code": code, "owner": owner, "message": message, "fix": fix}
    if entry not in _WARNINGS:
        _WARNINGS.append(entry)


# ── Ownership de arquivo ─────────────────────────────────────────────────────
# A F3S consolida PLANO, não compila código. Um conflito de ownership é defeito
# de dado semântico: ele descreve mal quem cria o quê, e a correção é regerar um
# plano. Não é motivo para descartar as tasks íntegras das outras features.
#
# Medido em `cadastro-funcionarios-04`: 31 conflitos derrubavam 218 tasks
# válidas, porque a checagem levantava `CompilerError` no PRIMEIRO conflito e o
# `except` a jusante abortava a gravação inteira. O resultado era
# `traceability.json` placeholder e a cascata de 11 checks reprovados — todos
# sintoma, nenhum apontando a causa.
OWNERSHIP_CREATE_CREATE = "CREATE_CREATE_CONFLICT"
OWNERSHIP_UPDATE_NO_CREATE = "UPDATE_WITHOUT_CREATE"
OWNERSHIP_DUPLICATE_UPDATE = "DUPLICATE_UPDATE"
OWNERSHIP_SCOPE_VIOLATION = "OWNERSHIP_SCOPE_VIOLATION"
OWNERSHIP_INVALID_TARGET = "INVALID_TARGET_FILE"
OWNERSHIP_CROSS_WAVE = "CROSS_WAVE_OWNERSHIP_CONFLICT"

#: Conflitos de ownership do run corrente, na forma estruturada exigida pelo
#: relatório. Separado de `_WARNINGS` porque tem esquema próprio e é consumido
#: por ferramenta, não só lido por humano.
_CONFLICTS: list[dict[str, Any]] = []


def _reset_run_state() -> None:
    """Zera o estado de run. Necessário para chamadas repetidas em processo."""
    _WARNINGS.clear()
    _CONFLICTS.clear()


def _record_conflict(kind: str, target_file: str, claims: list[dict[str, Any]],
                     *, recommended_owner: str = "", reason: str = "",
                     resolution: str = "") -> dict[str, Any]:
    """Registra um conflito recuperável e devolve o registro.

    Nunca levanta: registrar um conflito não pode ser o motivo de uma falha.
    """
    conflict = {
        "code": kind,
        "severity": "warning",
        "target_file": target_file,
        "actions": sorted({str(c.get("action") or "") for c in claims}),
        "task_ids": [str(c.get("task_id") or "") for c in claims],
        "features": sorted({str(c.get("feature") or "") for c in claims}),
        "waves": sorted({str(c.get("wave_id") or "") for c in claims if c.get("wave_id")}),
        "source_files": sorted({str(c.get("source") or "") for c in claims if c.get("source")}),
        "claims": claims,
        "recommended_owner": recommended_owner,
        "reason": reason,
        "resolution": resolution,
    }
    if conflict not in _CONFLICTS:
        _CONFLICTS.append(conflict)
    return conflict


def normalize_token(token: Any) -> str:
    """Forma canônica de um token de `produces`/`consumes`.

    Sem isto, `api-contract:GetAllFuncoes`, `API-Contract:getallfuncoes` e
    `apiContract:GetAllFuncoes` eram três tokens distintos e o casamento
    produtor↔consumidor simplesmente não acontecia — a aresta que liga o
    client do frontend ao contrato do backend deixava de existir, e o grafo
    ficava com frontend e backend como componentes desconexos. O §12 pede
    tokens determinísticos; esta função é onde isso é imposto, não pedido.

    O prefixo sempre normaliza para minúsculas. O sufixo preserva o caixa
    quando é um identificador (`SCR-…`, `CMP-…`, `operationId`), porque esses
    ids são chaves em outro artefato e mudá-los quebraria a junção.
    """
    text = str(token or "").strip()
    if not text or ":" not in text:
        return text
    # `test:e2e:FLW-X` tem dois pontos no prefixo; tenta o prefixo composto antes.
    for prefix in sorted(TOKEN_PREFIXES, key=len, reverse=True):
        if text.lower().startswith(prefix + ":"):
            suffix = text[len(prefix) + 1:].strip()
            if prefix in _ID_TOKEN_PREFIXES:
                return f"{prefix}:{suffix.upper()}"
            if prefix in {"api-contract", "api-implementation", "api-client"}:
                return f"{prefix}:{suffix}"
            return f"{prefix}:{suffix}".lower()
    return text


def token_parts(token: str) -> tuple[str, str]:
    """`(prefixo canônico, sufixo)` de um token, ou `("", token)` se livre."""
    text = str(token or "")
    for prefix in sorted(TOKEN_PREFIXES, key=len, reverse=True):
        if text.lower().startswith(prefix + ":"):
            return prefix, text[len(prefix) + 1:]
    return "", text


def normalize_target(raw: Any) -> str:
    """Forma canônica de um `target_file` para COMPARAÇÃO de ownership.

    Só normaliza o que é ruído de escrita — separador, `./` inicial, barra
    duplicada, espaço nas pontas. Não muda maiúsculas: o repositório gera código
    para sistemas de arquivos sensíveis a caixa, e achatar isso criaria conflito
    onde não há. O caminho persistido nunca é alterado por esta função.
    """
    texto = str(raw or "").strip().replace("\\", "/")
    while "//" in texto:
        texto = texto.replace("//", "/")
    while texto.startswith("./"):
        texto = texto[2:]
    return texto.strip("/")


def _spec_menciona(spec_text: str, target: str) -> bool:
    """A spec da feature cita este arquivo?

    A spec é a autoridade funcional (§3.4 do contrato da fase). Casar pelo
    caminho inteiro e pelo basename cobre as duas formas em que os agentes
    escrevem a referência, sem depender de nome de domínio algum — nada aqui
    conhece `Funcionario`, `W0` ou o projeto.
    """
    if not spec_text or not target:
        return False
    alvo = normalize_target(target)
    if alvo.casefold() in spec_text.casefold():
        return True
    base = alvo.rsplit("/", 1)[-1]
    return bool(base) and base.casefold() in spec_text.casefold()


#: Quanto MAIOR o número, mais a aresta é inferida pelo compilador e menos ela
#: representa uma decisão do plano — logo, é a primeira a ser sacrificada para
#: desfazer um ciclo. `explicit_task` (0) só cai se o ciclo for todo explícito.
_PRIORIDADE_ARESTA = {
    "explicit_task": 0,
    "same_file": 1,
    "producer_consumer": 2,
    "group_dependency": 3,
    "migration_wave_dependency": 4,
    "scaffold_dependency": 5,
}


def _achar_ciclo(edges: Mapping[tuple[str, str], Any]) -> list[str]:
    """Um ciclo do grafo, como lista de nós. Vazio quando acíclico.

    DFS iterativa com três cores. A ordenação das listas de adjacência mantém o
    resultado estável entre execuções — um ciclo escolhido ao acaso produziria
    `traceability.json` diferente a cada run.
    """
    adj: dict[str, list[str]] = defaultdict(list)
    for origem, destino in edges:
        adj[origem].append(destino)
    for nos in adj.values():
        nos.sort()

    BRANCO, CINZA, PRETO = 0, 1, 2
    cor: dict[str, int] = {}
    pilha: list[str] = []

    def visitar(no: str) -> list[str]:
        cor[no] = CINZA
        pilha.append(no)
        for vizinho in adj.get(no, ()):
            estado = cor.get(vizinho, BRANCO)
            if estado == CINZA:
                return pilha[pilha.index(vizinho):] + [vizinho]
            if estado == BRANCO:
                achado = visitar(vizinho)
                if achado:
                    return achado
        pilha.pop()
        cor[no] = PRETO
        return []

    sys.setrecursionlimit(max(sys.getrecursionlimit(), 10_000))
    for no in sorted(adj):
        if cor.get(no, BRANCO) == BRANCO:
            ciclo = visitar(no)
            if ciclo:
                return ciclo
    return []


def _quebrar_ciclos(edges: dict[tuple[str, str], dict[str, str]],
                    *, limite: int = 200) -> list[dict[str, str]]:
    """Torna o grafo acíclico removendo arestas inferidas. Devolve as removidas.

    Um ciclo é defeito de dado do plano, não do compilador — e derrubar a
    consolidação inteira por causa dele repetiria o erro que a checagem de
    ownership cometia. A ordenação topológica não existe com ciclo, então
    alguma aresta precisa cair; a escolha é determinística e fica registrada.
    """
    removidas: list[dict[str, str]] = []
    for _ in range(limite):
        ciclo = _achar_ciclo(edges)
        if not ciclo:
            break
        no_ciclo = [
            (chave, edges[chave]) for chave in
            ((ciclo[i], ciclo[i + 1]) for i in range(len(ciclo) - 1))
            if chave in edges
        ]
        if not no_ciclo:
            break
        chave, aresta = max(no_ciclo, key=lambda par: (
            _PRIORIDADE_ARESTA.get(str(par[1].get("reason")), 9),
            par[0]))
        del edges[chave]
        removidas.append({**aresta, "cycle": " → ".join(ciclo)})
        _warn(
            "C007", f"{aresta['from']} → {aresta['to']}",
            f"aresta {aresta.get('reason')} removida para desfazer ciclo: "
            + " → ".join(ciclo),
            "o plano declara dependência circular entre as tasks citadas; "
            "regere os planos das features envolvidas com a ordem correta",
        )
    return removidas


class _PlanoDegradado:
    """Substituto de `dependency_graph.Plan` quando a topologia é impossível.

    Mesma superfície que o resto do compilador consome (`order`, `waves`), com
    ordem determinística por wave → feature → task_id. Existe para que um grafo
    irrecuperável ainda produza `traceability.json`; a perda é a precisão da
    ordem, não as tasks.
    """

    def __init__(self, ordem: list[str]) -> None:
        self.order = ordem
        self.waves = [list(ordem)] if ordem else []
        self.degraded = True


def _plano_degradado(graph_input: Sequence[Mapping[str, Any]]) -> "_PlanoDegradado":
    ordenadas = sorted(graph_input, key=lambda t: (
        int(t.get("migration_wave_order") or 0),
        str(t.get("feature") or ""),
        str(t.get("task_id") or ""),
    ))
    return _PlanoDegradado([str(t["task_id"]) for t in ordenadas])


def _claim_de_task(task: Mapping[str, Any]) -> dict[str, Any]:
    """Reivindicação de ownership no formato do relatório."""
    return {
        "task_id": str(task.get("task_id") or ""),
        "feature": str(task.get("feature") or ""),
        "wave_id": str(task.get("migration_wave_id") or ""),
        "wave_order": int(task.get("migration_wave_order") or 0),
        "action": str(task.get("action") or ""),
        "target_file": str(task.get("target_file") or ""),
        "source": f"specs/{task.get('feature')}/plan-graph.json",
    }


def _dono_determinístico(creates: list[dict[str, Any]],
                         sugerido: str) -> dict[str, Any]:
    """Escolhe o dono da criação. Estável entre execuções.

    Preferência: a feature recomendada pelas specs. Sem recomendação, a menor
    ordem de wave, desempatada por `task_id` — nunca a ordem de iteração do
    dicionário, que varia com o disco.
    """
    if sugerido:
        for task in creates:
            if str(task.get("feature")) == sugerido:
                return task
    return sorted(creates, key=lambda t: (
        int(t.get("migration_wave_order") or 0), str(t.get("task_id"))))[0]


def _spec_texts(specs_dir: Path, features: Sequence[str]) -> dict[str, str]:
    """Texto das specs por feature. Ausência é vazio, nunca erro."""
    textos: dict[str, str] = {}
    for feature in features:
        caminho = specs_dir / feature / "spec.md"
        try:
            textos[feature] = caminho.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            textos[feature] = ""
    return textos


def recommend_owner(target: str, claims: list[dict[str, Any]],
                    spec_texts: Mapping[str, str]) -> tuple[str, str]:
    """Owner sugerido para um `target_file` disputado. `("", motivo)` se indeciso.

    Ordem de decisão, derivada das specs e dos metadados de wave — sem hardcode
    de nome de feature, wave ou entidade:

    1. **A spec cita o arquivo em exatamente uma feature** → essa feature é a
       dona. É a regra que resolve o caso real: a spec de negócio nomeia a
       entidade que a wave entrega, e a spec de foundation não.
    2. **Nenhuma ou várias specs citam** → cai para a menor ordem de wave, que é
       a única ordenação total disponível e é determinística. Marcado como
       indeciso para que o conflito continue visível.
    """
    citando = sorted({
        str(c.get("feature"))
        for c in claims
        if _spec_menciona(spec_texts.get(str(c.get("feature")), ""), target)
    })
    if len(citando) == 1:
        return citando[0], (
            f"a spec de {citando[0]} é a única que declara {target.rsplit('/', 1)[-1]} "
            f"no escopo funcional da wave")
    por_ordem = sorted(
        claims, key=lambda c: (int(c.get("wave_order") or 0), str(c.get("feature"))))
    if por_ordem:
        return "", (
            f"{len(citando) or 'nenhuma'} spec(s) reivindicam o arquivo — owner "
            f"indeterminado; consolidação usa {por_ordem[0].get('feature')} "
            f"(menor ordem de wave) apenas para desempate determinístico")
    return "", "sem reivindicações"


def _render_warnings_banner(project: str) -> str:
    """Bloco humano dos avisos — agrupado por código e por correção.

    A fase segue como executada; este banner é o canal que impede a degradação
    de virar silêncio.
    """
    if not _WARNINGS:
        return ""
    by_code: dict[tuple[str, str], list[str]] = defaultdict(list)
    for item in _WARNINGS:
        by_code[(item["code"], item["fix"])].append(f"{item['owner']}: {item['message']}")
    lines = [
        "",
        "─" * 72,
        f"⚠️  COMPILAÇÃO DEGRADADA — {len(_WARNINGS)} aviso(s) em {project}",
        "   A fase NÃO foi bloqueada: traceability.json e tasks.md foram gerados.",
        "   Os itens abaixo precisam de correção antes da F4 gerar código confiável.",
        "─" * 72,
    ]
    for (code, fix), items in sorted(by_code.items()):
        lines.append(f"\n  [{code}] {len(items)} ocorrência(s)")
        for item in items[:5]:
            lines.append(f"     · {item}")
        if len(items) > 5:
            lines.append(f"     · (+{len(items) - 5} não listadas)")
        lines.append(f"     ↳ CORREÇÃO: {fix}")
    lines.append("")
    lines.append("  Relatório completo: outputs/tobe/speckit/compile-warnings.json")
    lines.append("─" * 72)
    return "\n".join(lines)


def _fatal_payload(args: Any, message: str) -> dict[str, Any]:
    return {
        "status": "warning",
        "message": message,
        "command": args.command,
        "project": args.project,
        "artifacts_written": False,
        "fix": "corrija o defeito acima nos plan-graph.json/task-fragment.json da "
               "feature citada e re-execute a F3S a partir da wave5b",
    }


def _render_fatal_banner(args: Any, message: str) -> str:
    """Defeito que o compilador não sabe degradar.

    Continua sem travar a fase quando `--warn` está ativo, mas o operador
    precisa saber que, desta vez, `traceability.json` e `tasks.md` NÃO foram
    escritos — que era exatamente o que o JSON de uma linha anterior escondia.
    """
    return "\n".join([
        "",
        "─" * 72,
        f"🛑 COMPILAÇÃO NÃO CONCLUÍDA — {args.project}",
        f"   {message}",
        "",
        "   traceability.json e specs/*/tasks.md NÃO foram gerados nesta execução.",
        "   As fases a jusante (compliance, exit gate, F4) verão os artefatos",
        "   da execução anterior, ou nenhum.",
        "",
        "   CORREÇÃO: ajuste o plan-graph.json/task-fragment.json da feature citada",
        "   e re-execute a F3S a partir da wave5b.",
        "   Registro: outputs/tobe/speckit/compile-warnings.json",
        "─" * 72,
    ])


def _persist_fatal(args: Any, message: str) -> None:
    """Grava o motivo da falha para que ela sobreviva ao log do runner."""
    try:
        speckit = _speckit_dir(args.project, REPO_ROOT)
        speckit.mkdir(parents=True, exist_ok=True)
        (speckit / "compile-warnings.json").write_text(json.dumps({
            "project": args.project,
            "generated_at": datetime.datetime.now(
                datetime.timezone.utc).isoformat(timespec="seconds"),
            "status": "failed",
            "artifacts_written": False,
            "total_warnings": len(_WARNINGS) + 1,
            "fatal": {
                "message": message,
                "fix": "corrija o defeito nos plan-graph.json/task-fragment.json da "
                       "feature citada e re-execute a F3S a partir da wave5b",
            },
            "warnings": list(_WARNINGS),
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        # Persistir o aviso nunca pode ser o motivo de uma falha adicional.
        pass


def _speckit_dir(project: str, repo_root: Path) -> Path:
    return repo_root / "projects" / project / "outputs" / "tobe" / "speckit"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CompilerError(f"arquivo ausente: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CompilerError(f"JSON inválido em {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise CompilerError(f"raiz de {path} precisa ser objeto JSON")
    return data


def _normalized_path(raw: Any, *, owner: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise CompilerError(f"{owner}: path vazio")
    path = raw.strip()
    if "\\" in path or path.startswith("/"):
        raise CompilerError(f"{owner}: path não normalizado: {path!r}")
    # Diretório declarado como target: `.../Migrations/`. É como o agente de
    # planning expressa "crie a pasta". Materializar o placeholder é a leitura
    # determinística dessa intenção — travar a compilação inteira por causa da
    # barra final não é.
    if path.endswith("/"):
        original, path = path, path.rstrip("/") + "/" + _DIR_PLACEHOLDER
        _warn(
            "C001", owner,
            f"target declarado como diretório: {original!r} — materializado como {path!r}",
            "no plan.md/plan-graph.json, declare o arquivo placeholder "
            f"(`{_DIR_PLACEHOLDER}`) em vez do diretório",
        )
    pure = PurePosixPath(path)
    if any(part in {"", ".", ".."} for part in pure.parts) or str(pure) != path:
        raise CompilerError(f"{owner}: path não normalizado: {path!r}")
    # `PurePosixPath('.gitkeep').suffix` é '' — dotfiles não têm sufixo. Testar
    # só o sufixo classificava todo arquivo oculto como diretório e reprovava
    # `.gitkeep`, `.editorconfig`, `.gitignore`, `.dockerignore`.
    if not pure.suffix and not pure.name.startswith("."):
        _warn(
            "C002", owner,
            f"target sem extensão, tratado como diretório: {path!r} — "
            f"materializado como {path}/{_DIR_PLACEHOLDER}",
            "declare um arquivo com extensão no plano, ou o placeholder "
            f"`{_DIR_PLACEHOLDER}` explicitamente",
        )
        path = path + "/" + _DIR_PLACEHOLDER
    return path


def _source_refs_or_empty(raw: Any) -> list[dict[str, str]]:
    """Versão tolerante de `_source_refs`, só para comparação/diagnóstico.

    O fragment pode trazer `source_refs` malformado ou ausente; isso deixou de
    ser fatal quando o plano passou a ser a fonte do campo, mas ainda precisa
    ser detectável para entrar na contagem de reconciliação.
    """
    if not isinstance(raw, list):
        return []
    result: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        artifact, anchor = item.get("artifact"), item.get("anchor")
        if isinstance(artifact, str) and artifact and isinstance(anchor, str) and anchor:
            result.append({"artifact": artifact, "anchor": anchor})
    return result


def _list_values(raw: Any, *, owner: str, field: str) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list) or any(not isinstance(item, str) or not item for item in raw):
        raise CompilerError(f"{owner}.{field} precisa ser array de strings não vazias")
    if len(raw) != len(set(raw)):
        raise CompilerError(f"{owner}.{field} contém valores duplicados")
    return list(raw)


def _source_refs(raw: Any, *, owner: str) -> list[dict[str, str]]:
    # Lista vazia é o estado que `speckit_fragment_repair.py` produz quando TODAS
    # as âncoras de uma entrada apontam para seções inexistentes na spec: ele
    # remove as âncoras alucinadas e sobra `[]`. Exigir não-vazio aqui fazia o
    # reparador conserta o fragment para um estado que o compilador rejeitava —
    # duas ferramentas do mesmo pipeline em contradição direta. A rastreabilidade
    # dessa entrada fica degradada e isso é registrado; não é motivo para
    # descartar o grafo inteiro.
    if isinstance(raw, list) and not raw:
        _warn(
            "C003", owner,
            "source_refs vazio — entrada sem rastreabilidade para a spec",
            "corrija as âncoras da spec.md referenciada (ver repair-issues.json) "
            "e regere o plano da feature",
        )
        return []
    if not isinstance(raw, list):
        raise CompilerError(f"{owner}.source_refs precisa ser array não vazio")
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict) or set(item) != {"artifact", "anchor"}:
            raise CompilerError(
                f"{owner}.source_refs[{index}] precisa conter somente artifact e anchor"
            )
        artifact = item.get("artifact")
        anchor = item.get("anchor")
        if not isinstance(artifact, str) or not artifact or not isinstance(anchor, str) or not anchor:
            raise CompilerError(f"{owner}.source_refs[{index}] contém valor vazio")
        key = (artifact, anchor)
        if key in seen:
            raise CompilerError(f"{owner}.source_refs contém referência duplicada: {key!r}")
        seen.add(key)
        result.append({"artifact": artifact, "anchor": anchor})
    return result


def _feature_files(specs_dir: Path, name: str) -> dict[str, Path]:
    return {
        path.parent.name: path
        for path in sorted(specs_dir.glob(f"*/{name}"))
        if path.is_file()
    }


def _extract_scaffold_structure(spec_md_text: str) -> str:
    """Corpo da seção "## Estrutura a gerar" do spec.md de um scaffold.

    Redundância defensiva: 000-scaffold-{stack} não tem plan.md, então spec.md
    é a única fonte da árvore de arquivos esperada. Copiar o corpo para o
    tasks.md garante que o ava-f4s-codegen-agent a veja mesmo que o input do F4
    declarado em ava-pipeline.yaml não inclua spec.md desta feature.
    """
    lines = spec_md_text.splitlines()
    start = next((i for i, line in enumerate(lines)
                 if line.strip() == "## Estrutura a gerar"), None)
    if start is None:
        return ""
    end = next((i for i in range(start + 1, len(lines))
               if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start + 1:end]).strip()


def _manifest_features(speckit: Path, project: str) -> dict[str, dict[str, Any]]:
    path = speckit / "wave-spec-manifest.json"
    manifest = _read_json(path)
    if manifest.get("schema_version") != "1.0.0" or manifest.get("project") != project:
        raise CompilerError(f"{path}: manifesto incompatível com project={project!r}")
    features = manifest.get("features")
    if not isinstance(features, list) or not features:
        raise CompilerError(f"{path}: features[] obrigatório e não vazio")
    result = {str(item.get("feature") or ""): item for item in features}
    if "" in result or len(result) != len(features):
        raise CompilerError(f"{path}: feature vazia ou duplicada")
    return result


# ─── Diagnóstico ─────────────────────────────────────────────────────────────
# `compile_project` para no primeiro erro, o que obriga o operador a descobrir os
# bloqueios um por execução — cada correção revela o próximo. O diagnóstico roda
# as mesmas checagens semânticas SEM parar, e é a mesma função usada para validar
# o plano logo depois da wave4, no produtor, antes que o defeito se propague.

def _finding(code: str, severity: str, feature: str, message: str,
             root_cause: str, fix: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": severity, "feature": feature,
            "message": message, "root_cause": root_cause, "fix": fix, **extra}


def _norm_txt(text: str) -> str:
    """Sem acento, sem caixa, sem espaço duplo — espelha `_norm` do CHK-SK-006."""
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip().lower()


def _slug_txt(text: str) -> str:
    """Slug estilo GitHub — espelha `_slug` do CHK-SK-006."""
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(c for c in text if not unicodedata.combining(c)).lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def _headings_slug(conteudo: str) -> set[str]:
    """Slugs de todos os headings markdown do documento."""
    return {_slug_txt(linha.lstrip("#").strip())
            for linha in conteudo.splitlines() if linha.lstrip().startswith("#")}


def _ancora_resolve(anchor: str, conteudo: str, slugs: set[str]) -> bool:
    """Espelha `_ancora_resolve` do CHK-SK-006 — prosa, slug ou slug parcial.

    Manter as duas implementações idênticas é o que garante que o gate do
    produtor (wave4a) e o check da wave5b deem o mesmo veredicto.
    """
    if _norm_txt(anchor) in _norm_txt(conteudo):
        return True
    alvo = _slug_txt(anchor)
    if alvo in slugs:
        return True
    return any(h == alvo or h.startswith(alvo + "-") for h in slugs)


def _layered_pair(paths: Sequence[str]) -> bool:
    """True quando os produtores são a dupla Service (Application) + Controller (API).

    Arquitetura em camadas produz legitimamente o mesmo `api:` em dois arquivos:
    o serviço implementa a operação, o controller a expõe. Não é contaminação.
    """
    if len(paths) != 2:
        return False
    tem_servico = any("/Services/" in p or "Service." in p for p in paths)
    tem_controller = any("/Controllers/" in p or "Controller." in p for p in paths)
    return tem_servico and tem_controller


def _claims_dos_planos(planos: Mapping[str, Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Reivindicações de `target_file` por arquivo, lidas dos plan-graph.

    Trabalha sobre o PLANO, não sobre os fragments: é onde o ownership nasce, e
    é a única forma de o gate da wave4a acusar o defeito antes de gastar os
    despachos da wave5.
    """
    por_arquivo: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for feature, data in sorted(planos.items()):
        for item in data.get("files") or data.get("arquivos") or []:
            if not isinstance(item, dict):
                continue
            caminho = normalize_target(item.get("path") or item.get("target_file"))
            if not caminho:
                continue
            por_arquivo[caminho].append({
                "task_id": str(item.get("task_id") or item.get("group") or ""),
                "feature": feature,
                "wave_id": str(data.get("migration_wave_id") or ""),
                "wave_order": int(data.get("migration_wave_order") or 0),
                "action": str(item.get("action") or ""),
                "target_file": caminho,
                "source": f"specs/{feature}/plan-graph.json",
            })
    return por_arquivo


def _achados_de_ownership(planos: Mapping[str, Mapping[str, Any]],
                          specs_dir: Path) -> list[dict[str, Any]]:
    """Um achado por conflito de ownership. Enumera TODOS, nunca para no primeiro."""
    achados: list[dict[str, Any]] = []
    if not planos:
        return achados
    spec_texts = _spec_texts(specs_dir, sorted(planos))

    for caminho, claims in sorted(_claims_dos_planos(planos).items()):
        creates = [c for c in claims if c["action"] == "create"]
        updates = [c for c in claims if c["action"] and c["action"] != "create"]

        if len(creates) > 1:
            sugerido, motivo = recommend_owner(caminho, creates, spec_texts)
            codigo = (OWNERSHIP_SCOPE_VIOLATION if sugerido
                      else (OWNERSHIP_CROSS_WAVE
                            if len({c["wave_id"] for c in creates}) > 1
                            else OWNERSHIP_CREATE_CREATE))
            detalhe = "; ".join(
                f"{c['feature']}:{c['task_id'] or '?'} ({c['action']})" for c in creates)
            achados.append(_finding(
                codigo, "warning", creates[0]["feature"],
                f"{caminho}: {len(creates)} declarações action:create — {detalhe}",
                motivo or "mais de uma feature reivindica a criação do mesmo arquivo",
                (f"manter create em {sugerido} e converter as demais para "
                 f"action:update, caso realmente modifiquem o arquivo"
                 if sugerido else
                 "defina nas specs qual wave cria o arquivo; as demais usam "
                 "action:update quando houver modificação real")))
        elif not creates and updates:
            achados.append(_finding(
                OWNERSHIP_UPDATE_NO_CREATE, "warning", updates[0]["feature"],
                f"{caminho}: {len(updates)} update sem nenhum create",
                "nenhuma feature declara a criação deste arquivo",
                "declare action:create na wave que introduz o arquivo"))

        for claim in claims:
            if not claim["action"]:
                achados.append(_finding(
                    OWNERSHIP_INVALID_TARGET, "warning", claim["feature"],
                    f"{caminho}: entrada do plano sem `action`",
                    "o plano não diz se o arquivo é criado ou atualizado",
                    "declare action:create ou action:update na seção 4 do plano"))
    return achados


def diagnose_project(project: str, repo_root: Path | None = None,
                     *, plans_only: bool = False) -> dict[str, Any]:
    """Roda todas as checagens e devolve TODOS os achados, sem parar no primeiro.

    ``plans_only=True`` limita às checagens que dependem apenas dos
    `plan-graph.json` — é o modo usado como gate do produtor, logo após a wave4,
    quando os `task-fragment.json` ainda não existem.
    """
    root = repo_root or REPO_ROOT
    speckit = _speckit_dir(project, root)
    specs_dir = speckit / "specs"
    findings: list[dict[str, Any]] = []

    plans_raw = _feature_files(specs_dir, "plan-graph.json")
    frags_raw = {} if plans_only else _feature_files(specs_dir, "task-fragment.json")
    P: dict[str, dict[str, Any]] = {}
    for feature, path in plans_raw.items():
        try:
            P[feature] = _read_json(path)
        except CompilerError as exc:
            findings.append(_finding(
                "P000", "error", feature, str(exc),
                "plan-graph.json ilegível ou inválido",
                "regere o plano (ava-speckit-planning) desta feature"))
    F: dict[str, dict[str, Any]] = {}
    for feature, path in frags_raw.items():
        try:
            F[feature] = _read_json(path)
        except CompilerError as exc:
            findings.append(_finding(
                "F000", "error", feature, str(exc),
                "task-fragment.json ilegível ou inválido",
                "regere o fragment (ava-speckit-tasks) desta feature"))

    # ── Ownership de target_file entre features ──────────────────────────────
    # Esta é a checagem que faltava no gate da wave4a. Ela existia SÓ no
    # compilador (wave5b), duas waves depois, e lá era fatal. O gate cedo via a
    # mesma duplicação por outro ângulo (P005, sobre `produces`) e a classificava
    # como benigna — dois gates, o mesmo defeito, severidades opostas. Agora o
    # conflito é nomeado onde nasce, com todas as ocorrências enumeradas.
    findings.extend(_achados_de_ownership(P, specs_dir))

    # ── trace_id único em todo o conjunto ────────────────────────────────────
    traces: dict[str, list[str]] = defaultdict(list)
    for feature, data in P.items():
        traces[str(data.get("trace_id"))].append(f"{feature}/plan")
    for feature, data in F.items():
        traces[str(data.get("trace_id"))].append(f"{feature}/fragment")
    if len(traces) > 1:
        detalhe = "; ".join(f"{tid!r}: {', '.join(v[:4])}" for tid, v in traces.items())
        findings.append(_finding(
            "X001", "error", "", f"trace_id divergente — {detalhe}",
            "artefatos do mesmo projeto gravados com trace_id diferentes; "
            "o f4s_scaffold_injector sorteava UUID quando project-config.yaml não "
            "declara trace_id",
            "rode f4s_scaffold_injector novamente (já corrigido para herdar) ou "
            "declare trace_id em context/project-config.yaml"))

    # ── Coerência interna de cada plano ──────────────────────────────────────
    grupos_todos: dict[str, str] = {}
    arquivos_por_grupo: dict[str, int] = defaultdict(int)
    produtores: dict[str, list[tuple[str, str]]] = defaultdict(list)
    consumidores: dict[str, list[tuple[str, str]]] = defaultdict(list)
    raizes: dict[str, set[str]] = defaultdict(set)

    for feature, plan in P.items():
        for grupo in plan.get("groups") or []:
            gid = str(grupo.get("group") or "")
            if gid in grupos_todos:
                findings.append(_finding(
                    "P006", "error", feature,
                    f"grupo {gid} duplicado (também em {grupos_todos[gid]})",
                    "dois planos declaram o mesmo id de grupo",
                    "renomeie o grupo em uma das features"))
            grupos_todos[gid] = feature
        for item in plan.get("files") or []:
            caminho = str(item.get("path") or "")
            arquivos_por_grupo[str(item.get("group") or "")] += 1
            if caminho:
                raizes[feature].add(caminho.split("/")[0])
            for token in item.get("produces") or []:
                produtores[str(token)].append((feature, caminho))
            for token in item.get("consumes") or []:
                consumidores[str(token)].append((feature, caminho))

    for gid, feature in sorted(grupos_todos.items()):
        if not arquivos_por_grupo.get(gid):
            findings.append(_finding(
                "P001", "error", feature,
                f"grupo {gid} declarado sem nenhum arquivo na seção 4",
                "o plano declarou o grupo mas não enumerou os arquivos dele; o "
                "agente de tasks fica sem ownership e inventa os arquivos",
                f"regere o plano (ava-speckit-planning) de {feature}"))

    for token, quem in sorted(consumidores.items()):
        if token not in produtores:
            origem = ", ".join(f"{f}:{p.split('/')[-1]}" for f, p in quem[:3])
            findings.append(_finding(
                "P002", "error", quem[0][0],
                f"consume {token!r} sem nenhum produtor (consumido por {origem})",
                "o plano declara um consumo cujo produtor não está na seção 4 — "
                "normalmente porque o arquivo produtor foi omitido do plano",
                f"regere o plano de {quem[0][0]} incluindo o arquivo que produz "
                f"{token!r}, ou remova o consumo"))

    for token, quem in sorted(produtores.items()):
        if len(quem) < 2 or token not in consumidores:
            continue
        caminhos = [p for _f, p in quem]
        if _layered_pair(caminhos):
            findings.append(_finding(
                "P003", "warning", quem[0][0],
                f"{token!r} produzido por Service e Controller",
                "arquitetura em camadas: o serviço implementa e o controller "
                "expõe a mesma operação — ambos declaram produce",
                "aceitável; o compilador cria aresta para os dois produtores"))
            continue
        esperado = token.split(":", 1)[-1].lower()
        contaminados = [(f, p) for f, p in quem
                        if PurePosixPath(p).stem.lower() != esperado]
        legitimos = [(f, p) for f, p in quem
                     if PurePosixPath(p).stem.lower() == esperado]
        if legitimos and contaminados:
            lista = ", ".join(f"{f}:{PurePosixPath(p).name}" for f, p in contaminados)
            findings.append(_finding(
                "P004", "error", contaminados[0][0],
                f"{token!r} também declarado por {lista}, que não é o arquivo do contrato",
                "lista `produces` contaminada: o agente de planning copiou o token "
                "para um arquivo vizinho",
                f"remova {token!r} do produces de {lista}"))
        else:
            lista = ", ".join(f"{f}:{PurePosixPath(p).name}" for f, p in quem)
            findings.append(_finding(
                "P005", "warning", quem[0][0],
                f"{token!r} com {len(quem)} produtores: {lista}",
                "mais de um arquivo declara produzir o mesmo token e nenhum "
                "corresponde ao nome do contrato",
                "revise os produces; o compilador criará aresta para todos"))

    # ── Âncoras resolvem no arquivo-fonte ────────────────────────────────────
    # Mesma verificação do CHK-SK-006, antecipada para o gate do produtor: lá ela
    # só roda na wave5b, depois de todos os despachos de tasks. Aqui reprova o
    # plano que a inventou, sem gastar inferência.
    conteudo_cache: dict[str, str | None] = {}
    slug_cache: dict[str, set[str]] = {}
    ancoras_quebradas: dict[str, list[str]] = defaultdict(list)
    proj_dir = root / "projects" / project
    for feature, plan in P.items():
        for item in plan.get("files") or []:
            for ref in item.get("source_refs") or []:
                if not isinstance(ref, dict):
                    continue
                rel = str(ref.get("artifact") or "")
                anchor = str(ref.get("anchor") or "")
                if not rel or not anchor:
                    ancoras_quebradas[feature].append(
                        f"{PurePosixPath(str(item.get('path'))).name}: ref sem artifact/anchor")
                    continue
                if rel not in conteudo_cache:
                    alvo = proj_dir / rel
                    if not alvo.is_file():
                        alvo = root / rel
                    texto = alvo.read_text(encoding="utf-8", errors="replace") \
                        if alvo.is_file() else None
                    conteudo_cache[rel] = texto
                    slug_cache[rel] = _headings_slug(texto or "")
                texto = conteudo_cache[rel]
                if texto is None:
                    ancoras_quebradas[feature].append(f"{rel} (arquivo inexistente)")
                elif not _ancora_resolve(anchor, texto, slug_cache[rel]):
                    ancoras_quebradas[feature].append(f"{anchor!r} em {PurePosixPath(rel).name}")
    for feature, quebradas in sorted(ancoras_quebradas.items()):
        unicas = sorted(set(quebradas))
        findings.append(_finding(
            "P010", "error", feature,
            f"{len(quebradas)} referência(s) com âncora que não existe na fonte "
            f"({len(unicas)} distinta(s)): " + ", ".join(unicas[:4]),
            "o plano inventou nomes de âncora em vez de citar um heading real do "
            "artefato-fonte ou um id existente (BR-*, TC-*, DEC-*, operationId)",
            f"regere o plano de {feature} usando o texto literal do heading, seu "
            f"slug, ou um id que exista no arquivo citado",
            anchors=unicas))

    raizes_distintas = {feature: sorted(r) for feature, r in raizes.items() if r}
    conjuntos = {tuple(v) for v in raizes_distintas.values()}
    if len(conjuntos) > 1:
        detalhe = "; ".join(f"{f}={'/'.join(v)}" for f, v in sorted(raizes_distintas.items()))
        findings.append(_finding(
            "P009", "warning", "",
            f"raiz de caminho inconsistente entre features — {detalhe}",
            "o mesmo agente de planning usou layouts diferentes por feature",
            "padronize a raiz nos planos; a F4 gera em diretórios distintos por wave"))

    # ── Plano × fragment ─────────────────────────────────────────────────────
    if not plans_only:
        todas_tasks: dict[str, str] = {}
        for feature, frag in F.items():
            plan = P.get(feature)
            if plan is None:
                findings.append(_finding(
                    "F008", "error", feature, "fragment sem plan-graph correspondente",
                    "a feature tem task-fragment.json mas não tem plan-graph.json",
                    f"regere o plano (ava-speckit-planning) de {feature}"))
                continue
            planejados = {str(f.get("path")) for f in plan.get("files") or []}
            cobertos: set[str] = set()
            fora: list[str] = []
            for entry in frag.get("entries") or []:
                tid = str(entry.get("task_id") or "")
                alvo = str(entry.get("target_file") or "")
                if tid in todas_tasks:
                    findings.append(_finding(
                        "F004", "error", feature,
                        f"task_id {tid} duplicado (também em {todas_tasks[tid]})",
                        "dois fragments usam o mesmo task_id",
                        "regere um dos fragments com ids únicos"))
                todas_tasks[tid] = feature
                if alvo in planejados:
                    cobertos.add(alvo)
                else:
                    fora.append(alvo)
            if fora:
                findings.append(_finding(
                    "F001", "error", feature,
                    f"{len(fora)} arquivo(s) do fragment fora do plano, ex.: "
                    + ", ".join(PurePosixPath(x).name for x in fora[:3]),
                    "o fragment criou tasks para arquivos que o plano não declara — "
                    "geralmente porque o plano omitiu esses arquivos (ver P001/P002)",
                    f"regere o plano de {feature} incluindo-os, ou o fragment sem eles",
                    files=fora))
            faltando = sorted(planejados - cobertos)
            if faltando:
                findings.append(_finding(
                    "F002", "error", feature,
                    f"{len(faltando)} arquivo(s) do plano sem task, ex.: "
                    + ", ".join(PurePosixPath(x).name for x in faltando[:3]),
                    "o agente de tasks não cobriu todos os arquivos do plano — "
                    "subcobertura, tipicamente por teto de tokens de saída",
                    f"regere o fragment (ava-speckit-tasks) de {feature}",
                    files=faltando))
            for campo in ("spec_id", "plan_id", "migration_wave_id", "migration_wave_order"):
                if frag.get(campo) != plan.get(campo):
                    findings.append(_finding(
                        "F006", "error", feature,
                        f"{campo} diverge: plan={plan.get(campo)!r}, "
                        f"fragment={frag.get(campo)!r}",
                        "cabeçalhos do plano e do fragment fora de sincronia",
                        f"regere o fragment de {feature}"))
        pendentes = sorted({
            x for frag in F.values() for e in frag.get("entries") or []
            for x in (e.get("depends_on") or []) if x not in todas_tasks
        })
        if pendentes:
            findings.append(_finding(
                "F005", "error", "",
                f"{len(pendentes)} depends_on apontam para task inexistente: "
                + ", ".join(pendentes[:5]),
                "referência de dependência a task_id que nenhum fragment declara",
                "regere o fragment que declara essas dependências"))

    erros = [f for f in findings if f["severity"] == "error"]
    return {
        "project": project,
        "mode": "plans_only" if plans_only else "full",
        "features": sorted(set(P) | set(F)),
        "total_findings": len(findings),
        "errors": len(erros),
        "warnings": len(findings) - len(erros),
        "ok": not erros,
        "findings": findings,
    }


def render_diagnosis(report: Mapping[str, Any]) -> str:
    """Relatório legível, agrupado por feature e ordenado por severidade."""
    linhas: list[str] = []
    modo = "planos" if report.get("mode") == "plans_only" else "planos + fragments"
    linhas.append(f"Diagnóstico SpecKit — {report['project']} ({modo})")
    linhas.append(f"{report['errors']} erro(s), {report['warnings']} aviso(s) "
                  f"em {len(report['features'])} feature(s)")
    if not report["findings"]:
        linhas.append("\n  Nenhum problema encontrado.")
        return "\n".join(linhas)
    por_feature: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in report["findings"]:
        por_feature[item["feature"] or "(global)"].append(item)
    for feature in sorted(por_feature):
        linhas.append(f"\n── {feature}")
        for item in sorted(por_feature[feature],
                           key=lambda i: (i["severity"] != "error", i["code"])):
            marca = "ERRO " if item["severity"] == "error" else "aviso"
            linhas.append(f"  [{marca} {item['code']}] {item['message']}")
            linhas.append(f"           causa: {item['root_cause']}")
            linhas.append(f"          correção: {item['fix']}")
    return "\n".join(linhas)


def compile_project(project: str, repo_root: Path | None = None,
                    *, write: bool = True) -> dict[str, Any]:
    """Consolida os fragments das features e grava os artefatos derivados.

    Best-effort por contrato: nunca aborta por inconsistencia semantica.
    """
    _reset_run_state()
    root = repo_root or REPO_ROOT
    speckit = _speckit_dir(project, root)
    specs_dir = speckit / "specs"
    manifest = _manifest_features(speckit, project)
    plans = _feature_files(specs_dir, "plan-graph.json")
    fragments = _feature_files(specs_dir, "task-fragment.json")
    if not plans or not fragments:
        raise CompilerError(
            f"plan-graph.json e task-fragment.json são obrigatórios em {specs_dir}/*/"
        )
    if set(plans) != set(fragments):
        only_plans = sorted(set(plans) - set(fragments))
        only_fragments = sorted(set(fragments) - set(plans))
        raise CompilerError(
            f"features incompletas: sem fragment={only_plans}, sem plan-graph={only_fragments}"
        )
    expected_codegen = {feature for feature, item in manifest.items() if item.get("codegen")}
    plan_features = set(plans)
    # Scaffolds sintéticos da F4S (000-scaffold-<stack>) são features transversais
    # de W0 injetadas pelo f4s_scaffold_injector.py; não constam do manifesto de
    # waves de domínio, mas devem ser compilados como dependência inicial de cada
    # target_stack.
    scaffold_features = {feature for feature in plan_features
                         if feature.startswith("000-scaffold-")}
    domain_features = plan_features - scaffold_features
    if domain_features != expected_codegen:
        missing = sorted(expected_codegen - domain_features)
        extra = sorted(domain_features - expected_codegen)
        raise CompilerError(f"features de codegen divergem do manifesto: faltam={missing}, sobram={extra}")

    groups: dict[str, dict[str, Any]] = {}
    plan_files: dict[tuple[str, str], dict[str, Any]] = {}
    plan_meta: dict[str, dict[str, Any]] = {}
    trace_ids: set[str] = set()

    for feature, path in plans.items():
        plan = _read_json(path)
        _validate_header(plan, project, feature, path)
        declared = manifest.get(feature)
        if declared is None:
            # Scaffolds sintéticos (000-scaffold-<stack>) não constam do manifesto.
            if not feature.startswith("000-scaffold-"):
                raise CompilerError(f"{feature}: feature ausente do manifesto")
        elif plan.get("migration_wave_id") != declared.get("wave_id") \
                or plan.get("migration_wave_order") != declared.get("migration_wave_order"):
            raise CompilerError(f"{feature}: identidade da migration wave diverge do manifesto")
        trace_ids.add(str(plan.get("trace_id", "")))
        plan_meta[feature] = plan
        for group in plan.get("groups") or []:
            group_id = str(group.get("group") or "")
            if not group_id:
                raise CompilerError(f"{path}: grupo sem id")
            if group_id in groups:
                raise CompilerError(f"grupo duplicado entre planos: {group_id}")
            groups[group_id] = {**group, "feature": feature}
        for item in plan.get("files") or []:
            normalized = _normalized_path(item.get("path"), owner=f"{feature}.files")
            key = (feature, normalized)
            if key in plan_files:
                raise CompilerError(f"arquivo repetido no plano {feature}: {normalized}")
            plan_files[key] = {**item, "path": normalized}

    # ── Coerência interna do plano ───────────────────────────────────────────
    # Grupo declarado na seção 3 sem nenhum arquivo na seção 4 é plano
    # incompleto: o agente de tasks fica sem ownership para aquele grupo e
    # inevitavelmente inventa os arquivos, o que só aparecia muito depois como
    # "target_file fora da seção 4". Falhar aqui aponta o produtor certo.
    files_by_group: dict[str, int] = defaultdict(int)
    for (_feature, _path), item in plan_files.items():
        files_by_group[str(item.get("group") or "")] += 1
    empty_groups = sorted(gid for gid in groups if not files_by_group.get(gid))
    if empty_groups:
        # Grupo sem arquivo e plano incompleto — defeito SEMANTICO, recuperavel.
        # Descartar a consolidacao inteira por causa dele fazia uma feature vazia
        # (ou uma wave que legitimamente nao gera codigo) derrubar as demais.
        culpados = sorted({groups[gid]["feature"] for gid in empty_groups})
        _warn("C011", ", ".join(empty_groups),
              f"grupo(s) declarado(s) sem arquivos na secao 4 do plano",
              f"regere o plano (ava-speckit-planning) de: {', '.join(culpados)}")
        for gid in empty_groups:
            groups.pop(gid, None)

    try:
        dependency_graph.analyze(
            [{"group": group_id, "depends_on": group.get("depends_on") or []}
             for group_id, group in groups.items()],
            id_field="group",
        )
    except dependency_graph.DependencyGraphError as exc:
        raise CompilerError(f"grafo de grupos inválido: {exc}") from exc

    tasks: list[dict[str, Any]] = []
    # Campos de arquivo que o fragment recopiou divergindo do plano. O plano
    # vence, mas a divergência é contabilizada e devolvida no resultado — nada
    # é reconciliado em silêncio.
    reconciled: list[str] = []
    # Tokens com mais de um produtor — não fatal, mas devolvido no resultado.
    multi_producer: list[str] = []
    # Consumos sem produtor: aresta não criada, task segue no grafo. Devolvido
    # no resultado e em compile-warnings.json para correção posterior.
    orphan_consumes: list[str] = []
    for feature, path in fragments.items():
        fragment = _read_json(path)
        _validate_header(fragment, project, feature, path)
        trace_ids.add(str(fragment.get("trace_id", "")))
        plan = plan_meta[feature]
        if fragment.get("spec_id") != plan.get("spec_id") \
                or fragment.get("plan_id") != plan.get("plan_id"):
            raise CompilerError(f"{feature}: spec_id/plan_id divergem entre plan e fragment")
        for field in ("migration_wave_id", "migration_wave_order"):
            if fragment.get(field) != plan.get(field):
                raise CompilerError(f"{feature}: {field} diverge entre plan e fragment")
        for raw in fragment.get("entries") or []:
            task_id = str(raw.get("task_id") or "")
            _validate_task(raw, task_id or feature)
            target = _normalized_path(raw.get("target_file"), owner=task_id or feature)
            group_id = str(raw.get("group") or "")
            if group_id not in groups:
                raise CompilerError(f"{task_id}: grupo desconhecido {group_id!r}")
            if groups[group_id]["feature"] != feature:
                raise CompilerError(f"{task_id}: grupo {group_id} pertence a outra feature")
            if raw.get("target_stack") != groups[group_id].get("target_stack"):
                raise CompilerError(f"{task_id}: target_stack diverge do grupo {group_id}")
            planned = plan_files.get((feature, target))
            if not planned:
                fora = sorted({
                    str(e.get("target_file"))
                    for e in fragment.get("entries") or []
                    if (feature, str(e.get("target_file") or "")) not in plan_files
                })
                raise CompilerError(
                    f"{task_id}: target_file fora da seção 4 do plano: {target}. "
                    f"{len(fora)} arquivo(s) do fragment não constam do plano de {feature} — "
                    f"o plano não declara ownership deles. Regere o plano "
                    f"(ava-speckit-planning) ou o fragment (ava-speckit-tasks) de {feature}"
                )
            # `group` continua erro duro: define escalonamento e a cobertura de
            # grupos verificada no fim. `action` é campo de arquivo — reconciliado.
            if group_id != planned.get("group"):
                raise CompilerError(
                    f"{task_id}: group diverge do ownership de {target}: "
                    f"fragment={group_id!r}, plan={planned.get('group')!r}")
            if raw.get("action") != planned.get("action"):
                reconciled.append(f"{task_id}.action ({target})")
            # ── Campos de arquivo: o plano é a autoridade ────────────────────
            # `planning-agent.md` declara o plan-graph como "autoridade para
            # grupos, ownership de arquivos, produces, consumes e dependências",
            # e o fragment apenas os RECOPIA. Exigir igualdade dessa cópia era
            # pedir que a LLM reproduzisse verbatim uma tabela de 90-150 linhas
            # num turno com teto de saída — o mesmo modo de falha da ISSUE-004.
            # Agora esses campos são LIDOS DO PLANO; o que o fragment trouxer é
            # reconciliado e contabilizado, nunca silenciado.
            task_refs = _source_refs(planned.get("source_refs"), owner=target)
            plan_field_values: dict[str, Any] = {
                "task_type":   planned.get("task_type"),
                "action":      planned.get("action"),
                "source_refs": task_refs,
                # `work_kind` e os ids do protótipo seguem a mesma regra dos
                # demais campos de arquivo: o plano é a autoridade, o fragment
                # recopia e a divergência é contabilizada, nunca silenciada.
                "work_kind": (planned.get("work_kind") or raw.get("work_kind") or ""),
                "prototype_refs": _source_refs_or_empty(planned.get("prototype_refs"))
                or _source_refs_or_empty(raw.get("prototype_refs")),
            }
            for field in PLAN_OWNED_LIST_FIELDS:
                values = _list_values(planned.get(field), owner=target, field=field)
                if field in ("produces", "consumes"):
                    values = sorted({normalize_token(item) for item in values})
                elif not values:
                    # Campo novo ausente no plano legado: o fragment ainda pode
                    # trazê-lo, e descartá-lo perderia rastreabilidade real.
                    values = _list_values(raw.get(field), owner=task_id, field=field)
                plan_field_values[field] = values
            if raw.get("task_type") != planned.get("task_type"):
                reconciled.append(f"{task_id}.task_type ({target})")
            if _source_refs_or_empty(raw.get("source_refs")) != task_refs:
                reconciled.append(f"{task_id}.source_refs ({target})")
            for field in PLAN_OWNED_LIST_FIELDS:
                fragment_values = _list_values(raw.get(field), owner=task_id, field=field)
                if field in ("produces", "consumes"):
                    fragment_values = [normalize_token(item) for item in fragment_values]
                if set(fragment_values) != set(plan_field_values[field]):
                    reconciled.append(f"{task_id}.{field} ({target})")
            # `screen_id` singular do schema 3.0.0 alimenta `screen_ids` quando o
            # plano legado não declara a lista — é a mesma informação, e perdê-la
            # deixaria PROTOTYPE-SCREEN-COVERAGE cego em projeto migrado.
            if raw.get("screen_id") and not plan_field_values["screen_ids"]:
                plan_field_values["screen_ids"] = [str(raw["screen_id"]).upper()]

            tasks.append({
                **raw,
                "task_id": task_id,
                "feature": feature,
                "verify_profile": (raw.get("verify_profile")
                                   or planned.get("verify_profile")
                                   or groups[group_id].get("verify_profile") or ""),
                "spec_id": fragment.get("spec_id"),
                "plan_id": fragment.get("plan_id"),
                "migration_wave_id": fragment.get("migration_wave_id"),
                "migration_wave_order": fragment.get("migration_wave_order"),
                "target_file": target,
                **plan_field_values,
                "depends_on": _list_values(raw.get("depends_on"), owner=task_id,
                                            field="depends_on"),
                "depends_on_groups": _list_values(raw.get("depends_on_groups"), owner=task_id,
                                                   field="depends_on_groups"),
            })

    if not tasks:
        # Lista legitimamente vazia NÃO é falha técnica: o artefato é gravado,
        # válido, com motivo explícito e `recovery_placeholder: false`. Levantar
        # aqui fazia o reconciler cobrir o buraco com placeholder, que é
        # indistinguível de "o produtor nunca rodou".
        _warn("C010", "fragments",
              "nenhuma task encontrada nos fragments — traceability gravado vazio",
              "verifique se ava-speckit-tasks rodou para as features de codegen")
        vazio = _traceability_vazio(
            project, sorted(trace_ids)[0] if trace_ids else "",
            "nenhuma task declarada nos fragments das features de codegen")
        if write:
            _write_atomic(speckit / "traceability.json",
                          json.dumps(vazio, ensure_ascii=False, indent=2) + "\n")
            progresso_vazio = sync_task_progress(project, vazio, repo_root=root)
            _write_atomic(speckit / "compile-warnings.json",
                          json.dumps(_warnings_report(project, vazio, progresso_vazio),
                                     ensure_ascii=False, indent=2) + "\n")
        return vazio

    covered_files = {(task["feature"], task["target_file"]) for task in tasks}
    uncovered_files = sorted(set(plan_files) - covered_files)
    if uncovered_files:
        rendered = ", ".join(f"{feature}:{path}" for feature, path in uncovered_files[:8])
        por_feature = Counter(feature for feature, _ in uncovered_files)
        resumo = ", ".join(f"{feat}={qtd}" for feat, qtd in sorted(por_feature.items()))
        # Cobertura incompleta e lacuna de qualidade, nao falha tecnica: as
        # tasks que EXISTEM continuam validas e sao consolidadas.
        _warn("C012", f"{len(uncovered_files)} arquivo(s)",
              f"arquivos do plano sem task: {rendered}"
              f"{'…' if len(uncovered_files) > 8 else ''} (por feature: {resumo})",
              "regere o fragment (ava-speckit-tasks) das features listadas")
    covered_groups = {task["group"] for task in tasks}
    uncovered_groups = sorted(set(groups) - covered_groups)
    if uncovered_groups:
        _warn("C013", ", ".join(uncovered_groups),
              "grupo(s) do plano sem nenhuma task",
              "regere o fragment (ava-speckit-tasks) das features desses grupos")

    if len(trace_ids) != 1:
        _warn("C014", "trace_id",
              f"trace_id divergente entre fragments e planos: {sorted(trace_ids)!r}",
              "unifique o trace_id em project-config.yaml e regere os planos")
        trace_ids = {sorted(trace_ids)[0]} if trace_ids else {""}

    task_by_id = {task["task_id"]: task for task in tasks}
    if len(task_by_id) != len(tasks):
        # Mensagem acionável: o agente de tasks usa prefixos não escopados por
        # feature para trabalho transversal (T-TST-*, T-HOST-*), então duas waves
        # geram a mesma sequência. Sem os ids e as features, o operador não sabia
        # nem quantos nem onde.
        onde: dict[str, list[str]] = defaultdict(list)
        for task in tasks:
            onde[task["task_id"]].append(task["feature"])
        dup = {tid: feats for tid, feats in onde.items() if len(feats) > 1}
        amostra = ", ".join(f"{tid} ({'/'.join(sorted(set(f)))})"
                            for tid, f in sorted(dup.items())[:5])
        raise CompilerError(
            f"task_id duplicado entre fragments ({len(dup)}): {amostra}"
            f"{'…' if len(dup) > 5 else ''}. O task_id é a chave do ledger e do "
            f"grafo global — precisa ser único no conjunto. Reparo determinístico: "
            f"`speckit_plan_repair.py -p {project} --mode duplicate-task-ids --apply`"
        )

    edges: dict[tuple[str, str], dict[str, str]] = {}

    def add_edge(predecessor: str, successor: str, reason: str, source: str) -> None:
        key = (predecessor, successor)
        edges.setdefault(key, {
            "from": predecessor,
            "to": successor,
            "reason": reason,
            "source": source,
        })

    for task in tasks:
        for predecessor in task["depends_on"]:
            add_edge(predecessor, task["task_id"], "explicit_task", task["feature"])

    producers: dict[str, list[str]] = defaultdict(list)
    for task in tasks:
        for token in task["produces"]:
            producers[token].append(task["task_id"])
    for task in tasks:
        for token in task["consumes"]:
            candidates = producers.get(token, [])
            if not candidates:
                # Consumo órfão: o plano declara o consumo e omite quem produz.
                # Sem produtor não há aresta a criar — a ordenação continua
                # válida, só menos restrita. Travar aqui custava a F3S inteira
                # por um arquivo esquecido na seção 4 de um único plano.
                _warn(
                    "C004", task["task_id"],
                    f"consume {token!r} sem nenhum produtor — aresta não criada",
                    f"regere o plano de {task['feature']} incluindo o arquivo que "
                    f"produz {token!r}, ou remova o consumo",
                )
                orphan_consumes.append(f"{task['task_id']} → {token}")
                continue
            # Vários produtores é legítimo em arquitetura em camadas: o serviço
            # implementa a operação e o controller a expõe, e ambos declaram
            # produce. Exigir exatamente 1 reprovava esse desenho. A ordenação
            # segura é depender de TODOS — nunca menos. Contaminação real de
            # `produces` é reportada por `diagnose` (P004) e barrada no gate do
            # plano, que é onde o defeito nasce.
            for candidate in candidates:
                add_edge(candidate, task["task_id"], "producer_consumer", token)
            if len(candidates) > 1:
                multi_producer.append(f"{token} ({len(candidates)} produtores)")

    by_file: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for task in tasks:
        by_file[task["target_file"]].append(task)
    # Ownership: TODOS os conflitos são enumerados e nenhum aborta.
    # O `raise` que existia aqui descartava as tasks íntegras de todas as
    # features por causa do primeiro arquivo disputado. Agora o conflito é
    # registrado, um owner determinístico é escolhido só para a consolidação, e
    # as entries afetadas carregam `ownership_status`/`ownership_claims` para
    # que a decisão não esconda o defeito.
    spec_texts = _spec_texts(specs_dir, sorted(fragments))
    for target, owners in sorted(by_file.items()):
        creates = [task for task in owners if task.get("action") == "create"]
        updates = [task for task in owners if task.get("action") != "create"]

        if len(creates) > 1:
            claims = [_claim_de_task(task) for task in creates]
            features = {c["feature"] for c in claims}
            sugerido, motivo = recommend_owner(target, claims, spec_texts)
            kind = (OWNERSHIP_CROSS_WAVE
                    if len({c.get("wave_id") for c in claims}) > 1
                    else OWNERSHIP_CREATE_CREATE)
            if sugerido:
                # A spec resolveu quem é o dono: quem não é dono está fora do
                # escopo declarado da própria wave.
                kind = OWNERSHIP_SCOPE_VIOLATION
            _record_conflict(
                kind, target, claims,
                recommended_owner=sugerido, reason=motivo,
                resolution=(
                    f"manter create em {sugerido} e converter as demais para "
                    f"action:update, se a wave realmente modificar o arquivo"
                    if sugerido else
                    "defina nas specs qual wave cria o arquivo e converta as "
                    "demais para action:update quando houver modificação real"),
            )
            _warn(
                "C005", target,
                f"{len(creates)} create para o mesmo target_file "
                f"({', '.join(sorted(features))})",
                f"regere o plano das features citadas mantendo create em "
                f"{sugerido or 'uma única wave'}",
            )
            # Consolidação: um único dono de criação. Os demais viram update na
            # ordenação — o arquivo não deixa de ter task, e nenhuma task some.
            dono = _dono_determinístico(creates, sugerido)
            for task in creates:
                task["ownership_status"] = ("OWNER" if task is dono else "CONFLICT")
                task["ownership_claims"] = claims
                task["ownership_conflict"] = kind
                if task is not dono:
                    task["action_original"] = task.get("action")
                    task["action"] = "update"
        elif not creates and updates:
            claims = [_claim_de_task(task) for task in updates]
            _record_conflict(
                OWNERSHIP_UPDATE_NO_CREATE, target, claims,
                reason="nenhuma wave declara create para este arquivo",
                resolution="declare create na wave que introduz o arquivo")
            _warn("C006", target,
                  f"{len(updates)} update sem nenhum create para o target_file",
                  "declare create na wave que introduz o arquivo")
            for task in updates:
                task["ownership_status"] = "CONFLICT"
                task["ownership_conflict"] = OWNERSHIP_UPDATE_NO_CREATE
        elif len(updates) > 1:
            # Vários updates são legítimos (waves sucessivas endurecem o mesmo
            # arquivo). Registrado como informação, sem aviso no banner.
            _record_conflict(
                OWNERSHIP_DUPLICATE_UPDATE, target,
                [_claim_de_task(task) for task in updates],
                recommended_owner=(creates[0]["feature"] if creates else ""),
                reason="múltiplos update sobre o mesmo arquivo — permitido",
                resolution="nenhuma ação necessária")
        # Order by migration wave first so that later-wave updates of the same
        # file always come after earlier-wave creates/updates. Within the same
        # wave, create actions precede updates, and task_id breaks ties.
        ordered = sorted(owners, key=lambda task: (
            int(task.get("migration_wave_order") or 0),
            0 if task.get("action") == "create" else 1,
            task["task_id"],
        ))
        for predecessor, successor in zip(ordered, ordered[1:]):
            add_edge(predecessor["task_id"], successor["task_id"], "same_file", target)

    _add_group_edges(tasks, groups, edges, add_edge)
    _add_migration_wave_edges(tasks, manifest, edges, add_edge)
    _add_scaffold_edges(tasks, edges, add_edge)

    # Comando de verificação: perfil canônico resolvido pela stack, ANTES de
    # qualquer coisa ser gravada em traceability.json (que é imutável).
    incompatible_verify = _normalize_verify(tasks, project, root)
    # Validações do elo frontend ↔ backend. Rodam com o grafo já montado porque
    # E2E-DEPENDENCIES precisa das arestas, e depois das arestas porque nenhuma
    # delas pode alterar o grafo — são achados, não correções.
    prototype_doc = prototype_manifest.load_manifest(project, root)
    integration_findings = _integration_findings(tasks, edges, manifest, prototype_doc)
    for finding in integration_findings:
        if finding["severity"] == "error":
            _warn(finding["check_id"], ", ".join(finding["affected_items"][:3]) or "-",
                  finding["message"], finding["recommended_action"])

    # Ciclo é defeito de dado recuperável: desfaz-se removendo a aresta mais
    # inferida, com registro. Antes, `dependency_graph.analyze` levantava e a
    # consolidação inteira caía — o mesmo modo de falha do ownership.
    broken_edges = _quebrar_ciclos(edges)

    graph_input = []
    predecessors: dict[str, list[str]] = defaultdict(list)
    for predecessor, successor in edges:
        predecessors[successor].append(predecessor)
    conhecidos = {task["task_id"] for task in tasks}
    for task in tasks:
        graph_input.append({
            **task,
            # Predecessor fora do conjunto é referência quebrada do plano, não
            # motivo para não ordenar o que existe.
            "depends_on": sorted(p for p in predecessors[task["task_id"]]
                                 if p in conhecidos),
        })
    try:
        plan = dependency_graph.analyze(graph_input)
    except dependency_graph.DependencyGraphError as exc:
        # Último recurso: ordem determinística por wave/feature/task_id. Perde a
        # precisão topológica, mas entrega as tasks — que é o contrato da fase.
        _warn("C008", "grafo global",
              f"ordenação topológica indisponível ({exc}); usando ordem "
              f"determinística por wave/feature/task_id",
              "corrija as dependências declaradas nos planos das features citadas")
        plan = _plano_degradado(graph_input)

    compiled_by_id = {task["task_id"]: task for task in graph_input}
    entries = [
        _compiled_entry(compiled_by_id[task_id], plan, compiled_by_id)
        for task_id in plan.order
    ]
    ordered_edges = sorted(edges.values(), key=lambda edge: (edge["to"], edge["from"]))
    checksum_source = [
        {
            "task_id": entry["task_id"],
            "task_type": entry["task_type"],
            "migration_wave_id": entry["migration_wave_id"],
            "migration_wave_order": entry["migration_wave_order"],
            "source_refs": entry["source_refs"],
            "depends_on": entry["depends_on"],
            "backend_dependencies": entry["backend_dependencies"],
        }
        for entry in entries
    ]
    graph_checksum = hashlib.sha256(json.dumps(
        checksum_source, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()

    output = {
        "schema_version": "4.0.0",
        "project": project,
        "trace_id": next(iter(trace_ids)),
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "constitution": "outputs/tobe/speckit/constitution.md",
        # `INCOMPLETE` fica reservado à falha TÉCNICA. Warning de planejamento
        # não descaracteriza o artefato: ele foi produzido, com ressalvas
        # registradas. Era a confusão entre os dois que fazia o reconciler
        # trocar um artefato bom por placeholder.
        "status": "COMPLETE_WITH_WARNINGS" if (_WARNINGS or _CONFLICTS) else "COMPLETE",
        "recovery_placeholder": False,
        "artifacts_written": bool(write),
        "validation_summary": {
            "warnings": len(_WARNINGS),
            "errors": 0,
            "ownership_conflicts": len(_CONFLICTS),
            "broken_edges": len(broken_edges),
            "degraded_order": bool(getattr(plan, "degraded", False)),
            "integration_errors": sum(1 for item in integration_findings
                                      if item["severity"] == "error"),
            "integration_warnings": sum(1 for item in integration_findings
                                        if item["severity"] != "error"),
            "verify_commands_replaced": len(incompatible_verify),
        },
        "total_tasks": len(entries),
        "reconciled_from_plan": sorted(reconciled),
        # Vínculo ao protótipo: sem isto, PROTOTYPE-CHECKSUM-CONSISTENCY não tem
        # com o que comparar, e um protótipo regerado depois do planejamento
        # passa despercebido — todas as âncoras apontariam para conteúdo que
        # mudou, e a rastreabilidade mentiria sem nenhum sinal.
        "prototype_checksum": ((prototype_doc or {}).get("prototype") or {}).get(
            "checksum") if prototype_doc else None,
        "integration_findings": integration_findings,
        "incompatible_verify_commands": incompatible_verify,
        "multi_producer_tokens": sorted(set(multi_producer)),
        "orphan_consumes": sorted(set(orphan_consumes)),
        "ownership_conflicts": list(_CONFLICTS),
        "broken_edges": broken_edges,
        "warnings": list(_WARNINGS),
        "graph_checksum": graph_checksum,
        "dependency_edges": ordered_edges,
        "execution_order": list(plan.order),
        "execution_waves": [list(wave) for wave in plan.waves],
        "entries": entries,
    }

    if write:
        _write_atomic(speckit / "traceability.json",
                      json.dumps(output, ensure_ascii=False, indent=2) + "\n")
        for feature in sorted(fragments):
            feature_entries = [entry for entry in entries if entry["feature"] == feature]
            scaffold_structure = ""
            if feature.startswith("000-scaffold-"):
                spec_md_path = specs_dir / feature / "spec.md"
                if spec_md_path.is_file():
                    scaffold_structure = _extract_scaffold_structure(
                        spec_md_path.read_text(encoding="utf-8", errors="ignore"))
            _write_atomic(specs_dir / feature / "tasks.md",
                          _render_tasks(feature, feature_entries, scaffold_structure))
        _write_atomic(speckit / "traceability.csv",
                      _render_csv(output, delimiter=",", lineterminator="\n"),
                      encoding="utf-8-sig")
        # `tasks-progress.json` nasce aqui, junto do traceability. Deixá-lo para
        # um passo separado significava que qualquer falha entre os dois
        # produzia rastreabilidade sem progresso — e era o reconciler que
        # "resolvia", com placeholder. Idempotente: preserva o que já existe.
        progresso = sync_task_progress(project, output, repo_root=repo_root)

        # Sempre gravado, inclusive vazio: a ausência do arquivo passa a
        # significar "o compilador não rodou", nunca "rodou e nada achou".
        _write_atomic(speckit / "compile-warnings.json",
                      json.dumps(_warnings_report(project, output, progresso),
                                 ensure_ascii=False, indent=2) + "\n")
    return output


def _traceability_vazio(project: str, trace_id: str, motivo: str) -> dict[str, Any]:
    """Traceability válido com zero entries. Não é placeholder de recuperação."""
    return {
        "schema_version": "4.0.0",
        "project": project,
        "trace_id": trace_id,
        "generated_at": datetime.datetime.now(
            datetime.timezone.utc).isoformat(timespec="seconds"),
        "constitution": "outputs/tobe/speckit/constitution.md",
        "status": "COMPLETE_WITH_WARNINGS",
        "recovery_placeholder": False,
        "artifacts_written": True,
        "reason": motivo,
        "validation_summary": {"warnings": len(_WARNINGS), "errors": 0,
                               "ownership_conflicts": len(_CONFLICTS)},
        "total_tasks": 0,
        "reconciled_from_plan": [],
        "multi_producer_tokens": [],
        "orphan_consumes": [],
        "ownership_conflicts": list(_CONFLICTS),
        "broken_edges": [],
        "warnings": list(_WARNINGS),
        "graph_checksum": hashlib.sha256(b"[]").hexdigest(),
        "dependency_edges": [],
        "execution_order": [],
        "execution_waves": [],
        "entries": [],
    }


def sync_task_progress(project: str, output: Mapping[str, Any],
                       repo_root: Path | None = None) -> dict[str, Any]:
    """Cria/atualiza `tasks-progress.json` a partir do traceability recém-escrito.

    Delega ao `task_ledger`, que é quem já sabe preservar status, tentativas,
    evidências e timestamps das tasks conhecidas. Não duplicar essa lógica aqui
    é o que garante que consolidar e retomar continuem concordando.

    Nunca levanta: falha do razão vira aviso. O traceability já está em disco, e
    derrubar a consolidação depois disso perderia o artefato principal por causa
    do secundário.
    """
    try:
        import task_ledger  # noqa: PLC0415 — import tardio: evita ciclo
        return task_ledger.init(project, repo_root or REPO_ROOT)
    except Exception as exc:  # noqa: BLE001
        _warn("C009", "tasks-progress.json",
              f"razão de progresso não sincronizado: {type(exc).__name__}: {exc}",
              f"rode `python src/shared/tools/task_ledger.py -p {project} --init`")
        return {"tasks": []}


def _warnings_report(project: str, output: Mapping[str, Any],
                     progresso: Mapping[str, Any]) -> dict[str, Any]:
    """`compile-warnings.json` — suficiente para diagnóstico automatizado.

    As fases a jusante liam `artifacts_written` e não tinham como saber quantas
    entries foram de fato gravadas. Sem isso, `exit 0` era confundido com
    "artefatos produzidos", que é exatamente o buraco que este arquivo passa a
    fechar.
    """
    por_categoria: dict[str, int] = defaultdict(int)
    for item in _WARNINGS:
        por_categoria[str(item.get("code"))] += 1
    for item in _CONFLICTS:
        por_categoria[str(item.get("code"))] += 1

    features = sorted({f for c in _CONFLICTS for f in c.get("features") or []})
    waves = sorted({w for c in _CONFLICTS for w in c.get("waves") or []})
    fontes = sorted({s for c in _CONFLICTS for s in c.get("source_files") or []})
    return {
        "project": project,
        "generated_at": output["generated_at"],
        "status": output["status"],
        "artifacts_written": bool(output.get("artifacts_written")),
        "warnings_written": bool(_WARNINGS or _CONFLICTS),
        "traceability_entries_written": len(output.get("entries") or []),
        "tasks_progress_entries_written": len(progresso.get("tasks") or []),
        "warning_count": len(_WARNINGS) + len(_CONFLICTS),
        "warnings_by_category": dict(sorted(por_categoria.items())),
        "conflicts": list(_CONFLICTS),
        "affected_features": features,
        "affected_waves": waves,
        "source_files": fontes,
        "recommended_actions": sorted({
            str(c.get("resolution")) for c in _CONFLICTS if c.get("resolution")
        }),
        "orphan_consumes": sorted(set(output.get("orphan_consumes") or [])),
        "broken_edges": list(output.get("broken_edges") or []),
        "warnings": list(_WARNINGS),
    }


def _validate_header(data: Mapping[str, Any], project: str, feature: str, path: Path) -> None:
    if data.get("schema_version") not in ACCEPTED_SCHEMA_VERSIONS:
        raise CompilerError(
            f"{path}: schema_version={data.get('schema_version')!r}, "
            f"esperado um de {ACCEPTED_SCHEMA_VERSIONS}"
        )
    if data.get("project") != project:
        raise CompilerError(f"{path}: project={data.get('project')!r}, esperado {project!r}")
    if data.get("feature") != feature:
        raise CompilerError(f"{path}: feature={data.get('feature')!r}, esperado {feature!r}")
    for field in ("trace_id", "spec_id", "plan_id", "migration_wave_id"):
        if not data.get(field):
            raise CompilerError(f"{path}: campo obrigatório ausente: {field}")
    wave_order = data.get("migration_wave_order")
    if not isinstance(wave_order, int) or wave_order < 0:
        raise CompilerError(f"{path}: migration_wave_order precisa ser inteiro >= 0")


def _validate_task(task: Mapping[str, Any], owner: str) -> None:
    """Valida apenas o que o FRAGMENT é autoridade.

    `action`, `task_type`, `source_refs`, `produces` e `consumes` deixaram de ser
    exigidos aqui: são campos de arquivo, lidos do `plan-graph.json` pelo
    compilador (ver "Campos de arquivo: o plano é a autoridade"). Continuar
    exigindo a recópia obrigava o agente a reproduzir 41% de payload redundante
    por entry — medido no fragment da 003 — e foi o que consumiu o orçamento de
    saída antes de cobrir todos os arquivos do plano.

    Se vierem preenchidos (fragments antigos), são aceitos e reconciliados; se o
    valor for inválido, o erro aparece na comparação com o plano, não aqui.
    """
    required_non_empty = (
        "task_id", "title", "group", "target_stack",
        "target_file", "acceptance", "priority", "story_points",
    )
    missing = [field for field in required_non_empty if not task.get(field)]
    # `verify_command` OU `verify_profile`. Exigir o comando literal era o que
    # obrigava a LLM a escrever prosa executavel — a origem do `ng build` que
    # nao existe no PATH. Com o perfil declarado, o comando e derivado da stack.
    if not task.get("verify_command") and not task.get("verify_profile"):
        missing.append("verify_command|verify_profile")
    required_arrays = ("depends_on", "depends_on_groups")
    missing.extend(field for field in required_arrays if field not in task)
    if missing:
        raise CompilerError(f"{owner}: campos obrigatórios ausentes: {', '.join(missing)}")
    if task.get("priority") not in {"P1", "P2", "P3"}:
        raise CompilerError(f"{owner}: priority inválida: {task.get('priority')!r}")
    if task.get("story_points") not in {1, 2}:
        raise CompilerError(f"{owner}: story_points precisa ser 1 ou 2")
    if not isinstance(task.get("acceptance"), list) or not task["acceptance"]:
        raise CompilerError(f"{owner}: acceptance precisa ter ao menos um critério")


def _normalize_verify(tasks: list[dict[str, Any]], project: str,
                      repo_root: Path) -> list[dict[str, str]]:
    """Resolve `verify_profile` → comando real, por stack. Muta `tasks`.

    Este é o passo que corta o problema na origem. `f4s_build_runner` já fazia o
    verificador da stack vencer o override, mas na F4S — depois do dado ruim já
    ter entrado em `traceability.json`, que é imutável por contrato. Aqui o
    comando incompatível nunca chega a ser gravado.

    Nada é descartado em silêncio: `verify_command_original` preserva o que a
    LLM escreveu, e a troca vira aviso C020 com a evidência.
    """
    project_dir = repo_root / "projects" / project
    try:
        config = prototype_manifest.load_target_stack(project_dir)
    except prototype_manifest.PrototypeManifestError as exc:
        _warn("C021", "project-config",
              f"stack não resolvível ({exc}); verify_command mantido como veio",
              "declare tobe_stack em context/project-config.yaml")
        return []

    incompatible: list[dict[str, str]] = []
    cache: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for task in tasks:
        stack = str(task.get("target_stack") or "")
        key = (stack, str(task.get("verify_profile") or ""),
               str(task.get("verify_command") or ""), str(task.get("work_kind") or ""))
        resolved = cache.get(key)
        if resolved is None:
            resolved = verify_profiles.normalize(
                task.get("verify_command") or "",
                stack=stack,
                task_type=str(task.get("task_type") or ""),
                work_kind=str(task.get("work_kind") or ""),
                verify_profile=str(task.get("verify_profile") or ""),
                project_dir=project_dir, config=config, repo_root=repo_root)
            cache[key] = resolved
        original = task.get("verify_command") or ""
        task["verify_command_original"] = original
        task["verify_profile"] = resolved["verify_profile"]
        task["verify_resolved_from"] = resolved["resolved_from"]
        if resolved["verify_command"]:
            task["verify_command"] = resolved["verify_command"]
        if not resolved["compatible"] and original:
            incompatible.append({
                "task_id": str(task.get("task_id")),
                "target_stack": stack,
                "original": original,
                "replaced_by": resolved["verify_command"],
                "verify_profile": resolved["verify_profile"],
            })
    if incompatible:
        amostra = ", ".join(f"{item['task_id']} ({item['original'][:32]})"
                            for item in incompatible[:5])
        _warn("C020", f"{len(incompatible)} task(s)",
              f"verify_command incompatível com a stack foi substituído pelo "
              f"perfil canônico: {amostra}{'…' if len(incompatible) > 5 else ''}",
              "declare verify_profile no plan-graph.json em vez de escrever o "
              "comando; verify_profiles.PROFILES lista os aceitos")
    return incompatible


def _integration_findings(tasks: list[dict[str, Any]],
                          edges: Mapping[tuple[str, str], Any],
                          manifest: Mapping[str, Mapping[str, Any]],
                          prototype: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """Validações determinísticas do elo frontend ↔ backend (§12 do briefing).

    Todas produzem ACHADO, nunca exceção: um plano com um `consumes` órfão é
    defeito de dado recuperável, e a política do F3S.yaml é explícita — erro não
    trava fase, e nenhuma inconsistência localizada pode descartar tasks
    íntegras. O que muda em relação a antes é que o achado passa a EXISTIR: até
    aqui um frontend planejado sem backend correspondente simplesmente compilava
    e ninguém era avisado.
    """
    findings: list[dict[str, Any]] = []

    def _finding_item(code: str, severity: str, message: str, *,
                      task_ids: Sequence[str] = (), items: Sequence[str] = (),
                      evidence: str = "", action: str = "") -> None:
        findings.append({
            "check_id": code,
            "status": "fail" if severity == "error" else "warn",
            "severity": severity,
            "message": message,
            "task_ids": sorted(set(task_ids)),
            "affected_items": sorted(set(items)),
            "evidence": evidence,
            "recommended_action": action,
        })

    known_tasks = {task["task_id"] for task in tasks}
    producers: dict[str, list[str]] = defaultdict(list)
    for task in tasks:
        for token in task.get("produces") or []:
            producers[token].append(task["task_id"])

    # 1. Todo `consumes` tem produtor ou é dependência externa declarada.
    orphans: dict[str, list[str]] = defaultdict(list)
    for task in tasks:
        for token in task.get("consumes") or []:
            if token not in producers and not token.startswith("external:"):
                orphans[token].append(task["task_id"])
    for token, consumers in sorted(orphans.items()):
        _finding_item(
            "DEP-ORPHAN-CONSUME", "warning",
            f"consumo sem produtor: {token}", task_ids=consumers, items=[token],
            evidence=f"{len(consumers)} task(s) consomem {token} e nenhuma o produz",
            action=f"declare o produtor de {token} no plano, ou prefixe com "
                   f"'external:' se for dependência fora do escopo do projeto")

    # 2. Toda operação consumida pelo frontend tem contrato backend.
    contracted = {token_parts(token)[1] for token in producers
                  if token_parts(token)[0] in {"api-contract", "api-implementation"}}
    frontend_ops: dict[str, list[str]] = defaultdict(list)
    for task in tasks:
        if str(task.get("task_type")) != "frontend":
            continue
        for operation in task.get("api_ops") or []:
            frontend_ops[operation].append(task["task_id"])
    missing_contract = sorted(set(frontend_ops) - contracted)
    if missing_contract:
        _finding_item(
            "API-CONTRACT-FOR-FRONTEND", "error",
            "operação consumida pelo frontend sem contrato backend planejado",
            task_ids=[tid for op in missing_contract for tid in frontend_ops[op]],
            items=missing_contract,
            evidence=f"operationId sem produtor api-contract:*: {', '.join(missing_contract[:8])}",
            action="planeje a task de contrato backend (work_kind "
                   "backend_api_contract, produces api-contract:{operationId})")

    # 3. Toda tela dinâmica tem task de integração, ou justificativa de estática.
    if prototype:
        static_ok = {screen["screen_id"] for screen in prototype.get("screens") or []
                     if not screen.get("dynamic")}
        dynamic_screens = {screen["screen_id"] for screen in prototype.get("screens") or []
                           if screen.get("dynamic")}
        planned_screens = {sid for task in tasks for sid in task.get("screen_ids") or []}
        integration_screens = {
            sid for task in tasks
            if str(task.get("work_kind")) in {"frontend_integration", "frontend_api_client"}
            or "api-client" in " ".join(task.get("produces") or [])
            for sid in task.get("screen_ids") or []
        }
        gap = sorted((dynamic_screens & planned_screens) - integration_screens - static_ok)
        if gap:
            _finding_item(
                "FRONTEND-BACKEND-INTEGRATION", "error",
                "tela dinâmica planejada sem nenhuma task de integração com a API",
                items=gap,
                evidence=f"telas dinâmicas sem work_kind frontend_integration/"
                         f"frontend_api_client: {', '.join(gap[:8])}",
                action="planeje a task de client de API e a de integração da tela, "
                       "ou declare a tela como estática no screen-list.md")

    # 4. Toda task e2e depende de frontend e backend correspondentes.
    successors: dict[str, set[str]] = defaultdict(set)
    for predecessor, successor in edges:
        successors[successor].add(predecessor)
    by_id = {task["task_id"]: task for task in tasks}
    for task in tasks:
        if str(task.get("work_kind")) != "end_to_end_test":
            continue
        upstream_types = {str(by_id[pred].get("task_type"))
                          for pred in successors[task["task_id"]] if pred in by_id}
        missing = {"frontend", "backend"} - upstream_types
        if missing:
            _finding_item(
                "E2E-DEPENDENCIES", "warning",
                f"task end-to-end sem dependência de {', '.join(sorted(missing))}",
                task_ids=[task["task_id"]],
                evidence=f"predecessores: {sorted(upstream_types) or 'nenhum'}",
                action="declare depends_on das tasks de frontend e backend do fluxo, "
                       "ou consumes dos tokens api-client:*/api-implementation:*")

    # 5. Nenhuma dependência para task inexistente.
    dangling: dict[str, list[str]] = defaultdict(list)
    for task in tasks:
        for dependency in task.get("depends_on") or []:
            if dependency not in known_tasks:
                dangling[dependency].append(task["task_id"])
    if dangling:
        _finding_item(
            "DEP-UNKNOWN-TASK", "warning",
            "dependência declarada para task inexistente",
            task_ids=[tid for ids in dangling.values() for tid in ids],
            items=sorted(dangling),
            evidence=f"task_ids inexistentes: {', '.join(sorted(dangling)[:8])}",
            action="corrija depends_on no fragment, ou regere o fragment da feature")

    # 6. Nenhuma referência a screen/component/operationId inexistente.
    if prototype:
        real_screens = {screen["screen_id"] for screen in prototype.get("screens") or []}
        real_components = {
            component["component_id"]
            for screen in prototype.get("screens") or []
            for component in screen.get("components") or []
        } | {component["component_id"]
             for component in prototype.get("shared_components") or []}
        real_routes = {route["route_id"] for route in prototype.get("routes") or []}
        for field, catalogue, label in (("screen_ids", real_screens, "tela"),
                                        ("component_ids", real_components, "componente"),
                                        ("route_ids", real_routes, "rota")):
            invented: dict[str, list[str]] = defaultdict(list)
            for task in tasks:
                for value in task.get(field) or []:
                    if value not in catalogue:
                        invented[value].append(task["task_id"])
            if invented:
                _finding_item(
                    "PROTOTYPE-REF-INTEGRITY", "error",
                    f"{label} referenciada pelo plano não existe no protótipo",
                    task_ids=[tid for ids in invented.values() for tid in ids],
                    items=sorted(invented),
                    evidence=f"{field} inexistentes: {', '.join(sorted(invented)[:8])}",
                    action="use apenas os ids do prototype-implementation-manifest.json; "
                           "a F3S não inventa tela, componente nem rota")

    real_ops = {operation for entry in manifest.values()
                for operation in _manifest_api_ops(entry)}
    if real_ops:
        invented_ops: dict[str, list[str]] = defaultdict(list)
        for task in tasks:
            for operation in task.get("api_ops") or []:
                if operation not in real_ops:
                    invented_ops[operation].append(task["task_id"])
        if invented_ops:
            _finding_item(
                "API-REF-INTEGRITY", "error",
                "operationId referenciado pelo plano não existe no contrato",
                task_ids=[tid for ids in invented_ops.values() for tid in ids],
                items=sorted(invented_ops),
                evidence=f"operationId fora do OpenAPI/api-map: "
                         f"{', '.join(sorted(invented_ops)[:8])}",
                action="use apenas operationId declarados no OpenAPI; a F3S não "
                       "inventa endpoint")
    return findings


def _manifest_api_ops(entry: Mapping[str, Any]) -> set[str]:
    """Operações formalmente atribuídas a uma feature pelo manifesto de waves."""
    operations: set[str] = set()
    for source in entry.get("sources") or []:
        if str(source.get("source_id")) in {"api", "api-operations"}:
            operations.update(str(item) for item in source.get("anchors") or [])
    prototype = entry.get("prototype") or {}
    operations.update(str(item) for item in prototype.get("api_ops") or [])
    return operations


def _add_group_edges(tasks, groups, edges, add_edge) -> None:
    tasks_by_group: dict[str, list[str]] = defaultdict(list)
    for task in tasks:
        tasks_by_group[task["group"]].append(task["task_id"])

    def roots(group_id: str) -> list[str]:
        members = set(tasks_by_group[group_id])
        return sorted(task_id for task_id in members
                      if not any(pred in members for pred, succ in edges if succ == task_id))

    def terminals(group_id: str) -> list[str]:
        members = set(tasks_by_group[group_id])
        return sorted(task_id for task_id in members
                      if not any(succ in members for pred, succ in edges if pred == task_id))

    for group_id, group in groups.items():
        for predecessor_group in group.get("depends_on") or []:
            if predecessor_group not in groups:
                raise CompilerError(f"{group_id}: depende de grupo inexistente {predecessor_group}")
            for predecessor in terminals(predecessor_group):
                for successor in roots(group_id):
                    add_edge(predecessor, successor, "group_dependency",
                             f"{group_id} depends_on {predecessor_group}")

    for task in tasks:
        for predecessor_group in task["depends_on_groups"]:
            if predecessor_group not in groups:
                raise CompilerError(
                    f"{task['task_id']}: depende de grupo inexistente {predecessor_group}"
                )
            for predecessor in terminals(predecessor_group):
                add_edge(predecessor, task["task_id"], "group_dependency",
                         f"task depends_on_groups {predecessor_group}")


def _add_migration_wave_edges(tasks, manifest, edges, add_edge) -> None:
    tasks_by_wave: dict[str, list[str]] = defaultdict(list)
    for task in tasks:
        tasks_by_wave[str(task["migration_wave_id"])].append(task["task_id"])

    def roots(wave_id: str) -> list[str]:
        members = set(tasks_by_wave[wave_id])
        return sorted(task_id for task_id in members
                      if not any(pred in members for pred, succ in edges if succ == task_id))

    def terminals(wave_id: str) -> list[str]:
        members = set(tasks_by_wave[wave_id])
        return sorted(task_id for task_id in members
                      if not any(succ in members for pred, succ in edges if pred == task_id))

    by_wave = {str(item.get("wave_id")): item for item in manifest.values()}

    file_creates: dict[str, tuple[str, int]] = {}  # path -> (task_id, wave_order)
    file_updates: dict[str, list[tuple[str, int]]] = defaultdict(list)
    task_by_id = {task["task_id"]: task for task in tasks}
    for task in tasks:
        wave_order = int(task["migration_wave_order"])
        path = task["target_file"]
        if task["action"] == "create":
            if path not in file_creates or wave_order < file_creates[path][1]:
                file_creates[path] = (task["task_id"], wave_order)
        elif task["action"] == "update":
            file_updates[path].append((task["task_id"], wave_order))

    def has_earlier_owner(task_id: str) -> bool:
        """Return True if task touches a file owned/created earlier than its wave."""
        task = task_by_id[task_id]
        path = task["target_file"]
        wave_order = int(task["migration_wave_order"])
        if path in file_creates:
            owner_tid, owner_order = file_creates[path]
            if owner_tid != task_id and owner_order < wave_order:
                return True
        if task["action"] == "update":
            # Any earlier update of the same file makes this a non-root update.
            for updater_tid, updater_order in file_updates[path]:
                if updater_tid != task_id and updater_order < wave_order:
                    return True
        return False

    for wave_id, members in tasks_by_wave.items():
        wave = by_wave.get(wave_id)
        # W0 é reservada para scaffolds sintéticos da F4S; não consta do
        # manifesto de waves de domínio e não impõe dependências de wave.
        if wave_id == "W0":
            continue
        if not wave:
            raise CompilerError(f"migration wave ausente do manifesto: {wave_id}")
        for predecessor_wave in wave.get("depends_on") or []:
            if predecessor_wave not in by_wave:
                raise CompilerError(f"{wave_id}: depende de migration wave ausente {predecessor_wave}")
            if predecessor_wave not in tasks_by_wave:
                continue
            for predecessor in terminals(predecessor_wave):
                for successor in roots(wave_id):
                    
                    if has_earlier_owner(successor):
                        continue
                    add_edge(predecessor, successor, "migration_wave_dependency",
                             f"{wave_id} depends_on {predecessor_wave}")


def _add_scaffold_edges(tasks, edges, add_edge) -> None:
    """Toda task não-scaffold depende do scaffold da mesma target_stack."""
    def is_scaffold(task: Mapping[str, Any]) -> bool:
        return (
            str(task.get("feature") or "").startswith("000-scaffold-")
            or str(task.get("task_id") or "").startswith("T-SCAFFOLD-")
            or any(str(token).startswith("artifact:scaffold:")
                   for token in (task.get("produces") or []))
        )

    scaffold_tasks: dict[str, str] = {}
    for task in tasks:
        if is_scaffold(task):
            scaffold_tasks[task["target_stack"]] = task["task_id"]
    for task in tasks:
        if is_scaffold(task):
            continue
        scaffold_id = scaffold_tasks.get(task["target_stack"])
        if scaffold_id and scaffold_id != task["task_id"]:
            add_edge(scaffold_id, task["task_id"], "scaffold_dependency",
                     f"depends on scaffold for {task['target_stack']}")


def _compiled_entry(task: Mapping[str, Any], plan: dependency_graph.DependencyPlan,
                    task_by_id: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    task_id = str(task["task_id"])
    dependencies = list(plan.predecessors[task_id])
    backend_dependencies = []
    if task.get("task_type") == "frontend":
        backend_dependencies = [
            predecessor for predecessor in dependencies
            if task_by_id[predecessor].get("task_type") == "backend"
        ]
    return {
        "task_id": task_id,
        "title": task.get("title"),
        "spec_id": task.get("spec_id"),
        "plan_id": task.get("plan_id"),
        "feature": task.get("feature"),
        "group": task.get("group"),
        "migration_wave_id": task.get("migration_wave_id"),
        "migration_wave_order": task.get("migration_wave_order"),
        "task_type": task.get("task_type"),
        "target_stack": task.get("target_stack"),
        "source_refs": list(task.get("source_refs") or []),
        "rule_ids": list(task.get("rule_ids") or []),
        "api_ops": list(task.get("api_ops") or []),
        # `screen_id` singular permanece por compatibilidade com os consumidores
        # 3.0.0 (task_ledger, f4_task_context); `screen_ids` e a forma corrente.
        "screen_id": task.get("screen_id") or (
            (task.get("screen_ids") or [None])[0]),
        "screen_ids": list(task.get("screen_ids") or []),
        "component_ids": list(task.get("component_ids") or []),
        "route_ids": list(task.get("route_ids") or []),
        "design_tokens": list(task.get("design_tokens") or []),
        "flow_ids": list(task.get("flow_ids") or []),
        "work_kind": task.get("work_kind") or "",
        "prototype_refs": list(task.get("prototype_refs") or []),
        "test_ids": list(task.get("test_ids") or []),
        "target_files": [task.get("target_file")],
        "target_file": task.get("target_file"),
        "action": task.get("action"),
        # Ownership disputado viaja NA entry: quem lê o traceability precisa
        # saber que a resolução foi um desempate, não uma decisão do plano.
        # Sem isto a escolha determinística esconderia o conflito original.
        "ownership_status": task.get("ownership_status", "OWNER"),
        "ownership_claims": list(task.get("ownership_claims") or []),
        "ownership_conflict": task.get("ownership_conflict"),
        "action_original": task.get("action_original"),
        "source_feature": task.get("feature"),
        "source_wave": task.get("migration_wave_id"),
        "source_fragment": f"specs/{task.get('feature')}/task-fragment.json",
        "depends_on": dependencies,
        "backend_dependencies": backend_dependencies,
        "acceptance": list(task.get("acceptance") or []),
        "verify_command": task.get("verify_command"),
        "verify_profile": task.get("verify_profile") or "",
        "verify_resolved_from": task.get("verify_resolved_from") or "",
        "priority": task.get("priority") or "P2",
        "story_points": task.get("story_points"),
        "topological_rank": plan.ranks[task_id],
        "execution_wave": plan.ranks[task_id],
    }


def _render_tasks(feature: str, entries: list[dict[str, Any]],
                  scaffold_structure: str = "") -> str:
    wave = entries[0]["migration_wave_id"] if entries else "—"
    wave_order = entries[0]["migration_wave_order"] if entries else "—"
    lines = [
        f"# Tasks: {feature}",
        "",
        f"> **Migration Wave**: {wave} · **Ordem**: {wave_order}",
        "> Derivado de `outputs/tobe/speckit/traceability.json` — não editar à mão.",
        "",
        "| Task ID | Título | Tipo | Grupo | Stack | Arquivo alvo | Depende de | Backend direto | SP |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for entry in entries:
        values = [
            entry["task_id"], entry["title"], entry["task_type"], entry["group"],
            entry["target_stack"],
            f"`{entry['target_files'][0]}`",
            ", ".join(entry["depends_on"]) or "—",
            ", ".join(entry["backend_dependencies"]) or "—", str(entry["story_points"]),
        ]
        lines.append("| " + " | ".join(str(value).replace("|", "\\|") for value in values) + " |")
    if scaffold_structure:
        lines += [
            "",
            "## Estrutura Esperada (redundância — ver spec.md)",
            "",
            "> Copiado de `spec.md` para que o `ava-f4s-codegen-agent` veja a árvore "
            "mesmo se o input do F4 não incluir o spec.md desta feature.",
            "",
            scaffold_structure,
        ]
    return "\n".join(lines) + "\n"


# Columns for the flat tabular export. Arrays are serialized with a safe
# delimiter so every scalar field stays lossless and round-trippable.
_TASK_COLUMNS: list[tuple[str, list[str]]] = [
    ("task_id", []),
    ("title", []),
    ("spec_id", []),
    ("plan_id", []),
    ("feature", []),
    ("group", []),
    ("migration_wave_id", []),
    ("migration_wave_order", []),
    ("task_type", []),
    ("target_stack", []),
    ("target_file", ["target_files"]),
    ("action", []),
    ("priority", []),
    ("story_points", []),
    ("topological_rank", []),
    ("execution_wave", []),
    ("source_refs", ["source_refs"]),
    ("rule_ids", ["rule_ids"]),
    ("api_ops", ["api_ops"]),
    ("screen_id", []),
    ("test_ids", ["test_ids"]),
    ("depends_on", ["depends_on"]),
    ("backend_dependencies", ["backend_dependencies"]),
    ("acceptance", ["acceptance"]),
    ("verify_command", []),
]


def _serialize_cell(value: Any, *, array_delimiter: str = "\u241E") -> str:
    """Serialize a scalar or array value for CSV/XLSX export.

    Arrays are joined with the record separator ``\u241E`` (ASCII RS) so
    commas and newlines inside individual items are preserved.
    Nested objects (source_refs) become ``key=value;key=value`` records
    joined by the unit separator ``\u241F``.
    """
    if value is None:
        return ""
    if isinstance(value, list):
        if not value:
            return ""
        if isinstance(value[0], dict):
            return array_delimiter.join(
                ";".join(f"{k}={v}" for k, v in sorted(item.items()))
                for item in value
            )
        return array_delimiter.join(str(item) for item in value)
    return str(value)


def _entry_to_row(entry: Mapping[str, Any]) -> list[str]:
    row: list[str] = []
    for col, path in _TASK_COLUMNS:
        keys = path or [col]
        value: Any = entry
        for key in keys:
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(key)
        row.append(_serialize_cell(value))
    return row


def _render_csv(output: Mapping[str, Any], *, delimiter: str = ",",
                lineterminator: str = "\n") -> str:
    header = [col for col, _ in _TASK_COLUMNS]
    rows = [_entry_to_row(entry) for entry in output["entries"]]
    import io
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter=delimiter, lineterminator=lineterminator,
                        quoting=csv.QUOTE_MINIMAL)
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue()


def export_csv(output: Mapping[str, Any], path: Path,
               *, delimiter: str = ",", encoding: str = "utf-8-sig") -> None:
    """Export a compiled traceability document to a flat CSV file."""
    content = _render_csv(output, delimiter=delimiter, lineterminator="\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_atomic(path, content, encoding=encoding)


def export_xlsx(output: Mapping[str, Any], path: Path) -> None:
    """Export a compiled traceability document to Excel (.xlsx).

    The workbook contains three sheets:

    * ``tasks`` — one row per task, arrays serialized with delimiters.
    * ``dependencies`` — one row per dependency edge (from/to/reason/source).
    * ``execution_waves`` — mapping of wave index to task ids.

    OpenPyXL is used when available; otherwise a friendly error is raised.
    """
    try:
        import openpyxl
    except ImportError as exc:
        raise CompilerError(
            "exportação XLSX requer openpyxl; instale com: pip install openpyxl"
        ) from exc

    path.parent.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()

    # Sheet 1: tasks
    ws_tasks = wb.active
    if ws_tasks is None:
        ws_tasks = wb.create_sheet("tasks")
    else:
        ws_tasks.title = "tasks"
    ws_tasks.append([col for col, _ in _TASK_COLUMNS])
    for entry in output["entries"]:
        ws_tasks.append(_entry_to_row(entry))

    # Sheet 2: dependency edges
    ws_edges = wb.create_sheet("dependencies")
    ws_edges.append(["from", "to", "reason", "source"])
    for edge in output.get("dependency_edges", []):
        ws_edges.append([
            edge.get("from", ""),
            edge.get("to", ""),
            edge.get("reason", ""),
            edge.get("source", ""),
        ])

    # Sheet 3: execution waves
    ws_waves = wb.create_sheet("execution_waves")
    ws_waves.append(["execution_wave_index", "task_id"])
    for index, wave in enumerate(output.get("execution_waves", []), start=1):
        for task_id in wave:
            ws_waves.append([index, task_id])

    wb.save(path)


def export_traceability(output: Mapping[str, Any], speckit_dir: Path,
                        *, formats: Sequence[str] = ("csv",)) -> dict[str, Path]:
    """Write optional tabular exports next to ``traceability.json``.

    Supported formats: ``csv`` and ``xlsx``. Unknown formats are ignored.
    Returns a map of format -> written path.
    """
    written: dict[str, Path] = {}
    supported = {"csv", "xlsx"}
    for fmt in formats:
        fmt = fmt.lower().strip(".")
        if fmt not in supported:
            continue
        path = speckit_dir / f"traceability.{fmt}"
        if fmt == "csv":
            export_csv(output, path)
        elif fmt == "xlsx":
            export_xlsx(output, path)
        written[fmt] = path
    return written


def _write_atomic(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding=encoding)
    temporary.replace(path)


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="speckit_task_compiler.py")
    parser.add_argument("command",
                        choices=["compile", "validate", "order", "export", "diagnose"])
    parser.add_argument("-p", "--project", required=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--plans-only", action="store_true",
        help="diagnose: checa apenas os plan-graph.json (gate do produtor, "
             "logo após a wave4, antes de existirem os fragments)",
    )
    parser.add_argument(
        "--formats",
        default="csv",
        help="formatos de exportação separados por vírgula (csv, xlsx); usado com 'export' ou 'compile'",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="diretório de saída para exportação; padrão: outputs/tobe/speckit/",
    )
    parser.add_argument(
        "--warn",
        action="store_true",
        help="converte erros de validação em avisos e retorna exit 0",
    )
    args = parser.parse_args(argv)

    try:
        if args.command == "diagnose":
            # Nunca levanta por achado: o diagnóstico existe justamente para
            # listar tudo. Exit 2 sinaliza que há erro, mas o relatório sai.
            report = diagnose_project(args.project, plans_only=args.plans_only)
            print(json.dumps(report, ensure_ascii=False, indent=2) if args.json
                  else render_diagnosis(report))
            if args.warn and not report["ok"]:
                print(f"\nAVISO: diagnose encontrou problemas, mas --warn foi "
                      f"solicitado; continuando.", file=sys.stderr)
                return 0
            return 0 if report["ok"] else 2

        if args.command == "export":
            speckit = _speckit_dir(args.project, REPO_ROOT)
            traceability_path = speckit / "traceability.json"
            output = _read_json(traceability_path)
            target_dir = Path(args.output_dir) if args.output_dir else speckit
            written = export_traceability(
                output, target_dir,
                formats=[fmt.strip() for fmt in args.formats.split(",")],
            )
            result: Any = {
                "status": "exported",
                "formats": {fmt: str(path) for fmt, path in written.items()},
            }
            print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result)
            return 0

        output = compile_project(args.project, write=args.command == "compile")
        if args.command == "compile":
            formats = [fmt.strip() for fmt in args.formats.split(",")]
            if formats and formats != [""]:
                speckit = _speckit_dir(args.project, REPO_ROOT)
                written = export_traceability(output, speckit, formats=formats)
                export_paths = {fmt: str(path) for fmt, path in written.items()}
            else:
                export_paths = {}
    except CompilerError as exc:
        _persist_fatal(args, str(exc))
        if args.warn:
            print(json.dumps(_fatal_payload(args, str(exc)), ensure_ascii=False, indent=2)
                  if args.json else _render_fatal_banner(args, str(exc)))
            return 0
        print(_render_fatal_banner(args, str(exc)), file=sys.stderr)
        return 2
    except Exception as exc:
        detail = f"{type(exc).__name__}: {exc}"
        _persist_fatal(args, detail)
        if args.warn:
            print(json.dumps(_fatal_payload(args, detail), ensure_ascii=False, indent=2)
                  if args.json else _render_fatal_banner(args, detail))
            return 0
        print(_render_fatal_banner(args, detail), file=sys.stderr)
        raise

    if args.command == "order":
        result = {
            "execution_order": output["execution_order"],
            "execution_waves": output["execution_waves"],
        }
    elif args.command == "compile":
        result = {
            "status": "compiled_with_warnings" if _WARNINGS else "compiled",
            "tasks": output["total_tasks"],
            "graph_checksum": output["graph_checksum"],
            "exports": export_paths,
            "warnings": len(_WARNINGS),
            "warnings_report": str(
                _speckit_dir(args.project, REPO_ROOT) / "compile-warnings.json"),
        }
        # A compilação nunca trava a fase, mas o operador precisa VER o que foi
        # degradado. Sem este bloco o defeito some no log e reaparece três
        # passos adiante atribuído ao agente errado (ISSUE-004).
        if _WARNINGS:
            print(_render_warnings_banner(args.project), file=sys.stderr)
    else:
        result = {
            "status": "valid",
            "tasks": output["total_tasks"],
            "graph_checksum": output["graph_checksum"],
        }
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())