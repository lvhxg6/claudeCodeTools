# 对话服务
# Chat Service

"""
对话服务模块 - 封装 Claude CLI 调用，实现多轮对话功能。

支持功能：
- 处理用户问答
- 构建对话上下文（包含转写文本、总结、历史）
- 支持问题和编辑请求两种消息类型

Requirements:
- 5.1: 用户可以在对话框中输入问题或修改请求
- 5.2: 用户追问时系统能够结合原始转写内容和当前总结进行回答
- 5.3: 用户可以通过对话请求修改总结内容
- 5.6: 对话框显示用户输入和 AI 回复的完整历史
- 5.7: Claude_Code_CLI 不可用时显示服务不可用的错误信息
"""

import asyncio
import logging
import shlex
from typing import Optional

from src.config_manager import ConfigManager
from src.models import ChatMessage, MessageRole, MessageType


# 配置日志
logger = logging.getLogger(__name__)


class ChatError(Exception):
    """对话错误异常基类"""
    pass


class ChatCLIError(ChatError):
    """Claude CLI 错误异常
    
    当 Claude CLI 不可用或返回错误时抛出。
    
    Validates: Requirements 5.7
    """
    pass


class ChatTimeoutError(ChatError):
    """对话超时错误异常"""
    pass


# 默认问答 prompt 模板
DEFAULT_CHAT_PROMPT = """你是一个会议助手，帮助用户理解和分析会议内容。

原始会议转写内容：
{transcription}

当前会议总结：
{summary}

对话历史：
{chat_history}

用户问题：
{message}

请根据会议内容回答用户的问题。如果问题与会议内容无关，请礼貌地说明。"""


# 默认编辑请求 prompt 模板
DEFAULT_EDIT_PROMPT = """你是一个会议助手，帮助用户修改会议总结。

原始会议转写内容：
{transcription}

当前会议总结：
{summary}

对话历史：
{chat_history}

用户修改请求：
{message}

请根据用户的请求修改总结。只输出修改后的完整总结内容，使用 Markdown 格式。"""


class ChatService:
    """
    多轮对话服务，封装 Claude CLI 调用。
    
    支持用户问答和编辑请求两种交互模式。
    
    Attributes:
        config: 配置管理器实例
    
    Requirements:
        - 5.1: 用户可以在对话框中输入问题或修改请求
        - 5.2: 用户追问时系统能够结合原始转写内容和当前总结进行回答
        - 5.3: 用户可以通过对话请求修改总结内容
        - 5.6: 对话框显示用户输入和 AI 回复的完整历史
        - 5.7: Claude_Code_CLI 不可用时显示服务不可用的错误信息
    
    Example:
        >>> config = ConfigManager()
        >>> service = ChatService(config)
        >>> response = await service.chat(
        ...     transcription="会议内容...",
        ...     summary="# 总结...",
        ...     message="会议的主要结论是什么？",
        ...     history=[]
        ... )
    """
    
    def __init__(self, config: ConfigManager):
        """
        初始化对话服务。
        
        Args:
            config: 配置管理器实例，用于获取 Claude CLI 命令和超时设置
        
        Example:
            >>> config = ConfigManager()
            >>> service = ChatService(config)
        """
        self.config = config
    
    def _format_chat_history(self, history: list) -> str:
        """
        格式化对话历史。
        
        Args:
            history: 对话历史列表，可以是 ChatMessage 对象或字典
        
        Returns:
            str: 格式化后的对话历史文本
        """
        if not history:
            return "（无历史对话）"
        
        lines = []
        for msg in history:
            if isinstance(msg, ChatMessage):
                role = "用户" if msg.role == MessageRole.USER else "AI"
                content = msg.content
            elif isinstance(msg, dict):
                role = "用户" if msg.get("role") == MessageRole.USER else "AI"
                content = msg.get("content", "")
            else:
                continue
            
            lines.append(f"{role}: {content}")
        
        return "\n".join(lines) if lines else "（无历史对话）"
    
    def _build_context(
        self,
        transcription: str,
        summary: str,
        message: str,
        history: list,
        message_type: str = MessageType.QUESTION
    ) -> str:
        """
        构建对话上下文。
        
        根据消息类型选择合适的 prompt 模板，并填充上下文信息。
        
        Args:
            transcription: 原始转写文本
            summary: 当前总结内容
            message: 用户消息
            history: 对话历史
            message_type: 消息类型 (question/edit_request)
        
        Returns:
            str: 构建好的完整上下文
        
        Validates: Requirements 5.2
        """
        chat_history_text = self._format_chat_history(history)
        
        if message_type == MessageType.EDIT_REQUEST:
            template = DEFAULT_EDIT_PROMPT
        else:
            template = DEFAULT_CHAT_PROMPT
        
        return template.format(
            transcription=transcription,
            summary=summary,
            chat_history=chat_history_text,
            message=message
        )
    
    async def _run_claude_cli(self, prompt: str) -> str:
        """
        运行 Claude CLI 命令。
        
        Args:
            prompt: 发送给 Claude 的 prompt
        
        Returns:
            str: Claude 的响应内容
        
        Raises:
            ChatCLIError: Claude CLI 不可用或返回错误
            ChatTimeoutError: 请求超时
        """
        command = self.config.get_claude_command()
        timeout = self.config.get_claude_timeout()
        
        # 构建完整命令
        full_command = f'{command} -p {shlex.quote(prompt)}'
        
        logger.info(f"执行 Claude CLI 命令，prompt 长度: {len(prompt)} 字符")
        
        try:
            # 创建子进程
            process = await asyncio.create_subprocess_shell(
                full_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # 等待完成，带超时
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            # 检查返回码
            if process.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="replace").strip()
                logger.error(
                    f"Claude CLI 返回错误: returncode={process.returncode}, "
                    f"stderr={error_msg}"
                )
                raise ChatCLIError(
                    f"AI 服务返回错误: {error_msg or '未知错误'}"
                )
            
            # 解析输出
            result = stdout.decode("utf-8", errors="replace").strip()
            logger.info(f"Claude CLI 响应长度: {len(result)} 字符")
            
            return result
        
        except asyncio.TimeoutError:
            logger.error(f"Claude CLI 超时: timeout={timeout}s")
            raise ChatTimeoutError(
                f"AI 服务响应超时，请稍后重试"
            )
        
        except FileNotFoundError:
            logger.error(f"Claude CLI 命令未找到: {command}")
            raise ChatCLIError(
                "AI 服务暂时不可用，请检查 Claude CLI 是否已安装"
            )
        
        except ChatCLIError:
            raise
        
        except ChatTimeoutError:
            raise
        
        except Exception as e:
            logger.error(f"Claude CLI 调用失败: {e}")
            raise ChatCLIError(
                f"AI 服务调用失败: {str(e)}"
            )
    
    async def chat(
        self,
        transcription: str,
        summary: str,
        message: str,
        history: Optional[list] = None,
        message_type: str = MessageType.QUESTION
    ) -> str:
        """
        处理用户问答。
        
        根据用户消息类型（问题或编辑请求）调用 Claude CLI 生成回复。
        
        Args:
            transcription: 原始转写文本
            summary: 当前总结内容
            message: 用户消息
            history: 对话历史列表，可选
            message_type: 消息类型，默认为 "question"
        
        Returns:
            str: AI 的回复内容
        
        Raises:
            ChatCLIError: Claude CLI 不可用或返回错误
            ChatTimeoutError: 请求超时
            ChatError: 其他对话错误
        
        Validates: Requirements 5.1, 5.2, 5.3, 5.7
        
        Example:
            >>> config = ConfigManager()
            >>> service = ChatService(config)
            >>> response = await service.chat(
            ...     transcription="会议内容...",
            ...     summary="# 总结...",
            ...     message="会议的主要结论是什么？",
            ...     history=[]
            ... )
        """
        if history is None:
            history = []
        
        # 构建上下文
        prompt = self._build_context(
            transcription=transcription,
            summary=summary,
            message=message,
            history=history,
            message_type=message_type
        )
        
        logger.info(
            f"开始对话，消息类型: {message_type}, "
            f"消息: {message[:50]}..."
            if len(message) > 50 else f"开始对话，消息类型: {message_type}, 消息: {message}"
        )
        
        try:
            result = await self._run_claude_cli(prompt)
            logger.info(f"对话完成，回复长度: {len(result)} 字符")
            return result
        
        except (ChatCLIError, ChatTimeoutError):
            raise
        
        except Exception as e:
            logger.error(f"对话失败: {e}")
            raise ChatError(f"对话失败: {str(e)}") from e
    
    def get_context_info(
        self,
        transcription: str,
        summary: str,
        history: list
    ) -> dict:
        """
        获取上下文信息（用于调试和验证）。
        
        返回当前对话上下文的组成部分，用于验证 Property 3。
        
        Args:
            transcription: 原始转写文本
            summary: 当前总结内容
            history: 对话历史
        
        Returns:
            dict: 包含上下文各部分的字典
        
        Validates: Requirements 5.2
        """
        return {
            "has_transcription": bool(transcription),
            "transcription_length": len(transcription),
            "has_summary": bool(summary),
            "summary_length": len(summary),
            "history_count": len(history),
            "history_messages": [
                {
                    "role": msg.role if isinstance(msg, ChatMessage) else msg.get("role"),
                    "content_length": len(msg.content if isinstance(msg, ChatMessage) else msg.get("content", ""))
                }
                for msg in history
            ]
        }
