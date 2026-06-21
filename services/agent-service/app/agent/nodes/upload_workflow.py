"""Upload Workflow 节点 - 文件上传。

将生成的游戏文件上传到 MinIO 对象存储。
"""

import logging
from datetime import datetime

from app.agent.state import GenerationState
from app.agent.schemas import AgentLog, UploadResult
from app.agent.storage import ArtifactStorage
from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def upload_workflow(state: GenerationState) -> GenerationState:
    """UploadWorkflow - 上传生成文件。

    将生成的游戏代码上传到 MinIO 对象存储。

    Args:
        state: 当前状态

    Returns:
        更新后的状态，包含 artifact 字段
    """
    settings = get_settings()
    request = state["request"]

    logger.info(f"UploadWorkflow: 上传文件, task_id={request.task_id}")

    logs: list[AgentLog] = []

    logs.append(AgentLog(
        agent="UploadWorkflow",
        step="start",
        message="开始上传生成文件",
        timestamp=datetime.now().isoformat(),
    ))

    generated_files = state.get("generated_files")
    if generated_files is None:
        raise ValueError("没有可上传的文件")

    files = generated_files.get("files", {})
    if not files:
        raise ValueError("文件列表为空")

    # 上传到 MinIO（网络抖动时由 RetryPolicy 自动重试）
    storage = ArtifactStorage(settings)
    result = storage.upload_game_files(
        task_id=request.task_id,
        files=files,
    )

    upload_result = UploadResult(
        manifest_url=result.manifest_url,
        entry_url=result.entry_url,
        artifact_base_url=result.artifact_base_url,
        file_count=len(files),
    )

    logs.append(AgentLog(
        agent="UploadWorkflow",
        step="complete",
        message=f"文件上传成功: {len(files)} 个文件",
        timestamp=datetime.now().isoformat(),
    ))

    return {
        **state,
        "logs": logs,
        "artifact": upload_result,
    }
