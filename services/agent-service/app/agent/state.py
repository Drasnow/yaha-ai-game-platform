from dataclasses import dataclass, field

from app.schemas.generate import AgentLogResponse, GenerateRequest


@dataclass
class GameDesign:
    template: str
    title: str
    description: str
    tags: list[str]
    primary_color: str
    accent_color: str
    objective: str


@dataclass
class GeneratedFiles:
    files: dict[str, str]
    manifest: dict[str, object]


@dataclass
class AgentState:
    request: GenerateRequest
    logs: list[AgentLogResponse] = field(default_factory=list)
    selected_template: str | None = None
    requirement_summary: str = ""
    design: GameDesign | None = None
    generated: GeneratedFiles | None = None

    def log(self, agent_name: str, step: str, message: str) -> None:
        self.logs.append(AgentLogResponse(agent_name=agent_name, step=step, message=message))
