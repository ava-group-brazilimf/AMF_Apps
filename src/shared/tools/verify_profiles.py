#!/usr/bin/env python3
"""Resolve o comando de verificação de uma task a partir de um PERFIL canônico.

O defeito que este módulo corrige
---------------------------------
`verify_command` do `plan-graph.json` é prosa escrita por LLM. Medido em
`cadastro-funcionario-03`: a task trazia
`ng build --configuration=production --project=cadastro-funcionario-app`.
`ng` não existe no PATH — é `node_modules/.bin/ng.cmd`, e o `npm install` ainda
não tinha rodado. Resultado: `FileNotFoundError` → exit 127 em três tentativas,
seis remediações de LLM e 251s gastos num erro que **nenhum agente conserta
escrevendo código**, porque não é defeito de código.

`f4s_build_runner.resolve_command` já resolve isso na F4S, fazendo o verificador
determinístico da stack vencer o override da task. Mas ali é tarde: o dado ruim
já viajou pela F3S inteira, entrou em `traceability.json` (que é imutável) e
ficou registrado como se fosse contrato. Este módulo ataca a ORIGEM — a F3S
passa a planejar um `verify_profile`, e o comando concreto é derivado da stack.

A precedência é a mesma dos harnesses, e por escrito
----------------------------------------------------
1. Verificador determinístico da stack (`f4s_build_runner.STACK_VERIFIERS`);
2. Script declarado no manifesto do projeto (`package.json` scripts);
3. Comando padrão da stack (`f4s_build_runner.DEFAULT_COMMANDS`);
4. Só então o texto da LLM — e ainda assim normalizado, nunca aceito cru.

Nada aqui executa comando: a F3S planeja, a F4/F4S executa.
"""
from __future__ import annotations

import json
import re
import shlex
import sys
from pathlib import Path
from typing import Any, Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import f4s_build_runner  # noqa: E402
from scaffold_paths import STACK_COMPONENT_TYPES  # noqa: E402

#: Perfis canônicos. Nomes fixos: são contrato de schema, e renomear um perfil
#: invalida planos já gravados.
PROFILES: tuple[str, ...] = (
    "frontend-build",
    "frontend-unit-test",
    "frontend-lint",
    "backend-build",
    "backend-unit-test",
    "backend-lint",
    "integration-test",
    "e2e-test",
    "accessibility-test",
    "visual-regression-test",
    "lint",
    "none",
)

#: Perfil default por `task_type`/`work_kind`, usado quando o plano omite.
#: `none` é legítimo: uma task de documentação de contrato não constrói nada, e
#: forçar um build aí produz o falso vermelho que a política de erro do F3S.yaml
#: manda evitar.
DEFAULT_PROFILE_BY_WORK_KIND: dict[str, str] = {
    "design_system": "frontend-build",
    "frontend_layout": "frontend-build",
    "frontend_component": "frontend-unit-test",
    "frontend_page": "frontend-build",
    "frontend_route": "frontend-build",
    "frontend_form": "frontend-unit-test",
    "frontend_validation": "frontend-unit-test",
    "frontend_api_client": "frontend-unit-test",
    "frontend_state": "frontend-unit-test",
    "frontend_integration": "integration-test",
    "backend_api_contract": "backend-build",
    "backend_api_implementation": "backend-unit-test",
    "backend_domain": "backend-unit-test",
    "backend_persistence": "backend-unit-test",
    "integration_test": "integration-test",
    "visual_regression_test": "visual-regression-test",
    "accessibility_test": "accessibility-test",
    "end_to_end_test": "e2e-test",
    "scaffold": "frontend-build",
}

_FRONTEND_PROFILES = frozenset({
    "frontend-build", "frontend-unit-test", "frontend-lint",
    "e2e-test", "accessibility-test", "visual-regression-test",
})

#: Frameworks node cujo runner é o package manager do projeto.
_NODE_STACKS = frozenset({"angular", "react", "vue", "nestjs", "node", "svelte"})

#: Scripts do package.json procurados por perfil, em ordem de preferência.
_NPM_SCRIPTS: dict[str, tuple[str, ...]] = {
    "frontend-build": ("build",),
    "frontend-unit-test": ("test:ci", "test:unit", "test"),
    "frontend-lint": ("lint",),
    "lint": ("lint",),
    "e2e-test": ("e2e", "test:e2e", "cypress:run", "playwright"),
    "accessibility-test": ("test:a11y", "a11y", "axe"),
    "visual-regression-test": ("test:visual", "visual", "percy", "chromatic"),
    "integration-test": ("test:integration", "test:int"),
}

#: Comando por perfil e stack quando NÃO há verificador nem script declarado.
#: Tudo aqui é a toolchain oficial da stack; nada é inventado por task.
_STACK_PROFILE_COMMANDS: dict[str, dict[str, list[str]]] = {
    "dotnet": {
        "backend-build": ["dotnet", "build"],
        "backend-unit-test": ["dotnet", "test"],
        "integration-test": ["dotnet", "test", "--filter", "Category=Integration"],
        "backend-lint": ["dotnet", "format", "--verify-no-changes"],
    },
    "spring-boot": {
        "backend-build": ["mvn", "-B", "compile"],
        "backend-unit-test": ["mvn", "-B", "test"],
        "integration-test": ["mvn", "-B", "verify", "-DskipUnitTests"],
        "backend-lint": ["mvn", "-B", "checkstyle:check"],
    },
    "fastapi": {
        "backend-build": ["python", "-m", "compileall", "-q", "."],
        "backend-unit-test": ["python", "-m", "pytest", "-q"],
        "integration-test": ["python", "-m", "pytest", "-q", "-m", "integration"],
        "backend-lint": ["python", "-m", "ruff", "check", "."],
    },
    "gin": {
        "backend-build": ["go", "build", "./..."],
        "backend-unit-test": ["go", "test", "./..."],
        "integration-test": ["go", "test", "-tags=integration", "./..."],
        "backend-lint": ["go", "vet", "./..."],
    },
}

#: Aliases de linguagem ↔ framework, alinhados com `f4s_build_runner`.
_STACK_ALIASES = {
    "java": "spring-boot", "python": "fastapi", "go": "gin",
    "csharp": "dotnet", "blazor": "dotnet", "typescript": "node",
}


def _verifier_rel(verifier: Path) -> str:
    """Caminho do verificador relativo ao repo de ferramentas, com fallback."""
    try:
        return verifier.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return verifier.as_posix()


class VerifyProfileError(ValueError):
    """Perfil desconhecido ou stack sem forma de verificar o perfil pedido."""


def normalize_stack(stack: str) -> str:
    lowered = str(stack or "").strip().lower()
    return _STACK_ALIASES.get(lowered, lowered)


def is_frontend_profile(profile: str) -> bool:
    return profile in _FRONTEND_PROFILES


def default_profile(work_kind: str = "", task_type: str = "") -> str:
    """Perfil que a task deveria ter, quando o plano não declarou nenhum."""
    if work_kind and work_kind in DEFAULT_PROFILE_BY_WORK_KIND:
        return DEFAULT_PROFILE_BY_WORK_KIND[work_kind]
    kind = str(task_type or "").strip().lower()
    if kind == "frontend":
        return "frontend-build"
    if kind == "backend":
        return "backend-build"
    return "none"


def _package_manager(project_root: Path, declared: str = "") -> str:
    """Package manager REAL do projeto — lockfile vence a declaração.

    O `npm` do `project-config.yaml` não ajuda se o repositório tem
    `pnpm-lock.yaml`: quem resolve `node_modules/.bin` é o manager do lockfile.
    """
    for lockfile, manager in (("pnpm-lock.yaml", "pnpm"),
                              ("yarn.lock", "yarn"),
                              ("bun.lockb", "bun"),
                              ("package-lock.json", "npm")):
        if (project_root / lockfile).is_file():
            return manager
    declared = str(declared or "").strip().lower()
    return declared if declared in {"npm", "pnpm", "yarn", "bun"} else "npm"


def _npm_scripts(project_root: Path) -> dict[str, str]:
    path = project_root / "package.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    scripts = data.get("scripts")
    return {str(k): str(v) for k, v in scripts.items()} if isinstance(scripts, dict) else {}


def resolve(profile: str, *, stack: str, project_dir: Path | None = None,
            config: dict[str, Any] | None = None,
            frontend_root: Path | None = None,
            repo_root: Path | None = None) -> dict[str, Any]:
    """Comando concreto de um perfil, com a proveniência da decisão.

    Devolve `{profile, command, resolved_from, warnings, executable}`. Nunca
    executa nada; `command` é uma lista, para que o chamador não precise passar
    por shell — evitar o shell é o que impede que `&&` vire injeção.
    """
    profile = str(profile or "").strip().lower()
    if profile not in PROFILES:
        raise VerifyProfileError(
            f"verify_profile desconhecido: {profile!r} (aceitos: {', '.join(PROFILES)})")
    if profile == "none":
        return {"profile": profile, "command": [], "resolved_from": "profile-none",
                "warnings": [], "executable": ""}

    normalized = normalize_stack(stack)
    if not normalized:
        raise VerifyProfileError(
            "target_stack vazio — impossível resolver comando de verificação")
    warnings: list[str] = []

    # 1. Verificador determinístico da stack. Cobre install → build → boot →
    #    health (Angular) e structure → restore → build → test (.NET); é a
    #    autoridade sobre "compila e roda", então vence qualquer alternativa.
    verifier = f4s_build_runner.STACK_VERIFIERS.get(normalized)
    if verifier is not None and profile in {"frontend-build", "backend-build"}:
        if not verifier.is_file():
            raise VerifyProfileError(
                f"verificador da stack {normalized!r} ausente: {verifier}")
        return {
            "profile": profile,
            # `{python}` e não `sys.executable`: o comando vai para um ARTEFATO
            # de plano, e um caminho absoluto de interpretador tornaria o
            # `graph_checksum` dependente da máquina que rodou a F3S — o
            # cenário 10 (mesma entrada, dois runs) falharia por isso. O runner
            # já substitui `{python}` no despacho, como no F3S.yaml.
            # Relativo ao REPO DE FERRAMENTAS, sempre. `STACK_VERIFIERS` aponta
            # para scripts deste repositório, não para dentro do workspace do
            # projeto — usar `root` aqui estourava `ValueError` sempre que o
            # chamador passava outra raiz (é o caso de todo teste com tmp_path).
            "command": ["{python}", _verifier_rel(verifier),
                        "--root", ".", "--json"],
            "resolved_from": "stack-verifier",
            "warnings": warnings,
            "executable": "{python}",
        }

    # 2. Script declarado no manifesto do projeto.
    if normalized in _NODE_STACKS:
        app_root = frontend_root or project_dir or (repo_root or REPO_ROOT)
        manager = _package_manager(app_root,
                                   (config or {}).get("package_manager", ""))
        scripts = _npm_scripts(app_root)
        for candidate in _NPM_SCRIPTS.get(profile, ()):
            if candidate in scripts:
                run = ["run", candidate] if manager != "npm" else ["run", candidate]
                return {
                    "profile": profile,
                    "command": [manager, *run],
                    "resolved_from": "package-json-script",
                    "warnings": warnings,
                    "executable": manager,
                }
        fallback = _NPM_SCRIPTS.get(profile, ("build",))[0]
        warnings.append(
            f"package.json sem script para o perfil {profile!r}; planejado "
            f"{manager} run {fallback} — a F4 precisa criar esse script no scaffold")
        return {
            "profile": profile,
            "command": [manager, "run", fallback],
            "resolved_from": "package-manager-default",
            "warnings": warnings,
            "executable": manager,
        }

    # 3. Comando padrão da stack.
    by_profile = _STACK_PROFILE_COMMANDS.get(normalized, {})
    if profile in by_profile:
        command = list(by_profile[profile])
        return {"profile": profile, "command": command,
                "resolved_from": "stack-default", "warnings": warnings,
                "executable": command[0]}

    default = f4s_build_runner.DEFAULT_COMMANDS.get(normalized)
    if default:
        warnings.append(
            f"stack {normalized!r} não declara comando para o perfil {profile!r}; "
            f"usando o build padrão da stack")
        return {"profile": profile, "command": list(default),
                "resolved_from": "stack-build-fallback", "warnings": warnings,
                "executable": default[0]}

    raise VerifyProfileError(
        f"stack {normalized!r} não tem como satisfazer o perfil {profile!r} — "
        f"declare o comando em f4s_build_runner.DEFAULT_COMMANDS ou use profile 'none'")


# ─── Normalização do que a LLM escreveu ──────────────────────────────────────

#: Assinaturas que identificam o perfil a partir de um comando em prosa. A
#: ordem é do mais específico ao mais genérico.
_COMMAND_SIGNATURES: tuple[tuple[str, str], ...] = (
    # `\be2e` sem fronteira à direita: o alvo real é `CadastroFuncionarios.E2ETests`,
    # e exigir `\be2e\b` fazia essa task cair no ramo de build e perder o perfil.
    (r"\b(cypress|playwright)\b|\be2e", "e2e-test"),
    (r"\b(axe|pa11y|lighthouse)\b|a11y|accessibility", "accessibility-test"),
    (r"\b(percy|chromatic|backstop)\b|visual[- ]regression", "visual-regression-test"),
    (r"integration", "integration-test"),
    (r"\b(eslint|stylelint|prettier|ruff|checkstyle|dotnet\s+format)\b|\blint\b", "lint"),
    (r"\bng\s+test\b|\bjest\b|\bvitest\b|\bkarma\b|npm\s+(run\s+)?test", "frontend-unit-test"),
    (r"\bdotnet\s+test\b|\bmvn\b.*\btest\b|\bpytest\b|\bgo\s+test\b", "backend-unit-test"),
    (r"\bng\s+build\b|\bvite\s+build\b|npm\s+run\s+build|\bnext\s+build\b", "frontend-build"),
    (r"\bdotnet\s+build\b|\bmvn\b|\bgradle\b|\bgo\s+build\b", "backend-build"),
)


def infer_profile(verify_command: str, *, task_type: str = "",
                  work_kind: str = "") -> tuple[str, str]:
    """Perfil implícito num `verify_command` em prosa, e por quê.

    Serve à migração: planos legados só têm `verify_command`, e descartá-los
    perderia a intenção real ("isto é um teste e2e", "isto é um build de
    backend"). Inferir o PERFIL e reresolver o COMANDO preserva a intenção e
    joga fora só a parte que não sobrevive ao PATH.
    """
    text = str(verify_command or "").strip().lower()
    if not text:
        return default_profile(work_kind, task_type), "sem verify_command"
    for pattern, profile in _COMMAND_SIGNATURES:
        if re.search(pattern, text):
            return profile, f"assinatura {pattern!r} reconhecida no comando"
    return default_profile(work_kind, task_type), "comando não reconhecido"


def normalize(verify_command: str, *, stack: str, task_type: str = "",
              work_kind: str = "", verify_profile: str = "",
              project_dir: Path | None = None,
              config: dict[str, Any] | None = None,
              frontend_root: Path | None = None,
              repo_root: Path | None = None) -> dict[str, Any]:
    """Perfil + comando canônicos de uma task, e o que foi descartado.

    NUNCA levanta por comando ruim: um `verify_command` incompatível é defeito
    de dado recuperável, e a política do F3S.yaml diz que defeito recuperável
    vira aviso estruturado, não morte da fase.
    """
    warnings: list[str] = []
    profile = str(verify_profile or "").strip().lower()
    origin = "declared"
    if profile and profile not in PROFILES:
        warnings.append(
            f"verify_profile inválido {profile!r} — inferido a partir do comando")
        profile = ""
    if not profile:
        profile, reason = infer_profile(verify_command, task_type=task_type,
                                        work_kind=work_kind)
        origin = f"inferred ({reason})"

    # Um perfil de família errada é pior que nenhum: `dotnet build` numa task
    # Angular inferia `backend-build` e resolvia o verificador .NET — trocaria
    # um comando errado por outro comando errado. `STACK_COMPONENT_TYPES` é a
    # autoridade canônica sobre a família da stack; não há segundo mapa aqui.
    family = STACK_COMPONENT_TYPES.get(normalize_stack(stack)) or \
        STACK_COMPONENT_TYPES.get(str(stack or "").strip().lower())
    corrected = _coerce_family(profile, family)
    if corrected != profile:
        warnings.append(
            f"perfil {profile!r} não pertence à stack {stack!r} ({family}); "
            f"corrigido para {corrected!r}")
        profile = corrected
        origin = f"{origin} + coerced-to-{family}"

    try:
        resolved = resolve(profile, stack=stack, project_dir=project_dir,
                           config=config, frontend_root=frontend_root,
                           repo_root=repo_root)
    except VerifyProfileError as exc:
        warnings.append(f"{exc} — verify_profile degradado para 'none'")
        return {
            "verify_profile": "none", "verify_command": "",
            "command": [], "resolved_from": "unresolvable",
            "profile_origin": origin, "original_command": str(verify_command or ""),
            "compatible": False, "warnings": warnings,
        }

    warnings.extend(resolved["warnings"])
    command = " ".join(shlex.quote(part) if " " in part else part
                       for part in resolved["command"])
    original = str(verify_command or "").strip()
    compatible = _looks_compatible(original, resolved["command"], stack)
    if original and not compatible:
        warnings.append(
            f"verify_command da task era {original!r} e não é compatível com a "
            f"stack {stack!r}; substituído pelo perfil {profile!r} "
            f"({resolved['resolved_from']})")
    return {
        "verify_profile": profile,
        "verify_command": command,
        "command": resolved["command"],
        "resolved_from": resolved["resolved_from"],
        "profile_origin": origin,
        "original_command": original,
        "compatible": compatible,
        "warnings": warnings,
    }


#: Tradução de perfil entre famílias. Só perfis com par; `e2e-test`,
#: `integration-test`, `lint` e `none` são agnósticos e não são traduzidos.
_FAMILY_SWAP = {
    ("frontend-build", "backend"): "backend-build",
    ("frontend-unit-test", "backend"): "backend-unit-test",
    ("frontend-lint", "backend"): "backend-lint",
    ("backend-build", "frontend"): "frontend-build",
    ("backend-unit-test", "frontend"): "frontend-unit-test",
    ("backend-lint", "frontend"): "frontend-lint",
}


def _coerce_family(profile: str, family: str | None) -> str:
    if not family:
        return profile
    # `lint` genérico vira o lint DA FAMÍLIA. Sem isto, `dotnet format
    # --verify-no-changes` inferia `lint`, e `lint` não existe na tabela de
    # comandos do dotnet nem em DEFAULT_COMMANDS — o perfil degradava para
    # `none` e a task ficava literalmente sem verificação, que é pior que o
    # comando errado que ela tinha.
    if profile == "lint":
        return f"{family}-lint"
    return _FAMILY_SWAP.get((profile, family), profile)


def _looks_compatible(original: str, resolved_command: Iterable[str],
                      stack: str) -> bool:
    """Heurística conservadora de compatibilidade — só para o relatório.

    O comando resolvido vence de qualquer forma; isto existe para que o aviso
    diga a verdade sobre o que foi trocado, em vez de gritar em todo plano.
    """
    text = str(original or "").strip().lower()
    if not text:
        return True
    normalized = normalize_stack(stack)
    # Ferramenta de outra stack é incompatibilidade certa.
    foreign = {
        "dotnet": ("ng ", "npm ", "mvn ", "gradle", "pytest", "go build"),
        "angular": ("dotnet ", "mvn ", "gradle", "pytest", "go build"),
        "react": ("dotnet ", "mvn ", "gradle", "pytest", "go build", "ng "),
        "vue": ("dotnet ", "mvn ", "gradle", "pytest", "go build", "ng "),
        "spring-boot": ("dotnet ", "npm ", "ng ", "pytest", "go build"),
        "fastapi": ("dotnet ", "mvn ", "gradle", "ng "),
        "gin": ("dotnet ", "mvn ", "npm ", "ng "),
    }.get(normalized, ())
    if any(marker in text for marker in foreign):
        return False
    # Binário local de node invocado direto não resolve no PATH antes do install.
    if re.match(r"^(ng|vite|jest|vitest|cypress|playwright|tsc|eslint)\b", text):
        return False
    return True


def profile_catalog() -> list[dict[str, str]]:
    """Catálogo legível dos perfis. Consumido pelos prompts dos agentes."""
    descriptions = {
        "frontend-build": "compila o app frontend na stack configurada",
        "frontend-unit-test": "testes unitários de componente frontend",
        "frontend-lint": "lint do frontend",
        "backend-build": "compila a solução backend",
        "backend-unit-test": "testes unitários do backend",
        "backend-lint": "lint/format check do backend",
        "integration-test": "testes de integração entre camadas",
        "e2e-test": "teste end-to-end do fluxo funcional",
        "accessibility-test": "verificação de acessibilidade",
        "visual-regression-test": "comparação visual com o protótipo",
        "lint": "lint genérico do repositório",
        "none": "task sem verificação executável (contrato, documento)",
    }
    return [{"profile": name, "description": descriptions[name]} for name in PROFILES]


def _main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="verify_profiles.py")
    parser.add_argument("--profile", "-P")
    parser.add_argument("--stack", "-s")
    parser.add_argument("--project", "-p")
    parser.add_argument("--command", "-c", default="",
                        help="verify_command em prosa a normalizar")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.list:
        print(json.dumps(profile_catalog(), ensure_ascii=False, indent=2)
              if args.json else
              "\n".join(f"{item['profile']:24} {item['description']}"
                        for item in profile_catalog()))
        return 0
    if not args.stack:
        parser.error("--stack é obrigatório fora de --list")
    project_dir = (REPO_ROOT / "projects" / args.project) if args.project else None
    result = normalize(args.command, stack=args.stack,
                       verify_profile=args.profile or "", project_dir=project_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json
          else f"{result['verify_profile']}: {result['verify_command']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
