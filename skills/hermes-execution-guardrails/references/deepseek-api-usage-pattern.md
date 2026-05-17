# DeepSeek 调用规范 — 2026-05-17

## 快速调用

```python
import os, sys
sys.path.insert(0, '/home/ubuntu/.hermes/skills/onebot-3.0/onebot')

from dotenv import load_dotenv
load_dotenv('/home/ubuntu/.hermes/skills/onebot-3.0/.env')

from quant_core.llm_layers.llm_client import get_llm_client, LLMProvider

client = get_llm_client(LLMProvider.DEEPSEEK_V4)

resp = client.chat(
    messages=[{'role': 'user', 'content': '你的问题'}],
    temperature=0.1,
    max_tokens=4000,
)

if resp.success:
    print(resp.content)
else:
    print('ERROR:', resp.error)
```

## 环境变量

```bash
export DEEPSEEK_API_KEY=sk-899b63e2b0bb4c91b29aeecb7f145146
```

或从 `.env` 加载：
```bash
cd /home/ubuntu/.hermes/skills/onebot-3.0 && source .env
```

## 关键教训

1. **不要说"没有 ds CLI"** — DeepSeek 通过 openai 库调用，不是独立 CLI
2. **回复截断就再问** — 用户要求"继续问直到问对为止"
3. **不要凭记忆断言** — 忘记调用方法时查聊天记录或本文档
4. **temperature 0.1-0.3** — 技术问题用低 temperature
5. **max_tokens 4000** — 代码生成需要足够长度

## 审核工作流

- 用户说"DeepSeek 审核" = 调用 DS 检查代码/方案
- DS 回复不对时，**指出具体问题**（"你改了接口""返回格式不对"），要求重新回答
- "截断就再问一遍" = 循环直到正确，不是试两次就放弃
- DS 三次都不对 → 自己改，但要说明"DS 没给正确方案，我自己改了"
- 不要假装 DS 审核通过了，实际是自己改的

## 错误处理

```python
if not resp.success:
    # 常见错误：API key 未设置、网络超时、token 超限
    print(f'Error: {resp.error}')
    print(f'Latency: {resp.latency_ms}ms')
```
