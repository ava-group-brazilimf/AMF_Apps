# Source: {{SOURCE_ARTIFACT}}
# Agent: ava-qa-scenario-generator
# Generated: {{TIMESTAMP}}
# Trace: {{TRACE_ID}}

# ============================================================================
# TEMPLATE: BDD Gherkin Feature File
# Usage: The ava-qa-scenario-generator agent uses this template as the
#        canonical structure for all .feature files it generates.
#        Replace all {{PLACEHOLDER}} tokens with actual values.
#        Delete sections that do not apply (e.g., Background if no shared
#        preconditions, Scenario Outline if no parameterized scenarios).
#
# Rules:
#   - 1 Feature per file, 1 file per functional domain
#   - File naming: kebab-case, e.g., accounts-payable.feature
#   - Encoding: UTF-8 without BOM
#   - Every Scenario MUST have at least 2 tags: classification + module
#   - Every Scenario MUST have Given → When → Then (in that order)
#   - Max 10 steps per Scenario (Given + When + Then + And + But)
#   - Steps must be declarative (WHAT), not imperative (HOW)
#   - Each Scenario tests exactly 1 behavior — atomic and independent
#
# i18n:
#   - When language: "pt" → use Gherkin PT keywords:
#     Funcionalidade, Cenário, Esquema do Cenário, Contexto,
#     Dado, Quando, Então, E, Mas, Exemplos
#   - When language: "en" → use Gherkin EN keywords (as shown below)
#   - Tags (@happy, @sad, etc.) remain in English regardless of language
# ============================================================================

@{{MODULE_TAG}}
Feature: {{FEATURE_NAME}}
  As a {{ROLE}}
  I want {{CAPABILITY}}
  So that {{BUSINESS_VALUE}}

  # ──────────────────────────────────────────────────────────────────────────
  # Background: Shared preconditions for all scenarios in this Feature.
  # Delete this block if no preconditions are shared across scenarios.
  # ──────────────────────────────────────────────────────────────────────────
  Background:
    Given {{SHARED_PRECONDITION_1}}
    And {{SHARED_PRECONDITION_2}}

  # ──────────────────────────────────────────────────────────────────────────
  # HAPPY PATHS — Expected successful behavior
  # Minimum: 1 per Feature
  # ──────────────────────────────────────────────────────────────────────────

  # Source: {{SOURCE_REFERENCE}}
  @happy @{{MODULE_TAG}}
  Scenario: {{HAPPY_PATH_DESCRIPTION}}
    Given {{CONTEXT_STATE}}
    When {{ACTION_EVENT}}
    Then {{OBSERVABLE_OUTCOME}}
    And {{ADDITIONAL_VERIFICATION}}

  # ──────────────────────────────────────────────────────────────────────────
  # SAD PATHS — Error handling, validation failures, edge rejection
  # Minimum: 1 per Feature
  # ──────────────────────────────────────────────────────────────────────────

  # Source: {{SOURCE_REFERENCE}}
  @sad @{{MODULE_TAG}}
  Scenario: {{SAD_PATH_DESCRIPTION}}
    Given {{CONTEXT_STATE}}
    When {{INVALID_ACTION_OR_ERROR_CONDITION}}
    Then {{ERROR_HANDLING_OR_REJECTION}}
    And {{SYSTEM_REMAINS_IN_VALID_STATE}}

  # ──────────────────────────────────────────────────────────────────────────
  # EDGE CASES — Boundary values, nulls, concurrency, permissions
  # Use Scenario Outline when 2+ scenarios differ only in data
  # ──────────────────────────────────────────────────────────────────────────

  # Source: {{SOURCE_REFERENCE}}
  @edge @{{MODULE_TAG}}
  Scenario: {{EDGE_CASE_DESCRIPTION}}
    Given {{BOUNDARY_CONTEXT}}
    When {{BOUNDARY_ACTION}}
    Then {{BOUNDARY_OUTCOME}}

  # Source: {{SOURCE_REFERENCE}}
  @edge @{{MODULE_TAG}}
  Scenario Outline: {{PARAMETERIZED_DESCRIPTION}}
    Given {{CONTEXT_WITH_PARAM}} "<param>"
    When {{ACTION}}
    Then {{OUTCOME_WITH_EXPECTED}} "<expected>"

    Examples:
      | param    | expected  |
      | {{VAL1}} | {{RES1}}  |
      | {{VAL2}} | {{RES2}}  |
      | {{VAL3}} | {{RES3}}  |

  # ──────────────────────────────────────────────────────────────────────────
  # SMOKE (optional) — Critical path for pipeline smoke test
  # Tag with @smoke for CI/CD fast-feedback loop
  # ──────────────────────────────────────────────────────────────────────────

  # Source: {{SOURCE_REFERENCE}}
  @smoke @happy @{{MODULE_TAG}}
  Scenario: {{SMOKE_CRITICAL_PATH_DESCRIPTION}}
    Given {{MINIMAL_CONTEXT}}
    When {{CORE_ACTION}}
    Then {{CORE_OUTCOME}}
