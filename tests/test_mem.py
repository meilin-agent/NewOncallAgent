# 会话内存测试(对应 Go 版 utility/mem/mem_test.go,5 个用例)
# 覆盖:创建与缓存、滑动窗口裁剪、用户/AI 成对对齐、快照语义。

import pytest

from utility.mem.mem import Message, SimpleMemory, get_simple_memory


def _fresh_mem() -> SimpleMemory:
    m = SimpleMemory("test")
    return m


def test_create_and_cache():
    """GetSimpleMemory:不存在则创建并缓存,同一 id 返回同一实例"""
    a = get_simple_memory("mem-test-id")
    b = get_simple_memory("mem-test-id")
    assert a is b
    assert a.id == "mem-test-id"


def test_append_and_read():
    m = _fresh_mem()
    m.set_messages(Message(role="user", content="hi"))
    assert len(m.get_messages()) == 1
    assert m.get_messages()[0].content == "hi"


def test_window_sliding_even_drop():
    """窗口 6 条,超限从头部成对丢弃(丢弃偶数条,保持 user/assistant 对齐)"""
    m = _fresh_mem()
    # 写入 8 条(4 对 user/assistant)
    for i in range(4):
        m.set_messages(Message(role="user", content=f"u{i}"))
        m.set_messages(Message(role="assistant", content=f"a{i}"))
    assert len(m.get_messages()) == 6  # 8 条超限 2 条,不足 6 成对?——见下:excess=2 偶数直接丢 2
    # 实际:8-6=2(excess 偶数)丢最旧 2 条 → 剩 u1/a1/u2/a2/u3/a3
    assert m.get_messages()[0].content == "u1"


def test_window_odd_excess_pairs_up():
    """excess 为奇数时补齐成偶数丢弃,保证永远成对"""
    m = _fresh_mem()
    # 先塞 7 条(user 开头,不成对):u0 a0 u1 a1 u2 a2 u3 → 超限 1 条,excess%2=1 → excess+1=2 丢 2 条
    msgs = [("user", "u0"), ("assistant", "a0"), ("user", "u1"), ("assistant", "a1"),
            ("user", "u2"), ("assistant", "a2"), ("user", "u3")]
    for r, c in msgs:
        m.set_messages(Message(role=r, content=c))
    got = m.get_messages()
    assert len(got) <= 6
    assert got[0].content == "u1"  # 丢了 u0/a0


def test_get_messages_returns_snapshot():
    """GetMessages 返回深拷贝快照,外部修改不影响内部状态"""
    m = _fresh_mem()
    m.set_messages(Message(role="user", content="u0"))
    m.set_messages(Message(role="assistant", content="a0"))

    snap = m.get_messages()
    snap[0].content = "mutated"
    snap.append(Message(role="user", content="extra"))

    assert m.get_messages()[0].content == "u0"
    assert len(m.get_messages()) == 2
