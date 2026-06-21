"""Retry Workflow 节点 - 重试机制。

处理验证失败后的重试逻辑。
"""

import json
import logging
from datetime import datetime

from app.agent.state import GenerationState
from app.agent.schemas import AgentLog

logger = logging.getLogger(__name__)


async def retry_workflow(state: GenerationState) -> GenerationState:
    """RetryWorkflow - 重试机制。

    当验证失败时，增加重试计数并尝试修复问题。

    Args:
        state: 当前状态

    Returns:
        更新后的状态
    """
    request = state["request"]
    current_retry = state.get("retry_count", 0)

    logger.info(f"RetryWorkflow: 重试第 {current_retry + 1} 次, task_id={request.task_id}")

    logs: list[AgentLog] = []

    logs.append(AgentLog(
        agent="RetryWorkflow",
        step="start",
        message=f"开始重试 (第 {current_retry + 1} 次)",
        timestamp=datetime.now().isoformat(),
    ))

    # 获取验证问题
    validation = state.get("validation")
    if validation and not validation.passed:
        issues = validation.issues

        logs.append(AgentLog(
            agent="RetryWorkflow",
            step="issues_found",
            message=f"发现 {len(issues)} 个问题需要修复: {', '.join(issues[:3])}",
            timestamp=datetime.now().isoformat(),
        ))

        # 尝试修复常见问题
        generated_files = state.get("generated_files")
        if generated_files and "files" in generated_files:
            files = generated_files["files"]

            # 修复常见问题：HTML 缺少必要的 meta 标签
            if "index.html" in files:
                html = files["index.html"]
                if '<meta charset' not in html:
                    html = html.replace("<head>", '<head>\n<meta charset="utf-8">', 1)
                    files["index.html"] = html
                    logs.append(AgentLog(
                        agent="RetryWorkflow",
                        step="fix_applied",
                        message="已修复: 添加 charset meta 标签",
                        timestamp=datetime.now().isoformat(),
                    ))

            # 修复常见问题：JS 语法错误（简单的引号匹配）
            if "game.js" in files:
                js = files["game.js"]
                # 检查基本语法
                if js.count("'") % 2 != 0 or js.count('"') % 2 != 0:
                    logger.warning("JS 文件可能有引号不匹配问题")
                    logs.append(AgentLog(
                        agent="RetryWorkflow",
                        step="warning",
                        message="检测到 JS 文件可能有引号不匹配问题",
                        timestamp=datetime.now().isoformat(),
                    ))

            # 修复 manifest.json files 格式：确保是字符串数组
            if "manifest.json" in files:
                try:
                    manifest = json.loads(files["manifest.json"])
                    # 检查 key 是否存在且值合法
                    if "files" not in manifest or not isinstance(manifest["files"], list):
                        manifest["files"] = ["index.html", "style.css", "game.js", "manifest.json"]
                        files["manifest.json"] = json.dumps(manifest, ensure_ascii=False, indent=2)
                        logger.info("已修复 manifest.files（缺失或格式错误）")
                        logs.append(AgentLog(
                            agent="RetryWorkflow",
                            step="fix_applied",
                            message="已修复 manifest files 字段",
                            timestamp=datetime.now().isoformat(),
                        ))
                    elif not all(isinstance(f, str) for f in manifest["files"]):
                        manifest["files"] = ["index.html", "style.css", "game.js", "manifest.json"]
                        files["manifest.json"] = json.dumps(manifest, ensure_ascii=False, indent=2)
                        logger.info("已修复 manifest.files（非字符串数组）")
                        logs.append(AgentLog(
                            agent="RetryWorkflow",
                            step="fix_applied",
                            message="已修复 manifest files 格式",
                            timestamp=datetime.now().isoformat(),
                        ))
                except json.JSONDecodeError:
                    pass

    logs.append(AgentLog(
        agent="RetryWorkflow",
        step="complete",
        message=f"重试处理完成，等待重新验证",
        timestamp=datetime.now().isoformat(),
    ))

    return {
        **state,
        "logs": logs,
        "retry_count": current_retry + 1,
    }
