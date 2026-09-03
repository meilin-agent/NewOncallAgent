# AI 运维接口(对应 Go 版 chat_v1_ai_ops.go)
# 入参无字段,分析指令硬编码在后端(与 Go 版逐字一致),走 Plan-Execute-Replan 生成告警分析报告。

from internal.ai.agent.plan_execute_replan.plan_execute_replan import build_plan_agent
from utility.middleware.response import ok

# 硬编码任务指令(Go 版逐字原文,注意相邻字符串直接拼接、无分隔符)
_QUERY = (
    "1. 你是一个智能的服务告警分析助手,首先调用工具query_prometheus_alerts获取所有活跃的告警。"
    "2. 分别根据告警的名称调用工具query_internal_docs，获取告警名对应的处理方案。"
    "3. 完全遵循内部文档的内容进行查询和分析,不允许使用文档外的任何信息。"
    "4. 涉及到时间的参数都需要先通过工具get_current_time获取当前时间,再结合工具的时间要求进行传参。"
    "5. 涉及到日志的查询：如果日志查询工具可用，先通过日志工具获取相关日志信息，参数必须携带地域和日志主题；"
    "如果日志工具不可用，则跳过日志查询，基于已有的告警信息和内部文档完成分析。"
    "6. 分别将告警对应查询到的信息进行总结分析,最后生成告警运维分析报告，格式如下：\n"
    "告警分析报告\n"
    "---\n"
    "# 告警处理详情\n"
    "## 活跃告警清单\n"
    "## 告警根因分析N(第N个告警)\n"
    "## 处理方案执行N(第N个告警)\n"
    "## 结论\n"
)


def ai_ops() -> dict:
    result, detail = build_plan_agent(_QUERY)
    if result == "":
        raise ValueError("内部错误")
    return ok({"result": result, "detail": detail})
