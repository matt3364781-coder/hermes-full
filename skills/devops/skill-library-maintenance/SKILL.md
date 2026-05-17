---
name: skill-library-maintenance
description: Hermes Skill 库维护 — 合并、清理、优化、凭证固化
version: 1.0.0
tags: [hermes, skills, maintenance, consolidation]
---

# Skill 库维护

## 合并策略

当 skill 数量过多（>50）或存在重复功能时，执行合并：

### 1. 识别可合并组

扫描 `~/.hermes/skills/` 目录，按领域分组：

```bash
ls ~/.hermes/skills/ | sort
```

常见合并模式：
- `chinese-code-review` + `chinese-commit-conventions` + `chinese-documentation` + `chinese-git-workflow` → `chinese-dev-toolkit`
- `github` + `github-code-review` + `github-pr-workflow` + `github-issues` + `github-repo-management` → `github-toolkit`
- `writing-plans` + `executing-plans` + `finishing-a-development-branch` → `dev-lifecycle`
- `onebot-3.0-deploy` + `onebot-github-repo` → `onebot-3.0/subskills/`

### 2. 合并执行步骤

```bash
# 1. 创建 umbrella skill
mkdir -p ~/.hermes/skills/NEW-UMBRELLA

# 2. 复制子 skill 内容（保留 SKILL.md 作为子文件）
cp ~/.hermes/skills/skill-a/SKILL.md ~/.hermes/skills/NEW-UMBRELLA/skill-a.md
cp ~/.hermes/skills/skill-b/SKILL.md ~/.hermes/skills/NEW-UMBRELLA/skill-b.md

# 3. 创建索引 SKILL.md
cat > ~/.hermes/skills/NEW-UMBRELLA/SKILL.md << 'EOF'
---
name: NEW-UMBRELLA
description: 合并描述
tags: [tag1, tag2]
---

# NEW-UMBRELLA

包含子模块：
- **skill-a.md** — 描述
- **skill-b.md** — 描述
EOF

# 4. 删除旧 skills
rm -rf ~/.hermes/skills/skill-a ~/.hermes/skills/skill-b
```

### 3. 归入现有 Umbrella

如果目标 umbrella 已存在，直接放入 `subskills/`：

```bash
mkdir -p ~/.hermes/skills/EXISTING/subskills/
cp -r ~/.hermes/skills/skill-to-merge ~/.hermes/skills/EXISTING/subskills/
rm -rf ~/.hermes/skills/skill-to-merge

# 更新 umbrella 的 SKILL.md 添加子技能索引
```

## 清理策略

### 删除未使用的 skills

**判断标准**（满足任一即可删除）：
1. 最后修改时间早于 30 天且用户从未主动调用
2. 功能已被其他 skill 覆盖
3. 系统预装但用户明确不使用（gaming, minecraft 等）

```bash
# 检查最后修改时间
for d in ~/.hermes/skills/*/; do
    name=$(basename "$d")
    last_mod=$(find "$d" -type f -printf '%T@\n' 2>/dev/null | sort -n | tail -1 | xargs -I{} date -d @{} +%Y-%m-%d)
    echo "$last_mod $name"
done | sort
```

### 清理缓存和垃圾

```bash
# 清理 Hermes 缓存
rm -rf ~/.hermes/cache/* ~/.hermes/logs/* ~/.hermes/audio_cache/* ~/.hermes/image_cache/*

# 清理旧 sessions（保留最近 10 个）
cd ~/.hermes/sessions && ls -t | tail -n +11 | xargs rm -rf

# 清理 __pycache__
find ~/.hermes/skills/ -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# 清理 .pyc
find ~/.hermes/skills/ -type f -name "*.pyc" -delete 2>/dev/null

# 清理嵌入式 .git（skills 不应有自己的 git repo）
find ~/.hermes/skills/ -type d -name ".git" -exec rm -rf {} + 2>/dev/null
```

## 凭证固化规则

**核心原则：凭证/地址必须存为独立 skill，不能依赖 memory**

### 为什么 skill 比 memory 更可靠

| 特性 | Memory | Skill |
|------|--------|-------|
| 持久性 | 会压缩、丢失、被覆盖 | 文件系统持久保存 |
| 检索 | 模糊匹配，可能找不到 | 明确名称，直接加载 |
| 更新 | 自动，不可控 | 手动，可控 |
| 共享 | 绑定单个 agent | 可跨 agent 使用 |

### 凭证 Skill 模板

```markdown
---
name: PROJECT-github-repo
description: PROJECT GitHub 仓库信息 — 防止遗忘仓库地址和凭证
tags: [github, repo, credentials]
---

# GitHub 仓库

**仓库**: `https://github.com/USER/REPO`
**SSH**: `git@github.com:USER/REPO.git`

**用户名**: `USER`
**Token**: `ghp_...`

已配置在:
- `~/.git-credentials`
- `~/.hermes/.env`

## 推送命令

```bash
git remote add origin https://USER:TOKEN@github.com/USER/REPO.git
git push -u origin main
```
```

### 创建时机

- 用户提供 GitHub 仓库地址时
- 用户提供 API key/token 时
- 用户说"你老是忘记..."时

## 体积查询规范

当用户问 "体积多大" 时，**先确认层面，给一个数字，禁止自动给 breakdown**。

| 层面 | 路径 | 说明 |
|------|------|------|
| **核心源码** | `~/.hermes/skills/NAME/onebot/` 或源码根目录 | 纯代码文件 |
| **Skill 完整包** | `~/.hermes/skills/NAME/` | 含 venv、数据、模型 |
| **Hermes 总占用** | `~/.hermes/` | 含所有 skills、缓存、运行环境 |

**用户信号识别**：
- "体积多大" → 给一个数字，等追问再给 breakdown
- "别复杂化" / "看清楚我的问题" → 立即停止解释，只回答核心数字
- "排除掉...之后呢" → 用户主动要求细分，此时给 breakdown

**2026-05-16 实际案例**：
- ❌ 错误：用户问"Hermes 体积多大"，自动给 breakdown（5.3G/3G/11MB），被纠正"别复杂化"
- ✅ 正确：回答 "5.3 GB"，等用户追问"排除后"再细分
- ❌ 错误：用户问"排除后"，给 hermes-agent/skills/cache breakdown，被纠正"是不是忘了包含 onebot"
- ✅ 正确：确认 "~/.hermes/ 排除后是 1.9 GB（含 hermes-agent 1.4G + skills 0.4G + 其他）"

## 维护检查清单

- [ ] Skill 数量 < 50
- [ ] 无重复功能 skill
- [ ] 无 30 天未使用的 skill
- [ ] 凭证已固化为独立 skill
- [ ] 缓存已清理
- [ ] `__pycache__` 已清理
- [ ] 嵌入式 `.git` 已清理

## 代码删除规范

当用户说"删了吧我们不搞"时，**立即执行，零确认**。

### 删除清单模板

```bash
# 1. 删除物理文件
rm -rf path/to/feature_dir/
rm -f path/to/feature_file.py

# 2. 清理引用（必须全部检查）
```

### 引用清理检查表

| 位置 | 检查项 |
|------|--------|
| `__init__.py` | 移除 import 语句、从 `__all__` 移除 |
| 核心模块 | 移除初始化代码、构造函数参数、字段声明 |
| 调用点 | 移除函数调用，替换为占位/空实现 |
| 输出结构 | 从返回 dict 中移除相关 key |
| 类型定义 | 从 dataclass 移除相关字段 |
| Docstring | 移除功能描述中的相关引用 |
| 注释 | 移除代码注释中的相关说明 |

### 验证步骤

```bash
# 全局搜索确认零残留
grep -ri "feature_name" ~/.hermes/skills/onebot-3.0/onebot/quant_core/ 2>/dev/null || echo "CLEAN"
```

**必须返回 0 匹配才算完成。**
