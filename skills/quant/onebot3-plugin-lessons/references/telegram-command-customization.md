# Telegram 命令定制记录

## 目标
把 44 个内置 Telegram `/` 命令精简到用户常用范围，加中文注释。

## 修改文件
`~/.local/lib/python3.12/site-packages/hermes_cli/commands.py`

## 添加内容

### 1. `TELEGRAM_HIDDEN_COMMANDS` — 隐藏的命令集

```python
TELEGRAM_HIDDEN_COMMANDS: frozenset[str] = frozenset({
    "topic", "branch", "rollback", "approve", "deny",
    "whoami", "profile", "sethome", "codex-runtime", "codex_runtime",
    "personality", "footer", "insights", "platform",
    "bundles", "curator", "kanban", "reload-mcp", "reload_mcp",
    "reload-skills", "reload_skills", "commands", "update", "debug",
    "subgoal", "background",
})
```

注意：**不包含**插件命令（`/forgetless`, `/report`）。插件命令是用户的专属工具，不能藏。

### 2. `ZH_DESCRIPTIONS` — 中文描述映射

```python
ZH_DESCRIPTIONS: dict[str, str] = {
    "new": "新开 session",
    "stop": "杀掉后台进程",
    "model": "切换模型",
    ...
}
```

### 3. 过滤逻辑

在 `telegram_bot_commands()` 中两个循环分别加上：

```python
# 内置命令
if tg_name and cmd.name not in TELEGRAM_HIDDEN_COMMANDS:
    desc = ZH_DESCRIPTIONS.get(cmd.name, cmd.description)
    result.append((tg_name, desc))

# 插件命令
if tg_name and name not in TELEGRAM_HIDDEN_COMMANDS:
    result.append((tg_name, description))
```

## 保持 dispatchable

隐藏的命令仍可通过 `is_gateway_known_command()` 被 gateway 正常识别和分发。
不要用 `cli_only=True`，那会让命令完全无法在 Telegram 使用。

## 重启生效

修改后 gateway 重启 → `set_my_commands()` 自动注册新菜单。
