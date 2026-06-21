"""Vision Agent 节点 - 视觉设计规范生成。

使用 LLM 设计游戏的视觉风格规范。
"""

import logging
from datetime import datetime

from app.agent.state import GenerationState
from app.agent.schemas import AgentLog, VisionSpec
from app.llm.client import LLMClient
from app.llm.providers import create_provider
from app.core.config import get_settings

logger = logging.getLogger(__name__)

VISION_PROMPT = """你是一个资深游戏视觉设计师。请根据用户的创意，设计游戏的视觉风格。

## 用户创意
{prompt}
用户上传的素材内容：{assets_context}

## 设计要求
请设计一个吸引人的游戏视觉风格，包括：
1. 整体视觉风格（pixel/cartoon/minimal/neon/nature/retro/futuristic）
2. 配色方案（主色、强调色、背景色）
3. 动画效果提示
4. 游戏氛围
5. 字体风格

请以 JSON 格式输出视觉规范：
{{
    "style": "pixel/cartoon/minimal/neon/nature/retro/futuristic",
    "color_palette": {{
        "primary": "#hex",
        "accent": "#hex",
        "background": "#hex"
    }},
    "animation_hints": ["效果描述1", "效果描述2"],
    "mood": "轻松愉快/紧张刺激/神秘悬疑/怀旧复古/未来科技",
    "typography_hint": "字体风格描述"
}}
"""


async def vision_agent(state: GenerationState) -> GenerationState:
    """VisionAgent - 设计视觉规范。

    使用 LLM 分析用户创意，生成游戏的视觉设计规范。

    Args:
        state: 当前状态

    Returns:
        更新后的状态，包含 vision 字段
    """
    settings = get_settings()
    request = state["request"]

    logger.info(f"VisionAgent: 生成视觉规范, task_id={request.task_id}")

    log_start = AgentLog(
        agent="VisionAgent",
        step="start",
        message="开始生成视觉规范",
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
        prompt = VISION_PROMPT.format(
            prompt=request.prompt,
            assets_context=state.get("asset_context") or "",
        )

        # 调用 LLM 生成视觉规范
        result = await llm.generate_json(
            prompt=prompt,
            schema=VisionSpec,
        )

        await llm.close()

        log_complete = AgentLog(
            agent="VisionAgent",
            step="complete",
            message=f"视觉规范生成完成: {result.style} 风格, 氛围: {result.mood}",
            timestamp=datetime.now().isoformat(),
        )

        # 返回状态更新（只返回改动字段，不含 request 等原始字段，避免并发写冲突）
        return {
            "logs": [log_start, log_complete],
            "vision": result,
            "specialist_results": {"vision": "success"},
        }

    except Exception as e:
        logger.warning(f"VisionAgent: 生成失败，使用默认规范: {e}")

        # 使用默认视觉规范
        default_vision = VisionSpec(
            style="cartoon",
            color_palette={"primary": "#312e81", "accent": "#facc15", "background": "#0f172a"},
            animation_hints=["基础动画效果"],
            mood="轻松愉快",
            typography_hint="现代简洁字体",
        )

        log_fallback = AgentLog(
            agent="VisionAgent",
            step="fallback",
            message=f"使用默认视觉规范，原因: {str(e)}",
            timestamp=datetime.now().isoformat(),
        )

        return {
            "logs": [log_start, log_fallback],
            "vision": default_vision,
            "specialist_results": {"vision": f"fallback: {str(e)}"},
        }
