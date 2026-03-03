"""
Profile Plugin Registry

管理 Profile Plugin 的注册、获取和查找。
"""

import logging
from typing import Dict, List, Optional

from profiles.base import BaseProfilePlugin
from profiles.errors import ProfileRegistrationError


# ================================================================
# Registry Class
# ================================================================

class ProfilePluginRegistry:
    """Profile Plugin 注册表

    职责：
    - 管理 Profile Plugin 的注册和获取
    - 防止重复注册
    - 提供查询功能
    - 支持清理和重置

    Example:
        >>> registry = ProfilePluginRegistry()
        >>> profile = SeekDBProfilePlugin()
        >>> registry.register("seekdb", profile)
        >>> retrieved = registry.get("seekdb")
        >>> assert retrieved is profile
    """

    def __init__(self, allow_overwrite: bool = False):
        """初始化注册表

        Args:
            allow_overwrite: 是否允许覆盖已注册的 Plugin（默认不允许）
        """
        self._profiles: Dict[str, BaseProfilePlugin] = {}
        self.allow_overwrite = allow_overwrite
        self._logger = logging.getLogger(self.__class__.__name__)

    def register(self, name: str, profile: BaseProfilePlugin) -> None:
        """注册 Profile Plugin

        Args:
            name: Plugin 名称（唯一标识符）
            profile: Plugin 实例

        Raises:
            ProfileRegistrationError: 如果名称已存在且不允许覆盖
            ValueError: 如果名称或 profile 无效

        Example:
            >>> registry = ProfilePluginRegistry()
            >>> registry.register("seekdb", SeekDBProfilePlugin())
        """
        # 验证参数
        if not name or not isinstance(name, str):
            raise ValueError(f"Profile name must be a non-empty string, got: {name}")

        if not isinstance(profile, BaseProfilePlugin):
            raise ValueError(
                f"Profile must be an instance of BaseProfilePlugin, "
                f"got: {type(profile).__name__}"
            )

        # 检查是否已存在
        if name in self._profiles and not self.allow_overwrite:
            existing = self._profiles[name]
            raise ProfileRegistrationError(
                message=f"Profile '{name}' is already registered with {type(existing).__name__}. "
                        f"Use unregister() first or set allow_overwrite=True.",
                profile_name=name
            )

        # 注册
        self._profiles[name] = profile
        self._logger.info(f"Registered profile '{name}' ({type(profile).__name__})")

    def get(self, name: str) -> Optional[BaseProfilePlugin]:
        """获取 Profile Plugin

        Args:
            name: Plugin 名称

        Returns:
            Optional[BaseProfilePlugin]: Plugin 实例，如果不存在则返回 None

        Example:
            >>> profile = registry.get("seekdb")
            >>> if profile:
            ...     print(f"Found: {profile.get_name()}")
        """
        return self._profiles.get(name)

    def get_or_raise(self, name: str) -> BaseProfilePlugin:
        """获取 Profile Plugin，不存在则抛出异常

        Args:
            name: Plugin 名称

        Returns:
            BaseProfilePlugin: Plugin 实例

        Raises:
            ProfileRegistrationError: 如果 Plugin 不存在

        Example:
            >>> try:
            ...     profile = registry.get_or_raise("seekdb")
            ... except ProfileRegistrationError as e:
            ...     print(f"Profile not found: {e}")
        """
        profile = self.get(name)
        if profile is None:
            raise ProfileRegistrationError(
                message=f"Profile '{name}' is not registered",
                profile_name=name,
                context={"available_profiles": self.list_names()}
            )
        return profile

    def unregister(self, name: str) -> bool:
        """注销 Profile Plugin

        Args:
            name: Plugin 名称

        Returns:
            bool: 是否成功注销（如果不存在则返回 False）

        Example:
            >>> if registry.unregister("seekdb"):
            ...     print("Unregistered successfully")
        """
        if name in self._profiles:
            del self._profiles[name]
            self._logger.info(f"Unregistered profile '{name}'")
            return True
        return False

    def list_all(self) -> List[str]:
        """列出所有已注册的 Plugin 名称

        Returns:
            List[str]: Plugin 名称列表

        Example:
            >>> names = registry.list_all()
            >>> print(f"Registered profiles: {names}")
        """
        return list(self._profiles.keys())

    def list_names(self) -> List[str]:
        """别名方法，同 list_all()"""
        return self.list_all()

    def get_all(self) -> List[BaseProfilePlugin]:
        """获取所有已注册的 Plugin 实例

        Returns:
            List[BaseProfilePlugin]: Plugin 实例列表

        Example:
            >>> profiles = registry.get_all()
            >>> for profile in profiles:
            ...     print(profile.get_name())
        """
        return list(self._profiles.values())

    def count(self) -> int:
        """获取已注册 Plugin 的数量

        Returns:
            int: Plugin 数量
        """
        return len(self._profiles)

    def is_registered(self, name: str) -> bool:
        """检查 Plugin 是否已注册

        Args:
            name: Plugin 名称

        Returns:
            bool: 是否已注册
        """
        return name in self._profiles

    def clear(self) -> None:
        """清空注册表

        Example:
            >>> registry.clear()
            >>> assert registry.count() == 0
        """
        self._profiles.clear()
        self._logger.info("Cleared all profiles")

    def get_info(self, name: str) -> Optional[Dict[str, str]]:
        """获取 Plugin 信息

        Args:
            name: Plugin 名称

        Returns:
            Optional[Dict[str, str]]: Plugin 信息字典，如果不存在则返回 None

        Example:
            >>> info = registry.get_info("seekdb")
            >>> print(f"Name: {info['name']}, Type: {info['type']}")
        """
        profile = self.get(name)
        if profile is None:
            return None

        return {
            "name": name,
            "type": type(profile).__name__,
            "plugin_name": profile.get_name(),
            "description": profile.get_description(),
            "supported_operations": ", ".join(profile.get_supported_operations()),
        }

    def __contains__(self, name: str) -> bool:
        """支持 'in' 操作符

        Example:
            >>> if "seekdb" in registry:
            ...     print("seekdb is registered")
        """
        return self.is_registered(name)

    def __len__(self) -> int:
        """支持 len() 函数

        Example:
            >>> print(f"Total profiles: {len(registry)}")
        """
        return self.count()

    def __repr__(self) -> str:
        """字符串表示"""
        return f"{self.__class__.__name__}(count={self.count()}, profiles={self.list_names()})"


# ================================================================
# Global Registry
# ================================================================

_global_registry: Optional[ProfilePluginRegistry] = None


def get_global_registry() -> ProfilePluginRegistry:
    """获取全局注册表实例（单例模式）

    Returns:
        ProfilePluginRegistry: 全局注册表

    Example:
        >>> registry = get_global_registry()
        >>> registry.register("seekdb", SeekDBProfilePlugin())
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ProfilePluginRegistry()
    return _global_registry


def reset_global_registry() -> None:
    """重置全局注册表

    主要用于测试场景。

    Example:
        >>> reset_global_registry()
        >>> assert get_global_registry().count() == 0
    """
    global _global_registry
    _global_registry = None


# ================================================================
# Convenience Functions
# ================================================================

def register_profile(name: str, profile: BaseProfilePlugin) -> None:
    """注册 Profile Plugin 到全局注册表

    Args:
        name: Plugin 名称
        profile: Plugin 实例

    Raises:
        ProfileRegistrationError: 如果名称已存在

    Example:
        >>> register_profile("seekdb", SeekDBProfilePlugin())
    """
    registry = get_global_registry()
    registry.register(name, profile)


def get_profile(name: str) -> Optional[BaseProfilePlugin]:
    """从全局注册表获取 Profile Plugin

    Args:
        name: Plugin 名称

    Returns:
        Optional[BaseProfilePlugin]: Plugin 实例，如果不存在则返回 None

    Example:
        >>> profile = get_profile("seekdb")
        >>> if profile:
        ...     profile.should_skip_test(test_case)
    """
    registry = get_global_registry()
    return registry.get(name)


def unregister_profile(name: str) -> bool:
    """从全局注册表注销 Profile Plugin

    Args:
        name: Plugin 名称

    Returns:
        bool: 是否成功注销

    Example:
        >>> unregister_profile("seekdb")
    """
    registry = get_global_registry()
    return registry.unregister(name)


def list_profiles() -> List[str]:
    """列出全局注册表中的所有 Plugin 名称

    Returns:
        List[str]: Plugin 名称列表

    Example:
        >>> names = list_profiles()
        >>> print(f"Available profiles: {names}")
    """
    registry = get_global_registry()
    return registry.list_all()


def get_all_profiles() -> List[BaseProfilePlugin]:
    """获取全局注册表中的所有 Plugin 实例

    Returns:
        List[BaseProfilePlugin]: Plugin 实例列表

    Example:
        >>> for profile in get_all_profiles():
        ...     print(profile.get_name())
    """
    registry = get_global_registry()
    return registry.get_all()


__all__ = [
    # Registry Class
    "ProfilePluginRegistry",
    # Global Registry
    "get_global_registry",
    "reset_global_registry",
    # Convenience Functions
    "register_profile",
    "get_profile",
    "unregister_profile",
    "list_profiles",
    "get_all_profiles",
]
