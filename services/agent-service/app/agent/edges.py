"""LangGraph 边定义。

定义节点之间的条件路由逻辑。
"""

from typing import Literal

from langgraph.constants import END
from langgraph.types import Send

from app.agent.state import GenerationState, get_supervisor_result, get_validation
from app.agent.schemas import IssueKind


def route_by_supervisor(state: GenerationState) -> list[Send] | str:
    """根据 Supervisor Agent 决策结果路由。

    rejected → 直接结束（用户请求不合法或超出能力范围）
    approved → 并行触发所有 Specialist Agents（通过 Send 列表实现动态并行）

    Args:
        state: 当前状态

    Returns:
        rejected: 流程结束
        list[Send]: 并行执行 Specialist Agents
    """
    supervisor_result = get_supervisor_result(state)

    if supervisor_result is None:
        # 降级保护：没有 supervisor 结果，尝试走生成路径
        return [
            Send("vision_agent", state),
            Send("gameplay_agent", state),
            Send("narrative_agent", state),
        ]

    status = supervisor_result.status

    if status == "rejected":
        return "rejected"

    # 所有 approved → 并行触发三个 Specialist
    return [
        Send("vision_agent", state),
        Send("gameplay_agent", state),
        Send("narrative_agent", state),
    ]


def should_retry(state: GenerationState) -> Literal["retry_workflow", "regenerate", "upload_workflow", "error"]:
    """验证后决定下一步路由。

    Validator 返回后触发此边，根据问题分类和重试次数决定：
      - passed=True               → upload_workflow
      - regenerate_requested=True  → regenerate（unfixable 标记的，不占 retry_count）
      - 存在 critical 问题         → error（直接失败）
      - 存在 fixable 问题 + 未超限 → retry_workflow（自动修复）
      - 存在 fixable 问题 + 已超限 → error（兜底）
      - 有 issues 但无法归类       → regenerate（尝试重新生成）

    注意：
      - regenerate_requested 与 retry_count 完全解耦，不会互相消耗
      - 同一 cycle 中 UNFIXABLE 优先被 retry_workflow 标记 regenerate_requested，
        下一个 cycle 直接重新生成，不再浪费 fixable 重试次数
    """
    validation = get_validation(state)

    if validation is None:
        return "error"

    if validation.passed:
        return "upload_workflow"

    issue_kinds = validation.issue_kinds or []
    retry_count = state.get("retry_count", 0)
    regenerate_requested = state.get("regenerate_requested", False)

    # 优先检查 unfixable 标记（由 retry_workflow 在上一 cycle 写入，不消耗 retry_count）
    if regenerate_requested:
        return "regenerate"

    # critical 问题 → 直接失败
    if IssueKind.CRITICAL in issue_kinds:
        return "error"

    # fixable 问题 → 自动修复
    if IssueKind.FIXABLE in issue_kinds:
        if retry_count < 3:
            return "retry_workflow"
        return "error"

    # 有 issues 但无法归类 → 视为不可修复，尝试重新生成
    if validation.issues:
        return "regenerate"

    return "error"
