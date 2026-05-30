"""SVG 安全清洗器：移除脚本、事件属性、外部实体等危险内容"""
import re


# 需要移除的危险标签
_DANGEROUS_TAGS = {"script", "foreignObject", "use"}

# 需要移除的危险属性（on* 事件处理器）
_DANGEROUS_ATTR_PATTERN = re.compile(
    r'\bon\w+\s*=\s*"[^"]*"|\bon\w+\s*=\s*\'[^\']*\'|\bon\w+\s*=\s*[^\s>]+',
    re.IGNORECASE,
)

# XML 外部实体引用
_ENTITY_PATTERN = re.compile(r'<!ENTITY\b[^>]*>', re.IGNORECASE)

# DOCTYPE 声明（可能包含外部实体）
_DOCTYPE_PATTERN = re.compile(r'<!DOCTYPE\b[^>]*>', re.IGNORECASE)


def sanitize_svg(content: str) -> str:
    """对 SVG 字符串做安全清洗。

    移除：
    - <script> 标签
    - <foreignObject> 标签
    - <use> 标签（可能引用外部资源）
    - on* 事件属性（onclick, onload 等）
    - <!ENTITY 外部实体声明
    - <!DOCTYPE 声明

    返回清洗后的 SVG 字符串。清洗失败返回空字符串。
    """
    if not content or not content.strip():
        return ""

    try:
        # 1. 移除 DOCTYPE 和实体声明
        cleaned = _DOCTYPE_PATTERN.sub("", content)
        cleaned = _ENTITY_PATTERN.sub("", cleaned)

        # 2. 移除危险标签（带属性的完整标签）
        for tag in _DANGEROUS_TAGS:
            cleaned = re.sub(
                rf'<{tag}\b[^>]*>.*?</{tag}\s*>',
                "",
                cleaned,
                flags=re.IGNORECASE | re.DOTALL,
            )
            # 自闭合形式
            cleaned = re.sub(
                rf'<{tag}\b[^>]*/>',
                "",
                cleaned,
                flags=re.IGNORECASE,
            )

        # 3. 移除 on* 事件属性
        cleaned = _DANGEROUS_ATTR_PATTERN.sub("", cleaned)

        # 4. 清理多余空白行
        cleaned = re.sub(r'\n\s*\n', '\n', cleaned)

        if not cleaned.strip():
            return ""

        return cleaned.strip()

    except Exception:
        return ""
