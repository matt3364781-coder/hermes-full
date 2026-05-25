# KronosCluster v1.3 — 实现参考

## 架构

plugins/onebot3/kronos/ 下 4 个文件完全自包含：

```
__init__.py   → 暴露 KronosCluster, get_cluster, predict, predict_from_anchoring
engine.py     → KronosEngine（共享模型单例 + 独立后处理配置）
cluster.py    → KronosCluster（5 引擎融合）
model/        → 从 Kronos 官方 repo 拷贝的 kronos.py + module.py
```

## Model 加载

**关键模式：共享单例，不是 5 份拷贝。**

Kronos-base（102M params, 391MB）从 HF cache 加载一次：
```python
KronosEngine._load_once()  # 类方法，只在首次调用时加载
_tokenizer = KronosTokenizer.from_pretrained(TOKENIZER_ID, local_files_only=True)
_model = Kronos.from_pretrained(MODEL_ID, local_files_only=True)
```

每个 KronosEngine 实例共享 _model + _tokenizer，但各自有独立：
- lookback（窗口大小）
- threshold（触发阈值，支持 "adaptive" 动态值）
- ema_period（EMA 平滑周期）
- vol_weight / ignore_volume（成交量权重）
- vol_regime（波动率自适应开关）

## 推理流程

```
predict(klines: list[dict]) → dict
```

### 唯一路径（zone classifier）

1. 截取 `klines[-self.lookback:]` 作为输入窗口
2. 提取 numpy array (T, 6) = [open, high, low, close, volume, amount]
3. Z-score 归一化，clip=5
4. 从 klines 的 date 字段构建 stamp tensor（B, T, 5）= [minute, hour, weekday, day, month]
5. `tokenizer.encode(normed_tensor, half=True)` → (s1_ids, s2_ids)
6. `model.decode_s1(s1_ids, s2_ids, stamp)` → (s1_logits, context)
7. 取 `context[0, -1, :]`（832-dim hidden state）→ `zone_classifier.predict_proba()` → 5 类区间概率
8. argmax → zone label → `ZONE_TO_DIRECTION` 字典映射到方向
9. EMA 平滑（基于 continuous zone_score）→ 过滤微弱信号
10. 阈值过滤（`_get_threshold()`）

**v1.3 移除：decoder direction 路径。** 之前用 KronosPredictor 做自回归 next-bar 预测，300 次驗證準確率 42.3%（比隨機 50% 還差），已全面刪除 engine.py 和 cluster.py 中的相關代碼。

### 入口汇总（predict_from_anchoring — v1.3 更新）

`predict_from_anchoring(snap)` 在 cluster.predict() 结果上额外处理：

```python
# 1. GEX 方向判断
gex_net = snap["gex"]["net_gex"]
gex_aligned = (kronos_direction == sign(gex_net)) and kronos_direction != 0

# 2. 对齐时提升置信度
if gex_aligned:
    conf = min(conf + 0.15, 0.95)
```

⚠️ GEX 只修正置信度，不反转方向。
⚠️ v1.3 移除了 `decoder_summary` 字段。

## 聚类融合

```
_get_weights(market_regime) → 动态权重
_fuse(signals, weights) → 融合结果
```

分歧度定义：
- 1（全一致）：方向值全相同 → confidence=0.9, size=1.0
- 2（轻度分歧）：两个方向，且 |加权和|>0.3 → confidence=0.6, size=0.5
- 3（严重分歧）：三个方向（含0）或全中性 → confidence=0.0, size=0.0, alert

NEUTRAL(0) 不计入分歧计数（视为弃权）。

## 接口兼容

```python
# __init__.py
def get_kronos_prediction():
    snap = get_current_snapshot()
    return predict_from_anchoring(snap)

# /report handler — 格式化输出
kronos = get_kronos_prediction()
dir_map = {1: "CALL 🔵", 0: "NEUTRAL ⚪", -1: "PUT 🔴"}
d = dir_map.get(kronos.get("direction", 0), "?")
lines.append(f"  方向: {d} 置信度={kronos.get('confidence', 0):.0%}")
lines.append(f"  分歧度: {['一致','轻度分歧','严重分歧'][kronos.get('agreement', 3)-1]}")
lines.append(f"  分类器: {kronos.get('path_type', '?')} zone={kronos.get('zone', '?')}")
gex_a = "✅" if kronos.get("gex_aligned") else "⚠️"
lines.append(f"  GEX: {gex_a} net={kronos.get('gex_net', 0):,.0f} regime={kronos.get('gex_regime', '?')}")
```

## 已知问题

- vol 引擎的 threshold="adaptive" 需要 `_get_threshold()` 特殊处理；EMA 步骤和最终阈值过滤都引用同一个 variable `threshold`（不是 `self.threshold`），否则 float vs str 比较报错
- import 路径：`model.kronos` 要求插件目录在 sys.path 中，`KronosEngine._load_once()` 会自动添加
- 5 引擎推理约 4-6s（CPU），未来可加 `torch.inference_mode()` 提速
- `feedback()` 方法已写但无人调用，滚动准确率惩罚（`_get_recent_accuracy()`）永遠返回 None — 動態權重準確率調整是擺設
