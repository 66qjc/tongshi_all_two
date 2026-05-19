"""文件上传安全校验"""
from pathlib import Path

# 允许的文件类型（扩展名 → MIME 描述）
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

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 通用上传：50MB
MAX_EXCEL_SIZE = 10 * 1024 * 1024   # Excel 导入：10MB


def validate_upload(filename: str, file_size: int,
                    allowed_extensions: set = ALLOWED_UPLOAD_EXTENSIONS,
                    max_size: int = MAX_UPLOAD_SIZE) -> str | None:
    """校验上传文件，返回错误信息字符串；校验通过返回 None"""
    if not filename:
        return "未选择文件"
    ext = Path(filename).suffix.lower()
    if ext not in allowed_extensions:
        return f"不支持的文件类型: {ext}"
    if file_size > max_size:
        size_mb = max_size / (1024 * 1024)
        return f"文件大小超过限制 ({size_mb:.0f}MB)"
    return None
