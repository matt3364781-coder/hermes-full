# 时间序列验证 — 金融 ML 训练铁律

## 问题

用随机 shuffle 做 train/test split 会把相邻 K 线泄漏到测试集。
相同市场状态的样本出现在两边，模型等于见过类似数据再考。

## 实测

| 验证方式 | 准确率 | 水分 |
|----------|--------|------|
| 随机 shuffle | 69.6% | — |
| 时间序列前80%/后20% | 57.5% | **+12.1%** |

## 正确做法

```python
# ❌ 错误
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2)

# ✅ 正确
split = int(len(X) * 0.8)
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]
```

## 适用场景

- 任何 K 线/时间序列相关的 ML 训练
- 不适用：独立同分布数据（非时序）

## 报告规范

任何 ML 准确率报告必须附带：
1. 验证方式（随机 shuffle / 时间序列 / 滚动交叉验证）
2. 样本量
3. 分类数 + 随机基准线
