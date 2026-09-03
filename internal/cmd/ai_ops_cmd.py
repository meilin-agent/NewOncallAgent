# CLI 冒烟:AIOps 冒烟测试(对应 Go 版 internal/ai/cmd/ai_ops_cmd/main.go)
# 用法:python internal/cmd/ai_ops_cmd.py

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from internal.ai.agent.plan_execute_replan.plan_execute_replan import build_plan_agent

# cmd 版任务指令(与 HTTP 版略有差别,镜像 Go 的 cmd 版)
QUERY = (
    "1. 你是一个智能的服务告警运维分析助手,首先调用工具query_prometheus_alerts获取所有活跃的告警。"
    "2. 分别根据告警的名称调用工具query_internal_docs，获取告警名对应的处理方案。"
    "3. 完全遵循内部文档的内容进行查询和分析,不允许使用文档外的任何信息。"
    "4. 涉及到时间的参数都需要先通过工具get_current_time获取当前时间,再结合用户的时间要求进行传参。"
    "5. 涉及到日志的查询,需要先通过日志工具获取相关日志信息，参数必须携带地域和日志主题。"
    "6. 分别将告警对应查询到的信息进行总结分析,最后汇总所有告警和总结。"
)


def main():
    result, detail = build_plan_agent(QUERY)
    print("=" * 60)
    print("detail 共", len(detail), "条")
    for i, d in enumerate(detail, start=1):
        print(f"--- 步骤 {i} ---")
        print(d[:2000])
    print("=" * 60)
    print("最终报告:")
    print(result)


if __name__ == "__main__":
    main()
