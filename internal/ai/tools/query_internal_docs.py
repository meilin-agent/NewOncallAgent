# 内部文档 RAG 检索工具(对应 Go 版 internal/ai/tools/query_internal_docs.go)
# 每次调用走 Milvus 检索(TopK=3),返回文档列表 JSON。
# Go 版错误处理用了 log.Fatal(进程级炸弹),Python 版改为抛异常由上层处理。

import json

from internal.ai.retriever.retriever import new_milvus_retriever

TOOL_NAME = "query_internal_docs"

TOOL_DESCRIPTION = (
    "Use this tool to search internal documentation and knowledge base for relevant information. "
    "It performs RAG (Retrieval-Augmented Generation) to find similar documents and extract "
    "processing steps. This is useful when you need to understand internal procedures, best "
    "practices, or step-by-step guides stored in the company's documentation."
)

SPEC = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": TOOL_DESCRIPTION,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The query string to search in internal documentation for "
                    "relevant information and processing steps",
                }
            },
            "required": ["query"],
        },
    },
}


def query_internal_docs(args: dict) -> str:
    """RAG 检索内部文档,返回文档列表 JSON 字符串"""
    query = args.get("query", "")
    rr = new_milvus_retriever()
    docs = rr.retrieve(query)
    return json.dumps([d.to_dict() for d in docs], ensure_ascii=False)
