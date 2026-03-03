"""
Contract DSL 统一加载 API

提供从 YAML 文件到 Contract 对象的一站式加载功能。
"""

from pathlib import Path
from typing import Union, Tuple, Dict, Any

from contract.parser import get_default_parser
from contract.validator import ContractSchemaValidator
from contract.semantic_validator import SemanticValidator
from contract.builder import build_contract
from contract import Contract
from contract.errors import ContractError, ContractParseError, ContractValidationError


def load_contract(source: Union[str, Path]) -> Contract:
    """从 YAML 文件加载 Contract 对象（一站式 API）

    完整流程：
    1. YAML 解析
    2. Schema 结构验证（快速失败）
    3. 语义验证（错误聚合）
    4. 依赖图构建与循环检测
    5. Contract 对象构建

    Args:
        source: YAML 文件路径（str 或 Path）

    Returns:
        Contract: 完整验证后的 Contract 对象

    Raises:
        ContractParseError: YAML 解析失败或 Schema 验证失败
        ContractValidationError: 语义验证失败（包含所有错误）
        DependencyCycleError: 依赖循环检测失败
        PriorityConflictError: 规则优先级冲突

    Example:
        >>> from contract import load_contract
        >>> contract = load_contract("contracts/seekdb.yaml")
        >>> print(f"Loaded {len(contract.core_slots)} slots")
    """
    # Step 1: Parse YAML
    parser = get_default_parser()
    raw_data = parser.load_file(source)

    # Step 2: Schema validation (fast-fail)
    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(raw_data)

    # Step 3: Semantic validation (error aggregation)
    semantic_validator = SemanticValidator()
    semantically_valid = semantic_validator.validate(validated)

    # Step 4: Build Contract object
    contract = build_contract(semantically_valid)

    return contract


def load_contract_from_string(content: str) -> Contract:
    """从 YAML 字符串加载 Contract 对象

    Args:
        content: YAML 格式的字符串

    Returns:
        Contract: 完整验证后的 Contract 对象

    Raises:
        ContractParseError: YAML 解析失败或 Schema 验证失败
        ContractValidationError: 语义验证失败
        DependencyCycleError: 依赖循环检测失败
        PriorityConflictError: 规则优先级冲突

    Example:
        >>> yaml_content = '''
        ... database_name: test_db
        ... core_slots:
        ...   - slot_name: dimension
        ...     type: integer
        ...     scope: COLLECTION
        ...     depends_on: []
        ... '''
        >>> from contract import load_contract_from_string
        >>> contract = load_contract_from_string(yaml_content)
    """
    # Step 1: Parse YAML from string
    parser = get_default_parser()
    raw_data = parser.load_string(content)

    # Step 2: Schema validation
    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(raw_data)

    # Step 3: Semantic validation
    semantic_validator = SemanticValidator()
    semantically_valid = semantic_validator.validate(validated)

    # Step 4: Build Contract object
    contract = build_contract(semantically_valid)

    return contract


def load_contract_with_validation_result(source: Union[str, Path]) -> Tuple[Contract, Dict[str, Any]]:
    """加载 Contract 并返回验证结果（用于调试）

    与 load_contract 类似，但返回额外的验证信息。

    Args:
        source: YAML 文件路径或 YAML 字符串内容

    Returns:
        tuple: (Contract 对象, 验证信息列表)

    Example:
        >>> from contract import load_contract_with_validation_result
        >>> contract, info = load_contract_with_validation_result("contract.yaml")
        >>> print(f"Loaded {info['slot_count']} slots")
        >>> print(f"Dependency graph has {info['edge_count']} edges")
    """
    # Step 1: Parse YAML
    parser = get_default_parser()

    # 判断是文件路径还是 YAML 字符串内容
    if isinstance(source, str) and source.strip().startswith(("database_name:", "core_slots:", "#", "-")):
        # YAML 字符串内容
        raw_data = parser.load_string(source)
    else:
        # 文件路径
        raw_data = parser.load_file(source)

    # Step 2: Schema validation
    schema_validator = ContractSchemaValidator()
    validated = schema_validator.validate(raw_data)

    # Step 3: Semantic validation
    semantic_validator = SemanticValidator()
    semantically_valid = semantic_validator.validate(validated)

    # Step 4: Build Contract object
    contract = build_contract(semantically_valid)

    # Collect validation info
    info = {
        "slot_count": len(contract.core_slots),
        "edge_count": len(contract.dependency_graph.edges),
        "scopes": set(slot.scope for slot in contract.core_slots),
        "rule_count": sum(len(slot.rules) for slot in contract.core_slots),
        "enabled_rule_count": sum(
            len([r for r in slot.rules if r.enabled])
            for slot in contract.core_slots
        ),
    }

    return contract, info


__all__ = [
    "load_contract",
    "load_contract_from_string",
    "load_contract_with_validation_result",
]
