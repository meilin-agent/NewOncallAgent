# 节点日志回调(对应 Go 版 utility/log_call_back/log_call_back.go)
# 镜像 Eino 回调日志格式 [view start]:[Component:Type:Name] / [view end]:[...],
# 便于与 Go 版并跑对照。纯控制台日志,无业务影响。

import json
import logging

logger = logging.getLogger("log_call_back")


def _dump(v) -> str:
    if v is None:
        return ""
    try:
        return json.dumps(v, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(v)


def log_start(component: str, node_type: str, node_name: str, node_input=None):
    """节点开始:镜像 [view start]:[Component:Type:Name] + 输入 JSON"""
    logger.info("[view start]:[%s:%s:%s]", component, node_type, node_name)
    if node_input is not None:
        logger.info("  input: %s", _dump(node_input))


def log_end(component: str, node_type: str, node_name: str, node_output=None):
    """节点结束"""
    logger.info("[view end]:[%s:%s:%s]", component, node_type, node_name)
    if node_output is not None:
        logger.info("  output: %s", _dump(node_output))
