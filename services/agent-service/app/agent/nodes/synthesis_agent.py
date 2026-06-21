"""Synthesis Agent 节点 - 设计整合。

整合所有 Specialist Agent 的输出，生成统一的游戏设计规范。
"""

import logging
import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.agent.state import GenerationState
from app.agent.schemas import AgentLog, UnifiedDesign
from app.llm.client import LLMClient
from app.llm.providers import create_provider
from app.core.config import get_settings

logger = logging.getLogger(__name__)

SYNTHESIS_PROMPT = """你是一个游戏设计总监。请整合所有设计规范，生成最终的游戏设计文档。

## 用户原始创意
{prompt}

## 视觉规范
{vision}

## 游戏机制
{gameplay}

## 叙事内容
{narrative}

## Supervisor 复杂度判断
{complexity_hint}

## 整合要求
1. 根据所有规范生成一个统一的游戏设计
2. 确定游戏标题（简洁有吸引力，8-20字符）
3. 确定游戏描述（1-2句话）
4. 确定游戏标签（3-5个）
5. 选择最适合的模板类型作为参考
6. 确认复杂度（必须与 Supervisor 判断一致）

请以 JSON 格式输出整合后的设计：
{{
    "title": "游戏标题",
    "description": "游戏描述",
    "tags": ["tag1", "tag2", "tag3"],
    "template_hint": "click/avoid/quiz/puzzle/action/endless_runner/timing",
    "complexity": "simple/medium/complex（必须与 Supervisor 判断一致）"
}}
"""


class SynthesisOutput(BaseModel):
    """整合输出。"""
    title: str
    description: str
    tags: list[str]
    template_hint: str
    complexity: str  # simple / medium / complex


def _extract_theme(prompt: str) -> str:
    """从 prompt 中提取主题词。"""
    cleaned = prompt
    for token in ["做一个", "生成", "游戏", "互动", "点击", "得分", "问答", "躲避", "挑战", "玩家", "选择", "答案"]:
        cleaned = cleaned.replace(token, " ")
    words = re.findall(r"[一-鿿A-Za-z0-9]{2,8}", cleaned)
    if not words:
        return "Yaha"
    blocked = {"一个", "玩法", "创意", "需要", "可以", "越多越好"}
    for word in words:
        if word not in blocked:
            return word[:8]
    return "Yaha"


async def synthesis_agent(state: GenerationState) -> GenerationState:
    """SynthesisAgent - 整合设计规范。

    整合 VisionAgent、GameplayAgent、NarrativeAgent 的输出，
    生成统一的游戏设计规范。

    Args:
        state: 当前状态

    Returns:
        更新后的状态，包含 unified_design 字段
    """
    settings = get_settings()
    request = state["request"]

    logger.info(f"SynthesisAgent: 整合设计规范, task_id={request.task_id}")

    logs: list[AgentLog] = []

    logs.append(AgentLog(
        agent="SynthesisAgent",
        step="start",
        message="开始整合 Specialist 设计规范",
        timestamp=datetime.now().isoformat(),
    ))

    try:
        # 检查是否有足够的 Specialist 输出
        vision = state.get("vision")
        gameplay = state.get("gameplay")
        narrative = state.get("narrative")

        if vision is None:
            raise ValueError("VisionAgent 输出缺失")

        # 构建 prompt
        supervisor_result = state.get("supervisor_result")
        complexity_hint = getattr(supervisor_result, "complexity", "simple") if supervisor_result else "simple"
        complexity_hint_text = f"Supervisor 判断为 {complexity_hint} 复杂度游戏"

        prompt = SYNTHESIS_PROMPT.format(
            prompt=request.prompt,
            vision=f"风格: {vision.style}, 氛围: {vision.mood}, 配色: {vision.color_palette}",
            gameplay=f"类型: {gameplay.genre if gameplay else '未指定'}, 目标: {gameplay.objective if gameplay else '未指定'}, 操作: {gameplay.controls if gameplay else '未指定'}",
            narrative=f"主题: {narrative.theme if narrative else '未指定'}, 故事: {narrative.story_hook if narrative else '未指定'}",
            complexity_hint=complexity_hint_text,
        )

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

        # 调用 LLM 整合设计
        result = await llm.generate_json(
            prompt=prompt,
            schema=SynthesisOutput,
        )

        await llm.close()

        # 构建 UnifiedDesign
        unified_design = UnifiedDesign(
            title=result.title,
            description=result.description,
            tags=result.tags,
            vision=vision,
            gameplay=gameplay,
            narrative=narrative,
            template_hint=result.template_hint,
            complexity=getattr(result, "complexity", complexity_hint) or complexity_hint,
        )

        logs.append(AgentLog(
            agent="SynthesisAgent",
            step="complete",
            message=f"设计整合完成: {unified_design.title}",
            timestamp=datetime.now().isoformat(),
        ))

        return {
            **state,
            "logs": logs,
            "unified_design": unified_design,
        }

    except Exception as e:
        logger.warning(f"SynthesisAgent: 整合失败，使用默认设计: {e}")

        # 使用默认设计
        theme = _extract_theme(request.prompt)
        vision = state.get("vision")
        supervisor_result = state.get("supervisor_result")
        fallback_complexity = getattr(supervisor_result, "complexity", "simple") if supervisor_result else "simple"

        unified_design = UnifiedDesign(
            title=f"{theme}游戏",
            description=f"根据创意生成的游戏：{request.prompt[:50]}...",
            tags=["generated", "llm", "yaha"],
            vision=vision,
            gameplay=state.get("gameplay"),
            narrative=state.get("narrative"),
            template_hint="click",
            complexity=fallback_complexity,
        )

        logs.append(AgentLog(
            agent="SynthesisAgent",
            step="fallback",
            message=f"使用默认设计，原因: {str(e)}",
            timestamp=datetime.now().isoformat(),
        ))

        return {
            **state,
            "logs": logs,
            "unified_design": unified_design,
        }
