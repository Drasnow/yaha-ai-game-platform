# Yaha 游戏平台 Multi-Agent 架构设计文档 (LangGraph)

> 本文档描述 Yaha 互动游戏平台 V5 增强计划中的 Multi-Agent 架构设计，使用 **LangGraph** 框架实现。

---

## 一、为什么选择 LangGraph

### 1.1 传统 Agent vs LangGraph

| 特征 | 传统 Agent 实现 | LangGraph |
|------|----------------|-----------|
| **状态管理** | 手动传递 state dict | 内置 StateGraph，自动状态传递 |
| **流程控制** | if/else 硬编码 | Conditional Edge 动态路由 |
| **并行执行** | asyncio.gather 手动编排 | 内置 Send/Join 机制 |
| **回溯能力** | 复杂的状态快照逻辑 | Checkpoint 内置支持 |
| **可视化** | 第三方工具 | 内置可视化调试器 |
| **持久化** | 自行实现 | Checkpoint + Resume |

### 1.2 LangGraph 核心概念

```
┌─────────────────────────────────────────────────────────────────────┐
│                          LangGraph 核心概念                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   StateGraph                                                          │
│   ┌───────────────────────────────────────────────────────────┐     │
│   │  State: {"request": ..., "vision": None, "gameplay": ...} │     │
│   └───────────────────────────────────────────────────────────┘     │
│           │                                                           │
│           ▼                                                           │
│   ┌─────────────┐     ┌─────────────┐                              │
│   │  Node A     │────▶│  Node B     │  Edge (状态驱动)              │
│   │  (Agent)    │     │  (Workflow) │                              │
│   └─────────────┘     └─────────────┘                              │
│           │                                                           │
│           ▼                                                           │
│   ┌─────────────┐                                                    │
│   │  Node C     │◄── Conditional Edge (路由决策)                     │
│   └─────────────┘                                                    │
│                                                                      │
│   Checkpoint: 任意节点可保存快照，支持中断恢复                          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 二、整体架构设计

### 2.1 LangGraph StateGraph 架构图

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         User Request (Prompt + Assets)                          │
└─────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              GenerationStateGraph                               │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                              State 定义                                   │   │
│  │  class GenerationState(TypedDict):                                       │   │
│  │      request: GenerateRequest        # 用户请求                            │   │
│  │      supervisor_result: SupervisorResult | None  # Supervisor 决策      │   │
│  │      vision: VisionSpec | None       # 视觉规范                            │   │
│  │      gameplay: GameplaySpec | None   # 游戏机制                            │   │
│  │      narrative: NarrativeSpec | None # 叙事内容                            │   │
│  │      unified_design: UnifiedDesign  # 整合设计                            │   │
│  │      generated_files: GeneratedFiles # 生成代码                            │   │
│  │      validation: ValidationResult   # 验证结果                            │   │
│  │      artifact: UploadResult         # 上传结果                            │   │
│  │      logs: list[AgentLog]          # 执行日志                            │   │
│  │      error: str | None              # 错误信息                            │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                          │                                       │
│  ┌──────────────────────────────────────┴───────────────────────────────────┐  │
│  │                                                                             │  │
│  │  ┌─────────────┐                                                          │  │
│  │  │  START      │                                                          │  │
│  │  └──────┬──────┘                                                          │  │
│  │         │                                                                  │  │
│  │         ▼                                                                  │  │
│  │  ┌─────────────────────────────────────────────────────────────────────┐  │  │
│  │  │              supervisor_agent（LLM 入口判断）                              │  │  │
│  │  │  ┌───────────────────────────────────────────────────────────────┐  │  │  │
│  │  │  │  • rejected → feedback_message → END（返回引导）                 │  │  │  │
│  │  │  │  • approved（任何） → [并行] vision/gameplay/narrative agents   │  │  │  │
│  │  │  └───────────────────────────────────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────────────────────────────────┘  │  │
│  │                              │                                          │  │
│  │         ┌───────────────────────────────────────┐                    │  │
│  │         │                                       │                    │  │
│  │         │     ┌───────────────────────────────┼────────────────┐   │  │
│  │         │     │                               │                │   │  │
│  │         │     ▼                               ▼                ▼   │  │
│  │         │ ┌─────────────┐           ┌─────────────┐  ┌─────────────┐│  │  │
│  │         │ │ VisionAgent │           │GameplayAgent│  │NarrativeAgent││  │  │
│  │         │     │  (并行执行)  │            │  (并行执行)  │ │  (并行执行)  ││   │  │
│  │         │     └──────┬──────┘            └──────┬──────┘ └──────┬──────┘│   │  │
│  │         │            │                           │               │       │   │  │
│  │         │            └───────────────────────────┼───────────────┘       │   │  │
│  │         │                                    │                           │   │  │
│  │         │                                    ▼                           │   │  │
│  │         │                          ┌─────────────────┐                    │   │  │
│  │         │                          │ SynthesisAgent  │                    │   │  │
│  │         │                          │   (整合设计)    │                    │   │  │
│  │         │                          └────────┬────────┘                    │   │  │
│  │         │                                   │                             │   │  │
│  │                                    │                         │   │   │  │
│  │                                    ▼                         │   │   │  │
│  │                          ┌─────────────────┐                   │   │   │  │
│  │                          │CodeGeneratorNode│                   │   │   │  │
│  │                          │  (LLM生成代码) │                   │   │   │  │
│  │                          └────────┬────────┘                   │   │   │  │
│  │                                   │                         │   │   │  │
│  │                                   ▼                         │   │   │  │
│  │                         ┌─────────────────┐                   │   │   │  │
│  │                         │ ValidatorNode   │                   │   │   │  │
│  │                         │   (安全验证)    │                   │   │   │  │
│  │                         └────────┬────────┘                   │   │   │  │
│  │                                  │                         │   │   │  │
│  │              ┌───────────────────┼───────────────────┐   │   │   │  │
│  │              ▼                   ▼                   ▼   │   │   │  │
│  │       ┌─────────────┐     ┌─────────────┐    ┌─────────────┐ │ │  │
│  │       │    END      │     │   upload    │    │    END      │ │  │  │
│  │       │   (拒绝)    │     │  workflow   │    │  (错误)     │ │  │  │
│  │  └─────────────┘                   └─────────────┘          └─────────────┘ │  │
│  │                                                                             │  │
│  └─────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 节点类型说明

| 节点类型 | 名称 | 说明 | LLM 调用 |
|----------|------|------|----------|
| **Agent Node** | VisionAgent | 使用 LLM 设计视觉规范 | 是 |
| **Agent Node** | GameplayAgent | 使用 LLM 设计游戏机制 | 是 |
| **Agent Node** | NarrativeAgent | 使用 LLM 设计叙事内容 | 是 |
| **Agent Node** | SynthesisAgent | 使用 LLM 整合设计 | 是 |
| **Agent Node** | CodeGeneratorNode | 使用 LLM 生成代码 | 是 |
| **Agent Node** | SupervisorAgent | 使用 LLM 判断输入类型（简单/复杂/拒绝） | 是 |
| **Workflow Node** | TemplateWorkflow | 模板快速生成设计规范 | 否 |
| **Workflow Node** | ValidatorNode | 安全规则验证 | 否 |
| **Workflow Node** | UploadWorkflow | MinIO 上传 | 否 |
| **Workflow Node** | RetryWorkflow | 失败重试（最多 3 次） | 否 |
| **Router Node** | SupervisorAgent（条件边 Send） | 入口 Supervisor，通过 `add_conditional_edges` 直接触发 Specialist 并行分发 | 否 |

### 2.3 LangGraph 多 Agent 流程图

以下是项目实际实现的 LangGraph 完整流程图，对应代码 `app/agent/graph.py`：

```
用户请求 (prompt + assets)
          │
          ▼
┌─────────────────────┐
│      START          │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   supervisor_agent（Supervisor Agent）                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  LLM 判断输入类型                                                   │   │
│  │  • rejected     → 设置 feedback_message → END（返回引导给用户）    │   │
│  │  • approved（任何） → [并行] VisionAgent + GameplayAgent + NarrativeAgent  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
            ┌──────────────────────┼──────────────────────┐
            │                      │                      │
            ▼                      │                      ▼
   ┌─────────────────┐             │           ┌──────────────────────┐
   │           │  [并行执行] Specialist Agents  │
   │  (模板路径)     │             │           │  [并行] 3个 Agents  │
   └────────┬────────┘             │           └──────────┬───────────┘
            │                      │                      │
            │                      │          ┌───────────┼───────────┐
            │                      │          ▼           ▼           ▼
            │                      │   ┌────────┐   ┌────────┐  ┌────────┐
            │                      │   │ Vision │   │Gameplay│  │Narrative│
            │                      │   │ Agent │   │ Agent  │  │ Agent  │
            │                      │   └───┬────┘   └───┬────┘  └───┬────┘
            │                      │       └───────────┼───────────┘
            │                      │                 ▼
            │                      │         ┌────────────────┐
            │                      │         │ synthesis_agent│
            │                      │         │   (整合设计)  │
            │                      │         └────────┬───────┘
            │                      │                  │
            └──────────────────────┼──────────────────┤
                                   │                  │
                                   ▼                  ▼
                         ┌─────────────────┐ ┌────────────────┐
                         │ code_generator  │◄┤ code_generator │
                         │  (模板渲染)    │ └────────────────┘
                         └────────┬────────┘
                                  │
                                  ▼
                        ┌──────────────────┐
                        │ validator_workflow│
                        └────────┬────────┘
                                 │
            ┌────────────────────┼────────────────────┐
            ▼                    ▼                    ▼
     ┌─────────────┐      ┌─────────────┐     ┌─────────────┐
     │retry_workflow│     │ upload_wf   │     │     END     │
     │  (重试3次)  │     │ (上传文件)  │     │  (拒绝终止)  │
     └──────┬──────┘     └──────┬──────┘     └─────────────┘
            │                    │
            └────────┬───────────┘
                     ▼
               ┌──────────┐
               │ upload_wf│
               └────┬─────┘
                    ▼
                ┌───────┐
                │  END  │
                └───────┘
```

### 节点详解

| 节点 | 类型 | 作用 | LLM 调用 |
|------|------|------|----------|
| **supervisor_agent** | Agent 节点 | 入口 Supervisor。使用 LLM 分析用户 prompt，判断是否为有效游戏请求（排除闲聊/无关内容）、复杂度（简单/复杂），决定后续路径。拒绝时返回 `feedback_message` 引导用户重新输入。approved 时通过条件边直接触发三个 Specialist 并行执行。 | 是 |
| **code_generator_agent** | Agent 节点 | 调用 LLM 生成完整的 HTML/CSS/JS 游戏代码。根据 `unified_design` 中的视觉、机制、叙事规范生成代码。complexity 字段决定生成规模和复杂度（simple=单关卡 ~60s，complex=多关卡 ~3-5min）。LLM 超时 5 分钟，支持指数退避重试（最多 3 次）。 | 是 |
| **vision_agent** | Agent 节点 | 视觉设计师。使用 LLM 生成游戏视觉规范（风格、配色、动画、氛围、字体）。三个 Specialist 中并行执行。 | 是 |
| **gameplay_agent** | Agent 节点 | 游戏机制设计师。使用 LLM 生成游戏机制规范（类型、目标、玩法、难度、计分、操作方式）。 | 是 |
| **narrative_agent** | Agent 节点 | 叙事设计师。使用 LLM 生成叙事内容规范（主题、故事钩子、角色、进度叙事、反馈消息）。 | 是 |
| **synthesis_agent** | Agent 节点 | 设计整合师。等待三个 Specialist 结果汇总后，使用 LLM 将视觉、机制、叙事规范整合为统一的 `UnifiedDesign`。 | 是 |
| **code_generator_agent** | Agent 节点 | 代码生成器。读取 `UnifiedDesign`，调用 LLM 生成 HTML/CSS/JS 游戏文件及 `manifest.json`。无论是 template 路径还是 specialist 路径，最终都经过此节点生成文件，实现统一的产物质量。LLM 超时 5 分钟，支持指数退避重试（最多 3 次）。 | 是 |
| **validator_workflow** | Workflow 节点 | 安全验证器。检查生成代码的完整性（文件结构、关键函数、manifest），无 LLM 调用。三层检查（文件结构 / manifest 格式 / 安全模式）各自独立，互不重叠。fixable 问题标记为 `FIXABLE` 返回给边路由处理。 | 否 |
| **retry_workflow** | Workflow 节点 | 重试工作流。当 `validator_workflow` 失败时触发：对 fixable 问题自动修复（manifest 格式、HTML 引用等）；对 unfixable 问题标记 `regenerate_requested`，触发重新调用 CodeGeneratorAgent。最多 3 次自动修复机会。 | 否 |
| **upload_workflow** | Workflow 节点 | 文件上传器。将生成的文件上传至 MinIO 存储，返回 manifest_url / entry_url / artifact_base_url。 | 否 |

### 边路由说明

```
supervisor_agent 路由：
  status == "rejected"           → END（返回 supervisor_feedback 给用户）
  status == "approved"（任何）  → [并行] Send(vision_agent) + Send(gameplay_agent) + Send(narrative_agent)

validator_workflow 路由：
  验证通过 + passed=True                      → upload_workflow → END
  验证失败 + regenerate_requested=True         → code_generator_agent（重新生成）
  验证失败 + critical 问题                    → END (安全问题直接终止)
  验证失败 + fixable 问题 + retry_count < 3  → retry_workflow → validator_workflow
  验证失败 + fixable 问题 + retry_count >= 3 → END (修复耗尽终止)
```

### Supervisor Agent 决策说明

Supervisor Agent 是整个流程的入口，使用 LLM 判断用户输入：

- **rejected**：用户输入与游戏设计无关（如闲聊、问候、知识问答等）。流程终止，`GenerateResponse.status = "rejected"`，`supervisor_feedback` 字段返回给用户友好的引导信息。
- **approved**：所有有效游戏请求都走统一路径（`Supervisor → 3 Specialist 并行（Send API）→ synthesis → code_generator → validator → upload`），调用 LLM 生成代码。`complexity` 字段（simple/complex）仅传递给 code_generator，用于控制生成代码的规模和复杂度。LLM 调用次数：1 次（Supervisor）+ 3 次（Specialist）+ 1 次（Synthesis）+ 1 次（CodeGenerator）= **6 次**。

### 路径对比

| 路径 | 触发条件 | LLM 调用 | 耗时 |
|------|---------|---------|------|
| **拒绝路径** | Supervisor 判定为无关输入 | 1 次（Supervisor） | ~1s |
| **统一生成路径** | 所有 approved 请求 | 6 次（Supervisor + 3 Specialist + Synthesis + CodeGenerator） | ~30-120s |

---

## 三、数据结构设计

### 3.1 LangGraph State 定义

```python
from typing import TypedDict, NotRequired, Literal
from pydantic import BaseModel

class GenerationState(TypedDict):
    """LangGraph 状态定义"""

    # 输入
    request: GenerateRequest  # 用户请求（不再有 generation_mode 字段）

    # Supervisor 决策（入口 Agent）
    supervisor_result: SupervisorResult | None

    # Specialist 输出 (并行填充)
    vision: NotRequired[VisionSpec | None]
    gameplay: NotRequired[GameplaySpec | None]
    narrative: NotRequired[NarrativeSpec | None]

    # 整合与生成
    unified_design: NotRequired[UnifiedDesign | None]
    generated_files: NotRequired[dict | None]
    validation: NotRequired[ValidationResult | None]
    artifact: NotRequired[UploadResult | None]

    # 执行追踪
    logs: list[AgentLog]
    error: NotRequired[str | None]
    retry_count: NotRequired[int]

    # Specialist 结果（并行写入合并）
    specialist_results: NotRequired[dict[str, str]]


class SupervisorResult(BaseModel):
    """Supervisor Agent 决策结果"""
    status: Literal["approved_simple", "approved_complex", "rejected"]
    complexity: str
    reason: str
    feedback_message: str


class AgentLog(BaseModel):
    """执行日志"""
    agent: str
    step: str
    message: str
    timestamp: str
```

### 3.2 Specialist Output Schemas

```python
class VisionSpec(BaseModel):
    """视觉设计规范"""
    style: Literal["pixel", "cartoon", "minimal", "neon", "nature", "retro", "futuristic"]
    color_palette: dict[str, str]
    animation_hints: list[str]
    mood: str
    typography_hint: str


class GameplaySpec(BaseModel):
    """游戏机制规范"""
    genre: Literal["click", "avoid", "quiz", "puzzle", "action", "endless_runner", "timing"]
    objective: str
    mechanics: list[str]
    difficulty_curve: str
    scoring_system: str
    time_limit: int | None
    win_condition: str
    fail_condition: str
    controls: list[str]


class NarrativeSpec(BaseModel):
    """叙事内容规范"""
    theme: str
    story_hook: str
    character_description: str
    progression_narrative: str
    feedback_messages: dict[str, str]


class UnifiedDesign(BaseModel):
    """整合后的统一设计"""
    title: str
    description: str
    tags: list[str]
    vision: VisionSpec
    gameplay: GameplaySpec
    narrative: NarrativeSpec
    template_hint: str


class GeneratedFiles(BaseModel):
    """生成的代码文件"""
    files: dict[str, str]
    manifest: dict[str, object]


class ValidationResult(BaseModel):
    """验证结果"""
    passed: bool
    issues: list[str]
    warnings: list[str]


class UploadResult(BaseModel):
    """上传结果"""
    manifest_url: str
    entry_url: str
    artifact_base_url: str
    file_count: int
```

---

## 四、LangGraph 实现详解

### 4.1 项目结构

```
services/agent-service/
├── app/
│   ├── main.py                    # FastAPI 入口
│   ├── llm/                       # LLM 调用层 (Phase 0)
│   │   ├── __init__.py
│   │   ├── client.py             # LLM Client
│   │   ├── providers.py          # Provider 适配
│   │   └── exceptions.py         # LLM 异常
│   ├── agent/                     # Agent 层 (LangGraph)
│   │   ├── __init__.py
│   │   ├── state.py              # GenerationState 定义
│   │   ├── graph.py              # LangGraph 主图
│   │   ├── nodes/                # 节点实现
│   │   │   ├── __init__.py
│   │   │   ├── supervisor_agent.py  # Supervisor Agent（入口判断）
│   │   │   ├── vision_agent.py      # VisionAgent
│   │   │   ├── gameplay_agent.py    # GameplayAgent
│   │   │   ├── narrative_agent.py   # NarrativeAgent
│   │   │   ├── synthesis_agent.py   # SynthesisAgent
│   │   │   ├── code_generator_agent.py  # CodeGeneratorAgent（LLM生成代码）
│   │   │   ├── validator_workflow.py  # ValidatorWorkflow
│   │   │   ├── upload_workflow.py   # UploadWorkflow
│   │   │   ├── fanout_node.py      # [已废弃，节点已删除，保留文件]
│   │   │   ├── retry_workflow.py   # RetryWorkflow
│   │   │   └── edges.py            # 边定义
│   ├── schemas/
│   │   └── generate.py
│   └── core/
│       └── config.py
├── tests/
└── .env.example
```

### 4.2 LangGraph 主图定义

```python
# app/agent/graph.py

from langgraph.graph import StateGraph, END
from langgraph.constants import Send

from app.agent.state import GenerationState
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
from app.agent.edges import route_by_supervisor, should_retry


def create_generation_graph() -> StateGraph:
    """创建游戏生成主图"""
    graph = StateGraph(GenerationState)

    # 注册节点
    graph.add_node("supervisor_agent", supervisor_agent)
    graph.add_node("vision_agent", vision_agent)
    graph.add_node("gameplay_agent", gameplay_agent)
    graph.add_node("narrative_agent", narrative_agent)
    graph.add_node("synthesis_agent", synthesis_agent)
    graph.add_node("code_generator", code_generator_agent)
    graph.add_node("validator", validator_workflow)
    graph.add_node("upload_workflow", upload_workflow)
    graph.add_node("retry_workflow", retry_workflow)

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

    # Specialist → Synthesis
    graph.add_edge("vision_agent", "synthesis_agent")
    graph.add_edge("gameplay_agent", "synthesis_agent")
    graph.add_edge("narrative_agent", "synthesis_agent")

    # Synthesis → Code Generator
    graph.add_edge("synthesis_agent", "code_generator")

    # Validator 条件边
    graph.add_conditional_edges(
        "validator",
        should_retry,
        {
            "retry_workflow": "retry_workflow",
            "upload_workflow": "upload_workflow",
            "error": END,
        }
    )

    graph.add_edge("retry_workflow", "validator")
    graph.add_edge("upload_workflow", END)

    return graph.compile()


def _route_to_specialists(state: GenerationState) -> list[Send]:
    """并行触发所有 Specialist Agents"""
    return [
        Send("vision_agent", state),
        Send("gameplay_agent", state),
        Send("narrative_agent", state),
    ]
```

### 4.3 节点实现示例

#### 4.3.1 Specialist Agent (VisionAgent)

```python
# app/agent/nodes/vision.py

from app.agent.state import GenerationState
from app.agent.schemas import VisionSpec
from app.llm.client import LLMClient
from app.core.config import get_settings


VISION_PROMPT = """你是一个资深游戏视觉设计师。请根据用户的创意，设计游戏的视觉风格。

用户创意：{prompt}
素材数量：{asset_count}

请以 JSON 格式输出视觉规范：
{{
    "style": "pixel/cartoon/minimal/neon/nature/retro/futuristic",
    "color_palette": {{"primary": "#xxx", "accent": "#xxx", "background": "#xxx"}},
    "animation_hints": ["效果描述列表"],
    "mood": "轻松愉快/紧张刺激/神秘悬疑",
    "typography_hint": "字体风格描述"
}}
"""


async def vision_agent(state: GenerationState) -> GenerationState:
    """VisionAgent - 设计视觉规范"""
    settings = get_settings()

    try:
        llm = LLMClient(
            provider=create_provider(
                settings.llm_provider,
                settings.llm_base_url,
                settings.llm_api_key,
                settings.llm_model,
            )
        )

        prompt = VISION_PROMPT.format(
            prompt=state["request"].prompt,
            asset_count=len(state["request"].assets),
        )

        result = await llm.generate_json(
            prompt=prompt,
            schema=VisionSpec,
        )

        state["vision"] = result
        state["logs"].append({
            "agent": "VisionAgent",
            "step": "complete",
            "message": f"视觉规范生成完成: {result.style} 风格"
        })

    except Exception as e:
        state["specialist_results"] = state.get("specialist_results", {})
        state["specialist_results"]["vision"] = f"failed: {str(e)}"
        state["logs"].append({
            "agent": "VisionAgent",
            "step": "error",
            "message": f"视觉规范生成失败: {str(e)}"
        })

    return state
```

#### 4.3.2 Supervisor Agent 实现

```python
# app/agent/nodes/supervisor_agent.py

from pydantic import BaseModel
from app.agent.state import GenerationState
from app.agent.schemas import AgentLog, SupervisorResult
from app.llm.client import LLMClient
from app.llm.providers import create_provider
from app.core.config import get_settings

SUPERVISOR_PROMPT = """你是一个游戏创意审核助手。请分析用户的输入，判断其类型。

用户输入：{prompt}

## 判断标准：
- **rejected**：闲聊、问候、知识问答、与游戏设计无关的内容
- **approved_simple**：简短描述（<100字符）+ 常见游戏类型（点击挑战、问答闯关、躲避障碍）
- **approved_complex**：详细描述（>=100字符）或 有独特创意要求

请输出 JSON：
{{
    "status": "approved_simple | approved_complex | rejected",
    "complexity": "simple | medium | complex",
    "reason": "判断理由",
    "feedback_message": "如果 rejected，给用户的友好引导"
}}
"""


class SupervisorSchema(BaseModel):
    status: str
    complexity: str
    reason: str
    feedback_message: str


async def supervisor_agent(state: GenerationState) -> GenerationState:
    settings = get_settings()
    provider = create_provider(...)
    llm = LLMClient(provider=provider)

    result = await llm.generate_json(
        prompt=SUPERVISOR_PROMPT.format(prompt=state["request"].prompt),
        schema=SupervisorSchema,
    )
    await llm.close()

    return {
        **state,
        "supervisor_result": SupervisorResult(**result.model_dump()),
        "logs": [
            AgentLog(agent="SupervisorAgent", step="start",
                     message="开始分析用户输入", timestamp=...),
            AgentLog(agent="SupervisorAgent", step="decision",
                     message=f"决策: {result.status}", timestamp=...),
        ],
    }
```

### 4.4 边定义 (Edges)

```python
# app/agent/edges.py

from typing import Literal

from langgraph.constants import END
from langgraph.types import Send

from app.agent.state import GenerationState


def route_by_supervisor(state: GenerationState) -> list[Send] | str:
    """根据 Supervisor Agent 决策结果路由。

    rejected → 直接结束（用户请求不合法或超出能力范围）
    approved → 并行触发所有 Specialist Agents（通过 Send 列表实现动态并行）
    """
    sr = state.get("supervisor_result")
    if sr is None:
        # 降级保护：没有 supervisor 结果，尝试走生成路径
        return [
            Send("vision_agent", state),
            Send("gameplay_agent", state),
            Send("narrative_agent", state),
        ]
    if sr.status == "rejected":
        return "rejected"
    # 所有 approved → 并行触发三个 Specialist
    return [
        Send("vision_agent", state),
        Send("gameplay_agent", state),
        Send("narrative_agent", state),
    ]


def should_retry(state: GenerationState) -> Literal["retry_workflow", "upload_workflow", "error"]:
    """验证后决定下一步"""
    validation = state.get("validation")
    if validation is None:
        return "error"
    if validation.passed:
        return "upload_workflow"
    if state.get("retry_count", 0) < 3:
        return "retry_workflow"
    return "error"
```

---

## 五、Checkpoint 与恢复

### 5.1 启用 Checkpoint

```python
# app/agent/graph.py

from langgraph.checkpoint.memory import MemorySaver

def create_generation_graph() -> StateGraph:
    graph = StateGraph(GenerationState)

    # ... 添加节点和边 ...

    # 使用内存 Checkpoint
    checkpointer = MemorySaver()

    return graph.compile(checkpointer=checkpointer)


# 带有 Checkpoint 的执行
async def run_generation_with_checkpoint(
    request: GenerateRequest,
    thread_id: str,
) -> GenerationState:
    """运行生成流程，支持中断恢复"""

    graph = get_generation_graph()
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = GenerationState(
        request=request,
        logs=[],
        retry_count=0,
    )

    return await graph.ainvoke(initial_state, config=config)


async def resume_generation(thread_id: str) -> GenerationState:
    """恢复中断的生成流程"""
    graph = get_generation_graph()
    config = {"configurable": {"thread_id": thread_id}}

    return await graph.ainvoke(None, config=config)  # None 表示从上次状态继续
```

---

## 六、LLM Provider 配置

### 6.1 环境变量

```env
# LLM Provider Configuration
LLM_PROVIDER="fighting"
LLM_BASE_URL="http://43.106.115.130:8080/v1"
LLM_API_KEY="sk-xxx"
LLM_MODEL="gpt-5.5"
LLM_TIMEOUT="300"
LLM_MAX_RETRIES="3"

# Agent Behavior
ENABLE_LLM_FALLBACK="true"
DEFAULT_GENERATION_MODE="auto"
```

---

## 七、实施计划

### Phase 0：LangGraph 基础设施 (已完成)

- [x] LLM Client 实现
- [x] Provider 适配器
- [x] 异常处理

### Phase 1：LangGraph StateGraph 实现 (已完成)

- [x] 创建 `GenerationState` 状态定义
- [x] 实现 `StateGraph` 主图
- [x] 实现 `SupervisorAgent` 入口判断
- [x] 定义边和条件路由

### Phase 2：Agent Nodes 实现 (已完成)

- [x] SupervisorAgent 入口判断（简单/复杂/拒绝）
- [x] VisionAgent 视觉规范
- [x] GameplayAgent 游戏机制
- [x] NarrativeAgent 叙事内容
- [x] SynthesisAgent 设计整合

### Phase 3：Workflow Nodes 实现 (已完成)

- [x] SupervisorAgent 直接触发 Specialist 并行分发（Send API）
- [x] VisionAgent 视觉规范生成（LLM）
- [x] GameplayAgent 游戏机制生成（LLM）
- [x] NarrativeAgent 叙事内容生成（LLM）
- [x] SynthesisAgent 设计整合（LLM）
- [x] CodeGeneratorNode 代码生成（LLM 生成完整游戏代码）
- [x] ValidatorNode 安全验证
- [x] UploadWorkflow 文件上传
- [x] RetryWorkflow 重试机制

### Phase 4：高级特性

- [ ] Checkpoint 与恢复
- [ ] SupervisorAgent 拒绝路径的前端对接（supervisor_feedback 展示）
- [ ] puzzle/action/endless_runner 等游戏类型的专用渲染器

---

## 八、参考资料

官方文档总览：
https://docs.langchain.com/oss/python/langgraph/overview （英）
https://docs.langchain.org.cn/oss/python/langgraph/overview （中）

LangSmith
https://docs.langchain.com/langsmith/observability