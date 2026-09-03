# CLI 冒烟:检索召回测试(对应 Go 版 internal/ai/cmd/recall_cmd/main.go)
# 用法:python internal/cmd/recall_cmd.py [查询串]

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from internal.ai.retriever.retriever import new_milvus_retriever


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else "服务下线是什么原因"
    docs = new_milvus_retriever().retrieve(query)
    print(f"检索 '{query}' 召回 {len(docs)} 条:")
    for d in docs:
        print("=" * 60)
        print(d.content)


if __name__ == "__main__":
    main()
