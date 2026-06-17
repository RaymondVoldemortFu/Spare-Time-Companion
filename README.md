# Spare-Time Companion

面向桌面陪伴场景的云端语音对话 Demo。项目用 FastAPI 承载后端智能能力，用 React + Vite 提供 Web 虚拟客户端，支持登录注册、邀请码、文字对话、语音上传、ASR、LLM Agent 决策、TTS 播报、历史记录与运行日志。

> 真实桌面客户端只负责采集输入、播放音频和展示表情；自然语言理解、上下文管理、长期记录和语音合成都在云端完成。

## 项目亮点

- **语音闭环**：客户端上传音频后，服务端完成 ASR 识别、LLM 回复决策和 TTS 音频合成。
- **自然对话**：支持普通聊天、活动建议、主动触发、反馈、重新生成和上下文连续理解。
- **Agent 记录**：保留每轮 Agent 运行摘要，便于复盘输入来源、工具上下文、最终动作和音频状态。
- **邀请码注册**：邀请码存储在数据库中，带有效期和使用次数限制；首次启动会自动生成默认邀请码。
- **可部署 Demo**：本地默认 SQLite，提供 Dockerfile 与 `docker-compose.yml`，可快速部署为公网演示服务。

## 技术栈

- **后端**：Python 3.12、FastAPI、SQLModel、Alembic、uv
- **前端**：React 19、Vite、TypeScript、lucide-react
- **大模型**：阿里百炼 OpenAI 兼容接口，默认 `qwen3.7-plus`
- **语音能力**：阿里云 DashScope SDK，支持 ASR 与 TTS
- **数据库**：SQLite 默认存储，开发环境开箱即用

## 目录结构

```text
.
├── backend/              # FastAPI 服务端、数据库模型、业务服务和测试
├── frontend/             # React Web 虚拟客户端
├── logs/                 # 应用、LLM、ASR、TTS 分级日志
├── Dockerfile            # 后端镜像构建文件，内置前端 dist 静态资源
├── docker-compose.yml    # 单服务部署编排
├── pyproject.toml        # Python 依赖与测试/格式化配置
└── README.md
```

## 快速开始

### 1. 准备环境变量

复制 `.env.example` 为 `.env`，并填入真实密钥：

```bash
cp .env.example .env
```

`.env` 至少需要包含：

```env
MODEL_NAME=qwen3.7-plus
LLM_API_KEY=replace-with-aliyun-bailian-key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
ALI_API_KEY=replace-with-aliyun-dashscope-key
ASR_MODEL=fun-asr-realtime
VOICE_MODEL=cosyvoice-v3-flash
TTS_VOICE=longanyang
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=Your_Strong_Admin_Password_2026!
SECRET_KEY=replace-with-a-long-random-secret-value
APP_TIMEZONE=Asia/Shanghai
```

公网 Demo 必须使用强管理员密码：至少 14 位，并同时包含大小写字母、数字和符号。`SECRET_KEY` 长度必须不少于 32 位。

### 2. 启动后端

```bash
/opt/homebrew/bin/uv sync
/opt/homebrew/bin/uv run uvicorn app.main:app --app-dir backend --reload
```

后端默认监听 `http://127.0.0.1:8000`，OpenAPI 文档地址为 `http://127.0.0.1:8000/docs`。

### 3. 启动前端

```bash
cd frontend
/opt/homebrew/bin/npm install
/opt/homebrew/bin/npm run dev
```

访问 `http://127.0.0.1:5173`，使用 `.env` 中的管理员账号登录，或使用邀请码注册普通用户。

## 邀请码

邀请码不配置在 `.env` 中，而是由服务在数据库里维护。首次启动时，如果数据库中没有可用邀请码，系统会自动生成一个 72 小时有效的邀请码。

查看当前可用邀请码：

```bash
/opt/homebrew/bin/uv run python backend/scripts/list_invites.py
```

管理员登录后也可以通过接口创建邀请码。

## 外部服务检查

服务启动时默认会检查 LLM 和 TTS。检查失败会阻止后端启动，避免 Demo 在关键能力不可用时继续运行。ASR 需要真实音频输入，因此会在音频上传接口中验证。

手动检查外部服务：

```bash
/opt/homebrew/bin/uv run python backend/scripts/check_external_services.py
```

如需临时关闭启动检查，可在 `.env` 中设置：

```env
STARTUP_EXTERNAL_CHECKS=false
```

## Docker 部署

Docker 镜像会读取已构建的 `frontend/dist`，因此需要先构建前端：

```bash
cd frontend
/opt/homebrew/bin/npm install
/opt/homebrew/bin/npm run build
cd ..
docker compose up --build
```

`docker-compose.yml` 会将容器内 `8000` 映射到主机 `80`，并挂载：

- `./data:/app/data`：保存 SQLite 数据库
- `./logs:/app/logs`：保存运行日志

## 主要 API

完整接口文档见 `/docs`。常用接口包括：

- `POST /api/v1/auth/login`：登录
- `POST /api/v1/auth/register`：邀请码注册
- `POST /api/v1/auth/invites`：创建邀请码
- `POST /api/v1/companion/turn/text`：文字对话
- `POST /api/v1/companion/turn/audio`：音频对话
- `POST /api/v1/companion/turn/trigger`：主动触发回应
- `POST /api/v1/companion/feedback`：提交反馈
- `GET /api/v1/companion/history`：查看对话历史
- `GET /api/v1/companion/agent-runs`：查看 Agent 运行记录

## 日志

服务启动后会在项目根目录 `logs/` 下写入分级日志：

- `logs/app.log`：应用启动、请求和通用日志
- `logs/llm.log`：LLM healthcheck 与对话决策请求
- `logs/asr.log`：ASR 音频识别请求
- `logs/tts.log`：TTS 语音合成请求

日志 message 使用 JSON 字段，包含事件名、模型名、耗时、输入/输出长度、成功状态或错误原因；不会记录 API Key。

## 开发命令

```bash
# 后端测试
/opt/homebrew/bin/uv run pytest

# 后端 lint
/opt/homebrew/bin/uv run ruff check .

# 前端构建
cd frontend
/opt/homebrew/bin/npm run build
```

## 常见问题

**启动时报管理员密码错误**

检查 `.env` 中的 `ADMIN_PASSWORD` 是否足够强，不能使用默认弱口令。

**启动时报 SECRET_KEY 错误**

检查 `SECRET_KEY` 是否已替换为至少 32 位的随机字符串。

**后端启动时外部服务检查失败**

确认 `LLM_API_KEY`、`LLM_BASE_URL`、`ALI_API_KEY`、`VOICE_MODEL`、`TTS_VOICE` 配置正确，并先运行 `check_external_services.py` 定位失败项。

**Docker 启动后前端页面不存在**

确认已经执行过 `npm run build`，并且 `frontend/dist` 存在。Dockerfile 会把该目录复制进镜像。

