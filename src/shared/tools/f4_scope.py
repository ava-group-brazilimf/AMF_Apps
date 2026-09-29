#!/usr/bin/env python3
"""
f4_scope.py — Política de caminhos por tipo de task e reconciliação de artefatos.

O defeito que este módulo fecha
-------------------------------
A F4 tinha **dois** destinos válidos, `source-code/frontend` e
`source-code/backend`, e nada mais. Medido em `cadastro-funcionario-03`:

* `T-W0-TF-001` — "Criar `infra/terraform/main.tf`" — vinha do SpecKit com
  `task_type: backend` e `target_files: ["infra/terraform/main.tf"]`. Como o
  prompt exigia escrita sob `source-code/backend/`, o agente escreveu
  `backend/infra/terraform/main.tf`: **o arquivo foi empurrado para o diretório
  errado só para satisfazer a regra**, e depois recusado no commit por estar
  "fora do canônico". Perdeu-se o artefato e a task.
* `T-W0-FE-001` — declarava `frontend/cadastro-funcionario-app/angular.json` e o
  agente escreveu `frontend/angular.json`. Caminho alternativo **válido**,
  tratado como ausência.

Aqui a pergunta muda de "está no diretório canônico?" para **"pertence ao escopo
desta task?"** — e a resposta considera o tipo da task, os alvos declarados, o
scaffold real e as convenções do projeto, nessa ordem.

Espaço de caminhos
------------------
Tudo neste módulo é relativo à raiz do repositório de código,
`projects/{p}/outputs/tobe/source-code/` — o mesmo espaço dos `target_files` do
SpecKit (`backend/global.json`, `infra/terraform/main.tf`) e da saída do
`git status` naquele repo.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable

#: Os três escopos de trabalho da F4. `frontend` e `backend` são os componentes
#: canônicos criados pela F4S; `infra` é o terceiro, que não existia e por isso
#: não tinha para onde ir.
KIND_FRONTEND = "frontend"
KIND_BACKEND = "backend"
KIND_INFRA = "infra"
TASK_KINDS: tuple[str, ...] = (KIND_FRONTEND, KIND_BACKEND, KIND_INFRA)

#: Raízes permitidas por tipo de task, dentro de `source-code/`.
ALLOWED_ROOTS: dict[str, tuple[str, ...]] = {
    KIND_FRONTEND: ("frontend",),
    KIND_BACKEND: ("backend",),
    KIND_INFRA: ("infra", "iac", "deploy", "terraform"),
}

#: Arquivos de repositório que qualquer task pode tocar quando os declara.
SHARED_ROOT_FILES: frozenset[str] = frozenset({
    ".gitignore", ".gitattributes", ".editorconfig", "README.md",
    "GENERATION_LOG.md",
})

#: Sinais de que a task é de infraestrutura mesmo quando o `task_type` do
#: SpecKit diz outra coisa. Ordem de força: alvo declarado > comando de
#: verificação > id/título.
_INFRA_PATH = re.compile(r"(^|/)(infra|iac|terraform|deploy)(/|$)", re.IGNORECASE)
_INFRA_SUFFIX = re.compile(r"\.(tf|tfvars|tfvars\.example|bicep)$", re.IGNORECASE)
_INFRA_COMMAND = re.compile(
    r"\b(terraform|tflint|tfsec|checkov|bicep|pulumi|az\s+deployment)\b", re.IGNORECASE)
_INFRA_ID = re.compile(r"-(TF|IAC|INFRA)-", re.IGNORECASE)

#: Sufixos que nunca entram em commit de task — build, cache e segredo.
_NEVER_COMMIT = re.compile(
    r"(^|/)(node_modules|bin|obj|dist|\.angular|__pycache__|\.venv|target|\.f4s)(/|$)"
    r"|\.(pfx|pem|key|p12)$"
    r"|(^|/)(\.env|appsettings\.Development\.json|terraform\.tfvars)$",
    re.IGNORECASE)


# ─── Classificação da task ───────────────────────────────────────────────────

@dataclass
class Classification:
    kind: str
    reason: str
    declared_type: str = ""
    overridden: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "reason": self.reason,
                "declared_task_type": self.declared_type,
                "overridden_by_evidence": self.overridden}


def declared_targets(task: dict[str, Any]) -> list[str]:
    alvos = list(task.get("target_files") or [])
    if not alvos and task.get("target_file"):
        alvos = [task["target_file"]]
    return [normalize(item) for item in alvos if str(item).strip()]


def _looks_infra(task: dict[str, Any]) -> tuple[bool, str]:
    alvos = declared_targets(task)
    if alvos and all(_INFRA_PATH.search(a) or _INFRA_SUFFIX.search(a) for a in alvos):
        return True, f"todos os target_files sao de infraestrutura ({alvos[0]})"
    comando = str(task.get("verify_command") or "")
    if _INFRA_COMMAND.search(comando):
        return True, f"verify_command e de infraestrutura ({comando.split()[0]})"
    if _INFRA_ID.search(str(task.get("task_id") or "")):
        return True, "task_id marca a task como infraestrutura"
    return False, ""


def classify(task: dict[str, Any]) -> Classification:
    """Tipo efetivo da task. Evidência vence o rótulo do SpecKit.

    `T-W0-TF-001` chegava com `task_type: backend` e alvo
    `infra/terraform/main.tf`. Obedecer ao rótulo era o que fazia o arquivo
    terminar em `backend/infra/terraform/` — dentro do canônico, no lugar errado.
    """
    declarado = str(task.get("task_type") or "").strip().lower()
    infra, motivo = _looks_infra(task)
    if infra:
        return Classification(
            kind=KIND_INFRA, reason=motivo, declared_type=declarado,
            overridden=declarado not in ("", KIND_INFRA))
    if declarado in (KIND_FRONTEND, KIND_BACKEND):
        return Classification(kind=declarado,
                              reason=f"task_type declarado: {declarado}",
                              declared_type=declarado)
    if declarado == KIND_INFRA:
        return Classification(kind=KIND_INFRA, reason="task_type declarado: infra",
                              declared_type=declarado)

    alvos = declared_targets(task)
    for kind in (KIND_FRONTEND, KIND_BACKEND):
        if alvos and all(a.split("/", 1)[0] == kind for a in alvos):
            return Classification(kind=kind,
                                  reason=f"target_files sob {kind}/",
                                  declared_type=declarado)
    stack = str(task.get("target_stack") or "").strip().lower()
    if stack in {"angular", "react", "vue", "blazor"}:
        return Classification(kind=KIND_FRONTEND,
                              reason=f"stack {stack} e de frontend",
                              declared_type=declarado)
    return Classification(kind=KIND_BACKEND,
                          reason="sem evidencia contraria; backend por defeito",
                          declared_type=declarado)


def is_blocking(kind: str) -> bool:
    """Infra não bloqueia a esteira: ela não é dependência de compilação.

    `terraform validate` falha por credencial ausente, provider indisponível ou
    backend remoto não configurado — nenhum deles diz nada sobre a qualidade do
    arquivo `.tf` gerado.
    """
    return kind != KIND_INFRA


# ─── Política de caminhos ────────────────────────────────────────────────────

def normalize(path: Any) -> str:
    """Caminho relativo a `source-code/`, sem prefixos de projeto nem `./`."""
    texto = str(path or "").replace("\\", "/").strip().strip('"')
    marcador = "outputs/tobe/source-code/"
    if marcador in texto:
        texto = texto.split(marcador, 1)[1]
    texto = re.sub(r"^\./", "", texto).lstrip("/")
    return texto


def allowed_prefixes(kind: str, task: dict[str, Any] | None = None) -> list[str]:
    """Raízes permitidas para a task, já incluindo os alvos que ela declara."""
    prefixos = list(ALLOWED_ROOTS.get(kind, (kind,)))
    for alvo in declared_targets(task or {}):
        raiz = alvo.split("/", 1)[0]
        if raiz and raiz not in prefixos and raiz not in SHARED_ROOT_FILES:
            prefixos.append(raiz)
    return prefixos


def is_allowed(path: Any, kind: str, task: dict[str, Any] | None = None) -> bool:
    """O arquivo pertence ao escopo desta task?"""
    rel = normalize(path)
    if not rel or _NEVER_COMMIT.search(rel):
        return False
    if rel in SHARED_ROOT_FILES:
        return True
    if rel in declared_targets(task or {}):
        return True
    raiz = rel.split("/", 1)[0]
    return raiz in allowed_prefixes(kind, task)


def _same_basename(a: str, b: str) -> bool:
    return a.rsplit("/", 1)[-1].lower() == b.rsplit("/", 1)[-1].lower()


# ─── Reconciliação ───────────────────────────────────────────────────────────

#: Classes de artefato exigidas pelo contrato de reconciliação.
EXPECTED_AND_FOUND = "expected_and_found"
EXPECTED_BUT_MISSING = "expected_but_missing"
ALTERNATIVE_PATH = "generated_in_alternative_valid_path"
OUTSIDE_SCOPE = "generated_outside_allowed_scope"
MODIFIED_EXISTING = "modified_existing_file"
UNEXPECTED_RELATED = "unexpected_but_related"
UNEXPECTED_UNRELATED = "unexpected_and_unrelated"


@dataclass
class Reconciliation:
    """O que a task realmente produziu, comparado ao que o DAG esperava."""

    kind: str
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    to_commit: list[str] = field(default_factory=list)
    excluded: list[dict[str, str]] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    alternative_paths: list[dict[str, str]] = field(default_factory=list)

    @property
    def has_output(self) -> bool:
        return bool(self.to_commit)

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "artifacts": list(self.artifacts),
            "to_commit": list(self.to_commit),
            "excludedFromCommit": list(self.excluded),
            "missingArtifacts": list(self.missing),
            "alternativeArtifactPaths": list(self.alternative_paths),
        }


def reconcile(task: dict[str, Any], *, changed: Iterable[str],
              agent_declared: Iterable[str] = (),
              existing_before: Iterable[str] = (),
              kind: str | None = None) -> Reconciliation:
    """Concilia alvo declarado × diff real do git × declaração do agente.

    Regras que este trecho existe para impor:

    * caminho real diferente do declarado **não** é ausência — é
      `generated_in_alternative_valid_path`, e o arquivo vai para o commit;
    * arquivo fora do escopo não é apagado nem ignorado em silêncio: fica em
      `excludedFromCommit` **com motivo**;
    * `infra/**` é escopo legítimo de task de infraestrutura.
    """
    tipo = kind or classify(task).kind
    alvos = declared_targets(task)
    mudados = [normalize(item) for item in changed if str(item).strip()]
    declarados_agente = [normalize(item) for item in agent_declared if str(item).strip()]
    antes = {normalize(item) for item in existing_before if str(item).strip()}

    resultado = Reconciliation(kind=tipo)
    vistos: set[str] = set()

    # 1. Todo arquivo realmente alterado é classificado.
    for rel in mudados:
        if rel in vistos:
            continue
        vistos.add(rel)
        permitido = is_allowed(rel, tipo, task)
        if rel in alvos:
            classe = MODIFIED_EXISTING if rel in antes else EXPECTED_AND_FOUND
        elif not permitido:
            classe = OUTSIDE_SCOPE
        elif any(_same_basename(rel, alvo) for alvo in alvos):
            classe = ALTERNATIVE_PATH
        elif rel in declarados_agente:
            classe = UNEXPECTED_RELATED
        elif rel in antes:
            classe = MODIFIED_EXISTING
        else:
            classe = UNEXPECTED_RELATED

        registro = {"path": rel, "classification": classe, "allowed": permitido}
        if classe == ALTERNATIVE_PATH:
            alvo = next((a for a in alvos if _same_basename(rel, a)), "")
            registro["declared_path"] = alvo
            resultado.alternative_paths.append({"declared": alvo, "actual": rel})
        resultado.artifacts.append(registro)

        if permitido:
            resultado.to_commit.append(rel)
        else:
            motivo = ("fora do escopo permitido para task de tipo "
                      f"{tipo} (raizes: {', '.join(allowed_prefixes(tipo, task))})")
            if rel.startswith(".f4s/") or rel == ".f4s":
                motivo = "estado interno do pipeline (snapshots, baseline)"
            elif _NEVER_COMMIT.search(rel):
                motivo = "artefato de build, cache ou material sensivel"
            resultado.excluded.append({"path": rel, "reason": motivo})

    # 2. Alvo declarado que não apareceu em lugar nenhum é ausência de verdade.
    for alvo in alvos:
        if alvo in vistos:
            continue
        if any(item.get("classification") == ALTERNATIVE_PATH
               and item.get("declared_path") == alvo for item in resultado.artifacts):
            continue
        resultado.missing.append(alvo)
        resultado.artifacts.append({"path": alvo,
                                    "classification": EXPECTED_BUT_MISSING,
                                    "allowed": True})
    return resultado
