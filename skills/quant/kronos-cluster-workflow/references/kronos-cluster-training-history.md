# Kronos Cluster Training History

## 訓練歷程（2026-05-24）

### 第一階段：55d 5min（被淘汰）

- 數據：yfinance SPY 5min, 55天 (3,042 bars), 2026-03-30 ~ 2026-05-22
- 標籤：百分位 rolling 100-bar P5/P95
- 分類器：LogisticRegression 預設 C=1.0
- 驗證：shuffle 70.5% → **真實 OOS 37.3%**（死記噪音）
- 教訓：**shuffle 有 33pp 水分，跨時間驗證是必須的**

### 第二階段：1y 5min（過渡）

- 數據：用戶提供 spy_5min_1year.csv (47,576 bars)
- 訓練：stride=50 → 948 samples
- C 掃描發現預設 C=1.0 過擬合（97.9% train vs 70.0% test）
- 最佳 C=0.01：train=77.6%, test=67.4%, gap=10.2pp
- 但 5min 先天缺陷：支撐 recall 7%，被 Kimi 判死刑

### 第三階段：Swing Point 區域標籤（封存）

- 路線：用左右各 5 根極值 + zone_radius=3 取代百分位
- 結果：3-fold avg 44.3%，比百分位 75.2% 差很多
- 失敗根因：Kronos hidden state 是時序壓縮向量，不是幾何特徵向量
  - 百分位問的是「價格相對於近期區間的位置」→ Kronos 天然保留
  - Swing Point 問的是「是否局部極值」→ 需要曲率特徵，Kronos 沒有
- 封存到：`~/.hermes/plugins/onebot3/data/archive/detect_range_swing.py`
- 復活條件：>2000 樣本 + 非 Kronos 特徵（raw OHLC + 成交量剖面）

### 第四階段：日線百分位 3-class（最終定稿）

- 數據：SPY_daily_2022_now.csv (1,100 bars), stride=2
- 標籤：detect_range(rolling 100-bar P5/P95)
- C=0.01：train=83.0%, test=74.6%, gap=8.3pp ✅
- 3-fold avg：75.2%（比狗基線 54% 高 21pp）
- 最終保存：`zone_classifier.pkl`
- 5min 模型：已全部刪除

## 關鍵決策備忘

| 決策 | 結論 | 原因 |
|------|------|------|
| 分類器 | LogisticRegression | 非線性用在這 = 過擬合保證 |
| class_weight | 不加 balanced | 百分位分布天然均衡，balanced 倒扣 |
| 5min 模型 | 廢棄 | 支撐 recall 7%，數學上不可救 |
| Swing Point | 封存 | Kronos 無曲率特徵，LR 學不動 |
| 標籤性質 | 均值回歸信號 | 不是結構性支撐/阻力，但策略有效 |
| 驗證方式 | 時間序 forward chaining | shuffle 有 ~33pp 水分 |
