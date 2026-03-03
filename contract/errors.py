"""
Contract DSL 异常层次结构

定义 Contract 加载、验证、构建过程中所有异常类型。
遵循分层原则：语法错误快速失败，语义错误聚合报告。
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple


# ================================================================
# 基础异常
# ================================================================

class ContractError(Exception):
    """所有 Contract 相关错误的基类"""
    pass


# ================================================================
# 语法/结构错误（快速失败）
# ================================================================

class ContractParseError(ContractError):
    """语法/结构错误 - 快速失败

    在 YAML 解析或结构验证阶段抛出，表示文档无法可靠解析。

    Attributes:
        message: 错误消息
        location: 错误位置（可选）
    """

    def __init__(self, message: str, location: Optional["ValidationLocation"] = None):
        self.message = message
        self.location = location
        super().__init__(self._format())

    def _format(self) -> str:
        if self.location:
            return f"{self.location.format()}: {self.message}"
        return self.message


# ================================================================
# 位置信息
# ================================================================

@dataclass
class ValidationLocation:
    """结构化的验证位置

    用于精确定位错误发生的位置，支持 scope/slot/rule/field 多级定位。

    Attributes:
        scope: Slot 作用域（如 "COLLECTION"）
        slot_name: Slot 名称
        rule_id: Rule ID
        field_path: 字段路径（如 "rules[0].relational.operator"）
    """
    scope: Optional[str] = None
    slot_name: Optional[str] = None
    rule_id: Optional[str] = None
    field_path: Optional[str] = None

    def format(self) -> str:
        """格式化为可读字符串

        格式: scope:COLLECTION.slot:dimension.rule:check_dim.rules[0].relational.operator
        使用 '.' 作为分隔符，field_path 中若含 '.' 也能正确解析。
        """
        parts = []
        if self.scope:
            parts.append(f"scope:{self.scope}")
        if self.slot_name:
            parts.append(f"slot:{self.slot_name}")
        if self.rule_id:
            parts.append(f"rule:{self.rule_id}")
        if self.field_path:
            parts.append(self.field_path)
        return ".".join(parts) if parts else "<unknown>"


# ================================================================
# 语义验证错误（聚合报告）
# ================================================================

@dataclass
class ValidationIssue:
    """单个语义验证问题

    Attributes:
        error_code: 错误代码（如 "DUPLICATE_SLOT", "DEPENDENCY_CYCLE"）
        message: 错误消息
        location: 错误位置
        severity: 严重程度（"ERROR" 或 "WARNING"）
    """
    error_code: str
    message: str
    location: ValidationLocation
    severity: str = "ERROR"

    def format(self) -> str:
        """格式化为可读字符串

        格式: [ERROR_CODE] scope:COLLECTION.slot:dimension: Error message
        """
        return f"[{self.error_code}] {self.location.format()}: {self.message}"

    def to_dict(self) -> dict:
        """转换为机器可读的字典格式

        用于 JSON 报告、日志系统、CLI 结构化输出等场景。

        Returns:
            dict: 包含 error_code, message, location, severity 的结构化字典
        """
        return {
            "error_code": self.error_code,
            "message": self.message,
            "location": {
                "scope": self.location.scope,
                "slot_name": self.location.slot_name,
                "rule_id": self.location.rule_id,
                "field_path": self.location.field_path,
            },
            "severity": self.severity,
        }


class ContractValidationError(ContractError):
    """语义验证错误 - 聚合多个问题

    在语义验证阶段抛出，包含所有检测到的问题列表。

    Attributes:
        issues: 验证问题元组（不可变，确保异常对象安全性）
    """

    def __init__(self, issues: List[ValidationIssue]):
        # 转换为元组，确保不可变性
        self.issues: Tuple[ValidationIssue, ...] = tuple(issues)
        super().__init__(self._format())

    def _format(self) -> str:
        lines = [f"Contract validation failed with {len(self.issues)} issue(s):"]
        for issue in self.issues:
            lines.append(f"  {issue.format()}")
        return "\n".join(lines)

    def get_errors(self) -> List[ValidationIssue]:
        """获取所有 ERROR 级别的问题"""
        return [i for i in self.issues if i.severity == "ERROR"]

    def get_warnings(self) -> List[ValidationIssue]:
        """获取所有 WARNING 级别的问题"""
        return [i for i in self.issues if i.severity == "WARNING"]


# ================================================================
# 特殊语义错误
# ================================================================

@dataclass
class DependencyCycle:
    """依赖循环

    表示 slot 之间的依赖关系形成了闭环。

    Attributes:
        cycle_path: 循环路径，每个元素是 (scope, slot_name) 元组
    """
    cycle_path: List[Tuple[str, str]]

    def format(self) -> str:
        """格式化为可读字符串

        输出格式: COLLECTION.a → COLLECTION.b → COLLECTION.a
        包含 scope 前缀以消除歧义，最后重复起点表示闭环。
        """
        readable = " → ".join(f"{scope}.{name}" for scope, name in self.cycle_path)
        # 添加闭环（回到起点）
        if self.cycle_path:
            readable += f" → {self.cycle_path[0][0]}.{self.cycle_path[0][1]}"
        return readable

    def to_validation_issue(self) -> ValidationIssue:
        """转换为 ValidationIssue

        循环涉及多个位置，不指定单一 location。
        """
        return ValidationIssue(
            error_code="DEPENDENCY_CYCLE",
            message=f"Detected dependency cycle: {self.format()}",
            location=ValidationLocation(),  # 空位置，因为循环跨越多个 slot
            severity="ERROR"
        )


class DependencyCycleError(ContractValidationError):
    """依赖循环错误

    特殊的语义验证错误，专门用于报告依赖循环。
    """

    def __init__(self, cycle: DependencyCycle):
        self.cycle = cycle
        super().__init__([cycle.to_validation_issue()])


class PriorityConflictError(ContractValidationError):
    """规则优先级冲突错误

    同一 slot 下存在多个相同 priority 的规则。

    Attributes:
        slot_name: 冲突发生的 slot 名称
        conflicts: 冲突列表，每个元素是 (priority, [rule_ids]) 元组
    """

    def __init__(self, slot_name: str, conflicts: List[Tuple[int, List[str]]]):
        self.slot_name = slot_name
        self.conflicts = conflicts

        issues = []
        for priority, rule_ids in conflicts:
            issues.append(ValidationIssue(
                error_code="PRIORITY_CONFLICT",
                message=f"Rules {rule_ids} in slot '{slot_name}' have same priority {priority}",
                location=ValidationLocation(slot_name=slot_name),
                severity="ERROR"
            ))
        super().__init__(issues)


# ================================================================
# 其他特殊错误（预留扩展）
# ================================================================

class AmbiguousDependencyRefError(ContractValidationError):
    """依赖引用歧义错误

    当 depends_on 引用在目标 scope 中存在多个同名 slot 时抛出。
    Phase 2 中不应发生（slot_name 在同 scope 下唯一），
    但预留此错误类型以支持未来扩展。
    """
    pass


class UndefinedDependencyRefError(ContractValidationError):
    """依赖引用未定义错误

    当 depends_on 引用的 slot 不存在时抛出。
    """

    def __init__(self, ref_name: str, ref_scope: str, source_slot: str):
        self.ref_name = ref_name
        self.ref_scope = ref_scope
        self.source_slot = source_slot

        issues = [ValidationIssue(
            error_code="UNDEFINED_DEPENDENCY_REF",
            message=f"Slot '{source_slot}' depends on undefined slot '{ref_name}' in scope {ref_scope}",
            location=ValidationLocation(slot_name=source_slot),
            severity="ERROR"
        )]
        super().__init__(issues)
