"""Agent Nodes 模块。

包含 LangGraph StateGraph 中的所有节点实现。

命名规范:
- _agent.py: 使用 LLM 的 Agent 节点
- _workflow.py: 工作流节点
- _node.py: 其他节点
"""

from app.agent.nodes.supervisor_agent import supervisor_agent
from app.agent.nodes.vision_agent import vision_agent
from app.agent.nodes.gameplay_agent import gameplay_agent
from app.agent.nodes.narrative_agent import narrative_agent
from app.agent.nodes.synthesis_agent import synthesis_agent
from app.agent.nodes.code_generator_node import code_generator_node
from app.agent.nodes.validator_node import validator_node
from app.agent.nodes.upload_workflow import upload_workflow
from app.agent.nodes.retry_workflow import retry_workflow
from app.agent.nodes.fanout_node import specialist_fan_out
# DEPRECATED: template_workflow 在图中未连接，保留作为备选路径
from app.agent.nodes.template_workflow import template_workflow

__all__ = [
    "supervisor_agent",
    "vision_agent",
    "gameplay_agent",
    "narrative_agent",
    "synthesis_agent",
    "code_generator_node",
    "validator_node",
    "upload_workflow",
    "retry_workflow",
    "specialist_fan_out",
    # DEPRECATED: 模板快速路径，当前图中未使用
    "template_workflow",
]
