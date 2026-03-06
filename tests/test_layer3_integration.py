"""
Layer 3: Workflow Integration Tests
=====================================
Multi-script scenarios that test interactions between scripts.
"""

import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(__file__))
from conftest import run_hook_script, run_validation_script, SCRIPTS_DIR, PROJECT_ROOT


# ============================================================================
# 1. Retry Budget: Full lifecycle (check → increment → exhaust)
# ============================================================================
class TestRetryBudgetLifecycle:
    """Integration: retry budget from fresh → exhausted."""

    @pytest.mark.integration
    def test_full_budget_cycle(self, tmp_sermon_project):
        """Exhaust budget via repeated --check-and-increment, then verify denial."""
        gate = "verification"
        step = "1"

        # Fill up to max (DEFAULT=10)
        for i in range(10):
            code, parsed, _, _ = run_validation_script(
                "validate_retry_budget.py",
                ["--step", step, "--gate", gate, "--check-and-increment"],
                project_dir=tmp_sermon_project,
            )
            assert code == 0
            assert parsed["can_retry"] is True
            assert parsed["retries_used"] == i + 1

        # 11th attempt: should be denied
        code, parsed, _, _ = run_validation_script(
            "validate_retry_budget.py",
            ["--step", step, "--gate", gate, "--check-and-increment"],
            project_dir=tmp_sermon_project,
        )
        assert code == 0
        assert parsed["can_retry"] is False
        assert parsed["budget_remaining"] == 0
        assert parsed["incremented"] is False  # shouldn't increment when denied

    @pytest.mark.integration
    def test_separate_gates_independent(self, tmp_sermon_project):
        """Different gates should have independent budgets."""
        for gate in ("verification", "pacs", "review"):
            code, parsed, _, _ = run_validation_script(
                "validate_retry_budget.py",
                ["--step", "1", "--gate", gate, "--check-and-increment"],
                project_dir=tmp_sermon_project,
            )
            assert parsed["retries_used"] == 1

        # Each gate should be at 1, not 3
        for gate in ("verification", "pacs", "review"):
            code, parsed, _, _ = run_validation_script(
                "validate_retry_budget.py",
                ["--step", "1", "--gate", gate],
                project_dir=tmp_sermon_project,
            )
            assert parsed["retries_used"] == 1


# ============================================================================
# 2. Validation Chain: pACS → Review → Translation dependencies
# ============================================================================
class TestValidationChain:
    """Integration: validation scripts work with shared filesystem state."""

    @pytest.mark.integration
    def test_pacs_and_retry_share_project_dir(self, tmp_sermon_project):
        """Both scripts should work with the same project directory."""
        # pACS check (will fail — no log file)
        code1, parsed1, _, _ = run_validation_script(
            "validate_pacs.py",
            ["--step", "1"],
            project_dir=tmp_sermon_project,
        )
        assert parsed1["valid"] is False

        # Retry check (should still work — different concern)
        code2, parsed2, _, _ = run_validation_script(
            "validate_retry_budget.py",
            ["--step", "1", "--gate", "pacs"],
            project_dir=tmp_sermon_project,
        )
        assert parsed2["valid"] is True
        assert parsed2["can_retry"] is True

    @pytest.mark.integration
    def test_pacs_with_l0_check(self, tmp_sermon_project):
        """--check-l0 should add L0 validation alongside PA checks."""
        code, parsed, _, _ = run_validation_script(
            "validate_pacs.py",
            ["--step", "1", "--check-l0"],
            project_dir=tmp_sermon_project,
        )
        assert code == 0
        assert "l0_valid" in parsed
        assert "l0_warnings" in parsed


# ============================================================================
# 3. PreToolUse Guard Orchestration
# ============================================================================
class TestGuardOrchestration:
    """Integration: multiple PreToolUse hooks on the same action."""

    @pytest.mark.integration
    def test_destructive_and_tdd_independent(self, tmp_path):
        """block_destructive + block_test_file_edit are independent concerns."""
        (tmp_path / ".tdd-guard").touch()

        # Destructive command on non-test file → blocked by destructive guard
        code1, _, err1 = run_hook_script(
            "block_destructive_commands.py",
            stdin_data={"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}},
            env_override={"CLAUDE_PROJECT_DIR": str(tmp_path)},
        )
        assert code1 == 2

        # Safe edit on test file → blocked by TDD guard
        code2, _, err2 = run_hook_script(
            "block_test_file_edit.py",
            stdin_data={"tool_name": "Edit", "tool_input": {
                "file_path": str(tmp_path / "tests" / "test_main.py"),
            }},
            env_override={"CLAUDE_PROJECT_DIR": str(tmp_path)},
        )
        assert code2 == 2

        # Safe edit on non-test file → both guards allow
        code3, _, _ = run_hook_script(
            "block_destructive_commands.py",
            stdin_data={"tool_name": "Bash", "tool_input": {"command": "echo hello"}},
            env_override={"CLAUDE_PROJECT_DIR": str(tmp_path)},
        )
        assert code3 == 0

    @pytest.mark.integration
    def test_secret_filter_and_sensitive_guard_both_run(self):
        """Both PostToolUse hooks can run on the same sensitive file write."""
        # Secret filter for Read of .env
        code1, _, err1 = run_hook_script(
            "output_secret_filter.py",
            stdin_data={
                "tool_name": "Read",
                "tool_response": {
                    "type": "text",
                    "file": {
                        "filePath": ".env",
                        "content": "API_KEY=sk-proj-abc123def456ghi789jkl012mno345pqr\n",
                    },
                },
                "tool_input": {"file_path": ".env"},
            },
        )
        assert code1 == 0

        # Sensitive file guard for Write to .env
        code2, _, _ = run_hook_script(
            "security_sensitive_file_guard.py",
            stdin_data={"tool_input": {"file_path": ".env"}},
        )
        assert code2 == 0


# ============================================================================
# 4. Setup → Validation Pipeline
# ============================================================================
class TestSetupValidationPipeline:
    """Integration: setup_init validates scripts that validation scripts depend on."""

    @pytest.mark.integration
    def test_setup_validates_all_validation_scripts_exist(self):
        """setup_init should verify all validation scripts are present."""
        code, out, err = run_hook_script(
            "setup_init.py",
            stdin_data={"source": "init"},
            env_override={"CLAUDE_PROJECT_DIR": PROJECT_ROOT},
        )
        assert code == 0
        # The output should mention script validation
        combined = out + err
        assert "script" in combined.lower() or "PASS" in combined or "hook" in combined.lower()


# ============================================================================
# 5. Workflow Validation: Multiple validators on same project
# ============================================================================
class TestMultiValidatorScenario:
    """Integration: running multiple validators against the same project state."""

    @pytest.mark.integration
    def test_all_validators_handle_empty_project(self, tmp_sermon_project):
        """All validation scripts should return valid JSON on empty project."""
        validators = [
            ("validate_pacs.py", ["--step", "1"]),
            ("validate_retry_budget.py", ["--step", "1", "--gate", "verification"]),
            ("validate_traceability.py", ["--step", "1"]),
        ]
        for script, args in validators:
            code, parsed, _, _ = run_validation_script(
                script, args, project_dir=tmp_sermon_project,
            )
            assert code == 0, f"{script} crashed with exit code {code}"
            assert parsed is not None, f"{script} did not return valid JSON"
            assert "valid" in parsed, f"{script} missing 'valid' field"
