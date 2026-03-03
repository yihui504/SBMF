"""
Profile Plugin Layer

数据库特化逻辑层，提供测试过滤和结果后处理功能。
"""

# Errors
from profiles.errors import (
    ProfileError,
    ProfileSkipError,
    ProfilePostProcessError,
    ProfileRegistrationError,
)

# Base Classes
from profiles.base import (
    BaseProfilePlugin,
    SkipDecision,
)

# SeekDB Implementation
from profiles.seekdb import (
    SeekDBProfilePlugin,
    SeekDBConstants,
)

# Registry
from profiles.registry import (
    ProfilePluginRegistry,
    get_global_registry,
    reset_global_registry,
    register_profile,
    get_profile,
    unregister_profile,
    list_profiles,
    get_all_profiles,
)

__all__ = [
    # Errors
    "ProfileError",
    "ProfileSkipError",
    "ProfilePostProcessError",
    "ProfileRegistrationError",
    # Base Classes
    "BaseProfilePlugin",
    "SkipDecision",
    # SeekDB Implementation
    "SeekDBProfilePlugin",
    "SeekDBConstants",
    # Registry
    "ProfilePluginRegistry",
    "get_global_registry",
    "reset_global_registry",
    "register_profile",
    "get_profile",
    "unregister_profile",
    "list_profiles",
    "get_all_profiles",
]
