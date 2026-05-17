# Hermes Constitution Fusion — Project Rules Integration Guide

> How to fuse project-specific rules (constitution) into Hermes Agent's system prompt.
> Session: 2026-05-13. Verified against `prompt_builder.py` and `run_agent.py`.

## System Prompt Layer Architecture (Code-Verified)

```
Layer 1:  SOUL.md (~/.hermes/SOUL.md) → OR fallback DEFAULT_AGENT_IDENTITY
Layer 2:  HERMES_AGENT_HELP_GUIDANCE (hardcoded)
Layer 3:  MEMORY_GUIDANCE / SESSION_SEARCH / SKILLS (hardcoded, conditional)
Layer 4:  Nous subscription prompt (hardcoded, conditional)
Layer 5:  TOOL_USE_ENFORCEMENT_GUIDANCE (hardcoded, conditional)
Layer 6:  system_message (gateway injected)
Layer 7:  Persistent memory (user + memory blocks)
Layer 8:  Skills guidance (loaded skills)
Layer 9:  Context files (.hermes.md / AGENTS.md / CLAUDE.md / .cursorrules)
Layer 10: Timestamp + platform hints
```

**Key facts:**
- SOUL.md and DEFAULT_AGENT_IDENTITY are **mutually exclusive** — SOUL.md wins if non-empty
- Context files are **mutually exclusive** — first match wins: `.hermes.md` > `AGENTS.md` > `CLAUDE.md` > `.cursorrules`
- Each context source capped at **20,000 chars** (`CONTEXT_FILE_MAX_CHARS`)
- SOUL.md has **no explicit cap** but goes through `_truncate_content()` with same 20K default
- Hardcoded guidance **cannot be modified** without forking Hermes source

## Three-Layer Fusion Strategy (Optimal)

For projects needing strong constitutional enforcement (e.g., quant trading systems):

| Layer | File | Content | Size Limit | Actual Layer |
|-------|------|---------|-----------|--------------|
| 1 | `~/.hermes/SOUL.md` | Core identity + hard rules + execution style | ~20K | 1 |
| 2 | `<project>/.hermes.md` | Workflow rules + entrypoints + key fixes | 20K | 9 |
| 3 | `~/.hermes/skills/<project>/` | Full detail + references + scripts | No limit | 8 |

**Why this works:**
- SOUL.md at Layer 1 **overrides** DEFAULT_AGENT_IDENTITY completely
- `.hermes.md` at Layer 9 provides project context when cwd is in project directory
- Skill at Layer 8 loads on-demand with unlimited size for detailed procedures

## SOUL.md Template

```markdown
---
name: project-identity
version: 1.0.0
---

# PROJECT NAME — AI Execution Identity

You are the AI execution layer of [PROJECT]. Your human is [ROLE] who [EXPECTATIONS].

## HARD RULES (Absolute, Non-Negotiable)

1. **NO LYING** — Never claim completion without execution.
2. **NO SELF-AUTHORIZED ACTIONS** — AI packages data; human decides.
3. **NO UNVERIFIED CLAIMS** — Distinguish: fully fixed / partially fixed / not fixed.
4. **STOP ON UNCERTAINTY** — STOP → UNKNOWN → wait for instruction.
5. **SOURCE IS CANONICAL** — [source file] is single source of truth.

## EXECUTION STYLE

- Zero fluff. Zero emotion. Zero chitchat.
- Output must be immediately usable.
- One-shot completion. No stopping halfway.
- Structure: conclusion → score → brief comment → executable.

## ARCHITECTURE

[Minimal framework description]

## ENVIRONMENT

- Workspace: `/path/`
- Key tools: [list]
- Timezone: [timezone]
```

## .hermes.md Template

```markdown
---
name: project-context
title: PROJECT Context
version: 1.0.0
---

# PROJECT — Project Context

## Core Entrypoint

```python
[minimal runnable example]
```

## Workflow Rules

1. [rule 1]
2. [rule 2]

## Key Fixes

| Fix | File | Detail |
|-----|------|--------|
| [name] | [path] | [description] |

## Data Sources

- [source] ✅/[source] ❌
```

## Pitfalls

### "Architecture.md as Layer 2" — Does Not Work

Hermes only recognizes 4 context file types (`.hermes.md`, `AGENTS.md`, `CLAUDE.md`, `.cursorrules`). Custom filenames like `Architecture.md` or `append.md` are **not loaded**.

### "Multiple Context Files" — Does Not Work

Context files are **first-match-wins**, not cumulative. You cannot have both `.hermes.md` and `AGENTS.md` loaded together.

### "SOUL.md for Full Constitution" — Too Big

AGENTS.md-style full constitution (600KB+) exceeds 20K cap. Extract **core rules only** into SOUL.md, put details in skill.

### "Modifying Hardcoded Guidance" — Requires Fork

`DEFAULT_AGENT_IDENTITY`, `MEMORY_GUIDANCE`, etc. are Python constants in `prompt_builder.py`. Changing them requires:
1. Editing `~/.hermes/hermes-agent/agent/prompt_builder.py`
2. Reinstalling Hermes from modified source
3. Re-applying changes after every update

**Not recommended** for production setups.

## Verification Commands

```bash
# Check SOUL.md loaded
head -5 ~/.hermes/SOUL.md

# Check .hermes.md discovered
cd /path/to/project && python3 -c "
from pathlib import Path
import sys
sys.path.insert(0, '~/.hermes/hermes-agent')
from agent.prompt_builder import _find_hermes_md
print(_find_hermes_md(Path.cwd()))
"

# Check skill installed
ls ~/.hermes/skills/<project>/
```
