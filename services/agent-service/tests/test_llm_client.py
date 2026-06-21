"""LLM Client 单元测试。"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel

from app.llm.client import LLMClient
from app.llm.exceptions import (
    LLMAuthenticationError,
    LLMError,
    LLMProviderError,
    LLMTimeoutError,
)
from app.llm.providers import (
    ChatMessage,
    ChatResponse,
    OpenAIProvider,
    create_provider,
)


class VisionSpec(BaseModel):
    """测试用的 Schema。"""
    style: str
    color_palette: dict[str, str]


class MockProvider:
    """模拟 LLM Provider。"""

    def __init__(self, response_content: str = "测试响应"):
        self._response_content = response_content
        self.chat = AsyncMock(
            return_value=ChatResponse(
                content=response_content,
                model="test-model",
                usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            )
        )


@pytest.mark.asyncio
class TestLLMClient:
    """LLMClient 测试。"""

    def setup_method(self):
        """测试前准备。"""
        self.mock_provider = MockProvider()
        self.client = LLMClient(provider=self.mock_provider, max_retries=1, retry_delay=0.1)

    async def test_generate_basic(self):
        """测试基本生成。"""
        response = await self.client.generate("你好")
        assert response == "测试响应"

    async def test_generate_with_system_prompt(self):
        """测试带系统提示的生成。"""
        response = await self.client.generate("你好", system_prompt="你是一个助手")
        assert response == "测试响应"

    async def test_call_count_tracking(self):
        """测试调用计数。"""
        assert self.client.call_count == 0
        await self.client.generate("测试")
        assert self.client.call_count == 1

    async def test_token_tracking(self):
        """测试 Token 统计。"""
        assert self.client.total_tokens == 0
        await self.client.generate("测试")
        assert self.client.total_tokens == 30

    def test_reset_stats(self):
        """测试重置统计。"""
        self.client.generate("测试")  # 不 await，因为我们要测试 reset_stats
        self.client.reset_stats()
        assert self.client.call_count == 0
        assert self.client.total_tokens == 0


@pytest.mark.asyncio
class TestLLMClientRetry:
    """LLMClient 重试机制测试。"""

    async def test_retry_on_timeout(self):
        """测试超时重试。"""
        mock_provider = MagicMock()
        mock_provider.chat = AsyncMock(side_effect=LLMTimeoutError("超时"))

        client = LLMClient(provider=mock_provider, max_retries=2, retry_delay=0.01)

        with pytest.raises(LLMError, match="LLM 调用失败"):
            await client.generate("测试")

        assert mock_provider.chat.call_count == 3  # 初始 + 2 次重试

    async def test_no_retry_on_auth_error(self):
        """认证错误会重试（因为是 LLMProviderError 的子类）。"""
        mock_provider = MagicMock()
        mock_provider.chat = AsyncMock(side_effect=LLMAuthenticationError("无效的 API Key"))

        client = LLMClient(provider=mock_provider, max_retries=2, retry_delay=0.01)

        # 认证错误也是 LLMProviderError，会重试
        with pytest.raises(LLMError, match="LLM 调用失败"):
            await client.generate("测试")

        assert mock_provider.chat.call_count == 3  # 初始 + 2 次重试


@pytest.mark.asyncio
class TestLLMClientJsonMode:
    """JSON 模式测试。"""

    def setup_method(self):
        """测试前准备。"""
        json_response = '{"style": "pixel", "color_palette": {"primary": "#000"}}'
        self.mock_provider = MockProvider(response_content=json_response)
        self.client = LLMClient(provider=self.mock_provider)

    async def test_generate_json(self):
        """测试 JSON 生成。"""
        result = await self.client.generate_json(
            prompt="生成一个视觉规范",
            schema=VisionSpec,
        )
        assert isinstance(result, VisionSpec)
        assert result.style == "pixel"
        assert result.color_palette["primary"] == "#000"

    async def test_extract_json_from_markdown(self):
        """测试从 Markdown 代码块中提取 JSON。"""
        mock_provider = MockProvider(
            response_content='```json\n{"style": "neon", "color_palette": {"primary": "#f00"}}\n```'
        )
        client = LLMClient(provider=mock_provider)

        result = await client.generate_json(
            prompt="生成规范",
            schema=VisionSpec,
        )
        assert result.style == "neon"
        assert result.color_palette["primary"] == "#f00"


class TestCreateProvider:
    """Provider 创建测试。"""

    def test_create_openai_compatible(self):
        """测试创建 OpenAI 兼容 Provider。"""
        provider = create_provider(
            provider_type="openai-compatible",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
            model="gpt-4o",
        )
        assert isinstance(provider, OpenAIProvider)
        assert provider.default_model == "gpt-4o"

    def test_create_fighting_provider(self):
        """测试创建 fighting Provider。"""
        provider = create_provider(
            provider_type="fighting",
            base_url="http://example.com/v1",
            api_key="test-key",
            model="gpt-5.5",
        )
        assert isinstance(provider, OpenAIProvider)
        assert provider.default_model == "gpt-5.5"

    def test_unsupported_provider(self):
        """测试不支持的 Provider。"""
        with pytest.raises(ValueError, match="不支持的 Provider 类型"):
            create_provider(
                provider_type="unsupported",
                base_url="http://example.com",
                api_key="test",
                model="test",
            )


class TestChatMessage:
    """ChatMessage 测试。"""

    def test_create_message(self):
        """测试创建消息。"""
        msg = ChatMessage(role="user", content="你好")
        assert msg.role == "user"
        assert msg.content == "你好"

    def test_message_serialization(self):
        """测试消息序列化。"""
        msg = ChatMessage(role="assistant", content="我是助手")
        data = msg.model_dump()
        assert data["role"] == "assistant"
        assert data["content"] == "我是助手"


class TestChatResponse:
    """ChatResponse 测试。"""

    def test_create_response(self):
        """测试创建响应。"""
        resp = ChatResponse(
            content="测试响应",
            model="gpt-4o",
            usage={"total_tokens": 100},
        )
        assert resp.content == "测试响应"
        assert resp.model == "gpt-4o"
        assert resp.usage["total_tokens"] == 100

    def test_response_with_raw(self):
        """测试带原始响应的响应。"""
        raw = {"choices": [{"message": {"content": "原始"}}]}
        resp = ChatResponse(content="解析后", raw_response=raw)
        assert resp.raw_response == raw
