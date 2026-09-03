# 模型薄封装(对应 Go 版 chat_pipeline/model.go):newChatModel → quick 模型
# LangGraph 重构后返回 langchain_openai ChatOpenAI(可 bind_tools)。

from internal.ai.models.open_ai import chat_openai_quick


def new_chat_model():
    return chat_openai_quick()
