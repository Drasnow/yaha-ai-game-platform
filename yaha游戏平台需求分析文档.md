# Yaha AI Native 互动游戏平台 MVP 需求分析文档

> 来源任务：`yaha游戏平台开发任务.md`  
> 目标周期：2 天内完成可运行 Demo，并在 3 天内提交交付物  
> 核心判断：该任务不是普通 CRUD 平台，而是考察“AI Agent 生成互动游戏 + 对象存储产物 + Web 动态加载游玩”的端到端工程能力。

---

## 1. 项目目标

本项目需要从零搭建一个 AI Native 互动游戏 Web 平台 MVP，参考 Astrocade 类产品形态，让用户可以：

1. 作为玩家浏览平台中的互动游戏，并点击进入 Play 页面直接游玩。
2. 作为创作者注册/登录后，在 Create 页面输入创意和上传素材。
3. 由 FastAPI/Python Agent 微服务生成一个可运行的小游戏产物。
4. 将生成产物上传到对象存储。
5. 将游戏元信息写入数据库。
6. 创作者预览后发布，发布后的游戏出现在首页。
7. 玩家点击首页游戏后，前端根据数据库中的远端产物地址动态加载并运行游戏。

最终 Demo 必须证明完整业务闭环真实可跑，不能只有静态页面，也不能只使用前端写死的本地组件。

---

## 2. 用户角色分析

### 2.1 未登录访客 / 玩家

核心诉求：快速发现并体验互动游戏。

需要支持：

- 浏览首页已发布游戏列表。
- 查看游戏卡片信息：封面、标题、作者、简介、标签、发布时间。
- 点击游戏进入 Play 页面。
- Play 页面动态加载远端游戏文件并运行。
- 加载失败时看到明确错误态，而不是白屏。

### 2.2 创作者

核心诉求：用自然语言和素材快速生成可发布小游戏。

需要支持：

- 邮箱注册、邮箱登录、退出登录。
- 登录后访问 Create 页面。
- 输入游戏创意文本，例如玩法、风格、角色、胜负条件。
- 上传至少一种素材：图片、文件或视频。
- 提交生成任务并查看任务状态。
- 查看 Agent 生成过程摘要或日志。
- 生成成功后预览游戏。
- 发布游戏，使其出现在首页。

### 2.3 平台维护者 / 面试官视角

核心诉求：判断系统是否具备真实工程设计能力。

需要展示：

- 数据库中有用户、游戏、版本、素材、生成任务、Agent 日志等结构。
- 对象存储中存在游戏 bundle / manifest / asset 等远端产物。
- Play 页面不是硬编码本地组件，而是根据数据库 meta 动态加载。
- Agent 生成流程不是纯假数据，至少有可扩展到真实模型的编排设计。
- README、环境变量、启动命令、测试数据、完成度说明完整。

---

## 3. MVP 范围定义

### 3.1 必须完成

| 模块 | MVP 要求 |
| --- | --- |
| Auth | 邮箱注册、邮箱登录、退出登录、Session 保持、Create 页面访问控制 |
| Home | 展示所有 published 游戏，至少 3 个示例游戏，其中 1 个来自 Create 流程 |
| Create | 文本创意输入、至少一种素材上传、创建生成任务、展示进度和 Agent 日志摘要 |
| Agent 生成 | Next.js 主应用触发 FastAPI/Python Agent 状态机流程，生成可运行小游戏文件 |
| 对象存储 | 使用 MinIO 或 S3 兼容服务保存游戏产物，不用普通本地文件目录替代产品边界 |
| 数据库 | 保存用户、游戏、版本、素材、任务、日志、发布状态 |
| Play | 根据数据库 meta 动态加载对象存储中的 manifest / bundle / assets 并运行 |
| 发布 | 生成结果可预览，发布后进入首页 |
| 文档 | README、系统设计文档、环境变量说明、启动命令、完成度说明 |

### 3.2 可以简化但要解释清楚

| 功能 | MVP 处理方式 |
| --- | --- |
| Google / GitHub 登录 | 可先不真实接入，但需要在设计文档中说明 OAuth 数据模型和扩展方式 |
| 真实复杂游戏生成 | 可生成固定模板结构的小游戏，但必须由任务流程生成文件、上传、入库、发布 |
| 多 Agent 智能程度 | 可以用状态机模拟多个 Agent 步骤，但日志和接口要能替换成真实 LLM 调用 |
| 安全沙箱 | MVP 可用 iframe sandbox + 静态 HTML/JS 限制，文档说明后续 Docker / Firecracker 隔离方案 |
| 搜索、点赞、收藏 | 加分项，时间紧时不作为首要目标 |
| 演示视频 | 推荐但非必须 |

### 3.3 不建议投入过多时间

- 复杂 UI 动效。
- 完整社交系统。
- 复杂排行榜。
- 多人实时游戏。
- 过度抽象的微服务架构。
- 一开始就接入多个第三方 OAuth。

2 天周期内，最重要的是证明核心链路真实、稳定、可复现。

---

## 4. 核心业务流程

### 4.1 玩家游玩流程

1. 用户访问首页。
2. 前端请求 Next.js 业务 API 获取 published 游戏列表。
3. Next.js 通过 Prisma 从数据库读取游戏 meta。
4. 首页展示游戏卡片。
5. 用户点击某个游戏。
6. 前端进入 `/play/[gameId]`。
7. Play 页面请求 Next.js 业务 API 获取该游戏的最新 published version。
8. Next.js 返回 manifest URL、bundle URL、asset URL 等远端产物信息。
9. 前端加载 manifest。
10. 前端在 sandbox iframe 中加载并运行游戏。
11. 记录 play_start、load_success、load_failed 等埋点。

### 4.2 创作者生成发布流程

1. 用户注册或登录。
2. 用户进入 Create 页面。
3. 输入创意文本并上传素材。
4. 前端提交创建任务请求。
5. Next.js 主应用保存素材到对象存储。
6. Next.js 主应用创建 generation_task 记录，状态为 pending/running。
7. Next.js 调用 FastAPI/Python Agent 微服务执行 Agent 工作流。
8. Agent 依次完成需求理解、游戏设计、代码生成、构建检查、产物打包。
9. 生成产物上传到对象存储指定路径。
10. 数据库写入 game、game_version、agent_log 等记录。
11. 任务状态更新为 succeeded。
12. 前端轮询或订阅任务状态，展示进度和结果。
13. 用户预览生成游戏。
14. 用户点击发布。
15. Next.js 主应用将游戏状态改为 published。
16. 首页可以看到该游戏。

---

## 5. 功能需求拆解

### 5.1 Auth 登录注册

#### 必做能力

- 邮箱注册。
- 邮箱登录。
- 密码加密存储。
- 退出登录。
- Session / Cookie 登录态保持。
- 未登录用户访问 Create 时跳转登录页。
- 登录后刷新页面仍能识别用户。

#### 建议实现

- 使用 Next.js 主应用完成邮箱注册、邮箱登录、退出登录和受保护页面访问控制。
- 认证可以选 Better Auth / Auth.js / 自研 Cookie Session，2 天 Demo 优先选最熟悉、最快能跑通的一种。
- Google / GitHub 第三方登录可以先不真实接入，但必须在系统设计文档中说明 OAuth 扩展方案：新增 `oauth_accounts` 表，将第三方账号与内部 `users` 绑定，避免把 provider 字段直接塞进 users 导致后续多账号绑定困难。

#### 数据字段建议

- `id`
- `email`
- `password_hash`
- `display_name`
- `avatar_url`
- `provider`
- `provider_account_id`
- `created_at`
- `updated_at`

---

### 5.2 Home 首页

#### 必做能力

- 从 Next.js 业务 API 或数据库读取已发布游戏。
- 游戏卡片展示封面、标题、作者、简介、标签、发布时间。
- 至少展示 3 个示例游戏。
- 至少 1 个游戏必须来自 Create 流程生成并发布。
- 点击进入 Play 页面。

#### 加分能力

- 标签筛选。
- 搜索。
- 游玩次数统计。
- 点赞或收藏。

#### 验收重点

不能只在前端写死数组。可以在数据库 seed 中预置 2 个示例游戏，再通过 Create 流程生成并发布第 3 个。

---

### 5.3 Create 创建页

#### 必做能力

- 文本创意输入。
- 文件 / 图片 / 视频至少支持一种上传。
- 提交生成任务。
- 展示任务状态：pending、running、succeeded、failed。
- 展示 Agent 步骤日志，例如：
  - 需求分析中
  - 玩法设计中
  - 代码生成中
  - 构建校验中
  - 上传产物中
  - 写入数据库中
- 生成成功后展示预览入口。
- 支持发布。

#### 体验建议

- 任务状态用轮询实现即可，例如每 2 秒请求一次 `/api/generation-tasks/:id`。
- Agent 日志不需要太复杂，但要可读，能证明不是单次黑盒调用。
- 失败时展示失败原因和重试入口。

---

### 5.4 Agent 生成链路

#### MVP 目标

实现一个可解释、可扩展的 Multi-Agent 生成流程。短期内可以用状态机 + 模板生成保证稳定交付，接口上保留真实 LLM / Agent Harness 接入能力。

#### 推荐拆分

| Agent | 职责 |
| --- | --- |
| Requirement Agent | 解析用户创意，提取游戏类型、主题、角色、目标、素材用途 |
| Game Design Agent | 生成玩法规则、胜负条件、UI 布局、交互方式 |
| Code Generation Agent | 生成 HTML / JS / CSS 或 React 小游戏代码 |
| Build & Validate Agent | 检查产物结构、manifest、入口文件、安全限制 |
| Artifact Agent / Publish Coordinator | Agent 服务生成或上传产物；Next.js 主应用负责写入数据库、生成可预览版本 |

#### MVP 实现策略

建议第一版不要追求复杂代码生成，而是：

1. 让 Agent 根据创意选择一个小游戏模板，例如点击得分、躲避障碍、问答互动、拖拽收集。
2. 将用户创意、标题、主题色、素材 URL 注入模板。
3. 生成完整 `index.html`、`game.js`、`style.css`、`manifest.json`。
4. 上传到 MinIO 的路径中。
5. Play 页面根据 `manifest.json` 运行。

这样既能保证 Demo 稳定，又能说明未来可以替换成真实 LLM 代码生成。

---

### 5.5 Play 动态加载

#### 必做能力

- 根据 `gameId` 从 Next.js 业务 API 获取游戏版本 meta。
- meta 中必须包含远端产物地址。
- 前端加载 manifest。
- 在 Web 端运行游戏。
- 加载中、加载成功、加载失败都有状态。

#### 推荐产物协议

对象存储路径示例：

```text
s3://game-bundles/games/{gameId}/versions/{versionId}/manifest.json
s3://game-bundles/games/{gameId}/versions/{versionId}/index.html
s3://game-bundles/games/{gameId}/versions/{versionId}/game.js
s3://game-bundles/games/{gameId}/versions/{versionId}/style.css
s3://game-bundles/games/{gameId}/versions/{versionId}/assets/*
```

`manifest.json` 示例：

```json
{
  "schemaVersion": "1.0",
  "entry": "index.html",
  "title": "星际点击挑战",
  "description": "点击星星获得分数，在倒计时内挑战高分。",
  "assets": ["style.css", "game.js"],
  "runtime": "iframe-html-v1"
}
```

#### 安全要求

- 使用 iframe sandbox 运行远端游戏。
- 不允许生成游戏直接访问主站 Cookie。
- 不把真实密钥暴露给前端。
- 对上传文件类型、大小做限制。
- 后续可扩展到 Docker 沙箱构建和静态安全扫描。

---

## 6. 非功能需求

### 6.1 可运行性

- 项目必须能一键或少量命令启动。
- 推荐使用 Docker Compose 启动数据库、MinIO、应用服务。
- `.env.example` 必须完整列出环境变量。
- README 必须说明初始化数据库和 seed 测试数据方式。

### 6.2 可复现性

- 仓库至少 3 次清晰 commit。
- 提供测试账号或注册流程。
- 提供至少 3 个测试游戏。
- 明确哪些是真实实现，哪些是 Mock。

### 6.3 安全性

- 密码必须 hash。
- 上传文件限制类型和大小。
- 生成代码运行在 iframe sandbox 中。
- 对象存储凭证只在服务端使用。
- `.env` 不提交真实密钥。
- Agent Prompt 中不要注入系统密钥。

### 6.4 可观测性

- 记录生成任务状态。
- 记录 Agent 步骤日志。
- 记录 Play 加载成功 / 失败事件。
- 生成失败时有错误信息。
- README 中附手工验收步骤。

### 6.5 失败恢复

需要在系统设计文档中明确以下失败场景和处理方式：

| 失败场景 | MVP 处理方式 |
| --- | --- |
| 模型输出不稳定 | 模板生成兜底，保留 `MOCK_AGENT_MODE` |
| 代码生成缺少文件 | Build Validate Agent 拦截，任务标记 failed |
| 上传 MinIO 失败 | 任务标记 failed，保留错误信息，可重试 |
| 数据库写入失败 | 回滚事务，避免 game/version 半成品 |
| 发布失败 | 游戏保持 draft，不进入首页 |
| Play 加载失败 | 前端展示错误态，上报 `load_failed` |

### 6.6 内容审核、资源限额和成本统计

这些是 Create 模块加分项，MVP 可以轻量实现或在完成度说明中解释：

| 设计项 | MVP 建议 |
| --- | --- |
| 内容审核 | 对 prompt 和文件名做关键词拦截；真实版本接内容安全 API |
| 上传限额 | 限制单文件大小，例如 10MB；限制 MIME 类型 |
| 生成限额 | 每个用户每天限制生成次数，例如 10 次，MVP 可只在文档说明 |
| 运行限额 | 产物只允许静态 HTML/CSS/JS，不允许服务端代码 |
| 成本统计 | generation_tasks 增加 `estimated_cost` / `model_tokens` 字段，MVP 可为空 |

---

## 7. 数据模型建议

### 7.1 users

| 字段 | 说明 |
| --- | --- |
| id | 用户 ID |
| email | 邮箱 |
| password_hash | 密码哈希 |
| display_name | 展示名 |
| avatar_url | 头像 |
| created_at | 创建时间 |
| updated_at | 更新时间 |

### 7.1.1 oauth_accounts

用于说明 Google / GitHub 第三方登录的扩展设计。MVP 可以只建表或只写入设计文档，不一定真实接入 OAuth。

| 字段 | 说明 |
| --- | --- |
| id | 绑定记录 ID |
| user_id | 内部用户 ID |
| provider | google/github |
| provider_account_id | 第三方平台用户唯一 ID |
| provider_email | 第三方账号邮箱 |
| access_token_encrypted | 加密后的 access token，MVP 可不保存 |
| refresh_token_encrypted | 加密后的 refresh token，MVP 可不保存 |
| created_at | 创建时间 |
| updated_at | 更新时间 |

### 7.2 games

| 字段 | 说明 |
| --- | --- |
| id | 游戏 ID |
| author_id | 作者用户 ID |
| title | 标题 |
| description | 简介 |
| cover_url | 封面地址 |
| tags | 标签数组或关联表 |
| status | draft/published/archived |
| latest_version_id | 最新版本 ID |
| play_count | 游玩次数 |
| created_at | 创建时间 |
| published_at | 发布时间 |

### 7.3 game_versions

| 字段 | 说明 |
| --- | --- |
| id | 版本 ID |
| game_id | 游戏 ID |
| version | 版本号 |
| manifest_url | manifest 远端地址 |
| bundle_base_url | 产物基础地址 |
| runtime | 运行时类型，例如 iframe-html-v1 |
| source_task_id | 来源生成任务 ID |
| created_at | 创建时间 |

### 7.4 assets

| 字段 | 说明 |
| --- | --- |
| id | 素材 ID |
| owner_id | 上传者 ID |
| task_id | 所属生成任务 |
| file_name | 原文件名 |
| mime_type | 文件类型 |
| size | 文件大小 |
| object_key | 对象存储 key |
| public_url | 访问 URL |
| created_at | 创建时间 |

### 7.5 generation_tasks

| 字段 | 说明 |
| --- | --- |
| id | 任务 ID |
| user_id | 创建者 |
| prompt | 用户创意 |
| status | pending/running/succeeded/failed |
| current_step | 当前步骤 |
| result_game_id | 生成出的游戏 ID |
| result_version_id | 生成出的版本 ID |
| error_message | 失败原因 |
| created_at | 创建时间 |
| updated_at | 更新时间 |

### 7.6 agent_logs

| 字段 | 说明 |
| --- | --- |
| id | 日志 ID |
| task_id | 任务 ID |
| agent_name | Agent 名称 |
| step | 步骤名 |
| message | 可读日志 |
| raw_payload | 原始输入输出，Demo 可简化 |
| created_at | 创建时间 |

### 7.7 play_events

| 字段 | 说明 |
| --- | --- |
| id | 事件 ID |
| game_id | 游戏 ID |
| version_id | 版本 ID |
| user_id | 可为空，未登录玩家 |
| event_name | play_start/load_success/load_failed |
| metadata | 事件附加信息 |
| created_at | 创建时间 |

---

## 8. API 设计建议

### Auth

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/auth/register` | 邮箱注册 |
| POST | `/api/auth/login` | 邮箱登录 |
| POST | `/api/auth/logout` | 退出登录 |
| GET | `/api/auth/me` | 获取当前用户 |

这些 API 由 Next.js Route Handlers 或 Server Actions 提供。FastAPI 不负责用户登录态，只作为内部 Python Agent 微服务被 Next.js 调用。

### Home / Game

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/games` | 获取 published 游戏列表 |
| GET | `/api/games/:id` | 获取游戏详情 |
| POST | `/api/games/:id/publish` | 发布游戏 |
| GET | `/api/games/:id/play-meta` | 获取 Play 所需 manifest 和版本信息 |

### Create / Generation

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/assets/upload` | 上传素材 |
| POST | `/api/generation-tasks` | 创建生成任务 |
| GET | `/api/generation-tasks/:id` | 查询任务状态 |
| GET | `/api/generation-tasks/:id/logs` | 查询 Agent 日志 |
| POST | `/api/generation-tasks/:id/retry` | 重试失败任务，加分项 |

### Analytics

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/play-events` | 上报 Play 加载和游玩事件 |

---

## 9. 推荐技术栈

结合 HyperHit 的分层思路，本项目建议采用“Next.js 全栈业务主应用 + FastAPI/Python Agent 微服务”的混合架构。Next.js 负责页面、Auth、业务 API、数据库、发布状态和对象存储元信息；FastAPI 只负责 Python 更擅长的 Agent 编排、模型调用、游戏文件生成和产物校验。

### 9.1 首选技术栈：Next.js 全栈业务主应用 + FastAPI/Python Agent 微服务

| 层级 | 推荐技术 | 原因 |
| --- | --- | --- |
| Web 主应用 | Next.js 14/15 + React + TypeScript | 同时承载页面、业务 API、Auth、发布流程，2 天内开发闭环最快 |
| UI | Tailwind CSS + shadcn/ui | 快速做出可演示界面 |
| 业务 API | Next.js Route Handlers / Server Actions | 处理 Home、Auth、Create、Play、发布、任务状态等常规业务 |
| Agent 微服务 | FastAPI + Python | 只处理 Agent 编排、模型调用、文件生成、产物校验这些 Python 更擅长的部分 |
| 数据库 | PostgreSQL | 结构化保存用户、游戏、版本、素材、任务、日志、埋点 |
| ORM / 迁移 | Prisma | Next.js 主应用统一管理核心业务数据，开发速度快 |
| TS 数据校验 | Zod | Route Handlers / Server Actions 请求参数校验 |
| Python 数据校验 | Pydantic v2 | FastAPI Agent 请求和响应 schema |
| 认证 | Better Auth / Auth.js / Cookie Session | 登录态留在 Next.js 主应用内，避免跨服务 Cookie/CORS 复杂度 |
| 对象存储 | MinIO，本地 S3 兼容 | 满足对象存储要求，可迁移到阿里 OSS / AWS S3 |
| 对象存储 SDK | Next.js 用 AWS SDK v3；Python 可用 boto3 | 业务素材可由 Next.js 上传，Agent 产物可由 Python 上传或返回给 Next.js 上传 |
| 异步任务 | MVP 用 Next.js 创建任务 + HTTP 调 FastAPI；增强版用 RabbitMQ / Redis Queue | 2 天内避免过重消息队列，后续可借鉴 HyperHit 演进 |
| Agent 编排 | 自研 Python 状态机，或 LangGraph | Python 更适合 Agent、LLM 调用、模板生成和产物校验 |
| 模型服务 | OpenAI / Anthropic / 本地 Hermes 调用，Demo 可配置 MOCK_AGENT_MODE | 有真实模型最好；没有也能用模板生成跑通链路 |
| 游戏产物 | HTML + CSS + Vanilla JS + manifest.json | 最容易动态加载，iframe sandbox 运行成本低 |
| 沙箱运行 | Next.js Play 页面 iframe sandbox + Python/TS 产物静态校验 | MVP 可落地，后续扩展 Docker 沙箱 |
| 部署 | Docker Compose 启动 web、agent-service、postgres、minio | 面试官可本地复现完整链路 |
| 测试 | Vitest/Playwright + pytest/httpx | Next.js 测业务 API，FastAPI 测 Agent 微服务 |

### 9.2 为什么推荐这种混合架构

HyperHit 的可借鉴点是：Node/Next.js 做业务编排和数据中心，Python 做 AI/重计算服务。Yaha 也适合这样拆：

1. Auth、Home、Game、Task、Play、发布状态等常规业务放 Next.js，少一个完整 Python 业务后端，开发更快。
2. Agent 编排、模型调用、文件生成、产物校验放 Python，符合你的熟悉方向。
3. 数据库由 Prisma 统一管理，避免 Next.js 和 FastAPI 双 ORM 同时写同一批业务表。
4. MVP 用 HTTP 调用 FastAPI，简单可控；后续再升级 RabbitMQ / Redis Queue。
5. 面试讲法更成熟：业务主应用 + AI Agent 微服务，和 HyperHit 的工程分层一致。

### 9.3 需要控制的风险

| 风险 | 控制方式 |
| --- | --- |
| 双服务增加部署复杂度 | Docker Compose 写清 `web`、`agent-service`、`postgres`、`minio` 启动方式 |
| Next.js 与 FastAPI 职责混乱 | 明确 Next.js 写库和管业务，FastAPI 只生成产物并返回结果 |
| HTTP 调 Agent 时间较长 | MVP 可同步等待或短轮询；超过 30 秒再改队列 |
| 数据模型重复 | Prisma 是唯一业务数据库模型；Python 不直接维护业务表 |
| 消息队列过早引入 | MVP 不上 RabbitMQ，文档说明后续增强即可 |

---

## 10. 推荐系统架构

```text
浏览器
  │
  ▼
Next.js 全栈业务主应用
  │
  ├─ 页面层
  │   ├─ Home 页面：浏览 published 游戏
  │   ├─ Auth 页面：注册、登录、退出
  │   ├─ Create 页面：输入创意、上传素材、查看任务
  │   └─ Play 页面：加载 manifest，在 iframe sandbox 运行游戏
  │
  ├─ 业务 API / Server Actions
  │   ├─ Auth：注册、登录、退出、当前用户
  │   ├─ Game：游戏列表、详情、发布、play-meta
  │   ├─ Asset：素材上传到 MinIO
  │   ├─ Generation Task：创建任务、查询状态、查看 Agent 日志
  │   └─ Play Event：记录加载和游玩埋点
  │
  ├─ Prisma：访问 PostgreSQL
  ├─ AWS SDK v3：访问 MinIO
  └─ HTTP 调用内部 Agent 服务：/generate
      │
      ▼
FastAPI / Python Agent 微服务
  │
  ├─ Python Agent Orchestrator
  │   ├─ Requirement Agent：解析创意
  │   ├─ Game Design Agent：设计玩法
  │   ├─ Code Generation Agent：生成 HTML/CSS/JS/manifest
  │   ├─ Build Validate Agent：校验产物和安全规则
  │   └─ Artifact Agent：上传 MinIO 或返回产物给 Next.js
  │
  ├─ Pydantic：校验 Agent 输入输出
  └─ boto3：可选上传 MinIO

PostgreSQL：用户、游戏、版本、任务、日志、事件
MinIO：素材、游戏 bundle、manifest、封面
```

---

## 11. 目录结构建议

```text
yaha-ai-game-platform/
  apps/
    web/
    app/
      page.tsx
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
      game-card.tsx
      create-form.tsx
      task-progress.tsx
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
        templates/
          click_challenge.py
          avoid_obstacle.py
          quiz_game.py
    tests/
    pyproject.toml
    .env.example

  docs/
    system-design.md
    completion-report.md
    ai-collaboration.md
    manual-test-checklist.md

  docker-compose.yml
  README.md
```

---

## 12. 2 天交付计划建议

### 第 1 天上午：项目骨架和基础设施

- 初始化 Next.js 全栈主应用 + FastAPI Agent 微服务。
- 配置 PostgreSQL、Prisma、MinIO、FastAPI Agent 服务、Docker Compose。
- 建立数据模型。
- 完成 seed 数据。
- 完成基础页面布局。

### 第 1 天下午：Auth、Home、Play 基础链路

- 完成邮箱注册、登录、退出。
- 完成 Home 游戏列表接口和页面。
- 完成 Play meta 接口。
- 完成 iframe sandbox 加载固定对象存储游戏产物。
- 先让“远端加载游玩”跑通。

### 第 2 天上午：Create 和 Agent 生成链路

- 完成素材上传到 MinIO。
- 完成 generation task 创建和状态查询。
- 实现 Agent 状态机日志。
- 实现模板化小游戏生成。
- 上传生成产物到 MinIO。
- 写入 game / game_version 数据。

### 第 2 天下午：发布、验收和文档

- 完成预览和发布。
- 确保生成游戏进入首页。
- 准备 3 个示例游戏。
- 补齐 README、`.env.example`、系统设计文档、完成度说明。
- 录制可选演示视频。
- 整理 AI 协作记录。
- 做完整手工验收。

---

## 13. 验收清单

### 必须能演示

- [ ] 邮箱注册新用户。
- [ ] 邮箱登录。
- [ ] 未登录不能访问 Create。
- [ ] 首页展示至少 3 个游戏。
- [ ] 首页数据来自数据库。
- [ ] 点击游戏进入 Play。
- [ ] Play 页面根据数据库 meta 加载远端 manifest。
- [ ] iframe 中成功运行远端游戏。
- [ ] Create 页面可输入创意。
- [ ] Create 页面可上传素材。
- [ ] 提交后生成任务进入 running。
- [ ] 页面展示 Agent 步骤日志。
- [ ] 生成产物上传到 MinIO。
- [ ] 数据库写入 game 和 game_version。
- [ ] 生成结果可预览。
- [ ] 发布后首页可见。
- [ ] `.env.example` 不包含真实密钥。
- [ ] README 能让面试官复现启动。

### 推荐准备的演示证据

- MinIO 控制台截图：显示游戏产物文件。
- 数据库截图或 DBeaver / pgAdmin / SQL 客户端截图：显示 games、versions、tasks、logs。
- 终端日志：显示 Agent 步骤执行。
- 浏览器截图：登录、Create、任务成功、Home、Play。
- 5 分钟以内演示视频。

---

## 14. 风险分析与应对

| 风险 | 影响 | 应对 |
| --- | --- | --- |
| 真实 LLM 生成代码不稳定 | Demo 可能失败 | 使用模板生成兜底，保留真实模型接口 |
| 对象存储接入耗时 | Play 链路无法验收 | 优先使用 MinIO + S3 SDK，尽早跑通上传和读取 |
| Auth 浪费时间 | 主链路受影响 | 使用成熟认证库或简单 Credentials 登录 |
| iframe 跨域加载失败 | Play 页面无法运行 | MinIO 设置公开读或通过 Next.js 代理返回产物 |
| Docker 环境问题 | 面试官无法复现 | README 写清本地启动命令和常见问题 |
| 任务队列复杂 | 生成链路集成失败 | MVP 用数据库状态 + Next.js 调 FastAPI HTTP；后续再上 RabbitMQ / Redis Queue |
| UI 做太久 | 核心链路不完整 | UI 保持简洁，优先端到端闭环 |

---

## 15. 最终交付物建议

必须提交：

1. GitHub 源码仓库，至少 3 次 commit。
2. Demo 地址或完整本地启动方式。
3. 启动命令，推荐 Docker Compose。
4. 测试数据说明。
5. `.env.example`。
6. 系统设计文档。
7. 技术栈说明。
8. 完成度说明。

建议额外提交：

1. 5 分钟演示视频。
2. AI 协作记录。
3. 关键截图。
4. 手工验收步骤。

### 15.1 对照原任务 3.3 的提交清单

| 原任务提交项 | 本项目准备方式 |
| --- | --- |
| 源码仓库 | GitHub 仓库，至少 4 次 commit：初始化、Auth/Home/Play、Create/Agent、Docs |
| Demo 地址 | 优先本地可运行 Demo；如有时间再部署线上 |
| 启动命令 | README 写清 `docker compose up -d`、Next.js 主应用 `pnpm dev`、Agent 服务 `uvicorn` |
| 测试数据 | seed 2 个 published 游戏；现场 Create 生成并发布第 3 个 |
| 环境变量 | web/agent-service 各自 `.env.example`，不提交真实密钥 |
| 系统设计文档 | `docs/system-design.md` 写架构图、API、数据模型、Agent 工作流、产物协议、安全、已知问题 |
| 技术栈 | README 和 completion-report 明确 Next.js + FastAPI + PostgreSQL + MinIO + Python Agent |
| 完成度说明 | `docs/completion-report.md` 说明已完成、未完成、Mock、再给 1 周计划 |
| 测试与验证证据 | `docs/manual-test-checklist.md` + 截图路径 + 关键日志 |
| 演示视频 | 可选但推荐，覆盖登录、Create、发布、Home、Play |
| AI 协作记录 | `docs/ai-collaboration.md` 记录工具、Prompt、AI 贡献和人工修复 |

---

## 16. 技术栈最终建议摘要

如果只选一套最适合你当前能力和本任务的方案，建议使用：

```text
Web 主应用：Next.js + React + TypeScript + Tailwind CSS + shadcn/ui
业务 API：Next.js Route Handlers / Server Actions
Agent 微服务：FastAPI + Python + Pydantic v2
数据库：PostgreSQL
ORM / 迁移：Prisma
认证：Better Auth / Auth.js / Cookie Session
对象存储：MinIO，本地 S3 兼容，后续可迁移 OSS/S3
对象存储 SDK：Next.js 使用 AWS SDK v3；Python Agent 可选 boto3
Agent 编排：Python 自研状态机；增强版可接 LangGraph / CrewAI
模型服务：OpenAI/Anthropic/Hermes 可选；MVP 保留 MOCK_AGENT_MODE 兜底
异步任务：MVP 用 Next.js 任务表 + HTTP 调 FastAPI；增强版用 RabbitMQ / Redis Queue
游戏产物：HTML + CSS + Vanilla JS + manifest.json
运行隔离：iframe sandbox + Agent/业务层产物安全校验
部署：Docker Compose 启动 web、agent-service、postgres、minio
测试验证：Vitest/Playwright 验证 Web 主应用；pytest/httpx 验证 Agent 服务
```

这套方案的优点是：Next.js 负责常规业务闭环，开发速度快；Python Agent 服务负责生成链路，符合你的熟悉方向；数据库由 Prisma 统一管理，避免双 ORM；MVP 用 HTTP 调用降低复杂度，后续可以像 HyperHit 一样升级为 RabbitMQ 任务总线。

---

## 17. 一句话结论

本任务的核心不是“做一个游戏列表网站”，而是要证明你能在短时间内设计并实现一个 AI Agent 驱动的互动游戏生成平台。当前最优方案是：用 Next.js 全栈主应用跑通登录、任务、数据库、发布、Home 和 Play；用 FastAPI/Python Agent 微服务跑通游戏生成、产物校验和可扩展的 Agent 编排。
