---
name: systematic-debugging
description: "4-phase root cause debugging: understand bugs before fixing."
version: 1.1.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
metadata:
  hermes:
    tags: [debugging, troubleshooting, problem-solving, root-cause, investigation]
    related_skills: [test-driven-development, writing-plans, subagent-driven-development]
---

# Systematic Debugging

## Overview

Random fixes waste time and create new bugs. Quick patches mask underlying issues.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

**Violating the letter of this process is violating the spirit of debugging.**

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

## When to Use

Use for ANY technical issue:
- Test failures
- Bugs in production
- Unexpected behavior
- Performance problems
- Build failures
- Integration issues

**Use this ESPECIALLY when:**
- Under time pressure (emergencies make guessing tempting)
- "Just one quick fix" seems obvious
- You've already tried multiple fixes
- Previous fix didn't work
- You don't fully understand the issue

**Don't skip when:**
- Issue seems simple (simple bugs have root causes too)
- You're in a hurry (rushing guarantees rework)
- Someone wants it fixed NOW (systematic is faster than thrashing)

## The Four Phases

You MUST complete each phase before proceeding to the next.

---

## Phase 1: Root Cause Investigation

**BEFORE attempting ANY fix:**

### 1. Read Error Messages Carefully

- Don't skip past errors or warnings
- They often contain the exact solution
- Read stack traces completely
- Note line numbers, file paths, error codes

**Action:** Use `read_file` on the relevant source files. Use `search_files` to find the error string in the codebase.

### 2. Reproduce Consistently

- Can you trigger it reliably?
- What are the exact steps?
- Does it happen every time?
- If not reproducible → gather more data, don't guess

**Action:** Use the `terminal` tool to run the failing test or trigger the bug:

```bash
# Run specific failing test
pytest tests/test_module.py::test_name -v

# Run with verbose output
pytest tests/test_module.py -v --tb=long
```

### 3. Check Recent Changes

- What changed that could cause this?
- Git diff, recent commits
- New dependencies, config changes

**Action:**

```bash
# Recent commits
git log --oneline -10

# Uncommitted changes
git diff

# Changes in specific file
git log -p --follow src/problematic_file.py | head -100
```

### 4. Gather Evidence in Multi-Component Systems

**WHEN system has multiple components (API → service → database, CI → build → deploy):**

**BEFORE proposing fixes, add diagnostic instrumentation:**

For EACH component boundary:
- Log what data enters the component
- Log what data exits the component
- Verify environment/config propagation
- Check state at each layer

Run once to gather evidence showing WHERE it breaks.
THEN analyze evidence to identify the failing component.
THEN investigate that specific component.

### 5. Trace Data Flow

**WHEN error is deep in the call stack:**

- Where does the bad value originate?
- What called this function with the bad value?
- Keep tracing upstream until you find the source
- Fix at the source, not at the symptom

**Action:** Use `search_files` to trace references:

```python
# Find where the function is called
search_files("function_name(", path="src/", file_glob="*.py")

# Find where the variable is set
search_files("variable_name\\s*=", path="src/", file_glob="*.py")
```

### 6. Check Python Environment & Binary Compatibility

**WHEN the error involves `ModuleNotFoundError`, `ImportError`, or missing C extensions:**

Python environments can have subtle incompatibilities between the interpreter and compiled extensions:

- **UV-installed Python** (e.g. `~/.local/share/uv/python/...`) may ship without `_testcapi` or other C extension modules that system Python includes
- **Cross-version `.so` copying fails** — a `.so` built for Python 3.12 will not load in Python 3.11 (undefined symbols like `PyType_FromMetaclass`)
- **System Python has it, venv Python doesn't** — check both `sys.executable` paths

**Diagnostic commands:**
```bash
# Which Python is active?
python -c "import sys; print(sys.executable); print(sys.version)"

# Does system Python have the module?
/usr/bin/python3 -c "import _testcapi; print('OK')"

# Find the .so on the system
find /usr -name "*testcapi*" 2>/dev/null

# Check if venv Python is uv-managed (often missing dev headers)
python -c "import sysconfig; print(sysconfig.get_config_var('INCLUDEPY'))"
```

**Fix strategies:**
1. **Stub the missing module** — create a pure-Python `.py` file with the required constants/functions (e.g. `_testcapi.py` with `DBL_MIN`/`DBL_MAX`)
2. **Use system Python for the venv** — recreate venv with `/usr/bin/python3 -m venv`
3. **Install python3-dev / python3-full** — ensures C extension headers are present
4. **Never copy `.so` across Python minor versions** — it will fail with undefined symbols

### Phase 1 Completion Checklist

- [ ] Error messages fully read and understood
- [ ] Issue reproduced consistently
- [ ] Recent changes identified and reviewed
- [ ] Evidence gathered (logs, state, data flow)
- [ ] Problem isolated to specific component/code
- [ ] Root cause hypothesis formed

**STOP:** Do not proceed to Phase 2 until you understand WHY it's happening.

---

## Phase 2: Pattern Analysis

**Find the pattern before fixing:**

### 1. Find Working Examples

- Locate similar working code in the same codebase
- What works that's similar to what's broken?

**Action:** Use `search_files` to find comparable patterns:

```python
search_files("similar_pattern", path="src/", file_glob="*.py")
```

### 2. Compare Against References

- If implementing a pattern, read the reference implementation COMPLETELY
- Don't skim — read every line
- Understand the pattern fully before applying

### 3. Identify Differences

- What's different between working and broken?
- List every difference, however small
- Don't assume "that can't matter"

### 4. Understand Dependencies

- What other components does this need?
- What settings, config, environment?
- What assumptions does it make?

---

## Phase 3: Hypothesis and Testing

**Scientific method:**

### 1. Form a Single Hypothesis

- State clearly: "I think X is the root cause because Y"
- Write it down
- Be specific, not vague

### 2. Test Minimally

- Make the SMALLEST possible change to test the hypothesis
- One variable at a time
- Don't fix multiple things at once

### 3. Verify Before Continuing

- Did it work? → Phase 4
- Didn't work? → Form NEW hypothesis
- DON'T add more fixes on top

### 4. When You Don't Know

- Say "I don't understand X"
- Don't pretend to know
- Ask the user for help
- Research more

---

## Phase 4: Implementation

**Fix the root cause, not the symptom:**

### 1. Create Failing Test Case

- Simplest possible reproduction
- Automated test if possible
- MUST have before fixing
- Use the `test-driven-development` skill

### 2. Implement Single Fix

- Address the root cause identified
- ONE change at a time
- No "while I'm here" improvements
- No bundled refactoring

### 3. Verify Fix

```bash
# Run the specific regression test
pytest tests/test_module.py::test_regression -v

# Run full suite — no regressions
pytest tests/ -q
```

### 4. If Fix Doesn't Work — The Rule of Three

- **STOP.**
- Count: How many fixes have you tried?
- If < 3: Return to Phase 1, re-analyze with new information
- **If ≥ 3: STOP and question the architecture (step 5 below)**
- DON'T attempt Fix #4 without architectural discussion

### 5. If 3+ Fixes Failed: Question Architecture

**Pattern indicating an architectural problem:**
- Each fix reveals new shared state/coupling in a different place
- Fixes require "massive refactoring" to implement
- Each fix creates new symptoms elsewhere

**STOP and question fundamentals:**
- Is this pattern fundamentally sound?
- Are we "sticking with it through sheer inertia"?
- Should we refactor the architecture vs. continue fixing symptoms?

**Discuss with the user before attempting more fixes.**

This is NOT a failed hypothesis — this is a wrong architecture.

---

## Red Flags — STOP and Follow Process

If you catch yourself thinking:
- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "Add multiple changes, run tests"
- "Skip the test, I'll manually verify"
- "It's probably X, let me fix that"
- "I don't fully understand but this might work"
- "Pattern says X but I'll adapt it differently"
- "Here are the main problems: [lists fixes without investigation]"
- Proposing solutions before tracing data flow
- **"One more fix attempt" (when already tried 2+)**
- **Each fix reveals a new problem in a different place**

**ALL of these mean: STOP. Return to Phase 1.**

**If 3+ fixes failed:** Question the architecture (Phase 4 step 5).

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Issue is simple, don't need process" | Simple issues have root causes too. Process is fast for simple bugs. |
| "Emergency, no time for process" | Systematic debugging is FASTER than guess-and-check thrashing. |
| "Just try this first, then investigate" | First fix sets the pattern. Do it right from the start. |
| "I'll write test after confirming fix works" | Untested fixes don't stick. Test first proves it. |
| "Multiple fixes at once saves time" | Can't isolate what worked. Causes new bugs. |
| "Reference too long, I'll adapt the pattern" | Partial understanding guarantees bugs. Read it completely. |
| "I see the problem, let me fix it" | Seeing symptoms ≠ understanding root cause. |
| "One more fix attempt" (after 2+ failures) | 3+ failures = architectural problem. Question the pattern, don't fix again. |
| **"系统跑通了，基线是XX秒" — without verifying data source** | Claiming performance baselines without verifying the data is real (not simulated) will get called out. Verify source before reporting numbers. |

## Data Source Authenticity & System State Rule

When reporting system state, performance baselines, "it works" claims, or **any factual assertion about what exists on the filesystem**:

**MUST verify before claiming:**
1. Is the data coming from a real API or simulated/synthetic?
2. Check timestamps — are they recent (not stale cached)?
3. Check values — do they match live market data (not hardcoded defaults)?
4. For **filesystem claims** (files exist, directories present, models cached) → use `ls`/`find`/`stat` in terminal or `search_files` to **verify on disk**. Never rely on memory or context summaries for file state.
5. If uncertain → say "我没确认" and verify first

**This applies especially when:**
- Reporting pipeline timing baselines
- Claiming a fix resolved a data issue
- Presenting real-time data as evidence of system health
- **Crossing context windows** (context compression/summarization)

### ⚠️ CRITICAL: Context Summary Skepticism

Context summaries (auto-generated session handoffs) are **LLM-generated** and CAN hallucinate file system, model, and cache state. **Treat them as navigation aids, not authoritative sources.**

**FAILURE PATTERN (documented from real sessions):**
- Context summary claims "HuggingFace cache also purged" → ❌ FALSE. HF cache was intact with 391MB model.
- Assistant accepted the claim without `find` verification → repeated the falsehood to user → user frustrated.

**Required procedure on cross-window handoff:**
1. Context summary says something exists or doesn't exist on disk → **verify with `ls`/`find`/`stat`**
2. Context summary claims a file was deleted/created → **check the actual path**
3. Context summary describes current architecture → **walk the directory tree to confirm**
4. If uncertain about a claim from context summary → **say "让我查一下盘上实际情况"** — never pass it through unexamined

**Never:** repeat a filesystem claim from compressed context without disk verification, especially when:
- The user has corrected you before about file state claims
- The claim involves "deleted", "purged", "removed" or other definitive state assertions
- You're in a new context window and the only source is the summary

### Additional Caution With Cross-Window Claims

**When crossing context windows** (new session after compression): the summary may describe past work incorrectly. Specifically watch for:
- **Claiming something "doesn't exist"** when it's still on disk (most dangerous — leads to redundant work)
- **Claiming something "works" or "is fixed"** when it wasn't verified
- **Attributing actions to the wrong session** or sequence

When in doubt: `find`, `ls`, `stat`. This takes 2 seconds and prevents a 5-minute argument.

## Phase 5 (Extension): Verifying Running Services / Daemon Threads

**Use when the question is "is X actually doing its thing inside the live process?" — NOT "does the code work?"**

### The Isolation Test Trap (⚠️ CORRECTION-DRIVEN)

**Don't test in a separate python3 process and infer the gateway process is fine.** The code may work in isolation but:
- The daemon thread may not have started (import failed silently)
- The thread may have crashed on first run (exception killed daemon thread, no trace)
- Logger config may differ between isolated test and gateway
- Plugin loading order may affect availability of dependencies

**Correct procedure — verify via the ACTUAL gateway process:**

### Step 1: Check Process Thread Count

```bash
# Gateway PID
ps aux | grep "hermes.*gateway" | grep -v grep
# Threads
ps -T -p <PID> -o lwp,comm | wc -l
# Expected: 8-12 threads (main + cron + memory_monitor + platform threads + daemon threads)
```

### Step 2: Find Hard Evidence in Side Effects

Daemon threads that write to files — check the **output artifacts**:

```bash
# DB modification time (does it match pulse interval?)
ls -la data/market.db
# Check latest row timestamp vs gateway start time
python3 -c "
import sqlite3, os
conn = sqlite3.connect('data/market.db')
ts = conn.execute('SELECT MAX(timestamp) FROM raw_snapshots').fetchone()[0]
print(f'Latest snapshot: {ts}')
" 
```

**Key insight:** If the DB was last modified after gateway startup with recent data → daemon IS running. This is MORE reliable than log output (loggers can be misconfigured).

### Step 3: Look Beyond Log Output

**Log output absence ≠ daemon is dead.** Possible reasons:
- Logger not configured at the specific sub-logger level (e.g., `onebot3.scheduler` not propagated to root logger handler)
- Log level filtering (INFO filtered out by handler config)
- Exception caught silently at wrong logger level

**Always cross-check with side effects** (DB writes, file timestamps, /proc counters) before claiming a daemon is down.

### Step 4: Correlate with Gateway Restart Time

```bash
# When did gateway start?
stat -c '%y' /proc/<PID> 2>/dev/null
# OR from logs:
grep "Starting Hermes Gateway" ~/.hermes/logs/gateway.log | tail -1

# Compare with artifact timestamps
# - DB last modification
# - Latest snapshot timestamp
# - Did data write AFTER restart? → thread alive
# - Data only from BEFORE restart? → thread never ran in this session
```

### Step 5: Verify Data Content Freshness

Don't just check timestamps — verify the actual data values:

```python
# Check that the latest snapshot has real market data, not stale defaults
snap = db.execute("SELECT underlying_price, gex FROM raw_snapshots ORDER BY rowid DESC LIMIT 1").fetchone()
# Price should match live market, GEX should be non-zero
```

### Common Pitfalls

| Assumption | Reality | Evidence |
|------------|---------|----------|
| "Log shows no [PULSE] → daemon dead" | Logger may not be wired to handler | DB has fresh data ✅ |
| "Test in python3 -c 'from scheduler import start_all' works → gateway is fine" | daemon thread in separate process, not gateway | Thread not in /proc/<gateway_PID>/task |
| "market.db exists → data fresh" | DB could be from PREVIOUS gateway session | Compare DB mtime to gateway start time |
| "Gateway has 9 threads → daemons accounted for" | Could be platform/cron threads, not pulse | Need to verify via data content |

### When User Says "别撒谎，你检查彻底了吗"

**STOP. Do not defend. Do not re-assert.** The user is saying your evidence chain is incomplete.

**Immediate action:**
1. Acknowledge the gap: "你說得對，我來徹底查"
2. Go back to Step 1-5 above — produce hard evidence
3. Only conclude after verifying via process artifacts (DB, threads, file timestamps)
4. If wrong, admit it clearly with the correct evidence

## Quick Reference

| Phase | Key Activities | Success Criteria |
|-------|---------------|------------------|
| **1. Root Cause** | Read errors, reproduce, check changes, gather evidence, trace data flow | Understand WHAT and WHY |
| **2. Pattern** | Find working examples, compare, identify differences | Know what's different |
| **3. Hypothesis** | Form theory, test minimally, one variable at a time | Confirmed or new hypothesis |
| **4. Implementation** | Create regression test, fix root cause, verify | Bug resolved, all tests pass |

## Hermes Agent Integration

### Investigation Tools

Use these Hermes tools during Phase 1:

- **`search_files`** — Find error strings, trace function calls, locate patterns
- **`read_file`** — Read source code with line numbers for precise analysis
- **`terminal`** — Run tests, check git history, reproduce bugs
- **`web_search`/`web_extract`** — Research error messages, library docs

### With delegate_task

For complex multi-component debugging, dispatch investigation subagents:

```python
delegate_task(
    goal="Investigate why [specific test/behavior] fails",
    context="""
    Follow systematic-debugging skill:
    1. Read the error message carefully
    2. Reproduce the issue
    3. Trace the data flow to find root cause
    4. Report findings — do NOT fix yet

    Error: [paste full error]
    File: [path to failing code]
    Test command: [exact command]
    """,
    toolsets=['terminal', 'file']
)
```

### With test-driven-development

When fixing bugs:
1. Write a test that reproduces the bug (RED)
2. Debug systematically to find root cause
3. Fix the root cause (GREEN)
4. The test proves the fix and prevents regression

## Real-World Impact

From debugging sessions:
- Systematic approach: 15-30 minutes to fix
- Random fixes approach: 2-3 hours of thrashing
- First-time fix rate: 95% vs 40%
- New bugs introduced: Near zero vs common

**No shortcuts. No guessing. Systematic always wins.**
