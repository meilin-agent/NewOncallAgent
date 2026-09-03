# 向量编码器(对应 Go 版 internal/ai/embedder/embedder.go)
# OllamaEmbedding:nomic-embed-text 768 维,10s 超时。
# 失败返回错误由调用方降级处理(对应 Go 版修复:不能用 log.Fatal 炸掉整个进程)。

import httpx

from utility.config import cfg_get


def ollama_embedding(text: str) -> list[float]:
    """调用本地 Ollama /api/embed 将文本向量化,返回 768 维向量

    注意:禁用代理(对应 Go 启动脚本用 ProxyHandler({}) 预热模型的修复,
    httpx 默认 trust_env 会走系统代理导致本地请求被 302 到 https 代理)。
    """
    model = cfg_get("ollama_embedding_model.model", "nomic-embed-text")
    base_url = cfg_get("ollama_embedding_model.base_url", "http://localhost:11434")
    resp = httpx.post(
        f"{base_url}/api/embed",
        json={"model": model, "input": text},
        timeout=10,
        trust_env=False,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["embeddings"][0]
