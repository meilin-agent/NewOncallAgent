# 全局常量与通用工具(对应 Go 版 utility/common/common.go)

import json

MilvusDBName = "agent"   # Milvus 数据库名
MilvusCollectionName = "biz"  # collection 表名

# 上传文件/知识文档目录,默认值,启动时被 config.yaml 的 file_dir 覆盖(对应 main.go 中的逻辑)
FileDir = "./docs/"


def parse_json_tolerant(text: str):
    """容错解析 LLM 返回的 JSON。

    部分兼容端点(DashScope/qwen)偶发在 arguments 后附带多余字符导致 json.loads 抛
    "Extra data",这里用 raw_decode 取第一个完整 JSON 值,失败仍抛原异常。
    """
    if not text:
        raise ValueError("empty json text")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        obj, _ = decoder.raw_decode(text.lstrip())
        return obj

