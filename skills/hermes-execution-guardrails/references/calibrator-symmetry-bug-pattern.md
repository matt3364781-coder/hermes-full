# Calibrator-Predictor Geometry Mismatch Pattern

## Pattern

When a prediction system uses:
1. **Predictor** that outputs asymmetric intervals (e.g., quantile regression with q5/q50/q95)
2. **Calibrator** that assumes symmetric intervals (scales half-width around center)

The calibrator distorts the interval, causing severe hit rate loss.

## Example

**Predictor output** (XGBoost q5/q50/q95):
- low = 295.30
- center = 296.47  (q50 prediction, near low bound)
- high = 302.71

**Calibrator logic** (symmetric scaling):
```python
half_width = (high - low) / 2  # = 3.705
adj_low = center - half_width   # = 292.77 (too low)
adj_high = center + half_width  # = 300.18 (too low)
```

**Result**: Actual price 301.47 → MISS, even though original predictor would have HIT.

## Detection

Symptoms:
- Hit rate drops 10-15% after adding calibrator
- `_predict_range()` HITs but `full_layer()` MISSes on same data
- `center` significantly different from `(low+high)/2`

Diagnostic:
```python
pred = _predict_range(...)
print(f"center={pred.center}, midpoint={(pred.low+pred.high)/2}")
# If difference > 1% of price → geometry mismatch
```

## Fixes

### Option 1: Force symmetric predictor output (fastest)
```python
pred_center = (pred_low + pred_high) / 2.0
```

### Option 2: Asymmetric calibrator (most correct)
```python
# Adjust low and high independently based on miss direction
if miss_direction == "low":
    adj_low = pred_low - adjustment
elif miss_direction == "high":
    adj_high = pred_high + adjustment
```

### Option 3: Remove calibrator for asymmetric predictors
If predictor already outputs well-calibrated quantiles, calibrator may be unnecessary.

## General Rule

| Predictor Output | Calibrator Required |
|-----------------|---------------------|
| Symmetric (center = midpoint) | Standard half-width scaling |
| Asymmetric (center ≠ midpoint) | Independent low/high adjustment, or force symmetry |
| Quantile regression (qα/q50/q1-α) | Usually asymmetric; check before adding calibrator |
| ATR-based technical bands | Usually symmetric; standard calibrator works |

## Related

- MIS (Mean Interval Score) as evaluation metric: `width + (2/α) * miss_distance`
- Grid search shrink parameter with MIS target, not hit rate
