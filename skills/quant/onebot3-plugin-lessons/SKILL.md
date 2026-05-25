---
name: onebot3-plugin-lessons
category: quant
description: ONE Bot 3.0 插件系统踩坑记录与工程决策
tags: [plugin, cron, onebot3, anchoring, distiller]
---

# ONE Bot 3.0 插件系统 — 经验教训

## 触发条件

- 新建/修改 `~/.hermes/plugins/onebot3/` 下任意文件后需要验证全链路
- 脉冲挂死、DB 数据不对、插件加载失败时先查此 skill

## 架构总览

```
~/.hermes/plugins/onebot3/
├── plugin.yaml           ← 配置 + API Token (根目录，框架发现必需)
├── __init__.py           ← 统一入口，导入即自启调度器
├── lib/                  ← L5: 工具层（调度+forgetless）
│   ├── scheduler.py      ← 脉冲(5min) + 备份(60min) daemon 线程
│   └── forgetless.py     ← 拉 archive.db 原文脚本
├── anchoring/            ← L1: 采集（全量数据：OHLCV+GEX+指标+情绪+宏观）
├── kronos/               ← L2: 模型预测（只读自身需要的数据）
├── distiller/            ← L3: 归档蒸馏（**不是 LLM 报告层**）
└── data/                 ← L4: 存储（market.db + 备份）
```

## 数据流（关键 — 常被记错，2026-05-24 用户再次纠正）

```
L1 (anchoring) → 全量数据采集
  ├─ price/OHLCV ─→ L2 (kronos) 读取 → 出预测 → Hermes
  ├─ gex ─────────→ L2 (kronos) 做二次确认
  ├─ indicators ──┐
  ├─ sentiment ───┤
  ├─ macro ───────┤ ──→ Hermes（我）→ 出研判报告
  ├─ earnings ────┤
  └─ analyst ─────┘
```

**铁律：L2 只读它需要的数据（price + GEX），不消费全量 L1。** L1 的其他数据（indicators, sentiment, macro, earnings, analyst）直接给 Hermes，不经过 L2。
**铁律：L3 (distiller) 是归档层，跟报告链路无关。** LLM 报告是 Hermes Agent 自己写的，不在 onebot3 插件分层内。

## 调度方式

**scheduler.py daemon 线程，启动即跑。** __init__.py 最后一行自动拉起，不依赖 cron。

| 线程 | 间隔 | 职责 | 模式 |
|------|------|------|------|
| 脉冲 (线程A) | 每 5min | L1 数据采集+GEX+指标 → 写 data/market.db | 纯 Python，不耗 token |
| 备份 (线程B) | 每 60min | archive.db 增量导出 → data/memory_backups/ | 纯 Python，不耗 token |

**停止方式：** `from lib.scheduler import stop_all`

**原则：**
- 数据采集（脉冲/备份）→ daemon 线程，不耗 token，不依赖 cron
- 报告/摘要 → 手动触发，不设自动推送（用户不看推送）
- 调度器在 `__init__.py` 底部通过 daemon thread 自启（`threading.Thread(target=lambda: __import__('onebot3.lib.scheduler', fromlist=['start_all']).start_all(), daemon=True).start()`）— 用完整 dot path 代替 sys.path hack，避免工作目錄不在插件目錄時導入失敗

## 关键发现

### Archive DB 数据流真相

**两个写入路径，差距很大：**

| 路径 | 触发时机 | 参数 | 存了啥 |
|------|----------|------|--------|
| `sync_turn()` | 每轮结束后 | `user_content: str, assistant_content: str` | 只存字符串 ❌ |
| `on_session_end()` | session 结束时 | `messages: List[Dict]`（完整消息体） | 全部消息 ✅ |

**核心发现：** `sync_turn()` 从框架只收到两个字符串——`user_content` 和 `assistant_content`。Assistant 消息中如果有 `tool_calls` 结构体（函数名、参数），框架根本不传给 provider。这就不是 Archive 插件写得不好，是框架的 MemoryProvider 接口设计限制了。

**修法（方向性）：** `on_session_end()` 收到完整消息列表，`archive_session()` 过去只取了 `msg["content"]` 丢弃了 `msg["tool_calls"]`。改成在 content 末尾序列化 tool_calls（2026-05-24 已修）。但注意这是事后补——日常回合还是存不进去，因为 sync_turn() 拿不到。

**用户的设计原则（2026-05-24）：**
> 「文字信息才是真正的子弹。别的信息全都可以从上下文获取。」

这意味着：对于上下文压缩后的会话恢复，用户说了什么、我回了什么是不可丢失的原始信息。工具调用参数和输出结果都可以从上下文中重新推断。Archive.db 存了完整的 user/assistant/tool 文字流（79MB, 33K+ 条），这对于上下文丢失后的恢复目标来说已经够用。tool_calls 结构体（函数名/参数）没有存，但这是框架接口限制，不是 Archive 插件的问题。

**Archive DB 快照（2026-05-24）：** 路径 `~/.hermes/memory/archive.db`，79MB，33,536 条消息，525 个 session。user 6,036 / assistant 10,783 / tool 16,717 条。

## KronosCluster v1.0（2026-05-24 定）

### 基座模型状态
HF cache 完好：Kronos-base(391MB) + Kronos-Tokenizer-base(16MB)
路径：`~/.cache/huggingface/hub/models--NeoQuasar--Kronos-{base,Tokenizer-base}/snapshots/`

### 实现模式

关键模式：**1 份模型权重 → N 个独立处理器**。Kronos-base(102M params) 只从 HF cache 加载一次，作为 KronosEngine 的类变量。每个引擎实例共享同一份 weights，但各自独立处理器（不同 lookback、EMA、阈值）。

model/kronos.py + model/module.py 从 [shiyu-coder/Kronos](https://github.com/shiyu-coder/Kronos) 拷贝过来，自包含在插件内，不依赖外部 git clone 或 pip install。

### 目录结构

```
plugins/onebot3/kronos/
├── __init__.py    ← stub，暴露 KronosCluster + predict_from_anchoring
├── engine.py      ← KronosEngine(config)：单例模型 + 独立处理器
├── cluster.py     ← KronosCluster：5 引擎 + 动态权重 + 分歧检测
├── model/
│   ├── __init__.py
│   ├── kronos.py  ← 官方 Kronos/RMSNorm/TemporalEmbedding/HierarchicalEmbedding
│   └── module.py  ← 官方 TransformerBlock/DualHead/BSQuantizer
```

### 引擎调用链（v1.3, 2026-05-24） — 只有 zone classifier 主路径

```
KronosCluster.predict(klines)
  └→ 依次调每个 KronosEngine.predict(klines)
       │
       │  主路径（zone classifier — 唯一路径）
       ├→ 截取 lookback 窗口 → Z-score 归一化 → build_time_stamp
       ├→ tokenizer.encode() → (s1_ids, s2_ids)
       ├→ model.decode_s1() → (s1_logits, context) ← context.shape=(1,T,832)
       ├→ zone_classifier.predict_proba(context[-1,:]) → 5 类区间概率
       ├→ zone → direction 映射（见下方标签表）
       └→ EMA 平滑（基于 continuous zone_score）→ 过滤微弱信号
  └→ _get_weights(market_regime) → 动态权重
  └→ _fuse() → 分歧检测 + 加权投票 + 仓位建议
```

**注意：decoder direction 信号已于 v1.3 移除。** 之前加的 Kronos 自回归 next-bar 预测路径，經 300 次验证準確率僅 42.3%（比隨機 50% 還差），已從 engine.py 和 cluster.py 完全拔掉。不再有任何雙路徑。

**Decoder 反轉模式：** 42.3% < 50% 意味著預測方向與實際方向**反相關**。如果將信號反轉（put→call, call→put），準確率會是 57.7%。不過 57.7% 在二元方向預測中仍然太弱，不值得保留。**debug 模式：二元預測低於 50% 時，先檢查是否反相關，反轉後再決定是否丟棄。**

### 区间标签体系（5 分类）

| 标签 | 名称 | 方向 | 策略 |
|------|------|------|------|
| 0 | 支撑区 | CALL | 买Call进场 |
| 1 | 中性区 | NEUTRAL | 观望 |
| 2 | 阻力区 | PUT | 减仓/对冲 |
| 3 | A+1突破 | CALL | 追涨 |
| 4 | A-1突破 | PUT | 避险 |

最终置信度 = 分类概率 × 置信度基数。  
用户是万年多头，支撑区 + A+1突破 是最重要的买点信号。

### 训练结果（2026-05-24 重大更新 — 55d 严重过拟合，1y 才是真·泛化冠军）

**⚠️ 2026-05-24 跨时间 OOS 验证发现 55d 模型严重过拟合。** 原本以为 55d 优于 1y，实测：

| 模型 | shuffle test | 真实 OOS（未来数据） | 差距 |
|------|-------------|---------------------|------|
| 55d 模型（旧主力） | 70.5% | **37.3%** ❌ | -33.2pp |
| 1y 模型 C=1.0（初版） | 97.9% | 70.0% | -27.9pp |
| **1y 模型 C=0.01（最优）** 🆕 | **77.6%** | **67.4%** | **10.2pp ✅** |
| **1y 模型 C=0.1** | **86.3%** | **68.9%** | **17.4pp** |

**55d 模型 37.3% OOS 只比随机高 17pp** — 分类器死记了 55 天价格噪音，换个时间段直接失效。
**1y 模型 70.0% 真实 OOS** — 用全年数据训练，时间序 80/20 分割（训练 2025-05～2026-03，测试 2026-03～2026-05），泛化能力大幅提升。
**C=0.01 最佳正则化：** train=77.6%, test=67.4%, gap=10.2pp — 虽然绝对精度比 C=1.0 低 2.6pp，但过拟合差距缩小了 17.7pp，模型更可靠。

结论翻转：**之前「1y 不如 55d」的结论是 shuffle 验证的假象。** 实际 1y 模型才是真正可用的版本。**C 超参数调优发现默认 C=1.0 严重过拟合，需要强正则化（C=0.01 或 0.1）才能获得可靠泛化。**

#### 当前主力模型

| 文件 | 数据源 | 样本数 | 验证方式 | 准确率 | 状态 |
|------|--------|--------|----------|--------|------|
| `zone_classifier.pkl` | 55d 5min yfinance | 2,982 | shuffle | 70.5% | **❌ 过拟合，应替换** |
| **`zone_classifier_1y.pkl`** 🆕 | **1y 5min CSV** (47,576 bars) | **948** (stride=50) | **时间序 80/20** | **67.4% (C=0.01)** | **✅ 当前主力（正则化最优）** |

**1y 模型训练参数：**
- 数据：`spy_5min_1year.csv`（47,576 bars, 2025-05-27 ~ 2026-05-23）
- Stride=50 → 948 samples
- 训练/测试：chronological 80/20（train: 2025-05 ~ 2026-03, test: 2026-03 ~ 2026-05）
- 标签：百分位法（p1/p5/p95/p99）, window=100
- Classifier：LogisticRegression, max_iter=2000, solver='lbfgs'
- 特征缓存：`kronos/models/features_1y_stride50.npz`
- **C超参数调优**（2026-05-24新增 — 默认C=1.0严重过拟合）：

| C值 | Train | Test (OOS) | 差距 | 说明 |
|-----|-------|-----------|------|------|
| 0.01 | 77.6% | **67.4%** | 10.2pp ✅ | 强正则化，泛化最佳 |
| 0.1 | 86.3% | **68.9%** | 17.4pp | 中等正则化，精度略高 |
| 1.0 | 97.9% | 70.0% | 27.9pp ❌ | **过拟合（缺省值陷阱）** |
| 10.0 | 100.0% | 70.2% | 29.8pp ❌ | 严重过拟合 |

**当前推荐：C=0.01 或 C=0.1，不要用默认 C=1.0。**

**1y 模型各标签测试集结果（C=0.01，训练 77.6%，测试 67.4%）：**

| 标签 | 名称 | 精确率 | 召回率 | F1 |
|------|------|--------|--------|-----|
| 0 | 支撑区 | 0.75 | 0.21 | 0.33 |
| 1 | 中性区 | 0.76 | **0.93** | **0.84** |
| 2 | 阻力区 | 0.38 | 0.19 | 0.26 |
| 3 | A+1突破 | 0.53 | 0.59 | 0.56 |
| 4 | A-1突破 | 0.50 | 0.29 | 0.36 |

中性区 recall=93% 最稳，支撑/阻力区偏弱（~20%），突破类中等（29-59%）。
稀有类别 recall 低是 LogisticRegression 的已知局限，换 MLP 可能改善。

**C=0.1 模型（训练 86.3%，测试 68.9%）分类报告可看：** 总体上 recall 分布类似，C=0.1 在少数 classes 上略有提升但过拟合 gap 更大（17.4pp vs 10.2pp）。推荐生产部署用 C=0.01 模型。两份模型均在 kronos/models/ 下。**加载时注意：clf_data['model']，不是裸 pickle。**

#### 跨时间 OOS 验证发现（2026-05-24 新增）

**原「1y 不如 55d」结论错误。** 之前 1y 数据用 shuffle split 测出 60.4%，55d 用 shuffle 测出 70.5%，以为 55d 更好。事实上 1y 数据的 60.4% 是**数据过密**（stride=5 on 47K bars）带来的 label 漂移问题，不是模型更差。

真实对比（跨时间 OOS）：

| 训练数据 | 训练准确率 | 时间序 OOS 测试 | 说明 |
|---------|-----------|----------------|------|
| 55d yfinance (2982 samples) | 86.1% | **37.3%** | 死记 55 天噪音 |
| **1y CSV (948 samples, stride=50)** | **97.9%** | **70.0%** | **全年模式更泛化** |

关键发现：**用全年数据训练的模型，即使在低采样率（stride=50, 仅 948 samples）下，OOS 泛化也远超高密度短周期训练（stride=1, 2982 samples）。** 数据多样性比数据密度重要。

这个结果也部分驳斥了「线性模型跨区段局限」——1y 跨越 $585→$749，线性模型仍然学到了跨区段有效映射。70.0% 比 37.3% 好得多，说明之前失败的原因不是「线性模型学不了」，而是「55 天样本太少导致过拟合」。

#### 为什么 1 年 5min 数据反而比 55 天差？— 2026-05-24 结论翻转

**⚠️ 2026-05-24 跨时间 OOS 验证后，原结论被推翻。**

原本对比：
- 1y 数据 shuffle test: 60.4%（stride=5, ~9500 samples）
- 55d 数据 shuffle test: 70.5%（stride=1, ~2982 samples）

结论：「1y 反而不如 55d，线性模型跨区段局限。」

**但跨时间 OOS 验证发现真相完全不同：**
- 55d 模型（shuffle 70.5%）→ 真实 OOS **37.3%** ❌ 严重过拟合
- 1y 模型（shuffle 60.4%）→ 真实 OOS **70.0%** ✅ 真正泛化

**真实原因：** 1y 数据 shuffle 60.4% 低的原因是 **数据过密（stride=5 on 47K bars）** 导致 label 漂移统计上更严重，不是分类器学习能力差。用更稀疏的采样（stride=50, 948 samples）加上时间序验证，1y 模型反而远优于 55d。

**最终结论：数据多样性比数据密度重要。** 55d 只有 ~$640→$745 的单一上涨区间，分类器学到的是区间内噪声。1y 数据跨越 $585→$749 的多阶段市场，模型学到了更普适的区间位置映射。

**2026-05-24 之前的分析仍保留作为参考历史：**

~~排除假设：用户猜测「1年有极端黑天事件干扰」，实际验证排除 >2% 的 6 个极端交易日后 Test Acc 只从 60.4% 升到 62.3%（+1.9%）。极端事件不是主因。~~

~~真正原因：标签定义跨市场阶段不一致。~~

~~解法：1. 只训近期数据（55 天 70.5% 方案）——简单有效 2. 换非线性分类器（MLP/RandomForest）——更多参数 + 非线性激活，能学跨区段映射~~

**保留价值：** 上述「线性模型跨区段局限」理论本身有道理，只是 1y 模型的实际表现（70.0% OOS）说明丰富数据可以抵消这个局限。如果将来用更长周期（3年+）训练，这个理论可能再次成立。

详见 `references/linear-model-training-insights.md`。

#### ⚠️ 时间序列验证（数据泄漏陷阱）— 2026-05-24 重大更新

用随机 shuffle 做 train/test split 会把相邻 K 线泄漏到测试集。旧版 60d 模型实测水分 +12.1%：

| 验证方式 | 旧 60d 准确率 |
|----------|--------------|
| 随机 shuffle | 69.6% |
| 时间序列 split（正确） | **57.5%** |

**任何 ML 训练报告准确率时，必须先说明验证方式。**

更残酷的事实：**即使做了时间序列 80/20 split，如果只在 55d 数据上训练，模型仍然过拟合。** 2026-05-24 实测：

| 模型 | 训练数据 | 时间序 80/20 | 跨时期 OOS（未来数据） |
|------|---------|-------------|---------------------|
| 55d 模型 | 2026-03-30~05-22 | 未测（太短） | **37.3%** |
| 1y 模型 | 2025-05~2026-05 | **70.0%** | 作为验证方式本身 |

**铁律：训练数据必须覆盖至少两个不同的市场阶段。** 只在一个单边区间内训练，时间序 split 也不够——模型学到的是区间内噪音，不是泛化模式。

| 标签 | 名称 | 精确率 | 召回率 | F1 |
|------|------|--------|--------|-----|
| 0 | 支撑区 | 0.53 | 0.43 | 0.48 |
| 1 | 中性区 | 0.46 | 0.57 | 0.51 |
| 2 | 阻力区 | 0.61 | 0.52 | 0.56 |
| 3 | A+1突破 | 0.66 | 0.72 | 0.69 |
| 4 | A-1突破 | 0.65 | 0.55 | 0.59 |

#### 训练教训

1. **不要拿 924 samples 说训好了**（第一次 stride=5 被用户指出来，用户原话「我塞了好几千的样本给你」）
2. **不要报告随机 shuffle 的准确率**（水分 12%，必须跑时间序列 split 核实）
3. **数据源**：yfinance SPY 5min K线，period=60d，约 4680 bars。特徵提取~15分钟（CPU），训练<3秒

### 关键接口

`predict_from_anchoring(snap: dict) → dict` — 兼容 __init__.py 的 get_kronos_prediction()，/report 命令不改一行。

`KronosCluster.predict(klines, market_regime) → {direction, direction_label, confidence, agreement, size, details, weights}`

**v1.3 更新：去掉 decoder direction 路径。** 之前 engine 返回的 `decoder_direction`、`decoder_confidence`、`decoder_detail` 已验证無效（42.3%），已全部刪除。

### 5 个 Kronos 实例

| 实例 | lookback | threshold | ema | vol_weight | 职责 |
|------|----------|-----------|-----|------------|------|
| scalper | 10 | 0.005 | 5 | 0.0 | 超短周期，捕捉反转 |
| swing | 40 | 0.015 | 20 | 0.3 | 波段趋势 |
| trend | 120 | 0.03 | 50 | 0.5 | 日线级趋势 |
| vol | 60 | adaptive | — | True | 高波动自适应 |
| pattern | 20 | pattern_only | — | ignore_vol | 纯K线形态 |

实例之间完全独立，不共享内部状态。输入层不同，决策逻辑不同。

### 动态权重

基础：scalper=0.15, swing=0.25, trend=0.25, vol=0.15, pattern=0.20
状态调整：trending→trend+0.15/scalper-0.10, ranging→scalper+0.15/trend-0.10, high_vol→vol+0.20
准确率惩罚：近期<0.4 降权 0.5x

### 分歧检测

- 完全一致(分歧度=1) → confidence=0.9, size=1.0
- 轻度分歧(分歧度=2 且 |sum|>0.3) → confidence=0.6, size=0.5
- 严重分歧(分歧度=3) → confidence=0.0, size=0.0, alert='high_divergence'

### predict_from_anchoring() — GEX 二次确认（v1.3）

`predict_from_anchoring()` 在 cluster.predict() 结果上附加：

1. **GEX 方向判断**: `gex_net > 0 → gex_confirm=1` (正GEX=支撑=看多), `< 0 → -1` (负GEX=阻力=看空)
2. **对齐提升**: 如果 Kronos 方向与 GEX 方向一致且非中性 → `confidence += 0.15` (cap 0.95)

输出字段：`gex_net`, `gex_regime`, `gex_confirm`, `gex_aligned` (bool)。

**v1.3 移除：** `decoder_summary` 和 `decoder_calls/puts/neutral` 隨 decoder 路徑一同刪除。

⚠️ **GEX 用于修正置信度，不反转方向。** 即使 GEX 强烈看空，Kronos 的 direction 保持不变——GEX 只影响 confidence 高低。

### 接口兼容

get_kronos_prediction() 走到 predict_from_anchoring(snap)，/report 命令不改。返回格式扩展了 decoder_summary 和 gex_aligned 字段。

#### 标签策略大改 — Swing Point 区域标签（2026-05-24 Kimi 方案）

**触发条件：** 跨时间 OOS 验证发现百分位标签本质是「均值回归信号」，不是结构性支撑/阻力。5min 模型支撑 recall 仅 7%，被 Kimi 判定为「数学上不可能救活」。

**Kimi 的核心判决（2026-05-24）：**
> 「Swing Point 单点标签 + 高维 LR = 自杀。必须改成「区域标签」，否则 recall 永远爬不起来。」

**原因：**
- Swing Point（左右各 5 根严格极值）只占全部 K 线的 ~2%
- LR 是线性模型，决策面被 98% 的中性类（label 1）完全主导
- 758 样本 × 832 维多类分类 = 每类平均 150 样本去拟合 832 维超平面 → 维度灾难

**解法 — 区域版 Swing Point 标签：**
- 波峰/波谷检测后，向两侧扩展 zone_radius=3 根 K 线 → 把「点」变成「区域」
- label 0/2 样本量从 2% 拉到 15-20%，LR 才能看见
- 突破/跌破只在非 swing zone 触发，避免标签冲突
- 用 ffill 追踪最近 swing price，而非 rolling 百分位

函数 `detect_range()` 已加入 `engine.py`（2026-05-24）。
签名：`detect_range(df_close, df_high, df_low, left=5, right=5, zone_radius=3) → labels (ndarray)`

**参数调优建议：**
- 日线默认 left=right=5（~2周极值窗口），zone_radius=3（~1周区域）
- 5min 可放宽到 left=right=3（15分钟极值窗口）但会引入更多噪声
- 如果 0/2 仍 < 10%，zone_radius 拉到 5

**评价指标 — 狗基线（2026-05-24 新增）：**
- 永远预测「中性区（class 1）」的模型称为「狗策略」
- 报告 classifier 准确率时**必须同时报告狗基线**
- 如果模型只比狗高 <10pp → 模型不可用
- 日线 Swing Point 各 fold 比狗高 20-30pp ✅

### 5min 模型死刑判决（2026-05-24 Kimi 确认）

**结论：当前 5min 模型必须砍掉。**

数学上不可救：
- 758 样本 × 5-class × 832-dim = 每个 class 平均 150 个样本去拟合 832 维超平面
- 支撑 recall 7% = 模型根本没学到支撑特征

**如果一定要抢救 5min，必须同时做：**
1. 样本量 ×10：stride 从 50 降到 5（758 → ~7,500 样本）
2. 窗口扩大：left=right=20（100 分钟结构）过滤日内杂讯

**推荐策略：先砍 5min，日线调通后再考虑复活。**

### LR 训练 checklist（2026-05-24 Kimi 更新）

1. **C 值搜索（必须跑，不要用默认 C=1.0）**
   - `C=0.1`：中正则化，精度较高，过拟合 gap ~17pp
   - `C=0.01`：强正则化，gap 最小（~10pp），推荐
   - `C=0.005`, `C=0.001`：极强正则化，如果 C=0.01 还过拟合 >10pp 时试
   - 默认 C=1.0 是陷阱，832 维 × 758 样本下严重过拟合

2. **class_weight='balanced'（必加）**
   - Swing Point 区域版后 class 0/2 仍可能比 class 1 少
   - 自动加权，防止决策面被中性类主导
   - 不加 balanced 时稀有类 recall 可能 < 10%

3. **PCA 降维（备用方案）**
   - 当 C=0.001 后过拟合 gap 仍 > 10pp 时使用
   - PCA(n_components=0.90) → 832 维降到 ~50-120 维（保留 90% 方差）
   - PCA 是训练 pipeline 的一环，不改 Kronos 提取逻辑
   - `from sklearn.decomposition import PCA`

4. **3-Fold Forward Chaining 验证**
   - 时间序列前 50%/70%/85% 训练，后 20%/15%/15% 测试
   - 3 fold × 4 C 值 × 2 balanced 模式 = 24 次训练
   - 选平均 test acc 最高的配置

### 训练教训（2026-05-24 用户纠正）

**不要用 Kronos hidden state 做方向预测（二分类涨跌）。** 用户说「目的是震荡区间不是预测股价」。

**正确目标：区间定位。** Kronos 的 832-dim hidden state 回答「现在在震荡区间的哪里」：
- A-1(向下突破)/0(支撑区→CALL)/1(中性)/2(阻力区→PUT)/A+1(向上突破→CALL)

#### 跨时间 OOS 验证铁律（2026-05-24 新增 — 被 55d 模型 37.3% OOS 教训）

**任何时候训练 zone classifier，必须跑跨时间 OOS 验证：**

1. 在训练数据之外选择一个独立的未来时段（至少 1 个月）
2. 确保该时段的价格区间与训练数据不同（否则验证不够）
3. 用 stride=50 提取 Kronos hidden state
4. 报告真实准确率
5. 如果 OOS 准确率低于训练准确率 15pp+ → 模型过拟合

**55d 模型的教训：** shuffle 70.5% vs 真实 OOS 37.3%（差距 33pp）= 死记噪音。1y 模型 97.9% train vs 70.0% OOS（差距 28pp）虽然也有过拟合，但绝对精度够用。

**验证数据源切换**（2026-05-24 验证）：
- 55d 模型 OOS 验证耗时：~3 分钟（~1600 samples, stride=20, CPU）
- 使用 1y CSV 的 OOS 期（2025-05~2026-03，~40K bars）

### Kimi + Hermes 协作模式（2026-05-24）

当任务可分割成独立子任务时，让 Kimi Agent 和 Hermes 并行工作：

| 谁做 | 做什么 | 例子 |
|------|--------|------|
| Kimi | 纯函数逻辑改写 | detect_range() Swing Point 算法 |
| Kimi | 不涉及文件系统/工具调用的纯代码 | 列名映射、函数体 |
| Hermes | 文件修改、集成、运行测试 | 把 Kimi 的函数体写进真实文件 |
| Hermes | 耗时计算/训练 | 重训分类器、Kronos 推理 |

**原则：** Kimi 输出函数体 → Hermes 集成进真实文件 → 测试 → 重训。不要 Kimi 去改真实文件或跑训练，它没有执行环境。

详见 `references/kronos-cluster-training.md`。

### 时间序列数据泄漏陷阱（高优先级）

**永远不要用随机 shuffle 分割金融时间序列数据。** 相邻 K 线共享相同市场状态，随机分配会把相似样本泄漏到测试集，高估准确率 10-15%。

正确的做法：
```python
# ❌ 错误（有水分）
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)

# ✅ 正确（时间序列分割）
split = int(len(X) * 0.8)
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]
```

实测水分：随机 shuffle 69.6% → 时间序列 57.5%（-12.1%）。**任何 ML 训练报告准确率前，必须先说明验证方式。**

### 训练模式 — 支持本地 CSV/Parquet（2026-05-24 新增）

`train_classifier.py` 支持 `--csv` 参数载入本地 CSV，不再只依赖 yfinance：

```bash
# 载入 Kimi 提供的 CSV 数据（注意路径：在 data/training/ 下）
python3 train_classifier.py --lookback 60 --stride 1 --csv data/training/SPY_1h_combined.csv

# 载入 5min 55天 CSV（在 kronos/data/ 下）
python3 train_classifier.py --lookback 60 --stride 1 --csv kronos/data/spy_5m_55d_yf.csv

# 仍是 yfinance 模式（默认）
python3 train_classifier.py --lookback 60 --period 60d --stride 1 --force
```

**重要 — 文件路径：**
- **1h / daily 数据** → `data/training/`（跟 training/ 腳本同層）
- **Kronos 训练用 parquet/CSV** → `kronos/data/`
- 训练脚本 CWD = `plugins/onebot3/`，路径相对此目录
- 混淆会导致 FileNotFoundError（1h 的 CSV 在 `data/training/` 不在 `kronos/data/`）

CSV 需要的列：Date/Datetime, Open, High, Low, Close, Volume（列名自动模糊匹配）。

详见 `references/kronos-cluster-training.md`。

### 关键技术发现

- `model.decode_s1()` **已经返回 context** 作为第二个返回值（`s1_logits, context = model.decode_s1(...)`，shape=(B,T,832)），不需要 forward hook
- 模型代码拷贝到插件内自包含，不依赖 git clone 或 pip install
- sys.path 需要加 kronos/ 目录（不是 kronos/model/），然后 `from model.kronos import Kronos`

### Plugin 命令注册 — `/forgetless` 和 `/report` 模式

两个插件命令已注册：`/forgetless` 拉对话原文交接 session，`/report` 拉 L1+L2 行情数据出报告。均在 `register(ctx)` 函数中通过 `ctx.register_command()` 实现。

```python
def register(ctx=None):
    if ctx is not None:
        ctx.register_command(
            name="forgetless",
            handler=_forgetless_handler,
            description="拉 archive.db N 小时内完整对话原文",
            args_hint="[hours] [session]",
        )
```

**Handler 签名：** `fn(raw_args: str) -> str | None`
- `raw_args` 是斜杠后面跟着的文本（如 `/forgetless 4 session` 的 `4 session`）
- 返回字符串会被 gateway 自动发送回 Telegram
- 框架 `plugins.py` line 1189-1190：`ctx = PluginContext(manifest, self); register_fn(ctx)`
- **自动出现在 Telegram `/` 菜单**，通过 `telegram_menu_commands()` 收集插件命令 → `set_my_commands()`
- **只需要 gateway 重启** 就能生效
- Handler 运行在 gateway 进程，不能调 agent tool — 用 `subprocess.run()` 跑外部脚本

### Forgetless 模式 — 代替 framework tool（2026-05-24）

**不要注册 framework tool。** 够简单就不需要。

脚本位置: `lib/forgetless.py`（插件内，L5 工具层）
用户触发: 说 `forgetless` 或 `查记录`，问 N 小时后运行

**激活流程：**
1. 用户说 forgetless → 问「拉过去几小时？」
2. `python3 ~/.hermes/plugins/onebot3/lib/forgetless.py --hours N`
3. 返回完整对话原文（含工具输出）

**直接 execute_code 版（不需要脚本，紧急时用）：**

```python
import sqlite3, json, datetime, time

db = sqlite3.connect("/home/ubuntu/.hermes/memory/archive.db")
db.row_factory = sqlite3.Row
cutoff = time.time() - N * 3600

rows = db.execute("""
    SELECT role, content, timestamp
    FROM conversations
    WHERE timestamp > ?
    ORDER BY timestamp
""", (cutoff,)).fetchall()

for m in rows:
    ts = datetime.datetime.fromtimestamp(m["timestamp"]).strftime("%H:%M")
    icon = {"user":"🧑","assistant":"🤖","tool":"🔧"}.get(m["role"], "❓")
    print(f"{icon} [{ts}] {m['role']}: {m['content'][:200]}")
```

**原理：** memory 存激活词 → 我读到后 execute_code 查 archive.db → 返回原文。
不需要 system_prompt_block 注入、不需要 tool schema 注册、不需要框架 hook。

**为什么 framework tool 方案被回滚：**
Originally 注册了 `get_session_raw` + `system_prompt_block()` 提示行 + memory 三层保护。用户说"花里胡哨屁用没有"——archive.db 已经有数据了，execute_code 直接读就行，加 tool 是多此一举。

**铁律：** 能 execute_code + SQLite 解决的，不要注册 framework tool。

### Guardrails/行为锁已废弃（2026-05-24）

- `hermes-execution-guardrails` skill 已删（用户说"根本不起作用"）
- `fact-checker` skill 已删（用户说没用）
- `self-check` 插件已删（只有空 plugin.yaml）
- `patch-honesty-check` cron 已删（每天修补 prompt_builder.py 的行为锁注入，已无意义）
- prompt_builder.py 里的「强制预加载技能规则」和「强制真实性自检规则」注入块已清除（~44 行）
- 不再需要在回复前自动加载特定 skill
- 不再有每日 cron 检查 prompt_builder.py 完整性

## 用户沟通偏好（重要）

- **目录/结构展示用 plain** — `dir/` + `  file.py` 平铺，不要 tree 连线 + 大小标注。用户说「你做plain给我啊你这么搞我眼花」
- **架构描述要 concise** — 4层: L1 L2 L3 L4 = data。不要逐文件注释
- **有问题直接答，不要绕** — 用户厌恶长铺垫
- **诚实说不知道/没做完** — 比声称完成好。用户对吹牛零容忍
- **说过的功能不要反着问** — 用户说「forgetless是给你看的不是给我看的」，改完就别再问
- **幹活時不要跑偏** — 用戶說「大哥你跑偏了，我們現在是 Kronos 模型組不是隨機森林大哥」。工作範圍明確時不要提「可以試試 MLP / XGBoost / RandomForest」這類沒被要求的方案。用戶對 scope creep 零容忍，不是他的需求就不要說。
- **長時間任務主動報進度** — 用戶會問「開始了嗎？」如果你啓動了長時間背景進程（訓練/下載），30-60 秒內主動報一次「已開始 X，預計 Y 分鐘完成」，不用等用戶問。notify_on_complete 之外也值得手動確認進度一次。

## 清理模式（用户已验证）

当用户说"清理skill"或"清理垃圾"时：

1. **scripts/ → 全清** — 所有独立脚本一旦迁移到插件就删原文件
2. **skills/ 空分类目录 → 批量删** — 没有 SKILL.md 的 category 目录都是壳
3. **stale cron → 删** — 框架级保留 `weekly-memory-distill` 和已删除 cron 的输出目录
4. **插件 → clean** — self-check 之类的空壳插件
5. **prompt_builder.py 注入 → clean** — 任何 patch 注入的规则块
6. **memory 旧条目 → prune** — 过期的 cron 配置、已回退的调度器记录等
7. **日志 → 删 diagnostic 日志**（shutdown/exit diag），保留当前运行日志

## 踩坑记录

### 10. 先查本地 API 再搜網絡

**問題（2026-05-24）：** 用戶問「Tradier 能不能下 5min 歷史 K 線」，我直接打開瀏覽器去 Tradier 文檔搜，用戶怒了：「我們自己就有 tradier 的 api 你干嘛要上网搜」。

**根因：** 忘記了 `api_client.py` 裡已經有 TradierClient，API key 就硬編碼在上面。任何關於數據源能力的問題，本地代碼就是答案。

**鐵律：** 
1. 用戶問 API 能力 → 先去查 `~/.hermes/plugins/onebot3/anchoring/api_client.py`
2. 看已有什麼 client、什麼方法、什麼 key
3. 不確定就直接 `curl` 測（key 在代碼裡明文）
4. 最後才考慮上網搜文檔

### 12. 系统测试 API key 边界

**问题：** 用户给了 Polygon API key 问能不能用。如果只回答"能"或"不能"会漏掉关键信息——它不能用做什么、能用做什么、限制是什么。

**正确流程（"API key 边界测试"模式）：**

1. **列测试清单** — 按使用场景分组：即时报价 / 聚合K线 / 期权 / 参考数据
2. **逐端点测** — 用 curl 或 urllib 打每个端点，区分 HTTP 状态码含义
   - `200 ✅` = 可用
   - `403 ❌` = Forbidden（需升级计划）
   - `429 ⚠️` = Rate limited（等第限制）
   - `404` = 端点不存在 / 不合语法
3. **检查分页** — 对历史数据端点，确认 `next_url` 存在且可追踪
4. **检查延时** — 返回数据中的 status 字段（`DELAYED` = 15分钟延迟），对比当前时间
5. **检查 Rate Limit** — 连续打 10 次，看多少成功、间隔多长

**Polygon 实测结果（key=`pavJHKDnT7vBA8kXH55_0HdsKNCpZYPg`）：**

| 功能 | 结果 | 备注 |
|------|------|------|
| 5min 历史 | ✅ 全量分页 | ~1000 bars/page, follow next_url |
| 日K | ✅ 全量 | 250 bars/year |
| 期权历史 | ⚠️ 延迟15分钟 | |
| 即时报价 | ❌ 403 | 需升级 |
| Rate limit | ⚠️ ~5req/min | Free tier |

**教训：** 用户给新 API key → 5 分钟测全端点 → 给一份「能用/不能用/限制」对照表。不要猜，不要假设。

### 14. 🔴🔴🔴 L3 是归档层，跟報告鏈路無關（高優先級 — 已被用戶多次糾正，2026-05-24 再次糾正）

**問題：** 彙報時說「L1→L2→L3 (LLM報告)」或「L3=LLM報告層」，用戶會立刻暴怒糾正。

**用戶原話：** 「L3不是LLm啊大哥你又失憶 L3是歸檔，L4是存儲」

**正確分層（刻在腦子裡，不許再錯）：**
- L1 = anchoring（採集）
- L2 = kronos（預測）— 只讀自己需要的數據
- L3 = distiller（歸檔）— **不是 LLM 報告層**
- L4 = data（存儲）
- L5 = lib（工具）
- **LLM 報告 = Hermes Agent 自己寫，不在 onebot3 插件分層內**

**正確數據流：**
```
L1 採集全量數據
├── price+gex → L2 讀取 → 預測結果 → Hermes
└── 其餘數據（指標/情緒/宏觀/財報） → Hermes
```
L2 不消費全量 L1。Hermes 拿 L1 其餘數據 + L2 預測結果，直接寫報告。L3/L4 跟報告無關。

### 13. 何時不用 delegate_task/subagent（2026-05-24）

**問題：** 用戶問 Kronos 訓練能否用子代理加速。答案是不能。

**根因：** Kronos 模型是單例 Singleton（`_load_once()` 類方法），子代理每個 fork 一份新進程→各自重新加載 Kronos（+391MB）→ 搶 CPU 核心→ 反而更慢。

**適用 delgate_task 的場景：**
- I/O 密集型（並發 API 請求、多個文件下載）
- 推理結果可獨立驗證（沒有共享狀態）
- 子任務之間無依賴

**不適用 delgate_task 的場景：**
- 共享大模型的推理（Kronos base, LLM）
- CPU 是瓶頸（不是 I/O）
- 需要跨子任務共享中間狀態
- 子任務需要用戶交互（delgate_task 不支援 `clarify`）

**鐵律：** 確認瓶頸在 CPU 推理還是 I/O 延遲。CPU 瓶頸時子代理只會讓事情更慢。

### 11. Yahoo 5min 數據不存在「分月拼接」

**問題（2026-05-24）：** 用戶說「用 yahoo 下載不同的月份拼一起就可以有一年了」，我照做了但 yfinance 返回空數據。

**根因：** Yahoo 5min 數據有 **60 自然天硬限制**，後端沒存超過 60 天的 5min K 線。不是分片策略的問題。

**實測證據：**
- 2026-04-01 → 2886 bars ✅（但實際返回了直到 5/22 的所有數據）
- 2026-03-01 → empty ❌（60 天線在 ~3/25）
- 任何早於 60 天的日期 → empty

**鐵律：** 不要假設用戶說的數據方案一定可行。先 `yfinance.download(interval="5m")` 測一下再寫腳本。

詳見 `references/data-source-capabilities.md`。

### 9. 闭包陷阱 — `register()` 中 `del` 局部变量导致 handler 炸

**问题（2026-05-24）：** 在 `register(ctx)` 的 try 块中，`_forgetless_handler` 闭包引用了外层 `subprocess`。末尾 `del subprocess` 导致 handler 被调用时报错：

```
❌ 执行失败: cannot access free variable 'subprocess' where it is not associated with a value in enclosing scope
```

**根因：** `del` 删除了闭包引用的自由变量。Python 闭包在定义时捕获变量的引用，`del` 后该引用悬空。

**铁律：** 不要 `del` 任何被闭包引用的局部变量。如果担心命名空间污染，把 handler 定义成模块级函数而不是嵌套闭包。

### 1. 验证数据源真实性的铁律

**问题（2026-05-24）：** 用户发现我声称的"脉冲性能基线"是基于模拟数据，不是真正的 Tradier 输出。

**根因：** 跳过了"先确认数据源连通性再进行性能分析"的步骤。

**铁律：**
1. 无论报告任何基线/性能数据，**必须先验证连到的是真实数据源**
2. 查 `market.db` 最新快照的时间戳和内容是真实 Tradier 数据还是模拟回放
3. 不确定就查，不猜。用户对"吹牛说是真的"零容忍

**验证命令：**
```python
from anchoring.db_manager import DBManager
db = DBManager('data/market.db')
snap = db.get_latest_snapshot()
# 检查 snap 的 source / timestamp / underlying_price
```

### 2. 模块级 import side-effect 陷阱

**问题：** `__init__.py` 底部有 `try: register()`，`from __init__ import X` 触发全脉冲 161s。

**修复：** 去掉模块级自注册。所有 L1 查询直接读 SQLite，不创建 AnchoringEngine 实例。
- 修复前: `from __init__ import get_current_snapshot` → 161s
- 修复后: → **<0.01s**

### 3. GEX O(n²) → O(n) 向量化

**问题：** `_calc_max_pain` 嵌套循环 9886 行 × ~500 行权价 → ~500 万次迭代 = 71.88s。

**修复：** 向量化成 O(n) 累积和（numpy 数组操作替代双重循环）→ **1.16s**。

### 4. DB 清理 TTL 时区陷阱

**问题：** `datetime.now()`（CDT）+ `.isoformat()`（T 分隔）vs SQLite `CURRENT_TIMESTAMP`（UTC，空格分隔）→ 每次脉冲后数据全灭。

**修复：** `datetime.utcnow()` + `strftime("%Y-%m-%d %H:%M:%S")` 对齐 SQLite。

### 5. MemoryProvider 陷阱 — 插件加载被静默跳过

**问题：** standalone 插件中加入 `from agent.memory_provider import MemoryProvider` 后，插件被 skips。

**根因：** `hermes_cli/plugins.py` 检测到关键字后自动将 kind 从 `"standalone"` 改为 `"exclusive"` → 两边都不加载。

**铁律：** 永远不在 standalone 插件中添加 MemoryProvider 关键字。替代方案：需要报数前直接读 `data/market.db`。

### 6. 格式 bug

- 嵌套 f-string → `$$522.00`（2026-05-24）
- `\\$` SyntaxWarning（2026-05-24）

### 7. i18n 翻译键显示为键名（`gateway.usage.xxx`）

**问题（2026-05-24）：** `/usage` 命令输出 `gateway.usage.header_session_info` 等原始键名而非中文文本。

**根因：** Hermes i18n 系统在 `agent/i18n.py` 中通过 `t()` 函数查找 `locales/<lang>.yaml`。该目录在安装时不存在（`~/.local/lib/python3.12/site-packages/locales/` 整个缺失），导致 `_load_catalog()` 返回空字典，`t()` 回退到返回键名本身。

**修复：** 创建 `locales/en.yaml` 和 `locales/zh.yaml`，嵌套 YAML 结构：

```yaml
gateway:
  usage:
    no_data: "暂无 session 数据"
    header_session_info: "Session 信息"
```

`_flatten_into()` 自动将嵌套 YAML 转为扁平键名。i18n 缓存进程级，加文件后必须 gateway 重启刷新 `_catalog_cache`。

### 8. Telegram 命令菜单定制（~/.local/lib/python3.12/site-packages/hermes_cli/commands.py）

**问题（2026-05-24）：** 44 个内置 Telegram `/` 命令太杂，用户要精简。

**方案（不要用 `cli_only=True`）：** 加 `TELEGRAM_HIDDEN_COMMANDS` frozenset + `ZH_DESCRIPTIONS` dict，在 `telegram_bot_commands()` 中过滤。隐藏的命令仍可通过 `is_gateway_known_command()` 正常 dispatch。

⚠️ **铁律：** 永远不要把用户的插件命令（`/forgetless`, `/report`）放进隐藏集。

### 8. Telegram 命令菜单定制（~/.local/lib/python3.12/site-packages/hermes_cli/commands.py）

**问题（2026-05-24）：** 44 个内置 Telegram `/` 命令太杂，用户要精简。

**方案（不要用 `cli_only=True`）：** 加 `TELEGRAM_HIDDEN_COMMANDS` frozenset + `ZH_DESCRIPTIONS` dict，在 `telegram_bot_commands()` 中过滤。隐藏的命令仍可通过 `is_gateway_known_command()` 正常 dispatch。

⚠️ **铁律：** 永远不要把用户的插件命令（`/forgetless`, `/report`）放进隐藏集。

详情见 `utilities/forgetless` skill 的 `references/telegram-command-setup.md`。

## 已验证的跑通路径

```python
from __init__ import (
    get_current_snapshot, get_gex_levels, get_indicator_signal,
    get_sentiment, get_formatted_block, get_kronos_prediction,
    get_distilled_daily, get_distiller_block
)
snap = get_current_snapshot()    # L1 <0.01s（读 data/market.db）
k = get_kronos_prediction()      # L2 ~4.6s（读 data/market.db）
daily = get_distilled_daily()    # L3 <0.01s（读 data/market.db）
```

**Forgetless（换 session 后查原文）：** `python3 lib/forgetless.py --hours N` 或 Telegram `/forgetless N`

**i18n 修复：** 参考 `references/hermes-i18n-locale-fix.md` — locales 目录创建 + en.yaml/zh.yaml 内容模式。

**一键出报告：** Telegram `/report` — 拉 L1+L2 完整数据，格式见 `references/report-command.md`

详见 `references/data-source-capabilities.md` — YFinance 60天硬限制 / Tradier 10天 / 用户提供 1年 5min CSV / 各来源對比

### 模型备份命名约定（2026-05-24）

每次训练区分类器时会覆盖 `kronos/models/zone_classifier.pkl`。用前缀保存不同版本：

| 文件 | 数据源 | 用途 |
|------|--------|------|
| `zone_classifier.pkl` | 当前主力 | 推理用 |
| `zone_classifier_5m55d.pkl` | 5min 55天 yfinance | 5min 备选 |
| `zone_classifier_1h.pkl` | 1h CSV | 长期结构备选 |

**原则：** 每次训新模型前先 `cp zone_classifier.pkl zone_classifier_xxx.pkl`，否则旧模型被覆盖。

### 存档快照工作流（2026-05-24 新增）

当用户说「保存现状」或「真正的存档」时：

1. **tar 源码**（排除大文件、cache、训练数据）：
   ```bash
   cd ~/.hermes/plugins/onebot3
   tar -czf data/kronos-v{X}.{Y}-src.tar.gz \
     --exclude='__pycache__' \
     --exclude='*.pkl' --exclude='*.csv' \
     --exclude='*.npz' --exclude='*.parquet' \
     kronos/
   ```
2. **附带快照说明** `data/kronos-v{X}.{Y}-SNAPSHOT.md`，包含：
   - 版本号、时间、封包名
   - 文件清单
   - 当前状态（准确率、标签策略、训练数据、集群配置）
   - 已知限制
   - 还原方式
3. **存储位置**：`~/.hermes/plugins/onebot3/data/`（L4 存储层）
4. **还原**：解压 + 把对应的 `zone_classifier.pkl` 放回 `kronos/models/` 即可
5. **不要把大模型或训练数据包进源码快照** — 模型 `zone_classifier*.pkl` (34KB) 可单独备份，Kronos-base (391MB) 在 HF cache 不需要备份

#### 当前存档清单（2026-05-24）
- `kronos-v1.0-src.tar.gz`（19K）— KronosCluster v1.0 源码快照
- `kronos-v1.0-SNAPSHOT.md` — 快照说明
- `zone_classifier_1y.pkl` — 当前最佳模型（70.0% OOS）
- `zone_classifier.pkl` — 旧 55d 模型（37.3% OOS，已过期）

### 用户提供 5min 1年 CSV（2026-05-24）

用户拿到的 **spy_5min_1year.csv**（47,576 bars, 24h UTC 覆盖）放在 `kronos/data/`。2026-05-24 已开始训练（stride=5, ~9,500 samples, CPU 推理约 30 分钟）。详见 `references/data-source-capabilities.md`。

**注意 UTC 时区：** 这数据的 timestamps 是 UTC，不是 ET。训练脚本的 `between_time("09:30", "16:00")` 过滤在 UTC 下不适用（UTC 09:30 = ET 05:30）。如果训练要用，需在预处理阶段做 UTC→ET 转换。

### Polygon API 数据源（2026-05-24 新增）

用户提供的 Polygon key `pavJHKDnT7vBA8kXH55_0HdsKNCpZYPg`，free tier。可获取全量历史 5min（分页），但不可用于实时数据。详见 `references/data-source-capabilities.md`。

## 当前性能基线（2026-05-24）

| 操作 | 耗时 | 状态 |
|------|------|------|
| 全脉冲（链+GEX+指标） | ~8.8s | ✅ 正常 |
| GEX 计算 | ~1.2s | ✅ 正常 |
| L1 查询（读 DB） | <0.01s | ✅ 正常 |
| KronosCluster 推理（5 引擎） | ~6.5s | ✅ 已上线（共享模型权重，CPU 推理） |
| Distiller 出报告 | <0.01s | ✅ 正常 |
| i18n locales 目录 | — | ❌ 已创建 en.yaml + zh.yaml |

⚠️ Kronos HF cache 完好（391MB+16MB），旧 symlink（指向 skill 目录）已在 2026-05-24 清理时清除。插件现在自包含，不依赖任何外部 symlink。
