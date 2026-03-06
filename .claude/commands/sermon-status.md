# /sermon-status — Workflow Progress Status

Display current sermon research workflow progress.

## Usage
```
/sermon-status
```

## Reads
- state.yaml (workflow state)
- session.json (domain context)
- todo-checklist.md (detailed progress)

## Display

1. **Current Phase**: Phase 0/1/2/2.5/3
2. **Current Step**: N/130
3. **Progress**: N% complete
4. **Passage**: [selected passage or pending]
5. **Completed Waves**: [list]
6. **Completed Gates**: [list]
7. **Pending Gate Warning**: If a gate has not been executed before current step
8. **SRCS Status**: Overall score (if evaluated)
9. **Last HITL**: [checkpoint name and decision]
10. **Section Progress**: Per-section completion breakdown

## Gate Enforcement
Uses `_sermon_lib.check_pending_gate()` to detect unexecuted gates.
If a gate is pending, displays a warning:
```
WARNING: Gate N has not been executed. Run the gate before proceeding.
```

## No Side Effects
This command only reads — it never modifies state.yaml, session.json, or checklist.
