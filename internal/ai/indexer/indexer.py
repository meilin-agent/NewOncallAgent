# Milvus 索引器(对应 Go 版 internal/ai/indexer/indexer.go)
# 向量化 + Upsert 写入。注意:collection 的 id 是 autoID 主键,pymilvus 禁止在实体里传 id 字段
# (Go 版显式传的 id 被服务端忽略),分块 UUID 仅作为文档对象的 id,不落库。

from internal.ai.embedder.embedder import ollama_embedding
from internal.ai.loader.loader import Document
from utility.client.milvus_client import new_milvus_client
from utility.common import MilvusCollectionName


def index_documents(docs: list[Document]) -> list[str]:
    """向量化每个文档并写入 Milvus,返回服务端生成的自增 id 列表(字符串)"""
    if not docs:
        return []
    client = new_milvus_client()
    rows = []
    for doc in docs:
        vec = ollama_embedding(doc.content)
        rows.append(
            {
                "content": doc.content,
                "metadata": doc.meta_data,
                "vector": vec,
            }
        )
    res = client.insert(MilvusCollectionName, rows)
    return [str(x) for x in res["ids"]]


def delete_by_source(client, source: str) -> int:
    """按 metadata["_source"] == source 删除旧数据(上传覆盖更新的机制),返回删除条数。

    注意:source 必须是正斜杠路径(Windows 下需 Path.as_posix 规范化)。
    """
    expr = f'metadata["_source"] == "{source}"'
    rows = client.query(MilvusCollectionName, filter=expr, output_fields=["id"])
    ids = [r["id"] for r in rows]
    if ids:
        client.delete(MilvusCollectionName, ids=ids)
    return len(ids)
