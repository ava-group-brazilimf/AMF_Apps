"""Testes do tratamento de erro do runner de produção (`ava-pipeline-runner-cli.py`).

Motivação concreta: o `except` que degradava uma tool reprovada lia `on_fail`
como nome solto — inexistente naquele escopo. O resultado para o operador era
um `NameError` levantado DENTRO do handler, soterrando a falha real que já
estava explicada na tela logo acima. Defeito no tratamento de erro é pior que
o erro tratado: apaga o diagnóstico.

Roda com o Python do repo:
    python -m pytest tests/tools/test_runner_error_handling.py -q
"""
from __future__ import annotations

import builtins
import symtable
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_19 = REPO_ROOT / "ava-pipeline-runner-cli.py"


@pytest.fixture(scope="module")
def fonte() -> str:
    if not RUNNER_19.is_file():
        pytest.skip("ava-pipeline-runner-cli.py ausente neste checkout")
    return RUNNER_19.read_text(encoding="utf-8")


def nomes_indefinidos(source: str, filename: str = "runner") -> list[tuple[str, str]]:
    """Nomes lidos dentro de funções que não são local, global do módulo nem builtin.

    Equivale ao F821 do pyflakes, que não está disponível neste ambiente. O
    `symtable` do CPython já classifica cada símbolo por escopo — um símbolo
    marcado `is_global()` dentro de uma função só é válido se existir de fato
    no topo do módulo ou nos builtins.
    """
    topo = symtable.symtable(source, filename, "exec")
    conhecidos = set(topo.get_identifiers()) | set(dir(builtins))
    achados: list[tuple[str, str]] = []

    def visitar(tabela: symtable.SymbolTable, caminho: list[str]) -> None:
        for filha in tabela.get_children():
            visitar(filha, caminho + [filha.get_name()])
        if tabela.get_type() != "function":
            return
        for simbolo in tabela.get_symbols():
            if (simbolo.is_global() and simbolo.is_referenced()
                    and simbolo.get_name() not in conhecidos):
                achados.append((".".join(caminho), simbolo.get_name()))

    visitar(topo, ["<module>"])
    return sorted(set(achados))


def test_runner_nao_referencia_nome_indefinido(fonte: str):
    """Nenhuma função lê um nome que não existe — o defeito que gerou o NameError."""
    achados = nomes_indefinidos(fonte)
    assert not achados, (
        "nome(s) indefinido(s) no runner — vira NameError só em runtime, "
        f"tipicamente no caminho de erro que quase nunca é exercitado: {achados}"
    )


def test_a_checagem_pegaria_o_defeito_original(fonte: str):
    """Prova que o teste acima tem poder de detecção, e não passa por vacuidade."""
    com_bug = fonte.replace(
        'if str(step.get("on_fail") or "") == "warn" else',
        'if on_fail == "warn" else',
        1,
    )
    if com_bug == fonte:
        pytest.skip("trecho corrigido não encontrado — reescrito desde então")
    assert ("main", "on_fail") in [
        (caminho.split(".")[-1], nome)
        for caminho, nome in nomes_indefinidos(com_bug, "com-bug")
    ]


def test_falha_de_tool_le_on_fail_do_passo(fonte: str):
    """`on_fail` é atributo do passo do DAG — nunca uma variável de escopo."""
    assert 'if str(step.get("on_fail") or "") == "warn" else' in fonte


def test_entrypoint_converte_excecao_em_mensagem_objetiva(fonte: str):
    """Traceback cru nunca é a última palavra para o operador.

    O bloco `__main__` precisa capturar o que escapar de `main()` e traduzir
    em causa + próximo passo, mantendo o trace como anexo para quem for
    corrigir o runner.
    """
    assert "def _abortar_com_mensagem" in fonte
    assert "ERRO INTERNO DO PIPELINE_RUNNER" in fonte
    assert "except KeyboardInterrupt:" in fonte, (
        "Ctrl-C do operador não é defeito — não pode sair como stack trace")
    entrypoint = fonte.split('if __name__ == "__main__":')[-1]
    assert "_abortar_com_mensagem" in entrypoint, (
        "o conversor precisa estar ligado ao entrypoint, não apenas definido")
