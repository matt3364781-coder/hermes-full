# OpenClaw / Kimi Claw Workspace Migration Guide

Session: 2026-05-11  
Source: `workspace.zip` from user (OpenClaw/Kimi Claw workspace)  
Target: Hermes Skill (`onebot-3.0`)

## Migration Pattern

### 1. Extract and Inventory

```bash
cd /tmp && unzip -l workspace.zip
```

Key files to look for:
- `AGENTS.md` — constitution with embedded source code
- `BOOTSTRAP.md` — startup rules and structure lock
- `MEMORY.md` — memory constitution
- `SOUL.md` — execution style protocol
- `IDENTITY.md` — output style lock
- `USER.md` — user profile
- `templates/*.md` — report templates
- `scripts/*.py` — utility scripts
- `skills/*/SKILL.md` — individual skills

### 2. Map to Hermes Structure

| OpenClaw Path | Hermes Skill Path | Purpose |
|--------------|-------------------|---------|
| `workspace/AGENTS.md` | `references/AGENTS.md` | Constitution reference |
| `workspace/BOOTSTRAP.md` | `references/BOOTSTRAP.md` | Structure reference |
| `workspace/MEMORY.md` | `references/MEMORY.md` | Memory rules reference |
| `workspace/SOUL.md` | `references/SOUL.md` | Style reference |
| `workspace/IDENTITY.md` | `references/IDENTITY.md` | Output format reference |
| `workspace/templates/*.md` | `templates/*.md` | Copy as-is |
| `workspace/scripts/*.py` | `scripts/*.py` | Copy as-is |
| `workspace/skills/*/SKILL.md` | Merge into main `SKILL.md` | Skill definitions |

### 3. Write SKILL.md

Critical requirements:
- **YAML frontmatter** with `name`, `description`, `version`
- **Trigger conditions** — when should this skill activate
- **Workflow** — step-by-step process
- **Tool mapping** — how ONEBOT modules map to Hermes tools
- **Style rules** — if source had strict output rules, embed them explicitly

### 4. Pitfalls

1. **Do NOT copy constitution files as SKILL.md** — Hermes needs YAML frontmatter and structured body
2. **Style conflicts** — If source had strict output rules (e.g., short-format only), they must be explicitly stated in SKILL.md body. Hermes default style may override them otherwise.
3. **Memory incompatibility** — OpenClaw's `memory_core/` directory structure does not map to Hermes. Use `memory` tool for LTM, `file` tool for diary-like persistence.
4. **Subagent differences** — OpenClaw native subagents → Hermes `delegate_task` tool
5. **Gateway differences** — OpenClaw built-in gateway → Hermes `hermes gateway` command
6. **Constitution injection** — OpenClaw injects AGENTS.md into every prompt; Hermes loads skills on-demand. Key rules must be in SKILL.md body, not just references.

### 5. Verification

After migration:
```
/skill onebot-3.0
```

Test with a task that should trigger the skill's workflow.

## Example: onebot-3.0 Skill Structure

```
onebot-3.0/
├── SKILL.md                          ← Main skill file
├── references/
│   ├── AGENTS.md                     ← 580KB constitution with source
│   ├── BOOTSTRAP.md                  ← Structure lock
│   ├── HEARTBEAT.md                  ← Backup rules
│   ├── IDENTITY.md                   ← Output style
│   ├── MEMORY.md                     ← Memory constitution
│   ├── SOUL.md                       ← Engineer strict mode
│   ├── TOOLS.md                      ← Tool inventory
│   └── USER.md                       ← User profile
├── templates/
│   ├── backtest_report.md
│   ├── event_driven_playbook.md
│   ├── intraday_brief_template.md
│   ├── performance_attribution.md
│   ├── portfolio_monitor.md
│   ├── post_market_wrap_template.md
│   ├── risk_alert_system.md
│   └── weekly_report_template.md
└── scripts/
    ├── compact_prompt.py
    ├── diary_prompt.py
    └── memory_consolidation.py
```
