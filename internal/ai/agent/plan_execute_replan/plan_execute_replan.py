# Plan-Execute-Replan 主流程(LangGraph 重构版,对应 Go 版 plan_execute_replan.go)
#
# 用 LangGraph StateGraph 实现 Plan-Execute-Replan(参照 LangGraph 官方 plan-and-execute 模式):
#
#   START → planner(think,强制 plan 工具)
#        → executor(quick,内层 ReAct 子图,≤10 次模型调用)
#        → replanner(think,强制 plan/respond 二选一)
#        → 条件路由:respond → END;plan(剩余计划)→ executor(继续循环)
#
# detail 收集各阶段中间消息;结束后用 final_report 兜底生成报告,失败回退原始结果。
# 外层循环上限由 graph recursion_limit 控制(≈20 轮 × 2 节点)。

import json
import logging
from typing_extensions import Annotated, TypedDict

import operator
from langgraph.graph import END, START, StateGraph

from internal.ai.agent.plan_execute_replan.executor import make_executor_node
from internal.ai.agent.plan_execute_replan.final_report import generate_final_report
from internal.ai.agent.plan_execute_replan.planner import make_planner_node
from internal.ai.agent.plan_execute_replan.replan import make_replanner_node
from internal.ai.tools.lc_tools import aiops_local_tools, mcp_tools_to_langchain
from internal.ai.tools.query_log import get_log_mcp_tools

logger = logging.getLogger(__name__)

MAX_OUTER_ITERATIONS = 20  # 外层 execute-replan 循环上限(与 Go 版一致)
RECURSION_LIMIT = 80  # 每个 super-step 计 1 次:planner 1 + (executor+replanner)×20 + 余量


class PlanState(TypedDict):
    objective: str
    plan: list[str]                      # 当前执行计划(步骤列表)
    past_steps: Annotated[list[dict], operator.add]  # [{"step","result"}]
    detail: Annotated[list[str], operator.add]       # 各阶段中间消息(detail 输出)
    response: str                        # respond 工具的最终答复


def _build_graph(mcp_tool_specs: list, mcp_client) -> object:
    """构建 Plan-Execute-Replan 图(executor 工具集依赖 MCP 探测结果,故需入参)"""
    tools = aiops_local_tools() + mcp_tool_specs
    builder = StateGraph(PlanState)
    builder.add_node("planner", make_planner_node())
    builder.add_node("executor", make_executor_node(tools, mcp_client))
    builder.add_node("replanner", make_replanner_node())
    builder.add_edge(START, "planner")
    builder.add_edge("planner", "executor")
    builder.add_edge("executor", "replanner")

    # 路由:respond → END;plan(剩余步骤)→ 回 executor 继续
    def route_after_replanner(state: PlanState):
        return END if state.get("response") else "executor"

    builder.add_conditional_edges("replanner", route_after_replanner, {"executor": "executor", END: END})
    return builder.compile()


def build_plan_agent(query: str) -> tuple[str, list[str]]:
    """执行 AIOps 分析,返回 (最终报告, 执行过程详情列表)"""
    # 1. 日志 MCP 工具为可选:连接失败(10s 超时)降级为空列表,不阻断流程
    mcp_client = None
    mcp_lc_tools: list = []
    try:
        mcp_raw_tools, mcp_client = get_log_mcp_tools()
        mcp_lc_tools = mcp_tools_to_langchain(mcp_raw_tools, mcp_client)
        logger.info("日志 MCP 工具已连接,发现 %d 个工具", len(mcp_lc_tools))
    except Exception as e:
        logger.warning("[warn] log MCP tool unavailable, degrade to continue without it: %s", e)

    graph = _build_graph(mcp_lc_tools, mcp_client)
    try:
        result = graph.invoke(
            {"objective": query, "plan": [], "past_steps": [], "detail": [], "response": ""},
            {"recursion_limit": RECURSION_LIMIT},
        )
    finally:
        if mcp_client is not None:
            mcp_client.close()

    detail: list[str] = result.get("detail", [])
    content: str = result.get("response", "")
    if not content:
        raise RuntimeError("get lastMessage Error")

    # 2. 兜底收尾:基于全部执行记录强制生成最终报告,失败回退原始结果
    report = generate_final_report(query, detail, content)
    if report is not None:
        content = report
    else:
        logger.warning("[warn] generate final report failed, fallback to raw result")
    return content, detail
