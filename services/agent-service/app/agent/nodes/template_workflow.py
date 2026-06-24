"""Template Workflow 节点 - 模板快速生成（设计阶段）。

基于预定义模板生成游戏设计规范（UnifiedDesign），
文件渲染和验证交给下游 code_generator_agent 和 validator_workflow 完成。
"""

import logging
import re
from datetime import datetime

from app.agent.state import GenerationState, get_request, _to_serializable
from app.agent.schemas import AgentLog, UnifiedDesign, VisionSpec, GameplaySpec, NarrativeSpec
from app.agent.builder import GameDesign

logger = logging.getLogger(__name__)


# 模板关键词映射
TEMPLATE_KEYWORDS = {
    "quiz_game": ["问答", "答题", "quiz", "知识", "选择题", "题库", "闯关", "quiz"],
    "avoid_obstacle": ["躲避", "闪避", "障碍", "avoid", "dodge", "飞船", "跑酷", "生存", "跳跃"],
    "click_challenge": ["点击", "得分", "星星", "click", "挑战", "收集", "连击"],
}
DEFAULT_TEMPLATE = "click_challenge"


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


def _select_template(prompt: str) -> tuple[str, str]:
    """根据 prompt 选择模板。"""
    prompt_lower = prompt.lower()
    for candidate, keywords in TEMPLATE_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in prompt_lower:
                return candidate, keyword
    return DEFAULT_TEMPLATE, "默认点击玩法"


async def template_workflow(state: GenerationState) -> GenerationState:
    """模板工作流 - 生成游戏设计规范（快速路径）。

    基于用户 prompt 选择合适模板，生成 UnifiedDesign 规范。
    文件渲染由下游 code_generator_agent 完成。

    Args:
        state: 当前状态

    Returns:
        更新后的状态，包含 unified_design 字段
    """
    request = get_request(state)
    logger.info(f"TemplateWorkflow: 快速生成设计规范, task_id={request.task_id}")

    logs: list[AgentLog] = []

    logs.append(AgentLog(
        agent="TemplateWorkflow",
        step="start",
        message="开始模板快速生成设计规范",
        timestamp=datetime.now().isoformat(),
    ))

    try:
        # 1. 解析 prompt，选择模板
        selected_template, matched_keyword = _select_template(request.prompt)
        theme = _extract_theme(request.prompt)

        logs.append(AgentLog(
            agent="TemplateWorkflow",
            step="parse_prompt",
            message=f"已解析创意并选择模板: {selected_template}（命中: {matched_keyword}）",
            timestamp=datetime.now().isoformat(),
        ))

        # 2. 生成设计规范
        design_map = {
            "click_challenge": GameDesign(
                template="click_challenge",
                title=f"{theme}点击挑战",
                description=f"根据创意生成的 30 秒点击得分小游戏：{request.prompt}",
                tags=["click", "casual", "generated", "template"],
                primary_color="#312e81",
                accent_color="#facc15",
                objective="30 秒内点击目标获得高分",
            ),
            "avoid_obstacle": GameDesign(
                template="avoid_obstacle",
                title=f"{theme}躲避挑战",
                description=f"根据创意生成的方向键躲避障碍小游戏：{request.prompt}",
                tags=["avoid", "action", "generated", "template"],
                primary_color="#7f1d1d",
                accent_color="#fb7185",
                objective="操控角色躲避障碍，坚持更久",
            ),
            "quiz_game": GameDesign(
                template="quiz_game",
                title=f"{theme}问答闯关",
                description=f"根据创意生成的轻量问答互动游戏：{request.prompt}",
                tags=["quiz", "knowledge", "generated", "template"],
                primary_color="#1d4ed8",
                accent_color="#93c5fd",
                objective="连续回答问题并获得分数",
            ),
        }

        design = design_map[selected_template]

        # 3. 创建 UnifiedDesign
        unified_design = UnifiedDesign(
            title=design.title,
            description=design.description,
            tags=design.tags,
            vision=VisionSpec(
                style="cartoon",
                color_palette={"primary": design.primary_color, "accent": design.accent_color, "background": "#0f172a"},
                animation_hints=["点击反馈动画", "目标移动动画"],
                mood="轻松愉快",
                typography_hint="现代简洁字体",
            ),
            gameplay=GameplaySpec(
                genre="click" if selected_template == "click_challenge" else ("avoid" if selected_template == "avoid_obstacle" else "quiz"),
                objective=design.objective,
                mechanics=["点击得分", "时间限制"],
                difficulty_curve="前期简单，后期加速",
                scoring_system="每点击一次 +1 分",
                time_limit=30 if selected_template == "click_challenge" else None,
                win_condition="达到目标分数或时间结束",
                fail_condition="时间耗尽",
                controls=["鼠标点击"],
            ),
            narrative=NarrativeSpec(
                theme=theme,
                story_hook=f"欢迎来到 {theme} 世界！",
                character_description="可爱的游戏角色",
                progression_narrative="随着分数增加，难度逐渐提升",
                feedback_messages={
                    "start": "游戏开始！",
                    "success": "太棒了！",
                    "fail": "时间到！再试一次吧！",
                },
            ),
            template_hint=selected_template,
        )

        logs.append(AgentLog(
            agent="TemplateWorkflow",
            step="design_complete",
            message=f"设计规范生成完成: {unified_design.title}",
            timestamp=datetime.now().isoformat(),
        ))

        # 4. 不再渲染文件和验证，交给下游 code_generator_agent 和 validator_workflow
        return _to_serializable({
            **state,
            "logs": logs,
            "unified_design": unified_design,
            "generation_path": "template",
        })

    except Exception as e:
        logger.error(f"TemplateWorkflow: 生成失败: {e}")

        logs.append(AgentLog(
            agent="TemplateWorkflow",
            step="error",
            message=f"生成失败: {str(e)}",
            timestamp=datetime.now().isoformat(),
        ))

        return _to_serializable({
            **state,
            "logs": logs,
            "error": f"模板生成失败: {str(e)}",
        })
