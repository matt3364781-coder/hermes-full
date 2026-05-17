# ONEBOT Evolution Results

> 创建时间: 2026-05-16
> 记录 ONEBOT 系列 skill 的进化运行结果

## 运行记录

### 2026-05-15 批次

| Skill | Engine | Runs | Variations | Tasks | Baseline | Best | Improvement | Status |
|-------|--------|------|-----------|-------|----------|------|-------------|--------|
| hermes-execution-guardrails | v2 | 5 | 3-5 | 10-20 | 0.500 | 1.000 | +100% | ✅ 成功 |
| onebot-l2-prediction | v2 | 7 | 3 | 10 | 0.0 | 0.0 | 0% | ❌ 失败 |
| onebot-l3-analysis | v2 | 3 | 3 | 10 | 0.0 | 0.0 | 0% | ❌ 失败 |
| onebot-l4-arbitration | v2 | 3 | 3 | 10 | 0.0 | 0.0 | 0% | ❌ 失败 |
| onebot-l6-minervini | v2 | 1 | 3 | 10 | 1.0 | 1.0 | 0% | ❌ 无改进 |
| brainstorming | v1 | 1 | - | - | N/A | N/A | 0% | - |
| dispatching-parallel-agents | v1 | 1 | - | - | N/A | N/A | -0.5% | - |
| hermes-self-evolution | v1 | 1 | - | - | N/A | N/A | 0% | - |
| verification-before-completion | v1 | 1 | - | - | N/A | N/A | 0% | - |

### hermes-execution-guardrails 成功案例

**最佳运行** (20260515_175927):
```json
{
  "baseline_median": 0.5,
  "best_median": 1.0,
  "improvement": 0.5,
  "variations": 3,
  "num_tasks": 10,
  "constraints_passed": true,
  "elapsed_seconds": 257
}
```

**关键成功因素**:
1. Behavior constraint skill（定义 AI 行为规则）
2. Red-team tasks 设计有效（让 baseline 违反规则）
3. 二进制评分 + median 聚合区分度明显

### ONEBOT 技术文档技能失败分析

**失败模式**:
- baseline_median = 0.0（所有变体都拿 0 分）
- 或 baseline_median = 1.0（已达上限，无改进空间）

**根因**: 技术文档 skill 不适用 behavior skill 的评估策略
- 详见 `references/technical-skill-evaluation-fix.md`

## Skill 大小统计

| Skill | Size | Type |
|-------|------|------|
| onebot-3.0 | 5.2KB | umbrella |
| onebot-l1-data | 8.8KB | technical |
| onebot-l2-prediction | 6.7KB | technical |
| onebot-l3-analysis | 8.2KB | technical |
| onebot-l4-arbitration | 8.5KB | technical |
| onebot-l5-backtest | 0.7KB | technical |
| onebot-l6-minervini | 0.8KB | technical |
| onebot-l7-llm | 6.4KB | technical |
| onebot-core-engine | 3.1KB | technical |
| onebot-architecture | 6.8KB | technical |
| onebot-constitution | 5.0KB | technical |
| onebot-quant-models | 5.5KB | technical |
| onebot-source-fixes | 12.0KB | technical |
| onebot-workflow-pitfalls | 37.2KB | technical |

## 结论

- **Behavior skill**: v2 进化有效，hermes-execution-guardrails 达到 +100% 提升
- **Technical skill**: v2 进化无效，需要专门的格式验证评估器
- **Umbrella skill** (onebot-3.0): 5.2KB，不需要拆分
- **所有 ONEBOT skill** < 20KB，无需拆分
