#!/usr/bin/env python3
"""
f4s_generation_log.py — Registro estruturado da geração F4S.

Mantém:
  - `GENERATION_LOG.md` dentro do repo de source-code (legível por humanos).
  - `f4s-state.json` com estado de execução e últimos commits.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOG_HEADER = """# F4S Generation Log

| Timestamp | Spec | Attempt | Build Command | Exit Code | Commit | Notes |
|-----------|------|---------|---------------|-----------|--------|-------|
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_log(repo_root: Path) -> None:
    """Cria GENERATION_LOG.md com o cabeçalho da tabela."""
    log_path = repo_root / "GENERATION_LOG.md"
    log_path.write_text(LOG_HEADER, encoding="utf-8")


def append_log(repo_root: Path, spec: str, attempt: int,
               build_command: str, exit_code: int,
               commit: str = "-", notes: str = "") -> None:
    """Adiciona uma linha ao GENERATION_LOG.md."""
    log_path = repo_root / "GENERATION_LOG.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if not log_path.exists():
        log_path.write_text(LOG_HEADER, encoding="utf-8")
    notes = notes.replace("|", "\\|")
    line = (
        f"| {_now_iso()} | {spec} | {attempt} | {build_command} | "
        f"{exit_code} | {commit or '-'} | {notes} |\n"
    )
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(line)


def load_state(repo_root: Path) -> dict[str, Any]:
    """Lê `f4s-state.json` ou devolve estado inicial."""
    state_path = repo_root / "f4s-state.json"
    if state_path.exists():
        try:
            return json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {
        "initialized": False,
        "specs": [],
        "last_commit": None,
        "final_build_exit_code": None,
    }


def save_state(repo_root: Path, state: dict[str, Any]) -> None:
    """Persiste `f4s-state.json` formatado."""
    state_path = repo_root / "f4s-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now_iso()
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False),
                          encoding="utf-8")


def record_spec(repo_root: Path, spec: str, attempt: int,
                build_result: dict[str, Any], commit: str = "-",
                notes: str = "") -> None:
    """Registra spec no log e no estado, garantindo atomicidade lógica."""
    append_log(repo_root, spec, attempt, build_result["command"],
               build_result["exit_code"], commit, notes)
    state = load_state(repo_root)
    state["specs"].append({
        "spec": spec,
        "attempt": attempt,
        "exit_code": build_result["exit_code"],
        "commit": commit or None,
        "timestamp": _now_iso(),
        "notes": notes,
    })
    state["last_commit"] = commit or state.get("last_commit")
    save_state(repo_root, state)
