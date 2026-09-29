"""
Testes dos wrappers `.github/agents/*.agent.md` (specs/033).

Cada assert aqui corresponde a um fato **medido** no spike M0
(`docs/copilot-cli-runtime-facts.md`), não a uma preferência de estilo:

* `tools:` é enforçado de verdade — agente sem `view` não lê arquivo;
* `version:` e `allowed-tools:` são descartados com
  `unknown fields ignored` — emiti-los produz agente sem restrição de tool;
* a tool de shell chama-se `powershell`, não `bash`;
* o corpo tem cap de 30.000 caracteres.

Roda com o Python do repo:
    python -m pytest tests/tools/test_agent_wrappers.py -q
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "shared" / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import agent_registry as reg  # noqa: E402
import generate_agent_wrappers as gen  # noqa: E402

AGENTS_MD = REPO_ROOT / "AGENTS.md"
WRAPPER_DIR = REPO_ROOT / ".github" / "agents"

_FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)

#: Nomes reais das tools do Copilot CLI (M0 § 5). Qualquer outro valor é aceito
#: pelo parser e deixa o agente sem a ferramenta, sem avisar.
VALID_TOOLS = {
    "view", "create", "edit", "glob", "grep",
    "powershell", "read_powershell", "stop_powershell",
    "web_fetch", "web_search",
}


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def catalog() -> list[dict[str, str]]:
    return reg.catalog()


@pytest.fixture(scope="module")
def wrappers() -> dict[str, Path]:
    return {p.name[: -len(".agent.md")]: p for p in sorted(WRAPPER_DIR.glob("ava-*.agent.md"))}


def _frontmatter(path: Path) -> str:
    match = _FRONTMATTER_RE.search(path.read_text(encoding="utf-8"))
    assert match, f"{path.name}: sem frontmatter YAML"
    return match.group(1)


def _body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.search(text)
    return text[match.end():] if match else text


# ─── AGENTS.md — a fonte única ───────────────────────────────────────────────

#: Dois tetos, porque são dois custos diferentes — medir o arquivo inteiro
#: confundia os dois e forçava enxugar documentação de mantenedor para caber:
#:
#:   AGENTS-CORE  → injetado nos 102 wrappers, cobrado em TODA janela de agente.
#:                  É o número que importa. Teto apertado.
#:   arquivo      → carregado uma vez no fluxo interativo (medido: ~+2K tokens de
#:                  systemTokens). O cabeçalho é doc de mantenedor. Teto folgado.
AGENTS_CORE_MAX_BYTES = 8 * 1024
AGENTS_MD_MAX_BYTES = 10 * 1024


def test_agents_core_cabe_no_orcamento_replicado():
    """O bloco herdado é cobrado 102 vezes — cada KB aqui vale 102 KB de prompt."""
    core = gen.read_agents_core().encode("utf-8")
    assert len(core) <= AGENTS_CORE_MAX_BYTES, (
        f"AGENTS-CORE tem {len(core)} bytes — teto de {AGENTS_CORE_MAX_BYTES}. "
        "Enxugue a regra, não o teto: isto é replicado em todos os wrappers."
    )


def test_agents_md_existe_e_cabe_no_orcamento():
    """O arquivo inteiro só é cobrado uma vez, no fluxo interativo."""
    assert AGENTS_MD.is_file(), "AGENTS.md não existe na raiz do repo"
    assert AGENTS_MD.stat().st_size <= AGENTS_MD_MAX_BYTES, (
        f"AGENTS.md tem {AGENTS_MD.stat().st_size} bytes — teto de {AGENTS_MD_MAX_BYTES}"
    )


def test_agents_core_proibe_delegacao_a_subagente_generico():
    """A regra tem de chegar às 8 fases — F2–F8 não têm FILE_PERSISTENCE_RULE.

    Medido em 56 sessões: `general-purpose` 53/53 e `explore` 19/24 terminaram com
    zero tool calls sob BYOK. A proibição só vale se estiver no bloco herdado.
    """
    core = gen.read_agents_core()
    for termo in ("general-purpose", "explore"):
        assert termo in core, f"AGENTS-CORE não proíbe delegação a {termo!r}"
    assert "background" in core.lower()


def test_agents_md_tem_exatamente_um_bloco_core():
    text = AGENTS_MD.read_text(encoding="utf-8")
    assert text.count(gen.CORE_START) == 1
    assert text.count(gen.CORE_END) == 1
    assert text.index(gen.CORE_START) < text.index(gen.CORE_END)


def test_agents_md_nao_nomeia_tecnologia_legada():
    """Regra geral serve delphi, java, .net e o que vier — sem constante."""
    core = gen.read_agents_core().lower()
    for token in ("delphi", "vb6", "cobol", "powerbuilder", ".pas", ".dfm", "mediatr"):
        assert token not in core, f"AGENTS-CORE nomeia tecnologia legada: {token!r}"
    # `java`/`dotnet` só podem aparecer como exemplo de valor de configuração,
    # nunca como regra — e nem isso está presente hoje.
    assert not re.search(r"\bjava\b(?!script)", core)
    assert not re.search(r"\b(dotnet|\.net)\b", core)


# ─── Cobertura ───────────────────────────────────────────────────────────────

def test_todo_agente_despachavel_tem_wrapper(catalog, wrappers):
    """Sem wrapper, o agente só é alcançável por dispatch textual — que falha em
    silêncio (`Skill not found`, seguido de "execução direta" sem artefato)."""
    faltando = sorted({e["agent"] for e in catalog} - set(wrappers))
    assert not faltando, f"{len(faltando)} agente(s) sem wrapper: {faltando[:10]}"


def test_nenhum_wrapper_orfao(catalog, wrappers):
    """Wrapper sem agente correspondente vira agente fantasma no picker."""
    orfaos = sorted(set(wrappers) - {e["agent"] for e in catalog})
    assert not orfaos, f"wrapper(s) sem agente no registry: {orfaos}"


def test_sub_skills_nao_ganham_wrapper(wrappers):
    """`db-analyzer/skills/*.md` são apoio lido por um agente pai."""
    sub_skills = {r["agent"] for r in reg.load() if not r["dispatchable"]}
    assert not (sub_skills & set(wrappers))


# ─── Frontmatter — o que o M0 provou que quebra ──────────────────────────────

def test_frontmatter_nao_emite_campos_descartados(wrappers):
    """`version:`/`allowed-tools:` no topo são ignorados com warning; um wrapper
    com eles nasce sem restrição de tool e sem versão."""
    for agent_id, path in wrappers.items():
        block = _frontmatter(path)
        assert not re.search(r"^version:", block, re.MULTILINE), f"{agent_id}: `version:` no topo"
        assert not re.search(r"^allowed-tools:", block, re.MULTILINE), (
            f"{agent_id}: `allowed-tools:` — a chave enforçada é `tools:`"
        )
        for proibido in ("phase:", "module:", "inputs:", "outputs:", "dependencies:", "handoffs:"):
            assert not re.search(rf"^{re.escape(proibido)}", block, re.MULTILINE), (
                f"{agent_id}: campo não suportado no topo: {proibido}"
            )


def test_frontmatter_tem_os_campos_obrigatorios(wrappers):
    for agent_id, path in wrappers.items():
        block = _frontmatter(path)
        assert re.search(r"^name:\s*\S", block, re.MULTILINE), f"{agent_id}: sem `name`"
        assert re.search(r"^description:\s*\S", block, re.MULTILINE), (
            f"{agent_id}: sem `description` — é obrigatório no schema do CLI"
        )
        assert re.search(r"^tools:\s*\[", block, re.MULTILINE), f"{agent_id}: sem `tools`"
        assert re.search(r"^metadata:", block, re.MULTILINE), f"{agent_id}: sem `metadata`"


def test_name_casa_o_padrao_da_constituicao(wrappers):
    for agent_id, path in wrappers.items():
        nome = re.search(r"^name:\s*(\S+)", _frontmatter(path), re.MULTILINE).group(1)
        assert nome == agent_id, f"{path.name}: `name` {nome!r} não casa o arquivo"
        assert re.fullmatch(r"ava-[a-z0-9-]+", nome), f"{nome}: fora de ^ava-[a-z0-9-]+$"


def test_tools_usa_os_nomes_reais_do_cli(wrappers):
    """`Bash` não existe; a tool de shell chama-se `powershell` (M0 § 5)."""
    for agent_id, path in wrappers.items():
        raw = re.search(r"^tools:\s*(\[.*?\])", _frontmatter(path), re.MULTILINE).group(1)
        tools = json.loads(raw)
        assert tools, f"{agent_id}: `tools` vazio — o agente não conseguiria nem ler a spec"
        invalidas = sorted(set(tools) - VALID_TOOLS)
        assert not invalidas, f"{agent_id}: tools inválidas {invalidas}"
        assert "bash" not in tools, f"{agent_id}: `bash` não existe no CLI — use `powershell`"


def test_modelo_pinado_nunca_auto(wrappers):
    """Sem pin o sub-agente cai em gpt-5.4 e a chamada retorna 404 no BYOK."""
    for agent_id, path in wrappers.items():
        modelo = re.search(r"^model:\s*(\S+)", _frontmatter(path), re.MULTILINE)
        assert modelo, f"{agent_id}: sem `model`"
        assert modelo.group(1) == gen.DEFAULT_MODEL, f"{agent_id}: modelo {modelo.group(1)!r}"


def test_metadata_version_bate_com_o_frontmatter_canonico(wrappers):
    """O frontmatter da spec canônica é a autoridade da versão (Artigo II)."""
    for agent_id, path in wrappers.items():
        versao = re.search(r'^\s+version:\s*"([^"]*)"', _frontmatter(path), re.MULTILINE)
        assert versao, f"{agent_id}: sem `metadata.version`"
        canonico = reg.get(agent_id)
        assert canonico is not None
        assert versao.group(1) == (canonico["version"] or "0.0.0"), (
            f"{agent_id}: metadata.version divergente da spec canônica"
        )


def test_metadata_spec_aponta_para_arquivo_existente(wrappers):
    for agent_id, path in wrappers.items():
        alvo = re.search(r'^\s+spec:\s*"([^"]*)"', _frontmatter(path), re.MULTILINE)
        assert alvo, f"{agent_id}: sem `metadata.spec`"
        assert (REPO_ROOT / alvo.group(1)).is_file(), (
            f"{agent_id}: metadata.spec inexistente: {alvo.group(1)}"
        )


# ─── Corpo ───────────────────────────────────────────────────────────────────

def test_corpo_abaixo_do_cap_de_30k(wrappers):
    """Cap verificado no M0. Corpo maior é truncado pelo CLI — perda silenciosa."""
    estourados = {a: len(_body(p)) for a, p in wrappers.items()
                  if len(_body(p)) >= gen.BODY_CHAR_CAP}
    assert not estourados, f"corpo(s) ≥ {gen.BODY_CHAR_CAP} chars: {estourados}"


def test_corpo_carrega_o_bloco_agents_core_byte_a_byte(wrappers):
    """A herança dos guardrails é verificada, não presumida: o runner roda com
    `--no-custom-instructions`, então o bloco injetado é a única entrega."""
    core = gen.read_agents_core()
    for agent_id, path in wrappers.items():
        assert core in _body(path), (
            f"{agent_id}: bloco AGENTS-CORE ausente ou divergente de AGENTS.md — "
            "rode generate_agent_wrappers.py"
        )


def test_corpo_aponta_para_a_spec_canonica(wrappers):
    """O wrapper localiza a spec; nunca a substitui (fonte única de domínio)."""
    for agent_id, path in wrappers.items():
        corpo = _body(path)
        canonico = reg.get(agent_id)
        assert canonico["path"] in corpo, f"{agent_id}: corpo não referencia a spec canônica"
        assert gen.GENERATED_HEADER in corpo, f"{agent_id}: sem marca de arquivo gerado"


# ─── Determinismo do gerador ─────────────────────────────────────────────────

def test_disco_em_dia_com_o_registry():
    """Mesmo contrato do `--check` no CI: wrapper editado à mão é reprovado."""
    problemas = gen.check(gen.build_all())
    assert not problemas, (
        f"{len(problemas)} divergência(s); rode generate_agent_wrappers.py: {problemas[:5]}"
    )


def test_geracao_e_deterministica():
    """Duas gerações seguidas produzem bytes idênticos."""
    assert gen.build_all() == gen.build_all()


def test_tool_name_map_cobre_as_tools_declaradas():
    """Toda tool usada em `allowed-tools` tem tradução — sem tradução, o grant
    some silenciosamente e o agente não consegue gravar o que promete."""
    declaradas: set[str] = set()
    for record in reg.load():
        if record["dispatchable"] and not record["deprecated"]:
            declaradas.update(t.strip() for t in record.get("tools") or [])
    faltando = sorted(declaradas - set(gen.TOOL_NAME_MAP))
    assert not faltando, f"tools sem entrada em TOOL_NAME_MAP: {faltando}"
