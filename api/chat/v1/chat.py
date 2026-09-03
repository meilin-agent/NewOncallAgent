# 接口请求/响应模型(对应 Go 版 api/chat/v1/chat.go)
#
# 注意:Go 版 ChatReq/ChatStreamReq 的字段没有 json tag,GoFrame 按字段名原样反序列化,
# 前端契约发送的是首字母大写的 {"Id": ..., "Question": ...}(见 frontend/app.js),
# 因此 Python 侧字段名直接大写保持一致。响应结构有 json tag,为小写驼峰。

from pydantic import BaseModel


class ChatReq(BaseModel):
    Id: str = ""  # 会话ID,用于关联聊天历史(默认空串镜像 Go 零值语义)
    Question: str = ""  # 用户提问内容


class ChatRes(BaseModel):
    answer: str = ""  # AI最终回答文本


class ChatStreamReq(BaseModel):
    Id: str = ""
    Question: str = ""


class ChatStreamRes(BaseModel):
    pass  # 流式响应走 SSE,无 JSON 响应体


class FileUploadRes(BaseModel):
    fileName: str = ""  # 保存的文件名
    filePath: str = ""  # 文件保存路径
    fileSize: int = 0  # 文件大小(字节)


class AIOpsReq(BaseModel):
    pass  # 无请求体字段,分析指令硬编码在后端


class AIOpsRes(BaseModel):
    result: str = ""  # AI运维分析结果文本
    detail: list[str] = []  # 详细执行步骤或中间输出
