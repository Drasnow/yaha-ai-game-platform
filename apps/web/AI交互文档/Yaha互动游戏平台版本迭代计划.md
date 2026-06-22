# Yaha互动游戏平台版本迭代计划

> 来源文档：`yaha游戏平台开发任务.md`、`yaha游戏平台需求分析文档.md`、`Yaha互动游戏平台技术方案.md`  
> 目标：按版本逐步从零实现可运行 Demo，最终满足“登录/注册 → 创意生成 → 游戏发布 → 浏览游玩”的完整 MVP 闭环。  
> 推荐项目目录：`D:\leibo\yaha-ai-game-platform`  
> 终端环境：Windows + Git Bash。下面命令优先使用 POSIX 写法，例如 `cd /d/leibo/yaha-ai-game-platform`。

---

## 0. 总体迭代策略

### 0.1 版本划分

> **注意：** 当前实现已全部完成所有 MVP 版本（V0-V4），V5 增强功能部分也已实现（LangGraph、SSE、LangSmith）。

| 版本 | 核心目标 | 实际状态 |
| --- | --- | --- |
| V0 | 环境、工具链、项目骨架、基础启动 | ✅ 已完成 |
| V1 | Web 基础页面、Auth、数据库 CRUD、Home 列表 | ✅ 已完成 |
| V2 | MinIO 对象存储、远端游戏产物、Play 动态加载 | ✅ 已完成 |
| V3 | Create 页面、FastAPI Agent、生成任务、发布闭环 | ✅ 已完成（含 LangGraph） |
| V4 | 交付文档、测试验证、演示准备、最终验收 | ✅ 已完成 |
| V5 | MVP 外增强：OAuth、搜索、点赞、LangGraph、SSE、LangSmith | ✅ 已完成（部分超出计划） |

### 0.2 最小验收闭环

当前已全部实现：

1. ✅ 用户可以注册、登录、退出（Cookie Session + Session 表）
2. ✅ 登录后可以进入 Create 页面
3. ✅ 用户输入创意并上传至少一种素材
4. ✅ 系统创建 generation task，并展示 Agent 步骤日志（SSE 流式推送）
5. ✅ FastAPI/LangGraph Agent 生成游戏文件：`index.html`、`style.css`、`game.js`、`manifest.json`
6. ✅ 生成产物上传到 MinIO/S3 兼容对象存储
7. ✅ 数据库写入 `games`、`game_versions`、`generation_tasks`、`agent_logs`
8. ✅ 用户预览并发布游戏
9. ✅ Home 页面展示已发布游戏（需执行 seed 写入测试数据）
10. ✅ Play 页面根据数据库 meta 动态加载对象存储中的远端游戏文件

## 0.3 当前实际实现总览

> 以下为截至当前的完整实现状态对照，标注了各版本实际完成的文件路径。

### 前端（apps/web）

| 页面/路由 | 路径 | 状态 |
| --- | --- | --- |
| 首页 | `app/page.tsx` | ✅ |
| 登录 | `app/login/page.tsx` | ✅ |
| 注册 | `app/register/page.tsx` | ✅ |
| Create | `app/create/page.tsx` + `components/create-game-form.tsx` | ✅ |
| Play | `app/play/[gameId]/page.tsx` + `play-client.tsx` | ✅ |
| 我的游戏 | `app/games/page.tsx` | ✅ |
| 导航栏 | `components/site-header.tsx` | ✅ |

| API 路由 | 路径 | 状态 |
| --- | --- | --- |
| Auth | `app/api/v1/auth/[...auth]/route.ts` | ✅ |
| 游戏列表/创建 | `app/api/v1/games/route.ts` | ✅ |
| 游戏详情/更新 | `app/api/v1/games/[gameId]/route.ts` | ✅ |
| 发布 | `app/api/v1/games/[gameId]/publish/route.ts` | ✅ |
| Play meta | `app/api/v1/games/[gameId]/play-meta/route.ts` | ✅ |
| 素材上传 | `app/api/v1/assets/upload/route.ts` | ✅ |
| 任务创建/列表 | `app/api/v1/generation-tasks/route.ts` | ✅ |
| 任务详情 | `app/api/v1/generation-tasks/[taskId]/route.ts` | ✅ |
| 任务日志 | `app/api/v1/generation-tasks/[taskId]/logs/route.ts` | ✅ |
| 任务 SSE | `app/api/v1/generation-tasks/[taskId]/stream/route.ts` | ✅（新增）|
| Play 事件 | `app/api/v1/play-events/route.ts` | ✅ |

| 库文件 | 作用 | 状态 |
| --- | --- | --- |
| `lib/auth.ts` | Cookie Session 工具 | ✅ |
| `lib/prisma.ts` | Prisma 客户端 | ✅ |
| `lib/storage.ts` | MinIO 上传封装 | ✅ |
| `lib/agent-client.ts` | Agent 调用（SSE + fallback） | ✅（超出计划）|
| `lib/generation-tasks.ts` | 任务序列化/工具函数 | ✅ |
| `lib/generation-task-runner.ts` | 任务执行器 | ✅ |
| `lib/assets.ts` | 素材工具函数 | ✅ |

### Agent 服务（services/agent-service）

| 文件/目录 | 作用 | 状态 |
| --- | --- | --- |
| `app/main.py` | FastAPI（/generate + /generate/stream） | ✅（超出计划）|
| `app/core/config.py` | 配置（含 LangSmith） | ✅（超出计划）|
| `app/schemas/generate.py` | Pydantic 请求/响应 | ✅ |
| `app/agent/state.py` | LangGraph State 定义 | ✅（超出计划）|
| `app/agent/graph.py` | LangGraph StateGraph 定义 | ✅（超出计划）|
| `app/agent/edges.py` | 边路由逻辑 | ✅（超出计划）|
| `app/agent/schemas.py` | Agent 间 Pydantic 数据类 | ✅（超出计划）|
| `app/agent/validator.py` | 产物安全校验 | ✅ |
| `app/agent/asset_content.py` | 素材内容抓取 | ✅（超出计划）|
| `app/agent/nodes/supervisor_agent.py` | SupervisorAgent | ✅（超出计划）|
| `app/agent/nodes/vision_agent.py` | VisionAgent | ✅（超出计划）|
| `app/agent/nodes/narrative_agent.py` | NarrativeAgent | ✅（超出计划）|
| `app/agent/nodes/gameplay_agent.py` | GameplayAgent | ✅（超出计划）|
| `app/agent/nodes/code_generator_node.py` | 代码生成节点 | ✅（超出计划）|
| `app/agent/nodes/validator_node.py` | 校验节点 | ✅（超出计划）|
| `app/agent/nodes/upload_workflow.py` | 上传工作流 | ✅（超出计划）|
| `app/agent/nodes/template_workflow.py` | 模板化生成 | ✅（超出计划）|
| `app/agent/nodes/retry_workflow.py` | 重试工作流 | ✅（超出计划）|
| `app/agent/nodes/synthesis_agent.py` | 整合 Agent | ✅（超出计划）|
| `app/agent/nodes/fanout_node.py` | Specialist 并行节点 | ✅（超出计划）|
| `app/llm/client.py` | LLM 客户端 | ✅（超出计划）|
| `app/llm/providers.py` | 模型提供商 | ✅（超出计划）|
| `app/llm/exceptions.py` | 异常类 | ✅（超出计划）|
| `langgraph.json` | LangGraph 配置 | ✅（超出计划）|
| `tests/test_validator.py` | 校验测试 | ✅ |
| `tests/test_llm_client.py` | LLM 客户端测试 | ✅（超出计划）|

---

# V0：开发环境和项目骨架

## V0.1 版本目标

先把所有必须工具、目录、依赖和基础服务准备好，确保项目能启动一个空页面、一个 FastAPI 健康检查、PostgreSQL 和 MinIO。

本版本不追求完整业务，只追求“机器环境可用 + 项目结构正确 + 服务能跑”。

## V0.2 需要准备的技术栈

| 部分 | 技术 |
| --- | --- |
| 前端/主应用 | Node.js LTS、pnpm、Next.js、React、TypeScript |
| UI | Tailwind CSS、shadcn/ui |
| 业务 API | Next.js Route Handlers / Server Actions |
| 数据库 | PostgreSQL |
| ORM | Prisma |
| 对象存储 | MinIO |
| Agent 服务 | Python 3.11+、FastAPI、Pydantic、uv 或 venv |
| 容器 | Docker Desktop、Docker Compose |
| 版本管理 | Git、GitHub |
| 测试 | pytest、httpx、Vitest 或 Playwright |

## V0.3 检查本机工具是否安装

在 Git Bash 中执行：

```bash
node -v
npm -v
pnpm -v
python --version
uv --version
docker --version
docker compose version
git --version
```

期望：

- `node -v` 建议为 `v20.x` 或更新 LTS。
- `pnpm -v` 能输出版本号。
- `python --version` 建议为 `Python 3.11+`。
- `docker compose version` 能正常输出版本。
- 如果某个命令不存在，按下面安装步骤处理。

## V0.4 安装 Node.js

推荐安装 Node.js LTS：

1. 打开 `https://nodejs.org/`。
2. 下载 LTS 版本安装包。
3. 安装后重新打开 Git Bash。
4. 验证：

```bash
node -v
npm -v
```

## V0.5 安装 pnpm

```bash
npm install -g pnpm
pnpm -v
```

如果 `pnpm` 命令找不到，关闭并重新打开 Git Bash，再执行：

```bash
pnpm -v
```

## V0.6 安装 Python 和 uv

检查 Python：

```bash
python --version
```

如果没有 Python 3.11+，建议安装：

1. 打开 `https://www.python.org/downloads/`。
2. 下载 Python 3.11 或 3.12。
3. 安装时勾选 `Add Python to PATH`。
4. 重新打开 Git Bash 验证。

安装 uv：

```bash
pip install uv
uv --version
```

如果 `pip install uv` 失败，也可以先用传统 venv，后续命令替换为 `python -m venv .venv`。

## V0.7 安装 Docker Desktop

1. 打开 `https://www.docker.com/products/docker-desktop/`。
2. 安装 Docker Desktop。
3. 启动 Docker Desktop。
4. 验证：

```bash
docker --version
docker compose version
docker ps
```

如果 `docker ps` 报错，通常是 Docker Desktop 没启动。

## V0.8 创建项目目录

```bash
cd /d/leibo
mkdir -p yaha-ai-game-platform
cd yaha-ai-game-platform
git init
```

建议第一次提交：

```bash
git add .
git commit -m "chore: initialize repository"
```

如果 Git 提示没有用户名邮箱，设置：

```bash
git config --global user.name "你的名字"
git config --global user.email "你的邮箱"
```

## V0.9 创建 Next.js 主应用

```bash
cd /d/leibo/yaha-ai-game-platform
mkdir -p apps
cd apps
pnpm create next-app@latest web \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir false \
  --import-alias "@/*"
```

进入 Web 应用并启动：

```bash
cd /d/leibo/yaha-ai-game-platform/apps/web
pnpm dev
```

浏览器打开：

```text
http://127.0.0.1:4000
```

验收：能看到 Next.js 默认页面。

如果启动时报 `listen EACCES: permission denied 0.0.0.0:3001`，通常是 Windows 不允许当前进程绑定该端口，或端口被系统/安全软件/虚拟化网络保留。当前机器上 `2988-3087` 是 Windows TCP excluded port range，所以 `3000/3001` 都不能用。优先改为只监听本机地址并使用 `4000` 端口：

```bash
cd /d/leibo/yaha-ai-game-platform/apps/web
pnpm next dev -H 127.0.0.1 -p 4000
```

如果 4000 也失败，换一个较少冲突且不在 excluded range 里的端口：

```bash
pnpm next dev -H 127.0.0.1 -p 4100
```

如果这样能启动，建议把 `apps/web/package.json` 的 dev 脚本改成固定本机地址：

```json
"dev": "next dev -H 127.0.0.1 -p 4000"
```

排查端口占用可以执行：

```bash
netstat -ano | grep ':3000\|:3001\|:4000\|:4100'
netsh interface ipv4 show excludedportrange protocol=tcp
```

停止服务：在终端按 `Ctrl+C`。

## V0.10 创建 FastAPI Agent 服务

```bash
cd /d/leibo/yaha-ai-game-platform
mkdir -p services/agent-service
cd services/agent-service
uv init
uv add fastapi uvicorn pydantic pydantic-settings python-multipart boto3 pytest httpx
mkdir -p app
```

创建 `services/agent-service/app/main.py`：

```python
from fastapi import FastAPI

app = FastAPI(title="Yaha Agent Service")

@app.get("/health")
def health():
    return {"status": "ok"}
```

启动：

```bash
cd /d/leibo/yaha-ai-game-platform/services/agent-service
uv run uvicorn app.main:app --reload --port 8000
```

验证：

```bash
curl http://localhost:8000/health
```

期望返回：

```json
{"status":"ok"}
```

## V0.11 配置 Docker Compose 基础依赖

在项目根目录创建 `docker-compose.yml`，包含 PostgreSQL 和 MinIO：

```yaml
services:
  postgres:
    image: postgres:16
    container_name: yaha-postgres
    environment:
      POSTGRES_USER: yaha
      POSTGRES_PASSWORD: yaha_password
      POSTGRES_DB: yaha_game
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  minio:
    image: minio/minio:latest
    container_name: yaha-minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: yaha_minio
      MINIO_ROOT_PASSWORD: yaha_minio_password
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data

volumes:
  postgres_data:
  minio_data:
```

启动依赖：

```bash
cd /d/leibo/yaha-ai-game-platform
docker compose up -d
```

检查：

```bash
docker compose ps
```

访问 MinIO 控制台：

```text
http://localhost:9001
```

账号密码：

```text
yaha_minio / yaha_minio_password
```

## V0.12 V0 验收清单

- [ ] `node -v` 正常。
- [ ] `pnpm -v` 正常。
- [ ] `python --version` 正常。
- [ ] `uv --version` 正常，或已确认用 venv 替代。
- [ ] `docker compose version` 正常。
- [ ] Next.js 能打开 `http://localhost:3000`。
- [ ] FastAPI 能访问 `http://localhost:8000/health`。
- [ ] PostgreSQL 和 MinIO 容器处于 running。
- [ ] MinIO 控制台能登录。

建议提交：

```bash
git add .
git commit -m "chore: setup project skeleton and local services"
```

---

# V1：基础页面、Auth、数据库 CRUD

## V1.1 版本目标

实现一个可操作的 Web 平台雏形：有页面、有数据库、有登录注册、有游戏列表 CRUD，有 seed 数据。此时 Play 可以先跳转到占位页，但 Home 数据必须来自数据库，不能写死在前端数组。

## V1.2 本版本要实现的页面

| 页面 | 路径 | 目标 |
| --- | --- | --- |
| Home | `/` | 展示 published 游戏卡片 |
| Register | `/register` | 邮箱注册 |
| Login | `/login` | 邮箱登录 |
| Create | `/create` | 先做受保护占位页 |
| Play | `/play/[gameId]` | 先做占位和游戏 meta 展示 |
| Admin/Debug | `/debug` 可选 | 查看当前用户、数据库连接状态 |

## V1.3 安装 Web 依赖

```bash
cd /d/leibo/yaha-ai-game-platform/apps/web
pnpm add @prisma/client zod bcryptjs nanoid
pnpm add -D prisma tsx @types/bcryptjs
```

初始化 Prisma：

```bash
pnpm prisma init
```

## V1.4 配置环境变量

创建 `apps/web/.env.example`：

```env
DATABASE_URL="postgresql://yaha:yaha_password@localhost:5432/yaha_game"
SESSION_SECRET="replace-with-random-secret"
NEXT_PUBLIC_APP_URL="http://localhost:3000"
MINIO_ENDPOINT="http://localhost:9000"
MINIO_ACCESS_KEY="yaha_minio"
MINIO_SECRET_KEY="yaha_minio_password"
MINIO_BUCKET="yaha-games"
AGENT_SERVICE_URL="http://localhost:8000"
```

复制成本地 `.env`：

```bash
cd /d/leibo/yaha-ai-game-platform/apps/web
cp .env.example .env
```

## V1.5 设计 Prisma 基础模型

在 `apps/web/prisma/schema.prisma` 中先实现这些表：

- `User`
- `Session`
- `OAuthAccount`
- `Game`
- `GameVersion`
- `Asset`
- `GenerationTask`
- `AgentLog`
- `PlayEvent`

V1 可以先重点用到 `User`、`Session`、`Game`、`GameVersion`，其他表先建好字段，后续版本逐步使用。

迁移数据库：

```bash
cd /d/leibo/yaha-ai-game-platform/apps/web
pnpm prisma migrate dev --name init
pnpm prisma generate
```

查看数据库：

```bash
pnpm prisma studio
```

浏览器打开 Prisma Studio 后检查表是否存在。

## V1.6 实现邮箱注册、登录、退出

建议使用自研 Cookie Session，2 天内最稳：

| API | 方法 | 作用 |
| --- | --- | --- |
| `/api/v1/auth/register` | POST | 创建用户、写 session cookie |
| `/api/v1/auth/login` | POST | 校验密码、写 session cookie |
| `/api/v1/auth/logout` | POST | 删除 session、清 cookie |
| `/api/v1/auth/me` | GET | 返回当前用户 |

密码处理：

- 使用 `bcryptjs.hash(password, 10)` 存储。
- 登录时用 `bcryptjs.compare()` 校验。
- Cookie 设置 `httpOnly`、`sameSite=lax`。

测试注册：

```bash
curl -i -X POST http://localhost:3000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@yaha.local","password":"12345678","displayName":"Demo Creator"}'
```

测试登录：

```bash
curl -i -X POST http://localhost:3000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@yaha.local","password":"12345678"}'
```

## V1.7 实现游戏 CRUD API

| API | 方法 | 作用 |
| --- | --- | --- |
| `/api/v1/games` | GET | 获取 published 游戏列表 |
| `/api/v1/games` | POST | 创建 draft 游戏，开发调试用 |
| `/api/v1/games/[gameId]` | GET | 获取游戏详情 |
| `/api/v1/games/[gameId]` | PATCH | 更新游戏信息 |
| `/api/v1/games/[gameId]/publish` | POST | 发布游戏 |
| `/api/v1/games/[gameId]/play-meta` | GET | 获取 Play 所需 meta |

V1 的 `play-meta` 可以先返回数据库里的占位 manifest URL，V2 再接入 MinIO 真实文件。

## V1.8 准备 seed 数据

创建 `apps/web/prisma/seed.ts`，插入：

- 1 个 demo 用户。
- 2 个 published 示例游戏。
- 每个游戏一条 `GameVersion`，manifest URL 可以先占位。

执行：

```bash
cd /d/leibo/yaha-ai-game-platform/apps/web
pnpm prisma db seed
```

如果还没配置 seed 命令，在 `apps/web/package.json` 加：

```json
{
  "prisma": {
    "seed": "tsx prisma/seed.ts"
  }
}
```

## V1.9 页面验收

启动依赖和 Web：

```bash
cd /d/leibo/yaha-ai-game-platform
docker compose up -d
cd apps/web
pnpm dev
```

浏览器检查：

1. 打开 `http://localhost:3000`，能看到 2 个 seed 游戏。
2. 打开 `/register`，能注册新用户。
3. 打开 `/login`，能登录。
4. 登录后访问 `/create` 不被拦截。
5. 退出后访问 `/create` 会跳转登录。
6. 点击游戏卡片进入 `/play/[gameId]`，能看到游戏 meta 或占位状态。

## V1.10 自动测试建议

先做最少量测试：

```bash
cd /d/leibo/yaha-ai-game-platform/apps/web
pnpm lint
pnpm build
```

如果配置 Vitest：

```bash
pnpm add -D vitest
pnpm vitest run
```

## V1.11 V1 验收清单

- [ ] 数据库迁移成功。
- [ ] seed 有 2 个 published 游戏。
- [ ] Home 从数据库读取游戏，不是前端写死数组。
- [ ] 注册、登录、退出可用。
- [ ] Create 页面受保护。
- [ ] Game CRUD API 可调用。
- [ ] `pnpm build` 通过。

建议提交：

```bash
git add .
git commit -m "feat: add auth and game crud foundation"
```

---

# V2：对象存储、远端游戏产物、Play 动态加载

## V2.1 版本目标

把“游戏文件来自远端对象存储”这件事做实。此版本先不做 Agent 自动生成，先手动准备一个可玩的静态小游戏产物上传到 MinIO，再让 Play 页面通过数据库中的 URL 动态加载。

这是为了提前规避原任务不接受项：Play 页面不能只运行本地写死组件。

## V2.2 准备 MinIO Bucket

进入 MinIO 控制台：

```text
http://localhost:9001
```

创建 bucket：

```text
yaha-games
```

开发阶段可以设置为公开读，方便 iframe 加载。真实项目可以改为 Next.js 代理或签名 URL。

## V2.3 安装对象存储 SDK

```bash
cd /d/leibo/yaha-ai-game-platform/apps/web
pnpm add @aws-sdk/client-s3 @aws-sdk/s3-request-presigner
```

创建 `apps/web/lib/storage.ts`：

- 读取 `MINIO_ENDPOINT`、`MINIO_ACCESS_KEY`、`MINIO_SECRET_KEY`、`MINIO_BUCKET`。
- 封装 `putObject()`。
- 封装 `getPublicUrl()`。

## V2.4 创建本地示例游戏产物

在项目中创建一个开发用产物目录，例如：

```text
tmp/sample-game/index.html
tmp/sample-game/style.css
tmp/sample-game/game.js
tmp/sample-game/manifest.json
```

`manifest.json` 至少包含：

```json
{
  "title": "Sample Click Game",
  "entry": "index.html",
  "files": ["index.html", "style.css", "game.js"],
  "runtime": "iframe-static-html"
}
```

## V2.5 写上传脚本

创建 `apps/web/scripts/upload-sample-game.ts`，作用：

1. 读取 `tmp/sample-game` 文件。
2. 上传到 MinIO 路径：`games/seed/sample-click-game/v1/`。
3. 更新或创建对应 `GameVersion` 的 `manifest_url`、`entry_url`、`artifact_base_url`。

执行：

```bash
cd /d/leibo/yaha-ai-game-platform/apps/web
pnpm tsx scripts/upload-sample-game.ts
```

验证对象是否存在：

1. 打开 MinIO 控制台。
2. 进入 `yaha-games` bucket。
3. 能看到 `games/seed/sample-click-game/v1/index.html` 等文件。

## V2.6 实现 Play 动态加载

Play 页面流程：

1. 访问 `/play/[gameId]`。
2. 请求 `/api/v1/games/[gameId]/play-meta`。
3. API 从数据库读取 published `GameVersion`。
4. 返回：
   - `manifestUrl`
   - `entryUrl`
   - `artifactBaseUrl`
5. 前端展示加载中。
6. iframe 加载 `entryUrl`。
7. iframe 加载成功后上报 `load_success`。
8. 加载失败展示错误态并上报 `load_failed`。

iframe 建议：

```tsx
<iframe
  src={entryUrl}
  sandbox="allow-scripts allow-pointer-lock"
  className="h-[720px] w-full rounded-lg border"
/>
```

注意：不要加 `allow-same-origin`，除非确实需要；否则隔离性会变弱。

## V2.7 实现 Play 事件 API

| API | 方法 | 作用 |
| --- | --- | --- |
| `/api/v1/play-events` | POST | 记录 `load_start`、`load_success`、`load_failed`、`play_start` |

写入 `play_events` 表，至少包含：

- `game_id`
- `version_id`
- `event_type`
- `message`
- `created_at`

## V2.8 V2 验收命令

启动服务：

```bash
cd /d/leibo/yaha-ai-game-platform
docker compose up -d
cd apps/web
pnpm dev
```

上传示例产物：

```bash
cd /d/leibo/yaha-ai-game-platform/apps/web
pnpm tsx scripts/upload-sample-game.ts
```

测试 play-meta：

```bash
curl http://localhost:3000/api/v1/games/<gameId>/play-meta
```

浏览器验收：

1. 打开 Home。
2. 点击一个游戏进入 Play。
3. Network 面板能看到加载的是 `http://localhost:9000/yaha-games/.../index.html` 或 Next.js 代理地址。
4. 页面里能操作小游戏。
5. 数据库 `play_events` 有加载事件。

## V2.9 V2 验收清单

- [ ] MinIO bucket 存在。
- [ ] 静态游戏文件上传到 MinIO。
- [ ] `GameVersion` 保存远端 manifest/entry 地址。
- [ ] Play 页面通过远端 URL 加载 iframe。
- [ ] 加载失败不会白屏。
- [ ] Play 事件写入数据库。

建议提交：

```bash
git add .
git commit -m "feat: load playable games from object storage"
```

---

# V3：Create + FastAPI Agent 生成发布闭环

## V3.0 实际实现状态

> ✅ 已完成。本版本实际实现已**超出原计划**，主要升级：

- 自研状态机 → **LangGraph StateGraph**（显式图工作流）
- 单次 HTTP 调用 → **SSE 流式**实时推送每个节点日志
- 固定模板选择 → **SupervisorAgent（LLM 意图分类）**判断简单/复杂后路由
- 简单游戏 → **TemplateWorkflow**（模板化生成）
- 复杂游戏 → **SpecialistFanOut**（VisionAgent + NarrativeAgent + GameplayAgent 并行 + SynthesisAgent）
- 无可观测性 → **LangSmith 完整 trace**
- FastAPI 不可用时 → **Next.js 本地 fallback 生成器**

## V3.1 版本目标

打通原任务最核心的链路：用户输入创意和素材，系统通过 FastAPI/Python Agent 生成小游戏文件，上传 MinIO，写入数据库，用户预览并发布，Home 展示，Play 可玩。

这是整个项目最重要的版本。

## V3.2 Create 页面能力

Create 页面需要包含：

- 创意文本输入框。
- 文件上传控件，至少支持图片或普通文件一种。
- 生成按钮。
- 任务进度区域。
- Agent 日志列表。
- 生成成功后的预览链接。
- 发布按钮。
- 最近任务历史，可选但建议做。

## V3.3 素材上传 API

| API | 方法 | 作用 |
| --- | --- | --- |
| `/api/v1/assets/upload` | POST | 上传用户素材到 MinIO |

限制建议：

- 单文件最大 10MB。
- MVP 支持 `image/png`、`image/jpeg`、`image/webp`、`text/plain`。
- 文件名做清理，避免路径穿越。
- 返回 `assetId`、`objectKey`、`publicUrl`。

测试：

```bash
curl -i -X POST http://localhost:3000/api/v1/assets/upload \
  -F 'file=@/d/leibo/yaha-ai-game-platform/tmp/test.png'
```

## V3.4 Generation Task API

| API | 方法 | 作用 |
| --- | --- | --- |
| `/api/v1/generation-tasks` | POST | 创建生成任务并调用 Agent |
| `/api/v1/generation-tasks` | GET | 获取当前用户任务历史 |
| `/api/v1/generation-tasks/[taskId]` | GET | 查询任务状态 |
| `/api/v1/generation-tasks/[taskId]/logs` | GET | 查询 Agent 日志 |
| `/api/v1/generation-tasks/[taskId]/retry` | POST | 失败重试，可后置 |

任务状态：

```text
pending -> running -> succeeded
pending -> running -> failed
```

## V3.5 FastAPI Agent 接口

FastAPI 内部接口：

```text
POST http://localhost:8000/generate
```

请求体：

```json
{
  "task_id": "task_xxx",
  "user_id": "user_xxx",
  "prompt": "做一个点击星星得分的小游戏",
  "assets": [
    {
      "asset_id": "asset_xxx",
      "url": "http://localhost:9000/yaha-games/assets/.../image.png",
      "mime_type": "image/png"
    }
  ]
}
```

响应体：

```json
{
  "status": "succeeded",
  "title": "星星点击挑战",
  "description": "点击随机出现的星星，在 30 秒内获得尽可能高的分数。",
  "tags": ["click", "casual", "score"],
  "artifact": {
    "manifest_url": "http://localhost:9000/yaha-games/games/generated/task_xxx/v1/manifest.json",
    "entry_url": "http://localhost:9000/yaha-games/games/generated/task_xxx/v1/index.html",
    "artifact_base_url": "http://localhost:9000/yaha-games/games/generated/task_xxx/v1/"
  },
  "logs": [
    {"agent_name": "RequirementAgent", "step": "parse_prompt", "message": "已解析玩法类型：点击得分"},
    {"agent_name": "GameDesignAgent", "step": "design_rules", "message": "生成 30 秒计时和得分规则"},
    {"agent_name": "CodeGenerationAgent", "step": "render_files", "message": "生成 index.html/style.css/game.js/manifest.json"},
    {"agent_name": "BuildValidateAgent", "step": "validate", "message": "产物结构校验通过"},
    {"agent_name": "ArtifactAgent", "step": "upload", "message": "产物已上传对象存储"}
  ]
}
```

## V3.6 Agent 编排实现方式

MVP 先用 Python 状态机，不强依赖真实 LLM：

1. `RequirementAgent`：解析 prompt，判断游戏模板。
2. `GameDesignAgent`：生成标题、简介、规则、颜色、标签。
3. `CodeGenerationAgent`：基于模板生成 HTML/CSS/JS/manifest。
4. `BuildValidateAgent`：检查必须文件、危险 API、manifest 格式。
5. `ArtifactAgent`：上传 MinIO 或把文件返回给 Next.js 上传。

可支持 3 个模板：

- 点击得分游戏：`click_challenge`
- 躲避障碍游戏：`avoid_obstacle`
- 问答互动游戏：`quiz_game`

## V3.7 产物安全检查

`BuildValidateAgent` 至少拦截：

- `<script src="http://...">` 外部脚本。
- `eval()`。
- `Function()`。
- `localStorage` 读写可先禁止。
- `document.cookie`。
- `fetch()` 访问非白名单地址。

MVP 产物只允许静态 HTML/CSS/JS。

## V3.8 Next.js 调 Agent 后的数据库写入

`POST /api/v1/generation-tasks` 流程：

1. 校验用户登录。
2. 创建 `GenerationTask`，状态 `pending`。
3. 更新状态为 `running`。
4. 调用 FastAPI `/generate`。
5. 收到响应后，用 Prisma transaction 写入：
   - `games`
   - `game_versions`
   - `agent_logs`
   - 更新 `generation_tasks.status = succeeded`
6. 如果失败：
   - `generation_tasks.status = failed`
   - 写入 `error_message`

## V3.9 预览和发布

生成成功后，游戏先是 `draft`：

- Create 页面显示“预览”。
- 预览可以复用 `/play/[gameId]?preview=1`。
- 用户点击“发布”。
- 调用 `/api/v1/games/[gameId]/publish`。
- 更新 `games.status = published`。
- Home 页面可见。

## V3.10 V3 验收步骤

启动全部服务：

```bash
cd /d/leibo/yaha-ai-game-platform
docker compose up -d
cd services/agent-service
uv run uvicorn app.main:app --reload --port 8000
```

另开一个 Git Bash：

```bash
cd /d/leibo/yaha-ai-game-platform/apps/web
pnpm dev
```

浏览器验收：

1. 注册或登录账号。
2. 进入 `/create`。
3. 输入：`做一个点击星星得分的小游戏，30 秒内尽量多得分`。
4. 上传一张图片或文件。
5. 点击生成。
6. 看到任务状态从 running 到 succeeded。
7. 看到 Agent 日志至少 5 步。
8. 看到产物地址或预览按钮。
9. 点击预览，游戏能运行。
10. 点击发布。
11. 回到首页，能看到新游戏。
12. 点击首页新游戏进入 Play，能从 MinIO 远端加载并运行。

数据库验收：

```bash
cd /d/leibo/yaha-ai-game-platform/apps/web
pnpm prisma studio
```

检查：

- `games` 有新记录。
- `game_versions` 有 manifest/entry URL。
- `generation_tasks` 状态为 `succeeded`。
- `agent_logs` 有多条日志。
- `assets` 有上传素材记录。

对象存储验收：

- MinIO bucket 中有 `games/generated/<taskId>/v1/`。
- 下面有 `index.html`、`style.css`、`game.js`、`manifest.json`。

## V3.11 V3 验收清单

- [ ] Create 页面可输入创意。
- [ ] 至少支持一种文件上传。
- [ ] 生成任务有状态。
- [ ] Agent 日志可见。
- [ ] FastAPI 生成真实文件。
- [ ] 产物上传到 MinIO。
- [ ] 数据库保存 meta。
- [ ] 可预览。
- [ ] 可发布。
- [ ] Home 展示 Create 生成的游戏。
- [ ] Play 动态加载远端文件。

建议提交：

```bash
git add .
git commit -m "feat: complete create agent publish play loop"
```

---

# MVP：前端细节调整

## MVP.1 调整目标

在 V3 完整链路打通后，对前端交互和 UI 细节进行收尾打磨，提升用户体验。

## MVP.2 已完成的调整

### 导航栏精简

- **改动文件**：`apps/web/components/site-header.tsx`
- **内容**：删除了用户已登录状态下右上角的"新建游戏"按钮。该入口在"我的游戏"页面内已存在，导航栏重复放置导致界面冗余。

### 新建游戏页面增加游戏名称输入

- **改动文件**：`apps/web/components/create-game-form.tsx`
- **内容**：在"创意文本"输入框上方新增"游戏名称"文本框，对应数据库 `games.title` 字段。用户必须填写游戏名称后才能提交。
- **表单改动**：
  - 新增 `name="title"` 的 `<input>` 字段，必填，最大 100 字
  - 提交前增加非空校验
  - POST 请求体加入 `title` 字段

### API 层适配

- **改动文件**：`apps/web/lib/generation-tasks.ts`、`apps/web/app/api/v1/generation-tasks/route.ts`、`apps/web/app/api/v1/generation-tasks/[taskId]/route.ts`
- **内容**：
  - `generationTaskCreateSchema` 增加 `title` 必填字段（1-100字）
  - 响应序列化（`serializeGenerationTask`）增加 `title` 字段
  - 两个 API route 的 `taskSelect` 均加入 `title: true`

### 任务执行层适配

- **改动文件**：`apps/web/lib/generation-task-runner.ts`
- **内容**：
  - `createAndRunGenerationTask` 函数参数增加 `title: string`
  - `prisma.generationTask.create` 时写入 `title` 字段
  - `tx.game.create` 创建游戏时直接使用用户传入的 `title`，不再依赖 Agent 返回值

### 数据库 Schema

- **改动文件**：`apps/web/prisma/schema.prisma`
- **内容**：`GenerationTask` 模型新增 `title String @map("title") @default("")` 字段（已有数据默认为""）

### 验证脚本同步

- **改动文件**：`apps/web/scripts/verify-generation-tasks.ts`、`apps/web/scripts/verify-v38-db-write.ts`
- **内容**：测试用例同步适配新增的 `title` 参数

## MVP.3 提交建议

```bash
git add .
git commit -m "feat: add game title input to create page and clean up nav"
```

---

# V4：交付验收、文档、稳定性修复

## V4.1 版本目标

把项目从“能跑”整理成“别人能复现、能验收、能看懂”的交付状态。这个版本重点不是加功能，而是补齐原任务要求的提交物。

## V4.2 必须补齐的文档

| 文件 | 内容 |
| --- | --- |
| `README.md` | 项目介绍、技术栈、启动命令、账号、验收步骤 |
| `docs/system-design.md` | 架构图、核心接口、数据模型、Agent 工作流、产物协议、安全方案、已知问题 |
| `docs/completion-report.md` | 已完成、未完成、Mock、再给 1 周怎么迭代 |
| `docs/manual-test-checklist.md` | 手工验收步骤和结果 |
| `docs/ai-collaboration.md` | 使用的 AI 工具、关键 prompt、AI 贡献、人工 review 和修复 |
| `.env.example` | Web 和 Agent 服务所需环境变量，不提交真实密钥 |

## V4.3 README 启动命令建议

README 中要尽量给少量命令：

```bash
git clone <你的仓库地址>
cd yaha-ai-game-platform
cp apps/web/.env.example apps/web/.env
cp services/agent-service/.env.example services/agent-service/.env
docker compose up -d
cd apps/web && pnpm install && pnpm prisma migrate deploy && pnpm prisma db seed && pnpm dev
```

另一个终端：

```bash
cd services/agent-service
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

如果后续把 web 和 agent-service 也放进 Docker Compose，则 README 可以简化为：

```bash
docker compose up --build
```

## V4.4 测试与验证

Web：

```bash
cd /d/leibo/yaha-ai-game-platform/apps/web
pnpm lint
pnpm build
```

Agent：

```bash
cd /d/leibo/yaha-ai-game-platform/services/agent-service
uv run pytest -q
```

接口健康检查：

```bash
curl http://localhost:8000/health
curl http://localhost:3000/api/v1/games
```

手工验收：

1. 注册账号。
2. 登录。
3. 进入 Create。
4. 输入创意并上传素材。
5. 生成游戏。
6. 查看 Agent 日志。
7. 预览。
8. 发布。
9. Home 出现新游戏。
10. Play 页面远端加载游戏。
11. MinIO 中能看到生成文件。
12. Prisma Studio 中能看到数据库记录。

## V4.5 截图和演示材料

建议截图：

- Home 三个游戏。
- 注册/登录成功。
- Create 输入和上传。
- 任务日志。
- MinIO 产物目录。
- Prisma Studio 数据记录。
- Play 运行游戏。

建议录制 5 分钟以内视频，覆盖：

```text
登录 → Create → Agent 生成日志 → 预览 → 发布 → Home → Play → MinIO/数据库证明
```

## V4.6 最终交付清单

- [ ] GitHub 仓库地址。
- [ ] 至少 3 次 commit，建议 4 次以上。
- [ ] Demo 地址或完整本地启动命令。
- [ ] Docker Compose 可启动 PostgreSQL 和 MinIO。
- [ ] `.env.example` 完整。
- [ ] seed 测试数据完整。
- [ ] 至少 3 个 Home 游戏，其中 1 个来自 Create。
- [ ] 系统设计文档完整。
- [ ] 技术栈说明完整。
- [ ] 完成度说明完整。
- [ ] 测试和手工验收记录。
- [ ] AI 协作记录。
- [ ] 可选演示视频。

建议提交：

```bash
git add .
git commit -m "docs: prepare delivery materials and validation checklist"
```

---

# V5：MVP 外增强功能

## V5.1 版本目标

> ⚠️ **重要更新：** 以下部分功能已在主版本中实现，标注为"已实现"。

## V5.2 推荐增强顺序（更新）

### 5A — Agent 微服务增强（LangGraph 深度功能）

||| 优先级 | 功能 | 价值 | 风险 | 状态 |
||| --- | --- | --- | --- | --- |
||| P0 | 持久化检查点（Redis/Postgres Saver） | 生成中途崩溃可恢复，不丢进度 | 低 | 待实现 |
||| P0 | 请求取消（Request Cancellation） | 客户端断连立即停止 Agent，节省 LLM 费用 | 低 | 待实现 |
||| P0 | 背景 Worker 模式 | `/generate` 立即返回 taskId，后台执行，前端轮询 | 低 | 待实现 |
||| P1 | Human-in-the-Loop 中断 | 设计规范确认后再生成代码，用户可干预 | 中 | 待实现 |
||| P1 | LLM Token 级流式输出 | 替换节点 SSE 为逐 token 流，用户实时看代码生成 | 低 | 待实现 |
||| P1 | 原生 Structured Output | OpenAI `response_format=json_schema` / Anthropic Tool Use | 低 | 待实现 |
||| P2 | Prometheus 可观测性 | Token 用量、延迟、错误率、并发数等指标 | 低 | 待实现 |
||| P2 | 多轮 Session Memory | 同用户多轮迭代时 Agent 保留上下文 | 中 | 待实现 |
||| P3 | LangChain @tool / tool_definitions | Specialist Agent schema 校验和工具调用协议 | 中 | 待实现 |
||| P3 | LLM-based 内容安全分类器 | NSFW / 恶意代码检测，过滤生成内容 | 中 | 待实现 |
||| P4 | Docker 沙箱执行生成过程 | Agent 在临时容器隔离执行，杜绝危险操作 | 高 | 待实现 |

### 5B — 前端 + 后端 Web App 增强

||| 优先级 | 功能 | 价值 | 风险 | 状态 |
||| --- | --- | --- | --- | --- |
||| P0 | Play iframe 加载修复 | MinIO public policy + Presigned URL fallback | 低 | 待实现 |
||| P0 | 首页搜索 + 标签筛选 | 游戏发现体验升级，支持模糊搜索 | 低 | 待实现 |
||| P1 | Playwright E2E 测试 | 覆盖登录→Create→发布→Play 全链路 | 低 | 待实现 |
||| P1 | Google / GitHub OAuth | 社交账号一键登录，降低注册门槛 | 中 | 待实现 |
||| P1 | 游玩次数统计 + 排行榜 | Play 加载上报事件，首页展示最热游戏 | 低 | 待实现 |
||| P1 | 点赞 / 收藏功能 | 用户粘性提升，支持个人游戏库 | 低 | 待实现 |
||| P2 | Redis 缓存层 | 热门游戏列表 / Session 缓存，降低 DB 压力 | 中 | 待实现 |
||| P2 | CDN 托管生成文件 | 生成的游戏文件走 CDN，提升加载速度 | 低 | 待实现 |
||| P2 | 数据库连接池调优（PgBouncer） | 减少连接开销，提升并发吞吐 | 中 | 待实现 |
||| P2 | API 限流（Rate Limiting） | 按用户/IP 对高消耗接口限流，防滥用 | 低 | 待实现 |
||| P3 | 任务历史 + 重试 UI | Create 页面展示历史任务，失败一键重试 | 低 | 待实现 |
||| P3 | 游戏版本管理 | 同一游戏多次生成自动保存历史版本，支持回滚 | 中 | 待实现 |
||| P3 | Docker Compose 生产部署文档 | Nginx 反代 + HTTPS + 自动证书续期 | 低 | 待实现 |
||| P4 | 前端性能优化 | SSR/ISR、代码分割、懒加载、WebP 图片压缩 | 低 | 待实现 |

## V5.3 搜索和标签筛选（5B）

实现：

- Home 搜索框。
- 标签过滤。
- `/api/v1/games?query=&tag=`。
- Prisma 查询 title/description/tags。

验收：

```bash
curl 'http://localhost:3000/api/v1/games?query=星星'
```

## V5.4 游玩次数统计（5B）

实现：

- Play iframe 加载成功后调用 `/api/v1/play-events`。
- `games.play_count += 1` 或从 `play_events` 聚合。
- Home 卡片展示游玩次数。

验收：

1. 打开某个游戏 Play。
2. 回到 Home。
3. 游玩次数增加。

## V5.5 任务历史和失败重试（5B）

实现：

- Create 页面右侧展示最近 10 条任务。
- 失败任务显示 `error_message`。
- 提供 retry 按钮。
- retry 创建新任务或复用旧任务，保留日志。

验收：

- 手动让 Agent 返回失败。
- 页面显示 failed。
- 点击 retry 后重新进入 running。

## V5.6 GitHub OAuth（5B）

实现前提：已有 `oauth_accounts` 表。

步骤：

1. GitHub Developer Settings 创建 OAuth App。
2. Callback URL：`http://localhost:3000/api/v1/auth/oauth/github/callback`。
3. `.env` 增加：

```env
GITHUB_CLIENT_ID=""
GITHUB_CLIENT_SECRET=""
```

4. 新增 API：
   - `/api/v1/auth/oauth/github/start`
   - `/api/v1/auth/oauth/github/callback`
5. 回调后绑定或创建用户。

验收：

- 点击 GitHub 登录。
- 跳转 GitHub 授权。
- 回调后站内处于登录态。
- `oauth_accounts` 有绑定记录。

## V5.7 背景 Worker 模式（5A） + Redis 队列（5B）

MVP 中 Next.js 直接 HTTP 调 FastAPI，请求在请求生命周期内同步完成。增强版改为：

**Agent 侧（5A）：**

- `/generate` 改为立即返回 taskId（HTTP 202 Accepted）。
- Agent 执行移入后台 asyncio Task。
- 前端通过 SSE 或轮询 `/generate/{taskId}/status` 获取结果。
- 支持客户端断连时的 `Request Cancellation`（检查 `asyncio.cancelled()`）。

**Web App 侧（5B）：**

- Next.js 只负责创建任务和展示结果，不阻塞请求。
- 任务状态持久化到数据库（增加 `generation_tasks` 表）。
- 前端轮询任务状态变化。

推荐先用 Redis Queue（复杂度低于 RabbitMQ），后续可扩展为 Celery + Redis。

验收：

- 创建任务 API 立即返回 taskId。
- Worker 后台处理。
- 页面轮询看到状态变化。
- 断连后 Agent 停止工作（取消）。

## V5.8 接入真实 LLM（5A）

> ✅ 已实现 — `app/llm/` 模块已接入 OpenAI/Anthropic 等模型提供商，配置 `.env` 中的 `MODEL_*` 变量即可切换。

当前 Agent 通过 Specialist Agent（Vision / Gameplay / Narrative）分工调用 LLM，每个节点独立 `generate_json`，有指数退避重试和模板兜底。

进一步增强方向：

- **原生 Structured Output**：改用 OpenAI `response_format=json_schema` / Anthropic Tool Use，替代 prompt-based JSON，提升解析成功率并减少 token 消耗。
- **LLM Token 级流式输出**：接入 `astream_events`，在 Specialist 节点输出时逐 token 流式推送，用户实时看到代码出现。
- **多轮 Session Memory**：接入 LangChain `BaseChatMessageHistory`，同用户多轮迭代同一游戏时 Agent 保留上下文。

## V5.9 持久化检查点与 Human-in-the-Loop（5A）

当前每个生成请求独立执行，中途崩溃则进度全丢。增强方案：

**持久化检查点（Checkpointing）：**

- 接入 LangGraph 内置的 `RedisSaver` 或 `PostgresSaver`：
  ```python
  from langgraph.checkpoint.postgres import PostgresSaver
  checkpointer = PostgresSaver.from_conn_string(DATABASE_URL)
  graph = builder.compile(checkpointer=checkpointer)
  ```
- 每个节点完成后自动快照，崩溃后凭 `thread_id` 恢复，继续执行剩余节点。
- 同时实现"时间旅行"调试：支持回看任意中间状态。

**Human-in-the-Loop 中断：**

- 在 `synthesis_agent` 节点后插入 `interrupt()`，让用户确认设计规范后再继续：
  ```python
  from langgraph.types import interrupt, Command

  def synthesis_agent(state: GenerationState) -> GenerationState:
      spec = synthesize_specialist_results(state)
      interrupt("请确认游戏设计规范：是否继续生成代码？")
      return {"game_spec": spec}
  ```
- 前端 `/create` 页面弹出确认 Dialog，用户点击后调用 `Command(resume={"approved": True})` 继续。

验收：

- 人为注入进程崩溃后，任务从上一个检查点恢复。
- 设计规范确认 Dialog 出现，审批后代码生成继续。

## V5.10 沙箱升级与内容安全（5A）

**当前安全层（已实现）：**

- `validator.py` 使用 `eval` 安全隔离、`Function()` 构造沙箱、`fetch` 限制内网访问。
- HTML 文件内容校验，防止脚本注入。

**待增强（5A）：**

- **Docker 沙箱执行**：Agent 生成过程在临时 Docker 容器中隔离执行（`docker run --rm --read-only`），彻底杜绝文件系统操作和内网访问。
- **LLM-based 内容分类器**：Prompt 注入检测（如系统 prompt 泄露尝试）、生成内容 NSFW 分类（可接入 OpenAI Moderation API 或自部署模型）。
- **LangChain `@tool` 迁移**：将 Specialist Agent 从 prompt-based JSON 迁移至 `@tool` / `tool_definitions`，获得 schema 校验和工具调用协议，减少 LLM 幻觉导致的解析错误。

**Web App 侧（5B）：**

- iframe `sandbox` 属性精细化配置（限制脚本执行、网络访问、表单提交等）。
- 上传内容速率限制，防止滥用存储。

## V5.11 可观测性增强（5A）

当前已有 LangSmith `@traceable` 装饰器追踪 LLM 调用。生产级部署需补充：

- **Prometheus 指标**：Token 用量计数器、`/generate` 端到端延迟直方图、并发活跃任务数、错误率。
- **OpenTelemetry 集成**：跨服务分布式追踪（Next.js → FastAPI → LLM Provider）。
- **结构化日志**：统一 JSON 日志格式，字段包含 `task_id`、`user_id`、`node_name`、`duration_ms`，便于日志聚合分析。

验收：

- Prometheus `/metrics` 端点暴露关键指标。
- Grafana 仪表盘展示 Token 消耗趋势和错误率。

## V5.12 V5 验收清单

- [ ] MVP 已稳定完成后才开始 V5。
- [ ] 所有 P0 功能已通过手动验收。
- [ ] 新增功能有对应单元 / 集成测试。
- [ ] 每个增强功能独立 commit。
- [ ] completion-report 中明确哪些属于 MVP 外增强。
- [ ] 不因增强功能破坏 Create → Play 核心闭环。

---

# 推荐执行顺序和时间分配

## 如果只有 2 天

### 第 1 天上午：V0

- 安装和检查工具。
- 创建项目骨架。
- 跑通 Next.js、FastAPI、PostgreSQL、MinIO。

### 第 1 天下午：V1

- Prisma 数据模型。
- Auth。
- Home 数据库列表。
- seed 2 个游戏。

### 第 1 天晚上：V2

- MinIO 上传。
- Play 远端加载。
- Play 事件记录。

### 第 2 天上午：V3

- Create 页面。
- 上传素材。
- generation task。
- FastAPI Agent 模板生成。

### 第 2 天下午：V3 收尾 + V4

- 发布流程。
- Home 展示 Create 生成游戏。
- Play 验证。
- 修 bug。

### 第 2 天晚上：V4

- README。
- 系统设计。
- 完成度说明。
- AI 协作记录。
- 手工验收截图或录屏。

## 如果有额外 1 天

优先做：

1. Docker Compose 一键启动 web + agent-service。
2. 任务历史和失败重试。
3. 搜索和标签筛选。
4. GitHub OAuth。
5. 演示视频。

---

# 最重要的开发原则

1. 先打通闭环，再优化体验。
2. Home 数据必须来自数据库。
3. Play 必须动态加载远端对象存储产物。
4. Create 生成流程必须真实产生文件、上传、入库、发布。
5. Agent 可以先模板化，但必须有多步骤日志和可扩展接口。
6. 不要把时间浪费在复杂社交、复杂动画、多人游戏、过度微服务上。
7. 每个版本完成后都提交一次 commit，保证最终仓库不少于 3 次 commit。
