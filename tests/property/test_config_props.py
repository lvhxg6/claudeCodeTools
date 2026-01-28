# ConfigManager 属性测试
# ConfigManager Property-Based Tests

"""
ConfigManager 配置管理器的属性测试。

使用 Hypothesis 进行属性测试，验证配置管理器的核心属性：
- Property 9: 配置加载正确性
- Property 10: 默认配置回退

**Feature: meeting-summary**
**Validates: Requirements 7.1, 7.2, 7.4**
"""

import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional

import pytest
import yaml
from hypothesis import given, settings, assume, example, HealthCheck
from hypothesis import strategies as st

from src.config_manager import ConfigManager


# =============================================================================
# 自定义策略 (Custom Strategies)
# =============================================================================

# 有效的 URL 策略
@st.composite
def valid_urls(draw):
    """生成有效的 URL 地址"""
    protocol = draw(st.sampled_from(["http", "https"]))
    host = draw(st.sampled_from([
        "localhost",
        "127.0.0.1",
        "192.168.1.1",
        "whisper-service",
        "api.example.com",
        "internal.server.local"
    ]))
    port = draw(st.integers(min_value=1, max_value=65535))
    return f"{protocol}://{host}:{port}"


# 有效的 Claude 命令策略
@st.composite
def valid_claude_commands(draw):
    """生成有效的 Claude CLI 命令"""
    base_command = draw(st.sampled_from([
        "claude",
        "claude-cli",
        "/usr/local/bin/claude",
        "./claude"
    ]))
    
    # 可选参数
    has_args = draw(st.booleans())
    if has_args:
        args = draw(st.lists(
            st.sampled_from([
                "--verbose",
                "--quiet",
                "--timeout=60",
                "--model=claude-3",
                "-v",
                "-q"
            ]),
            min_size=0,
            max_size=3
        ))
        if args:
            return f"{base_command} {' '.join(args)}"
    
    return base_command


# 有效的 YAML 配置策略
@st.composite
def valid_yaml_configs(draw):
    """生成有效的 YAML 配置字典"""
    config = {}
    
    # Whisper 配置
    if draw(st.booleans()):
        whisper_config = {}
        if draw(st.booleans()):
            whisper_config["url"] = draw(valid_urls())
        if draw(st.booleans()):
            whisper_config["timeout"] = draw(st.integers(min_value=1, max_value=3600))
        if draw(st.booleans()):
            whisper_config["language"] = draw(st.sampled_from(["zh", "en", "ja", "ko"]))
        if whisper_config:
            config["whisper"] = whisper_config
    
    # Claude 配置
    if draw(st.booleans()):
        claude_config = {}
        if draw(st.booleans()):
            claude_config["command"] = draw(valid_claude_commands())
        if draw(st.booleans()):
            claude_config["timeout"] = draw(st.integers(min_value=1, max_value=600))
        if claude_config:
            config["claude"] = claude_config
    
    # Server 配置
    if draw(st.booleans()):
        server_config = {}
        if draw(st.booleans()):
            server_config["host"] = draw(st.sampled_from(["0.0.0.0", "127.0.0.1", "localhost"]))
        if draw(st.booleans()):
            server_config["port"] = draw(st.integers(min_value=1024, max_value=65535))
        if draw(st.booleans()):
            server_config["upload_max_size"] = draw(st.integers(min_value=1, max_value=500))
        if server_config:
            config["server"] = server_config
    
    return config


# 无效配置文件内容策略
@st.composite
def invalid_config_contents(draw):
    """生成无效的配置文件内容"""
    invalid_type = draw(st.sampled_from([
        "invalid_yaml",
        "non_dict",
        "empty",
        "malformed"
    ]))
    
    if invalid_type == "invalid_yaml":
        return "invalid: yaml: content: ["
    elif invalid_type == "non_dict":
        return "- item1\n- item2\n- item3"
    elif invalid_type == "empty":
        return ""
    else:  # malformed
        return "key: value\n  bad_indent: here"


# =============================================================================
# 辅助函数
# =============================================================================

def create_temp_config_file(config_data: dict) -> str:
    """创建临时配置文件并返回路径"""
    fd, path = tempfile.mkstemp(suffix='.yaml', prefix='config_test_')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f)
    except Exception:
        os.close(fd)
        raise
    return path


def create_temp_config_file_with_content(content: str) -> str:
    """创建包含指定内容的临时配置文件"""
    fd, path = tempfile.mkstemp(suffix='.yaml', prefix='config_test_')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception:
        os.close(fd)
        raise
    return path


def cleanup_temp_file(path: str) -> None:
    """清理临时文件"""
    try:
        if os.path.exists(path):
            os.unlink(path)
    except Exception:
        pass


# =============================================================================
# Property 9: 配置加载正确性
# =============================================================================

class TestProperty9ConfigLoadingCorrectness:
    """
    **Feature: meeting-summary, Property 9: 配置加载正确性**
    
    *对于任意* 有效的 YAML 配置文件，系统应该正确解析并返回配置的 
    Whisper 服务地址和 Claude CLI 命令。
    
    **Validates: Requirements 7.1, 7.2**
    """
    
    @settings(max_examples=100)
    @given(whisper_url=valid_urls())
    def test_whisper_url_loaded_correctly(self, whisper_url: str):
        """
        **Feature: meeting-summary, Property 9: 配置加载正确性**
        
        验证：对于任意有效的 Whisper URL，配置管理器应正确加载并返回该 URL。
        
        **Validates: Requirements 7.1**
        """
        config_path = None
        try:
            # Arrange: 创建包含 Whisper URL 的配置文件
            config_data = {
                "whisper": {
                    "url": whisper_url
                }
            }
            config_path = create_temp_config_file(config_data)
            
            # Act: 加载配置
            config = ConfigManager(config_path)
            loaded_url = config.get_whisper_url()
            
            # Assert: 加载的 URL 应与配置文件中的一致
            assert loaded_url == whisper_url, \
                f"Expected URL '{whisper_url}', but got '{loaded_url}'"
        finally:
            if config_path:
                cleanup_temp_file(config_path)
    
    @settings(max_examples=100)
    @given(claude_command=valid_claude_commands())
    def test_claude_command_loaded_correctly(self, claude_command: str):
        """
        **Feature: meeting-summary, Property 9: 配置加载正确性**
        
        验证：对于任意有效的 Claude 命令，配置管理器应正确加载并解析该命令。
        
        **Validates: Requirements 7.2**
        """
        config_path = None
        try:
            # Arrange: 创建包含 Claude 命令的配置文件
            config_data = {
                "claude": {
                    "command": claude_command
                }
            }
            config_path = create_temp_config_file(config_data)
            
            # Act: 加载配置
            config = ConfigManager(config_path)
            loaded_command = config.get_claude_command()
            
            # Assert: 加载的命令应与配置文件中的一致（字符串形式）
            assert loaded_command == claude_command, \
                f"Expected command '{claude_command}', but got '{loaded_command}'"
        finally:
            if config_path:
                cleanup_temp_file(config_path)
    
    @settings(max_examples=100)
    @given(config_data=valid_yaml_configs())
    def test_full_config_loaded_correctly(self, config_data: dict):
        """
        **Feature: meeting-summary, Property 9: 配置加载正确性**
        
        验证：对于任意有效的完整配置，配置管理器应正确加载所有配置项。
        
        **Validates: Requirements 7.1, 7.2**
        """
        config_path = None
        try:
            # Arrange: 创建配置文件
            config_path = create_temp_config_file(config_data)
            
            # Act: 加载配置
            config = ConfigManager(config_path)
            
            # Assert: 验证 Whisper URL
            if "whisper" in config_data and "url" in config_data["whisper"]:
                expected_url = config_data["whisper"]["url"]
                assert config.get_whisper_url() == expected_url, \
                    f"Whisper URL mismatch: expected '{expected_url}', got '{config.get_whisper_url()}'"
            
            # Assert: 验证 Claude 命令
            if "claude" in config_data and "command" in config_data["claude"]:
                expected_cmd = config_data["claude"]["command"]
                # 如果是列表，合并为字符串
                if isinstance(expected_cmd, list):
                    expected_cmd = " ".join(expected_cmd)
                assert config.get_claude_command() == expected_cmd, \
                    f"Claude command mismatch: expected '{expected_cmd}', got '{config.get_claude_command()}'"
        finally:
            if config_path:
                cleanup_temp_file(config_path)
    
    @settings(max_examples=100)
    @given(
        whisper_url=valid_urls(),
        claude_command=valid_claude_commands()
    )
    def test_config_values_independent(
        self, 
        whisper_url: str, 
        claude_command: str
    ):
        """
        **Feature: meeting-summary, Property 9: 配置加载正确性**
        
        验证：Whisper URL 和 Claude 命令的配置相互独立，修改一个不影响另一个。
        
        **Validates: Requirements 7.1, 7.2**
        """
        config_path = None
        try:
            # Arrange: 创建包含两个配置的文件
            config_data = {
                "whisper": {"url": whisper_url},
                "claude": {"command": claude_command}
            }
            config_path = create_temp_config_file(config_data)
            
            # Act: 加载配置
            config = ConfigManager(config_path)
            
            # Assert: 两个配置值应独立正确
            assert config.get_whisper_url() == whisper_url
            assert config.get_claude_command() == claude_command
        finally:
            if config_path:
                cleanup_temp_file(config_path)


# =============================================================================
# Property 10: 默认配置回退
# =============================================================================

class TestProperty10DefaultConfigFallback:
    """
    **Feature: meeting-summary, Property 10: 默认配置回退**
    
    *对于任意* 不存在或无效的配置文件，系统应该使用默认配置值：
    - Whisper 服务地址默认为 "http://localhost:8765"
    - Claude CLI 命令默认为 "claude"
    
    **Validates: Requirements 7.4**
    """
    
    # 默认值常量
    DEFAULT_WHISPER_URL = "http://localhost:8765"
    DEFAULT_CLAUDE_COMMAND = "claude"
    
    @settings(max_examples=100)
    @given(nonexistent_path=st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_-'),
        min_size=5,
        max_size=20
    ))
    def test_nonexistent_file_uses_defaults(self, nonexistent_path: str):
        """
        **Feature: meeting-summary, Property 10: 默认配置回退**
        
        验证：对于任意不存在的配置文件路径，系统应使用默认配置值。
        
        **Validates: Requirements 7.4**
        """
        # Arrange: 构造不存在的路径
        temp_dir = tempfile.gettempdir()
        config_path = os.path.join(temp_dir, f"nonexistent_{nonexistent_path}_{uuid.uuid4().hex}.yaml")
        
        # 确保文件不存在
        assume(not os.path.exists(config_path))
        
        # Act: 使用不存在的路径创建配置管理器
        config = ConfigManager(config_path)
        
        # Assert: 应使用默认值
        assert config.get_whisper_url() == self.DEFAULT_WHISPER_URL, \
            f"Expected default Whisper URL '{self.DEFAULT_WHISPER_URL}', " \
            f"but got '{config.get_whisper_url()}'"
        assert config.get_claude_command() == self.DEFAULT_CLAUDE_COMMAND, \
            f"Expected default Claude command {self.DEFAULT_CLAUDE_COMMAND}, " \
            f"but got {config.get_claude_command()}"
    
    @settings(max_examples=100)
    @given(invalid_content=invalid_config_contents())
    def test_invalid_config_uses_defaults(self, invalid_content: str):
        """
        **Feature: meeting-summary, Property 10: 默认配置回退**
        
        验证：对于任意无效的配置文件内容，系统应使用默认配置值。
        
        **Validates: Requirements 7.4**
        """
        config_path = None
        try:
            # Arrange: 创建包含无效内容的配置文件
            config_path = create_temp_config_file_with_content(invalid_content)
            
            # Act: 加载配置
            config = ConfigManager(config_path)
            
            # Assert: 应使用默认值
            assert config.get_whisper_url() == self.DEFAULT_WHISPER_URL, \
                f"Expected default Whisper URL for invalid config, " \
                f"but got '{config.get_whisper_url()}'"
            assert config.get_claude_command() == self.DEFAULT_CLAUDE_COMMAND, \
                f"Expected default Claude command for invalid config, " \
                f"but got {config.get_claude_command()}"
        finally:
            if config_path:
                cleanup_temp_file(config_path)
    
    @settings(max_examples=100)
    @given(partial_config=valid_yaml_configs())
    def test_missing_keys_use_defaults(self, partial_config: dict):
        """
        **Feature: meeting-summary, Property 10: 默认配置回退**
        
        验证：对于部分配置，缺失的配置项应使用默认值。
        
        **Validates: Requirements 7.4**
        """
        config_path = None
        try:
            # Arrange: 创建部分配置文件
            config_path = create_temp_config_file(partial_config)
            
            # Act: 加载配置
            config = ConfigManager(config_path)
            
            # Assert: 验证 Whisper URL
            if "whisper" not in partial_config or "url" not in partial_config.get("whisper", {}):
                assert config.get_whisper_url() == self.DEFAULT_WHISPER_URL, \
                    f"Expected default Whisper URL when not configured, " \
                    f"but got '{config.get_whisper_url()}'"
            
            # Assert: 验证 Claude 命令
            if "claude" not in partial_config or "command" not in partial_config.get("claude", {}):
                assert config.get_claude_command() == self.DEFAULT_CLAUDE_COMMAND, \
                    f"Expected default Claude command when not configured, " \
                    f"but got {config.get_claude_command()}"
        finally:
            if config_path:
                cleanup_temp_file(config_path)
    
    @settings(max_examples=100)
    @given(random_suffix=st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N')),
        min_size=5,
        max_size=15
    ))
    def test_reload_preserves_defaults_for_missing_file(self, random_suffix: str):
        """
        **Feature: meeting-summary, Property 10: 默认配置回退**
        
        验证：重新加载不存在的配置文件后，仍应使用默认值。
        
        **Validates: Requirements 7.4**
        """
        # Arrange: 生成随机的不存在路径
        temp_dir = tempfile.gettempdir()
        config_path = os.path.join(temp_dir, f"{random_suffix}_{uuid.uuid4().hex}_config.yaml")
        assume(not os.path.exists(config_path))
        
        # Act: 创建配置管理器并重新加载
        config = ConfigManager(config_path)
        config.reload()
        
        # Assert: 重新加载后仍应使用默认值
        assert config.get_whisper_url() == self.DEFAULT_WHISPER_URL
        assert config.get_claude_command() == self.DEFAULT_CLAUDE_COMMAND
    
    @settings(max_examples=100)
    @given(
        whisper_url=valid_urls(),
        claude_command=valid_claude_commands()
    )
    def test_config_then_delete_falls_back_to_defaults(
        self, 
        whisper_url: str, 
        claude_command: str
    ):
        """
        **Feature: meeting-summary, Property 10: 默认配置回退**
        
        验证：配置文件被删除后重新加载，应回退到默认值。
        
        **Validates: Requirements 7.4**
        """
        config_path = None
        try:
            # Arrange: 创建配置文件
            config_data = {
                "whisper": {"url": whisper_url},
                "claude": {"command": claude_command}
            }
            config_path = create_temp_config_file(config_data)
            
            # Act: 加载配置，验证自定义值
            config = ConfigManager(config_path)
            assert config.get_whisper_url() == whisper_url
            
            # Act: 删除配置文件并重新加载
            os.unlink(config_path)
            config_path = None  # 标记为已删除
            config.reload()
            
            # Assert: 应回退到默认值
            assert config.get_whisper_url() == self.DEFAULT_WHISPER_URL, \
                f"Expected default URL after file deletion, but got '{config.get_whisper_url()}'"
            assert config.get_claude_command() == self.DEFAULT_CLAUDE_COMMAND, \
                f"Expected default command after file deletion, but got {config.get_claude_command()}"
        finally:
            if config_path:
                cleanup_temp_file(config_path)


# =============================================================================
# 综合属性测试
# =============================================================================

class TestConfigPropertiesCombined:
    """
    综合属性测试，验证 Property 9 和 Property 10 的交互行为。
    
    **Feature: meeting-summary**
    **Validates: Requirements 7.1, 7.2, 7.4**
    """
    
    @settings(max_examples=100)
    @given(
        initial_url=valid_urls(),
        updated_url=valid_urls()
    )
    def test_config_update_reflects_new_values(
        self, 
        initial_url: str, 
        updated_url: str
    ):
        """
        **Feature: meeting-summary, Property 9: 配置加载正确性**
        
        验证：配置文件更新后重新加载，应反映新的配置值。
        
        **Validates: Requirements 7.1**
        """
        config_path = None
        try:
            # Arrange: 创建初始配置
            config_path = create_temp_config_file({"whisper": {"url": initial_url}})
            
            # Act: 加载初始配置
            config = ConfigManager(config_path)
            assert config.get_whisper_url() == initial_url
            
            # Act: 更新配置文件
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump({"whisper": {"url": updated_url}}, f)
            config.reload()
            
            # Assert: 应反映新值
            assert config.get_whisper_url() == updated_url, \
                f"Expected updated URL '{updated_url}', but got '{config.get_whisper_url()}'"
        finally:
            if config_path:
                cleanup_temp_file(config_path)
    
    @settings(max_examples=100)
    @given(config_data=valid_yaml_configs())
    def test_config_property_returns_independent_copy(self, config_data: dict):
        """
        **Feature: meeting-summary, Property 9: 配置加载正确性**
        
        验证：config 属性返回的是配置的独立副本，修改副本不影响原配置。
        
        **Validates: Requirements 7.1, 7.2**
        """
        config_path = None
        try:
            # Arrange: 创建配置文件
            config_path = create_temp_config_file(config_data)
            
            # Act: 加载配置并获取副本
            config = ConfigManager(config_path)
            original_whisper_url = config.get_whisper_url()
            
            # Act: 修改副本
            config_copy = config.config
            if "whisper" in config_copy:
                config_copy["whisper"]["url"] = "http://modified:9999"
            
            # Assert: 原配置不应被修改
            assert config.get_whisper_url() == original_whisper_url, \
                "Modifying config copy should not affect original config"
        finally:
            if config_path:
                cleanup_temp_file(config_path)
