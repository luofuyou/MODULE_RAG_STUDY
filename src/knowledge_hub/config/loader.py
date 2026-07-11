"""配置加载器 — 提供 YAML 配置发现、加载和校验。

职责：
- 按优先级查找配置文件（环境变量 > 当前目录 > 示例文件）
- 调用 Settings.from_yaml() 加载并校验
- 提供 singleton 式的全局配置获取
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from knowledge_hub.config.settings import Settings

# 配置文件搜索优先级
CONFIG_SEARCH_PATHS = [
    os.environ.get("KH_CONFIG", ""),                     # 环境变量 KH_CONFIG
    os.path.join(os.getcwd(), "settings.yaml"),          # 当前目录
    os.path.join(os.getcwd(), "settings.example.yaml"),  # 示例文件兜底
]

# 全局配置缓存（模块级别单例）
_settings: Optional[Settings] = None


def find_config_file() -> str:
    """按优先级查找配置文件。

    Returns:
        第一个存在的配置文件路径。

    Raises:
        FileNotFoundError: 所有路径都不存在时。
    """
    for path in CONFIG_SEARCH_PATHS:
        if path and Path(path).exists():
            return path
    raise FileNotFoundError(
        "无法找到配置文件。请复制 settings.example.yaml 为 settings.yaml "
        "或设置环境变量 KH_CONFIG。搜索路径:\n"
        + "\n".join(f"  - {p}" for p in CONFIG_SEARCH_PATHS if p)
    )


def load_settings(config_path: Optional[str] = None) -> Settings:
    """加载并返回 Settings 实例。

    Args:
        config_path: 可选，指定配置文件路径。为 None 时自动查找。

    Returns:
        已验证的 Settings 实例。

    Raises:
        FileNotFoundError: 配置文件不存在。
        pydantic.ValidationError: 配置校验失败。
    """
    global _settings

    if config_path is None:
        config_path = find_config_file()

    settings = Settings.from_yaml(config_path)
    _settings = settings
    return settings


def get_settings() -> Settings:
    """获取当前全局配置（必须先调用 load_settings()）。

    Returns:
        全局 Settings 实例。

    Raises:
        RuntimeError: 尚未加载配置。
    """
    if _settings is None:
        raise RuntimeError("配置尚未加载，请先调用 load_settings()")
    return _settings


def reload_settings(config_path: Optional[str] = None) -> Settings:
    """强制重新加载配置。

    Args:
        config_path: 可选，指定新的配置文件路径。

    Returns:
        新的 Settings 实例。
    """
    global _settings
    _settings = load_settings(config_path)
    return _settings
