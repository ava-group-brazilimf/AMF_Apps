"""
Testes do plano da esteira (ava-pipeline.yaml → pipeline.steps).

Trava a ORDEM DE EXECUÇÃO no CI: a sequência é decisão de processo, não
detalhe de implementação, e regrediu antes por estar espalhada em código.

Roda com o Python do repo:
    python -m pytest tests/tools/test_pipeline_plan.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "shared" / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import agent_registry as reg  # noqa: E402
import pipeline_config  # noqa: E402
import pipeline_plan  # noqa: E402
import ava_pipeline  # noqa: E402
from pipeline_plan import PlanError  # noqa: E402

#: A esteira, na ordem exata acordada. Mudar isto é mudar o processo —
#: o teste existe justamente para que a mudança seja deliberada.
ESTEIRA = [
    ("F1",  "F1", "ava-asis-orchestrator",    "FP"),
    ("F2a", "F2", "ava-tobe-orchestrator",    "SD"),
    ("F2b", "F2", "ava-devops-orchestrator",  "DP"),
    ("F2c", "F2", "ava-qa-orchestrator",      "TPT"),
    ("F3",  "F3", "ava-prototype",            None),
    # F3S — camada de planejamento SpecKit (spec 039). A posição é o contrato:
    # depois do protótipo, que é fonte de `spec-prototype.md`, e antes da
    # codegen, que é quem consome as tasks. Mover isto quebra a causalidade.
    ("F3S", "F3S", "ava-speckit-orchestrator", "SK"),
    ("F4",  "F4", "ava-stack-orchestrator",   "SG"),
    ("F5",  "F5", "ava-devops-orchestrator",  "DE"),
    ("F6",  "F6", "ava-qa-orchestrator",      "QE"),
    ("F8a", "F8", "ava-summary",              "SAS"),
    ("F8b", "F8", "ava-summary-remediation",  None),
    ("F8c", "F8", "ava-summary",              "SV"),
    ("F8d", "F8", "ava-summary",              "SAS"),
]


@pytest.fixture(scope="module")
def cfg():
    return pipeline_config.load_config()


@pytest.fixture(scope="module")
def plan(cfg):
    return pipeline_plan.build_plan(cfg)


# ─── Ordem ───────────────────────────────────────────────────────────────────

def test_ordem_da_esteira_exata(plan):
    """Sequência, etapa, grupo, agente e trigger — item a item."""
    got = [(s.phase, s.group, s.agent, s.trigger) for s in plan]
    assert got == ESTEIRA


def test_nao_ha_f7_na_esteira(plan):
    """F7 (deliverables) não faz parte da esteira executada pelo CLI."""
    assert not [s for s in plan if s.group == "F7"]


def test_etapas_sao_unicas(plan):
    """`phase` é o id endereçável por --phase; duplicata tornaria --phase ambíguo."""
    ids = [s.phase for s in plan]
    assert len(ids) == len(set(ids))


# ─── Coerência com o agent_registry ──────────────────────────────────────────

def test_todo_agente_existe_e_e_despachavel(plan):
    problems = pipeline_plan.validate_plan(plan)
    assert not problems, "plano divergente do agent_registry: " + "; ".join(problems)


def test_spec_path_vem_do_registry(plan):
    """O caminho da spec é resolvido pelo registry, não por heurística de nome.

    O runner antigo procurava por substring em rglob("*.md") e escolhia o maior
    arquivo candidato — podia carregar o agente errado sem avisar.
    """
    for step in plan:
        assert step.spec_path is not None, f"{step.phase}: sem spec_path"
        assert step.spec_path.is_file(), f"{step.phase}: {step.spec_path} não existe"
        assert step.spec_path == REPO_ROOT / reg.get(step.agent)["path"]


def test_divergencia_de_fase_e_intencional(plan):
    """A etapa da esteira NÃO é a fase do módulo — e o validador não pode exigir isso.

    Contrato de processo: aqui F5 é DevOps Execute e F6 é QA Execution, enquanto
    no registry F5 é o módulo qa-agents e F6 é devops-agents. Se um dia alguém
    "alinhar" os dois eixos, este teste denuncia a mudança de semântica.
    """
    por_etapa = {s.phase: s for s in plan}
    assert por_etapa["F5"].agent == "ava-devops-orchestrator"
    assert por_etapa["F6"].agent == "ava-qa-orchestrator"
    assert reg.PHASE_BY_MODULE["qa-agents"] == "F5"
    assert reg.PHASE_BY_MODULE["devops-agents"] == "F6"
    # Os dois eixos divergem de propósito nestas duas etapas:
    assert por_etapa["F5"].registry_phase == "F6"
    assert por_etapa["F6"].registry_phase == "F5"
    # E validate_plan tolera isso — nenhum problema reportado.
    assert not pipeline_plan.validate_plan([por_etapa["F5"], por_etapa["F6"]])


def test_orquestradores_de_dois_momentos_nao_repetem_o_trigger(plan):
    """DevOps e QA rodam duas vezes, em momentos diferentes — triggers diferentes.

    DevOps: DP planeja (F2b), DE executa (F5).
    QA:     TPT planeja (F2c), QE executa (F6).

    Repetir o trigger de planejamento no segundo momento é o defeito que o
    CHANGELOG de 2026-08-05 descreve: com TPT nas duas etapas, a esteira de
    execução do QA (GR→BM→…→PT→RS) nunca era disparada.
    """
    por_agente: dict[str, list[str | None]] = {}
    for s in plan:
        por_agente.setdefault(s.agent, []).append(s.trigger)

    assert por_agente["ava-devops-orchestrator"] == ["DP", "DE"]
    assert por_agente["ava-qa-orchestrator"] == ["TPT", "QE"]


def test_execucao_vem_depois_do_planejamento(plan):
    """Ordem dos momentos: planejar antes de executar, em ambos os orquestradores."""
    pos = {s.phase: i for i, s in enumerate(plan)}
    assert pos["F2b"] < pos["F5"], "DevOps: DP tem de vir antes de DE"
    assert pos["F2c"] < pos["F6"], "QA: TPT tem de vir antes de QE"
    # O gate do QE exige a esteira de código (F4) e o DevOps Momento 2 (F5).
    assert pos["F4"] < pos["F6"] and pos["F5"] < pos["F6"]


def test_orquestradores_batem_com_o_registry(plan):
    """Onde a esteira usa um orquestrador, é o que o registry registra para a fase."""
    for step in plan:
        if step.agent.endswith("-orchestrator"):
            assert step.agent == reg.orchestrator_of(step.registry_phase)


# ─── Seletores ───────────────────────────────────────────────────────────────

def test_phase_casa_grupo_e_etapa(cfg):
    grupo = pipeline_plan.build_plan(cfg, phases=["F2"])
    assert [s.phase for s in grupo] == ["F2a", "F2b", "F2c"]

    etapa = pipeline_plan.build_plan(cfg, phases=["F2b"])
    assert [s.phase for s in etapa] == ["F2b"]
    assert etapa[0].trigger == "DP"


def test_phase_preserva_a_ordem_do_yaml_nao_a_da_digitacao(cfg):
    plan = pipeline_plan.build_plan(cfg, phases=["F8", "F1", "F4"])
    assert [s.phase for s in plan] == ["F1", "F4", "F8a", "F8b", "F8c", "F8d"]


def test_agent_da_esteira_traz_todas_as_etapas_com_seus_triggers(cfg):
    """ava-devops-orchestrator aparece duas vezes, com modos diferentes."""
    plan = pipeline_plan.build_plan(cfg, agent="ava-devops-orchestrator")
    assert [(s.phase, s.trigger) for s in plan] == [("F2b", "DP"), ("F5", "DE")]


def test_agent_fora_da_esteira_vira_passo_avulso(cfg):
    plan = pipeline_plan.build_plan(cfg, agent="ava-asis-inventory")
    assert len(plan) == 1
    assert plan[0].ad_hoc is True
    assert plan[0].trigger is None
    assert plan[0].spec_path.is_file()


def test_agent_desconhecido_reprova(cfg):
    with pytest.raises(PlanError, match="agente desconhecido"):
        pipeline_plan.build_plan(cfg, agent="ava-nao-existe")


def test_from_corta_o_prefixo(cfg):
    plan = pipeline_plan.build_plan(cfg, start_at="F4")
    assert [s.phase for s in plan] == ["F4", "F5", "F6", "F8a", "F8b", "F8c", "F8d"]


def test_phase_sem_correspondencia_reprova(cfg):
    with pytest.raises(PlanError, match="nenhum passo casa"):
        pipeline_plan.build_plan(cfg, phases=["F99"])


# ─── Prompt ──────────────────────────────────────────────────────────────────

def test_formato_do_prompt(plan):
    """Formato idêntico ao do runner original — os orquestradores dependem dele."""
    por_etapa = {s.phase: s for s in plan}
    assert por_etapa["F1"].build_prompt("MeuERP") == \
        "@ava-asis-orchestrator | FP | project: MeuERP"
    assert por_etapa["F3"].build_prompt("MeuERP") == \
        "@ava-prototype project: MeuERP"
    assert por_etapa["F5"].build_prompt("MeuERP") == \
        "@ava-devops-orchestrator | DE | project: MeuERP"


# ─── Degradação ──────────────────────────────────────────────────────────────

def test_sem_steps_reprova_alto():
    """Sem o YAML, falhar é o certo — nunca rodar uma esteira inventada."""
    with pytest.raises(PlanError, match="nenhum passo declarado"):
        pipeline_plan.declared_steps({"steps": []})


def test_passo_incompleto_reprova():
    with pytest.raises(PlanError, match="inválido"):
        pipeline_plan.declared_steps({"steps": [{"phase": "F1"}]})


def test_etapa_duplicada_reprova():
    with pytest.raises(PlanError, match="duplicada"):
        pipeline_plan.declared_steps({"steps": [
            {"phase": "F1", "agent": "a"}, {"phase": "F1", "agent": "b"},
        ]})


# ─── Coerência com o runner de produção ──────────────────────────────────────
# `ava-pipeline-runner-cli.py` mantém a esteira numa lista Python própria, e foi ele
# quem gerou o projeto auditado. Acrescentar uma fase só no `ava-pipeline.yaml`
# deixa o runner de produção rodando a esteira antiga em silêncio — foi
# exatamente o que aconteceu com a F3S até esta verificação.

RUNNER_19 = REPO_ROOT / "ava-pipeline-runner-cli.py"


@pytest.fixture(scope="module")
def runner19():
    if not RUNNER_19.is_file():
        pytest.skip("ava-pipeline-runner-cli.py ausente neste checkout")
    pytest.importorskip("anthropic", reason="motor SDK do runner de produção")
    return _load_module(RUNNER_19, "runner19_sob_teste")


def _load_module(path, name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_runner19_conhece_as_mesmas_fases_do_yaml(runner19, cfg):
    """Toda fase declarada no YAML existe no PIPELINE do runner de produção.

    O runner tem fases extras de propósito (F0 AST, F1a..F1f especializados,
    S1..S4, FC, FP) — o teste é de continência, não de igualdade.
    """
    do_yaml = {s.phase for s in pipeline_plan.declared_steps(cfg)}
    # Fases expandidas pelo fan-out por DAG viram `F3S:constitution`, `F3S:002-w1-orders`…
    # A continência é pelo prefixo antes de `:`.
    do_runner = {s["phase"].split(":")[0] for s in runner19.PIPELINE}
    # F8a..F8d do YAML correspondem a S1..S4 no runner — mapeamento histórico.
    equivalentes = {"F8a", "F8b", "F8c", "F8d"}
    faltando = do_yaml - do_runner - equivalentes
    assert not faltando, (
        f"fase declarada no ava-pipeline.yaml e ausente do runner de produção: "
        f"{sorted(faltando)}. Quem acrescenta uma etapa precisa tocar os dois.")


def test_runner19_roda_a_f3s_entre_o_prototipo_e_a_codegen(runner19):
    fases = [s["phase"] for s in runner19.PIPELINE]
    f3s = [i for i, f in enumerate(fases) if f.startswith("F3S")]
    assert f3s, "a camada de planejamento SpecKit não seria executada"
    assert fases.index("F3") < min(f3s) and max(f3s) < fases.index("F4")


def test_runner19_expande_a_f3s_em_um_despacho_por_agente(runner19, monkeypatch):
    """A primeira execução real rodou a F3S como passo ÚNICO: skill de 8KB (só o
    orquestrador), 68.170 tokens de saída, 26 artefatos numa resposta. Os seis
    corpos de agente nunca entraram em contexto, e a saída divergiu de todos os
    contratos que eles declaram.
    """
    monkeypatch.setattr(
        pipeline_plan.speckit_wave_manifest,
        "build_manifest",
        lambda project, root, **_: {"features": [
            {"feature": "001-w0-foundation", "codegen": False},
            {"feature": "002-w1-orders", "codegen": True},
        ]},
    )
    runtime_pipeline = [dict(step) for step in runner19.PIPELINE]
    runner19._expand_dag_phases(runtime_pipeline, "P")
    f3s = [s for s in runtime_pipeline if s["phase"].startswith("F3S")]
    assert len(f3s) > 1, "F3S como despacho único não carrega os corpos dos sub-agentes"
    agentes = {s["agent"] for s in f3s}
    assert "ava-speckit-constitution" in agentes
    assert "ava-speckit-tasks" in agentes
    assert "ava-speckit-orchestrator" not in agentes, (
        "o orquestrador não deve aparecer como passo — quem executa são os agentes")
    # Toda spec tem o parâmetro que diz ao agente qual fonte lhe cabe
    specs = [s for s in f3s if s["agent"] == "ava-speckit-specification"]
    assert specs and all(s.get("feature") for s in specs)


def test_dag_f3s_materializa_gates_compilador_e_ledger():
    steps = pipeline_plan.dag_steps("F3S")
    tools = [step for step in steps if step.get("kind") == "tool"]
    ids = [step["agent"] for step in tools]

    # Ordem completa das tools da F3S. A lista estava defasada desde que
    # wave4a (plan-validate), wave5b (fragment-repair) e wave6b
    # (compliance-normalize) entraram no DAG, e o teste vinha vermelho — o que
    # deixou o grafo sem guarda justamente enquanto essas waves eram alteradas.
    assert ids == [
        "speckit-entry-gate",
        # Extração estática do protótipo, ANTES do manifesto de waves: é ela que
        # fornece telas, componentes, rotas e tokens ao recorte por wave.
        "speckit-prototype-manifest",
        "speckit-wave-manifest",
        "speckit-plan-validate",
        "f4s-scaffold-inject",
        "speckit-fragment-repair",
        "speckit-task-compile",
        # Confere PRODUÇÃO logo após a consolidação: `compile --warn` saía com 0
        # sem gravar artefato, e o passo ficava verde. Exit code não é prova.
        "speckit-production-gate",
        "speckit-output-reconcile-planning",
        "speckit-ledger-init",
        "speckit-dependency-checks",
        # Cobertura protótipo → tarefa → API → integração → e2e. Passo próprio
        # porque `--suite` do CLI de checks aceita um valor por invocação.
        "speckit-frontend-integration-checks",
        "speckit-compliance-normalize",
        "speckit-output-reconcile-final",
        "speckit-compliance-gate",
        "speckit-exit-gate",
    ]
    assert all(step["command"] for step in tools)
    checks = next(step for step in tools if step["agent"] == "speckit-dependency-checks")
    report_arg = checks["command"][checks["command"].index("--json-out") + 1]
    assert report_arg == "outputs/tobe/speckit/checks-report.json"
    assert not report_arg.startswith("projects/{project}/")

    # O gate de aprovação roda DEPOIS da normalização (precisa do
    # compliance-status.json canônico) e ANTES do gate de saída (a decisão é o
    # que libera a F4). Inverter qualquer um dos dois esvazia o gate.
    assert ids.index("speckit-compliance-normalize") \
        < ids.index("speckit-compliance-gate") < ids.index("speckit-exit-gate")

    # `requires_approval` precisa CHEGAR ao passo: `dag_steps` monta o dict com
    # uma lista fixa de chaves, então uma chave nova no YAML não se propaga
    # sozinha — e sem ela o runner nunca conduz a decisão.
    aprovacao = [step for step in tools if step.get("requires_approval")]
    assert [step["agent"] for step in aprovacao] == ["speckit-compliance-gate"]

    # Toda tool que pode reprovar por qualidade do CONTEÚDO precisa sair com 0,
    # senão o runner a rotula como falha e o achado — que é acionável e está em
    # disco — vira ruído de exit code. Ver a política de degradação em
    # pipeline_runner._degrade_phase.
    por_id = {step["agent"]: step["command"] for step in tools}
    for tool_id in ("speckit-plan-validate", "speckit-fragment-repair",
                    "speckit-task-compile", "speckit-dependency-checks"):
        assert "--warn" in por_id[tool_id], f"{tool_id} precisa de --warn"


def test_dag_f3s_expande_specs_por_wave_e_codegen_por_filtro(monkeypatch):
    monkeypatch.setattr(
        pipeline_plan.speckit_wave_manifest,
        "build_manifest",
        lambda project, root, **_: {"features": [
            {"feature": "001-w0-foundation", "codegen": True},
            {"feature": "002-w1-orders", "codegen": True},
        ]},
    )

    steps = pipeline_plan.dag_steps("F3S", REPO_ROOT, project="P")
    specs = [step for step in steps if step["agent"] == "ava-speckit-specification"]
    plans = [step for step in steps if step["agent"] == "ava-speckit-planning"]
    tasks = [step for step in steps if step["agent"] == "ava-speckit-tasks"]

    assert [step["feature"] for step in specs] == [
        "001-w0-foundation", "002-w1-orders",
    ]
    assert [step["feature"] for step in plans] == [
        "001-w0-foundation", "002-w1-orders",
    ]
    assert [step["feature"] for step in tasks] == [
        "001-w0-foundation", "002-w1-orders",
    ]


def test_expansao_runtime_mantem_manifesto_antes_das_specs(monkeypatch):
    monkeypatch.setattr(
        pipeline_plan.speckit_wave_manifest,
        "build_manifest",
        lambda project, root, **_: {"features": [
            {"feature": "001-w0-foundation", "codegen": False},
            {"feature": "002-w1-orders", "codegen": True},
        ]},
    )
    placeholder = pipeline_plan.Step(
        phase="F3S", group="F3S", agent="ava-speckit-orchestrator",
        trigger="SK", label="SpecKit", foreach={"source": "dag"},
    )

    steps = pipeline_plan.expand_runtime_dag(placeholder, "P")
    agents = [step.agent for step in steps]

    assert agents.index("speckit-wave-manifest") < agents.index("ava-speckit-specification")
    assert agents.index("ava-speckit-specification") < agents.index("ava-speckit-planning")


def test_tool_command_resolve_python_e_project():
    step = pipeline_plan.Step(
        phase="F3S:tool:test", group="F3S", agent="test", trigger=None,
        label="test", kind="tool", command=["{python}", "tool.py", "-p", "{project}"],
    )

    command = ava_pipeline.resolve_tool_command(step, "Meu-ERP")

    assert command[0] == sys.executable
    assert command[1:] == ["tool.py", "-p", "Meu-ERP"]


def test_tool_warning_preserva_exit_code_e_continua(tmp_path, monkeypatch):
    step = pipeline_plan.Step(
        phase="F3S:tool:warning", group="F3S", agent="warning", trigger=None,
        label="warning", kind="tool",
        command=[sys.executable, "-c", "import sys; sys.exit(7)"],
        on_fail="warn",
    )
    monkeypatch.setattr(ava_pipeline, "REPO_ROOT", tmp_path)

    result = ava_pipeline.run_tool_step(step, "P", timeout_s=30)

    assert result["status"] == "warning"
    assert result["exit_code"] == 7
    assert result["on_fail"] == "warn"


def test_dag_propaga_on_fail_ate_o_step_runtime(monkeypatch):
    monkeypatch.setattr(
        pipeline_plan.speckit_wave_manifest,
        "build_manifest",
        lambda project, root, **_: {"features": []},
    )
    placeholder = pipeline_plan.Step(
        phase="F3S", group="F3S", agent="ava-speckit-orchestrator",
        trigger="SK", label="SpecKit", foreach={"source": "dag"},
    )

    steps = pipeline_plan.expand_runtime_dag(placeholder, "P")
    plan_validate = next(step for step in steps if step.agent == "speckit-plan-validate")

    assert plan_validate.on_fail == "warn"


def test_copilot_argv_propaga_feature(plan):
    step = pipeline_plan.Step(
        phase="F3S:planning:001-domain", group="F3S",
        agent="ava-speckit-planning", trigger="GL", label="planning",
        registry_phase="F3S", feature="001-domain",
    )
    route = ava_pipeline.Route(base_url="http://example", via_proxy=False)

    argv = ava_pipeline.copilot_argv(step, "P", route)

    assert argv[-2:] == ["--feature", "001-domain"]


def test_verify_command_rejeita_operador_de_shell():
    with pytest.raises(ValueError, match="operador de shell"):
        ava_pipeline.verification_argv("dotnet build && dotnet test")


def test_verify_command_aceita_script_unico():
    assert ava_pipeline.verification_argv("pwsh -File verify.ps1") == [
        "pwsh", "-File", "verify.ps1",
    ]


def test_runner19_expoe_a_f3s_no_menu_e_no_contrato_de_artefatos(runner19):
    """Antes da seleção do projeto, o menu preserva o placeholder da F3S."""
    assert "F3S" in runner19.PHASE_GROUPS
    fases_do_grupo = runner19.PHASE_GROUPS["F3S"]["phases"]
    assert fases_do_grupo == ["F3S"]
    contrato = runner19.PHASE_ARTIFACT_CONTRACT["F3S"]["required"]
    assert "tobe/speckit/constitution.md" in contrato
    assert "tobe/speckit/traceability.json" in contrato


def test_runner19_recebe_os_manifestos_de_insumo_do_yaml(runner19, cfg):
    """Os manifestos moram no YAML; o runner os anexa por fase, sem copiá-los."""
    declarados = {s.phase for s in pipeline_plan.declared_steps(cfg) if s.inputs}
    anexados = {s["phase"].split(":")[0] for s in runner19.PIPELINE if s.get("inputs")}
    assert declarados <= anexados, (
        f"manifesto declarado no YAML e não anexado no runner: "
        f"{sorted(declarados - anexados)}")
    # A F4 é a exceção declarada: o manifesto dela é FECHADO e VAZIO no runner,
    # porque o contexto é montado por task em `f4_task_context`. O manifesto
    # global existia para garantir que blueprint, protótipo e specs chegassem ao
    # gerador — e chegavam, todos, em TODOS os 218 despachos (659 KB por vez).
    # O invariante que continua valendo ("o protótipo precisa chegar ao coder")
    # é conferido em test_f4_task_context.py, no contexto da task de frontend.
    f4 = next(s for s in runner19.PIPELINE if s["phase"] == "F4")
    assert f4["inputs"]["mandatory"] == [], (
        "a F4 monta contexto por task; um manifesto de fase aqui reintroduz "
        "specs/*/spec.md de todas as features em todo despacho")
    assert f4["inputs"]["floor"] == [], (
        "o piso de contexto da F4 também sai: a task não usa shared-context.md")

    # No YAML o manifesto continua declarado — ele é o que o CLI declarativo
    # estreita por feature (`pipeline_plan._narrow_inputs`).
    f4_yaml = next(s for s in pipeline_plan.declared_steps(cfg) if s.phase == "F4")
    obrigatorios = [i["path"] if isinstance(i, dict) else i
                    for i in f4_yaml.inputs["mandatory"]]
    assert "outputs/tobe/prototype/index.html" in obrigatorios, (
        "o artefato que nunca chegava ao gerador de código precisa ser obrigatório")
    assert "outputs/tobe/speckit/specs/*/spec.md" in obrigatorios, (
        "000-scaffold-{stack} não tem plan.md — spec.md é a única fonte da "
        "árvore de arquivos esperada e precisa chegar ao coder da stack")


def test_toda_fase_do_pipeline_aparece_no_menu(runner19):
    """PIPELINE e PHASE_GROUPS são duas listas que precisam concordar.

    Defeito real: a F4S foi acrescentada ao PIPELINE e esquecida em
    PHASE_GROUPS. Ela executava na esteira completa, mas não aparecia no menu
    de seleção por fase — invisível para quem opera, e impossível de rodar
    isolada. Falha silenciosa da mesma família que `test_runner19_conhece_as_
    mesmas_fases_do_yaml` já cobre para o YAML.
    """
    no_menu = {
        base
        for dados in runner19.PHASE_GROUPS.values()
        for fase in dados["phases"]
        for base in [fase.split(":")[0]]
    }
    no_pipeline = {s["phase"].split(":")[0] for s in runner19.PIPELINE}

    ausentes = sorted(no_pipeline - no_menu)
    assert not ausentes, (
        f"fase(s) no PIPELINE e fora do menu de seleção: {ausentes}. "
        f"Acrescente-a(s) a PHASE_GROUPS — sem isso a fase roda na esteira "
        f"completa mas o operador não consegue selecioná-la.")


def test_runner19_expoe_a_f4s_no_menu(runner19):
    """A fase de scaffold precisa ser selecionável isoladamente.

    É o passo que o operador mais precisa rodar sozinho: para reapresentar o
    gate de aprovação, ou para regerar o baseline sem tocar no resto.
    """
    assert "F4S" in runner19.PHASE_GROUPS
    assert runner19.PHASE_GROUPS["F4S"]["phases"] == ["F4S"]
    rotulo = runner19.PHASE_GROUPS["F4S"]["label"]
    assert "frontend" in rotulo and "backend" in rotulo, (
        "o rótulo precisa dizer a ordem — é a decisão determinística da fase")

    passo = next(s for s in runner19.PIPELINE if s["phase"] == "F4S")
    assert passo["kind"] == "tool", "a F4S é determinística, não um agente"
    assert "scaffold_runner.py" in " ".join(passo["command"])

    # A ordem no PIPELINE importa: scaffold antes do orquestrador de stack.
    ordem = [s["phase"] for s in runner19.PIPELINE]
    assert ordem.index("F4S") < ordem.index("F4")
