"""LangGraph State 定义。

定义游戏生成流程中的所有状态字段。
"""

from typing import TypedDict, NotRequired, Annotated

from pydantic import BaseModel

from app.schemas.generate import GenerateRequest
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


# ========================================
# 数据类（用于内部状态传递）
# ========================================

class GameDesign(BaseModel):
    """游戏设计数据类。"""
    template: str
    title: str
    description: str
    tags: list[str]
    primary_color: str
    accent_color: str
    objective: str


class GeneratedFiles(BaseModel):
    """生成的代码文件。"""
    files: dict[str, str]
    manifest: dict[str, object]


# ========================================
# Reducer 函数
# ========================================

def _merge_logs(existing: list, new: list) -> list:
    """合并日志列表。"""
    if existing is None:
        return new
    if new is None:
        return existing
    return existing + new


def _merge_specialist_results(existing: dict, new: dict) -> dict:
    """合并 Specialist 结果。"""
    if existing is None:
        return new
    if new is None:
        return existing
    return {**existing, **new}


def _last_writer(existing, new):
    """保留最后一次写入的值（用于并发节点写入不同字段）。"""
    return new


class GenerationState(TypedDict):
    """LangGraph 状态定义。

    所有字段在节点之间传递，定义了游戏生成流程的完整状态。

    注意：
    - logs 和 specialist_results 使用 Annotated + reducer 支持并行写入合并
    """

    # ===== 输入 =====
    request: GenerateRequest  # 用户请求（必需）

    # ===== Supervisor 决策（入口 Agent） =====
    supervisor_result: SupervisorResult | None  # Supervisor Agent 决策结果

    # ===== Specialist 输出（并行填充） =====
    vision: Annotated[VisionSpec | None, _last_writer]  # 视觉规范
    gameplay: Annotated[GameplaySpec | None, _last_writer]  # 游戏机制
    narrative: Annotated[NarrativeSpec | None, _last_writer]  # 叙事内容

    # ===== 整合与生成 =====
    unified_design: NotRequired[UnifiedDesign | None]  # 整合设计
    generated_files: NotRequired[dict | None]  # 生成的文件（包含 files 和 manifest）
    validation: NotRequired[ValidationResult | None]  # 验证结果
    artifact: NotRequired[UploadResult | None]  # 上传结果

    # ===== 执行追踪（支持并行合并）=====
    logs: Annotated[list[AgentLog], _merge_logs]  # 执行日志列表
    error: NotRequired[str | None]  # 错误信息

    # ===== 素材上下文 =====
    asset_context: NotRequired[str | None]  # 从用户上传素材中提取的文本内容，供 LLM 消费

    # ===== 路由决策 =====
    specialist_results: Annotated[dict[str, str], _merge_specialist_results]  # Specialist 结果

    # ===== 重试控制 =====
    retry_count: NotRequired[int]  # 当前重试次数


def create_initial_state(request: GenerateRequest) -> GenerationState:
    """创建初始状态。

    Args:
        request: 用户生成请求

    Returns:
        初始化的 GenerationState
    """
    return GenerationState(
        request=request,
        supervisor_result=None,
        vision=None,
        gameplay=None,
        narrative=None,
        logs=[],
        specialist_results={},
        retry_count=0,
        asset_context=None,
    )


__all__ = [
    "GenerationState",
    "create_initial_state",
    "GameDesign",
    "GeneratedFiles",
    "SupervisorResult",
]
