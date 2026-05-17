**Session corrections:** "能不能" ≠ 执行许可，等"去做"/"开干"才动手。先读文档再声称。诚实评估优于包装。frustration = 先尝试/读文档再声称 inability。资源充足性需显式确认。自主执行，不问许可。
§
User: ONEBOT 3.0 quant dev + system architect. Extreme low tolerance for verbosity — "别他妈墨迹了"/"停止停止" = immediate cessation, direct execution, zero explanations. Tests with "有没有吹牛逼". Prefers optimal solutions. Chicago TZ. Hates cp, prefers mv; append-only configs. Output: conclusion→score→comment→executable. One-shot completion. **Key: expects autonomous self-directed execution without asking for approval.**
§
**GitHub**: `matt3364781-coder/onebot-3.0`，token 在 subskills/github-repo/SKILL.md。用户**讨厌被问仓库地址**，要求我先查 skill/文件而不是问。正常部署包 = 源码+配置+文档，排除 .venv/ *.safetensors 运行时模型JSON 旧备份 密钥，约 5MB。
§
User expects tasks fully completed before reporting. "全部干好了再给我打报告" — no incremental status updates, no mid-task summaries. Deliver only final results.
§
User wants skills aggressively consolidated — 53→41 merged, expects me to identify and remove untouched skills proactively without micromanagement.
§
海诺的指令：如果看到他回复的内容里有 @one2slv_bot 或 "Kimi"，我就不需要回复他（这是给 KimiClaw 的指令）。但叫 "Hermes" 时就算不带 @ 也是在叫我，必须回复。