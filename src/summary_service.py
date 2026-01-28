# 总结服务
# Summary Service

"""
总结服务模块 - 封装 Claude CLI 调用，实现智能会议总结功能。

支持功能：
- 调用 Claude CLI 生成会议总结
- 根据用户请求更新总结
- 总结 prompt 模板管理

Requirements:
- 3.1: 转写完成后调用 Claude_Code_CLI 进行会议内容总结
- 3.2: 总结时剔除会议中的废话和闲聊内容
- 3.3: 提取会议的结论性内容
- 3.4: 保留支撑结论的关键论据和沟通要点
- 3.5: 输出业务导向的总结报告，使用 Markdown 格式
- 3.6: Claude_Code_CLI 不可用时显示服务不可用的错误信息
"""

import asyncio
import logging
import shlex
from typing import Optional

from src.config_manager import ConfigManager


# 配置日志
logger = logging.getLogger(__name__)


class SummaryError(Exception):
    """总结错误异常基类"""
    pass


class ClaudeCLIError(SummaryError):
    """Claude CLI 错误异常
    
    当 Claude CLI 不可用或返回错误时抛出。
    
    Validates: Requirements 3.6
    """
    pass


class SummaryTimeoutError(SummaryError):
    """总结超时错误异常"""
    pass


# 默认总结 prompt 模板
DEFAULT_SUMMARY_PROMPT = """请对以下会议转写内容进行智能总结：

要求：
1. 剔除废话和闲聊内容
2. 提取会议结论性内容
3. 保留支撑结论的关键论据和沟通要点
4. 输出业务导向的总结报告
5. 使用 Markdown 格式

转写内容：
{transcription}"""


# 默认更新 prompt 模板
DEFAULT_UPDATE_PROMPT = """请根据用户的修改请求更新会议总结。

原始转写内容：
{transcription}

当前总结：
{current_summary}

对话历史：
{chat_history}

用户修改请求：
{edit_request}

请根据用户请求更新总结，保持 Markdown 格式，只输出更新后的总结内容。"""


class SummaryService:
    """
    智能总结服务，封装 Claude CLI 调用。
    
    使用 Claude Code CLI 进行会议内容总结和协作编辑。
    
    Attributes:
        config: 配置管理器实例
    
    Requirements:
        - 3.1: 转写完成后调用 Claude_Code_CLI 进行会议内容总结
        - 3.2: 总结时剔除会议中的废话和闲聊内容
        - 3.3: 提取会议的结论性内容
        - 3.4: 保留支撑结论的关键论据和沟通要点
        - 3.5: 输出业务导向的总结报告，使用 Markdown 格式
        - 3.6: Claude_Code_CLI 不可用时显示服务不可用的错误信息
    
    Example:
        >>> config = ConfigManager()
        >>> service = SummaryService(config)
        >>> summary = await service.generate_summary("会议转写内容...")
    """
    
    def __init__(self, config: ConfigManager):
        """
        初始化总结服务。
        
        Args:
            config: 配置管理器实例，用于获取 Claude CLI 命令和超时设置
        
        Example:
            >>> config = ConfigManager()
            >>> service = SummaryService(config)
        """
        self.config = config
    
    def _get_summary_prompt(self, transcription: str) -> str:
        """
        获取总结 prompt。
        
        Args:
            transcription: 转写文本
        
        Returns:
            str: 格式化后的 prompt
        """
        template = self.config.get_summary_prompt_template()
        if not template:
            template = DEFAULT_SUMMARY_PROMPT
        return template.format(transcription=transcription)
    
    def _get_update_prompt(
        self, 
        transcription: str, 
        current_summary: str, 
        edit_request: str, 
        chat_history: list
    ) -> str:
        """
        获取更新 prompt。
        
        Args:
            transcription: 原始转写文本
            current_summary: 当前总结内容
            edit_request: 用户修改请求
            chat_history: 对话历史
        
        Returns:
            str: 格式化后的 prompt
        """
        # 格式化对话历史
        history_text = ""
        if chat_history:
            history_lines = []
            for msg in chat_history:
                role = "用户" if msg.get("role") == "user" else "AI"
                content = msg.get("content", "")
                history_lines.append(f"{role}: {content}")
            history_text = "\n".join(history_lines)
        else:
            history_text = "（无历史对话）"
        
        return DEFAULT_UPDATE_PROMPT.format(
            transcription=transcription,
            current_summary=current_summary,
            chat_history=history_text,
            edit_request=edit_request
        )
    
    async def _run_claude_cli(self, prompt: str) -> str:
        """
        运行 Claude CLI 命令。
        
        Args:
            prompt: 发送给 Claude 的 prompt
        
        Returns:
            str: Claude 的响应内容
        
        Raises:
            ClaudeCLIError: Claude CLI 不可用或返回错误
            SummaryTimeoutError: 请求超时
        """
        command = self.config.get_claude_command()
        timeout = self.config.get_claude_timeout()
        
        # 构建完整命令
        # Claude CLI 使用 -p 参数进行非交互式输出，从 stdin 读取 prompt
        full_command = f'{command} -p'
        
        logger.info(f"执行 Claude CLI 命令，prompt 长度: {len(prompt)} 字符")
        
        try:
            # 创建子进程，通过 stdin 传递 prompt
            process = await asyncio.create_subprocess_shell(
                full_command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # 通过 stdin 发送 prompt，等待完成，带超时
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=prompt.encode('utf-8')),
                timeout=timeout
            )
            
            # 检查返回码
            if process.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="replace").strip()
                logger.error(
                    f"Claude CLI 返回错误: returncode={process.returncode}, "
                    f"stderr={error_msg}"
                )
                raise ClaudeCLIError(
                    f"AI 服务返回错误: {error_msg or '未知错误'}"
                )
            
            # 解析输出
            result = stdout.decode("utf-8", errors="replace").strip()
            logger.info(f"Claude CLI 响应长度: {len(result)} 字符")
            
            return result
        
        except asyncio.TimeoutError:
            logger.error(f"Claude CLI 超时: timeout={timeout}s")
            raise SummaryTimeoutError(
                f"AI 服务响应超时，请稍后重试"
            )
        
        except FileNotFoundError:
            logger.error(f"Claude CLI 命令未找到: {command}")
            raise ClaudeCLIError(
                "AI 服务暂时不可用，请检查 Claude CLI 是否已安装"
            )
        
        except ClaudeCLIError:
            raise
        
        except SummaryTimeoutError:
            raise
        
        except Exception as e:
            logger.error(f"Claude CLI 调用失败: {e}")
            raise ClaudeCLIError(
                f"AI 服务调用失败: {str(e)}"
            )
    
    async def generate_summary(self, transcription: str) -> str:
        """
        根据转写文本生成会议总结。
        
        调用 Claude CLI 生成智能会议总结，剔除废话，提取结论和论据。
        
        Args:
            transcription: 转写文本内容
        
        Returns:
            str: Markdown 格式的会议总结
        
        Raises:
            ClaudeCLIError: Claude CLI 不可用或返回错误
            SummaryTimeoutError: 请求超时
            SummaryError: 其他总结错误
        
        Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
        
        Example:
            >>> config = ConfigManager()
            >>> service = SummaryService(config)
            >>> summary = await service.generate_summary("会议转写内容...")
            >>> print(summary)
            '# 会议总结\\n\\n## 主要结论\\n...'
        """
        if not transcription or not transcription.strip():
            logger.warning("转写文本为空，返回空总结")
            return ""
        
        prompt = self._get_summary_prompt(transcription)
        
        logger.info(f"开始生成总结，转写文本长度: {len(transcription)} 字符")
        
        try:
            result = await self._run_claude_cli(prompt)
            logger.info(f"总结生成完成，总结长度: {len(result)} 字符")
            return result
        
        except (ClaudeCLIError, SummaryTimeoutError):
            raise
        
        except Exception as e:
            logger.error(f"生成总结失败: {e}")
            raise SummaryError(f"生成总结失败: {str(e)}") from e
    
    async def update_summary(
        self, 
        transcription: str, 
        current_summary: str, 
        edit_request: str, 
        chat_history: Optional[list] = None
    ) -> str:
        """
        根据用户请求更新总结。
        
        调用 Claude CLI 根据用户的修改请求更新会议总结。
        
        Args:
            transcription: 原始转写文本
            current_summary: 当前总结内容
            edit_request: 用户的修改请求
            chat_history: 对话历史列表，可选
        
        Returns:
            str: 更新后的 Markdown 格式总结
        
        Raises:
            ClaudeCLIError: Claude CLI 不可用或返回错误
            SummaryTimeoutError: 请求超时
            SummaryError: 其他总结错误
        
        Validates: Requirements 3.1, 3.5, 3.6
        
        Example:
            >>> config = ConfigManager()
            >>> service = SummaryService(config)
            >>> updated = await service.update_summary(
            ...     transcription="会议内容...",
            ...     current_summary="# 总结\\n...",
            ...     edit_request="请补充第二点的细节"
            ... )
        """
        if chat_history is None:
            chat_history = []
        
        prompt = self._get_update_prompt(
            transcription=transcription,
            current_summary=current_summary,
            edit_request=edit_request,
            chat_history=chat_history
        )
        
        logger.info(
            f"开始更新总结，修改请求: {edit_request[:50]}..."
            if len(edit_request) > 50 else f"开始更新总结，修改请求: {edit_request}"
        )
        
        try:
            result = await self._run_claude_cli(prompt)
            logger.info(f"总结更新完成，新总结长度: {len(result)} 字符")
            return result
        
        except (ClaudeCLIError, SummaryTimeoutError):
            raise
        
        except Exception as e:
            logger.error(f"更新总结失败: {e}")
            raise SummaryError(f"更新总结失败: {str(e)}") from e
