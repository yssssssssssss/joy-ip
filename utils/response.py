#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一API响应格式工具
"""

from flask import jsonify
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class APIResponse:
    """统一API响应格式"""

    @staticmethod
    def success(
        data: Any = None,
        message: str = "操作成功",
        **kwargs
    ) -> tuple:
        """
        成功响应

        Args:
            data: 返回数据
            message: 成功消息
            **kwargs: 额外字段

        Returns:
            tuple: (response, status_code)
        """
        response = {
            "success": True,
            "message": message,
        }
        if data is not None:
            response["data"] = data
        response.update(kwargs)
        return jsonify(response), 200

    @staticmethod
    def error(
        message: str,
        code: str = "ERROR",
        status_code: int = 200,
        details: Optional[Dict] = None,
        **kwargs
    ) -> tuple:
        """
        错误响应（业务错误，默认返回200）

        Args:
            message: 错误消息
            code: 错误代码（用于前端判断）
            status_code: HTTP状态码
            details: 错误详情
            **kwargs: 额外字段

        Returns:
            tuple: (response, status_code)
        """
        response = {
            "success": False,
            "error": message,
            "code": code,
        }
        if details:
            response["details"] = details
        response.update(kwargs)
        return jsonify(response), status_code

    @staticmethod
    def server_error(
        message: str = "服务器内部错误",
        exception: Optional[Exception] = None
    ) -> tuple:
        """
        服务器错误响应（返回500）

        Args:
            message: 错误消息
            exception: 异常对象（用于日志记录）

        Returns:
            tuple: (response, status_code)
        """
        if exception:
            logger.error(f"{message}: {str(exception)}", exc_info=True)

        response = {
            "success": False,
            "error": message,
            "code": "SERVER_ERROR"
        }
        return jsonify(response), 500


class ErrorCode:
    """错误代码常量"""
    # 参数错误
    MISSING_PARAM = "MISSING_PARAM"
    INVALID_PARAM = "INVALID_PARAM"

    # 业务错误
    COMPLIANCE_ERROR = "COMPLIANCE"
    GENERATION_FAILED = "GENERATION_FAILED"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    UPLOAD_FAILED = "UPLOAD_FAILED"
    SCRIPT_ERROR = "SCRIPT_ERROR"

    # 任务错误
    JOB_NOT_FOUND = "JOB_NOT_FOUND"
    JOB_FAILED = "JOB_FAILED"

    # 服务器错误
    SERVER_ERROR = "SERVER_ERROR"
