# 两个 Lambda 节点(对应 Go 版 chat_pipeline/lambda_func.go)
# InputToRag:取 Query 作为检索串;InputToChat:拼装模板变量 {content, history, date}。

from datetime import datetime

from internal.ai.agent.chat_pipeline.user_message import UserMessage


def input_to_rag(um: UserMessage) -> str:
    """镜像 newInputToRagLambda:输出 input.Query"""
    return um.query


def input_to_chat(um: UserMessage) -> dict:
    """镜像 newInputToChatLambda:输出 {content, history, date}(date 格式镜像 Go 的 2006-01-02 15:04:05)"""
    return {
        "content": um.query,
        "history": um.history,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
