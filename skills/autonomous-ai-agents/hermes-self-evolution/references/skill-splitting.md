# Skill Splitting — 大技能拆分策略

> 创建时间: 2026-05-15
> 问题: onebot-3.0 130KB 无法进化
> 根因: 超过 100KB 的技能需要拆分为子技能

## 问题现象

| Skill | Size | Can Evolve? | Reason |
|-------|------|-------------|--------|
| onebot-3.0 | 130KB | ❌ No | Too large, exceeds processing limits |
| onebot-l2-prediction | 8KB | ✅ Yes | Single layer, focused scope |
| onebot-l3-analysis | 12KB | ✅ Yes | Single layer, focused scope |
| onebot-l4-arbitration | 6KB | ✅ Yes | Single layer, focused scope |

## 拆分原则

**按架构层级拆分**（ONEBOT 示例）:
```
onebot-3.0/                    ←  umbrella skill（协调、入口）
├── onebot-l2-prediction/     ←  L2: BS/XGBoost/Kronos
├── onebot-l3-analysis/       ←  L3: Greeks/Gamma/Sentiment/Macro
├── onebot-l4-arbitration/    ←  L4: 争议仲裁
├── onebot-l6-minervini/      ←  L6: SEPA 趋势交易
└── onebot-workflow-pitfalls/ ←  跨层通用陷阱
```

**拆分标准**:
1. **单一职责**: 每个子技能只覆盖一个功能域
2. **独立评估**: 子技能可以独立进化，不受其他层影响
3. **<20KB 目标**: 理想大小 5-15KB，最大不超过 20KB
4. **可组合**: Umbrella skill 引用子技能，不重复内容

## 拆分流程

```python
def split_skill(skill_path: str) -> List[str]:
    """Split a large skill into smaller sub-skills."""
    
    # 1. Analyze structure
    sections = parse_skill_sections(skill_path)
    
    # 2. Group by domain
    domains = group_sections_by_domain(sections)
    
    # 3. Create sub-skills
    for domain, domain_sections in domains.items():
        if size(domain_sections) > 20KB:
            # Further split
            sub_domains = split_by_sub_domain(domain_sections)
        else:
            create_sub_skill(domain, domain_sections)
    
    # 4. Create umbrella skill
    create_umbrella_skill(skill_path, domains)
    
    # 5. Validate
    validate_split(skill_path)
```

## Umbrella Skill 结构

```markdown
---
name: onebot-3.0
description: "ONEBOT 3.0 量化投研系统 — 协调层"
---

# ONEBOT 3.0

**六层架构投研系统。**

## 架构概览

```
Layer 2: 预测模型 → 见 [onebot-l2-prediction]
Layer 3: 分析引擎 → 见 [onebot-l3-analysis]
Layer 4: 争议仲裁 → 见 [onebot-l4-arbitration]
Layer 6: SEPA 趋势 → 见 [onebot-l6-minervini]
```

## 通用工作流

1. 加载相关子技能
2. 按层顺序执行
3. 汇总结果

## 通用陷阱

→ 详见 [onebot-workflow-pitfalls]
```

## 验证清单

- [ ] 每个子技能 < 20KB
- [ ] 子技能之间无重复内容
- [ ] Umbrella skill 只包含协调逻辑
- [ ] 所有子技能可以独立进化
- [ ] 原始 skill 的测试用例分配到对应子技能

## 当前状态

| Skill | Status | Size |
|-------|--------|------|
| onebot-3.0 | ❌ 待拆分 | 130KB |
| onebot-l2-prediction | ✅ 已独立 | 8KB |
| onebot-l3-analysis | ✅ 已独立 | 12KB |
| onebot-l4-arbitration | ✅ 已独立 | 6KB |
| onebot-l6-minervini | ✅ 已独立 | 10KB |
| onebot-workflow-pitfalls | ✅ 已独立 | 15KB |

## 相关文件

- `evolution/skills/skill_splitter.py` — 自动拆分工具（计划中）
