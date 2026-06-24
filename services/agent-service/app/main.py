from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import logging
import os
import json

import langsmith

from app.core.config import get_settings
from app.agent.graph import init_graph, run_generation, run_generation_stream
from app.agent.validator import ArtifactValidationError
from app.schemas.generate import ArtifactResponse, GenerateRequest, GenerateResponse, AgentLogResponse

# LangSmith: 从配置同步到环境变量，langsmith SDK 会自动读取标准环境变量
_settings = get_settings()
if _settings.langsmith_api_key:
    os.environ["LANGSMITH_API_KEY"] = _settings.langsmith_api_key
if _settings.langsmith_project:
    os.environ["LANGSMITH_PROJECT"] = _settings.langsmith_project
if _settings.langsmith_tracing:
    os.environ["LANGSMITH_TRACING"] = str(_settings.langsmith_tracing).lower()

# INFO 模式：只打印 Agent 的 LLM prompt 和响应，不输出第三方库的 DEBUG 噪声
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s",
)
# 抑制第三方库的 DEBUG 日志
for _lib in ["httpx", "httpcore", "botocore", "urllib3", "boto3"]:
    logging.getLogger(_lib).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan：启动时初始化 Redis + 图，关闭时清理资源。"""
    # ── 启动阶段 ──────────────────────────────────────────
    settings = get_settings()

    if settings.redis_password:
        redis_url = (
            f"redis://:{settings.redis_password}"
            f"@{settings.redis_host}:{settings.redis_port}"
            f"/{settings.redis_db}"
        )
    else:
        redis_url = (
            f"redis://{settings.redis_host}:{settings.redis_port}"
            f"/{settings.redis_db}"
        )

    checkpointer = None
    try:
        from langgraph.checkpoint.redis.aio import AsyncRedisSaver
        from langgraph.checkpoint.redis.base import JsonPlusRedisSerializer

        # 按 langgraph-checkpoint-redis 官方 async 示例：
        # https://github.com/redis-developer/langgraph-redis
        # 整个 setup + graph 初始化都在 async with 上下文内完成，
        # 官方 async 示例（line 214）将所有操作放在 with 内：
        #   async with AsyncRedisSaver.from_conn_string(...) as checkpointer:
        #       await checkpointer.asetup()
        #       # 所有 checkpoint 操作...
        # 这样保证连接在操作期间始终有效，graph.compile() 持有 checkpointer 后
        # 进入 yield（应用运行期），with 块外的 graph 全局变量持有 checkpointer 引用，
        # Redis 连接在 uvicorn 单 worker 进程生命周期内保持有效。

        # 注册所有可能进入 Redis checkpoint 的自定义 Pydantic 类型，
        # 避免反序列化时被 LangGraph JsonPlus 拦截并降级。
        # 分为两类：
        #   - app.schemas.generate:  API 层 request/response 模型
        #   - app.agent.schemas:    Agent 内部状态模型
        from app.agent.state import GameDesign, GeneratedFiles
        from app.agent.schemas import (
            VisionSpec,
            GameplaySpec,
            NarrativeSpec,
            UnifiedDesign,
            ValidationResult,
            UploadResult,
            AgentLog,
            SupervisorResult,
        )

        custom_serde = JsonPlusRedisSerializer(
            allowed_msgpack_modules=[
                # API 层
                ("app.schemas.generate", "GenerationAsset"),
                ("app.schemas.generate", "GenerateRequest"),
                # Agent state 层（主要状态类型）
                ("app.agent.state", "GameDesign"),
                ("app.agent.state", "GeneratedFiles"),
                # Agent schemas 层（所有节点输出类型）
                ("app.agent.schemas", "VisionSpec"),
                ("app.agent.schemas", "GameplaySpec"),
                ("app.agent.schemas", "NarrativeSpec"),
                ("app.agent.schemas", "UnifiedDesign"),
                ("app.agent.schemas", "ValidationResult"),
                ("app.agent.schemas", "UploadResult"),
                ("app.agent.schemas", "AgentLog"),
                ("app.agent.schemas", "SupervisorResult"),
            ]
        )

        # 官方推荐的 TTL 配置：checkpoint 30 分钟无活动后自动过期，
        # 防止 Redis 存储无限堆积。游戏生成任务通常在分钟内完成，
        # 足够覆盖正常流程；异常中断的任务在 30 分钟后自动清理。
        redis_ttl = {"default_ttl": 30, "refresh_on_read": True}

        async with AsyncRedisSaver.from_conn_string(
            redis_url,
            ttl=redis_ttl,
        ) as checkpointer:
            # 注入自定义 serde 以支持自定义类型序列化
            checkpointer.serde = custom_serde
            await checkpointer.asetup()
            logger.info(
                f"Redis checkpointer 已连接: {settings.redis_host}:{settings.redis_port}"
                f" (ttl={redis_ttl['default_ttl']}min)"
            )
            init_graph(checkpointer=checkpointer)
            logger.info("LangGraph 图实例初始化完成")
            yield

    except Exception as exc:
        logger.warning(f"Redis 连接失败，LangGraph 将无持久化检查点: {exc}")
        init_graph(checkpointer=None)
        logger.info("LangGraph 图实例初始化完成（无 checkpointer）")
        yield  # 无 checkpointer 时也继续启动


app = FastAPI(title="Yaha Agent Service", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """游戏生成接口。

    调用 LangGraph Supervisor → [并行] VisionAgent + GameplayAgent + NarrativeAgent → Synthesis → CodeGenerator → Validator → Upload 流程。
    thread_id 绑定 task_id，同一任务重启后可从断点恢复。
    """
    try:
        result = await run_generation(request)

        artifact = result.get("artifact")
        unified_design = result.get("unified_design")

        supervisor_result = result.get("supervisor_result")
        if supervisor_result and supervisor_result.status == "rejected":
            logs = [
                AgentLogResponse(
                    agent_name=log.agent,
                    step=log.step,
                    message=log.message,
                )
                for log in result.get("logs", [])
            ]
            return GenerateResponse(
                status="rejected",
                title="",
                description="",
                tags=[],
                artifact=None,
                logs=logs,
                supervisor_feedback=supervisor_result.feedback_message,
            )

        if result.get("error"):
            raise HTTPException(status_code=500, detail=result["error"])

        if not artifact:
            raise HTTPException(status_code=500, detail="生成失败：未生成产物")

        logs = [
            AgentLogResponse(
                agent_name=log.agent,
                step=log.step,
                message=log.message,
            )
            for log in result.get("logs", [])
        ]

        return GenerateResponse(
            status="succeeded",
            title=unified_design.title if unified_design else "游戏",
            description=unified_design.description if unified_design else "",
            tags=unified_design.tags if unified_design else [],
            artifact=ArtifactResponse(
                manifest_url=artifact.manifest_url,
                entry_url=artifact.entry_url,
                artifact_base_url=artifact.artifact_base_url,
            ),
            logs=logs,
            supervisor_feedback=None,
        )

    except ArtifactValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent 生成失败：{exc}") from exc


@app.post("/generate/stream")
async def generate_stream(request: GenerateRequest):
    """游戏生成流式接口（SSE）。

    实时推送每个 Agent 节点执行时产生的新日志，
    前端/Web 服务可据此增量写入数据库，实现任务进度的实时展示。
    thread_id 绑定 task_id，支持断点续跑。
    """
    async def sse_generator():
        try:
            # 发送开始信号
            yield _sse_event({"type": "start", "task_id": request.task_id})

            async for state_update in run_generation_stream(request):
                # state_update 来自 graph.astream()，每个元素是该 superstep 中
                # 某个节点返回的部分状态字典（key=节点名，value=该节点返回的字段更新）。
                #
                # ⚠ 陷阱：state_update.values() 里的值可能是：
                #   - Python dict        ✅ 安全
                #   - Pydantic BaseModel ❌ 直接 json.dumps() 会崩溃
                #   - 普通字符串         ✅ 安全
                #   - 列表              ✅ 安全
                # 因此对每个 value 先统一转 dict，再用 .get() 安全取值。
                #
                # 注意：state dict 中可能包含 request (GenerateRequest) 等
                # 无法 JSON 序列化的字段，跳过这些即可。
                for node_name, partial_state in state_update.items():
                    # 过滤掉不可序列化的值类型
                    if partial_state is None:
                        continue
                    if isinstance(partial_state, str):
                        continue
                    if isinstance(partial_state, (list, tuple)):
                        continue

                    # Pydantic 模型 → dict；已经是 dict → 原样使用
                    if hasattr(partial_state, "model_dump"):
                        partial_state = partial_state.model_dump()
                    if not isinstance(partial_state, dict):
                        continue

                    logs = partial_state.get("logs")
                    if logs:
                        for log in logs:
                            log_data = log.model_dump() if hasattr(log, "model_dump") else log
                            if isinstance(log_data, dict):
                                yield _sse_event({
                                    "type": "log",
                                    "agent": log_data.get("agent", ""),
                                    "step": log_data.get("step", ""),
                                    "message": log_data.get("message", ""),
                                    "timestamp": log_data.get("timestamp") or "",
                                })

                    # Supervisor rejected / approved
                    supervisor_result = partial_state.get("supervisor_result")
                    if supervisor_result:
                        sr = supervisor_result.model_dump() if hasattr(supervisor_result, "model_dump") else supervisor_result
                        if isinstance(sr, dict):
                            status = sr.get("status")
                            if status == "rejected":
                                yield _sse_event({
                                    "type": "rejected",
                                    "feedback": sr.get("feedback_message", ""),
                                })
                            elif status in ("approved_simple", "approved_complex"):
                                yield _sse_event({
                                    "type": "supervisor_decision",
                                    "status": status,
                                    "complexity": sr.get("complexity", ""),
                                })

                    # Validator 完成
                    validation = partial_state.get("validation")
                    if validation is not None:
                        val = validation.model_dump() if hasattr(validation, "model_dump") else validation
                        if isinstance(val, dict):
                            yield _sse_event({
                                "type": "validation",
                                "passed": val.get("passed", False),
                                "issues": val.get("issues", []),
                            })

                    # Artifact 上传完成
                    artifact = partial_state.get("artifact")
                    if artifact is not None:
                        art = artifact.model_dump() if hasattr(artifact, "model_dump") else artifact
                        if isinstance(art, dict):
                            yield _sse_event({
                                "type": "artifact",
                                "manifest_url": art.get("manifest_url", ""),
                                "entry_url": art.get("entry_url", ""),
                                "artifact_base_url": art.get("artifact_base_url", ""),
                                "file_count": art.get("file_count", 0),
                            })

                    # 游戏设计（unified_design）完成
                    unified_design = partial_state.get("unified_design")
                    if unified_design is not None:
                        ud = unified_design.model_dump() if hasattr(unified_design, "model_dump") else unified_design
                        if isinstance(ud, dict):
                            yield _sse_event({
                                "type": "game_design",
                                "title": ud.get("title", ""),
                                "description": ud.get("description", ""),
                                "tags": ud.get("tags", []),
                            })

                    # 错误信息
                    error = partial_state.get("error")
                    if error:
                        yield _sse_event({"type": "error", "message": error})

            # 流结束
            yield _sse_event({"type": "end"})

        except Exception as exc:
            yield _sse_event({"type": "error", "message": f"流式生成异常: {exc}"})

    async def event_iterator():
        """包装协程为普通迭代器，供 StreamingResponse 使用。"""
        generator = sse_generator()
        while True:
            try:
                event = await generator.__anext__()
                yield event
            except StopAsyncIteration:
                break

    return StreamingResponse(
        event_iterator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
