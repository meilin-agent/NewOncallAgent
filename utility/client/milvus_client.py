# Milvus 客户端(对应 Go 版 utility/client/client.go)
# 启动自举:连 default 库 → 不存在则创建 agent 库 → 不存在则创建 biz collection
# (id VARCHAR 256 主键 autoID / vector FLOAT_VECTOR 768 / content VARCHAR 8192 / metadata JSON,
#  开启动态字段)→ 建索引(id=AUTOINDEX/L2,vector=HNSW/L2/M=16/efConstruction=64)→ LoadCollection。
# 注意:实际生效的向量距离度量是 L2(Go 版 indexer 配置的 COSINE 因表已存在从未生效)。

import logging
import threading

from pymilvus import DataType, MilvusClient

from utility.common import MilvusCollectionName, MilvusDBName

logger = logging.getLogger(__name__)

_URI = "http://localhost:19530"

# 进程级单例(线程安全)。修复:高频并发下频繁创建/关闭 MilvusClient 会触发 pymilvus
# 共享 gRPC channel 偶发 "closed channel"(LangGraph ToolNode 多线程工具调用后出现),
# 连接复用与 Go 版语义一致。
_client_singleton: MilvusClient | None = None
_client_lock = threading.Lock()


def _create_client() -> MilvusClient:
    """连接 agent 库的 Milvus 客户端,首次调用时完成建库建表建索引(幂等)"""
    # 1. 先连 default 库,确保 agent 数据库存在(不 close,避免关闭共享 channel)
    default = MilvusClient(uri=_URI)
    if MilvusDBName not in default.list_databases():
        default.create_database(MilvusDBName)
        logger.info("创建 Milvus 数据库: %s", MilvusDBName)

    # 2. 连接 agent 库,确保 biz collection 存在
    client = MilvusClient(uri=_URI, db_name=MilvusDBName)
    if not client.has_collection(MilvusCollectionName):
        schema = client.create_schema(auto_id=True, enable_dynamic_field=True)
        schema.add_field("id", DataType.VARCHAR, is_primary=True, max_length=256, auto_id=True)
        schema.add_field("vector", DataType.FLOAT_VECTOR, dim=768)
        schema.add_field("content", DataType.VARCHAR, max_length=8192)
        schema.add_field("metadata", DataType.JSON)
        client.create_collection(MilvusCollectionName, schema=schema)
        logger.info("创建 Milvus collection: %s", MilvusCollectionName)

        # 3. 建索引:id 用 AutoIndex(L2);vector 用 HNSW(L2, M=16, efConstruction=64)
        try:
            idx = client.prepare_index_params()
            idx.add_index(field_name="id", index_type="AUTOINDEX", metric_type="L2")
            idx.add_index(
                field_name="vector",
                index_type="HNSW",
                metric_type="L2",
                params={"M": 16, "efConstruction": 64},
            )
            client.create_index(MilvusCollectionName, idx)
        except Exception:
            # 部分 pymilvus 版本不允许标量字段带 metric_type,去掉后重试
            idx = client.prepare_index_params()
            idx.add_index(field_name="id", index_type="AUTOINDEX")
            idx.add_index(
                field_name="vector",
                index_type="HNSW",
                metric_type="L2",
                params={"M": 16, "efConstruction": 64},
            )
            client.create_index(MilvusCollectionName, idx)
        logger.info("Milvus 索引创建完成")

    # 4. 加载 collection 进内存(与 Go 版一致,幂等)
    client.load_collection(MilvusCollectionName)
    return client


def new_milvus_client() -> MilvusClient:
    """返回进程级单例的 Milvus 客户端(线程安全,首次调用完成建库自举)"""
    global _client_singleton
    with _client_lock:
        if _client_singleton is None:
            _client_singleton = _create_client()
        return _client_singleton
