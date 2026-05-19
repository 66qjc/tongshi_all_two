"""Unified response helpers"""
from typing import Any
from fastapi.responses import JSONResponse


def success(data: Any = None, message: str = "ok") -> dict:
    return {"code": 0, "data": data, "message": message}


def error(code: int = 400, message: str = "请求失败") -> JSONResponse:
    return JSONResponse(status_code=200, content={"code": code, "data": None, "message": message})
