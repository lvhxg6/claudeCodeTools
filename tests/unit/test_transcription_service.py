# TranscriptionService 单元测试
# TranscriptionService Unit Tests

"""
TranscriptionService 转写服务的单元测试。

测试覆盖：
- transcribe() 方法调用 Whisper API
- check_health() 健康检查方法
- 错误处理（连接错误、超时、API 错误）
- MIME 类型获取

Requirements:
- 2.1: 音频文件上传完成后调用 Whisper_Service 进行语音转文字
- 2.2: 使用 OpenAI 兼容的 /v1/audio/transcriptions 接口
- 2.4: Whisper_Service 不可用时显示服务不可用的错误信息
- 2.5: 转写完成后保存 Transcription 并进入总结阶段
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from src.transcription_service import (
    TranscriptionService,
    TranscriptionError,
    WhisperServiceError,
    TranscriptionTimeoutError,
)
from src.config_manager import ConfigManager


class TestTranscriptionServiceInit:
    """测试 TranscriptionService 初始化"""
    
    def test_init_with_config(self):
        """测试使用配置初始化"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        assert service.config is config
        assert service._client is None
    
    def test_init_stores_config_reference(self):
        """测试初始化保存配置引用"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        assert service.config.get_whisper_url() == "http://localhost:8765"


class TestTranscriptionServiceGetMimeType:
    """测试 _get_mime_type 方法"""
    
    def test_mp3_mime_type(self):
        """测试 MP3 文件的 MIME 类型"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        assert service._get_mime_type("meeting.mp3") == "audio/mpeg"
    
    def test_mp3_uppercase_mime_type(self):
        """测试大写 MP3 文件的 MIME 类型"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        assert service._get_mime_type("meeting.MP3") == "audio/mpeg"
    
    def test_wav_mime_type(self):
        """测试 WAV 文件的 MIME 类型"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        assert service._get_mime_type("recording.wav") == "audio/wav"
    
    def test_wav_uppercase_mime_type(self):
        """测试大写 WAV 文件的 MIME 类型"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        assert service._get_mime_type("recording.WAV") == "audio/wav"
    
    def test_m4a_mime_type(self):
        """测试 M4A 文件的 MIME 类型"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        assert service._get_mime_type("audio.m4a") == "audio/mp4"
    
    def test_m4a_uppercase_mime_type(self):
        """测试大写 M4A 文件的 MIME 类型"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        assert service._get_mime_type("audio.M4A") == "audio/mp4"
    
    def test_unknown_extension_defaults_to_mpeg(self):
        """测试未知扩展名默认返回 audio/mpeg"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        assert service._get_mime_type("audio.ogg") == "audio/mpeg"
        assert service._get_mime_type("audio.flac") == "audio/mpeg"
        assert service._get_mime_type("audio.unknown") == "audio/mpeg"


class TestTranscriptionServiceGetBaseUrl:
    """测试 _get_base_url 方法"""
    
    def test_get_base_url_without_trailing_slash(self):
        """测试获取基础 URL（无尾部斜杠）"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        # 默认 URL 是 http://localhost:8765
        assert service._get_base_url() == "http://localhost:8765"
    
    def test_get_base_url_strips_trailing_slash(self, tmp_path):
        """测试获取基础 URL 时去除尾部斜杠"""
        import yaml
        config_file = tmp_path / "config.yaml"
        config_data = {
            "whisper": {
                "url": "http://whisper-server:9000/"
            }
        }
        config_file.write_text(yaml.dump(config_data), encoding='utf-8')
        
        config = ConfigManager(str(config_file))
        service = TranscriptionService(config)
        
        assert service._get_base_url() == "http://whisper-server:9000"


class TestTranscriptionServiceExtractErrorDetail:
    """测试 _extract_error_detail 方法"""
    
    def test_extract_error_from_error_dict(self):
        """测试从 error 字典中提取错误详情"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "error": {"message": "Invalid audio format"}
        }
        
        result = service._extract_error_detail(mock_response)
        assert result == "Invalid audio format"
    
    def test_extract_error_from_error_string(self):
        """测试从 error 字符串中提取错误详情"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "error": "Something went wrong"
        }
        
        result = service._extract_error_detail(mock_response)
        assert result == "Something went wrong"
    
    def test_extract_error_from_detail_field(self):
        """测试从 detail 字段中提取错误详情"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "detail": "File too large"
        }
        
        result = service._extract_error_detail(mock_response)
        assert result == "File too large"
    
    def test_extract_error_from_message_field(self):
        """测试从 message 字段中提取错误详情"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": "Service unavailable"
        }
        
        result = service._extract_error_detail(mock_response)
        assert result == "Service unavailable"
    
    def test_extract_error_fallback_to_status_code(self):
        """测试无法解析 JSON 时回退到状态码"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        mock_response = MagicMock()
        mock_response.json.side_effect = Exception("Invalid JSON")
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        result = service._extract_error_detail(mock_response)
        assert "HTTP 500" in result
        assert "Internal Server Error" in result


class TestTranscriptionServiceTranscribe:
    """测试 transcribe 方法 - Validates: Requirements 2.1, 2.2"""
    
    @pytest.mark.asyncio
    async def test_transcribe_success(self):
        """测试成功转写音频文件"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        # 模拟成功的 HTTP 响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "这是会议内容的转写结果"}
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.is_closed = False
        
        service._client = mock_client
        
        audio_data = b"fake audio data"
        result = await service.transcribe(audio_data, "meeting.mp3", "zh")
        
        assert result == "这是会议内容的转写结果"
        mock_client.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_transcribe_uses_correct_endpoint(self):
        """测试转写使用正确的 API 端点 - Validates: Requirements 2.2"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "转写结果"}
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.is_closed = False
        
        service._client = mock_client
        
        await service.transcribe(b"audio", "test.mp3", "zh")
        
        # 验证调用的 URL 包含正确的端点
        call_args = mock_client.post.call_args
        url = call_args[0][0]
        assert "/v1/audio/transcriptions" in url
    
    @pytest.mark.asyncio
    async def test_transcribe_sends_correct_data(self):
        """测试转写发送正确的请求数据"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "转写结果"}
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.is_closed = False
        
        service._client = mock_client
        
        audio_data = b"test audio content"
        await service.transcribe(audio_data, "meeting.mp3", "en")
        
        # 验证请求参数
        call_args = mock_client.post.call_args
        assert "files" in call_args.kwargs
        assert "data" in call_args.kwargs
        
        data = call_args.kwargs["data"]
        assert data["model"] == "whisper-1"
        assert data["language"] == "en"
    
    @pytest.mark.asyncio
    async def test_transcribe_api_error_raises_whisper_service_error(self):
        """测试 API 返回错误时抛出 WhisperServiceError - Validates: Requirements 2.4"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Invalid audio format"}
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.is_closed = False
        
        service._client = mock_client
        
        with pytest.raises(WhisperServiceError) as exc_info:
            await service.transcribe(b"audio", "test.mp3", "zh")
        
        assert "Invalid audio format" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_transcribe_timeout_raises_timeout_error(self):
        """测试请求超时时抛出 TranscriptionTimeoutError"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("Request timed out")
        mock_client.is_closed = False
        
        service._client = mock_client
        
        with pytest.raises(TranscriptionTimeoutError) as exc_info:
            await service.transcribe(b"audio", "test.mp3", "zh")
        
        assert "超时" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_transcribe_connect_error_raises_whisper_service_error(self):
        """测试连接错误时抛出 WhisperServiceError - Validates: Requirements 2.4"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        mock_client.is_closed = False
        
        service._client = mock_client
        
        with pytest.raises(WhisperServiceError) as exc_info:
            await service.transcribe(b"audio", "test.mp3", "zh")
        
        assert "不可用" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_transcribe_http_error_raises_whisper_service_error(self):
        """测试 HTTP 错误时抛出 WhisperServiceError"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.HTTPError("HTTP error occurred")
        mock_client.is_closed = False
        
        service._client = mock_client
        
        with pytest.raises(WhisperServiceError) as exc_info:
            await service.transcribe(b"audio", "test.mp3", "zh")
        
        assert "请求失败" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_transcribe_unknown_error_raises_transcription_error(self):
        """测试未知错误时抛出 TranscriptionError"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Unknown error")
        mock_client.is_closed = False
        
        service._client = mock_client
        
        with pytest.raises(TranscriptionError) as exc_info:
            await service.transcribe(b"audio", "test.mp3", "zh")
        
        assert "Unknown error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_transcribe_empty_text_response(self):
        """测试 API 返回空文本"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": ""}
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.is_closed = False
        
        service._client = mock_client
        
        result = await service.transcribe(b"audio", "test.mp3", "zh")
        
        assert result == ""
    
    @pytest.mark.asyncio
    async def test_transcribe_missing_text_field(self):
        """测试 API 响应缺少 text 字段"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}  # 没有 text 字段
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.is_closed = False
        
        service._client = mock_client
        
        result = await service.transcribe(b"audio", "test.mp3", "zh")
        
        assert result == ""
    
    @pytest.mark.asyncio
    async def test_transcribe_default_language_is_chinese(self):
        """测试默认语言为中文"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "转写结果"}
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.is_closed = False
        
        service._client = mock_client
        
        # 不指定语言参数
        await service.transcribe(b"audio", "test.mp3")
        
        call_args = mock_client.post.call_args
        data = call_args.kwargs["data"]
        assert data["language"] == "zh"


class TestTranscriptionServiceCheckHealth:
    """测试 check_health 方法 - Validates: Requirements 8.1, 8.2"""
    
    @pytest.mark.asyncio
    async def test_check_health_returns_true_when_healthy(self):
        """测试服务健康时返回 True"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.is_closed = False
        
        service._client = mock_client
        
        result = await service.check_health()
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_health_uses_correct_endpoint(self):
        """测试健康检查使用正确的端点"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.is_closed = False
        
        service._client = mock_client
        
        await service.check_health()
        
        call_args = mock_client.get.call_args
        url = call_args[0][0]
        assert "/health" in url
    
    @pytest.mark.asyncio
    async def test_check_health_returns_false_on_non_200_status(self):
        """测试非 200 状态码时返回 False"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        mock_response = MagicMock()
        mock_response.status_code = 503
        
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.is_closed = False
        
        service._client = mock_client
        
        result = await service.check_health()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_check_health_returns_false_on_timeout(self):
        """测试超时时返回 False"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("Timeout")
        mock_client.is_closed = False
        
        service._client = mock_client
        
        result = await service.check_health()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_check_health_returns_false_on_connect_error(self):
        """测试连接错误时返回 False"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")
        mock_client.is_closed = False
        
        service._client = mock_client
        
        result = await service.check_health()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_check_health_returns_false_on_exception(self):
        """测试其他异常时返回 False"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Unknown error")
        mock_client.is_closed = False
        
        service._client = mock_client
        
        result = await service.check_health()
        
        assert result is False


class TestTranscriptionServiceClientManagement:
    """测试 HTTP 客户端管理"""
    
    def test_get_client_creates_client_when_none(self):
        """测试客户端为空时创建新客户端"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        assert service._client is None
        
        client = service._get_client()
        
        assert client is not None
        assert isinstance(client, httpx.AsyncClient)
    
    def test_get_client_reuses_existing_client(self):
        """测试复用现有客户端"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        client1 = service._get_client()
        client2 = service._get_client()
        
        assert client1 is client2
    
    @pytest.mark.asyncio
    async def test_close_closes_client(self):
        """测试关闭客户端"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        # 创建客户端
        client = service._get_client()
        assert not client.is_closed
        
        # 关闭
        await service.close()
        
        assert service._client is None
    
    @pytest.mark.asyncio
    async def test_close_when_no_client(self):
        """测试没有客户端时关闭不报错"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        # 不应抛出异常
        await service.close()
        
        assert service._client is None
    
    @pytest.mark.asyncio
    async def test_get_client_creates_new_after_close(self):
        """测试关闭后重新创建客户端"""
        config = ConfigManager("nonexistent.yaml")
        service = TranscriptionService(config)
        
        client1 = service._get_client()
        await service.close()
        client2 = service._get_client()
        
        assert client1 is not client2


class TestTranscriptionServiceConstants:
    """测试服务常量"""
    
    def test_transcription_endpoint_constant(self):
        """测试转写端点常量"""
        assert TranscriptionService.TRANSCRIPTION_ENDPOINT == "/v1/audio/transcriptions"
    
    def test_health_endpoint_constant(self):
        """测试健康检查端点常量"""
        assert TranscriptionService.HEALTH_ENDPOINT == "/health"
    
    def test_default_model_constant(self):
        """测试默认模型常量"""
        assert TranscriptionService.DEFAULT_MODEL == "whisper-1"


class TestTranscriptionExceptions:
    """测试异常类"""
    
    def test_transcription_error_is_exception(self):
        """测试 TranscriptionError 是 Exception 子类"""
        error = TranscriptionError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"
    
    def test_whisper_service_error_is_transcription_error(self):
        """测试 WhisperServiceError 是 TranscriptionError 子类"""
        error = WhisperServiceError("Service unavailable")
        assert isinstance(error, TranscriptionError)
        assert isinstance(error, Exception)
        assert str(error) == "Service unavailable"
    
    def test_transcription_timeout_error_is_transcription_error(self):
        """测试 TranscriptionTimeoutError 是 TranscriptionError 子类"""
        error = TranscriptionTimeoutError("Request timed out")
        assert isinstance(error, TranscriptionError)
        assert isinstance(error, Exception)
        assert str(error) == "Request timed out"
