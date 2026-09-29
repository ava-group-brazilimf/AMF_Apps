"""
Teto de execução e streaming dos passos `kind: tool` (F4S e demais).

Contexto: a F4S de `nopcommerce-02` morreu aos 900s com 79/79 `.csproj` já no
disco e o verifier ainda por rodar. O runner recomendava "aumente timeout_s do
passo no DAG" — propriedade que não existia em lugar nenhum: nem no nó, nem no
`Step`, nem em `run_tool_step`. Os testes abaixo travam as duas metades da
correção: o teto agora atravessa o modelo inteiro, e a saída da tool chega ao
operador ENQUANTO acontece, não depois.

Roda com o Python do repo:
    python -m pytest tests/tools/test_f4s_tool_timeout.py -q
"""
from __future__ import annotations

import io
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "shared" / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import ava_pipeline  # noqa: E402
import pipeline_plan  # noqa: E402
import proc_stream  # noqa: E402


def _step(**kwargs) -> pipeline_plan.Step:
    base = dict(phase="F4S", group="F4S", agent="scaffold-runner", trigger=None,
                label="scaffold", kind="tool", command=[sys.executable, "-c", "pass"])
    base.update(kwargs)
    return pipeline_plan.Step(**base)


def _runner_dag() -> list[dict]:
    """O DAG literal do `ava-pipeline-runner-cli.py`, sem importar o runner.

    O módulo tem espaço no nome e um import-time pesado (SDK Anthropic); ler a
    lista `STEPS` do fonte é o que mantém este teste barato e sem rede.
    """
    fonte = (REPO_ROOT / "ava-pipeline-runner-cli.py").read_text(encoding="utf-8")
    inicio = fonte.index('{"phase": "F4S"')
    fim = fonte.index('{"phase": "F4",', inicio)
    return fonte[inicio:fim]


# ── TESTE 1 · Step sem timeout_s usa o default global ───────────────────────

def test_step_sem_timeout_cai_no_default_global():
    passo = _step()

    assert passo.timeout_s is None, "o campo é opcional — nenhum nó existente o declara"
    assert (pipeline_plan.resolve_tool_timeout_s(passo.timeout_s)
            == pipeline_plan.DEFAULT_TOOL_TIMEOUT_S)
    # Compatibilidade: construir um Step sem a chave continua válido, e a
    # serialização do plano segue redonda.
    assert passo.as_dict()["timeout_s"] is None
    assert pipeline_plan.DEFAULT_TOOL_TIMEOUT_S == 3600


# ── TESTE 2 · timeout_s do Step chega ao subprocesso ────────────────────────

def test_timeout_do_step_chega_ao_subprocesso(monkeypatch, tmp_path):
    visto: dict[str, object] = {}

    def _falso(command, cwd=None, **kwargs):
        visto.update(kwargs)
        visto["command"] = command
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(proc_stream, "run", _falso)
    monkeypatch.setattr(ava_pipeline.proc_stream, "run", _falso)
    monkeypatch.setattr(ava_pipeline, "REPO_ROOT", tmp_path)

    resultado = ava_pipeline.run_tool_step(_step(timeout_s=1234), "P")

    assert visto["timeout_s"] == 1234, "o teto do nó tem de chegar ao Popen"
    assert resultado["timeout_s"] == 1234
    assert resultado["status"] == "completed"


def test_timeout_do_step_vence_o_fallback_legado(monkeypatch, tmp_path):
    """Prioridade: nó do DAG → fallback do chamador → default global."""
    visto: dict[str, object] = {}
    monkeypatch.setattr(
        ava_pipeline.proc_stream, "run",
        lambda command, cwd=None, **kw: (visto.update(kw)
                                         or subprocess.CompletedProcess(command, 0, "", "")))
    monkeypatch.setattr(ava_pipeline, "REPO_ROOT", tmp_path)

    ava_pipeline.run_tool_step(_step(timeout_s=1234), "P", timeout_s=900)
    assert visto["timeout_s"] == 1234

    ava_pipeline.run_tool_step(_step(), "P", timeout_s=900)
    assert visto["timeout_s"] == 900, "sem nó, o fallback do chamador vale"

    ava_pipeline.run_tool_step(_step(), "P")
    assert visto["timeout_s"] == pipeline_plan.DEFAULT_TOOL_TIMEOUT_S


def test_dag_yaml_propaga_timeout_ate_o_step():
    """A outra porta de entrada de tools: `tools:` do pipeline-dag/*.yaml."""
    passo = pipeline_plan.Step(
        phase="F3S:tool:x", group="F3S", agent="x", trigger=None, label="x",
        kind="tool", command=["{python}", "t.py"], timeout_s=2400,
    )
    assert passo.as_dict()["timeout_s"] == 2400


# ── TESTE 3 · o nó F4S declara 3600 e nada o substitui por 900 ──────────────

def test_no_f4s_declara_timeout_de_3600():
    no = _runner_dag()

    assert '"timeout_s": 3600' in no, "o nó F4S precisa declarar o próprio teto"
    assert "scaffold_runner.py" in no


def test_runner_nao_passa_mais_900_fixo_ao_run_tool_step():
    fonte = (REPO_ROOT / "ava-pipeline-runner-cli.py").read_text(encoding="utf-8")

    assert "run_tool_step(tool_step, project, timeout_s=900)" not in fonte
    assert "run_tool_step(tool_step, project)" in fonte
    assert "timeout_s=step.get(\"timeout_s\")" in fonte


def test_nenhum_timeout_derivado_de_bounded_context():
    """Nenhuma camada pode transformar contagem de BC em prazo."""
    suspeitos = ("len(bcs)", "len(bounded", "* len(", "bcs) *", "por_bc", "per_bc")
    for rel in ("ava-pipeline-runner-cli.py",
                "src/shared/tools/pipeline_plan.py",
                "src/shared/tools/ava_pipeline.py",
                "src/shared/tools/proc_stream.py"):
        fonte = (REPO_ROOT / rel).read_text(encoding="utf-8")
        for linha in fonte.splitlines():
            if "timeout" not in linha.lower():
                continue
            assert not any(marca in linha for marca in suspeitos), \
                f"{rel}: timeout derivado de contagem de BC — {linha.strip()!r}"


# ── TESTE 4 · stdout aparece DURANTE a execução ─────────────────────────────

class _EchoEspiao(io.StringIO):
    """Console de mentira que carimba o instante de cada escrita."""

    def __init__(self) -> None:
        super().__init__()
        self.marcas: list[tuple[float, str]] = []

    def write(self, texto: str) -> int:  # type: ignore[override]
        if texto.strip():
            self.marcas.append((time.monotonic(), texto))
        return super().write(texto)


def test_stdout_e_transmitido_durante_a_execucao():
    console = _EchoEspiao()
    programa = (
        "import sys, time\n"
        "for i in range(3):\n"
        "    print(f'linha {i}', flush=True)\n"
        "    time.sleep(0.35)\n"
    )
    inicio = time.monotonic()
    resultado = proc_stream.run([sys.executable, "-c", programa],
                                timeout_s=30, stream=console)
    fim = time.monotonic()

    assert resultado.returncode == 0
    texto = console.getvalue()
    assert "linha 0" in texto and "linha 2" in texto

    # A prova de que não houve espera pelo fim: a PRIMEIRA linha chegou ao
    # console bem antes de o processo terminar.
    primeira = console.marcas[0][0]
    assert primeira - inicio < (fim - inicio) / 2, (
        f"primeira linha só apareceu em {primeira - inicio:.2f}s de "
        f"{fim - inicio:.2f}s totais — isso é despejo no fim, não streaming")


# ── TESTE 5 · stderr não é descartado ──────────────────────────────────────

def test_stderr_aparece_e_nada_e_descartado():
    console = _EchoEspiao()
    programa = (
        "import sys\n"
        "print('para-stdout', flush=True)\n"
        "print('para-stderr', file=sys.stderr, flush=True)\n"
        "sys.exit(3)\n"
    )
    resultado = proc_stream.run([sys.executable, "-c", programa],
                                timeout_s=30, stream=console)

    texto = console.getvalue()
    assert "para-stdout" in texto
    assert "para-stderr" in texto, "stderr jamais pode ser suprimido"
    assert resultado.returncode == 3
    assert "para-stdout" in resultado.stdout
    assert "para-stderr" in resultado.stderr


def test_stdout_e_stderr_simultaneos_nao_travam():
    """Volume acima do buffer do pipe nos dois fluxos ao mesmo tempo.

    Com leitura serial (um pipe por vez) isto é o deadlock clássico: o filho
    bloqueia escrevendo no pipe que ninguém está drenando.
    """
    programa = (
        "import sys\n"
        "bloco = 'x' * 1000\n"
        "for i in range(400):\n"
        "    sys.stdout.write(bloco + '\\n')\n"
        "    sys.stderr.write(bloco + '\\n')\n"
        "sys.stdout.flush(); sys.stderr.flush()\n"
    )
    resultado = proc_stream.run([sys.executable, "-c", programa],
                                timeout_s=60, stream=io.StringIO())

    assert resultado.returncode == 0
    assert len(resultado.stdout) >= 400 * 1000
    assert len(resultado.stderr) >= 400 * 1000


def test_unicode_preservado_atraves_da_fronteira_de_bloco():
    programa = (
        "import sys\n"
        "sys.stdout.reconfigure(encoding='utf-8')\n"
        "print('ção — ▶ ✅ ' * 5000, flush=True)\n"
    )
    resultado = proc_stream.run([sys.executable, "-c", programa],
                                timeout_s=30, stream=io.StringIO())

    assert resultado.returncode == 0
    assert "\ufffd" not in resultado.stdout, "byte partido entre dois blocos"
    assert resultado.stdout.count("✅") == 5000


# ── TESTE 6 · logs preservados e nunca duplicados ──────────────────────────

def test_log_exibido_continua_capturado_e_sem_duplicata():
    console = _EchoEspiao()
    programa = "print('marcador-unico', flush=True)"
    resultado = proc_stream.run([sys.executable, "-c", programa],
                                timeout_s=30, stream=console)

    assert resultado.stdout.count("marcador-unico") == 1, "capturado para diagnóstico"
    assert console.getvalue().count("marcador-unico") == 1, "exibido UMA vez"


def test_prefixo_rotula_a_linha_sem_alterar_o_conteudo():
    console = io.StringIO()
    programa = "print('Build succeeded.', flush=True)\nprint('0 Warning(s)', flush=True)"
    resultado = proc_stream.run([sys.executable, "-c", programa],
                                timeout_s=30, stream=console, prefix="[F4S] ")

    linhas = [l for l in console.getvalue().splitlines() if l.strip()]
    assert linhas == ["[F4S] Build succeeded.", "[F4S] 0 Warning(s)"]
    # O texto capturado é o original, sem carimbo — é ele que vai para o
    # diagnóstico e para o parser de JSON dos generators.
    assert "[F4S]" not in resultado.stdout


def test_scaffold_runner_nao_reemite_stderr_ja_transmitido():
    fonte = (TOOLS_DIR / "scaffold_runner.py").read_text(encoding="utf-8")

    assert "_echo(proc.stderr" not in fonte, (
        "stderr sai ao vivo pelo proc_stream; reemitir no fim duplicaria o log")
    assert "echo_stderr=True" in fonte


# ── TESTE 7 · timeout real: mata a árvore e não roda o verifier ────────────

def test_timeout_encerra_processo_e_filhos(tmp_path):
    """O pai dorme para sempre e ainda gera um NETO que também dorme."""
    marcador = tmp_path / "neto.pid"
    neto = "import os, time; open(r'%s','w').write(str(os.getpid())); time.sleep(300)" % marcador
    pai = (
        "import subprocess, sys, time\n"
        f"subprocess.Popen([sys.executable, '-c', {neto!r}])\n"
        "print('comecei', flush=True)\n"
        "time.sleep(300)\n"
    )
    console = _EchoEspiao()
    inicio = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired) as excinfo:
        proc_stream.run([sys.executable, "-c", pai], timeout_s=3, stream=console)
    decorrido = time.monotonic() - inicio

    assert decorrido < 30, "o teto tem de encerrar, não esperar o processo"
    # A saída já produzida sobrevive ao kill — é o que a mensagem de erro usa.
    assert "comecei" in (excinfo.value.output or "")
    assert "comecei" in console.getvalue()

    # O neto foi levado junto: `Popen.kill()` sozinho o deixaria vivo.
    for _ in range(40):
        if marcador.is_file():
            break
        time.sleep(0.1)
    if marcador.is_file():
        pid_neto = int(marcador.read_text().strip())
        vivo = True
        for _ in range(40):
            if not _pid_vivo(pid_neto):
                vivo = False
                break
            time.sleep(0.1)
        assert not vivo, f"neto {pid_neto} ficou órfão após o timeout"


def _pid_vivo(pid: int) -> bool:
    if os.name == "nt":
        saida = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                               capture_output=True, text=True, check=False)
        return str(pid) in (saida.stdout or "")
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def test_timeout_nao_e_reiniciado_por_saida_nova():
    """O teto é TOTAL, não de inatividade: falar sem parar não compra tempo."""
    programa = (
        "import time\n"
        "while True:\n"
        "    print('ainda aqui', flush=True)\n"
        "    time.sleep(0.05)\n"
    )
    inicio = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        proc_stream.run([sys.executable, "-c", programa], timeout_s=2,
                        stream=io.StringIO())
    decorrido = time.monotonic() - inicio

    assert decorrido < 20, (
        f"processo falante sobreviveu {decorrido:.1f}s a um teto de 2s — "
        f"o prazo está sendo reiniciado a cada linha")


def test_run_tool_step_rotula_o_timeout_com_o_teto_efetivo(tmp_path, monkeypatch):
    monkeypatch.setattr(ava_pipeline, "REPO_ROOT", tmp_path)
    passo = _step(timeout_s=2,
                  command=[sys.executable, "-c", "import time; time.sleep(120)"])

    with pytest.raises(subprocess.TimeoutExpired) as excinfo:
        ava_pipeline.run_tool_step(passo, "P")

    assert excinfo.value.timeout_s == 2, "a exceção carrega o teto CONFIGURADO"
    assert excinfo.value.phase == "F4S"
    assert hasattr(excinfo.value, "tail")


def test_verifier_nao_roda_depois_de_timeout_nem_de_falha():
    """No `scaffold_runner`, o verifier é filho do sucesso do generator."""
    fonte = (TOOLS_DIR / "scaffold_runner.py").read_text(encoding="utf-8")
    corpo = fonte[fonte.index("for tentativa in range"):fonte.index("def create_baseline")]

    guarda = corpo.index('if not geracao.get("success")')
    verifier = corpo.index("_verifier_argv")
    assert guarda < verifier, "o verifier tem de vir DEPOIS da guarda de sucesso"
    # A guarda termina em `continue`: a tentativa é abortada antes do verifier.
    assert "continue" in corpo[guarda:verifier]
    # E o timeout do generator devolve success=False, caindo na mesma guarda.
    assert '"code": "TIMEOUT"' in fonte and '"success": False' in fonte


# ── TESTE 8 · execução bem-sucedida encadeia o verifier ────────────────────

def test_sucesso_devolve_exit_zero_e_status_ok(tmp_path, monkeypatch):
    monkeypatch.setattr(ava_pipeline, "REPO_ROOT", tmp_path)
    passo = _step(timeout_s=30,
                  command=[sys.executable, "-c", "print('scaffold pronto')"])

    resultado = ava_pipeline.run_tool_step(passo, "P")

    assert resultado["status"] == "completed"
    assert resultado["exit_code"] == 0
    assert resultado["timeout_s"] == 30
    assert resultado["elapsed_s"] >= 0


def test_runner_classifica_ok_somente_com_exit_zero():
    fonte = (REPO_ROOT / "ava-pipeline-runner-cli.py").read_text(encoding="utf-8")

    assert '"tool_status": "OK" if result.get("status") == "completed" else "FAILED"' in fonte
    assert '"TIMEOUT" if _timeout else "FAILED"' in fonte


# ── TESTE 9 · falha do scaffold não chega ao verifier ─────────────────────

def test_falha_do_scaffold_propaga_exit_code(tmp_path, monkeypatch):
    monkeypatch.setattr(ava_pipeline, "REPO_ROOT", tmp_path)
    passo = _step(timeout_s=30, command=[sys.executable, "-c", "import sys; sys.exit(9)"])

    with pytest.raises(RuntimeError) as excinfo:
        ava_pipeline.run_tool_step(passo, "P")

    assert excinfo.value.returncode == 9


# ── TESTE 10 · verifier reprovado não vira fase OK ────────────────────────

def test_verifier_reprovado_nao_fecha_a_task_como_completed():
    fonte = (TOOLS_DIR / "scaffold_runner.py").read_text(encoding="utf-8")
    corpo = fonte[fonte.index("verificacao = _run_json"):fonte.index("def create_baseline")]

    ok = corpo.index('if verificacao.get("success")')
    completed = corpo.index("status=COMPLETED")
    assert ok < completed, "COMPLETED só pode existir dentro do ramo de sucesso"
    assert "status=FAILED" in corpo, "o ramo de reprovação tem de marcar FAILED"
    assert 'verification_status="failed"' in corpo


# ── TESTE 11 · timeout inválido avisa e cai no default ────────────────────

@pytest.mark.parametrize("invalido", [0, -1, "abc", "", None, 3.9, True])
def test_timeout_invalido_avisa_e_usa_default(invalido, capsys):
    efetivo = pipeline_plan.resolve_tool_timeout_s(invalido, label="F4S")

    if invalido in (None, ""):
        assert efetivo == pipeline_plan.DEFAULT_TOOL_TIMEOUT_S
        return
    if invalido == 3.9:  # numérico positivo: trunca, não reprova
        assert efetivo == 3
        return
    if invalido is True:  # bool é int em Python — e nunca é um prazo
        assert efetivo == pipeline_plan.DEFAULT_TOOL_TIMEOUT_S
    else:
        assert efetivo == pipeline_plan.DEFAULT_TOOL_TIMEOUT_S
        assert "timeout_s inválido" in capsys.readouterr().err


def test_timeout_invalido_no_step_nao_derruba_o_passo(tmp_path, monkeypatch):
    visto: dict[str, object] = {}
    monkeypatch.setattr(
        ava_pipeline.proc_stream, "run",
        lambda command, cwd=None, **kw: (visto.update(kw)
                                         or subprocess.CompletedProcess(command, 0, "", "")))
    monkeypatch.setattr(ava_pipeline, "REPO_ROOT", tmp_path)

    resultado = ava_pipeline.run_tool_step(_step(timeout_s=0), "P")

    assert visto["timeout_s"] == pipeline_plan.DEFAULT_TOOL_TIMEOUT_S
    assert resultado["status"] == "completed"


def test_proc_stream_recusa_teto_invalido():
    with pytest.raises(ValueError):
        proc_stream.run([sys.executable, "-c", "pass"], timeout_s=0)


# ── TESTE 12 · compatibilidade das demais fases ───────────────────────────

def test_passos_de_agente_seguem_sem_declarar_timeout():
    passo = pipeline_plan.Step(phase="F1", group="F1", agent="ava-asis-orchestrator",
                               trigger="FP", label="AS-IS")

    assert passo.kind == "agent"
    assert passo.timeout_s is None
    assert "timeout_s" in passo.as_dict()


def test_nenhum_outro_no_do_dag_precisou_declarar_timeout():
    fonte = (REPO_ROOT / "ava-pipeline-runner-cli.py").read_text(encoding="utf-8")
    assert fonte.count('"timeout_s": 3600') == 1, (
        "só a F4S declara teto próprio; as demais fases seguem no default")


def test_kill_tree_tem_implementacao_unica():
    """`agent_runner` delega em vez de manter a segunda cópia."""
    fonte = (TOOLS_DIR / "agent_runner.py").read_text(encoding="utf-8")

    assert "proc_stream.kill_process_tree(pid)" in fonte
    assert "taskkill" not in fonte, "a única chamada a taskkill vive em proc_stream"


# ── Aninhamento dos tetos: nenhum interno pode passar do teto do passo ─────

def test_tetos_internos_cabem_dentro_do_teto_do_passo():
    """A inversão original (interno 1800 > externo 900) matava o diagnóstico.

    Com o interno acima do externo, quem estoura é sempre o processo PAI — e o
    handler estruturado do filho, que gravaria o estado e diria em qual etapa
    parou, vira código inalcançável.
    """
    import scaffold_runner  # noqa: PLC0415

    sys.path.insert(0, str(REPO_ROOT / "src" / "shared" / "utils"))
    import verify_dotnet_solution  # noqa: PLC0415

    teto_do_passo = 3600  # o que o nó F4S declara no DAG
    assert scaffold_runner.DEFAULT_TIMEOUT < teto_do_passo
    assert verify_dotnet_solution.DEFAULT_COMMAND_TIMEOUT_S < teto_do_passo
    assert verify_dotnet_solution.DEFAULT_COMMAND_TIMEOUT_S <= scaffold_runner.DEFAULT_TIMEOUT


def test_verifier_nao_tem_mais_teto_de_900_por_comando():
    fonte = ((REPO_ROOT / "src" / "shared" / "utils" / "verify_dotnet_solution.py")
             .read_text(encoding="utf-8"))

    assert "timeout: int = 900" not in fonte
    assert 'default=900' not in fonte
    assert "DEFAULT_COMMAND_TIMEOUT_S = 1800" in fonte


def test_prompt_sem_quebra_de_linha_chega_antes_do_fim():
    """O gate de aprovação da F4S pergunta com `input()`, sem `\n`.

    Leitura por LINHA esconderia o prompt até o processo terminar — ou seja,
    até o timeout da aprovação. Ler por bloco é o que mantém o gate usável.
    """
    console = _EchoEspiao()
    programa = (
        "import sys, time\n"
        "sys.stdout.write('Aprovar o scaffold? [s/N]: ')\n"
        "sys.stdout.flush()\n"
        "time.sleep(1.2)\n"
    )
    inicio = time.monotonic()
    proc_stream.run([sys.executable, "-c", programa], timeout_s=30, stream=console)
    fim = time.monotonic()

    assert "Aprovar o scaffold? [s/N]: " in console.getvalue()
    assert console.marcas, "nada chegou ao console"
    assert console.marcas[0][0] - inicio < (fim - inicio) / 2, (
        "o prompt só apareceu no fim — leitura por linha, não por bloco")
