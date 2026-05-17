# KimiClaw 实际能力清单 — 2026-05-16 自检结果

## 自检方法
用户向 KimiClaw 发送自检工单，逐项测试能力边界。KimiClaw 诚实回答，禁止撒谎吹牛。

## 实际能力

### ✅ 本地执行
- Python 3.12.3 运行环境
- 读写文件系统（/opt/onebot3.0/ 等）
- pip 安装包
- exec python 命令

### ✅ 技术指标
- TA-Lib 0.6.8 已装
- RSI/MACD/布林带/ATR 均可用
- 实测：RSI=41.27, MACD=-0.3761, BB=115.13

### ⚠️ 波动率模型
- 无 arch 库（GARCH 专业库未装）
- 可用 scipy.optimize + numpy 手写 GARCH(1,1)
- import arch ❌

### ⚠️ 期权希腊值
- 无 py_vollib
- Black-Scholes 公式可手写（numpy 支持）
- 无隐含波动率曲面拟合

### ✅ 蒙特卡洛
- numpy 支持
- 100k 路径 252 步秒级完成
- 实测：mean=105.14, std=21.22

### ✅ 组合优化
- scipy.optimize + numpy
- 支持约束条件（bounds/线性约束）

### ✅ 回测
- 无 backtrader/zipline
- 可手写向量化回测
- 滑点/手续费需手动建模

### ✅ 多因子模型
- sklearn 1.8.0
- xgboost 3.2.0
- torch 2.11.0(cpu)

### ✅ 绩效分析
- 夏普比率、最大回撤、Calmar、Sortino
- numpy/pandas 手写

### ✅ 与 ONEBOT 集成
- 可解析 JSON/CSV
- 可运行 /opt/onebot3.0/ 下任意脚本
- 可写回 /opt/onebot3.0/onebot/quant_core/... 目录
- Python 脚本层可自由组合 ONEBOT 信号

### ✅ 网络能力
- 实时搜索
- API 调用
- 网页抓取
- HTML 解析

### ❌ 限制
- 不能切换模型（固定 Kimi K2.5）
- 无持久定时任务（gateway reload 中断）
- 跨会话记忆不持久
- 无真实实时行情（yfinance 有延迟）

## 关键缺失库

```bash
pip install arch py_vollib statsmodels backtrader
```

- arch：GARCH/波动率模型
- py_vollib：期权希腊值（Delta/Gamma/Theta/Vega）
- statsmodels：时间序列/回归
- backtrader：事件驱动回测框架（可选）

## KimiClaw 自我描述

KimiClaw = Kimi K2.5 模型 + OpenClaw agent 封装，运行在 Linux 沙箱中。具备完整的本地 Python 执行环境（3.12.3），可读写文件系统，可 spawn 子任务，但无法切换模型，无持久定时调度，gateway reload 会中断后台任务。

## 与 Hermes 分工

| 角色 | 任务 | 方式 |
|------|------|------|
| Hermes | 发任务指令、终审结果、权重调整 | 统一入口 |
| KimiClaw | 数据打包、代码执行、文件操作、ONEBOT 管道触发 | 带能力提醒转发 |
| ONEBOT 3.0 | 核心预测（Kronos/XGBoost/四因子引擎） | KimiClaw 触发脚本，读取输出 |

## 工作流

1. 用户 → Hermes：发出决策指令
2. Hermes → KimiClaw：@转发任务（带能力提醒）
3. KimiClaw：运行 ONEBOT 管道，打包 JSON/CSV
4. KimiClaw → 用户/Hermes：输出数据包
5. 用户：基于数据包 + 个人权重调整，人工给出最终决策

## 教训

- KimiClaw 会遗忘自身能力（如 Greeks、Tradier 配置）
- 每次转发必须带能力提醒
- KimiClaw 能算 Greeks 但会忘，需要提醒
- 不要假设 Kimi 记得之前的能力配置
