# CLI 冒烟:批量建库脚本(对应 Go 版 internal/ai/cmd/knowledge_cmd/main.go)
# 遍历 ./docs 下所有 .md 文件,逐个按 _source 删旧数据后重建索引。
# 用法:python internal/cmd/knowledge_cmd.py

import sys
from pathlib import Path

# 保证从项目根目录能直接运行(镜像 Go 的 import 语义)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from internal.ai.agent.knowledge_index_pipeline.orchestration import build_knowledge_indexing
from internal.ai.indexer.indexer import delete_by_source
from internal.ai.loader.loader import load_file
from internal.ai.retriever.retriever import new_milvus_retriever
from utility import common
from utility.client.milvus_client import new_milvus_client


def main():
    docs_dir = Path(common.FileDir)
    if not docs_dir.exists():
        print(f"[x] 目录不存在: {docs_dir}")
        return

    md_files = sorted(docs_dir.glob("*.md"))
    if not md_files:
        print(f"[!] {docs_dir} 下没有 .md 文件")
        return

    client = new_milvus_client()
    total = 0
    for p in md_files:
        uri = p.as_posix()
        doc = load_file(uri)
        deleted = delete_by_source(client, doc.meta_data["_source"])
        ids = build_knowledge_indexing(uri)
        print(f"[ok] {p.name}: 删除旧数据 {deleted} 条,写入 {len(ids)} 个分块")
        total += len(ids)
    print(f"完成,共写入 {total} 个分块")

    # 顺便打印一次检索召回验证(对应 recall_cmd 的用途)
    docs = new_milvus_retriever().retrieve("服务下线是什么原因")
    print(f"\n检索验证 '服务下线是什么原因' 召回 {len(docs)} 条:")
    for d in docs:
        print("-", d.content[:80].replace("\n", " "))


if __name__ == "__main__":
    main()
