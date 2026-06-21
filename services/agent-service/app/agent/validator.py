import json
import re
from pathlib import PurePosixPath

from app.agent.state import GeneratedFiles


BLOCKED_PATTERNS = [
    (re.compile(r"<script\s+[^>]*src=[\"'](?:https?:)?//", re.IGNORECASE), "禁止加载外部脚本"),
    (re.compile(r"\beval\s*\(", re.IGNORECASE), "禁止使用 eval()"),
    (re.compile(r"\b(?:new\s+)?Function\s*\(", re.IGNORECASE), "禁止使用 Function()"),
    (re.compile(r"\blocalStorage\b", re.IGNORECASE), "禁止读写 localStorage"),
    (re.compile(r"\bsessionStorage\b", re.IGNORECASE), "禁止读写 sessionStorage"),
    (re.compile(r"document\.cookie", re.IGNORECASE), "禁止访问 document.cookie"),
    (re.compile(r"\bfetch\s*\(", re.IGNORECASE), "禁止发起非白名单 fetch 请求"),
    (re.compile(r"\bXMLHttpRequest\b", re.IGNORECASE), "禁止使用 XMLHttpRequest"),
]
REQUIRED_FILES = {"index.html", "style.css", "game.js", "manifest.json"}
ALLOWED_FILES = REQUIRED_FILES


class ArtifactValidationError(ValueError):
    pass


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
