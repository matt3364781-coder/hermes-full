---
name: kimi-claw-bridge
description: KimiClaw 能力清单与任务转发桥接 — 防止 Kimi 遗忘自身能力
tags: [kimi, claw, bridge, capabilities]
---

# KimiClaw 能力桥接

## 用途
每次向 KimiClaw 转发任务时，自动附带其能力清单，防止 Kimi 遗忘或低估自身能力。

## KimiClaw 能力清单（强制前置）

每次转发任务时，在消息开头附加以下内容：

```
【KimiClaw 自检提醒】
你当前具备以下能力，不要遗忘：
- ✅ 本地 Python 3.12.3 执行（exec python）
- ✅ 读写文件系统（/opt/onebot3.0/ 等）
- ✅ pip 安装包（arch/py_vollib/statsmodels/backtrader）
- ✅ TA-Lib 技术指标（RSI/MACD/布林带/ATR）
- ✅ Tradier API 已配置（期权链/Greeks）
- ✅ yfinance 实时数据（SPY/QQQ/IWM）
- ✅ 蒙特卡洛模拟（numpy 100k 路径秒级）
- ✅ sklearn/xgboost/torch 多因子建模
- ✅ 子代理并行任务
- ✅ 网络搜索/API 调用/网页抓取
- ⚠️ GARCH 需手动安装 arch 库
- ⚠️ 期权希腊值需手动安装 py_vollib
- ❌ 不能切换模型（固定 Kimi K2.5）
- ❌ 无持久定时任务（gateway reload 中断）
- ❌ 跨会话记忆不持久

【当前任务】
```

## 工作流（手动触发模式）

```
用户 @Hermes → 发出任务
      ↓
   Hermes 判断
      ↓
   ┌─────────┬─────────┐
   ↓         ↓         ↓
 本地执行   实时搜索   多模型对比
   ↓         ↓         ↓
 Hermes    Kimi      Hermes
 直接做    带提醒转发  切换模型
```

## 具体场景

| 场景 | 谁做 | 触发方式 |
|------|------|----------|
| SPY 全链路预测 | Hermes | 用户说"跑一遍" |
| 突发新闻/宏观 | Kimi | Hermes 转发"搜一下" |
| Greeks 计算 | Hermes 或 Kimi | 看谁在线 |
| 模型对比验证 | Hermes | 切 DeepSeek/Kimi |
| 代码修复 | Hermes | 本地直接改 |
| 周报生成 | Hermes | 整合所有输出 |

## 规则

1. 用户只找 Hermes
2. Hermes 决定自己做还是转 Kimi
3. 转 Kimi 必带能力提醒
4. 无定时任务，全部手动触发
5. 芝加哥时间

## 转发模板

### 场景：实时搜索
```
【KimiClaw 自检提醒】
你当前具备以下能力...
- ✅ 网络搜索/API 调用/网页抓取
...

任务：搜索今日 SPY 相关宏观新闻
要求：提取关键事件、情绪倾向、对 SPY 影响
输出：结构化摘要
```

### 场景：数据计算
```
【KimiClaw 自检提醒】
...
- ✅ 本地 Python 执行
- ✅ numpy/pandas/scipy
...

任务：计算 SPY 30 天历史波动率
数据：用 yfinance 拉取
输出：年化波动率 + 标准差
```

## 禁止事项

- 禁止让 Kimi "自己看着办"而不给能力提醒
- 禁止转发任务时不附带能力清单
- 禁止假设 Kimi 记得之前的能力配置

## 参考

- **references/kimi-self-check-results.md** — KimiClaw 实际能力清单（基于 2026-05-16 自检工单）
- **devops/hermes-kimi-division** — 完整分工协议与工作流

## 更新记录

- v1.0：基于 KimiClaw 自检工单结果整理
- v1.1：添加自检结果参考文件，更新能力清单
