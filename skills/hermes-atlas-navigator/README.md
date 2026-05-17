# 🗺️ Hermes Atlas Navigator

**[🇷🇺 Русский](README.ru.md) · [🇨🇳 中文](README.zh.md)**

> Find the right tool in 30 seconds, not 30 minutes.

---

## 😤 The Pain: Ecosystem Discovery is Broken

Hermes Agent has 111+ community projects. 264K+ GitHub stars. 12 categories.

But when you need something specific — a memory provider, a web UI, a deployment template — you face:

- **Scattered repos** across dozens of GitHub accounts
- **No single index** — you hunt through issues, Discord, random blog posts
- **Star count lies** — a 5K-star project might be abandoned, a 100-star one might be exactly what you need
- **Wrong category** — you search "memory" and find 6 different approaches with zero comparison

You spend 20 minutes browsing. Or you give up and build from scratch.

That's not engineering. That's archaeology.

---

## ✨ The Solution: Structured Navigation

This skill turns Hermes Atlas (https://hermesatlas.com) into a searchable, filterable command center.

| What You Need | Where to Look | Top Pick |
|---------------|-------------|----------|
| **Persistent memory** | `/lists/best-memory-providers` | `mem0ai/mem0` — 54.6K stars, official provider |
| **Reusable skills** | `/lists/top-skills` | `mukul975/Anthropic-Cybersecurity-Skills` — 754 skills |
| **Web UI / GUI** | `/lists/workspaces-and-guis` | `nesquena/hermes-webui` — 5.3K stars |
| **Docker / deploy** | `/lists/deployment-options` | `numtide/llm-agents.nix` — 1.1K stars |
| **Multi-agent swarm** | `/lists/multi-agent-frameworks` | `builderz-labs/mission-control` — 1.1K stars |
| **Token tracking** | `/lists/developer-tools` | `junhoyeo/tokscale` — 2.5K stars |

### The Key Insight

Hermes Atlas is not just a list. It has:
- **Live GitHub data** — stars, forks, weekly growth
- **Security review** — every project vetted
- **6 curated lists** — opinionated starting points
- **12 categories** — from Core to Domain Applications
- **Search** — client-side filter by name or description

**This skill wraps all of that into a 5-step workflow.**

---

## 🚀 Quick Start

### 1. Load the skill

```bash
skill_view('hermes-atlas-navigator')
```

### 2. Find a resource

```bash
# Search by keyword
"I need persistent memory for my agent"
→ Navigate to /lists/best-memory-providers
→ Compare mem0 (54.6K), gbrain (12.7K), hindsight (11.8K)
→ Pick based on: managed vs self-hosted, graph vs vector, local vs cloud

# Or search the full map
"telegram bot ui"
→ Search hermesatlas.com for "telegram"
→ Find hermes-telegram-miniapp (212 stars), hermes-webui (5.3K)
→ Deep dive on project page for features, last update, GitHub link
```

### 3. Verify before installing

```bash
# Click "view on github" from Atlas project page
# Check: README quality, last commit, open issues, license
# Confirm it matches your exact need
```

---

## 🏗 The 5-Step Workflow

```
┌─────────────────────────────────────────────────────────┐
│  Step 1: Identify need                                  │
│  "I need a skill for web scraping"                      │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  Step 2: Search or browse                               │
│  Option A: Search box on hermesatlas.com                │
│  Option B: Curated list (top-skills, developer-tools)   │
│  Option C: Category scroll (Skills & registries)        │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  Step 3: Evaluate candidates                            │
│  Stars? +X/wk growth? Official tag? Description match?  │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  Step 4: Deep dive                                      │
│  Project page → GitHub repo → README → Recent activity  │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  Step 5: Report findings                                │
│  Top 3-5 matches with reasoning and direct links        │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 Category Map

| # | Category | What Lives Here | Star Leader |
|---|----------|----------------|-------------|
| 01 | Core & official | Nous Research maintained | hermes-agent (129K) |
| 02 | Workspaces & GUIs | Web/desktop interfaces | hermes-webui (5.3K) |
| 03 | Skills & registries | Reusable capabilities | Anthropic-Cybersecurity (5.9K) |
| 04 | Memory & context | Semantic memory, RAG | mem0 (54.6K) |
| 05 | Integrations & plugins | Third-party connectors | — |
| 06 | Models & inference | LLM providers, local inference | — |
| 07 | Agent frameworks | Orchestration, delegation | — |
| 08 | Data & RAG | Vector DBs, embeddings | — |
| 09 | Testing & eval | Benchmarks, red-teaming | — |
| 10 | Domain applications | Vertical agents (SRE, gaming) | hermescraft (19) |
| 11 | Security & compliance | Audit, hardening | — |
| 12 | Community & docs | Tutorials, newsletters | — |

---

## 🛡 Pitfalls

| Symptom | Cause | Fix |
|---------|-------|-----|
| Search shows nothing | Typo or too specific term | Try broader keyword or browse curated list |
| High stars, dead project | Abandoned but popular | Check "last updated" on project page |
| Skill doesn't install | Not agentskills.io compliant | Check category label — some repos are full apps, not skills |
| Missing hot new tool | Atlas curated weekly | Check "+X / wk" growth, not just total stars |

---

## 💡 The "Wow" Effect

> You say: "I need a web UI for my Telegram bot."
> 
> 30 seconds later: "Here are 3 options. This one has 5.3K stars and mobile support. This one is 212 stars but runs locally. This one is native Mac. Pick based on your hosting."

No browsing. No guessing. No building from scratch.

---

## 📦 Install as Hermes Skill

```bash
hermes skills install https://github.com/bytheby72/hermes-atlas-navigator
```

Or add to `config.yaml`:
```yaml
skills:
  external_dirs:
    - https://github.com/bytheby72/hermes-atlas-navigator
```

---

*Built with 🔍 and zero patience for hunting through 111 repos manually.*
