# Yaha互动游戏平台技术方案

> 目标：基于 `yaha游戏平台开发任务.md` 和 `yaha游戏平台需求分析文档.md`，给出一套 2 天内可落地的“Next.js 全栈业务主应用 + FastAPI/Python Agent 微服务”MVP 方案。  
> 核心原则：Next.js 承担产品页面、Auth、业务 API、数据库和对象存储元信息；FastAPI 只承担 Python 更擅长的 Agent 编排、游戏文件生成和产物校验。  
> 关键闭环：注册/登录 → 输入创意和上传素材 → Next.js 创建生成任务 → HTTP 调 FastAPI Agent → Python 生成游戏文件并上传 MinIO → Next.js 写入 PostgreSQL → 预览发布 → 首页展示 → Play 页面远端加载运行。

---

## 1. 技术方案总览

### 1.1 最终推荐技术栈

| 层级 | 技术 | 用途 |
| --- | --- | --- |
| Web 主应用 | Next.js 14/15 + React + TypeScript | Home、Auth、Create、Play、业务 API |
| 前端 UI | Tailwind CSS + shadcn/ui | 快速搭建可演示界面 |
| 业务 API | Next.js Route Handlers / Server Actions | 用户、游戏、任务、发布、Play meta、埋点 |
| 数据校验 | Zod + Pydantic v2 | Next.js 校验业务请求；FastAPI 校验 Agent 请求/响应 |
| 数据库 | PostgreSQL | 用户、游戏、版本、素材、任务、日志、埋点 |
| ORM / 迁移 | Prisma | Next.js 主应用统一管理核心业务数据 |
| 认证 | Better Auth / Auth.js / Cookie Session | 邮箱注册、登录、退出、受保护页面 |
| 对象存储 | MinIO | 本地 S3 兼容对象存储 |
| 对象存储 SDK | AWS SDK v3；Python 可选 boto3 | Next.js 管素材和元信息；Python 可上传 Agent 产物 |
| Agent 微服务 | FastAPI + Python 3.11+ | Agent 编排、模型调用、文件生成、产物校验 |
| **Agent 编排** | **LangGraph StateGraph（已实现，超出原计划）** | **Supervisor → Specialist → Template → CodeGen → Validator → Upload 完整图工作流** |
| **Agent 流式接口** | **FastAPI SSE（已实现，超出原计划）** | **/generate/stream 实时推送每个节点日志，前端增量写入 DB** |
| **LLM 客户端** | **独立 app/llm/ 模块（已实现，超出原计划）** | **OpenAI 兼容接口，多模型支持，完整降级策略** |
| **可观测性** | **LangSmith（已实现，超出原计划）** | **完整 trace，API Key 可配置** |
| 异步任务 | MVP 用任务表 + HTTP 调 FastAPI；增强版 RabbitMQ / Redis Queue | 2 天内先降低复杂度，后续借鉴 HyperHit 演进 |
| 游戏产物 | HTML + CSS + Vanilla JS + manifest.json | 最容易远端加载和 iframe 运行 |
| 运行隔离 | iframe sandbox + 产物静态校验 | MVP 安全隔离 |
| 部署 | Docker Compose | 一键启动 web、agent-service、postgres、minio |
| 测试 | Vitest/Playwright + pytest/httpx | Web 主应用和 Agent 服务分别验证 |

### 1.2 为什么采用混合架构

HyperHit 的可借鉴点是：Node/Next.js 做业务编排和数据中心，Python 做 AI/重计算服务。Yaha 也适合类似分层：

1. Auth、Home、Game、Task、Play、发布状态等常规业务放 Next.js，开发闭环更快。
2. Agent 编排、模型调用、文件生成、产物校验放 Python，更符合你的熟悉方向。
3. PostgreSQL 由 Prisma 统一管理，避免 Next.js 和 FastAPI 双 ORM 同时维护业务表。
4. MVP 用 HTTP 调 FastAPI，简单可控；后续再升级 RabbitMQ / Redis Queue。
5. 面试讲法更成熟：业务主应用 + AI Agent 微服务，而不是两个后端职责混杂。

### 1.3 本方案的取舍

| 取舍 | 决策 |
| --- | --- |
| 业务后端放哪里 | 放 Next.js 主应用，使用 Route Handlers / Server Actions |
| Python 服务负责什么 | 只负责 Agent、模型调用、游戏文件生成、产物校验 |
| 是否一开始上 RabbitMQ | 不强制。MVP 用 HTTP，后续增强再上队列 |
| 是否真实 LLM 生成任意代码 | 不建议第一版依赖。先模板生成，保留真实 LLM 接口 |
| 是否用本地文件代替对象存储 | 不允许。必须用 MinIO/S3 兼容边界 |

---

## 2. 系统架构

```text
Browser
  │
  ▼
Next.js Web 主应用
  │
  ├─ Pages
  │   ├─ Home（/）：展示 published 游戏
  │   ├─ Login（/login）：登录
  │   ├─ Register（/register）：注册
  │   ├─ Create（/create）：输入创意、上传素材、查看 Agent 日志
  │   ├─ Play（/play/[gameId]）：iframe sandbox 加载远端游戏
  │   └─ Games（/games）：我的游戏列表
  │
  ├─ Route Handlers
  │   ├─ Auth（/api/v1/auth/[...auth]）：注册、登录、退出、当前用户
  │   ├─ Games（/api/v1/games、[gameId]）：游戏列表、详情、发布、play-meta
  │   ├─ Assets（/api/v1/assets/upload）：素材上传到 MinIO
  │   ├─ Generation Tasks（/api/v1/generation-tasks、[taskId]）：创建、轮询、日志
  │   ├─ Generation Tasks Stream（/api/v1/generation-tasks/[taskId]/stream）：SSE 轮询
  │   └─ Play Events（/api/v1/play-events）：记录加载和游玩事件
  │
  ├─ Prisma → PostgreSQL
  ├─ AWS SDK v3 → MinIO
  ├─ AgentClient → FastAPI SSE + sync fallback
  └─ LangSmith（可选，可观测性）

FastAPI / Python Agent Service
  │
  ├─ POST /generate（同步）
  ├─ POST /generate/stream（SSE 流式）
  ├─ GET /health
  │
  ├─ LangGraph StateGraph
  │   │
  │   ├─ SupervisorAgent：意图分类（LLM）
  │   │   → approved_simple → TemplateWorkflow
  │   │   → approved_complex → FanOut（并行 Specialist）
  │   │   → rejected → 返回拒绝反馈
  │   │
  │   ├─ SpecialistFanOut（并行执行）
  │   │   ├─ VisionAgent（LLM）：视觉规范
  │   │   ├─ NarrativeAgent（LLM）：叙事规范
  │   │   └─ GameplayAgent（LLM）：游戏机制
  │   │
  │   ├─ SynthesisAgent（LLM）：整合 Specialist 结果
  │   ├─ CodeGeneratorNode：生成 HTML/CSS/JS/manifest
  │   ├─ ValidatorNode：产物安全校验（危险 API 拦截）
  │   ├─ UploadWorkflow：上传 MinIO
  │   └─ RetryWorkflow：失败重试（可选）
  │
  ├─ app/llm/（LLM 客户端，支持 OpenAI 兼容接口）
  ├─ Pydantic schemas（GenerateRequest/Response）
  └─ LangSmith 集成（可选）

PostgreSQL（用户、游戏、版本、素材、任务、日志、埋点）
MinIO（uploaded-assets/、game-bundles/）
```

### 2.1 模块边界

| 模块 | 责任 |
| --- | --- |
| Next.js 页面 | 展示、表单、轮询任务、iframe 播放 |
| Next.js 业务 API | Auth、Game、Asset、Task、Play Event、数据库写入 |
| Prisma 层 | 唯一业务数据库模型和迁移来源 |
| Storage 层 | Next.js 封装 MinIO 上传、公开 URL 和产物 meta |
| AgentClient | Next.js 调 FastAPI 的内部客户端 |
| FastAPI Agent 服务 | 接收生成请求，运行 Python Agent，返回产物结果 |
| Runtime 层 | Play 只使用远端 manifest/bundle，不硬编码游戏 |

---

## 3. 项目目录结构

```text
yaha-ai-game-platform/
  apps/
    web/
      app/
        page.tsx
        layout.tsx
        globals.css
        login/page.tsx
        register/page.tsx
        create/page.tsx
        play/[gameId]/page.tsx
        api/
          auth/...
          games/...
          assets/...
          generation-tasks/...
          play-events/...
      components/
        site-header.tsx
        game-card.tsx
        create-form.tsx
        task-progress.tsx
        agent-log-list.tsx
        game-player.tsx
      lib/
        auth.ts
        prisma.ts
        storage.ts
        agent-client.ts
        types.ts
      prisma/
        schema.prisma
        migrations/
        seed.ts
      public/
        placeholder-cover.svg
      package.json
      next.config.ts
      .env.example

  services/
    agent-service/
      app/
        main.py
        core/
          config.py
        schemas/
          generate.py
        agent/
          orchestrator.py
          state.py
          agents.py
          builder.py
          validator.py
          storage.py
          templates/
            click_challenge.py
            avoid_obstacle.py
            quiz_game.py
      tests/
        test_generate.py
        test_validator.py
      pyproject.toml
      .env.example

  docs/
    system-design.md
    completion-report.md
    ai-collaboration.md
    manual-test-checklist.md

  docker-compose.yml
  package.json
  pnpm-workspace.yaml
  README.md
```

---

## 4. 数据库模型

### 4.1 表结构

数据库由 Next.js 主应用通过 Prisma 统一管理。FastAPI Agent 服务不直接维护业务表，避免双 ORM 和跨服务事务复杂度。

| 表 | 用途 |
| --- | --- |
| users | 用户账号 |
| sessions | Cookie Session 登录态 |
| oauth_accounts | Google/GitHub 第三方账号绑定扩展 |
| games | 游戏主表 |
| game_versions | 游戏版本和远端产物地址 |
| assets | 上传素材 |
| generation_tasks | 生成任务 |
| agent_logs | Agent 步骤日志，由 Next.js 持久化 Python 返回的日志 |
| play_events | Play 加载和游玩事件 |

### 4.2 Prisma 模型字段建议

#### users

```text
id: string primary key
email: string unique
password_hash: string
display_name: string nullable
avatar_url: string nullable
provider: string default email
provider_account_id: string nullable
created_at: datetime
updated_at: datetime
```

#### sessions

```text
id: string primary key
token_hash: string unique
user_id: foreign key users.id
expires_at: datetime
created_at: datetime
```

#### oauth_accounts

用于满足原任务中“Google 和 GitHub 第三方登录需要给出数据模型、OAuth 接入设计和后续扩展方式”的加分要求。MVP 可以只保留数据模型和文档设计，不强制真实接入。

```text
id: string primary key
user_id: foreign key users.id
provider: google | github
provider_account_id: string
provider_email: string nullable
access_token_encrypted: text nullable
refresh_token_encrypted: text nullable
created_at: datetime
updated_at: datetime
unique(provider, provider_account_id)
```

OAuth 接入流程设计：

1. 前端点击 `Continue with GitHub/Google`。
2. Next.js 主应用生成 state，跳转第三方授权页。
3. 第三方回调 `/api/v1/auth/oauth/{provider}/callback`。
4. Next.js 主应用校验 state，用 code 换 token。
5. 获取第三方用户信息。
6. 根据 `provider + provider_account_id` 查找 `oauth_accounts`。
7. 如果已绑定，直接创建 session。
8. 如果未绑定但邮箱已存在，可提示登录后绑定。
9. 如果是新用户，创建 users 和 oauth_accounts，再创建 session。

#### games

```text
id: string primary key
author_id: foreign key users.id
title: string
description: text
cover_url: string nullable
tags: json / array
status: draft | published | archived
latest_version_id: foreign key game_versions.id nullable
play_count: int
published_at: datetime nullable
created_at: datetime
updated_at: datetime
```

#### game_versions

```text
id: string primary key
game_id: foreign key games.id
version: int
manifest_url: string
bundle_base_url: string
entry_file: string default index.html
runtime: string default iframe-html-v1
source_task_id: foreign key generation_tasks.id nullable
created_at: datetime
```

#### assets

```text
id: string primary key
owner_id: foreign key users.id
task_id: foreign key generation_tasks.id nullable
file_name: string
mime_type: string
size: int
object_key: string
public_url: string
created_at: datetime
```

#### generation_tasks

```text
id: string primary key
user_id: foreign key users.id
prompt: text
status: pending | running | succeeded | failed
current_step: string nullable
result_game_id: string nullable
result_version_id: string nullable
error_message: text nullable
created_at: datetime
updated_at: datetime
```

#### agent_logs

```text
id: string primary key
task_id: foreign key generation_tasks.id
agent_name: string
step: string
message: text
raw_payload: json nullable
created_at: datetime
```

#### play_events

```text
id: string primary key
game_id: foreign key games.id
version_id: foreign key game_versions.id nullable
user_id: foreign key users.id nullable
event_name: string
metadata: json nullable
created_at: datetime
```

---

## 5. API 设计

外部业务 API 统一由 Next.js 主应用提供，前缀建议：`/api/v1`。FastAPI Agent 服务不对浏览器开放，只提供内部接口给 Next.js 调用。

### 5.1 Auth

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/auth/register` | 邮箱注册 |
| POST | `/api/v1/auth/login` | 邮箱登录 |
| POST | `/api/v1/auth/logout` | 退出登录 |
| GET | `/api/v1/auth/me` | 获取当前用户 |

### 5.2 Games

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/games` | 获取 published 游戏列表，支持 `q`、`tag`、`sort` 查询参数 |
| GET | `/api/v1/games/{game_id}` | 获取游戏详情 |
| POST | `/api/v1/games/{game_id}/publish` | 发布游戏 |
| GET | `/api/v1/games/{game_id}/play-meta` | 获取 Play 运行所需 meta |
| POST | `/api/v1/games/{game_id}/like` | 点赞，加分项，可后置 |
| POST | `/api/v1/games/{game_id}/favorite` | 收藏，加分项，可后置 |

`GET /api/v1/games` 的 MVP 查询参数：

```text
q: 按标题/简介模糊搜索，可选
tag: 按标签筛选，可选
sort: latest | popular，默认 latest
```

2 天内如果时间紧，必须完成列表和详情；搜索、标签筛选、点赞、收藏可以作为加分项或后续一周计划。

### 5.3 Assets

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/assets/upload` | 上传素材到 MinIO |

请求类型：`multipart/form-data`

字段：

```text
file: 上传文件
task_id: 可选
```

### 5.4 Generation Tasks

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/generation-tasks` | 创建生成任务 |
| GET | `/api/v1/generation-tasks` | 获取当前用户生成任务历史，加分项但建议实现 |
| GET | `/api/v1/generation-tasks/{task_id}` | 查询任务状态 |
| GET | `/api/v1/generation-tasks/{task_id}/logs` | 查询 Agent 日志 |
| POST | `/api/v1/generation-tasks/{task_id}/retry` | 重试任务，加分项 |

任务历史列表建议在 Create 页面右侧展示最近 10 条，能体现“生成任务历史”和“Agent 执行日志”能力。

### 5.5 Play Events

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/play-events` | 上报 play_start、load_success、load_failed |

### 5.6 内部 Agent API

| 方法 | 路径 | 提供方 | 说明 |
| --- | --- | --- | --- |
| POST | `/generate` | FastAPI Agent Service | 根据任务输入生成游戏产物，返回 manifest、文件列表、日志和错误信息 |

Next.js 调用 `/generate` 的推荐流程：

1. Next.js 创建 `generation_tasks`，状态为 `running`。
2. Next.js 收集 prompt、素材 URL、用户信息和 task_id。
3. Next.js 使用 `AgentClient` 通过内网地址调用 FastAPI `/generate`。
4. FastAPI 返回生成产物、Agent 日志、校验结果、可选 MinIO object keys。
5. Next.js 持久化 `agent_logs`、`games`、`game_versions`，并更新任务状态。

---

## 6. 对象存储和产物协议

### 6.1 Bucket

使用一个 bucket：`yaha`

```text
yaha/
  uploaded-assets/
    {user_id}/{asset_id}/{filename}

  game-bundles/
    games/{game_id}/versions/{version_id}/
      manifest.json
      index.html
      style.css
      game.js
      assets/
        cover.png
```

### 6.2 manifest.json

```json
{
  "schemaVersion": "1.0",
  "runtime": "iframe-html-v1",
  "entry": "index.html",
  "title": "星际点击挑战",
  "description": "30 秒内点击星星得分",
  "files": ["index.html", "style.css", "game.js"],
  "assets": ["assets/cover.png"],
  "createdBy": "yaha-python-agent"
}
```

### 6.3 Play 加载流程

1. 前端进入 `/play/{gameId}`。
2. 请求 `GET /api/v1/games/{gameId}/play-meta`。
3. Next.js 返回 `manifest_url`、`bundle_base_url`、`entry_file`。
4. 前端 fetch manifest，展示远端产物地址。
5. iframe 加载 `${bundle_base_url}/${entry_file}`。
6. iframe 成功加载后上报 `load_success`。
7. 失败时展示错误态并上报 `load_failed`。

iframe 建议：

```tsx
<iframe
  src={entryUrl}
  sandbox="allow-scripts allow-pointer-lock"
  className="h-[720px] w-full rounded-xl border"
/>
```

---

## 7. Agent 编排

### 7.0 实际实现的 LangGraph 架构

当前实现已超出原计划的"自研状态机"，升级为基于 LangGraph 的显式图工作流：

```text
GenerateRequest
     │
     ▼
SupervisorAgent（LLM）
     │
     ├─ status=rejected → 返回 supervisor_feedback，终止
     │
     ├─ status=approved_simple → TemplateWorkflow
     │                            ├─ GameDesignAgent（基于模板生成）
     │                            ├─ CodeGeneratorNode
     │                            ├─ ValidatorNode（危险 API 校验）
     │                            └─ UploadWorkflow（上传 MinIO）
     │
     └─ status=approved_complex → SpecialistFanOut（并行 Specialist）
                                   ├─ VisionAgent（LLM）
                                   ├─ NarrativeAgent（LLM）
                                   └─ GameplayAgent（LLM）
                                   └─ SynthesisAgent（LLM，整合 Specialist 结果）
                                   └─ CodeGeneratorNode
                                   └─ ValidatorNode
                                   └─ UploadWorkflow
```

流式日志（通过 `/generate/stream` SSE 推送）：
- 每个节点执行时立即推送新日志
- 前端实时写入数据库 `agent_logs` 表
- 失败时可选 RetryWorkflow 重试

### 7.1 工作流（原计划，供参考）

```text
GenerationTask(pending)
  ↓
RequirementAgent：解析 prompt 和素材
  ↓
GameDesignAgent：选择模板、生成玩法规则
  ↓
CodeGenerationAgent：生成 index.html/style.css/game.js/manifest.json
  ↓
BuildValidateAgent：检查文件完整性和危险 API
  ↓
ArtifactAgent：上传 MinIO 或返回产物给 Next.js
  ↓
Next.js：写入 agent_logs、games、game_versions，更新任务状态
  ↓
GenerationTask(succeeded)
```

### 7.2 游戏生成策略

实际实现使用 LangGraph + Specialist + 模板结合。Supervisor 判断复杂度后路由到不同路径：

**Supervisor 判断规则：**
- LLM 分析用户输入，判断是否有效（排除闲聊/问答）
- 无效 → rejected，返回友好提示
- 简单游戏（<100字符）→ TemplateWorkflow（模板化生成）
- 复杂游戏（>=100字符或独特玩法）→ SpecialistFanOut（并行 Specialist + LLM 生成）

**模板化生成（TemplateWorkflow）：**
|| 模板 | 关键词 | 玩法 |
|| --- | --- | --- |
|| click_challenge | 点击、得分、星星 | 倒计时内点击目标得分 |
|| avoid_obstacle | 躲避、障碍、生存 | 键盘或鼠标躲避障碍 |
|| quiz_game | 问答、选择、知识 | 多选题互动 |

**复杂生成（SpecialistFanOut）：** VisionAgent（视觉）→ NarrativeAgent（叙事）→ GameplayAgent（机制）→ SynthesisAgent（整合）→ CodeGeneratorNode → ValidatorNode → UploadWorkflow

**降级策略：** LLM 调用失败时自动降级为模板化生成；FastAPI 不可用时 Next.js 端有本地 fallback 生成器

| 模板 | 关键词 | 玩法 |
| --- | --- | --- |
| click_challenge | 点击、得分、星星、收集 | 倒计时内点击目标得分 |
| avoid_obstacle | 躲避、障碍、飞船、生存 | 键盘或鼠标躲避障碍 |
| quiz_game | 问答、选择、知识、剧情 | 多选题互动 |

没有匹配关键词时默认使用 `click_challenge`。

### 7.3 日志写入（SSE 流式）

实际实现使用 SSE 流式推送 + 前端实时写入数据库：

1. FastAPI `/generate/stream` 推送每个节点的新日志（SSE `data: {...}\n\n`）
2. Next.js SSE 路由 `/api/v1/generation-tasks/[taskId]/stream` 轮询后端 SSE 并转发给前端
3. 前端收到后立即写入 `agent_logs` 表
4. 每个日志包含：`agent`、`step`、`message`、`timestamp`

```json
{
  "agent_name": "GameDesignAgent",
  "step": "select_template",
  "message": "选择 click_challenge 模板，目标是在 30 秒内点击霓虹星星得分"
}
```

### 7.4 可升级点

当前已实现 LangGraph 完整图工作流，以下为后续增强方向：

- 接入更强大的 LLM 模型（Claude、GPT）
- 扩展 Specialist Agent 数量和能力
- 增加 Docker 沙箱构建和更严格 AST 安全扫描
- 持久化 LangGraph checkpoint，支持断点续跑
- 升级为 RabbitMQ 异步任务总线

---

## 8. 安全方案

### 8.1 上传安全

- 限制文件大小，例如 10MB。
- 限制 MIME 类型：image/png、image/jpeg、video/mp4、text/plain。
- 文件名不直接信任，object key 使用服务端生成 ID。
- 上传素材不直接作为可执行代码运行。

### 8.2 Agent 产物安全（实际实现）

产物校验拦截以下危险模式（完整实现于 `validator.py`）：

```text
# 禁止加载外部脚本
禁止 <script src="http://...">

# 禁止 eval / Function 构造器
禁止 eval()
禁止 Function()

# 禁止动态 Storage key
禁止 localStorage[something]（非字符串常量 key）
禁止 sessionStorage[variable]
禁止 localStorage.getItem(variable) / setItem(variable)

# 禁止主站 Cookie 访问
禁止 document.cookie

# 禁止发起非白名单网络请求
禁止 fetch()（任意 URL）
禁止 XMLHttpRequest

# 产物文件限制
只允许 index.html、style.css、game.js、manifest.json
manifest.json 必须为合法 JSON
manifest entry 必须为 index.html
```

### 8.3 Runtime 安全

- iframe 使用 sandbox。
- 不加 `allow-same-origin`，除非确实需要。
- 生成游戏不允许访问主站 Cookie。
- 真实密钥只在服务端环境变量中存在。

### 8.4 失败恢复设计

| 失败点 | 处理方式 |
| --- | --- |
| RequirementAgent 解析失败 | 使用默认 click_challenge 模板兜底，并写 AgentLog |
| 代码生成缺少文件 | BuildValidateAgent 标记任务 failed，返回缺失文件名 |
| 产物包含危险 API | BuildValidateAgent 拒绝发布，任务 failed |
| MinIO 上传失败 | 捕获异常，任务 failed，保留 error_message，允许 retry |
| 数据库写入失败 | Next.js 使用 Prisma 事务回滚，不产生半成品 game/version |
| 发布失败 | 游戏保持 draft，不进入首页 |
| Play manifest 加载失败 | 前端展示加载失败，并上报 `load_failed` |

### 8.5 内容审核、资源限额和成本统计

| 项目 | MVP 实现 | 后续扩展 |
| --- | --- | --- |
| 内容审核 | prompt 关键词和 MIME 类型拦截 | 接入内容安全 API / 模型审核 |
| 上传限额 | 单文件 10MB，限制文件类型 | 用户级空间配额 |
| 生成限额 | 文档说明或简单限制每日次数 | 按用户套餐/队列限流 |
| 运行限额 | 只允许静态 HTML/CSS/JS | Docker/Firecracker 沙箱 |
| 成本统计 | generation_tasks 预留 `model_tokens`、`estimated_cost` | 接入真实模型后写入实际 token 和费用 |

### 8.6 原任务“不接受项”规避清单

| 原任务不接受项 | 本方案规避方式 |
| --- | --- |
| 只有普通 CRUD，没有 Create Agent 生成链路 | Next.js 创建任务并调用 Python Agent 状态机生成文件、返回日志、上传 MinIO、再入库 |
| Play 只运行本地写死组件 | Play 通过数据库 meta 获取 MinIO manifest/bundle，并 iframe 加载远端 index.html |
| 用本地文件管理替代对象存储 | 使用 MinIO + AWS SDK v3 / boto3，保持 S3/OSS 兼容边界 |
| AI 生成都是固定假数据且不可扩展 | 模板生成只是兜底，Agent 函数保留真实 LLM/LangGraph 接口 |
| 没有 README、无法启动、无法复现 | Docker Compose + `.env.example` + seed + 手工验收文档 |

---

## 9. 从 0 构建项目

### 9.1 准备环境

需要：

- Node.js 20+
- pnpm 9+
- Python 3.11+
- uv 或 poetry
- Docker Desktop
- Git

检查：

```bash
node -v
pnpm -v
python --version
docker -v
git -v
```

### 9.2 创建项目目录

```bash
mkdir yaha-ai-game-platform
cd yaha-ai-game-platform
mkdir -p apps services docs
```

### 9.3 创建 Next.js 主应用

```bash
mkdir -p apps/web
cd apps/web
pnpm create next-app . \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir=false \
  --import-alias "@/*"

pnpm add zod @prisma/client @aws-sdk/client-s3 @aws-sdk/s3-request-presigner
pnpm add -D prisma
pnpm dlx shadcn@latest init
pnpm dlx shadcn@latest add button input card textarea badge progress alert dialog
cd ../..
```

`apps/web/.env.example`：

```env
DATABASE_URL="postgresql://yaha:yaha_password@localhost:5432/yaha_game"
NEXT_PUBLIC_APP_URL="http://localhost:3000"
AUTH_SECRET="replace-with-random-secret"

S3_ENDPOINT_URL="http://localhost:9000"
S3_REGION="us-east-1"
S3_ACCESS_KEY_ID="yaha_minio"
S3_SECRET_ACCESS_KEY="yaha_minio_password"
S3_BUCKET="yaha"
S3_PUBLIC_BASE_URL="http://localhost:9000/yaha"

AGENT_SERVICE_URL="http://localhost:8000"
MOCK_AGENT_MODE="true"
MAX_UPLOAD_SIZE_MB="10"
```

### 9.4 创建 FastAPI Agent 服务

使用 uv：

```bash
mkdir -p services/agent-service
cd services/agent-service
uv init
uv add fastapi uvicorn pydantic-settings python-multipart boto3 httpx pytest pytest-asyncio
uv add --dev ruff mypy
mkdir -p app/{core,schemas,agent/templates} tests
cd ../..
```

如果不用 uv，也可以用 poetry 或 venv + pip。

### 9.5 Docker Compose

根目录 `docker-compose.yml`：

```yaml
services:
  postgres:
    image: postgres:16-alpine
    container_name: yaha-postgres
    environment:
      POSTGRES_USER: yaha
      POSTGRES_PASSWORD: yaha_password
      POSTGRES_DB: yaha_game
    ports:
      - "5432:5432"
    volumes:
      - yaha_postgres_data:/var/lib/postgresql/data

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
      - yaha_minio_data:/data

volumes:
  yaha_postgres_data:
  yaha_minio_data:
```

启动：

```bash
docker compose up -d
```

MinIO 控制台：

```text
http://localhost:9001
账号：yaha_minio
密码：yaha_minio_password
```

创建 bucket：`yaha`，并设置公开读或至少让 `game-bundles` 可读。

### 9.6 环境变量

`apps/web/.env.example`：

```env
DATABASE_URL="postgresql://yaha:yaha_password@localhost:5432/yaha_game"
NEXT_PUBLIC_APP_URL="http://localhost:3000"
AUTH_SECRET="replace-with-random-secret"

S3_ENDPOINT_URL="http://localhost:9000"
S3_REGION="us-east-1"
S3_ACCESS_KEY_ID="yaha_minio"
S3_SECRET_ACCESS_KEY="yaha_minio_password"
S3_BUCKET="yaha"
S3_PUBLIC_BASE_URL="http://localhost:9000/yaha"

AGENT_SERVICE_URL="http://localhost:8000"
MAX_UPLOAD_SIZE_MB="10"
```

`services/agent-service/.env.example`：

```env
APP_ENV="development"
APP_URL="http://localhost:8000"

S3_ENDPOINT_URL="http://localhost:9000"
S3_REGION="us-east-1"
S3_ACCESS_KEY_ID="yaha_minio"
S3_SECRET_ACCESS_KEY="yaha_minio_password"
S3_BUCKET="yaha"
S3_PUBLIC_BASE_URL="http://localhost:9000/yaha"

MOCK_AGENT_MODE="true"
MAX_UPLOAD_SIZE_MB="10"
```

复制：

```bash
cp apps/web/.env.example apps/web/.env.local
cp services/agent-service/.env.example services/agent-service/.env
```

### 9.7 FastAPI Agent 基础文件

`services/agent-service/app/main.py`：

```python
from fastapi import FastAPI

from app.schemas.generate import GenerateRequest, GenerateResponse
from app.agent.orchestrator import generate_game

app = FastAPI(title="Yaha Python Agent Service")

@app.post("/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest) -> GenerateResponse:
    return generate_game(request)

@app.get("/health")
def health():
    return {"status": "ok"}
```

`services/agent-service/app/core/config.py`：

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_url: str = "http://localhost:8000"
    s3_endpoint_url: str
    s3_region: str = "us-east-1"
    s3_access_key_id: str
    s3_secret_access_key: str
    s3_bucket: str
    s3_public_base_url: str

    mock_agent_mode: bool = True
    max_upload_size_mb: int = 10

settings = Settings()
```

`services/agent-service/app/schemas/generate.py`：

```python
from pydantic import BaseModel

class GenerateRequest(BaseModel):
    task_id: str
    prompt: str
    asset_urls: list[str] = []

class AgentLogItem(BaseModel):
    agent_name: str
    step: str
    message: str

class GeneratedFile(BaseModel):
    path: str
    content: str
    content_type: str

class GenerateResponse(BaseModel):
    title: str
    description: str
    manifest: dict
    files: list[GeneratedFile]
    logs: list[AgentLogItem]
```

### 9.8 数据库和 Prisma

初始化：

```bash
cd apps/web
pnpm dlx prisma init
```

在 `apps/web/prisma/schema.prisma` 定义 users、sessions、oauth_accounts、games、game_versions、assets、generation_tasks、agent_logs、play_events。

建模后执行：

```bash
pnpm dlx prisma migrate dev --name init
pnpm dlx prisma db seed
```

### 9.9 Storage 封装

`apps/web/lib/storage.ts` 核心能力：

```ts
import { PutObjectCommand, S3Client } from "@aws-sdk/client-s3";

export const s3 = new S3Client({
  region: process.env.S3_REGION,
  endpoint: process.env.S3_ENDPOINT_URL,
  forcePathStyle: true,
  credentials: {
    accessKeyId: process.env.S3_ACCESS_KEY_ID!,
    secretAccessKey: process.env.S3_SECRET_ACCESS_KEY!,
  },
});

export async function uploadBytes(key: string, body: Buffer, contentType: string) {
  await s3.send(new PutObjectCommand({
    Bucket: process.env.S3_BUCKET!,
    Key: key,
    Body: body,
    ContentType: contentType,
  }));
  return `${process.env.S3_PUBLIC_BASE_URL}/${key}`;
}
```

### 9.10 Auth 实现顺序

文件：

```text
apps/web/lib/auth.ts
apps/web/app/api/auth/...
apps/web/app/login/page.tsx
apps/web/app/register/page.tsx
```

实现：

1. 优先使用 Better Auth / Auth.js Credentials；时间紧可自研 Cookie Session。
2. 登录时生成随机 session token。
3. Prisma 写入 users 和 sessions。
4. Cookie 只保存原始 token，设置 HttpOnly。
5. Server Action / Route Handler 中统一读取当前用户。

### 9.11 Home 和 Play 实现顺序

Next.js 主应用：

```text
apps/web/app/api/games/...
apps/web/app/page.tsx
apps/web/components/game-card.tsx
apps/web/app/play/[gameId]/page.tsx
apps/web/components/game-player.tsx
```

先 seed 两个远端游戏到 MinIO 和 PostgreSQL，确保 Play 链路先跑通。

### 9.12 Create 和 Agent 实现顺序

Next.js 主应用：

```text
apps/web/app/api/assets/...
apps/web/app/api/generation-tasks/...
apps/web/lib/agent-client.ts
apps/web/app/create/page.tsx
apps/web/components/create-form.tsx
apps/web/components/task-progress.tsx
apps/web/components/agent-log-list.tsx
```

FastAPI Agent 服务：

```text
services/agent-service/app/main.py
services/agent-service/app/agent/orchestrator.py
services/agent-service/app/agent/templates/click_challenge.py
```

流程：

1. 上传素材到 `/api/v1/assets/upload`。
2. 创建任务 `/api/v1/generation-tasks`。
3. Next.js Route Handler 通过 `AgentClient` 调 FastAPI `/generate`。
4. Next.js 持久化 Agent 日志、上传/确认 bundle、写入 game_version。
5. 前端每 2 秒轮询任务和日志，成功后展示预览和发布按钮。

---

## 10. 开发顺序

### 阶段 1：基础设施

目标：web、agent-service、postgres、minio 都能启动。

验收：

- `http://localhost:3000` 打开前端。
- `http://localhost:8000/health` 返回 ok。
- `http://localhost:8000/docs` 能看到 Agent Service OpenAPI。
- `http://localhost:9001` 能打开 MinIO。
- Prisma 能创建表并 seed 数据。

### 阶段 2：Auth

目标：注册、登录、退出和受保护接口。

验收：

- 注册后 users 表出现记录。
- 登录后浏览器有 HttpOnly Cookie。
- `/api/v1/auth/me` 返回当前用户。
- 未登录访问 Create 时前端跳登录。

### 阶段 3：Home + Play

目标：先证明远端产物加载可用。

验收：

- MinIO 中存在 seed 游戏 bundle。
- games/game_versions 表有对应 meta。
- 首页展示 published 游戏。
- Play iframe 加载 MinIO 的 `index.html`。
- 页面显示 manifest URL 或 bundle URL。

### 阶段 4：Create + Agent

目标：输入创意后生成真实文件并上传。

验收：

- Create 能上传素材。
- 创建 generation task 后状态从 pending 到 running。
- agent_logs 持续写入。
- MinIO 出现新 bundle。
- 数据库出现新 game_version。
- 任务 succeeded 后可以预览。

### 阶段 5：发布和交付

目标：满足提交要求。

验收：

- 发布后首页出现 Create 生成的游戏。
- 首页至少 3 个游戏。
- 至少 1 个游戏来自 Create 流程。
- README、`.env.example`、系统设计、完成度说明齐全。

---

## 11. 两天排期

### Day 1 上午

- 初始化 apps/web 和 services/agent-service。
- 配置 Docker Compose、PostgreSQL、MinIO。
- 建 Prisma 模型和 migration。
- 搭 Next.js 主应用、FastAPI Agent `/health`、OpenAPI。

### Day 1 下午

- 完成 Auth。
- 完成 seed 用户和 seed 游戏。
- 完成 Home API 和页面。
- 完成 Play meta API 和 iframe 远端加载。

Day 1 结束必须能演示：登录、首页、Play 远端加载 MinIO 游戏。

### Day 2 上午

- 完成素材上传。
- 完成 generation task 创建和轮询。
- 完成 Python Agent 状态机和日志。
- 完成模板游戏生成。

### Day 2 下午

- 完成 bundle 上传 MinIO。
- 完成写入 game/game_version。
- 完成预览和发布。
- 补 README、系统设计、完成度说明、AI 协作记录。
- 完整录屏或截图验收。

Day 2 结束必须能演示：Create 生成 → 发布 → 首页可见 → Play 动态加载运行。

---

## 12. Git Commit 规划

```bash
git add .
git commit -m "chore: initialize frontend backend infrastructure"

git add .
git commit -m "feat: add auth home and remote play runtime"

git add .
git commit -m "feat: add python agent generation workflow"

git add .
git commit -m "docs: add delivery documents and verification guide"
```

---

## 13. README 启动命令

推荐 README 提供：

```bash
cp apps/web/.env.example apps/web/.env.local
cp services/agent-service/.env.example services/agent-service/.env
docker compose up -d
cd apps/web && pnpm install && pnpm dlx prisma migrate dev && pnpm dlx prisma db seed
cd ../../services/agent-service && uv sync
```

启动 Agent 服务：

```bash
cd services/agent-service
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动 Web 主应用：

```bash
cd apps/web
pnpm dev
```

访问：

```text
Web 主应用：http://localhost:3000
Agent Service OpenAPI：http://localhost:8000/docs
MinIO：http://localhost:9001
```

---

## 14. 手工验收流程

1. 打开首页，确认至少 2 个 seed 游戏。
2. 注册新账号。
3. 登录后进入 Create。
4. 输入创意：

```text
做一个赛博朋克风格的点击小游戏，玩家需要在 30 秒内点击霓虹星星获得高分。
```

5. 上传一张图片素材。
6. 创建任务。
7. 查看 Agent 日志：需求解析、玩法设计、代码生成、校验、上传。
8. 任务成功后点击预览。
9. 在 MinIO 检查新 bundle：

```text
game-bundles/games/{game_id}/versions/{version_id}/manifest.json
```

10. 点击发布。
11. 回首页，确认新游戏出现。
12. 点击新游戏进入 Play。
13. 确认 iframe 加载的是 MinIO 远端 `index.html`。
14. 打开数据库，确认 users、games、game_versions、generation_tasks、agent_logs、play_events 都有记录。

---

## 15. 交付文档

项目内建议包含：

```text
docs/system-design.md
docs/completion-report.md
docs/ai-collaboration.md
docs/manual-test-checklist.md
```

### system-design.md

写：架构图、模块边界、API、数据模型、Agent 工作流、产物协议、安全方案、失败恢复。

### completion-report.md

写：已完成、未完成、Mock 部分、取舍原因、再给 1 周怎么迭代。

### ai-collaboration.md

写：使用的 AI 工具、关键 prompt、AI 贡献、人工 review、修复过的问题。

### manual-test-checklist.md

写：完整手工验收步骤和截图/日志证据路径。

### 原任务 3.3 提交项对照

| 原任务提交项 | 本项目落地方式 |
| --- | --- |
| 源码仓库 | GitHub 仓库，至少 4 次 commit |
| Demo 地址 | 本地 Demo 启动方式；时间允许再给线上地址 |
| 启动命令 | README 提供 Docker Compose、web、agent-service 三组命令 |
| 测试数据 | seed 2 个游戏 + Create 生成并发布第 3 个游戏 |
| 环境变量 | `apps/web/.env.example` 和 `services/agent-service/.env.example` |
| 系统设计文档 | `docs/system-design.md` |
| 技术栈 | README 和 `docs/completion-report.md` 明确说明 |
| 完成度说明 | `docs/completion-report.md` |
| 测试与验证证据 | `docs/manual-test-checklist.md` + 截图/日志路径 |
| 演示视频 | 可选，建议 5 分钟以内覆盖登录、Create、发布、Home、Play |
| AI 协作记录 | `docs/ai-collaboration.md` |

---

## 16. 后续一周迭代方向

> 当前 MVP 已实现 LangGraph + 流式 SSE + 完整 Agent 工作流，以下为后续增强方向：

1. 接入更强大的 LLM（Claude、GPT-4）提升 Specialist 输出质量
2. 增加 Docker 沙箱构建和更严格的 AST 安全扫描
3. 持久化 LangGraph checkpoint，支持失败节点断点续跑
4. 升级为 RabbitMQ/Redis Queue 异步任务总线，前端完全无等待
5. 增加游戏版本管理和 Remix 派生
6. 增加搜索、标签筛选、点赞、收藏、排行榜
7. 增加 pytest 接口测试和 Playwright E2E
8. 部署到线上：Vercel + Railway/Fly.io + Supabase + S3/R2/OSS
9. 增加 GitHub/Google OAuth
10. 扩展 Specialist Agent 能力（音乐音效、关卡设计等）

---

## 17. 最终落地判断

> 以下为原计划验收点，实际实现状态均已超出预期：

| 验收点 | 技术方案对应实现 |
| --- | --- |
| 登录注册 | Next.js Cookie Session + Session 表 ✅ |
| 首页游戏流 | Next.js Home + Route Handlers + Prisma + PostgreSQL ✅ |
| 至少 3 个示例游戏 | seed 2 个 + Create 生成发布 1 个（需执行 seed）✅ |
| Play 动态加载远端文件 | `play-meta` 返回 MinIO manifest 和 bundle_base_url，iframe 加载远端 index.html ✅ |
| Create 多模态输入 | Next.js 表单 + Route Handler 文件上传 + MinIO ✅ |
| Multi-Agent 架构 | LangGraph StateGraph + Supervisor/SpecialistFanOut/TemplateWorkflow ✅ |
| 流式日志 | FastAPI SSE + Next.js SSE 路由 + 前端实时写入 DB ✅ |
| 对象存储 | MinIO + AWS SDK v3，不用普通本地目录替代 ✅ |
| 数据库存 meta | Prisma 模型保存 game、version、task、log ✅ |
| 安全隔离 | iframe sandbox + 产物危险 API 拦截（eval/Function/Storage/fetch）✅ |
| 可复现交付 | Docker Compose + `.env.example` + seed ✅ |
| LLM 可观测性 | LangSmith 集成 ✅（超出原计划）|
| LLM 客户端 | 独立 app/llm/ 模块，OpenAI 兼容接口，完整降级策略 ✅（超出原计划）|
| 本地 fallback | Next.js 端本地生成器（FastAPI 不可用时兜底）✅（超出原计划）|

> **本实现已超出原计划的技术方案，主要升级点：**
> - 自研状态机 → LangGraph StateGraph（显式图工作流）
> - 单次 HTTP 调用 → SSE 流式实时推送日志
> - 模板生成 → Supervisor（LLM 意图分类）+ SpecialistFanOut（并行 Specialist）
> - 无可观测性 → LangSmith 完整 trace

