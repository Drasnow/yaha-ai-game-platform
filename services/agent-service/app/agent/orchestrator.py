import re
from typing import Protocol

from app.agent.builder import TEMPLATE_RENDERERS
from app.agent.state import AgentState, GameDesign
from app.agent.storage import ArtifactStorage, UploadResult
from app.agent.validator import validate_generated_files
from app.core.config import get_settings
from app.schemas.generate import ArtifactResponse, GenerateRequest, GenerateResponse


TEMPLATE_KEYWORDS = {
    "quiz_game": ["问答", "答题", "quiz", "知识", "选择题", "题库", "闯关"],
    "avoid_obstacle": ["躲避", "闪避", "障碍", "avoid", "dodge", "飞船", "跑酷", "生存"],
    "click_challenge": ["点击", "得分", "星星", "click", "挑战", "收集"],
}
DEFAULT_TEMPLATE = "click_challenge"


class AgentStep(Protocol):
    agent_name: str

    def run(self, state: AgentState) -> None:
        ...


class RequirementAgent:
    agent_name = "RequirementAgent"

    def run(self, state: AgentState) -> None:
        prompt = state.request.prompt.lower()
        selected_template = DEFAULT_TEMPLATE
        matched_keyword = "默认点击玩法"

        for candidate, keywords in TEMPLATE_KEYWORDS.items():
            match = next((keyword for keyword in keywords if keyword.lower() in prompt), None)
            if match:
                selected_template = candidate
                matched_keyword = match
                break

        state.selected_template = selected_template
        state.requirement_summary = f"模板={selected_template}; 关键词={matched_keyword}; 素材数={len(state.request.assets)}"
        state.log(self.agent_name, "parse_prompt", f"已解析创意并选择模板：{selected_template}（命中：{matched_keyword}）。")


class GameDesignAgent:
    agent_name = "GameDesignAgent"

    def run(self, state: AgentState) -> None:
        if state.selected_template is None:
            raise RuntimeError("RequirementAgent 未生成模板选择")

        theme = _extract_theme(state.request.prompt)
        design_map = {
            "click_challenge": GameDesign(
                template="click_challenge",
                title=f"{theme}点击挑战",
                description=f"根据创意生成的 30 秒点击得分小游戏：{state.request.prompt}",
                tags=["click", "casual", "generated", "mvp"],
                primary_color="#312e81",
                accent_color="#facc15",
                objective="30 秒内点击目标获得高分",
            ),
            "avoid_obstacle": GameDesign(
                template="avoid_obstacle",
                title=f"{theme}躲避挑战",
                description=f"根据创意生成的方向键躲避障碍小游戏：{state.request.prompt}",
                tags=["avoid", "action", "generated", "mvp"],
                primary_color="#7f1d1d",
                accent_color="#fb7185",
                objective="操控角色躲避障碍，坚持更久",
            ),
            "quiz_game": GameDesign(
                template="quiz_game",
                title=f"{theme}问答闯关",
                description=f"根据创意生成的轻量问答互动游戏：{state.request.prompt}",
                tags=["quiz", "knowledge", "generated", "mvp"],
                primary_color="#1d4ed8",
                accent_color="#93c5fd",
                objective="连续回答问题并获得分数",
            ),
        }
        state.design = design_map[state.selected_template]
        state.log(self.agent_name, "design_rules", f"已生成玩法目标：{state.design.objective}。")


class CodeGenerationAgent:
    agent_name = "CodeGenerationAgent"

    def run(self, state: AgentState) -> None:
        if state.design is None:
            raise RuntimeError("GameDesignAgent 未生成设计")
        state.generated = TEMPLATE_RENDERERS[state.design.template](state.design, state.request.prompt, state.request.assets)
        state.log(self.agent_name, "render_files", "已生成 index.html/style.css/game.js/manifest.json。")


class BuildValidateAgent:
    agent_name = "BuildValidateAgent"

    def run(self, state: AgentState) -> None:
        if state.generated is None:
            raise RuntimeError("CodeGenerationAgent 未生成产物")
        validate_generated_files(state.generated)
        state.log(self.agent_name, "validate", "产物结构、manifest 与安全规则校验通过。")


class ArtifactAgent:
    agent_name = "ArtifactAgent"

    def __init__(self, storage: ArtifactStorage):
        self.storage = storage
        self.artifact: UploadResult | None = None

    def run(self, state: AgentState) -> None:
        if state.generated is None:
            raise RuntimeError("BuildValidateAgent 未提供可上传产物")
        self.artifact = self.storage.upload_game_files(state.request.task_id, state.generated.files)
        state.log(self.agent_name, "upload", "产物已上传对象存储。")


class AgentOrchestrator:
    def __init__(self, storage: ArtifactStorage | None = None, steps: list[AgentStep] | None = None):
        self.storage = storage or ArtifactStorage(get_settings())
        self.artifact_agent = ArtifactAgent(self.storage)
        self.steps = steps or [
            RequirementAgent(),
            GameDesignAgent(),
            CodeGenerationAgent(),
            BuildValidateAgent(),
            self.artifact_agent,
        ]

    def generate(self, request: GenerateRequest) -> GenerateResponse:
        state = AgentState(request=request)
        for step in self.steps:
            step.run(state)

        if state.design is None:
            raise RuntimeError("Agent design state is missing")
        if self.artifact_agent.artifact is None:
            raise RuntimeError("ArtifactAgent 未返回产物地址")

        artifact = self.artifact_agent.artifact
        return GenerateResponse(
            status="succeeded",
            title=state.design.title,
            description=state.design.description,
            tags=state.design.tags,
            artifact=ArtifactResponse(
                manifest_url=artifact.manifest_url,
                entry_url=artifact.entry_url,
                artifact_base_url=artifact.artifact_base_url,
            ),
            logs=state.logs,
        )


def _extract_theme(prompt: str) -> str:
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
