"""富文本 HTML 白名单清洗工具。"""
from __future__ import annotations

from html import escape
from html.parser import HTMLParser
import re
from urllib.parse import urlparse


ALLOWED_TAGS = {
    "a",
    "b",
    "blockquote",
    "br",
    "code",
    "div",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "hr",
    "i",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "s",
    "span",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "u",
    "ul",
}

VOID_TAGS = {"br", "hr", "img"}
DROP_WITH_CONTENT_TAGS = {"script", "style", "iframe", "object", "embed", "svg", "math", "template"}
SAFE_CLASS_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _safe_url(value: str) -> bool:
    value = value.strip()
    if not value:
        return False
    parsed = urlparse(value)
    if parsed.scheme:
        return parsed.scheme in {"http", "https"}
    return value.startswith(("/", "#", "./", "../"))


def _safe_class(value: str) -> str:
    tokens = [token for token in value.split() if SAFE_CLASS_RE.match(token)]
    return " ".join(tokens)


class _LessonHtmlSanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in DROP_WITH_CONTENT_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth or tag not in ALLOWED_TAGS:
            return

        cleaned_attrs = self._clean_attrs(tag, attrs)
        attr_text = "".join(
            f' {name}="{escape(value, quote=True)}"' for name, value in cleaned_attrs
        )
        self.parts.append(f"<{tag}{attr_text}>")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in DROP_WITH_CONTENT_TAGS:
            if self.skip_depth:
                self.skip_depth -= 1
            return
        if self.skip_depth or tag not in ALLOWED_TAGS or tag in VOID_TAGS:
            return
        self.parts.append(f"</{tag}>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        self.parts.append(escape(data, quote=False))

    def handle_entityref(self, name: str) -> None:
        if not self.skip_depth:
            self.parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if not self.skip_depth:
            self.parts.append(f"&#{name};")

    def _clean_attrs(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> list[tuple[str, str]]:
        result: list[tuple[str, str]] = []
        for raw_name, raw_value in attrs:
            name = raw_name.lower()
            value = (raw_value or "").strip()
            if not value or name.startswith("on") or name == "style":
                continue

            if name == "class":
                safe_value = _safe_class(value)
                if safe_value:
                    result.append((name, safe_value))
                continue

            if tag == "a" and name == "href" and _safe_url(value):
                result.append((name, value))
                continue

            if tag == "img" and name in {"src", "alt", "title"}:
                if name == "src" and not _safe_url(value):
                    continue
                result.append((name, value))
                continue

            if tag == "div" and name == "data-material-id" and value.isdigit():
                result.append((name, value))
                continue

            if tag == "div" and name == "data-material-type" and value in {"video", "pdf"}:
                result.append((name, value))
                continue

        return result


def sanitize_lesson_html(content: str | None) -> str:
    """清洗课时富文本，保留教学内容与资料占位符，移除危险标签和属性。"""
    if not content:
        return ""
    parser = _LessonHtmlSanitizer()
    parser.feed(content)
    parser.close()
    return "".join(parser.parts)
