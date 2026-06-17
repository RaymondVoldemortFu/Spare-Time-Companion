# Spare-Time Companion Demo

云端语音陪伴 demo：FastAPI 后端、React Web 虚拟客户端、SQLite 默认数据库、uv 包管理、Docker 部署文件。

## 技术栈

- Backend: Python 3.12, FastAPI, SQLModel, uv
- Frontend: React, Vite, TypeScript
- LLM: 阿里百炼 OpenAI 兼容接口，默认 `qwen3.7-plus`
- ASR/TTS: 阿里云 DashScope SDK，默认从 `.env` 读取 `ASR_MODEL`、`VOICE_MODEL`

## 必要环境变量

`.env` 至少需要：

```env
MODEL_NAME=qwen3.7-plus
LLM_API_KEY=...
LLM_BASE_URL=...
ALI_API_KEY=...
ASR_MODEL=fun-asr-realtime
VOICE_MODEL=cosyvoice-v3-plus
TTS_VOICE=longxiaochun
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=ReplaceWith_StrongPassword_2026!
SECRET_KEY=replace-for-public-demo
```

生产启动默认会检查 LLM 和 TTS。不可用时服务器拒绝启动。ASR 在真实音频上传时验证，因为它需要用户音频输入。
公网 demo 必须使用强管理员密码：至少 14 位，并包含大小写字母、数字和符号；弱密码会阻止服务器启动。

邀请码不再配置在 `.env`。服务会在数据库中维护带有效期的邀请码；首次启动如果没有可用邀请码，会自动生成一个 72 小时有效的邀请码。

查看当前可用邀请码：

```bash
/opt/homebrew/bin/uv run python backend/scripts/list_invites.py
```

## 本地开发

```bash
/opt/homebrew/bin/uv sync
/opt/homebrew/bin/uv run uvicorn app.main:app --app-dir backend --reload
cd frontend
/opt/homebrew/bin/npm install
/opt/homebrew/bin/npm run dev
```

访问 `http://127.0.0.1:5173`。默认管理员账号来自 `.env`。

## 构建部署

```bash
cd frontend
/opt/homebrew/bin/npm install
/opt/homebrew/bin/npm run build
cd ..
docker compose up --build
```

本项目提供 Docker 文件，但本机开发不需要运行 Docker。

## API

主要接口：

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/invites`
- `POST /api/v1/companion/turn/text`
- `POST /api/v1/companion/turn/audio`
- `POST /api/v1/companion/turn/trigger`
- `POST /api/v1/companion/feedback`
- `GET /api/v1/companion/history`
- `GET /api/v1/companion/agent-runs`

OpenAPI 文档在 `/docs`。

## 日志

服务启动后会在项目根目录 `logs/` 下写入分级日志：

- `logs/app.log`：应用启动、请求和通用日志
- `logs/llm.log`：每次 LLM healthcheck 与对话决策请求
- `logs/asr.log`：每次 ASR 音频识别请求
- `logs/tts.log`：每次 TTS 语音合成请求

日志使用 JSON 字段作为 message，包含事件名、模型名、耗时、输入/输出长度、成功或错误原因；不会记录 API Key。

手动检查外部服务：

```bash
/opt/homebrew/bin/uv run python backend/scripts/check_external_services.py
```
