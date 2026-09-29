#!/usr/bin/env python3
"""
generate_agent_wrappers.py — Gera os custom agents do GitHub Copilot CLI.

Por que isto existe
-------------------
A esteira tem 102 agentes despacháveis e, antes desta ferramenta, **1** wrapper em
`.github/agents/` — escrito à mão. Os outros 101 só eram alcançáveis por dispatch
textual (`@nome`), que **falha em silêncio**: os logs registram
`tool.execution_complete success:false, "Skill not found: ava-qa-orchestrator"` e a
sessão "cai para execução direta", produzindo artefato nenhum.

Escrever 102 wrappers à mão recriaria exatamente o modo de falha que originou o
`agent_registry.py` ("52 de 101 agentes ausentes, 18 versões divergentes",
specs/032). Por isso o wrapper é **derivado** do registry, nunca digitado.

Fatos de runtime que este gerador obedece
-----------------------------------------
Medidos no spike M0 (`docs/copilot-cli-runtime-facts.md`, Copilot CLI 1.0.77):

* `tools:` é **enforçado de verdade** — um agente sem `view` não consegue ler
  arquivo ("I don't have a `view` tool available in this environment").
* `version:` e `allowed-tools:` são **descartados** com
  `[WARNING] unknown fields ignored: version, allowed-tools`. O frontmatter atual
  dos 107 agentes usa exatamente essas duas chaves — emiti-las produziria wrappers
  sem restrição de tool e sem versão. A versão vai em `metadata.version`.
* A tool de shell chama-se **`powershell`**, não `bash`.
* O corpo do `.agent.md` tem cap de **30.000 caracteres**; 37 das 107 specs
  estouram. Por isso o wrapper é um ponteiro fino (~2 KB) e a spec real chega por
  `view` explícito.
* `--no-custom-instructions` (−11.372 tokens, a maior economia medida) **desliga o
  carregamento do `AGENTS.md`**. Daí a injeção do bloco `AGENTS-CORE`: a regra
  continua vindo de uma fonte única, mas é cobrada só na janela do agente que a usa.

Uso
---
    python src/shared/tools/generate_agent_wrappers.py                 # gera todos
    python src/shared/tools/generate_agent_wrappers.py --phase F1      # só uma fase
    python src/shared/tools/generate_agent_wrappers.py --check         # CI: exit 1 se drift
    python src/shared/tools/generate_agent_wrappers.py --dry-run       # não escreve nada

Exit codes: 0 OK · 1 drift/erro de geração · 2 erro de uso ou preflight.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent

sys.path.insert(0, str(SCRIPT_DIR))
import agent_registry  # noqa: E402

AGENTS_MD = REPO_ROOT / "AGENTS.md"
OUT_DIR = REPO_ROOT / ".github" / "agents"
USER_AGENTS_DIR = Path.home() / ".copilot" / "agents"

#: Cap verificado no M0. Hard fail — não truncar.
BODY_CHAR_CAP = 30_000

#: Delimitadores do trecho herdável do AGENTS.md.
CORE_START = "<!-- AGENTS-CORE:START -->"
CORE_END = "<!-- AGENTS-CORE:END -->"

#: Nomes das tools nas specs canônicas → nomes reais do Copilot CLI (M0 § 5).
#: Vivia em `agent_runner.py` sem uso; a casa dele é aqui.
TOOL_NAME_MAP: dict[str, str] = {
    "Read": "view",
    "Write": "create",
    "Edit": "edit",
    "Glob": "glob",
    "Grep": "grep",
    "Bash": "powershell",
    "WebFetch": "web_fetch",
    "WebSearch": "web_search",
    # Variantes presentes no repo. `Run` aparece em `azure-infra-estimator-tobe.md`
    # com a mesma intenção de `Bash` (executar script de estimativa).
    "Run": "powershell",
    # Nomes da superfície do Copilot no VS Code, usados por `build-fixer-agent.md`
    # e `docs-researcher-agent.md`.
    "fetch_webpage": "web_fetch",
    # Tools sem equivalente no CLI. Mapeadas para vazio (descartadas) em vez de
    # vazarem um nome inválido, que o CLI aceitaria deixando o agente sem a tool,
    # sem avisar.
    #   github_text_search: vem do github-mcp-server, que o runner remove com
    #                       `--disable-builtin-mcps`.
    #   TodoWrite/Task/NotebookEdit: só existem na superfície Claude Code.
    "github_text_search": "",
    "TodoWrite": "",
    "Task": "",
    "NotebookEdit": "",
}

#: Fallback quando a spec não declara `allowed-tools`. Read-only: é o menor grant
#: que ainda permite ler a própria spec — nunca conceder escrita por omissão.
DEFAULT_TOOLS = ["view", "glob", "grep"]

#: Pinado. Sem pin o sub-agente cai em `gpt-5.4` e a chamada retorna 404 contra o
#: provider BYOK (M0 — bug de roteamento de modelo).
DEFAULT_MODEL = "claude-sonnet-4"

_FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.DOTALL)

GENERATED_HEADER = "GERADO por src/shared/tools/generate_agent_wrappers.py — não editar à mão."


# ─── Leitura das fontes ──────────────────────────────────────────────────────

def read_agents_core() -> str:
    """Trecho herdável do AGENTS.md, entre os delimitadores AGENTS-CORE.

    Falha dura se o arquivo ou os delimitadores não existirem: gerar wrappers sem
    os guardrails é pior que não gerar.
    """
    if not AGENTS_MD.is_file():
        raise SystemExit(f"❌ AGENTS.md não encontrado em {AGENTS_MD}")
    text = AGENTS_MD.read_text(encoding="utf-8")
    if text.count(CORE_START) != 1 or text.count(CORE_END) != 1:
        raise SystemExit(
            f"❌ AGENTS.md deve conter exatamente um par {CORE_START} / {CORE_END}"
        )
    start = text.index(CORE_START) + len(CORE_START)
    end = text.index(CORE_END)
    core = text[start:end].strip()
    if not core:
        raise SystemExit("❌ bloco AGENTS-CORE vazio em AGENTS.md")
    return core


def parse_description(spec_text: str) -> str:
    """Description do frontmatter da spec canônica, colapsada em uma linha.

    O `description` é obrigatório no schema do CLI e dirige a seleção por
    inferência quando o agente é invocado por delegação nativa. As specs usam
    `description: |` com várias linhas e um `Ativa com: "..."` no fim; aqui isso
    vira uma frase só, porque o valor entra em YAML inline.
    """
    match = _FRONTMATTER_RE.search(spec_text)
    if not match:
        return ""
    block = match.group(1)
    lines = block.splitlines()

    collected: list[str] = []
    for index, line in enumerate(lines):
        if not re.match(r"^description:\s*", line):
            continue
        inline = re.sub(r"^description:\s*", "", line).strip()
        if inline and inline not in ("|", ">", "|-", ">-", "|+", ">+"):
            collected.append(inline)
            break
        # Bloco literal: consome as linhas indentadas seguintes.
        for follow in lines[index + 1:]:
            if follow.strip() and not follow.startswith((" ", "\t")):
                break
            collected.append(follow.strip())
        break

    text = " ".join(part for part in collected if part)
    text = text.strip().strip('"').strip("'")
    text = re.sub(r"\s+", " ", text)
    return _condense_description(text)


#: Teto do `description` no wrapper. O valor entra no prompt de sistema de todo
#: processo que carrega o agente, e várias specs usam o campo como changelog —
#: `orchestrator-asis.md` tem 2,6 KB de histórico de versão ali. Manter só o que
#: dirige a seleção: a primeira frase de responsabilidade + as frases de ativação.
_LEAD_CHAR_CAP = 260
_TRIGGER_CHAR_CAP = 220


def _truncate_on_boundary(text: str, cap: int) -> str:
    """Corta em fronteira de palavra, com reticências, se passar de ``cap``."""
    if len(text) <= cap:
        return text
    cut = text[:cap].rsplit(" ", 1)[0].rstrip(" ,;:-")
    return f"{cut}…"


def _condense_description(text: str) -> str:
    """Responsabilidade + frases de ativação, dentro do teto.

    O trecho ``Ativa com: "..."`` é o que dirige a seleção por inferência quando o
    agente é invocado por delegação nativa, então é preservado mesmo quando o
    corpo da descrição é cortado.
    """
    if not text:
        return ""

    triggers = ""
    match = re.search(r"(Ativa com:.*)$", text, re.IGNORECASE | re.DOTALL)
    if match:
        triggers = re.sub(r"\s+", " ", match.group(1)).strip()
        text = text[: match.start()].strip()

    # Descarta o ruído de changelog embutido na descrição ("v2.19: …", "v1.5: …").
    text = re.split(r"\s(?=v\d+\.\d+[.:])", text)[0].strip()

    lead = _truncate_on_boundary(text, _LEAD_CHAR_CAP)
    if not triggers:
        return lead
    return f"{lead} {_truncate_on_boundary(triggers, _TRIGGER_CHAR_CAP)}".strip()


def map_tools(allowed: list[str]) -> list[str]:
    """`allowed-tools` da spec → nomes reais das tools do CLI, sem duplicatas."""
    mapped: list[str] = []
    for raw in allowed:
        name = TOOL_NAME_MAP.get(raw.strip(), "")
        if name and name not in mapped:
            mapped.append(name)
    return mapped or list(DEFAULT_TOOLS)


# ─── Contexto opcional (fatia e contrato de saída) ───────────────────────────

def load_optional_context() -> tuple[dict[str, Any], dict[str, Any]]:
    """`AGENT_ARTIFACT_SLICE` e `ARTIFACT_CONTRACTS`, se importáveis.

    Ambos vivem em `asis-diagnostic/utils` e cobrem principalmente a F1. A
    ausência não é erro — o wrapper simplesmente omite a seção de estratégia de
    contexto. Import defensivo, convenção do repo.
    """
    slice_map: dict[str, Any] = {}
    contracts: dict[str, Any] = {}
    utils = REPO_ROOT / "src" / "modules" / "ava-fabric-agents" / "asis-diagnostic" / "utils"
    if not utils.is_dir():
        return slice_map, contracts
    sys.path.insert(0, str(utils))
    try:
        import context_budget  # type: ignore

        slice_map = dict(getattr(context_budget, "AGENT_ARTIFACT_SLICE", {}) or {})
    except Exception as exc:  # noqa: BLE001 - contexto é enriquecimento, não requisito
        print(f"   ⚠️  AGENT_ARTIFACT_SLICE indisponível: {exc}")
    try:
        import artifact_gate  # type: ignore

        contracts = dict(getattr(artifact_gate, "ARTIFACT_CONTRACTS", {}) or {})
    except Exception as exc:  # noqa: BLE001
        print(f"   ⚠️  ARTIFACT_CONTRACTS indisponível: {exc}")
    return slice_map, contracts


def _contract_paths(items: Any) -> list[str]:
    """Caminhos declarados num item de `ARTIFACT_CONTRACTS`, ignorando advisories."""
    paths: list[str] = []
    for item in items or []:
        if isinstance(item, dict) and not item.get("advisory") and item.get("path"):
            paths.append(str(item["path"]))
    return paths


# ─── Renderização ────────────────────────────────────────────────────────────

def _yaml_inline_string(value: str) -> str:
    """Escapa uma string para YAML inline entre aspas duplas."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render_wrapper(
    record: dict[str, Any],
    core: str,
    slice_map: dict[str, Any],
    contracts: dict[str, Any],
) -> str:
    """Conteúdo completo de um `.agent.md`."""
    agent_id = record["agent"]
    spec_path = record["path"]
    spec_text = (REPO_ROOT / spec_path).read_text(encoding="utf-8")

    description = parse_description(spec_text) or (
        f"Agente {agent_id} da esteira AVA Fabric (fase {record['phase'] or 'transversal'})."
    )
    tools = map_tools(record.get("tools") or [])

    front = [
        "---",
        f"name: {agent_id}",
        f"description: {_yaml_inline_string(description)}",
        "tools: [" + ", ".join(f'"{t}"' for t in tools) + "]",
        f"model: {DEFAULT_MODEL}",
        "target: github-copilot",
        "user-invocable: true",
        "metadata:",
        f"  version: {_yaml_inline_string(record.get('version') or '0.0.0')}",
        f"  phase: {_yaml_inline_string(record.get('phase') or '')}",
        f"  module: {_yaml_inline_string(record.get('module') or '')}",
        f"  spec: {_yaml_inline_string(spec_path)}",
        "---",
    ]

    body: list[str] = [
        "<!--",
        f"  {GENERATED_HEADER}",
        f"  Fonte: {spec_path}",
        "",
        "  Por que o wrapper é fino e não contém a spec:",
        "    - o corpo de um .agent.md tem cap de 30.000 caracteres (M0);",
        "      37 das 107 specs do repo estouram esse limite;",
        "    - `version:` e `allowed-tools:` são DESCARTADOS pelo parser do CLI",
        "      (unknown fields ignored). A chave correta é `tools:`, e ela é",
        "      enforçada de verdade;",
        "    - o bloco AGENTS-CORE abaixo é copiado de AGENTS.md porque o runner",
        "      usa --no-custom-instructions, que desliga o carregamento nativo.",
        "-->",
        "",
        f"Você é o agente **{agent_id}** da esteira AVA Fabric"
        + (f" (fase {record['phase']})." if record["phase"] else " (transversal)."),
        "",
        "## Sua especificação canônica",
        "",
        f"`{spec_path}`",
        "",
        "**Leia-a por inteiro antes de qualquer outra ação** e siga os Execution Steps",
        "literalmente. Este wrapper não substitui a spec — só a localiza e aplica as",
        "regras gerais da esteira.",
        "",
    ]

    slice_value = slice_map.get(agent_id)
    contract_paths = _contract_paths(contracts.get(agent_id))
    if slice_value is not None or contract_paths:
        body.append("## Estratégia de contexto")
        body.append("")
        if slice_value is not None:
            if isinstance(slice_value, (list, tuple)):
                rendered = ", ".join(f"`{s}`" for s in slice_value) if slice_value else "_(nenhuma — consolidador)_"
            else:
                rendered = f"`{slice_value}`"
            body.append(f"- **Fatia AST**: {rendered}")
            body.append(
                "- Leia **apenas** essa fatia. O context pack, quando presente, já a traz"
            )
            body.append("  decodificada — ele é a autoridade do seu contexto.")
        if contract_paths:
            body.append("- **Output contract**:")
            for path in contract_paths:
                body.append(f"  - `{path}`")
        body.append("")

    body.append("## Regras gerais da esteira (de AGENTS.md — não editar aqui)")
    body.append("")
    body.append(core)
    body.append("")

    return "\n".join(front) + "\n\n" + "\n".join(body).rstrip() + "\n"


# ─── Preflight ───────────────────────────────────────────────────────────────

def preflight(agent_ids: list[str]) -> None:
    """Falha se `~/.copilot/agents/` sombrear algum nome de `.github/agents/`.

    O diretório do usuário tem **precedência** sobre o do projeto. Uma colisão faz
    o CLI executar um agente diferente do que está versionado, sem avisar — a
    reprodutibilidade morre em silêncio. O diretório não existe na máquina medida
    no M0, mas pode ser criado a qualquer momento.
    """
    if not USER_AGENTS_DIR.is_dir():
        return
    wanted = {f"{agent_id}.agent.md" for agent_id in agent_ids}
    collisions = sorted(p.name for p in USER_AGENTS_DIR.glob("*.agent.md") if p.name in wanted)
    if collisions:
        print(
            f"❌ preflight: {USER_AGENTS_DIR} sombreia {len(collisions)} agente(s) "
            "de .github/agents/ (o diretório do usuário tem precedência):",
            file=sys.stderr,
        )
        for name in collisions:
            print(f"   {name}", file=sys.stderr)
        raise SystemExit(2)


# ─── Geração ─────────────────────────────────────────────────────────────────

def build_all(phase: str | None = None) -> dict[str, str]:
    """`{agent_id: conteúdo do wrapper}` para os agentes despacháveis."""
    core = read_agents_core()
    slice_map, contracts = load_optional_context()

    wrappers: dict[str, str] = {}
    oversized: list[tuple[str, int]] = []
    for entry in agent_registry.catalog():
        agent_id = entry["agent"]
        if phase and entry["phase"] != phase:
            continue
        record = agent_registry.get(agent_id)
        if record is None:
            continue
        content = render_wrapper(record, core, slice_map, contracts)
        body_len = len(content.split("---", 2)[-1])
        if body_len >= BODY_CHAR_CAP:
            oversized.append((agent_id, body_len))
        wrappers[agent_id] = content

    if oversized:
        print(f"❌ {len(oversized)} wrapper(s) com corpo ≥ {BODY_CHAR_CAP} chars:", file=sys.stderr)
        for agent_id, size in oversized:
            print(f"   {agent_id}: {size}", file=sys.stderr)
        print(
            "   O corpo é o AGENTS-CORE + ponteiro. Se estourou, AGENTS.md cresceu "
            "demais — enxugue o bloco, não trunque o wrapper.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    return wrappers


def write_all(wrappers: dict[str, str], dry_run: bool = False) -> tuple[int, int]:
    """Escreve os wrappers. Devolve `(escritos, inalterados)`."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written = unchanged = 0
    for agent_id, content in sorted(wrappers.items()):
        target = OUT_DIR / f"{agent_id}.agent.md"
        current = target.read_text(encoding="utf-8") if target.is_file() else None
        if current == content:
            unchanged += 1
            continue
        if not dry_run:
            target.write_text(content, encoding="utf-8", newline="\n")
        written += 1
    return written, unchanged


def check(wrappers: dict[str, str]) -> list[str]:
    """Divergências entre o disco e o que o registry produziria."""
    problems: list[str] = []
    for agent_id, content in sorted(wrappers.items()):
        target = OUT_DIR / f"{agent_id}.agent.md"
        if not target.is_file():
            problems.append(f"ausente: {target.relative_to(REPO_ROOT).as_posix()}")
        elif target.read_text(encoding="utf-8") != content:
            problems.append(f"divergente: {target.relative_to(REPO_ROOT).as_posix()}")

    expected = {f"{agent_id}.agent.md" for agent_id in wrappers}
    for path in sorted(OUT_DIR.glob("ava-*.agent.md")):
        if path.name not in expected:
            problems.append(
                f"órfão: {path.relative_to(REPO_ROOT).as_posix()} "
                "(não corresponde a nenhum agente despachável do registry)"
            )
    return problems


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="generate_agent_wrappers.py",
        description="Gera .github/agents/*.agent.md a partir do agent_registry",
    )
    parser.add_argument("--phase", help="Gera só os agentes desta fase (F1..F8)")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Não escreve; exit 1 se o disco divergir do que seria gerado (CI)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Mostra o que faria, sem escrever")
    args = parser.parse_args()

    wrappers = build_all(args.phase)
    if not wrappers:
        print("❌ nenhum agente encontrado no registry", file=sys.stderr)
        raise SystemExit(2)

    if args.check:
        problems = check(wrappers)
        if problems:
            print(f"❌ {len(problems)} divergência(s) em .github/agents/:", file=sys.stderr)
            for problem in problems:
                print(f"   {problem}", file=sys.stderr)
            print(
                "   Rode: python src/shared/tools/generate_agent_wrappers.py",
                file=sys.stderr,
            )
            raise SystemExit(1)
        print(f"✅ {len(wrappers)} wrapper(s) em dia com o registry")
        return

    preflight(list(wrappers))
    written, unchanged = write_all(wrappers, dry_run=args.dry_run)
    verb = "geraria" if args.dry_run else "gerados"
    print(f"✅ {len(wrappers)} wrapper(s) — {written} {verb}, {unchanged} inalterado(s)")
    print(f"   destino: {OUT_DIR.relative_to(REPO_ROOT).as_posix()}")


if __name__ == "__main__":
    main()
