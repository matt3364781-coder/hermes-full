# Skill 库清理记录 — 2026-05-16

## 背景

用户要求清理 skill 库，合并相似 skills，删除未使用的，优化结构。

## 执行操作

### 1. 合并相似 Skills

| 合并前 | 合并后 | 说明 |
|--------|--------|------|
| chinese-code-review | chinese-dev-toolkit | 4 个合并为 1 个 umbrella |
| chinese-commit-conventions | ↑ | ↑ |
| chinese-documentation | ↑ | ↑ |
| chinese-git-workflow | ↑ | ↑ |
| github | github-toolkit | 5 个合并为 1 个 umbrella |
| github-code-review | ↑ | ↑ |
| github-pr-workflow | ↑ | ↑ |
| github-issues | ↑ | ↑ |
| github-repo-management | ↑ | ↑ |
| writing-plans | dev-lifecycle | 3 个合并为 1 个 umbrella |
| executing-plans | ↑ | ↑ |
| finishing-a-development-branch | ↑ | ↑ |

### 2. 归入现有 Umbrella

| 原 Skill | 归入 | 说明 |
|----------|------|------|
| onebot-3.0-deploy | onebot-3.0/subskills/deploy/ | 最小部署包 |
| onebot-github-repo | onebot-3.0/subskills/github-repo/ | 仓库凭证 |
| onebot-3.0-backup-20260516_022600 | 删除 | 过期备份 |

### 3. 删除未使用的 Skills

删除列表（确认未使用）：
- gaming
- dogfood
- gifs
- apple
- diagramming
- domain
- inference-sh
- data-science
- devops
- email
- media
- note-taking
- red-teaming
- smart-home
- social-media
- yuanbao

### 4. 清理缓存和垃圾

```bash
# 清理 Hermes 缓存
rm -rf ~/.hermes/cache/* ~/.hermes/logs/* ~/.hermes/audio_cache/* ~/.hermes/image_cache/*

# 清理旧 sessions（保留最近 10 个）
cd ~/.hermes/sessions && ls -t | tail -n +11 | xargs rm -rf

# 清理 __pycache__
find ~/.hermes/skills/ -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# 清理 .pyc
find ~/.hermes/skills/ -type f -name "*.pyc" -delete 2>/dev/null

# 清理嵌入式 .git
find ~/.hermes/skills/ -type d -name ".git" -exec rm -rf {} + 2>/dev/null
```

## 结果

- **清理前**: 53 个 skills
- **清理后**: 32 个 skills
- **减少**: 21 个（40%）

## 保留的 32 个 Skills

anysearch-skill, autonomous-ai-agents, baidu-netdisk-storage, brainstorming, chinese-dev-toolkit, creative, data-science, dev-lifecycle, devops, dispatching-parallel-agents, email, github-toolkit, hermes-atlas-navigator, hermes-execution-guardrails, hermes-skill-factory, llm-wiki, mcp, mcp-builder, media, mlops, note-taking, onebot-3.0, productivity, receiving-code-review, red-teaming, requesting-code-review, research, self-improving, smart-home, social-media, software-development, subagent-driven-development, systematic-debugging, test-driven-development, token-optimizer, using-git-worktrees, using-superpowers, verification-before-completion, workflow-runner, writing-skills, yuanbao

## 教训

1. **定期清理**: Skill 数量会自然增长，需要主动维护
2. **合并优于删除**: 相似功能合并为 umbrella，保留知识
3. **凭证固化**: 地址/token 必须存为独立 skill，不能依赖 memory
4. **用户纠正 = 立即行动**: "你老是忘记..." → 立即创建 skill
