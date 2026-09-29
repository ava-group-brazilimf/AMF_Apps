"""
suites/prototype_coverage.py
============================
Verifica que cada tela, rota, formulário, token e endpoint do protótipo navegável
(F3) chegou à especificação e virou trabalho rastreável antes da geração de
código (F4).

O gate que faltava
------------------
Causa-raiz **RC-04** da auditoria de ``nopcommerce-02-cli-ava``, verbatim:

    "O agente de protótipo produziu design-tokens.json + screen-list.md + 15
    telas HTML, mas o agente ava-stack-angular-frontend não consome nenhum
    desses três artefatos como entrada obrigatória (...) Falta um *gate* na
    esteira que valide '1 rota Angular por linha do screen-list.md' e 'tokens
    do design-tokens.json materializados em styles.scss'."

Resultado medido sem esse gate: **7 de 15 telas ausentes**, apenas 2 fiéis
(13%), catálogo B2C entregue como tabela administrativa, `design-tokens.json`
não referenciado por nenhum arquivo do frontend.

Esta suíte é o gate pedido. Ela roda sobre a `spec-prototype.md` e a
rastreabilidade — antes da F4 começar, não depois da entrega.

Checks aplicados
  CHK-PROTO-001  toda tela `included` do screen-list.md está no spec-prototype.md
  CHK-PROTO-002  toda <section class="screen"> do index.html está inventariada
  CHK-PROTO-003  toda tela tem rota, >= 1 task e >= 1 cenário de teste
  CHK-PROTO-004  todo formulário do protótipo tem spec de validação e task
  CHK-PROTO-005  toda chave de design-tokens.json está mapeada na spec
  CHK-PROTO-006  todo endpoint declarado existe no contrato OpenAPI
  CHK-PROTO-007  os warnings do screen-list.md foram propagados para a spec

Uso (standalone):
    python -m src.shared.checks --project Meu-ERP --suite prototype_coverage
"""
from __future__ import annotations

import json
import re
import unicodedata
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.shared.checks.context import CheckContext
    from src.shared.checks.reporter import Reporter

SUITE = "prototype_coverage"

#: `<section class="screen ..." id="screen-cart">`
_SCREEN_SECTION = re.compile(r'<section[^>]*\bid="(screen-[a-z0-9-]+)"', re.IGNORECASE)

#: `<form ...>` e `id`/`name` do formulário
_FORM_TAG = re.compile(r"<form\b[^>]*>", re.IGNORECASE)
_FORM_ID = re.compile(r'\b(?:id|name)="([^"]+)"', re.IGNORECASE)

#: Heading que separa os warnings do inventário no screen-list.md (P2C §2.1)
_SCREEN_LIST_HEADING = re.compile(r"^#\s+Prototype Screen List\s*$", re.MULTILINE)

#: Base path declarado em `servers.url` do OpenAPI — ex.: https://host/api/v1 → /api/v1
_SERVER_BASE = re.compile(r"^\s*-?\s*url:\s*[\"']?https?://[^/\s\"']+(/[^\s\"']*)", re.MULTILINE)

_HTTP_VERBS = ("get", "post", "put", "patch", "delete", "head", "options")
_ENDPOINT = re.compile(
    r"\b(" + "|".join(v.upper() for v in _HTTP_VERBS) + r")\s+(/[A-Za-z0-9_\-/{}.]*)")


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip().lower()


def _kebab(text: str) -> str:
    base = _norm(text)
    base = re.sub(r"[^a-z0-9]+", "-", base)
    return base.strip("-")


class PrototypeCoverageSuite:
    """CHK-PROTO-001..007 — o gate que a RC-04 pediu."""

    def __init__(self, ctx: "CheckContext") -> None:
        self.ctx = ctx
        self.proto = ctx.outputs_dir / "tobe" / "prototype"
        self.speckit = ctx.outputs_dir / "tobe" / "speckit"
        self.spec_paths = self._find_prototype_specs()

    # ── entrada ──────────────────────────────────────────────────────────

    def run(self, reporter: "Reporter") -> None:
        if not self.proto.is_dir():
            reporter.record(SUITE, "CHK-PROTO-000 protótipo existe", True,
                            f"{self.proto} ausente — projeto sem F3, checks não aplicáveis")
            return
        if not self.spec_paths:
            reporter.record(
                SUITE, "CHK-PROTO-000 spec-prototype.md existe", False,
                "nenhuma spec de wave referencia o protótipo. O protótipo tem telas mas "
                "nenhuma virou "
                f"especificação — é exatamente o estado que produziu 7 telas faltando e "
                f"13% de fidelidade. Rode a F3S.")
            return

        spec = "\n\n".join(
            path.read_text(encoding="utf-8", errors="replace") for path in self.spec_paths
        )
        spec_norm = _norm(spec)
        telas_lista, warnings = self._parse_screen_list()
        telas_html = self._parse_index_html()
        trace = self._load_traceability()

        self._chk_001(reporter, telas_lista, spec_norm)
        self._chk_002(reporter, telas_html, spec_norm)
        self._chk_003(reporter, telas_lista, telas_html, spec, trace)
        self._chk_004(reporter, spec_norm, trace)
        self._chk_005(reporter, spec_norm)
        self._chk_006(reporter, spec)
        self._chk_007(reporter, warnings, spec_norm)

    # ── parsing das fontes ───────────────────────────────────────────────

    def _find_prototype_specs(self) -> list[Path]:
        """Localiza todas as specs de wave que receberam fatias do protótipo."""
        d = self.speckit / "specs"
        manifest_path = self.speckit / "wave-spec-manifest.json"
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                manifest = {}
            paths = []
            for feature in manifest.get("features") or []:
                sources = feature.get("sources") or []
                if any(source.get("source_id") == "prototype" for source in sources):
                    path = d / str(feature.get("feature")) / "spec.md"
                    if path.is_file():
                        paths.append(path)
            if paths:
                return paths
        if d.is_dir():
            for pasta in sorted(d.iterdir()):
                if pasta.is_dir() and pasta.name.endswith("-prototype"):
                    path = pasta / "spec.md"
                    return [path] if path.is_file() else []
        return []

    def _parse_screen_list(self) -> tuple[list[dict[str, str]], list[str]]:
        """Inventário de telas do `screen-list.md`.

        A tabela é localizada **pelo conteúdo do cabeçalho** — a primeira que
        tenha simultaneamente `Screen` e `Status`. É a regra defensiva que o
        próprio P2C §2.1 prescreve, e ela é a estratégia primária aqui, não o
        fallback: o arquivo real gerado pelo `ava-prototype` põe o H1
        `# Prototype Screen List` na **primeira linha** e a seção `## Warnings`
        **depois** dele. Fatiar pelo H1 fazia a tabela de warnings ser lida como
        inventário, e 15 telas válidas viravam "nenhuma tela `included`".

        Colunas indexadas pelo NOME do cabeçalho — a coluna opcional
        `api_source` desloca todas as demais.
        """
        path = self.proto / "screen-list.md"
        if not path.is_file():
            return [], []
        texto = path.read_text(encoding="utf-8", errors="replace")

        tabelas = self._tabelas_markdown(texto)
        inventario = next((t for t in tabelas
                           if ("screen" in t["colunas"] or "tela" in t["colunas"])
                           and "status" in t["colunas"]), None)

        warnings = [" | ".join(l) for t in tabelas if t is not inventario
                    for l in t["linhas"]]

        if inventario is None:
            return [], warnings

        telas: list[dict[str, str]] = []
        for celulas in inventario["linhas"]:
            row = dict(zip(inventario["colunas"], celulas))
            nome = (row.get("screen") or row.get("tela") or "").strip("`")
            if not nome:
                continue
            status = _norm(row.get("status", "").split("—")[0].split(" - ")[0]).split(" ")[0]
            telas.append({
                "name": nome,
                "screen_id": f"screen-{_kebab(nome)}",
                "status": status if status in {"included", "excluded", "deferred"} else "deferred",
                "api": row.get("api endpoint") or row.get("api") or "",
            })
        return telas, warnings

    @staticmethod
    def _sem_base(path: str, bases: list[str]) -> str:
        """Remove o base path do servidor, para comparar com os paths do contrato."""
        for base in bases:
            b = base.rstrip("/")
            if b and path.startswith(b + "/"):
                return path[len(b):]
        return path

    @staticmethod
    def _tabelas_markdown(texto: str) -> list[dict]:
        """Todas as tabelas do documento, com colunas normalizadas."""
        tabelas: list[dict] = []
        atual: dict | None = None
        for linha in texto.splitlines():
            crua = linha.strip()
            if not crua.startswith("|"):
                atual = None
                continue
            celulas = [c.strip() for c in crua.strip("|").split("|")]
            if set("".join(celulas)) <= set("-: "):
                continue  # linha separadora
            if atual is None:
                atual = {"colunas": [_norm(c) for c in celulas], "linhas": []}
                tabelas.append(atual)
            elif len(celulas) == len(atual["colunas"]):
                atual["linhas"].append(celulas)
        return tabelas

    def _parse_index_html(self) -> list[str]:
        path = self.proto / "index.html"
        if not path.is_file():
            return []
        texto = path.read_text(encoding="utf-8", errors="replace")
        vistos: list[str] = []
        for sid in _SCREEN_SECTION.findall(texto):
            if sid not in vistos:
                vistos.append(sid)
        return vistos

    def _load_traceability(self) -> list[dict[str, Any]]:
        path = self.speckit / "traceability.json"
        if not path.is_file():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        entries = data.get("entries") if isinstance(data, dict) else data
        return entries if isinstance(entries, list) else []

    # ── checks ───────────────────────────────────────────────────────────

    def _chk_001(self, reporter: "Reporter", telas: list[dict[str, str]],
                 spec_norm: str) -> None:
        incluidas = [t for t in telas if t["status"] == "included"]
        if not incluidas:
            reporter.record(SUITE, "CHK-PROTO-001 toda tela `included` está na spec", False,
                            "screen-list.md não declarou nenhuma tela `included`")
            return
        faltando = [t["name"] for t in incluidas
                    if _norm(t["name"]) not in spec_norm and t["screen_id"] not in spec_norm]
        ok = not faltando
        reporter.record(
            SUITE, "CHK-PROTO-001 toda tela `included` está na spec", ok,
            "" if ok else (
                f"{len(faltando)}/{len(incluidas)} ausentes de spec-prototype.md: "
                f"{', '.join(faltando[:10])} — omitir tela da spec é o mecanismo exato que "
                f"deixou 7 de 15 telas fora do código gerado"))

    def _chk_002(self, reporter: "Reporter", telas_html: list[str], spec_norm: str) -> None:
        if not telas_html:
            reporter.record(SUITE, "CHK-PROTO-002 toda <section class=screen> inventariada",
                            True, "index.html sem seções de tela — check não aplicável")
            return
        faltando = [sid for sid in telas_html if sid not in spec_norm]
        ok = not faltando
        reporter.record(
            SUITE, "CHK-PROTO-002 toda <section class=screen> inventariada", ok,
            "" if ok else f"{len(faltando)}/{len(telas_html)} sem menção na spec: "
                          f"{', '.join(faltando[:10])}")

    def _chk_003(self, reporter: "Reporter", telas: list[dict[str, str]],
                 telas_html: list[str], spec: str, trace: list[dict[str, Any]]) -> None:
        alvo = [t["screen_id"] for t in telas if t["status"] == "included"] or telas_html
        if not alvo:
            reporter.record(SUITE, "CHK-PROTO-003 tela tem rota, task e cenário de teste",
                            False, "nenhuma tela identificada")
            return

        com_task = {e.get("screen_id") for e in trace if e.get("screen_id")}
        com_teste = {e.get("screen_id") for e in trace
                     if e.get("screen_id") and (e.get("test_ids") or [])}
        spec_norm = _norm(spec)

        sem_rota, sem_task, sem_teste = [], [], []
        for sid in alvo:
            bloco = self._bloco_da_tela(spec, sid)
            if not re.search(r"(?im)^\s*\|?\s*rota\s*\|", bloco) and "/" not in bloco:
                sem_rota.append(sid)
            if sid not in com_task:
                sem_task.append(sid)
            if sid not in com_teste:
                sem_teste.append(sid)

        ok = not (sem_rota or sem_task or sem_teste)
        partes = []
        if sem_rota:
            partes.append(f"sem rota: {', '.join(sem_rota[:6])}")
        if sem_task:
            partes.append(f"sem task rastreada: {', '.join(sem_task[:6])}")
        if sem_teste:
            partes.append(f"sem cenário de teste: {', '.join(sem_teste[:6])}")
        _ = spec_norm
        reporter.record(SUITE, "CHK-PROTO-003 tela tem rota, task e cenário de teste", ok,
                        " · ".join(partes))

    def _chk_004(self, reporter: "Reporter", spec_norm: str,
                 trace: list[dict[str, Any]]) -> None:
        path = self.proto / "index.html"
        if not path.is_file():
            reporter.record(SUITE, "CHK-PROTO-004 formulário tem validação e task", True,
                            "index.html ausente — check não aplicável")
            return
        html = path.read_text(encoding="utf-8", errors="replace")
        formularios: list[str] = []
        for tag in _FORM_TAG.findall(html):
            m = _FORM_ID.search(tag)
            if m and m.group(1) not in formularios:
                formularios.append(m.group(1))
        if not formularios:
            reporter.record(SUITE, "CHK-PROTO-004 formulário tem validação e task", True,
                            "nenhum <form> identificável no protótipo")
            return

        tem_secao = "validacao" in spec_norm or "validação" in _norm(spec_norm)
        faltando = [f for f in formularios if _norm(f) not in spec_norm]
        tarefas_frontend = [e for e in trace if e.get("screen_id")]
        ok = tem_secao and not faltando and bool(tarefas_frontend)
        partes = []
        if not tem_secao:
            partes.append("spec sem seção de validação de formulários")
        if faltando:
            partes.append(f"formulário sem spec: {', '.join(faltando[:8])}")
        if not tarefas_frontend:
            partes.append("nenhuma task de frontend rastreada a uma tela")
        reporter.record(SUITE, "CHK-PROTO-004 formulário tem validação e task", ok,
                        " · ".join(partes))

    def _chk_005(self, reporter: "Reporter", spec_norm: str) -> None:
        path = self.proto / "design-tokens.json"
        if not path.is_file():
            reporter.record(SUITE, "CHK-PROTO-005 token mapeado na spec", True,
                            "design-tokens.json ausente — check não aplicável")
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            reporter.record(SUITE, "CHK-PROTO-005 token mapeado na spec", False,
                            f"design-tokens.json ilegível: {exc}")
            return

        chaves: list[str] = []
        for grupo, valores in (data or {}).items():
            if isinstance(valores, dict):
                chaves.extend(f"{grupo}.{k}" for k in valores)
        if not chaves:
            reporter.record(SUITE, "CHK-PROTO-005 token mapeado na spec", True,
                            "nenhum token declarado")
            return

        faltando = [c for c in chaves if _norm(c.split(".")[-1]) not in spec_norm]
        ok = not faltando
        reporter.record(
            SUITE, "CHK-PROTO-005 token mapeado na spec", ok,
            "" if ok else (
                f"{len(faltando)}/{len(chaves)} tokens sem alvo na spec: "
                f"{', '.join(faltando[:10])} — o frontend auditado não referenciou "
                f"design-tokens.json em nenhum arquivo"))

    def _chk_006(self, reporter: "Reporter", spec: str) -> None:
        contratos = sorted((self.ctx.outputs_dir / "tobe" / "docs" / "openapi").glob("*.yaml")) \
            if (self.ctx.outputs_dir / "tobe" / "docs" / "openapi").is_dir() else []
        if not contratos:
            reporter.record(SUITE, "CHK-PROTO-006 endpoint existe no contrato OpenAPI", True,
                            "nenhum contrato OpenAPI — check não aplicável")
            return
        blob = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in contratos)
        # O contrato declara os paths relativos ao `servers.url`. A spec escreve o
        # path completo, com o base path. Comparar cru dava 17/17 falsos positivos
        # em endpoints corretos — o defeito era do check, não da spec.
        bases = sorted({m for m in _SERVER_BASE.findall(blob) if m}, key=len, reverse=True)
        declarados = {f"{v} {self._sem_base(p, bases)}" for v, p in _ENDPOINT.findall(spec)}
        if not declarados:
            reporter.record(SUITE, "CHK-PROTO-006 endpoint existe no contrato OpenAPI", False,
                            "spec-prototype.md não declara nenhum endpoint — a seção de "
                            "integração de API é obrigatória")
            return
        ausentes = [op for op in sorted(declarados) if op.split(" ", 1)[1] not in blob]
        ok = not ausentes
        reporter.record(
            SUITE, "CHK-PROTO-006 endpoint existe no contrato OpenAPI", ok,
            "" if ok else (
                f"{len(ausentes)}/{len(declarados)} fora do contrato: "
                f"{', '.join(ausentes[:10])} — o contrato vence; registre a divergência "
                f"na spec em vez de propagá-la para o código"))

    def _chk_007(self, reporter: "Reporter", warnings: list[str], spec_norm: str) -> None:
        if not warnings:
            reporter.record(SUITE, "CHK-PROTO-007 warnings da fonte propagados", True,
                            "screen-list.md não trouxe seção de warnings")
            return
        nao_propagados = []
        for w in warnings:
            alvo = re.findall(r"`([^`]+)`", w)
            marcador = _norm(alvo[0]) if alvo else _norm(w)[:40]
            if marcador and marcador not in spec_norm:
                nao_propagados.append(marcador)
        ok = not nao_propagados
        reporter.record(
            SUITE, "CHK-PROTO-007 warnings da fonte propagados", ok,
            "" if ok else (
                f"não reemitidos em spec-prototype.md: {', '.join(nao_propagados[:6])} — "
                f"o motivo da qualidade reduzida precisa sobreviver de F3 até F4"))

    # ── util ─────────────────────────────────────────────────────────────

    @staticmethod
    def _bloco_da_tela(spec: str, screen_id: str) -> str:
        """Trecho da spec entre a menção da tela e o próximo heading de tela."""
        i = spec.find(screen_id)
        if i < 0:
            return ""
        resto = spec[i:]
        m = re.search(r"\n####\s", resto[1:])
        return resto[: m.start() + 1] if m else resto[:4000]
