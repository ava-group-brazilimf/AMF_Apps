"""Testes do harness de verificação Angular (spec 042).

As fases de rede (`npm install`/`npm ci`) e de compilação (`ng build`) são mockadas:
o objetivo aqui é a máquina de estados — escolha do comando de install, resolução do
dist, exit code por fase e shutdown do servidor. A prova de que uma árvore real
compila é o Quality Gate da spec, não um teste unitário.
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "shared" / "utils"))

import verify_angular_app as verifier  # noqa: E402


INDEX_HTML = "<!doctype html><html><body><app-root></app-root></body></html>"


def _make_app(root: Path, *, with_lockfile: bool = False) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "package.json").write_text('{"name":"x"}', encoding="utf-8")
    (root / "angular.json").write_text('{"version":1}', encoding="utf-8")
    if with_lockfile:
        (root / "package-lock.json").write_text('{"lockfileVersion":3}', encoding="utf-8")
    return root


def _fake_run(returncode: int = 0, stdout: str = "", stderr: str = "",
              on_call=None):
    """Substitui subprocess.run registrando os comandos executados."""
    calls: list[list[str]] = []

    def runner(cmd, *args, **kwargs):
        calls.append(list(cmd))
        if on_call is not None:
            on_call(cmd, kwargs)
        return subprocess.CompletedProcess(cmd, returncode, stdout, stderr)

    runner.calls = calls  # type: ignore[attr-defined]
    return runner


# ─── resolução do app_root ──────────────────────────────────────────────────────


def test_app_root_na_raiz(tmp_path: Path):
    app = _make_app(tmp_path)
    assert verifier.resolve_app_root(tmp_path) == app


def test_app_root_aninhado_layout_legado(tmp_path: Path):
    """Árvores anteriores à spec 042 enterravam o app em frontend/<app>-spa/."""
    app = _make_app(tmp_path / "frontend" / "login-spa")
    assert verifier.resolve_app_root(tmp_path) == app


def test_app_root_ambiguo_reprova(tmp_path: Path):
    _make_app(tmp_path / "a")
    _make_app(tmp_path / "b")
    with pytest.raises(verifier.VerifyError) as exc:
        verifier.resolve_app_root(tmp_path)
    assert exc.value.code == verifier.EXIT_PREREQ
    assert "mais de um angular.json" in exc.value.message


def test_app_root_ignora_node_modules(tmp_path: Path):
    app = _make_app(tmp_path)
    ninho = tmp_path / "node_modules" / "pacote"
    ninho.mkdir(parents=True)
    (ninho / "angular.json").write_text("{}", encoding="utf-8")
    assert verifier.resolve_app_root(tmp_path) == app


# ─── escolha do comando de install (D4) ─────────────────────────────────────────


def test_install_usa_npm_install_sem_lockfile(tmp_path: Path):
    app = _make_app(tmp_path)
    assert verifier.choose_install_command(app)[:2] == ["npm", "install"]


def test_install_usa_npm_ci_com_lockfile(tmp_path: Path):
    app = _make_app(tmp_path, with_lockfile=True)
    assert verifier.choose_install_command(app)[:2] == ["npm", "ci"]


# ─── resolução do dist ──────────────────────────────────────────────────────────


def test_dist_layout_angular_17(tmp_path: Path):
    """Angular 17+ emite dist/<app>/browser/index.html."""
    browser = tmp_path / "dist" / "app" / "browser"
    browser.mkdir(parents=True)
    (browser / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    assert verifier.find_dist_dir(tmp_path) == browser


def test_dist_layout_legado(tmp_path: Path):
    legado = tmp_path / "dist" / "app"
    legado.mkdir(parents=True)
    (legado / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    assert verifier.find_dist_dir(tmp_path) == legado


def test_dist_ausente(tmp_path: Path):
    assert verifier.find_dist_dir(tmp_path) is None


# ─── servidor estático ──────────────────────────────────────────────────────────


def test_servidor_usa_porta_efemera_e_serve_o_dist(tmp_path: Path):
    """Bind na porta 0 elimina a classe de falha 'porta já em uso'."""
    (tmp_path / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    server, port, thread = verifier.start_static_server(tmp_path)
    try:
        assert port > 0
        assert thread.is_alive()
        url = verifier.phase_health(
            verifier.Logger(tmp_path / "log.txt", quiet=True),
            port, "/", "<app-root", timeout=10, server_thread=thread,
        )
        assert url.endswith(f":{port}/")
    finally:
        server.shutdown()
        server.server_close()


def test_health_reprova_quando_conteudo_esperado_falta(tmp_path: Path):
    (tmp_path / "index.html").write_text("<html><body>outro</body></html>",
                                         encoding="utf-8")
    server, port, thread = verifier.start_static_server(tmp_path)
    try:
        with pytest.raises(verifier.VerifyError) as exc:
            verifier.phase_health(
                verifier.Logger(tmp_path / "log.txt", quiet=True),
                port, "/", "<app-root", timeout=5, server_thread=thread,
            )
        assert exc.value.code == verifier.EXIT_HEALTH
        assert "conteúdo esperado" in exc.value.message
    finally:
        server.shutdown()
        server.server_close()


def test_thread_morta_reporta_falha_de_boot(tmp_path: Path):
    """Não se espera o timeout inteiro por algo que nunca vai responder."""
    morta = threading.Thread(target=lambda: None)
    morta.start()
    morta.join()

    with pytest.raises(verifier.VerifyError) as exc:
        verifier.phase_health(
            verifier.Logger(tmp_path / "log.txt", quiet=True),
            1, "/", "<app-root", timeout=30, server_thread=morta,
        )
    assert exc.value.code == verifier.EXIT_BOOT


# ─── fases isoladas ─────────────────────────────────────────────────────────────


def test_prereq_reprova_sem_package_json(tmp_path: Path):
    (tmp_path / "angular.json").write_text("{}", encoding="utf-8")
    with pytest.raises(verifier.VerifyError) as exc:
        verifier.phase_prereq(verifier.Logger(tmp_path / "log.txt", quiet=True),
                              tmp_path)
    assert exc.value.code == verifier.EXIT_PREREQ


def test_install_falhando_devolve_exit_20(tmp_path: Path, monkeypatch):
    app = _make_app(tmp_path)
    monkeypatch.setattr(subprocess, "run", _fake_run(1, stderr="ERR_PNPM"))
    with pytest.raises(verifier.VerifyError) as exc:
        verifier.phase_install(verifier.Logger(tmp_path / "log.txt", quiet=True),
                               app, timeout=5)
    assert exc.value.code == verifier.EXIT_INSTALL


def test_build_falhando_devolve_exit_30(tmp_path: Path, monkeypatch):
    app = _make_app(tmp_path)
    monkeypatch.setattr(subprocess, "run", _fake_run(1, stdout="NG8004"))
    with pytest.raises(verifier.VerifyError) as exc:
        verifier.phase_build(verifier.Logger(tmp_path / "log.txt", quiet=True),
                             app, timeout=5)
    assert exc.value.code == verifier.EXIT_BUILD
    assert "NG8004" in exc.value.message


def test_build_sem_dist_devolve_exit_30(tmp_path: Path, monkeypatch):
    """Build que retorna 0 mas não emite index.html continua sendo falha de build."""
    app = _make_app(tmp_path)
    monkeypatch.setattr(subprocess, "run", _fake_run(0))
    with pytest.raises(verifier.VerifyError) as exc:
        verifier.phase_build(verifier.Logger(tmp_path / "log.txt", quiet=True),
                             app, timeout=5)
    assert exc.value.code == verifier.EXIT_BUILD
    assert "index.html não encontrado" in exc.value.message


# ─── orquestração ───────────────────────────────────────────────────────────────


def _mock_successful_build(tmp_path: Path, monkeypatch) -> Path:
    app = _make_app(tmp_path)
    browser = app / "dist" / "app" / "browser"

    def on_call(cmd, kwargs):
        if "build" in cmd:
            browser.mkdir(parents=True, exist_ok=True)
            (browser / "index.html").write_text(INDEX_HTML, encoding="utf-8")

    monkeypatch.setattr(subprocess, "run", _fake_run(0, on_call=on_call))
    return app


def test_verify_completo_passa(tmp_path: Path, monkeypatch):
    app = _mock_successful_build(tmp_path, monkeypatch)
    result = verifier.verify(app, timeout=10, quiet=True)

    assert result["status"] == "PASS"
    assert [p["name"] for p in result["phases"]] == [
        "prereq", "install", "build", "boot", "health",
    ]
    assert all(p["status"] == "PASS" for p in result["phases"])
    assert Path(result["log_path"]).is_file()


def test_skip_serve_pula_boot_e_health(tmp_path: Path, monkeypatch):
    app = _mock_successful_build(tmp_path, monkeypatch)
    result = verifier.verify(app, skip_serve=True, quiet=True)

    assert result["status"] == "PASS"
    fases = {p["name"]: p["status"] for p in result["phases"]}
    assert fases["build"] == "PASS"
    assert fases["boot"] == "SKIPPED"
    assert fases["health"] == "SKIPPED"


def test_verify_propaga_exit_code_da_fase(tmp_path: Path, monkeypatch):
    _make_app(tmp_path)
    monkeypatch.setattr(subprocess, "run", _fake_run(1, stderr="boom"))
    result = verifier.verify(tmp_path, quiet=True)

    assert result["status"] == "FAIL"
    assert result["exit_code"] == verifier.EXIT_INSTALL
    assert result["phases"][-1]["status"] == "FAIL"


def test_verify_nao_deixa_servidor_ativo(tmp_path: Path, monkeypatch):
    """O shutdown no `finally` substitui o `trap` do script original."""
    app = _mock_successful_build(tmp_path, monkeypatch)
    antes = threading.active_count()
    verifier.verify(app, timeout=10, quiet=True)

    # A thread do servidor é daemon e encerra no shutdown; nada deve sobrar ativo.
    for _ in range(50):
        if threading.active_count() <= antes:
            break
        threading.Event().wait(0.1)
    assert threading.active_count() <= antes


# ─── CLI ────────────────────────────────────────────────────────────────────────


def test_cli_json_em_sucesso(tmp_path: Path, monkeypatch, capsys):
    app = _mock_successful_build(tmp_path, monkeypatch)
    code = verifier.main(["--root", str(app), "--json", "--timeout", "10"])
    payload = json.loads(capsys.readouterr().out)
    assert code == verifier.EXIT_PASS
    assert payload["status"] == "PASS"


def test_cli_exit_60_em_diretorio_inexistente(tmp_path: Path, capsys):
    code = verifier.main(["--root", str(tmp_path / "nao-existe"), "--json"])
    assert code == verifier.EXIT_USAGE


def test_cli_propaga_exit_code_da_fase(tmp_path: Path, monkeypatch, capsys):
    _make_app(tmp_path)
    monkeypatch.setattr(subprocess, "run", _fake_run(1, stderr="boom"))
    code = verifier.main(["--root", str(tmp_path), "--json"])
    assert code == verifier.EXIT_INSTALL
