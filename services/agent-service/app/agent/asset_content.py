"""素材内容读取工具。

根据 mime_type 从 URL 获取文件内容并转为文本：
- text/plain / text/markdown → 直接 decode UTF-8
- .docx（application/vnd.openxmlformats-officedocument.wordprocessingml.document）→ python-docx
"""

import asyncio
import logging
import zipfile
import io
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel

from app.schemas.generate import GenerationAsset

logger = logging.getLogger(__name__)

MAX_CHARS_PER_FILE = 2000
FETCH_TIMEOUT_SECONDS = 10.0

# ========================================
# URL 安全验证
# ========================================

_ALLOWED_DOMAINS: set[str] | None = None  # None = 未初始化


def _get_allowed_domains() -> set[str] | None:
    """惰性加载白名单域名字符串，缓存结果。"""
    global _ALLOWED_DOMAINS
    if _ALLOWED_DOMAINS is None:
        from app.core.config import get_settings
        raw = get_settings().allowed_asset_domains
        _ALLOWED_DOMAINS = {d.strip().lower() for d in raw.split(",") if d.strip()} or None
    return _ALLOWED_DOMAINS


def _check_url_allowed(url: str) -> str | None:
    """检查 URL 域名是否在白名单中。

    Args:
        url: 待检查的 URL

    Returns:
        None 表示允许；str 表示拒绝原因
    """
    allowed = _get_allowed_domains()
    if not allowed:
        return None  # 未配置白名单，放行

    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        # 去除可选的端口号
        if ":" in host:
            host = host.rsplit(":", 1)[0]
        if host in allowed:
            return None
        return f"域名 '{host}' 不在允许列表中（允许：{', '.join(sorted(allowed))}）"
    except Exception as exc:
        return f"URL 解析失败: {exc}"


# ========================================
# 模型
# ========================================


class AssetContent(BaseModel):
    asset_id: str
    content: str
    truncated: bool = False
    error: str | None = None


def _read_docx(content: bytes) -> str:
    """从 DOCX 二进制内容中提取纯文本。

    DOCX 本质上是 ZIP 文件，内部 word/document.xml 包含所有文本。
    """
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            with zf.open("word/document.xml") as xml_file:
                import re
                xml_text = xml_file.read().decode("utf-8", errors="replace")
                # 去除 XML 标签，保留文本节点
                text = re.sub(r"<[^>]+>", "", xml_text)
                text = re.sub(r"\s+", " ", text).strip()
                return text
    except Exception as exc:
        logger.warning(f"DOCX 解析失败: {exc}")
        raise


async def fetch_asset_content(asset: GenerationAsset) -> AssetContent:
    """从 URL 获取单个素材文件内容并转为文本。

    Args:
        asset: 素材信息（URL + mime_type）

    Returns:
        AssetContent，包含提取的文本内容
    """
    try:
        # 安全检查：域名白名单
        deny_reason = _check_url_allowed(str(asset.url))
        if deny_reason:
            logger.warning(f"素材 URL 被拦截: {asset.url} — {deny_reason}")
            return AssetContent(
                asset_id=asset.asset_id,
                content="",
                error=f"素材 URL 不被允许: {deny_reason}",
            )

        async with httpx.AsyncClient(timeout=FETCH_TIMEOUT_SECONDS) as client:
            response = await client.get(str(asset.url))
            response.raise_for_status()
            raw = response.content

        mime = asset.mime_type.lower()

        if mime == "text/plain":
            text = raw.decode("utf-8", errors="replace")
        elif mime == "text/markdown":
            text = raw.decode("utf-8", errors="replace")
        elif mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text = _read_docx(raw)
        else:
            return AssetContent(
                asset_id=asset.asset_id,
                content="",
                error=f"不支持的文件类型: {mime}",
            )

        truncated = len(text) > MAX_CHARS_PER_FILE
        if truncated:
            text = text[:MAX_CHARS_PER_FILE]

        return AssetContent(
            asset_id=asset.asset_id,
            content=text,
            truncated=truncated,
        )

    except httpx.TimeoutException:
        logger.warning(f"获取素材超时: {asset.url}")
        return AssetContent(
            asset_id=asset.asset_id,
            content="",
            error="素材获取超时",
        )
    except httpx.HTTPStatusError as exc:
        logger.warning(f"获取素材 HTTP 错误 {exc.response.status_code}: {asset.url}")
        return AssetContent(
            asset_id=asset.asset_id,
            content="",
            error=f"素材下载失败 ({exc.response.status_code})",
        )
    except Exception as exc:
        logger.warning(f"素材内容读取失败: {exc}")
        return AssetContent(
            asset_id=asset.asset_id,
            content="",
            error=str(exc),
        )


async def fetch_all_asset_contents(
    assets: list[GenerationAsset],
    max_chars: int = MAX_CHARS_PER_FILE,
) -> list[AssetContent]:
    """并发获取所有素材文本内容。

    Args:
        assets: 素材列表
        max_chars: 单文件最大字符数（兼容参数，实际使用 MAX_CHARS_PER_FILE）

    Returns:
        AssetContent 列表，包含每个素材的文本内容
    """
    if not assets:
        return []

    results = await asyncio.gather(
        *(fetch_asset_content(asset) for asset in assets),
        return_exceptions=True,
    )

    contents = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            contents.append(AssetContent(
                asset_id=assets[i].asset_id,
                content="",
                error=str(result),
            ))
        else:
            contents.append(result)

    return contents


def build_assets_context(contents: list[AssetContent]) -> str:
    """将素材内容列表格式化为可供 LLM 消费的上下文字符串。

    Args:
        contents: fetch_all_asset_contents 返回的结果

    Returns:
        格式化的上下文字符串，如果无有效内容则返回空字符串
    """
    valid = [c for c in contents if c.content and not c.error]
    if not valid:
        return ""

    lines = ["\n\n## 参考素材\n"]
    for c in valid:
        suffix = "（内容已截断）" if c.truncated else ""
        lines.append(f"--- 素材 {c.asset_id} {suffix} ---\n{c.content}\n")

    return "".join(lines)
