# Hermes i18n Locale 修复

## 问题

`/usage` 等命令显示 `gateway.usage.header_session_info` 等原始键名而非中文翻译。

## 根因

Hermes i18n 系统在 `agent/i18n.py` 中用 `t()` 函数查找 `locales/<lang>.yaml`。
目录路径：`Path(__file__).resolve().parent.parent / "locales"` → `~/.local/lib/python3.12/site-packages/locales/`

该目录在安装时不存在，`_load_catalog()` 返回空字典，`t()` 回退到返回键名本身。

## 修复步骤

```bash
mkdir -p ~/.local/lib/python3.12/site-packages/locales/
```

创建 `locales/en.yaml` 和 `locales/zh.yaml`，嵌套 YAML 结构：

```yaml
gateway:
  usage:
    no_data: "暂无 session 数据"
    header_session: "Session 用量"
    header_session_info: "Session 信息"
    label_messages: "消息数：{count}"
    label_estimated_context: "预估上下文：{count} tokens"
    detailed_after_first: "（首次回复后显示详细信息）"
    # ... etc
```

语法：`_flatten_into()` 将嵌套 YAML 转为扁平键名（`gateway.usage.no_data`）。

## 验证

```python
from agent.i18n import t, reset_language_cache
reset_language_cache()
print(t("gateway.usage.header_session_info", lang="zh"))
# → "Session 信息"
```

## 生效

i18n 缓存进程级，新增/修改文件后必须 gateway 重启刷新 `_catalog_cache`。

## 所有命令的中文描述（ZH_DESCRIPTIONS）

中文翻译定义在 `~/.local/lib/python3.12/site-packages/hermes_cli/commands.py` 的 `ZH_DESCRIPTIONS` 字典中，用于 Telegram 菜单显示。插件命令的描述在 `register()` 的 `ctx.register_command(description="...")` 中直接定义。

## 覆盖的键范围

已在 en.yaml + zh.yaml 中覆盖的最常用 gateway key：
- `gateway.usage.*` — /usage 命令
- `gateway.agents.*` — /agents 命令
- `gateway.help.*` — /help 命令
- `gateway.status.*` — /status 命令
- `gateway.stop.*` — /stop 命令
- `gateway.retry.*|undo.*|compress.*` — 消息控制
- `gateway.model.*|goal.*|fast.*|reasoning.*|voice.*|yolo.*` — 配置
- `gateway.restart.*|approve.*|deny.*` — 运维

缺失的 key 会回退到英文，再缺失就显示键名本身（被动安全）。
