Ready for review
Select text to add comments on the plan
Plano: novo artefato 09_test_coverage.json — detecção de cobertura de testes
Contexto
O pipeline hoje extrai 8 artefatos JSON de um legado Delphi via dois caminhos paralelos: AST real (src/ast_bridge.py → binário ava_ast_cli.exe → XML → IR normalizada) e fallback regex (src/regex_extractors.py, usado por arquivo quando o AST falha/está indisponível), orquestrados em src/delphi_ast_analyzer.py::analyze(). O usuário quer um 9º artefato, 09_test_coverage.json, atuando como "especialista em teste de código": mapear se o legado tem testes automatizados (DUnit/DUnitX), preferindo detecção via AST real e caindo pra regex só onde o AST não cobre — incluindo artefatos auxiliares (scripts manuais, configs de runner, CI/CD, dados de teste) que nunca passam por AST, pois não são código Delphi.

Investigação prévia (compilando snippets reais com ava_ast_cli.exe) confirmou:

[TestFixture]/[Test] são parseados pelo DelphiAST como <ATTRIBUTES><ATTRIBUTE><NAME value="..."/></ATTRIBUTE></ATTRIBUTES>, mas emitidos como irmão anterior (não filho) do <TYPEDECL>/<METHOD> que decoram — sem id/ref de ligação. Hoje zero plumbing pra isso em ast_bridge.py.
published é uma tag XML distinta (<PUBLISHED visibility="true">, igual a PRIVATE/PUBLIC), mas o loop atual de métodos (root.iter("METHOD")) achata a árvore e perde essa ancestralidade — hoje nenhum método carrega visibilidade na IR.
Herança de classe (classes[].parent) já está capturada (adicionado nesta sessão, A6) — checar parent in {"TTestCase", ...} é filtro Python puro, zero plumbing novo.
uses hoje é só nome de unit, sem linha — não alterar esse campo (quebraria integrations_from_ir() e outros consumidores); linha de uses TestFramework/DUnitX precisa de um re-scan dedicado.
Nota: um agente de design levantou a suspeita de que delphi_ast_analyzer.py/ regex_extractors.py estariam "desatualizados" (arquitetura antiga). Verifiquei diretamente e isso é falso — os arquivos já têm a arquitetura completa IR/irs/regex_pas/_assign_ids/ast_mode (linhas 224-338 de delphi_ast_analyzer.py, confirmado agora). Descartar essa alegação; o resto do design abaixo já foi corrigido/validado contra o código real.

Requisito exato do usuário
Detecção em .pas (AST primeiro, regex só onde o AST não cobre):

Nome de arquivo: *Test*.pas, *Spec*.pas, *Tests.pas, DUnit*.pas, *TestCase*.pas, *_test.pas
uses TestFramework, uses DUnitX
Atributos [TestFixture], [Test]
published procedure Test*
Artefatos auxiliares (nunca são código Delphi — sempre regex/glob):

Categoria	Padrões	Label
Scripts de teste manual	*test*.txt, *test*.docx, *test*.xls, *test*.xlsx, *roteiro*.md	"Manual — Documented"
Configs de runner	*.dunitx, *.testrunner, TestInsight*.ini, *.nunit, *.runsettings	"Runner Config"
CI/CD com stage de teste	*.yml, *.yaml, Jenkinsfile, *.ps1 (só se conteúdo tiver "test" ou "dunit", case-insensitive)	"CI Test Stage"
Dados de teste	*fixture*.*, *mock*.*, *testdata*.*, *seed*.*	"Test Data"
Implementação
1. src/ast_bridge.py — plumbing novo (nada disso existe hoje)
Duas novas funções privadas de varredura de árvore (mesmo estilo _a/_int já existentes), chamadas uma vez cada dentro de normalize_ast():

_VIS_TAGS = {"PRIVATE": "private", "PROTECTED": "protected",
             "STRICTPRIVATE": "strict_private", "STRICTPROTECTED": "strict_protected",
             "PUBLIC": "public", "PUBLISHED": "published"}
TEST_FRAMEWORK_UNITS = {"testframework", "dunitx", "dunitx.testframework", "dunit"}
TEST_FIXTURE_BASE_CLASSES = {"ttestcase", "tdunitxtestfixture"}

def _index_attributes(root: ET.Element) -> dict[int, list[str]]:
    """id(TYPEDECL|METHOD) -> [nomes de atributo]. ATTRIBUTES é irmão anterior
    do alvo no mesmo pai — sem id/ref. Precisa de varredura posicional
    (list(node), não .iter(), que perde a ordem entre irmãos)."""
    by_target: dict[int, list[str]] = {}
    def walk(node):
        pending = []
        for child in list(node):
            if child.tag == "ATTRIBUTES":
                pending = [_a(n, "value") for n in child.iter("NAME") if _a(n, "value")]
            elif child.tag in ("TYPEDECL", "METHOD"):
                if pending:
                    by_target[id(child)] = pending
                pending = []
            else:
                pending = []
            walk(child)
    walk(root)
    return by_target

def _index_visibility(root: ET.Element) -> dict[int, str]:
    """id(METHOD) -> 'private'|'public'|'published'|... — ElementTree não tem
    .getparent(), então propaga a visibilidade atual descendo pela árvore."""
    by_method: dict[int, str] = {}
    def walk(node, current):
        for child in list(node):
            nxt = _VIS_TAGS.get(child.tag, current)
            if child.tag == "METHOD" and current:
                by_method[id(child)] = current
            walk(child, nxt)
    walk(root, None)
    return by_method

def _test_framework_uses(root: ET.Element) -> list[dict]:
    """Re-scan dedicado de USES/UNIT só p/ frameworks de teste — não mexe no
    campo `uses` existente (que outros consumidores esperam como set de strings)."""
    hits = []
    for us in root.iter("USES"):
        for u in us.iter("UNIT"):
            name = _a(u, "name")
            if name and name.lower() in TEST_FRAMEWORK_UNITS:
                hits.append({"name": name, "line": _int(u, "line")})
    return hits
Decisão de forma da IR — enriquecer em vez de criar estrutura paralela: adicionar campos opcionais aos dicts já existentes de classes/methods (dict access em Python não quebra com chaves extras — procs_from_ir()/ overview_from_ir() continuam funcionando sem alteração):

classes[i]: adicionar "attributes": attrs_idx.get(id(td), []).
methods[i]: adicionar "visibility": vis_idx.get(id(m)) e "attributes": attrs_idx.get(id(m), []).
Novo campo de nível superior na IR (ao lado de uses/classes/methods): "test_uses": _test_framework_uses(root).
Hook point: logo após o cálculo de uses = ... em normalize_ast(), chamar attrs_idx = _index_attributes(root) e vis_idx = _index_visibility(root) uma vez cada; usar nos loops existentes de classes e methods.

2. src/regex_extractors.py — fallback regex
Checagem de nome de arquivo — helper único, aplicado a TODOS os .pas (tanto os que foram parseados via AST quanto os que caíram em fallback, já que é só nome de arquivo):

import fnmatch
TEST_FILENAME_PATTERNS = ["*test*.pas", "*spec*.pas", "*tests.pas",
                           "dunit*.pas", "*testcase*.pas", "*_test.pas"]

def is_test_filename(path: Path) -> bool:
    name = path.name.lower()
    return any(fnmatch.fnmatch(name, pat) for pat in TEST_FILENAME_PATTERNS)
Fallback regex para .pas sem AST — nova função, mesma convenção das outras ({"counts":..., "<key>": [...]}, source_ref{file,line}); reaproveita o CLASS_DECL_RE já existente (de A6 desta sessão) pra herança de classe:

TEST_FRAMEWORK_UNIT_RE = re.compile(r"\b(TestFramework|DUnitX(?:\.TestFramework)?|DUnit)\b", re.I)
TEST_ATTRIBUTE_RE = re.compile(r"^\s*\[\s*(TestFixture|Test|TestCase)\b[^\]]*\]", re.I | re.M)
PUBLISHED_BLOCK_RE = re.compile(
    r"\bpublished\b(.*?)(?=\b(?:strict\s+private|strict\s+protected|private|protected|public|published)\b|end\s*;)",
    re.I | re.S)
PUBLISHED_TEST_METHOD_RE = re.compile(r"\bprocedure\s+(Test\w*)\s*;", re.I)

def extract_test_coverage(files: list[tuple[Path, str]]) -> dict[str, Any]:
    findings = []
    for path, src in files:
        clean = strip_comments(src)
        for m in TEST_FRAMEWORK_UNIT_RE.finditer(clean):
            findings.append({"kind": "framework_uses", "name": m.group(1), "detected_via": "regex",
                             "source_ref": {"file": path.name, "line": line_of(clean, m.start())}})
        for m in CLASS_DECL_RE.finditer(clean):
            if (m.group(2) or "").lower() in TEST_FIXTURE_BASE_CLASSES_STR:  # {"ttestcase","tdunitxtestfixture"}
                findings.append({"kind": "fixture_class", "name": m.group(1), "detected_via": "regex",
                                 "source_ref": {"file": path.name, "line": line_of(clean, m.start())}})
        for m in TEST_ATTRIBUTE_RE.finditer(clean):
            findings.append({"kind": "attribute", "name": m.group(1), "detected_via": "regex",
                             "source_ref": {"file": path.name, "line": line_of(clean, m.start())}})
        for block in PUBLISHED_BLOCK_RE.finditer(clean):
            for tm in PUBLISHED_TEST_METHOD_RE.finditer(block.group(1)):
                findings.append({"kind": "published_test_method", "name": tm.group(1), "detected_via": "regex",
                                 "source_ref": {"file": path.name,
                                                "line": line_of(clean, block.start(1) + tm.start())}})
    by_kind = {}
    for f in findings:
        by_kind[f["kind"]] = by_kind.get(f["kind"], 0) + 1
    return {"counts": {"total": len(findings), "by_kind": by_kind}, "test_findings": findings}
Artefatos auxiliares (não-.pas) — nova função, assinatura recebe source_root: Path direto (conteúdo só é lido condicionalmente, pra categoria CI); hoje analyze() só faz rglob("*.pas")/rglob("*.dfm"), isso é um rglob novo por padrão:

CI_CONTENT_RE = re.compile(r"\b(test|dunit)\b", re.I)
AUX_TEST_PATTERNS = {
    "manual_doc":    ["*test*.txt", "*test*.docx", "*test*.xls", "*test*.xlsx", "*roteiro*.md"],
    "runner_config": ["*.dunitx", "*.testrunner", "TestInsight*.ini", "*.nunit", "*.runsettings"],
    "ci_test_stage": ["*.yml", "*.yaml", "Jenkinsfile", "*.ps1"],   # + gate de conteúdo abaixo
    "test_data":     ["*fixture*.*", "*mock*.*", "*testdata*.*", "*seed*.*"],
}
AUX_LABELS = {"manual_doc": "Manual — Documented", "runner_config": "Runner Config",
              "ci_test_stage": "CI Test Stage", "test_data": "Test Data"}

def scan_test_indicators(source_root: Path) -> dict[str, Any]:
    items, seen = [], set()
    for category, patterns in AUX_TEST_PATTERNS.items():
        for pat in patterns:
            for fp in source_root.rglob(pat):
                if not fp.is_file() or (category, fp) in seen:
                    continue
                if category == "ci_test_stage" and not CI_CONTENT_RE.search(read_text(fp)):
                    continue
                seen.add((category, fp))
                items.append({"category": category, "label": AUX_LABELS[category],
                              "source_ref": {"file": fp.name,
                                             "path": str(fp.relative_to(source_root)), "line": None}})
    counts = {c: sum(1 for it in items if it["category"] == c) for c in AUX_TEST_PATTERNS}
    return {"counts": counts, "items": items}
3. src/delphi_ast_analyzer.py::analyze() — orquestração
Inserir logo após R["08_code_overview"] = ov (linha 327 hoje) e antes de run_id = new_run_id() (linha 329). Reaproveitar pas_paths, já disponível desde o topo da função (linha 226: pas_paths = sorted(root.rglob("*.pas"))) — não reconstruir a partir de outra lista:

filename_hits = {p.name for p in pas_paths if rgx.is_test_filename(p)}

ast_findings = []
for ir in irs:
    for c in ir.get("classes", []):
        if (c.get("parent") or "").lower() in ast_bridge.TEST_FIXTURE_BASE_CLASSES \
           or any(a.lower() == "testfixture" for a in c.get("attributes", [])):
            ast_findings.append({"kind": "fixture_class", "name": c["name"], "detected_via": "ast",
                                 "source_ref": {"file": c["file"], "line": c["line"]}})
    for m in ir.get("methods", []):
        if m.get("visibility") == "published" and m["name"].lower().startswith("test"):
            ast_findings.append({"kind": "published_test_method", "name": m["qualified_name"],
                                 "detected_via": "ast",
                                 "source_ref": {"file": ir["file"], "line": m["begin_line"]}})
        for attr in m.get("attributes", []):
            if attr.lower() in {"test", "testcase"}:
                ast_findings.append({"kind": "attribute", "name": f"[{attr}] {m['qualified_name']}",
                                     "detected_via": "ast",
                                     "source_ref": {"file": ir["file"], "line": m["begin_line"]}})
    for tu in ir.get("test_uses", []):
        ast_findings.append({"kind": "framework_uses", "name": tu["name"], "detected_via": "ast",
                             "source_ref": {"file": ir["file"], "line": tu["line"]}})

regex_findings = rgx.extract_test_coverage(regex_pas)["test_findings"] if regex_pas else []
findings = ast_findings + regex_findings
findings += [{"kind": "filename_pattern", "name": f, "detected_via": "filename",
             "source_ref": {"file": f, "line": None}} for f in sorted(filename_hits)]

aux = rgx.scan_test_indicators(Path(source_root))

test_unit_files = {f["source_ref"]["file"] for f in findings}
test_method_keys = {(f["source_ref"]["file"], f["name"]) for f in findings
                     if f["kind"] in {"published_test_method", "attribute"}}
R["09_test_coverage"] = {
    "counts": {
        "test_units": len(test_unit_files),
        "test_methods": len(test_method_keys),
        "test_fixtures": sum(1 for f in findings if f["kind"] == "fixture_class"),
        "manual_test_docs": aux["counts"]["manual_doc"],
        "runner_configs": aux["counts"]["runner_config"],
        "ci_test_stages": aux["counts"]["ci_test_stage"],
        "test_data_files": aux["counts"]["test_data"],
        "mode": ast_mode,
    },
    "test_findings": _assign_ids(findings, "TST"),
    "auxiliary_indicators": _assign_ids(aux["items"], "TSTX"),
}
Decisões: duas listas (test_findings pro código Delphi, auxiliary_indicators pros 4 tipos não-.pas) em vez de uma lista fundida — taxonomias e semânticas de detected_via/category diferentes, fundir forçaria um schema mínimo comum artificial. test_methods deduplicado por (file, name) pra não contar duas vezes um método DUnitX com [Test] E seção published — mas ambos os achados continuam em test_findings pra rastreabilidade. Prefixos de ID "TST"/"TSTX" via _assign_ids() já existente, seguindo a convenção BR-/DBR-/INT-/API- já em uso.

4. src/schemas.py
"09_test_coverage": "Cobertura de testes (frameworks DUnit/DUnitX, fixtures, testes e indicadores auxiliares de teste)",
5. src/schemas/artifacts.schema.json
Adicionar "09_test_coverage" ao array artifact.enum (linhas 9-13).
Atualizar a description do schema (linha 5) de "8 artefatos" pra "9 artefatos".
Novo bloco {"if"/"then"} no array allOf, no nível de rigor do 06_integrations (não tão estrito quanto 01_business_rules, já que não há uma classe de regressão conhecida pra guardar ainda):
{
  "if": { "properties": { "artifact": { "const": "09_test_coverage" } } },
  "then": {
    "properties": {
      "payload": {
        "type": "object",
        "required": ["counts", "test_findings", "auxiliary_indicators"],
        "properties": {
          "counts": {
            "type": "object",
            "required": ["test_units", "test_methods", "test_fixtures",
                         "manual_test_docs", "runner_configs", "ci_test_stages",
                         "test_data_files", "mode"]
          },
          "test_findings": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["id", "kind", "source_ref"],
              "properties": {
                "kind": { "type": "string", "enum": ["fixture_class", "published_test_method",
                                                       "attribute", "framework_uses", "filename_pattern"] },
                "detected_via": { "type": "string", "enum": ["ast", "regex", "filename"] }
              }
            }
          },
          "auxiliary_indicators": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["id", "category", "label", "source_ref"],
              "properties": {
                "category": { "type": "string", "enum": ["manual_doc", "runner_config",
                                                           "ci_test_stage", "test_data"] }
              }
            }
          }
        }
      }
    }
  }
}
6. Efeitos colaterais a atualizar (mecânicos, mas não esquecer)
agents/delphi-analyzer.prompt.md (linhas 2, 13, 19, 41, 60 confirmadas nesta sessão): trocar "8 artefatos" → "9 artefatos"; adicionar 09_test_coverage na listagem de verificação (linhas 44-46).
Na esteira (C:\Desenv\repo\branch-executions-develop\imfai-ava-fabric-apps-agents), arquivo src/modules/ava-fabric-agents/asis-diagnostic/utils/run_delphi_ast_analysis.py: a lista expected (hoje 8 artefatos + manifest.json + metrics.jsonl) precisa do 09_test_coverage.json. Mudança mecânica de uma linha nesse outro repositório, no wrapper que o Step 0 do solution-delphi.md já chama — fazer junto, não esquecer.
Achado importante, deliberadamente FORA de escopo por decisão do usuário
Lendo src/modules/ava-fabric-agents/asis-diagnostic/agents/test-qa-asis.md (agente ava-asis-test-qa, v3.0.0) na esteira: ele já existe e já faz quase exatamente o que este artefato mapeia — inclusive suas tabelas de detecção (linhas 69-85) são idênticas, campo por campo, às que o usuário passou nesta conversa (mesmos 6 padrões de nome de arquivo Delphi, mesmos 4 tipos de artefato auxiliar com os mesmos labels). Isso confirma que o 09_test_coverage.json é pensado como matéria-prima determinística para esse agente (Skills 1 e 2: Test Discovery / Test Approach Detection), exatamente como 08_code_overview.classes virou o ClassRegistry[] do solution-delphi.md.

Risco identificado, não resolvido nesta rodada: ava-asis-test-qa é dispatchado em paralelo com ava-asis-solution-delphi na mesma Phase A do orquestrador (orchestrator-asis.md, dispatch_schedule.phase_a.mode: immediate). Se um "Step 0" equivalente fosse simplesmente duplicado dentro de test-qa-asis.md (mesma chamada Bash que já existe em solution-delphi.md), os dois agentes disparariam a extração ao mesmo tempo e escreveriam nos mesmos arquivos em outputs/asis/delphi-ast-raw/ concorrentemente — risco de corrida. O ponto de hook mais seguro seria mover a chamada da tool pro orquestrador (existe precedente exato: "Step 0.5 — Delphi Backup Cleanup", que já roda 1x, condicional a legacy_technology == delphi, antes do fan-out da Phase A) — mas isso é uma mudança maior num arquivo grande e sensível (orchestrator-asis.md, 2070 linhas).

Decisão do usuário: não mexer nisso agora. Este plano cobre só a criação do artefato 09_test_coverage.json neste projeto. A integração cruzada com ava-asis-test-qa (e a decisão de onde hospedar o Step 0 compartilhado) fica para uma rodada futura, quando for aberta explicitamente.

Verificação
Criar fixture sintética (scratchpad, fora do repo):
uCalculatorTests.pas — bate no nome (*Tests.pas), uses ..., DUnitX.TestFramework;, [TestFixture] TCalculatorTests = class(TDUnitXTestFixture) com [Test] procedure Test_Add;; mais uma segunda classe TCalculatorLegacyTests = class(TTestCase) com seção published contendo procedure TestSubtract;.
uNotATest.pas — unidade comum, controle negativo (zero achados esperados).
Pasta auxiliar: roteiro_manual.md (manual_doc), run.testrunner + TestInsight.ini (runner_config), azure-pipelines.yml com "dunit" num step (ci_test_stage positivo) + deploy.yml sem menção a test/dunit (controle negativo — deve ser excluído), mock_customer.json (test_data).
python src/run_pipeline.py <fixture_dir> --extraction <scratch>/extraction --compressed <scratch>/compressed.
Confirmar 09_test_coverage.json gerado e validate_artifacts.py sem violações.
Conferir: mode == "ast+regex-fallback", test_units == 2, test_fixtures == 2, test_methods == 2, manual_test_docs == 1, runner_configs == 2, ci_test_stages == 1 (só o yml com "dunit", não o deploy.yml), test_data_files == 1; detected_via == "ast" em todos exceto o achado puro de nome de arquivo ("filename").
Repetir com AVA_AST_CLI apontando pra um caminho inexistente (força mode == "regex-only") e confirmar que os mesmos 4 tipos de sinal Delphi ainda aparecem via regex (nome de arquivo, framework_uses, fixture_class, published_test_method, attribute) — aceitando que a associação de atributo por regex é mais aproximada que via AST.
Arquivos críticos
src/ast_bridge.py — _index_attributes, _index_visibility, _test_framework_uses, hook em normalize_ast().
src/regex_extractors.py — is_test_filename, extract_test_coverage, scan_test_indicators.
src/delphi_ast_analyzer.py::analyze() — bloco novo entre 08_code_overview e run_id = new_run_id().
src/schemas.py — entrada em ARTIFACTS.
src/schemas/artifacts.schema.json — enum + bloco allOf.
agents/delphi-analyzer.prompt.md — contagem 8→9.
(repo separado) .../asis-diagnostic/utils/run_delphi_ast_analysis.py — lista expected.
Add Comment