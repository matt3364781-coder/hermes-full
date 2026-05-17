# GEPA (Genetic-Pareto Prompt Evolution) 最佳实践

来源: DeepSeek 研究 + DSPy 论文 + GEPA 论文

## 迭代次数

| Skill 复杂度 | 最少迭代 | 最大安全迭代 | 过拟合信号 |
|-------------|---------|------------|-----------|
| 简单分类 (3-5 标签) | 5 | 10 | Holdout 分数下降 >2% |
| 提取/格式化 | 8 | 15 | 输出格式退化 |
| 多步推理 | 10 | 20 | 丢失边界情况 |
| Agent 编排 | 12 | 25 | 幻觉增加 |

**检测**: 监控 Pareto frontier 大小 — 如果在迭代 8 后 < 3 个不同 prompt 变体，就是过拟合。验证损失连续 3 次迭代不下降时停止。

## 评估数据来源

**优先级**:
1. **sessiondb** (真实用户交互) → 总是优先。GEPA 在优化实际失败案例时表现最好。比纯 synthetic 基线提升 12-18%。
2. **synthetic** → 用于: 新 skill 零会话历史 / 覆盖生产中未见的边界情况 / 对抗性输入鲁棒性测试。生成 3 倍于需求的 synthetic examples，然后去重。
3. **golden** → 仅用于: 最终验证 / 回归测试 / 合规场景。**永远不要仅用 golden 数据优化** — 会记忆平凡解。

**推荐混合**: 80% synthetic + 20% sessiondb (warm-start) 优化，100% golden + sessiondb holdout 验证。

## 优化器 vs 评估模型

**通用规则**: 优化器应该**相同能力或略弱于**评估模型。

| 优化器模型 | 评估模型 | 效果 |
|-----------|---------|------|
| gpt-4.1 | gpt-4.1-mini | ✅ 平衡 — 优化器探索，评估捕获噪声 |
| gpt-4.1 | gpt-4.1 | ❌ 过度自信 — 优化器通过匹配评估偏差"作弊" |
| gpt-4.1-mini | gpt-4.1 | ✅ 鲁棒 — 优化器被迫泛化 |
| gpt-3.5-turbo | gpt-4.1 | ⚠️ 信号弱 — 优化器无法有效探索 |

**原理**: GEPA 的反射步骤使用优化器模型批评失败。如果两个模型相同，会产生*递归自我确认偏差*。

**Hermes Self-Evolution 推荐**:
- `optimizer_model="openai/gpt-4.1-mini"`, `eval_model="openai/gpt-4.1"`
- 或 `optimizer_model="openai/gpt-4.1"` 但加 `eval_rubric=strict_kwargs`

## 好评估数据集的特征

1. **覆盖多样性** (不是大小)
   - 每个 skill 子任务 5-10 个 examples
   - 每个预期失败模式 2-3 个 examples
   - 每个已知边界情况 1 个 example

2. **难度分层**
   - 30% 简单 (置信度 > 0.9)
   - 50% 中等 (置信度 0.5-0.9)
   - 20% 困难 (已知失败 / 低置信度)

3. **标签质量**
   - synthetic: 生成和评估**不要**用同一模型 (Self-Instruct 论文显示会创建坍塌的评估空间)
   - sessiondb: 包含时间戳和用户满意度分数

4. **最小大小**: 20 个 examples (复杂 skill 100+)。GEPA 的遗传操作需要足够的示例多样性。

## GEPA 陷阱与修复

| 陷阱 | 症状 | 修复 |
|-----|------|------|
| 语义漂移 | 输出偏离原始领域 | 加 cosine similarity ≥ 0.7 约束 |
| Prompt 膨胀 | Skill 文件大小增长 3 倍+ | 设 max_prompt_length (默认 4096) |
| 变异坍塌 | 所有进化 prompt 收敛到相同策略 | 监控 population_diversity；< 3 个唯一解集群时重启 |
| 评估过拟合 | eval 95%+，holdout 60% | GEPA 内用 k-fold 交叉验证 |
| 延迟回归 | 2-token 输出变成 500-token 文章 | skill.yaml 约束中加 output_length_budget |
| 多模态泄漏 | Skill 开始幻觉工具调用 | DSPy 模块中启用 strict_output_schema |
| 反馈循环 | GEPA 优化自己的评估标准 | 监控 eval_model vs optimizer_model 一致性；分数差异 >15% 时暂停 |

## 验证: 更好 vs 只是不同

**三层验证层级**:

### Tier 1: 统计显著性
5-fold holdout 评估。Skill "更好" 仅当:
- 均值提升 ≥ 2% (GEPA 特定阈值)
- 标准差不增加 > 10%
- 最差 fold 不下降

### Tier 2: 行为测试
- 原始 skill 通过的所有测试，进化版也必须通过
- 新增测试覆盖之前失败的场景
- 无回归

### Tier 3: 人工审查
- 输出风格一致性
- 无意外行为变化
- 符合用户偏好

## 相关论文

- [DSPy (Khattab et al., 2023)](https://arxiv.org/abs/2310.03714)
- [GEPA (Sahoo et al., 2024)](https://arxiv.org/abs/2402.06912)
- [STaR (Zelikman et al., 2022)](https://arxiv.org/abs/2203.14465)
- [Self-Instruct (Wang et al., 2022)](https://arxiv.org/abs/2212.10560)
