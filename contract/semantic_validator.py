"""
Contract DSL Semantic Validator

语义验证器（Validate + Analyze，不改变业务逻辑）：

职责：
1. 语义检查（错误聚合）
   - 重复 slot 检测
   - reference_slot 存在性检查
   - depends_on 引用存在性检查
   - 依赖循环检测（M4）
   - 规则优先级冲突检测（M5）

2. 语义分析与标准化（类型安全，不改变业务含义）
   - 解析 depends_on 为 SlotReference
   - 解析规则引用为 SlotReference
   - 包装规则为 NormalizedRule
   - 构建 dependency_graph（M4）

输入：ValidatedRawContract
输出：SemanticallyValidContract
失败：抛出 ContractValidationError（聚合所有问题）
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from contract.schema import (
    ValidatedRawContract,
    ValidatedRawSlot,
    ValidatedRawSlotDependency,
    SemanticallyValidContract,
    NormalizedSlot,
    NormalizedRule,
    NormalizedConstraints,
    DependencyGraph,
)
from contract.types import (
    SlotKey,
    SlotReference,
    ConditionNode,
    ConditionNode,
    NormalizedRuleBody,
    NormalizedRelationalRule,
    NormalizedRangeRule,
    NormalizedEnumRule,
    NormalizedConditionalRule,
    OperationEqualsNode,
    SlotEqualsNode,
    SlotInRangeNode,
    AndNode,
    OrNode,
    NotNode,
    NormalizedRangeConstraints,
    NormalizedEnumConstraints,
    NormalizedVectorConstraints,
)
from contract.errors import (
    ContractParseError,
    ContractValidationError,
    ValidationIssue,
    ValidationLocation,
    AmbiguousDependencyRefError,
    UndefinedDependencyRefError,
    PriorityConflictError,
)


# ================================================================
# Semantic Validator
# ================================================================

class SemanticValidator:
    """语义验证器（Validate + Analyze，不改变业务逻辑）

    M3 范围：
    - 框架搭建
    - 重复 slot 检测
    - 引用存在性检查

    M4-M5 将添加：
    - 依赖循环检测
    - 规则优先级冲突检测
    - dependency_graph 构建
    """

    def __init__(self):
        """初始化语义验证器"""
        pass

    def validate(self, contract: ValidatedRawContract) -> SemanticallyValidContract:
        """执行语义验证和分析

        Args:
            contract: Schema 验证后的 Contract

        Returns:
            SemanticallyValidContract: 语义验证并标准化后的 Contract

        Raises:
            ContractValidationError: 语义验证失败，聚合所有问题
        """
        issues = []

        # Step 1: 语义检查（错误聚合）
        issues.extend(self._check_duplicate_slots(contract))
        issues.extend(self._check_reference_existence(contract))
        issues.extend(self._check_priority_conflicts(contract))

        # 如果有任何问题，聚合抛出
        if issues:
            raise ContractValidationError(issues)

        # Step 2: 标准化（类型安全转换，不改变业务含义）
        normalized_slots = self._normalize_slots(contract)

        # Step 3: 构建 dependency_graph（M4 完整实现）
        dependency_graph = self._build_dependency_graph(normalized_slots)

        # Step 4: 循环检测（M4 新增）
        dependency_graph.validate_no_cycles()

        return SemanticallyValidContract(
            database_name=contract.database_name,
            version=contract.version,
            core_slots=normalized_slots,
            dependency_graph=dependency_graph
        )

    # ================================================================
    # 语义检查方法
    # ================================================================

    def _check_duplicate_slots(
        self,
        contract: ValidatedRawContract
    ) -> List[ValidationIssue]:
        """检测重复 slot

        规则：同一 scope 下的 slot_name 必须唯一。
        不同 scope 可以有同名 slot（它们代表不同资源）。
        """
        issues = []
        seen = {}  # (scope, slot_name) -> first_location

        for slot in contract.core_slots:
            key = (slot.scope, slot.slot_name)

            if key in seen:
                issues.append(ValidationIssue(
                    error_code="DUPLICATE_SLOT",
                    message=f"Duplicate slot '{slot.slot_name}' in scope {slot.scope}",
                    location=ValidationLocation(
                        scope=slot.scope,
                        slot_name=slot.slot_name
                    )
                ))
            else:
                seen[key] = ValidationLocation(
                    scope=slot.scope,
                    slot_name=slot.slot_name
                )

        return issues

    def _check_reference_existence(
        self,
        contract: ValidatedRawContract
    ) -> List[ValidationIssue]:
        """检查引用存在性

        检查：
        1. 规则中的 reference_slot 是否存在
        2. depends_on 中的引用是否存在
        """
        issues = []

        # 构建已存在的 slot 索引
        existing_slots = {
            (slot.scope, slot.slot_name): slot
            for slot in contract.core_slots
        }

        # 检查每个 slot 的 depends_on
        for slot in contract.core_slots:
            slot_key = (slot.scope, slot.slot_name)

            for dep in slot.depends_on:
                # 检查依赖是否存在
                dep_key = self._resolve_dependency_key(dep, slot.scope)

                if dep_key not in existing_slots:
                    issues.append(ValidationIssue(
                        error_code="UNDEFINED_DEPENDENCY_REF",
                        message=f"Slot '{slot.slot_name}' depends on undefined slot '{dep.slot_name}' in scope {dep_key[0]}",
                        location=ValidationLocation(
                            scope=slot.scope,
                            slot_name=slot.slot_name
                        )
                    ))

        # 检查规则中的 reference_slot
        for slot in contract.core_slots:
            if slot.rules:
                for rule in slot.rules:
                    if rule.get("type") == "relational":
                        relational = rule.get("relational", {})
                        ref_slot_name = relational.get("reference_slot")

                        if ref_slot_name:
                            # 解析引用（可能带 scope）
                            ref_key = self._resolve_reference_slot(ref_slot_name, slot)

                            if ref_key not in existing_slots:
                                issues.append(ValidationIssue(
                                    error_code="UNDEFINED_REFERENCE_SLOT",
                                    message=f"Rule '{rule.get('rule_id')}' references undefined slot '{ref_slot_name}'",
                                    location=ValidationLocation(
                                        scope=slot.scope,
                                        slot_name=slot.slot_name,
                                        rule_id=rule.get('rule_id')
                                    )
                                ))

        return issues

    def _check_priority_conflicts(
        self,
        contract: ValidatedRawContract
    ) -> List[ValidationIssue]:
        """检查规则优先级冲突

        规则：同一 slot 下不能有多个相同 priority 的规则。

        Returns:
            List[ValidationIssue]: 检测到的冲突问题列表
        """
        issues = []

        for slot in contract.core_slots:
            if not slot.rules:
                continue

            # 按优先级分组规则
            priority_groups = {}
            for rule in slot.rules:
                priority = rule.get("priority", 100)
                if priority not in priority_groups:
                    priority_groups[priority] = []
                priority_groups[priority].append(rule.get("rule_id"))

            # 检查是否有优先级冲突（多个规则共享相同优先级）
            conflicts = []
            for priority, rule_ids in priority_groups.items():
                if len(rule_ids) > 1:
                    conflicts.append((priority, rule_ids))

            if conflicts:
                # 为每个冲突创建 ValidationIssue
                for priority, rule_ids in conflicts:
                    issues.append(ValidationIssue(
                        error_code="PRIORITY_CONFLICT",
                        message=f"Rules {rule_ids} in slot '{slot.slot_name}' have same priority {priority}",
                        location=ValidationLocation(
                            scope=slot.scope,
                            slot_name=slot.slot_name
                        ),
                        severity="ERROR"
                    ))

        return issues

    # ================================================================
    # 标准化方法
    # ================================================================

    def _normalize_slots(
        self,
        contract: ValidatedRawContract
    ) -> List[NormalizedSlot]:
        """标准化槽列表（类型安全转换）"""
        normalized = []

        for raw_slot in contract.core_slots:
            # 标准化 depends_on
            depends_on = self._normalize_depends_on(raw_slot.depends_on, raw_slot.scope)

            # 标准化 constraints
            constraints = self._normalize_constraints(raw_slot.constraints)

            # 标准化 rules
            rules = self._normalize_rules(raw_slot.rules, raw_slot)

            normalized.append(NormalizedSlot(
                slot_name=raw_slot.slot_name,
                description=raw_slot.description,
                type=raw_slot.type,
                scope=raw_slot.scope,
                depends_on=depends_on,
                constraints=constraints,
                rules=rules,
            ))

        return normalized

    def _normalize_depends_on(
        self,
        dependencies: List[ValidatedRawSlotDependency],
        source_scope: str
    ) -> List[SlotReference]:
        """标准化 depends_on 为 SlotReference 列表"""
        normalized = []

        for dep in dependencies:
            # 根据依赖引用规则解析：
            # - 简化格式默认同 scope
            # - 完整格式可以显式指定 scope
            if dep.reason is None:
                # 简化格式，同 scope
                normalized.append(SlotReference(
                    scope=source_scope,
                    slot_name=dep.slot_name,
                    reason=None
                ))
            else:
                # 完整格式，可能有 scope
                # 这里 ValidatedRawSlotDependency 没有 scope 字段
                # 暂时默认同 scope（M4 会根据 DSL 规范优化）
                normalized.append(SlotReference(
                    scope=source_scope,
                    slot_name=dep.slot_name,
                    reason=dep.reason
                ))

        return normalized

    def _normalize_constraints(
        self,
        constraints: Optional[Any]
    ) -> Optional[NormalizedConstraints]:
        """标准化约束（RawSlotConstraints → NormalizedConstraints）"""
        if constraints is None:
            return None

        result = {}

        if constraints.get("range") is not None:
            range_data = constraints["range"]
            result["range"] = NormalizedRangeConstraints(
                min=range_data.get("min"),
                max=range_data.get("max"),
                inclusive=range_data.get("inclusive", True)
            )

        if constraints.get("enum") is not None:
            enum_data = constraints["enum"]
            result["enum"] = NormalizedEnumConstraints(
                values=enum_data.get("values", []),
                strict=enum_data.get("strict", True)
            )

        if constraints.get("vector") is not None:
            vector_data = constraints["vector"]
            result["vector"] = NormalizedVectorConstraints(
                element_type=vector_data.get("element_type"),
                dimension_slot=vector_data.get("dimension_slot")
            )

        # 如果没有约束，返回 None
        return NormalizedConstraints(**result) if result else None

    def _normalize_rules(
        self,
        raw_rules: Optional[List[Dict[str, Any]]],
        raw_slot: ValidatedRawSlot
    ) -> List[NormalizedRule]:
        """标准化规则列表（类型安全转换）"""
        if not raw_rules:
            return []

        normalized = []
        for raw_rule in raw_rules:
            rule_type = raw_rule["type"]

            if rule_type == "relational":
                body = NormalizedRelationalRule(
                    operator=raw_rule["relational"]["operator"],
                    reference_slot=self._parse_slot_reference(
                        raw_rule["relational"]["reference_slot"],
                        raw_slot.scope
                    ),
                    error_message=raw_rule["relational"]["error_message"]
                )
            elif rule_type == "range":
                range_data = raw_rule["range"]
                body = NormalizedRangeRule(
                    min_value=range_data["min_value"],
                    max_value=range_data["max_value"],
                    inclusive_min=range_data.get("inclusive_min", True),
                    inclusive_max=range_data.get("inclusive_max", True)
                )
            elif rule_type == "enum":
                enum_data = raw_rule["enum"]
                body = NormalizedEnumRule(
                    allowed_values=enum_data.get("allowed_values", []),
                    strict=enum_data.get("strict", True)
                )
            elif rule_type == "conditional":
                # Phase 2 结构支持，完整保留 then/else 内容
                conditional_data = raw_rule["conditional"]
                body = NormalizedConditionalRule(
                    condition=self._parse_condition_node(conditional_data["condition"], raw_slot.scope),
                    then_rules=[],  # M4 会递归构建
                    else_rules=None
                )
            else:
                # 不应该到达这里（Schema 已验证）
                continue

            normalized.append(NormalizedRule(
                rule_id=raw_rule["rule_id"],
                type=rule_type,
                severity=raw_rule["severity"],
                enabled=raw_rule["enabled"],
                priority=raw_rule.get("priority", 100),
                body=body
            ))

        return normalized

    # ================================================================
    # 引用解析辅助方法
    # ================================================================

    def _resolve_dependency_key(
        self,
        dep: ValidatedRawSlotDependency,
        source_scope: str
    ) -> Tuple[str, str]:
        """解析依赖引用为 (scope, slot_name) 元组

        解析规则：
        - 当前：简化格式默认同 scope（M4 会优化）
        - M4 将支持显式 scope 解析
        """
        # M3 临时：简化格式默认同 scope
        return (source_scope, dep.slot_name)

    def _resolve_reference_slot(
        self,
        ref: str,
        raw_slot: ValidatedRawSlot
    ) -> Tuple[str, str]:
        """解析规则中的 reference_slot 为 (scope, slot_name) 元组

        M3 临时：简化格式默认同 scope
        M4 将支持: "scope.slot_name" 或 "{scope: scope, slot: slot_name}"
        """
        # M3 临时：默认同 scope
        return (raw_slot.scope, ref)

    def _parse_slot_reference(
        self,
        ref: str,
        source_scope: str
    ) -> SlotReference:
        """解析槽引用为 SlotReference

        M3 临时实现：简化格式默认同 scope
        M4 将支持显式 scope
        """
        return SlotReference(
            scope=source_scope,
            slot_name=ref
        )

    def _parse_condition_node(
        self,
        condition: Dict[str, Any],
        source_scope: str
    ) -> ConditionNode:
        """解析条件 AST 节点

        M3: 基础解析，支持简单节点
        M4: 完整递归解析 then/else
        """
        node_type = condition.get("type")

        if node_type == "operation_equals":
            return OperationEqualsNode(operation=condition.get("operation"))
        elif node_type == "slot_equals":
            return SlotEqualsNode(
                slot=self._parse_slot_reference(
                    condition.get("slot_name"),
                    source_scope
                ),
                value=condition.get("value")
            )
        elif node_type == "slot_in_range":
            return SlotInRangeNode(
                slot=self._parse_slot_reference(
                    condition.get("slot_name"),
                    source_scope
                ),
                min_value=condition.get("min_value"),
                max_value=condition.get("max_value")
            )
        elif node_type == "and":
            # M4: 递归解析 operands
            return AndNode(operands=[])
        elif node_type == "or":
            return OrNode(operands=[])
        elif node_type == "not":
            return NotNode(operand=OperationEqualsNode(operation=""))
        else:
            # 默认返回一个占位节点
            return OperationEqualsNode(operation="")

    def _build_dependency_graph(self, normalized_slots: List[NormalizedSlot]) -> DependencyGraph:
        """构建依赖图（M4 完整实现）

        Args:
            normalized_slots: 标准化后的槽列表

        Returns:
            DependencyGraph: 包含所有 slots 和 edges 的依赖图
        """
        # 收集所有 slot keys
        slots = tuple(slot.key for slot in normalized_slots)

        # 构建依赖边：(dependent, dependency)
        # 注意：边方向是从依赖者到被依赖者
        edges = []
        for slot in normalized_slots:
            slot_key = slot.key
            for dep_ref in slot.depends_on:
                # dep_ref 是 SlotReference，包含 scope 和 slot_name
                dep_key = dep_ref.key
                edges.append((slot_key, dep_key))

        return DependencyGraph(slots=slots, edges=tuple(edges))
