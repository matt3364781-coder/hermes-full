---
name: onebot-tech-wiki
description: ONEBOT 3.0 技术决策与参数来源记录
scope: ONEBOT 3.0 量化系统的技术决策、参数来源、踩坑记录
conventions:
  - 每个决策独立一页，包含：问题、方案、验证结果、最终决定
  - 参数必须标注来源（回测年份、数据量、统计方法）
  - 踩坑记录包含：症状、根因、修复、预防措施
open_questions: []
---

# ONEBOT Tech Wiki

记录 ONEBOT 3.0 的技术决策、参数来源和踩坑教训。

## 目录

- [[unified-range-cache-optimization]] — 模型加载缓存优化（去掉 TTL）
- [[unified-range-fallback-params]] — 统计回退参数来源
- [[path-hallucination-lessons]] — 路径幻觉教训

## 规则

1. 所有参数必须可追溯（回测年份、样本量）
2. 技术决策必须记录 rejected alternatives
3. 踩坑记录必须包含预防措施
