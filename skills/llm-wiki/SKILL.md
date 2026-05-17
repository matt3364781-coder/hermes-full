---
name: llm-wiki
description: "Karpathy's LLM Wiki — build and maintain a persistent, interlinked markdown knowledge base with human feedback loop. Ingest sources, query compiled knowledge, lint for consistency, and process audit feedback."
version: 3.0.0
author: Hermes Agent (based on work by Lewis Liu / lylewis@outlook.com)
license: MIT
metadata:
  hermes:
    tags: [wiki, knowledge-base, research, notes, markdown, rag-alternative, audit]
    category: research
    related_skills: [obsidian, arxiv, agentic-research-ideas]
    config:
      - key: wiki.path
        description: Path to the LLM Wiki knowledge base directory
        default: "~/wiki"
        prompt: Wiki directory path
---

# Karpathy's LLM Wiki

Build and maintain a persistent, compounding knowledge base as interlinked markdown files.
Based on [Andrej Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

Unlike traditional RAG (which rediscovers knowledge from scratch per query), the wiki
compiles knowledge once and keeps it current. Cross-references are already there.
Contradictions have already been flagged. Synthesis reflects everything ingested.

**Division of labor:** The human curates sources and directs analysis. The agent
summarizes, cross-references, files, and maintains consistency.

## When This Skill Activates

Use this skill when the user:
- Asks to create, build, or start a wiki or knowledge base
- Asks to ingest, add, or process a source into their wiki
- Asks a question and an existing wiki is present at the configured path
- Asks to lint, audit, or health-check their wiki
- References their wiki, knowledge base, or "notes" in a research context

## Wiki Location

Configured via `skills.config.wiki.path` in `~/.hermes/config.yaml`:

```yaml
skills:
  config:
    wiki:
      path: ~/wiki
```

Falls back to `~/wiki` default. The resolved path is injected when this skill loads.

## Architecture: Three Layers

```
<wiki-root>/
├── CLAUDE.md           # Schema: scope, conventions, current articles, gaps (read every session)
├── log/                # Per-day operation log (one file per day: YYYYMMDD.md)
│   ├── 20260409.md
│   └── 20260410.md
├── audit/              # Human feedback inbox (one file per comment)
│   ├── 20260409-143022-claude-code-size.md
│   └── resolved/       # Processed feedback, archived with resolution notes
├── raw/                # Layer 1: Immutable source material
│   ├── articles/       # Web articles, clippings
│   ├── papers/         # PDFs, arxiv papers
│   ├── notes/          # Meeting notes, interviews
│   └── refs/           # Pointer files for large binaries kept outside raw/
├── wiki/               # Layer 2: LLM-generated knowledge
│   ├── index.md        # Master catalog — every page, structured by category
│   ├── concepts/       # Concept/topic pages (split into subfolders when >1200 words)
│   ├── entities/       # People, tools, papers, organizations
│   └── summaries/      # Per-source summary pages
└── outputs/
    └── queries/        # Query answers (promote durable ones to wiki/)
```

**Layer 1 — Raw Sources:** Immutable. The agent reads but never modifies these.
**Layer 2 — The Wiki:** Agent-owned markdown files. Created, updated, and cross-referenced by the agent.
**Layer 3 — The Schema:** `CLAUDE.md` defines scope, conventions, tag taxonomy, and open questions.

### Core Principles

**1. Divide and conquer** — A single concept page should never exceed ~1200 words.
When a topic would blow past that, create a subfolder `wiki/concepts/<topic>/` with
an `index.md` overview and separate files for each aspect.

**2. Mermaid for diagrams, KaTeX for formulas** — Never use ASCII art for diagrams.
All formulas must be in KaTeX: inline `$f(x) = \sum_i w_i x_i$` or block `$$...$$`.

**3. Raw file policy** — Small text sources → copy into `raw/<subfolder>/`.
Large binaries (>10 MB) → create a pointer file at `raw/refs/<slug>.md` with:
```yaml
---
kind: ref
external_path: /Volumes/external/models/llama-3-70b/
size: ~140 GB
---
```

**4. Audit is the human feedback surface** — The `audit/` directory is how humans
correct AI-written content without losing corrections in chat history. The AI must
periodically run the `audit` op — never silently ignore `audit/*.md` files.

## Resuming an Existing Wiki (CRITICAL)

When the user has an existing wiki, **always orient yourself before doing anything**:

1. **Read `CLAUDE.md`** — understand the scope, conventions, and open questions.
2. **Read `wiki/index.md`** — learn what pages exist and their summaries.
3. **Scan recent logs** — read the last 2-3 files in `log/` to understand recent activity.

```bash
WIKI="${wiki_path:-$HOME/wiki}"
read_file "$WIKI/CLAUDE.md"
read_file "$WIKI/wiki/index.md"
search_files "*.md" target="files" path="$WIKI/log" | tail -3
```

Only after orientation should you ingest, query, lint, or audit.

## Initializing a New Wiki

When the user asks to create or start a wiki:

1. Determine the wiki path (from config, env var, or ask; default `~/wiki`)
2. Run the scaffold script:
   ```bash
   python3 ~/.hermes/skills/research/llm-wiki/scripts/scaffold.py <wiki-root> "<Topic Title>"
   ```
3. Help the user fill in `CLAUDE.md` — define scope, naming conventions, initial research questions
4. Suggest first sources to ingest

## The Five Operations

Every action on the wiki is one of these five. Each appends an entry to the current day's log file (`log/YYYYMMDD.md`).

### 1. `compile`

(Re)structure wiki content from existing `raw/` material — including splitting oversized pages, merging near-duplicates, and rebuilding `index.md`.

**When to run**: after a big ingest batch, when an existing page has outgrown 1200 words, when `index.md` no longer reflects reality, or when the user says "clean up the wiki".

**Steps**:
1. Read `CLAUDE.md`, `wiki/index.md`, and every file in the target subtree.
2. For each page over ~1200 words: plan a split into `concepts/<topic>/` with an index + sub-pages. Confirm the plan with the user before writing.
3. For each pair of near-duplicate pages: propose a merge. Confirm, then rewrite.
4. Regenerate `wiki/index.md` so every page is listed exactly once.
5. Log: `## [HH:MM] compile | <what you did — files touched, splits, merges>`

### 2. `ingest`

Add a new source. **One source typically touches 5–15 wiki pages.**

**Steps**:
1. Save source to the right subfolder:
   - web article → `raw/articles/<slug>.md`
   - paper → `raw/papers/<slug>.md` (extracted text for big PDFs)
   - note → `raw/notes/<slug>.md`
   - large binary → `raw/refs/<slug>.md` pointer file
2. Read the source in full.
3. Create `wiki/summaries/<slug>.md` (200–400 words — key takeaways, not a rewrite).
4. Create or update relevant concept pages in `wiki/concepts/`. Respect divide-and-conquer.
5. Create or update entity pages in `wiki/entities/` for any new people/tools/papers/organizations.
6. Update `wiki/index.md` so the new pages appear under the right category.
7. Log: `## [HH:MM] ingest | <slug> — <one-line description> (touched N pages)`

### 3. `query`

Answer a question **grounded in the wiki**, not general knowledge.

**Steps**:
1. Read `wiki/index.md`. Scan for relevant pages by category.
2. Read the identified pages in full; follow one level of wikilinks.
3. If the wiki doesn't have enough material, say so and suggest what to ingest next.
4. Synthesize the answer, citing pages inline with `[[Page Name]]`.
5. Save to `outputs/queries/<YYYY-MM-DD>-<question-slug>.md`.
6. If the answer is durable → promote to `wiki/concepts/`, add to `index.md`.
7. Log: `## [HH:MM] query | <question-slug>` (and `## [HH:MM] promote | ...` if promoted).

### 4. `lint`

Health check. Run:

```bash
python3 ~/.hermes/skills/research/llm-wiki/scripts/lint_wiki.py <wiki-root>
```

The script reports:
- **Dead wikilinks** — `[[Target]]` where `Target.md` doesn't exist
- **Orphan pages** — pages with no inbound wikilinks
- **Missing index entries** — pages not listed in `wiki/index.md`
- **Frequently-linked missing pages** — `[[X]]` referenced 3+ times but no page
- **log/ shape** — stray files or wrong filenames in `log/`
- **audit/ shape** — malformed YAML frontmatter in `audit/*.md`
- **Audit target resolution** — every open audit's `target` file must exist

For each issue, propose a fix, confirm with the user, then apply. Log: `## [HH:MM] lint | <N> issues found, <M> fixed`.

### 5. `audit`

Process human feedback from `audit/`.

**Steps**:
1. Run `python3 ~/.hermes/skills/research/llm-wiki/scripts/audit_review.py <wiki-root> --open` to get a grouped list.
2. For each open audit, read the file. Use the `anchor_before` / `anchor_text` / `anchor_after` window to locate the exact range in the target file.
3. Decide the action: **Accept**, **Partially accept**, **Reject**, or **Defer**.
4. For applied audits, append a `# Resolution` section to the audit file.
5. Move the file from `audit/` to `audit/resolved/`. Filename unchanged.
6. Log per resolved audit: `## [HH:MM] audit | resolved 20260409-143022-a1b2 — <one-line what>`
7. Never delete audit files. Rejected ones still go to `resolved/` with their rationale.

## Audit System

The `audit/` directory is the human feedback surface. Humans can file feedback via:
- The Obsidian plugin (`plugins/obsidian-audit/`)
- The local web viewer (`web/`)
- Manual creation in the `audit/` directory

### Audit File Format

```markdown
---
id: 20260409-143022-a1b2
target: wiki/tech/Claude_Code.md
target_lines: [45, 52]
anchor_before: "## 技术概览\n\n| 维度 | 详情 |\n|------|------|\n"
anchor_text: "| **规模** | ~1,900 个文件，512,000+ 行代码 |"
anchor_after: "\n| **语言** | TypeScript（strict 模式） |"
severity: warn
author: lewis
source: obsidian-plugin
created: 2026-04-09T14:30:22+08:00
status: open
---

# Comment

实际应该是 ~1,800 个文件，参考 2026-03-31 commit abc123 的 tree。

# Resolution

<!-- Filled in when processed and moved to resolved/ -->
```

### Severity Semantics

- **info** — "worth noting but not wrong"
- **suggest** — "consider this"
- **warn** — "something looks off"
- **error** — "this is wrong"

Process `error` and `warn` first, then `suggest`, then `info`.

### Anchor Strategy

Line numbers drift. The anchor window (`anchor_before` + `anchor_text` + `anchor_after`) is the reliable way to locate feedback.

**On read (during `audit` op)**:
1. Try `target_lines` — check whether the text contains `anchor_text`.
2. If not, search the whole file for `anchor_text`.
3. If multiple matches, use combined `anchor_before + anchor_text + anchor_after`.
4. If still no match, the anchor is **stale** — flag to the user.

## Tooling

| Tool | Purpose |
|------|---------|
| [Obsidian](https://obsidian.md) | IDE for browsing the wiki; graph view shows connections |
| **`scripts/scaffold.py`** | Bootstrap a new wiki directory tree |
| **`scripts/lint_wiki.py`** | Seven-pass health check |
| **`scripts/audit_review.py`** | Group open/resolved audits by target file |
| `plugins/obsidian-audit/` | Obsidian plugin — select text → add feedback → writes to `audit/` |
| `web/` | Local Node.js server — preview the wiki with mermaid/math rendered |
| [qmd](https://github.com/tobi/qmd) | Optional local semantic search (useful at >100 pages) |

## Working with the Wiki

### Searching

```bash
search_files "transformer" path="$WIKI" file_glob="*.md"
search_files "*.md" target="files" path="$WIKI"
search_files "*.md" target="files" path="$WIKI/log" | tail -3
```

### Obsidian Integration

The wiki directory works as an Obsidian vault out of the box. Set Obsidian's attachment folder to `raw/assets/`.

## Pitfalls

- **Never modify files in `raw/`** — sources are immutable.
- **Always orient first** — read CLAUDE.md + index.md + recent logs before any operation.
- **Always update index.md and log/YYYYMMDD.md** — skipping this makes the wiki degrade.
- **Don't create pages for passing mentions** — a name appearing once doesn't warrant a page.
- **Don't create pages without cross-references** — every page must link to at least 2 others.
- **Keep pages scannable** — split pages over 1200 words.
- **Ask before mass-updating** — if an ingest would touch 10+ pages, confirm first.
- **Handle contradictions explicitly** — note both claims with dates.
- **Never ignore audit/ files** — the AI must periodically run the `audit` op.
- **Never delete audit files** — even rejected audits go to `resolved/`.
- **Use the anchor window, not line numbers** — when processing audits, locate text via anchors.

## References

- `references/schema-guide.md` — What to put in `CLAUDE.md`
- `references/article-guide.md` — How to write good wiki articles
- `references/log-guide.md` — The `log/` folder convention
- `references/audit-guide.md` — Audit file format, anchor strategy, processing workflow
- `references/tooling-tips.md` — Obsidian setup, Web Clipper, qmd, plugin + web installation
