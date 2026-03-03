"""
Contract DSL Schema 原始数据结构定义

定义 YAML 解析后的原始数据类型（TypedDict/TypedClasses）。
这是 Schema Validator 的输入和输出类型。
"""

from typing import List, Dict, Any, Optional, Union, TYPE_CHECKING, Tuple
from dataclasses import dataclass

# 导入语义层类型（用于前向引用）
if TYPE_CHECKING:
    from contract.types import (
        SlotKey,
        SlotReference,
        ConditionNode,
        NormalizedConstraints,
        NormalizedRule,
        NormalizedRuleBody,
        NormalizedRelationalRule,
        NormalizedRangeRule,
        NormalizedEnumRule,
        NormalizedConditionalRule,
        DependencyGraph,
    )


# ================================================================
# 原始数据结构类型定义
# ================================================================

class RawSlotDependency:
    """原始依赖定义（未验证）

    DSL 格式选项：
    - 简化格式: "slot_name"
    - 完整格式: {"slot_name": "xxx", "reason": "xxx"}

    Schema 验证后统一转换为完整格式。
    """
    slot_name: str
    reason: Optional[str] = None


class RawRangeConstraint:
    """原始范围约束"""
    min: Optional[Union[int, float]] = None
    max: Optional[Union[int, float]] = None
    inclusive: bool = True


class RawEnumConstraint:
    """原始枚举约束"""
    values: List[Any]


class RawVectorConstraint:
    """原始向量约束"""
    element_type: Optional[str] = None  # "float32", "float16", etc.
    dimension_slot: Optional[str] = None


class RawSlotConstraints:
    """原始槽约束"""
    range: Optional[RawRangeConstraint] = None
    enum: Optional[RawEnumConstraint] = None
    vector: Optional[RawVectorConstraint] = None


class RawRelationalRule:
    """原始关系规则"""
    operator: str  # ">=", "<=", ">", "<", "==", "!=", "in", "not_in"
    reference_slot: str
    error_message: str


class RawRangeRule:
    """原始范围规则"""
    min_value: Any
    max_value: Any
    inclusive_min: bool = True
    inclusive_max: bool = True


class RawConditionalRule:
    """原始条件规则（Phase 2 结构支持，暂不评估）"""
    condition: Dict[str, Any]
    then: List[Dict[str, Any]]
    else_clause: Optional[List[Dict[str, Any]]] = None


class RawEnumRule:
    """原始枚举规则"""
    allowed_values: List[Any]
    strict: bool = True


class RawRule:
    """原始规则定义

    DSL 格式：
    ```yaml
    rule_id: string
    type: "relational" | "range" | "conditional" | "enum" | "type"
    severity: "HIGH" | "MEDIUM" | "LOW"
    enabled: boolean
    priority: integer  # 默认 100
    relational?: RawRelationalRule
    range?: RawRangeRule
    conditional?: RawConditionalRule
    enum?: RawEnumRule
    ```
    """
    rule_id: str
    type: str
    severity: str
    enabled: bool
    priority: int = 100

    # 规则特定内容（根据 type，只有一个是必需的）
    relational: Optional[RawRelationalRule] = None
    range: Optional[RawRangeRule] = None
    conditional: Optional[RawConditionalRule] = None
    enum: Optional[RawEnumRule] = None


class RawSlot:
    """原始槽定义（未验证）

    DSL 格式：
    ```yaml
    slot_name: string
    description: string
    type: "integer" | "float" | "string" | "enum" | "boolean" | "vector"
    scope: "DATABASE" | "COLLECTION" | "PARTITION" | "INDEX" | "REPLICA"
    depends_on: List<RawSlotDependency>
    constraints?: RawSlotConstraints
    rules?: List<RawRule>
    ```
    """
    slot_name: str
    description: str
    type: str
    scope: str
    depends_on: List[Union[str, Dict[str, Any]]]  # Schema 验证后统一
    constraints: Optional[RawSlotConstraints] = None
    rules: Optional[List[Dict[str, Any]]] = None


class RawContract:
    """原始 Contract 定义（未验证）

    DSL 格式：
    ```yaml
    database_name: string (可选)
    version: string (可选)
    core_slots: List<RawSlot>
    ```
    """
    database_name: Optional[str] = None
    version: Optional[str] = None
    core_slots: List[Dict[str, Any]]


# ================================================================
# 验证后的数据结构（Schema 验证输出）
# ================================================================

@dataclass(frozen=True)
class ValidatedRawSlotDependency:
    """验证后的依赖定义"""
    slot_name: str
    reason: Optional[str]


@dataclass(frozen=True)
class ValidatedRawSlot:
    """验证后的槽定义

    Schema 验证确保：
    - slot_name 是非空字符串
    - type 是合法的 SlotType 枚举值
    - scope 是合法的 SlotScope 枚举值
    - depends_on 是列表（元素已转换为统一格式）
    """
    slot_name: str
    description: str
    type: str
    scope: str
    depends_on: List[ValidatedRawSlotDependency]
    constraints: Optional[RawSlotConstraints] = None
    rules: Optional[List[Dict[str, Any]]] = None


@dataclass(frozen=True)
class ValidatedRawContract:
    """验证后的 Contract 定义

    Schema 验证确保：
    - core_slots 存在且是列表
    - 每个 slot 的基本类型正确
    - 不检查：重复 slot、引用存在性、依赖循环（这些是语义验证）

    Attributes:
        database_name: 数据库名称（可选）
        version: 版本字符串（可选）
        core_slots: 验证后的槽列表
    """
    database_name: Optional[str]
    version: Optional[str]
    core_slots: List[ValidatedRawSlot]


# ================================================================
# 语义验证后的数据结构（Semantic Validator 输出）
# ================================================================

# 导入语义层类型
from contract.types import (
    SlotKey,
    SlotReference,
    ConditionNode,
    NormalizedConstraints,
    NormalizedRule,
    NormalizedRuleBody,
    NormalizedRelationalRule,
    NormalizedRangeRule,
    NormalizedEnumRule,
    NormalizedConditionalRule,
)


@dataclass(frozen=True)
class NormalizedSlot:
    """标准化后的槽定义

    与 ValidatedRawSlot 的区别：
    - depends_on: List[SlotReference]（已解析）
    - constraints: NormalizedConstraints（类型安全）
    - rules: List[NormalizedRule]（类型安全 Union）

    这是纯标准化，不改变业务含义。
    """
    slot_name: str
    description: str
    type: str
    scope: str
    depends_on: List[SlotReference]
    constraints: Optional[NormalizedConstraints]
    rules: List[NormalizedRule]

    @property
    def key(self) -> SlotKey:
        """获取 SlotKey"""
        return SlotKey(scope=self.scope, slot_name=self.slot_name)


# DependencyGraph 占位符（M4 实现）
@dataclass(frozen=True)
class DependencyGraph:
    """依赖图（M4 实现完整功能）

    M4: 依赖关系、拓扑排序、循环检测

    图表示：
    - slots: 图中所有节点的 SlotKey
    - edges: 有向边，(dependent, dependency) 表示 dependent → dependency
      例如：top_k → dimension 表示 "top_k 依赖于 dimension"

    Attributes:
        slots: 所有槽的 SlotKey 元组
        edges: 依赖边元组，每个元素是 (dependent, dependency)
    """
    slots: Tuple[SlotKey, ...] = ()  # 所有槽的 SlotKey 列表
    edges: Tuple[Tuple[SlotKey, SlotKey], ...] = ()  # (dependent, dependency) 依赖边

    def is_empty(self) -> bool:
        """检查依赖图是否为空"""
        return len(self.slots) == 0

    def get_dependencies(self, slot: SlotKey) -> Tuple[SlotKey, ...]:
        """获取指定 slot 的所有直接依赖

        Args:
            slot: 要查询的 SlotKey

        Returns:
            该 slot 依赖的所有 SlotKey 元组
        """
        deps = []
        for edge in self.edges:
            # Edge 可以是 (dependent, dependency) 元组或单个 SlotKey
            if isinstance(edge, tuple) and len(edge) == 2:
                dependent, dependency = edge
                if dependent == slot:
                    deps.append(dependency)
            elif isinstance(edge, SlotKey):
                # 自环情况：edge 是单个 SlotKey
                if edge == slot:
                    deps.append(slot)
        return tuple(deps)

    def get_dependents(self, slot: SlotKey) -> Tuple[SlotKey, ...]:
        """获取依赖于指定 slot 的所有 slot

        Args:
            slot: 要查询的 SlotKey

        Returns:
            依赖于该 slot 的所有 SlotKey 元组
        """
        dependents = []
        for edge in self.edges:
            if isinstance(edge, tuple) and len(edge) == 2:
                dependent, dependency = edge
                if dependency == slot:
                    dependents.append(dependent)
            elif isinstance(edge, SlotKey):
                # 自环情况
                if edge == slot:
                    dependents.append(slot)
        return tuple(dependents)

    def topological_sort(self) -> List[SlotKey]:
        """拓扑排序（Kahn 算法）

        Returns:
            按依赖顺序排列的 SlotKey 列表
            依赖少的在前，依赖多的在后

        Raises:
            ValueError: 如果图中存在循环
        """
        # 构建入度表
        in_degree = {slot: 0 for slot in self.slots}
        for dependent, dependency in self.edges:
            if dependency in in_degree:
                in_degree[dependent] += 1

        # 找出所有入度为 0 的节点
        queue = [slot for slot in self.slots if in_degree[slot] == 0]
        result = []

        while queue:
            # 取出一个入度为 0 的节点
            current = queue.pop(0)
            result.append(current)

            # 减少所有依赖于当前节点的入度
            for dependent in self.get_dependents(current):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        # 如果结果数量不等于节点数量，说明存在循环
        if len(result) != len(self.slots):
            # 找出未访问的节点（这些节点在循环中）
            unvisited = set(self.slots) - set(result)
            raise ValueError(f"Graph contains cycle involving: {unvisited}")

        return result

    def detect_cycle(self) -> Optional['DependencyCycle']:
        """检测依赖循环（DFS 着色算法）

        Returns:
            如果检测到循环，返回 DependencyCycle 对象；否则返回 None

        使用三种颜色标记节点状态：
        - WHITE: 未访问
        - GRAY: 正在访问（在当前 DFS 路径上）
        - BLACK: 已完成访问
        """
        from contract.errors import DependencyCycle

        # 状态：WHITE=未访问, GRAY=访问中, BLACK=已完成
        WHITE, GRAY, BLACK = 0, 1, 2
        state = {slot: WHITE for slot in self.slots}
        parent = {}  # 用于重建路径

        def dfs(node: SlotKey, path: List[SlotKey]) -> Optional[List[SlotKey]]:
            """DFS 搜索循环

            Returns:
                如果发现循环，返回循环路径；否则返回 None
            """
            state[node] = GRAY
            path.append(node)

            # 访问所有依赖
            for dependency in self.get_dependencies(node):
                if state[dependency] == GRAY:
                    # 发现循环：从 dependency 到 node 形成闭环
                    cycle_start = path.index(dependency)
                    cycle_path = path[cycle_start:] + [dependency]
                    return cycle_path
                elif state[dependency] == WHITE:
                    result = dfs(dependency, path)
                    if result:
                        return result

            # 标记为已完成
            state[node] = BLACK
            path.pop()
            return None

        # 对所有未访问的节点执行 DFS
        for slot in self.slots:
            if state[slot] == WHITE:
                cycle_path = dfs(slot, [])
                if cycle_path:
                    # 转换 SlotKey 为 (scope, slot_name) 元组
                    cycle_tuples = [(sk.scope, sk.slot_name) for sk in cycle_path]
                    return DependencyCycle(cycle_path=cycle_tuples)

        return None

    def validate_no_cycles(self) -> None:
        """验证无循环依赖

        Raises:
            DependencyCycleError: 如果检测到循环依赖
        """
        from contract.errors import DependencyCycleError, DependencyCycle

        cycle = self.detect_cycle()
        if cycle:
            raise DependencyCycleError(cycle)


@dataclass(frozen=True)
class SemanticallyValidContract:
    """语义验证并分析后的 Contract

    Schema 验证确保结构正确，语义验证确保：
    - 无重复 slot
    - 所有引用存在
    - 无依赖循环
    - 无规则优先级冲突
    - 所有类型已标准化

    Attributes:
        database_name: 数据库名称
        version: 版本字符串
        core_slots: 标准化后的槽列表
        dependency_graph: 依赖图（必须存在，非 Optional）
    """
    database_name: Optional[str]
    version: Optional[str]
    core_slots: List[NormalizedSlot]
    dependency_graph: DependencyGraph


# ================================================================
# Contract: 最终的可执行 Contract 对象
# ================================================================

@dataclass(frozen=True)
class Contract:
    """Contract DSL 最终的可执行对象

    M6: Contract Builder 的输出

    这是语义验证和构建后的最终 Contract 对象，包含：
    - 所有验证通过的数据
    - 业务逻辑查询方法
    - 不可变数据结构（frozen）

    Attributes:
        database_name: 数据库名称
        version: 版本字符串
        core_slots: 标准化后的槽列表
        dependency_graph: 依赖图
    """
    database_name: Optional[str]
    version: Optional[str]
    core_slots: Tuple[NormalizedSlot, ...]
    dependency_graph: DependencyGraph

    # ================================================================
    # 业务逻辑查询方法
    # ================================================================

    def get_slot(self, scope: str, slot_name: str) -> Optional[NormalizedSlot]:
        """获取指定 slot

        Args:
            scope: slot 的 scope（DATABASE, COLLECTION 等）
            slot_name: slot 的名称

        Returns:
            NormalizedSlot 如果找到；否则返回 None
        """
        key = SlotKey(scope=scope, slot_name=slot_name)
        for slot in self.core_slots:
            if slot.key == key:
                return slot
        return None

    def get_slot_by_key(self, key: SlotKey) -> Optional[NormalizedSlot]:
        """通过 SlotKey 获取 slot

        Args:
            key: SlotKey 对象

        Returns:
            NormalizedSlot 如果找到；否则返回 None
        """
        for slot in self.core_slots:
            if slot.key == key:
                return slot
        return None

    def get_dependencies(self, scope: str, slot_name: str) -> Tuple[SlotReference, ...]:
        """获取指定 slot 的依赖

        Args:
            scope: slot 的 scope
            slot_name: slot 的名称

        Returns:
            依赖的 SlotReference 元组，如果没有依赖则返回空元组
        """
        slot = self.get_slot(scope, slot_name)
        if slot:
            return tuple(slot.depends_on)
        return ()

    def get_rules(self, scope: str, slot_name: str) -> Tuple[NormalizedRule, ...]:
        """获取指定 slot 的规则

        Args:
            scope: slot 的 scope
            slot_name: slot 的名称

        Returns:
            规则的 NormalizedRule 元组，如果没有规则则返回空元组
        """
        slot = self.get_slot(scope, slot_name)
        if slot:
            return tuple(slot.rules)
        return ()

    def get_enabled_rules(self, scope: str, slot_name: str) -> Tuple[NormalizedRule, ...]:
        """获取指定 slot 的启用规则

        Args:
            scope: slot 的 scope
            slot_name: slot 的名称

        Returns:
            启用的规则元组
        """
        slot = self.get_slot(scope, slot_name)
        if slot:
            return tuple(r for r in slot.rules if r.enabled)
        return ()

    def get_topological_order(self) -> List[SlotKey]:
        """获取 slot 的拓扑排序顺序

        Returns:
            按依赖顺序排列的 SlotKey 列表
            依赖少的在前，依赖多的在后
        """
        return self.dependency_graph.topological_sort()

    def get_slots_by_scope(self, scope: str) -> Tuple[NormalizedSlot, ...]:
        """获取指定 scope 的所有 slot

        Args:
            scope: scope 名称（DATABASE, COLLECTION 等）

        Returns:
            该 scope 下的所有 NormalizedSlot 元组
        """
        return tuple(slot for slot in self.core_slots if slot.scope == scope)

    def has_dependency(self, scope: str, slot_name: str, dep_scope: str, dep_slot_name: str) -> bool:
        """检查是否存在指定的依赖关系

        Args:
            scope: 依赖者的 scope
            slot_name: 依赖者的 slot 名称
            dep_scope: 被依赖者的 scope
            dep_slot_name: 被依赖者的 slot 名称

        Returns:
            如果存在依赖关系则返回 True
        """
        dependencies = self.get_dependencies(scope, slot_name)
        dep_key = SlotKey(scope=dep_scope, slot_name=dep_slot_name)
        return any(dep.key == dep_key for dep in dependencies)
