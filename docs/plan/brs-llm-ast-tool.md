Ready for review
Select text to add comments on the plan
Fix: BRS LLM stage fails with "Missing credentials" when the agent delegates to the AST tool
Context
The Step 0 AST extraction for T2TiERP-1-Delphi-001-cli-ava ran for ~13 minutes, produced all 9 deterministic artifacts, and then died at the end:

== 2/3  BRS — regras de negócio: etapas 1-8 (com LLM) ==
[BRS] 19995 regra(s) atômica(s) -> 977 candidata(s) -> 310 dossiê(s); fonte localizado em 310.
[BRS] AVISO: etapa LLM falhou (OpenAIError: Missing credentials. ... AZURE_OPENAI_API_KEY ...);
      mantendo apenas o resultado determinístico.
FALHA: 2 violação(ões) de schema:
  - 10_business_rule_cases.json: payload: 'catalog' is a required property
  - 10_business_rule_cases.json: payload/counts: 'catalog_rules' is a required property
(log: run_ast_analysis.delphi.log:1210-1218)

Root cause — two independent gaps, both must be closed
Nothing in this repo ever loads .env. The repo-root .env holds exactly the four keys the BRS stage needs (AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_LLM_MODEL, AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION), but there is no load_dotenv anywhere in src/ (only in vendored Headroom). ava-pipeline-runner-cli.py authenticates from .copilot-key, never from .env. So os.environ never carries AZURE_OPENAI_*, and run_ast_analysis.py:712 (env = dict(os.environ)) faithfully propagates nothing.

The analyzer's own .env is never found. The external analyzer (C:\Desenv\repo\tool\ast\imfai-ava-tools\ava-fabric-delphi-analyzer) defaults --brs-env-file to the relative string ".env", and run_ast_analysis.py:730 launches it with cwd=<analyzer_home>/src. The file lives at <analyzer_home>/.env, so Path(".env").is_file() is False and load_dotenv is silently skipped. The .env on disk is fully populated — it just never gets read.

Consequently api_key is None, AzureChatOpenAI raises, and the analyzer's bare except Exception flattens it into one opaque warning line. Because payload["catalog"] is only written when the LLM stage succeeds (brs/pipeline.py:197-201) while the artifact schema marks catalog unconditionally required (artifacts.schema.json:246), the deterministic-only fallback can never pass validation — the whole run is reported as FALHA. Fixing the credentials therefore fixes both symptoms.

Two related defects found on the way:

pipeline_runner 16.py:2042 passes --brs-llm; ava-pipeline-runner-cli.py:2100 dropped it — the runner's own AST step no longer requests the LLM stage at all.
The BRS LLM python deps (langchain-openai, langchain-core, tenacity, tiktoken, python-dotenv) are verified installed in the active interpreter, so they are not the cause here — but an ImportError would be swallowed into the exact same opaque message, so the pre-flight should cover it too.
Intended outcome
run_ast_analysis.py --brs-llm runs with the same Azure OpenAI configuration the pipeline uses, from .env, regardless of whether it is launched by the agent (solution-delphi Step 0) or by ava-pipeline-runner-cli.py — and when the configuration is genuinely absent it fails immediately and by name, instead of after 13 minutes of extraction.

Decisions (confirmed)
Topic	Decision
Config source	Repo-root .env first, analyzer .env as fallback. Ambient os.environ still wins over both.
Missing credentials	Pre-flight check, fail fast before spawning the analyzer.
Scope	run_ast_analysis.py + ava-pipeline-runner-cli.py (--brs-llm restore) + solution-delphi.md doc drift.
Out of scope: the external analyzer repo (C:\Desenv\repo\tool\ast\...) is not modified.

Changes
1. src/modules/ava-fabric-agents/asis-diagnostic/utils/run_ast_analysis.py (primary)
This is the one file both launch routes go through, so it carries the fix.

1a. Add a .env reader + credential resolver (new module-level helpers, near _get_analyzer_home at line 535).

_REPO_ROOT = Path(__file__).resolve().parents[5] — the file sits at src/modules/ava-fabric-agents/asis-diagnostic/utils/, so parents[5] is the repo root.
_BRS_ENV_KEYS = ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_LLM_MODEL", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_API_VERSION") — mirrors the analyzer's _resolve_settings (<analyzer_home>/src/brs/llm_extract.py:221-254); do not invent new names.
_read_env_file(path) -> dict[str, str]: prefer from dotenv import dotenv_values (python-dotenv is installed), with a small stdlib fallback parser (skip blanks/#, split on first =, strip surrounding quotes) so the tool keeps working on an interpreter without the package. Return {} when the file is absent.
_resolve_brs_env(analyzer_home) -> tuple[dict[str, str], list[Path]]: merge with precedence ambient os.environ > repo-root .env > <analyzer_home>/.env; return the resolved values plus the list of paths actually consulted (for the error message). Do not mutate the parent os.environ — build a dict, consistent with the repo's existing idiom in agent_runner.py:220-229 and ava-pipeline-runner-cli.py:403-411.
1b. Pre-flight validation — new _preflight_brs_llm(analyzer_home) -> int, called from run_ast_analysis() (around line 936, right after analyzer_home is validated and before the if language == "delphi" dispatch), only when brs_llm and language == "delphi":

Hard-fail (return non-zero) if AZURE_OPENAI_API_KEY resolves empty. Message must name the variable, the .env paths searched, and the fact that --brs-llm was requested.
Hard-fail if importlib.util.find_spec("langchain_openai") is None, pointing at <analyzer_home>/requirements-brs-llm.txt — otherwise that ImportError becomes the same opaque [BRS] AVISO line.
Warn (do not fail) if AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_LLM_MODEL are unresolved: the analyzer falls back to brs_config.yml (llm.base_url, llm.model) for those two.
Print the resolved endpoint / model / api-version and api_key=*** (never the key) so the log shows what the run will actually use.
1c. Propagate into the child — in _run_delphi_analyzer (lines 697-737):

Accept the resolved dict as a parameter; after env = dict(os.environ) (line 712), apply it with env.setdefault(k, v) so a genuinely-exported ambient value still wins.
When brs_llm is set, append ["--brs-env-file", str(analyzer_home / ".env")] to cmd (line 725-726) so the analyzer's relative-path default is bypassed with an absolute path. Belt-and-braces: even if the env dict were empty, the analyzer now finds its own .env.
2. ava-pipeline-runner-cli.py — restore --brs-llm on the AST step
At line 2100, match pipeline_runner 16.py:2042:

cmd = [sys.executable, str(run_ast_py), "--project", project, "--brs-llm"]
No env plumbing is needed here — the Popen at line 2116 inherits os.environ, and change #1 makes run_ast_analysis.py resolve .env itself. (ava-pipeline-runner-cli.py is untracked in git; the canonical src/shared/tools/ava_pipeline.py has no AST step, so there is no second runner to patch.)

3. src/modules/ava-fabric-agents/asis-diagnostic/agents/solution-delphi.md — doc drift
Lines 344-352: the credential hint points at a stale machine path (C:\projects\avanade\imfai-ava-tools\...). Replace with the two paths the tool now actually searches: the repo-root .env, then <ava_ast_analyzer_path>/.env.
Lines 325 / 331 / 341: --ava-analyzer-path does not exist in run_ast_analysis.py's argparse (lines 1044-1060 define only --project, --language, --mirror-legacy-delphi, --brs-llm). Drop the flag from the documented command; analyzer resolution already reads ava_ast_analyzer_path from project-config.yaml inside _get_analyzer_home (line 535).
Note in the retry section that a credential failure now exits before extraction starts, so the documented single retry without --brs-llm is a deliberate degrade, not a workaround for a 13-minute wasted run.
Verification
Unit — extend tests/utils/test_run_ast_analysis.py (which already covers _get_analyzer_home env masking at line 88):

_read_env_file parses quoted/unquoted values, ignores comments and blanks, returns {} for a missing file.
_resolve_brs_env precedence: ambient beats repo .env beats analyzer .env (use monkeypatch
tmp_path).
_preflight_brs_llm returns non-zero and names AZURE_OPENAI_API_KEY when no source supplies it.
_run_delphi_analyzer appends --brs-env-file <analyzer_home>/.env only when brs_llm=True (assert on the cmd list with subprocess.Popen patched).
Negative e2e (fast) — temporarily unset the key and confirm the run aborts in seconds with the named error instead of extracting:

$env:AZURE_OPENAI_API_KEY=''
python src/modules/ava-fabric-agents/asis-diagnostic/utils/run_ast_analysis.py `
  --project T2TiERP-1-Delphi-001-cli-ava --brs-llm
(rename the two .env files aside for this check, then restore them)

Positive e2e (small corpus) — point a scratch project-config.yaml at a small sample under C:\Desenv\repo\tool\ast\imfai-ava-tools\ava-fabric-delphi-analyzer\examples\ and run with --brs-llm. Success criteria in the produced outputs/asis/ast-raw/delphi/run_ast_analysis.delphi.log:

the [BRS] AVISO: etapa LLM falhou line is gone;
a [BRS] Catálogo: N aceita(s), ... line is present;
the run ends without the FALHA: ... 'catalog' is a required property block;
compressed/10_business_rule_cases.json contains payload.catalog and payload.counts.catalog_rules, with payload.counts.mode == "deterministic+llm".
Runner path — python "ava-pipeline-runner-cli.py" on the same scratch project; confirm the printed command now includes --brs-llm and the resulting log matches criterion 3.

Full re-run — only after 3 and 4 pass, re-run --project T2TiERP-1-Delphi-001-cli-ava --brs-llm (~13 min extraction + LLM stage over 310 dossiers) and confirm exit 0.

Notes / risks
The full T2TiERP run sends 310 dossiers to Azure OpenAI (brs_config.yml: batch_size: 25, max_concurrency: 3) — real cost and wall-clock. Validate on the small corpus first.
The analyzer's except Exception at brs/pipeline.py:225 still swallows runtime LLM failures (401, throttling, network) into one warning line, and its schema still requires catalog unconditionally. Our pre-flight covers configuration failures only; a mid-run API failure will still surface as the same FALHA. Worth raising against the analyzer repo separately.
No secrets are added to tracked files: .env stays gitignored; only variable names appear in code and docs.