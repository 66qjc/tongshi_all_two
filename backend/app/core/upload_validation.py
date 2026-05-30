"""文件上传安全校验"""
from pathlib import Path

# 允许上传的文件扩展名。
ALLOWED_UPLOAD_EXTENSIONS = {
    # 图片
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
    # 文档
    ".pdf", ".doc", ".docx", ".ppt", ".pptx",
    # 视频
    ".mp4", ".webm", ".mov",
    # 压缩包
    ".zip",
}

ALLOWED_EXCEL_EXTENSIONS = {".xlsx", ".xls"}

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 通用上传：50MB。
MAX_EXCEL_SIZE = 10 * 1024 * 1024   # Excel 导入：10MB。

# 魔数映射：扩展名 -> 允许的文件头字节前缀（均在偏移 0 处检查）。
_MAGIC_SIGNATURES = {
    ".pdf": [b"%PDF"],
    ".png": [b"\x89PNG"],
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
    ".gif": [b"GIF87a", b"GIF89a"],
    ".webp": [b"RIFF"],  # 在 validate_magic_number 中额外校验偏移 8 的 WEBP 标识
    ".zip": [b"PK"],
    ".mp4": [b"ftyp"],   # 在 validate_magic_number 中校验偏移 4 的 ftyp
    ".mov": [b"ftyp"],
    ".webm": [b"\x1a\x45\xdf\xa3"],  # Matroska/EBML
    ".docx": [b"PK"],    # ZIP 容器格式，PK 头
    ".pptx": [b"PK"],
}

# 需要跳过魔数校验的扩展名：无标准魔数或魔数不可靠。
# .svg 由 SVG 安全清洗器单独处理；.doc（旧格式）魔数复杂，跳过。
_SKIP_MAGIC_EXTENSIONS = {".svg", ".doc"}


def detect_content_type(content: bytes, filename: str) -> str:
    """根据文件头魔数和扩展名推断 MIME 类型。"""
    ext = Path(filename).suffix.lower()

    if ext in {".pdf"} and content[:4] == b"%PDF":
        return "application/pdf"
    if ext in {".png"} and content[:4] == b"\x89PNG":
        return "image/png"
    if ext in {".jpg", ".jpeg"} and content[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if ext in {".gif"} and content[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if ext in {".webp"} and content[:4] == b"RIFF":
        return "image/webp"
    if ext in {".zip"} and content[:2] == b"PK":
        return "application/zip"
    if ext in {".docx"} and content[:2] == b"PK":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if ext in {".pptx"} and content[:2] == b"PK":
        return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    if ext in {".mp4", ".mov"}:
        return "video/mp4"
    if ext in {".webm"}:
        return "video/webm"
    if ext in {".svg"}:
        return "image/svg+xml"

    return "application/octet-stream"


def validate_magic_number(content: bytes, filename: str) -> str | None:
    """校验文件头魔数是否与扩展名匹配；通过返回 None，失败返回错误信息。"""
    ext = Path(filename).suffix.lower()

    if ext in _SKIP_MAGIC_EXTENSIONS or ext not in _MAGIC_SIGNATURES:
        return None

    # MP4/MOV：ISOBMFF 容器格式，ftyp box type 位于偏移 4 字节处
    if ext in (".mp4", ".mov"):
        if len(content) >= 8 and content[4:8] == b"ftyp":
            return None
        return f"文件内容与扩展名 {ext} 不匹配"

    # WebP：偏移 0 处为 RIFF 且偏移 8 处为 WEBP
    if ext == ".webp":
        if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
            return None
        return f"文件内容与扩展名 {ext} 不匹配"

    # 标准：检查偏移 0 处的魔数前缀
    signatures = _MAGIC_SIGNATURES.get(ext, [])
    for sig in signatures:
        if content[:len(sig)] == sig:
            return None

    return f"文件内容与扩展名 {ext} 不匹配"


def validate_upload(filename: str, file_size: int,
                    allowed_extensions: set = ALLOWED_UPLOAD_EXTENSIONS,
                    max_size: int = MAX_UPLOAD_SIZE,
                    content: bytes | None = None) -> str | None:
    """校验上传文件；通过返回 None，失败返回错误信息。"""
    if not filename:
        return "未选择文件"
    ext = Path(filename).suffix.lower()
    if ext not in allowed_extensions:
        return f"不支持的文件类型: {ext}"
    if file_size > max_size:
        size_mb = max_size / (1024 * 1024)
        return f"文件大小超过限制 ({size_mb:.0f}MB)"
    if content is not None:
        magic_err = validate_magic_number(content, filename)
        if magic_err:
            return magic_err
    return None
