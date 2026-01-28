# SummaryService 单元测试
# SummaryService Unit Tests

"""
SummaryService 总结服务的单元测试。

测试覆盖：
- generate_summary() 方法
- update_summary() 方法
- Claude CLI 调用
- 错误处理

Requirements:
- 3.1: 转写完成后调用 Claude_Code_CLI 进行会议内容总结
- 3.5: 输出业务导向的总结报告，使用 Markdown 格式
- 3.6: Claude_Code_CLI 不可用时显示服务不可用的错误信息
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.summary_service import (
    SummaryService,
    SummaryError,
    ClaudeCLIError,
    SummaryTimeoutError,
    DEFAULT_SUMMARY_PROMPT,
    DEFAULT_UPDATE_PROMPT,
)
from src.config_manager import ConfigManager


class TestSummaryServiceInit:
    """测试 SummaryService 初始化"""
    
    def test_init_with_config(self):
        """测试使用配置初始化"""
        config = ConfigManager("nonexistent.yaml")
        service = SummaryService(config)
        
        assert service.config == config


class TestSummaryServicePrompts:
    """测试 prompt 模板"""
    
    def test_get_summary_prompt_with_transcription(self):
        """测试生成总结 prompt"""
        config = ConfigManager("nonexistent.yaml")
        service = SummaryService(config)
        
        transcription = "这是会议内容"
        prompt = service._get_summary_prompt(transcription)
        
        assert transcription in prompt
        assert "智能总结" in prompt
    
    def test_get_update_prompt_with_all_params(self):
        """测试生成更新 prompt"""
        config = ConfigManager("nonexistent.yaml")
        service = SummaryService(config)
        
        prompt = service._get_update_prompt(
            transcription="原始内容",
            current_summary="当前总结",
            edit_request="请修改",
            chat_history=[
                {"role": "user", "content": "问题1"},
                {"role": "assistant", "content": "回答1"}
            ]
        )
        
        assert "原始内容" in prompt
        assert "当前总结" in prompt
        assert "请修改" in prompt
        assert "问题1" in prompt
        assert "回答1" in prompt
    
    def test_get_update_prompt_empty_history(self):
        """测试空对话历史的更新 prompt"""
        config = ConfigManager("nonexistent.yaml")
        service = SummaryService(config)
        
        prompt = service._get_update_prompt(
            transcription="内容",
            current_summary="总结",
            edit_request="修改",
            chat_history=[]
        )
        
        assert "无历史对话" in prompt


class TestSummaryServiceGenerateSummary:
    """测试 generate_summary 方法"""
    
    @pytest.mark.asyncio
    async def test_generate_summary_success(self):
        """
        测试成功生成总结
        
        Validates: Requirements 3.1, 3.5
        """
        config = ConfigManager("nonexistent.yaml")
        service = SummaryService(config)
        
        mock_result = "# 会议总结\n\n## 主要结论\n- 结论1"
        
        with patch.object(service, '_run_claude_cli', new_callable=AsyncMock) as mock_cli:
            mock_cli.return_value = mock_result
            
            result = await service.generate_summary("会议转写内容")
            
            assert result == mock_result
            mock_cli.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_summary_empty_transcription(self):
        """测试空转写文本返回空总结"""
        config = ConfigManager("nonexistent.yaml")
        service = SummaryService(config)
        
        result = await service.generate_summary("")
        
        assert result == ""
    
    @pytest.mark.asyncio
    async def test_generate_summary_whitespace_transcription(self):
        """测试只有空白的转写文本返回空总结"""
        config = ConfigManager("nonexistent.yaml")
        service = SummaryService(config)
        
        result = await service.generate_summary("   \n\t  ")
        
        assert result == ""
    
    @pytest.mark.asyncio
    async def test_generate_summary_cli_error(self):
        """
        测试 Claude CLI 错误时抛出异常
        
        Validates: Requirements 3.6
        """
        config = ConfigManager("nonexistent.yaml")
        service = SummaryService(config)
        
        with patch.object(service, '_run_claude_cli', new_callable=AsyncMock) as mock_cli:
            mock_cli.side_effect = ClaudeCLIError("CLI 不可用")
            
            with pytest.raises(ClaudeCLIError) as exc_info:
                await service.generate_summary("内容")
            
            assert "CLI 不可用" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_generate_summary_timeout_error(self):
        """测试超时错误"""
        config = ConfigManager("nonexistent.yaml")
        service = SummaryService(config)
        
        with patch.object(service, '_run_claude_cli', new_callable=AsyncMock) as mock_cli:
            mock_cli.side_effect = SummaryTimeoutError("超时")
            
            with pytest.raises(SummaryTimeoutError):
                await service.generate_summary("内容")


class TestSummaryServiceUpdateSummary:
    """测试 update_summary 方法"""
    
    @pytest.mark.asyncio
    async def test_update_summary_success(self):
        """测试成功更新总结"""
        config = ConfigManager("nonexistent.yaml")
        service = SummaryService(config)
        
        mock_result = "# 更新后的总结"
        
        with patch.object(service, '_run_claude_cli', new_callable=AsyncMock) as mock_cli:
            mock_cli.return_value = mock_result
            
            result = await service.update_summary(
                transcription="原始内容",
                current_summary="当前总结",
                edit_request="请补充细节"
            )
            
            assert result == mock_result
            mock_cli.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_summary_with_history(self):
        """测试带对话历史的更新"""
        config = ConfigManager("nonexistent.yaml")
        service = SummaryService(config)
        
        mock_result = "更新结果"
        
        with patch.object(service, '_run_claude_cli', new_callable=AsyncMock) as mock_cli:
            mock_cli.return_value = mock_result
            
            result = await service.update_summary(
                transcription="内容",
                current_summary="总结",
                edit_request="修改",
                chat_history=[{"role": "user", "content": "问题"}]
            )
            
            assert result == mock_result
    
    @pytest.mark.asyncio
    async def test_update_summary_cli_error(self):
        """测试更新时 CLI 错误"""
        config = ConfigManager("nonexistent.yaml")
        service = SummaryService(config)
        
        with patch.object(service, '_run_claude_cli', new_callable=AsyncMock) as mock_cli:
            mock_cli.side_effect = ClaudeCLIError("错误")
            
            with pytest.raises(ClaudeCLIError):
                await service.update_summary(
                    transcription="内容",
                    current_summary="总结",
                    edit_request="修改"
                )


class TestSummaryServiceRunClaudeCLI:
    """测试 _run_claude_cli 方法"""
    
    @pytest.mark.asyncio
    async def test_run_claude_cli_success(self):
        """测试成功执行 Claude CLI"""
        config = ConfigManager("nonexistent.yaml")
        service = SummaryService(config)
        
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
        service = SummaryService(config)
        
        with patch('asyncio.create_subprocess_shell', new_callable=AsyncMock):
            with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError()):
                with pytest.raises(SummaryTimeoutError) as exc_info:
                    await service._run_claude_cli("test prompt")
                
                assert "超时" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_run_claude_cli_not_found(self):
        """测试 CLI 命令未找到"""
        config = ConfigManager("nonexistent.yaml")
        service = SummaryService(config)
        
        with patch('asyncio.create_subprocess_shell', side_effect=FileNotFoundError()):
            with pytest.raises(ClaudeCLIError) as exc_info:
                await service._run_claude_cli("test prompt")
            
            assert "未安装" in str(exc_info.value) or "不可用" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_run_claude_cli_nonzero_return(self):
        """测试 CLI 返回非零状态码"""
        config = ConfigManager("nonexistent.yaml")
        service = SummaryService(config)
        
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(
            return_value=(b"", b"Error message")
        )
        
        with patch('asyncio.create_subprocess_shell', return_value=mock_process):
            with patch('asyncio.wait_for', new_callable=AsyncMock) as mock_wait:
                mock_wait.return_value = (b"", b"Error message")
                mock_process.returncode = 1
                
                with pytest.raises(ClaudeCLIError) as exc_info:
                    await service._run_claude_cli("test prompt")
                
                assert "错误" in str(exc_info.value)


class TestSummaryServiceExceptions:
    """测试异常类"""
    
    def test_summary_error_is_exception(self):
        """测试 SummaryError 是 Exception 子类"""
        assert issubclass(SummaryError, Exception)
    
    def test_claude_cli_error_is_summary_error(self):
        """测试 ClaudeCLIError 是 SummaryError 子类"""
        assert issubclass(ClaudeCLIError, SummaryError)
    
    def test_summary_timeout_error_is_summary_error(self):
        """测试 SummaryTimeoutError 是 SummaryError 子类"""
        assert issubclass(SummaryTimeoutError, SummaryError)
    
    def test_exception_message(self):
        """测试异常消息"""
        error = ClaudeCLIError("测试错误消息")
        assert str(error) == "测试错误消息"


class TestSummaryServiceConstants:
    """测试常量"""
    
    def test_default_summary_prompt_exists(self):
        """测试默认总结 prompt 存在"""
        assert DEFAULT_SUMMARY_PROMPT is not None
        assert "{transcription}" in DEFAULT_SUMMARY_PROMPT
    
    def test_default_update_prompt_exists(self):
        """测试默认更新 prompt 存在"""
        assert DEFAULT_UPDATE_PROMPT is not None
        assert "{transcription}" in DEFAULT_UPDATE_PROMPT
        assert "{current_summary}" in DEFAULT_UPDATE_PROMPT
        assert "{edit_request}" in DEFAULT_UPDATE_PROMPT
