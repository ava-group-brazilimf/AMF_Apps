#!/usr/bin/env python3
"""
AVA Fabric — CLI da esteira · Motor SDK (Anthropic)
====================================================
Executa um passo da esteira chamando o endpoint Anthropic-compatible do Foundry
direto pelo SDK, em **contexto isolado** (histórico novo a cada passo).

Extraído de ``pipeline_runner.py``, preservando o contrato que já funcionava:
o modelo roda **sem tools** e devolve os artefatos como blocos
``<!-- FILE: caminho -->…<!-- /FILE -->``, que este módulo grava em disco.

Rota via proxy
--------------
A única diferença entre rota direta e rota via Headroom é o ``base_url``:
o proxy registra ``POST /v1/messages`` e encaminha o header de auth verbatim,
então basta apontar o SDK para ``http://host:port`` — **sem sufixo de path**.
O ``anthropic-version`` continua obrigatório: além do Foundry, o proxy o usa
para decidir o upstream (``_is_anthropic_auth``).

Dependência
-----------
``anthropic`` é importado **dentro** de ``make_client`` de propósito: o repo é
stdlib-only por convenção e o motor ``copilot`` não precisa do SDK. Só quem
escolhe ``--engine sdk`` paga a dependência.
"""
from __future__ import annotations

import datetime
import re
import socket
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(SCRIPT_DIR))

import context_manifest  # noqa: E402
from pipeline_plan import Step  # noqa: E402


class ContextError(Exception):
    """Insumo obrigatório ausente. O CLI converte em exit 2, sem gastar inferência."""


def resolve_context(project: str, step: Step, cfg: dict[str, Any],
                    preamble: list[str] | None = None):
    """Resolução de contexto do passo — sem I/O de rede, usável em ``--dry-run``.

    Passo vindo do fan-out recebe o preâmbulo de iteração: o que já está
    verificado no grupo, a task que ele possui e as últimas notas de progresso.
    A rotina "leia o progresso e escolha a próxima feature" é imposta aqui, não
    confiada à memória do agente — e a escolha não é dele.
    """
    blocos = list(preamble or [])
    if not blocos and getattr(step, "task_group", ""):
        try:
            import task_ledger  # noqa: PLC0415
            blocos = task_ledger.iteration_preamble(
                project, step.task_group, task_id=getattr(step, "task_id", "") or None)
        except Exception:  # noqa: BLE001 — preâmbulo nunca derruba o passo (IV3)
            blocos = []
    return context_manifest.resolve(project, step.inputs, cfg, preamble=blocos)

# ─── Cores ANSI ──────────────────────────────────────────────────────────────
RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
DIM = "\033[2m"
MAGENTA = "\033[95m"


@dataclass
class Route:
    """Como as requisições chegam ao Foundry."""
    base_url: str
    via_proxy: bool

    @property
    def label(self) -> str:
        return "proxy (Headroom)" if self.via_proxy else "direta"


# ─── DNS (private endpoints via VPN) ─────────────────────────────────────────

def apply_dns_overrides(cfg: dict[str, Any]) -> bool:
    """Monkeypatch em ``socket.getaddrinfo`` para hosts sem DNS privado.

    Desligado por padrão: o endpoint ``/anthropic`` resolve nativamente sob a
    VPN. Só serve a ambientes sem split-DNS configurado.
    """
    block = cfg.get("dns_overrides") or {}
    hosts = block.get("hosts") or {}
    if not block.get("enabled") or not hosts:
        return False

    original = socket.getaddrinfo

    def patched(host, port, *args, **kwargs):
        return original(hosts.get(host, host), port, *args, **kwargs)

    socket.getaddrinfo = patched
    return True


# ─── Cliente ─────────────────────────────────────────────────────────────────

def make_client(cfg: dict[str, Any], route: Route, api_key: str):
    """Cria o cliente Anthropic apontado para ``route.base_url``."""
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "ERRO: o pacote `anthropic` é necessário para --engine sdk.\n"
            "      pip install -r src/shared/tools/requirements-pipeline.txt\n"
            "      (ou use --engine copilot, que não depende do SDK)"
        ) from exc

    return anthropic.Anthropic(
        api_key=api_key,
        base_url=route.base_url,
        default_headers={
            "anthropic-version": cfg.get("foundry", {}).get("anthropic_version", "2023-06-01")
        },
    )


def ping(client, model: str) -> None:
    """Teste rápido de conectividade. Propaga a exceção para o CLI classificar."""
    with client.messages.stream(
        model=model,
        messages=[{"role": "user", "content": "ping"}],
        max_tokens=5,
    ) as stream:
        stream.get_final_message()


# ─── Contexto ────────────────────────────────────────────────────────────────

def load_skill(step: Step, cfg: dict[str, Any]) -> str:
    """Lê a spec do agente pelo caminho exato vindo do ``agent_registry``.

    O runner antigo procurava por heurística de substring e escolhia o maior
    arquivo candidato — podia carregar o agente errado em silêncio.
    """
    limit = int(cfg.get("context", {}).get("skill_chars", 500_000))
    if not step.spec_path or not step.spec_path.is_file():
        return f"[spec não encontrada para {step.agent}]"
    content = step.spec_path.read_text(encoding="utf-8", errors="ignore")
    if len(content) > limit:
        content = content[:limit] + "\n\n[... skill truncado no limite de contexto ...]"
    return content


def load_context(project: str, cfg: dict[str, Any], step: Step | None = None) -> str:
    """Monta o contexto do passo.

    Com ``step.inputs`` declarado, delega ao ``context_manifest`` — allowlist
    explícita, ordem de declaração, `.html` elegível, falta de obrigatório
    reprovando **antes** da inferência. Sem declaração, cai no caminho legado
    abaixo, preservado byte a byte.

    O motivo de existir a delegação está em ``context_manifest`` §"O defeito":
    a heurística legada nunca alcançava ``outputs/tobe/`` — o gerador de código
    da F4 rodou sem um único artefato TO-BE em contexto.
    """
    if step is not None and step.inputs:
        res = resolve_context(project, step, cfg)
        if res.blocked:
            raise ContextError(context_manifest.format_missing(
                res, step.phase, step.agent, project))
        return context_manifest.render(res)

    ctx = cfg.get("context", {})
    file_chars = int(ctx.get("file_chars", 500_000))
    max_arts = int(ctx.get("max_artifacts", 500))
    max_bodies = int(ctx.get("max_artifact_bodies", 30))
    body_chars = int(ctx.get("artifact_body_chars", 20_000))
    out_subdir = cfg.get("execution", {}).get("output_subdir", "outputs/pipeline_runner")

    parts: list[str] = []
    proj_path = REPO_ROOT / "projects" / project

    for fname in ("context/project-config.yaml", "context/shared-context.md"):
        fpath = proj_path / fname
        if fpath.is_file():
            text = fpath.read_text(encoding="utf-8", errors="ignore")
            if len(text) > file_chars:
                text = text[:file_chars] + "\n[... truncado no limite de contexto ...]"
            parts.append(f"### {fname}\n```\n{text}\n```")

    # Artefatos já gerados enriquecem o contexto dos passos seguintes.
    out_root = proj_path / "outputs"
    if out_root.is_dir():
        skip = (proj_path / out_subdir).resolve()
        existing: list[str] = []
        bodies: list[str] = []
        for p in sorted(out_root.rglob("*")):
            if not p.is_file() or skip in p.resolve().parents:
                continue
            existing.append(str(p.relative_to(REPO_ROOT)))
            if p.suffix in (".md", ".mmd", ".yaml", ".json") and len(bodies) < max_bodies:
                try:
                    text = p.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                if text.strip():
                    bodies.append(f"### {p.relative_to(REPO_ROOT)}\n```\n{text[:body_chars]}\n```")
        if existing:
            parts.append("### Artefatos já existentes em outputs/\n" + "\n".join(existing[:max_arts]))
        if bodies:
            parts.append("## Conteúdo dos Artefatos Gerados\n\n" + "\n\n".join(bodies))

    return "\n\n".join(parts) if parts else "[Sem contexto disponível]"


# ─── Prompts ─────────────────────────────────────────────────────────────────

def build_system_prompt(step: Step, skill_content: str, project: str, context: str) -> str:
    """System prompt com o contexto real do projeto injetado."""
    return f"""Você é o agente AVA Fabric '{step.agent}' operando no pipeline de modernização de sistemas legados.

PROJETO ATIVO: {project}
WORKSPACE: {REPO_ROOT}
PROJETO PATH: {REPO_ROOT}/projects/{project}/
ETAPA DA ESTEIRA: {step.phase} — {step.label}
TASK AUTORIZADA: {step.task_id or 'N/A'}

## CONTEXTO DO PROJETO (lido do disco)

{context}

## SKILL DO AGENTE

{skill_content}

## REGRAS DE EXECUÇÃO — OBRIGATÓRIAS

### FORMATO DE SAÍDA — ÚNICA FORMA ACEITA
Para CADA arquivo que precisar criar, use EXCLUSIVAMENTE este bloco:

<!-- FILE: projects/{project}/outputs/<caminho_relativo> -->
[conteúdo completo do arquivo aqui]
<!-- /FILE -->

### PROIBIÇÕES ABSOLUTAS
- ❌ NÃO use <tool_call>, <tool_response> ou qualquer bloco de ferramenta
- ❌ NÃO use Bash(), Read(), Write() ou funções de shell
- ❌ NÃO use WriteAllText, New-Item ou comandos PowerShell
- ❌ NÃO simule execução de comandos — apenas gere o conteúdo dos arquivos
- ❌ NÃO use placeholder — gere conteúdo REAL e COMPLETO em cada arquivo

### OBRIGAÇÕES
- ✅ Gere TODOS os artefatos listados no Output Contract do skill
- ✅ Use SOMENTE blocos <!-- FILE: ... --> / <!-- /FILE -->
- ✅ Caminho deve começar com: projects/{project}/outputs/
- ✅ Ao final, liste os arquivos gerados em tabela Markdown
"""


# ─── Extração de artefatos ───────────────────────────────────────────────────

_FILE_BLOCK = re.compile(
    r'<!--\s*FILE:\s*([^\n\r]+?)\s*-->\r?\n(.*?)<!--\s*/FILE\s*-->',
    re.DOTALL,
)


def _resolve_path(rel_path: str, project: str) -> Path:
    """Resolve um caminho relativo para Path absoluto dentro do projeto."""
    rp = rel_path.replace("\\\\", "/").replace("\\", "/").lstrip("/")
    base = REPO_ROOT if rp.startswith("projects/") else REPO_ROOT / "projects" / project
    return (base / rp).resolve()


def parse_and_write_outputs(response: str, project: str) -> list[str]:
    """Extrai os blocos ``<!-- FILE: ... -->`` da resposta e grava no disco.

    Caminhos que escapem de ``projects/{project}/`` são recusados: o conteúdo
    vem do modelo, então nada garante que o caminho seja bem-comportado.
    """
    written: list[str] = []
    guard = (REPO_ROOT / "projects" / project).resolve()

    for match in _FILE_BLOCK.finditer(response):
        target = _resolve_path(match.group(1).strip(), project)
        if guard != target and guard not in target.parents:
            print(f"{YELLOW}  ⚠️  caminho recusado (fora do projeto): {match.group(1).strip()}{RESET}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(match.group(2), encoding="utf-8")
        written.append(str(target.relative_to(REPO_ROOT)))

    return written


# ─── Execução de um passo ────────────────────────────────────────────────────

def run_step(client, step: Step, project: str, model: str, cfg: dict[str, Any],
             output_dir: Path) -> dict[str, Any]:
    """Executa um passo em contexto isolado (histórico novo), com streaming."""
    skill_content = load_skill(step, cfg)
    context = load_context(project, cfg, step)
    system_prompt = build_system_prompt(step, skill_content, project, context)
    user_prompt = step.build_prompt(project)
    max_tokens = int(cfg.get("foundry", {}).get("max_tokens", 32768))

    print(f"\n{DIM}  Enviando: {user_prompt}{RESET}")
    print(f"{DIM}  Aguardando resposta...{RESET}\n")
    print(f"{CYAN}{'─' * 60}{RESET}")

    full_response = ""
    with client.messages.stream(
        model=model,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        max_tokens=max_tokens,
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            full_response += text

    print(f"\n{CYAN}{'─' * 60}{RESET}")

    written = parse_and_write_outputs(full_response, project)
    if written:
        print(f"\n{GREEN}  📄 Artefatos escritos ({len(written)}):{RESET}")
        for w in written:
            print(f"  {GREEN}     {w}{RESET}")
    else:
        print(f"\n{YELLOW}  ⚠️  Nenhum bloco FILE: encontrado na resposta.{RESET}")

    log_path = _write_log(step, project, model, user_prompt, full_response, written, output_dir)
    print(f"\n{GREEN}  ✅ Log salvo: {log_path.relative_to(REPO_ROOT)}{RESET}")

    return {"phase": step.phase, "agent": step.agent, "artifacts": written,
            "log": str(log_path.relative_to(REPO_ROOT)), "chars": len(full_response)}


def _write_log(step: Step, project: str, model: str, user_prompt: str,
               response: str, written: list[str], output_dir: Path) -> Path:
    now = datetime.datetime.now()
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{step.phase}_{step.agent}_{now.strftime('%Y%m%d_%H%M%S')}.md"
    path.write_text(
        f"# {step.phase} — {step.label}\n\n"
        f"**Agente:** @{step.agent}  \n"
        f"**Trigger:** {step.trigger or 'N/A'}  \n"
        f"**Projeto:** {project}  \n"
        f"**Modelo:** {model}  \n"
        f"**Data:** {now.strftime('%Y-%m-%d %H:%M:%S')}  \n"
        f"**Artefatos gerados:** {len(written)}  \n\n"
        f"---\n\n"
        f"## Arquivos escritos\n\n"
        + ("\n".join(f"- `{w}`" for w in written) if written else "_Nenhum_")
        + f"\n\n## Prompt enviado\n\n```\n{user_prompt}\n```\n\n"
        f"## Resposta\n\n{response}\n",
        encoding="utf-8",
    )
    return path


def estimate_prompt_chars(step: Step, project: str, cfg: dict[str, Any]) -> int:
    """Tamanho do prompt que seria enviado — usado pelo --dry-run, sem inferência.

    Insumo obrigatório ausente não levanta aqui: o ``--dry-run`` precisa listar o
    plano inteiro, inclusive os passos que iriam falhar. Quem reprova é
    ``preflight_inputs`` no CLI, com a mensagem completa.
    """
    skill = load_skill(step, cfg)
    if step.inputs:
        context = context_manifest.render(resolve_context(project, step, cfg))
    else:
        context = load_context(project, cfg)
    return len(build_system_prompt(step, skill, project, context)) + len(step.build_prompt(project))
