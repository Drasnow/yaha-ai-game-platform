from dataclasses import dataclass

from fastapi.testclient import TestClient

from app.agent.orchestrator import AgentOrchestrator
from app.main import app
from app.schemas.generate import GenerateRequest


@dataclass(frozen=True)
class FakeUploadResult:
    manifest_url: str = "http://localhost:9000/yaha-games/games/generated/task_test/v1/manifest.json"
    entry_url: str = "http://localhost:9000/yaha-games/games/generated/task_test/v1/index.html"
    artifact_base_url: str = "http://localhost:9000/yaha-games/games/generated/task_test/v1/"


class FakeStorage:
    def __init__(self):
        self.uploaded_files = None

    def upload_game_files(self, task_id: str, files: dict[str, str]) -> FakeUploadResult:
        self.uploaded_files = files
        assert task_id == "task_test"
        assert {"index.html", "style.css", "game.js", "manifest.json"}.issubset(files)
        return FakeUploadResult()


def _generate(prompt: str):
    storage = FakeStorage()
    result = AgentOrchestrator(storage=storage).generate(
        GenerateRequest(
            task_id="task_test",
            user_id="user_test",
            prompt=prompt,
            assets=[],
        )
    )
    return result, storage


def test_orchestrator_generates_quiz_game_response():
    result, storage = _generate("做一个关于太空知识的问答互动游戏，玩家选择答案得分")

    assert result.status == "succeeded"
    assert result.artifact.manifest_url.endswith("manifest.json")
    assert "quiz" in result.tags
    assert [log.agent_name for log in result.logs] == [
        "RequirementAgent",
        "GameDesignAgent",
        "CodeGenerationAgent",
        "BuildValidateAgent",
        "ArtifactAgent",
    ]
    assert storage.uploaded_files is not None


def test_orchestrator_supports_click_challenge_template():
    result, storage = _generate("做一个点击星星得分的小游戏，30 秒内尽量多得分")

    assert "click" in result.tags
    assert "点击挑战" in result.title
    assert '"template": "click_challenge"' in storage.uploaded_files["manifest.json"]


def test_orchestrator_supports_avoid_obstacle_template():
    result, storage = _generate("做一个飞船躲避障碍的生存跑酷游戏")

    assert "avoid" in result.tags
    assert "躲避挑战" in result.title
    assert '"template": "avoid_obstacle"' in storage.uploaded_files["manifest.json"]


def test_generate_request_validation():
    client = TestClient(app)
    response = client.post("/generate", json={"task_id": "", "user_id": "u", "prompt": "", "assets": []})
    assert response.status_code == 422
