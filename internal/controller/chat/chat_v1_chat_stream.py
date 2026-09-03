# 流式对话接口(对应 Go 版 chat_v1_chat_stream.go)
# SSE 协议:握手 connected → 每个增量 chunk 一条 message → 流结束发 done(data 固定 "Stream completed");
# 异常发 error。完整回复在收尾时(非空)成对写回会话内存(镜像 Go 的 defer 语义:error 路径也写)。
# SSE 端点返回 StreamingResponse,不经过统一 JSON 包装(豁免)。

import queue
import threading

from fastapi.responses import StreamingResponse

from api.chat.v1.chat import ChatStreamReq
from internal.ai.agent.chat_pipeline.orchestration import run_chat_agent
from internal.ai.agent.chat_pipeline.user_message import UserMessage
from internal.logic.sse.sse import connected_block, done_line, error_line, message_line
from utility import mem
from utility.mem.mem import Message


def chat_stream(req: ChatStreamReq) -> StreamingResponse:
    user_message = UserMessage(
        id=req.Id,
        query=req.Question,
        history=mem.get_simple_memory(req.Id).get_messages(),
    )

    def gen():
        yield connected_block(req.Id)

        full_parts: list[str] = []
        q: queue.Queue = queue.Queue()

        def _on_chunk(c: str):
            full_parts.append(c)
            q.put(c)

        def _run():
            try:
                run_chat_agent(user_message, stream=True, on_chunk=_on_chunk)
                q.put(None)  # 正常结束标记
            except Exception as e:  # noqa: BLE001
                q.put(e)

        # LLM 调用在子线程执行,生成器逐段 yield 增量(镜像 Go 同步直写+Flush 的效果)
        t = threading.Thread(target=_run, daemon=True)
        t.start()

        try:
            while True:
                item = q.get()
                if item is None:
                    break
                if isinstance(item, Exception):
                    raise item
                yield message_line(item)
            yield done_line()
        except Exception as e:  # noqa: BLE001
            yield error_line(str(e))
        finally:
            # 镜像 Go defer:只要有部分内容就写回内存
            if full_parts:
                complete = "".join(full_parts)
                mem.get_simple_memory(req.Id).set_messages(Message(role="user", content=req.Question))
                mem.get_simple_memory(req.Id).set_messages(Message(role="assistant", content=complete))

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )
