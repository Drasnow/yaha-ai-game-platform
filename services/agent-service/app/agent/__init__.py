"""Agent 模块。

包含 LangGraph StateGraph 实现和 Agent 节点。
"""

from app.agent.state import GenerationState, create_initial_state
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
from app.agent.graph import (
    get_generation_graph,
    run_generation,
    run_generation_stream,
)
from app.agent.edges import (
    route_by_supervisor,
    should_retry,
)

__all__ = [
    # State
    "GenerationState",
    "create_initial_state",
    # Schemas
    "VisionSpec",
    "GameplaySpec",
    "NarrativeSpec",
    "UnifiedDesign",
    "ValidationResult",
    "UploadResult",
    "AgentLog",
    "SupervisorResult",
    # Graph
    "get_generation_graph",
    "run_generation",
    "run_generation_stream",
    # Edges
    "route_by_supervisor",
    "should_retry",
]
