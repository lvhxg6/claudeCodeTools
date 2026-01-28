# ChatService 单元测试
# ChatService Unit Tests

"""
ChatService 对话服务的单元测试。

测试覆盖：
- chat() 方法
- 上下文构建
- Claude CLI 调用
- 错误处理

Requirements:
- 5.1: 用户可以在对话框中输入问题或修改请求
- 5.2: 用户追问时系统能够结合原始转写内容和当前总结进行回答
- 5.3: 用户可以通过对话请求修改总结内容
- 5.7: Claude_Code_CLI 不可用时显示服务不可用的错误信息
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from src.chat_service import (
    ChatService,
    ChatError,
    ChatCLIError,
    ChatTimeoutError,
    DEFAULT_CHAT_PROMPT,
    DEFAULT_EDIT_PROMPT,
)
from src.config_manager import ConfigManager
from src.models import ChatMessage, MessageRole, MessageType


class TestChatServiceInit:
    """测试 ChatService 初始化"""
    
    def test_init_with_config(self):
        """测试使用配置初始化"""
        config = ConfigManager("nonexistent.yaml")
        service = ChatService(config)
        
        assert service.config == config


class TestChatServiceFormatHistory:
    """测试对话历史格式化"""
    
    def test_format_empty_history(self):
        """测试空历史"""
        config = ConfigManager("nonexistent.yaml")
        service = ChatService(config)
        
        result = service._format_chat_history([])
        
        assert "无历史对话" in result
    
    def test_format_history_with_chat_messages(self):
        """测试 ChatMessage 对象历史"""
        config = ConfigManager("nonexistent.yaml")
        service = ChatService(config)
        
        history = [
            ChatMessage(
                role=MessageRole.USER,
                content="问题1",
                message_type=MessageType.QUESTION
            ),
            ChatMessage(
                role=MessageRole.ASSISTANT,
                content="回答1",
                message_type=MessageType.RESPONSE
            )
        ]
        
        result = service._format_chat_history(history)
        
        assert "用户: 问题1" in result
        assert "AI: 回答1" in result
    
    def test_format_history_with_dicts(self):
        """测试字典格式历史"""
        config = ConfigManager("nonexistent.yaml")
        service = ChatService(config)
        
        history = [
            {"role": "user", "content": "问题"},
            {"role": "assistant", "content": "回答"}
        ]
        
        result = service._format_chat_history(history)
        
        assert "用户: 问题" in result
        assert "AI: 回答" in result


class TestChatServiceBuildContext:
    """测试上下文构建"""
    
    def test_build_context_for_question(self):
        """
        测试问题类型的上下文构建
        
        Validates: Requirements 5.2
        """
        config = ConfigManager("nonexistent.yaml")
        service = ChatService(config)
        
        context = service._build_context(
            transcription="转写内容",
            summary="总结内容",
            message="用户问题",
            history=[],
            message_type=MessageType.QUESTION
        )
        
        assert "转写内容" in context
        assert "总结内容" in context
        assert "用户问题" in context
    
    def test_build_context_for_edit_request(self):
        """
        测试编辑请求类型的上下文构建
        
        Validates: Requirements 5.3
        """
        config = ConfigManager("nonexistent.yaml")
        service = ChatService(config)
        
        context = service._build_context(
            transcription="转写内容",
            summary="总结内容",
            message="修改请求",
            history=[],
            message_type=MessageType.EDIT_REQUEST
        )
        
        assert "转写内容" in context
        assert "总结内容" in context
        assert "修改请求" in context
    
    def test_build_context_includes_history(self):
        """测试上下文包含对话历史"""
        config = ConfigManager("nonexistent.yaml")
        service = ChatService(config)
        
        history = [
            {"role": "user", "content": "之前的问题"},
            {"role": "assistant", "content": "之前的回答"}
        ]
        
        context = service._build_context(
            transcription="转写",
            summary="总结",
            message="新问题",
            history=history,
            message_type=MessageType.QUESTION
        )
        
        assert "之前的问题" in context
        assert "之前的回答" in context


class TestChatServiceChat:
    """测试 chat 方法"""
    
    @pytest.mark.asyncio
    async def test_chat_success(self):
        """
        测试成功对话
        
        Validates: Requirements 5.1, 5.2
        """
        config = ConfigManager("nonexistent.yaml")
        service = ChatService(config)
        
        mock_result = "这是 AI 的回复"
        
        with patch.object(service, '_run_claude_cli', new_callable=AsyncMock) as mock_cli:
            mock_cli.return_value = mock_result
            
            result = await service.chat(
                transcription="会议内容",
                summary="会议总结",
                message="问题"
            )
            
            assert result == mock_result
            mock_cli.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_chat_with_history(self):
        """测试带历史的对话"""
        config = ConfigManager("nonexistent.yaml")
        service = ChatService(config)
        
        mock_result = "回复"
        
        with patch.object(service, '_run_claude_cli', new_callable=AsyncMock) as mock_cli:
            mock_cli.return_value = mock_result
            
            result = await service.chat(
                transcription="内容",
                summary="总结",
                message="问题",
                history=[{"role": "user", "content": "之前"}]
            )
            
            assert result == mock_result
    
    @pytest.mark.asyncio
    async def test_chat_edit_request(self):
        """
        测试编辑请求
        
        Validates: Requirements 5.3
        """
        config = ConfigManager("nonexistent.yaml")
        service = ChatService(config)
        
        mock_result = "# 更新后的总结"
        
        with patch.object(service, '_run_claude_cli', new_callable=AsyncMock) as mock_cli:
            mock_cli.return_value = mock_result
            
            result = await service.chat(
                transcription="内容",
                summary="总结",
                message="请修改",
                message_type=MessageType.EDIT_REQUEST
            )
            
            assert result == mock_result
    
    @pytest.mark.asyncio
    async def test_chat_cli_error(self):
        """
        测试 CLI 错误
        
        Validates: Requirements 5.7
        """
        config = ConfigManager("nonexistent.yaml")
        service = ChatService(config)
        
        with patch.object(service, '_run_claude_cli', new_callable=AsyncMock) as mock_cli:
            mock_cli.side_effect = ChatCLIError("CLI 不可用")
            
            with pytest.raises(ChatCLIError) as exc_info:
                await service.chat(
                    transcription="内容",
                    summary="总结",
                    message="问题"
                )
            
            assert "CLI 不可用" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_chat_timeout_error(self):
        """测试超时错误"""
        config = ConfigManager("nonexistent.yaml")
        service = ChatService(config)
        
        with patch.object(service, '_run_claude_cli', new_callable=AsyncMock) as mock_cli:
            mock_cli.side_effect = ChatTimeoutError("超时")
            
            with pytest.raises(ChatTimeoutError):
                await service.chat(
                    transcription="内容",
                    summary="总结",
                    message="问题"
                )


class TestChatServiceRunClaudeCLI:
    """测试 _run_claude_cli 方法"""
    
    @pytest.mark.asyncio
    async def test_run_claude_cli_success(self):
        """测试成功执行 CLI"""
        config = ConfigManager("nonexistent.yaml")
        service = ChatService(config)
        
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(
            return_value=(b"CLI output", b"")
        )
        
        with patch('asyncio.create_subprocess_shell', return_value=mock_process):
            with patch('asyncio.wait_for', new_callable=AsyncMock) as mock_wait:
                mock_wait.return_value = (b"CLI output", b"")
                
                result = await service._run_claude_cli("test prompt")
                
                assert result == "CLI output"
    
    @pytest.mark.asyncio
    async def test_run_claude_cli_timeout(self):
        """测试 CLI 超时"""
        config = ConfigManager("nonexistent.yaml")
        service = ChatService(config)
        
        with patch('asyncio.create_subprocess_shell', new_callable=AsyncMock):
            with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError()):
                with pytest.raises(ChatTimeoutError) as exc_info:
                    await service._run_claude_cli("test prompt")
                
                assert "超时" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_run_claude_cli_not_found(self):
        """测试 CLI 命令未找到"""
        config = ConfigManager("nonexistent.yaml")
        service = ChatService(config)
        
        with patch('asyncio.create_subprocess_shell', side_effect=FileNotFoundError()):
            with pytest.raises(ChatCLIError) as exc_info:
                await service._run_claude_cli("test prompt")
            
            assert "不可用" in str(exc_info.value)


class TestChatServiceGetContextInfo:
    """测试 get_context_info 方法"""
    
    def test_get_context_info_basic(self):
        """测试基本上下文信息"""
        config = ConfigManager("nonexistent.yaml")
        service = ChatService(config)
        
        info = service.get_context_info(
            transcription="转写内容",
            summary="总结内容",
            history=[]
        )
        
        assert info["has_transcription"] is True
        assert info["transcription_length"] == 4
        assert info["has_summary"] is True
        assert info["summary_length"] == 4
        assert info["history_count"] == 0
    
    def test_get_context_info_with_history(self):
        """测试带历史的上下文信息"""
        config = ConfigManager("nonexistent.yaml")
        service = ChatService(config)
        
        history = [
            ChatMessage(
                role=MessageRole.USER,
                content="问题",
                message_type=MessageType.QUESTION
            )
        ]
        
        info = service.get_context_info(
            transcription="转写",
            summary="总结",
            history=history
        )
        
        assert info["history_count"] == 1
        assert len(info["history_messages"]) == 1
        assert info["history_messages"][0]["role"] == MessageRole.USER


class TestChatServiceExceptions:
    """测试异常类"""
    
    def test_chat_error_is_exception(self):
        """测试 ChatError 是 Exception 子类"""
        assert issubclass(ChatError, Exception)
    
    def test_chat_cli_error_is_chat_error(self):
        """测试 ChatCLIError 是 ChatError 子类"""
        assert issubclass(ChatCLIError, ChatError)
    
    def test_chat_timeout_error_is_chat_error(self):
        """测试 ChatTimeoutError 是 ChatError 子类"""
        assert issubclass(ChatTimeoutError, ChatError)


class TestChatServiceConstants:
    """测试常量"""
    
    def test_default_chat_prompt_exists(self):
        """测试默认对话 prompt 存在"""
        assert DEFAULT_CHAT_PROMPT is not None
        assert "{transcription}" in DEFAULT_CHAT_PROMPT
        assert "{summary}" in DEFAULT_CHAT_PROMPT
        assert "{message}" in DEFAULT_CHAT_PROMPT
    
    def test_default_edit_prompt_exists(self):
        """测试默认编辑 prompt 存在"""
        assert DEFAULT_EDIT_PROMPT is not None
        assert "{transcription}" in DEFAULT_EDIT_PROMPT
        assert "{summary}" in DEFAULT_EDIT_PROMPT
        assert "{message}" in DEFAULT_EDIT_PROMPT
