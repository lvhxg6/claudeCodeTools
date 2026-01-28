# FastAPI 主应用
# Main Application

"""
FastAPI 主应用模块 - 提供 Web API 端点。

支持功能：
- 文件上传 API (POST /api/upload)
- 健康检查 API (GET /api/health)

Requirements:
- 1.2: 验证文件格式是否为支持的类型（mp3、wav、m4a）
- 1.3: 上传不支持的文件格式时显示明确的错误提示信息
- 1.4: 上传有效的音频文件时显示上传进度并在完成后确认
- 1.5: 音频文件上传成功后自动开始处理流程
"""

import logging
import os
import tempfile
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.audio_service import (
    validate_audio_format,
    get_format_error_message,
    AudioFormatError,
)
from src.config_manager import ConfigManager
from src.session_manager import SessionManager, SessionNotFoundError
from src.models import Summary, SummaryStatus

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="会议录音智能总结系统",
    description="将会议录音自动转写为文字，并通过 AI 智能分析生成结构化的会议总结报告",
    version="1.0.0"
)

# 初始化服务
config_manager = ConfigManager()
session_manager = SessionManager()

# 临时文件存储目录
TEMP_UPLOAD_DIR = tempfile.mkdtemp(prefix="meeting_summary_")
logger.info(f"临时文件存储目录: {TEMP_UPLOAD_DIR}")


# ============== 响应模型 ==============

class SummaryResponse(BaseModel):
    """总结响应模型"""
    content: str
    status: str
    version: int


class UploadResponse(BaseModel):
    """上传响应模型"""
    session_id: str
    transcription: str
    summary: SummaryResponse


class ErrorDetail(BaseModel):
    """错误详情模型"""
    code: str
    message: str
    details: Optional[str] = None
    retry_allowed: bool = False


class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: ErrorDetail


# ============== 错误代码 ==============

class ErrorCode:
    """错误代码常量"""
    FILE_FORMAT_ERROR = "FILE_FORMAT_ERROR"
    FILE_SIZE_ERROR = "FILE_SIZE_ERROR"
    FILE_UPLOAD_ERROR = "FILE_UPLOAD_ERROR"
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# ============== 辅助函数 ==============

def get_upload_max_size_bytes() -> int:
    """获取上传文件大小限制（字节）"""
    max_size_mb = config_manager.get_upload_max_size()
    return max_size_mb * 1024 * 1024


def save_temp_file(file_content: bytes, filename: str) -> str:
    """
    保存文件到临时目录。
    
    Args:
        file_content: 文件内容
        filename: 原始文件名
    
    Returns:
        保存后的文件路径
    """
    # 生成安全的文件名
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(TEMP_UPLOAD_DIR, safe_filename)
    
    # 如果文件已存在，添加序号
    base, ext = os.path.splitext(safe_filename)
    counter = 1
    while os.path.exists(file_path):
        file_path = os.path.join(TEMP_UPLOAD_DIR, f"{base}_{counter}{ext}")
        counter += 1
    
    # 写入文件
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    logger.info(f"文件已保存: {file_path}")
    return file_path


# ============== API 端点 ==============

@app.post(
    "/api/upload",
    response_model=UploadResponse,
    responses={
        400: {"model": ErrorResponse, "description": "文件格式或大小错误"},
        500: {"model": ErrorResponse, "description": "服务器内部错误"}
    },
    summary="上传音频文件",
    description="上传音频文件进行转写和总结处理"
)
async def upload_audio(
    file: UploadFile = File(..., description="音频文件 (mp3, wav, m4a)"),
    language: str = Form(default="zh", description="语言代码，默认 zh")
):
    """
    上传音频文件进行处理。
    
    接收音频文件，验证格式和大小，创建会话并保存文件。
    由于转写服务和总结服务尚未实现，暂时返回占位符数据。
    
    Args:
        file: 上传的音频文件
        language: 语言代码，默认 "zh"
    
    Returns:
        UploadResponse: 包含 session_id、transcription 和 summary
    
    Raises:
        HTTPException: 文件格式错误 (400)、文件过大 (400)、服务器错误 (500)
    
    Validates: Requirements 1.2, 1.3, 1.4, 1.5
    """
    logger.info(f"收到文件上传请求: {file.filename}, 语言: {language}")
    
    # 1. 验证文件格式 (Requirements 1.2, 1.3)
    if not file.filename:
        logger.warning("上传文件名为空")
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": ErrorCode.FILE_FORMAT_ERROR,
                    "message": "文件名不能为空",
                    "retry_allowed": True
                }
            }
        )
    
    if not validate_audio_format(file.filename):
        logger.warning(f"不支持的文件格式: {file.filename}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": ErrorCode.FILE_FORMAT_ERROR,
                    "message": get_format_error_message(),
                    "details": f"上传的文件: {file.filename}",
                    "retry_allowed": True
                }
            }
        )
    
    # 2. 读取文件内容并检查大小
    try:
        file_content = await file.read()
        file_size = len(file_content)
        max_size = get_upload_max_size_bytes()
        
        logger.info(f"文件大小: {file_size / 1024 / 1024:.2f} MB")
        
        if file_size > max_size:
            max_size_mb = config_manager.get_upload_max_size()
            logger.warning(f"文件过大: {file_size} bytes > {max_size} bytes")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": ErrorCode.FILE_SIZE_ERROR,
                        "message": f"文件过大，请上传小于 {max_size_mb}MB 的文件",
                        "details": f"当前文件大小: {file_size / 1024 / 1024:.2f}MB",
                        "retry_allowed": True
                    }
                }
            )
        
        if file_size == 0:
            logger.warning("上传的文件为空")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": ErrorCode.FILE_FORMAT_ERROR,
                        "message": "上传的文件为空",
                        "retry_allowed": True
                    }
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"读取文件失败: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": ErrorCode.FILE_UPLOAD_ERROR,
                    "message": "文件读取失败，请重试",
                    "details": str(e),
                    "retry_allowed": True
                }
            }
        )
    
    # 3. 创建会话
    try:
        session_id = session_manager.create_session(audio_filename=file.filename)
        logger.info(f"创建会话: {session_id}")
    except Exception as e:
        logger.error(f"创建会话失败: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR,
                    "message": "创建会话失败，请重试",
                    "details": str(e),
                    "retry_allowed": True
                }
            }
        )
    
    # 4. 保存文件到临时目录
    try:
        # 使用 session_id 作为文件名前缀，避免冲突
        _, ext = os.path.splitext(file.filename)
        temp_filename = f"{session_id}{ext}"
        file_path = save_temp_file(file_content, temp_filename)
        
        # 更新会话，记录文件路径（可选，用于后续处理）
        session_manager.update_session(session_id, {
            "audio_filename": file.filename
        })
        
    except Exception as e:
        logger.error(f"保存文件失败: {e}")
        # 清理已创建的会话
        try:
            session_manager.delete_session(session_id)
        except:
            pass
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": ErrorCode.FILE_UPLOAD_ERROR,
                    "message": "文件保存失败，请重试",
                    "details": str(e),
                    "retry_allowed": True
                }
            }
        )
    
    # 5. 返回响应 (Requirements 1.4, 1.5)
    # 注意：由于转写服务和总结服务尚未实现，暂时返回占位符
    logger.info(f"文件上传成功: session_id={session_id}")
    
    return UploadResponse(
        session_id=session_id,
        transcription="",  # 转写服务尚未实现，暂时为空
        summary=SummaryResponse(
            content="",  # 总结服务尚未实现，暂时为空
            status=SummaryStatus.DRAFT,
            version=1
        )
    )


@app.get(
    "/api/health",
    summary="健康检查",
    description="检查系统和依赖服务的健康状态"
)
async def health_check():
    """
    健康检查端点。
    
    返回系统状态和版本信息。
    Whisper 服务状态检查将在后续任务中实现。
    
    Returns:
        健康状态信息
    """
    return {
        "status": "healthy",
        "whisper_service": "unknown",  # 将在任务 5.2 中实现
        "version": "1.0.0"
    }


# ============== 应用启动 ==============

def get_app() -> FastAPI:
    """获取 FastAPI 应用实例"""
    return app


if __name__ == "__main__":
    import uvicorn
    
    host = config_manager.get_server_host()
    port = config_manager.get_server_port()
    
    logger.info(f"启动服务器: {host}:{port}")
    uvicorn.run(app, host=host, port=port)
