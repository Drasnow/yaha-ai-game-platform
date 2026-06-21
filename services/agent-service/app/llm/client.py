"""LLM Client 主类。

提供统一的 LLM 调用接口，支持重试、模板回退等功能。
"""

import asyncio
import json
import logging
from typing import Any, Callable, TypeVar

from pydantic import BaseModel

from langsmith.run_helpers import traceable

from app.llm.exceptions import (
    LLMError,
    LLMProviderError,
    LLMTimeoutError,
)
from app.llm.providers import (
    ChatMessage,
    ChatResponse,
    LLMProvider,
    create_provider,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class LLMClient:
    """LLM 统一客户端。"""

    def __init__(
        self,
        provider: LLMProvider,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: int = 300,
    ):
        """
        初始化 LLM Client。

        Args:
            provider: LLM Provider 实例
            max_retries: 最大重试次数
            retry_delay: 初始重试延迟（秒），会指数退避
            timeout: 请求超时时间（秒）
        """
        self.provider = provider
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout

        # 统计信息
        self._call_count = 0
        self._total_tokens = 0
        self._error_count = 0

    @property
    def call_count(self) -> int:
        """LLM 调用次数。"""
        return self._call_count

    @property
    def total_tokens(self) -> int:
        """总 Token 消耗。"""
        return self._total_tokens

    @property
    def error_count(self) -> int:
        """错误次数。"""
        return self._error_count

    def reset_stats(self) -> None:
        """重置统计信息。"""
        self._call_count = 0
        self._total_tokens = 0
        self._error_count = 0

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        json_mode: bool = False,
        **kwargs,
    ) -> str:
        """
        生成文本。

        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            model: 模型名称（可选）
            temperature: 温度参数
            max_tokens: 最大生成 Token 数
            json_mode: 是否返回 JSON 格式
            **kwargs: 其他参数

        Returns:
            生成的文本内容
        """
        messages = []
        if system_prompt:
            messages.append(ChatMessage(role="system", content=system_prompt))
        messages.append(ChatMessage(role="user", content=prompt))

        return await self._chat_with_retry(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode,
            **kwargs,
        )

    async def generate_json(
        self,
        prompt: str,
        schema: type[BaseModel],
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs,
    ) -> BaseModel:
        """
        生成 JSON 格式的结构化数据。

        Args:
            prompt: 用户提示
            schema: Pydantic Schema 类
            system_prompt: 系统提示
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大生成 Token 数
            **kwargs: 其他参数

        Returns:
            解析后的 Pydantic 模型实例
        """
        schema_json = schema.model_json_schema()
        schema_str = json.dumps(schema_json, indent=2, ensure_ascii=False)

        system = system_prompt or ""
        system += f"\n\n请严格按照以下 JSON Schema 生成响应，不要添加任何额外内容：\n{schema_str}"

        result = await self.generate(
            prompt=prompt,
            system_prompt=system,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=True,
            **kwargs,
        )

        try:
            data = json.loads(result)
            return schema.model_validate(data)
        except json.JSONDecodeError as e:
            raise LLMError(f"JSON 解析失败: {e}\n原始响应: {result}") from e

    @traceable(run_type="chat", name="LLM Chat")
    async def _chat_with_retry(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        json_mode: bool = False,
        **kwargs,
    ) -> str:
        """带重试的聊天请求。"""
        last_error: Exception | None = None
        delay = self.retry_delay

        for attempt in range(self.max_retries + 1):
            try:
                response = await self.provider.chat(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )

                self._call_count += 1
                if response.usage:
                    self._total_tokens += response.usage.get("total_tokens", 0)

                content = response.content.strip()

                # 调试日志：打印发送给 LLM 的消息和原始响应
                _log_llm_io(
                    messages=messages,
                    raw_response=response.content,
                    parsed_content=content,
                    model=model,
                    attempt=attempt + 1,
                )

                if json_mode:
                    content = self._extract_json(content)

                return content

            except LLMTimeoutError as e:
                last_error = e
                self._error_count += 1
                logger.warning(f"LLM 请求超时 (尝试 {attempt + 1}/{self.max_retries + 1}): {e}")

            except (LLMProviderError, Exception) as e:
                # LLMProviderError 和其他异常都需要重试
                last_error = e
                self._error_count += 1
                if isinstance(e, LLMProviderError):
                    logger.warning(f"LLM Provider 错误 (尝试 {attempt + 1}/{self.max_retries + 1}): {e}")
                else:
                    logger.error(f"LLM 调用异常 (尝试 {attempt + 1}/{self.max_retries + 1}): {e}")

            if attempt < self.max_retries:
                await asyncio.sleep(delay)
                delay *= 2  # 指数退避

        raise LLMError(f"LLM 调用失败，已重试 {self.max_retries + 1} 次") from last_error

    def _extract_json(self, content: str) -> str:
        """从响应中提取 JSON。"""
        content = content.strip()

        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip().startswith("```") else lines[1:])

        if content.startswith("```json"):
            content = content[7:]

        if content.startswith("```"):
            content = content[3:]

        content = content.strip()

        if content.startswith("```"):
            end_idx = content.find("```", 3)
            if end_idx != -1:
                content = content[:end_idx].strip()

        return content

    async def close(self) -> None:
        """关闭客户端。

        注意：由于底层 HTTP Client 已迁移到全局连接池复用，
        此方法不再关闭连接。应用退出时调用 llm.providers.close_all_clients()。
        """
        pass


def _log_llm_io(
    messages: list[ChatMessage],
    raw_response: str,
    parsed_content: str,
    model: str | None,
    attempt: int,
) -> None:
    """打印 LLM 输入输出。"""
    separator = "=" * 60
    logger.info(f"\n{separator}\n[LLM Request] model={model} attempt={attempt}")
    for i, msg in enumerate(messages):
        role = msg.role.upper()
        content_preview = msg.content[:300] + ("..." if len(msg.content) > 300 else "")
        logger.info(f"  [{i}] {role}: {content_preview}")
    logger.info(f"\n[LLM Raw Response]: {raw_response}")
    if raw_response != parsed_content:
        logger.info(f"[LLM Parsed Response]: {parsed_content}")
    logger.info(f"{separator}\n")


def create_llm_client(
    provider_type: str,
    base_url: str,
    api_key: str,
    model: str,
    max_retries: int = 3,
    timeout: int = 300,
    reasoning_effort: str | None = None,
    tool_output_token_limit: int | None = None,
    personality: str | None = None,
) -> LLMClient:
    """创建 LLM Client。"""
    provider = create_provider(
        provider_type=provider_type,
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout=timeout,
        reasoning_effort=reasoning_effort,
        tool_output_token_limit=tool_output_token_limit,
        personality=personality,
    )
    return LLMClient(
        provider=provider,
        max_retries=max_retries,
        timeout=timeout,
    )
