# 服务入口(对应 Go 版 main.go)
# 启动流程镜像 Go 版:读取 config.yaml 的 file_dir → 覆盖 common.FileDir(缺失则报错)→
# 创建 FastAPI → CORS 中间件 + 统一响应异常处理器 → 注册 /api 下 4 个路由 + /api.json 桩 → 端口 6872。

import logging

import uvicorn
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from api.chat.v1.chat import ChatReq, ChatStreamReq
from internal.controller.chat import chat_v1_ai_ops, chat_v1_chat, chat_v1_chat_stream, chat_v1_file_upload
from utility import common
from utility.config import cfg_get, load_config
from utility.middleware.response import register_exception_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def create_app() -> FastAPI:
    # 1. 读配置(镜像 main.go:file_dir 缺失直接报错退出)
    load_config()
    file_dir = cfg_get("file_dir")
    if file_dir is None:
        raise RuntimeError("config.yaml 缺少 file_dir 配置")
    common.FileDir = file_dir

    # 2. 创建 HTTP 服务
    app = FastAPI(title="OncallAgent")

    # 3. 中间件:CORS(镜像 Go CORSMiddleware)+ 统一响应异常处理器
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)

    # 4. 路由(镜像 Go /api 路由组)
    @app.post("/api/chat")
    def route_chat(req: ChatReq):
        return chat_v1_chat.chat(req)

    @app.post("/api/chat_stream")
    def route_chat_stream(req: ChatStreamReq):
        return chat_v1_chat_stream.chat_stream(req)

    @app.post("/api/upload")
    def route_upload(file: UploadFile | None = File(None)):
        return chat_v1_file_upload.file_upload(file)

    @app.post("/api/ai_ops")
    def route_ai_ops():
        return chat_v1_ai_ops.ai_ops()

    # /api.json 桩:start-oncall.bat 的后端就绪健康检查依赖此路径(Go 版为 GoFrame OpenAPI)
    @app.get("/api.json")
    def route_openapi():
        return {"openapi": "3.0.0", "info": {"title": "OncallAgent", "version": "1.0.0"}}

    return app


app = create_app()

if __name__ == "__main__":
    # 端口 6872 与 Go 版一致
    uvicorn.run(app, host="0.0.0.0", port=6872)
