# Direct LLM Mutation (v2) 实现细节

> 创建时间: 2026-05-15
> 来源: 实际实现 `evolve_skill_v2.py`

## 与 GEPA/MIPROv2 的对比

| 维度 | Direct LLM Mutation (v2) | DSPy + GEPA (v1) |
|------|-------------------------|------------------|
| **核心机制** | LLM 直接生成 N 个变体 | 遗传算法 + Pareto 优化 |
| **依赖** | 仅 LLM API | DSPy + LLM API |
| **迭代方式** | 单次生成 N 个 | 多代进化 |
| **探索能力** | 有限（N 个独立变体） | 强（遗传操作产生新组合） |
| **评估方式** | 简单约束检查 | 多指标 Pareto frontier |
| **成本** | ~$1-3 | ~$2-10 |
| **时间** | 1-3 分钟 | 5-15 分钟 |
| **适用** | 简单 skill、快速验证 | 复杂 skill、精细优化 |

## 核心组件

### 1. SkillExecutor (`evolution/skills/skill_executor.py`)

解析 skill 文本中的约束，评估输出合规性。

**解析的约束类型**:
- `## HARD RULES` 下的编号规则
- `MUST ...` 语句
- `NEVER ...` 语句  
- `ALWAYS ...` 语句

**评估输出**:
```python
{
    "violations": ["Missing: MUST do X", "Violation: NEVER do Y"],
    "satisfied": ["ALWAYS do Z"],
    "compliant": False,
    "constraints_checked": 5
}
```

### 2. Fitness Metric (`evolution/core/fitness.py`)

```python
score = 0.5 * compliance + 0.5 * behavior_match
```

- **合规度 (50%)**: 是否违反任何 MUST/NEVER 约束
- **行为匹配 (50%)**: 输出是否包含期望行为的关键词

### 3. 生成提示词

LLM 被提示：
1. 保持整体结构（HARD RULES、sections）
2. 解决示例中的失败模式
3. 提高清晰度、具体性、可操作性
4. 添加缺失约束或删除冗余约束
5. 保持相同核心目的
6. 输出 JSON 数组格式的 skill body 变体

## 实现中的陷阱

### 陷阱 1: JSON 解析失败
**症状**: LLM 输出格式不标准，json.loads 失败
**修复**: 先尝试提取 `[]` 包裹的 JSON，失败则回退到原始 skill

### 陷阱 2: 导入循环
**症状**: `evolve_skill_v2.py` 同时从 `skill_module` 和 `skill_executor` 导入
**修复**: `SkillExecutor` 独立文件，评估时直接实例化

### 陷阱 3: 重复导入
**症状**: `skill_fitness_metric` 被导入两次
**修复**: 清理导入语句，确保每个符号只从正确位置导入一次

## 何时使用 v2 而非 v1

**用 v2**:
- Skill 文本 < 1000 字符
- 约束数量 < 5 个
- 需要 5 分钟内出结果
- DSPy 安装失败或版本不兼容
- 预算有限（单次 < $3）

**用 v1**:
- Skill 文本 > 2000 字符
- 多步推理或复杂边界情况
- 需要统计显著性验证
- 有 50+ 评估 examples
- 需要 Pareto frontier 分析

## 代码位置

```
~/.hermes/hermes-agent-self-evolution/
├── evolution/skills/evolve_skill_v2.py      ← 主入口
├── evolution/skills/skill_executor.py       ← 约束解析+评估
├── evolution/core/fitness.py                ← 评分函数
└── evolution/skills/evolve_skill.py         ← v1 (GEPA/MIPROv2)
```

## 运行示例

```bash
cd ~/.hermes/hermes-agent-self-evolution
source .venv/bin/activate

# 快速测试
python -m evolution.skills.evolve_skill_v2 \
    --skill hermes-execution-guardrails \
    --variations 3 \
    --dry-run

# 正式运行
python -m evolution.skills.evolve_skill_v2 \
    --skill hermes-execution-guardrails \
    --variations 5 \
    --eval-source synthetic \
    --optimizer-model deepseek/deepseek-chat
```
