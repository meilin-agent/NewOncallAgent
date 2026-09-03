# 工具注册表(对应 Go 版 chat_pipeline/reAgent.go 的工具绑定)
# LangGraph 重构后:返回 LangChain Tool 列表,由 LangGraph 的 ToolNode 直接调用
# (LangChain 重构替代原 dispatch 分发器,工具名称与 description 逐字保留)。

from internal.ai.tools.lc_tools import chat_tools


def chat_tool_list() -> list:
    """Chat 模式 ReAct 工具集(顺序与 Go 版一致:query_prometheus_alerts, mysql_crud,
    get_current_time, query_internal_docs, encourage;MCP 日志工具不注册)"""
    return chat_tools()
