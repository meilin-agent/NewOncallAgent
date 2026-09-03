# 当前时间工具(对应 Go 版 internal/ai/tools/get_current_time.go)
# 返回秒/毫秒/微秒三种时间戳与格式化时间。

import json
from datetime import datetime

TOOL_NAME = "get_current_time"

TOOL_DESCRIPTION = (
    "Get current system time in multiple formats. Returns the current time in seconds (Unix "
    "timestamp), milliseconds, and microseconds. Use this tool when you need to retrieve current "
    "system time for logging, timing operations, or timestamping events."
)

SPEC = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": TOOL_DESCRIPTION,
        "parameters": {"type": "object", "properties": {}},
    },
}


def get_current_time() -> str:
    now = datetime.now()
    out = {
        "success": True,
        "seconds": int(now.timestamp()),
        "milliseconds": int(now.timestamp() * 1000),
        "microseconds": int(now.timestamp() * 1_000_000),
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S.%f"),
        "message": "Current time retrieved successfully",
    }
    return json.dumps(out, ensure_ascii=False, indent=2)
