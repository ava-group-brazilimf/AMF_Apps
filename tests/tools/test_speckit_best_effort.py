"""F3S consolida planejamento em modo best-effort — defeito semântico não descarta tasks.

O defeito, medido em `cadastro-funcionarios-04`:

`speckit_task_compiler.py compile` levantava `CompilerError` no PRIMEIRO conflito
de ownership (`target_file` com mais de um `action: create`). Havia **31**
conflitos e **218 tasks íntegras** nos fragments. O `except` a jusante abortava a
gravação inteira, então:

* `traceability.json` nunca era escrito;
* `task_ledger --init` não tinha de onde derivar → `tasks-progress.json` idem;
* o reconciler da wave6c cobria os dois buracos com placeholders de recuperação;
* 11 dos 18 checks reprovavam — todos sintoma da mesma causa, nenhum a nomeando.

E `--warn` só trocava o exit code: o passo ficava **verde sem artefato**.

Estes testes cobrem os 12 cenários do contrato da fase. Nenhum depende de
`cadastro-funcionarios-04` — todos montam o projeto do zero.

    python -m pytest tests/tools/test_speckit_best_effort.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "src" / "shared" / "tools"
sys.path.insert(0, str(TOOLS))

import speckit_output_reconciler as reconciler  # noqa: E402
import speckit_production_gate as prod_gate     # noqa: E402
import speckit_task_compiler as compiler        # noqa: E402
import task_ledger                              # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════
#  Construtor de projeto — nada aqui conhece nome de domínio ou de projeto
# ═══════════════════════════════════════════════════════════════════════════

TRACE = "trace-teste-001"


def _wave(indice: int, nome: str, *, codegen: bool = True) -> dict:
    return {"feature": f"{indice:03d}-{nome}", "wave_id": f"W{indice - 1}",
            "wave_order": indice - 1, "codegen": codegen}


class Projeto:
    """Monta um projeto SpecKit mínimo e válido em disco."""

    def __init__(self, raiz: Path, nome: str = "P") -> None:
        self.raiz = raiz
        self.nome = nome
        self.speckit = raiz / "projects" / nome / "outputs" / "tobe" / "speckit"
        self.specs = self.speckit / "specs"
        self.specs.mkdir(parents=True, exist_ok=True)
        (self.speckit / "constitution.md").write_text(
            "# Constituição\n\nP-001 camadas.\n", encoding="utf-8")
        self.features: list[dict] = []

    def feature(self, indice: int, nome: str, arquivos: list[dict], *,
                codegen: bool = True, spec_extra: str = "",
                spec_cita_arquivos: bool = True) -> "Projeto":
        """Adiciona uma feature com plan-graph e task-fragment coerentes.

        `spec_cita_arquivos=False` produz uma spec que NÃO nomeia os arquivos —
        é como se exercita a regra de que a spec é a autoridade para decidir
        ownership disputado.
        """
        meta = _wave(indice, nome, codegen=codegen)
        self.features.append(meta)
        fid = meta["feature"]
        pasta = self.specs / fid
        pasta.mkdir(parents=True, exist_ok=True)

        titulos = ("\n".join(f"## {a['path'].rsplit('/', 1)[-1]}" for a in arquivos)
                   if spec_cita_arquivos else "")
        (pasta / "spec.md").write_text(
            f"# Especificação — {fid}\n\n## Escopo\n{spec_extra}\n{titulos}\n",
            encoding="utf-8")
        if not codegen:
            return self

        grupo = f"G-{indice:03d}"
        files = []
        entries = []
        for pos, arq in enumerate(arquivos, start=1):
            tid = arq.get("task_id") or f"T-{indice:03d}-{pos:03d}"
            refs = [{"artifact": f"outputs/tobe/speckit/specs/{fid}/spec.md",
                     "anchor": "Escopo"}]
            comum = {
                "path": arq["path"], "group": grupo, "action": arq["action"],
                "task_type": "backend", "target_stack": "dotnet",
                "source_refs": refs,
                "produces": arq.get("produces", [f"file:{tid.lower()}"]),
                "consumes": arq.get("consumes", []),
            }
            files.append({**comum, "task_id": tid})
            entries.append({
                "task_id": tid, "title": f"Task {tid}", "group": grupo,
                "task_type": "backend", "target_stack": "dotnet",
                "source_refs": refs, "target_file": arq["path"],
                "action": arq["action"], "depends_on": [], "depends_on_groups": [],
                "produces": comum["produces"], "consumes": comum["consumes"],
                "acceptance": ["compila"], "verify_command": "echo ok",
                "priority": "P1", "story_points": 1,
            })

        cabecalho = {
            "schema_version": "3.0.0", "project": self.nome, "trace_id": TRACE,
            "feature": fid, "spec_id": f"SPEC-{indice:03d}",
            "plan_id": f"PLAN-{indice:03d}",
            "migration_wave_id": meta["wave_id"],
            "migration_wave_order": meta["wave_order"],
        }
        (pasta / "plan.md").write_text(f"# Plano {fid}\n", encoding="utf-8")
        (pasta / "plan-graph.json").write_text(json.dumps({
            **cabecalho,
            "groups": [{"group": grupo, "feature": fid, "target_stack": "dotnet",
                        "depends_on": []}],
            "files": files,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        (pasta / "task-fragment.json").write_text(json.dumps({
            **cabecalho, "entries": entries,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        return self

    def fechar(self) -> "Projeto":
        (self.speckit / "wave-spec-manifest.json").write_text(json.dumps({
            "schema_version": "1.0.0", "project": self.nome, "trace_id": TRACE,
            "features": [
                {"feature": f["feature"], "wave_id": f["wave_id"],
                 "migration_wave_order": f["wave_order"], "codegen": f["codegen"]}
                for f in self.features
            ],
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        return self

    # ── leitura ──────────────────────────────────────────────────────────────
    def traceability(self) -> dict:
        return json.loads((self.speckit / "traceability.json").read_text(encoding="utf-8"))

    def progresso(self) -> dict:
        return json.loads((self.speckit / "tasks-progress.json").read_text(encoding="utf-8"))

    def avisos(self) -> dict:
        return json.loads((self.speckit / "compile-warnings.json").read_text(encoding="utf-8"))


def _f(path: str, action: str = "create", **extra) -> dict:
    return {"path": path, "action": action, **extra}


@pytest.fixture
def projeto(tmp_path: Path) -> Projeto:
    return Projeto(tmp_path)


def _compilar(p: Projeto) -> dict:
    return compiler.compile_project(p.nome, p.raiz, write=True)


# ═══════════════════════════════════════════════════════════════════════════
#  Cenário 1 — dois creates para o mesmo target_file
# ═══════════════════════════════════════════════════════════════════════════

def test_cenario1_create_duplicado_avisa_e_preserva_tudo(projeto: Projeto):
    projeto.feature(1, "foundation", [_f("src/Base.cs"), _f("src/Kernel.cs")]) \
           .feature(2, "core", [_f("src/Base.cs"), _f("src/Servico.cs")]).fechar()

    saida = _compilar(projeto)

    assert saida["total_tasks"] == 4, "task foi descartada por causa do conflito"
    trace = projeto.traceability()
    assert len(trace["entries"]) == 4
    assert trace["recovery_placeholder"] is False
    assert trace["artifacts_written"] is True
    assert trace["status"] == "COMPLETE_WITH_WARNINGS"
    assert trace["validation_summary"]["ownership_conflicts"] >= 1
    assert len(projeto.progresso()["tasks"]) == 4
    assert projeto.avisos()["artifacts_written"] is True


def test_cenario1_exit_code_zero_em_modo_warn(projeto: Projeto, monkeypatch, capsys):
    projeto.feature(1, "foundation", [_f("src/Base.cs")]) \
           .feature(2, "core", [_f("src/Base.cs")]).fechar()
    monkeypatch.setattr(compiler, "REPO_ROOT", projeto.raiz)

    codigo = compiler._main(["compile", "-p", projeto.nome, "--json", "--warn"])
    capsys.readouterr()

    assert codigo == 0
    assert projeto.traceability()["total_tasks"] == 2


# ═══════════════════════════════════════════════════════════════════════════
#  Cenário 2 — create em W0 e update em W3
# ═══════════════════════════════════════════════════════════════════════════

def test_cenario2_update_posterior_nao_e_conflito(projeto: Projeto):
    projeto.feature(1, "foundation", [_f("src/Base.cs")]) \
           .feature(4, "hardening", [_f("src/Base.cs", "update")]).fechar()

    _compilar(projeto)
    trace = projeto.traceability()
    conflitos = [c for c in trace["ownership_conflicts"]
                 if c["code"] == compiler.OWNERSHIP_CREATE_CREATE]

    assert conflitos == [], "update posterior foi tratado como conflito de criação"
    por_id = {e["task_id"]: e for e in trace["entries"]}
    criador = [e for e in por_id.values() if e["action"] == "create"]
    assert len(criador) == 1
    assert criador[0]["feature"] == "001-foundation", "ownership de criação migrou"
    assert any(e["action"] == "update" for e in por_id.values()), "update sumiu"


# ═══════════════════════════════════════════════════════════════════════════
#  Cenário 3 — entidade de negócio criada em duas waves
# ═══════════════════════════════════════════════════════════════════════════

def test_cenario3_spec_decide_o_owner(projeto: Projeto):
    """A spec é a autoridade funcional: quem nomeia o artefato é o dono."""
    # A spec de foundation NÃO nomeia o arquivo; a de core nomeia. É esse sinal
    # — e só ele — que decide o owner. Nada aqui depende do nome do arquivo.
    projeto.feature(1, "foundation", [_f("src/Entidade.cs")],
                    spec_cita_arquivos=False,
                    spec_extra="Entrega apenas abstrações transversais.") \
           .feature(2, "core", [_f("src/Entidade.cs")],
                    spec_extra="Entrega o CRUD da entidade.").fechar()

    _compilar(projeto)
    conflitos = projeto.traceability()["ownership_conflicts"]

    assert len(conflitos) == 1
    assert conflitos[0]["code"] == compiler.OWNERSHIP_SCOPE_VIOLATION
    assert conflitos[0]["recommended_owner"] == "002-core"
    assert projeto.traceability()["total_tasks"] == 2


def test_cenario3_owner_indeterminado_fica_marcado(projeto: Projeto):
    """Sem sinal na spec, o desempate é determinístico E o conflito continua visível."""
    projeto.feature(1, "foundation", [_f("src/X.cs")], spec_cita_arquivos=False) \
           .feature(2, "core", [_f("src/X.cs")], spec_cita_arquivos=False).fechar()

    _compilar(projeto)
    conflito = projeto.traceability()["ownership_conflicts"][0]

    assert conflito["recommended_owner"] == ""
    assert "indeterminado" in conflito["reason"]
    entradas = {e["task_id"]: e for e in projeto.traceability()["entries"]}
    estados = {e.get("ownership_status") for e in entradas.values()}
    assert "CONFLICT" in estados, "o conflito foi resolvido em silêncio"


# ═══════════════════════════════════════════════════════════════════════════
#  Cenário 4 — vários conflitos em arquivos diferentes
# ═══════════════════════════════════════════════════════════════════════════

def test_cenario4_todos_os_conflitos_sao_enumerados(projeto: Projeto):
    arquivos = [_f(f"src/A{i}.cs") for i in range(6)]
    projeto.feature(1, "foundation", arquivos) \
           .feature(2, "core", arquivos).fechar()

    _compilar(projeto)
    trace = projeto.traceability()

    assert len(trace["ownership_conflicts"]) == 6, "parou antes de enumerar tudo"
    assert trace["total_tasks"] == 12, "tasks perdidas"
    assert len(projeto.progresso()["tasks"]) == 12


def test_cenario4_diagnose_enumera_antes_das_tasks(projeto: Projeto):
    """wave4a passa a acusar o defeito onde ele nasce — no plano."""
    arquivos = [_f(f"src/A{i}.cs") for i in range(4)]
    projeto.feature(1, "foundation", arquivos).feature(2, "core", arquivos).fechar()

    relatorio = compiler.diagnose_project(projeto.nome, projeto.raiz, plans_only=True)
    codigos = [f["code"] for f in relatorio["findings"]]

    assert codigos.count(compiler.OWNERSHIP_CROSS_WAVE) == 4
    assert all(f["severity"] == "warning"
               for f in relatorio["findings"]
               if f["code"] == compiler.OWNERSHIP_CROSS_WAVE)


# ═══════════════════════════════════════════════════════════════════════════
#  Cenário 5 — task inválida entre válidas
# ═══════════════════════════════════════════════════════════════════════════

def test_cenario5_entry_ilegivel_nao_derruba_o_razao(projeto: Projeto):
    projeto.feature(1, "foundation", [_f("src/A.cs"), _f("src/B.cs")]).fechar()
    _compilar(projeto)

    trace = projeto.traceability()
    trace["entries"].append({"sem": "task_id"})
    (projeto.speckit / "traceability.json").write_text(
        json.dumps(trace, ensure_ascii=False), encoding="utf-8")

    ledger = task_ledger.init(projeto.nome, projeto.raiz)
    assert len(ledger["tasks"]) == 2
    assert any("task_id" in a for a in ledger["warnings"])


# ═══════════════════════════════════════════════════════════════════════════
#  Cenário 6 — idempotência do traceability
# ═══════════════════════════════════════════════════════════════════════════

def test_cenario6_recompilar_e_deterministico(projeto: Projeto):
    projeto.feature(1, "foundation", [_f("src/A.cs")]) \
           .feature(2, "core", [_f("src/A.cs"), _f("src/B.cs")]).fechar()

    primeiro = _compilar(projeto)
    ids_1 = [e["task_id"] for e in primeiro["entries"]]
    segundo = _compilar(projeto)
    ids_2 = [e["task_id"] for e in segundo["entries"]]

    assert ids_1 == ids_2, "ordem ou ids mudaram entre execuções"
    assert primeiro["graph_checksum"] == segundo["graph_checksum"]
    assert projeto.traceability()["recovery_placeholder"] is False


# ═══════════════════════════════════════════════════════════════════════════
#  Cenário 7 — progresso existente é preservado
# ═══════════════════════════════════════════════════════════════════════════

def test_cenario7_progresso_em_andamento_sobrevive(projeto: Projeto):
    projeto.feature(1, "foundation", [_f("src/A.cs"), _f("src/B.cs")]).fechar()
    _compilar(projeto)

    ledger = projeto.progresso()
    alvo = ledger["tasks"][0]
    alvo.update({"status": "verified", "attempts": 2,
                 "evidence": {"command": "dotnet build", "exit_code": 0},
                 "started_at": "2026-01-01T00:00:00+00:00",
                 "files_written": ["src/A.cs"]})
    task_ledger.save(projeto.nome, ledger, projeto.raiz)

    # Nova feature entra; a task já verificada não pode regredir.
    projeto.feature(2, "core", [_f("src/C.cs")]).fechar()
    _compilar(projeto)

    depois = {t["task_id"]: t for t in projeto.progresso()["tasks"]}
    preservada = depois[alvo["task_id"]]
    assert preservada["status"] == "verified"
    assert preservada["attempts"] == 2
    assert preservada["evidence"]["exit_code"] == 0
    assert preservada["started_at"] == "2026-01-01T00:00:00+00:00"
    assert preservada["files_written"] == ["src/A.cs"]
    novas = [t for t in depois.values() if t["status"] == "pending"]
    assert novas, "a task nova não entrou"


# ═══════════════════════════════════════════════════════════════════════════
#  Cenário 8 — zero tasks legítimo
# ═══════════════════════════════════════════════════════════════════════════

def test_cenario8_lista_vazia_nao_e_placeholder(projeto: Projeto):
    projeto.feature(1, "foundation", []).fechar()

    saida = _compilar(projeto)

    assert saida["total_tasks"] == 0
    trace = projeto.traceability()
    assert trace["recovery_placeholder"] is False
    assert trace["entries"] == []
    assert trace["reason"], "lista vazia sem motivo explícito"
    ledger = projeto.progresso()
    assert ledger["recovery_placeholder"] is False
    assert ledger["tasks"] == []
    assert ledger["reason"]


# ═══════════════════════════════════════════════════════════════════════════
#  Cenário 9 — falha técnica de escrita
# ═══════════════════════════════════════════════════════════════════════════

def test_cenario9_falha_de_escrita_preserva_artefato_anterior(projeto: Projeto,
                                                              monkeypatch, capsys):
    projeto.feature(1, "foundation", [_f("src/A.cs")]).fechar()
    _compilar(projeto)
    bom = (projeto.speckit / "traceability.json").read_text(encoding="utf-8")
    assert json.loads(bom)["total_tasks"] == 1

    def _explode(*a, **k):
        raise OSError("disco cheio")

    monkeypatch.setattr(compiler, "_write_atomic", _explode)
    monkeypatch.setattr(compiler, "REPO_ROOT", projeto.raiz)
    # Falha técnica reprova — pela exceção que o CLI converte em exit != 0, ou
    # por código de retorno. O que NÃO pode acontecer é sair 0.
    try:
        codigo = compiler._main(["compile", "-p", projeto.nome, "--json"])
    except OSError:
        codigo = 1
    capsys.readouterr()

    assert codigo != 0, "falha técnica precisa reprovar"
    # O artefato válido anterior continua íntegro.
    atual = (projeto.speckit / "traceability.json").read_text(encoding="utf-8")
    assert json.loads(atual)["total_tasks"] == 1
    assert json.loads(atual)["recovery_placeholder"] is False


def test_cenario9_projeto_inexistente_reprova(capsys):
    codigo = prod_gate.main(["-p", "projeto-que-nao-existe"])
    capsys.readouterr()
    assert codigo == 2


# ═══════════════════════════════════════════════════════════════════════════
#  Cenário 10 — feature de cutover só com spec.md
# ═══════════════════════════════════════════════════════════════════════════

def test_cenario10_feature_nao_codegen_e_ignorada(projeto: Projeto):
    projeto.feature(1, "foundation", [_f("src/A.cs")]) \
           .feature(5, "cutover", [], codegen=False).fechar()

    saida = _compilar(projeto)

    assert saida["total_tasks"] == 1
    features = {e["feature"] for e in saida["entries"]}
    assert "005-cutover" not in features, "task artificial criada para cutover"
    assert not (projeto.specs / "005-cutover" / "plan-graph.json").exists()


# ═══════════════════════════════════════════════════════════════════════════
#  Cenário 11 — reexecução completa
# ═══════════════════════════════════════════════════════════════════════════

def test_cenario11_reexecucao_nao_perde_progresso_nem_cria_placeholder(projeto: Projeto):
    projeto.feature(1, "foundation", [_f("src/A.cs")]) \
           .feature(2, "core", [_f("src/A.cs"), _f("src/B.cs")]).fechar()
    _compilar(projeto)

    ledger = projeto.progresso()
    ledger["tasks"][0]["status"] = "verified"
    task_ledger.save(projeto.nome, ledger, projeto.raiz)
    conflitos_1 = projeto.traceability()["ownership_conflicts"]

    _compilar(projeto)

    assert projeto.traceability()["ownership_conflicts"] == conflitos_1, \
        "resolução de ownership não é determinística"
    assert projeto.traceability()["recovery_placeholder"] is False
    assert any(t["status"] == "verified" for t in projeto.progresso()["tasks"])


def test_cenario11_gate_de_producao_confirma(projeto: Projeto):
    projeto.feature(1, "foundation", [_f("src/A.cs"), _f("src/B.cs")]).fechar()
    _compilar(projeto)

    veredito = prod_gate.check_production(projeto.nome, projeto.raiz)

    assert veredito["produced"] is True
    assert veredito["problems"] == []
    assert veredito["traceability_entries"] == veredito["progress_tasks"] == 2
    assert veredito["artifacts_written"] is True


def test_gate_de_producao_reprova_placeholder(projeto: Projeto):
    """Exit code não é prova: o gate olha o disco."""
    projeto.feature(1, "foundation", [_f("src/A.cs")]).fechar()
    (projeto.speckit / "traceability.json").write_text(json.dumps({
        "schema_version": "4.0.0", "recovery_placeholder": True,
        "status": "INCOMPLETE", "entries": [],
    }), encoding="utf-8")
    (projeto.speckit / "tasks-progress.json").write_text(json.dumps({
        "schema_version": "3.0.0", "recovery_placeholder": True, "tasks": [],
    }), encoding="utf-8")

    veredito = prod_gate.check_production(projeto.nome, projeto.raiz)

    assert veredito["produced"] is False
    assert any("placeholder" in p for p in veredito["problems"])


# ═══════════════════════════════════════════════════════════════════════════
#  Cenário 12 — feature isolada, sem plans anteriores
# ═══════════════════════════════════════════════════════════════════════════

def test_cenario12_primeira_feature_sem_contexto_anterior(projeto: Projeto):
    projeto.feature(1, "foundation", [_f("src/A.cs")]).fechar()

    relatorio = compiler.diagnose_project(projeto.nome, projeto.raiz, plans_only=True)
    saida = _compilar(projeto)

    assert saida["total_tasks"] == 1
    assert not [f for f in relatorio["findings"]
                if f["code"].startswith("OWNERSHIP") or f["code"].startswith("CREATE")]


def test_cenario12_dag_da_planning_recebe_plans_anteriores():
    """O contexto advisory precisa estar declarado, ou o defeito volta."""
    import yaml
    dag = yaml.safe_load(
        (REPO_ROOT / "src/shared/data/pipeline-dag/F3S.yaml").read_text(encoding="utf-8"))
    planner = next(a for w in dag["waves"] for a in (w.get("agents") or [])
                   if a["id"] == "ava-speckit-planning")
    advisory = planner["inputs"]["advisory"]

    assert any("plan-graph.json" in str(i) for i in advisory), (
        "o planejador voltou a decidir ownership sem ver o que já foi reivindicado")
    # Advisory, nunca mandatory: a primeira feature não tem plano anterior.
    assert not any("plan-graph.json" in str(i)
                   for i in planner["inputs"].get("mandatory") or [])


# ═══════════════════════════════════════════════════════════════════════════
#  Reconciler — não substitui artefato válido, reconstrói placeholder
# ═══════════════════════════════════════════════════════════════════════════

def test_reconciler_nao_troca_artefato_valido_por_placeholder(projeto: Projeto):
    projeto.feature(1, "foundation", [_f("src/A.cs"), _f("src/B.cs")]).fechar()
    _compilar(projeto)
    antes = projeto.traceability()

    reconciler.reconcile(projeto.nome, "final", projeto.raiz)

    depois = projeto.traceability()
    assert depois["recovery_placeholder"] is False
    assert len(depois["entries"]) == len(antes["entries"]) == 2


def test_reconciler_reconstroi_a_partir_dos_fragments(projeto: Projeto):
    """Placeholder antigo + fragments íntegros = reconstrução, não resignação."""
    projeto.feature(1, "foundation", [_f("src/A.cs"), _f("src/B.cs")]).fechar()
    (projeto.speckit / "traceability.json").write_text(json.dumps({
        "schema_version": "recovery-1.0.0", "recovery_placeholder": True,
        "status": "INCOMPLETE", "entries": [],
    }), encoding="utf-8")

    relatorio = reconciler.reconcile(projeto.nome, "final", projeto.raiz)

    assert relatorio["rebuild"]["attempted"] is True
    assert relatorio["rebuild"]["rebuilt"] is True
    assert relatorio["rebuild"]["entries"] == 2
    trace = projeto.traceability()
    assert trace["recovery_placeholder"] is False
    assert len(trace["entries"]) == 2


# ═══════════════════════════════════════════════════════════════════════════
#  Reparo de ownership — reproduzível, conservador, idempotente
# ═══════════════════════════════════════════════════════════════════════════

def test_reparo_converte_so_o_conflito_que_a_spec_resolve(projeto: Projeto):
    import speckit_plan_repair as reparo

    # Decidível: só a spec de core nomeia o arquivo.
    projeto.feature(1, "foundation", [_f("src/Decidivel.cs"), _f("src/Kernel.cs")],
                    spec_cita_arquivos=False) \
           .feature(2, "core", [_f("src/Decidivel.cs")],
                    spec_extra="Entrega Decidivel.cs.",
                    spec_cita_arquivos=False) \
           .feature(3, "outra", [_f("src/Kernel.cs")], spec_cita_arquivos=False) \
           .fechar()

    seco = reparo.repair_ownership(projeto.nome, projeto.raiz, apply=False)

    assert seco["total_convertidos"] == 1, "converteu além do que a spec decide"
    assert seco["total_indecisos"] == 1, "resolveu no escuro um owner indeterminado"
    assert seco["conversoes"][0]["owner"] == "002-core"
    assert seco["conversoes"][0]["feature"] == "001-foundation"
    # Dry-run não toca no disco.
    plano = json.loads((projeto.specs / "001-foundation" / "plan-graph.json")
                       .read_text(encoding="utf-8"))
    assert all(f["action"] == "create" for f in plano["files"])


def test_reparo_aplicado_e_idempotente(projeto: Projeto):
    import speckit_plan_repair as reparo

    projeto.feature(1, "foundation", [_f("src/X.cs")], spec_cita_arquivos=False) \
           .feature(2, "core", [_f("src/X.cs")], spec_extra="Entrega X.cs.",
                    spec_cita_arquivos=False).fechar()

    primeiro = reparo.repair_ownership(projeto.nome, projeto.raiz, apply=True)
    segundo = reparo.repair_ownership(projeto.nome, projeto.raiz, apply=True)

    assert primeiro["total_convertidos"] == 1
    assert segundo["total_convertidos"] == 0, "reparo não convergiu"

    # Plano e fragment ficam coerentes — o compilador cruza os dois.
    for nome in ("plan-graph.json", "task-fragment.json"):
        dados = json.loads((projeto.specs / "001-foundation" / nome)
                           .read_text(encoding="utf-8"))
        itens = dados.get("files") or dados.get("entries")
        assert all(i["action"] == "update" for i in itens), nome

    _compilar(projeto)
    conflitos = projeto.traceability()["ownership_conflicts"]
    assert not [c for c in conflitos
                if c["code"] in (compiler.OWNERSHIP_CREATE_CREATE,
                                 compiler.OWNERSHIP_SCOPE_VIOLATION)]
    assert projeto.traceability()["total_tasks"] == 2


def test_reparo_nao_toca_owner_indeterminado(projeto: Projeto):
    """§3.5: decisão determinística não pode virar correção silenciosa no dado."""
    import speckit_plan_repair as reparo

    projeto.feature(1, "foundation", [_f("src/Y.cs")], spec_cita_arquivos=False) \
           .feature(2, "core", [_f("src/Y.cs")], spec_cita_arquivos=False).fechar()

    resultado = reparo.repair_ownership(projeto.nome, projeto.raiz, apply=True)

    assert resultado["total_convertidos"] == 0
    assert resultado["total_indecisos"] == 1
    for feat in ("001-foundation", "002-core"):
        plano = json.loads((projeto.specs / feat / "plan-graph.json")
                           .read_text(encoding="utf-8"))
        assert plano["files"][0]["action"] == "create", "dado alterado sem decisão"


# ═══════════════════════════════════════════════════════════════════════════
#  F3S é planejamento — não compila código
# ═══════════════════════════════════════════════════════════════════════════

def test_f3s_nao_compila_codigo_da_aplicacao():
    """Nenhum nó da F3S invoca toolchain de build."""
    import yaml
    dag = yaml.safe_load(
        (REPO_ROOT / "src/shared/data/pipeline-dag/F3S.yaml").read_text(encoding="utf-8"))
    toolchain = ("dotnet", "msbuild", "npm", "yarn", "ng", "tsc", "mvn", "gradle")
    for wave in dag["waves"]:
        for tool in wave.get("tools") or []:
            executavel = Path(str(tool["command"][1])).name.lower()
            assert not any(executavel.startswith(t) for t in toolchain), (
                f"{tool['id']} invoca toolchain de build na F3S: {tool['command']}")


def test_compilador_documenta_que_nao_compila_codigo():
    fonte = (TOOLS / "speckit_task_compiler.py").read_text(encoding="utf-8")
    cabecalho = fonte[:fonte.index('"""', fonte.index('"""') + 3)]
    assert "nao compila codigo" in cabecalho.lower() or \
           "não compila código" in cabecalho.lower()
