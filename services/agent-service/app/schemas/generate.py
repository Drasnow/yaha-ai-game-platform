from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class GenerationAsset(BaseModel):
    asset_id: str = Field(min_length=1)
    url: HttpUrl
    mime_type: str = Field(min_length=1)


class GenerateRequest(BaseModel):
    task_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    prompt: str = Field(min_length=1, max_length=2000)
    assets: list[GenerationAsset] = Field(default_factory=list)
    # 不再由用户选择 generation_mode，由 Supervisor Agent 自动判断


class ArtifactResponse(BaseModel):
    manifest_url: str
    entry_url: str
    artifact_base_url: str


class AgentLogResponse(BaseModel):
    agent_name: str
    step: str
    message: str


class GenerateResponse(BaseModel):
    status: Literal["succeeded", "failed", "rejected"]
    title: str
    description: str
    tags: list[str]
    artifact: ArtifactResponse | None  # rejected 时为 None
    logs: list[AgentLogResponse]
    supervisor_feedback: str | None  # rejected 时返回给用户的引导信息
