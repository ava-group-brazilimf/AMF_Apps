#!/usr/bin/env python3
"""
AVA Fabric — Manifesto de contexto por passo
=============================================
Resolve **quais artefatos** entram no contexto de um passo da esteira, a partir
de uma declaração explícita, e reprova antes de gastar inferência quando um
insumo obrigatório não está em disco.

O defeito que este módulo corrige (spec 039 §2, P-1)
----------------------------------------------------
``load_context`` — duplicado em ``ava-pipeline-runner-cli.py`` e em ``sdk_engine.py`` —
percorria ``sorted(outputs.rglob("*"))`` e injetava o corpo dos **N primeiros**
arquivos com sufixo em ``(.md, .mmd, .yaml, .json)``. N = 60 no runner de
produção, 30 no motor do CLI. Em ordem alfabética ``asis/`` precede ``tobe/``.

Medido em ``projects/nopcommerce-02-cli-ava`` (185 arquivos elegíveis):

    posições 1..60 injetadas  →  30 de asis/ast-raw/** + 30 de asis/**
    artefatos tobe/ injetados →  ZERO

    api-map.md 116 · architecture-blueprint.md 117 · decision-matrix 118
    backlog-tobe 119 · openapi-spec 144 · regras-negocio 145
    tech-framework 151 · wave-plan 154 · design-tokens 164
    screen-list 167 · test-cases 169
    prototype/index.html — nunca elegível, `.html` fora da allowlist

Ou seja: o gerador de código da F4 nunca recebeu um único artefato TO-BE. Não é
um problema de qualidade de prompt; é entrega de contexto. Este módulo troca a
heurística "os N primeiros em ordem alfabética" por uma allowlist declarada.

Contrato
--------
Cada passo pode declarar, em ``ava-pipeline.yaml`` ou na tabela ``PIPELINE`` do
runner::

    inputs:
      mandatory:
        - "outputs/tobe/docs/architecture-blueprint.md"
        - path: "outputs/tobe/docs/openapi/*.yaml"
          produced_by: "ava-tobe-spec (F2, fase 4.61)"
      advisory:
        - "outputs/tobe/prototype/figma-spec.md"

* ``mandatory`` ausente ⇒ ``blocked=True``; o CLI encerra com exit 2 **sem**
  chamar o modelo, nomeando artefato, produtor e caminho esperado.
* ``advisory`` ausente ⇒ aviso registrado; a execução continua.
* A ordem de injeção é a de **declaração**, nunca a do filesystem.
* Item declarado é entregue independentemente do sufixo — é isso que faz
  ``index.html`` finalmente chegar ao coder. Só binário conhecido é recusado.
* ``base: "workspace"`` resolve a partir da raiz do repositório; o default
  (``project``) resolve a partir de ``projects/{project}/``.

Compatibilidade
---------------
Passo **sem** ``inputs:`` cai no caminho legado, byte a byte igual ao de hoje —
mesma allowlist de sufixos, mesmo teto de corpos, mesma ordem. A migração é
opt-in por passo; nenhuma etapa existente muda de comportamento sozinha. A
fronteira está congelada em ``tests/tools/test_context_manifest.py``.

Uso
---
    from context_manifest import resolve, render, format_missing

    res = resolve(project, step.inputs, cfg)
    if res.blocked:
        raise SystemExit(format_missing(res, step.phase, step.agent, project))
    contexto = render(res)
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

# SCRIPT_DIR = src/shared/tools → parents: shared, src, repo
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]

# Força UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

#: Arquivos do projeto que entram no contexto de **todo** passo, antes de
#: qualquer insumo declarado. Espelha o piso do ``load_context`` original.
_PROJECT_FLOOR = ("context/project-config.yaml", "context/shared-context.md")

#: Sufixos elegíveis no caminho **legado**. Congelado de propósito: mexer aqui
#: mudaria o comportamento de etapas que ninguém revisou. O caminho declarado
#: não usa esta lista — ver ``_BINARY_SUFFIXES``.
_LEGACY_SUFFIXES = (".md", ".mmd", ".yaml", ".json")

#: Binários conhecidos: recusados mesmo quando declarados, com aviso.
_BINARY_SUFFIXES = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".svgz",
    ".pdf", ".zip", ".gz", ".7z", ".rar", ".tar",
    ".dll", ".exe", ".pdb", ".so", ".dylib", ".bin", ".class", ".pyc",
    ".xlsx", ".docx", ".pptx", ".mdb", ".accdb",
})

#: Acima disto, a expansao de um diretorio declarado vira aviso explicito.
#: Nao recusa nada - so nomeia o que acontecia em silencio. A F5 estourava
#: 1M de tokens porque `outputs/tobe/source-code` (diretorio) expandia para a
#: aplicacao inteira, e nenhuma linha do log dizia isso.
_DIR_EXPANSION_WARN = 50

#: Caminhos de amostra por motivo de recusa. Diagnóstico, não inventário.
_SKIP_SAMPLE = 5

#: Motivos de recusa. Chaves estáveis: o resumo renderizado e o
#: `skipped_counts` do JSON de inspeção são lidos por quem opera a esteira.
_R_BUDGET = "orçamento de contexto esgotado"
_R_BINARY = "binário"
_R_BUILD = "artefato de build ou dependência restaurável"
_R_OUTSIDE = "resolve para fora do diretório declarado — recusado"
_R_READ = "falha de leitura"
_R_DUPLICATE = "já injetado por outra declaração"

#: Teto do bloco de avisos no prompt renderizado. **Independente** do orçamento
#: dos corpos: `declared_total_chars` governa conteúdo, este governa metadado.
#: Sem um teto próprio, a contabilidade das recusas cresce com o número de
#: arquivos do projeto — que é justamente a variável que já estourou uma vez.
_WARN_CHARS_MAX = 4_000

#: Diretórios que NUNCA entram na expansão de um diretório declarado. São
#: dependência restaurável ou saída de build: não descrevem o sistema, e são a
#: maior parte dos 40.468 arquivos de `outputs/tobe/source-code`.
#: Não afeta glob explícito — quem escreve `**/bin/*.dll` sabe o que quer.
_BUILD_DIRS = frozenset({
    "bin", "obj", "node_modules", ".git", "dist", "build", "coverage",
    ".vs", ".vscode", ".idea", "__pycache__", ".pytest_cache", ".mypy_cache",
    "packages", "vendor", "target", ".next", ".nuxt", ".angular", ".gradle",
    "TestResults", ".terraform", "venv", ".venv",
})

#: Sufixos de arquivo temporário/cache recusados na expansão de diretório.
_TRANSIENT_SUFFIXES = frozenset({
    ".log", ".tmp", ".temp", ".bak", ".swp", ".cache", ".lock", ".pid",
})

_TRUNC_MARK = "\n\n[... truncado no limite de contexto ...]"


# ─── Estruturas ──────────────────────────────────────────────────────────────

@dataclass
class MissingInput:
    """Um insumo declarado que não existe em disco."""
    pattern: str
    tier: str                      # "mandatory" | "advisory"
    produced_by: str = ""
    expected_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"pattern": self.pattern, "tier": self.tier,
                "produced_by": self.produced_by, "expected_at": self.expected_at}


@dataclass
class LoadedInput:
    """Um artefato efetivamente carregado para o contexto."""
    rel: str                       # caminho relativo à raiz do repo, POSIX
    tier: str
    body: str
    truncated: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {"path": self.rel, "tier": self.tier,
                "chars": len(self.body), "truncated": self.truncated}


@dataclass
class Resolution:
    """Resultado da resolução de contexto de um passo."""
    project: str
    declared: bool                              # veio de `inputs:` ou do fallback
    floor: list[LoadedInput] = field(default_factory=list)
    included: list[LoadedInput] = field(default_factory=list)
    inventory: list[str] = field(default_factory=list)
    missing_mandatory: list[MissingInput] = field(default_factory=list)
    missing_advisory: list[MissingInput] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    preamble: list[str] = field(default_factory=list)
    #: Existência conferida sem injetar corpo — tier `exists`.
    verified: list[str] = field(default_factory=list)
    #: Recusas AGREGADAS por motivo. Um contador, não uma lista de caminhos.
    skipped_counts: dict[str, int] = field(default_factory=dict)
    #: Amostra curta por motivo, só para diagnóstico. Teto em `_SKIP_SAMPLE`.
    skipped_samples: dict[str, list[str]] = field(default_factory=dict)
    #: Censo da resolução: descobertos, considerados, injetados, ignorados.
    stats: dict[str, int] = field(default_factory=dict)

    @property
    def blocked(self) -> bool:
        """Verdadeiro quando o passo não pode rodar. O CLI converte em exit 2."""
        return bool(self.missing_mandatory)

    @property
    def skipped_total(self) -> int:
        return sum(self.skipped_counts.values())

    def bump(self, chave: str, quanto: int = 1) -> None:
        self.stats[chave] = self.stats.get(chave, 0) + quanto

    def as_dict(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "declared": self.declared,
            "blocked": self.blocked,
            "included": [i.as_dict() for i in self.included],
            "verified": list(self.verified),
            "missing_mandatory": [m.as_dict() for m in self.missing_mandatory],
            "missing_advisory": [m.as_dict() for m in self.missing_advisory],
            "warnings": list(self.warnings),
            "skipped_counts": dict(self.skipped_counts),
            "skipped_total": self.skipped_total,
            "stats": dict(self.stats),
            "total_chars": sum(len(i.body) for i in self.floor + self.included),
        }


def _note_skip(res: Resolution, reason: str, rel: str = "") -> None:
    """Registra UMA recusa de forma agregada, nunca uma linha por arquivo.

    Era aqui o defeito que estourou a F6. O caminho antigo fazia
    ``res.warnings.append(f"{rel}: orçamento esgotado")`` para **cada** arquivo
    não injetado; com 40.468 arquivos declarados via diretório, isso produziu
    40.097 linhas / 7,5 MB — 3,8× mais texto que os 2 MB de corpos que o
    orçamento estava protegendo. O guard virou a causa do estouro.

    Agora: um contador por motivo, e no máximo ``_SKIP_SAMPLE`` caminhos de
    amostra. `res.warnings` continua recebendo a amostra — os chamadores que
    inspecionam a lista seguem funcionando —, mas limitada.
    """
    res.skipped_counts[reason] = res.skipped_counts.get(reason, 0) + 1
    amostra = res.skipped_samples.setdefault(reason, [])
    if rel and len(amostra) < _SKIP_SAMPLE:
        amostra.append(rel)
        res.warnings.append(f"{rel}: {reason}")


# ─── Normalização da declaração ──────────────────────────────────────────────

def _normalize_items(raw: Any, tier: str) -> list[dict[str, str]]:
    """Aceita string ou dict; devolve sempre dict com as chaves conhecidas."""
    items: list[dict[str, str]] = []
    for entry in raw or []:
        if isinstance(entry, str):
            items.append({"path": entry, "base": "project", "produced_by": "", "tier": tier})
        elif isinstance(entry, dict) and entry.get("path"):
            items.append({
                "path": str(entry["path"]),
                "base": str(entry.get("base") or "project"),
                "produced_by": str(entry.get("produced_by") or ""),
                "max_chars": entry.get("max_chars"),
                "tier": tier,
            })
        # entrada malformada é ignorada com aviso emitido pelo chamador
    return items


def _base_dir(base: str, project: str, repo_root: Path) -> Path:
    if base == "workspace":
        return repo_root
    return repo_root / "projects" / project


def _floor_names(step_inputs: Any) -> tuple[str, ...]:
    """Piso do passo: `floor:` declarado vence o default; `floor: []` remove.

    Existe porque `context/shared-context.md` — prosa longa que repete, em
    formato narrativo, o que os artefatos já dizem — é peso morto em passos que
    declaram exatamente de que precisam. Sem esta chave, o único jeito de tirá-lo
    seria mudar o piso de TODA a esteira. Ausente a chave, nada muda.
    """
    if isinstance(step_inputs, dict) and "floor" in step_inputs:
        bruto = step_inputs.get("floor")
        if bruto is None:
            return ()
        if isinstance(bruto, (list, tuple)):
            return tuple(str(x).replace("\\", "/") for x in bruto)
    return _PROJECT_FLOOR


def _is_build_artifact(path: Path, root: Path) -> bool:
    """True para arquivo sob diretório de build/dependência, ou temporário."""
    try:
        partes = path.relative_to(root).parts
    except ValueError:
        partes = path.parts
    if any(parte in _BUILD_DIRS for parte in partes[:-1]):
        return True
    return path.suffix.lower() in _TRANSIENT_SUFFIXES


def _expand(item: dict[str, Any], project: str, repo_root: Path,
            res: "Resolution | None" = None) -> list[Path] | None:
    """Expande um item em caminhos existentes. ``None`` = nada encontrado.

    Um item que aponta para DIRETÓRIO vira a árvore inteira. É legítimo para
    `outputs/tobe/docs/decisions` (dezenas de ADRs) e catastrófico para
    `outputs/tobe/source-code` (a aplicação gerada: 40.468 arquivos / 379 MB no
    `meu-erp-03`). Duas defesas, ambas só na expansão de DIRETÓRIO:

    * `bin/`, `obj/`, `node_modules/`, `dist/`, `.git/`… saem antes de qualquer
      leitura — são dependência restaurável e saída de build, nunca descrevem o
      sistema. Glob explícito não é afetado: quem escreve `**/bin/*.dll` sabe o
      que quer.
    * expansão acima de `_DIR_EXPANSION_WARN` vira aviso nomeado.
    """
    base = _base_dir(item.get("base", "project"), project, repo_root)
    pattern = item["path"].replace("\\", "/")

    if any(ch in pattern for ch in "*?["):
        matches = sorted(p for p in base.glob(pattern) if p.is_file())
        if res is not None:
            res.bump("discovered", len(matches))
            res.bump("considered", len(matches))
        return matches or None

    target = base / pattern
    if target.is_dir():
        brutos = sorted(p for p in target.rglob("*") if p.is_file())
        matches = [p for p in brutos if not _is_build_artifact(p, target)]
        descartados = len(brutos) - len(matches)
        if res is not None:
            res.bump("discovered", len(brutos))
            res.bump("considered", len(matches))
            for _ in range(descartados):
                _note_skip(res, _R_BUILD)
            if len(matches) > _DIR_EXPANSION_WARN:
                res.warnings.append(
                    f"{pattern}: diretório declarado expandiu para {len(matches)} "
                    f"arquivo(s) elegíveis (de {len(brutos)} em disco) — o corpo de "
                    f"cada um entra no prompt até esgotar o orçamento; declare os "
                    f"arquivos necessários, ou use o tier `exists`, em vez do diretório")
        return matches or None
    if res is not None and target.is_file():
        res.bump("discovered")
        res.bump("considered")
    return [target] if target.is_file() else None


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _rel(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _read(path: Path, limit: int) -> tuple[str, bool]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    if len(text) > limit:
        return text[:limit], True
    return text, False


# ─── Resolução ───────────────────────────────────────────────────────────────

def resolve(project: str, step_inputs: dict[str, Any] | None,
            cfg: dict[str, Any], repo_root: Path | None = None,
            preamble: Iterable[str] = ()) -> Resolution:
    """Resolve o contexto de um passo.

    ``step_inputs`` vindo vazio ou ``None`` cai no caminho legado — o mesmo
    comportamento de hoje, preservado para não mudar etapas não migradas.
    """
    root = repo_root or REPO_ROOT
    ctx = cfg.get("context") or {}
    res = Resolution(project=project, declared=bool(step_inputs and (
        step_inputs.get("mandatory") or step_inputs.get("advisory")
        or step_inputs.get("exists"))))
    res.preamble = list(preamble)

    proj_dir = root / "projects" / project
    file_chars = int(ctx.get("file_chars", 500_000))

    # Piso: config do projeto e contexto compartilhado, em todo passo — salvo
    # quando o passo declara o próprio `floor:`.
    floor_rels: set[str] = set()
    for name in _floor_names(step_inputs):
        fpath = proj_dir / name
        if fpath.is_file():
            body, trunc = _read(fpath, file_chars)
            res.floor.append(LoadedInput(rel=name, tier="floor", body=body, truncated=trunc))
            floor_rels.add(_rel(fpath, root))

    if res.declared:
        # `exists` roda ANTES dos tiers que injetam: é gate, não contexto. Um
        # insumo ausente aqui já reprova o passo sem que nada tenha sido lido.
        _resolve_exists(res, step_inputs or {}, project, root)
        _resolve_declared(res, step_inputs or {}, project, root, ctx,
                          floor_rels=floor_rels)
    else:
        _resolve_legacy(res, proj_dir, root, cfg, ctx)

    res.bump("injected", len(res.included))
    res.bump("floor_files", len(res.floor))
    res.bump("skipped", res.skipped_total)
    return res


def _resolve_exists(res: Resolution, step_inputs: dict[str, Any],
                    project: str, root: Path) -> None:
    """Tier ``exists``: confere presença e população — **nunca injeta corpo**.

    Separa duas perguntas que o manifesto antigo confundia: *"a F4 rodou?"* e
    *"o modelo precisa ler isto?"*. O gate da F6 quer a primeira, e respondê-la
    despejando 379 MB de código no prompt foi o defeito.

    Um item ``dir/**`` exige diretório existente e NÃO vazio; sem `**`, exige o
    arquivo. Ausência conta como `missing_mandatory` — o passo reprova antes de
    gastar inferência, com o mesmo caminho de erro dos demais obrigatórios.
    """
    for item in _normalize_items(step_inputs.get("exists"), "exists"):
        base = _base_dir(item.get("base", "project"), project, root)
        padrao = item["path"].replace("\\", "/")
        alvo = base / padrao[:-3] if padrao.endswith("/**") else base / padrao

        if padrao.endswith("/**"):
            ok = alvo.is_dir() and any(
                p.is_file() and not _is_build_artifact(p, alvo)
                for p in alvo.rglob("*"))
            detalhe = "diretório ausente ou vazio"
        else:
            ok = alvo.is_file() or alvo.is_dir()
            detalhe = "arquivo ausente"

        if ok:
            res.verified.append(padrao)
            res.bump("verified")
        else:
            res.missing_mandatory.append(MissingInput(
                pattern=padrao, tier="exists",
                produced_by=item.get("produced_by", ""),
                expected_at=f"{_rel(alvo, root)}  ({detalhe})"))


def _resolve_declared(res: Resolution, step_inputs: dict[str, Any],
                      project: str, root: Path, ctx: dict[str, Any],
                      floor_rels: set[str] | None = None) -> None:
    body_chars = int(ctx.get("declared_body_chars", 400_000))
    total_chars = int(ctx.get("declared_total_chars", 2_000_000))

    items = (_normalize_items(step_inputs.get("mandatory"), "mandatory")
             + _normalize_items(step_inputs.get("advisory"), "advisory"))

    # Arquivo já entregue pelo piso não é injetado de novo: conteúdo duplicado
    # gasta orçamento e ainda dá ao modelo duas cópias da mesma verdade.
    seen: set[str] = set(floor_rels or ())
    used = sum(len(i.body) for i in res.floor)

    for item in items:
        tier = item["tier"]
        base = _base_dir(item.get("base", "project"), project, root)
        matches = _expand(item, project, root, res)

        if not matches:
            missing = MissingInput(
                pattern=item["path"], tier=tier,
                produced_by=item.get("produced_by", ""),
                expected_at=_rel(base / item["path"].replace("\\", "/"), root),
            )
            (res.missing_mandatory if tier == "mandatory"
             else res.missing_advisory).append(missing)
            continue

        for path in matches:
            if not _is_inside(path, base):
                _note_skip(res, _R_OUTSIDE, item["path"])
                continue

            rel = _rel(path, root)
            if rel in seen:
                _note_skip(res, _R_DUPLICATE)
                continue
            seen.add(rel)

            if path.suffix.lower() in _BINARY_SUFFIXES:
                _note_skip(res, _R_BINARY, rel)
                continue

            limit = int(item.get("max_chars") or body_chars)
            if used >= total_chars:
                # Um contador, não uma linha por arquivo. Ver `_note_skip`.
                _note_skip(res, _R_BUDGET, rel)
                continue
            limit = min(limit, total_chars - used)

            try:
                body, trunc = _read(path, limit)
            except OSError as exc:
                _note_skip(res, f"{_R_READ} ({type(exc).__name__})", rel)
                continue

            used += len(body)
            res.included.append(LoadedInput(rel=rel, tier=tier, body=body, truncated=trunc))


def _resolve_legacy(res: Resolution, proj_dir: Path, root: Path,
                    cfg: dict[str, Any], ctx: dict[str, Any]) -> None:
    """Caminho de compatibilidade — idêntico ao ``load_context`` original.

    Mantido byte a byte de propósito: corrigir a heurística aqui mudaria o
    comportamento de todas as etapas ainda não migradas, sem revisão.
    """
    max_arts = int(ctx.get("max_artifacts", 500))
    max_bodies = int(ctx.get("max_artifact_bodies", 30))
    body_chars = int(ctx.get("artifact_body_chars", 20_000))
    out_subdir = (cfg.get("execution") or {}).get("output_subdir", "outputs/pipeline_runner")

    out_root = proj_dir / "outputs"
    if not out_root.is_dir():
        return

    skip = (proj_dir / out_subdir).resolve()
    for path in sorted(out_root.rglob("*")):
        if not path.is_file() or skip in path.resolve().parents:
            continue
        res.inventory.append(_rel(path, root))
        if path.suffix in _LEGACY_SUFFIXES and len(res.included) < max_bodies:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if text.strip():
                res.included.append(LoadedInput(
                    rel=_rel(path, root), tier="legacy",
                    body=text[:body_chars], truncated=len(text) > body_chars))
    res.inventory = res.inventory[:max_arts]


# ─── Renderização ────────────────────────────────────────────────────────────

def render(res: Resolution) -> str:
    """Monta o bloco de contexto injetado no system prompt."""
    parts: list[str] = []

    if res.preamble:
        parts.append("## ESTADO DA EXECUÇÃO\n\n" + "\n\n".join(res.preamble))

    for item in res.floor:
        body = item.body + (_TRUNC_MARK if item.truncated else "")
        parts.append(f"### {item.rel}\n```\n{body}\n```")

    if res.declared:
        if res.included:
            blocos = []
            for item in res.included:
                marca = " (obrigatório)" if item.tier == "mandatory" else " (complementar)"
                body = item.body + (_TRUNC_MARK if item.truncated else "")
                blocos.append(f"### {item.rel}{marca}\n```\n{body}\n```")
            parts.append("## INSUMOS DECLARADOS DESTE PASSO\n\n" + "\n\n".join(blocos))
        if res.missing_advisory:
            linhas = [f"- {m.pattern}"
                      + (f" — produzido por {m.produced_by}" if m.produced_by else "")
                      for m in res.missing_advisory]
            parts.append(
                "## INSUMOS COMPLEMENTARES AUSENTES\n\n"
                "Estes artefatos foram declarados como complementares e não existem em disco.\n"
                "Registre a degradação no artefato de saída — nunca invente o conteúdo.\n\n"
                + "\n".join(linhas))
    else:
        if res.inventory:
            parts.append("### Artefatos já existentes em outputs/\n" + "\n".join(res.inventory))
        if res.included:
            blocos = [f"### {i.rel}\n```\n{i.body}\n```" for i in res.included]
            parts.append("## Conteúdo dos Artefatos Gerados\n\n" + "\n\n".join(blocos))

    if res.verified:
        parts.append(
            "## INSUMOS CONFERIDOS (existência, sem injeção de conteúdo)\n\n"
            "Estes caminhos existem em disco e estão populados. O conteúdo **não** foi\n"
            "injetado de propósito: leia sob demanda apenas o que a tarefa exigir.\n\n"
            + "\n".join(f"- `{v}`" for v in res.verified))

    resumo = render_warnings(res)
    if resumo:
        parts.append(resumo)

    return "\n\n".join(parts) if parts else "[Sem contexto disponível]"


def context_census(res: Resolution) -> dict[str, int]:
    """Métricas de contexto do passo, em chars e em contagem de arquivos.

    Serve ao registro por passo/tarefa: é a régua que mostra, sem adivinhação,
    de onde vieram os chars que foram para o prompt.
    """
    piso = sum(len(i.body) for i in res.floor)
    corpos = sum(len(i.body) for i in res.included)
    avisos = len(render_warnings(res))
    total = len(render(res))
    return {
        "floor_chars": piso,
        "body_chars": corpos,
        "warning_chars": avisos,
        "frame_chars": max(0, total - piso - corpos - avisos),
        "total_chars": total,
        "files_discovered": res.stats.get("discovered", 0),
        "files_considered": res.stats.get("considered", 0),
        "files_injected": len(res.included),
        "files_verified": len(res.verified),
        "files_skipped": res.skipped_total,
    }


def render_warnings(res: Resolution) -> str:
    """Bloco de avisos AGREGADO, com teto próprio de caracteres.

    O bloco antigo era `"\\n".join(res.warnings)` sem teto algum: na F6 do
    `meu-erp-03` isso rendeu 40.097 linhas / 7,5 MB — mais que triplicando um
    prompt cujos corpos cabiam nos 2 MB do orçamento. Aqui o custo é O(motivos),
    não O(arquivos), e ainda assim cortado em `_WARN_CHARS_MAX`.
    """
    if not (res.warnings or res.skipped_counts or res.stats):
        return ""

    linhas: list[str] = ["## RESUMO DE CONTEXTO", ""]
    censo = [
        ("descobertos", res.stats.get("discovered", 0)),
        ("considerados", res.stats.get("considered", 0)),
        ("injetados", len(res.included)),
        ("conferidos sem injeção", len(res.verified)),
        ("ignorados", res.skipped_total),
    ]
    linhas += [f"- {nome}: {valor:,} arquivo(s)".replace(",", ".")
               for nome, valor in censo if valor]

    if res.skipped_counts:
        linhas += ["", "### Não injetados, por motivo", ""]
        for motivo, quantos in sorted(res.skipped_counts.items(),
                                      key=lambda kv: -kv[1]):
            amostra = res.skipped_samples.get(motivo) or []
            sufixo = (f"  (ex.: {', '.join(a.rsplit('/', 1)[-1] for a in amostra[:3])}…)"
                      if amostra else "")
            linhas.append(f"- {quantos:,} arquivo(s) — {motivo}{sufixo}".replace(",", "."))

    # Avisos singulares (manifesto malformado, diretório enorme declarado…).
    # A amostra por motivo já entrou em `res.warnings` via `_note_skip`; aqui
    # ela é redundante, então só entram os avisos que não têm contador.
    motivos = set(res.skipped_counts)
    singulares = [w for w in res.warnings
                  if not any(w.endswith(m) for m in motivos)]
    if singulares:
        linhas += ["", "### Avisos", ""]
        linhas += [f"- {w}" for w in singulares]

    bloco = "\n".join(linhas)
    if len(bloco) > _WARN_CHARS_MAX:
        bloco = (bloco[:_WARN_CHARS_MAX]
                 + f"\n[... resumo de contexto truncado em {_WARN_CHARS_MAX} chars ...]")
    return bloco


def format_missing(res: Resolution, phase: str, agent: str, project: str) -> str:
    """Mensagem acionável para o operador — o que faltou e quem produz."""
    linhas = [f"insumo obrigatório ausente no passo {phase} ({agent}), projeto {project}:", ""]
    for m in res.missing_mandatory:
        linhas.append(f"  - {m.pattern}")
        if m.produced_by:
            linhas.append(f"      produzido por: {m.produced_by}")
        linhas.append(f"      esperado em:   {m.expected_at}")
    linhas += [
        "",
        "  O passo não foi despachado — nenhuma inferência foi gasta.",
        "  Rode a fase produtora antes, ou ajuste `inputs.mandatory` do passo em",
        "  src/shared/data/ava-pipeline.yaml se o artefato deixou de ser obrigatório.",
    ]
    return "\n".join(linhas)


# ─── CLI de inspeção ─────────────────────────────────────────────────────────

def _main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        prog="python src/shared/tools/context_manifest.py",
        description="Inspeciona o contexto que um passo receberia — custo zero de inferência.")
    parser.add_argument("-p", "--project", required=True)
    parser.add_argument("--phase", help="etapa da esteira; sem ela, inspeciona o caminho legado")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    sys.path.insert(0, str(SCRIPT_DIR))
    import pipeline_config  # noqa: PLC0415
    import pipeline_plan    # noqa: PLC0415

    cfg = pipeline_config.load_config(args.project)
    step_inputs = None
    if args.phase:
        for step in pipeline_plan.declared_steps(cfg):
            if step.phase == args.phase or step.group == args.phase:
                step_inputs = step.inputs
                break

    res = resolve(args.project, step_inputs, cfg)
    if args.json:
        print(json.dumps(res.as_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"projeto: {res.project} · declarado: {res.declared} · bloqueado: {res.blocked}")
        for item in res.included:
            print(f"  [{item.tier:9}] {item.rel} ({len(item.body):,} chars)")
        for m in res.missing_mandatory:
            print(f"  [AUSENTE ] {m.pattern}")
        for w in res.warnings:
            print(f"  [aviso   ] {w}")
    return 2 if res.blocked else 0


if __name__ == "__main__":
    raise SystemExit(_main())
