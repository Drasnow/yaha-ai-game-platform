"""Code Generator 节点 - 代码生成。

基于统一设计规范，通过 LLM 生成游戏代码。
"""

import logging
import json
import re
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

from app.agent.state import GenerationState
from app.agent.schemas import AgentLog
from app.agent.builder import TEMPLATE_RENDERERS, GameDesign, GeneratedFiles
from app.agent.validator import validate_generated_files
from app.llm.client import LLMClient
from app.llm.providers import create_provider
from app.core.config import get_settings

logger = logging.getLogger(__name__)


# ========================================
# LLM 输出 Schema
# ========================================

class GeneratedGameCode(BaseModel):
    """LLM 生成的完整游戏代码"""

    index_html: str = Field(
        description="index.html 完整文件内容，包含游戏 HTML 结构、引用 CSS 和 JS"
    )
    style_css: str = Field(
        description="style.css 完整文件内容，控制游戏视觉样式"
    )
    game_js: str = Field(
        description="game.js 完整文件内容，包含所有游戏逻辑"
    )
    manifest_json: str = Field(
        description="manifest.json 完整文件内容，包含游戏元数据"
    )
    generation_notes: str = Field(
        description="代码生成说明，解释设计决策和注意事项",
        default=""
    )


# ========================================
# LLM 提示词构建
# ========================================

def _build_game_code_prompt(
    title: str,
    prompt: str,
    style: str,
    color_palette: dict,
    mood: str,
    typography_hint: str,
    animation_hints: list,
    genre: str,
    objective: str,
    mechanics: list,
    difficulty_curve: str,
    scoring_system: str,
    time_limit: int | None,
    win_condition: str,
    fail_condition: str,
    controls: list,
    theme: str,
    story_hook: str,
    character_description: str,
    progression_narrative: str,
    feedback_messages: dict,
    complexity: str,
) -> str:
    """构建游戏代码生成提示词。"""

    palette_str = json.dumps(color_palette, ensure_ascii=False)
    mechanics_str = "\n".join(f"  - {m}" for m in mechanics)
    controls_str = "、".join(controls)
    animation_str = "\n".join(f"  - {a}" for a in animation_hints) if animation_hints else "无特殊动画"

    feedback_str = "\n".join(f"  - {k}: {v}" for k, v in feedback_messages.items())

    is_complex = complexity in ("complex", "medium")
    complexity_instruction = ""

    if is_complex:
        complexity_instruction = """
## 复杂度要求（复杂游戏）
- 必须实现完整的游戏循环：开始 → 游戏中 → 结束
- 实现多关卡推进机制（至少 3 个关卡）
- 实现道具收集/背包系统
- 实现密码锁/拼图等谜题逻辑
- 实现计分系统与评级
- 实现提示系统
- 实现行为记录（重试次数、提示使用次数等）
- 游戏时长建议 3-5 分钟
"""
    else:
        complexity_instruction = """
## 复杂度要求（简单游戏）
- 核心循环：点击/选择 → 反馈 → 计分
- 简单关卡结构（单关或简单多关）
- 基础计分系统
- 游戏时长建议 30-60 秒
"""

    return f"""你是一个资深 HTML5 游戏开发者。请根据以下设计规范，生成一个完整的、可运行的单文件 HTML5 游戏。

## 游戏基本信息
- 标题：{title}
- 用户原始需求：{prompt}

## 视觉设计规范
- 视觉风格：{style}
- 配色方案（必须严格使用）：{palette_str}
- 游戏氛围：{mood}
- 字体风格：{typography_hint}
- 动画效果要求：
{animation_str}

## 游戏机制规范
- 游戏类型：{genre}
- 游戏目标：{objective}
- 核心玩法：
{mechanics_str}
- 难度曲线：{difficulty_curve}
- 计分系统：{scoring_system}
- 时间限制：{"无限制" if time_limit is None else f"{time_limit}秒"}
- 获胜条件：{win_condition}
- 失败条件：{fail_condition}
- 操作方式：{controls_str}

## 叙事内容规范
- 游戏主题：{theme}
- 开场描述（story_hook）：{story_hook}
- 角色描述：{character_description}
- 进度叙事：{progression_narrative}
- 反馈消息：
{feedback_str}

{complexity_instruction}

## 技术要求
1. 生成 4 个独立文件：index.html、style.css、game.js、manifest.json
2. 所有游戏逻辑必须在 game.js 中实现（纯 JavaScript，不依赖外部库）
3. index.html 引用 style.css 和 game.js
4. 颜色必须严格使用 color_palette 中的值
5. 禁止使用任何外部图片、音视频资源（纯 CSS/Canvas 绘图）
6. 必须实现开始界面、游戏中界面、结束界面（含分数展示）
7. 必须实现响应式布局（适配移动端）
8. 禁止内联 style 和 script 标签
9. game.js 中禁止使用 async/await/Promise（保持单线程事件循环）
11. **严禁使用 `Function()` 构造函数或 `new Function()`**（会导致安全校验失败）

## 输出要求
请严格按照以下 JSON Schema 输出，**不要添加任何额外内容，不要添加 markdown 代码块标记**：
{{
  "index_html": "index.html 完整内容",
  "style_css": "style.css 完整内容",
  "game_js": "game.js 完整内容",
  "manifest_json": "manifest.json 完整内容（JSON 字符串，schemaVersion='1.0', entry='index.html', runtime='iframe-html-v1'）",
  "generation_notes": "设计说明，1-2 句话"
}}"""


# ========================================
# 主节点
# ========================================

async def code_generator_node(state: GenerationState) -> GenerationState:
    """CodeGeneratorNode - 调用 LLM 生成游戏代码。

    基于 unified_design 中包含的 vision、gameplay、narrative 规范，
    调用 LLM 生成完整的游戏代码文件。

    Args:
        state: 当前状态

    Returns:
        更新后的状态，包含 generated_files 字段
    """
    settings = get_settings()
    request = state["request"]
    unified_design = state.get("unified_design")

    logger.info(f"CodeGenerator: 生成游戏代码, task_id={request.task_id}")

    log_start = AgentLog(
        agent="CodeGenerator",
        step="start",
        message="开始调用 LLM 生成游戏代码",
        timestamp=datetime.now().isoformat(),
    )

    try:
        # -----------------------------------------------------------
        # 补偿逻辑（Saga）：若 unified_design 无效，提前降级到模板
        # -----------------------------------------------------------
        if unified_design is None:
            raise ValueError("unified_design 缺失，请先运行 SynthesisAgent")

        complexity = getattr(unified_design, "complexity", "simple")
        vision = unified_design.vision
        gameplay = unified_design.gameplay
        narrative = unified_design.narrative

        # 构建 LLM 提示词
        prompt = _build_game_code_prompt(
            title=unified_design.title,
            prompt=request.prompt,
            style=vision.style if vision else "pixel",
            color_palette=vision.color_palette if vision else {"primary": "#312e81", "accent": "#facc15", "background": "#0f172a"},
            mood=vision.mood if vision else "轻松愉快",
            typography_hint=vision.typography_hint if vision else "现代简洁字体",
            animation_hints=vision.animation_hints if vision else [],
            genre=gameplay.genre if gameplay else "click",
            objective=gameplay.objective if gameplay else "完成游戏目标",
            mechanics=gameplay.mechanics if gameplay else [],
            difficulty_curve=gameplay.difficulty_curve if gameplay else "逐步提升",
            scoring_system=gameplay.scoring_system if gameplay else "得分制",
            time_limit=gameplay.time_limit if gameplay else None,
            win_condition=gameplay.win_condition if gameplay else "达到目标",
            fail_condition=gameplay.fail_condition if gameplay else "时间耗尽",
            controls=gameplay.controls if gameplay else ["鼠标点击"],
            theme=narrative.theme if narrative else "通用游戏",
            story_hook=narrative.story_hook if narrative else "欢迎来到游戏世界！",
            character_description=narrative.character_description if narrative else "游戏角色",
            progression_narrative=narrative.progression_narrative if narrative else "逐步推进",
            feedback_messages=narrative.feedback_messages if narrative else {},
            complexity=complexity,
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

        # 调用 LLM 生成代码（网络/LLM 错误由 RetryPolicy 重试）
        result: GeneratedGameCode = await llm.generate_json(
            prompt=prompt,
            schema=GeneratedGameCode,
            max_tokens=25000,
        )

        await llm.close()

        log_llm_done = AgentLog(
            agent="CodeGenerator",
            step="llm_complete",
            message=f"LLM 代码生成完成: {unified_design.title}",
            timestamp=datetime.now().isoformat(),
        )

        # 验证并构建 manifest
        files: dict[str, str] = {
            "index.html": result.index_html,
            "style.css": result.style_css,
            "game.js": result.game_js,
            "manifest.json": result.manifest_json,
        }

        # 验证文件内容（ValueError 由 RetryPolicy 决定是否重试）
        _validate_files(files)

        manifest = json.loads(result.manifest_json)

        log_validate = AgentLog(
            agent="CodeGenerator",
            step="validate_complete",
            message=f"已生成 {len(files)} 个文件: {', '.join(files.keys())}",
            timestamp=datetime.now().isoformat(),
        )

        return {
            **state,
            "logs": [log_start, log_llm_done, log_validate],
            "generated_files": {
                "files": files,
                "manifest": manifest,
            },
        }

    except ValueError:
        # -----------------------------------------------------------
        # 业务逻辑错误（unified_design 缺失、manifest 格式错误等）
        # → 跳过 LLM 重试，改用模板降级
        # -----------------------------------------------------------
        logger.warning(f"CodeGenerator: 业务错误，改用模板降级")

        template_hint = getattr(unified_design, "template_hint", None) if unified_design else None
        template_map = {
            "click": "click_challenge",
            "avoid": "avoid_obstacle",
            "quiz": "quiz_game",
            "puzzle": "quiz_game",
            "action": "avoid_obstacle",
            "endless_runner": "avoid_obstacle",
            "timing": "click_challenge",
        }
        template_name = template_map.get(template_hint, "click_challenge") if template_hint else "click_challenge"

        vision = unified_design.vision if unified_design else None
        gameplay = unified_design.gameplay if unified_design else None

        design = GameDesign(
            template=template_name,
            title=unified_design.title if unified_design else request.prompt[:20],
            description=getattr(unified_design, "description", "") if unified_design else "",
            tags=getattr(unified_design, "tags", []) if unified_design else [],
            primary_color=vision.color_palette.get("primary", "#312e81") if vision else "#312e81",
            accent_color=vision.color_palette.get("accent", "#facc15") if vision else "#facc15",
            objective=gameplay.objective if gameplay else "完成游戏目标",
        )

        generated: GeneratedFiles = TEMPLATE_RENDERERS[template_name](
            design, request.prompt, request.assets
        )

        log_fallback = AgentLog(
            agent="CodeGenerator",
            step="fallback",
            message=f"模板降级生成: {template_name}",
            timestamp=datetime.now().isoformat(),
        )

        return {
            **state,
            "logs": [log_start, log_fallback],
            "generated_files": {
                "files": generated.files,
                "manifest": generated.manifest,
            },
        }

    except Exception:
        # LLM 调用 / 网络错误：交给 RetryPolicy 重试，不做降级
        raise


def _validate_files(files: dict[str, str]) -> None:
    """验证生成的文件内容。

    Args:
        files: 文件名字典

    Raises:
        ValueError: 文件内容不符合要求
    """
    required_files = ["index.html", "style.css", "game.js", "manifest.json"]

    for fname in required_files:
        if fname not in files:
            raise ValueError(f"缺少必需文件: {fname}")

        content = files[fname]
        if not content or len(content.strip()) == 0:
            raise ValueError(f"文件 {fname} 内容为空")

    # 检查 index.html 引用了正确的文件
    html = files["index.html"]
    if 'href="style.css"' not in html and "href='style.css'" not in html:
        raise ValueError("index.html 未正确引用 style.css")
    if 'src="game.js"' not in html and "src='game.js'" not in html:
        raise ValueError("index.html 未正确引用 game.js")

    # 检查 CSS 和 JS 不为空
    if len(files["style.css"].strip()) < 10:
        raise ValueError("style.css 内容过短")
    if len(files["game.js"].strip()) < 10:
        raise ValueError("game.js 内容过短")

    # 验证 manifest.json 可解析
    try:
        manifest = json.loads(files["manifest.json"])
        if manifest.get("runtime") != "iframe-html-v1":
            raise ValueError("manifest.json runtime 必须为 'iframe-html-v1'")
    except json.JSONDecodeError as e:
        raise ValueError(f"manifest.json 格式错误: {e}")
