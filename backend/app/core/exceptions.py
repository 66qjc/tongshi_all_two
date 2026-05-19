"""Custom exceptions and unified response"""


class BusinessException(Exception):
    """业务异常，自动转为统一响应格式"""
    def __init__(self, code: int = 400, message: str = "请求失败"):
        self.code = code
        self.message = message
        super().__init__(message)
