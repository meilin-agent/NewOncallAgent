# 配置加载(对应 Go 版 GoFrame 的 g.Cfg(),读取 manifest/config/config.yaml)
# 顶层 key 与 Go 版完全一致:server / logger / ds_think_chat_model / ds_quick_chat_model /
# doubao_embedding_model / ollama_embedding_model / file_dir
# Python 版新增一个可选 key:log_mcp_url(日志 MCP 地址,Go 版硬编码在代码里)

import threading
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

_config: dict | None = None
_lock = threading.Lock()


def load_config(path: str | Path | None = None) -> dict:
    """加载 config.yaml(进程内缓存,与 Go 版启动时读取一次的语义一致)"""
    global _config
    with _lock:
        if _config is None:
            p = Path(path) if path else PROJECT_ROOT / "manifest" / "config" / "config.yaml"
            with open(p, "r", encoding="utf-8") as f:
                _config = yaml.safe_load(f) or {}
        return _config


def cfg_get(key: str, default=None):
    """按点分隔 key 取值,如 cfg_get("ds_quick_chat_model.api_key")"""
    cur = load_config()
    for part in key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur
