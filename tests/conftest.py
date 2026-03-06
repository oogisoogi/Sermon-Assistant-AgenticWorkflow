"""Shared fixtures for all test layers."""

import json
import os
import sys
import subprocess
import tempfile
import shutil

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, ".claude", "hooks", "scripts")
AGENTS_DIR = os.path.join(PROJECT_ROOT, ".claude", "agents")
COMMANDS_DIR = os.path.join(PROJECT_ROOT, ".claude", "commands")
SKILLS_DIR = os.path.join(PROJECT_ROOT, ".claude", "skills")
SETTINGS_PATH = os.path.join(PROJECT_ROOT, ".claude", "settings.json")

# Ensure scripts directory is importable
sys.path.insert(0, SCRIPTS_DIR)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def project_root():
    return PROJECT_ROOT


@pytest.fixture
def scripts_dir():
    return SCRIPTS_DIR


@pytest.fixture
def tmp_project(tmp_path):
    """Create a minimal temporary project directory for isolated tests."""
    proj = tmp_path / "test_project"
    proj.mkdir()
    (proj / ".claude" / "context-snapshots" / "sessions").mkdir(parents=True)
    (proj / ".claude" / "hooks" / "scripts").mkdir(parents=True)
    return proj


@pytest.fixture
def tmp_sermon_project(tmp_path):
    """Create a temporary project with sermon workflow structure."""
    proj = tmp_path / "sermon_project"
    proj.mkdir()
    (proj / ".claude" / "context-snapshots").mkdir(parents=True)
    (proj / "verification-logs").mkdir()
    (proj / "pacs-logs").mkdir()
    (proj / "review-logs").mkdir()
    return proj


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def run_hook_script(script_name, stdin_data=None, args=None, env_override=None,
                    timeout=30):
    """Run a hook script via subprocess and return (exit_code, stdout, stderr).

    Args:
        script_name: Filename in .claude/hooks/scripts/
        stdin_data: dict or string to pass via stdin
        args: list of CLI arguments
        env_override: dict of environment variable overrides
        timeout: seconds before killing the process
    """
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    cmd = [sys.executable, script_path]
    if args:
        cmd.extend(args)

    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = PROJECT_ROOT
    if env_override:
        env.update(env_override)

    stdin_str = None
    if stdin_data is not None:
        stdin_str = json.dumps(stdin_data) if isinstance(stdin_data, dict) else str(stdin_data)

    result = subprocess.run(
        cmd,
        input=stdin_str,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    return result.returncode, result.stdout, result.stderr


def run_validation_script(script_name, cli_args, project_dir=None, timeout=30):
    """Run a validation script with CLI args and return parsed JSON output.

    Returns: (exit_code, parsed_json_or_None, raw_stdout, raw_stderr)
    """
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    cmd = [sys.executable, script_path] + cli_args
    if project_dir:
        cmd.extend(["--project-dir", str(project_dir)])

    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout,
    )
    parsed = None
    if result.stdout.strip():
        try:
            parsed = json.loads(result.stdout)
        except json.JSONDecodeError:
            pass
    return result.returncode, parsed, result.stdout, result.stderr
