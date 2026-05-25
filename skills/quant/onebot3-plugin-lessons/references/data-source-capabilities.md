# 数据源 5min K 线能力对照

> 实战验证（2026-05-24），SPY 5min K 线

## YFinance

| 特性 | 值 |
|------|-----|
| 5min 可回溯 | **最多 60 自然天**（~55 交易日） |
| 1h / 1d | 多年 |
| 分片拼接 | ❌ 不可行——Yahoo 后端没存，不是分片大小的问题 |
| 实测 | 2026-04-01 → 2886 bars ✅ / 2026-03-01 → empty ❌ |
| 越界返回 | 空 DataFrame，不报错不警告 |

**关键**：Yahoo 5min 数据**从当前日期倒推 60 天**，不是从切片 start 日期算。所以 `start=2026-04-01` 返回了 4月+5月所有数据（到 5/22 最新），而不是只返回 4月。

**"分月拼一年"不成立。** 不是分片策略的问题，是 Yahoo 后端物理上没存超过 60 天的 5min 数据。

## Tradier Time & Sales

| 特性 | 值 |
|------|-----|
| 5min 可回溯 | **~7-10 交易日** |
| 返回格式 | OHLCV + VWAP，标准 JSON |
| 身份验证 | Bearer token（`api_client.py` 里已有 `o6fWRfSJw3tAlZXPxgS4wRW7hcX8`） |
| 端点 | `GET /v1/markets/timesales?symbol=SPY&interval=5min&start=...&end=...&session_filter=all` |
| 参数 | `interval`: 1min / 5min / 15min |
| 其他 | 跟期權全鏈同一來源，數據一致性更好 |

## 用户提供的 5min 数据（2026-05-24）

用户拿到的 **spy_5min_1year.csv**，放在 `kronos/data/`：

| 特性 | 值 |
|------|-----|
| 记录数 | **47,576 bars** |
| 时间范围 | 2025-05-27 → 2026-05-23（~1 年） |
| 覆盖 | 全天 24h（UTC 時區，含 pre/after-hours） |
| 列 | timestamp, open, high, low, close, volume, vwap, transactions |
| 来源 | 用户提供 |
| 文件 | `~/.hermes/plugins/onebot3/kronos/data/spy_5min_1year.csv` |
| 状态 | ✅ 已训练（2026-05-24, stride=5, 9,504 samples, Test Acc=60.4%） |

**训练结果：** 47,576 bars 训出的 LogisticRegression 只有 60.4% Test Acc，低于 55天模型的 70.5%。原因是线性模型无法跨市场阶段保持标签定义一致性（详见 `参考文献中的 linear-model-training-insights.md`）。

## Polygon.io（2026-05-24 新增）

用户提供的 Polygon API key：`pavJHKDnT7vBA8kXH55_0HdsKNCpZYPg`

| 特性 | 值 |
|------|-----|
| 5min 历史 | ✅ **全量**（分页，每页 ~1000 bars） |
| 分页方式 | 返回 `next_url`，追加 `&apiKey=KEY` 继续下一页 |
| 实测范围 | 至少 2 年（5min 2yr → 1192 bars page1） |
| 日K 1年 | ✅ 250 bars，一次性返回 |
| Previous Close | ✅ |
| 即时报价 | ❌ 403 Forbidden（此 key 无美国股票即时权限） |
| 期权即时 | ❌ 403（获取期权链失败） |
| 期权历史 | ⚠️ DELAYED（15分钟延迟） |
| 实时 | ❌ 不是实时（至少 15 分钟延迟） |
| Rate Limit | ⚠️ ~5 次/分钟（免费等第） |
| Timestamps | UTC（毫秒 epoch），需转换成 ET 分析 |

**端点清单（已验证）：**
- 聚合数据（bars）：`/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{from}/{to}`
- 分页：`data.next_url + '&apiKey=KEY'`
- 期权历史合約：`/v2/aggs/ticker/O:SPY{exp}{type}{strike}/range/...`
- Previous Close：`/v2/aggs/ticker/{symbol}/prev`
- Ticker details：`/v3/reference/tickers/{symbol}`

**分頁實測（2026-05-24）：**
- 5min 30天範圍 → 4 頁完成（每頁 ~1000 bars），共 4,030 bars
- 5min 60天範圍 → 需 ~8 頁，完整跟蹤 next_url 到 `null` 為止
- 每頁間隔 3.5 秒可避免 Rate Limit（free tier 約 5 req/min）
- 2.5 秒間隔會觸發 429

**用途建議：** 適合批量下載歷史 5min 做訓練集（需處理分頁），但不適合替代 Tradier 跑實時 L1 採集。

**教訓：** 拿到 API key 先逐個端點測，返回 403/429 分別對應不同限制，不要假設。分頁標準模式：`data.next_url + '&apiKey=KEY'`。不要一次測太多端點連續打——等 30 秒讓 rate limit 重置。

## 实际训练数据来源建议

| 数据 | 来源 | 覆盖深度 | 用途 |
|------|------|----------|------|
| 5min K 线 | YFinance | ~60 天 / ~4600 bars | Kronos 训练主力 |
| 5min K 线 | 用户提供 CSV | ~1 年 / 47,576 bars | 长期训练（需调整过滤） |
| 最新的 5min | Tradier | ~10 天 | 最新数据校验，避免 yfinance 延迟 |
| 1h K 线 | YFinance / CSV | 多年 | 长期趋势验证, Kronos 跨时间尺度 |
| 日 K 线 | YFinance | 1994~至今 | 区間定義、支撐阻力計算 |

## 教训

- **用户说的数据方案要先验证，不要直接信。** Yahoo 5min "分月拼一年" 听起来合理但 Yahoo 后端不支持
- **先查本地 API client 再搜網絡。** 這項目 `api_client.py` 裡面已經有 Tradier + YFinance + Finnhub 三套，大部分問題代碼就能回答
- **測試永遠是最好的文檔。** 一個 curl 就驗證了 Tradier 5min 能不能用，比看半天文檔快
- **用戶提供的數據要先檢查時間範圍和粒度**。24h 覆蓋的 5min 數據跟 yfinance 的 9:30-16:00 不同，處理方式不同
