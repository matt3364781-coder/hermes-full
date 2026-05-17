# 删除操作审查教训 — 2026-05-16

## 场景

用户列出删除清单：portfolio_opt, prediction_market, option_implied, cointegration, divergence, sentiment_social, risk, candlestick, regime_hmm, kalman, gamma_wall, vol_forecast

## 错误

直接准备执行删除，未审查模块实际功能。

## 用户纠正

- "gamma wall应该也有用啊你再仔细想一下"
- "optionimplied这个是干麻的应该可以保留吧你仔细查一下"

## 正确流程

1. 对每个候选删除项：
   - 读取模块源码，理解实际功能
   - 运行实际测试，确认输出状态
   - 判断是否真的无用/低效
2. 分类输出：
   - 确认删除（有实际证据）
   - 建议保留（功能有效）
   - 待用户决定（边界情况）
3. 等用户确认后再执行删除

## 核实结果

| 模块 | 用户标签 | 实际状态 | 结论 |
|------|---------|---------|------|
| gamma_wall | 低效（与gamma重复） | GEX极值点，与gamma互补 | 保留 |
| option_implied | 无用（Greeks未接入） | 期权微观结构核心引擎 | 保留 |
| cointegration | 无用（无协整信号） | 恒无信号 | 删除 |
| sentiment_social | 无用（API不稳定） | 911行代码，无API keys | 删除 |

## 教训

- 用户的"无用"标签可能基于旧数据
- 代码可能已经修复，需要实际验证
- 破坏性操作必须二次确认
- 我的角色是核实者，不是单纯执行者
