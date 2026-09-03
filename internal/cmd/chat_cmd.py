# CLI 冒烟:两轮对话测试(记忆)(对应 Go 版 internal/ai/cmd/chat_cmd/main.go)
# 第一轮介绍名字,第二轮验证记忆 + 安慰 + 当前时间(触发工具调用)。
# 用法:python internal/cmd/chat_cmd.py

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from internal.ai.agent.chat_pipeline.orchestration import run_chat_agent
from internal.ai.agent.chat_pipeline.user_message import UserMessage
from utility import mem
from utility.mem.mem import Message


def main():
    session_id = "111"
    rounds = [
        "你好，我叫nash",
        "还记得我叫啥吗？我现在心情很不好，你能不能安慰我一下？请问当前时间是多少？",
    ]
    for question in rounds:
        print(f"\n用户: {question}")
        um = UserMessage(id=session_id, query=question, history=mem.get_simple_memory(session_id).get_messages())
        answer = run_chat_agent(um)
        print(f"AI: {answer}")
        mem.get_simple_memory(session_id).set_messages(Message(role="user", content=question))
        mem.get_simple_memory(session_id).set_messages(Message(role="assistant", content=answer))


if __name__ == "__main__":
    main()
