# Prometheus 告警查询工具(对应 Go 版 internal/ai/tools/query_metrics_alerts.go)
# 工具名:query_prometheus_alerts。GET http://127.0.0.1:9090/api/v1/alerts,10s 超时,
# 按 alertname 去重只保留第一条,duration 由 activeAt 计算。

import json
from datetime import datetime, timezone

import httpx

TOOL_NAME = "query_prometheus_alerts"

TOOL_DESCRIPTION = (
    "Query active alerts from Prometheus alerting system. This tool retrieves all currently "
    "active/firing alerts including their labels, annotations, state, and values. Use this tool "
    "when you need to check what alerts are currently firing, investigate alert conditions, or "
    "monitor alert status."
)

SPEC = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": TOOL_DESCRIPTION,
        "parameters": {"type": "object", "properties": {}},
    },
}

_BASE_URL = "http://127.0.0.1:9090"


def _calculate_duration(active_at: str) -> str:
    """自 activeAt 至今的时长,格式 XhXmXs / XmXs / Xs(镜像 Go calculateDuration)"""
    try:
        at = datetime.fromisoformat(active_at.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - at
        total = int(delta.total_seconds())
        if total < 0:
            total = 0
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        if h > 0:
            return f"{h}h{m}m{s}s"
        if m > 0:
            return f"{m}m{s}s"
        return f"{s}s"
    except (ValueError, AttributeError):
        return ""


def query_prometheus_alerts() -> str:
    """查询活跃告警,返回 JSON 字符串;失败抛异常(镜像 Go tools node:工具报错 → agent 失败)"""
    try:
        resp = httpx.get(f"{_BASE_URL}/api/v1/alerts", timeout=10, trust_env=False)
        resp.raise_for_status()
        data = resp.json()
        alerts = data.get("data", {}).get("alerts", [])
    except Exception as e:
        out = {"success": False, "error": str(e), "message": "Failed to query Prometheus alerts"}
        raise RuntimeError(json.dumps(out, ensure_ascii=False)) from e

    seen: set[str] = set()
    simplified = []
    for a in alerts:
        labels = a.get("labels") or {}
        name = labels.get("alertname", "")
        if name in seen:
            continue
        seen.add(name)
        simplified.append(
            {
                "alert_name": name,
                "description": (a.get("annotations") or {}).get("description", ""),
                "state": a.get("state", ""),
                "active_at": a.get("activeAt", ""),
                "duration": _calculate_duration(a.get("activeAt", "")),
            }
        )
    out = {"success": True, "alerts": simplified}
    return json.dumps(out, ensure_ascii=False)
