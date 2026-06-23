"""Agent 层的 Pydantic Schemas 定义。

包含所有 Agent 节点的输入输出规范。
"""

from typing import Literal

from pydantic import BaseModel, Field


class VisionSpec(BaseModel):
    """视觉设计规范"""

    style: Literal["pixel", "cartoon", "minimal", "neon", "nature", "retro", "futuristic"] = Field(
        description="游戏视觉风格"
    )
    color_palette: dict[str, str] = Field(
        description="配色方案，如 {'primary': '#xxx', 'accent': '#xxx', 'background': '#xxx'}"
    )
    animation_hints: list[str] = Field(
        description="动画效果提示列表"
    )
    mood: Literal["轻松愉快", "紧张刺激", "神秘悬疑", "怀旧复古", "未来科技"] = Field(
        description="游戏整体氛围"
    )
    typography_hint: str = Field(
        description="字体风格描述"
    )


class GameplaySpec(BaseModel):
    """游戏机制规范"""

    genre: Literal["click", "avoid", "quiz", "puzzle", "action", "endless_runner", "timing"] = Field(
        description="游戏类型"
    )
    objective: str = Field(
        description="游戏目标描述"
    )
    mechanics: list[str] = Field(
        description="核心玩法机制列表"
    )
    difficulty_curve: str = Field(
        description="难度曲线描述"
    )
    scoring_system: str = Field(
        description="计分系统描述"
    )
    time_limit: int | None = Field(
        default=None,
        description="时间限制（秒），无限制为 None"
    )
    win_condition: str = Field(
        description="获胜条件"
    )
    fail_condition: str = Field(
        description="失败条件"
    )
    controls: list[str] = Field(
        description="操作方式列表，如 ['鼠标点击', '方向键移动']"
    )


class NarrativeSpec(BaseModel):
    """叙事内容规范"""

    theme: str = Field(
        description="游戏主题"
    )
    story_hook: str = Field(
        description="故事钩子，吸引玩家的开场描述"
    )
    character_description: str = Field(
        description="角色描述"
    )
    progression_narrative: str = Field(
        description="进度叙事，随着游戏进行的故事发展"
    )
    feedback_messages: dict[str, str] = Field(
        description="反馈消息字典，如 {'correct': '太棒了！', 'wrong': '再想想...', 'win': '恭喜通关！'}"
    )


class UnifiedDesign(BaseModel):
    """整合后的统一设计"""

    title: str = Field(
        description="游戏标题"
    )
    description: str = Field(
        description="游戏描述"
    )
    tags: list[str] = Field(
        description="游戏标签列表"
    )
    vision: VisionSpec = Field(
        description="视觉规范"
    )
    gameplay: GameplaySpec = Field(
        description="游戏机制规范"
    )
    narrative: NarrativeSpec = Field(
        description="叙事内容规范"
    )
    template_hint: str = Field(
        description="推荐使用的模板类型（仅作参考，code_generator 实际调用 LLM 生成）"
    )
    complexity: str = Field(
        description="复杂度：simple / medium / complex（决定生成代码的规模和深度）"
    )


class IssueKind(str):
    """验证问题分类"""
    FIXABLE = "fixable"       # 可修复：引用路径错、manifest 格式错，可自动修复后重验证
    UNFIXABLE = "unfixable"   # 不可修复：LLM 输出崩溃、JSON 格式严重错误，需重新生成
    CRITICAL = "critical"     # 严重：安全问题，直接失败


class ValidationResult(BaseModel):
    """验证结果"""

    passed: bool = Field(
        description="验证是否通过"
    )
    issues: list[str] = Field(
        default_factory=list,
        description="发现的问题列表"
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="警告信息列表"
    )
    issue_kinds: list[str] = Field(
        default_factory=list,
        description="每个 issue 对应的分类：fixable / unfixable / critical"
    )


class UploadResult(BaseModel):
    """上传结果"""

    manifest_url: str = Field(
        description="Manifest 文件 URL"
    )
    entry_url: str = Field(
        description="游戏入口文件 URL"
    )
    artifact_base_url: str = Field(
        description="产物基础 URL"
    )
    file_count: int = Field(
        description="上传的文件数量"
    )


class AgentLog(BaseModel):
    """执行日志"""

    agent: str = Field(
        description="Agent 名称"
    )
    step: str = Field(
        description="执行步骤"
    )
    message: str = Field(
        description="日志消息"
    )
    timestamp: str | None = Field(
        default=None,
        description="时间戳"
    )


class SupervisorResult(BaseModel):
    """Supervisor Agent 决策结果"""

    status: Literal["approved_simple", "approved_complex", "rejected"] = Field(
        description="决策状态：approved=有效游戏请求，rejected=无效输入"
    )
    complexity: str = Field(
        description="复杂度：simple / medium / complex（所有 approved 请求都会走 LLM 生成路径，complexity 传给 code_generator 控制生成规模）"
    )
    reason: str = Field(
        description="判断理由"
    )
    feedback_message: str = Field(
        description="拒绝时给用户的友好引导（仅 rejected 时有效）"
    )
