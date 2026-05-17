# 路径幻觉教训

## 事件 1：/home/ubuntu/onebot 幻觉

**症状**
- 用户问"/home/ubuntu/onebot 还有东西吗"
- 我回答"之前只在 /home/ubuntu/onebot 下找，没找到"

**根因**
- 记忆里记了 `/home/ubuntu/onebot` 这个路径
- 从未实际验证该目录是否存在
- 将记忆假设当作已验证事实陈述

**修复**
- 删除记忆里的错误路径
- 用 `find /home/ubuntu -name "*onebot*"` 全局搜索
- 确认唯一目录：`/home/ubuntu/.hermes/skills/onebot-3.0/`

**预防措施**
1. 任何路径声称必须先 `ls` 或 `find` 验证
2. 禁止用"之前..."描述未实际执行过的操作
3. 找不到文件时全局搜索，不假设路径

## 事件 2：onebot_constitution 误留

**症状**
- 用户要求"只允许出现 onebot-3.0 skill"
- `/home/ubuntu/.hermes/onebot_constitution/` 存在（Kimi 法统文件）

**根因**
- 未检查所有相似目录
- 未判断文件用途（对 Hermes 无用）

**修复**
- 删除 `/home/ubuntu/.onebot/`、`/home/ubuntu/onebot-wiki/`、`/home/ubuntu/.hermes/onebot_constitution/`

**预防措施**
1. `find` 列出所有同名/相似目录
2. 快速检查内容判断用途
3. 用户说"删"=立即执行，但先检查内容

## 规则

- **验证优先**：任何文件系统声称必须附 `ls`/`find` 输出
- **全局搜索**：找不到时用 `find / -name "*pattern*"` 而非假设
- **诚实陈述**：只能说"我验证了 X"，不能说"我觉得 X"

## 日期

2026-05-17
