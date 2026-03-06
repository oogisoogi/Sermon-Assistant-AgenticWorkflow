#!/usr/bin/env python3
"""
PostToolUse Hook — GroundedClaim Validation

Validates GroundedClaim format in sermon research output files.
Fires on Edit|Write, but only validates files in research-package/ directories.

Triggered by: PostToolUse with matcher "Edit|Write"
Exit code: 0 (warning only — never blocks)

P1 Compliance: All validation is deterministic via _sermon_lib.py functions.
"""

import json
import os
import re
import sys
from typing import Optional

# Add script directory to path
sys.path.insert(0, os.path.dirname(__file__))

try:
    from _sermon_lib import (
        check_hallucination_firewall,
        has_blocking_hallucination,
        validate_claims_batch,
    )
except ImportError:
    # If _sermon_lib not available, exit silently
    sys.exit(0)


def _extract_yaml_claims(content: str) -> Optional[list[dict]]:
    """Extract claims from markdown content with embedded YAML.

    Looks for ```yaml blocks containing 'claims:' key.
    Falls back to simple regex extraction if YAML parsing fails.
    """
    try:
        import yaml
    except ImportError:
        print("WARNING: PyYAML not installed, GroundedClaim validation skipped.",
              file=sys.stderr)
        return None

    # Find YAML blocks
    yaml_blocks = re.findall(
        r"```ya?ml\s*\n(.*?)```",
        content,
        re.DOTALL,
    )

    for block in yaml_blocks:
        try:
            data = yaml.safe_load(block)
            if isinstance(data, dict) and "claims" in data:
                return data["claims"]
        except (yaml.YAMLError, AttributeError):
            continue

    return None


def _get_agent_from_filename(filename: str) -> Optional[str]:
    """Map output filename to agent name."""
    file_agent_map = {
        "01-original-text-analysis.md": "original-text-analyst",
        "02-translation-manuscript-comparison.md": "manuscript-comparator",
        "03-structural-analysis.md": "structure-analyst",
        "04-parallel-passage-analysis.md": "parallel-passage-analyst",
        "05-theological-analysis.md": "theological-analyst",
        "06-literary-analysis.md": "literary-analyst",
        "07-rhetorical-analysis.md": "rhetorical-analyst",
        "08-historical-cultural-context.md": "historical-context-analyst",
        "09-keyword-study.md": "keyword-expert",
        "10-biblical-geography.md": "biblical-geography-expert",
        "11-historical-cultural-background.md": "historical-cultural-expert",
    }
    return file_agent_map.get(os.path.basename(filename))


def main():
    """Read PostToolUse JSON from stdin, validate if sermon research output."""
    try:
        stdin_data = sys.stdin.read()
        if not stdin_data.strip():
            sys.exit(0)

        payload = json.loads(stdin_data)

        # Get the file path from tool_input
        tool_input = payload.get("tool_input", {})
        file_path = tool_input.get("file_path", "")

        if not file_path:
            sys.exit(0)

        # Only validate files in research-package/ directories
        if "research-package/" not in file_path:
            sys.exit(0)

        # Only validate .md files
        if not file_path.endswith(".md"):
            sys.exit(0)

    except (json.JSONDecodeError, KeyError, TypeError):
        sys.exit(0)

    # Read the file content
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        sys.exit(0)

    warnings: list[str] = []

    # 1. Hallucination Firewall check
    if has_blocking_hallucination(content):
        findings = check_hallucination_firewall(content)
        block_findings = [f for f in findings if f["level"] == "BLOCK"]
        for finding in block_findings[:3]:  # Limit to 3 warnings
            warnings.append(
                f"HALLUCINATION FIREWALL [{finding['level']}]: "
                f"'{finding['match']}' at position {finding['position']}"
            )

    # 2. GroundedClaim validation (if claims found)
    claims = _extract_yaml_claims(content)
    if claims is not None:
        agent_name = _get_agent_from_filename(file_path)
        result = validate_claims_batch(claims, agent_name=agent_name)
        if not result["valid"]:
            for err in result["errors"][:5]:  # Limit to 5 errors
                warnings.append(f"CLAIM VALIDATION: {err}")
            if result["duplicate_ids"]:
                warnings.append(
                    f"DUPLICATE IDs: {result['duplicate_ids']}"
                )

    # Output warnings via stderr (informational, never blocking)
    if warnings:
        print(
            f"SERMON GRA CHECK ({os.path.basename(file_path)}):\n"
            + "\n".join(f"  - {w}" for w in warnings),
            file=sys.stderr,
        )

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Safety-first: never block on unexpected errors
        sys.exit(0)
