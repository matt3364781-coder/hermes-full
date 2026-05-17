# llm-wiki — Karpathy 风格知识库

基于 Andrej Karpathy 的 [LLM Wiki 模式](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)，构建持久化、互链接的 Markdown 知识库。

## 核心理念

> 不是每次提问都重新检索原始资料（像 RAG 那样），而是让 AI 把读过的资料**编译**成一个持久的、互相链接的 wiki。知识会累积，越用越丰富。

**分工**：
- **人类负责**：找资料、提问题、给反馈
- **AI 负责**：写内容、建链接、维护一致性、处理纠错

---

## 快速开始

### 1. 创建新 wiki

```bash
python3 ~/.hermes/skills/research/llm-wiki/scripts/scaffold.py <路径> "<主题>"

# 示例
python3 ~/.hermes/skills/research/llm-wiki/scripts/scaffold.py ~/wiki "AI Research"
```

### 2. 健康检查

```bash
python3 ~/.hermes/skills/research/llm-wiki/scripts/lint_wiki.py <路径>

# 检查：死链接、孤立页面、缺失索引、audit 格式等
```

### 3. 查看审计反馈

```bash
python3 ~/.hermes/skills/research/llm-wiki/scripts/audit_review.py <路径> --open

# 查看人类通过 Obsidian/Web 提交的反馈
```

---

## 核心操作（五操作模型）

| 操作 | 说明 | 触发场景 |
|------|------|----------|
| `ingest` | 添加新书/资料 | 用户提供 URL、文件或文本 |
| `query` | 基于 wiki 回答问题 | 用户提问，AI 从 wiki 综合答案 |
| `compile` | 重构/合并/拆分页面 | 页面超过 1200 字、索引过时 |
| `lint` | 健康检查 | 定期检查 wiki 健康状况 |
| `audit` | 处理人类反馈 | 处理 Obsidian/Web 提交的纠错 |

---

## 目录结构

```
<wiki-root>/
├── CLAUDE.md           # Schema 文档（每次会话必读）
├── log/                # 每日操作日志（YYYYMMDD.md）
├── audit/              # 人类反馈 inbox
│   └── resolved/       # 已处理的反馈
├── raw/                # 原始资料（只读）
│   ├── articles/
│   ├── papers/
│   ├── notes/
│   └── refs/
├── wiki/               # AI 生成的知识
│   ├── index.md        # 总索引
│   ├── concepts/       # 概念页
│   ├── entities/       # 人物/机构页
│   └── summaries/      # 书籍摘要
└── outputs/
    └── queries/        # 查询答案
```

---

## 配套工具

| 工具 | 说明 |
|------|------|
| [Obsidian](https://obsidian.md) | 浏览 wiki 的 IDE，支持双向链接和图谱视图 |
| `plugins/obsidian-audit/` | Obsidian 插件 — 选中文本提交反馈 |
| `web/` | 本地 Web 服务器 — 预览 wiki + 提交反馈 |
| [qmd](https://github.com/tobi/qmd) | 可选的本地语义搜索（>100 页时有用） |

---

## 配置

在 `~/.hermes/config.yaml` 中配置 wiki 路径：

```yaml
skills:
  config:
    wiki:
      path: ~/wiki
```

---

## 文档导航

| 文档 | 说明 |
|------|------|
| [`SKILL.md`](SKILL.md) | 完整技能文档（13KB） |
| [`references/schema-guide.md`](references/schema-guide.md) | CLAUDE.md 编写指南 |
| [`references/article-guide.md`](references/article-guide.md) | Wiki 文章编写规范 |
| [`references/log-guide.md`](references/log-guide.md) | Log 目录格式说明 |
| [`references/audit-guide.md`](references/audit-guide.md) | Audit 系统完整文档 |
| [`references/tooling-tips.md`](references/tooling-tips.md) | Obsidian/Web 工具配置 |

---

## 版本

- **当前版本**: 1.0.0
- **作者**: Hermes Agent (based on work by Jake Kim / vvip2u@126.com)
- **许可证**: MIT
- **分类**: research

---

## 相关技能

- [`obsidian`](../obsidian/) — Obsidian 笔记管理
- [`arxiv`](../arxiv/) — 学术论文搜索
- [`agentic-research-ideas`](../agentic-research-ideas/) — 研究灵感生成

---

## 使用示例

### 让 Hermes 帮你创建 wiki

```
帮我创建一个 wiki，主题是"AI Agent 研究"，存在 ~/wiki-agent
```

### 让 Hermes 帮你 ingest 资料

```
把这篇文章 ingest 到 wiki 里：https://karpathy.com/llm-wiki
```

### 让 Hermes 回答 wiki 问题

```
wiki 里怎么说 Transformer 架构的？
```

### 让 Hermes 做健康检查

```
跑一下 lint，看看 wiki 有什么问题
```

### 让 Hermes 处理反馈

```
处理一下 pending 的 audit 反馈
```

---

## 核心原则

1. **Divide and conquer** — 概念页不超过 1200 字，超长则拆分
2. **Mermaid 图表，KaTeX 公式** — 不用 ASCII 艺术
3. **Raw 文件只读** — 原始资料不可修改，纠错在 wiki 页面
4. **Audit 是人类反馈表面** — AI 必须定期处理 `audit/` 文件

---

## 贡献

此技能基于 Karpathy 的 LLM Wiki Gist，由 Jake Kim 完善，集成到 Hermes Agent。

# 参考链接

## Related work

- [Karpathy's original Gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- [pedronauck/skills karpathy-kb](https://github.com/pedronauck/skills/tree/main/skills/karpathy-kb) — full Obsidian vault integration
- [Astro-Han/karpathy-llm-wiki](https://github.com/Astro-Han/karpathy-llm-wiki) — example implementation
- [qmd](https://github.com/tobi/qmd) — semantic search for Markdown wikis
- [llm-wiki-skill](https://github.com/lewislulu/llm-wiki-skill) - An OpenClaw / Codex Agent Skill for building Karpathy-style LLM knowledge bases.
