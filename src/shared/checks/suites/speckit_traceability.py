"""
suites/speckit_traceability.py
==============================
Valida a espinha de rastreabilidade da fase F3S nos dois sentidos.

Por que nos dois sentidos
-------------------------
A auditoria de ``nopcommerce-02-cli-ava`` encontrou a `traceability-matrix.md`
gerada pela esteira marcando **as 15 linhas AS-IS→TO-BE→TC como ✅ para classes
que não existiam no código gerado** — "a matriz é um falso positivo integral".

Rastreabilidade só vale se for verificável. Aqui:

* **adiante** — toda regra de negócio, operação de API e caso de teste da fonte
  precisa alcançar ao menos uma task; omissão vira reprovação, não silêncio;
* **de volta** — toda task precisa de linha na rastreabilidade, e a âncora
  dessa linha é procurada **reabrindo o arquivo-fonte**. Âncora inventada
  reprova e bloqueia a F4.

O JSON é a autoridade, não o Markdown
------------------------------------
A primeira execução real da F3S emitiu 175 tasks como tabela Markdown compacta —
formato diferente do que o agente mandava usar, porque blocos por task não cabem
no orçamento de saída. O parser não reconheceu nada e a suíte reportou "nenhuma
task declarada", escondendo 175 tasks válidas.

Desde então: ``traceability.json`` carrega os campos que a maquinaria consome, e
``specs/{feature}/tasks.md`` é a visão humana derivada dele. A suíte lê o JSON;
da tabela confere apenas que não divergiu (CHK-SK-015). Parsing de Markdown saiu
do caminho crítico.

Checks aplicados
  CHK-SK-001  constitution.md existe e não é trivial
  CHK-SK-002  todo specs/{feature}/spec.md existe e não é trivial
  CHK-SK-003  todo specs/{feature}/plan.md existe e não é trivial
  CHK-SK-004  cada pasta de feature tem spec.md, plan.md e tasks.md
  CHK-SK-005  traceability.json tem entradas, e a contagem declarada bate
  CHK-SK-006  toda âncora é encontrada no arquivo-fonte declarado
  CHK-SK-007  toda BR-* do catálogo alcança >= 1 task
  CHK-SK-008  toda operação do OpenAPI alcança >= 1 task
  CHK-SK-009  todo TC-* de test-cases.md alcança >= 1 task
  CHK-SK-010  toda task tem critério de aceite e target_files
  CHK-SK-011  tasks-progress.json é 1:1 com traceability.json por task_id
  CHK-SK-012  toda entrada `verified` tem evidência com exit code real
  CHK-SK-013  traceability.json conforma ao schema — chave raiz e campos
  CHK-SK-014  todo spec.md tem as 6 seções literais do readiness-gate C2
  CHK-SK-015  todo task_id do JSON aparece na tabela de tasks.md, e vice-versa

Uso (standalone):
    python -m src.shared.checks --project Meu-ERP --suite speckit_traceability

Uso (programático):
    from src.shared.checks.suites.speckit_traceability import SpeckitTraceabilitySuite
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.shared.tools import dependency_graph

if TYPE_CHECKING:
    from src.shared.checks.context import CheckContext
    from src.shared.checks.reporter import Reporter

SUITE = "speckit_traceability"

#: Padrão de `task_id` — espelha o schema
_TASK_ID = re.compile(r"^T-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d{3}$")
_TASK_ID_INLINE = re.compile(r"\bT-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d{3}\b")

#: Campos sem os quais a task não pode ser despachada nem verificada
_CAMPOS_OBRIGATORIOS = ("task_id", "spec_id", "plan_id", "group", "target_stack",
                        "source_artifact", "source_anchor", "target_files")
_CAMPOS_OBRIGATORIOS_V2 = _CAMPOS_OBRIGATORIOS + (
    "title", "feature", "action", "depends_on", "acceptance", "verify_command",
    "priority", "story_points", "topological_rank", "execution_wave",
)
_CAMPOS_OBRIGATORIOS_V3 = _CAMPOS_OBRIGATORIOS_V2 + (
    "task_type", "backend_dependencies",
)
_CAMPOS_OBRIGATORIOS_V4 = (
    "task_id", "title", "spec_id", "plan_id", "feature", "group",
    "migration_wave_id", "migration_wave_order", "task_type", "target_stack",
    "source_refs", "target_files", "action", "depends_on", "backend_dependencies",
    "acceptance", "verify_command", "priority", "story_points", "topological_rank",
    "execution_wave",
)

_ROOT_V2 = (
    "total_tasks", "graph_checksum", "dependency_edges", "execution_order",
    "execution_waves",
)

_SCHEMA_REL = "src/shared/schemas/speckit-traceability-v4.schema.json"

#: As 6 seções que o readiness-gate C2 confere por glob. Literais, sem tradução.
_SECOES_C2 = ("## Context", "## Input", "## Processing",
              "## Output", "## Examples", "## Failure Modes")

#: Ids de regra de negócio, casos de teste
_BR_ID = re.compile(r"\bBR-[A-Z0-9]+(?:-[A-Z0-9]+)*\b")
_TC_ID = re.compile(r"\bTC-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*\b")

#: Operação OpenAPI dentro de um path item
_HTTP_VERBS = ("get", "post", "put", "patch", "delete", "head", "options")

#: Tamanho abaixo do qual um artefato é considerado esqueleto, não entrega
_MIN_CHARS = 400


def _norm(text: str) -> str:
    """Normaliza para comparação de âncora: sem acento, sem caixa, sem espaço duplo."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip().lower()


def _slug(text: str) -> str:
    """Slug estilo GitHub de um heading: sem acento, minúsculo, hífens no lugar de espaço."""
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(c for c in text if not unicodedata.combining(c)).lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def _headings_slug(conteudo: str) -> set[str]:
    """Slugs de todos os headings markdown do documento.

    Uma âncora pode ser escrita como prosa (``Estrutura a gerar``) ou como slug
    (``3-modelo-de-domínio``). A busca por substring só resolve a primeira forma:
    o slug tem hífen onde o heading tem espaço e ponto, e nunca casa literalmente.
    Isso reprovava 56 referências legítimas do `nopcommerce-04` — falso negativo,
    não âncora inventada. Slug inexistente continua reprovando.
    """
    return {_slug(linha.lstrip("#").strip())
            for linha in conteudo.splitlines() if linha.lstrip().startswith("#")}


def _ancora_resolve(anchor: str, conteudo: str, slugs: set[str]) -> bool:
    """A âncora aponta para algo que existe de fato no artefato-fonte?

    Três formas aceitas, todas verificáveis contra o arquivo:

    1. **prosa literal** — ``Estrutura a gerar``, ``BR-MED-001``, ``DEC-021``;
    2. **slug de heading** — ``3-modelo-de-domínio`` para ``## 3. Modelo de Domínio``;
    3. **slug parcial de heading** — ``4.1-calcular-imposto`` para
       ``### 4.1 Calcular Imposto (Tax)``. A âncora cita a seção e omite o
       sufixo entre parênteses; é referência real, não invenção. O corte só vale
       em fronteira de segmento, então ``Section3-CatalogDomain`` — que não
       prefixa heading nenhum — continua reprovando.
    """
    if _norm(anchor) in _norm(conteudo):
        return True
    alvo = _slug(anchor)
    if alvo in slugs:
        return True
    return any(h == alvo or h.startswith(alvo + "-") for h in slugs)


class SpeckitTraceabilitySuite:
    """CHK-SK-001..012 — a espinha da F3S."""

    def __init__(self, ctx: "CheckContext") -> None:
        self.ctx = ctx
        self.speckit = ctx.outputs_dir / "tobe" / "speckit"
        self.outputs = ctx.outputs_dir
        self.manifest_features = self._load_manifest_features()

    # ── entrada ──────────────────────────────────────────────────────────

    def run(self, reporter: "Reporter") -> None:
        if not self.speckit.is_dir():
            reporter.record(
                SUITE, "CHK-SK-000 diretório outputs/tobe/speckit/ existe", False,
                f"{self.speckit} ausente — a fase F3S não rodou neste projeto. "
                f"Rode: ava-pipeline run -p {self.ctx.project} --phase F3S",
            )
            return

        trace = self._chk_013_schema(reporter)

        self._chk_001_constitution(reporter)
        self._chk_002_003_specs_plans(reporter)
        self._chk_004_pares(reporter)
        self._chk_014_secoes_c2(reporter)
        self._chk_005_contagem(reporter, trace)
        self._chk_015_tabela(reporter, trace)
        self._chk_006_ancoras(reporter, trace)
        self._chk_007_regras(reporter, trace)
        self._chk_008_api(reporter, trace)
        self._chk_009_test_cases(reporter, trace)
        self._chk_010_campos(reporter, trace)
        self._chk_016_017_dependencias(reporter, trace)
        self._chk_018_ordem(reporter, trace)
        self._chk_011_012_razao(reporter, trace)

    # ── descoberta do layout specs/{feature}/ ────────────────────────────

    def _features(self) -> list[Path]:
        """Pastas de feature — `specs/NNN-slug/`, na ordem do número."""
        d = self.speckit / "specs"
        if not d.is_dir():
            return []
        return sorted(p for p in d.iterdir() if p.is_dir())

    def _load_manifest_features(self) -> dict[str, bool]:
        path = self.speckit / "wave-spec-manifest.json"
        if not path.is_file():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return {
            str(item.get("feature")): bool(item.get("codegen"))
            for item in (data.get("features") or []) if item.get("feature")
        }

    def _expected_features(self, *, codegen_only: bool = False) -> list[Path]:
        directory = self.speckit / "specs"
        if self.manifest_features:
            names = [name for name, codegen in self.manifest_features.items()
                     if codegen or not codegen_only]
            return [directory / name for name in sorted(names)]
        return self._features()

    # ── carga ────────────────────────────────────────────────────────────

    def _chk_013_schema(self, reporter: "Reporter") -> list[dict[str, Any]]:
        """Conformidade estrutural, **antes** de qualquer check semântico.

        A primeira execução real emitiu a raiz como ``tasks`` em vez de
        ``entries``. O carregamento tolerante devolvia ``[]`` e a suíte reportava
        "nenhuma task" — o erro estrutural aparecia como ausência de dado,
        escondendo a causa. Aqui a chave errada é nomeada.
        """
        path = self.speckit / "traceability.json"
        nome = "CHK-SK-013 traceability.json conforma ao schema"
        if not path.is_file():
            reporter.record(SUITE, nome, False,
                            f"{path} ausente — sem ele nenhuma task é rastreável")
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            reporter.record(SUITE, nome, False, f"JSON inválido: {exc}")
            return []

        if not isinstance(data, dict):
            reporter.record(SUITE, nome, False,
                            f"raiz é {type(data).__name__}, esperado objeto com `entries`")
            return []

        entries = data.get("entries")
        if entries is None:
            outras = [k for k in data if isinstance(data.get(k), list)]
            reporter.record(SUITE, nome, False,
                            f"chave raiz `entries` ausente. Chaves encontradas: "
                            f"{', '.join(sorted(data))}"
                            + (f" — a lista está em `{outras[0]}`; renomeie para `entries` "
                               f"conforme {_SCHEMA_REL}" if outras else ""))
            return []
        if not isinstance(entries, list) or not entries:
            reporter.record(SUITE, nome, False, "`entries` vazio ou não é lista")
            return []

        version = data.get("schema_version")
        if version not in {"1.0.0", "2.0.0", "3.0.0", "4.0.0"}:
            reporter.record(SUITE, nome, False,
                            f"schema_version não suportada: {version!r}")
            return []

        root_missing = []
        if version in {"2.0.0", "3.0.0", "4.0.0"}:
            root_missing = [field for field in _ROOT_V2 if field not in data]

        faltando: list[str] = []
        formato: list[str] = []
        required_fields = (
            _CAMPOS_OBRIGATORIOS_V4 if version == "4.0.0"
            else _CAMPOS_OBRIGATORIOS_V3 if version == "3.0.0"
            else _CAMPOS_OBRIGATORIOS_V2 if version == "2.0.0"
            else _CAMPOS_OBRIGATORIOS
        )
        for e in entries:
            tid = e.get("task_id", "?")
            ausentes = [c for c in required_fields if c not in e or e.get(c) is None]
            non_empty = ["task_id", "spec_id", "plan_id", "group", "target_stack",
                         "target_files"]
            non_empty.extend(["source_refs", "migration_wave_id"] if version == "4.0.0"
                             else ["source_artifact", "source_anchor"])
            for field in non_empty:
                if field in e and not e.get(field) and field not in ausentes:
                    # Presente-porém-vazio ≠ ausente. `source_refs: []` é o
                    # estado que o reparador deixa quando todas as âncoras da
                    # spec eram inválidas; quem for corrigir precisa saber que
                    # o defeito está na spec, não no schema do compilador.
                    ausentes.append(f"{field} (vazio)")
            if version == "4.0.0" and isinstance(e.get("source_refs"), list):
                invalid_refs = [ref for ref in e["source_refs"] if not isinstance(ref, dict)
                                or not ref.get("artifact") or not ref.get("anchor")]
                if invalid_refs and "source_refs" not in ausentes:
                    ausentes.append("source_refs")
            if ausentes:
                faltando.append(f"{tid}: {', '.join(ausentes)}")
            if not _TASK_ID.match(str(tid)):
                formato.append(str(tid))

        partes = []
        if root_missing:
            partes.append(f"campos raiz v2 ausentes: {', '.join(root_missing)}")
        if faltando:
            partes.append(f"campos obrigatórios ausentes em {len(faltando)} entrada(s): "
                          f"{'; '.join(faltando[:4])}")
            partes.append("`group` e `target_stack` roteiam o fan-out da F4; "
                          "`target_files` e `source_anchor` sustentam razão e âncora — "
                          "sem eles a task não pode ser despachada nem verificada")
        if formato:
            partes.append(f"task_id fora do padrão T-XXX-000: {', '.join(formato[:6])}")
        reporter.record(SUITE, nome, not partes,
                (f"schema v{version} · " if not partes else "") + " · ".join(partes))
        return entries

    def _tabela_de_tasks(self, feature: Path) -> set[str]:
        """Ids declarados na tabela de `tasks.md` — visão humana derivada do JSON."""
        path = feature / "tasks.md"
        if not path.is_file():
            return set()
        return set(_TASK_ID_INLINE.findall(path.read_text(encoding="utf-8", errors="replace")))

    # ── checks ───────────────────────────────────────────────────────────

    def _chk_001_constitution(self, reporter: "Reporter") -> None:
        path = self.speckit / "constitution.md"
        ok = path.is_file() and len(path.read_text(encoding="utf-8", errors="replace")) >= _MIN_CHARS
        detalhe = "" if ok else (
            f"{path} ausente ou com menos de {_MIN_CHARS} chars. Ela entra no contexto de "
            f"todo agente a jusante, inclusive de cada chamada de codegen — um esqueleto aqui "
            f"propaga por toda a F4."
        )
        reporter.record(SUITE, "CHK-SK-001 constitution.md presente e substantiva", ok, detalhe)

    def _chk_002_003_specs_plans(self, reporter: "Reporter") -> None:
        all_features = self._expected_features()
        for chk, arquivo in (("CHK-SK-002", "spec.md"), ("CHK-SK-003", "plan.md")):
            features = all_features if arquivo == "spec.md" else self._expected_features(
                codegen_only=True
            )
            presentes = [f / arquivo for f in features if (f / arquivo).is_file()]
            ausentes = [f"{f.name}/{arquivo}" for f in features if not (f / arquivo).is_file()]
            magros = [f"{p.parent.name}/{p.name}" for p in presentes
                      if len(p.read_text(encoding="utf-8", errors="replace")) < _MIN_CHARS]
            ok = bool(features) and not ausentes and not magros
            if not features:
                detalhe = f"nenhuma pasta de feature em {self.speckit / 'specs'}"
            elif ausentes:
                detalhe = f"ausentes: {', '.join(ausentes[:8])}"
            elif magros:
                detalhe = f"abaixo de {_MIN_CHARS} chars: {', '.join(magros)}"
            else:
                detalhe = f"{len(presentes)} arquivo(s)"
            reporter.record(SUITE, f"{chk} specs/{{feature}}/{arquivo} presentes e substantivos",
                            ok, detalhe)

    def _chk_004_pares(self, reporter: "Reporter") -> None:
        """No layout SpecKit, o trio vive na mesma pasta — o par é por diretório."""
        features = self._expected_features()
        structured = False
        trace_path = self.speckit / "traceability.json"
        if trace_path.is_file():
            try:
                trace_data = json.loads(trace_path.read_text(encoding="utf-8"))
                structured = trace_data.get("schema_version") in {"2.0.0", "3.0.0", "4.0.0"}
            except (OSError, json.JSONDecodeError):
                pass
        incompletas = []
        for f in features:
            codegen = self.manifest_features.get(f.name, True)
            required = ("spec.md",)
            if codegen:
                required += ("plan.md", "tasks.md")
                if structured:
                    required += ("plan-graph.json", "task-fragment.json")
            faltando = [n for n in required if not (f / n).is_file()]
            if faltando:
                incompletas.append(f"{f.name}: falta {', '.join(faltando)}")
        ok = bool(features) and not incompletas
        detalhe = ("nenhuma pasta de feature encontrada" if not features
                   else " · ".join(incompletas))
        reporter.record(SUITE, "CHK-SK-004 cada feature tem todos os artefatos", ok, detalhe)

    def _chk_014_secoes_c2(self, reporter: "Reporter") -> None:
        """As 6 seções que o readiness-gate C2 confere por glob.

        A primeira execução real produziu 0 de 7 specs com elas — o produtor que
        criamos não satisfazia o consumidor que já existia. Traduzi-las também
        reprova: o C2 casa o heading literal em inglês.
        """
        features = self._features()
        sem_secoes = []
        for f in features:
            spec = f / "spec.md"
            if not spec.is_file():
                continue
            texto = spec.read_text(encoding="utf-8", errors="replace")
            faltando = [s for s in _SECOES_C2 if s not in texto]
            if faltando:
                sem_secoes.append(f"{f.name}: {len(faltando)}/6 ausentes "
                                  f"({', '.join(s.removeprefix('## ') for s in faltando[:3])}…)")
        ok = bool(features) and not sem_secoes
        detalhe = ("nenhuma pasta de feature encontrada" if not features
                   else " · ".join(sem_secoes[:5]))
        if sem_secoes:
            detalhe += " · sem elas o readiness-gate C2 reprova a wave inteira"
        reporter.record(SUITE, "CHK-SK-014 spec.md tem as 6 seções do readiness-gate", ok, detalhe)

    def _chk_005_contagem(self, reporter: "Reporter", trace: list[dict[str, Any]]) -> None:
        """Entradas existem, e a contagem declarada bate com a real.

        A primeira execução declarou `total_tasks: 157` com 175 entradas — número
        afirmado divergindo do contado, dentro da própria camada criada para
        eliminar isso.
        """
        path = self.speckit / "traceability.json"
        declarado = None
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                declarado = data.get("total_tasks") if isinstance(data, dict) else None
            except (OSError, json.JSONDecodeError):
                declarado = None

        ids = [e.get("task_id") for e in trace]
        duplicados = sorted({i for i in ids if ids.count(i) > 1})
        ok = bool(trace) and not duplicados and (declarado is None or declarado == len(trace))
        partes = []
        if not trace:
            partes.append("traceability.json sem entradas — nenhuma task é rastreável")
        if duplicados:
            partes.append(f"task_id duplicado: {', '.join(str(d) for d in duplicados[:6])}")
        if declarado is not None and declarado != len(trace):
            partes.append(f"contagem declarada {declarado} != {len(trace)} entradas reais — "
                          f"quem conta é este check, não o agente")
        reporter.record(SUITE, "CHK-SK-005 traceability.json tem entradas e contagem coerente",
                        ok, " · ".join(partes))

    def _chk_015_tabela(self, reporter: "Reporter", trace: list[dict[str, Any]]) -> None:
        """A tabela humana de `tasks.md` não pode divergir do JSON."""
        features = self._features()
        no_json = {str(e.get("task_id")) for e in trace}
        na_tabela: set[str] = set()
        for f in features:
            na_tabela |= self._tabela_de_tasks(f)

        so_no_json = sorted(no_json - na_tabela)
        so_na_tabela = sorted(na_tabela - no_json)
        ok = bool(no_json) and not so_no_json and not so_na_tabela
        partes = []
        if not no_json:
            partes.append("sem entradas no JSON para comparar")
        if so_no_json:
            partes.append(f"no JSON e fora da tabela: {', '.join(so_no_json[:8])}")
        if so_na_tabela:
            partes.append(f"na tabela e fora do JSON: {', '.join(so_na_tabela[:8])}")
        reporter.record(SUITE, "CHK-SK-015 tasks.md não divergiu do traceability.json",
                        ok, " · ".join(partes))

    def _chk_006_ancoras(self, reporter: "Reporter", trace: list[dict[str, Any]]) -> None:
        """Reabre o arquivo-fonte e procura a âncora. É o check que separa
        rastreabilidade verificável de narrativa."""
        if not trace:
            reporter.record(
                SUITE, "CHK-SK-006 toda âncora existe no arquivo-fonte", False,
                "sem entradas para verificar — verificação sem dado não é verificação. "
                "Um check de âncora que passa vazio é o mesmo `PASS (Simulated)` que "
                "motivou esta camada. Ver CHK-SK-013 para a causa.")
            return

        cache: dict[str, str | None] = {}
        slugs: dict[str, set[str]] = {}
        quebradas: list[str] = []
        sem_fonte: list[str] = []

        for entry in trace:
            task_id = entry.get("task_id", "?")
            refs = entry.get("source_refs")
            if not isinstance(refs, list):
                refs = [{"artifact": entry.get("source_artifact"),
                         "anchor": entry.get("source_anchor")}]
            for ref in refs:
                rel = ref.get("artifact") if isinstance(ref, dict) else ""
                anchor = ref.get("anchor") if isinstance(ref, dict) else ""
                if not rel or not anchor:
                    quebradas.append(f"{task_id} (sem fonte ou âncora)")
                    continue
                if rel not in cache:
                    path = self.ctx.project_dir / rel
                    if not path.is_file():
                        path = self.ctx.REPO_ROOT / rel
                    cache[rel] = path.read_text(encoding="utf-8", errors="replace") \
                        if path.is_file() else None
                    slugs[rel] = _headings_slug(cache[rel] or "")
                conteudo = cache[rel]
                if conteudo is None:
                    sem_fonte.append(f"{task_id} → {rel}")
                elif not _ancora_resolve(anchor, conteudo, slugs[rel]):
                    quebradas.append(f"{task_id} → '{anchor}' não encontrado em {rel}")

        ok = not quebradas and not sem_fonte
        partes = []
        if sem_fonte:
            partes.append(f"arquivo-fonte inexistente: {'; '.join(sem_fonte[:5])}")
        if quebradas:
            partes.append(f"âncora não encontrada: {'; '.join(quebradas[:5])}")
        if quebradas:
            partes.append("âncora inventada é o defeito que a matriz falso-positiva do "
                          "nopcommerce-02 exibiu — corrija a spec, não o check")
        reporter.record(SUITE, "CHK-SK-006 toda âncora existe no arquivo-fonte", ok,
                        " · ".join(partes))

    def _chk_007_regras(self, reporter: "Reporter", trace: list[dict[str, Any]]) -> None:
        catalogo = self._ids_do_catalogo_de_regras()
        if not catalogo:
            reporter.record(SUITE, "CHK-SK-007 toda regra de negócio alcança uma task", True,
                            "nenhum catálogo de regras encontrado — check não aplicável")
            return
        cobertas = {rid for e in trace for rid in (e.get("rule_ids") or [])}
        faltando = sorted(catalogo - cobertas)
        ok = not faltando
        reporter.record(
            SUITE, "CHK-SK-007 toda regra de negócio alcança uma task", ok,
            "" if ok else f"{len(faltando)}/{len(catalogo)} sem task: {', '.join(faltando[:10])}",
            blocking=False)

    def _chk_008_api(self, reporter: "Reporter", trace: list[dict[str, Any]]) -> None:
        operacoes = self._operacoes_do_openapi()
        if not operacoes:
            reporter.record(SUITE, "CHK-SK-008 toda operação de API alcança uma task", True,
                            "nenhum contrato OpenAPI encontrado — check não aplicável")
            return
        cobertas = {_norm(op) for e in trace for op in (e.get("api_ops") or [])}
        faltando = sorted(op for op in operacoes if _norm(op) not in cobertas)
        ok = not faltando
        reporter.record(
            SUITE, "CHK-SK-008 toda operação de API alcança uma task", ok,
            "" if ok else f"{len(faltando)}/{len(operacoes)} sem task: {', '.join(faltando[:10])}")

    def _chk_009_test_cases(self, reporter: "Reporter", trace: list[dict[str, Any]]) -> None:
        catalogo = self._ids_de_test_cases()
        if not catalogo:
            reporter.record(SUITE, "CHK-SK-009 todo caso de teste alcança uma task", True,
                            "test-cases.md não encontrado — check não aplicável")
            return
        cobertos = {t for e in trace for t in (e.get("test_ids") or [])}
        faltando = sorted(catalogo - cobertos)
        ok = not faltando
        reporter.record(
            SUITE, "CHK-SK-009 todo caso de teste alcança uma task", ok,
            "" if ok else f"{len(faltando)}/{len(catalogo)} sem task: {', '.join(faltando[:10])}")

    def _chk_010_campos(self, reporter: "Reporter", trace: list[dict[str, Any]]) -> None:
        if not trace:
            reporter.record(SUITE, "CHK-SK-010 toda task tem aceite e arquivo alvo", False,
                            "sem entradas para verificar — ver CHK-SK-013")
            return

        sem_aceite, sem_alvo, alvo_diretorio = [], [], []
        for e in trace:
            tid = e.get("task_id", "?")
            if not (e.get("acceptance") or []):
                sem_aceite.append(tid)
            alvos = e.get("target_files") or []
            if not alvos:
                sem_alvo.append(tid)
            for alvo in alvos:
                # Dotfile é arquivo: `Path('.gitkeep').suffix` é '', e testar só
                # o sufixo reprovava todo placeholder (`.gitkeep`, `.gitignore`,
                # `.editorconfig`) como se fosse diretório — o mesmo defeito que
                # derrubava o compilador antes de 2026-08-21.
                if alvo.endswith("/") or (
                    Path(alvo).suffix == "" and not Path(alvo).name.startswith(".")
                ):
                    alvo_diretorio.append(f"{tid} → {alvo}")
        ok = not (sem_aceite or sem_alvo or alvo_diretorio)
        partes = []
        if sem_aceite:
            partes.append(f"sem critério de aceite: {', '.join(sem_aceite[:8])}")
        if sem_alvo:
            partes.append(f"sem target_files: {', '.join(sem_alvo[:8])}")
        if alvo_diretorio:
            partes.append(f"alvo é diretório, não arquivo: {'; '.join(alvo_diretorio[:5])}")
        reporter.record(SUITE, "CHK-SK-010 toda task tem aceite e arquivo alvo", ok,
                        " · ".join(partes))

    def _chk_016_017_dependencias(self, reporter: "Reporter",
                                  trace: list[dict[str, Any]]) -> None:
        nome16 = "CHK-SK-016 referências de dependência são íntegras"
        nome17 = "CHK-SK-017 grafo de dependências é acíclico"
        if not trace:
            reporter.record(SUITE, nome16, False, "sem entries para construir o grafo")
            reporter.record(SUITE, nome17, False, "sem entries para construir o grafo")
            return

        try:
            dependency_graph.analyze(trace)
        except dependency_graph.DependencyGraphError as exc:
            ciclos = [issue for issue in exc.issues if issue.code == "cycle"]
            estruturais = [issue for issue in exc.issues if issue.code != "cycle"]
            reporter.record(
                SUITE, nome16, not estruturais,
                " · ".join(issue.message for issue in estruturais[:8]),
            )
            reporter.record(
                SUITE, nome17, not ciclos and not estruturais,
                ("validação de ciclo bloqueada por referências inválidas" if estruturais
                 else " · ".join(issue.message for issue in ciclos[:3])),
            )
            return

        by_id = {entry["task_id"]: entry for entry in trace}
        layer_issues = []
        for entry in trace:
            if "task_type" not in entry and "backend_dependencies" not in entry:
                continue
            task_id = entry["task_id"]
            task_type = entry.get("task_type")
            if task_type not in {"backend", "frontend"}:
                layer_issues.append(f"{task_id}: task_type inválido {task_type!r}")
                continue
            expected = []
            if task_type == "frontend":
                expected = sorted(
                    predecessor for predecessor in (entry.get("depends_on") or [])
                    if by_id[predecessor].get("task_type") == "backend"
                )
            declared = sorted(entry.get("backend_dependencies") or [])
            if declared != expected:
                layer_issues.append(
                    f"{task_id}: backend_dependencies={declared!r}, esperado {expected!r}"
                )

        reporter.record(
            SUITE, nome16, not layer_issues,
            (" · ".join(layer_issues[:8]) if layer_issues
             else f"{len(trace)} task(s), referências e camadas válidas"),
        )
        reporter.record(SUITE, nome17, True, "nenhum ciclo detectado")

    def _chk_018_ordem(self, reporter: "Reporter", trace: list[dict[str, Any]]) -> None:
        nome = "CHK-SK-018 ordem persistida corresponde ao DAG"
        if not trace:
            reporter.record(SUITE, nome, False, "sem entries para calcular a ordem")
            return
        try:
            plan = dependency_graph.analyze(trace)
        except dependency_graph.DependencyGraphError:
            reporter.record(SUITE, nome, False,
                            "grafo inválido — corrija CHK-SK-016/017 antes da ordem")
            return

        path = self.speckit / "traceability.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            reporter.record(SUITE, nome, False, str(exc))
            return

        persisted_order = data.get("execution_order")
        persisted_waves = data.get("execution_waves")
        if persisted_order is None and persisted_waves is None:
            reporter.record(
                SUITE, nome, True,
                "contrato v1 compatível: ordem calculável, ainda não persistida",
            )
            return

        expected_order = list(plan.order)
        expected_waves = [list(wave) for wave in plan.waves]
        ok = persisted_order == expected_order and persisted_waves == expected_waves
        detail = "" if ok else (
            f"persistido order={persisted_order!r}, waves={persisted_waves!r}; "
            f"calculado order={expected_order!r}, waves={expected_waves!r}"
        )
        reporter.record(SUITE, nome, ok, detail)

    def _chk_011_012_razao(self, reporter: "Reporter", trace: list[dict[str, Any]]) -> None:
        path = self.speckit / "tasks-progress.json"
        if not path.is_file():
            reporter.record(SUITE, "CHK-SK-011 tasks-progress.json é 1:1 com traceability.json",
                            False, f"{path} ausente — rode "
                                   f"`python src/shared/tools/task_ledger.py -p "
                                   f"{self.ctx.project} --init`")
            reporter.record(SUITE, "CHK-SK-012 status verificado tem evidência real", False,
                            "sem razão de progresso não há evidência a conferir")
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            reporter.record(SUITE, "CHK-SK-011 tasks-progress.json é 1:1 com traceability.json",
                            False, str(exc))
            reporter.record(SUITE, "CHK-SK-012 status verificado tem evidência real", False,
                            "razão ilegível")
            return

        ledger = data.get("tasks") or []
        ids_ledger = {t.get("task_id") for t in ledger}
        ids_trace = {e.get("task_id") for e in trace}
        ok11 = ids_ledger == ids_trace and bool(ids_trace)
        partes = []
        if ids_trace - ids_ledger:
            partes.append(f"no traceability e fora do razão: "
                          f"{', '.join(sorted(ids_trace - ids_ledger)[:8])}")
        if ids_ledger - ids_trace:
            partes.append(f"no razão e fora do traceability: "
                          f"{', '.join(sorted(ids_ledger - ids_trace)[:8])}")
        reporter.record(SUITE, "CHK-SK-011 tasks-progress.json é 1:1 com traceability.json",
                        ok11, " · ".join(partes))

        sem_evidencia = []
        for t in ledger:
            if t.get("status") != "verified":
                continue
            ev = t.get("evidence") or {}
            if not ev.get("command") or ev.get("exit_code") is None:
                sem_evidencia.append(t.get("task_id", "?"))
            elif ev.get("exit_code") != 0:
                sem_evidencia.append(f"{t.get('task_id')} (exit {ev.get('exit_code')})")
        ok12 = not sem_evidencia
        detalhe = "" if ok12 else (
            f"'verified' sem exit code 0 registrado: {', '.join(sem_evidencia[:8])} — "
            f"status afirmado sem prova é a RC-02 da auditoria (`PASS (Simulated)`)"
        )
        reporter.record(SUITE, "CHK-SK-012 status verificado tem evidência real", ok12, detalhe)

    # ── fontes externas ──────────────────────────────────────────────────

    def _ids_do_catalogo_de_regras(self) -> set[str]:
        for rel in ("asis/docs/business-rules-catalog.json",
                    "asis/docs/business-rules.json",
                    "asis/docs/business-rules.md",
                    "tobe/docs/regras-negocio.md"):
            path = self.outputs / rel
            if path.is_file():
                return set(_BR_ID.findall(path.read_text(encoding="utf-8", errors="replace")))
        return set()

    def _ids_de_test_cases(self) -> set[str]:
        for rel in ("tobe/qa/test-cases.md", "qa/test-cases.md", "asis/qa/test-cases.md"):
            path = self.outputs / rel
            if path.is_file():
                return set(_TC_ID.findall(path.read_text(encoding="utf-8", errors="replace")))
        return set()

    def _operacoes_do_openapi(self) -> list[str]:
        """Identidade de cada operação declarada — `operationId` quando existe.

        A esteira inteira referencia operação por `operationId`: o token é
        `api:{operationId}` nos guardrails de `ava-speckit-planning` e
        `ava-speckit-tasks`, e é o que `speckit_wave_manifest.py` extrai do
        contrato. Este check devolvia `METHOD /path`, notação que nenhuma task
        usa — as 19 operações do `nopcommerce-04` apareciam 19/19 "sem task"
        sendo que todas estavam cobertas. Comparação incompatível, não lacuna.

        `METHOD /path` continua sendo o identificador de fallback para operação
        sem `operationId`, que aí é de fato irreferenciável por token.

        Parse textual de propósito: o repo é stdlib-only e não há dependência de
        parser YAML garantida aqui.
        """
        d = self.outputs / "tobe" / "docs" / "openapi"
        if not d.is_dir():
            return []
        operacoes: list[str] = []
        for path in sorted(d.glob("*.yaml")):
            linhas = path.read_text(encoding="utf-8", errors="replace").splitlines()
            dentro_paths = False
            path_atual = None
            pendente: str | None = None   # operação aberta ainda sem operationId
            for linha in linhas:
                if re.match(r"^paths:\s*$", linha):
                    dentro_paths = True
                    continue
                if dentro_paths and re.match(r"^\S", linha):
                    dentro_paths = False
                if not dentro_paths:
                    continue
                m_path = re.match(r"^\s{2}(/\S*):\s*$", linha)
                if m_path:
                    if pendente:
                        operacoes.append(pendente)
                    pendente = None
                    path_atual = m_path.group(1)
                    continue
                m_verb = re.match(r"^\s{4}(" + "|".join(_HTTP_VERBS) + r"):\s*$", linha)
                if m_verb and path_atual:
                    if pendente:
                        operacoes.append(pendente)
                    pendente = f"{m_verb.group(1).upper()} {path_atual}"
                    continue
                m_op = re.match(r"^\s{6}operationId:\s*[\"']?([A-Za-z0-9_.-]+)", linha)
                if m_op and pendente:
                    operacoes.append(m_op.group(1))
                    pendente = None
            if pendente:
                operacoes.append(pendente)
        return operacoes
