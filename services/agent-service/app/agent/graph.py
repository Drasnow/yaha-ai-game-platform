"""LangGraph StateGraph 主图定义。

定义游戏生成流程的完整状态图结构。

参考 LangGraph 官方文档:
- https://docs.langchain.com/oss/python/langgraph/use-graph-api
- https://docs.langchain.com/oss/python/langgraph/fault-tolerance
- https://docs.langchain.com/langsmith/trace-with-langgraph  # LangGraph + LangSmith 标准集成
"""

import logging
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.constants import START
from langgraph.types import Command, RetryPolicy, Send
from langgraph.errors import NodeError

# LangGraph 内置内存 checkpointer，同时服务于：
# 1. 进程内状态持久化（断点续算）
# 2. LangSmith tracing 数据管道（每个 node 的输入输出自动上报）
# 官方文档: https://docs.langchain.com/langsmith/trace-with-langgraph
try:
    from langgraph.checkpoint.memory import MemorySaver
except ImportError:
    MemorySaver = None

from app.agent.state import GenerationState, create_initial_state
from app.agent.nodes import (
    supervisor_agent,
    vision_agent,
    gameplay_agent,
    narrative_agent,
    synthesis_agent,
    code_generator_agent,
    validator_workflow,
    upload_workflow,
    retry_workflow,
    specialist_fan_out,
)
from app.agent.edges import (
    route_by_supervisor,
    should_retry,
)

logger = logging.getLogger(__name__)

# LangSmith Tracing:
# 环境变量已在 app.main 模块加载时设置完毕（LANGSMITH_API_KEY / PROJECT / TRACING）
# LangGraph 会自动读取这些 env var 并将每个 node 的执行上报至 LangSmith。
# 无需额外 import 或初始化 langsmith SDK。
#
# LangSmith API key 所在区域如果非默认（US），需额外设置 LANGSMITH_ENDPOINT：
#   - GCP EU:  "https://eu.api.smith.langchain.com"
#   - AWS US:  "https://aws.api.smith.langchain.com"
#   - GCP APAC: "https://apac.api.smith.langchain.com"

# Checkpointer:
# MemorySaver 提供进程内状态持久化，同时作为 LangSmith tracing 的数据管道。
# 每个 node 的输入/输出/异常会被自动上报，在 https://smith.langchain.com 看到完整树状 trace。
# 注意：MemorySaver 在进程重启后状态丢失，仅适合开发调试。
_checkpointer = MemorySaver() if MemorySaver else None


def _get_invoke_config(request) -> dict:
    """构建传递给 graph.ainvoke / graph.astream 的 config。

    LangGraph 执行时会自动将这些 run 上报到 LangSmith，呈现为树状 trace：
      supervisor_agent
        └── LLM Chat (child run, via @traceable)
      specialist_fan_out
        ├── vision_agent
        ├── gameplay_agent
        └── narrative_agent
      synthesis_agent
      code_generator_agent
        └── LLM Chat (child run)
      validator
      upload_workflow

    thread_id: 固定线程名，按请求聚合，方便在 LangSmith 中定位
    tags: 方便在 LangSmith 中按 tag 过滤
    """
    return {
        "configurable": {
            "thread_id": f"yaha-{request.task_id}",
        },
        "run_name": f"yaha-generate-{request.task_id}",
        "tags": ["yaha-agent", "game-generation"],
    }


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
    5. CodeGeneratorAgent → 调用 LLM 生成游戏代码
    6. ValidatorWorkflow → 验证
       - 通过           → UploadWorkflow → END
       - critical 问题  → END（安全问题，直接失败）
       - unfixable 问题 → CodeGeneratorAgent（重新调用 LLM）
       - fixable 问题   → RetryWorkflow（自动修复，最多 3 次）→ ValidatorWorkflow 重验证

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
        code_generator_agent,
        retry_policy=CODEGEN_RETRY,
        error_handler=_on_code_gen_error,
        timeout=CODEGEN_TIMEOUT,
    )

    # 验证与上传
    # 验证节点：验证失败是正常业务结果，返回 passed=False 由 should_retry 边处理重试
    graph.add_node("validator", validator_workflow)
    graph.add_node(
        "upload_workflow",
        upload_workflow,
        retry_policy=FAST_RETRY,
        error_handler=_on_upload_error,
        timeout=600,
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
    # 验证与上传（重试机制说明）
    # ========================================
    # 验证失败时，should_retry 边根据问题分类路由：
    #   fixable   → retry_workflow（自动修复，最多 3 次）→ validator 重验证
    #   unfixable → code_generator（重新调用 LLM 生成）
    #   critical  → END（安全问题，直接失败）
    #   passed    → upload_workflow → END
    # ========================================

    # Validator → 条件边（修复/重新生成/上传/错误）
    # - validation.passed=True                      → upload_workflow
    # - regenerate_requested=True                   → code_generator（重新调用 LLM）
    # - critical 问题                              → error（直接失败）
    # - fixable 问题 + retry_count < 3             → retry_workflow（自动修复后重验证）
    # - fixable 问题 + retry_count >= 3 或其他     → error（兜底）
    graph.add_conditional_edges(
        "validator",
        should_retry,
        {
            "retry_workflow": "retry_workflow",
            "regenerate": "code_generator",
            "upload_workflow": "upload_workflow",
            "error": END,
        }
    )

    # RetryWorkflow → 修复后重新验证
    graph.add_edge("retry_workflow", "validator")

    # Upload → END
    graph.add_edge("upload_workflow", END)

    # ========================================
    # 编译图（传入 checkpointer 以支持 LangSmith tracing）
    # ========================================
    if _checkpointer:
        return graph.compile(checkpointer=_checkpointer)
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

    # LangGraph 会自动将每个节点的输入/输出作为 child run 上报到 LangSmith
    config = _get_invoke_config(request)
    result = await graph.ainvoke(initial_state, config=config)

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

    config = _get_invoke_config(request)
    async for state in graph.astream(initial_state, config=config):
        yield state

    logger.info(f"流式生成流程完成, task_id={request.task_id}")
