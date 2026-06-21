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


class ArtifactResponse(BaseModel):
    manifest_url: str
    entry_url: str
    artifact_base_url: str


class AgentLogResponse(BaseModel):
    agent_name: str
    step: str
    message: str


class GenerateResponse(BaseModel):
    status: Literal["succeeded", "failed"]
    title: str
    description: str
    tags: list[str]
    artifact: ArtifactResponse
    logs: list[AgentLogResponse]
