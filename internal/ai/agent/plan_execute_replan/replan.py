# Replanner 节点(LangGraph 重构版,对应 Go 版 replan.go + Eino planexecute 默认行为)
# think 模型 + 强制在 plan / respond 两个工具中二选一(bind_tools + tool_choice="required"):
#   respond → 终止外层循环;plan → 生成剩余计划覆盖并继续。只解析 tool_calls[0]。

import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import StructuredTool

from internal.ai.models.open_ai import chat_openai_think
from utility.mem.mem import Message

from .executor import _render_executed_steps
from .planner import make_plan_tool

RESPOND_TOOL_DESCRIPTION = (
    "Generate a direct response to the user. Use this tool when you have all the "
    "information needed to provide a final answer."
)

REPLANNER_PROMPT = """You are going to review the progress toward an objective. Analyze the current state and determine the optimal next action.

## YOUR TASK
Based on the progress above, you MUST choose exactly ONE action:

### Option 1: COMPLETE (if objective is fully achieved)
Call '{respond_tool}' with:
- A comprehensive final answer
- Clear conclusion summarizing how the objective was met
- Key insights from the execution process

### Option 2: CONTINUE (if more work is needed)
Call '{plan_tool}' with a revised plan that:
- Contains ONLY remaining steps (exclude completed ones)
- Incorporates lessons learned from executed steps
- Addresses any gaps or issues discovered
- Maintains logical step sequence

## PLANNING REQUIREMENTS
Each step in your plan must be:
- **Specific and actionable**: Clear instructions that can be executed without ambiguity
- **Self-contained**: Include all necessary context, parameters, and requirements
- **Independently executable**: Can be performed by an agent without dependencies on other steps
- **Logically sequenced**: Arranged in optimal order for efficient execution
- **Objective-focused**: Directly contribute to achieving the main goal

## PLANNING GUIDELINES
- Eliminate redundant or unnecessary steps
- Adapt strategy based on new information
- Include relevant constraints, parameters, and success criteria for each step

## DECISION CRITERIA
- Has the original objective been completely satisfied?
- Are there any remaining requirements or sub-goals?
- Do the results suggest a need for strategy adjustment?
- What specific actions are still required?"""


def make_respond_tool() -> StructuredTool:
    """respond 工具(仅供 bind_tools 提供 schema,不实际执行)"""
    from langchain_core.tools import tool

    @tool("respond", description=RESPOND_TOOL_DESCRIPTION)
    def respond_tool(response: str) -> str:
        """最终答复(占位)"""
        return ""

    return respond_tool


def make_replanner_node():
    """返回 replanner 图节点函数:
    输出 respond 时 → {"response": str};输出 plan 时 → {"plan": [steps]}。两者都附带 detail。"""
    model = chat_openai_think().bind_tools([make_plan_tool(), make_respond_tool()], tool_choice="required")

    def replanner_node(state: dict) -> dict:
        objective = state["objective"]
        plan_steps = state.get("plan", [])
        executed_text = _render_executed_steps(state.get("past_steps", []))

        # system 部分:不含 "User:" 段;两个工具占位符替换
        system = REPLANNER_PROMPT.replace("{plan_tool}", "plan").replace("{respond_tool}", "respond")
        user = (
            f"## OBJECTIVE\n{objective}\n\n"
            f"## ORIGINAL PLAN\n{json.dumps({'steps': plan_steps}, ensure_ascii=False)}\n\n"
            f"## COMPLETED STEPS & RESULTS\n{executed_text}"
        )
        msg = model.invoke(
            [
                SystemMessage(content=system),
                HumanMessage(content=user),
            ]
        )
        if not msg.tool_calls:
            raise RuntimeError("no tool call")
        tc = msg.tool_calls[0]  # 只取第一个(镜像 Eino)
        args: dict = tc["args"] or {}
        arguments = json.dumps(args, ensure_ascii=False)
        detail_msg = Message(
            role="assistant",
            content=arguments,
            tool_call_id=tc.get("id", ""),
            tool_call_name=tc.get("name", ""),
        )
        if tc["name"] == "respond":
            return {"response": args.get("response", ""), "detail": [detail_msg.string()]}
        if tc["name"] == "plan":
            return {"plan": args.get("steps", []), "detail": [detail_msg.string()]}
        raise RuntimeError(f"unexpected tool call: {tc['name']}")

    return replanner_node
