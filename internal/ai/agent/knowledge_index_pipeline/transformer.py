# Markdown 按标题切分器(对应 Go 版 eino-ext markdown HeaderSplitter)
# 配置镜像 Go 版:Headers={"#": "title"}(只认一级标题)、TrimHeaders=False(标题行保留在切块内)、
# 每块 ID 为 uuid4。切分规则:
#   1. 按 \n 拆行,空行跳过,每行 TrimSpace;
#   2. 代码块保护:遇到 ``` 或 ~~~ 围栏进入代码块,块内行不参与标题判断,直到匹配的结束围栏;
#   3. 非代码块内,行以 "#" 开头且(len==1 或第二个字符为空格)判定为新标题:
#      先落盘已积累的行,再把标题行加入新 chunk 开头,title 元数据 = "# " 后的文本;
#   4. 文件末尾剩余行作为最后一个 chunk;
#   5. 每个 chunk 继承原文档元数据(_file_name/_extension/_source)并叠加 title。

import uuid

from internal.ai.loader.loader import Document


def _is_fence(line: str) -> bool:
    """是否为代码围栏行(``` 或 ~~~ 开头)"""
    return line.startswith("```") or line.startswith("~~~")


def split_markdown(doc: Document) -> list[Document]:
    text = doc.content
    lines = text.split("\n")

    chunks: list[Document] = []
    current: list[str] = []
    current_title: str | None = None
    in_code_block = False
    fence_prefix = ""

    for line in lines:
        trimmed = line.strip()

        if in_code_block:
            current.append(line)
            if trimmed.startswith(fence_prefix):
                in_code_block = False
                fence_prefix = ""
            continue

        if _is_fence(trimmed) and (len(trimmed) == 3 or len(trimmed) > 3):
            # 进入代码块(镜像 Go:仅当该行只出现一次围栏标记时进入)
            in_code_block = True
            fence_prefix = trimmed[:3]
            current.append(line)
            continue

        if trimmed == "":
            # 空行跳过
            continue

        # 标题判断:以 "#" 开头且(len==1 或第二个字符是空格)
        if trimmed.startswith("#") and (len(trimmed) == 1 or trimmed[1] == " "):
            if current:
                chunks.append(
                    Document(
                        id=str(uuid.uuid4()),
                        content="\n".join(current),
                        meta_data={**doc.meta_data, "title": current_title} if current_title else dict(doc.meta_data),
                    )
                )
                current = []
            current_title = trimmed[1:].strip()
            current.append(trimmed)  # TrimHeaders=False:标题行保留在 chunk 内
            continue

        current.append(trimmed)

    # 文件末尾剩余行作为最后一个 chunk
    if current:
        chunks.append(
            Document(
                id=str(uuid.uuid4()),
                content="\n".join(current),
                meta_data={**doc.meta_data, "title": current_title} if current_title else dict(doc.meta_data),
            )
        )

    return chunks
