"""
Contract DSL Builder

将 SemanticallyValidContract 转换为最终的 Contract 对象。
"""

from contract.schema import (
    SemanticallyValidContract,
    Contract,
    NormalizedSlot,
    DependencyGraph,
)


class ContractBuilder:
    """Contract Builder

    将语义验证后的 SemanticallyValidContract 转换为最终的 Contract 对象。

    M6: 实现 Contract 构建逻辑
    """

    def build(self, validated_contract: SemanticallyValidContract) -> Contract:
        """构建最终的 Contract 对象

        Args:
            validated_contract: 语义验证后的 Contract

        Returns:
            Contract: 最终的可执行 Contract 对象
        """
        # 将 List 转换为 Tuple 以确保不可变性
        core_slots = tuple(validated_contract.core_slots)

        # 创建 Contract 对象
        return Contract(
            database_name=validated_contract.database_name,
            version=validated_contract.version,
            core_slots=core_slots,
            dependency_graph=validated_contract.dependency_graph
        )


# ================================================================
# 便捷函数
# ================================================================

def build_contract(validated_contract: SemanticallyValidContract) -> Contract:
    """便捷函数：构建 Contract 对象

    Args:
        validated_contract: 语义验证后的 Contract

    Returns:
        Contract: 最终的可执行 Contract 对象
    """
    builder = ContractBuilder()
    return builder.build(validated_contract)
