"""Unit tests for run_ast_analysis.py language routing."""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[2]
        / "src"
        / "modules"
        / "ava-fabric-agents"
        / "asis-diagnostic"
        / "utils"
    ),
)

import run_ast_analysis as raa


class TestLanguageDetection(unittest.TestCase):
    def test_supported_contains_expected(self):
        self.assertIn("delphi", raa.SUPPORTED_LANGUAGES)
        self.assertIn("dotnet", raa.SUPPORTED_LANGUAGES)
        self.assertIn("java", raa.SUPPORTED_LANGUAGES)

    def test_detect_from_extensions_dotnet(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Program.cs").write_text("class Program {}")
            (root / "App.vb").write_text("Module App End Module")
            self.assertEqual(raa._detect_language(root), "dotnet")

    def test_detect_from_extensions_java(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src" / "main" / "java").mkdir(parents=True)
            (root / "src" / "main" / "java" / "Main.java").write_text("public class Main {}")
            self.assertEqual(raa._detect_language(root), "java")

    def test_detect_from_extensions_delphi(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "unit1.pas").write_text("unit Unit1;")
            self.assertEqual(raa._detect_language(root), "delphi")

    def test_detect_build_files_java(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pom.xml").write_text("<project></project>")
            self.assertEqual(raa._detect_language(root), "java")

    def test_unknown_when_no_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(raa._detect_language(root), "unknown")


class TestAnalyzerHomeResolution(unittest.TestCase):
    def test_config_map_wins(self):
        cfg = {
            "ava_ast_analyzers": {"dotnet": "C:\\dotnet-analyzer"},
            "ava_ast_analyzer_path": "C:\\legacy",
        }
        home = raa._get_analyzer_home(cfg, "dotnet")
        self.assertEqual(home, Path("C:\\dotnet-analyzer"))

    def test_legacy_alias_for_delphi(self):
        cfg = {"ava_ast_analyzer_path": "C:\\delphi-analyzer"}
        home = raa._get_analyzer_home(cfg, "delphi")
        self.assertEqual(home, Path("C:\\delphi-analyzer"))

    def test_sibling_discovery_finds_java_analyzer(self):
        # The real workspace has a sibling imfai-ava-tools repo for java.
        home = raa._get_analyzer_home({}, "java")
        expected = Path("C:/_git/imfai-ava-tools/ava-fabric-java-analyzer")
        self.assertEqual(home, expected)

    def test_missing_returns_none(self):
        cfg = {}
        with unittest.mock.patch.dict(os.environ, {"AVA_DOTNET_ANALYZER_HOME": "", "AVA_JAVA_ANALYZER_HOME": "", "AVA_DELPHI_ANALYZER_HOME": ""}, clear=False):
            # Mask the sibling repo discovery by asking for a language that has no
            # sibling analyzer directory under imfai-ava-tools.
            home = raa._get_analyzer_home(cfg, "cobol")
            self.assertIsNone(home)


class TestResolveLanguage(unittest.TestCase):
    def _write_config(self, directory: Path, **fields) -> None:
        config = {"project_name": "test-project", **fields}
        context = directory / "context"
        context.mkdir(parents=True, exist_ok=True)
        try:
            import yaml
        except ImportError:
            return
        (context / "project-config.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")

    def test_cli_language_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_config(root, legacy_technology="delphi", repository_path=str(root))
            # Change CWD to the temp dir so projects/ resolves correctly
            orig = Path.cwd()
            try:
                # Make the project directory match config resolution
                Path(tmp).mkdir(exist_ok=True)
                (Path(tmp) / "projects" / "test-project" / "context").mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copy(Path(tmp) / "context" / "project-config.yaml", Path(tmp) / "projects" / "test-project" / "context" / "project-config.yaml")
                import os
                os.chdir(tmp)
                lang, is_auto = raa.resolve_language("test-project", "dotnet")
                self.assertEqual(lang, "dotnet")
                self.assertFalse(is_auto)
            finally:
                os.chdir(orig)

    def test_legacy_config_language(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_config(root, legacy_technology="java", repository_path="")
            import shutil
            import os
            orig = Path.cwd()
            try:
                (Path(tmp) / "projects" / "test-project" / "context").mkdir(parents=True, exist_ok=True)
                shutil.copy(Path(tmp) / "context" / "project-config.yaml", Path(tmp) / "projects" / "test-project" / "context" / "project-config.yaml")
                os.chdir(tmp)
                lang, is_auto = raa.resolve_language("test-project", None)
                self.assertEqual(lang, "java")
                self.assertFalse(is_auto)
            finally:
                os.chdir(orig)

    def test_auto_detect_java(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src"
            src.mkdir()
            (src / "Hello.java").write_text("class Hello {}")
            self._write_config(root, legacy_technology="", repository_path=str(root))
            import shutil
            import os
            orig = Path.cwd()
            try:
                (Path(tmp) / "projects" / "test-project" / "context").mkdir(parents=True, exist_ok=True)
                shutil.copy(Path(tmp) / "context" / "project-config.yaml", Path(tmp) / "projects" / "test-project" / "context" / "project-config.yaml")
                os.chdir(tmp)
                lang, is_auto = raa.resolve_language("test-project", None)
                self.assertEqual(lang, "java")
                self.assertTrue(is_auto)
            finally:
                os.chdir(orig)

    def test_legacy_vbnet_resolves_to_dotnet(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_config(root, legacy_technology="vbnet", repository_path="")
            import shutil
            import os
            orig = Path.cwd()
            try:
                (Path(tmp) / "projects" / "test-project" / "context").mkdir(parents=True, exist_ok=True)
                shutil.copy(Path(tmp) / "context" / "project-config.yaml", Path(tmp) / "projects" / "test-project" / "context" / "project-config.yaml")
                os.chdir(tmp)
                lang, is_auto = raa.resolve_language("test-project", None)
                self.assertEqual(lang, "dotnet")
                self.assertFalse(is_auto)
            finally:
                os.chdir(orig)


class TestResolveDotNetLanguage(unittest.TestCase):
    def _write_config(self, directory: Path, **fields) -> None:
        config = {"project_name": "test-project", **fields}
        project_context = directory / "projects" / "test-project" / "context"
        project_context.mkdir(parents=True, exist_ok=True)
        try:
            import yaml
        except ImportError:
            return
        text = yaml.safe_dump(config)
        (project_context / "project-config.yaml").write_text(text, encoding="utf-8")

    def _setup_project_dir(self, tmp: str) -> Path:
        return Path(tmp)

    def _load_config_in_dir(self, root: Path) -> dict:
        orig = os.getcwd()
        try:
            os.chdir(root)
            return raa._load_config("test-project")
        finally:
            os.chdir(orig)

    def test_dotnet_language_config_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._setup_project_dir(tmp)
            self._write_config(root, legacy_technology="dotnet", repository_path=str(root),
                               ava_ast_analyzers={"dotnet_language": "cs"})
            config = self._load_config_in_dir(root)
            self.assertEqual(raa.resolve_dotnet_language(config, root), "cs")

    def test_legacy_vbnet_maps_to_vb(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._setup_project_dir(tmp)
            self._write_config(root, legacy_technology="vbnet", repository_path=str(root))
            config = self._load_config_in_dir(root)
            self.assertEqual(raa.resolve_dotnet_language(config, root), "vb")

    def test_detect_cs_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._setup_project_dir(tmp)
            self._write_config(root, legacy_technology="dotnet", repository_path=str(root))
            (root / "Program.cs").write_text("class Program {}")
            (root / "App.csproj").write_text("<Project></Project>")
            config = self._load_config_in_dir(root)
            self.assertEqual(raa.resolve_dotnet_language(config, root), "cs")

    def test_detect_vb_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._setup_project_dir(tmp)
            self._write_config(root, legacy_technology="dotnet", repository_path=str(root))
            (root / "Program.vb").write_text("Module Program End Module")
            (root / "App.vbproj").write_text("<Project></Project>")
            config = self._load_config_in_dir(root)
            self.assertEqual(raa.resolve_dotnet_language(config, root), "vb")

    def test_detect_both(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._setup_project_dir(tmp)
            self._write_config(root, legacy_technology="dotnet", repository_path=str(root))
            (root / "Program.cs").write_text("class Program {}")
            (root / "Program.vb").write_text("Module Program End Module")
            config = self._load_config_in_dir(root)
            self.assertEqual(raa.resolve_dotnet_language(config, root), "both")

    def test_default_both_when_empty_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._setup_project_dir(tmp)
            self._write_config(root, legacy_technology="dotnet", repository_path=str(root))
            config = self._load_config_in_dir(root)
            self.assertEqual(raa.resolve_dotnet_language(config, root), "both")




class TestBrsEnvResolution(unittest.TestCase):
    """Credenciais Azure OpenAI da etapa 5 do BRS (--brs-llm)."""

    def test_read_env_file_missing_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(raa._read_env_file(Path(tmp) / ".env"), {})

    def test_read_env_file_parses_comments_blanks_and_quotes(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text(
                "# comentário\n"
                "\n"
                "AZURE_OPENAI_API_KEY=plain-key\n"
                'AZURE_OPENAI_ENDPOINT="https://example.openai.azure.com/"\n'
                "AZURE_OPENAI_LLM_MODEL='Kimi-K2.7-Code'\n",
                encoding="utf-8",
            )
            values = raa._read_env_file(env_path)
            self.assertEqual(values["AZURE_OPENAI_API_KEY"], "plain-key")
            self.assertEqual(
                values["AZURE_OPENAI_ENDPOINT"], "https://example.openai.azure.com/"
            )
            self.assertEqual(values["AZURE_OPENAI_LLM_MODEL"], "Kimi-K2.7-Code")

    def _cleared_env(self):
        return unittest.mock.patch.dict(
            os.environ, {k: "" for k in raa._BRS_ENV_KEYS}, clear=False
        )

    def test_repo_env_wins_over_analyzer_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp) / "repo"
            analyzer = Path(tmp) / "analyzer"
            repo_root.mkdir()
            analyzer.mkdir()
            (repo_root / ".env").write_text("AZURE_OPENAI_API_KEY=from-repo\n", encoding="utf-8")
            (analyzer / ".env").write_text(
                "AZURE_OPENAI_API_KEY=from-analyzer\nAZURE_OPENAI_LLM_MODEL=from-analyzer\n",
                encoding="utf-8",
            )
            with self._cleared_env(), unittest.mock.patch.object(raa, "_REPO_ROOT", repo_root):
                resolved, searched = raa._resolve_brs_env(analyzer)
            self.assertEqual(resolved["AZURE_OPENAI_API_KEY"], "from-repo")
            # chave ausente no repo cai para o .env do analyzer
            self.assertEqual(resolved["AZURE_OPENAI_LLM_MODEL"], "from-analyzer")
            self.assertEqual(searched, [repo_root / ".env", analyzer / ".env"])

    def test_ambient_env_wins_over_both_env_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp) / "repo"
            analyzer = Path(tmp) / "analyzer"
            repo_root.mkdir()
            analyzer.mkdir()
            (repo_root / ".env").write_text("AZURE_OPENAI_API_KEY=from-repo\n", encoding="utf-8")
            (analyzer / ".env").write_text(
                "AZURE_OPENAI_API_KEY=from-analyzer\n", encoding="utf-8"
            )
            with unittest.mock.patch.dict(
                os.environ, {"AZURE_OPENAI_API_KEY": "from-ambient"}, clear=False
            ), unittest.mock.patch.object(raa, "_REPO_ROOT", repo_root):
                resolved, _ = raa._resolve_brs_env(analyzer)
            self.assertEqual(resolved["AZURE_OPENAI_API_KEY"], "from-ambient")

    def test_resolve_does_not_mutate_os_environ(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp) / "repo"
            repo_root.mkdir()
            (repo_root / ".env").write_text("AZURE_OPENAI_API_KEY=from-repo\n", encoding="utf-8")
            with self._cleared_env(), unittest.mock.patch.object(raa, "_REPO_ROOT", repo_root):
                raa._resolve_brs_env(Path(tmp) / "analyzer")
                self.assertEqual(os.environ.get("AZURE_OPENAI_API_KEY"), "")

    def test_preflight_fails_when_api_key_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp) / "repo"
            repo_root.mkdir()
            with self._cleared_env(), unittest.mock.patch.object(raa, "_REPO_ROOT", repo_root):
                _, rc = raa._preflight_brs_llm(Path(tmp) / "analyzer")
            self.assertNotEqual(rc, 0)

    def test_preflight_fails_when_langchain_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp) / "repo"
            repo_root.mkdir()
            (repo_root / ".env").write_text("AZURE_OPENAI_API_KEY=k\n", encoding="utf-8")
            with self._cleared_env(), \
                    unittest.mock.patch.object(raa, "_REPO_ROOT", repo_root), \
                    unittest.mock.patch.object(
                        raa.importlib.util, "find_spec", return_value=None):
                _, rc = raa._preflight_brs_llm(Path(tmp) / "analyzer")
            self.assertNotEqual(rc, 0)

    def test_preflight_passes_with_key_and_deps(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp) / "repo"
            repo_root.mkdir()
            (repo_root / ".env").write_text(
                "AZURE_OPENAI_API_KEY=k\nAZURE_OPENAI_ENDPOINT=https://e/\n"
                "AZURE_OPENAI_LLM_MODEL=m\n",
                encoding="utf-8",
            )
            with self._cleared_env(), \
                    unittest.mock.patch.object(raa, "_REPO_ROOT", repo_root), \
                    unittest.mock.patch.object(
                        raa.importlib.util, "find_spec", return_value=object()):
                resolved, rc = raa._preflight_brs_llm(Path(tmp) / "analyzer")
            self.assertEqual(rc, 0)
            self.assertEqual(resolved["AZURE_OPENAI_API_KEY"], "k")


class TestDelphiAnalyzerInvocation(unittest.TestCase):
    """_run_delphi_analyzer monta cmd/env corretos para a etapa BRS/LLM."""

    def _invoke(self, *, brs_llm: bool, brs_env: dict | None):
        with tempfile.TemporaryDirectory() as tmp:
            analyzer_home = Path(tmp) / "analyzer"
            (analyzer_home / "src").mkdir(parents=True)
            (analyzer_home / "src" / "run_pipeline.py").write_text("", encoding="utf-8")
            captured: dict = {}

            def fake_popen(cmd, **kwargs):
                captured["cmd"] = cmd
                captured["env"] = kwargs["env"]
                raise RuntimeError("stop-after-capture")

            with unittest.mock.patch.object(raa.subprocess, "Popen", side_effect=fake_popen):
                with self.assertRaises(RuntimeError):
                    raa._run_delphi_analyzer(
                        analyzer_home,
                        Path(tmp) / "repo",
                        Path(tmp) / "extraction",
                        Path(tmp) / "compressed",
                        Path(tmp) / "run.log",
                        brs_llm=brs_llm,
                        brs_env=brs_env,
                    )
            return analyzer_home, captured

    def test_brs_env_file_passed_as_absolute_path(self):
        analyzer_home, captured = self._invoke(brs_llm=True, brs_env={})
        self.assertIn("--brs-llm", captured["cmd"])
        idx = captured["cmd"].index("--brs-env-file")
        self.assertEqual(captured["cmd"][idx + 1], str(analyzer_home / ".env"))

    def test_no_brs_flags_when_disabled(self):
        _, captured = self._invoke(brs_llm=False, brs_env={"AZURE_OPENAI_API_KEY": "k"})
        self.assertNotIn("--brs-llm", captured["cmd"])
        self.assertNotIn("--brs-env-file", captured["cmd"])

    def test_credentials_reach_child_env(self):
        with unittest.mock.patch.dict(os.environ, {"AZURE_OPENAI_API_KEY": ""}, clear=False):
            _, captured = self._invoke(
                brs_llm=True, brs_env={"AZURE_OPENAI_API_KEY": "from-dotenv"}
            )
        self.assertEqual(captured["env"]["AZURE_OPENAI_API_KEY"], "from-dotenv")

    def test_exported_ambient_value_is_not_overwritten(self):
        with unittest.mock.patch.dict(
            os.environ, {"AZURE_OPENAI_API_KEY": "from-ambient"}, clear=False
        ):
            _, captured = self._invoke(
                brs_llm=True, brs_env={"AZURE_OPENAI_API_KEY": "from-dotenv"}
            )
        self.assertEqual(captured["env"]["AZURE_OPENAI_API_KEY"], "from-ambient")


class TestAstNormalization(unittest.TestCase):
    def test_payload_any_upper_and_lower_case(self):
        self.assertEqual(raa._payload_any({"payload": {"a": 1}}), {"a": 1})
        self.assertEqual(raa._payload_any({"Payload": {"a": 1}}), {"a": 1})
        self.assertEqual(raa._payload_any({}), {})

    def test_classify_rule_fallback(self):
        r = raa._classify_rule({"type": "calculation", "expression": "a + b"})
        self.assertEqual(r["category"], "calculation")
        # generic rule with no type gets classified from expression
        r = raa._classify_rule({"expression": "x == null"})
        self.assertEqual(r["category"], "validation")
        # method name heuristic
        r = raa._classify_rule({"method": "ValidateCustomer"})
        self.assertEqual(r["category"], "validation")

    def test_normalize_form_business_rules_dotnet_flat_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "02_form_business_rules.json"
            path.write_text(
                json.dumps(
                    {
                        "Artifact": "form_business_rules",
                        "SchemaVersion": "1.0.0",
                        "Payload": [
                            {
                                "Name": "LoginForm",
                                "FormType": "winforms",
                                "Controls": [
                                    {"Name": "txtUser", "ControlType": "TextBox", "Text": "user"},
                                    {"Name": "btnOk", "ControlType": "Button"},
                                ],
                                "EventHandlers": ["btnOk.Click => OnOk"],
                                "SourceRef": {"File": "LoginForm.cs", "Line": 10},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            raa._normalize_form_business_rules(path)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["artifact"], "form_business_rules")
            payload = data["payload"]
            self.assertEqual(payload["counts"], {"forms": 1, "fields": 2})
            self.assertEqual(payload["forms"][0]["form_name"], "LoginForm")
            self.assertEqual(payload["forms"][0]["form_type"], "winforms")
            self.assertEqual(payload["forms"][0]["source_file"], "LoginForm.cs")
            self.assertEqual(payload["forms"][0]["event_handlers"], ["btnOk.Click => OnOk"])
            self.assertEqual(payload["forms"][0]["fields"][0]["name"], "txtUser")
            self.assertEqual(payload["forms"][0]["fields"][0]["component_class"], "TextBox")
            self.assertEqual(payload["forms"][0]["fields"][1]["event_handlers"], {"Click": "OnOk"})

    def test_normalize_form_business_rules_java_canonical(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "02_form_business_rules.json"
            path.write_text(
                json.dumps(
                    {
                        "artifact": "form_business_rules",
                        "schema_version": "1.0.0",
                        "payload": {
                            "counts": {"forms": 1, "fields": 1},
                            "forms": [
                                {
                                    "form_name": "MainView",
                                    "form_class": "MainView",
                                    "source_file": "MainView.java",
                                    "field_count": 1,
                                    "fields": [
                                        {
                                            "name": "submitBtn",
                                            "component_class": "JButton",
                                            "properties": {"text": "Submit"},
                                            "event_handlers": {"actionPerformed": "onSubmit"},
                                            "has_validation": False,
                                            "data_bindings": [],
                                        }
                                    ],
                                    "event_handlers": ["submitBtn.actionPerformed => onSubmit"],
                                }
                            ],
                        },
                    }
                ),
                encoding="utf-8",
            )
            raa._normalize_form_business_rules(path)
            data = json.loads(path.read_text(encoding="utf-8"))
            payload = data["payload"]
            self.assertEqual(payload["counts"], {"forms": 1, "fields": 1})
            self.assertEqual(payload["forms"][0]["form_name"], "MainView")
            self.assertTrue(payload["forms"][0]["fields"][0]["event_handlers"])

    def test_normalize_business_rules_list_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "01_business_rules.json"
            path.write_text(
                json.dumps(
                    {
                        "Artifact": "business_rules",
                        "SchemaVersion": "1.0.0",
                        "Payload": [
                            {
                                "id": "BR-00001",
                                "type": "conditional_logic",
                                "unit": "Order",
                                "method": "CalcTotal",
                                "expression": "if x > 0 then ...",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            raa._normalize_business_rules(path)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["artifact"], "business_rules")
            self.assertIn("rules", data["payload"])
            self.assertEqual(data["payload"]["counts"]["total"], 1)
            self.assertIn("category", data["payload"]["rules"][0])

    def test_normalize_business_rules_string_payload_left_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "01_business_rules.json"
            original = {
                "artifact": "business_rules",
                "schema_version": "1.0.0",
                "payload": {"rules": "__buckets:type\n__key:calculation\n[0]{id:str}"},
            }
            path.write_text(json.dumps(original), encoding="utf-8")
            raa._normalize_business_rules(path)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["payload"]["rules"], original["payload"]["rules"])

    def test_normalize_overview_from_legacy_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "08_code_overview.json"
            path.write_text(
                json.dumps(
                    {
                        "Artifact": "code_overview",
                        "Payload": {
                            "totalFiles": 10,
                            "totalClasses": 5,
                            "business_rules": 3,
                        },
                    }
                ),
                encoding="utf-8",
            )
            raa._normalize_overview(path)
            data = json.loads(path.read_text(encoding="utf-8"))
            totals = data["payload"]["totals"]
            self.assertEqual(totals["units_total"], 10)
            self.assertEqual(totals["classes"], 5)
            self.assertEqual(totals["business_rules"], 3)

    def test_ensure_manifest_metrics_creates_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            extraction = Path(tmp) / "extraction"
            compressed = Path(tmp) / "compressed"
            extraction.mkdir()
            compressed.mkdir()
            (extraction / "08_code_overview.json").write_text(
                json.dumps({"payload": {"totals": {"units_total": 7}}}),
                encoding="utf-8",
            )
            raa._ensure_manifest_metrics(compressed, extraction)
            self.assertTrue((compressed / "manifest.json").exists())
            self.assertTrue((compressed / "metrics.jsonl").exists())

    def test_validate_output_tolerates_optional_java_sql_functions(self):
        with tempfile.TemporaryDirectory() as tmp:
            extraction = Path(tmp) / "extraction"
            compressed = Path(tmp) / "compressed"
            extraction.mkdir()
            compressed.mkdir()
            for i, name in enumerate(raa._EXPECTED_EXTRACTION_FILES):
                if name == "10_sql_functions.json":
                    continue  # missing on purpose
                (extraction / name).write_text("{}", encoding="utf-8")
            for name in raa._EXPECTED_COMPRESSED_FILES:
                (compressed / name).write_text("{}", encoding="utf-8")
            missing = raa._validate_output("java", extraction, compressed)
            self.assertNotIn("extraction/10_sql_functions.json", missing)
            # same missing file is reported for dotnet
            missing_dotnet = raa._validate_output("dotnet", extraction, compressed)
            self.assertIn("extraction/10_sql_functions.json", missing_dotnet)


if __name__ == "__main__":
    unittest.main()
