# 🗺️ Hermes Atlas 导航器

**[🇺🇸 English](README.md) · [🇷🇺 Русский](README.ru.md)**

> 30 秒内找到合适的工具，而不是 30 分钟。

---

## 😤 痛点：生态系统发现是破碎的

Hermes Agent 有 111+ 个社区项目。264K+ GitHub 星标。12 个分类。

但当你需要某个具体的东西时——一个记忆提供者、一个网页界面、一个部署模板——你会面临：

- **分散的仓库** 遍布数十个 GitHub 账户
- **没有单一索引** —— 你在 issues、Discord、随机博客文章中搜寻
- **星标数具有欺骗性** —— 一个 5K 星标的项目可能已被废弃，而一个 100 星标的项目可能正是你需要的
- **错误的分类** —— 你搜索 "memory"，找到 6 种不同的方法，却没有任何对比

你花了 20 分钟浏览。或者你放弃，从头开始构建。

这不是工程。这是考古。

---

## ✨ 解决方案：结构化导航

这个 skill 将 Hermes Atlas (https://hermesatlas.com) 变成一个可搜索、可筛选的指挥中心。

| 你需要什么 | 去哪里找 | 首选推荐 |
|-----------|---------|----------|
| **持久化记忆** | `/lists/best-memory-providers` | `mem0ai/mem0` — 54.6K 星标，官方提供者 |
| **可复用技能** | `/lists/top-skills` | `mukul975/Anthropic-Cybersecurity-Skills` — 754 个技能 |
| **网页界面 / GUI** | `/lists/workspaces-and-guis` | `nesquena/hermes-webui` — 5.3K 星标 |
| **Docker / 部署** | `/lists/deployment-options` | `numtide/llm-agents.nix` — 1.1K 星标 |
| **多智能体集群** | `/lists/multi-agent-frameworks` | `builderz-labs/mission-control` — 1.1K 星标 |
| **Token 追踪** | `/lists/developer-tools` | `junhoyeo/tokscale` — 2.5K 星标 |

### 核心洞察

Hermes Atlas 不只是一个列表。它有：
- **实时 GitHub 数据** —— 星标、分支、周增长
- **安全审查** —— 每个项目都经过审核
- **6 个精选列表** —— 专家推荐，从何处开始
- **12 个分类** —— 从 Core 到 Domain Applications
- **搜索** —— 按名称或描述的客户端过滤

**这个 skill 将所有这些包装成一个 5 步工作流程。**

---

## 🚀 快速开始

### 1. 加载 skill

```bash
skill_view('hermes-atlas-navigator')
```

### 2. 查找资源

```bash
# 按关键词搜索
"我需要为我的智能体提供持久化记忆"
→ 导航到 /lists/best-memory-providers
→ 对比 mem0 (54.6K)、gbrain (12.7K)、hindsight (11.8K)
→ 根据以下条件选择：托管 vs 自托管、图 vs 向量、本地 vs 云端

# 或在全站搜索
"telegram bot ui"
→ 在 hermesatlas.com 搜索 "telegram"
→ 找到 hermes-telegram-miniapp (212 星标)、hermes-webui (5.3K)
→ 在项目页面深入了解功能、最后更新时间、GitHub 链接
```

### 3. 安装前验证

```bash
# 从 Atlas 项目页面点击 "view on github"
# 检查：README 质量、最后提交、开放 issues、许可证
# 确认它完全符合你的需求
```

---

## 🏗 5 步工作流程

```
┌─────────────────────────────────────────────────────────┐
│  步骤 1：确定需求                                        │
│  "我需要一个用于网页抓取的 skill"                         │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  步骤 2：搜索或浏览                                      │
│  选项 A：hermesatlas.com 上的搜索框                      │
│  选项 B：精选列表 (top-skills, developer-tools)          │
│  选项 C：分类滚动 (Skills & registries)                   │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  步骤 3：评估候选者                                      │
│  星标数？+X/周 增长？Official 标签？描述匹配度？          │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  步骤 4：深入了解                                        │
│  项目页面 → GitHub 仓库 → README → 近期活动               │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  步骤 5：报告发现                                        │
│  前 3-5 个匹配项，附理由和直接链接                        │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 分类地图

| # | 分类 | 这里有什么 | 星标领先者 |
|---|------|-----------|-----------|
| 01 | Core & official | Nous Research 维护 | hermes-agent (129K) |
| 02 | Workspaces & GUIs | 网页/桌面界面 | hermes-webui (5.3K) |
| 03 | Skills & registries | 可复用能力 | Anthropic-Cybersecurity (5.9K) |
| 04 | Memory & context | 语义记忆、RAG | mem0 (54.6K) |
| 05 | Integrations & plugins | 第三方连接器 | — |
| 06 | Models & inference | LLM 提供者、本地推理 | — |
| 07 | Agent frameworks | 编排、委托 | — |
| 08 | Data & RAG | 向量数据库、嵌入 | — |
| 09 | Testing & eval | 基准测试、红队测试 | — |
| 10 | Domain applications | 垂直智能体 (SRE、游戏) | hermescraft (19) |
| 11 | Security & compliance | 审计、加固 | — |
| 12 | Community & docs | 教程、新闻通讯 | — |

---

## 🛡 常见陷阱

| 症状 | 原因 | 解决方法 |
|------|------|----------|
| 搜索无结果 | 拼写错误或术语太具体 | 尝试更宽泛的关键词或浏览精选列表 |
| 星标高但项目已死 | 已废弃但曾经流行 | 检查项目页面上的 "last updated" |
| Skill 安装失败 | 不符合 agentskills.io 标准 | 检查分类标签 —— 有些仓库是完整应用，不是 skill |
| 缺少热门新工具 | Atlas 每周精选一次 | 看 "+X/周" 增长，不只是总星标数 |

---

## 💡 "哇"效果

> 你说："我需要一个用于 Telegram 机器人的网页界面。"
> 
> 30 秒后："这里有 3 个选项。这个有 5.3K 星标，支持移动端。这个有 212 星标，但本地运行。这个是原生 Mac 版。根据你的托管方式选择。"

无需浏览。无需猜测。无需从头构建。

---

## 📦 作为 Hermes Skill 安装

```bash
hermes skills install https://github.com/bytheby72/hermes-atlas-navigator
```

或在 `config.yaml` 中添加：
```yaml
skills:
  external_dirs:
    - https://github.com/bytheby72/hermes-atlas-navigator
```

---

*Built with 🔍 and zero patience for hunting through 111 repos manually.*
