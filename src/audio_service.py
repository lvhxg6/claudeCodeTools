# 音频服务
# Audio Service

"""
音频服务模块 - 负责音频文件的验证和处理。

支持功能：
- 文件格式验证（mp3、wav、m4a）
- 文件大小检查

Requirements:
- 1.2: 验证文件格式是否为支持的类型（mp3、wav、m4a）
- 1.3: 上传不支持的文件格式时显示明确的错误提示信息
"""

import os
from typing import Set


# 支持的音频文件扩展名（小写）
SUPPORTED_AUDIO_EXTENSIONS: Set[str] = {"mp3", "wav", "m4a"}


class AudioFormatError(Exception):
    """音频格式错误异常"""
    pass


def validate_audio_format(filename: str) -> bool:
    """
    验证音频文件格式是否为支持的类型。
    
    检查文件名的扩展名是否为支持的音频格式（mp3、wav、m4a）。
    扩展名检查不区分大小写。
    
    Args:
        filename: 文件名（可以包含路径）
    
    Returns:
        bool: 如果文件格式受支持返回 True，否则返回 False
    
    Validates: Requirements 1.2
    
    Property 1: 文件格式验证
        *对于任意* 文件名和扩展名，文件格式验证函数应该：
        - 当扩展名为 mp3、wav、m4a（不区分大小写）时返回 true
        - 当扩展名为其他值时返回 false
    
    Examples:
        >>> validate_audio_format("meeting.mp3")
        True
        >>> validate_audio_format("meeting.MP3")
        True
        >>> validate_audio_format("meeting.wav")
        True
        >>> validate_audio_format("meeting.m4a")
        True
        >>> validate_audio_format("meeting.txt")
        False
        >>> validate_audio_format("meeting")
        False
        >>> validate_audio_format("")
        False
    """
    if not filename:
        return False
    
    # 获取文件扩展名（不包含点号）
    # os.path.splitext 返回 (root, ext)，其中 ext 包含点号
    _, ext = os.path.splitext(filename)
    
    # 如果没有扩展名，返回 False
    if not ext:
        return False
    
    # 移除点号并转换为小写进行比较
    ext_lower = ext[1:].lower()  # 去掉开头的点号
    
    return ext_lower in SUPPORTED_AUDIO_EXTENSIONS


def get_supported_formats() -> Set[str]:
    """
    获取支持的音频文件格式列表。
    
    Returns:
        Set[str]: 支持的文件扩展名集合（小写）
    
    Example:
        >>> formats = get_supported_formats()
        >>> "mp3" in formats
        True
    """
    return SUPPORTED_AUDIO_EXTENSIONS.copy()


def get_format_error_message() -> str:
    """
    获取文件格式错误的提示信息。
    
    Returns:
        str: 用户友好的错误提示信息
    
    Validates: Requirements 1.3
    
    Example:
        >>> msg = get_format_error_message()
        >>> "mp3" in msg
        True
    """
    formats = ", ".join(sorted(SUPPORTED_AUDIO_EXTENSIONS))
    return f"不支持的文件格式，请上传 {formats} 文件"
