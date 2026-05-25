---
name: forgetless
description: 跨session对话回忆工具 — 从archive.db拉完整对话原文
---

# Forgetless — 跨 Session 对话回忆

## 激活方式（优先级从高到低）

1. **Telegram `/forgetless` 命令** — 输入 `/` 菜单中可见。`/forgetless N` 拉 N 小时，`/forgetless session` 只看清单
2. **说「forgetless」或「查记录」或「拉过去」** — 我问 N，然后跑脚本
3. **直接跑脚本** — `python3 ~/.hermes/plugins/onebot3/lib/forgetless.py --hours N`

## 脚本路径
`~/.hermes/plugins/onebot3/lib/forgetless.py`（onebot3 插件 L5 工具层）

## 注册机制
命令在 `__init__.py` 的 `register(ctx)` 函数中通过 `ctx.register_command()` 注册。gateway 重启后生效，自动出现在 Telegram `/` 菜单。不靠 memory、不靠 skill 加载。

## 关键行为（自动读取模式 — 不可跳过）

这是跨 session 交接工具。用户在新 session 中输入 `/forgetless N` 后：
1. 命令 handler 写入 `/tmp/forgetless_output.txt`
2. 我收到 **「📦 已加载过去N小时对话」** 回执消息
3. **必须立即读取 `/tmp/forgetless_output.txt`** — 这是原始对话记录
4. 读完可以删文件（不删也行，下次覆盖）

⚠️ 不要在回执消息上追问用户「要拉记录吗」或等用户再说一遍——数据已经在文件里了，直接读。用户不耐烦重复说话。

⚠️ 用户有极大概率在我回复之前就察觉我没读文件。不要声称「读完了」或「全在」给摘要骗过去。用户的命令是「每一条全部看」——必须逐段 read_file 读完，不能挑几行取样就说读完了。

## 数据源
- `~/.hermes/memory/archive.db` → conversations 表
- 79MB, 33K+ 条记录，Hermes 框架实时写入
- 用户说的、我回的、工具输出 → 全文可查
