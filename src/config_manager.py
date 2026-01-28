# 配置管理器
# Config Manager

"""
配置管理器模块 - 负责加载和管理 YAML 配置文件。

支持功能：
- YAML 配置文件加载
- 默认配置回退
- 配置热重载
"""

import logging
import os
from typing import Any, Optional

import yaml

# 配置日志
logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """配置错误异常"""
    pass


class ConfigManager:
    """
    配置管理器，负责加载和管理 YAML 配置。
    
    支持从 YAML 文件加载配置，当配置文件不存在或无效时使用默认配置值。
    
    Attributes:
        config_path: 配置文件路径
        _config: 加载的配置数据
    
    Example:
        >>> config = ConfigManager("config.yaml")
        >>> whisper_url = config.get_whisper_url()
        >>> claude_cmd = config.get_claude_command()
    """
    
    # 默认配置值
    DEFAULT_CONFIG = {
        "whisper": {
            "url": "http://localhost:8765",
            "timeout": 300,
            "language": "zh"
        },
        "claude": {
            "command": "claude",
            "timeout": 120
        },
        "server": {
            "host": "0.0.0.0",
            "port": 8000,
            "upload_max_size": 100
        },
        "summary": {
            "prompt_template": """请对以下会议转写内容进行智能总结：

要求：
1. 剔除废话和闲聊内容
2. 提取会议结论性内容
3. 保留支撑结论的关键论据和沟通要点
4. 输出业务导向的总结报告
5. 使用 Markdown 格式

转写内容：
{transcription}"""
        }
    }
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        初始化配置管理器。
        
        Args:
            config_path: 配置文件路径，默认为 "config.yaml"
        
        Note:
            如果配置文件不存在或无效，将使用默认配置值并记录警告日志。
        """
        self.config_path = config_path
        self._config: dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """
        加载配置文件。
        
        从指定路径加载 YAML 配置文件，如果文件不存在或解析失败，
        则使用默认配置值。
        """
        # 首先使用默认配置
        self._config = self._deep_copy_dict(self.DEFAULT_CONFIG)
        
        # 尝试加载配置文件
        if not os.path.exists(self.config_path):
            logger.warning(
                f"配置文件 '{self.config_path}' 不存在，使用默认配置值"
            )
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                file_config = yaml.safe_load(f)
            
            if file_config is None:
                logger.warning(
                    f"配置文件 '{self.config_path}' 为空，使用默认配置值"
                )
                return
            
            if not isinstance(file_config, dict):
                logger.warning(
                    f"配置文件 '{self.config_path}' 格式无效，使用默认配置值"
                )
                return
            
            # 合并配置（文件配置覆盖默认配置）
            self._merge_config(self._config, file_config)
            logger.info(f"成功加载配置文件: {self.config_path}")
            
        except yaml.YAMLError as e:
            logger.warning(
                f"配置文件 '{self.config_path}' 解析失败: {e}，使用默认配置值"
            )
        except IOError as e:
            logger.warning(
                f"无法读取配置文件 '{self.config_path}': {e}，使用默认配置值"
            )
    
    def _deep_copy_dict(self, d: dict) -> dict:
        """
        深拷贝字典。
        
        Args:
            d: 要拷贝的字典
        
        Returns:
            字典的深拷贝
        """
        result = {}
        for key, value in d.items():
            if isinstance(value, dict):
                result[key] = self._deep_copy_dict(value)
            elif isinstance(value, list):
                result[key] = value.copy()
            else:
                result[key] = value
        return result
    
    def _merge_config(self, base: dict, override: dict) -> None:
        """
        递归合并配置字典。
        
        Args:
            base: 基础配置字典（会被修改）
            override: 覆盖配置字典
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def _validate_config(self) -> bool:
        """
        验证配置有效性。
        
        Returns:
            配置是否有效
        """
        # 验证 whisper URL
        whisper_url = self._config.get("whisper", {}).get("url", "")
        if not whisper_url or not isinstance(whisper_url, str):
            logger.warning("Whisper URL 配置无效")
            return False
        
        # 验证 claude command
        claude_cmd = self._config.get("claude", {}).get("command", "")
        if not claude_cmd:
            logger.warning("Claude command 配置无效")
            return False
        
        return True
    
    def get_whisper_url(self) -> str:
        """
        获取 Whisper 服务地址。
        
        Returns:
            Whisper 服务的 URL 地址
        
        Example:
            >>> config = ConfigManager()
            >>> url = config.get_whisper_url()
            >>> print(url)  # "http://localhost:8765"
        """
        return self._config.get("whisper", {}).get(
            "url", 
            self.DEFAULT_CONFIG["whisper"]["url"]
        )
    
    def get_claude_command(self) -> list[str]:
        """
        获取 Claude CLI 命令。
        
        返回 Claude CLI 命令作为列表，支持带参数的命令。
        例如 "claude --url xxx" 会被解析为 ["claude", "--url", "xxx"]
        
        Returns:
            Claude CLI 命令列表
        
        Example:
            >>> config = ConfigManager()
            >>> cmd = config.get_claude_command()
            >>> print(cmd)  # ["claude"]
        """
        command = self._config.get("claude", {}).get(
            "command",
            self.DEFAULT_CONFIG["claude"]["command"]
        )
        
        # 如果已经是列表，直接返回
        if isinstance(command, list):
            return command
        
        # 如果是字符串，按空格分割
        if isinstance(command, str):
            return command.split()
        
        # 其他情况返回默认值
        return [self.DEFAULT_CONFIG["claude"]["command"]]
    
    def get_whisper_timeout(self) -> int:
        """
        获取 Whisper 服务超时时间。
        
        Returns:
            超时时间（秒）
        """
        return self._config.get("whisper", {}).get(
            "timeout",
            self.DEFAULT_CONFIG["whisper"]["timeout"]
        )
    
    def get_whisper_language(self) -> str:
        """
        获取 Whisper 默认语言。
        
        Returns:
            语言代码
        """
        return self._config.get("whisper", {}).get(
            "language",
            self.DEFAULT_CONFIG["whisper"]["language"]
        )
    
    def get_claude_timeout(self) -> int:
        """
        获取 Claude CLI 超时时间。
        
        Returns:
            超时时间（秒）
        """
        return self._config.get("claude", {}).get(
            "timeout",
            self.DEFAULT_CONFIG["claude"]["timeout"]
        )
    
    def get_server_host(self) -> str:
        """
        获取服务器监听地址。
        
        Returns:
            监听地址
        """
        return self._config.get("server", {}).get(
            "host",
            self.DEFAULT_CONFIG["server"]["host"]
        )
    
    def get_server_port(self) -> int:
        """
        获取服务器监听端口。
        
        Returns:
            监听端口
        """
        return self._config.get("server", {}).get(
            "port",
            self.DEFAULT_CONFIG["server"]["port"]
        )
    
    def get_upload_max_size(self) -> int:
        """
        获取上传文件大小限制。
        
        Returns:
            文件大小限制（MB）
        """
        return self._config.get("server", {}).get(
            "upload_max_size",
            self.DEFAULT_CONFIG["server"]["upload_max_size"]
        )
    
    def get_summary_prompt_template(self) -> str:
        """
        获取总结 prompt 模板。
        
        Returns:
            Prompt 模板字符串
        """
        return self._config.get("summary", {}).get(
            "prompt_template",
            self.DEFAULT_CONFIG["summary"]["prompt_template"]
        )
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值。
        
        支持使用点号分隔的键路径，如 "whisper.url"。
        
        Args:
            key: 配置键，支持点号分隔的路径
            default: 默认值
        
        Returns:
            配置值或默认值
        
        Example:
            >>> config = ConfigManager()
            >>> url = config.get("whisper.url")
            >>> timeout = config.get("whisper.timeout", 300)
        """
        keys = key.split(".")
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def reload(self) -> None:
        """
        重新加载配置。
        
        从配置文件重新加载配置，用于配置文件变更后的热更新。
        
        Example:
            >>> config = ConfigManager()
            >>> # 修改配置文件后
            >>> config.reload()
        """
        logger.info(f"重新加载配置文件: {self.config_path}")
        self._load_config()
    
    @property
    def config(self) -> dict[str, Any]:
        """
        获取完整配置字典（只读）。
        
        Returns:
            配置字典的副本
        """
        return self._deep_copy_dict(self._config)
