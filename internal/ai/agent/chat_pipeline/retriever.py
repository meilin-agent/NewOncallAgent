# 检索器薄封装(对应 Go 版 chat_pipeline/retriever.go)

from internal.ai.retriever.retriever import new_milvus_retriever


def new_retriever():
    return new_milvus_retriever()
