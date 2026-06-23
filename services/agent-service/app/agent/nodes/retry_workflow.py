"""Retry Workflow 节点 - 修复与重新生成决策。

处理验证失败后的两种处理路径：
  - fixable:    可自动修复的问题 → 在已有文件上修复 → 重新验证
  - unfixable:  不可修复的问题 → 标记触发重新生成（由 should_retry 边路由回 CodeGenerator）
"""

import json
import logging
from datetime import datetime

from app.agent.state import GenerationState
from app.agent.schemas import AgentLog, IssueKind

logger = logging.getLogger(__name__)

# 重试上限（fixable 修复次数）
MAX_FIX_ATTEMPTS = 3


async def retry_workflow(state: GenerationState) -> GenerationState:
    """RetryWorkflow - 修复不可用文件并决定下一步。

    1. 从 ValidationResult 中提取问题列表和分类
    2. 对 fixable 问题执行自动修复
    3. 对 unfixable 问题标记重新生成请求
    4. 返回更新后的状态，由 should_retry 边决定路由

    Args:
        state: 当前状态

    Returns:
        更新后的状态，包含 regenerate_requested 标志
    """
    request = state["request"]
    current_retry = state.get("retry_count", 0)
    validation = state.get("validation")

    logger.info(f"RetryWorkflow: 处理第 {current_retry + 1} 次, task_id={request.task_id}")

    logs: list[AgentLog] = []

    logs.append(AgentLog(
        agent="RetryWorkflow",
        step="start",
        message=f"开始处理验证失败 (第 {current_retry + 1} 次)",
        timestamp=datetime.now().isoformat(),
    ))

    regenerate_requested = False
    fix_applied = False

    if validation and not validation.passed:
        issues = validation.issues
        issue_kinds = validation.issue_kinds or []

        logs.append(AgentLog(
            agent="RetryWorkflow",
            step="issues_found",
            message=f"发现 {len(issues)} 个问题: {', '.join(issues[:3])}",
            timestamp=datetime.now().isoformat(),
        ))

        generated_files = state.get("generated_files")
        if generated_files and "files" in generated_files:
            files = generated_files["files"]

            # ---- 修复所有 fixable 问题 ----
            fix_applied = _fix_issues(files, issues, issue_kinds, logs)

            # ---- 检查是否存在 unfixable / critical 问题 ----
            for msg, kind in zip(issues, issue_kinds):
                if kind in (IssueKind.UNFIXABLE, IssueKind.CRITICAL):
                    regenerate_requested = True
                    logger.info(f"RetryWorkflow: 检测到 {kind} 问题 [{msg}]，标记重新生成")
                    break

    # 构建结果日志
    if regenerate_requested:
        logs.append(AgentLog(
            agent="RetryWorkflow",
            step="regenerate_marked",
            message="存在不可修复问题，标记请求重新调用 CodeGenerator",
            timestamp=datetime.now().isoformat(),
        ))
    elif fix_applied:
        logs.append(AgentLog(
            agent="RetryWorkflow",
            step="fixes_applied",
            message="已应用自动修复，等待重新验证",
            timestamp=datetime.now().isoformat(),
        ))
    else:
        logs.append(AgentLog(
            agent="RetryWorkflow",
            step="no_action",
            message="无自动修复项，等待重新验证",
            timestamp=datetime.now().isoformat(),
        ))

    return {
        **state,
        "logs": logs,
        "retry_count": current_retry + 1,
        "regenerate_requested": regenerate_requested,
    }


def _fix_issues(
    files: dict[str, str],
    issues: list[str],
    issue_kinds: list[str],
    logs: list[AgentLog],
) -> bool:
    """对所有 fixable 问题执行自动修复。

    Returns:
        True 表示有修复被应用
    """
    any_fixed = False

    # ---- 预解析 manifest.json（只解析一次） ----
    manifest_data = None
    if "manifest.json" in files:
        try:
            manifest_data = json.loads(files["manifest.json"])
        except json.JSONDecodeError:
            manifest_data = None

    # ---- HTML 相关修复 ----
    if "index.html" in files:
        html = files["index.html"]
        html_changed = False

        # 1. 缺少 charset
        if "charset" not in html.lower() and "<head>" in html:
            html = html.replace("<head>", '<head>\n<meta charset="utf-8">', 1)
            _log_fix(logs, "添加缺失的 charset meta 标签")
            html_changed = True
            any_fixed = True

        # 4. 缺少 CSS/JS 引用
        if 'href="style.css"' not in html and "href='style.css'" not in html:
            html = html.replace("</head>", '<link rel="stylesheet" href="style.css">\n</head>', 1)
            _log_fix(logs, "修复 index.html 的 style.css 引用")
            html_changed = True
            any_fixed = True
        if 'src="game.js"' not in html and "src='game.js'" not in html:
            html = html.replace("</body>", '<script src="game.js"></script>\n</body>', 1)
            _log_fix(logs, "修复 index.html 的 game.js 引用")
            html_changed = True
            any_fixed = True

        if html_changed:
            files["index.html"] = html

    # ---- manifest.json 修复（只写一次） ----
    if "manifest.json" in files and manifest_data is not None:
        manifest_changed = False
        fixed_msgs: set[str] = set()

        # 2. files 字段
        files_field = manifest_data.get("files")
        needs_files_fix = False
        if files_field is None:
            needs_files_fix = True
        elif not isinstance(files_field, list):
            needs_files_fix = True
        elif not all(isinstance(f, str) for f in files_field):
            needs_files_fix = True
        elif not {"index.html", "style.css", "game.js"}.issubset(set(files_field)):
            needs_files_fix = True

        if needs_files_fix:
            manifest_data["files"] = ["index.html", "style.css", "game.js", "manifest.json"]
            manifest_changed = True
            fixed_msgs.add("修复 manifest files 字段")

        # 3. entry / runtime
        if manifest_data.get("entry") != "index.html":
            manifest_data["entry"] = "index.html"
            manifest_changed = True
            fixed_msgs.add("修复 manifest entry 字段")
        if manifest_data.get("runtime") != "iframe-html-v1":
            manifest_data["runtime"] = "iframe-html-v1"
            manifest_changed = True
            fixed_msgs.add("修复 manifest runtime 字段")

        if manifest_changed:
            files["manifest.json"] = json.dumps(manifest_data, ensure_ascii=False, indent=2)
            for msg in fixed_msgs:
                _log_fix(logs, msg)
            any_fixed = True

    return any_fixed


def _log_fix(logs: list[AgentLog], message: str) -> None:
    logs.append(AgentLog(
        agent="RetryWorkflow",
        step="fix_applied",
        message=message,
        timestamp=datetime.now().isoformat(),
    ))
