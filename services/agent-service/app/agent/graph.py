"""LangGraph StateGraph 主图定义。

定义游戏生成流程的完整状态图结构。

参考 LangGraph 官方文档:
- https://docs.langchain.com/oss/python/langgraph/use-graph-api
- https://docs.langchain.com/oss/python/langgraph/fault-tolerance
- https://docs.langchain.com/langsmith/trace-with-langgraph  # LangGraph + LangSmith 标准集成
- https://docs.langchain.com/oss/python/langgraph/persistence  # 持久化检查点
"""

import logging
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.constants import START
from langgraph.types import Command, RetryPolicy
from langgraph.errors import NodeError

from app.agent.state import GenerationState, create_initial_state, get_request
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

# Checkpointer 由外部（main.py）注入，支持 MemorySaver / RedisSaver / PostgresSaver 等。
# 官方文档: https://docs.langchain.com/oss/python/langgraph/persistence
# - MemorySaver: 进程内，仅开发调试用
# - RedisSaver: 跨进程持久化，服务重启后可恢复（生产推荐）
# - PostgresSaver: 同样支持跨进程，ACID 保证更强
# 每个 node 的输入/输出/异常会自动上报 LangSmith（需 env 配置 LANGSMITH_*）。


# ========================================
# 图实例管理（单例）
# ========================================

_graph_instance: StateGraph | None = None


def init_graph(checkpointer) -> StateGraph:
    """初始化并缓存全局图实例（幂等）。

    应在 FastAPI lifespan 中调用，确保 Redis 连接就绪后再初始化图。

    Args:
        checkpointer: LangGraph Checkpointer 实例（如 RedisSaver）。
                      传 None 则不启用持久化检查点（fallback 到无 checkpointer）。

    Returns:
        编译后的 StateGraph
    """
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = create_generation_graph(checkpointer=checkpointer)
        logger.info("LangGraph 图实例已初始化（checkpointer=%s)", type(checkpointer).__name__)
    return _graph_instance


def get_generation_graph() -> StateGraph | None:
    """获取全局图实例（需先调用 init_graph）。"""
    return _graph_instance


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
    task_id = get_request(state).task_id
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
    task_id = get_request(state).task_id
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


# ========================================
# 图构建
# ========================================

def create_generation_graph(checkpointer=None) -> StateGraph:
    """创建游戏生成主图。

    所有有效游戏请求都走统一路径：
    1. START → SupervisorAgent（LLM 判断）
    2. SupervisorAgent → 路由决策
       - "rejected" → END（返回引导信息给用户）
       - 任何 approved → 并行执行 VisionAgent + GameplayAgent + NarrativeAgent
    3. SynthesisAgent → 整合设计
    4. CodeGeneratorAgent → 调用 LLM 生成游戏代码
    5. ValidatorWorkflow → 验证
       - 通过           → UploadWorkflow → END
       - critical 问题  → END（安全问题，直接失败）
       - unfixable 问题 → CodeGeneratorAgent（重新调用 LLM）
       - fixable 问题   → RetryWorkflow（自动修复，最多 3 次）→ ValidatorWorkflow 重验证

    complexity（simple/complex）仅用于控制 code_generator 的生成规模和详细程度，
    不影响流程分支。

    Args:
        checkpointer: LangGraph Checkpointer 实例（如 RedisSaver）。
                      传 None 则不启用持久化检查点。

    Returns:
        编译后的 StateGraph
    """
    graph = StateGraph(GenerationState)

    # ========================================
    # 注册所有节点
    # ========================================

    # 入口判断节点
    graph.add_node("supervisor_agent", supervisor_agent)

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

    # SupervisorAgent → 路由决策（rejected 结束，approved 并行执行 Specialists）
    graph.add_conditional_edges(
        "supervisor_agent",
        route_by_supervisor,
        {
            "rejected": END,
        }
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

    # 编译图（checkpointer 由外部注入，支持 MemorySaver / RedisSaver / PostgresSaver）
    return graph.compile(checkpointer=checkpointer)


# ========================================
# 执行入口
# ========================================

def _get_invoke_config(request) -> dict:
    """构建传递给 graph.ainvoke / graph.astream 的 config。

    LangGraph 执行时会自动将这些 run 上报到 LangSmith，呈现为树状 trace：
      supervisor_agent
        └── LLM Chat (child run, via @traceable)
      vision_agent / gameplay_agent / narrative_agent (并行)
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


async def run_generation(request) -> GenerationState:
    """运行生成流程。

    通过全局单例图实例执行，thread_id 绑定 task_id，
    确保同一任务可从上次中断的节点恢复（Redis 持久化检查点）。

    Args:
        request: GenerateRequest 用户请求

    Returns:
        最终状态
    """
    graph = get_generation_graph()
    if graph is None:
        raise RuntimeError("图实例未初始化，请先调用 init_graph(checkpointer)")
    initial_state = create_initial_state(request)

    logger.info(f"开始生成流程, task_id={request.task_id}")

    config = _get_invoke_config(request)
    result = await graph.ainvoke(initial_state, config=config)

    logger.info(f"生成流程完成, task_id={request.task_id}, error={result.get('error')}")

    return result


async def run_generation_stream(request):
    """流式运行生成流程。

    通过全局单例图实例执行，支持断点续跑。

    Args:
        request: GenerateRequest 用户请求

    Yields:
        中间状态更新
    """
    graph = get_generation_graph()
    if graph is None:
        raise RuntimeError("图实例未初始化，请先调用 init_graph(checkpointer)")
    initial_state = create_initial_state(request)

    logger.info(f"开始流式生成流程, task_id={request.task_id}")

    config = _get_invoke_config(request)
    async for state in graph.astream(initial_state, config=config):
        yield state

    logger.info(f"流式生成流程完成, task_id={request.task_id}")
