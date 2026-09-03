# ReAct Agent(LangGraph 重构版,对应 Go 版 Eino react.Agent)
#
# 用 LangGraph StateGraph 实现经典 ReAct 循环:
#   START → agent(model.bind_tools) → tools_condition
#           ├─ 有 tool_calls → tools(ToolNode) → agent(循环)
#           └─ 无 tool_calls → END
# 语义与 Go 版保持一致:
# - 消息在 state.messages 中累积(不裁剪);
# - MaxStep=25 语义改为 state 内 step 计数:每次 agent 模型调用 +1、每个工具执行 +1,
#   超限抛错(镜像 Go compose.WithMaxRunSteps);
# - 工具顺序执行(OrderedToolsNode)由 LangGraph 默认顺序工具节点保证。

from typing_extensions import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

MAX_STEP = 25


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    step: int  # 累计模型调用与工具执行步数(镜像 Go MaxStep 25)


def _step_limit_error():
    return RuntimeError("exceed max run steps")


def build_react_graph(model, tools, max_step: int = MAX_STEP):
    """构建 ReAct LangGraph 图:model 为已 bind_tools 的 ChatOpenAI,tools 为 LangChain 工具列表。

    返回可反复 invoke/stream 的编译图。
    """
    # handle_tool_errors=False:工具抛异常直接向上传播,镜像 Go tools node(错误不塞进 tool message)
    tool_node = ToolNode(tools, handle_tool_errors=False)

    def agent_node(state: AgentState):
        step = state.get("step", 0) + 1  # 模型调用 +1 步
        if step > max_step:
            raise _step_limit_error()
        out = model.invoke(state["messages"])
        return {"messages": [out], "step": step}

    def tool_node_wrapper(state: AgentState):
        n_calls = len(state["messages"][-1].tool_calls or [])  # 工具执行 +N 步
        step = state.get("step", 0) + n_calls
        if step > max_step:
            raise _step_limit_error()
        out = tool_node.invoke({"messages": state["messages"]})
        return {"messages": out["messages"], "step": step}

    builder = StateGraph(AgentState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", tool_node_wrapper)
    builder.add_edge(START, "agent")
    builder.add_conditional_edges(
        "agent",
        tools_condition,
        {"tools": "tools", END: END},
    )
    builder.add_edge("tools", "agent")
    return builder.compile()


def run_react(
    messages: list,
    model=None,
    tools: list | None = None,
    max_step: int = MAX_STEP,
    stream: bool = False,
    on_chunk=None,
) -> str:
    """执行 ReAct 循环(一次性调用),返回最终回答文本。

    messages: LangChain BaseMessage 列表(system + history + user)。
    stream=True 时通过 on_chunk(token) 回调输出文本增量(仅最终文本轮,
    工具调用轮的 token 为空/被过滤,与手写版行为一致)。
    """
    graph = build_react_graph(model, tools, max_step)
    if not stream:
        final = graph.invoke({"messages": messages, "step": 0})
        return final["messages"][-1].content or ""

    # 流式:stream_mode="messages" 逐 token 产出;跳过空块与工具调用轮
    parts = []
    try:
        for chunk, _meta in graph.stream(
            {"messages": messages, "step": 0},
            stream_mode="messages",
        ):
            content = chunk.content or ""
            if not content:
                continue
            parts.append(content)
            if on_chunk:
                on_chunk(content)
    except StopIteration:
        pass
    return "".join(parts)
