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
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.audio_service import (
    validate_audio_format,
    get_format_error_message,
    AudioFormatError,
)
from src.config_manager import ConfigManager
from src.session_manager import SessionManager, SessionNotFoundError
from src.models import Summary, SummaryStatus, ChatMessage, MessageRole, MessageType
from src.transcription_service import TranscriptionService
from src.chat_service import ChatService, ChatCLIError, ChatTimeoutError

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

# 配置静态文件服务
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# 初始化服务
config_manager = ConfigManager()
session_manager = SessionManager()
transcription_service = TranscriptionService(config_manager)
chat_service = ChatService(config_manager)

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


class ChatRequest(BaseModel):
    """对话请求模型"""
    session_id: str
    message: str
    type: str = "question"  # question 或 edit_request


class ChatResponse(BaseModel):
    """对话响应模型"""
    response: str
    updated_summary: Optional[SummaryResponse] = None


class FinalizeRequest(BaseModel):
    """确认生成请求模型"""
    session_id: str


class FinalizeResponse(BaseModel):
    """确认生成响应模型"""
    summary: SummaryResponse
    download_url: str


# ============== 错误代码 ==============

class ErrorCode:
    """错误代码常量"""
    FILE_FORMAT_ERROR = "FILE_FORMAT_ERROR"
    FILE_SIZE_ERROR = "FILE_SIZE_ERROR"
    FILE_UPLOAD_ERROR = "FILE_UPLOAD_ERROR"
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    CHAT_SERVICE_ERROR = "CHAT_SERVICE_ERROR"
    CHAT_TIMEOUT_ERROR = "CHAT_TIMEOUT_ERROR"
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

@app.get("/", include_in_schema=False)
async def root():
    """
    首页重定向到静态页面。
    """
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


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
    
    返回系统状态、Whisper 服务状态和版本信息。
    
    Returns:
        健康状态信息，包含：
        - status: 系统整体状态 (healthy/degraded)
        - whisper_service: Whisper 服务状态 (available/unavailable)
        - version: 系统版本号
    
    Validates: Requirements 8.1, 8.2, 8.3
    """
    # 检查 Whisper 服务状态
    whisper_healthy = await transcription_service.check_health()
    whisper_status = "available" if whisper_healthy else "unavailable"
    
    # 系统整体状态：如果 Whisper 不可用，系统处于降级状态
    system_status = "healthy" if whisper_healthy else "degraded"
    
    logger.info(f"健康检查: system={system_status}, whisper={whisper_status}")
    
    return {
        "status": system_status,
        "whisper_service": whisper_status,
        "version": "1.0.0"
    }


@app.post(
    "/api/chat",
    response_model=ChatResponse,
    responses={
        400: {"model": ErrorResponse, "description": "请求参数错误"},
        404: {"model": ErrorResponse, "description": "会话不存在"},
        500: {"model": ErrorResponse, "description": "服务器内部错误"}
    },
    summary="对话",
    description="与 AI 进行对话，支持问答和编辑请求"
)
async def chat(request: ChatRequest):
    """
    对话端点。
    
    处理用户的问题或编辑请求，返回 AI 回复。
    如果是编辑请求，还会返回更新后的总结。
    
    Args:
        request: 对话请求，包含 session_id、message 和 type
    
    Returns:
        ChatResponse: 包含 AI 回复和可选的更新后总结
    
    Raises:
        HTTPException: 会话不存在 (404)、服务错误 (500)
    
    Validates: Requirements 5.2, 5.3, 6.2, 6.3, 6.4
    """
    logger.info(
        f"收到对话请求: session_id={request.session_id}, "
        f"type={request.type}, message={request.message[:50]}..."
        if len(request.message) > 50 
        else f"收到对话请求: session_id={request.session_id}, type={request.type}, message={request.message}"
    )
    
    # 1. 验证消息类型
    valid_types = {MessageType.QUESTION, MessageType.EDIT_REQUEST}
    if request.type not in valid_types:
        logger.warning(f"无效的消息类型: {request.type}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR,
                    "message": f"无效的消息类型，必须是 'question' 或 'edit_request'",
                    "retry_allowed": True
                }
            }
        )
    
    # 2. 获取会话
    try:
        session = session_manager.get_session(request.session_id)
    except SessionNotFoundError:
        logger.warning(f"会话不存在: {request.session_id}")
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": ErrorCode.SESSION_NOT_FOUND,
                    "message": "会话已过期，请重新上传文件",
                    "retry_allowed": False
                }
            }
        )
    
    # 3. 构建对话历史
    history = [
        {"role": msg.role, "content": msg.content}
        for msg in session.chat_history
    ]
    
    # 4. 调用对话服务
    try:
        response_text = await chat_service.chat(
            transcription=session.transcription,
            summary=session.summary.content,
            message=request.message,
            history=history,
            message_type=request.type
        )
    except ChatTimeoutError as e:
        logger.error(f"对话超时: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": ErrorCode.CHAT_TIMEOUT_ERROR,
                    "message": "AI 服务响应超时，请稍后重试",
                    "retry_allowed": True
                }
            }
        )
    except ChatCLIError as e:
        logger.error(f"对话服务错误: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": ErrorCode.CHAT_SERVICE_ERROR,
                    "message": "AI 服务暂时不可用，请稍后重试",
                    "details": str(e),
                    "retry_allowed": True
                }
            }
        )
    except Exception as e:
        logger.error(f"对话失败: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR,
                    "message": "对话处理失败，请重试",
                    "details": str(e),
                    "retry_allowed": True
                }
            }
        )
    
    # 5. 保存用户消息到历史
    user_message = ChatMessage(
        role=MessageRole.USER,
        content=request.message,
        message_type=request.type
    )
    session.add_message(user_message)
    
    # 6. 保存 AI 回复到历史
    ai_message = ChatMessage(
        role=MessageRole.ASSISTANT,
        content=response_text,
        message_type=MessageType.RESPONSE
    )
    session.add_message(ai_message)
    
    # 7. 如果是编辑请求，更新总结
    updated_summary = None
    if request.type == MessageType.EDIT_REQUEST:
        try:
            session.update_summary_content(response_text)
            updated_summary = SummaryResponse(
                content=session.summary.content,
                status=session.summary.status,
                version=session.summary.version
            )
            logger.info(f"总结已更新: version={session.summary.version}")
        except ValueError as e:
            logger.warning(f"无法更新总结: {e}")
            # 如果总结已经是最终版本，不更新但不报错
    
    # 8. 更新会话
    session_manager.update_session(request.session_id, {})
    
    logger.info(f"对话完成: session_id={request.session_id}")
    
    return ChatResponse(
        response=response_text,
        updated_summary=updated_summary
    )


@app.post(
    "/api/finalize",
    response_model=FinalizeResponse,
    responses={
        404: {"model": ErrorResponse, "description": "会话不存在"},
        400: {"model": ErrorResponse, "description": "总结已经是最终版本"},
        500: {"model": ErrorResponse, "description": "服务器内部错误"}
    },
    summary="确认生成",
    description="确认生成最终版本的总结"
)
async def finalize(request: FinalizeRequest):
    """
    确认生成端点。
    
    将总结状态从草稿变更为最终版本。
    
    Args:
        request: 确认请求，包含 session_id
    
    Returns:
        FinalizeResponse: 包含最终版本总结和下载链接
    
    Raises:
        HTTPException: 会话不存在 (404)、已是最终版本 (400)
    
    Validates: Requirements 6.5, 6.6
    """
    logger.info(f"收到确认生成请求: session_id={request.session_id}")
    
    # 1. 获取会话
    try:
        session = session_manager.get_session(request.session_id)
    except SessionNotFoundError:
        logger.warning(f"会话不存在: {request.session_id}")
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": ErrorCode.SESSION_NOT_FOUND,
                    "message": "会话已过期，请重新上传文件",
                    "retry_allowed": False
                }
            }
        )
    
    # 2. 确认生成
    try:
        session.finalize_summary()
        logger.info(f"总结已确认: session_id={request.session_id}")
    except ValueError as e:
        logger.warning(f"无法确认总结: {e}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR,
                    "message": "总结已经是最终版本",
                    "retry_allowed": False
                }
            }
        )
    
    # 3. 更新会话
    session_manager.update_session(request.session_id, {})
    
    # 4. 返回响应
    return FinalizeResponse(
        summary=SummaryResponse(
            content=session.summary.content,
            status=session.summary.status,
            version=session.summary.version
        ),
        download_url=f"/api/download/{request.session_id}"
    )


@app.get(
    "/api/download/{session_id}",
    summary="下载总结",
    description="下载 Markdown 格式的会议总结"
)
async def download(session_id: str):
    """
    下载端点。
    
    返回 Markdown 格式的会议总结文件。
    
    Args:
        session_id: 会话 ID
    
    Returns:
        Markdown 文件下载响应
    
    Raises:
        HTTPException: 会话不存在 (404)
    
    Validates: Requirements 4.3
    """
    from fastapi.responses import Response
    
    logger.info(f"收到下载请求: session_id={session_id}")
    
    # 1. 获取会话
    try:
        session = session_manager.get_session(session_id)
    except SessionNotFoundError:
        logger.warning(f"会话不存在: {session_id}")
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": ErrorCode.SESSION_NOT_FOUND,
                    "message": "会话已过期，请重新上传文件",
                    "retry_allowed": False
                }
            }
        )
    
    # 2. 生成文件名
    # 使用原始音频文件名（去掉扩展名）+ _summary.md
    base_name = os.path.splitext(session.audio_filename)[0]
    filename = f"{base_name}_summary.md"
    
    # 3. 返回 Markdown 文件
    content = session.summary.content
    
    logger.info(f"下载完成: session_id={session_id}, filename={filename}")
    
    return Response(
        content=content.encode("utf-8"),
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


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
