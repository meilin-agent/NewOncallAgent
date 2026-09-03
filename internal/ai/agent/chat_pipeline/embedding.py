# 向量编码薄封装(对应 Go 版 chat_pipeline/embedding.go,本包内实际未被图引用)

from internal.ai.embedder.embedder import ollama_embedding


def new_embedding():
    return ollama_embedding
