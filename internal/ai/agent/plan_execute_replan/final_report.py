# 最终报告生成(对应 Go 版 plan_execute_replan/final_report.go)
# 兜底收尾:流程可能因模型未正确调用 respond 工具而中断在中间状态,
# 基于全部执行记录强制生成最终报告;每条记录截断 4000 字符;
# 生成失败/结果为空 → 返回 None,由调用方回退原始结果。

from internal.ai.models.open_ai import (
    QUICK_TEMPERATURE,
    QUICK_TOP_P,
    openai_for_deepseek_v3_quick,
)

TRUNCATE_LIMIT = 4000

SYSTEM_PROMPT = (
    "你是一个专业的运维告警分析助手，负责把 AI 自动排查过程的执行记录整理成结构清晰的中文"
    "分析报告。只基于给定的执行记录进行分析，不要编造不存在的告警或数据。"
)

USER_PROMPT = """以下是智能运维分析流程中产生的全部执行记录，请基于这些记录生成最终的中文告警分析报告。
报告结构要求：
1. 活跃告警清单（含告警名称、触发接口/指标、持续时间等可获取的信息）
2. 告警根因分析
3. 处理方案（引用执行记录中检索到的内部文档步骤）
4. 结论
如果执行记录中没有查询到任何活跃告警，请如实说明当前没有活跃告警，不要编造。"""


def generate_final_report(query: str, detail: list[str], fallback: str) -> str | None:
    """基于执行记录生成最终中文报告;detail 为空直接返回 None(镜像 Go:空 detail 直接返回 fallback)。

    失败或响应为空返回 None,由调用方回退到原始结果。
    """
    if not detail:
        return None

    records = []
    for i, d in enumerate(detail, start=1):
        text = d if len(d) <= TRUNCATE_LIMIT else d[:TRUNCATE_LIMIT] + "...(内容过长已截断)"
        records.append(f"【执行记录 {i}】\n{text}\n")

    user = USER_PROMPT + "\n\n" + "".join(records)

    try:
        client, model = openai_for_deepseek_v3_quick()
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            temperature=QUICK_TEMPERATURE,
            top_p=QUICK_TOP_P,
        )
        content = resp.choices[0].message.content
        if not content:
            return None
        return content
    except Exception:
        return None
