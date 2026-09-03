# CLI 冒烟:模型+工具绑定测试(对应 Go 版 internal/ai/cmd/llm_tool_cmd/main.go)
# 用 think 模型 + MCP/mysql/time 工具,问"告诉我你有哪些工具可以使用"。
# 用法:python internal/cmd/llm_tool_cmd.py

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from internal.ai.models.open_ai import openai_for_deepseek_v31_think
from internal.ai.tools import get_current_time, mysql_crud
from internal.ai.tools.query_log import get_log_mcp_tools


def main():
    client, model = openai_for_deepseek_v31_think()

    specs = []
    try:
        mcp_specs, mcp_client = get_log_mcp_tools()
        specs.extend(mcp_specs)
        mcp_client.close()
    except Exception as e:
        print(f"[warn] MCP 工具不可用: {e}")
    specs.append(mysql_crud.SPEC)
    specs.append(get_current_time.SPEC)

    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "告诉我你有哪些工具可以使用"}],
        tools=specs,
        tool_choice="required",
    )
    msg = resp.choices[0].message
    for tc in msg.tool_calls or []:
        print(f"工具: {tc.function.name}")
        print(json.dumps(json.loads(tc.function.arguments or "{}"), ensure_ascii=False, indent=2))
    if msg.content:
        print(msg.content)


if __name__ == "__main__":
    main()
