"""LangGraph StateGraph 主图定义。

定义游戏生成流程的完整状态图结构。

参考 LangGraph 官方文档:
- https://docs.langchain.com/oss/python/langgraph/use-graph-api
- https://docs.langchain.com/oss/python/langgraph/fault-tolerance
"""

import logging
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.constants import START
from langgraph.types import Command, RetryPolicy, Send
from langgraph.errors import NodeError

from app.agent.state import GenerationState, create_initial_state
from app.agent.nodes import (
    supervisor_agent,
    vision_agent,
    gameplay_agent,
    narrative_agent,
    synthesis_agent,
    code_generator_node,
    validator_node,
    upload_workflow,
    retry_workflow,
    specialist_fan_out,
)
from app.agent.edges import (
    route_by_supervisor,
    should_retry,
)

logger = logging.getLogger(__name__)

# ========================================
# 统一 RetryPolicy：覆盖 LLM 超时、网络抖动、存储临时故障
# ========================================

# code_generator 最多 3 次尝试（首次 + 2 次重试），超时 5 分钟
CODEGEN_RETRY = RetryPolicy(
    max_attempts=3,
    initial_interval=2.0,
    backoff_factor=2.0,
    max_interval=30.0,
    jitter=True,
)
CODEGEN_TIMEOUT = 300  # 5 分钟墙上时钟

# validator 和 upload_workflow 较快，重试间隔短
FAST_RETRY = RetryPolicy(
    max_attempts=3,
    initial_interval=1.0,
    backoff_factor=2.0,
    max_interval=10.0,
    jitter=True,
)

# ========================================
# error_handler：所有重试耗尽后执行
# ========================================

def _on_upload_error(state: GenerationState, error: NodeError) -> Command:
    """upload_workflow 所有重试耗尽后触发：记录错误状态，流程结束。"""
    task_id = state.get("request", {}).task_id if state.get("request") else "unknown"
    logger.error(f"[error_handler] upload_workflow 耗尽重试，task_id={task_id}: {error.error}")
    return Command(
        update={
            "logs": state.get("logs", []) + [{
                "agent": "UploadWorkflow",
                "step": "error_handler",
                "message": f"上传失败（已重试 3 次）: {error.error}",
                "timestamp": datetime.now().isoformat(),
            }],
            "error": f"上传失败: {error.error}",
        },
        goto=END,
    )


def _on_code_gen_error(state: GenerationState, error: NodeError) -> Command:
    """code_generator 所有重试耗尽后触发：记录错误状态，流程结束。"""
    task_id = state.get("request", {}).task_id if state.get("request") else "unknown"
    logger.error(f"[error_handler] code_generator 耗尽重试，task_id={task_id}: {error.error}")
    return Command(
        update={
            "logs": state.get("logs", []) + [{
                "agent": "CodeGenerator",
                "step": "error_handler",
                "message": f"代码生成失败（已重试 3 次）: {error.error}",
                "timestamp": datetime.now().isoformat(),
            }],
            "error": f"代码生成失败: {error.error}",
        },
        goto=END,
    )

# 全局图实例缓存
_generation_graph = None


def create_generation_graph() -> StateGraph:
    """创建游戏生成主图。

    所有有效游戏请求都走统一路径：
    1. START → SupervisorAgent（LLM 判断）
    2. SupervisorAgent → 路由决策
       - "rejected" → END（返回引导信息给用户）
       - 任何 approved → specialist_fan_out（LLM 专家并行）
    3. Specialist Fan-Out：VisionAgent + GameplayAgent + NarrativeAgent 并行执行
    4. SynthesisAgent → 整合设计
    5. CodeGenerator → 调用 LLM 生成游戏代码
    6. Validator → 验证
       - 失败 → RetryWorkflow（最多 3 次）→ Validator
       - 通过 → UploadWorkflow → END

    complexity（simple/complex）仅用于控制 code_generator 的生成规模和详细程度，
    不影响流程分支。

    Returns:
        编译后的 StateGraph
    """
    graph = StateGraph(GenerationState)

    # ========================================
    # 注册所有节点
    # ========================================

    # 入口判断节点
    graph.add_node("supervisor_agent", supervisor_agent)

    # Specialist Fan-Out（分发节点）
    graph.add_node("specialist_fan_out", specialist_fan_out)

    # Specialist Agents
    graph.add_node("vision_agent", vision_agent)
    graph.add_node("gameplay_agent", gameplay_agent)
    graph.add_node("narrative_agent", narrative_agent)

    # 整合与生成
    graph.add_node("synthesis_agent", synthesis_agent)
    graph.add_node(
        "code_generator",
        code_generator_node,
        retry_policy=CODEGEN_RETRY,
        error_handler=_on_code_gen_error,
        timeout=CODEGEN_TIMEOUT,
    )

    # 验证与上传
    # 验证节点：验证失败是正常业务结果，返回 passed=False 由 should_retry 边处理重试
    graph.add_node("validator", validator_node)
    graph.add_node(
        "upload_workflow",
        upload_workflow,
        retry_policy=FAST_RETRY,
        error_handler=_on_upload_error,
        timeout=30,
    )
    graph.add_node("retry_workflow", retry_workflow)

    # ========================================
    # 定义边
    # ========================================

    # START → SupervisorAgent
    graph.add_edge(START, "supervisor_agent")

    # SupervisorAgent → 路由决策（所有 approved 都走 specialist_fan_out）
    graph.add_conditional_edges(
        "supervisor_agent",
        route_by_supervisor,
        {
            "specialist_fan_out": "specialist_fan_out",
            "rejected": END,
        }
    )

    # ========================================
    # Specialist 并行执行 (Fan-Out)
    # 使用 Send API 实现动态并行
    # ========================================

    # Fan-Out: 条件边返回 Send 列表实现并行执行
    graph.add_conditional_edges(
        "specialist_fan_out",
        _route_to_specialists,
    )

    # Fan-In: Specialist 完成后汇聚到 Synthesis
    graph.add_edge("vision_agent", "synthesis_agent")
    graph.add_edge("gameplay_agent", "synthesis_agent")
    graph.add_edge("narrative_agent", "synthesis_agent")

    # Synthesis → Code Generator
    graph.add_edge("synthesis_agent", "code_generator")

    # Code Generator → Validator
    graph.add_edge("code_generator", "validator")

    # ========================================
    # 验证与上传
    # ========================================

    # Validator → 条件边（重试/上传/错误）
    # - validation.passed=True           → upload_workflow
    # - validation.passed=False + <3次   → retry_workflow
    # - validation=None / 重试耗尽       → END
    # 注意：validator_node 抛出的异常由 RetryPolicy 在此边执行前捕获并重试
    graph.add_conditional_edges(
        "validator",
        should_retry,
        {
            "retry_workflow": "retry_workflow",
            "upload_workflow": "upload_workflow",
            "error": END,
        }
    )

    # Retry → Validator（重新验证）
    graph.add_edge("retry_workflow", "validator")

    # Upload → END
    graph.add_edge("upload_workflow", END)

    # ========================================
    # 编译图
    # ========================================
    return graph.compile()


def _route_to_specialists(state: GenerationState) -> list[Send]:
    """Route: 并行触发所有 Specialist Agents。

    使用 Send API 实现动态并行执行。
    每个 Send 会创建一个独立的执行分支，所有分支在同一 superstep 内并行执行。

    Args:
        state: 当前状态

    Returns:
        Send 对象列表，每个 Specialist 一个
    """
    return [
        Send("vision_agent", state),
        Send("gameplay_agent", state),
        Send("narrative_agent", state),
    ]


def get_generation_graph() -> StateGraph:
    """获取全局图实例（单例模式）。

    Returns:
        编译后的 StateGraph
    """
    global _generation_graph
    if _generation_graph is None:
        _generation_graph = create_generation_graph()
    return _generation_graph


async def run_generation(request) -> GenerationState:
    """运行生成流程。

    Args:
        request: GenerateRequest 用户请求

    Returns:
        最终状态
    """
    graph = get_generation_graph()
    initial_state = create_initial_state(request)

    logger.info(f"开始生成流程, task_id={request.task_id}")

    result = await graph.ainvoke(initial_state)

    logger.info(f"生成流程完成, task_id={request.task_id}, error={result.get('error')}")

    return result


async def run_generation_stream(request):
    """流式运行生成流程。

    Args:
        request: GenerateRequest 用户请求

    Yields:
        中间状态更新
    """
    graph = get_generation_graph()
    initial_state = create_initial_state(request)

    logger.info(f"开始流式生成流程, task_id={request.task_id}")

    async for state in graph.astream(initial_state):
        yield state

    logger.info(f"流式生成流程完成, task_id={request.task_id}")
