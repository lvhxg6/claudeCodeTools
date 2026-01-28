# ConfigManager 单元测试
# ConfigManager Unit Tests

"""
ConfigManager 配置管理器的单元测试。

测试覆盖：
- YAML 配置文件加载
- 默认配置回退
- get_whisper_url() 方法
- get_claude_command() 方法
- reload() 方法
"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from src.config_manager import ConfigManager


class TestConfigManagerInit:
    """测试 ConfigManager 初始化"""
    
    def test_init_with_default_path(self):
        """测试使用默认路径初始化"""
        config = ConfigManager("nonexistent_config.yaml")
        assert config.config_path == "nonexistent_config.yaml"
    
    def test_init_with_custom_path(self):
        """测试使用自定义路径初始化"""
        config = ConfigManager("/custom/path/config.yaml")
        assert config.config_path == "/custom/path/config.yaml"


class TestConfigManagerDefaultValues:
    """测试默认配置值"""
    
    def test_default_whisper_url(self):
        """测试默认 Whisper URL"""
        config = ConfigManager("nonexistent.yaml")
        assert config.get_whisper_url() == "http://localhost:8765"
    
    def test_default_claude_command(self):
        """测试默认 Claude 命令"""
        config = ConfigManager("nonexistent.yaml")
        assert config.get_claude_command() == "claude"
    
    def test_default_whisper_timeout(self):
        """测试默认 Whisper 超时时间"""
        config = ConfigManager("nonexistent.yaml")
        assert config.get_whisper_timeout() == 300
    
    def test_default_claude_timeout(self):
        """测试默认 Claude 超时时间"""
        config = ConfigManager("nonexistent.yaml")
        assert config.get_claude_timeout() == 120
    
    def test_default_server_host(self):
        """测试默认服务器地址"""
        config = ConfigManager("nonexistent.yaml")
        assert config.get_server_host() == "0.0.0.0"
    
    def test_default_server_port(self):
        """测试默认服务器端口"""
        config = ConfigManager("nonexistent.yaml")
        assert config.get_server_port() == 8000


class TestConfigManagerLoadFromFile:
    """测试从文件加载配置"""
    
    def test_load_valid_config(self, tmp_path):
        """测试加载有效的配置文件"""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "whisper": {
                "url": "http://custom-whisper:9000",
                "timeout": 600
            },
            "claude": {
                "command": "custom-claude --verbose"
            }
        }
        config_file.write_text(yaml.dump(config_data), encoding='utf-8')
        
        config = ConfigManager(str(config_file))
        
        assert config.get_whisper_url() == "http://custom-whisper:9000"
        assert config.get_whisper_timeout() == 600
        assert config.get_claude_command() == "custom-claude --verbose"
    
    def test_load_partial_config(self, tmp_path):
        """测试加载部分配置（其他使用默认值）"""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "whisper": {
                "url": "http://partial-whisper:8000"
            }
        }
        config_file.write_text(yaml.dump(config_data), encoding='utf-8')
        
        config = ConfigManager(str(config_file))
        
        # 自定义值
        assert config.get_whisper_url() == "http://partial-whisper:8000"
        # 默认值
        assert config.get_whisper_timeout() == 300
        assert config.get_claude_command() == "claude"
    
    def test_load_empty_config_file(self, tmp_path):
        """测试加载空配置文件"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("", encoding='utf-8')
        
        config = ConfigManager(str(config_file))
        
        # 应该使用默认值
        assert config.get_whisper_url() == "http://localhost:8765"
        assert config.get_claude_command() == "claude"
    
    def test_load_invalid_yaml(self, tmp_path):
        """测试加载无效的 YAML 文件"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: content: [", encoding='utf-8')
        
        config = ConfigManager(str(config_file))
        
        # 应该使用默认值
        assert config.get_whisper_url() == "http://localhost:8765"
        assert config.get_claude_command() == "claude"
    
    def test_load_non_dict_yaml(self, tmp_path):
        """测试加载非字典格式的 YAML"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("- item1\n- item2", encoding='utf-8')
        
        config = ConfigManager(str(config_file))
        
        # 应该使用默认值
        assert config.get_whisper_url() == "http://localhost:8765"


class TestConfigManagerClaudeCommand:
    """测试 Claude 命令解析"""
    
    def test_claude_command_string(self, tmp_path):
        """测试字符串格式的 Claude 命令"""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "claude": {
                "command": "claude --url http://api.example.com --verbose"
            }
        }
        config_file.write_text(yaml.dump(config_data), encoding='utf-8')
        
        config = ConfigManager(str(config_file))
        
        assert config.get_claude_command() == "claude --url http://api.example.com --verbose"
    
    def test_claude_command_list(self, tmp_path):
        """测试列表格式的 Claude 命令"""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "claude": {
                "command": ["claude", "--url", "http://api.example.com"]
            }
        }
        config_file.write_text(yaml.dump(config_data), encoding='utf-8')
        
        config = ConfigManager(str(config_file))
        
        assert config.get_claude_command() == "claude --url http://api.example.com"
    
    def test_claude_command_simple(self, tmp_path):
        """测试简单的 Claude 命令"""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "claude": {
                "command": "claude"
            }
        }
        config_file.write_text(yaml.dump(config_data), encoding='utf-8')
        
        config = ConfigManager(str(config_file))
        
        assert config.get_claude_command() == "claude"


class TestConfigManagerReload:
    """测试配置重载"""
    
    def test_reload_config(self, tmp_path):
        """测试重新加载配置"""
        config_file = tmp_path / "config.yaml"
        
        # 初始配置
        initial_config = {
            "whisper": {
                "url": "http://initial:8000"
            }
        }
        config_file.write_text(yaml.dump(initial_config), encoding='utf-8')
        
        config = ConfigManager(str(config_file))
        assert config.get_whisper_url() == "http://initial:8000"
        
        # 更新配置文件
        updated_config = {
            "whisper": {
                "url": "http://updated:9000"
            }
        }
        config_file.write_text(yaml.dump(updated_config), encoding='utf-8')
        
        # 重新加载
        config.reload()
        
        assert config.get_whisper_url() == "http://updated:9000"


class TestConfigManagerGet:
    """测试通用 get 方法"""
    
    def test_get_nested_key(self, tmp_path):
        """测试获取嵌套键"""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "whisper": {
                "url": "http://test:8000"
            }
        }
        config_file.write_text(yaml.dump(config_data), encoding='utf-8')
        
        config = ConfigManager(str(config_file))
        
        assert config.get("whisper.url") == "http://test:8000"
    
    def test_get_with_default(self):
        """测试获取不存在的键时返回默认值"""
        config = ConfigManager("nonexistent.yaml")
        
        assert config.get("nonexistent.key", "default_value") == "default_value"
    
    def test_get_top_level_key(self, tmp_path):
        """测试获取顶级键"""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "whisper": {
                "url": "http://test:8000"
            }
        }
        config_file.write_text(yaml.dump(config_data), encoding='utf-8')
        
        config = ConfigManager(str(config_file))
        
        result = config.get("whisper")
        assert isinstance(result, dict)
        assert result["url"] == "http://test:8000"


class TestConfigManagerProperty:
    """测试 config 属性"""
    
    def test_config_property_returns_copy(self, tmp_path):
        """测试 config 属性返回副本"""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "whisper": {
                "url": "http://test:8000"
            }
        }
        config_file.write_text(yaml.dump(config_data), encoding='utf-8')
        
        config = ConfigManager(str(config_file))
        
        # 获取配置副本
        config_copy = config.config
        
        # 修改副本不应影响原配置
        config_copy["whisper"]["url"] = "http://modified:9000"
        
        assert config.get_whisper_url() == "http://test:8000"
