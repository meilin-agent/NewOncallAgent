# Executor 节点(LangGraph 重构版,对应 Go 版 executor.go + Eino adk ChatModelAgent)
# 内层用一个独立的 ReAct LangGraph 子图(quick 模型 + 工具),上限 10 次模型调用
# (镜像 Eino RemainingIterations:模型每轮 +1 步、工具执行 +1 步 → max_step=20)。

import json
import logging

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from internal.ai.agent.chat_pipeline.react_agent import build_react_graph
from internal.ai.models.open_ai import chat_openai_quick
from utility.mem.mem import Message

logger = logging.getLogger(__name__)

EXECUTOR_SYSTEM_PROMPT = (
    "You are a diligent and meticulous executor agent. Follow the given plan and execute your "
    "tasks carefully and thoroughly."
)

EXECUTOR_USER_TEMPLATE = """## OBJECTIVE
{input}
## Given the following plan:
{plan}
## COMPLETED STEPS & RESULTS
{executed_steps}
## Your task is to execute the first step, which is:
{step}"""

MAX_MODEL_CALLS = 10  # 内层 ReAct 模型调用上限(镜像 Go MaxIterations=10)
MAX_STEP = MAX_MODEL_CALLS * 2  # 模型+工具各计一步


def _render_executed_steps(past_steps: list[dict]) -> str:
    """镜像 Go formatExecutedSteps:"Step: %s\nResult: %s\n\n" 逐条拼接"""
    return "".join(f"Step: {s['step']}\nResult: {s['result']}\n\n" for s in past_steps)


def _to_detail(m: BaseMessage) -> Message:
    """LangChain 消息 → detail 用的 Message(镜像 Go schema.Message.String 语义)"""
    if isinstance(m, AIMessage):
        calls = []
        for tc in m.tool_calls or []:
            calls.append(
                {
                    "id": tc.get("id", ""),
                    "name": tc.get("name", ""),
                    "arguments": json.dumps(tc.get("args", {}), ensure_ascii=False),
                }
            )
        return Message(role="assistant", content=m.content or "", tool_calls=calls)
    return Message(role="tool", content=m.content or "", tool_call_id=getattr(m, "tool_call_id", ""))


def make_executor_node(tools: list, mcp_client=None):
    """返回 executor 图节点函数。

    tools:LangChain 工具列表(本地 3 个 + 可选 MCP 动态工具)。
    mcp_client:McpLogClient 或 None(MCP 工具由 mcp_client 代理,见 lc_tools.mcp_tools_to_langchain)。
    """
    model = chat_openai_quick().bind_tools(tools)
    sub_graph = build_react_graph(model, tools, max_step=MAX_STEP)
    base_len = None  # 记录子图初始消息数,用于截取新增消息

    def executor_node(state: dict) -> dict:
        nonlocal base_len
        plan = state["plan"]
        if not plan:
            raise RuntimeError("plan is empty")
        step = plan[0]
        objective = state["objective"]
        user_content = EXECUTOR_USER_TEMPLATE.format(
            input=objective,
            plan=json.dumps({"steps": plan}, ensure_ascii=False),
            executed_steps=_render_executed_steps(state.get("past_steps", [])),
            step=step,
        )
        msgs: list[BaseMessage] = [
            SystemMessage(content=EXECUTOR_SYSTEM_PROMPT),
            HumanMessage(content=user_content),
        ]
        result = sub_graph.invoke({"messages": msgs, "step": 0})
        all_msgs = result["messages"]
        # detail:子图产生的除初始 2 条外的全部消息
        details = [_to_detail(m).string() for m in all_msgs[2:]]
        final_content = ""
        for m in reversed(all_msgs):
            if isinstance(m, AIMessage):
                final_content = m.content or ""
                break
        return {
            "past_steps": [{"step": step, "result": final_content}],
            "detail": details,
        }

    return executor_node
