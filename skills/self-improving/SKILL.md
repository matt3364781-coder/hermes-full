---
name: self-improving
description: >
  Self-improving agent skill. Tracks task outcomes, learns from errors,
  auto-generates improved workflows, and maintains persistent memory
  of what works and what doesn't. Use when you want the agent to get
  better over time at specific types of tasks.
category: agent-enhancement
---

# Self-Improving Skill

## Purpose

This skill enables the agent to learn from experience and improve its
performance over time. It tracks:
- Task success/failure rates
- Common error patterns
- Effective workflows
- User preferences and corrections

## How It Works

### 1. Outcome Tracking

After completing any complex task (5+ tool calls), the skill automatically:
- Records the task type and complexity
- Notes errors encountered and how they were resolved
- Saves successful workflows as reusable patterns

### 2. Error Pattern Recognition

The skill maintains a database of error patterns:
```
error_patterns.json
{
  "pattern": "ModuleNotFoundError: No module named 'x'",
  "context": "Python import failure",
  "solution": "pip install x",
  "frequency": 3,
  "last_seen": "2026-05-12"
}
```

### 3. Workflow Optimization

Successful multi-step workflows are saved as reusable templates:
```
workflows/
  fix-import-error.md
  debug-api-401.md
  setup-new-provider.md
```

### 4. Memory Integration

Learned patterns are written to:
- `memory` (environment facts, tool quirks)
- `user` (preferences, corrections)
- Skills are updated with new pitfalls and solutions

## Usage

### Automatic Mode

The skill activates automatically after complex tasks. No user action needed.

**Proactive Mode (2026-05-14):** User expects the agent to update `state.json` without being asked. After every:
- User correction ("don't do X, do Y")
- Bug discovery and fix
- Significant finding or decision
- Session topic shift

→ Immediately write to `~/.hermes/self-improving/state.json`. Do NOT wait for user to say "record this".

Set `"active_mode": true` in state.json to signal proactive tracking is on.

### Manual Review

To review what the agent has learned:
```
What have you learned from our recent sessions?
Show me your error patterns.
What workflows have you saved?
```

### Apply Learned Patterns

When starting a similar task, the skill pre-loads relevant patterns:
```
[Self-Improving] Loading 3 relevant patterns for "API debugging"
[Self-Improving] Applied pattern: "Check auth headers first"
```

## Storage

```
~/.hermes/self-improving/
  error_patterns.json      # Error → Solution mappings
  workflows/               # Reusable workflow templates
  performance.json         # Task success rates by category
  corrections.json         # User corrections and preferences
```

## Integration with ONEBOT

When working with ONEBOT 3.0, this skill also tracks:
- Prediction accuracy by layer
- Weight configuration effectiveness
- Market regime detection accuracy
- Model performance (Kronos, XGBoost, etc.)

## Commands

| Command | Description |
|---------|-------------|
| `learn from this` | Manually trigger learning from last task |
| `show patterns` | Display learned error patterns |
| `show workflows` | Display saved workflows |
| `show performance` | Display performance metrics |
| `forget pattern <id>` | Remove a learned pattern |
| `export learnings` | Export all learned data |

## Best Practices

1. **Correct the agent explicitly** — "Don't do X, do Y instead" is recorded
2. **Confirm good outputs** — "That was perfect" reinforces patterns
3. **Review periodically** — Ask "What have you learned?" weekly
4. **Clean up** — Remove outdated patterns with `forget pattern`

## Pitfalls

- **Loading ≠ active** — The skill directory existing does NOT mean outcomes are being tracked. The skill must be explicitly invoked or triggered by 5+ tool calls. A `state.json` with zero entries is an empty shell.
- **Scaffold ≠ working** — Creating directories and empty JSON files is NOT the same as recording real session outcomes. Verify with `cat ~/.hermes/self-improving/state.json` that actual data exists.
- **No autonomous reflection** — Unlike OpenClaw's dreams, this skill does NOT autonomously review past sessions. It only records what is explicitly fed to it. Pair with cron for autonomous behavior.

## 用户纠正自动检测（2026-05-16 优化）

基于 OpenClaw Self-Improving 机制，增强 Hermes 的自动学习：

### 检测信号

**必须记录的用户纠正模式**：
- "不对" / "错了" / "不是" / "你没听懂"
- "我说了" / "我跟你说了" / "我不是这么说的"
- "停止" / "别" / "不要" / "听明白了吗"
- "你能不能" → 用户问可行性，不等于执行许可
- "全部干好了再给我打报告" → 禁止中途汇报
- "别他妈墨迹了" → 立即执行，零解释
- "有没有吹牛逼" → 用户测试验证

**偏好信号**（记录到 user profile）：
- "我喜欢" / "我讨厌" / "以后"
- "记住这个" / "别忘了"
- " Chicago TZ" / "用 mv 不用 cp"

### 三级记忆存储

```
~/.hermes/self-improving/
├── memory.md          # HOT: ≤50 条，每次对话加载
├── corrections.json   # 最近 50 条纠正
├── patterns/          # WARM: 错误模式 → 解决方案
│   ├── fix-import-error.md
│   ├── verify-before-claim.md
│   └── stop-on-stop.md
└── archive/           # COLD: 过期模式
```

### 自动写入规则

**触发条件**（满足任一即写入）：
1. 用户明确纠正（"不对，应该是 X"）
2. 用户表达挫败（"你又忘了" / "我说过"）
3. 任务失败（代码报错、测试不通过）
4. 用户确认正确（"可以了" / "就这么办"）

**写入位置**：
- 纠正 → `corrections.json`（追加，保留最近 50 条）
- 偏好 → `memory`（用户 profile）
- 模式 → `patterns/`（3 次重复 → 升级为模式）

### 反思日志格式

每次复杂任务（5+ 工具调用）后自动记录：

```json
{
  "timestamp": "2026-05-16T11:00:00Z",
  "task": "合并 skills",
  "tool_calls": 12,
  "errors": 0,
  "user_corrections": ["删除未使用的 skills"],
  "lessons": ["先列清单再执行，避免遗漏"],
  "outcome": "success"
}
```

### 禁止行为

- 不要等用户说"记住这个"才记录
- 不要等任务结束才反思（中途发现问题立即记）
- 不要把临时指令记为永久偏好（"这次用 X" ≠ "以后都用 X"）
- 不要重复记录相同纠正（检查是否已存在）
