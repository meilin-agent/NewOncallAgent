# 模型客户端工厂(对应 Go 版 internal/ai/models/open_ai.go)
#
# 函数名保留 Go 版的 "DeepSeek" 历史命名,实际配置指向阿里百炼 DashScope 兼容模式
# (qwen-max),统一走 OpenAI 兼容 SDK。配置键结构不变:
#   ds_think_chat_model.{model, api_key, base_url}  — Planner/Replanner 用,无采样参数
#   ds_quick_chat_model.{model, api_key, base_url}  — Chat/Executor/FinalReport 用,temperature=0.3, top_p=0.9
#
# LangGraph 重构后,Agent 编排层统一走 langchain_openai ChatOpenAI(bind_tools / invoke),
# 原生 openai OpenAI 客户端保留给 final_report、cmd 冒烟脚本等非编排调用使用。

from openai import OpenAI

from utility.config import cfg_get

# quick 模型的采样参数(集中定义,ReAct 与 final_report 共用)
QUICK_TEMPERATURE = 0.3
QUICK_TOP_P = 0.9


def _new_client(cfg_key: str) -> OpenAI:
    api_key = cfg_get(f"{cfg_key}.api_key", "")
    base_url = cfg_get(f"{cfg_key}.base_url", "")
    if not api_key:
        raise ValueError(f"配置缺失:{cfg_key}.api_key 为空,请检查 manifest/config/config.yaml")
    return OpenAI(api_key=api_key, base_url=base_url)


def _new_chat_openai(cfg_key: str, temperature: float | None = None, top_p: float | None = None):
    """返回 langchain_openai ChatOpenAI(供 LangGraph bind_tools / invoke 使用)"""
    from langchain_openai import ChatOpenAI

    api_key = cfg_get(f"{cfg_key}.api_key", "")
    base_url = cfg_get(f"{cfg_key}.base_url", "")
    model = cfg_get(f"{cfg_key}.model", "")
    if not api_key:
        raise ValueError(f"配置缺失:{cfg_key}.api_key 为空,请检查 manifest/config/config.yaml")
    kwargs = {"model": model, "api_key": api_key, "base_url": base_url}
    if temperature is not None:
        kwargs["temperature"] = temperature
    if top_p is not None:
        kwargs["top_p"] = top_p
    return ChatOpenAI(**kwargs)


def openai_for_deepseek_v31_think() -> tuple[OpenAI, str]:
    """think 模型(原生 OpenAI 客户端,Planner/Replanner 的 cmd 调试等用途)"""
    return _new_client("ds_think_chat_model"), cfg_get("ds_think_chat_model.model", "")


def openai_for_deepseek_v3_quick() -> tuple[OpenAI, str]:
    """quick 模型(原生 OpenAI 客户端,FinalReport 用)"""
    return _new_client("ds_quick_chat_model"), cfg_get("ds_quick_chat_model.model", "")


def chat_openai_think():
    """LangGraph 版 think 模型:Planner / Replanner 用(无采样参数,与 Go 版一致)"""
    return _new_chat_openai("ds_think_chat_model")


def chat_openai_quick():
    """LangGraph 版 quick 模型:Chat Agent / Executor 用(temperature=0.3, top_p=0.9)"""
    return _new_chat_openai("ds_quick_chat_model", temperature=QUICK_TEMPERATURE, top_p=QUICK_TOP_P)
