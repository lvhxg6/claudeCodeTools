# 文件验证属性测试
# File Validation Property-Based Tests

"""
文件格式验证的属性测试。

使用 Hypothesis 进行属性测试，验证文件格式验证函数的核心属性：
- Property 1: 文件格式验证

**Feature: meeting-summary**
**Validates: Requirements 1.2**
"""

import pytest
from hypothesis import given, settings, assume, example
from hypothesis import strategies as st

from src.audio_service import (
    validate_audio_format,
    SUPPORTED_AUDIO_EXTENSIONS,
    get_supported_formats
)


# =============================================================================
# 自定义策略 (Custom Strategies)
# =============================================================================

# 支持的音频扩展名列表
SUPPORTED_EXTENSIONS = ["mp3", "wav", "m4a"]


@st.composite
def valid_filenames_without_extension(draw):
    """生成有效的文件名（不含扩展名）"""
    # 使用字母、数字、下划线和连字符
    name = draw(st.text(
        alphabet=st.characters(
            whitelist_categories=('L', 'N'),
            whitelist_characters='_-'
        ),
        min_size=1,
        max_size=50
    ))
    return name


@st.composite
def supported_extensions(draw):
    """生成支持的音频扩展名（包括大小写变体）"""
    ext = draw(st.sampled_from(SUPPORTED_EXTENSIONS))
    # 随机选择大小写变体
    case_variant = draw(st.sampled_from([
        ext.lower(),           # mp3
        ext.upper(),           # MP3
        ext.capitalize(),      # Mp3
        ext.swapcase(),        # 如果是 mp3 -> MP3
    ]))
    return case_variant


@st.composite
def unsupported_extensions(draw):
    """生成不支持的文件扩展名"""
    # 常见的不支持的扩展名
    common_unsupported = [
        "txt", "pdf", "doc", "docx", "xls", "xlsx",
        "jpg", "jpeg", "png", "gif", "bmp",
        "mp4", "avi", "mkv", "mov", "flv",
        "ogg", "flac", "aac", "wma",  # 其他音频格式但不支持
        "zip", "rar", "7z", "tar", "gz",
        "exe", "dll", "so", "py", "js",
        "html", "css", "json", "xml", "yaml"
    ]
    
    # 随机选择一个不支持的扩展名
    ext = draw(st.sampled_from(common_unsupported))
    
    # 确保不在支持列表中
    assume(ext.lower() not in SUPPORTED_EXTENSIONS)
    
    # 随机选择大小写变体
    case_variant = draw(st.sampled_from([
        ext.lower(),
        ext.upper(),
        ext.capitalize()
    ]))
    return case_variant


@st.composite
def random_extensions(draw):
    """生成随机的文件扩展名"""
    ext = draw(st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N')),
        min_size=1,
        max_size=10
    ))
    return ext


@st.composite
def valid_audio_filenames(draw):
    """生成有效的音频文件名（支持的格式）"""
    name = draw(valid_filenames_without_extension())
    ext = draw(supported_extensions())
    return f"{name}.{ext}"


@st.composite
def invalid_audio_filenames(draw):
    """生成无效的音频文件名（不支持的格式）"""
    name = draw(valid_filenames_without_extension())
    ext = draw(unsupported_extensions())
    return f"{name}.{ext}"


@st.composite
def filenames_with_path(draw):
    """生成带路径的文件名"""
    # 生成路径部分
    path_parts = draw(st.lists(
        st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_-'),
            min_size=1,
            max_size=20
        ),
        min_size=0,
        max_size=5
    ))
    
    # 生成文件名
    filename = draw(valid_filenames_without_extension())
    ext = draw(supported_extensions())
    
    # 组合路径
    if path_parts:
        path = "/".join(path_parts)
        return f"{path}/{filename}.{ext}"
    return f"{filename}.{ext}"


# =============================================================================
# Property 1: 文件格式验证
# =============================================================================

class TestProperty1FileFormatValidation:
    """
    **Feature: meeting-summary, Property 1: 文件格式验证**
    
    *对于任意* 文件名和扩展名，文件格式验证函数应该：
    - 当扩展名为 mp3、wav、m4a（不区分大小写）时返回 true
    - 当扩展名为其他值时返回 false
    
    **Validates: Requirements 1.2**
    """
    
    @settings(max_examples=100)
    @given(
        filename=valid_filenames_without_extension(),
        ext=supported_extensions()
    )
    def test_supported_formats_return_true(self, filename: str, ext: str):
        """
        **Feature: meeting-summary, Property 1: 文件格式验证**
        
        验证：对于任意支持的扩展名（mp3、wav、m4a，不区分大小写），
        validate_audio_format 应返回 True。
        
        **Validates: Requirements 1.2**
        """
        # Arrange: 构造完整文件名
        full_filename = f"{filename}.{ext}"
        
        # Act: 验证文件格式
        result = validate_audio_format(full_filename)
        
        # Assert: 应返回 True
        assert result is True, \
            f"Expected True for supported format '{full_filename}', but got {result}"
    
    @settings(max_examples=100)
    @given(
        filename=valid_filenames_without_extension(),
        ext=unsupported_extensions()
    )
    def test_unsupported_formats_return_false(self, filename: str, ext: str):
        """
        **Feature: meeting-summary, Property 1: 文件格式验证**
        
        验证：对于任意不支持的扩展名，validate_audio_format 应返回 False。
        
        **Validates: Requirements 1.2**
        """
        # Arrange: 构造完整文件名
        full_filename = f"{filename}.{ext}"
        
        # Act: 验证文件格式
        result = validate_audio_format(full_filename)
        
        # Assert: 应返回 False
        assert result is False, \
            f"Expected False for unsupported format '{full_filename}', but got {result}"
    
    @settings(max_examples=100)
    @given(ext=st.sampled_from(SUPPORTED_EXTENSIONS))
    def test_case_insensitivity_lowercase(self, ext: str):
        """
        **Feature: meeting-summary, Property 1: 文件格式验证**
        
        验证：小写扩展名应被正确识别为支持的格式。
        
        **Validates: Requirements 1.2**
        """
        # Arrange: 使用小写扩展名
        filename = f"test_file.{ext.lower()}"
        
        # Act & Assert
        assert validate_audio_format(filename) is True, \
            f"Lowercase extension '{ext.lower()}' should be supported"
    
    @settings(max_examples=100)
    @given(ext=st.sampled_from(SUPPORTED_EXTENSIONS))
    def test_case_insensitivity_uppercase(self, ext: str):
        """
        **Feature: meeting-summary, Property 1: 文件格式验证**
        
        验证：大写扩展名应被正确识别为支持的格式。
        
        **Validates: Requirements 1.2**
        """
        # Arrange: 使用大写扩展名
        filename = f"test_file.{ext.upper()}"
        
        # Act & Assert
        assert validate_audio_format(filename) is True, \
            f"Uppercase extension '{ext.upper()}' should be supported"
    
    @settings(max_examples=100)
    @given(ext=st.sampled_from(SUPPORTED_EXTENSIONS))
    def test_case_insensitivity_mixed_case(self, ext: str):
        """
        **Feature: meeting-summary, Property 1: 文件格式验证**
        
        验证：混合大小写扩展名应被正确识别为支持的格式。
        
        **Validates: Requirements 1.2**
        """
        # Arrange: 使用混合大小写扩展名
        mixed_case = "".join(
            c.upper() if i % 2 == 0 else c.lower() 
            for i, c in enumerate(ext)
        )
        filename = f"test_file.{mixed_case}"
        
        # Act & Assert
        assert validate_audio_format(filename) is True, \
            f"Mixed case extension '{mixed_case}' should be supported"
    
    @settings(max_examples=100)
    @given(filename=filenames_with_path())
    def test_filenames_with_path_supported(self, filename: str):
        """
        **Feature: meeting-summary, Property 1: 文件格式验证**
        
        验证：带路径的文件名也应正确验证扩展名。
        
        **Validates: Requirements 1.2**
        """
        # Act: 验证带路径的文件名
        result = validate_audio_format(filename)
        
        # Assert: 应返回 True（因为使用了支持的扩展名）
        assert result is True, \
            f"Expected True for filename with path '{filename}', but got {result}"
    
    @settings(max_examples=100)
    @given(filename=valid_filenames_without_extension())
    def test_filename_without_extension_returns_false(self, filename: str):
        """
        **Feature: meeting-summary, Property 1: 文件格式验证**
        
        验证：没有扩展名的文件名应返回 False。
        
        **Validates: Requirements 1.2**
        """
        # Act: 验证没有扩展名的文件名
        result = validate_audio_format(filename)
        
        # Assert: 应返回 False
        assert result is False, \
            f"Expected False for filename without extension '{filename}', but got {result}"
    
    @settings(max_examples=100)
    @given(
        filename=valid_filenames_without_extension(),
        ext=random_extensions()
    )
    def test_random_extensions_classification(self, filename: str, ext: str):
        """
        **Feature: meeting-summary, Property 1: 文件格式验证**
        
        验证：对于任意随机扩展名，验证结果应与扩展名是否在支持列表中一致。
        
        **Validates: Requirements 1.2**
        """
        # Arrange: 构造完整文件名
        full_filename = f"{filename}.{ext}"
        
        # Act: 验证文件格式
        result = validate_audio_format(full_filename)
        
        # Assert: 结果应与扩展名是否支持一致
        is_supported = ext.lower() in SUPPORTED_EXTENSIONS
        assert result == is_supported, \
            f"For extension '{ext}', expected {is_supported}, but got {result}"


# =============================================================================
# 边界情况测试
# =============================================================================

class TestProperty1EdgeCases:
    """
    **Feature: meeting-summary, Property 1: 文件格式验证 - 边界情况**
    
    测试文件格式验证的边界情况。
    
    **Validates: Requirements 1.2**
    """
    
    def test_empty_filename_returns_false(self):
        """
        **Feature: meeting-summary, Property 1: 文件格式验证**
        
        验证：空文件名应返回 False。
        
        **Validates: Requirements 1.2**
        """
        assert validate_audio_format("") is False, \
            "Empty filename should return False"
    
    def test_only_dot_extension_returns_false(self):
        """
        **Feature: meeting-summary, Property 1: 文件格式验证**
        
        验证：只有点号开头的文件名（如 ".mp3"）应返回 False。
        
        注意：os.path.splitext 将 ".mp3" 视为没有扩展名的隐藏文件，
        因此 ".mp3" 的扩展名为空字符串，应返回 False。
        
        **Validates: Requirements 1.2**
        """
        # os.path.splitext(".mp3") 返回 (".mp3", "")，即没有扩展名
        assert validate_audio_format(".mp3") is False, \
            "'.mp3' should return False as it has no extension (hidden file)"
        assert validate_audio_format(".wav") is False, \
            "'.wav' should return False as it has no extension (hidden file)"
        assert validate_audio_format(".m4a") is False, \
            "'.m4a' should return False as it has no extension (hidden file)"
    
    def test_double_extension_uses_last(self):
        """
        **Feature: meeting-summary, Property 1: 文件格式验证**
        
        验证：双扩展名文件应使用最后一个扩展名进行验证。
        
        **Validates: Requirements 1.2**
        """
        # 最后一个扩展名是 mp3，应返回 True
        assert validate_audio_format("file.txt.mp3") is True, \
            "Double extension with .mp3 last should return True"
        
        # 最后一个扩展名是 txt，应返回 False
        assert validate_audio_format("file.mp3.txt") is False, \
            "Double extension with .txt last should return False"
    
    @settings(max_examples=100)
    @given(ext=st.sampled_from(SUPPORTED_EXTENSIONS))
    def test_extension_with_dots_in_filename(self, ext: str):
        """
        **Feature: meeting-summary, Property 1: 文件格式验证**
        
        验证：文件名中包含多个点号时，应正确识别最后的扩展名。
        
        **Validates: Requirements 1.2**
        """
        # Arrange: 创建包含多个点号的文件名
        filename = f"meeting.2024.01.15.{ext}"
        
        # Act & Assert
        assert validate_audio_format(filename) is True, \
            f"Filename with dots '{filename}' should be supported"
    
    @settings(max_examples=100)
    @given(
        filename=valid_filenames_without_extension(),
        ext=st.sampled_from(SUPPORTED_EXTENSIONS)
    )
    def test_extension_with_spaces_in_filename(self, filename: str, ext: str):
        """
        **Feature: meeting-summary, Property 1: 文件格式验证**
        
        验证：文件名中包含空格时，扩展名验证仍应正常工作。
        
        **Validates: Requirements 1.2**
        """
        # Arrange: 创建包含空格的文件名
        spaced_filename = f"my meeting recording.{ext}"
        
        # Act & Assert
        assert validate_audio_format(spaced_filename) is True, \
            f"Filename with spaces should be supported"


# =============================================================================
# 一致性测试
# =============================================================================

class TestProperty1Consistency:
    """
    **Feature: meeting-summary, Property 1: 文件格式验证 - 一致性**
    
    测试文件格式验证的一致性行为。
    
    **Validates: Requirements 1.2**
    """
    
    @settings(max_examples=100)
    @given(filename=valid_audio_filenames())
    def test_validation_is_deterministic(self, filename: str):
        """
        **Feature: meeting-summary, Property 1: 文件格式验证**
        
        验证：对同一文件名多次调用验证函数应返回相同结果。
        
        **Validates: Requirements 1.2**
        """
        # Act: 多次调用验证函数
        result1 = validate_audio_format(filename)
        result2 = validate_audio_format(filename)
        result3 = validate_audio_format(filename)
        
        # Assert: 结果应一致
        assert result1 == result2 == result3, \
            f"Validation should be deterministic for '{filename}'"
    
    @settings(max_examples=100)
    @given(
        filename=valid_filenames_without_extension(),
        ext=st.sampled_from(SUPPORTED_EXTENSIONS)
    )
    def test_supported_formats_match_constant(self, filename: str, ext: str):
        """
        **Feature: meeting-summary, Property 1: 文件格式验证**
        
        验证：验证结果应与 SUPPORTED_AUDIO_EXTENSIONS 常量一致。
        
        **Validates: Requirements 1.2**
        """
        # Arrange
        full_filename = f"{filename}.{ext}"
        
        # Act
        result = validate_audio_format(full_filename)
        is_in_constant = ext.lower() in SUPPORTED_AUDIO_EXTENSIONS
        
        # Assert
        assert result == is_in_constant, \
            f"Validation result should match SUPPORTED_AUDIO_EXTENSIONS"
    
    def test_get_supported_formats_returns_expected_set(self):
        """
        **Feature: meeting-summary, Property 1: 文件格式验证**
        
        验证：get_supported_formats() 返回的集合应包含所有支持的格式。
        
        **Validates: Requirements 1.2**
        """
        # Act
        formats = get_supported_formats()
        
        # Assert
        expected = {"mp3", "wav", "m4a"}
        assert formats == expected, \
            f"Expected {expected}, but got {formats}"
