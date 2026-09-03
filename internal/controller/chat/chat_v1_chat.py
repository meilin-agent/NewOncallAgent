# 快速对话接口(对应 Go 版 chat_v1_chat.go)
# 调用链:内存历史 → UserMessage{ID, Query, History} → BuildChatAgent → Invoke → 写回内存 → answer

from api.chat.v1.chat import ChatReq
from internal.ai.agent.chat_pipeline.orchestration import run_chat_agent
from internal.ai.agent.chat_pipeline.user_message import UserMessage
from utility import mem
from utility.mem.mem import Message
from utility.middleware.response import ok


def chat(req: ChatReq) -> dict:
    user_message = UserMessage(
        id=req.Id,
        query=req.Question,
        history=mem.get_simple_memory(req.Id).get_messages(),
    )

    answer = run_chat_agent(user_message)

    # 用户消息与AI回复存入会话内存(一问一答成对写入)
    mem.get_simple_memory(req.Id).set_messages(Message(role="user", content=req.Question))
    mem.get_simple_memory(req.Id).set_messages(Message(role="assistant", content=answer))

    return ok({"answer": answer})
