"""
Profile Plugin Errors

定义 Profile Plugin 层使用的错误类型。
"""

from typing import Optional, Dict, Any


# ================================================================
# Base Error Class
# ================================================================

class ProfileError(Exception):
    """Profile Plugin 基础错误类

    所有 Profile Plugin 相关的异常都应继承此类。

    Attributes:
        message: 错误消息
        profile_name: Profile 名称（可选）
        context: 错误上下文信息（可选）
    """

    def __init__(
        self,
        message: str,
        profile_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """初始化 Profile 错误

        Args:
            message: 错误消息
            profile_name: Profile 名称
            context: 错误上下文信息
        """
        self.message = message
        self.profile_name = profile_name
        self.context = context or {}

        # 构建完整的错误消息
        full_message = self._build_message()
        super().__init__(full_message)

    def _build_message(self) -> str:
        """构建完整的错误消息"""
        parts = []

        if self.profile_name:
            parts.append(f"[{self.profile_name}]")

        parts.append(self.message)

        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"({context_str})")

        return " ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式

        Returns:
            Dict[str, Any]: 错误信息字典
        """
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "profile_name": self.profile_name,
            "context": self.context
        }


# ================================================================
# Skip Error
# ================================================================

class ProfileSkipError(ProfileError):
    """测试跳过错误

    当 Profile Plugin 决定跳过某个测试时抛出。

    注意：这不是一个真正的"错误"，而是一种控制流机制。
    预条件门禁会捕获此错误并返回 PRECONDITION_FAILED。

    Attributes:
        test_case_id: 测试用例 ID
        skip_reason: 跳过原因
    """

    def __init__(
        self,
        skip_reason: str,
        test_case_id: Optional[str] = None,
        profile_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """初始化跳过错误

        Args:
            skip_reason: 跳过原因
            test_case_id: 测试用例 ID
            profile_name: Profile 名称
            context: 错误上下文信息
        """
        self.test_case_id = test_case_id
        self.skip_reason = skip_reason

        # 添加到上下文
        if context is None:
            context = {}
        if test_case_id:
            context["test_case_id"] = test_case_id

        super().__init__(
            message=skip_reason,
            profile_name=profile_name,
            context=context
        )

    def _build_message(self) -> str:
        """构建跳过消息"""
        base = super()._build_message()
        return f"SKIP: {base}"


# ================================================================
# Post-Process Error
# ================================================================

class ProfilePostProcessError(ProfileError):
    """结果后处理错误

    当 Profile Plugin 在后处理结果时发生错误时抛出。

    Attributes:
        original_result: 原始结果
        processing_step: 处理步骤（可选）
    """

    def __init__(
        self,
        message: str,
        original_result: Any = None,
        processing_step: Optional[str] = None,
        profile_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """初始化后处理错误

        Args:
            message: 错误消息
            original_result: 原始结果
            processing_step: 处理步骤
            profile_name: Profile 名称
            context: 错误上下文信息
        """
        self.original_result = original_result
        self.processing_step = processing_step

        # 添加到上下文
        if context is None:
            context = {}
        if processing_step:
            context["processing_step"] = processing_step

        super().__init__(
            message=message,
            profile_name=profile_name,
            context=context
        )

    def _build_message(self) -> str:
        """构建后处理错误消息"""
        base = super()._build_message()
        return f"POST_PROCESS_ERROR: {base}"


# ================================================================
# Registration Error
# ================================================================

class ProfileRegistrationError(ProfileError):
    """Profile 注册错误

    当注册或获取 Profile Plugin 时发生错误时抛出。

    常见场景：
    - 尝试注册已存在的 Profile 名称
    - 尝试获取不存在的 Profile
    """

    def __init__(
        self,
        message: str,
        profile_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """初始化注册错误

        Args:
            message: 错误消息
            profile_name: Profile 名称
            context: 错误上下文信息
        """
        super().__init__(
            message=message,
            profile_name=profile_name,
            context=context
        )

    def _build_message(self) -> str:
        """构建注册错误消息"""
        base = super()._build_message()
        return f"REGISTRATION_ERROR: {base}"


__all__ = [
    "ProfileError",
    "ProfileSkipError",
    "ProfilePostProcessError",
    "ProfileRegistrationError",
]
