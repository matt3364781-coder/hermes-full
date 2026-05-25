# Telegram Slash Command Setup — Plugin Registration + Menu + i18n

Complete record of how `/forgetless` was registered and the Telegram gateway was customized in the 2026-05-24 session.

## Plugin Command Registration (`ctx.register_command()`)

In `onebot3/__init__.py` → `register(ctx)`:

```python
def register(ctx=None):
    if ctx is not None:
        ctx.register_command(
            name="forgetless",
            handler=_handler_fn,
            description="拉 archive.db N 小时内完整对话原文",
            args_hint="[hours] [session]",
        )
```

### Handler signature
```python
def _handler_fn(raw_args: str) -> str:
    """raw_args = text after /forgetless (e.g. "4", "session", "4 session")"""
```
- Returns a string → delivered as the bot's reply in Telegram
- Can have side effects (e.g. write to temp file)
- Runs in gateway process, synchronous

### Key constraints
- `args_hint` with `[brackets]` = optional arg → appears in Telegram menu
- `args_hint` with `<angle brackets>` = required arg → excluded from Telegram menu (plugin only)
- Command names: lowercase a-z, 0-9, underscores only for Telegram

## Forking the Handler (file vs.display)

For session-handoff commands: handler writes data to `/tmp/forgetless_output.txt`, agent reads it on next turn. Handler returns short confirmation string only:

```python
out_path = "/tmp/forgetless_output.txt"
with open(out_path, "w") as f:
    f.write(output)
return f"📦 已加载过去{hours}小时对话（{session_count}个session/{msg_count}条），继续聊就行"
```

Agent sees the confirmation → knows to read `/tmp/forgetless_output.txt`.

## Hiding Commands from Telegram Menu

Edit `~/.local/lib/python3.12/site-packages/hermes_cli/commands.py`:

```python
TELEGRAM_HIDDEN_COMMANDS: frozenset[str] = frozenset({
    "topic", "branch", "rollback", "approve", "deny",
    "whoami", "profile", "sethome", "codex-runtime", "codex_runtime",
    "personality", "footer", "insights", "platform",
    "bundles", "curator", "kanban", "reload-mcp", "reload_mcp",
    "reload-skills", "reload_skills", "commands", "update", "debug",
    "subgoal", "background",
    # NOTE: Do NOT hide user's custom plugin commands!
})
```

Also filter in `telegram_bot_commands()`:
```python
if tg_name and cmd.name not in TELEGRAM_HIDDEN_COMMANDS:
    desc = ZH_DESCRIPTIONS.get(cmd.name, cmd.description)
    result.append((tg_name, desc))
```

⚠️ Hidden commands still work when typed directly — `is_gateway_known_command()` checks them separately from the menu filter.

## Chinese Descriptions

Add `ZH_DESCRIPTIONS` dict next to `TELEGRAM_HIDDEN_COMMANDS`:
```python
ZH_DESCRIPTIONS: dict[str, str] = {
    "new": "新开 session",
    "retry": "重发上条消息",
    ...
}
```

Only affects built-in commands (plugin commands use their own description from `ctx.register_command()`).

## i18n fix — Missing Locale Files

Hermes i18n (`agent/i18n.py`) looks for `locales/<lang>.yaml` relative to `agent/` parent. If missing, `t()` returns the raw key path (`gateway.usage.header_session_info`).

Fix: create `~/.local/lib/python3.12/site-packages/locales/en.yaml` and `zh.yaml` with nested YAML structure matching the dotted keys:

```yaml
gateway:
  usage:
    no_data: "暂无 session 数据"
    header_session: "Session 用量"
    header_session_info: "Session 信息"
    # ... etc.
```

YAML is flattened at load time by `_flatten_into()` → `gateway.usage.no_data` resolves.

## Files Modified in This Session

| File | Change |
|------|--------|
| `plugins/onebot3/__init__.py` | Added `register_command("forgetless", ...)` in `register(ctx)` |
| `plugins/onebot3/lib/forgetless.py` | Created — reads archive.db by time range |
| `commands.py` | Added `TELEGRAM_HIDDEN_COMMANDS` + `ZH_DESCRIPTIONS` + filter logic |
| `locales/en.yaml` | Created — English i18n catalog |
| `locales/zh.yaml` | Created — Chinese i18n catalog |

## Pitfalls

1. **gateway must restart** — plugin command registration only happens at `register(ctx)` call during gateway startup. Code changes alone don't take effect until `/restart`.
2. **Plugin commands not in GATEWAY_KNOWN_COMMANDS** — they're checked via `_iter_plugin_command_entries()`, separate from the frozenset. `is_gateway_known_command()` handles both.
3. **`cli_only=True` breaks dispatch** — commands marked `cli_only=True` are removed from `GATEWAY_KNOWN_COMMANDS` and return "Unknown command". Use `TELEGRAM_HIDDEN_COMMANDS` instead.
4. **i18n cache is per-process** — after adding locale files, gateway must restart to flush `_catalog_cache`.
5. **argv vs YAML safe_load** — `commands.py` is a `.py` file; YAML i18n catalogs use PyYAML `safe_load`.
