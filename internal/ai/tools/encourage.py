# 鼓励工具(对应 Go 版 internal/ai/tools/encourage.go)
# 按毫秒时间戳 % 5 从 5 条英文鼓励语中取一条。仅注册在 chat 模式 ReAct agent 中。

import time

TOOL_NAME = "encourage"

TOOL_DESCRIPTION = (
    "Encourage the user with a positive message. Use this tool when you want to provide "
    "motivation, support, or positive reinforcement to the user. The tool will return a randomly "
    "selected encouraging message to uplift the user's spirits."
)

SPEC = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": TOOL_DESCRIPTION,
        "parameters": {"type": "object", "properties": {}},
    },
}

_PHRASES = [
    "Keep up the great work! You're doing amazing!",
    "Believe in yourself! You have the power to achieve anything!",
    "Every step you take is a step closer to your goals. Keep going!",
    "You are capable of incredible things. Don't give up!",
    "Your efforts are paying off! Stay positive and keep pushing forward!",
]


def encourage() -> str:
    return _PHRASES[int(time.time() * 1000) % len(_PHRASES)]
