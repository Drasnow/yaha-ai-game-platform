"""LLM 异常定义。"""

from typing import Any


class LLMError(Exception):
    """LLM 调用基础异常。"""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class LLMProviderError(LLMError):
    """Provider 级别错误（API 不可用、超时等）。"""

    pass


class LLMTimeoutError(LLMProviderError):
    """请求超时。"""

    pass


class LLMRateLimitError(LLMProviderError):
    """请求频率超限。"""

    pass


class LLMAuthenticationError(LLMProviderError):
    """认证失败（API Key 无效等）。"""

    pass


class LLMValidationError(LLMError):
    """响应格式验证失败。"""

    pass


class LLMResponseError(LLMError):
    """LLM 返回了错误响应。"""

    def __init__(self, message: str, error_code: str | None = None, **kwargs):
        super().__init__(message, kwargs)
        self.error_code = error_code
