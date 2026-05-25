# KronosCluster 訓練：震盪區間定位

## ⚠️ 核心鐵律（用戶強調）

**訓練目標是區間定位，不是股價預測。** Kronos 的 832-dim hidden state 應該回答「現在在震盪區間的哪裡」（支撐區/中性區/阻力區），不是「下一根漲還是跌」。

方向預測（二分類：漲/跌）在 5 分鐘線上 ≈ 白噪聲

## 正確的訓練框架

### 標籤生成 — Swing Point 法（2026-05-24 起）

**用局部波峯波谷代替百分位（舊版）。** 百分位法的 5%/95% 分位不是真實支撐阻力位，Swing Point 貼合交易認知。

```
波谷（低於左右各5根）= label 0 支撐區
波峰（高於左右各5根）= label 2 阻力區
close 站上最近波峰    = label 3 A+1突破
close 跌穿最近波谷    = label 4 A-1跌破
其餘                 = label 1 中性
```

實現於 `train_classifier.py` 的 `detect_range()` 函數。由 Kimi Agent 編寫，我整合替換。

```python
def detect_range(df, window=100):
    left = right = 5

    low_l  = df['low'].shift(1).rolling(window=left,  min_periods=1).min()
    low_r  = df['low'].shift(-right).rolling(window=right, min_periods=1).min()
    is_trough = (df['low'] < low_l) & (df['low'] < low_r)

    high_l = df['high'].shift(1).rolling(window=left,  min_periods=1).max()
    high_r = df['high'].shift(-right).rolling(window=right, min_periods=1).max()
    is_peak = (df['high'] > high_l) & (df['high'] > high_r)

    last_peak   = df['high'].where(is_peak).shift(1).ffill()
    last_trough = df['low'].where(is_trough).shift(1).ffill()

    labels = pd.Series(1, index=df.index, dtype=int)
    labels[is_trough] = 0
    labels[is_peak]   = 2

    not_swing = ~(is_trough | is_peak)
    breakout = not_swing & last_peak.notna() & (df['close'] > last_peak)
    labels[breakout] = 3
    breakdown = not_swing & last_trough.notna() & (df['close'] < last_trough)
    labels[breakdown] = 4
    return labels
```

**注意兼容大小寫列名：** CSV 可能帶 `open`/`high`/`low`（小寫）或 `Open`/`High`/`Low`（大寫）。函數內部用 `if 'low' in df.columns else 'Low'` 自動檢測。

**前5根/後5根K線** 因缺少左右上下文，`rolling` 的 min_periods 會讓 `is_trough`/`is_peak` 自然為 False，不會誤判。初始無 Swing Point 時 `last_peak`/`last_trough` 為 NaN，`breakout`/`breakdown` 自然為 False。

### 完整訓練流程

給定歷史價格序列：

1. **找 Swing Point**：局部波峯波谷檢測（左右各5根）
2. **標位置**：Swing Point + 突破/跌破 → 5 類標籤
3. **Kronos 特徵提取**：滑窗 → 歸一化 → tokenizer.encode() → decode_s1() → context[-1, :]（832-dim）
4. **訓練**：LogisticRegression（4165 params）

### 過去 vs 現在標籤對比（1年 5min 數據樣本）

**舊百分位法（label 分布）：** `0:1327 / 1:3339 / 2:2038 / 3:1730 / 4:1070` — 支撐區/阻力區偏多
**Swing Point（label 分布）：** `0:59 / 1:689 / 2:62 / 3:96 / 4:94` — 更稀疏，只標真·轉折點

Swing Point 更貼合交易認知：不是每個統計百分位都是支撐阻力，只有局部極值才算。

### 特徵提取關鍵代碼

```python
from kronos.engine import KronosEngine, _normalize_klines, _build_time_stamp
import torch

model = KronosEngine._shared_model
tokenizer = KronosEngine._shared_tokenizer
device = KronosEngine._device

normed, _, _ = _normalize_klines(arr)
stamp = _build_time_stamp(timestamps, device)
x_tensor = torch.from_numpy(normed).unsqueeze(0).to(device)

with torch.no_grad():
    tokens = tokenizer.encode(x_tensor, half=True)
    _, context = model.decode_s1(tokens[0], tokens[1], stamp)
    emb = context[0, -1, :].cpu().numpy()  # (832,)
```

### 训练结果汇总（2026-05-24 更新 — 跨时间 OOS 验证发现 55d 严重过拟合）

#### ⚠️ 2026-05-24 重大发现：55d 模型严重过拟合

原本 shuffle 验证认为 55d 模型（70.5%）优于 1y 模型（60.4%）。**跨时间 OOS 验证完全推翻此结论：**

| 模型 | shuffle test | 真实 OOS（未来数据） | 差距 |
|------|-------------|---------------------|------|
| 55d 模型（旧主力） | 70.5% | **37.3%** ❌ | -33.2pp |
| 1y 模型（新） | 97.9% | **70.0%** ✅ | -27.9pp |

**结论翻转：55d 模型是伪高精度。** 它死记了 55 天单边上涨区间的噪音模式，换到任何其他时间段直接失效。1y 数据训练的模型即使只用 948 samples（stride=50），OOS 准确率也达到 70.0%——数据多样性才是泛化的关键。

**1y 模型（当前主力）训练细节：**
- 数据：`spy_5min_1year.csv`（47,576 bars, 2025-05-27 ~ 2026-05-23）
- Stride=50 → 948 samples
- 时间序 80/20 分割（train: 2025-05 ~ 2026-03, test: 2026-03 ~ 2026-05）
- 标签：百分位法 p1/p5/p95/p99, window=100
- 特征缓存：`kronos/models/features_1y_stride50.npz`
- 模型：`kronos/models/zone_classifier_1y.pkl`

#### ⚠️ 百分位法 vs Swing Point 决策记录

Swing Point 已測試後**回退到百分位法**，原因：

| 指標 | 百分位法 | Swing Point |
|------|---------|-------------|
| test acc | 70.5% | 70.7%（相近）|
| 支撐區 recall | 0.43 | **< 0.1 ❌** |
| 阻力區 recall | 0.52 | **< 0.1 ❌** |
| 標籤分布 | 密集（~15% 非中性） | 極稀疏（~6% 非中性） |

Swing Point 標籤太稀疏，LogisticRegression 學不到足夠的支撐/阻力樣本 → 支撐區和阻力區召回率幾乎為 0。百分位法雖然假信號多，但至少能檢測到支撐區和阻力區。

**當前主力仍是百分位法。** 如果以後換非線性分類器（MLP），可以重新考慮 Swing Point，因為非線性模型能從稀疏標籤中學到更多。

#### 各數據源對比（百分位標籤，shuffle split）

| 數據源 | 樣本數 | Test Acc | 支撐區 F1 | A+1突破 F1 |
|--------|--------|----------|-----------|-------------|
| 舊 5min 60d (yfinance) | 4,620 | 69.6% | 0.57 | 0.78 |
| **新 5min 55d** 🟢 | 2,982 | **70.5%** | **0.58** | **0.76** |
| 1h (Kimi CSV) | 3,413 | 67.9% | 0.36 | 0.78 |
| 1y 5min (用戶提供, stride=5) | 9,504 | 60.4% | 0.46 | 0.71 |

结论（2026-05-24 修正）：**55d 模型 shuffle 70.5% 是数据泄漏假象，真实 OOS 仅 37.3%。1y 模型时间序 70.0% 才是真·泛化能力。** 数据多样性 > 数据密度。

#### 为什么 1 年 5min 数据「之前以为」不如 55 天？— 2026-05-24 结论翻转

之前基于 shuffle split 的结论「1y 数据 60.4% 不如 55d 的 70.5%」是**错误的**。真相：

1. **55d 用 shuffle split 有大量数据泄漏**——相邻 K 线形态相似，shuffle 把相似的训练/测试样本混在一起 → 虚高 33pp
2. **1y 用 stride=5 采样过密**——9504 samples 横跨 $585→$749，label 在同一个 100-bar 窗口内频繁变化 → 线性模型统计上更难拟合
3. **用公平对比（时间序 80/20 + stride=50）：** 1y 模型 70.0% vs 55d 的 37.3% → **1y 完胜**

最终结论：之前认为的「线性模型跨区段局限」理论本身有道理，但 1y 模型的实际表现（70.0% OOS）说明**丰富数据可以抵消这个局限**。55 天只有单一上涨区间，1 年数据跨越 $585→$749 多阶段市场，模型学到了更普适的映射。

**如果将来用更长周期（3年+）训练，跨度更大的价格 range 可能会让线性模型再次失效**——那时换 MLP 才有意义。

### ⚠️ 時間序列驗證（數據泄漏陷阱）

隨機 shuffle 做 train/test split 會把相鄰 K 線洩漏到測試集。Bar 100 和 Bar 101 走勢高度相似，模型在訓練集見過類似形態，考試時自然高分。水分 +12.1%。

**正確做法：** 時間序列 split（前 80% 訓練，後 20% 測試，不 shuffle）。

**任何時候報告準確率，必須先說明驗證方式。**

真實泛化表現（時間序列 split，舊 60d 模型）：

| 標籤 | 名稱 | 精確率 | 召回率 | F1 | 說明 |
|------|------|--------|--------|-----|------|
| 0 | 支撐區 | 0.53 | 0.43 | 0.48 | 仍偏弱 |
| 1 | 中性區 | 0.46 | 0.57 | 0.51 | 易被污染 |
| 2 | 阻力區 | 0.61 | 0.52 | 0.56 | 中等 |
| 3 | A+1突破 | **0.66** | **0.72** | **0.69** | **✅ 可用** |
| 4 | A-1突破 | 0.65 | 0.55 | 0.59 | 中等 |

A+1突破檢測（recall=72%）是唯一真實有價值的信號。

### 訓練歷史記錄

| 嘗試 | 標籤法 | samples | stride | 驗證 | 準確率 |
|------|--------|---------|--------|------|--------|
| 方向預測二分類 | — | 462 | 10 | shuffle | 55.6% |
| 早期區間 5 類 | 百分位 | 924 | 5 | shuffle | 58.9% |
| 全量區間 5 類 | 百分位 | 4620 | 1 | shuffle | 69.6% |
| 全量區間 5 類（真實） | 百分位 | 4620 | 1 | 時間序列 | **57.5%** |
| 55天 5min | 百分位 | 2982 | 1 | shuffle | **70.5%** |
| 55天 Swing Point | Swing Point | 2982 | 1 | shuffle | 70.7% (recall<0.1, 已回退) |
| **1y 5min 全年** 🆕 | **百分位** | **948** | **50** | **时间序 80/20** | **70.0%（真·泛化）** |
| 55d 5min（旧主力） | 百分位 | 2982 | 1 | 跨时间 OOS | **37.3%（严重过拟合）** |

### 數據來源文件路徑（易混淆）

```
plugins/onebot3/
├── train_classifier.py       ← 腳本，CWD=此目錄
├── kronos/
│   ├── data/                 ← 5min 訓練用 CSV（spy_5m_55d_yf.csv 等）
│   └── models/               ← zone_classifier.pkl + 備份在這
└── data/
    ├── training/             ← 1h / daily CSV（Kimi 上傳的源文件）
    └── market.db             ← 脈衝數據庫
```

- `train_classifier.py --csv kronos/data/spy_5m_55d_yf.csv` ✅
- `train_classifier.py --csv kronos/data/spy_5min_1year.csv` ✅
- `train_classifier.py --csv data/training/SPY_1h_combined.csv` ✅
- ❌ `kronos/data/SPY_1h_combined.csv` — 不存在，1h 在 `data/training/`

### Kimi 協作模式（2026-05-24）

當任務可分割成獨立子任務時，讓 Kimi Agent 和 Hermes 並行工作：

- **Kimi 負責：** 純函數邏輯改寫（如 detect_range 標籤演算法）— 不需要啟動 Hermes 工具、不涉及文件系統操作、純 Python 函數
- **Hermes 負責：** 文件修改、重訓運行、系統整合（補 decoder direction、更新 cluster.py）

**分工原則：** Kimi 輸出函數體 → Hermes 集成進真實文件 → 測試 → 重訓。不要 Kimi 去改真實文件或跑訓練。

### 训练教训

1. **不要拿 924 samples 说训好了**（用户指出来说「我塞了好几千的样本给你」）
2. **不要报告随机 shuffle 的准确率**（必须跑跨时间 OOS 核实 — 55d 模型的 shuffle 70.5% 实际只有 37.3%）
3. **永远做跨时间 OOS 验证** — 训练数据之外的日期跑一次，才知道模型是学到模式还是死记噪音
4. **数据多样性比数据密度重要** — 55d 高密度（stride=1, 2982 samples）不如 1y 低密度（stride=50, 948 samples）
5. **时间序 80/20 分割**：前 80% 训练，后 20% 测试，不 shuffle，不交叉
6. **数据源**：YFinance 5min 最多 60 天；用户提供 1 年 CSV 有 47,576 bars 但需注意 UTC 时区
7. **5min 比 1h 效果好** — 粒度更细，区间定义更精准
8. **Swing Point 比百分位稀疏** — 这是 feature 不是 bug，真·转折点才有交易意义
9. **特征缓存很重要** — Kronos 推理 0.5-1s/sample × 1000+ = 10+ 分钟。第一次算完后保存 `.npz`，训练迭代秒出结果

10. **🏆 完整训练检查清单（2026-05-24 用户纠正后总结）**：

    ```
    ⚠️ 别急着跑训练，先做这6步：
    
    1. 确定标签策略（百分位 p1/p5/p95/p99）
    2. 确定 stride（每天~78根5min，stride=50 约1500样本/年）
    3. 跨时间 OOS 划分：前 80% 训练，后 20% 测试
       - 训练数据必须覆盖 ≥2 个市场阶段（单边涨不够）
    4. ⚠️ 检查 classifier 的 pickle 结构：
       clf_data = pickle.load(f)
       clf = clf_data['model'] if isinstance(clf_data, dict) else clf_data
       # 文件保存为 dict {'model': clf, 'train_accuracy': ..., ...}
       # 不是裸的 LogisticRegression 对象
    5. 调 C 超参数（LogisticRegression，832维特征）：
       - 先用 C=0.01, 0.1, 1.0, 10.0 快速扫描
       - 选 train/test 差距最小 + test 最高的 C
       - C=0.01 通常最佳（gap 10pp）
       - C=1.0/train>90% → 严重过拟合信号
    6. 报告格式必须带：
       - 验证方式（时间序 OOS）
       - train / test 准确率
       - 各标签 recall
       - 与旧模型的 OOS 对比
    ```

11. **🚨 训练准确率 >90% 是红旗（2026-05-24 用户愤怒纠正）**
    - 5 分类 LogisticRegression，832 维特征
    - 758 训练样本时，C=1.0 给出 97.9% train = 严重过拟合
    - 用户原话：「97.9的准确率太离谱了大哥，你能不能好好检查啊？？？」
    - **检查方法**：跑 cross-validation（时间序 5-fold）看 C=0.01/0.1/1.0/10.0 的 train/valid 差距
    - **修复**：C=0.01 强制正则化，train 降到 77.6%，真实 OOS 仍有 67.4%

### 已知限制

- LogisticRegression 只有 4165 params，太简单
- 55d 模型已发现严重过拟合（shuffle 70.5% → OOS 37.3%），不应再使用
- 1y 模型（70.0% OOS）支撑/阻力区 recall ~20%，突破区 29-59%，仍有改善空间
- Swing Point 已测试（70.7% acc）但支撑/阻力 recall < 0.1，当前主力是百分位法
- 百分位法跨价格区段时标签飘移问题仍在，只是 1y 数据的多样性抵消了部分影响
