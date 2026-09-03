# LangChain 工具装配层(LangGraph 重构新增)
# 用 langchain_core.tools @tool 把 6 个原生工具包装为 LangChain Tool,
# 名称与 description 与 Go 版逐字一致(保持 Agent 可见契约不变)。
# 由 ToolNode 直接调用,替代原来的 dispatch 分发器。

import json

from langchain_core.tools import StructuredTool, tool

from internal.ai.tools import (
    encourage,
    get_current_time,
    mysql_crud,
    query_internal_docs,
    query_metrics_alerts,
)


@tool("query_prometheus_alerts", description=query_metrics_alerts.TOOL_DESCRIPTION)
def query_prometheus_alerts_tool() -> str:
    """查询 Prometheus 活跃告警(原始工具函数见 query_metrics_alerts.py)"""
    return query_metrics_alerts.query_prometheus_alerts()


@tool(
    "query_internal_docs",
    description=query_internal_docs.TOOL_DESCRIPTION,
)
def query_internal_docs_tool(query: str) -> str:
    """RAG 检索内部文档(原始工具函数见 query_internal_docs.py)"""
    return query_internal_docs.query_internal_docs({"query": query})


@tool("get_current_time", description=get_current_time.TOOL_DESCRIPTION)
def get_current_time_tool() -> str:
    """获取当前时间(秒/毫秒/微秒)"""
    return get_current_time.get_current_time()


@tool(
    "mysql_crud",
    description=mysql_crud.TOOL_DESCRIPTION,
)
def mysql_crud_tool(dsn: str, sql: str, operate_type: str) -> str:
    """执行 MySQL SQL(原始工具函数见 mysql_crud.py)"""
    return mysql_crud.mysql_crud({"dsn": dsn, "sql": sql, "operate_type": operate_type})


@tool("encourage", description=encourage.TOOL_DESCRIPTION)
def encourage_tool() -> str:
    """输出鼓励语"""
    return encourage.encourage()


def chat_tools() -> list:
    """Chat 模式 ReAct 工具集(顺序与 Go 版一致,不含日志 MCP)"""
    return [query_prometheus_alerts_tool, query_internal_docs_tool, get_current_time_tool, mysql_crud_tool, encourage_tool]


def aiops_local_tools() -> list:
    """AIOps Executor 的本地工具集(顺序与 Go 版一致;日志 MCP 动态附加)"""
    return [query_prometheus_alerts_tool, query_internal_docs_tool, get_current_time_tool]


def mcp_tools_to_langchain(mcp_tools: list, mcp_client) -> list:
    """把 MCP 动态发现的工具转成 LangChain StructuredTool(代理到 mcp_client.call_tool)。

    参数类型按 inputSchema 的 properties 简单映射为 str(可选的 required 不强制),
    复杂类型以 JSON 字符串传入,MCP 侧自行解释。
    """
    result = []
    for t in mcp_tools:
        name, desc = t.name, t.description or ""
        schema = t.inputSchema or {"type": "object", "properties": {}}
        props = schema.get("properties", {})

        if props:
            args_desc = "、".join(f"{k}:{v.get('description', '')}" for k, v in props.items())

            def _func(name=name, mcp_client=mcp_client, args_desc=args_desc, **kwargs):
                args = {k: v for k, v in kwargs.items() if v is not None}
                # 复杂参数(对象/数组)以 JSON 字符串传入,原样透传
                for k, v in list(args.items()):
                    if isinstance(v, str) and v.startswith(("{", "[")):
                        try:
                            args[k] = json.loads(v)
                        except json.JSONDecodeError:
                            pass
                return mcp_client.call_tool(name, args)

            # 动态生成参数签名:全部可选,任意类型
            tool_obj = StructuredTool.from_function(
                func=_func,
                name=name,
                description=desc,
                args_schema=_make_args_model(name, props),
            )
        else:

            def _noargs(name=name, mcp_client=mcp_client):
                return mcp_client.call_tool(name, {})

            tool_obj = StructuredTool.from_function(func=_noargs, name=name, description=desc)
        result.append(tool_obj)
    return result


def _make_args_model(tool_name: str, props: dict):
    """按 inputSchema properties 动态生成 Pydantic 参数模型(字段名见 props,全部转 str 可选)"""
    from pydantic import BaseModel, Field, create_model

    fields = {}
    for pname, pinfo in (props or {}).items():
        fields[pname] = (
            str | None,
            Field(default=None, description=pinfo.get("description", "")),
        )
    model = create_model(f"Mcp{tool_name}Args", **fields)
    model.__doc__ = "MCP 动态工具参数"
    return model
