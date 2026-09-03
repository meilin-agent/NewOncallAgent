# Markdown 标题切分测试(对应 Go 版 transformer_test.go,2 个用例)

import uuid

from internal.ai.agent.knowledge_index_pipeline.transformer import split_markdown
from internal.ai.loader.loader import Document


def _doc(content: str) -> Document:
    return Document(id="orig", content=content, meta_data={"_source": "docs/x.md", "_file_name": "x.md"})


def test_split_by_markdown_headers():
    """两个 # 标题段落 → 2 个文档,title 为标题文本,id 为 UUID 格式"""
    text = "# 服务下线\n\n服务下线通常由网络故障引起。\n\n# 接口失败率过高\n\n可能是代码缺陷导致。"
    docs = split_markdown(_doc(text))
    assert len(docs) == 2
    assert docs[0].meta_data["title"] == "服务下线"
    assert docs[1].meta_data["title"] == "接口失败率过高"
    for d in docs:
        uuid.UUID(d.id)  # id 为合法 UUID
        assert d.meta_data["_source"] == "docs/x.md"  # 继承原文档元数据


def test_no_headers_keeps_single_chunk():
    """无标题文档保持 1 个 chunk 且无 title 元数据"""
    docs = split_markdown(_doc("这是没有标题的文档内容\n只有普通文本。"))
    assert len(docs) == 1
    assert "title" not in docs[0].meta_data
    assert "这是没有标题的文档内容" in docs[0].content
