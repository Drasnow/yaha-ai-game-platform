"""Validator 节点 - 安全验证与结构检查。

验证生成代码的安全性、完整性和结构正确性。
验证失败时返回问题分类：
  - fixable:    可自动修复（引用路径错、manifest 格式错等）
  - unfixable:  不可修复，需重新调用 LLM（JSON 格式崩溃、缺少字段等）
  - critical:   严重问题（安全风险），直接失败

注意：不调用 validator.py 的 validate_generated_files()，
因为后者会重复检查 REQUIRED_FILES 和 manifest entry，
导致同一问题被同时归类为 fixable 和 critical。
安全模式检查（BANNED_PATTERNS）直接内联在此文件中。
"""

import json
import logging
import re
from datetime import datetime

from app.agent.state import GenerationState
from app.agent.schemas import AgentLog, ValidationResult, IssueKind

logger = logging.getLogger(__name__)

# ========================================
# 安全模式检查（BANNED_PATTERNS）
# ========================================

BANNED_PATTERNS = [
    (re.compile(r"<script\s+[^>]*src=[\"'](?:https?:)?//", re.IGNORECASE), "禁止加载外部脚本"),
    (re.compile(r"\beval\s*\(", re.IGNORECASE), "禁止使用 eval()"),
    (re.compile(r"\bFunction\s*\(", 0), "禁止使用 Function() 构造器"),
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

# 引用路径检查的正则
_REF_PATTERN = [
    ('href="style.css"', 'href=\'style.css\''),
    ('src="game.js"', 'src=\'game.js\''),
]


def _check_file_structure(files: dict[str, str]) -> list[tuple[str, str]]:
    """检查文件结构完整性。

    Returns:
        [(issue_msg, issue_kind), ...]，空列表表示通过
    """
    issues: list[tuple[str, str]] = []
    required = ["index.html", "style.css", "game.js", "manifest.json"]

    for fname in required:
        if fname not in files:
            issues.append((f"缺少必需文件: {fname}", IssueKind.UNFIXABLE))
        elif not files[fname].strip():
            issues.append((f"文件 {fname} 内容为空", IssueKind.UNFIXABLE))

    if "index.html" in files:
        html = files["index.html"]
        for ref_ok_1, ref_ok_2 in _REF_PATTERN:
            if ref_ok_1 not in html and ref_ok_2 not in html:
                issues.append(
                    (f"index.html 未正确引用 {ref_ok_1.split('=')[0].lstrip('href=\"src=')} 文件", IssueKind.FIXABLE)
                )

    if "style.css" in files and len(files["style.css"].strip()) < 10:
        issues.append(("style.css 内容过短", IssueKind.FIXABLE))

    if "game.js" in files and len(files["game.js"].strip()) < 10:
        issues.append(("game.js 内容过短", IssueKind.FIXABLE))

    return issues


def _check_manifest(files: dict[str, str]) -> list[tuple[str, str]]:
    """检查 manifest.json 内容正确性。

    Returns:
        [(issue_msg, issue_kind), ...]，空列表表示通过
    """
    issues: list[tuple[str, str]] = []

    if "manifest.json" not in files:
        return [("manifest.json 缺失", IssueKind.UNFIXABLE)]

    try:
        manifest = json.loads(files["manifest.json"])
    except json.JSONDecodeError as e:
        return [(f"manifest.json 格式错误: {e}", IssueKind.UNFIXABLE)]

    if manifest.get("entry") != "index.html":
        issues.append(("manifest entry 必须是 index.html", IssueKind.FIXABLE))

    if manifest.get("runtime") != "iframe-html-v1":
        issues.append(("manifest runtime 必须是 'iframe-html-v1'", IssueKind.FIXABLE))

    manifest_files = manifest.get("files")
    if not isinstance(manifest_files, list) or not all(isinstance(f, str) for f in manifest_files):
        issues.append(("manifest files 必须是文件名字符串数组", IssueKind.FIXABLE))
    else:
        missing_in_manifest = {"index.html", "style.css", "game.js"} - set(manifest_files)
        if missing_in_manifest:
            issues.append(
                (f"manifest files 缺少必要文件: {', '.join(sorted(missing_in_manifest))}", IssueKind.FIXABLE)
            )

    return issues


def _check_security(files: dict[str, str]) -> list[tuple[str, str]]:
    """检查代码安全风险。

    Returns:
        [(issue_msg, issue_kind), ...]，空列表表示通过。安全问题统一标记为 CRITICAL。
    """
    issues: list[tuple[str, str]] = []

    for fname, content in files.items():
        if not fname.endswith((".html", ".js", ".css")):
            continue
        for pattern, message in BANNED_PATTERNS:
            if pattern.search(content):
                issues.append((f"{fname} 安全校验失败：{message}", IssueKind.CRITICAL))

    return issues


async def validator_workflow(state: GenerationState) -> GenerationState:
    """ValidatorWorkflow - 验证生成代码。

    检查三层内容，全部失败才返回 passed=False + issue_kinds：
      1. 文件结构完整性（存在性、引用路径、内容非空）
      2. manifest 配置正确性（JSON 格式、必需字段）
      3. 安全规则校验（危险函数、注入风险）

    所有检查均在 validator_workflow 内完成，不依赖 code_generator_agent。
    """
    request = state["request"]

    logger.info(f"ValidatorWorkflow: 验证生成代码, task_id={request.task_id}")

    logs: list[AgentLog] = []
    all_issues: list[str] = []
    all_kinds: list[str] = []

    logs.append(AgentLog(
        agent="Validator",
        step="start",
        message="开始验证生成代码",
        timestamp=datetime.now().isoformat(),
    ))

    try:
        generated_files = state.get("generated_files")
        if generated_files is None:
            raise ValueError("没有可验证的文件")

        files = generated_files.get("files", {})

        # ---- 层 1: 文件结构 ----
        for msg, kind in _check_file_structure(files):
            all_issues.append(msg)
            all_kinds.append(kind)
            logger.warning(f"Validator [structure]: {msg} ({kind})")

        # ---- 层 2: manifest ----
        for msg, kind in _check_manifest(files):
            all_issues.append(msg)
            all_kinds.append(kind)
            logger.warning(f"Validator [manifest]: {msg} ({kind})")

        # ---- 层 3: 安全规则 ----
        for msg, kind in _check_security(files):
            all_issues.append(msg)
            all_kinds.append(kind)
            logger.warning(f"Validator [security]: {msg} ({kind})")

        if not all_issues:
            logs.append(AgentLog(
                agent="Validator",
                step="complete",
                message="所有验证通过",
                timestamp=datetime.now().isoformat(),
            ))
            return {
                **state,
                "logs": logs,
                "validation": ValidationResult(
                    passed=True,
                    issues=[],
                    warnings=[],
                    issue_kinds=[],
                ),
            }

        logs.append(AgentLog(
            agent="Validator",
            step="validation_failed",
            message=f"发现 {len(all_issues)} 个问题: {', '.join(all_issues[:3])}",
            timestamp=datetime.now().isoformat(),
        ))

        return {
            **state,
            "logs": logs,
            "validation": ValidationResult(
                passed=False,
                issues=all_issues,
                warnings=[],
                issue_kinds=all_kinds,
            ),
        }

    except Exception as e:
        logger.error(f"Validator: 验证失败: {e}")
        return {
            **state,
            "logs": logs + [AgentLog(
                agent="Validator",
                step="error",
                message=f"验证异常: {str(e)}",
                timestamp=datetime.now().isoformat(),
            )],
            "validation": ValidationResult(
                passed=False,
                issues=[f"验证过程异常: {str(e)}"],
                warnings=[],
                issue_kinds=[IssueKind.CRITICAL],
            ),
        }
