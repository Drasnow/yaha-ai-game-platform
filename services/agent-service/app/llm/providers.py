"""LLM Provider 适配器。

支持多种 LLM Provider 的统一接口。
"""

import asyncio
import json
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

import httpx
from pydantic import BaseModel

from app.llm.exceptions import (
    LLMAuthenticationError,
    LLMProviderError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
    LLMValidationError,
)


# ============================================================
# 全局 HTTP Client 连接池（按 base_url 缓存）
# ============================================================

_http_client_pool: dict[str, httpx.AsyncClient] = {}
_pool_lock = asyncio.Lock()


async def _get_shared_client(base_url: str, headers: dict[str, str], timeout: int) -> httpx.AsyncClient:
    """获取或创建共享的 HTTP Client，复用连接池。

    Args:
        base_url: API 基础 URL
        headers: HTTP 请求头
        timeout: 超时时间（秒）

    Returns:
        共享的 AsyncClient
    """
    if base_url not in _http_client_pool:
        async with _pool_lock:
            if base_url not in _http_client_pool:
                _http_client_pool[base_url] = httpx.AsyncClient(
                    base_url=base_url,
                    headers=headers,
                    timeout=timeout,
                    limits=httpx.Limits(
                        max_connections=20,
                        max_keepalive_connections=10,
                        keepalive_expiry=30.0,
                    ),
                )
    return _http_client_pool[base_url]


async def close_all_clients() -> None:
    """关闭所有池化的 HTTP Client，释放连接资源。"""
    async with _pool_lock:
        for client in _http_client_pool.values():
            await client.aclose()
        _http_client_pool.clear()


# ============================================================
# 数据模型
# ============================================================

class ChatMessage(BaseModel):
    """聊天消息。"""

    role: str
    content: str


class ChatResponse(BaseModel):
    """聊天响应。"""

    content: str
    model: str | None = None
    usage: dict[str, Any] | None = None
    raw_response: dict[str, Any] | None = None


# ============================================================
# Provider 抽象基类
# ============================================================

class LLMProvider(ABC):
    """LLM Provider 抽象基类。"""

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs,
    ) -> ChatResponse:
        """发送聊天请求。"""
        ...


# ============================================================
# OpenAI 兼容 Provider
# ============================================================

class OpenAIProvider(LLMProvider):
    """OpenAI 兼容格式的 Provider（包含 OpenAI、SiliconFlow、Ollama、LM Studio、Fighting 等）。

    使用全局连接池复用 HTTP Client。
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = 300,
        default_model: str = "gpt-4o",
        reasoning_effort: str | None = None,
        tool_output_token_limit: int | None = None,
        personality: str | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.default_model = default_model
        self.reasoning_effort = reasoning_effort
        self.tool_output_token_limit = tool_output_token_limit
        self.personality = personality

    def _build_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs,
    ) -> ChatResponse:
        client = await _get_shared_client(
            self.base_url, self._build_headers(), self.timeout
        )
        model = model or self.default_model

        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        if self.reasoning_effort:
            payload["reasoning_effort"] = self.reasoning_effort
        if self.tool_output_token_limit:
            payload["tool_output_token_limit"] = self.tool_output_token_limit
        if self.personality:
            payload["personality"] = self.personality

        payload.update(kwargs)

        try:
            response = await client.post("/chat/completions", json=payload)
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(f"请求超时: {e}") from e
        except httpx.ConnectError as e:
            raise LLMProviderError(f"连接失败: {e}") from e
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise LLMAuthenticationError("API Key 无效或已过期") from e
            if e.response.status_code == 429:
                raise LLMRateLimitError("请求频率超限，请稍后重试") from e
            raise LLMProviderError(f"HTTP 错误: {e.response.status_code} - {e.response.text}") from e

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", response.text)
            except Exception:
                error_msg = response.text
            raise LLMResponseError(f"API 返回错误: {error_msg}")

        data = response.json()

        if "error" in data:
            error_info = data["error"]
            raise LLMResponseError(
                error_info.get("message", "Unknown error"),
                error_code=error_info.get("type"),
            )

        try:
            choice = data["choices"][0]
            content = choice["message"]["content"]

            return ChatResponse(
                content=content,
                model=data.get("model"),
                usage=data.get("usage"),
                raw_response=data,
            )
        except (KeyError, IndexError) as e:
            raise LLMValidationError(f"响应格式不符合预期: {data}") from e


# ============================================================
# Anthropic Provider
# ============================================================

class AnthropicProvider(LLMProvider):
    """Anthropic Claude Provider。

    使用全局连接池复用 HTTP Client。
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.anthropic.com",
        timeout: int = 300,
        default_model: str = "claude-3-5-sonnet-20240620",
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.default_model = default_model

    def _build_headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
            "anthropic-dangerous-direct-browser-access": "true",
        }

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> ChatResponse:
        client = await _get_shared_client(
            self.base_url, self._build_headers(), self.timeout
        )
        model = model or self.default_model

        anthropic_messages = []
        for m in messages:
            if m.role == "system":
                continue
            anthropic_messages.append({"role": m.role, "content": m.content})

        payload: dict[str, Any] = {
            "model": model,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        payload.update(kwargs)

        try:
            response = await client.post("/v1/messages", json=payload)
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(f"请求超时: {e}") from e
        except httpx.ConnectError as e:
            raise LLMProviderError(f"连接失败: {e}") from e
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise LLMAuthenticationError("API Key 无效或已过期") from e
            if e.response.status_code == 429:
                raise LLMRateLimitError("请求频率超限，请稍后重试") from e
            raise LLMProviderError(f"HTTP 错误: {e.response.status_code} - {e.response.text}") from e

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", response.text)
            except Exception:
                error_msg = response.text
            raise LLMResponseError(f"API 返回错误: {error_msg}")

        data = response.json()

        if "error" in data:
            error_info = data["error"]
            raise LLMResponseError(
                error_info.get("message", "Unknown error"),
                error_code=error_info.get("type"),
            )

        try:
            content = data["content"][0]["text"]

            return ChatResponse(
                content=content,
                model=data.get("model"),
                usage={
                    "input_tokens": data.get("usage", {}).get("input_tokens", 0),
                    "output_tokens": data.get("usage", {}).get("output_tokens", 0),
                },
                raw_response=data,
            )
        except (KeyError, IndexError) as e:
            raise LLMValidationError(f"响应格式不符合预期: {data}") from e


# ============================================================
# Provider 工厂函数
# ============================================================

def create_provider(
    provider_type: str,
    base_url: str,
    api_key: str,
    model: str,
    timeout: int = 300,
    reasoning_effort: str | None = None,
    tool_output_token_limit: int | None = None,
    personality: str | None = None,
) -> LLMProvider:
    """根据类型创建 LLM Provider。"""
    provider_type = provider_type.lower()

    if provider_type in ("openai-compatible", "openai", "siliconflow", "ollama", "lmstudio", "lm_studio", "fighting", "custom"):
        return OpenAIProvider(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            default_model=model,
            reasoning_effort=reasoning_effort,
            tool_output_token_limit=tool_output_token_limit,
            personality=personality,
        )
    elif provider_type in ("anthropic", "claude"):
        return AnthropicProvider(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            default_model=model,
        )
    else:
        raise ValueError(f"不支持的 Provider 类型: {provider_type}")
