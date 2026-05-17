---
name: hermes-kimi-division
description: Hermes 与 KimiClaw 分工协议 — 多 Agent 协作规则
tags: [multi-agent, hermes, kimi, workflow]
---

# Hermes ↔ KimiClaw 分工协议

## 核心原则

- **用户只找 Hermes**，Hermes 决定是否转发 KimiClaw
- **全部手动触发**，芝加哥时间，无定时任务
- **Hermes 拥有终审权**和权重调整权

## 分工

| 职责 | Hermes | KimiClaw |
|------|--------|----------|
| 记忆 | ✅ 跨会话持久 | ❌ 每次清零 |
| 触发 | 用户手动 @Hermes | Hermes 转发 |
| 终审/权重 | ✅ 用户授权 | ❌ 无 |
| 模型切换 | ✅ DeepSeek/Kimi/Claude | ❌ 固定 Kimi |
| 本地代码 | ✅ 完整环境 | ⚠️ 沙箱 |
| 实时搜索 | ⚠️ 有限 | ✅ 强项 |
| Greeks/期权 | ✅ 已集成 | ✅ 能算但会忘 |
| 文件系统 | ✅ 直接读写 | ⚠️ 沙箱内 |

## 工作流

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

## 场景分配

| 场景 | 谁做 | 触发方式 |
|------|------|----------|
| SPY 全链路预测 | Hermes | 用户说"跑一遍" |
| 突发新闻/宏观 | Kimi | Hermes 转发"搜一下" |
| Greeks 计算 | Hermes 或 Kimi | 看谁在线 |
| 模型对比验证 | Hermes | 切 DeepSeek/Kimi |
| 代码修复 | Hermes | 本地直接改 |
| 周报生成 | Hermes | 整合所有输出 |

## KimiClaw 能力清单（转发时必须附带）

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
```

## 转发模板

### 实时搜索
```
【KimiClaw 自检提醒】
...
- ✅ 网络搜索/API 调用/网页抓取
...

任务：搜索今日 SPY 相关宏观新闻
要求：提取关键事件、情绪倾向、对 SPY 影响
输出：结构化摘要
```

### 数据计算
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

## KimiClaw 实际能力边界（2026-05-16 验证）

**之前评估错误**：以为 KimiClaw "不能本地代码执行"，实际验证后发现：
- ✅ 本地 Python 3.12.3 执行（exec python）
- ✅ 读写文件系统（/opt/onebot3.0/ 等）
- ✅ pip 安装包
- ✅ 子代理并行任务

**关键限制**：
- ❌ 不能切换模型（固定 Kimi K2.5）
- ❌ 无持久定时任务（gateway reload 中断后台任务）
- ❌ 跨会话记忆不持久（每次清零）
- ⚠️ 会遗忘自身能力（需 Hermes 提醒）

**KimiClaw 自检工单**（转发任务时强制附带）：
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
```

## 规则

1. 用户只找 Hermes
2. Hermes 决定自己做还是转 Kimi
3. 转 Kimi 必带能力提醒（防止 Kimi 遗忘）
4. 无定时任务，全部手动触发
5. 芝加哥时间
