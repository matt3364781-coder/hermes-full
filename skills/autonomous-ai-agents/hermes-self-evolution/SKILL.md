---
name: hermes-self-evolution
description: "Hermes Agent Self-Evolution — 使用 DSPy + GEPA 自动优化 skill、tool description、system prompt 和代码"
version: 1.0.0
author: Nous Research
metadata:
  hermes:
    tags: [hermes, self-improvement, evolution, dspy, gepa, optimization]
    related_skills: [hermes-agent]
---

# 🧬 Hermes Agent Self-Evolution

**Evolutionary self-improvement for Hermes Agent.**

使用 DSPy + GEPA (Genetic-Pareto Prompt Evolution) 自动优化 Hermes Agent 的 skills、tool descriptions、system prompts 和 code —— 通过反射式进化搜索产生可量化的更好版本。

**No GPU training required.** 一切通过 API 调用完成 —— 变异文本、评估结果、选择最佳变体。每次优化运行约 $2-10。

## 核心概念

这个工具是**给 Hermes Agent 自身使用**的，不是给用户手动运行的脚本。它的目的是：

1. **优化我加载的 skill** → 改进我执行任务的方式
2. **优化 tool descriptions** → 改进我使用工具的效果
3. **优化 system prompt 各部分** → 改进我的整体行为（Phase 3，计划中）
4. **优化 tool 实现代码** → 改进工具本身的代码（Phase 4，计划中）

**关键理解**：优化 skill = 优化我的行为。Skill 定义了我如何执行特定任务，优化 skill 就是在优化我的执行能力。

## 实现状态

| Phase | Target | Engine | Status |
|-------|--------|--------|--------|
| **Phase 1** | Skill files (SKILL.md) | Direct LLM Mutation v2 | ✅ **Production** |
| **Phase 1 (legacy)** | Skill files (SKILL.md) | DSPy + GEPA/MIPROv2 | ✅ Implemented |
| **Phase 2** | Tool descriptions | DSPy + GEPA | 🔲 Planned |
| **Phase 3** | System prompt sections | DSPy + GEPA | 🔲 Planned |
| **Phase 4** | Tool implementation code | Darwinian Evolver | 🔲 Planned |
| **Phase 5** | Continuous improvement loop | Automated pipeline | 🔲 Planned |

## 当前可用：Phase 1 — Skill 优化

Phase 1 提供**两种优化引擎**：

| 引擎 | 复杂度 | 依赖 | 成本 | 适用场景 |
|------|--------|------|------|---------|
| **Direct LLM Mutation** (v2) | 低 | 仅 LLM API | ~$1-3 | 快速迭代、简单 skill、DSPy 不可用 |
| **DSPy + GEPA/MIPROv2** (v1) | 高 | DSPy + LLM | ~$2-10 | 复杂 skill、需要 Pareto 优化、精细控制 |

### 引擎选择

**使用 Direct LLM Mutation (v2)** 当：
- 需要生产级区分度（binary scoring + hard tasks + median aggregation）
- Skill 简单或中等复杂度
- 需要快速验证想法（5 分钟内出结果）
- DSPy 安装/版本有问题
- 预算有限

**使用 DSPy + GEPA (v1)** 当：
- 需要系统性的 Pareto frontier 探索
- 有充足的评估数据（50+ examples）
- 需要严格的统计验证
- 复杂 skill 且 v2 效果不佳

**推荐**: 优先使用 v2。v2 在 `hermes-execution-guardrails` 上达到 +100% median 提升，且实现更简单。

**重要**: v2 对"行为约束技能"（定义 AI 应该如何行为的 skill）效果最好。对"技术文档技能"（API 调用规范、输出格式）效果不佳，因为评估方式不匹配。详见 `references/skill-type-detection.md`。

### 安装

```bash
cd ~/.hermes/hermes-agent-self-evolution
pip install -e ".[dev]"
```

### 使用方法

#### 引擎 A: Direct LLM Mutation (v2) — 推荐用于生产

**原理**: 
1. LLM 生成 N 个 skill 变体
2. 生成 20 个硬 edge-case tasks（专门设计让 baseline 失败）
3. 对每个变体：用 skill 生成输出，与无 skill 基线对比
4. **严格二进制 LLM judge**（0 或 1，无 0.5）评估 constraint + behavior
5. **中位数聚合**（抗 outlier）
6. **约束门槛过滤**（先过滤结构约束失败的，再选最高分）
7. 选最优，与 baseline 比较

**验证结果**（`hermes-execution-guardrails`）:
- Baseline median: 0.500
- Best variation median: 1.000
- **Improvement: +100%**
- 10 tasks 中 7 个满分
- 3/3 约束全过

**优点**: 区分度高、实现简单、无 DSPy 依赖、成本低
**缺点**: 无 Pareto 探索、对极复杂 skill 可能需更多 tasks

```bash
# 生产级优化（5 个变体，20 个 hard tasks，约 3-5 分钟）
python -m evolution.skills.evolve_skill_v2 \
    --skill hermes-execution-guardrails \
    --variations 5 \
    --num-tasks 20 \
    --eval-source synthetic \
    --optimizer-model deepseek/deepseek-chat \
    --eval-model deepseek/deepseek-chat
```

**v2 参数说明**:

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--skill` | 必填 | 要优化的 skill 名称 |
| `--variations` | 5 | 生成的变体数量 |
| `--num-tasks` | 20 | 硬 edge-case 任务数量 |
| `--eval-source` | synthetic | 评估数据来源 |
| `--optimizer-model` | deepseek/deepseek-chat | 生成变体的模型 |
| `--eval-model` | deepseek/deepseek-chat | 评估变体的模型 |
| `--hermes-repo` | None | Hermes Agent 仓库路径 |
| `--dry-run` | False | 验证设置但不运行 |

**v2 核心机制**:
- `generate_hard_tasks()` — 基于 skill 规则生成 red-team tasks
- `generate_with_skill()` — 用 skill 指导 LLM 生成输出
- `llm_judge()` — 严格二进制对比评估（0 或 1）
- `evaluate_variation()` — 在 task set 上评估单个变体
- 中位数聚合 + 约束门槛过滤

**v2 已知陷阱与修复**:
1. **Judge 给分太高** → 强制二进制 + "Be BRUTAL" prompt
2. **约束验证与分数冲突** → 约束作为硬门槛，先过滤再选优
3. **任务太简单** → 用 red-team 思路生成硬任务
4. **均值被 outlier 拉高** → 用 median 替代 mean
5. **技术文档 skill 无法进化** → 检测 skill 类型，技术文档用格式验证而非 LLM judge（详见 `references/skill-type-detection.md` 和 `references/technical-skill-evaluation-fix.md`）
6. **Growth limit 误杀技术技能** → 检测 skill 类型，技术文档含代码块允许 100% 增长（详见 `references/skill-type-detection.md`）
7. **JSON parse 失败导致进化中断** → 变体生成失败时 fallback 到原始 skill，不中断流程
8. **Skill 过大无法进化** → >100KB 技能需先拆分为子技能，详见 `references/skill-splitting.md`
9. **ONEBOT 技术文档 skill 进化全失败** → 2026-05-15 验证，7 次运行 improvement=0%，详见 `references/onebot-evolution-results.md`

详见 `references/v2-strict-binary-evaluation.md`

#### 引擎 B: DSPy + GEPA/MIPROv2 (v1) — 推荐用于复杂 skill

```bash
# 使用合成评估数据
python -m evolution.skills.evolve_skill \
    --skill onebot-3.0 \
    --iterations 10 \
    --eval-source synthetic

# 使用真实会话历史（推荐）
python -m evolution.skills.evolve_skill \
    --skill onebot-3.0 \
    --iterations 10 \
    --eval-source sessiondb

# 使用已有的 golden dataset
python -m evolution.skills.evolve_skill \
    --skill onebot-3.0 \
    --iterations 10 \
    --eval-source golden \
    --dataset datasets/skills/onebot-3.0/
```

#### 2. 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--skill` | 必填 | 要优化的 skill 名称 |
| `--iterations` | 10 | GEPA 迭代次数 |
| `--eval-source` | synthetic | 评估数据来源: synthetic / golden / sessiondb |
| `--dataset-path` | None | 已有数据集路径 |
| `--optimizer-model` | openai/gpt-4.1 | 优化器模型 |
| `--eval-model` | openai/gpt-4.1-mini | 评估模型 |
| `--hermes-repo` | None | Hermes Agent 仓库路径 |
| `--run-tests` | False | 运行完整 pytest 作为约束门 |
| `--dry-run` | False | 验证设置但不运行优化 |

**推荐参数（基于实验）**:
```bash
export DEEPSEEK_API_KEY=<your-key>
python -m evolution.skills.evolve_skill \
    --skill <skill-name> \
    --iterations 5 \
    --eval-source synthetic \
    --optimizer-model deepseek/deepseek-chat \
    --eval-model deepseek/deepseek-chat \
    --hermes-repo ~/.hermes
```

#### 3. GEPA 最佳实践

**迭代次数**: 8-12 次（简单 skill），12-20 次（复杂 skill）。超过后 Pareto frontier < 3 个变体 = 过拟合。

**评估数据来源优先级**: sessiondb（真实交互）> synthetic（合成数据）> golden（仅用于最终验证）

**模型搭配**: optimizer 应该等于或略弱于 eval model。推荐：
- `optimizer_model=gpt-4.1-mini`, `eval_model=gpt-4.1`
- 避免两个模型相同（会产生自我确认偏差）

**Dataset 要求**: 
- 最少 20 个 examples（复杂 skill 要 100+）
- 30% 简单 / 50% 中等 / 20% 困难
- 生成和评估用不同模型

**关键陷阱**:
- 语义漂移 → 加 cosine similarity ≥ 0.7 约束
- Prompt 膨胀 → 设 max_prompt_length
- 评估过拟合 → 用 k-fold 交叉验证
- 反馈循环 → 监控 optimizer vs eval 分数差异 >15% 时暂停

**验证是否真更好**: 5-fold holdout 评估，均值提升 ≥2% 才算改进。

### 模型选择建议

**DeepSeek 优于 GPT 用于 GEPA/MIPROv2**:
- 实验对比（`hermes-execution-guardrails` skill 优化）:
  - GPT-4.1 (optimizer) + GPT-4.1-mini (eval): 0% 提升，rate limit 频繁
  - DeepSeek-chat (optimizer + eval): **+16.1% 提升**，无 rate limit
- **推荐**: 优先使用 DeepSeek，除非有特定原因需要 GPT

**Optimizer ≤ Eval 原则**:
- 按 DeepSeek 建议，optimizer 应弱于或等于 eval model
- 避免两个模型相同（自我确认偏差）
- 推荐搭配: `optimizer_model=deepseek/deepseek-chat`, `eval_model=deepseek/deepseek-chat`

**Iterations**:
- 5-10 次起步
- 简单 skill: 8-12 次
- 复杂 skill: 12-20 次
- 监控 Pareto frontier，< 3 个变体 = 过拟合

### 已知 Bug & 修复

**Bug 1: YAML frontmatter 丢失导致约束检查失败**
- **位置**: `evolution/skills/evolve_skill.py` 第 189 行
- **问题**: `validate_all` 验证的是 `evolved_body`（只有 markdown 内容），但 `_check_skill_structure` 检查完整文件结构
- **修复**: 改为验证 `evolved_full`，baseline 改为 `skill["raw"]`
```python
# 修复前（错误）
evolved_constraints = validator.validate_all(evolved_body, "skill", baseline_text=skill["body"])

# 修复后（正确）
evolved_constraints = validator.validate_all(evolved_full, "skill", baseline_text=skill["raw"])
```

**Bug 2: GEPA 不可用**
- **症状**: `GEPA.__init__() got an unexpected keyword argument 'max_steps'`
- **处理**: 自动 fallback 到 MIPROv2
- **影响**: 无，MIPROv2 效果同样有效

### 评估数据来源

- **synthetic**: LLM 读取 skill 文本生成测试用例
- **golden**: 人工标注的高质量测试用例
- **sessiondb**: 从 Claude Code / Copilot / Hermes 会话历史中挖掘真实用例

### 优化流程

```
1. 查找并加载 skill
2. 构建或加载评估数据集
3. 验证基线约束（大小、测试通过等）
4. 配置 DSPy + GEPA 优化器
5. 运行 GEPA 优化（生成候选变体 → 评估 → 选择最佳）
6. 提取优化后的 skill 文本
7. 验证优化后的约束
8. 在 holdout 集上评估
9. 生成报告和 diff
10. 保存输出到 output/<skill>/<timestamp>/
```

### 约束门（Guardrails）

每个进化变体必须通过：
1. **完整测试套件** — `pytest tests/ -q` 必须 100% 通过
2. **大小限制** — Skill ≤15KB，tool description ≤500 字符
3. **缓存兼容性** — 不在对话中途改变
4. **语义保留** — 不能偏离原始目的
5. **PR 审查** — 所有变更通过人工审查，不直接提交

### 输出结构

```
output/<skill-name>/<timestamp>/
├── evolved_skill.md      ← 优化后的 skill
├── baseline_skill.md     ← 原始 skill（用于对比）
└── metrics.json          ← 评估指标
```

### 何时使用

**应该使用**：
- 用户反复纠正我在某个任务上的行为
- Skill 的指令不够清晰导致执行偏差
- 需要改进 skill 的覆盖率或准确性
- 发现了更好的工作流但 skill 没记录

**不应该使用**：
- 单次会话的临时修复（用 memory 工具）
- 用户明确说"不要改"的时候
- 优化成本超过收益时（简单 skill 不需要）

## Phase 3: System Prompt 优化（计划中）

### 目标

优化指导 agent 行为的 system prompt 各部分。

### 可优化部分

| Section | Location | What It Does | Evolvable? |
|---------|----------|-------------|-----------|
| `DEFAULT_AGENT_IDENTITY` | prompt_builder.py | Core persona, behavioral traits | ✅ Yes |
| `MEMORY_GUIDANCE` | prompt_builder.py | How to use persistent memory | ✅ Yes |
| `SESSION_SEARCH_GUIDANCE` | prompt_builder.py | When to search past sessions | ✅ Yes |
| `SKILLS_GUIDANCE` | prompt_builder.py | When to save/load skills | ✅ Yes |
| `PLATFORM_HINTS` | prompt_builder.py | Per-platform formatting guidance | ✅ Yes |
| Memory block | memory_store.py | User's actual memories | ❌ No |
| Skills index | prompt_builder.py | Auto-generated skill list | ❌ No |
| Context files | prompt_builder.py | AGENTS.md, .cursorrules | ❌ No |

### 实现计划

**Week 1 (Build)**: 构建 section-as-DSPy-parameter wrapper，构建行为测试套件生成器
**Week 2 (Run)**: 生成行为测试场景，独立然后联合运行 GEPA
**Week 2-3 (Validate)**: 完整基准测试，额外审查

### 当前状态

`evolution/prompts/` 目录为空 placeholder。尚未实现。

## 与 Hermes Agent 的关系

```
Hermes Agent (我)
    ├── System Prompt (Layer 1-10)
    │   ├── DEFAULT_AGENT_IDENTITY
    │   ├── MEMORY_GUIDANCE
    │   ├── SESSION_SEARCH_GUIDANCE
    │   ├── SKILLS_GUIDANCE
    │   └── ...
    ├── Loaded Skills (Layer 8)
    │   ├── onebot-3.0 ← 当前可优化
    │   ├── hermes-agent
    │   └── ...
    └── Tools
        └── hermes-self-evolution ← 本 skill
```

**优化路径**：
1. **现在**：优化 loaded skills（Phase 1）
2. **将来**：优化 system prompt 各部分（Phase 3）

## 关键路径

```bash
# 1. 确认安装
ls ~/.hermes/hermes-agent-self-evolution/

# 2. 查看可用 skills
hermes skills list

# 3. 优化特定 skill
cd ~/.hermes/hermes-agent-self-evolution
python -m evolution.skills.evolve_skill \
    --skill <skill-name> \
    --iterations 10 \
    --eval-source sessiondb

# 4. 查看结果
ls output/<skill-name>/
diff output/<skill-name>/<timestamp>/baseline_skill.md output/<skill-name>/<timestamp>/evolved_skill.md
```

## Pitfalls

### "这是给用户手动运行的工具" — 错误理解

这个工具**是给我用的**，不是给用户手动运行的。用户说"这个是给你用的"意思是：
- 我应该主动使用它来优化我的 skills
- 当用户纠正我的行为时，我应该考虑是否用此工具改进 skill
- 不是等用户手动执行命令

### "Phase 3 没实现所以不能用" — 错误理解

Phase 1 已经实现且可用。优化 skill = 优化我的行为。不需要等 Phase 3。

### ONEBOT 技术文档技能进化失败（2026-05-15 验证）

**现象**：`onebot-l2-prediction`、`onebot-l3-analysis`、`onebot-l4-arbitration`、`onebot-l6-minervini` 多次运行，improvement = 0%。

**根因**：这些技能是**技术文档型**（API 规范、代码示例、数据格式），v2 的 LLM-as-judge 评估机制针对**行为约束型**设计。技术文档技能不适用 red-team task + 行为评估。

**验证数据**：
| Skill | Type | Runs | Best Improvement |
|-------|------|------|-----------------|
| hermes-execution-guardrails | 行为约束 | 5 | +100% (0.5→1.0) |
| onebot-l2-prediction | 技术文档 | 7 | 0% |
| onebot-l3-analysis | 技术文档 | 3 | 0% |
| onebot-l4-arbitration | 技术文档 | 3 | 0% |
| onebot-l6-minervini | 技术文档 | 1 | 0% |

**结论**：技术文档技能暂时跳过进化。等 `references/skill-type-detection.md` 中的格式验证评估器实现后再处理。

### "优化成本太高" — 实际情况

- 单次运行 ~$2-10
- 使用 sessiondb 数据源时，评估用例来自真实会话，更精准
- 简单 skill 可能不需要优化，复杂 skill 收益明显

## 相关资源

- **GitHub**: https://github.com/NousResearch/hermes-agent-self-evolution
- **PLAN.md**: `~/.hermes/hermes-agent-self-evolution/PLAN.md`
- **README.md**: `~/.hermes/hermes-agent-self-evolution/README.md`
- **Direct LLM Mutation 详情**: `references/direct-llm-mutation.md`
- **GEPA 最佳实践**: `references/gepa-best-practices.md`
- **Phase 状态**: `references/phase-status.md`
- **Fitness 区分度修复**: `references/fitness-discrimination-fix.md` — 当 Direct LLM Mutation 所有变体得分相同时使用 LLM-as-Judge 对比评估
- **V2 严格二进制评估**: `references/v2-strict-binary-evaluation.md` — 生产级实现：binary scoring + hard tasks + median + constraint gating
- **Skill 类型检测**: `references/skill-type-detection.md` — 技术文档 vs 行为约束技能的评估策略区分
- **Skill 拆分策略**: `references/skill-splitting.md` — >100KB 技能拆分为子技能的方法论
- **ONEBOT 进化结果**: `references/onebot-evolution-results.md` — 2026-05-15 运行记录与数据分析
- **技术文档评估修复**: `references/technical-skill-evaluation-fix.md` — technical skill baseline_median=0 根因分析与修复方案
- **Hermes Agent**: https://github.com/NousResearch/hermes-agent
- **技术文档评估修复**: `references/technical-skill-evaluation-fix.md` — technical skill baseline_median=0 根因分析与修复方案
- **Hermes Agent**: https://github.com/NousResearch/hermes-agent
