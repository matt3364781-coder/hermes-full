---
name: hermes-oauth-setup
description: OAuth 凭据添加 — 本地和远程服务器流程，含 --manual-paste 设备码模式 + PTY 非交互终端处理
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [hermes, oauth, configuration, proxy, remote-server]
    related_skills: [hermes-execution-guardrails]
---

# Hermes OAuth 认证设置

## 概述

为 Hermes 的各种 provider 添加 OAuth 凭据，用于 proxy 转发 API 调用。

支持的 provider:
- `xai-oauth` — xAI Grok（需 SuperGrok 订阅）
- `nous` — Nous Portal
- `openai-codex` — OpenAI Codex

## 核心命令

```bash
hermes auth add <provider> --type oauth [options]
```

### 关键参数

| 参数 | 说明 |
|------|------|
| `--type oauth` | **必须指定** |
| `--no-browser` | 不自动打开浏览器（远程服务器） |
| `--manual-paste` | **远程服务器必备** — 跳过回环回调，改用手动粘贴 |
| `--label LABEL` | 可选标签，区分多个凭据 |
| `--scope SCOPE` | OAuth scope 覆盖（默认足够） |

## 远程服务器流程（--manual-paste）

适用场景：腾讯 Lighthouse、GCP Cloud Shell、GitHub Codespaces、EC2 Instance Connect 等不可达 `127.0.0.1` 回环地址的远程环境。

### 标准流程

**Step 1** — 运行命令：
```bash
hermes auth add xai-oauth --type oauth --manual-paste
```

**Step 2** — 命令输出类似：
```
Open this URL to authorize Hermes with xAI:
https://auth.x.ai/oauth2/authorize?response_type=code&...

─── Manual callback paste ─────────────────────────────────────
After approving in your browser, your browser will try to load
  http://127.0.0.1:56121/callback
which fails (the loopback listener is on this remote machine,
not on your laptop) — that is expected.  Copy the FULL URL
from your browser's address bar of that failed page and paste
it below.
───────────────────────────────────────────────────────────────
Callback URL:
```

**Step 3** — 把授权 URL 发给用户（手机/其他电脑浏览器），用户登录 SuperGrok 授权。

**Step 4** — 授权后浏览器跳转到 `http://127.0.0.1:56121/callback?code=...`（打不开是正常的），**把完整 URL 复制回来**。

**Step 5** — 粘贴回调 URL 到终端，按回车。

### 非交互终端处理（⚠️ 关键坑）

**问题**：`--manual-paste` 需要 stdin 交互输入。Hermes Agent 的 `terminal()` 工具运行后无法直接接受键盘输入。命令会在约 60 秒内 timeout，报 `state mismatch`。

**正确做法**：使用 PTY 后台进程 + process 工具。

```python
# 1. 启动 PTY 后台进程
proc = terminal(background=True, pty=True,
    command="hermes auth add xai-oauth --type oauth --manual-paste")

# 2. 读取输出获取授权 URL
url = process.log(session_id)["output"]  # 提取 URL

# 3. 用户授权后，把回调 URL 提交到进程
process.submit(session_id, "http://127.0.0.1:...?code=...&state=...")
```

**或者**：通过 `subprocess.run()` 封装：
```python
result = subprocess.run(
    ['hermes', 'auth', 'add', 'xai-oauth', '--type', 'oauth', '--manual-paste'],
    capture_output=True, text=True, timeout=30
)
# 提取 URL 给用户
url = result.stdout
# ... 用户授权后 ...
# 再用同一个进程的 stdin 输入，或者用 pexpect
```

**注意 1**：每次运行都生成新的 `state` + `code_challenge`。之前输出的 URL 失效，不能复用。

**注意 2**：`hermes login --provider xai-oauth` 已被移除（v0.14），全部改用 `hermes auth add`。

### xAI API Key — 错误信息诊断

**情况 1**: `"Incorrect API key provided: xa***o8"`
- **诊断**: Key 无效/过期/被吊销
- **处理**: 生成新 key 再试
- **也可能是**：凭据池里有**多个 key**，当前激活的是旧的那个

**情况 2**: `"team doesn't have any credits or licenses yet"`
- **诊断**: Key 认证通过了，但绑定的 Team 账户没有 API 额度
- **处理**: 确认 key 来自个人 SuperGrok 账号（不是新建的 Team）
- **地址栏检查**: console.x.ai 左上角显示的是 Personal 还是 Team 名称

**情况 3**: `"Your newly created team doesn't have any credits or licenses yet"`
- **诊断**: 和情况 2 同理，但明确提示是新创建的 Team
- **处理**: 需在 https://console.x.ai 购买 credits，或用个人账号重新注册/生成 key

### 凭据管理注意事项

**多个凭据共存问题**：`hermes auth list` 查看所有凭据，带 `←` 箭头的是**当前激活的凭据**。添加新 key 后，旧 key 仍保留并可能被优先使用。

```bash
# 查看所有凭据，注意 ← 标记
hermes auth list xai-oauth
# 输出示例：
#   #1  team-key             api_key manual ←    ← 这个是激活的
#   #2  supergrok            api_key manual       ← 这个虽然是新的但没激活
```

**删除旧凭据**：
```bash
hermes auth remove xai-oauth <label>   # 按标签
hermes auth remove xai-oauth 1         # 按索引
```

**修改凭据后必须重启 proxy**——proxy 启动时加载凭据池，添加/删除凭据后不重启仍用旧凭据。
```bash
# 先杀掉旧 proxy 进程
# 再重新启动
hermes proxy start --provider xai --port 8645
```

## 验证

```bash
# 查看凭据状态
hermes auth list
hermes auth status xai-oauth

# 启动 proxy 测试
hermes proxy providers       # 应该看到 xai
hermes proxy start --provider xai --port 8645

# 用 curl 验证 API 转发
curl http://localhost:8645/v1/models \
  -H "Content-Type: application/json"
```

## 登出/重置

```bash
# 清除 xAI 凭据
hermes auth remove xai-oauth     # 按 ID 删除
hermes auth logout xai-oauth     # 登出整个 provider
hermes auth reset xai-oauth      # 重置耗尽状态

# 重新添加
hermes auth add xai-oauth --type oauth --manual-paste
```

## 故障排查

### state mismatch
**原因**：命令 timeout 后重跑，新 URL 已换 state，你用的是旧 URL 授权的。
**修复**：每次必须用**本次输出**的 URL 去授权，不能用历史 URL。

### No available xAI OAuth credentials
**原因**：凭据过期、API 调用限额耗尽、或从未添加过。
**修复**：`hermes auth reset xai-oauth` 或重新 `hermes auth add ...`。

### 回调 URL 打不开
**这不是 bug** — 回调监听器在远程服务器上，本地浏览器自然连不上。`--manual-paste` 模式就是解决这个问题的：把打不开的 URL 粘贴回来。

### Connection refused on proxy port
**原因**：proxy 没运行或绑定到 127.0.0.1 但 curl 从外部访问。
**修复**：`hermes proxy start --provider xai --port 8645 --host 0.0.0.0`

### xAI OAuth 回退到 Grok Build 设备码（远程服务器致命坑）
**现象**：用户打开授权 URL → 点 Authorize → xAI 检测 `redirect_uri=http://127.0.0.1:56121/callback` 不可达（远程服务器上没有浏览器）→ 页面显示"无法建立连接 / 请将下面的代码复制并粘贴到 Grok Build 中"→ 流程卡死。
**原因**：xAI 的 OAuth 服务器在 redirect_uri 不可达时，会 fallback 到 Grok 桌面应用的 device code 流程，而不是 web 浏览器回调。`--manual-paste` 模式设计上假设你手动粘贴回调 URL，但 xAI 根本不给你回调 URL。
**影响断言**：**xAI OAuth 的 `--manual-paste` 模式在远程服务器上实际不可用**。非 xAI 的 provider（我们尚未测试）可能仍可用。
**替代方案**：直接使用 API Key（见下文"API Key 替代方案"）。

### xAI API Key — Team 账号无额度
**现象**：`hermes auth add xai-oauth --type api-key --api-key "xxx" --label name` 添加成功，`hermes proxy start --provider xai` 启动成功，但 curl 测试返回：`"The caller does not have permission to execute the specified operation" / "Your newly created team doesn't have any credits or licenses yet."`
**原因**：xAI 控制台生成的 API Key 可能是 Team 账号下的，Team 账号默认没有 credits/licenses——即使个人已有 SuperGrok 订阅。
**解决**：确保 API Key 来自**个人 SuperGrok 账号**，不是新建的 Team。个人账号的 SuperGrok 订阅才有 API 额度。如果控制台自动创建了 Team，需要在控制台购买 credits，或用个人账号重新注册/登录生成 key。

## API Key 替代方案（OAuth 失灵时的 Plan B）

当 OAuth 流程无法完成时（远程服务器、xAI 回退到 Grok Build 等），可以直接用 API Key：

```bash
# 添加 API Key 凭据
hermes auth add xai-oauth --type api-key --api-key "你的key" --label my-supergrok

# 验证
hermes auth list                     # 确认凭据已添加
hermes proxy start --provider xai --port 8645   # 启动 proxy
curl http://127.0.0.1:8645/v1/models            # 测试连通性
```

**注意事项**：
- API Key 必须来自个人 SuperGrok 账号，不是 Team 账号
- 如果提示 team 无 credits，去 https://console.x.ai 确认登录的是个人账号
- 用 `--label` 区分多个凭据（如 `supergrok-personal`, `team-account`）

### 删除凭据
```bash
hermes auth remove xai-oauth <label>   # 按标签删除
hermes auth remove xai-oauth 1         # 按索引删除
```

## 参考

- `hermes-execution-guardrails` — 执行行为硬约束
- xAI OAuth 文档：https://auth.x.ai/
- xAI Console (API Keys): https://console.x.ai
- Hermes Gateway 文档：内置 `hermes proxy --help`
