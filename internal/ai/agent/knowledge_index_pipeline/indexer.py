# 索引器薄封装(对应 Go 版 knowledge_index_pipeline/indexer.go)

from internal.ai.indexer.indexer import index_documents


def new_indexer():
    return index_documents
