#!/usr/bin/env python3
"""`source-code/README.md` — a porta de entrada da árvore gerada pela F4S.

Por que existe
--------------
`outputs/tobe/source-code/` recebe um repositório git próprio (o baseline) com
frontend e backend lado a lado. Quem abre essa pasta — o operador, o agente
coder da F4, ou alguém revisando o baseline meses depois — encontrava duas
árvores sem nenhuma folha de rosto: qual stack, qual versão, quais bounded
contexts, se compilou, com qual comando se compila de novo. Tudo isso já existe
em `tasks-progress.json`, num formato que ninguém lê à mão.

Este módulo é a projeção legível desse estado. Não descobre nada por conta
própria: lê o que a fase registrou e formata. Se um campo não foi registrado, o
README diz "não registrado" em vez de adivinhar — um README que inventa a versão
do SDK é pior do que um que admite não saber.

Regenerado a cada execução, DEPOIS dos dois componentes e ANTES do baseline —
essa ordem é o que faz o arquivo entrar no commit que representa "o sistema
compila".
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from scaffold_paths import (  # noqa: E402
    COMPONENT_TYPES,
    SOURCE_CODE_ROOT,
    resolve_source_code_path,
)

README_FILENAME = "README.md"

#: Marca de autoria, invisível no Markdown renderizado. É o que separa "este
#: arquivo é a projeção do estado da F4S, pode reescrever" de "alguém escreveu
#: isto, não toque". Sem ela, uma re-execução da F4S — a primeira coisa que se
#: recomenda quando o passo estoura — apagaria o README de 248 linhas que um
#: agente de fase posterior escreveu com docker-compose, pipeline e auth.
SENTINELA = "<!-- gerado-por: f4s/scaffold_readme -->"


def foi_gerado_por_nos(caminho: Path) -> bool:
    """`True` se o arquivo é nosso (ou não existe) — só aí ele é reescrito."""
    alvo = Path(caminho)
    if not alvo.is_file():
        return True
    try:
        return SENTINELA in alvo.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False

#: Como recompilar cada componente à mão, quando o front-matter do scaffold não
#: declara `build_command`. São os comandos que o próprio verifier roda — é o
#: que evita o README sugerir uma coisa e o gate cobrar outra.
_BUILD_FALLBACK: dict[str, str] = {
    "dotnet": "dotnet build",
    "angular": "npm install && npx ng build",
    "react": "npm install && npm run build",
    "vue": "npm install && npm run build",
    "spring-boot": "./mvnw package",
    "java": "./mvnw package",
    "fastapi": "pip install -r requirements.txt",
    "python": "pip install -r requirements.txt",
}

_TRADUCAO_STATUS = {
    "completed": "✅ concluído",
    "failed": "❌ reprovado",
    "running": "⏳ em execução",
    "verifying": "⏳ em verificação",
    "generated": "⏳ gerado, não verificado",
    "cancelled": "⛔ cancelado",
    "succeeded": "✅ ok",
    "not_reached": "— não alcançado",
}


def _agora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def _rotulo(valor: Any) -> str:
    """Status legível, sem esconder um valor desconhecido atrás de um traço."""
    if valor in (None, ""):
        return "— não registrado"
    texto = str(valor).strip().lower()
    return _TRADUCAO_STATUS.get(texto, str(valor))


def _tabela(linhas: list[tuple[str, Any]]) -> list[str]:
    """Tabela de duas colunas; omite o que a fase não registrou."""
    uteis = [(k, v) for k, v in linhas if v not in (None, "", [], {})]
    if not uteis:
        return []
    saida = ["| Campo | Valor |", "| --- | --- |"]
    saida += [f"| {chave} | {valor} |" for chave, valor in uteis]
    return saida


def _comando_de_build(stack: str, definition: Any) -> str:
    declarado = str(getattr(definition, "build_command", "") or "").strip()
    return declarado or _BUILD_FALLBACK.get(str(stack or "").lower(), "")


def _bloco_componente(component_type: str, tarefa: dict[str, Any],
                      resultado: dict[str, Any],
                      definition: Any = None) -> list[str]:
    stack = tarefa.get("stack") or resultado.get("stack") or "não declarada"
    geracao = resultado.get("generation") or {}
    verificacao = resultado.get("verification") or {}
    caminho = resolve_source_code_path(component_type)

    linhas = [f"### `{caminho}/` — {stack}", ""]

    # `Status` aparece sempre — inclusive como "não registrado", porque uma
    # tabela sem status é lida como "deu certo". Os demais são opcionais por
    # stack (`restore` só existe no .NET) e somem quando não há o que dizer:
    # "— não registrado" em toda linha faz o leitor procurar problema onde
    # não há.
    campos: list[tuple[str, Any]] = [("Status", _rotulo(tarefa.get("status")))]
    for titulo, chave in (("Verificação", "verification_status"),
                          ("Build", "build_status"),
                          ("Restore", "restore_status")):
        if tarefa.get(chave) is not None:
            campos.append((titulo, _rotulo(tarefa[chave])))
    campos.append(("Tentativas", tarefa.get("attempts")))

    # Campos específicos da stack: só entram se o generator os devolveu. É o
    # que mantém o README correto quando uma stack nova chegar sem eles.
    for chave, titulo in (
        ("solution", "Solution"),
        ("solution_prefix", "Prefixo"),
        ("tfm", "Target framework"),
        ("sdk", "SDK"),
        ("app_name", "Aplicação"),
        ("angular_major", "Angular (major)"),
    ):
        if geracao.get(chave):
            campos.append((titulo, f"`{geracao[chave]}`"))

    escritos = geracao.get("files_written")
    if isinstance(escritos, list):
        campos.append(("Arquivos gerados", len(escritos)))
    preservados = geracao.get("files_skipped")
    if isinstance(preservados, list) and preservados:
        campos.append(("Arquivos preservados", len(preservados)))
    if resultado.get("reused"):
        campos.append(("Origem", "reaproveitado de execução anterior"))

    linhas += _tabela(campos)

    comando = _comando_de_build(stack, definition)
    if comando:
        linhas += ["", "Recompilar à mão:", "",
                   "```bash", f"cd {caminho}", comando, "```"]

    avisos = resultado.get("warnings") or verificacao.get("warnings") or []
    if avisos:
        linhas += ["", f"⚠️ {len(avisos)} aviso(s) na verificação — "
                       f"ver `.artifacts/` dentro do componente."]

    erro = resultado.get("error") or tarefa.get("error_summary")
    if erro:
        # Um componente reprovado tem de gritar aqui: este arquivo é a primeira
        # coisa que alguém lê ao abrir a pasta, e "silêncio" seria lido como ok.
        linhas += ["", f"> ❌ **Reprovado.** {str(erro).splitlines()[0][:300]}"]

    return linhas + [""]


def build_readme(project: str, state: dict[str, Any],
                 components: dict[str, Any] | None = None, *,
                 bcs: list[str] | None = None,
                 baseline: dict[str, Any] | None = None,
                 definitions: dict[str, Any] | None = None) -> str:
    """Monta o texto do README a partir do estado já registrado pela fase."""
    components = components or {}
    definitions = definitions or {}
    tarefas = {
        ct: next((t for t in (state.get("tasks") or {}).values()
                  if t.get("component_type") == ct), {})
        for ct in COMPONENT_TYPES
    }

    linhas = [
        SENTINELA,
        "",
        f"# {project} — código-fonte gerado",
        "",
        "Base compilável de frontend e backend produzida **deterministicamente** "
        "pela fase F4S (scaffold) da esteira AVA Fabric.",
        "",
        "> ⚠️ Arquivo gerado: é reescrito por inteiro a cada execução da F4S. "
        "Edições manuais são perdidas — documente decisões em outro arquivo.",
        "",
    ]

    cabecalho: list[tuple[str, Any]] = [
        ("Projeto", f"`{project}`"),
        ("Gerado em", _agora()),
        ("run_id", f"`{state.get('run_id')}`" if state.get("run_id") else None),
        ("Bounded contexts", ", ".join(f"`{b}`" for b in (bcs or [])) or None),
    ]
    linhas += _tabela(cabecalho) + [""]

    linhas += ["## Estrutura", "", "```text", SOURCE_CODE_ROOT + "/"]
    largura = max(len(ct) for ct in COMPONENT_TYPES) + 1  # +1 pela barra
    for indice, ct in enumerate(COMPONENT_TYPES):
        ramo = "└──" if indice == len(COMPONENT_TYPES) - 1 else "├──"
        stack = (tarefas[ct].get("stack")
                 or (components.get(ct) or {}).get("stack") or "—")
        linhas.append(f"{ramo} {ct + '/':<{largura}}   # {stack}")
    linhas += ["```", "",
               "Os dois caminhos são canônicos e derivam apenas do "
               "`component_type` — a stack nunca entra na composição do "
               "diretório. Ver `scaffold_paths.resolve_source_code_path`.",
               ""]

    linhas += ["## Componentes", ""]
    for ct in COMPONENT_TYPES:
        linhas += _bloco_componente(ct, tarefas[ct] or {},
                                    components.get(ct) or {},
                                    definitions.get(ct))

    linhas += ["## Baseline", ""]
    sha = (baseline or {}).get("commit_sha")
    if sha:
        linhas += [
            f"Esta pasta é um repositório git próprio. Commit do baseline: "
            f"`{sha[:12]}`.", "",
            "O baseline só é criado depois de os DOIS componentes compilarem — "
            "é o ponto de retorno para \"o sistema inteiro compila\", não "
            "\"esta metade compila\".",
        ]
    elif (baseline or {}).get("error"):
        linhas += [f"Baseline **não** criado: {baseline['error']}", "",
                   "Sem baseline, os agentes coder permanecem bloqueados."]
    else:
        # O SHA do commit que INCLUI este arquivo não pode estar dentro dele.
        # Descrever o mecanismo e apontar o `git log` é honesto; escrever
        # "ainda não criado" no arquivo que o commit carrega, não seria.
        linhas += [
            "Esta pasta é um repositório git próprio, e o baseline é commitado "
            "logo depois deste arquivo — por isso o SHA não aparece aqui.",
            "",
            "```bash",
            f"git -C {SOURCE_CODE_ROOT} log -1",
            "```",
        ]
    linhas += [""]

    linhas += [
        "## O que vem depois",
        "",
        "Esta árvore é **fundação**, não funcionalidade: projetos, referências, "
        "camadas e configuração de build. As features são escritas sobre ela "
        "pelos agentes coder da F4, e eles só são liberados após a aprovação "
        "explícita registrada em `outputs/tobe/tasks-progress.json`.",
        "",
        "Para regenerar:",
        "",
        "```bash",
        f"python src/shared/tools/scaffold_runner.py --project {project} --json",
        "```",
        "",
    ]
    return "\n".join(linhas)


def readme_path(project_dir: Path) -> Path:
    return (Path(project_dir) / "outputs" / "tobe" / SOURCE_CODE_ROOT
            / README_FILENAME)


def write_readme(project_dir: Path, project: str, state: dict[str, Any],
                 components: dict[str, Any] | None = None, *,
                 bcs: list[str] | None = None,
                 baseline: dict[str, Any] | None = None,
                 definitions: dict[str, Any] | None = None,
                 force: bool = False) -> Path:
    """Escreve `outputs/tobe/source-code/README.md` e devolve o caminho.

    Reescreve o próprio README a cada execução — ele é projeção de estado, não
    documento acumulativo. README de OUTRO autor é preservado (ver `SENTINELA`);
    `force=True` é a autorização explícita para sobrescrever mesmo assim, e vem
    do `--force` da fase, que já significa "sobrescreva o que existir".
    """
    destino = readme_path(project_dir)
    destino.parent.mkdir(parents=True, exist_ok=True)
    if not force and not foi_gerado_por_nos(destino):
        return destino
    conteudo = build_readme(project, state, components, bcs=bcs,
                            baseline=baseline, definitions=definitions)
    destino.write_text(conteudo, encoding="utf-8", newline="\n")
    return destino
