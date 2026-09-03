# Milvus 检索集成测试(对应 Go 版 retriever_test.go)
# Milvus 不可达(或 Ollama 未启动)时自动 skip,不阻塞离线测试。

import socket

import pytest


def _probe_milvus() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 19530), timeout=1):
            return True
    except OSError:
        return False

milvus_reachable = pytest.mark.skipif(
    not _probe_milvus(),
    reason="Milvus not reachable at localhost:19530, integration test skipped",
)


@milvus_reachable
def test_retrieve_returns_documents():
    """检索"服务下线"应返回文档(需先跑 knowledge_cmd 建库)"""
    from internal.ai.retriever.retriever import new_milvus_retriever

    rr = new_milvus_retriever()
    docs = rr.retrieve("服务下线是什么原因")
    assert isinstance(docs, list)
    # 库可能是空的,但检索调用本身不应报错
    for d in docs:
        assert d.content
        assert "_score" in d.meta_data
