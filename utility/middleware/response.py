# 统一响应格式(对应 Go 版 utility/middleware/middleware.go)
#
# Go 版 ResponseMiddleware 行为:handler 返回后,成功时包成 {"message":"OK","data":<payload>},
# 出错时(message = err.Error())也返回 HTTP 200 + {"message":"<错误文本>","data":null}。
# Python 侧用"handler 内显式 ok() 包装 + 全局异常处理器"实现等价语义;
# SSE 端点返回 StreamingResponse,天然不经过 JSON 包装(豁免)。

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def ok(data=None) -> dict:
    """成功响应外壳:{"message": "OK", "data": <payload>}"""
    return {"message": "OK", "data": data}


def register_exception_handlers(app: FastAPI):
    """业务异常/参数校验错误一律转成 HTTP 200 的 {"message","data"} 外壳(镜像 Go 语义)"""

    async def on_exception(request: Request, exc: Exception):
        return JSONResponse({"message": str(exc), "data": None}, status_code=200)

    async def on_validation_error(request: Request, exc: RequestValidationError):
        # Go 版对缺失字段用零值不报错;这里兜底统一为 200 错误外壳
        return JSONResponse({"message": str(exc), "data": None}, status_code=200)

    app.add_exception_handler(Exception, on_exception)
    app.add_exception_handler(RequestValidationError, on_validation_error)
