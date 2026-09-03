# 文件上传接口(对应 Go 版 chat_v1_file_upload.go)
# multipart 字段名 file,保存到 file_dir(默认 ./docs),随后同步构建知识库索引
# (按 metadata["_source"] 删旧再重建,实现覆盖式更新)。
# 与 Go 版差异(已确认的修复):返回真实文件路径与文件字节数(Go 版返回的是目录路径、大小恒 0)。

import logging
import os
from pathlib import Path

from fastapi import UploadFile

from internal.ai.agent.knowledge_index_pipeline.orchestration import build_knowledge_indexing
from internal.ai.indexer.indexer import delete_by_source
from internal.ai.loader.loader import load_file
from utility import common
from utility.client.milvus_client import new_milvus_client
from utility.middleware.response import ok

logger = logging.getLogger(__name__)


def build_into_index(path: str) -> list[str]:
    """加载文档 → 按 _source 删旧数据 → 重建索引(镜像 Go buildIntoIndex)"""
    doc = load_file(path)
    source = doc.meta_data["_source"]

    client = new_milvus_client()
    try:
        deleted = delete_by_source(client, source)
        if deleted:
            logger.info("删除同源旧数据 %d 条: %s", deleted, source)
    except Exception as e:  # 删除失败只告警不中断(镜像 Go [warn] 行为)
        logger.warning("[warn] delete old index data failed: %s", e)

    return build_knowledge_indexing(path)


def file_upload(file: UploadFile | None) -> dict:
    if file is None:
        raise ValueError("请上传文件")

    file_dir = common.FileDir
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)

    content = file.file.read()
    save_path = os.path.join(file_dir, file.filename)
    with open(save_path, "wb") as f:
        f.write(content)

    uri = Path(save_path).as_posix()  # 正斜杠路径(与 loader 的 _source 一致,保证删旧命中)

    build_into_index(uri)

    return ok(
        {
            "fileName": file.filename,
            "filePath": uri,
            "fileSize": len(content),
        }
    )
