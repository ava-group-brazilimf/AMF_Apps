"""
Testes da resolução de configuração do CLI da esteira.

O ponto da entrega é ter UMA fonte de modelo/endpoint/proxy. Estes testes
travam a precedência declarada em ava-pipeline.yaml:

    flags do CLI > env > project-config.yaml > ava-pipeline.yaml > fallback

Roda com o Python do repo:
    python -m pytest tests/tools/test_pipeline_config.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "shared" / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import pipeline_config as pc  # noqa: E402

ENV_VARS = [name for name, _, _ in pc._ENV_MAP]


@pytest.fixture(autouse=True)
def env_limpo(monkeypatch):
    """Nenhum teste pode depender do ambiente da máquina que roda o CI."""
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)


# ─── Ancoragem ───────────────────────────────────────────────────────────────

def test_repo_root_aponta_para_o_repo():
    """O runner antigo tinha WORKSPACE hardcoded para OUTRO checkout."""
    assert pc.REPO_ROOT == REPO_ROOT
    assert (pc.REPO_ROOT / "src" / "shared" / "tools").is_dir()


def test_yaml_de_defaults_existe():
    assert pc.TOOL_CONFIG.is_file(), f"{pc.TOOL_CONFIG} sumiu"


# ─── Camadas ─────────────────────────────────────────────────────────────────

def test_yaml_vence_o_fallback():
    """O YAML é a fonte editável; o fallback só cobre o YAML sumir."""
    cfg = pc.load_config()
    assert cfg["steps"], "steps deveriam vir do YAML — fallback traz lista vazia"
    # 13: F3S (SpecKit) + F4 (git-backed Speckit codegen) — F4S foi fundido no F4.
    # A contagem exata é travada em tests/tools/test_pipeline_plan.py::ESTEIRA.
    assert len(cfg["steps"]) == 13


def test_env_vence_o_yaml(monkeypatch):
    monkeypatch.setenv("AVA_FOUNDRY_MODEL", "claude-opus-4-6")
    assert pc.load_config()["models"]["default"] == "claude-opus-4-6"


def test_env_converte_tipos(monkeypatch):
    monkeypatch.setenv("AVA_PIPELINE_MAX_TOKENS", "1024")
    monkeypatch.setenv("AVA_PIPELINE_DNS_OVERRIDES", "true")
    cfg = pc.load_config()
    assert cfg["foundry"]["max_tokens"] == 1024
    assert cfg["dns_overrides"]["enabled"] is True


def test_env_malformada_nao_derruba_e_mantem_a_camada_abaixo(monkeypatch, capsys):
    """Config ruim degrada com aviso — a esteira não pode parar por isso (IV3)."""
    base = pc.load_config()["foundry"]["max_tokens"]
    monkeypatch.setenv("AVA_PIPELINE_MAX_TOKENS", "nao-e-numero")
    cfg = pc.load_config()
    assert cfg["foundry"]["max_tokens"] == base
    assert "ignorado" in capsys.readouterr().err


def test_env_vazia_e_ignorada(monkeypatch):
    base = pc.load_config()["models"]["default"]
    monkeypatch.setenv("AVA_FOUNDRY_MODEL", "")
    assert pc.load_config()["models"]["default"] == base


def test_project_config_vence_o_yaml(tmp_path, monkeypatch):
    """Bloco `pipeline:` do project-config.yaml sobrescreve os defaults."""
    proj = tmp_path / "projects" / "P" / "context"
    proj.mkdir(parents=True)
    (proj / "project-config.yaml").write_text(
        "project_name: P\npipeline:\n  models:\n    default: do-projeto\n",
        encoding="utf-8")
    monkeypatch.setattr(pc, "REPO_ROOT", tmp_path)
    assert pc.load_config("P")["models"]["default"] == "do-projeto"


def test_env_vence_o_project_config(tmp_path, monkeypatch):
    proj = tmp_path / "projects" / "P" / "context"
    proj.mkdir(parents=True)
    (proj / "project-config.yaml").write_text(
        "pipeline:\n  models:\n    default: do-projeto\n", encoding="utf-8")
    monkeypatch.setattr(pc, "REPO_ROOT", tmp_path)
    monkeypatch.setenv("AVA_FOUNDRY_MODEL", "do-env")
    assert pc.load_config("P")["models"]["default"] == "do-env"


def test_project_sem_bloco_pipeline_nao_quebra():
    """MeuERP-002 não declara `pipeline:` — tem de cair nos defaults."""
    assert pc.load_config("MeuERP-002")["models"]["default"] == "claude-sonnet-4-6"


# ─── Merge ───────────────────────────────────────────────────────────────────

def test_merge_e_recursivo_em_dicts():
    base = {"a": {"x": 1, "y": 2}}
    assert pc._deep_merge(base, {"a": {"y": 9}}) == {"a": {"x": 1, "y": 9}}


def test_merge_substitui_listas_por_inteiro():
    """`steps:` de um projeto substitui a esteira, nunca funde por índice."""
    base = {"steps": [1, 2, 3]}
    assert pc._deep_merge(base, {"steps": [9]}) == {"steps": [9]}


def test_merge_nao_muta_a_base():
    base = {"a": {"x": 1}, "steps": [1]}
    pc._deep_merge(base, {"a": {"x": 2}, "steps": [3]})
    assert base == {"a": {"x": 1}, "steps": [1]}


# ─── Modelo ──────────────────────────────────────────────────────────────────

def test_cli_vence_tudo(monkeypatch):
    monkeypatch.setenv("AVA_FOUNDRY_MODEL", "do-env")
    assert pc.resolve_model(pc.load_config(), "explicito") == "explicito"


def test_alias_e_expandido():
    assert pc.resolve_model(pc.load_config(), "sonnet") == "claude-sonnet-4-6"


def test_modelo_sem_alias_passa_direto():
    assert pc.resolve_model(pc.load_config(), "claude-opus-4-6") == "claude-opus-4-6"


# ─── API key ─────────────────────────────────────────────────────────────────

def test_api_key_ausente_reprova_com_instrucao(tmp_path, monkeypatch):
    monkeypatch.setattr(pc, "REPO_ROOT", tmp_path)
    with pytest.raises(SystemExit, match="não encontrado"):
        pc.api_key({"foundry": {"api_key_file": ".copilot-key"}})


def test_api_key_vazia_reprova(tmp_path, monkeypatch):
    (tmp_path / ".copilot-key").write_text("   ", encoding="utf-8")
    monkeypatch.setattr(pc, "REPO_ROOT", tmp_path)
    with pytest.raises(SystemExit, match="vazio"):
        pc.api_key({"foundry": {"api_key_file": ".copilot-key"}})


# ─── Proxy ───────────────────────────────────────────────────────────────────

def _constantes_de_codigo(path: Path) -> list[object]:
    """Constantes que o módulo realmente avalia — sem docstrings nem comentários."""
    import ast

    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = {
        id(node.body[0].value)
        for node in ast.walk(tree)
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and node.body and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    }
    return [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and id(n) not in docstrings]


def test_proxy_nunca_e_hardcoded():
    """Host/porta vêm de headroom_config.py, nunca de literal neste módulo.

    Porta duplicada foi o defeito que fez o launcher sondar 8787 com o proxy em
    8788 e degradar em silêncio, rodando a fase inteira sem compressão.
    """
    constantes = _constantes_de_codigo(TOOLS_DIR / "pipeline_config.py")
    assert 8787 not in constantes
    assert not [c for c in constantes if isinstance(c, str) and "127.0.0.1" in c]

    cmd = pc.load_config()["proxy"]["url_command"]
    assert cmd[0].endswith("headroom_config.py")
    assert "--proxy-url" in cmd


def test_endpoint_e_modelo_nao_sao_hardcoded_no_cli():
    """Endpoint/modelo vivem no YAML. No CLI só pode haver referência à config.

    O ava_pipeline.py é o lugar mais tentador para "só desta vez" cravar um
    valor — é ele que o operador chama.
    """
    constantes = _constantes_de_codigo(TOOLS_DIR / "ava_pipeline.py")
    suspeitos = [c for c in constantes if isinstance(c, str)
                 and ("services.ai.azure.com" in c or c.startswith("claude-"))]
    assert not suspeitos, f"valores que deveriam vir do YAML: {suspeitos}"


def test_proxy_indisponivel_devolve_none_sem_levantar(monkeypatch):
    monkeypatch.setattr(pc, "_run_tool", lambda *a, **k: None)
    assert pc.proxy_url(pc.load_config()) is None
    assert pc.proxy_alive(pc.load_config()) is False


# ─── Resolução de rota ───────────────────────────────────────────────────────
# Determinístico de propósito: derrubar o proxy real para testar a degradação
# mexeria no ambiente de quem roda a suíte.

import ava_pipeline as ap  # noqa: E402


@pytest.fixture
def proxy_fora(monkeypatch):
    monkeypatch.setattr(ap.pipeline_config, "proxy_url", lambda cfg: "http://127.0.0.1:8787")
    monkeypatch.setattr(ap.pipeline_config, "proxy_alive", lambda cfg: False)


@pytest.fixture
def proxy_no_ar(monkeypatch):
    monkeypatch.setattr(ap.pipeline_config, "proxy_url", lambda cfg: "http://127.0.0.1:9999")
    monkeypatch.setattr(ap.pipeline_config, "proxy_alive", lambda cfg: True)


def test_rota_usa_o_proxy_quando_no_ar(proxy_no_ar):
    rota = ap.resolve_route(pc.load_config(), "auto")
    assert rota.via_proxy is True
    assert rota.base_url == "http://127.0.0.1:9999"


def test_base_url_do_proxy_nao_leva_sufixo_de_path(proxy_no_ar):
    """O SDK acrescenta /v1/messages — rota registrada no proxy."""
    assert not ap.resolve_route(pc.load_config(), "auto").base_url.endswith("/anthropic")


def test_auto_degrada_com_aviso_alto(proxy_fora, capsys):
    """Nunca rodar sem compressão em silêncio — o aviso é a mitigação."""
    cfg = pc.load_config()
    rota = ap.resolve_route(cfg, "auto")
    assert rota.via_proxy is False
    assert rota.base_url == cfg["foundry"]["endpoint"]
    assert "SEM compressão" in capsys.readouterr().out


def test_require_aborta_quando_o_proxy_esta_fora(proxy_fora):
    with pytest.raises(SystemExit, match="não respondeu"):
        ap.resolve_route(pc.load_config(), "require")


def test_off_nao_consulta_o_proxy(monkeypatch):
    def explode(cfg):
        raise AssertionError("mode=off não pode sondar o proxy")

    monkeypatch.setattr(ap.pipeline_config, "proxy_alive", explode)
    rota = ap.resolve_route(pc.load_config(), "off")
    assert rota.via_proxy is False
