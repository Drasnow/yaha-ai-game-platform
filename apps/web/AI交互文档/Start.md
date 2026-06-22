# 项目启动说明

本文档说明本地如何启动 Yaha AI Game Platform 的完整 MVP 服务。

## 0. 前置准备

请先手动打开 Docker Desktop，并确认 Docker 已经启动完成。

项目根目录：

~~~powershell
cd D:\leibo\yaha-ai-game-platform
~~~

## 1. 启动基础依赖：PostgreSQL + MinIO

在项目根目录执行：

~~~powershell
docker compose up -d
~~~

查看服务状态：

~~~powershell
docker compose ps
~~~

正常情况下应看到：

- `yaha-postgres`：PostgreSQL 数据库
- `yaha-minio`：MinIO 对象存储

停止基础依赖：

~~~powershell
docker compose down
~~~

## 2. 访问 MinIO 控制台

浏览器打开：

~~~text
http://localhost:9001
~~~

登录信息来自 `docker-compose.yml`：

~~~text
用户名：yaha_minio
密码：yaha_minio_password
~~~

对象存储 Bucket：

~~~text
yaha-games
~~~

生成游戏后，可以在 MinIO 中查看类似路径：

~~~text
games/generated/<taskId>/v1/index.html
games/generated/<taskId>/v1/style.css
games/generated/<taskId>/v1/game.js
games/generated/<taskId>/v1/manifest.json
~~~

## 3. 启动 FastAPI Agent 服务

新开一个终端，执行：

~~~powershell
cd D:\leibo\yaha-ai-game-platform\services\agent-service
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
~~~

健康检查：

~~~powershell
Invoke-RestMethod http://127.0.0.1:8000/health
~~~

正常返回：

~~~json
{"status":"ok"}
~~~

前端点击“创建生成任务”后，Agent 终端应出现类似日志：

~~~text
POST /generate HTTP/1.1" 200 OK
~~~

## 4. 启动 Web 前端

新开一个终端，执行：

~~~powershell
cd D:\leibo\yaha-ai-game-platform\apps\web
pnpm dev
~~~

当前项目启动地址为：

~~~text
http://127.0.0.1:4000
~~~

如果看到如下输出，说明 Web 已启动：

~~~text
Next.js ...
Local: http://127.0.0.1:4000
Ready
~~~

## 5. 前端验证 Create + Agent 链路

浏览器打开：

~~~text
http://127.0.0.1:4000
~~~

验证步骤：

1. 注册或登录账号。
2. 进入 Create 页面：`http://127.0.0.1:4000/create`。
3. 输入至少 10 个字的创意，例如：

   ~~~text
   做一个太空星星点击得分游戏，30秒内点击越多越好
   ~~~

4. 可选上传一个图片或文本素材。
5. 点击“创建生成任务”。
6. 页面应显示“生成成功”，并出现 Agent 日志。
7. 点击“预览游戏”可以进入 Play 页面。
8. 点击“发布游戏”后，首页可以看到该生成游戏。

验证时可同时观察两个终端：

Web 终端应出现：

~~~text
POST /api/v1/generation-tasks
~~~

Agent 终端应出现：

~~~text
POST /generate HTTP/1.1" 200 OK
~~~

## 6. 常用验证命令

### Web 类型检查

~~~powershell
cd D:\leibo\yaha-ai-game-platform\apps\web
pnpm exec tsc --noEmit
~~~

### Agent 测试

~~~powershell
cd D:\leibo\yaha-ai-game-platform\services\agent-service
uv run pytest -q
~~~

### 查看最近生成任务

~~~powershell
docker exec yaha-postgres psql -U yaha -d yaha_game -c "select id,status,current_step,result_game_id,created_at from generation_tasks order by created_at desc limit 5;"
~~~

### 查看最近 Agent 日志

~~~powershell
docker exec yaha-postgres psql -U yaha -d yaha_game -c "select task_id,agent_name,step,message,created_at from agent_logs order by created_at desc limit 20;"
~~~

## 7. 推荐启动顺序

每次本地演示建议按这个顺序启动：

1. 手动打开 Docker Desktop。
2. 根目录执行 `docker compose up -d`。
3. 启动 Agent 服务：`uv run uvicorn app.main:app --host 127.0.0.1 --port 8000`。
4. 启动 Web：`pnpm dev`。
5. 打开 `http://127.0.0.1:4000` 验证。

## 8. 常见问题

### 点击创建任务后 Agent 终端没有 `/generate`

优先检查：

1. Agent 是否已启动在 `127.0.0.1:8000`。
2. `apps/web/.env` 是否包含：

   ~~~text
   AGENT_SERVICE_URL="http://localhost:8000"
   ~~~

3. 修改 `.env` 后需要重启 `pnpm dev`。
4. Web 终端是否出现 `POST /api/v1/generation-tasks`。

### MinIO 看不到生成文件

检查：

1. Create 页面是否显示“生成成功”。
2. Agent 终端是否出现 `/generate 200 OK`。
3. MinIO bucket 是否为 `yaha-games`。
4. 路径是否在 `games/generated/<taskId>/v1/` 下。

### 端口占用

常用端口：

- Web：`4000`
- Agent：`8000`
- MinIO API：`9000`
- MinIO Console：`9001`
- PostgreSQL：`5432`
