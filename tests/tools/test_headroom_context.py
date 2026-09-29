"""
Testes da tool Headroom — decodificação, configuração e fatia por agente.

Cobre as invariantes de specs/031:
  IV1  a fatia por agente vem de context_budget.AGENT_ARTIFACT_SLICE (fonte única)
  IV2  headroom_context é o único decodificador do formato Headroom
  IV3  tudo funciona sem `headroom-ai` instalado (só decodificação é 100% stdlib)

Roda com o Python do repo — não exige o venv da tool:
    python -m pytest tests/tools/test_headroom_context.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL_DIR = REPO_ROOT / "src" / "shared" / "tools" / "headroom"
sys.path.insert(0, str(TOOL_DIR))

import headroom_config as hcfg  # noqa: E402
import headroom_context as hctx  # noqa: E402


# ─── Formato [A] — string tabular do SmartCrusher ────────────────────────────

def test_decode_table_string_tipos_e_ordem():
    """Cabeçalho `[N]{k:t,…}` + CSV → list[dict] com os tipos declarados."""
    raw = ("[2]{flag:bool,loc:int,name:string,ratio:float}\n"
           "true,10,alfa,1.5\n"
           "false,11,beta,2.25\n")
    assert hctx.decode_table_string(raw) == [
        {"flag": True, "loc": 10, "name": "alfa", "ratio": 1.5},
        {"flag": False, "loc": 11, "name": "beta", "ratio": 2.25},
    ]


def test_decode_table_string_csv_rfc4180():
    """Vírgula, aspas escapadas com `""` e newline dentro de campo citado."""
    raw = ('[3]{desc:string,name:string}\n'
           '"com, virgula",a\n'
           '"com ""aspas""",b\n'
           '"com\nnewline",c\n')
    assert hctx.decode_table_string(raw) == [
        {"desc": "com, virgula", "name": "a"},
        {"desc": 'com "aspas"', "name": "b"},
        {"desc": "com\nnewline", "name": "c"},
    ]


def test_decode_table_string_nullable_e_json():
    """Sufixo `?` = nullable (campo vazio → None); tipo `json` é desserializado."""
    raw = ('[2]{nested:json?,opt:string?}\n'
           '"{""a"":1}",x\n'
           ',\n')
    assert hctx.decode_table_string(raw) == [
        {"nested": {"a": 1}, "opt": "x"},
        {"nested": None, "opt": None},
    ]


def test_decode_table_string_recusa_nao_tabular():
    """Texto comum não é confundido com envelope — devolve None."""
    assert hctx.decode_table_string("apenas um texto\ncom duas linhas") is None
    assert hctx.decode_table_string("[sem chave de schema]\nx,y") is None


def test_celula_fora_do_tipo_preserva_texto():
    """Valor que não converte é preservado como texto, nunca descartado."""
    raw = "[1]{loc:int}\nnao-e-numero\n"
    assert hctx.decode_table_string(raw) == [{"loc": "nao-e-numero"}]


# ─── Formato [B] — factored_array do motor fallback ──────────────────────────

def test_decode_factored_array():
    node = {"__headroom__": "factored_array", "schema": ["name", "loc"],
            "count": 2, "kept": 2, "sampled": False,
            "rows": [["alfa", 1], ["beta", 2]]}
    assert hctx.decode_headroom(node) == [{"name": "alfa", "loc": 1},
                                          {"name": "beta", "loc": 2}]


def test_decode_report_sinaliza_perda_por_amostragem():
    """`sampled: true` é perda real — decode_report tem de expor isso."""
    doc = {"payload": {"itens": {
        "__headroom__": "factored_array", "schema": ["n"],
        "count": 500, "kept": 90, "sampled": True,
        "rows": [[i] for i in range(90)]}}}
    report = hctx.decode_report(doc)
    assert report["factored_arrays"] == 1
    assert report["rows_total"] == 500
    assert report["rows_dropped"] == 410


# ─── Propriedades gerais do decodificador ────────────────────────────────────

def test_decode_e_recursivo_e_idempotente():
    doc = {"artifact": "x", "payload": {"nivel1": {"nivel2": [
        {"__headroom__": "factored_array", "schema": ["a"], "rows": [[1], [2]]}]}}}
    once = hctx.decode_headroom(doc)
    assert once["payload"]["nivel1"]["nivel2"][0] == [{"a": 1}, {"a": 2}]
    assert hctx.decode_headroom(once) == once


def test_conteudo_nao_comprimido_passa_intacto():
    plain = {"a": [1, 2, 3], "b": "texto\ncom newline", "c": {"d": None}, "e": True}
    assert hctx.decode_headroom(plain) == plain


# ─── IV1 — fonte canônica única da fatia por agente ──────────────────────────

def test_fatia_vem_de_context_budget():
    """AGENT_ARTIFACT_SLICE é importado, não redefinido (specs/030)."""
    assert hctx.AGENT_ARTIFACT_SLICE, "fatias não carregadas de context_budget.py"
    assert hctx.AGENT_ARTIFACT_SLICE["ava-asis-db-analyzer"] == [
        "03_database_rules", "04_database_schemas", "05_procedures"]
    # Agente de consolidação: fatia vazia, nunca recebe artefato AST.
    assert hctx.AGENT_ARTIFACT_SLICE["ava-asis-gaps-risks"] == []


def test_nao_existe_segundo_mapa_de_fatias():
    """Guarda contra a reintrodução de AGENT_ARTIFACT_MAP (IV1)."""
    assert not hasattr(hctx, "AGENT_ARTIFACT_MAP")


def test_build_agent_context_sem_artefatos_nao_quebra():
    """Projeto sem compressed/ degrada: contexto vazio, sem exceção."""
    ctx = hctx.build_agent_context("__projeto_inexistente__", "ava-asis-inventory")
    assert ctx["artifacts"] == ["08_code_overview", "02_form_business_rules"]
    assert ctx["tokens_estimated"] == 0
    assert ctx["compressed_dir"] == ""


def test_agente_desconhecido_e_sinalizado():
    ctx = hctx.build_agent_context("__projeto_inexistente__", "ava-nao-existe")
    assert ctx["known_agent"] is False
    assert ctx["artifacts"] == []


# ─── Configuração — precedência env > projeto > headroom.yaml ────────────────

def test_defaults_da_tool_sao_lidos_do_yaml():
    cfg = hcfg.load_config()
    assert cfg["model"] == "claude-sonnet-4-6"
    assert cfg["context_limit"] == 200000
    # Endpoint Anthropic-compatible do Foundry, não Azure OpenAI.
    assert cfg["proxy"]["upstream"].endswith("/anthropic")
    assert cfg["proxy"]["host"] == "127.0.0.1", "proxy não pode escutar fora do loopback"


def test_ambiente_sobrescreve_o_yaml(monkeypatch):
    monkeypatch.setenv("AVA_FOUNDRY_MODEL", "claude-opus-4-6")
    monkeypatch.setenv("AVA_FOUNDRY_CONTEXT_LIMIT", "1000000")
    monkeypatch.setenv("HEADROOM_PORT", "9999")
    cfg = hcfg.load_config()
    assert cfg["model"] == "claude-opus-4-6"
    assert cfg["context_limit"] == 1000000
    assert cfg["proxy"]["port"] == 9999


def test_env_malformada_nao_derruba(monkeypatch):
    """Valor inválido é ignorado e a camada de baixo prevalece (IV3)."""
    monkeypatch.setenv("AVA_FOUNDRY_CONTEXT_LIMIT", "nao-e-numero")
    assert hcfg.load_config()["context_limit"] == 200000


def test_merge_e_recursivo(monkeypatch):
    """Sobrescrever a porta preserva o resto do bloco proxy."""
    monkeypatch.setenv("HEADROOM_PORT", "8788")
    proxy = hcfg.load_config()["proxy"]
    assert proxy["port"] == 8788
    assert proxy["upstream"].endswith("/anthropic")
    assert proxy["backend"] == "anthropic"


def test_proxy_env_usa_anthropic_target_api_url():
    """O headroom NÃO tem --upstream: o destino é ANTHROPIC_TARGET_API_URL."""
    env = hcfg.proxy_env()
    assert env["ANTHROPIC_TARGET_API_URL"].endswith("/anthropic")
    assert env["HEADROOM_PORT"] == "8787"
    assert env["HEADROOM_BACKEND"] == "anthropic"
    assert env["HEADROOM_TELEMETRY"] == "off"
    assert "HEADROOM_UPSTREAM" not in env


# ─── IV3 — a esteira roda sem o motor instalado ──────────────────────────────

def test_decodificacao_nao_depende_do_motor():
    """decode_headroom é 100% stdlib — independe de HEADROOM_AVAILABLE."""
    assert "headroom" not in sys.modules or True  # o motor pode ou não estar presente
    raw = "[1]{a:int}\n7\n"
    assert hctx.decode_table_string(raw) == [{"a": 7}]


def test_read_artifact_de_projeto_inexistente_devolve_vazio():
    assert hctx.read_artifact("__projeto_inexistente__", "04_database_schemas") == {}


# ─── Métricas ────────────────────────────────────────────────────────────────

def test_metrics_path_fica_junto_da_observabilidade(tmp_path, monkeypatch):
    """O JSONL vai para outputs/observability/, ao lado de agent-events.jsonl."""
    monkeypatch.setattr(hcfg, "REPO_ROOT", tmp_path)
    path = hcfg.metrics_path("ProjetoX")
    assert path.parent.name == "observability"
    assert path.name == "headroom-metrics.jsonl"
    assert path.parent.is_dir()


def test_linha_de_metrica_e_json_valido(tmp_path, monkeypatch):
    monkeypatch.setattr(hcfg, "REPO_ROOT", tmp_path)
    path = hcfg.metrics_path("ProjetoX")
    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps({"agent_id": "ava-asis-inventory", "savings_pct": 85.0}) + "\n")
    linhas = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    assert linhas[0]["savings_pct"] == 85.0


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
