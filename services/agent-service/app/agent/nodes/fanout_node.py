"""Specialist Fan-Out 节点 - 并行分发。

初始化 Specialist 执行前的状态。
"""

import logging
from datetime import datetime

from app.agent.state import GenerationState
from app.agent.schemas import AgentLog

logger = logging.getLogger(__name__)


async def specialist_fan_out(state: GenerationState) -> GenerationState:
    """Specialist Fan-Out - 初始化并行执行状态。

    这是一个普通节点，返回状态更新。
    实际的 Send 并行分发在边定义中处理。

    Args:
        state: 当前状态

    Returns:
        更新后的状态
    """
    logger.info(f"SpecialistFanOut: 准备并行分发, task_id={state['request'].task_id}")

    log_entry = AgentLog(
        agent="SpecialistFanOut",
        step="prepare",
        message="准备并行执行 Specialist Agents",
        timestamp=datetime.now().isoformat(),
    )

    return {
        **state,
        "logs": [log_entry],
        "specialist_results": {},
    }
