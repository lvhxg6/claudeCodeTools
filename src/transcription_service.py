# 转写服务
# Transcription Service

"""
转写服务模块 - 封装 Whisper API 调用，实现语音转文字功能。

支持功能：
- 调用 Whisper API 进行语音转文字
- 健康检查 Whisper 服务状态
- 错误处理和超时管理

Requirements:
- 2.1: 音频文件上传完成后调用 Whisper_Service 进行语音转文字
- 2.2: 使用 OpenAI 兼容的 /v1/audio/transcriptions 接口
- 2.4: Whisper_Service 不可用时显示服务不可用的错误信息
- 2.5: 转写完成后保存 Transcription 并进入总结阶段
"""

import logging
from typing import Optional

import httpx

from src.config_manager import ConfigManager


# 配置日志
logger = logging.getLogger(__name__)


class TranscriptionError(Exception):
    """转写错误异常基类"""
    pass


class WhisperServiceError(TranscriptionError):
    """Whisper 服务错误异常
    
    当 Whisper 服务不可用或返回错误时抛出。
    
    Validates: Requirements 2.4
    """
    pass


class TranscriptionTimeoutError(TranscriptionError):
    """转写超时错误异常"""
    pass


class TranscriptionService:
    """
    语音转文字服务，封装 Whisper API 调用。
    
    使用 OpenAI 兼容的 /v1/audio/transcriptions 接口进行语音转文字。
    
    Attributes:
        config: 配置管理器实例
        _client: HTTP 客户端实例
    
    Requirements:
        - 2.1: 音频文件上传完成后调用 Whisper_Service 进行语音转文字
        - 2.2: 使用 OpenAI 兼容的 /v1/audio/transcriptions 接口
        - 2.4: Whisper_Service 不可用时显示服务不可用的错误信息
    
    Example:
        >>> config = ConfigManager()
        >>> service = TranscriptionService(config)
        >>> is_healthy = await service.check_health()
        >>> if is_healthy:
        ...     text = await service.transcribe(audio_bytes, "meeting.mp3")
    """
    
    # OpenAI 兼容的转写接口路径
    TRANSCRIPTION_ENDPOINT = "/v1/audio/transcriptions"
    # 健康检查接口路径
    HEALTH_ENDPOINT = "/health"
    # 默认模型名称（Whisper 服务可能需要）
    DEFAULT_MODEL = "whisper-1"
    
    def __init__(self, config: ConfigManager):
        """
        初始化转写服务。
        
        Args:
            config: 配置管理器实例，用于获取 Whisper 服务地址和超时设置
        
        Example:
            >>> config = ConfigManager()
            >>> service = TranscriptionService(config)
        """
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
    
    def _get_client(self) -> httpx.AsyncClient:
        """
        获取或创建 HTTP 客户端。
        
        使用懒加载模式创建客户端，避免在初始化时创建。
        
        Returns:
            httpx.AsyncClient: HTTP 客户端实例
        """
        if self._client is None or self._client.is_closed:
            timeout = httpx.Timeout(
                timeout=self.config.get_whisper_timeout(),
                connect=10.0  # 连接超时 10 秒
            )
            self._client = httpx.AsyncClient(timeout=timeout)
        return self._client
    
    async def close(self) -> None:
        """
        关闭 HTTP 客户端。
        
        在服务不再使用时调用，释放资源。
        
        Example:
            >>> service = TranscriptionService(config)
            >>> # 使用服务...
            >>> await service.close()
        """
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    def _get_base_url(self) -> str:
        """
        获取 Whisper 服务基础 URL。
        
        Returns:
            str: Whisper 服务的基础 URL
        """
        return self.config.get_whisper_url().rstrip("/")
    
    async def transcribe(
        self, 
        audio_file: bytes, 
        filename: str, 
        language: str = "zh"
    ) -> str:
        """
        将音频文件转写为文字。
        
        调用 Whisper API 的 OpenAI 兼容接口进行语音转文字。
        
        Args:
            audio_file: 音频文件的二进制内容
            filename: 音频文件名（用于确定 MIME 类型）
            language: 语言代码，默认为 "zh"（中文）
        
        Returns:
            str: 转写后的文字内容
        
        Raises:
            WhisperServiceError: Whisper 服务不可用或返回错误
            TranscriptionTimeoutError: 转写请求超时
            TranscriptionError: 其他转写错误
        
        Validates: Requirements 2.1, 2.2, 2.4
        
        Example:
            >>> config = ConfigManager()
            >>> service = TranscriptionService(config)
            >>> with open("meeting.mp3", "rb") as f:
            ...     audio_data = f.read()
            >>> text = await service.transcribe(audio_data, "meeting.mp3", "zh")
            >>> print(text)
            '会议内容...'
        """
        url = f"{self._get_base_url()}{self.TRANSCRIPTION_ENDPOINT}"
        
        # 构建 multipart/form-data 请求
        # OpenAI 兼容接口需要 file、model 和可选的 language 参数
        files = {
            "file": (filename, audio_file, self._get_mime_type(filename))
        }
        data = {
            "model": self.DEFAULT_MODEL,
            "language": language
        }
        
        logger.info(
            f"开始转写音频文件: {filename}, 语言: {language}, "
            f"文件大小: {len(audio_file)} bytes"
        )
        
        try:
            client = self._get_client()
            response = await client.post(url, files=files, data=data)
            
            # 检查响应状态
            if response.status_code == 200:
                result = response.json()
                # OpenAI 兼容接口返回 {"text": "转写内容"}
                transcription = result.get("text", "")
                logger.info(
                    f"转写完成: {filename}, 结果长度: {len(transcription)} 字符"
                )
                return transcription
            else:
                error_detail = self._extract_error_detail(response)
                logger.error(
                    f"Whisper API 返回错误: status={response.status_code}, "
                    f"detail={error_detail}"
                )
                raise WhisperServiceError(
                    f"转写失败: {error_detail}"
                )
        
        except httpx.TimeoutException as e:
            logger.error(f"转写请求超时: {filename}, error={e}")
            raise TranscriptionTimeoutError(
                f"转写请求超时，请稍后重试"
            ) from e
        
        except httpx.ConnectError as e:
            logger.error(f"无法连接到 Whisper 服务: {url}, error={e}")
            raise WhisperServiceError(
                "语音转写服务暂时不可用，请检查服务状态"
            ) from e
        
        except httpx.HTTPError as e:
            logger.error(f"HTTP 请求错误: {e}")
            raise WhisperServiceError(
                f"转写服务请求失败: {str(e)}"
            ) from e
        
        except TranscriptionError:
            # 重新抛出已知的转写错误（包括 WhisperServiceError 和 TranscriptionTimeoutError）
            raise
        
        except Exception as e:
            logger.error(f"转写过程发生未知错误: {e}")
            raise TranscriptionError(
                f"转写失败: {str(e)}"
            ) from e
    
    async def check_health(self) -> bool:
        """
        检查 Whisper 服务健康状态。
        
        调用 Whisper 服务的 /health 端点检查服务是否可用。
        
        Returns:
            bool: 服务健康返回 True，否则返回 False
        
        Validates: Requirements 8.1, 8.2
        
        Example:
            >>> config = ConfigManager()
            >>> service = TranscriptionService(config)
            >>> is_healthy = await service.check_health()
            >>> if is_healthy:
            ...     print("Whisper 服务可用")
            ... else:
            ...     print("Whisper 服务不可用")
        """
        url = f"{self._get_base_url()}{self.HEALTH_ENDPOINT}"
        
        try:
            client = self._get_client()
            # 健康检查使用较短的超时时间
            response = await client.get(url, timeout=10.0)
            
            if response.status_code == 200:
                logger.debug(f"Whisper 服务健康检查通过: {url}")
                return True
            else:
                logger.warning(
                    f"Whisper 服务健康检查失败: status={response.status_code}"
                )
                return False
        
        except httpx.TimeoutException:
            logger.warning(f"Whisper 服务健康检查超时: {url}")
            return False
        
        except httpx.ConnectError:
            logger.warning(f"无法连接到 Whisper 服务: {url}")
            return False
        
        except Exception as e:
            logger.warning(f"Whisper 服务健康检查异常: {e}")
            return False
    
    def _get_mime_type(self, filename: str) -> str:
        """
        根据文件名获取 MIME 类型。
        
        Args:
            filename: 文件名
        
        Returns:
            str: MIME 类型字符串
        """
        filename_lower = filename.lower()
        
        if filename_lower.endswith(".mp3"):
            return "audio/mpeg"
        elif filename_lower.endswith(".wav"):
            return "audio/wav"
        elif filename_lower.endswith(".m4a"):
            return "audio/mp4"
        else:
            # 默认使用通用音频类型
            return "audio/mpeg"
    
    def _extract_error_detail(self, response: httpx.Response) -> str:
        """
        从响应中提取错误详情。
        
        Args:
            response: HTTP 响应对象
        
        Returns:
            str: 错误详情字符串
        """
        try:
            error_data = response.json()
            # 尝试多种常见的错误格式
            if "error" in error_data:
                error = error_data["error"]
                if isinstance(error, dict):
                    return error.get("message", str(error))
                return str(error)
            elif "detail" in error_data:
                return str(error_data["detail"])
            elif "message" in error_data:
                return str(error_data["message"])
            else:
                return str(error_data)
        except Exception:
            return f"HTTP {response.status_code}: {response.text[:200]}"
