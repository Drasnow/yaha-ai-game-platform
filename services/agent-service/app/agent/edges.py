"""LangGraph 边定义。

定义节点之间的条件路由逻辑。
"""

from typing import Literal

from langgraph.constants import END

from app.agent.state import GenerationState


def route_by_supervisor(state: GenerationState) -> Literal["specialist_fan_out", "rejected"]:
    """根据 Supervisor Agent 决策结果路由。

    所有 approved（无论 simple 还是 complex）都走 specialist_fan_out，
    统一由 LLM 生成游戏代码。complexity 仅作为信息传递给 code_generator。

    Args:
        state: 当前状态

    Returns:
        路由目标: "specialist_fan_out" 或 "rejected"
    """
    supervisor_result = state.get("supervisor_result")

    if supervisor_result is None:
        # 降级保护：没有 supervisor 结果，尝试走生成路径
        return "specialist_fan_out"

    status = supervisor_result.status

    if status == "rejected":
        return "rejected"

    # 所有 approved 都走 specialist_fan_out（统一 LLM 生成路径）
    return "specialist_fan_out"


def should_retry(state: GenerationState) -> Literal["retry_workflow", "upload_workflow", "error"]:
    """验证后决定下一步。

    validator_node 成功返回时触发此边：
    - validation.passed=True           → upload_workflow
    - validation.passed=False + <3次  → retry_workflow
    - validation=None / 重试耗尽       → error（触发全局 error_handler）

    注意：validator_node 抛出的 ValidationError / ValueError 由 RetryPolicy
    在本边执行之前捕获并重试；所有重试耗尽后才执行 error_handler 并路由到 END。

    Args:
        state: 当前状态

    Returns:
        路由目标: "retry_workflow" | "upload_workflow" | "error"
    """
    validation = state.get("validation")

    if validation is None:
        return "error"

    if validation.passed:
        return "upload_workflow"

    retry_count = state.get("retry_count", 0)
    if retry_count < 3:
        return "retry_workflow"

    return "error"
