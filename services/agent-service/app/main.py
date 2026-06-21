from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
import logging
import os
import json
import asyncio

import langsmith

from app.core.config import get_settings
from app.agent.graph import run_generation, run_generation_stream
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

app = FastAPI(title="Yaha Agent Service")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """游戏生成接口。

    调用 LangGraph Supervisor → SpecialistFanOut/TemplateWorkflow → CodeGenerator → Validator → Upload 流程。
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
    """
    async def sse_generator():
        try:
            # 发送开始信号
            yield _sse_event({"type": "start", "task_id": request.task_id})

            async for state_update in run_generation_stream(request):
                # state_update 是一个 dict，key 是节点名，value 是该节点返回的部分状态
                for node_name, partial_state in state_update.items():
                    if not partial_state:
                        continue

                    logs = partial_state.get("logs", [])
                    if logs:
                        # 每个节点可能返回多条日志（如 SupervisorAgent 返回 [start, decision]）
                        for log in logs:
                            yield _sse_event({
                                "type": "log",
                                "agent": log.agent,
                                "step": log.step,
                                "message": log.message,
                                "timestamp": log.timestamp or "",
                            })

                    # Supervisor rejected：立即告知
                    supervisor_result = partial_state.get("supervisor_result")
                    if supervisor_result and supervisor_result.status == "rejected":
                        yield _sse_event({
                            "type": "rejected",
                            "feedback": supervisor_result.feedback_message,
                        })

                    # Supervisor approved：告知决策
                    if supervisor_result and supervisor_result.status in ("approved_simple", "approved_complex"):
                        yield _sse_event({
                            "type": "supervisor_decision",
                            "status": supervisor_result.status,
                            "complexity": supervisor_result.complexity,
                        })

                    # Validator 完成：告知验证结果
                    validation = partial_state.get("validation")
                    if validation is not None:
                        yield _sse_event({
                            "type": "validation",
                            "passed": validation.passed,
                            "issues": validation.issues,
                        })

                    # Artifact 上传完成：告知最终产物
                    artifact = partial_state.get("artifact")
                    if artifact is not None:
                        yield _sse_event({
                            "type": "artifact",
                            "manifest_url": artifact.manifest_url,
                            "entry_url": artifact.entry_url,
                            "artifact_base_url": artifact.artifact_base_url,
                            "file_count": artifact.file_count,
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
