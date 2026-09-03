# 日志 MCP 工具(对应 Go 版 internal/ai/tools/query_log.go)
#
# 通过 SSE MCP client 连接腾讯云日志服务 MCP,Initialize 握手后动态发现其全部工具。
# 与 Go 版差异:mcp_url 移入 config.yaml 的可选 key log_mcp_url(缺省使用原硬编码地址)。
#
# 实现要点:官方 mcp SDK 基于 asyncio,而本项目调用链是同步的,
# 因此用"专用后台线程 + 专属事件循环 + run_coroutine_threadsafe"桥接,
# session 常驻该循环,不可每次 asyncio.run 重建。
# 连接失败/超时(当前该腾讯地址返回 500 属常态)由调用方捕获降级,不阻断 AIOps 主流程。

import asyncio
import json
import logging
import threading

from utility.config import cfg_get

logger = logging.getLogger(__name__)

DEFAULT_MCP_URL = "https://mcp-api.tencent-cloud.com/sse/02807673a2788326"


class McpLogClient:
    """MCP 日志服务客户端(同步接口,内部桥接 asyncio)"""

    def __init__(self, url: str):
        self.url = url
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._session = None

    def connect(self, timeout: float = 10) -> list:
        """连接并发现工具(镜像 Go 的 10s ctx 超时);任何失败抛异常,由调用方降级。

        返回 mcp SDK 的 Tool 对象列表。
        """
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        try:
            session, tools = asyncio.run_coroutine_threadsafe(self._setup(), self._loop).result(
                timeout
            )
        except Exception:
            self.close()
            raise
        self._session = session
        return tools

    async def _setup(self):
        from mcp import ClientSession
        from mcp.client.sse import sse_client

        read, write = await sse_client(self.url)
        session = ClientSession(read, write)
        # 镜像 Go:InitializeRequest{ProtocolVersion: LATEST, ClientInfo: example-client/1.0.0}
        await session.initialize()
        return session, await session.list_tools()

    def call_tool(self, name: str, arguments: dict, timeout: float = 30) -> str:
        """同步调用 MCP 工具,拼接文本内容返回"""
        fut = asyncio.run_coroutine_threadsafe(
            self._session.call_tool(name, arguments=arguments), self._loop
        )
        res = fut.result(timeout)
        parts = []
        for c in res.content:
            if getattr(c, "type", "") == "text":
                parts.append(c.text)
        return "".join(parts)

    def close(self):
        if self._loop is not None and self._session is not None:
            try:
                fut = asyncio.run_coroutine_threadsafe(self._aclose(), self._loop)
                fut.result(timeout=3)
            except Exception:
                pass
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
        self._session = None

    async def _aclose(self):
        try:
            await self._session.aclose()
        except Exception:
            pass


def mcp_tools_to_openai(tools: list) -> list[dict]:
    """把 mcp SDK 的 Tool 列表转成 openai 工具格式"""
    specs = []
    for t in tools:
        params = t.inputSchema or {"type": "object", "properties": {}}
        specs.append(
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": params,
                },
            }
        )
    return specs


def get_log_mcp_tools(timeout: float = 10) -> tuple[list, McpLogClient | None]:
    """镜像 Go GetLogMcpTool:返回 (openai 工具规格列表, 客户端);失败抛异常,由调用方降级跳过"""
    url = cfg_get("log_mcp_url", DEFAULT_MCP_URL)
    if not url:
        raise ValueError("未配置日志 MCP 地址(log_mcp_url)")
    client = McpLogClient(url)
    mcp_tools = client.connect(timeout=timeout)
    return mcp_tools_to_openai(mcp_tools), client
