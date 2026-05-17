# Fitness Metric 区分度修复方案

> 创建时间: 2026-05-15
> 来源: DeepSeek 方案 + 实际验证
> 问题: Direct LLM Mutation v2 中所有变体得分相同 (0.500)，无法区分好坏

## 问题根因

1. **SkillExecutor 只做字符串匹配** — 检查输出是否包含 MUST/NEVER 关键词，无法捕捉语义差异
2. **Fitness metric 太简单** — 约束合规 50% + 关键词重叠 50%，区分度为 0
3. **没有真正执行 skill** — 没有让 LLM 用 skill 生成输出再评估

## 解决方案: LLM-as-Judge 对比评估

核心洞察: **skill 的本质是规则集合**。好的 skill 应该让 AI 输出更符合规则。所以 fitness 应该衡量：

> 给定同样的 task input，用 skill A 和 skill B 分别生成输出，哪个输出更好？

### 评估流程

```
对每个 skill 变体:
  1. 生成测试 task（从 skill 规则中提取主题）
  2. 用 skill 指导 LLM 生成输出 output_A
  3. 不用 skill 生成基线输出 output_B
  4. LLM judge 对比 output_A vs output_B
  5. 返回 constraint_score + behavior_score
```

### 成本

每个变体 **2 次 LLM 调用**:
1. 生成输出（~500 tokens）
2. Judge 评估（~300 tokens）

5 个变体 ≈ 10 次调用，成本可控。

### 关键代码结构

```python
class ImprovedFitnessEvaluator:
    def __init__(self, llm_client, judge_model="deepseek-chat"):
        self.client = llm_client
        self.judge_model = judge_model

    def evaluate_skill(self, skill: Skill, reference_skill: Skill = None):
        # 1. 生成测试 task
        task = self._generate_task(skill)

        # 2. 用 skill 生成输出
        output = self._generate_with_skill(task, skill)

        # 3. 生成基线输出
        ref_output = self._generate_without_skill(task)

        # 4. LLM judge 对比评估
        return self._llm_judge(task, output, ref_output, skill)

    def _llm_judge(self, task, output, ref_output, skill):
        prompt = f"""对比两个AI输出，评估它们对规则的遵守程度。

任务: {task}
规则: {skill.text}

输出A（使用规则）: {output}
输出B（无规则）: {ref_output}

评分（0-1，JSON格式）:
{{
    "constraint_score": float,  // 输出A比B更好地遵守规则？
    "behavior_score": float,    // 输出A比B更符合期望行为？
    "constraint_reason": str,
    "behavior_reason": str
}}"""

        response = self.client.chat.completions.create(
            model=self.judge_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300,
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        return result["constraint_score"], result["behavior_score"]
```

## 与简单字符串匹配的对比

| 维度 | 字符串匹配 (原方案) | LLM-as-Judge (新方案) |
|------|-------------------|---------------------|
| 区分度 | 0（所有变体同分） | > 0（能区分好坏） |
| 语义理解 | ❌ 无 | ✅ 有 |
| 成本 | 0 LLM 调用 | 2 LLM 调用/变体 |
| 速度 | 快（本地计算） | 慢（API 调用） |
| 准确性 | 低 | 高 |

## 实施建议

1. **保留原方案作为 fallback** — 当 LLM API 不可用时回退到字符串匹配
2. **批量评估** — 所有变体共享同一个基线输出，减少 50% 调用
3. **缓存结果** — 相同 task + skill 组合缓存 judge 结果
4. **渐进式启用** — 先对关键 skill 启用，验证效果后再推广

## 相关文件

- `evolution/skills/skill_executor.py` — 原字符串匹配实现
- `evolution/core/fitness.py` — 原 fitness metric
- `evolution/skills/evolve_skill_v2.py` — 需要集成新评估器
