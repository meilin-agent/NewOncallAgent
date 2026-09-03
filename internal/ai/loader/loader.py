# 文件加载器(对应 Go 版 eino-ext FileLoader:读单文件,写入 _file_name/_extension/_source 元数据)
# _source 统一为正斜杠路径(对应 Go 修复:Windows 反斜杠会导致 Milvus 过滤表达式解析失败)。

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Document:
    """镜像 Go 版 eino schema.Document(id/content/meta_data)"""

    id: str = ""
    content: str = ""
    meta_data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"id": self.id, "content": self.content, "meta_data": self.meta_data}


def load_file(uri: str) -> Document:
    """读取单个文件,返回文档对象"""
    p = Path(uri)
    content = p.read_text(encoding="utf-8", errors="replace")
    meta_data = {
        "_file_name": p.name,
        "_extension": p.suffix.lstrip("."),
        "_source": Path(uri).as_posix(),
    }
    return Document(id="", content=content, meta_data=meta_data)
