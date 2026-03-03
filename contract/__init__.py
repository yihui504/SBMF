"""
Contract DSL Runtime System

Phase 2: Contract DSL 加载、验证、构建系统。

Public API:
    - ContractError: 所有 Contract 错误的基类
    - ContractParseError: 语法/结构错误（快速失败）
    - ContractValidationError: 语义验证错误（聚合报告）
    - DependencyCycleError: 依赖循环错误
    - PriorityConflictError: 规则优先级冲突错误
    - ValidationLocation: 结构化的验证位置
    - ValidationIssue: 单个语义验证问题
    - DependencyCycle: 依赖循环描述
    - YAMLParser: YAML 解析器抽象基类
    - PyYAMLParser: PyYAML 解析器实现
    - ParserConfig: 解析器配置
    - get_default_parser: 获取默认解析器
    - ContractSchemaValidator: 结构验证器
    - SemanticValidator: 语义验证器
    - ContractBuilder: Contract 构建器
    - build_contract: 便捷的 Contract 构建函数
    - ValidatedRawContract: Schema 验证后的 Contract
    - SemanticallyValidContract: 语义验证后的 Contract
    - Contract: 最终的可执行 Contract 对象
"""

# ================================================================
# 异常层次
# ================================================================

from contract.errors import (
    ContractError,
    ContractParseError,
    ContractValidationError,
    DependencyCycleError,
    PriorityConflictError,
    AmbiguousDependencyRefError,
    UndefinedDependencyRefError,
)

# ================================================================
# 数据结构
# ================================================================

from contract.errors import (
    ValidationLocation,
    ValidationIssue,
    DependencyCycle,
)

# ================================================================
# Parser
# ================================================================

from contract.parser import (
    YAMLParser,
    PyYAMLParser,
    ParserConfig,
    get_default_parser,
)

# ================================================================
# Schema
# ================================================================

from contract.schema import (
    ValidatedRawContract,
    ValidatedRawSlot,
    ValidatedRawSlotDependency,
    SemanticallyValidContract,
    Contract,
)

# ================================================================
# Builder
# ================================================================

from contract.builder import (
    ContractBuilder,
    build_contract,
)

# ================================================================
# Types
# ================================================================

from contract.types import (
    SlotKey,
    SlotReference,
)

# ================================================================
# Validators
# ================================================================

from contract.validator import (
    ContractSchemaValidator,
)

from contract.semantic_validator import (
    SemanticValidator,
)

# ================================================================
# Schema & Builder
# ================================================================

from contract.schema import (
    SemanticallyValidContract,
    Contract,
)

from contract.builder import (
    ContractBuilder,
    build_contract,
)

# ================================================================
# Unified API
# ================================================================

from contract.api import (
    load_contract,
    load_contract_from_string,
    load_contract_with_validation_result,
)

# ================================================================
# Public API 导出
# ================================================================

__all__ = [
    # Exceptions
    "ContractError",
    "ContractParseError",
    "ContractValidationError",
    "DependencyCycleError",
    "PriorityConflictError",
    "AmbiguousDependencyRefError",
    "UndefinedDependencyRefError",
    # Data structures
    "ValidationLocation",
    "ValidationIssue",
    "DependencyCycle",
    # Parser
    "YAMLParser",
    "PyYAMLParser",
    "ParserConfig",
    "get_default_parser",
    # Schema
    "ValidatedRawContract",
    "ValidatedRawSlot",
    "ValidatedRawSlotDependency",
    "SemanticallyValidContract",
    "Contract",
    # Types
    "SlotKey",
    "SlotReference",
    # Validators
    "ContractSchemaValidator",
    "SemanticValidator",
    # Builder
    "ContractBuilder",
    "build_contract",
    # Unified API
    "load_contract",
    "load_contract_from_string",
    "load_contract_with_validation_result",
]
