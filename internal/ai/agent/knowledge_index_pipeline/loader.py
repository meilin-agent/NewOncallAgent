# 加载器薄封装(对应 Go 版 knowledge_index_pipeline/loader.go)

from internal.ai.loader.loader import load_file


def new_loader():
    return load_file
