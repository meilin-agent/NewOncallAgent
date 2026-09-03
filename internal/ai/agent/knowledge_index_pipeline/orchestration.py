# 知识库构建流水线(对应 Go 版 knowledge_index_pipeline/orchestration.go)
# 图结构:FileLoader → MarkdownSplitter → MilvusIndexer(AnyPredecessor 触发模式),
# 输入为文件 URI,输出为写入 Milvus 后生成的自增 id 列表。

from internal.ai.agent.knowledge_index_pipeline.indexer import new_indexer
from internal.ai.agent.knowledge_index_pipeline.loader import new_loader
from internal.ai.agent.knowledge_index_pipeline.transformer import split_markdown
from internal.ai.loader.loader import Document


def build_knowledge_indexing(source_uri: str) -> list[str]:
    """加载文件 → 按标题切分 → 向量化入 Milvus,返回写入的 id 列表"""
    loader = new_loader()
    doc: Document = loader(source_uri)
    chunks = split_markdown(doc)
    return new_indexer()(chunks)
