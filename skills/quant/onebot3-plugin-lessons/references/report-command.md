# /report 命令 — Plugin Command Registration Pattern

**Created:** 2026-05-24
**Updated:** 2026-05-24 (v2 — 格式化输出 + GEX 对齐 + 解码器方向)

## Registration

In `onebot3/__init__.py` → `register(ctx)` alongside `/forgetless`:

```python
ctx.register_command(
    name="report",
    handler=_report_handler,
    description="拉L1行情+L2预测数据，我出报告",
)
```

## Handler Pattern (v2)

L2 部分不再 dump key-value pairs，改为格式化输出：

```python
lines.append("📈 L2 Kronos 预测")
kronos = get_kronos_prediction()
if kronos and kronos.get("status") == "ok":
    dir_map = {1: "CALL 🔵", 0: "NEUTRAL ⚪", -1: "PUT 🔴"}
    d = dir_map.get(kronos.get("direction", 0), "?")
    lines.append(f"  方向: {d} 置信度={kronos.get('confidence', 0):.0%}")
    lines.append(f"  分歧度: {['一致','轻度分歧','严重分歧'][kronos.get('agreement', 3)-1]}")
    lines.append(f"  分类器: {kronos.get('path_type', '?')} zone={kronos.get('zone', '?')}")
    lines.append(f"  解码器: {kronos.get('decoder_summary', '?')}")
    gex_a = "✅" if kronos.get("gex_aligned") else "⚠️"
    lines.append(f"  GEX: {gex_a} net={kronos.get('gex_net', 0):,.0f} regime={kronos.get('gex_regime', '?')}")
```

输出示例：
```
📈 L2 Kronos 预测
  方向: CALL 🔵 置信度=85%
  分歧度: 一致
  分类器: CALL zone=0
  解码器: 3C/1N/1P
  GEX: ✅ net=450,000,000 regime=positive
```

## 字段说明

| 字段 | 含义 | 值域 |
|------|------|------|
| `direction` | 最终方向 | 1/0/-1 |
| `confidence` | 置信度 (GEX对齐时+0.15) | 0.0-0.95 |
| `agreement` | 分歧度 | 1(一致)/2(轻度)/3(严重) |
| `decoder_summary` | 解码器方向投票 | "3C/1N/1P" |
| `gex_aligned` | GEX 与方向一致 | True/False |
| `gex_net` | GEX 净额 | int |

## Return Flow

- Returns formatted data block → Telegram reply
- User sees data → says "出报告" → I write the analysis report
- No temp file needed

## Query functions used

| Function | Source |
|----------|--------|
| `get_current_snapshot()` | `__init__.py` → `anchoring.db_manager.DBManager` |
| `get_gex_levels()` | `__init__.py` → wraps snapshot GEX dict |
| `get_indicators()` | `__init__.py` → wraps snapshot indicators dict |
| `get_sentiment()` | `__init__.py` → wraps snapshot sentiment dict |
| `get_macro_events(3)` | `__init__.py` → wraps snapshot macro list |
| `get_earnings(3)` | `__init__.py` → wraps snapshot earnings list |
| `get_kronos_prediction()` | `__init__.py` → `predict_from_anchoring(snap)` |
