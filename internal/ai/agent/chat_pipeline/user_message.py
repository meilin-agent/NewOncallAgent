# 图输入结构(对应 Go 版 chat_pipeline/user_message.go)

from dataclasses import dataclass, field

from utility.mem.mem import Message


@dataclass
class UserMessage:
    id: str
    query: str
    history: list[Message] = field(default_factory=list)
