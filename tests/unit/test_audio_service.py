# AudioService 单元测试
# AudioService Unit Tests

"""
AudioService 音频服务的单元测试。

测试覆盖：
- validate_audio_format() 函数
- 支持的文件格式（mp3、wav、m4a）
- 大小写不敏感验证
- 边缘情况处理

Requirements:
- 1.2: 验证文件格式是否为支持的类型（mp3、wav、m4a）
- 1.3: 上传不支持的文件格式时显示明确的错误提示信息
"""

import pytest

from src.audio_service import (
    validate_audio_format,
    get_supported_formats,
    get_format_error_message,
    SUPPORTED_AUDIO_EXTENSIONS,
)


class TestValidateAudioFormat:
    """测试 validate_audio_format 函数"""
    
    # ===== 支持的格式测试 =====
    
    def test_mp3_format_lowercase(self):
        """测试小写 mp3 格式"""
        assert validate_audio_format("meeting.mp3") is True
    
    def test_mp3_format_uppercase(self):
        """测试大写 MP3 格式"""
        assert validate_audio_format("meeting.MP3") is True
    
    def test_mp3_format_mixed_case(self):
        """测试混合大小写 Mp3 格式"""
        assert validate_audio_format("meeting.Mp3") is True
    
    def test_wav_format_lowercase(self):
        """测试小写 wav 格式"""
        assert validate_audio_format("recording.wav") is True
    
    def test_wav_format_uppercase(self):
        """测试大写 WAV 格式"""
        assert validate_audio_format("recording.WAV") is True
    
    def test_m4a_format_lowercase(self):
        """测试小写 m4a 格式"""
        assert validate_audio_format("audio.m4a") is True
    
    def test_m4a_format_uppercase(self):
        """测试大写 M4A 格式"""
        assert validate_audio_format("audio.M4A") is True
    
    # ===== 不支持的格式测试 =====
    
    def test_txt_format_rejected(self):
        """测试 txt 格式被拒绝"""
        assert validate_audio_format("document.txt") is False
    
    def test_pdf_format_rejected(self):
        """测试 pdf 格式被拒绝"""
        assert validate_audio_format("document.pdf") is False
    
    def test_jpg_format_rejected(self):
        """测试 jpg 格式被拒绝"""
        assert validate_audio_format("image.jpg") is False
    
    def test_mp4_format_rejected(self):
        """测试 mp4 视频格式被拒绝"""
        assert validate_audio_format("video.mp4") is False
    
    def test_ogg_format_rejected(self):
        """测试 ogg 格式被拒绝"""
        assert validate_audio_format("audio.ogg") is False
    
    def test_flac_format_rejected(self):
        """测试 flac 格式被拒绝"""
        assert validate_audio_format("audio.flac") is False
    
    # ===== 边缘情况测试 =====
    
    def test_empty_filename(self):
        """测试空文件名"""
        assert validate_audio_format("") is False
    
    def test_no_extension(self):
        """测试没有扩展名的文件"""
        assert validate_audio_format("meeting") is False
    
    def test_only_extension(self):
        """测试只有扩展名的文件（被视为隐藏文件，无扩展名）"""
        # ".mp3" 在 Unix 系统中被视为隐藏文件名，没有扩展名
        # os.path.splitext(".mp3") 返回 ('.mp3', '')
        assert validate_audio_format(".mp3") is False
    
    def test_multiple_dots(self):
        """测试多个点号的文件名"""
        assert validate_audio_format("meeting.2024.01.15.mp3") is True
    
    def test_hidden_file_with_extension(self):
        """测试隐藏文件带扩展名"""
        assert validate_audio_format(".hidden.mp3") is True
    
    def test_path_with_filename(self):
        """测试带路径的文件名"""
        assert validate_audio_format("/path/to/meeting.mp3") is True
        assert validate_audio_format("./relative/path/meeting.wav") is True
    
    def test_windows_path(self):
        """测试 Windows 风格路径"""
        assert validate_audio_format("C:\\Users\\meeting.m4a") is True
    
    def test_filename_with_spaces(self):
        """测试带空格的文件名"""
        assert validate_audio_format("my meeting recording.mp3") is True
    
    def test_unicode_filename(self):
        """测试 Unicode 文件名"""
        assert validate_audio_format("会议录音.mp3") is True
        assert validate_audio_format("会议录音.txt") is False
    
    def test_extension_only_dot(self):
        """测试只有点号没有扩展名"""
        assert validate_audio_format("meeting.") is False
    
    def test_double_extension(self):
        """测试双扩展名（取最后一个）"""
        assert validate_audio_format("meeting.txt.mp3") is True
        assert validate_audio_format("meeting.mp3.txt") is False


class TestGetSupportedFormats:
    """测试 get_supported_formats 函数"""
    
    def test_returns_set(self):
        """测试返回集合类型"""
        formats = get_supported_formats()
        assert isinstance(formats, set)
    
    def test_contains_mp3(self):
        """测试包含 mp3"""
        formats = get_supported_formats()
        assert "mp3" in formats
    
    def test_contains_wav(self):
        """测试包含 wav"""
        formats = get_supported_formats()
        assert "wav" in formats
    
    def test_contains_m4a(self):
        """测试包含 m4a"""
        formats = get_supported_formats()
        assert "m4a" in formats
    
    def test_returns_copy(self):
        """测试返回副本（修改不影响原集合）"""
        formats = get_supported_formats()
        formats.add("ogg")
        
        # 原集合不应被修改
        assert "ogg" not in SUPPORTED_AUDIO_EXTENSIONS


class TestGetFormatErrorMessage:
    """测试 get_format_error_message 函数"""
    
    def test_returns_string(self):
        """测试返回字符串类型"""
        msg = get_format_error_message()
        assert isinstance(msg, str)
    
    def test_contains_supported_formats(self):
        """测试包含支持的格式"""
        msg = get_format_error_message()
        assert "mp3" in msg
        assert "wav" in msg
        assert "m4a" in msg
    
    def test_is_user_friendly(self):
        """测试消息用户友好"""
        msg = get_format_error_message()
        assert "不支持" in msg or "请上传" in msg
