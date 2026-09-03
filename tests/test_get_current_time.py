# 当前时间工具测试(对应 Go 版 get_current_time_test.go,2 个用例)
# 覆盖:工具名称、秒/毫秒/微秒时间戳自洽性。

import json
import time

from internal.ai.tools import get_current_time


def test_tool_name():
    assert get_current_time.TOOL_NAME == "get_current_time"
    assert get_current_time.SPEC["function"]["name"] == "get_current_time"


def test_timestamps_consistent():
    """秒/毫秒/微秒互相自洽,且 timestamp 格式为 YYYY-MM-DD HH:MM:SS.microseconds"""
    out = json.loads(get_current_time.get_current_time())
    assert out["success"] is True
    now_s = int(time.time())
    # 毫秒 = 秒*1000 + 微秒余数修正,允许 1 秒内的偏差(两次取系统时间)
    assert abs(out["seconds"] - now_s) <= 1
    assert out["milliseconds"] // 1000 in (out["seconds"], out["seconds"] - 1)
    assert out["microseconds"] // 1000000 in (out["seconds"], out["seconds"] - 1)
    assert abs(out["milliseconds"] * 1000 - out["microseconds"]) < 500_000
    # 格式化时间戳校验
    assert len(out["timestamp"]) == 26  # "YYYY-MM-DD HH:MM:SS.microseconds"
    assert out["timestamp"][4] == "-" and out["timestamp"][10] == " " and out["timestamp"][19] == "."
