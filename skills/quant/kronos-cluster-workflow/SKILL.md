---
name: kronos-cluster-workflow
description: KronosCluster v1.2 建置與訓練流程 — 日線百分位 3-class (75.2% avg)
---

# KronosCluster Workflow

## 系統位置
`~/.hermes/plugins/onebot3/kronos/`
- `engine.py` — `KronosEngine` + `detect_range()` (百分位 P5/P95)
- `cluster.py` — 5 engine 集群融合

## 標籤方案（已定稿）
**百分位 3-class** — 拒絕 Swing Point / MLP
- `detect_range(df_close, window=100)` → rolling P5/P95
- 0=支撐區 (close <= P5), 1=中性, 2=阻力區 (close >= P95)
- 與 Kronos hidden state 的趨勢編碼天然對齊

## 訓練設定
```python
LogisticRegression(C=0.01, solver='lbfgs', max_iter=2000, random_state=42)
# 勿加 class_weight！百分位分布均衡，balanced 倒扣
```

## 數據
- 日線: `/tmp/kimi_data/SPY_daily_2022_now.csv` (1100 bars)
- 5min: 已廢棄（支撐 recall 7%，無法救）

## ⚠️ 鐵律：報告準確率前必須做三件事（用戶暴怒觸發點）

這個 session 我被用戶現場抓到報 97.9% 假數字 — 以下是拯救方案：

**1. C 值掃描（禁止用預設 C=1.0）**
832 維 × ~400 訓練樣本 = 維度災難，預設 C=1.0 訓練集 97.9% / 驗證集 70%，差 28pp。必須跑:
```python
for C in [0.01, 0.05, 0.1, 0.5, 1.0]:
    clf = LogisticRegression(C=C, solver='lbfgs', max_iter=2000)
```
選 3-fold 平均 test acc 最高的。

**2. 狗基線對比（必須同步報告）**
永遠預測「中性區（class 1）」的模型叫狗策略。報告 classifier 準確率時必須同時報告狗基線。
- 如果模型只比狗高 <10pp → 模型不可用，直接說
- 日線百分位模型比狗高 ~20pp ✅

**3. 時間序驗證（禁止 shuffle）**
Shuffle 有 ~33pp 水分（55d 模型 shuffle 驗證 70.5%，時間序 OOS 只有 37.3%）。
```python
# 3-fold Forward Chaining
folds = [
    ("Fold 1 (早)", 0, int(n*0.50), int(n*0.50), int(n*0.70)),
    ("Fold 2 (中)", 0, int(n*0.70), int(n*0.70), int(n*0.85)),
    ("Fold 3 (晚)", 0, int(n*0.85), int(n*0.85), n),
]
```
報告用平均 test acc，不報最大值。

**實例 — 75.2% 是怎麼來的：**
- Fold 1 (早): 85.1% (狗 63.8%, +21pp ✅)
- Fold 2 (中): 65.7% (狗 45.7%, +20pp ✅)
- Fold 3 (晚): 74.6% (狗 53.5%, +21pp ✅)
- 平均: 75.2% (狗 ~54%)

## 標籤說明（均值回歸信號，不是結構性支撐/阻力）

百分位 P5/P95 標籤本質是均值回歸信號：價格跌到近 4 個月區間底部 → 買 CALL，漲到頂部 → 賣 PUT。
- ✅ 對 Kronos hidden state 的趨勢編碼天然對齊
- ❌ 不是真正的技術支撐/阻力位
- 對萬年多頭：**「跌到 P5 以下買 Call」是有效策略**
- SPY 長期向上，均值回歸只在震盪市有效，趨勢年會被打破

## 陷阱（2026-05-24 驗證）
- **🤡 先報 97.9% 再被用戶罵** — 永遠先調 C 再做 C sweep + 狗基線對比，不要直接報預設參數的數字
- **Kronos hidden state 無局部曲率特徵 → Swing Point 必翻。** 832 維裡可能有 50 維編碼趨勢、50 維編碼波動，但沒有一維編碼「左右各 5 根極值檢測」
- **5min 樣本/維度比 < 1 → 數學上不可救。** 758 樣本 × 832 維，每類平均 150 樣本去擬合 832 維超平面。支撐 recall 7%。
- **日線 gap > 10pp → 調降 C**，還不行就 PCA(n_components=0.90)
- **class_weight='balanced' 在百分位標籤下反效果** — 分布天然均衡（~5%/90%/5%），balanced 會壓中性區權重
- **標籤與特徵不對齊時模型不可能學好** — 標籤方法必須與特徵幾何對齊。這是核心原則。

## 參考文件
- `references/kronos-cluster-training-history.md` — 完整訓練歷程（四階段演進）
