from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.llm.client import LLMClient
from app.llm.providers import create_provider


class Settings(BaseSettings):
    # MinIO 配置
    minio_endpoint: str = "http://localhost:9000"
    minio_public_endpoint: str = "http://localhost:9000"
    minio_access_key: str = "yaha_minio"
    minio_secret_key: str = "yaha_minio_password"
    minio_bucket: str = "yaha-games"
    minio_region: str = "us-east-1"

    # Agent 行为控制
    mock_agent_mode: bool = False
    enable_llm_fallback: bool = True

    # 素材 URL 安全白名单（逗号分隔，匹配请求的目标域名）
    # 空字符串 = 禁止所有外部素材请求；留空则不限制（仅警告）
    # 示例: "cdn.yourdomain.com,assets.yourdomain.com"
    allowed_asset_domains: str = ""

    # LangSmith 可观测性
    langsmith_api_key: str = Field(default="", validation_alias="LANGSMITH_API_KEY")
    langsmith_project: str = Field(default="YAHA", validation_alias="LANGSMITH_PROJECT")
    langsmith_tracing: bool = Field(default=True, validation_alias="LANGSMITH_TRACING")

    # LLM Provider 配置
    llm_provider: str = "openai-compatible"  # openai-compatible | anthropic | siliconflow | ollama | lmstudio | fighting
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-5.5"
    llm_timeout: int = 300
    llm_max_retries: int = 3
    # Model behavior settings (provider-dependent)
    llm_reasoning_effort: str = "medium"  # low | medium | high
    llm_tool_output_token_limit: int | None = None
    llm_personality: str = "pragmatic"  # pragmatic | creative | precise

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def create_llm_client_from_settings(settings: Settings | None = None) -> LLMClient:
    """从设置创建 LLM Client（包含所有模型参数）。"""
    if settings is None:
        settings = get_settings()

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
    return LLMClient(
        provider=provider,
        max_retries=settings.llm_max_retries,
        timeout=settings.llm_timeout,
    )
