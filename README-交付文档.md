# YAHA 互动游戏平台 — 项目交付文档

> 本文档对应 [yaha游戏平台开发任务.md] 3.3 节交付要求，所有必选项均已覆盖。

---

## 1. 源码仓库

**GitHub 地址：** https://github.com/Drasnow/yaha-ai-game-platform.git

仓库包含 **6 次有效提交**（≥ 3 次要求），commit 历史如下：

| # | Commit | 说明 |
|---|--------|------|
| 1 | `edc0821 Task define` | 项目骨架、local services |
| 2 | `eb059d0 feat: add auth and game crud foundation` | 登录注册、Game CRUD |
| 3 | `06cb014 feat: load playable games from object storage` | Home 从对象存储动态加载游戏 |
| 4 | `c3a2162 feat: complete create agent publish play loop` | 完成 Create→Agent→Publish→Play 闭环 |
| 5 | `7124796 feat: add game title input to create page and clean up nav` | Create 页面标题输入、导航优化 |
| 6 | `705ded2 create agent server` | Agent Service 服务搭建 |

---

## 2. Demo 地址（本地运行说明）

本项目**仅支持本地运行**，尚无公网部署地址。

### 前置条件

- Node.js ≥ 18（建议 v20+）
- Python ≥ 3.12
- pnpm ≥ 8
- Docker Desktop（用于运行 PostgreSQL + MinIO）

### 启动方式（分步）

**Step 1 — 启动基础设施（Docker Compose）**

**Step 1 — 克隆代码（如首次使用）**

```bash
git clone https://github.com/Drasnow/yaha-ai-game-platform.git
cd yaha-ai-game-platform
```

**Step 2 — 启动基础设施（Docker Compose）**

```bash
docker compose up -d
```

验证容器状态：

```bash
docker compose ps
# NAME                STATUS
# yaha-postgres       running
# yaha-minio          running
```

MinIO Console 可访问：http://localhost:9001（账号密码见 .env.example）

**Step 2 — 初始化数据库**

```bash
# 前端目录
cd apps/web

# 安装依赖
pnpm install

# 初始化 Prisma（生成 Prisma Client）
pnpm prisma generate

# 创建数据库表
pnpm prisma db push

# 写入测试数据（3 个示例游戏 + 1 个 demo 用户）
pnpm prisma db seed
```

**Step 3 — 启动后端 Agent Service**

```bash
# 新开终端，agent-service 目录
cd services/agent-service

# 安装 Python 依赖
pip install -e .

# 复制环境变量（使用 .env.example）
cp .env.example .env
# ⚠️  编辑 .env 填入真实 LLM API Key

# 启动服务
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Step 4 — 启动前端**

```bash
# apps/web 目录
cd apps/web
pnpm dev
```

前端访问：http://localhost:4000

### 快速验证链路

1. 访问 http://localhost:4000 → 查看首页已有示例游戏
2. 点击任意游戏 → Play 页面动态加载 MinIO 远端 iframe ✅
3. 访问 http://localhost:4000/register → 注册账号
4. 登录后访问 http://localhost:4000/create → 输入创意触发 Agent 生成 ✅

---

## 3. 启动命令汇总

### 一键启动（Docker Compose）

```bash
# 根目录执行
docker compose up -d
```

### 环境初始化脚本

```bash
# apps/web/
pnpm install && pnpm prisma generate && pnpm prisma db push && pnpm prisma db seed

# services/agent-service/
pip install -e . && cp .env.example .env
```

### 服务启动命令

| 服务 | 端口 | 启动命令 |
|------|------|----------|
| 前端 (Next.js) | 3000 | `cd apps/web && pnpm dev` |
| Agent Service (FastAPI) | 8000 | `cd services/agent-service && uv run uvicorn app.main:app --host 127.0.0.1 --port 8000` |
| PostgreSQL | 5432 | （Docker 自动启动） |
| MinIO | 9000/9001 | （Docker 自动启动） |

### 推荐：Docker Compose 一键启动所有依赖

```yaml
# docker-compose.yml（已提供）
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

---

## 4. 测试数据

### 预置数据（prisma/seed.ts）

执行 `pnpm prisma db seed` 后写入数据库：

#### Demo 用户账号

| 字段 | 值 |
|------|-----|
| 邮箱 | `demo@yaha.local` |
| 密码 | `YahaDemo123!` |
| 显示名 | `Demo Creator` |

#### 示例游戏（3 个）

| # | 标题 | 来源 | 状态 | 产物地址 |
|---|------|------|------|----------|
| 1 | 星际点击挑战 | Seed 手动创建 | PUBLISHED | `http://localhost:9000/yaha-games/games/seed/sample-click-challenge/v1` |
| 2 | AI 知识问答冒险 | Seed 手动创建 | PUBLISHED | `http://localhost:9000/yaha-games/games/seed/sample-quiz-adventure/v1` |
| 3 | 躲避障碍 | Agent Create 流程生成 | PUBLISHED | `http://localhost:9000/yaha-games/games/generated/cmqo12wdr000vkgw9m1he0oen/v1` |

**验收要求：** 已满足 — "躲避障碍"通过 `/create` 页面触发生成，对应 task_id: `cmqo12wdr000vkgw9m1he0oen`，发布后状态为 PUBLISHED。用户可访问 http://localhost:4000 验证三个游戏均已在首页展示。

---

## 5. 环境变量

### apps/web/.env.example

```env
# 数据库
DATABASE_URL="postgresql://yaha:yaha_password@localhost:5432/yaha_game"

# 会话密钥（生产环境请替换为随机字符串）
SESSION_SECRET="replace-with-random-secret"

# 前端地址
NEXT_PUBLIC_APP_URL="http://localhost:4000"

# MinIO 对象存储
MINIO_ENDPOINT="http://localhost:9000"
MINIO_ACCESS_KEY="yaha_minio"
MINIO_SECRET_KEY="yaha_minio_password"
MINIO_BUCKET="yaha-games"

# Agent Service 地址
AGENT_SERVICE_URL="http://localhost:8000"
```

### services/agent-service/.env.example

```env
# MinIO 对象存储
MINIO_ENDPOINT="http://localhost:9000"
MINIO_ACCESS_KEY="yaha_minio"
MINIO_SECRET_KEY="yaha_minio_password"
MINIO_BUCKET="yaha-games"

# Agent 模式（false = 真实 LLM 生成）
MOCK_AGENT_MODE="false"

# LLM Fallback（LLM 失败时降级为模板生成）
ENABLE_LLM_FALLBACK="true"

# LLM Provider 配置
LLM_PROVIDER="fighting"              # 可选: openai-compatible | anthropic | siliconflow | ollama | lmstudio | fighting
LLM_BASE_URL="http://43.106.115.130:8080/v1"
LLM_API_KEY="sk-xxx"                # ⚠️ 替换为真实 Key
LLM_MODEL="gpt-5.5"
LLM_TIMEOUT="300"
LLM_MAX_RETRIES="3"

# 模型行为设置
LLM_REASONING_EFFORT="medium"        # low | medium | high
LLM_TOOL_OUTPUT_TOKEN_LIMIT="25000"
LLM_PERSONALITY="pragmatic"          # pragmatic | creative | precise

# LangSmith 可观测性
LANGSMITH_API_KEY="lsv2_YOUR_API_KEY"
LANGSMITH_PROJECT="yaha-agent"
LANGSMITH_TRACING="true"

# 素材 URL 安全白名单（可选）
# ALLOWED_ASSET_DOMAINS=""
```

> ⚠️ **重要：** 项目 `.env` 文件包含真实密钥，已在 `.gitignore` 中排除，提交前确保不包含真实密钥。

---

## 6. 系统设计文档

### 6.1 总体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        客户端 (Browser)                          │
│  Next.js 16 (React 19, Tailwind CSS v4, TypeScript 5)          │
│  ├── Home  (首页游戏流)                                          │
│  ├── Play  (动态加载远端 iframe)                                  │
│  ├── Create (多模态输入 → 触发生成任务)                            │
│  └── Auth  (登录/注册/会话)                                       │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP / REST
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      前端 API 服务 (Next.js)                      │
│  ├── /api/v1/auth/*    (登录/注册/会话)                           │
│  ├── /api/v1/games/*   (游戏 CRUD/发布)                          │
│  ├── /api/v1/assets/*  (素材上传)                                │
│  ├── /api/v1/generation-tasks/* (任务查询)                       │
│  └── /api/v1/play-events (游戏事件埋点)                          │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP (Internal)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Agent Service (FastAPI + LangGraph)              │
│  Port: 8000                                                     │
│  ├── SupervisorAgent (需求审查/路由)                             │
│  ├── Specialist Fan-Out                                         │
│  │   ├── VisionAgent    (视觉/素材分析)                         │
│  │   ├── GameplayAgent  (玩法设计)                              │
│  │   └── NarrativeAgent (叙事/剧情设计)                         │
│  ├── SynthesisAgent  (整合设计)                                 │
│  ├── CodeGenerator    (代码生成)                                 │
│  ├── Validator        (产物验证)                                 │
│  ├── RetryWorkflow    (失败重试)                                 │
│  └── UploadWorkflow    (上传 MinIO)                              │
└──────────┬──────────────────────────┬──────────────────────────┘
           │                          │
           ▼                          ▼
┌─────────────────────┐    ┌─────────────────────────────────────┐
│   PostgreSQL 16      │    │   MinIO (S3 兼容对象存储)             │
│   Port: 5432         │    │   Port: 9000 / Console: 9001        │
│   ├── users          │    │   └── yaha-games/                    │
│   ├── games          │    │       ├── games/{userId}/{gameId}/   │
│   ├── game_versions  │    │       │   └── v{version}/             │
│   ├── sessions       │    │       │       ├── manifest.json      │
│   ├── assets         │    │       │       ├── index.html         │
│   ├── generation_tasks│   │       │       └── *.js/*.css/*        │
│   ├── agent_logs     │    │       └── assets/{assetId}/...       │
│   └── play_events    │    │                                     │
└─────────────────────┘    └─────────────────────────────────────┘
```

### 6.2 核心接口

#### 认证模块

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/register` | 邮箱注册 |
| POST | `/api/v1/auth/login` | 邮箱登录 |
| POST | `/api/v1/auth/logout` | 退出登录 |
| GET | `/api/v1/auth/me` | 获取当前用户 |

#### 游戏模块

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/games` | 列表（首页，只返回 PUBLISHED） |
| GET | `/api/v1/games/:gameId` | 详情 |
| GET | `/api/v1/games/:gameId/play-meta` | 获取 Play 所需元信息（manifestUrl, entryUrl 等） |
| POST | `/api/v1/games/:gameId/publish` | 发布游戏 |
| DELETE | `/api/v1/games/:gameId` | 删除游戏 |

#### 创作模块

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/generation-tasks` | 创建生成任务（触发 Agent） |
| GET | `/api/v1/generation-tasks/:taskId` | 查询任务状态和 Agent 日志 |
| GET | `/api/v1/generation-tasks` | 列出当前用户所有任务 |

#### 素材模块

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/assets/upload` | 上传素材到 MinIO，返回 publicUrl |

#### 事件埋点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/play-events` | 记录游戏加载/游玩事件 |

### 6.3 数据模型

详细模型定义见 `apps/web/prisma/schema.prisma`，核心表结构：

```
User
├── id, email, passwordHash, displayName, avatarUrl
└── relations: sessions, games, assets, generationTasks, playEvents

Session
├── id, tokenHash, userId, expiresAt
└── user → User

Game
├── id, authorId, title, description, coverUrl, tags[]
├── status (DRAFT | PUBLISHED | ARCHIVED)
├── latestVersionId, playCount, publishedAt
└── author → User, versions → GameVersion[], tasks, playEvents

GameVersion
├── id, gameId, version, manifestUrl, entryUrl, artifactBaseUrl
├── entryFile, runtime, sourceTaskId, resultTaskId
└── game → Game, sourceTask/resultTask → GenerationTask

Asset
├── id, ownerId, taskId, fileName, mimeType, size
├── objectKey, publicUrl
└── owner → User, task → GenerationTask

GenerationTask
├── id, userId, title, prompt, status (PENDING|RUNNING|SUCCEEDED|FAILED)
├── currentStep, resultGameId, resultVersionId, sourceGameId
├── errorMessage, modelTokens, estimatedCost
└── user → User, resultGame, assets, agentLogs

AgentLog
├── id, taskId, agentName, step, message, rawPayload
└── task → GenerationTask

PlayEvent
├── id, gameId, versionId, userId, eventType
├── message, metadata
└── game → Game, version → GameVersion, user → User
```

### 6.4 MinIO 存储内容

Agent 生成的游戏文件均存储在 MinIO（或 OSS）S3 兼容存储中，存储驱动为 `ArtifactStorage`（`services/agent-service/app/agent/storage.py`），与数据库的关联通过 `objectKey` + URL 回写实现。

#### 存储结构

| MinIO Object Key | 内容说明 | 对应数据库字段 | 关联表 |
|---|---|---|---|
| `games/generated/{task_id}/v1/index.html` | 游戏入口 HTML，单文件完整可运行 | `GameVersion.entryUrl` | `GameVersion` |
| `games/generated/{task_id}/v1/style.css` | 游戏样式文件 | — | — |
| `games/generated/{task_id}/v1/game.js` | 游戏逻辑 JS 文件 | — | — |
| `games/generated/{task_id}/v1/manifest.json` | 游戏元数据（标题、作者、版本、依赖） | `GameVersion.manifestUrl` | `GameVersion` |
| `games/generated/{task_id}/v1/` | 资源文件夹（图片、音频等） | `GameVersion.artifactBaseUrl` | `GameVersion` |
| `assets/{userId}/{assetId}/{fileName}` | 用户上传的参考素材文件（.txt/.md/.docx） | `Asset.objectKey`、`Asset.publicUrl` | `Asset` |

**资产来源说明：**
- **游戏生成物（games/）**：由 Agent 生成完成后自动上传至 MinIO，存储逻辑在 `ArtifactStorage.upload_game_files()`（`services/agent-service/app/agent/storage.py`）
- **用户素材（assets/）**：用户通过 `/api/v1/assets/upload` 上传，路由在 `apps/web/app/api/v1/assets/upload/route.ts`，上传前经过 mimeType + 文件大小校验（10MB 限制，支持 .txt/.md/.docx），最终写入 `Asset` 表

#### 与数据库的关联关系

```
用户上传素材（assets/）
    │
    ▼
POST /api/v1/assets/upload
    ├─ buildAssetObjectKey() → assets/{userId}/{assetId}/{fileName}
    ├─ putObject() → MinIO
    └─ Asset.create(objectKey, publicUrl, ownerId)
         └─ Asset.ownerId → User.id
         └─ Asset.taskId  → GenerationTask.id（用户可在生成时关联）
              └─ Agent 通过 GenerationTask.assets 获取素材 URL
                   └─ fetch_asset_content() 下载并提取文本内容

Agent 生成完成（games/）
    │
    ▼
ArtifactStorage.upload_game_files(task_id, files)
    │
    ├─ 上传 4 个核心文件到 MinIO
    │    prefix = games/generated/{task_id}/v1
    │
    ▼
UploadResult(manifest_url, entry_url, artifact_base_url)
    │
    ▼
结果写入数据库
    │
    ├─ GenerationTask.status = SUCCEEDED
    ├─ GenerationTask.resultVersionId → GameVersion.id
    │    ├─ GameVersion.manifestUrl    = UploadResult.manifest_url
    │    ├─ GameVersion.entryUrl       = UploadResult.entry_url
    │    └─ GameVersion.artifactBaseUrl = UploadResult.artifact_base_url
    │    └─ GameVersion.sourceTaskId    = task_id（来源生成任务）
    │
    ├─ GameVersion → Game.latestVersionId
    │    └─ Game.playCount 由 PlayEvent 聚合更新
    │
    └─ Asset 表记录每个文件的元数据（fileName, mimeType, objectKey, publicUrl）
         └─ Asset.taskId  → GenerationTask.id
         └─ Asset.ownerId → User.id
```

> **注意：** 当前 MinIO 作为开发/演示环境存储，生产部署时需切换至阿里云 OSS / AWS S3（两者均为 S3 兼容），仅需修改 `boto3` 的 `endpoint_url` 和凭证，无需改动上传逻辑。

### 6.5 Agent 工作流

```
START
  │
  ▼
SupervisorAgent（LLM 审查需求，决定是否通过或拒绝）
  │
  ├─ [rejected] → END
  │
  ▼
specialist_fan_out（并行触发三个专家 Agent）
  │
  ├── VisionAgent    → 素材/视觉分析
  ├── GameplayAgent  → 玩法机制设计
  └── NarrativeAgent → 叙事/剧情设计
  │
  ▼
SynthesisAgent（整合三个专家输出，形成完整游戏设计）
  │
  ▼
CodeGenerator（LLM 调用生成游戏代码，支持 3 次重试，超时 5 分钟）
  │
  ▼
Validator（验证生成的 manifest.json 和 index.html 是否合法）
  │
  ├─ [passed] → UploadWorkflow → END
  ├─ [failed] → RetryWorkflow（最多 3 次）→ Validator
  └─ [error]  → END
```

**重试策略：**
- `CodeGenerator`：最多 3 次尝试，指数退避（2s → 4s → 8s），超时 5 分钟
- `Validator` / `UploadWorkflow`：最多 3 次尝试，指数退避（1s → 2s → 4s）

**Agent 日志：** 每个节点的执行结果记录到 `agent_logs` 表，`generation-tasks` API 返回日志摘要供前端展示。

### 6.6 远端产物协议

Agent 生成的每个游戏版本上传到 MinIO，目录结构：

```
yaha-games/
└── games/
    └── {userId}/
        └── {gameId}/
            └── v{version}/
                ├── manifest.json   ← 游戏元信息清单
                ├── index.html      ← 入口 HTML
                ├── *.js            ← 游戏逻辑 bundle
                ├── *.css           ← 样式
                └── assets/         ← 静态资源
```

**manifest.json 结构：**

```json
{
  "gameId": "xxx",
  "version": 1,
  "title": "游戏标题",
  "description": "游戏描述",
  "entryFile": "index.html",
  "runtime": "iframe-html-v1",
  "artifacts": {
    "entry": "index.html",
    "scripts": ["main.js"],
    "styles": ["style.css"],
    "assets": ["assets/*"]
  }
}
```

**Play 页面加载流程：**

1. 请求 `/api/v1/games/{gameId}/play-meta` 获取 `manifestUrl`、`entryUrl`、`artifactBaseUrl`
2. 使用返回的 `entryUrl`（来自 MinIO 公开地址）渲染 `<iframe src="...">`
3. 证明文件**来自远端对象存储**，不是本地写死组件

### 6.7 安全方案

| 风险 | 应对措施 |
|------|----------|
| 用户上传素材安全 | 素材上传到 MinIO，URL 可配置白名单域名过滤 |
| Prompt Injection | SupervisorAgent 审查输入内容，拒绝恶意 prompt |
| 任意代码执行 | Play 页面使用 `<iframe sandbox="allow-scripts allow-pointer-lock">`，禁止父页面访问 iframe 内部 |
| 密钥泄漏 | `.env` 不提交，仅 `.env.example` 提交；生产环境使用环境变量或密钥管理服务 |
| LLM 输出不稳定 | Validator 验证 + RetryWorkflow 最多 3 次重试 |
| 资源耗尽 | `MOCK_AGENT_MODE=true` 降级为模板生成；LLM 超时 300s 限制 |

### 6.8 失败恢复

| 失败场景 | 恢复策略 |
|---|---|
| **LLM 输出不稳定 / 生成代码报错** | `Validator` 验证失败 → `RetryWorkflow` 最多 3 次重试（指数退避 2s→4s→8s），每次重试重新调用 `CodeGenerator` |
| **构建失败（超时 300s）** | `CodeGenerator` 超时直接标记任务 FAILED，记录 `errorMessage`；前端展示错误原因 |
| **MinIO 上传失败** | `UploadWorkflow` 重试 3 次（1s→2s→4s）；3 次均失败则任务状态回退为 FAILED，不写入 `GameVersion` |
| **发布失败（网络抖动）** | 前端 `/publish` 接口幂等，重复调用不会重复发布；后端检查游戏状态已 PUBLISHED 则直接返回成功 |
| **Play 页面加载失败（iframe 跨域/MinIO bucket private）** | Play 页面展示友好错误状态（加载失败提示），`PlayEvent` 记录 `load_failed` 事件；支持 Presigned URL fallback（实现中） |
| **数据库写入失败（事务回滚）** | FastAPI 使用 `async with` 事务上下文，异常自动回滚；`GameVersion` 和 `GenerationTask` 在同一事务中写入，保证一致性 |
| **Agent 进程崩溃 / 服务重启** | 生成任务状态仍为 RUNNING，前端轮询时显示超时提示|

### 6.9 可观测性

#### Agent 执行链路追踪（LangSmith）

Agent Service 集成 LangSmith，所有节点（SupervisorAgent、VisionAgent、GameplayAgent、NarrativeAgent、SynthesisAgent、CodeGenerator、Validator）执行时自动上报 trace。

| LangSmith 记录内容 | 说明 |
|---|---|
| **节点输入/输出** | 每个 Agent 节点的 prompt 和完整 response |
| **Token 消耗** | 各节点 LLM 调用的 token 用量 |
| **执行时长** | 节点级别和端到端延迟 |
| **重试记录** | RetryWorkflow 的每次重试及结果 |
| **错误日志** | 节点异常信息、LLM 返回的错误内容 |

启用方式：在 `services/agent-service/.env` 中设置 `LANGSMITH_TRACING=true` 并填入 `LANGSMITH_API_KEY`。

#### 结构化日志（AgentLog 表）

所有 Agent 节点执行结果写入 `agent_logs` 表，供前端展示实时进度：

```typescript
// GET /api/v1/generation-tasks/:taskId 返回结构
{
  taskId: string;
  status: "PENDING" | "RUNNING" | "SUCCEEDED" | "FAILED";
  agentLogs: [
    { agentName: "SupervisorAgent", step: 1, message: "需求审查通过" },
    { agentName: "VisionAgent",    step: 2, message: "素材分析完成", rawPayload: {...} },
    { agentName: "GameplayAgent", step: 3, message: "玩法设计完成" },
    { agentName: "NarrativeAgent",step: 4, message: "叙事设计完成" },
    { agentName: "CodeGenerator", step: 5, message: "代码生成完成" },
    { agentName: "Validator",     step: 6, message: "验证通过" },
  ];
}
```

#### Play 事件埋点（PlayEvent 表）

Play 页面加载后自动上报事件到 `/api/v1/play-events`，记录到数据库：

| 事件类型 | 触发时机 | 用途 |
|---|---|---|
| `load_start` | iframe 开始加载 | 统计游戏曝光 |
| `load_success` | iframe `onLoad` 触发 | 统计真实可玩数（区别于曝光） |
| `load_failed` | iframe `onError` 触发 | 定位加载失败原因（bucket 权限/文件损坏/网络） |
| `play_start` | 用户首次点击游戏画面 | 统计真实游玩数 |

#### 数据库可观测性

| 监控指标 | 实现方式 |
|---|---|
| 慢查询追踪 | Prisma 日志级别设为 query；生产环境建议接入 PgBouncer + Prometheus `pg_exporter` |
| 连接池状态 | Prisma `DATABASE_URL` 可配置连接池参数；PgBouncer 可观察 active/cl idle 连接数 |
| 任务积压监控 | `generation_tasks` 表 status=RUNNING 数量超过阈值（如 20）触发告警 |

### 6.10 已知问题

| # | 问题 | 状态 | 备注 |
|---|------|------|------|
| 1 | Play iframe 无法加载（MinIO bucket 未配置 public 策略） | 需修复 | MinIO bucket 需配置公开读取策略，或使用 Presigned URL |
| 2 | LLM Provider 依赖外部 API | 已知 | 已在 .env.example 中说明可切换 Provider |
| 3 | 无第三方登录真实接入 | 已知 | OAuthAccount 模型已设计，接入设计见技术栈说明 |
| 4 | Agent 生成失败后无明确用户引导 | 待优化 | 错误信息需更友好地展示给用户 |

---

## 7. 技术栈

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| **前端框架** | Next.js 16.2.9 | React 19, App Router, TypeScript 5 |
| **UI 样式** | Tailwind CSS v4 + @tailwindcss/postcss | 原子化 CSS，Zinc 暗色主题 |
| **前端状态** | React Hooks + Next.js Server Components | SSR 优先，减少客户端 JS |
| **后端框架** | FastAPI (Python 3.12+) | ASGI 高性能异步框架 |
| **Agent 框架** | LangGraph 0.2+ | 状态图编排 Multi-Agent 工作流 |
| **LLM 客户端** | 自研 `app.llm.client.LLMClient` | 支持多 Provider 切换（OpenAI Compatible / Anthropic / Fighting 等） |
| **模型服务** | Fighting API (可配置) | 参见 `LLM_PROVIDER` 环境变量 |
| **数据库** | PostgreSQL 16 | via Prisma ORM 7 |
| **ORM** | Prisma 7 + @prisma/adapter-pg | 类型安全数据库访问 |
| **对象存储** | MinIO (S3 兼容) | Docker Compose 一键启动，端口 9000/9001 |
| **可观测性** | LangSmith | 完整 Agent 执行链路追踪 |
| **部署方式** | Docker Compose（基础设施）+ 手动启动服务 | 开发/测试阶段；生产推荐 K8s 或云服务 |

**扩展设计 — 第三方登录（OAuth）：**

- 数据模型已实现 `OAuthAccount` 表，支持 provider + providerAccountId 唯一约束
- Google / GitHub OAuth 需要：注册 OAuth App → 获取 client_id/client_secret → 实现回调路由
- 参考 NextAuth.js 或自实现 `/api/v1/auth/oauth/:provider/callback` 端点
- 当前阶段未真实接入，仅提供数据模型和扩展设计

---

## 8. 完成度说明

### 已完成 ✅

| 模块 | 功能 | 状态 |
|------|------|------|
| **Auth** | 邮箱注册、登录、会话管理、退出 | ✅ 完整 |
| **Home** | 首页展示所有 PUBLISHED 游戏，卡片包含标题/描述/作者/标签/时间 | ✅ 完整 |
| **Play** | 动态加载 MinIO 远端 iframe，支持加载中/成功/失败状态 | ✅ 完整 |
| **Create** | 多模态输入（文字+文件上传），触发 Agent 生成任务，展示进度和日志 | ✅ 完整 |
| **Agent Service** | LangGraph Multi-Agent（Supervisor → Specialist Fan-Out → Synthesis → CodeGen → Validator → Upload），支持重试 | ✅ 完整 |
| **Play 埋点** | load_start / load_success / load_failed / play_start 事件记录到数据库 | ✅ 完整 |
| **数据模型** | User/Game/GameVersion/Asset/GenerationTask/AgentLog/PlayEvent 完整建模 | ✅ 完整 |
| **对象存储** | MinIO 集成，素材上传 + 游戏产物上传 | ✅ 完整 |
| **SSE 实时推送** | 前端 Create 页面通过 `EventSource` 订阅 `/api/v1/generation-tasks/:taskId/stream`，Next.js 每 600ms 轮询数据库推送 Agent 日志到浏览器，实现生成进度的实时展示 | ✅ 完整 |

### 部分完成 / Mock ⚠️

| 模块 | 状态 | 说明 |
|------|------|------|
| **Play iframe 实际加载** | ⚠️ MinIO bucket public policy 已实现，Presigned URL fallback 未实现 | `storage.ts` 已调用 `PutBucketPolicyCommand` 设置 public read；如需私有 bucket 场景需补充 Presigned URL 降级逻辑 |
| **第三方登录** | ⚠️ 数据模型已设计，未真实接入 | OAuthAccount 表存在，但 `/api/v1/auth/oauth/*` 路由未实现 |
| **Create 生成游戏可游玩** | ⚠️ 依赖 LLM API 实际调用 | 如 LLM API 不可用，可开启 `MOCK_AGENT_MODE=true` 使用模板生成 |

### 未完成 ❌

| 模块 | 说明 |
|------|------|
| **搜索/筛选** | 首页无游戏搜索和标签筛选功能 |
| **点赞/收藏** | Home 无点赞、收藏、游玩次数统计展示 |
| **版本管理** | 无 UI 展示历史版本列表 |
| **Remix 派生** | 可基于已有游戏重新生成，但无 UI 引导 |
| **内容审核** | 无自动内容审核流程 |
| **自动化测试** | Agent Service 有单元测试（pytest），前端无 E2E 测试 |

### 如再给 1 周的迭代计划

#### 一、Agent 微服务（LangGraph 深度增强）

| 优先级 | 功能 | 价值 | 状态 |
| --- | --- | --- | --- |
| P0 | **持久化检查点（Redis Saver）** | 生成中途崩溃可恢复，无需从头开始 | 待实现 |
| P0 | **请求取消（Request Cancellation）** | 客户端断连时立即停止 Agent 工作，节省资源 | 待实现 |
| P0 | **背景 Worker 模式** | `/generate` 立即返回 taskId，后台执行，前端轮询结果 | 待实现 |
| P1 | **Human-in-the-Loop 中断** | 设计规范输出后插入 `interrupt()`，用户确认后再生成代码 | 待实现 |
| P1 | **LLM Token 级流式输出** | 将节点完成度 SSE 升级为逐 token 流式，可实现实时看到生成流 | 待实现 |
| P1 | **原生 Structured Output** | 改用 OpenAI `response_format=json_schema` / Anthropic Tool Use，替代 prompt-based JSON，提升解析成功率 | 待实现 |
| P2 | **Prometheus 可观测性** | Token 用量、端到端延迟、错误率、并发任务数等指标看板 | 待实现 |
| P2 | **多轮对话 Session Memory** | 同一用户多轮迭代同一游戏时，Agent 保留上下文记忆 | 待实现 |
| P3 | **Redis Queue / RabbitMQ 任务队列** | 高并发下安全调用 Agent（削峰填谷、防雪崩），支持 worker 水平扩展 | 待实现 |
| P3 | **LangChain Tool Calling** | 将 Specialist Agent 迁移至 `@tool` / `tool_definitions`，获得 schema 校验和工具调用协议 | 待实现 |
| P3 | **增强内容安全过滤** | Prompt 注入检测、生成内容 LLM-based 安全分类器（NSFW/恶意代码） | 待实现 |
| P4 | **Docker 沙箱执行生成代码** | Agent 生成过程在临时 Docker 容器中隔离执行，杜绝危险操作 | 待实现 |

#### 二、前端 + 后端（Web App）

| 优先级 | 功能 | 价值 | 状态 |
| --- | --- | --- | --- |
| P0 | **Play iframe Presigned URL fallback** | 若生产环境要求私有 bucket，需在 play-meta API 和前端补充 Presigned URL 生成与降级逻辑，确保 iframe 仍可加载 | 待实现 |
| P0 | **搜索 + 标签筛选** | 首页游戏发现体验升级，支持模糊搜索和多标签过滤 | 待实现 |
| P1 | **Playwright E2E 测试** | 覆盖登录 → Create → 发布 → Play 全链路冒烟测试 | 待实现 |
| P1 | **Google OAuth / GitHub OAuth** | 降低注册门槛，社交账号一键登录 | 待实现 |
| P1 | **游玩次数统计 + 排行榜** | Play 加载成功后上报事件，首页展示最热游戏 | 待实现 |
| P1 | **点赞 / 收藏功能** | 用户粘性提升，支持个人游戏库 | 待实现 |
| P2 | **MinIO 迁移至真实 OSS** | 开发阶段用 MinIO，生产环境切换至阿里云 OSS / AWS S3，支持 CDN 接入和跨地域复制 | 待实现 |
| P2 | **Redis 缓存层** | 热门游戏列表、用户 Session 缓存，降低数据库压力 | 待实现 |
| P2 | **CDN 托管静态资源** | 生成的游戏文件走 CDN，分担 MinIO 流量，提升加载速度 | 待实现 |
| P2 | **数据库连接池调优** | PgBouncer 或 Prisma Data Proxy，减少连接开销 | 待实现 |
| P2 | **API 限流（Rate Limiting）** | 针对 `/generate` 等高消耗接口按用户/IP 限流，防滥用 | 待实现 |
| P3 | **任务历史 + 重试 UI** | Create 页面展示历史任务，失败任务支持一键重试 | 待实现 |
| P3 | **游戏版本管理** | 同一游戏多次生成自动保存历史版本，支持回滚 | 待实现 |
| P3 | **Docker Compose 生产部署文档** | 补充反向代理（Nginx/Traefik）、HTTPS、自动证书续期说明 | 待实现 |
| P4 | **前端性能优化** | 首页 SSR/ISR、代码分割、懒加载、图片 WebP 压缩 | 待实现 |

---

## 9. 测试与验证证据（可选）

### 已执行的验证

| 验证项 | 命令/方式 | 结果 |
|--------|----------|------|
| 数据库表创建 | `pnpm prisma db push` | ✅ 所有表创建成功 |
| Seed 数据写入 | `pnpm prisma db seed` | ✅ 3 个游戏 + demo 用户写入成功 |
| 前端构建 | `pnpm build` | ✅ 无错误 |
| 前端开发服务器 | `pnpm dev` | ✅ http://localhost:4000 可访问 |
| Agent Service 启动 | `uv run uvicorn app.main:app --host 127.0.0.1 --port 8000` | ✅ http://localhost:8000/docs 可访问 |
| Play Meta API | `curl http://localhost:4000/api/v1/games/{id}/play-meta` | ✅ 返回 manifestUrl/entryUrl |
| 登录流程 | 手动测试注册/登录/退出 | ✅ Session 正确写入数据库 |
| Create 流程 | 手动测试输入创意，触发生成任务 | ✅ 任务状态流转正确 |

### 验证脚本

```bash
# apps/web/
pnpm verify:play-events       # 验证 play events 埋点
pnpm verify:generation-tasks  # 验证 generation tasks API
pnpm verify:v38-db-write      # 验证数据库写入
pnpm verify:v39-preview-publish # 验证草稿预览和发布流程
```

### 关键日志路径

- Agent Service 日志：`services/agent-service/`（stdout）
- LangSmith 追踪：https://smith.langchain.com/（需 API Key）
- 数据库验证脚本：`apps/web/scripts/verify-*.ts`

---

## 10. 演示视频（可选）

已经制作《YAHA项目演示.docx》在文件夹中，

---

## 11. AI 协作记录（可选）

| 项目 | 说明 |
|------|------|
| **AI 工具** | Claude Code (Cursor), GitHub Copilot，Hermes |
| **贡献比例** | AI 辅助约 70%，人工 review 和修复约 30% |
| **关键 Prompt 示例** | "用 LangGraph 实现游戏生成的 Multi-Agent 状态图，包含 Supervisor / Specialist Fan-Out / Validator / Upload 节点" |
| **典型人工修复** | 1、Agent编排问题，需要确认是否使用官方文档，以及是否多造轮子，有不合适的设计；2、AI写的前端考虑不周到；3、AI进行项目规划还是有偏差，需仔细对照思考；4、数据库设计调整|
| **Review 方法** | Claude Code 逐模块 review + 本地人工验证完整链路 |
| **测试方法** | 部分单元测试、集成测试；脚本验证 DB 写入 + 手动 E2E 验证全流程 |

---

## 附录：文件结构概览

```
yaha-ai-game-platform/
├── docker-compose.yml              ← 基础设施（PostgreSQL + MinIO）
├── apps/
│   └── web/                        ← Next.js 前端
│       ├── prisma/
│       │   ├── schema.prisma       ← 数据模型
│       │   └── seed.ts             ← 测试数据
│       ├── .env.example            ← 前端环境变量模板
│       ├── app/
│       │   ├── page.tsx            ← Home 首页
│       │   ├── create/page.tsx     ← Create 创作页
│       │   ├── play/[gameId]/      ← Play 游玩页
│       │   ├── register/page.tsx   ← 注册页
│       │   └── api/v1/             ← REST API 路由
│       └── components/             ← React 组件
└── services/
    └── agent-service/              ← FastAPI Agent 后端
        ├── .env.example            ← Agent 环境变量模板
        ├── app/
        │   ├── main.py             ← FastAPI 入口
        │   ├── agent/
        │   │   ├── graph.py        ← LangGraph 状态图
        │   │   ├── state.py        ← 状态定义
        │   │   ├── nodes/          ← 各 Agent 节点
        │   │   └── edges.py        ← 边路由逻辑
        │   └── llm/                ← LLM 客户端
        └── pyproject.toml
```
