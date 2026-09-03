# 对话 Agent 流水线(LangGraph 重构版,对应 Go 版 chat_pipeline/orchestration.go)
# 架构:RAG 预检索渲染初始消息 → ReAct LangGraph 图(agent + tools 循环)
# 图结构语义与 Go 版 Eino 一致:
#   START → (InputToRag → MilvusRetriever) → ChatTemplate → ReactAgent → END
# 在 LangGraph 中表现为:先执行 RAG 检索并把文档渲染进 system prompt,
# 再把 [system + history + user] 作为初始消息交给 ReAct 图。

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from internal.ai.agent.chat_pipeline.lambda_func import input_to_chat, input_to_rag
from internal.ai.agent.chat_pipeline.model import new_chat_model
from internal.ai.agent.chat_pipeline.prompt import SYSTEM_PROMPT
from internal.ai.agent.chat_pipeline.react_agent import run_react
from internal.ai.agent.chat_pipeline.retriever import new_retriever
from internal.ai.agent.chat_pipeline.tools_node import chat_tool_list
from internal.ai.agent.chat_pipeline.user_message import UserMessage


def _render_documents(docs) -> str:
    """镜像 Go 版 fmt %v 对 []*Document 的渲染:[chunk1 chunk2 chunk3](空格 join、带方括号)"""
    return "[" + " ".join(d.content for d in docs) + "]"


def _to_langchain_message(msg) -> BaseMessage:
    """mem 的会话历史消息 → LangChain 消息(历史只存 user/assistant 纯文本,见 chat controller)"""
    if msg.role == "assistant":
        return AIMessage(content=msg.content)
    return HumanMessage(content=msg.content)


def _build_messages_langchain(um: UserMessage, documents: str) -> list[BaseMessage]:
    """模板渲染(对应 Go 版 ChatTemplate):[system(prompt+date+documents), ...history, user]"""
    ctx = input_to_chat(um)
    system = SYSTEM_PROMPT.replace("{date}", ctx["date"]).replace("{documents}", documents)
    messages: list[BaseMessage] = [SystemMessage(content=system)]
    for h in ctx["history"]:
        messages.append(_to_langchain_message(h))
    messages.append(HumanMessage(content=ctx["content"]))
    return messages


def run_chat_agent(
    user_message: UserMessage,
    stream: bool = False,
    on_chunk=None,
) -> str:
    """执行完整对话流水线,返回最终回答文本。stream=True 时文本增量经 on_chunk 回调输出。"""
    # 边:START → InputToRag → MilvusRetriever
    query = input_to_rag(user_message)
    docs = new_retriever().retrieve(query)
    documents = _render_documents(docs)

    # ChatTemplate 渲染初始消息
    messages = _build_messages_langchain(user_message, documents)

    # ReactAgent(LangGraph ReAct 图)
    return run_react(
        messages,
        model=new_chat_model().bind_tools(chat_tool_list()),
        tools=chat_tool_list(),
        stream=stream,
        on_chunk=on_chunk,
    )
