#!/usr/bin/env python3
"""
validate_language_agnostic.py — Impede que regra geral vire regra de uma linguagem.

Por que isto existe
-------------------
`AGENTS.md` é herdado por **todos** os agentes, em todas as fases, para qualquer
linguagem legada (delphi, java, .net, cobol, vb6, powerbuilder, o que vier). Uma
única constante de tecnologia ali contamina a esteira inteira.

O repo já demonstra o problema: `shared/backend-context-protocol.md` tem nome
genérico e conteúdo .NET; `shared/mermaid-guardrails.md` aplica a tudo e carrega
exemplos Delphi; `orchestrator-asis.md:2075` declara uma fase **obrigatória**
(`## Delphi Backup Cleanup`) travada numa linguagem. Sem gate, a limpeza regride
na primeira PR.

Allowlist, não denylist
-----------------------
`shared/dotnet-research-instructions.md` legitimamente contém `dotnet` — é um
arquivo por-stack. Uma denylist global reprovaria o repo inteiro e seria desligada
na primeira semana. Aqui só os alvos declarados são varridos, e caminhos
legitimamente específicos entram em `ALLOWLIST`.

Uso
---
    python src/shared/utils/validate_language_agnostic.py --report
    python src/shared/utils/validate_language_agnostic.py --strict
    python src/shared/utils/validate_language_agnostic.py --report --paths AGENTS.md .github/agents

Exit codes: 0 sem violação (ou `--report`) · 1 violações em `--strict` · 2 erro de uso.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[3]

#: Alvos padrão — o que esta spec (033) se compromete a manter agnóstico.
#: A limpeza dos demais arquivos contaminados está mapeada em
#: `specs/033-agent-isolation-context-engineering/spec.md` § 7 e é follow-on.
DEFAULT_TARGETS = ["AGENTS.md", ".github/agents"]

#: Tecnologias legadas e stacks alvo que não podem aparecer numa regra geral.
#:
#: `\b` em volta para não casar dentro de palavra ("javascript" não é "java").
#: Cuidado com as extensões: `\b\.pas` **nunca** casa, porque entre um espaço e um
#: ponto não existe fronteira de palavra — ambos são não-word. Por isso as
#: alternativas iniciadas por ponto usam `(?<![\w.])` em vez de `\b`.
LANGUAGE_PATTERNS: dict[str, str] = {
    "delphi": r"\bdelphi\b",
    "vb6": r"\bvb6\b",
    "vbnet": r"\bvb\.?net\b",
    "cobol": r"\bcobol\b",
    "powerbuilder": r"\bpower ?builder\b",
    "dotnet": r"(?:\bdotnet\b|(?<![\w.])\.net\b)",
    "java": r"\bjava\b(?!script)",
    "pascal": r"(?:\bpascal\b|(?<![\w.])\.(?:pas|dfm|dpr)\b)",
    "angular": r"\bangular\b",
    "efcore": r"\b(?:ef ?core|entity ?framework)\b",
    "mediatr": r"\bmediatr\b",
    "spring": r"\bspring ?boot\b",
}

#: Caminhos (prefixo repo-relativo) legitimamente específicos de tecnologia, ou
#: fora do escopo da esteira. Um wrapper de agente de solução **precisa** nomear a
#: linguagem dele; os `speckit.*` são tooling do Spec Kit, não agentes AVA.
ALLOWLIST: tuple[str, ...] = (
    ".github/agents/speckit.",
    ".github/agents/ava-asis-solution-",
    ".github/agents/ava-coder-",
    ".github/agents/ava-stack-",
    ".github/agents/ava-build-cycle-",
    ".github/agents/ava-dotnet-",
    "src/shared/data/languages/",
    "src/shared/data/stacks/",
)

#: Linhas ignoradas em qualquer arquivo: referência a caminho de dados por
#: linguagem é resolução em runtime, não constante de regra.
LINE_EXEMPTIONS: tuple[str, ...] = (
    r"\{legacy_technology\}",
    r"\{language\}",
)


def is_allowlisted(rel_path: str) -> bool:
    return any(rel_path.startswith(prefix) for prefix in ALLOWLIST)


def _rel(path: Path) -> str:
    """Caminho repo-relativo, ou absoluto se o arquivo estiver fora da árvore.

    Arquivos fora do repo aparecem quando o lint é chamado com `--paths` apontando
    para outro lugar (ou por um teste, com um `tmp_path`). Estourar aqui
    transformaria um lint em erro fatal.
    """
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _line_exempt(line: str) -> bool:
    return any(re.search(pattern, line) for pattern in LINE_EXEMPTIONS)


def iter_files(targets: list[str]) -> list[Path]:
    """Arquivos `.md`/`.yaml`/`.yml` sob os alvos, ordenados e sem allowlistados."""
    files: list[Path] = []
    for target in targets:
        path = (REPO_ROOT / target).resolve()
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            for suffix in ("*.md", "*.yaml", "*.yml"):
                files.extend(sorted(path.rglob(suffix)))
        else:
            print(f"⚠️  alvo inexistente, ignorado: {target}", file=sys.stderr)

    result: list[Path] = []
    for path in sorted(set(files)):
        if not is_allowlisted(_rel(path)):
            result.append(path)
    return result


def scan(files: list[Path]) -> list[dict[str, object]]:
    """`[{path, line, technology, text}]` para cada ocorrência não isenta."""
    violations: list[dict[str, object]] = []
    compiled = {tech: re.compile(pattern, re.IGNORECASE)
                for tech, pattern in LANGUAGE_PATTERNS.items()}

    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        rel = _rel(path)
        for number, line in enumerate(text.splitlines(), start=1):
            if _line_exempt(line):
                continue
            for tech, regex in compiled.items():
                if regex.search(line):
                    violations.append({
                        "path": rel,
                        "line": number,
                        "technology": tech,
                        "text": line.strip()[:120],
                    })
    return violations


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="validate_language_agnostic.py",
        description="Reprova constantes de tecnologia em arquivos que devem ser genéricos",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--report", action="store_true",
                      help="Lista as violações sem falhar (mede a dívida)")
    mode.add_argument("--strict", action="store_true",
                      help="Exit 1 se houver qualquer violação (CI)")
    parser.add_argument("--paths", nargs="+", default=None,
                        help=f"Alvos a varrer (default: {' '.join(DEFAULT_TARGETS)})")
    args = parser.parse_args()

    if not args.report and not args.strict:
        args.report = True

    targets = args.paths or DEFAULT_TARGETS
    files = iter_files(targets)
    if not files:
        print("❌ nenhum arquivo para varrer", file=sys.stderr)
        raise SystemExit(2)

    violations = scan(files)
    if not violations:
        print(f"✅ {len(files)} arquivo(s) varrido(s) — nenhuma constante de tecnologia")
        return

    by_path: dict[str, list[dict[str, object]]] = {}
    for violation in violations:
        by_path.setdefault(str(violation["path"]), []).append(violation)

    stream = sys.stderr if args.strict else sys.stdout
    icon = "❌" if args.strict else "⚠️ "
    print(f"{icon} {len(violations)} violação(ões) em {len(by_path)} arquivo(s) "
          f"de {len(files)} varrido(s):", file=stream)
    for path, items in sorted(by_path.items()):
        print(f"\n   {path}", file=stream)
        for item in items:
            print(f"      L{item['line']:<5} [{item['technology']}] {item['text']}", file=stream)

    print(
        "\n   Regra geral não nomeia tecnologia. Resolva por "
        "`project-config.yaml → legacy_technology`, ou mova a instrução para a "
        "spec do agente daquela tecnologia.",
        file=stream,
    )
    if args.strict:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
