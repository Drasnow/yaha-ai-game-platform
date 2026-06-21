import json
import re
from pathlib import PurePosixPath

from app.agent.state import GeneratedFiles


BLOCKED_PATTERNS = [
    (re.compile(r"<script\s+[^>]*src=[\"'](?:https?:)?//", re.IGNORECASE), "禁止加载外部脚本"),
    (re.compile(r"\beval\s*\(", re.IGNORECASE), "禁止使用 eval()"),
    # Function 构造器
    # JavaScript 大小写敏感：`function` (小写 f) = 函数声明关键字；`Function` (大写 F) = 构造器
    # `\bFunction\s*\(` 精确拦截 "Function" + 左括号，中间允许空格（`Function ()` 也属于危险调用）
    # 放行: `function foo(){}`（小写 f）、`var $ = function(id){}`（小写 f）、`canvas.getContext`（无 Function 词）
    (re.compile(r"\bFunction\s*\(", 0), "禁止使用 Function() 构造器"),
    # localStorage / sessionStorage
    # 安全原则：只允许静态字符串 key，禁止变量 key（防止 prompt injection 通过 key 注入）
    # 放行: `localStorage.setItem('score', v)` / `localStorage.getItem('best')` / `localStorage.clear()`
    # 拦截: `localStorage[keyVar]` / `localStorage.setItem(keyVar, v)` / `localStorage.getItem(variable)`
    # 原理: `\bStorage\s*\[(?!\s*['\"])` 拦截 Storage[ 后第一个非空白字符不是引号的情况
    (
        re.compile(
            r"\b(?:local|session)Storage\s*\[(?!\s*['\"])",
            re.IGNORECASE,
        ),
        "禁止使用动态 key 访问存储",
    ),
    (
        re.compile(
            r"\b(?:local|session)Storage"
            r"\.(?:getItem|setItem|removeItem)"
            r"\s*\(\s*(?!\s*['\"])",
            re.IGNORECASE,
        ),
        "禁止使用变量作为存储 key",
    ),
    (re.compile(r"document\.cookie", re.IGNORECASE), "禁止访问 document.cookie"),
    (re.compile(r"\bfetch\s*\(", re.IGNORECASE), "禁止发起非白名单 fetch 请求"),
    (re.compile(r"\bXMLHttpRequest\b", re.IGNORECASE), "禁止使用 XMLHttpRequest"),
]
REQUIRED_FILES = {"index.html", "style.css", "game.js", "manifest.json"}
ALLOWED_FILES = REQUIRED_FILES


class ArtifactValidationError(ValueError):
    pass


# 别名，用于兼容导入
ValidationError = ArtifactValidationError


def validate_generated_files(generated: GeneratedFiles) -> None:
    missing_files = REQUIRED_FILES.difference(generated.files)
    if missing_files:
        raise ArtifactValidationError(f"缺少必要产物文件：{', '.join(sorted(missing_files))}")

    extra_files = set(generated.files).difference(ALLOWED_FILES)
    if extra_files:
        raise ArtifactValidationError(
            f"MVP 只允许静态 HTML/CSS/JS/manifest 产物文件：{', '.join(sorted(extra_files))}"
        )

    try:
        manifest = json.loads(generated.files["manifest.json"])
    except json.JSONDecodeError as exc:
        raise ArtifactValidationError("manifest.json 不是合法 JSON") from exc

    if manifest.get("entry") != "index.html":
        raise ArtifactValidationError("manifest entry 必须是 index.html")

    manifest_files = manifest.get("files")
    if not isinstance(manifest_files, list) or not all(isinstance(file_name, str) for file_name in manifest_files):
        raise ArtifactValidationError("manifest files 必须是文件名字符串数组")

    files = set(manifest_files)
    if not {"index.html", "style.css", "game.js"}.issubset(files):
        raise ArtifactValidationError("manifest files 必须包含 index.html/style.css/game.js")

    disallowed_manifest_files = {file_name for file_name in files if file_name not in ALLOWED_FILES}
    if disallowed_manifest_files:
        raise ArtifactValidationError(
            f"manifest files 只允许 index.html/style.css/game.js/manifest.json：{', '.join(sorted(disallowed_manifest_files))}"
        )

    for file_name in generated.files:
        _validate_safe_relative_file_name(file_name)
    for file_name in files:
        _validate_safe_relative_file_name(file_name)

    for file_name, content in generated.files.items():
        if file_name.endswith((".html", ".js")):
            for pattern, message in BLOCKED_PATTERNS:
                if pattern.search(content):
                    raise ArtifactValidationError(f"{file_name} 安全校验失败：{message}")


def _validate_safe_relative_file_name(file_name: str) -> None:
    path = PurePosixPath(file_name)
    if path.is_absolute() or ".." in path.parts or str(path) != file_name or not file_name.strip():
        raise ArtifactValidationError(f"非法产物文件路径：{file_name}")
