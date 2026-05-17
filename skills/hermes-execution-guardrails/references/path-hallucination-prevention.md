# 路径幻觉预防 — 2026-05-17

## 规则

1. **任何路径声称必须先验证**
   - 说"文件在 X"前，先 `ls X` 或 `find / -name "*pattern*"`
   - 禁止凭记忆断言文件系统状态

2. **禁止"之前我在..."话术**
   - 禁止用"之前..."描述未实际执行过的操作
   - 只能陈述当前验证结果（"我执行了 find，结果是..."）
   - 找不到文件时："我找不到，让我全局搜索" → 而非 "我之前在 X 找但没找到"

3. **用户说"存在"而我找不到**
   - 不要争辩
   - 正确回应："我这边 find 结果是空，你能给一下绝对路径吗？"
   - 用户知识可能来自另一个环境/分支/机器

4. **记忆里的路径 ≠ 已验证的路径**
   - 记忆可能污染（如 `/home/ubuntu/onebot` 从未存在但被记住）
   - 删除错误记忆后立即验证文件系统

## 踩坑记录

### 事件 1：/home/ubuntu/onebot 幻觉

- **症状**：用户问"/home/ubuntu/onebot 还有东西吗"，我回答"之前只在 /home/ubuntu/onebot 下找，没找到"
- **事实**：该目录从未存在过，我也从未在该目录执行过任何操作
- **根因**：记忆污染，将记忆假设当作已验证事实
- **修复**：`find /home/ubuntu -name "*onebot*"` 全局搜索，确认唯一目录是 `/home/ubuntu/.hermes/skills/onebot-3.0/`

### 事件 2：模块存在性断言错误

- **症状**：用户问 garch_vol/unified_range/minervini 是否存在，我声称"从未存在于 git 历史中"
- **事实**：文件在 `/home/ubuntu/.hermes/skills/onebot-3.0/onebot/quant_core/` 下存在
- **根因**：没先 `find` 检查当前文件系统，仅凭 git log 做绝对断言
- **修复**：`find /home/ubuntu -name "*garch*" -o -name "*unified*" -o -name "*minervini*"`

## 验证命令模板

```bash
# 查找文件
find /home/ubuntu -name "*pattern*" 2>/dev/null

# 确认目录内容
ls -la /path/to/dir

# 全局搜索（确认不存在）
find / -name "*pattern*" 2>/dev/null | grep -v proc
```
