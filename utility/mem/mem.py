# 会话内存管理(对应 Go 版 utility/mem/mem.go)
# 设计:基于会话 ID 的进程内内存缓存,滑动窗口最大 6 条消息,超出时成对(偶数)丢弃最旧消息,
# 保证 user/assistant 消息成对对齐。线程安全。

import threading
from dataclasses import dataclass, field


@dataclass
class Message:
    """镜像 Go 版 eino schema.Message(等价 OpenAI 消息结构)"""

    role: str  # user / assistant / tool / system
    content: str
    tool_calls: list = field(default_factory=list)  # [{id, name, arguments}]
    tool_call_id: str = ""
    tool_call_name: str = ""
    reasoning_content: str = ""

    def string(self) -> str:
        """镜像 Go 版 schema.Message.String():首行 "<role>: <content>",后续按序追加扩展字段。

        Go 版对 tool_calls 使用 Go 专属的 %+v 结构体格式,Python 侧用近似字符串镜像,
        仅供 detail 展示,非逐字符一致。
        """
        s = f"{self.role}: {self.content}"
        if self.reasoning_content:
            s += f"\nreasoning content:\n{self.reasoning_content}"
        if self.tool_calls:
            s += "\ntool_calls:\n"
            for i, tc in enumerate(self.tool_calls):
                # 近似 Go 的 %+v:{ID:xxx Index:0 Function:{Name:xxx Arguments:{...}} Extra:map[]}
                s += (
                    f"index[{i}]:{{ID:{tc.get('id', '')} Index:0 "
                    f"Function:{{Name:{tc.get('name', '')} Arguments:{tc.get('arguments', '')}}} Extra:map[]}}\n"
                )
        if self.tool_call_id:
            s += f"\ntool_call_id: {self.tool_call_id}"
        if self.tool_call_name:
            s += f"\ntool_call_name: {self.tool_call_name}"
        return s


class SimpleMemory:
    """单会话的滑动窗口内存"""

    def __init__(self, id_: str):
        self.id = id_
        self.messages: list[Message] = []
        self.max_window_size = 6  # 固定窗口大小(与 Go 版一致)
        self._mu = threading.Lock()

    def set_messages(self, msg: Message):
        """添加消息;超出窗口大小时从头部成对删除最旧消息(保持 user/assistant 对齐)"""
        with self._mu:
            self.messages.append(msg)
            if len(self.messages) > self.max_window_size:
                excess = len(self.messages) - self.max_window_size
                if excess % 2 != 0:
                    excess += 1  # 必须成对丢弃
                self.messages = self.messages[excess:]

    def get_messages(self) -> list[Message]:
        """返回深拷贝快照,防外部修改与数据竞争"""
        with self._mu:
            return [
                Message(
                    role=m.role,
                    content=m.content,
                    tool_calls=[dict(tc) for tc in m.tool_calls],
                    tool_call_id=m.tool_call_id,
                    tool_call_name=m.tool_call_name,
                    reasoning_content=m.reasoning_content,
                )
                for m in self.messages
            ]


# 全局会话缓存:id -> SimpleMemory(与 Go 版 SimpleMemoryMap 一致,无过期机制、无持久化)
_simple_memory_map: dict[str, SimpleMemory] = {}
_map_lock = threading.Lock()


def get_simple_memory(id_: str) -> SimpleMemory:
    """按会话 ID 获取内存,不存在则创建并缓存"""
    with _map_lock:
        mem = _simple_memory_map.get(id_)
        if mem is None:
            mem = SimpleMemory(id_)
            _simple_memory_map[id_] = mem
        return mem
