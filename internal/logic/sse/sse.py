# SSE 工具(对应 Go 版 internal/logic/sse/sse.go)
# 事件字节格式与 Go 版逐字节一致:
#   握手:id: <clientId>\nevent: connected\ndata: {"status": "connected", "client_id": "<clientId>"}\n\n
#   消息:id: <纳秒时间戳>\nevent: message|done|error\ndata: <原样文本>\n\n
# data 为原样文本,不做 JSON 转义(Go 版同样如此);Go 版的死代码(chan/map)不移植。

import time


def event_line(event_id, event: str, data: str) -> str:
    return f"id: {event_id}\nevent: {event}\ndata: {data}\n\n"


def connected_block(client_id: str) -> str:
    return (
        f"id: {client_id}\nevent: connected\n"
        f'data: {{"status": "connected", "client_id": "{client_id}"}}\n\n'
    )


def message_line(data: str) -> str:
    return event_line(time.time_ns(), "message", data)


def done_line() -> str:
    return event_line(time.time_ns(), "done", "Stream completed")


def error_line(data: str) -> str:
    return event_line(time.time_ns(), "error", data)
