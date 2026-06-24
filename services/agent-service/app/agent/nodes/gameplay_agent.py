"""Gameplay Agent 节点 - 游戏机制规范生成。

使用 LLM 设计游戏的核心玩法机制。
"""

import logging
from datetime import datetime

from app.agent.state import GenerationState, get_request, _to_serializable
from app.agent.schemas import AgentLog, GameplaySpec
from app.llm.client import LLMClient
from app.llm.providers import create_provider
from app.core.config import get_settings

logger = logging.getLogger(__name__)

GAMEPLAY_PROMPT = """你是一个资深游戏机制设计师。请根据用户的创意，设计游戏的玩法机制。

## 用户创意
{prompt}

用户上传的素材内容：
{assets_context}

## 设计要求
请设计一个有趣且可实现的游戏机制，包括：
1. 游戏类型（click/avoid/quiz/puzzle/action/endless_runner/timing）
2. 游戏目标
3. 核心玩法机制（列表形式）
4. 难度曲线
5. 计分系统
6. 时间限制（如有）
7. 获胜/失败条件
8. 操作方式

请以 JSON 格式输出游戏机制规范：
{{
    "genre": "click/avoid/quiz/puzzle/action/endless_runner/timing",
    "objective": "游戏目标描述",
    "mechanics": ["机制1", "机制2", "机制3"],
    "difficulty_curve": "难度曲线描述",
    "scoring_system": "计分系统描述",
    "time_limit": 30,
    "win_condition": "获胜条件描述",
    "fail_condition": "失败条件描述",
    "controls": ["鼠标点击", "方向键移动"]
}}
"""


async def gameplay_agent(state: GenerationState) -> GenerationState:
    """GameplayAgent - 设计游戏机制。

    使用 LLM 分析用户创意，生成游戏的玩法机制规范。

    Args:
        state: 当前状态

    Returns:
        更新后的状态，包含 gameplay 字段
    """
    settings = get_settings()
    request = get_request(state)

    logger.info(f"GameplayAgent: 生成游戏机制, task_id={request.task_id}")

    log_start = AgentLog(
        agent="GameplayAgent",
        step="start",
        message="开始生成游戏机制规范",
        timestamp=datetime.now().isoformat(),
    )

    try:
        # 创建 LLM Client
        provider = create_provider(
            provider_type=settings.llm_provider,
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            timeout=settings.llm_timeout,
            reasoning_effort=settings.llm_reasoning_effort,
            tool_output_token_limit=settings.llm_tool_output_token_limit,
            personality=settings.llm_personality,
        )
        llm = LLMClient(provider=provider)

        # 构建 prompt
        prompt = GAMEPLAY_PROMPT.format(
            prompt=request.prompt,
            assets_context=state.get("asset_context") or "",
        )

        # 调用 LLM 生成游戏机制
        result = await llm.generate_json(
            prompt=prompt,
            schema=GameplaySpec,
        )

        await llm.close()

        log_complete = AgentLog(
            agent="GameplayAgent",
            step="complete",
            message=f"游戏机制生成完成: {result.genre} 类型, 目标: {result.objective}",
            timestamp=datetime.now().isoformat(),
        )

        return _to_serializable({
            "logs": [log_start, log_complete],
            "gameplay": result,
            "specialist_results": {"gameplay": "success"},
        })

    except Exception as e:
        logger.warning(f"GameplayAgent: 生成失败，使用默认规范: {e}")

        # 使用默认游戏机制
        default_gameplay = GameplaySpec(
            genre="click",
            objective="30 秒内点击目标获得高分",
            mechanics=["点击得分", "时间限制"],
            difficulty_curve="前期简单，后期加速",
            scoring_system="每点击一次 +1 分",
            time_limit=30,
            win_condition="达到目标分数",
            fail_condition="时间耗尽",
            controls=["鼠标点击"],
        )

        log_fallback = AgentLog(
            agent="GameplayAgent",
            step="fallback",
            message=f"使用默认游戏机制，原因: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )

        return _to_serializable({
            "logs": [log_start, log_fallback],
            "gameplay": default_gameplay,
            "specialist_results": {"gameplay": f"fallback: {str(e)}"},
        })
