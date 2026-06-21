from fastapi import FastAPI, HTTPException

from app.agent.orchestrator import AgentOrchestrator
from app.agent.validator import ArtifactValidationError
from app.schemas.generate import GenerateRequest, GenerateResponse

app = FastAPI(title="Yaha Agent Service")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest):
    try:
        return AgentOrchestrator().generate(request)
    except ArtifactValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent 生成失败：{exc}") from exc
