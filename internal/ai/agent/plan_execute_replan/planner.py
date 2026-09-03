# Planner 节点(LangGraph 重构版,对应 Go 版 planner.go + Eino planexecute 默认行为)
# think 模型 + 强制调用 plan 工具(bind_tools + tool_choice="required"),
# 只解析 tool_calls[0](工具不实际执行,仅用于产出计划)。

import json

from langchain_core.tools import StructuredTool

from internal.ai.models.open_ai import chat_openai_think
from utility.mem.mem import Message

PLANNER_PROMPT = """You are an expert planning agent. Given an objective, create a comprehensive step-by-step plan to achieve the objective.

## YOUR TASK
Analyze the objective and generate a strategic plan that breaks down the goal into manageable, executable steps.

## PLANNING REQUIREMENTS
Each step in your plan must be:
- **Specific and actionable**: Clear instructions that can be executed without ambiguity
- **Self-contained**: Include all necessary context, parameters, and requirements
- **Independently executable**: Can be performed by an agent without dependencies on other steps
- **Logically sequenced**: Arranged in optimal order for efficient execution
- **Objective-focused**: Directly contribute to achieving the main goal

## PLANNING GUIDELINES
- Eliminate redundant or unnecessary steps
- Include relevant constraints, parameters, and success criteria for each step
- Ensure the final step produces a complete answer or deliverable
- Anticipate potential challenges and include mitigation strategies
- Structure steps to build upon each other logically
- Provide sufficient detail for successful execution

## QUALITY CRITERIA
- Plan completeness: Does it address all aspects of the objective?
- Step clarity: Can each step be understood and executed independently?
- Logical flow: Do steps follow a sensible progression?
- Efficiency: Is this the most direct path to the objective?
- Adaptability: Can the plan handle unexpected results or changes?"""

PLAN_TOOL_DESCRIPTION = (
    "Plan with a list of steps to execute in order. Each step should be clear, actionable, "
    "and arranged in a logical sequence. The output will be used to guide the execution "
    "process."
)


def make_plan_tool() -> StructuredTool:
    """plan 工具(仅供 bind_tools 提供 schema,不实际执行)"""
    from langchain_core.tools import tool

    @tool("plan", description=PLAN_TOOL_DESCRIPTION)
    def plan_tool(steps: list[str]) -> str:
        """返回计划步骤(占位,不实际执行)"""
        return ""

    return plan_tool


def make_planner_node():
    """返回 planner 图节点函数:输入 objective → 输出 {"plan": [steps], "detail": [...]}"""
    from langchain_core.messages import HumanMessage, SystemMessage

    model = chat_openai_think().bind_tools([make_plan_tool()], tool_choice="required")

    def planner_node(state: dict) -> dict:
        objective = state["objective"]
        msg = model.invoke(
            [
                SystemMessage(content=PLANNER_PROMPT),
                HumanMessage(content=objective),
            ]
        )
        if not msg.tool_calls:
            raise RuntimeError("no tool call")
        tc = msg.tool_calls[0]  # 只取第一个(镜像 Eino)
        args: dict = tc["args"] or {}
        arguments = json.dumps(args, ensure_ascii=False)
        steps = args.get("steps", [])
        if not steps:
            raise RuntimeError("plan tool returned no steps")
        # detail:planner 消息 content 即 tool call 的 arguments JSON(镜像 Go argToContent)
        detail_msg = Message(
            role="assistant",
            content=arguments,
            tool_call_id=tc.get("id", ""),
            tool_call_name="plan",
        )
        return {"plan": steps, "detail": [detail_msg.string()]}

    return planner_node
