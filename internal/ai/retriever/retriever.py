# Milvus 检索器(对应 Go 版 internal/ai/retriever/retriever.go)
# 检索参数:collection "biz"、向量字段 vector、TopK=3、近似搜索、L2 距离、Ollama 向量编码。

import json

from internal.ai.embedder.embedder import ollama_embedding
from internal.ai.loader.loader import Document
from utility.client.milvus_client import new_milvus_client
from utility.common import MilvusCollectionName

TOPK = 3


class MilvusRetriever:
    def __init__(self):
        # 注意:Go 版每次调用都重建 Milvus 客户端并加载 collection,Python 版同样在
        # 构造时建连接(与 Go 行为一致,便于对照;如需优化可缓存)
        self.client = new_milvus_client()

    def retrieve(self, query: str) -> list[Document]:
        """向量相似度检索,返回 TopK=3 文档(score 放入 meta_data["_score"],镜像 Go 行为)"""
        vec = ollama_embedding(query)
        res = self.client.search(
            MilvusCollectionName,
            data=[vec],
            anns_field="vector",
            search_params={"metric_type": "L2", "params": {"ef": 64}},
            limit=TOPK,
            output_fields=["*"],
        )
        docs = []
        for hit in res[0]:
            entity = hit["entity"]
            md = entity.get("metadata") or {}
            if isinstance(md, str):
                md = json.loads(md)
            md = dict(md)
            md["_score"] = hit["distance"]
            docs.append(
                Document(
                    id=hit["id"],
                    content=entity.get("content", ""),
                    meta_data=md,
                )
            )
        return docs


def new_milvus_retriever() -> MilvusRetriever:
    return MilvusRetriever()
