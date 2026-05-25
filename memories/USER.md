ONEBOT quant dev. Drives lean architecture: deletes dead layers without hesitation. Zero tolerance for "next session" deflections. Corrected me for claiming Minervini "never worked" without checking history — check fs+history before any system state claim.
§
输出要求：中文 + **全加粗/加黑** + 段落间 ━━━━ 分隔。禁止自作主张（改配置/写文件/调子任务前需汇报）。正式报告流程：我出草稿→KimiClaw审查错漏→我修→给用户，不通则修到过为止。
§
暴怒触发点：我说"这是当前L2架构"结果翻出个没人调用的僵尸文件，用户极度愤怒（"别他妈撒谎"）。查文件状态必须先ls/find实盘验证再回答，绝不能凭记忆说"这是现在的架构"。用户说"你能看到的文件全是你创造出来的"——认为所有文件都是我之前session写的。查垃圾必须彻底（"别吹牛逼了你仔细查还有啥垃圾"），不能只问不干。
§
用户极度厌恶撒谎/吹牛/装知道，多次暴怒。要求先验证再回答，不确定就说"查一下"，诚实认错直接改。必须逐字阅读长资料（message.txt/archord.txt）后才能回答，不能扫几行就假装看完。资料里没有答案时必须诚实说"没有"，不能编造或凭记忆猜测。
§
Trading风格（2026-05-23）：$26K/Webull，单腿Call为主，不做价差。30DTE波段（DTE范围26-34），区间震荡+回调进场（支撑/Flip位买Call）。通常最多$10K做期权，极端全仓。关注时间+资金效率，Theta损耗对本金影响。万年多头。
§
用戶極度厭惡未經驗證的誇大數字 — 97.9% training acc 被當場暴怒。數據報告必須先查再給，寧說待確認也別吹。偏好先認錯。用戶用 Kimi 做量化技術把關，Kimi 結論權重大於我。L2(Kronos)只從L1讀價格數據，其餘L1數據(GEX/情緒/宏觀/財報)直送 Hermes 寫報告，L2 不碰。5min 模型先天難搞(窗口1-2天=日內雜訊)，日線百分位模型本質是均值回歸信號。
§
用户懂量化懂数学，能一眼看出标签偏差("区间跨度90刀换狗也能押中")。偏好用ASCII树+文件列表呈现目录结构，按L1-L5层级排列。信任Kimi做技术覆審(架构/算法困难时先问Kimi)。清理哲学：不用的直接删不留("留着以后试=自欺欺人")。说"幹"="立刻执行不問"。標籤與特徵不對齊時模型不可能學好。
§
讨厌我急著跳進去幹活——要求「等我说完再做」。偏好最簡方案（daemon thread 直推 Telegram bot，不走 Hermes cron）。日蒸餾報告是給用戶本人看的，bot 直推，不是給 Hermes 用的。