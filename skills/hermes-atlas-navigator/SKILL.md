---
name: hermes-atlas-navigator
description: Navigate the Hermes Atlas ecosystem (hermesatlas.com) to find skills, tools, memory providers, workspaces, and deployment options matching a specific task or need.
version: 1.0.0
trigger: When the user needs to find a community skill, tool, workspace, memory provider, deployment template, or any other Hermes ecosystem resource for a specific use case.
prerequisites: Browser tool available (browser_navigate, browser_snapshot, browser_click, browser_type, browser_press)
---

# Hermes Atlas Navigator

## Overview

Hermes Atlas (https://hermesatlas.com) is the community-curated map of the Hermes Agent ecosystem. It tracks 111+ open-source projects across 12 categories with live GitHub data, quality filtering, and security review.

**Key stats (May 2026):**
- 264K+ total GitHub stars
- 111 repos, 12 categories
- 6 curated opinionated lists
- Updated weekly

## URL Structure

| Page | URL | Purpose |
|------|-----|---------|
| Home / Map | `https://hermesatlas.com/` | Full catalog with search and categories |
| Handbook | `https://hermesatlas.com/guide/` | Complete beginner's guide |
| Reports | `https://hermesatlas.com/reports/` | Quarterly ecosystem reports |
| Project detail | `https://hermesatlas.com/projects/{owner}/{repo}` | Deep dive on a specific repo |

### Curated Lists (opinionated starting points)

| List | URL | What it covers |
|------|-----|----------------|
| Best memory providers | `/lists/best-memory-providers` | Semantic memory, graph retrieval, cross-session persistence |
| Top skills | `/lists/top-skills` | Popular skills following agentskills.io standard |
| Deployment options | `/lists/deployment-options` | Docker, Nix, systemd, cloud templates |
| Multi-agent frameworks | `/lists/multi-agent-frameworks` | Fleet management, swarm coordinators |
| Developer tools | `/lists/developer-tools` | CLIs, linters, token trackers, migration helpers |
| Workspaces & GUIs | `/lists/workspaces-and-guis` | Web/desktop interfaces, chat UIs, dashboards |

## 12 Categories on the Map

1. **Core & official** — Nous Research maintained (hermes-agent, atropos, self-evolution, etc.)
2. **Workspaces & GUIs** — Web/desktop interfaces
3. **Skills & skill registries** — Reusable capabilities (agentskills.io standard)
4. **Memory & context** — Long-term semantic memory, graph retrieval
5. **Integrations & plugins** — Third-party service connectors
6. **Models & inference** — LLM providers, local inference, quantization
7. **Agent frameworks** — Orchestration, delegation, planning
8. **Data & RAG** — Vector DBs, document processing, embeddings
9. **Testing & eval** — Benchmarks, eval harnesses, red-teaming
10. **Domain applications** — Vertical-specific agents (SRE, gaming, blockchain)
11. **Security & compliance** — Audit, hardening, threat detection
12. **Community & docs** — Tutorials, newsletters, governance

## Workflow: Find a Resource for a Task

### Step 1: Identify the need category
Map the user's task to one of the 12 categories or 6 curated lists above.

### Step 2: Search or browse

**Option A — Use the search box on the homepage:**
1. Navigate to `https://hermesatlas.com/`
2. Click the search textbox (placeholder: "search repos by name or description...")
3. Type a keyword (e.g., "scraping", "memory", "telegram", "docker")
4. Press Enter
5. Results appear grouped by category with star counts and weekly growth

**Option B — Browse a curated list directly:**
1. Navigate to the relevant list URL (see table above)
2. Review ranked projects with star counts, descriptions, and weekly growth
3. Click any project for full breakdown

**Option C — Browse by category on the map:**
1. Navigate to `https://hermesatlas.com/`
2. Scroll to the relevant category section (e.g., "03 Skills & skill registries")
3. Review projects ranked by stars

### Step 3: Evaluate candidates
For each candidate project, note:
- **Stars** — popularity signal
- **+X / wk** — growth velocity (hot projects marked with "hot" tag)
- **Description** — one-line summary
- **Official tag** — maintained by Nous Research (higher trust)

### Step 4: Deep dive
Click a project link to open its detail page. It shows:
- Full description and features
- Language, license, maintainer, last update
- Link to GitHub repo
- Link to homepage/docs
- Related repos in the same category

### Step 5: Report findings
Present to the user:
1. What you searched for
2. Top 3-5 matches with repo name, stars, and why it fits
3. Direct GitHub links for the best matches
4. Recommendation with reasoning

## Quick Reference: Top Projects by Category

### Core (must-know)
- `NousResearch/hermes-agent` — 129K stars, the agent itself
- `NousResearch/hermes-agent-self-evolution` — 2.7K stars, evolutionary self-improvement
- `NousResearch/atropos` — 1.1K stars, RL training environments

### Top Skills (agentskills.io)
- `mukul975/Anthropic-Cybersecurity-Skills` — 5.9K stars, 754 cybersecurity skills
- `conorbronsdon/avoid-ai-writing` — 1.3K stars, humanize AI text
- `Agents365-ai/drawio-skill` — 901 stars, generate draw.io diagrams
- `wondelai/skills` — 812 stars, general agent skills
- `Romanescu11/hermes-skill-factory` — 179 stars, auto-generate skills from workflows

### Memory Providers
- `mem0ai/mem0` — 54.6K stars, official Hermes memory provider (managed or self-hosted)
- `garrytan/gbrain` — 12.7K stars, knowledge graph brain
- `vectorize-io/hindsight` — 11.8K stars, retain/recall/reflect workflows
- `plastic-labs/honcho` — 3.1K stars, official stateful memory library
- `yoloshii/ClawMem` — 145 stars, local-first, no cloud

### Workspaces & GUIs
- `nesquena/hermes-webui` — 5.3K stars, best web UI
- `outsourc-e/hermes-workspace` — 2.9K stars, native web workspace
- `fathah/hermes-desktop` — 873 stars, desktop companion
- `dodo-reach/hermes-desktop` — 744 stars, native Mac workspace

### Multi-Agent Frameworks
- `builderz-labs/mission-control` — 1.1K stars, orchestration platform
- `swarmclawai/swarmclaw` — 420 stars, self-hosted swarm runtime

### Deployment
- `numtide/llm-agents.nix` — 1.1K stars, Nix packages
- `rookiemann/portable-hermes-agent` — 82 stars, Windows portable
- `TheAiSingularity/hermesclaw` — 37 stars, NVIDIA sandboxed

### Developer Tools
- `junhoyeo/tokscale` — 2.5K stars, token usage tracker
- `joeynyc/hermes-skins` — 304 stars, CLI themes
- `0xNyk/openclaw-to-hermes` — 28 stars, migration tool

## Pitfalls

- **Search is client-side** — results filter dynamically as you type; no need to press Enter, but Enter confirms the filter
- **Star counts are live** — may differ slightly from current GitHub due to caching
- **"Official" tag matters** — Nous Research repos are more stable and better documented
- **Weekly growth (+X/wk)** — better signal than absolute stars for emerging tools
- **Some repos are skills, some are full apps** — check the category label before recommending

## Example Queries

| User Need | Search Term / List | Top Result |
|-----------|-------------------|------------|
| "Need a skill for web scraping" | Search: "scraping" or browse Skills | Check skills registries |
| "Want persistent memory" | `/lists/best-memory-providers` | `mem0ai/mem0` |
| "Need a web UI for Hermes" | `/lists/workspaces-and-guis` | `nesquena/hermes-webui` |
| "Deploy on Docker" | `/lists/deployment-options` | `xmbshwll/hermes-agent-docker` |
| "Track token costs" | `/lists/developer-tools` | `junhoyeo/tokscale` |
| "Multi-agent setup" | `/lists/multi-agent-frameworks` | `builderz-labs/mission-control` |
| "Cybersecurity skills" | `/lists/top-skills` | `mukul975/Anthropic-Cybersecurity-Skills` |

## Sharing / Distributing This Skill

When the user asks "how do I give this skill to another Hermes agent", explain these options:

**Option A — Direct file copy (fastest)**
The skill lives at `~/.hermes/skills/devops/hermes-atlas-navigator/SKILL.md`. Copy this file to the same path on the target agent's machine. It appears immediately in `skills_list`.

**Option B — Paste content**
Copy the full SKILL.md content, tell the other agent: "Save this as `~/.hermes/skills/<category>/hermes-atlas-navigator/SKILL.md`". The agent will see it on next `skills_list`.

**Option C — GitHub repository**
Push SKILL.md to a GitHub repo. Any agent can clone it into `~/.hermes/skills/` or use `skill_manage(action='create', ...)`.

---

## GitHub Authentication (for publishing)

If the user wants to push this skill to GitHub, you may need to authenticate gh CLI.

**Quick auth via token:**
```bash
mkdir -p ~/.config/gh
cat > ~/.config/gh/hosts.yml << 'EOF'
github.com:
    user: <USERNAME>
    oauth_token: <TOKEN>
    git_protocol: https
EOF
```

Then verify: `gh auth status`

**Security pitfalls:**
- NEVER echo a token or write it to terminal output where it may be logged
- NEVER pass tokens as plaintext command arguments (visible in process lists)
- ALWAYS use heredoc (`<< 'EOF'`) or file redirection to write tokens to config
- If the user pasted a token in chat, do NOT repeat it back in full
- Use fine-grained tokens with minimal repo scope when possible
- `gh auth login --with-token` may timeout in some environments; the hosts.yml workaround above is more reliable

---

## Verification

Always verify a recommendation by:
1. Opening the project detail page on Hermes Atlas
2. Clicking "view on github" to check README and recent activity
3. Confirming the project matches the user's exact need (not just keyword match)
