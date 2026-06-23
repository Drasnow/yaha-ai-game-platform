"""Supervisor Agent 节点 - 入口判断与路由。

使用 LLM 分析用户输入，判断：
- 是否是游戏相关请求（排除闲聊、问答、无关内容）
- 如果是游戏请求，判断复杂度（简单 / 复杂）
- 根据判断结果决定后续执行路径
"""

import logging
from datetime import datetime

from pydantic import BaseModel

from app.agent.state import GenerationState
from app.agent.schemas import AgentLog, SupervisorResult
from app.agent.asset_content import fetch_all_asset_contents, build_assets_context
from app.llm.client import LLMClient
from app.llm.providers import create_provider
from app.core.config import get_settings

logger = logging.getLogger(__name__)

SUPERVISOR_PROMPT = """你是一个游戏创意审核助手。请分析用户的输入，判断其类型。

用户输入：{prompt}

用户上传的素材内容：{assets_context}

请从以下维度判断：

## 1. 有效性判断
判断用户输入是否是与游戏设计相关的请求：
- **无关内容**（必须拒绝）：打招呼（"你好"、"Hello"）、闲聊（"今天天气如何"）、知识问答、非游戏类创意
- **有效游戏请求**：任何与游戏设计、互动体验相关的描述

## 2. 复杂度判断（仅对有效游戏请求）
- **简单游戏**：
  - 字数较少
  - 与预置模板高度相似：点击得分、问答闯关、躲避障碍
  - 无特殊玩法要求，无多角色/多关卡需求
  - 示例："做个点击得分的游戏"、"生成一个问答游戏"、"来个小游戏"
- **复杂游戏**：
  - 字数较多
  - 有独特创意、多角色、多关卡、复杂机制需求
  - 示例："做一个RPG游戏"、"设计一个有多重结局的解谜游戏"

请严格按照以下 JSON Schema 输出：
{{
    "status": "approved_simple | approved_complex | rejected",
    "complexity": "simple | medium | complex",
    "reason": "判断理由（1-2句话）",
    "feedback_message": "如果 rejected，给用户的友好引导，格式示例：抱歉，我只处理游戏设计相关的请求哦。请详细告诉我你想做什么样的游戏吧！"
}}

判断标准：
- 闲聊、问候、知识问答、明显非游戏类 → rejected
- 字数较少 且 常见游戏类型 → approved_simple
- 字数较多 或 有独特玩法要求 → approved_complex"""


class SupervisorSchema(BaseModel):
    """Supervisor Agent 输出 schema。"""
    status: str  # "approved_simple" | "approved_complex" | "rejected"
    complexity: str  # "simple" | "medium" | "complex"
    reason: str
    feedback_message: str


async def supervisor_agent(state: GenerationState) -> GenerationState:
    """Supervisor Agent - 入口判断与路由决策。

    使用 LLM 分析用户输入，判断是否有效以及复杂度，
    决定后续执行路径。

    Args:
        state: 当前状态

    Returns:
        更新后的状态，包含 supervisor_result 和路由决策
    """
    settings = get_settings()
    request = state["request"]

    logger.info(f"SupervisorAgent: 分析输入, task_id={request.task_id}")

    # 获取用户上传的素材内容
    asset_context = ""
    if request.assets:
        try:
            contents = await fetch_all_asset_contents(request.assets)
            asset_context = build_assets_context(contents)
            logger.info(f"SupervisorAgent: 已加载 {len([c for c in contents if c.content])} 个素材，共 {len(asset_context)} 字符")
        except Exception as exc:
            logger.warning(f"SupervisorAgent: 素材加载失败，跳过: {exc}")

    log_start = AgentLog(
        agent="SupervisorAgent",
        step="start",
        message="开始分析用户输入",
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

        # 调用 LLM 进行判断
        prompt = SUPERVISOR_PROMPT.format(prompt=request.prompt, assets_context=asset_context)
        result = await llm.generate_json(prompt=prompt, schema=SupervisorSchema)

        await llm.close()

        # 构建 SupervisorResult
        supervisor_result = SupervisorResult(
            status=result.status,
            complexity=result.complexity,
            reason=result.reason,
            feedback_message=result.feedback_message,
        )

        log_complete = AgentLog(
            agent="SupervisorAgent",
            step="decision",
            message=f"决策完成: {result.status}, 复杂度: {result.complexity}, 原因: {result.reason}",
            timestamp=datetime.now().isoformat(),
        )

        logger.info(
            f"SupervisorAgent: 决策结果 status={result.status}, "
            f"complexity={result.complexity}, task_id={request.task_id}"
        )

        return {
            **state,
            "logs": [log_start, log_complete],
            "supervisor_result": supervisor_result,
            "asset_context": asset_context,
        }

    except Exception as e:
        logger.warning(f"SupervisorAgent: LLM 调用失败，使用降级策略: {e}")

        # 降级策略：基于 prompt 长度简单判断
        prompt_len = len(request.prompt)
        if prompt_len < 10:
            # 太短，大概率不是游戏请求
            supervisor_result = SupervisorResult(
                status="rejected",
                complexity="simple",
                reason=f"prompt 长度仅 {prompt_len} 字符，可能是无关输入",
                feedback_message="抱歉，我只处理游戏设计相关的请求哦。请告诉我你想做什么类型的游戏吧！",
            )
        elif prompt_len < 100:
            supervisor_result = SupervisorResult(
                status="approved_simple",
                complexity="simple",
                reason=f"prompt 长度 {prompt_len} 字符，判定为简单游戏",
                feedback_message="",
            )
        else:
            supervisor_result = SupervisorResult(
                status="approved_complex",
                complexity="complex",
                reason=f"prompt 长度 {prompt_len} 字符，判定为复杂游戏",
                feedback_message="",
            )

        log_fallback = AgentLog(
            agent="SupervisorAgent",
            step="fallback",
            message=f"降级策略: status={supervisor_result.status}, 原因: {supervisor_result.reason}",
            timestamp=datetime.now().isoformat(),
        )

        return {
            **state,
            "logs": [log_start, log_fallback],
            "supervisor_result": supervisor_result,
            "asset_context": asset_context,
        }
