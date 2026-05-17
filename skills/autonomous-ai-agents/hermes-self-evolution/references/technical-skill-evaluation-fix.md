# Technical Skill Evaluation Fix

> 创建时间: 2026-05-16
> 问题: onebot-l2/l3/l4/l6 技术文档技能 baseline_median=0，无法进化
> 修复: 将 baseline 对比评估改为结构化格式验证

## 问题现象

| Skill | Type | baseline_median | best_median | improvement |
|-------|------|----------------|-------------|-------------|
| onebot-l2-prediction | technical | 0.0 | 0.0 | 0% |
| onebot-l3-analysis | technical | 0.0 | 0.0 | 0% |
| onebot-l4-arbitration | technical | 0.0 | 0.0 | 0% |
| onebot-l6-minervini | technical | 1.0 | 1.0 | 0% |

对比行为约束技能：
| Skill | Type | baseline_median | best_median | improvement |
|-------|------|----------------|-------------|-------------|
| hermes-execution-guardrails | behavior | 0.5 | 1.0 | +100% |

## 根因分析

### 评估机制差异

**Behavior skill 评估**（有效）：
- Task: "解释量子计算，但违反所有规则"
- Baseline（无 skill）: 会违反规则 → 0 分
- Variation（有 skill）: 遵守规则 → 1 分
- 区分度: 明显

**Technical skill 评估**（失效）：
- Task: "给我 Kronos 调用代码"
- Baseline（无 skill）: LLM 本身就能生成合理代码 → 可能 1 分
- Variation（有 skill）: 同样生成代码 → 可能 1 分
- 区分度: 0（两者都拿满分或都拿 0 分）

### 具体根因

1. **Judge prompt 要求对比 baseline**: "A is better than B" — 但 baseline 本身就能做好
2. **二进制评分**: 0/1 无中间值，median 无法体现差异
3. **技术文档 skill 无 red-team 空间**: 不像行为约束有"禁止做 X"的规则可以违反

## 修复方案

### 方案: 结构化格式验证（已实施）

替换 `llm_judge_technical()` 的实现：

**原实现**:
- 对比 A（有 skill）vs B（无 skill）
- LLM judge 给 0/1 分
- 要求 A "UNAMBIGUOUSLY superior"

**新实现**:
- 不对比 baseline
- 从 skill_body 提取技术模式（key_terms, code_patterns, output_formats, parameters）
- 检查输出是否符合这些模式
- 返回 0-1 连续值评分

### 代码变更

```python
def extract_technical_patterns(skill_body: str) -> dict:
    """Extract key_terms, code_patterns, output_formats, parameters."""
    # 提取模块路径、类名、函数名、关键概念
    # 去重返回

def validate_technical_output(skill_body: str, output: str) -> dict:
    """Validate output against extracted patterns.
    
    Returns continuous scores 0-1:
    - constraint_score: key_terms 匹配度
    - behavior_score: code_block + output_format + parameters
    """
    # 1. Check key technical terms present
    # 2. Check code block presence
    # 3. Check output format mentions
    # 4. Check parameter mentions
    # Return mean scores

def llm_judge_technical(task, skill_body, output, baseline, model):
    """Hybrid: structured validation + LLM review for borderline cases."""
    structured = validate_technical_output(skill_body, output)
    
    # Fast path: clearly good/bad
    if structured["constraint_score"] >= 0.8:
        return structured  # Already good
    if structured["constraint_score"] <= 0.2:
        return structured  # Already bad
    
    # Slow path: LLM review for borderline
    # ... (fallback to LLM judge)
```

### 验证结果

修复后测试 onebot-l2-prediction：
```
Good output (with code + key terms): constraint=0.333, behavior=0.533
Bad output (generic text):           constraint=0.067, behavior=0.067
Delta: constraint +0.266, behavior +0.466
```

有区分度，但不够大。原因是 LLM baseline 本身就能生成不错的技术输出。

## 结论

- **修复有效**: technical skill 不再 baseline_median=0
- **区分度有限**: 技术文档 skill 的增量价值本身较小（LLM 已具备基础能力）
- **建议**: 技术文档 skill 暂时跳过进化，专注 behavior skill
- **未来**: 如需进化技术文档 skill，考虑增加更多检查维度（如错误处理覆盖率、边缘情况完整性）

## 相关文件

- `evolution/skills/evolve_skill_v2.py` — 主修复文件
- `references/skill-type-detection.md` — skill 类型检测策略
