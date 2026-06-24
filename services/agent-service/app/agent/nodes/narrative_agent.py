"""Narrative Agent 节点 - 叙事内容规范生成。

使用 LLM 设计游戏的叙事元素和反馈内容。
"""

import logging
from datetime import datetime

from app.agent.state import GenerationState, get_request, _to_serializable
from app.agent.schemas import AgentLog, NarrativeSpec
from app.llm.client import LLMClient
from app.llm.providers import create_provider
from app.core.config import get_settings

logger = logging.getLogger(__name__)

NARRATIVE_PROMPT = """你是一个资深游戏叙事设计师。请根据用户的创意，设计游戏的叙事元素。

## 用户创意
{prompt}

用户上传的素材内容：
{assets_context}

## 设计要求
请设计一个吸引人的游戏叙事，包括：
1. 游戏主题
2. 故事钩子（吸引玩家的开场描述）
3. 角色描述
4. 进度叙事（随着游戏进行的故事发展）
5. 反馈消息（成功/失败/特殊时刻的消息）

请以 JSON 格式输出叙事规范：
{{
    "theme": "游戏主题",
    "story_hook": "吸引玩家的开场描述，1-2句话",
    "character_description": "角色描述",
    "progression_narrative": "随着游戏进行的故事发展描述",
    "feedback_messages": {{
        "start": "开始游戏消息",
        "success": "成功反馈消息",
        "wrong": "错误反馈消息",
        "fail": "失败消息",
        "win": "获胜消息"
    }}
}}
"""


async def narrative_agent(state: GenerationState) -> GenerationState:
    """NarrativeAgent - 设计叙事内容。

    使用 LLM 分析用户创意，生成游戏的叙事内容规范。

    Args:
        state: 当前状态

    Returns:
        更新后的状态，包含 narrative 字段
    """
    settings = get_settings()
    request = get_request(state)

    logger.info(f"NarrativeAgent: 生成叙事内容, task_id={request.task_id}")

    log_start = AgentLog(
        agent="NarrativeAgent",
        step="start",
        message="开始生成叙事内容规范",
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
        prompt = NARRATIVE_PROMPT.format(
            prompt=request.prompt,
            assets_context=state.get("asset_context") or "",
        )

        # 调用 LLM 生成叙事内容
        result = await llm.generate_json(
            prompt=prompt,
            schema=NarrativeSpec,
        )

        await llm.close()

        log_complete = AgentLog(
            agent="NarrativeAgent",
            step="complete",
            message=f"叙事内容生成完成: 主题={result.theme}",
            timestamp=datetime.now().isoformat(),
        )

        return _to_serializable({
            "logs": [log_start, log_complete],
            "narrative": result,
            "specialist_results": {"narrative": "success"},
        })

    except Exception as e:
        logger.warning(f"NarrativeAgent: 生成失败，使用默认规范: {e}")

        # 使用默认叙事规范
        default_narrative = NarrativeSpec(
            theme="通用游戏",
            story_hook="欢迎来到游戏世界！",
            character_description="可爱的游戏角色",
            progression_narrative="随着分数增加，难度逐渐提升，体验更多乐趣",
            feedback_messages={
                "start": "游戏开始！祝你好运！",
                "success": "太棒了！",
                "wrong": "再想想...",
                "fail": "游戏结束！再试一次吧！",
                "win": "恭喜你获胜！",
            },
        )

        log_fallback = AgentLog(
            agent="NarrativeAgent",
            step="fallback",
            message=f"使用默认叙事内容，原因: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )

        return _to_serializable({
            "logs": [log_start, log_fallback],
            "narrative": default_narrative,
            "specialist_results": {"narrative": f"fallback: {str(e)}"},
        })
