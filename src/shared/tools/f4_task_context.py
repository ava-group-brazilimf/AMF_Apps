#!/usr/bin/env python3
"""
f4_task_context.py — Contexto mínimo de UMA task da F4.

Por que existe
--------------
O manifesto `inputs` da F4 é global: `specs/*/spec.md`, `specs/*/plan.md`,
`specs/*/tasks.md`, blueprint, ADRs, OpenAPI, protótipo. Medido no projeto
`cadastro-funcionarios-04`, isso dá **659 KB (~169k tokens)** — e o fan-out por
task copiava esse manifesto inteiro para cada uma das 218 tasks. Cada despacho
carregava as specs de todas as features, inclusive as que não tinham nada a ver
com a task.

Aqui o contexto é montado **por task**: a feature dela, as dependências dela, os
arquivos-alvo dela, o erro da tentativa anterior dela. O resto fica em disco,
referenciado por caminho.

Três níveis de orçamento
------------------------
`level=0` é o contexto completo da task. `level=1` corta os documentos
transversais para índice de seções. `level=2` mantém só a task, os alvos e o
erro anterior. O laço sobe o nível quando o request repetiria byte a byte um
que já falhou, ou quando o orçamento de janela estoura — mesma política do
laço da F5.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

#: Orçamentos por documento, em caracteres. Somados, o nível 0 fica na casa de
#: 60–80 KB — contra os 659 KB que o manifesto global injetava por task.
CONSTITUTION_CHARS = 12_000
SPEC_CHARS = 18_000
PLAN_CHARS = 12_000
TASKS_CHARS = 8_000
DOC_CHARS = 6_000
OPENAPI_CHARS = 8_000
SNAPSHOT_ENTRIES = 200
BUILD_LOG_CHARS = 4_000
DEPENDENCY_LIMIT = 12

_HEADING = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)

#: Documentos transversais. Entram fatiados por relevância, nunca inteiros.
CROSS_CUTTING_DOCS: tuple[str, ...] = (
    "outputs/tobe/docs/architecture-blueprint.md",
    "outputs/tobe/docs/tech-framework-document.md",
    "outputs/tobe/docs/architecture-decision-matrix.md",
)


# ─── Leitura ─────────────────────────────────────────────────────────────────

def _project_dir(project: str, repo_root: Path | None = None) -> Path:
    return (repo_root or REPO_ROOT) / "projects" / project


def _read_limited(path: Path, limit: int) -> str:
    try:
        texto = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if len(texto) <= limit:
        return texto
    return (texto[:limit]
            + f"\n[... truncado em {limit:,} chars; o arquivo completo esta em "
              f"disco ...]")


def headings(texto: str) -> list[str]:
    return [f"{'#' * len(m.group(1))} {m.group(2).strip()}"
            for m in _HEADING.finditer(texto)]


def index_block(rel: str, texto: str, limit: int, *, sufixo: str = "",
                max_headings: int = 60) -> str:
    """Índice de seções — ou o corpo, quando ele já é menor que o índice.

    Reduzir contexto que já cabe seria trocar o documento por uma lista maior
    que ele. O nível de orçamento só pode encolher o prompt, nunca inflá-lo.
    """
    indice = "\n".join(f"- {h}" for h in headings(texto)[:max_headings])
    corpo = _read_limited_text(texto, limit)
    if not indice or len(indice) >= len(corpo):
        return f"### {rel}\n\n```markdown\n{corpo}\n```"
    return f"### {rel} — indice{sufixo}\n\n{indice}"


def relevant_sections(texto: str, termos: set[str], limit: int) -> str:
    """Só as seções cujo título/corpo casa com os termos da task.

    Mesmo mecanismo do `plan_excerpt` da F5: documento grande entra fatiado, e
    sem nenhuma seção pertinente entra o começo do documento, que costuma ser o
    resumo.
    """
    if not texto:
        return ""
    if len(texto) <= limit:
        return texto
    posicoes = [(m.start(), m.group(2).strip()) for m in _HEADING.finditer(texto)]
    if not posicoes:
        return _read_limited_text(texto, limit)

    secoes: list[tuple[str, str]] = []
    for i, (inicio, titulo) in enumerate(posicoes):
        fim = posicoes[i + 1][0] if i + 1 < len(posicoes) else len(texto)
        secoes.append((titulo, texto[inicio:fim]))

    def pontua(titulo: str, corpo: str) -> int:
        alvo = f"{titulo}\n{corpo[:1500]}".casefold()
        return sum(1 for termo in termos if termo and termo.casefold() in alvo)

    ranqueadas = sorted(
        ((pontua(t, c), i, t, c) for i, (t, c) in enumerate(secoes)),
        key=lambda item: (-item[0], item[1]))

    escolhidas: list[tuple[int, str]] = []
    total = 0
    for score, indice, _titulo, corpo in ranqueadas:
        if score <= 0:
            continue
        if total + len(corpo) > limit:
            continue
        escolhidas.append((indice, corpo))
        total += len(corpo)
    if not escolhidas:
        return _read_limited_text(texto, limit)
    escolhidas.sort(key=lambda item: item[0])
    return "\n".join(corpo for _, corpo in escolhidas)


def _read_limited_text(texto: str, limit: int) -> str:
    if len(texto) <= limit:
        return texto
    return (texto[:limit]
            + f"\n[... truncado em {limit:,} chars; leia o arquivo em disco ...]")


def task_terms(task: dict[str, Any]) -> set[str]:
    """Termos que definem a task — usados para fatiar documentos grandes."""
    bruto = " ".join(str(x) for x in (
        task.get("title", ""), task.get("task_id", ""), task.get("group", ""),
        task.get("feature", ""), task.get("spec_id", ""),
        " ".join(task.get("acceptance") or []),
        " ".join(task.get("rule_ids") or []),
        " ".join(str(a) for a in (task.get("api_ops") or [])),
        " ".join(task.get("target_files") or []),
    ))
    return {p for p in re.split(r"[^\wÀ-ÿ.-]+", bruto) if len(p) >= 4}


# ─── Blocos ──────────────────────────────────────────────────────────────────

def task_block(task: dict[str, Any], route: Any, attempt: int) -> str:
    linhas = [
        "## SUA TASK NESTA EXECUCAO — implemente SOMENTE ela",
        "",
        f"- task_id: `{task.get('task_id')}`",
        f"- titulo: {task.get('title') or '(sem titulo)'}",
        f"- spec_id: {task.get('spec_id') or '—'} · feature: "
        f"{task.get('feature') or '—'}",
        f"- grupo: {task.get('group') or '—'} · wave: "
        f"{task.get('migration_wave_id') or '—'} "
        f"(ordem {task.get('migration_wave_order', 0)})",
        f"- task_type: **{route.component_type}** · target_stack: "
        f"**{route.target_stack}**",
        f"- prioridade: {task.get('priority') or 'P2'} · rank topologico: "
        f"{task.get('topological_rank', 0)}",
        f"- tentativa: {attempt} (tentativas ja registradas: "
        f"{task.get('attempts', 0)})",
        f"- diretorio canonico (UNICO destino permitido): "
        f"`outputs/tobe/{route.canonical_source_rel}/`",
        f"- comando de verificacao que o pipeline vai rodar: "
        f"`{task.get('verify_command') or ' '.join(route.build_command)}`",
    ]
    alvos = task.get("target_files") or ([task["target_file"]]
                                         if task.get("target_file") else [])
    if alvos:
        linhas += ["", "### Arquivos-alvo declarados no SpecKit", ""]
        linhas += [f"- `{item}`" for item in alvos[:40]]
    aceites = task.get("acceptance") or []
    if aceites:
        linhas += ["", "### Criterios de aceite (todos precisam passar)", ""]
        linhas += [f"{i}. {item}" for i, item in enumerate(aceites, 1)]
    refs = task.get("source_refs") or []
    if refs:
        linhas += ["", "### Proveniencia (leia em disco se precisar)", ""]
        for ref in refs[:10]:
            if isinstance(ref, dict):
                linhas.append(f"- `{ref.get('artifact')}` ancora "
                              f"`{ref.get('anchor')}`")
    return "\n".join(linhas)


def dependencies_block(task: dict[str, Any],
                       por_id: dict[str, dict[str, Any]]) -> str:
    """Dependências diretas: id, status e arquivos — nunca o conteúdo delas."""
    ids = list(task.get("depends_on") or []) + list(
        task.get("backend_dependencies") or [])
    vistos: list[str] = []
    for item in ids:
        if item not in vistos:
            vistos.append(item)
    if not vistos:
        return ""
    linhas = ["## DEPENDENCIAS JA CONCLUIDAS (resumo + caminhos, nunca o corpo)",
              ""]
    for dep_id in vistos[:DEPENDENCY_LIMIT]:
        dep = por_id.get(dep_id)
        if not dep:
            linhas.append(f"- `{dep_id}` — ausente no razao")
            continue
        arquivos = ", ".join(f"`{f}`" for f in (dep.get("files_written") or [])[:6])
        linhas.append(
            f"- `{dep_id}` [{dep.get('status')}] {dep.get('title') or ''}"
            + (f" → {arquivos}" if arquivos else ""))
    if len(vistos) > DEPENDENCY_LIMIT:
        linhas.append(f"- (+{len(vistos) - DEPENDENCY_LIMIT} dependencias omitidas)")
    return "\n".join(linhas)


def feature_docs_block(project: str, task: dict[str, Any], level: int,
                       repo_root: Path | None = None) -> str:
    """spec.md / plan.md / tasks.md **da feature da task**, e de mais nenhuma."""
    feature = str(task.get("feature") or "").strip()
    if not feature:
        return ""
    base = _project_dir(project, repo_root) / "outputs" / "tobe" / "speckit" / "specs" / feature
    if not base.is_dir():
        return (f"### Feature `{feature}`\n\n"
                f"Diretorio da feature ausente em disco: "
                f"`outputs/tobe/speckit/specs/{feature}/`")
    termos = task_terms(task)
    partes: list[str] = []
    for nome, limite in (("spec.md", SPEC_CHARS), ("plan.md", PLAN_CHARS),
                         ("tasks.md", TASKS_CHARS)):
        caminho = base / nome
        if not caminho.is_file():
            continue
        texto = caminho.read_text(encoding="utf-8", errors="replace")
        rel = f"outputs/tobe/speckit/specs/{feature}/{nome}"
        if level >= 2:
            # Nivel 2 e o corte mais duro: so o caminho. O indice de um
            # documento com 40 secoes chega a ser MAIOR que o recorte por
            # relevancia do nivel 1 — e reduzir o orcamento nunca pode
            # aumentar o prompt.
            partes.append(f"- `{rel}` (leia em disco a secao que precisar)")
            continue
        corpo = (relevant_sections(texto, termos, limite) if level == 1
                 else _read_limited_text(texto, limite))
        partes.append(f"### {rel}\n\n```markdown\n{corpo}\n```")
    if level >= 2 and partes:
        return ("### Documentos da feature (nao injetados por orcamento)\n\n"
                + "\n".join(partes))
    return "\n\n".join(partes)


def constitution_block(project: str, task: dict[str, Any], level: int,
                       repo_root: Path | None = None) -> str:
    caminho = (_project_dir(project, repo_root) / "outputs" / "tobe" / "speckit"
               / "constitution.md")
    if not caminho.is_file():
        return ""
    texto = caminho.read_text(encoding="utf-8", errors="replace")
    rel = "outputs/tobe/speckit/constitution.md"
    if level >= 2:
        return ("### Documento governante (nao injetado por orcamento)\n\n"
                f"- `{rel}`")
    corpo = relevant_sections(texto, task_terms(task), CONSTITUTION_CHARS)
    return (f"### {rel} (secoes pertinentes — o documento governante)\n\n"
            f"```markdown\n{corpo}\n```")


def cross_cutting_block(project: str, task: dict[str, Any], level: int,
                        repo_root: Path | None = None) -> str:
    if level >= 2:
        return ("### Documentos transversais (nao injetados por orcamento)\n\n"
                + "\n".join(f"- `projects/{project}/{rel}`"
                            for rel in CROSS_CUTTING_DOCS))
    base = _project_dir(project, repo_root)
    termos = task_terms(task)
    partes: list[str] = []
    for rel in CROSS_CUTTING_DOCS:
        caminho = base / rel
        if not caminho.is_file():
            continue
        texto = caminho.read_text(encoding="utf-8", errors="replace")
        if level == 1:
            partes.append(f"### {rel} — indice\n\n"
                          + "\n".join(f"- {h}" for h in headings(texto)[:40]))
        else:
            partes.append(f"### {rel} (secoes pertinentes)\n\n```markdown\n"
                          f"{relevant_sections(texto, termos, DOC_CHARS)}\n```")
    adrs = base / "outputs" / "tobe" / "docs" / "decisions"
    if adrs.is_dir():
        arquivos = sorted(p.name for p in adrs.glob("*.md"))
        if arquivos:
            partes.append("### ADRs em disco (leia sob demanda)\n\n"
                          + "\n".join(f"- `outputs/tobe/docs/decisions/{n}`"
                                      for n in arquivos[:40]))
    return "\n\n".join(partes)


def contracts_block(project: str, task: dict[str, Any], level: int,
                    repo_root: Path | None = None) -> str:
    """OpenAPI só quando a task declara operações de API."""
    ops = [str(o) for o in (task.get("api_ops") or []) if str(o).strip()]
    base = _project_dir(project, repo_root) / "outputs" / "tobe" / "docs" / "openapi"
    if not base.is_dir():
        return ""
    arquivos = sorted(base.glob("*.yaml")) + sorted(base.glob("*.yml"))
    if not arquivos:
        return ""
    if not ops or level >= 2:
        return ("### Contratos OpenAPI em disco (esta task nao declara api_ops)\n\n"
                + "\n".join(f"- `outputs/tobe/docs/openapi/{p.name}`"
                            for p in arquivos[:20]))
    partes = [f"### Operacoes de API desta task: {', '.join(ops[:20])}"]
    orcamento = OPENAPI_CHARS
    for caminho in arquivos:
        if orcamento <= 0:
            break
        texto = caminho.read_text(encoding="utf-8", errors="replace")
        if not any(op.casefold() in texto.casefold() for op in ops):
            continue
        fatia = _read_limited_text(texto, min(orcamento, OPENAPI_CHARS))
        orcamento -= len(fatia)
        partes.append(f"### outputs/tobe/docs/openapi/{caminho.name} "
                      f"(contrato que esta task precisa respeitar)\n\n"
                      f"```yaml\n{fatia}\n```")
    return "\n\n".join(partes)


#: O protótipo é a autoridade sobre *quais* telas existem e *como* cada uma é.
#: `index.html` é o artefato que nunca chegava ao gerador de código — ele é a
#: causa medida do eixo "protótipo 13%". Entra para task de frontend, recortado
#: pela tela da task; para backend fica como referência de caminho.
PROTOTYPE_INDEX = "outputs/tobe/prototype/index.html"
PROTOTYPE_SCREENS = "outputs/tobe/prototype/screen-list.md"
PROTOTYPE_TOKENS = "outputs/tobe/prototype/design-tokens.json"
PROTOTYPE_CHARS = 20_000
TOKENS_CHARS = 4_000

#: Regras de negócio e mapa de API: recortados por `rule_ids`/`api_ops` da task.
RULES_DOCS: tuple[str, ...] = (
    "outputs/tobe/docs/regras-negocio.md",
    "outputs/asis/docs/business-rules.md",
    "outputs/tobe/docs/api-map.md",
    "outputs/tobe/docs/security-architecture.md",
)


def _screen_excerpt(html: str, screen_id: str, limit: int) -> str:
    """Trecho do protótipo em volta da tela da task; senão, o começo do arquivo."""
    if not html:
        return ""
    if screen_id:
        posicao = html.casefold().find(str(screen_id).casefold())
        if posicao >= 0:
            inicio = max(0, posicao - limit // 3)
            return html[inicio:inicio + limit]
    return _read_limited_text(html, limit)


def prototype_block(project: str, task: dict[str, Any], route: Any, level: int,
                    repo_root: Path | None = None) -> str:
    base = _project_dir(project, repo_root)
    caminhos = [PROTOTYPE_INDEX, PROTOTYPE_SCREENS, PROTOTYPE_TOKENS]
    existentes = [rel for rel in caminhos if (base / rel).is_file()]
    if not existentes:
        return ""
    frontend = getattr(route, "component_type", "") == "frontend"
    if not frontend or level >= 2:
        return ("### Prototipo em disco (autoridade sobre telas — leia sob demanda)\n\n"
                + "\n".join(f"- `{rel}`" for rel in existentes))

    partes: list[str] = []
    tela = str(task.get("screen_id") or "")
    if PROTOTYPE_SCREENS in existentes:
        partes.append(f"### {PROTOTYPE_SCREENS}\n\n```markdown\n"
                      f"{_read_limited(base / PROTOTYPE_SCREENS, DOC_CHARS)}\n```")
    if PROTOTYPE_INDEX in existentes:
        html = (base / PROTOTYPE_INDEX).read_text(encoding="utf-8", errors="replace")
        recorte = _screen_excerpt(html, tela, PROTOTYPE_CHARS)
        partes.append(f"### {PROTOTYPE_INDEX}"
                      + (f" (trecho da tela `{tela}`)" if tela else " (inicio)")
                      + f"\n\n```html\n{recorte}\n```")
    if PROTOTYPE_TOKENS in existentes:
        partes.append(f"### {PROTOTYPE_TOKENS}\n\n```json\n"
                      f"{_read_limited(base / PROTOTYPE_TOKENS, TOKENS_CHARS)}\n```")
    return "\n\n".join(partes)


def rules_docs_block(project: str, task: dict[str, Any], level: int,
                     repo_root: Path | None = None) -> str:
    """Regras de negócio e mapa de API — só as seções que a task referencia."""
    base = _project_dir(project, repo_root)
    existentes = [rel for rel in RULES_DOCS if (base / rel).is_file()]
    if not existentes:
        return ""
    if level >= 2:
        return ("### Regras e contratos em disco (nao injetados por orcamento)\n\n"
                + "\n".join(f"- `{rel}`" for rel in existentes))
    termos = task_terms(task) | {str(r) for r in (task.get("rule_ids") or [])}
    partes: list[str] = []
    for rel in existentes:
        texto = (base / rel).read_text(encoding="utf-8", errors="replace")
        if level == 1:
            partes.append(f"### {rel} — indice\n\n"
                          + "\n".join(f"- {h}" for h in headings(texto)[:30]))
        else:
            partes.append(f"### {rel} (secoes pertinentes)\n\n```markdown\n"
                          f"{relevant_sections(texto, termos, DOC_CHARS)}\n```")
    return "\n\n".join(partes)


def tree_block(route: Any, project: str) -> str:
    """Snapshot enxuto da árvore canônica — o que já existe, para não recriar."""
    destino: Path = route.canonical_source_dir
    if not destino.is_dir():
        return (f"### Arvore de `outputs/tobe/{route.canonical_source_rel}/`\n\n"
                f"Diretorio ainda nao existe. Ele e criado pela F4S; se voce "
                f"chegou aqui sem ele, PARE e reporte o bloqueio.")
    ignorar = {".git", "node_modules", "bin", "obj", "dist", ".angular",
               "__pycache__", ".venv", "target", ".f4s"}
    entradas: list[str] = []
    for caminho in sorted(destino.rglob("*")):
        if any(parte in ignorar for parte in caminho.parts):
            continue
        if caminho.is_dir():
            continue
        entradas.append(caminho.relative_to(destino).as_posix())
        if len(entradas) >= SNAPSHOT_ENTRIES:
            break
    total = len(entradas)
    cabecalho = (f"### Arvore atual de `outputs/tobe/{route.canonical_source_rel}/` "
                 f"({total}{'+' if total >= SNAPSHOT_ENTRIES else ''} arquivos)")
    return cabecalho + "\n\n```\n" + "\n".join(entradas) + "\n```"


def previous_attempt_block(task: dict[str, Any], failure_context: str = "") -> str:
    """Erro da tentativa anterior — a matéria-prima da etapa REFLECT."""
    partes: list[str] = []
    evidencia = task.get("evidence") or {}
    if evidencia:
        partes.append(
            "## TENTATIVA ANTERIOR (leia antes de repetir qualquer coisa)\n\n"
            f"- comando: `{evidencia.get('command')}`\n"
            f"- exit code: **{evidencia.get('exit_code')}**\n"
            f"- log: `{evidencia.get('log_path') or '—'}`\n"
            f"- registrado em: {evidencia.get('recorded_at')}")
    historico = task.get("attempt_history") or []
    if len(historico) > 1:
        linhas = ["", "### Historico de tentativas", ""]
        for item in historico[-3:]:
            linhas.append(f"- tentativa {item.get('attempt')}: exit "
                          f"{item.get('exit_code')} — {item.get('summary') or ''}")
        partes.append("\n".join(linhas))
    if failure_context:
        partes.append("## SAIDA REAL DO BUILD QUE FALHOU\n\n"
                      + failure_context[:BUILD_LOG_CHARS])
    return "\n\n".join(partes)


def rules_block(project: str, route: Any) -> str:
    canonico = f"projects/{project}/outputs/tobe/{route.canonical_source_rel}"
    return (
        "## LIMITES DESTA EXECUCAO — OBRIGATORIOS\n\n"
        f"- Escreva EXCLUSIVAMENTE sob `{canonico}/`. Qualquer arquivo fora "
        f"desse diretorio nao entra no commit e invalida a task.\n"
        f"- NUNCA use `source-code/{route.target_stack}/` nem qualquer "
        f"diretorio derivado da tecnologia. A stack e metadado, nao caminho.\n"
        "- Implemente SOMENTE a task acima. As demais tasks tem despacho e "
        "contexto proprios.\n"
        "- NAO recrie estrutura existente: leia a arvore acima e edite o que ja "
        "existe.\n"
        "- NAO leia diretorios inteiros nem carregue o repositorio no contexto.\n"
        "- NAO declare `verified`, `PASS` ou build simulado: quem grava status e "
        "o `task_ledger`, a partir do exit code real do build que o pipeline roda "
        "depois de voce."
    )


# ─── Montagem ────────────────────────────────────────────────────────────────

def build(project: str, task: dict[str, Any], route: Any, *,
          ledger_tasks: list[dict[str, Any]] | None = None,
          attempt: int = 1, level: int = 0, failure_context: str = "",
          repo_root: Path | None = None) -> str:
    """Contexto completo de uma task, respeitando o nível de orçamento."""
    por_id = {t["task_id"]: t for t in (ledger_tasks or [])}
    blocos = [
        task_block(task, route, attempt),
        dependencies_block(task, por_id),
        tree_block(route, project),
        previous_attempt_block(task, failure_context),
        constitution_block(project, task, level, repo_root),
        feature_docs_block(project, task, level, repo_root),
        contracts_block(project, task, level, repo_root),
        prototype_block(project, task, route, level, repo_root),
        rules_docs_block(project, task, level, repo_root),
        cross_cutting_block(project, task, level, repo_root),
        rules_block(project, route),
    ]
    return "\n\n".join(bloco for bloco in blocos if bloco)


def estimate_chars(project: str, task: dict[str, Any], route: Any, **kwargs: Any) -> int:
    return len(build(project, task, route, **kwargs))
