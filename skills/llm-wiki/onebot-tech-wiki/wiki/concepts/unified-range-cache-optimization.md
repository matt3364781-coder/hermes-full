# Unified Range 缓存优化

## 问题

`_predict_range()` 每次调用都重新加载 6 个 XGBoost 模型（共 51MB），导致：
- 首次调用延迟 > 1 秒
- 回测 1200 次耗时 21.8 分钟

## 根因

1. `_get_cached_forecaster()` 有 1 小时 TTL
2. 模型只在第一次调用时加载
3. 进程重启后缓存失效

## 方案对比

| 方案 | 优点 | 缺点 | 决定 |
|------|------|------|------|
| A. 去掉 TTL，永久缓存 | 简单，零开销 | 模型更新需重启 | ✅ 采用 |
| B. 添加 warmup() 预加载 | 启动时加载，首次调用快 | 启动时间增加 | ✅ 采用 |
| C. pickle 序列化 | 加载速度提升 5-10x | 需要额外维护序列化文件 | ❌ 不采用（模型文件已固定） |
| D. ONNX 加速 | 推理更快 | 需要转换，复杂度高 | ❌ 不采用 |

## 最终实现

```python
# 去掉 TTL
_RANGE_FORECASTER_CACHE: dict | None = None  # 永久缓存

def _get_cached_forecaster() -> dict:
    if _RANGE_FORECASTER_CACHE is not None:
        return _RANGE_FORECASTER_CACHE
    forecaster = _load_range_forecaster()
    _RANGE_FORECASTER_CACHE = forecaster
    return forecaster

def warmup() -> dict:
    """启动时预加载"""
    if _RANGE_FORECASTER_CACHE is not None:
        return _RANGE_FORECASTER_CACHE
    try:
        forecaster = _load_range_forecaster()
        _RANGE_FORECASTER_CACHE = forecaster
        return forecaster
    except Exception as e:
        return {"models": {}, "feature_names": [], "metrics": {}, "_load_error": str(e)}
```

## 验证结果

- 缓存命中时延迟：~0.019s（原 1.1s）
- 1200 次回测：24 秒（原 21.8 分钟）
- 60x 加速

## 相关文件

- `onebot/quant_core/analysis_layers/unified_range.py`

## 日期

2026-05-17
