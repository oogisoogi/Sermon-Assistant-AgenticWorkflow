# /sermon-start — Sermon Research Workflow Entry Point

Start the Sermon Research Workflow. This command initializes Phase 0 and begins orchestration.

## Usage
```
/sermon-start [mode] [input]
```

## Arguments
- **mode**: `theme` (default) | `passage` | `series`
- **input**: The topic, passage reference, or series description

## Examples
```
/sermon-start theme Trusting God in times of suffering
/sermon-start passage Psalm 23:1-6
/sermon-start series John Gospel series - Week 3 (John 3:1-21)
```

## Execution

1. Load the sermon-orchestrator skill
2. Detect input mode using `_sermon_lib.detect_input_mode()` if not specified
3. Create output directory structure via `_sermon_lib.create_output_structure()`
4. Initialize session.json via `_sermon_lib.generate_session_json()`
5. Generate 130-step checklist via `_sermon_lib.generate_checklist()`
6. Initialize state.yaml with sermon workflow fields
7. Check `user-resource/` for user-provided materials
8. If Mode A: dispatch `@passage-finder` for candidate passages
9. If Mode C: dispatch `@series-analyzer` for series context
10. If Mode B: proceed directly to HITL-1 with provided passage
11. Present HITL-1 options to user

## SOT Initialization
```yaml
workflow:
  name: "sermon-research"
  current_step: 1
  status: "running"
  sermon:
    mode: "{detected_mode}"
    output_dir: "{generated_dir}"
    completed_gates: []
```
