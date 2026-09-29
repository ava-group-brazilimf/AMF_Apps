#!/usr/bin/env python3
"""Normaliza e valida a coerência interna dos artefatos de waves da fase F2.

Por que esta tool existe
------------------------
A F3S não expande quando o `wave-model.json` e os demais artefatos da F2
contam histórias diferentes. O caso medido (cadastro-funcionarios, 2026-08-26)
foi este:

    F3S sem manifesto de waves válido: wave-model.json waves[1] não declara
    bc_details para bounded_contexts='BC-02'

Todos os arquivos exigidos pelo gate de entrada EXISTIAM. O que faltava era
coerência: o agente gravou `bounded_contexts: ["BC-02"]` (forma legada, por ID
textual) sem o `bc_details[]` que dá nome àquele ID — e o
`speckit_wave_manifest` não tem como inventar o nome de um BC.

A correção durável não é preencher `bc_details`: é **eliminar a representação
dupla**. O template canônico (`templates/wave-model.template.json`) já manda
`bounded_contexts[]` ser uma lista de OBJETOS `{bc_id, bc_name, ...}`. Com uma
lista só, a classe inteira de defeitos "referência sem definição" deixa de ser
possível por construção — não há dois conjuntos para divergirem. `bc_details`
é um shim de compatibilidade lido em um único ponto do repo
(`speckit_wave_manifest._normalize_model_waves`); esta tool absorve seus campos
na lista canônica e o remove.

Regra de ouro: **não há segunda fonte de verdade**. As validações cruzadas
contra o `wave-plan.md` reusam as funções do próprio `speckit_wave_manifest`
(`_sections`, `_plan_contexts`, `_wave_id`) e o veredito final é o
`build_manifest()` real — o mesmo que a F3S chama. Se esta tool passa, a F3S
expande; se reprova, ela aponta o campo e o arquivo.

Uso
---
    python src/shared/tools/wave_model_consistency.py --project <projeto>
    python src/shared/tools/wave_model_consistency.py --project <projeto> --fix

Sem `--fix` nada é escrito: é diagnóstico. Com `--fix` as divergências
mecanicamente corrigíveis são reparadas no arquivo e as demais continuam
reprovando — corrigir sozinho o que exige julgamento seria inventar
arquitetura, não reconciliar artefatos.

`--warn` (exit 0) anda junto com o relatório persistido em
`outputs/tobe/migration/wave-model-consistency.json`, pela política de erro do
runner: erro não trava fase, mas achado que só vai para o console se perde.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(SCRIPT_DIR))

import speckit_wave_manifest as manifest  # noqa: E402

# Mesma guarda de UTF-8 do speckit_wave_manifest: sem ela uma mensagem
# acentuada estoura UnicodeEncodeError no console cp1252 do Windows e a tool
# morre por um detalhe de terminal, não por um defeito real.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

REPORT_VERSION = "1.0.0"

MODEL_REL = "outputs/tobe/migration/wave-model.json"
PLAN_REL = "outputs/tobe/docs/wave-plan.md"
REPORT_REL = "outputs/tobe/migration/wave-model-consistency.json"

# Contrato canônico do trigger BC (ava-tobe-architecture-design). Tem
# precedência sobre qualquer markdown: é schema fixo, então lê-lo é `json.load`,
# não heurística. Ver `## BC Canonical JSON Contract` na spec daquele agente.
BC_MAP_JSON_RELS = (
    "outputs/tobe/docs/bounded-context-map.json",
    "outputs/asis/docs/bounded-context-map.json",
)

# Fallback para projetos gerados antes do contrato JSON existir. A ordem importa:
# a primeira fonte que nomear um BC define o nome dele.
BC_MAP_RELS = (
    "outputs/tobe/docs/bounded-context-map.md",
    "outputs/tobe/bounded-context-map.md",
    "outputs/asis/bounded-context-map.md",
    "outputs/asis/docs/bounded-context-map.md",
)

_BC_ID = re.compile(r"\bBC-\d+\b")
_BC_HEADING = re.compile(r"^#{2,3}\s+(BC-\d+)\s*[:—–-]\s*(.+?)\s*$", re.MULTILINE)
_BC_TABLE_ROW = re.compile(r"^\|\s*(BC-\d+)\s*\|\s*([^|]+?)\s*\|", re.MULTILINE)
_BC_MERMAID = re.compile(r"\[\"?(BC-\d+)\\n([^\\\"\]]+)")
_WAVE_ID = re.compile(r"^W\d+$")


class ConsistencyError(RuntimeError):
    """O projeto não existe ou o wave-model.json não é sequer legível."""


# ── leitura ──────────────────────────────────────────────────────────────────

def _project_dir(project: str, root: Path) -> Path:
    directory = root / "projects" / project
    if not directory.is_dir():
        raise ConsistencyError(f"project não encontrado: projects/{project}")
    return directory


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def _bc_catalog_json(project_dir: Path) -> dict[str, str]:
    """Nomes de BC lidos do contrato canônico, sem heurística de markdown.

    JSON ilegível ou fora do schema é ignorado em silêncio de propósito: quem
    reprova o contrato do trigger BC é a validação daquele agente, não esta
    tool. Aqui o pior caso é cair no fallback de markdown, que é o que os
    projetos anteriores ao contrato já usam.
    """
    catalog: dict[str, str] = {}
    for rel in BC_MAP_JSON_RELS:
        path = project_dir / rel
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        for item in data.get("bounded_contexts") or []:
            if not isinstance(item, dict):
                continue
            bc_id = str(item.get("bc_id") or "").strip()
            bc_name = str(item.get("bc_name") or "").strip()
            # "A definir" é o default explícito do contrato para evidência
            # ausente — é uma lacuna declarada, não um nome. Aceitá-lo aqui
            # produziria cinco BCs chamados "A definir" no wave-model.
            if bc_id and bc_name and bc_name.casefold() != "a definir":
                catalog.setdefault(bc_id, bc_name)
    return catalog


def _bc_catalog(project_dir: Path) -> dict[str, str]:
    """Nome canônico de cada BC, do contrato JSON e, na falta dele, dos markdowns.

    Três formas de markdown convivem nos artefatos reais e todas são aceitas:
    heading (`## BC-01: Employee Management`), linha de tabela
    (`| BC-01 | Nome |`) e rótulo de nó Mermaid
    (`BC01["BC-01\\nEmployee Management"]`). O primeiro arquivo da ordem de
    precedência que declarar um BC define o nome dele — e o
    `bounded-context-map.json` vem antes de todos.
    """
    catalog: dict[str, str] = _bc_catalog_json(project_dir)
    for rel in BC_MAP_RELS:
        text = _read(project_dir / rel)
        if not text:
            continue
        for pattern in (_BC_HEADING, _BC_TABLE_ROW, _BC_MERMAID):
            for bc_id, raw_name in pattern.findall(text):
                name = raw_name.strip().strip("*").strip("`").strip()
                # Linhas como `| BC-02 → BC-01 | Conformist |` não nomeiam nada.
                if not name or _BC_ID.search(name) or name.startswith("-"):
                    continue
                catalog.setdefault(bc_id, name)
    return catalog


# ── normalização (auto-correção) ─────────────────────────────────────────────

def _as_wave_id(value: Any) -> str:
    text = str(value if value is not None else "").strip()
    if re.fullmatch(r"\d+", text):
        return f"W{int(text)}"
    return text.upper()


def _bc_name_from_detail(detail: dict[str, Any]) -> str:
    """Nome do BC num bloco `bc_details`, tolerando o alias `name`.

    O contrato do manifesto é `bc_name`. Agentes gravaram `name` em execuções
    reais; aceitar o alias na leitura e gravar sempre `bc_name` é o que faz a
    normalização convergir em vez de oscilar entre as duas grafias.
    """
    for key in ("bc_name", "name", "bc_title", "title"):
        value = str(detail.get(key) or "").strip()
        if value:
            return value
    return ""


def _normalize_wave(
    wave: dict[str, Any],
    index: int,
    catalog: dict[str, str],
    plan_names: dict[str, str],
    fixes: list[str],
    errors: list[str],
) -> dict[str, Any]:
    wave = dict(wave)
    label = f"waves[{index}]"

    # 1. wave_id ⟷ wave_number — o manifesto aceita qualquer um dos dois, mas
    #    artefatos derivados (summary, gantt) leem campos diferentes. Declarar
    #    os dois, concordando, encerra a divergência.
    wave_id = _as_wave_id(wave.get("wave_id") if wave.get("wave_id") is not None
                          else wave.get("wave_number"))
    if not _WAVE_ID.fullmatch(wave_id):
        errors.append(f"{label}: wave_id/wave_number ausente ou inválido ({wave_id!r})")
        return wave
    label = wave_id
    if wave.get("wave_id") != wave_id:
        wave["wave_id"] = wave_id
        fixes.append(f"{label}: wave_id normalizado para {wave_id!r}")
    numero = int(wave_id[1:])
    if wave.get("wave_number") != numero:
        wave["wave_number"] = numero
        fixes.append(f"{label}: wave_number preenchido com {numero}")

    # 2. tshirt — o template e build_summary_comprehensive leem `tshirt`;
    #    `tshirt_size` é grafia divergente vista em produção.
    if not str(wave.get("tshirt") or "").strip():
        alias = str(wave.get("tshirt_size") or "").strip()
        if alias:
            wave["tshirt"] = alias
            fixes.append(f"{label}: tshirt derivado de tshirt_size ({alias!r})")

    # 3. bounded_contexts → lista canônica de objetos, absorvendo bc_details.
    raw_contexts = wave.get("bounded_contexts")
    if raw_contexts is None:
        raw_contexts = []
    if not isinstance(raw_contexts, list):
        errors.append(f"{label}: bounded_contexts precisa ser uma lista")
        return wave

    raw_details = wave.get("bc_details")
    details_by_id: dict[str, dict[str, Any]] = {}
    if isinstance(raw_details, list):
        for item in raw_details:
            if not isinstance(item, dict):
                continue
            bc_id = str(item.get("bc_id") or "").strip()
            if bc_id:
                details_by_id[bc_id] = item

    contexts: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for position, raw in enumerate(raw_contexts):
        if isinstance(raw, dict):
            context = dict(raw)
            bc_id = str(context.get("bc_id") or "").strip()
        elif isinstance(raw, str) and raw.strip():
            bc_id = raw.strip()
            context = {"bc_id": bc_id}
            fixes.append(f"{label}: bounded_contexts[{position}] {bc_id!r} "
                         "convertido de ID textual para objeto canônico")
        else:
            errors.append(f"{label}.bounded_contexts[{position}]: "
                          "precisa ser um objeto ou um BC ID textual")
            continue

        if not bc_id:
            errors.append(f"{label}.bounded_contexts[{position}]: bc_id vazio")
            continue
        if bc_id in seen_ids:
            errors.append(f"{label}: bc_id duplicado dentro da wave ({bc_id})")
            continue
        seen_ids.add(bc_id)

        # Campos do bc_details correspondente entram sem sobrescrever o que já
        # está no objeto: o objeto é a fonte, o detail é o complemento.
        detail = details_by_id.pop(bc_id, None)
        if detail:
            for key, value in detail.items():
                if key == "bc_id":
                    continue
                canonical = "bc_name" if key in ("name", "bc_title", "title") else key
                context.setdefault(canonical, value)

        name = str(context.get("bc_name") or "").strip()
        if not name and detail:
            name = _bc_name_from_detail(detail)
        if not name:
            name = catalog.get(bc_id, "") or plan_names.get(bc_id, "")
            if name:
                fixes.append(f"{label}: bc_name de {bc_id} resolvido "
                             f"a partir dos artefatos do projeto ({name!r})")
        if not name:
            errors.append(
                f"{label}: {bc_id} não tem bc_name e nenhum artefato do projeto "
                "o nomeia — declare o BC em outputs/tobe/docs/bounded-context-map.md "
                "ou preencha bc_name no wave-model.json")
            continue
        context["bc_name"] = name
        contexts.append(context)

    if details_by_id:
        # Definição sem referência: o inverso do defeito original, igualmente
        # incoerente — um BC descrito na wave que a wave não declara conter.
        orfaos = ", ".join(sorted(details_by_id))
        errors.append(f"{label}: bc_details descreve BCs ausentes de "
                      f"bounded_contexts: {orfaos}")

    wave["bounded_contexts"] = contexts
    if "bc_details" in wave and not details_by_id:
        wave.pop("bc_details")
        fixes.append(f"{label}: bc_details removido — seus campos foram "
                     "absorvidos em bounded_contexts[] (representação única)")

    return wave


def _normalize_dependencies(
    waves: list[dict[str, Any]], fixes: list[str], errors: list[str]
) -> None:
    """Encadeia as waves e confere que toda dependência aponta para uma wave real."""
    ids = [str(wave.get("wave_id") or "") for wave in waves]
    conhecidas = {wave_id for wave_id in ids if _WAVE_ID.fullmatch(wave_id)}
    anterior: str | None = None
    for wave in waves:
        wave_id = str(wave.get("wave_id") or "")
        # Presença da chave, não sua verdade: `dependencies: []` é declaração
        # explícita de "não depende de ninguém" e é o campo que o manifesto lê
        # primeiro. Escolher pelo valor faria a tool gravar um
        # `depends_on_waves` que contradiz um `dependencies: []` já presente —
        # dois campos discordando, exatamente o defeito que ela existe para
        # eliminar.
        campo = "dependencies" if "dependencies" in wave else "depends_on_waves"
        raw = wave.get(campo)
        if raw is None:
            # Ausente ≠ vazio. `[]` é a declaração explícita de que a wave não
            # depende de ninguém (correta para W0); ausência é lacuna, e a
            # cadeia sequencial é o que o próprio wave-plan.md já afirma.
            derivado = [anterior] if anterior else []
            wave["depends_on_waves"] = derivado
            fixes.append(f"{wave_id}: depends_on_waves ausente — preenchido "
                         f"com a cadeia sequencial {derivado}")
        else:
            if not isinstance(raw, list):
                errors.append(f"{wave_id}: {campo} precisa ser uma lista")
                anterior = wave_id
                continue
            normalizado = [_as_wave_id(item) for item in raw]
            if normalizado != list(raw):
                wave[campo] = normalizado
                fixes.append(f"{wave_id}: {campo} normalizado para ids de wave "
                             f"{normalizado}")
            pendentes = sorted(set(normalizado) - conhecidas)
            if pendentes:
                errors.append(f"{wave_id}: {campo} aponta para waves inexistentes: "
                              f"{', '.join(pendentes)}")
            if wave_id in normalizado:
                errors.append(f"{wave_id}: depende de si mesma")
        anterior = wave_id


def _normalize_totals(
    data: dict[str, Any], waves: list[dict[str, Any]], fixes: list[str], errors: list[str]
) -> None:
    total = len(waves)
    if data.get("total_waves") != total:
        anterior = data.get("total_waves")
        data["total_waves"] = total
        fixes.append(f"total_waves corrigido de {anterior!r} para {total}")
    summary = data.get("summary")
    if isinstance(summary, dict) and summary.get("total_waves") != total:
        summary["total_waves"] = total
        fixes.append(f"summary.total_waves corrigido para {total}")

    # FP/SP só são conferidos quando existem: até a Fase 3 (sizing) rodar, o
    # modelo carrega zeros de propósito, e reprovar aqui seria reprovar o
    # estado normal do artefato recém-gerado.
    def _numero(value: Any) -> float | None:
        try:
            return float(str(value).strip())
        except (TypeError, ValueError):
            return None

    for campo in ("total_fp", "total_sp"):
        parciais = [_numero(wave.get(campo)) for wave in waves]
        if any(item is None for item in parciais):
            continue
        soma = sum(parciais)  # type: ignore[arg-type]
        declarado = _numero(data.get(campo))
        if declarado is None:
            continue
        if abs(declarado - soma) > 0.01:
            errors.append(f"{campo}={declarado:g} diverge da soma das waves "
                          f"({soma:g}) — recalcule ou corrija as waves")


def _normalize_identity(
    data: dict[str, Any], project: str, fixes: list[str], errors: list[str]
) -> None:
    """Faz a guarda de projeto do manifesto sair do papel.

    `speckit_wave_manifest._load_model` compara `data["project"]` ou
    `metadata.project_name` com o projeto em execução. Um modelo que declara a
    identidade só em `project_name` de primeiro nível passa por essa guarda em
    silêncio — inclusive um modelo copiado de outro projeto. Promover a
    identidade para `metadata.project_name` liga a guarda.
    """
    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
        data["metadata"] = metadata

    declarado = str(data.get("project") or metadata.get("project_name")
                    or data.get("project_name") or "").strip()
    if declarado and declarado != project:
        errors.append(f"wave-model.json declara o projeto {declarado!r}, mas a "
                      f"execução é de {project!r} — artefato de outro projeto")
        return
    if metadata.get("project_name") != project:
        metadata["project_name"] = project
        fixes.append(f"metadata.project_name preenchido com {project!r} — sem "
                     "ele a guarda de projeto do manifesto não dispara")

    trace_id = str(data.get("trace_id") or metadata.get("trace_id") or "").strip()
    if trace_id and not metadata.get("trace_id"):
        metadata["trace_id"] = trace_id
        fixes.append("metadata.trace_id espelhado do trace_id de primeiro nível")


# ── validações cruzadas ──────────────────────────────────────────────────────

def _plan_bc_names(project_dir: Path) -> dict[str, str]:
    """Nomes de BC declarados no wave-plan.md, pela mesma leitura do manifesto."""
    sections = manifest._sections(
        _read(project_dir / PLAN_REL), manifest._WAVE_HEADING, stop_at_any_heading=True
    )
    nomes: dict[str, str] = {}
    for nome_wave, secao in sections.values():
        for bc_id, bc_name in manifest._plan_contexts(nome_wave, secao).items():
            if bc_name:
                nomes.setdefault(bc_id, bc_name)
    return nomes


def _deduplicar_bcs_entre_waves(waves: list[dict[str, Any]],
                                fixes: list[str], warnings: list[str]) -> None:
    """Um BC pertence à wave que o MIGRA — as demais só o referenciam.

    Caso medido (cadastro-funcionario-02, 2026-08-27): projeto com 3 BCs e
    estrutura fixa de 5 waves. O agente alocou BC-01+BC-02 em W1 e BC-03 em W2,
    deixando W3 sem BC próprio — e então deu a W3 um escopo transversal
    ("paridade funcional, performance, índices") **relistando os três BCs** em
    `bounded_contexts[]`.

    A intenção é legítima; o campo é que não significa isso. `bounded_contexts[]`
    declara quais BCs a wave MIGRA, e é dele que `speckit_wave_manifest` deriva o
    recorte vertical: as âncoras (`US-*`, `TC-*`, operações de API) de cada BC vão
    para a feature daquela wave. Relistar faz W1 e W3 reivindicarem as MESMAS
    âncoras, e a F3S gera spec e task duplicadas para o mesmo BC.

    A desambiguação é determinística porque waves são sequenciais: BC-01 não pode
    ser validado em W3 antes de existir em W1. A primeira ocorrência é a dona; as
    posteriores são referência transversal e saem da composição. O escopo
    transversal continua descrito em `scope_description`/`activities`, que é onde
    ele pertence.
    """
    dono: dict[str, str] = {}
    for wave in waves:
        wave_id = str(wave.get("wave_id") or "")
        mantidos: list[dict[str, Any]] = []
        removidos: list[str] = []
        for context in wave.get("bounded_contexts") or []:
            bc_id = str(context.get("bc_id") or "")
            if bc_id and bc_id in dono:
                removidos.append(bc_id)
                continue
            if bc_id:
                dono[bc_id] = wave_id
            mantidos.append(context)
        if removidos:
            wave["bounded_contexts"] = mantidos
            fixes.append(
                f"{wave_id}: {', '.join(removidos)} removido(s) de "
                f"bounded_contexts — já migrado(s) em "
                f"{', '.join(sorted({dono[bc] for bc in removidos}))}. A wave "
                "segue transversal a eles pelo scope_description; relistá-los "
                "duplicaria as âncoras e faria a F3S gerar spec/task repetidas.")
            if not mantidos:
                warnings.append(
                    f"{wave_id} ficou sem Bounded Context próprio. Revise se ela "
                    "deveria migrar algum BC ou se é mesmo uma wave transversal "
                    "— com 5 waves fixas e poucos BCs, sobra wave sem domínio.")


def _cross_validate(
    project_dir: Path,
    waves: list[dict[str, Any]],
    catalog: dict[str, str],
    errors: list[str],
    warnings: list[str],
) -> None:
    dono: dict[str, str] = {}
    for wave in waves:
        wave_id = str(wave.get("wave_id") or "")
        for context in wave.get("bounded_contexts") or []:
            bc_id = str(context.get("bc_id") or "")
            if bc_id in dono:
                # Não deveria acontecer: `_deduplicar_bcs_entre_waves` roda antes.
                errors.append(f"{bc_id} alocado em duas waves: {dono[bc_id]} e {wave_id}")
            else:
                dono[bc_id] = wave_id

    # BC citado no modelo mas inexistente no bounded-context-map é referência
    # órfã — o BC não tem definição arquitetural em lugar nenhum.
    if catalog:
        desconhecidos = sorted(set(dono) - set(catalog))
        if desconhecidos:
            errors.append(
                "BCs alocados em waves sem definição no bounded-context-map: "
                + ", ".join(desconhecidos))
        nao_alocados = sorted(set(catalog) - set(dono))
        if nao_alocados:
            warnings.append(
                "BCs definidos no bounded-context-map e não alocados a nenhuma "
                "wave: " + ", ".join(nao_alocados))
    else:
        warnings.append("bounded-context-map.md não encontrado — nomes de BC não "
                        "puderam ser conferidos contra a fonte de domínio")

    # wave-plan.md: mesmas waves, mesma composição. As divergências aqui são as
    # que o build_manifest também detecta; reportá-las nomeadas antes evita que
    # o operador receba só a mensagem genérica do gate.
    plan_path = project_dir / PLAN_REL
    if not plan_path.is_file():
        warnings.append("wave-plan.md ausente — composição não pôde ser conferida")
        return
    sections = manifest._sections(
        _read(plan_path), manifest._WAVE_HEADING, stop_at_any_heading=True
    )
    if not sections:
        warnings.append("wave-plan.md não tem headings de wave parseáveis "
                        "(`## W0 — Nome`) — composição não conferida")
        return
    modelo_ids = {str(wave.get("wave_id") or "") for wave in waves}
    plano_ids = set(sections)
    if plano_ids != modelo_ids:
        errors.append(f"waves do wave-plan.md divergem do modelo: "
                      f"model={sorted(modelo_ids)}, plan={sorted(plano_ids)}")
    modelo_bcs = {
        str(wave.get("wave_id") or ""): {
            str(context.get("bc_id")) for context in (wave.get("bounded_contexts") or [])
        }
        for wave in waves
    }
    for wave_id, (nome, secao) in sections.items():
        declarados = set(manifest._plan_contexts(nome, secao))
        no_modelo = modelo_bcs.get(wave_id, set())
        if declarados and declarados != no_modelo:
            delta = []
            if declarados - no_modelo:
                delta.append(f"só no plan={sorted(declarados - no_modelo)}")
            if no_modelo - declarados:
                delta.append(f"só no modelo={sorted(no_modelo - declarados)}")
            errors.append(f"{wave_id}: BCs do wave-plan.md divergem do modelo "
                          f"({'; '.join(delta)})")


# ── orquestração ─────────────────────────────────────────────────────────────

def analyze(project: str, repo_root: Path | None = None, *,
            fix: bool = False, force: bool = False) -> dict[str, Any]:
    """Diagnostica (e opcionalmente repara) a coerência dos artefatos de waves.

    `force` grava os reparos MECÂNICOS mesmo restando erro de julgamento (BC em
    duas waves, BC sem definição no mapa, divergência com o wave-plan). Existe
    para o caminho de remediação da F3S: reter uma normalização que só melhora o
    artefato — e nunca perde informação — por causa de um erro NÃO RELACIONADO
    mantém a fase travada sem necessidade. Os erros continuam reportados; o que
    muda é que deixam de impedir a escrita do que é seguro.
    """
    root = repo_root or REPO_ROOT
    project_dir = _project_dir(project, root)
    model_path = project_dir / MODEL_REL

    fixes: list[str] = []
    errors: list[str] = []
    warnings: list[str] = []

    if not model_path.is_file():
        raise ConsistencyError(
            f"wave-model.json ausente: {MODEL_REL} — rode a F2 "
            "(ava-tobe-migration-plan) para produzi-lo")
    try:
        data = json.loads(model_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConsistencyError(f"wave-model.json ilegível: {exc}") from exc
    if not isinstance(data, dict):
        raise ConsistencyError("wave-model.json precisa ser um objeto JSON")

    raw_waves = data.get("waves")
    if not isinstance(raw_waves, list) or not raw_waves:
        raise ConsistencyError("wave-model.json precisa declarar waves[] não vazio")

    catalog = _bc_catalog(project_dir)
    plan_names = _plan_bc_names(project_dir)

    waves: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_waves):
        if not isinstance(raw, dict):
            errors.append(f"waves[{index}] precisa ser um objeto, "
                          f"recebido {type(raw).__name__}")
            continue
        waves.append(_normalize_wave(raw, index, catalog, plan_names, fixes, errors))

    vistos: set[str] = set()
    for wave in waves:
        wave_id = str(wave.get("wave_id") or "")
        if wave_id in vistos:
            errors.append(f"wave_id duplicado: {wave_id}")
        vistos.add(wave_id)

    _deduplicar_bcs_entre_waves(waves, fixes, warnings)
    _normalize_dependencies(waves, fixes, errors)
    data["waves"] = waves
    _normalize_totals(data, waves, fixes, errors)
    _normalize_identity(data, project, fixes, errors)
    _cross_validate(project_dir, waves, catalog, errors, warnings)

    written = False
    if fix and fixes and (force or not errors):
        temporary = model_path.with_name(f".{model_path.name}.tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
        temporary.replace(model_path)
        written = True

    # Veredito final pelo mesmo código que a F3S executa. Rodar depois da
    # escrita é deliberado: o que importa é se o ARQUIVO EM DISCO expande, não
    # se a estrutura em memória expandiria.
    #
    # Por isso o veredito é pulado enquanto há correção pendente de escrita
    # (diagnóstico sem --fix): o disco ainda contém o defeito que acabamos de
    # apontar, e reportá-lo de novo como erro final faria a tool acusar como
    # insanável exatamente o que ela sabe consertar.
    manifest_error: str | None = None
    manifest_waves: int | None = None
    pendente = bool(fixes) and not written
    if not errors and not pendente:
        try:
            expandido = manifest.build_manifest(project, root)
            manifest_waves = expandido["total_waves"]
        except manifest.ManifestError as exc:
            manifest_error = str(exc)
            errors.append(f"manifesto de waves da F3S continua inválido: {exc}")
        except Exception as exc:  # noqa: BLE001 — degradar, nunca quebrar
            manifest_error = f"{type(exc).__name__}: {exc}"
            warnings.append(f"build_manifest não pôde ser executado: {manifest_error}")

    if errors:
        status = "error"
    elif pendente:
        status = "fixable"
    else:
        status = "ok"

    return {
        "report_version": REPORT_VERSION,
        "project": project,
        "status": status,
        "model": MODEL_REL,
        "written": written,
        "fixes": fixes,
        "errors": errors,
        "warnings": warnings,
        "manifest_error": manifest_error,
        "manifest_total_waves": manifest_waves,
        "waves": [
            {
                "wave_id": str(wave.get("wave_id") or ""),
                "wave_name": str(wave.get("wave_name") or ""),
                "wave_type": str(wave.get("wave_type") or ""),
                "bounded_contexts": [
                    {"bc_id": str(context.get("bc_id") or ""),
                     "bc_name": str(context.get("bc_name") or "")}
                    for context in (wave.get("bounded_contexts") or [])
                ],
            }
            for wave in waves
        ],
    }


def remediate(project: str, repo_root: Path | None = None, *,
              attempts: int = 3) -> list[dict[str, Any]]:
    """Tenta deixar o wave-model expansível, até `attempts` vezes. Nunca levanta.

    Cada passada aplica os reparos mecânicos e reavalia. Repetir tem sentido
    porque um reparo destrava a leitura do seguinte: converter os IDs textuais em
    objetos é o que permite conferir duplicidade de BC entre waves, que por sua
    vez é o que permite conferir a composição contra o wave-plan.md. Passada sem
    reparo novo encerra o laço — insistir só gastaria tempo.

    Devolve o relatório de cada tentativa, para quem chamou registrar o que foi
    feito. Erro de infraestrutura (projeto inexistente, JSON ilegível) vira um
    relatório de status `error`, nunca exceção: este caminho existe justamente
    para não derrubar a fase.
    """
    historico: list[dict[str, Any]] = []
    for tentativa in range(1, max(1, attempts) + 1):
        try:
            resultado = analyze(project, repo_root, fix=True, force=True)
        except ConsistencyError as exc:
            historico.append({"attempt": tentativa, "status": "error",
                              "errors": [str(exc)], "fixes": [], "warnings": []})
            break
        resultado["attempt"] = tentativa
        historico.append(resultado)
        if resultado["status"] == "ok" or not resultado["fixes"]:
            break
    return historico


def _write_report(project: str, root: Path, resultado: dict[str, Any]) -> Path:
    target = _project_dir(project, root) / REPORT_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp")
    temporary.write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    temporary.replace(target)
    return target


def _render(resultado: dict[str, Any], fix: bool) -> None:
    for item in resultado["fixes"]:
        marca = "corrigido" if resultado["written"] else "corrigível"
        print(f"  [{marca}] {item}")
    for item in resultado["warnings"]:
        print(f"  [aviso] {item}")
    for item in resultado["errors"]:
        print(f"  [ERRO] {item}")
    if resultado["status"] == "ok":
        total = resultado["manifest_total_waves"]
        sufixo = f" — manifesto F3S expande {total} wave(s)" if total else ""
        print(f"wave-model.json coerente{sufixo}")
    elif resultado["status"] == "fixable":
        print(f"{len(resultado['fixes'])} divergência(s) mecanicamente corrigível(is); "
              "rode de novo com --fix para aplicar")
    elif resultado["fixes"]:
        print("há divergências corrigíveis, mas erros não automáticos impedem a "
              "escrita — resolva os [ERRO] acima e rode com --fix")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="wave_model_consistency.py",
        description="Normaliza e valida a coerência do wave-model.json da F2.")
    parser.add_argument("--project", "-p", required=True)
    parser.add_argument("--fix", action="store_true",
                        help="aplica as correções mecânicas no wave-model.json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--warn", action="store_true",
                        help="converte reprovação em aviso e retorna exit 0")
    args = parser.parse_args(argv)

    try:
        resultado = analyze(args.project, fix=args.fix)
    except ConsistencyError as exc:
        payload = {
            "report_version": REPORT_VERSION,
            "project": args.project,
            "status": "error",
            "errors": [str(exc)],
            "fixes": [],
            "warnings": [],
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"ERRO: {exc}", file=sys.stderr)
        return 0 if args.warn else 2

    try:
        _write_report(args.project, REPO_ROOT, resultado)
    except OSError as exc:  # noqa: BLE001 — relatório é acessório, não o veredito
        resultado["warnings"].append(f"relatório não pôde ser gravado: {exc}")

    if args.json:
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
    else:
        _render(resultado, args.fix)

    if resultado["status"] == "ok":
        return 0
    return 0 if args.warn else 2


if __name__ == "__main__":
    raise SystemExit(main())
