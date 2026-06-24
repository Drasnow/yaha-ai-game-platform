"""LangGraph State 定义。

定义游戏生成流程中的所有状态字段。
"""

from typing import TypedDict, NotRequired, Annotated, Any

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
    - 所有 Pydantic 字段在 state 中以 dict 形式存储（Redis Checkpointer 序列化要求）
    """

    # ===== 输入 =====
    request: dict  # 用户请求（存为 dict，Redis Checkpointer 可序列化）

    # ===== Supervisor 决策（入口 Agent） =====
    supervisor_result: dict | None  # Supervisor Agent 决策结果

    # ===== Specialist 输出（并行填充） =====
    vision: Annotated[dict | None, _last_writer]  # 视觉规范
    gameplay: Annotated[dict | None, _last_writer]  # 游戏机制
    narrative: Annotated[dict | None, _last_writer]  # 叙事内容

    # ===== 整合与生成 =====
    unified_design: NotRequired[dict | None]  # 整合设计
    generated_files: NotRequired[dict | None]  # 生成的文件（包含 files 和 manifest）
    validation: NotRequired[dict | None]  # 验证结果
    artifact: NotRequired[dict | None]  # 上传结果

    # ===== 执行追踪（支持并行合并）=====
    logs: Annotated[list, _merge_logs]  # 执行日志列表（dict 列表）
    error: NotRequired[str | None]  # 错误信息

    # ===== 素材上下文 =====
    asset_context: NotRequired[str | None]  # 从用户上传素材中提取的文本内容，供 LLM 消费

    # ===== 路由决策 =====
    specialist_results: Annotated[dict[str, str], _merge_specialist_results]  # Specialist 结果

    # ===== 重试控制 =====
    retry_count: NotRequired[int]  # 当前重试/修复次数
    regenerate_requested: NotRequired[bool]  # 是否需要重新调用 CodeGenerator


# ========================================
# Pydantic → dict 序列化工具
# ========================================

def _to_serializable(value: Any) -> Any:
    """递归将 Pydantic 模型转换为 dict，确保所有值都可被 JSON 序列化。

    用于：
    1. create_initial_state：将 request 转 dict
    2. 各节点返回状态前：将 Pydantic 对象转 dict
    这样 LangGraph Redis Checkpointer 可以正常序列化整个 state。
    """
    if value is None:
        return None
    if isinstance(value, BaseModel):
        return _to_serializable(value.model_dump())
    if isinstance(value, dict):
        return {k: _to_serializable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_serializable(item) for item in value]
    return value


def create_initial_state(request: GenerateRequest) -> GenerationState:
    """创建初始状态。

    Args:
        request: 用户生成请求

    Returns:
        初始化的 GenerationState（所有值均为 dict / 基础类型）
    """
    raw = GenerationState(
        request=request.model_dump(),
        supervisor_result=None,
        vision=None,
        gameplay=None,
        narrative=None,
        logs=[],
        specialist_results={},
        retry_count=0,
        regenerate_requested=False,
        asset_context=None,
    )
    return _to_serializable(raw)


__all__ = [
    "GenerationState",
    "create_initial_state",
    "GameDesign",
    "GeneratedFiles",
    "SupervisorResult",
    "_to_serializable",
    "get_request",
    "get_supervisor_result",
    "get_validation",
    "get_unified_design",
    "get_vision",
    "get_gameplay",
    "get_narrative",
]


def get_vision(state: GenerationState) -> "VisionSpec | None":
    """从 state 中提取 Pydantic VisionSpec 对象。"""
    data = state.get("vision")
    if data is None:
        return None
    if isinstance(data, VisionSpec):
        return data
    return VisionSpec.model_validate(data)


def get_gameplay(state: GenerationState) -> "GameplaySpec | None":
    """从 state 中提取 Pydantic GameplaySpec 对象。"""
    data = state.get("gameplay")
    if data is None:
        return None
    if isinstance(data, GameplaySpec):
        return data
    return GameplaySpec.model_validate(data)


def get_narrative(state: GenerationState) -> "NarrativeSpec | None":
    """从 state 中提取 Pydantic NarrativeSpec 对象。"""
    data = state.get("narrative")
    if data is None:
        return None
    if isinstance(data, NarrativeSpec):
        return data
    return NarrativeSpec.model_validate(data)


def get_request(state: GenerationState) -> GenerateRequest:
    """从 state 中提取 Pydantic request 对象。

    state["request"] 存储为 dict 以便 Redis Checkpointer 序列化，
    此函数在需要用 Pydantic 属性的地方调用重建对象。
    """
    data = state["request"]
    if isinstance(data, GenerateRequest):
        return data
    return GenerateRequest.model_validate(data)


def get_supervisor_result(state: GenerationState) -> "SupervisorResult | None":
    """从 state 中提取 Pydantic SupervisorResult 对象。"""
    data = state.get("supervisor_result")
    if data is None:
        return None
    if isinstance(data, SupervisorResult):
        return data
    return SupervisorResult.model_validate(data)


def get_validation(state: GenerationState) -> "ValidationResult | None":
    """从 state 中提取 Pydantic ValidationResult 对象。"""
    data = state.get("validation")
    if data is None:
        return None
    if isinstance(data, ValidationResult):
        return data
    return ValidationResult.model_validate(data)


def get_unified_design(state: GenerationState) -> "UnifiedDesign | None":
    """从 state 中提取 Pydantic UnifiedDesign 对象。"""
    data = state.get("unified_design")
    if data is None:
        return None
    if isinstance(data, UnifiedDesign):
        return data
    return UnifiedDesign.model_validate(data)
