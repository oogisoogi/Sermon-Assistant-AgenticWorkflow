# /sermon-resume — Context Reset Recovery

Resume the sermon research workflow after a context reset.

## Usage
```
/sermon-resume
```

## Reads
- session.json (domain context + HITL snapshots)
- todo-checklist.md (progress tracking)
- research-synthesis.md (research insights, if available)

## Recovery Process

1. Read session.json to recover:
   - Input mode and passage
   - Options and settings
   - Last HITL snapshot

2. Read todo-checklist.md to determine:
   - Last completed step
   - Next step to execute
   - Overall progress percentage

3. Read research-synthesis.md (if exists) for:
   - Compressed research findings
   - Key insights for downstream phases

4. Display recovery summary:
   ```
   Sermon Research Workflow — Context Recovery
   Passage: [passage]
   Mode: [mode]
   Progress: [N]% (Step [M]/130)
   Last completed: [section name]
   Next step: [description]
   ```

5. Resume execution from the next incomplete step

## Context Reset Points
- After HITL-2: Load session.json + research-synthesis.md + checklist
- After HITL-3b: Load session.json + sermon-outline.md + synthesis + checklist
- After HITL-5b: Load session.json + sermon-final.md + checklist

## RLM Pattern
This command provides domain-specific pointers on TOP of the framework's existing restore_context.py recovery. It does NOT modify or replace the framework's context preservation system.
