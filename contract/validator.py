"""
Contract DSL Schema Validator

结构验证器（快速失败阶段）：
- 验证字段存在性
- 验证字段类型正确性
- 验证枚举值合法性
- 验证基本形状约束

不做：
- 引用存在性检查（reference_slot, depends_on）
- 重复 slot 检查
- 依赖循环检测
- 规则优先级冲突
"""

from typing import List, Dict, Any, Optional, Union
from contract.errors import ContractParseError, ValidationLocation
from contract.schema import (
    ValidatedRawContract,
    ValidatedRawSlot,
    ValidatedRawSlotDependency,
)


# ================================================================
# 合法的枚举值
# ================================================================

VALID_SLOT_TYPES = {"integer", "float", "string", "enum", "boolean", "vector"}
VALID_SCOPES = {"DATABASE", "COLLECTION", "PARTITION", "INDEX", "REPLICA"}
VALID_SEVERITIES = {"HIGH", "MEDIUM", "LOW"}
VALID_RULE_TYPES = {"relational", "range", "conditional", "enum", "type"}
VALID_COMPARISON_OPERATORS = {">=", "<=", ">", "<", "==", "!=", "in", "not_in"}


# ================================================================
# Schema Validator
# ================================================================

class ContractSchemaValidator:
    """Contract DSL 结构验证器

    职责：
    - 验证顶层结构（core_slots 存在且为列表）
    - 验证每个 core_slots 项的基本结构
    - 验证字段类型正确性
    - 验证枚举值在允许范围内
    - 验证规则基本结构

    不负责：
    - 检测重复 slot 名称（语义验证）
    - 检查 reference_slot 存在性（语义验证）
    - 检查 depends_on 引用存在性（语义验证）
    - 检查依赖循环（语义验证）
    - 检查规则优先级冲突（语义验证）
    """

    def validate(self, raw_data: Dict[str, Any]) -> ValidatedRawContract:
        """验证原始 Contract 数据

        Args:
            raw_data: YAML 解析后的字典

        Returns:
            ValidatedRawContract: 验证后的数据

        Raises:
            ContractParseError: 结构验证失败（快速失败）
        """
        # 验证顶层字段存在性
        if "core_slots" not in raw_data:
            raise ContractParseError(
                "Missing required field: 'core_slots'",
                location=ValidationLocation()
            )

        core_slots_raw = raw_data["core_slots"]
        if not isinstance(core_slots_raw, list):
            raise ContractParseError(
                f"Field 'core_slots' must be a list, got {type(core_slots_raw).__name__}",
                location=ValidationLocation(field_path="core_slots")
            )

        # 验证并转换每个 slot
        validated_slots = []
        for idx, slot_raw in enumerate(core_slots_raw):
            validated_slot = self._validate_slot(slot_raw, idx)
            validated_slots.append(validated_slot)

        # 构造验证后的 Contract
        return ValidatedRawContract(
            database_name=raw_data.get("database_name"),
            version=raw_data.get("version"),
            core_slots=validated_slots
        )

    def _validate_slot(self, slot_raw: Any, index: int) -> ValidatedRawSlot:
        """验证单个槽定义

        Args:
            slot_raw: 槽的原始数据
            index: 槽在 core_slots 列表中的索引（用于错误定位）

        Returns:
            ValidatedRawSlot: 验证后的槽数据

        Raises:
            ContractParseError: 槽验证失败
        """
        slot_location = ValidationLocation(field_path=f"core_slots[{index}]")

        if not isinstance(slot_raw, dict):
            raise ContractParseError(
                f"Slot at index {index} must be a dict, got {type(slot_raw).__name__}",
                location=slot_location
            )

        # 验证必填字段
        required_fields = {
            "slot_name": str,
            "description": str,
            "type": str,
            "scope": str,
        }
        for field_name, expected_type in required_fields.items():
            if field_name not in slot_raw:
                raise ContractParseError(
                    f"Missing required field: '{field_name}'",
                    location=slot_location
                )
            if not isinstance(slot_raw[field_name], expected_type):
                actual_type = type(slot_raw[field_name]).__name__
                raise ContractParseError(
                    f"Field '{field_name}' must be {expected_type.__name__}, got {actual_type}",
                    location=ValidationLocation(
                        slot_name=slot_raw.get("slot_name"),
                        field_path=f"core_slots[{index}].{field_name}"
                    )
                )

        # 验证 slot_name 非空
        slot_name = slot_raw["slot_name"]
        if not slot_name or not slot_name.strip():
            raise ContractParseError(
                "Field 'slot_name' cannot be empty",
                location=ValidationLocation(
                    slot_name="<empty>",
                    field_path=f"core_slots[{index}].slot_name"
                )
            )

        # 验证 enum 值
        slot_type = slot_raw["type"]
        if slot_type not in VALID_SLOT_TYPES:
            raise ContractParseError(
                f"Invalid type '{slot_type}'. Must be one of: {', '.join(sorted(VALID_SLOT_TYPES))}",
                location=ValidationLocation(
                    slot_name=slot_name,
                    field_path=f"core_slots[{index}].type"
                )
            )

        scope = slot_raw["scope"]
        if scope not in VALID_SCOPES:
            raise ContractParseError(
                f"Invalid scope '{scope}'. Must be one of: {', '.join(sorted(VALID_SCOPES))}",
                location=ValidationLocation(
                    slot_name=slot_name,
                    field_path=f"core_slots[{index}].scope"
                )
            )

        # 验证 depends_on 字段（如果存在）
        depends_on = self._validate_depends_on(slot_raw.get("depends_on", []), slot_name, index)

        # 验证 constraints（如果存在）
        constraints = self._validate_constraints(slot_raw.get("constraints"), slot_name, index)

        # 验证 rules（如果存在）
        rules = self._validate_rules(slot_raw.get("rules"), slot_name, index)

        return ValidatedRawSlot(
            slot_name=slot_name,
            description=slot_raw["description"],
            type=slot_type,
            scope=scope,
            depends_on=depends_on,
            constraints=constraints,
            rules=rules,
        )

    def _validate_depends_on(
        self,
        depends_on_raw: Any,
        slot_name: str,
        slot_index: int
    ) -> List[ValidatedRawSlotDependency]:
        """验证 depends_on 字段

        Args:
            depends_on_raw: depends_on 原始数据
            slot_name: 当前槽名称（用于错误定位）
            slot_index: 槽索引

        Returns:
            List[ValidatedRawSlotDependency]: 验证后的依赖列表

        Raises:
            ContractParseError: depends_on 验证失败
        """
        location = ValidationLocation(
            slot_name=slot_name,
            field_path=f"core_slots[{slot_index}].depends_on"
        )

        # depends_on 必须是列表
        if not isinstance(depends_on_raw, list):
            raise ContractParseError(
                f"Field 'depends_on' must be a list, got {type(depends_on_raw).__name__}",
                location=location
            )

        validated = []
        for idx, dep_raw in enumerate(depends_on_raw):
            dep_location = ValidationLocation(
                slot_name=slot_name,
                field_path=f"core_slots[{slot_index}].depends_on[{idx}]"
            )

            if isinstance(dep_raw, str):
                # 简化格式: "slot_name"
                if not dep_raw.strip():
                    raise ContractParseError(
                        "Dependency slot_name cannot be empty",
                        location=dep_location
                    )
                validated.append(ValidatedRawSlotDependency(slot_name=dep_raw, reason=None))

            elif isinstance(dep_raw, dict):
                # 完整格式: {"slot_name": "xxx", "reason": "xxx"}
                if "slot_name" not in dep_raw:
                    raise ContractParseError(
                        "Dependency dict must contain 'slot_name' field",
                        location=dep_location
                    )
                dep_slot_name = dep_raw["slot_name"]
                if not isinstance(dep_slot_name, str) or not dep_slot_name.strip():
                    raise ContractParseError(
                        "Dependency 'slot_name' must be a non-empty string",
                        location=dep_location
                    )
                reason = dep_raw.get("reason")
                if reason is not None and not isinstance(reason, str):
                    raise ContractParseError(
                        "Dependency 'reason' must be a string",
                        location=dep_location
                    )
                validated.append(ValidatedRawSlotDependency(
                    slot_name=dep_slot_name,
                    reason=reason
                ))

            else:
                raise ContractParseError(
                    f"Dependency must be string or dict, got {type(dep_raw).__name__}",
                    location=dep_location
                )

        return validated

    def _validate_constraints(
        self,
        constraints_raw: Any,
        slot_name: str,
        slot_index: int
    ) -> Optional[Dict[str, Any]]:
        """验证 constraints 字段

        Args:
            constraints_raw: constraints 原始数据
            slot_name: 槽名称
            slot_index: 槽索引

        Returns:
            验证后的 constraints（如果存在）

        Raises:
            ContractParseError: constraints 验证失败
        """
        if constraints_raw is None:
            return None

        location = ValidationLocation(
            slot_name=slot_name,
            field_path=f"core_slots[{slot_index}].constraints"
        )

        if not isinstance(constraints_raw, dict):
            raise ContractParseError(
                f"Field 'constraints' must be a dict, got {type(constraints_raw).__name__}",
                location=location
            )

        # 验证 range 约束（如果存在）
        if "range" in constraints_raw:
            range_raw = constraints_raw["range"]
            if range_raw is not None:
                self._validate_range_constraint(range_raw, slot_name, slot_index)

        # 验证 enum 约束（如果存在）
        if "enum" in constraints_raw:
            enum_raw = constraints_raw["enum"]
            if enum_raw is not None:
                self._validate_enum_constraint(enum_raw, slot_name, slot_index)

        return constraints_raw

    def _validate_range_constraint(
        self,
        range_raw: Any,
        slot_name: str,
        slot_index: int
    ) -> None:
        """验证 range 约束"""
        location = ValidationLocation(
            slot_name=slot_name,
            field_path=f"core_slots[{slot_index}].constraints.range"
        )

        if not isinstance(range_raw, dict):
            raise ContractParseError(
                f"Range constraint must be a dict, got {type(range_raw).__name__}",
                location=location
            )

        # 验证 min/max 类型（必须是数字或 None）
        for field in ["min", "max"]:
            if field in range_raw:
                value = range_raw[field]
                if value is not None and not isinstance(value, (int, float)):
                    raise ContractParseError(
                        f"Range constraint '{field}' must be a number, got {type(value).__name__}",
                        location=ValidationLocation(
                            slot_name=slot_name,
                            field_path=f"core_slots[{slot_index}].constraints.range.{field}"
                        )
                    )

        # 验证 inclusive 类型
        if "inclusive" in range_raw:
            if not isinstance(range_raw["inclusive"], bool):
                raise ContractParseError(
                    f"Range constraint 'inclusive' must be boolean, got {type(range_raw['inclusive']).__name__}",
                    location=ValidationLocation(
                        slot_name=slot_name,
                        field_path=f"core_slots[{slot_index}].constraints.range.inclusive"
                    )
                )

    def _validate_enum_constraint(
        self,
        enum_raw: Any,
        slot_name: str,
        slot_index: int
    ) -> None:
        """验证 enum 约束"""
        location = ValidationLocation(
            slot_name=slot_name,
            field_path=f"core_slots[{slot_index}].constraints.enum"
        )

        if not isinstance(enum_raw, dict):
            raise ContractParseError(
                f"Enum constraint must be a dict, got {type(enum_raw).__name__}",
                location=location
            )

        if "values" not in enum_raw:
            raise ContractParseError(
                "Enum constraint must contain 'values' field",
                location=location
            )

        values = enum_raw["values"]
        if not isinstance(values, list):
            raise ContractParseError(
                f"Enum constraint 'values' must be a list, got {type(values).__name__}",
                location=ValidationLocation(
                    slot_name=slot_name,
                    field_path=f"core_slots[{slot_index}].constraints.enum.values"
                )
            )

        # 验证 strict 类型（如果存在）
        if "strict" in enum_raw:
            if not isinstance(enum_raw["strict"], bool):
                raise ContractParseError(
                    f"Enum constraint 'strict' must be boolean, got {type(enum_raw['strict']).__name__}",
                    location=ValidationLocation(
                        slot_name=slot_name,
                        field_path=f"core_slots[{slot_index}].constraints.enum.strict"
                    )
                )

    def _validate_rules(
        self,
        rules_raw: Any,
        slot_name: str,
        slot_index: int
    ) -> Optional[List[Dict[str, Any]]]:
        """验证 rules 字段

        Args:
            rules_raw: rules 原始数据
            slot_name: 槽名称
            slot_index: 槽索引

        Returns:
            验证后的 rules 列表（如果存在）

        Raises:
            ContractParseError: rules 验证失败
        """
        if rules_raw is None:
            return None

        location = ValidationLocation(
            slot_name=slot_name,
            field_path=f"core_slots[{slot_index}].rules"
        )

        if not isinstance(rules_raw, list):
            raise ContractParseError(
                f"Field 'rules' must be a list, got {type(rules_raw).__name__}",
                location=location
            )

        # 验证每个规则
        for idx, rule_raw in enumerate(rules_raw):
            self._validate_rule(rule_raw, slot_name, slot_index, idx)

        return rules_raw

    def _validate_rule(
        self,
        rule_raw: Any,
        slot_name: str,
        slot_index: int,
        rule_index: int
    ) -> None:
        """验证单个规则"""
        rule_location = ValidationLocation(
            slot_name=slot_name,
            field_path=f"core_slots[{slot_index}].rules[{rule_index}]"
        )

        if not isinstance(rule_raw, dict):
            raise ContractParseError(
                f"Rule must be a dict, got {type(rule_raw).__name__}",
                location=rule_location
            )

        # 验证必填字段
        required_fields = {
            "rule_id": str,
            "type": str,
            "severity": str,
            "enabled": bool,
        }
        for field_name, expected_type in required_fields.items():
            if field_name not in rule_raw:
                raise ContractParseError(
                    f"Missing required field: '{field_name}'",
                    location=rule_location
                )
            if not isinstance(rule_raw[field_name], expected_type):
                actual_type = type(rule_raw[field_name]).__name__
                raise ContractParseError(
                    f"Field '{field_name}' must be {expected_type.__name__}, got {actual_type}",
                    location=ValidationLocation(
                        slot_name=slot_name,
                        field_path=f"core_slots[{slot_index}].rules[{rule_index}].{field_name}"
                    )
                )

        # 验证 rule_id 非空
        rule_id = rule_raw["rule_id"]
        if not rule_id or not rule_id.strip():
            raise ContractParseError(
                "Field 'rule_id' cannot be empty",
                location=ValidationLocation(
                    slot_name=slot_name,
                    field_path=f"core_slots[{slot_index}].rules[{rule_index}].rule_id"
                )
            )

        # 验证 enum 值
        rule_type = rule_raw["type"]
        if rule_type not in VALID_RULE_TYPES:
            raise ContractParseError(
                f"Invalid rule type '{rule_type}'. Must be one of: {', '.join(sorted(VALID_RULE_TYPES))}",
                location=ValidationLocation(
                    slot_name=slot_name,
                    field_path=f"core_slots[{slot_index}].rules[{rule_index}].type"
                )
            )

        severity = rule_raw["severity"]
        if severity not in VALID_SEVERITIES:
            raise ContractParseError(
                f"Invalid severity '{severity}'. Must be one of: {', '.join(sorted(VALID_SEVERITIES))}",
                location=ValidationLocation(
                    slot_name=slot_name,
                    field_path=f"core_slots[{slot_index}].rules[{rule_index}].severity"
                )
            )

        # 验证 priority（如果存在）
        if "priority" in rule_raw:
            priority = rule_raw["priority"]
            if not isinstance(priority, int):
                raise ContractParseError(
                    f"Field 'priority' must be an integer, got {type(priority).__name__}",
                    location=ValidationLocation(
                        slot_name=slot_name,
                        field_path=f"core_slots[{slot_index}].rules[{rule_index}].priority"
                    )
                )

        # 验证规则特定内容
        if rule_type == "relational":
            self._validate_relational_rule(rule_raw, slot_name, slot_index, rule_index)
        elif rule_type == "range":
            self._validate_range_rule(rule_raw, slot_name, slot_index, rule_index)
        elif rule_type == "enum":
            self._validate_enum_rule(rule_raw, slot_name, slot_index, rule_index)

    def _validate_relational_rule(
        self,
        rule_raw: Dict[str, Any],
        slot_name: str,
        slot_index: int,
        rule_index: int
    ) -> None:
        """验证关系规则"""
        if "relational" not in rule_raw:
            raise ContractParseError(
                f"Rule type 'relational' requires 'relational' field",
                location=ValidationLocation(
                    slot_name=slot_name,
                    field_path=f"core_slots[{slot_index}].rules[{rule_index}]"
                )
            )

        relational = rule_raw["relational"]
        if not isinstance(relational, dict):
            raise ContractParseError(
                f"Field 'relational' must be a dict, got {type(relational).__name__}",
                location=ValidationLocation(
                    slot_name=slot_name,
                    field_path=f"core_slots[{slot_index}].rules[{rule_index}].relational"
                )
            )

        # 验证必填字段
        if "operator" not in relational:
            raise ContractParseError(
                "Relational rule missing 'operator' field",
                location=ValidationLocation(
                    slot_name=slot_name,
                    field_path=f"core_slots[{slot_index}].rules[{rule_index}].relational"
                )
            )

        operator = relational["operator"]
        if not isinstance(operator, str) or operator not in VALID_COMPARISON_OPERATORS:
            raise ContractParseError(
                f"Invalid operator '{operator}'. Must be one of: {', '.join(sorted(VALID_COMPARISON_OPERATORS))}",
                location=ValidationLocation(
                    slot_name=slot_name,
                    field_path=f"core_slots[{slot_index}].rules[{rule_index}].relational.operator"
                )
            )

        if "reference_slot" not in relational:
            raise ContractParseError(
                "Relational rule missing 'reference_slot' field",
                location=ValidationLocation(
                    slot_name=slot_name,
                    field_path=f"core_slots[{slot_index}].rules[{rule_index}].relational"
                )
            )

        if not isinstance(relational["reference_slot"], str):
            raise ContractParseError(
                f"Field 'reference_slot' must be a string, got {type(relational['reference_slot']).__name__}",
                location=ValidationLocation(
                    slot_name=slot_name,
                    field_path=f"core_slots[{slot_index}].rules[{rule_index}].relational.reference_slot"
                )
            )

        if "error_message" not in relational:
            raise ContractParseError(
                "Relational rule missing 'error_message' field",
                location=ValidationLocation(
                    slot_name=slot_name,
                    field_path=f"core_slots[{slot_index}].rules[{rule_index}].relational"
                )
            )

    def _validate_range_rule(
        self,
        rule_raw: Dict[str, Any],
        slot_name: str,
        slot_index: int,
        rule_index: int
    ) -> None:
        """验证范围规则"""
        if "range" not in rule_raw:
            raise ContractParseError(
                f"Rule type 'range' requires 'range' field",
                location=ValidationLocation(
                    slot_name=slot_name,
                    field_path=f"core_slots[{slot_index}].rules[{rule_index}]"
                )
            )

        range_data = rule_raw["range"]
        if not isinstance(range_data, dict):
            raise ContractParseError(
                f"Field 'range' must be a dict, got {type(range_data).__name__}",
                location=ValidationLocation(
                    slot_name=slot_name,
                    field_path=f"core_slots[{slot_index}].rules[{rule_index}].range"
                )
            )

        # 验证必填字段
        for field in ["min_value", "max_value"]:
            if field not in range_data:
                raise ContractParseError(
                    f"Range rule missing '{field}' field",
                    location=ValidationLocation(
                        slot_name=slot_name,
                        field_path=f"core_slots[{slot_index}].rules[{rule_index}].range"
                    )
                )

    def _validate_enum_rule(
        self,
        rule_raw: Dict[str, Any],
        slot_name: str,
        slot_index: int,
        rule_index: int
    ) -> None:
        """验证枚举规则"""
        if "enum" not in rule_raw:
            raise ContractParseError(
                f"Rule type 'enum' requires 'enum' field",
                location=ValidationLocation(
                    slot_name=slot_name,
                    field_path=f"core_slots[{slot_index}].rules[{rule_index}]"
                )
            )

        enum_data = rule_raw["enum"]
        if not isinstance(enum_data, dict):
            raise ContractParseError(
                f"Field 'enum' must be a dict, got {type(enum_data).__name__}",
                location=ValidationLocation(
                    slot_name=slot_name,
                    field_path=f"core_slots[{slot_index}].rules[{rule_index}].enum"
                )
            )

        if "allowed_values" not in enum_data:
            raise ContractParseError(
                "Enum rule missing 'allowed_values' field",
                location=ValidationLocation(
                    slot_name=slot_name,
                    field_path=f"core_slots[{slot_index}].rules[{rule_index}].enum"
                )
            )

        if not isinstance(enum_data["allowed_values"], list):
            raise ContractParseError(
                f"Field 'allowed_values' must be a list, got {type(enum_data['allowed_values']).__name__}",
                location=ValidationLocation(
                    slot_name=slot_name,
                    field_path=f"core_slots[{slot_index}].rules[{rule_index}].enum.allowed_values"
                )
            )
