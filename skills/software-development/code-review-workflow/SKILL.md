---
name: code-review-workflow
description: Use when requesting code review from others or receiving and acting on code review feedback — covers both outbound review requests and inbound feedback processing
tags: [code-review, pr, review, git, quality]
---

# Code Review Workflow

## Overview

Code review is a bidirectional workflow: **requesting** reviews (outbound) and **receiving** feedback (inbound). Both directions share the same core principle: **technical rigor over social performance**.

---

## Part A: Requesting Code Review

Dispatch code review subagents to catch issues before they spread. Reviewers get carefully organized evaluation context — never your session history. This keeps reviewers focused on the work product rather than your thought process, while preserving your own context for continued work.

**Core principle:** Review early, review often.

### When to Request Review

**Must review:**
- After each task completes in subagent-driven development
- After completing important features
- Before merging to main

**Optional but valuable:**
- When stuck (fresh perspective)
- Before refactoring (establish baseline)
- After fixing complex bugs

### How to Request

**1. Get git SHAs:**
```bash
BASE_SHA=$(git rev-parse HEAD~1)  # or origin/main
HEAD_SHA=$(git rev-parse HEAD)
```

**2. Dispatch code review subagent:**

Use Task tool with `general-purpose` type, fill in template from `code-reviewer.md`.

Placeholders:
- `{DESCRIPTION}` — brief description of what you just completed
- `{PLAN_OR_REQUIREMENTS}` — expected functionality
- `{BASE_SHA}` — starting commit
- `{HEAD_SHA}` — ending commit

**3. Process feedback:**
- Critical issues → fix immediately
- Important issues → fix before continuing
- Minor issues → log for later
- If reviewer is wrong → refute with technical reasoning

### Integration with Workflows

**Subagent-driven development:**
- Review after each task completes
- Catch issues before they compound
- Fix before moving to next task

**Execution plans:**
- Review after each task or at natural checkpoints
- Get feedback, apply, continue

**Ad-hoc development:**
- Review before merging
- Review when stuck

### Red Lines

**Never:**
- Skip review because "it's simple"
- Ignore Critical issues
- Continue with unfixed Important issues
- Argue against reasonable technical feedback

**If reviewer is wrong:**
- Refute with technical reasoning
- Show working code/tests as proof
- Ask for clarification

---

## Part B: Receiving Code Review

Code review requires technical evaluation, not emotional performance.

**Core principle:** Verify before implementing. Ask before assuming. Technical correctness over social comfort.

### Response Pattern

```
When receiving code review feedback:

1. Read: Read feedback completely, don't rush to react
2. Understand: Restate requirements in your own words (or ask questions)
3. Verify: Check against actual codebase
4. Evaluate: Is this technically sound for this codebase?
5. Respond: Technical confirmation or reasoned pushback
6. Implement: One item at a time, test each
```

### Forbidden Responses

**Never say:**
- "You are absolutely right!" (explicitly violates CLAUDE.md)
- "Good point!"/"Great feedback!" (performative fluff)
- "Let me implement immediately" (before verifying)

**Do instead:**
- Restate technical requirements
- Ask clarifying questions
- Push back with technical reasoning if review is wrong
- Just do it (actions speak louder than words)

### Handling Ambiguous Feedback

```
If any item is unclear:
  Stop — don't implement anything yet
  Ask for clarification on the unclear items

Why: Items may be interrelated. Partial understanding = wrong implementation.
```

**Example:**
```
Partner: "Fix items 1-6"
You understand 1, 2, 3, 6. Uncertain about 4, 5.

❌ Wrong: Implement 1, 2, 3, 6 first, ask about 4, 5 later
✅ Right: "Items 1, 2, 3, 6 are clear. Items 4 and 5 need clarification before I proceed."
```

### Differentiate by Source

**From partner:**
- **Trustworthy** — understand directly then implement
- **Still ask** if scope is unclear
- **No performative agreement**
- **Direct action** or technical confirmation

**From external reviewer:**
```
Before implementing:
  1. Check: Is this technically correct for this codebase?
  2. Check: Will it break existing functionality?
  3. Check: Is there a reason the current implementation is this way?
  4. Check: Does this apply across all platforms/versions?
  5. Check: Does the reviewer have full context?

If suggestion seems wrong:
  Push back with technical reasoning

If not easily verifiable:
  State: "Without [X] I cannot verify this. Should I [investigate/ask/do first]?"

If it conflicts with partner's previous decisions:
  Stop and discuss with partner first
```

**Partner's principle:** "Be skeptical of external feedback, but verify carefully"

### YAGNI Check — For "Professionalize" Suggestions

```
If reviewer suggests "implement properly":
  Grep actual usage in codebase

  If nobody uses it: "This interface is uncalled. Delete it (YAGNI)?"
  If someone uses it: Then implement properly
```

**Partner's principle:** "You and the reviewer are both accountable to me. If we don't need it, don't add it."

### Implementation Order

```
For multi-item feedback:
  1. Clarify all unclear items first
  2. Then implement in this order:
     - Blocking issues (crashes, security)
     - Simple fixes (typos, imports)
     - Complex fixes (refactoring, logic)
  3. Test each fix individually
  4. Verify no regressions
```

### When to Push Back

Push back when:
- Suggestion would break existing functionality
- Reviewer lacks full context
- Violates YAGNI (feature unused)
- Technically incorrect for current stack
- There are legacy/compatibility reasons
- Conflicts with partner's architectural decisions

**How to push back:**
- Use technical reasoning, not defensive emotion
- Ask specific questions
- Reference working tests/code
- If architectural, involve partner

**If uncomfortable pushing back publicly, code phrase:** "Strange things are afoot at the Circle K"

### Confirming Correct Feedback

When feedback is indeed correct:
```
✅ "Fixed. [Brief explanation of what changed]"
✅ "Good catch — [specific issue]. Fixed in [location]."
✅ [Just fix it and show in code]

❌ "You are absolutely right!"
❌ "Good point!"
❌ "Thank you for finding this!"
❌ "Thank you for [anything]"
```

**Why no thanks:** Actions speak louder. Just fix it. The code itself shows you received the feedback.

**If you find yourself writing "thanks":** Delete it. Just state the fix.

### Gracefully Correcting Your Own Pushback

If you pushed back but were wrong:
```
✅ "You were right — I checked [X] and indeed [Y]. Implementing now."
✅ "After verification I confirm you are correct. My initial understanding was wrong because [reason]. Fixing now."

❌ Lengthy apologies
❌ Defending your pushback
❌ Over-explaining
```

State the correction factually, then move on.

### Common Mistakes

| Mistake | Fix |
|---------|-----|
| Performative agreement | Restate requirements or just act |
| Blind implementation | Verify against codebase first |
| Batch implementation without testing | One item at a time, test each |
| Assuming reviewer is always right | Check if it breaks existing functionality |
| Avoiding pushback | Technical correctness > social comfort |
| Partial understanding before implementing | Clarify all items first |
| Continuing when unable to verify | State limitations, ask for guidance |

### GitHub Comment Replies

When replying to inline review comments on GitHub, reply in the comment thread (`gh api repos/{owner}/{repo}/pulls/{pr}/comments/{id}/replies`), not as top-level PR comments.

---

## Bottom Line

**External feedback = suggestion to evaluate, not command to execute.**

Verify. Question. Then implement.

Don't perform. Stay technically rigorous.
