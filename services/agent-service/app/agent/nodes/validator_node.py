"""Validator 节点 - 安全验证。

验证生成代码的安全性。
"""

import logging
from datetime import datetime

from app.agent.state import GenerationState, GeneratedFiles
from app.agent.schemas import AgentLog, ValidationResult
from app.agent.validator import validate_generated_files, ValidationError

logger = logging.getLogger(__name__)


async def validator_node(state: GenerationState) -> GenerationState:
    """ValidatorNode - 验证生成代码。

    验证游戏代码的安全性，包括：
    - 文件结构完整性
    - manifest 配置正确性
    - 安全规则校验

    验证失败（ValidationError / ValueError）返回 passed=False，
    由 should_retry 边 + retry_workflow 处理重试（最多 3 次）。

    Args:
        state: 当前状态

    Returns:
        更新后的状态，包含 validation 字段
    """
    request = state["request"]

    logger.info(f"Validator: 验证生成代码, task_id={request.task_id}")

    logs: list[AgentLog] = []

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

        generated = GeneratedFiles(
            files=generated_files.get("files", {}),
            manifest=generated_files.get("manifest", {}),
        )

        # 执行验证
        validate_generated_files(generated)

        # 构建验证结果
        validation_result = ValidationResult(
            passed=True,
            issues=[],
            warnings=[],
        )

        logs.append(AgentLog(
            agent="Validator",
            step="complete",
            message="所有验证通过",
            timestamp=datetime.now().isoformat(),
        ))

        return {
            **state,
            "logs": logs,
            "validation": validation_result,
        }

    except ValidationError as e:
        logger.warning(f"Validator: 验证发现问题: {e}")

        validation_result = ValidationResult(
            passed=False,
            issues=[str(e)],
            warnings=[],
        )

        logs.append(AgentLog(
            agent="Validator",
            step="validation_failed",
            message=f"验证发现问题: {str(e)}",
            timestamp=datetime.now().isoformat(),
        ))

        return {
            **state,
            "logs": logs,
            "validation": validation_result,
        }

    except Exception as e:
        logger.error(f"Validator: 验证失败: {e}")

        validation_result = ValidationResult(
            passed=False,
            issues=[f"验证过程异常: {str(e)}"],
            warnings=[],
        )

        logs.append(AgentLog(
            agent="Validator",
            step="error",
            message=f"验证异常: {str(e)}",
            timestamp=datetime.now().isoformat(),
        ))

        return {
            **state,
            "logs": logs,
            "validation": validation_result,
        }
