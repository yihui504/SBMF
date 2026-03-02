# state/scoped.py
from typing import List, Dict, Optional
from dataclasses import dataclass
from state.base import StateModel
from core.models import SlotScope


@dataclass
class StateIdentifier:
    """状态标识符"""
    scope: SlotScope
    name: str

    def __hash__(self):
        return hash((self.scope.value, self.name))

    def __eq__(self, other):
        if not isinstance(other, StateIdentifier):
            return False
        return self.scope == other.scope and self.name == other.name


class ScopedStateModel(StateModel):
    """多粒度状态机模型（单粒度实现）

    Phase 1 实现：
    - 仅实现 COLLECTION 粒度的状态机
    - 其他粒度（DATABASE, PARTITION, INDEX, REPLICA）将在后续阶段实现
    """

    # ================================================================
    # COLLECTION 级别的状态定义
    # ================================================================

    COLLECTION_STATES = [
        "not_exist",   # 集合不存在
        "creating",    # 创建中
        "empty",       # 空集合
        "has_data",    # 有数据
        "loading",     # 加载中
        "indexing",    # 索引中
        "deleting",    # 删除中
        "error"        # 错误状态
    ]

    COLLECTION_TRANSITIONS = {
        "not_exist": ["creating", "error"],
        "creating": ["empty", "error"],
        "empty": ["has_data", "loading", "deleting", "error"],
        "has_data": ["empty", "loading", "indexing", "deleting", "error"],
        "loading": ["has_data", "error"],
        "indexing": ["has_data", "error"],
        "deleting": ["not_exist", "error"],
        "error": ["not_exist", "empty", "has_data"]
    }

    def get_valid_states(self, scope: SlotScope) -> List[str]:
        """返回指定粒度的所有有效状态"""
        if scope == SlotScope.COLLECTION:
            return self.COLLECTION_STATES
        # Phase 1: 其他粒度暂不支持
        return []

    def get_valid_transitions(self, scope: SlotScope) -> Dict[str, List[str]]:
        """返回指定粒度的有效状态转移"""
        if scope == SlotScope.COLLECTION:
            return self.COLLECTION_TRANSITIONS
        # Phase 1: 其他粒度暂不支持
        return {}

    def get_current_state(self,
                         scope: SlotScope,
                         name: str,
                         adapter: Optional['BaseAdapter']) -> str:
        """获取指定粒度的当前状态

        Phase 1: 简化实现，返回默认状态
        Phase 2: 将查询数据库获取实际状态
        """
        # Phase 1: 简化实现
        if scope == SlotScope.COLLECTION:
            return "not_exist"
        return "unknown"

    def is_transition_legal(self,
                           scope: SlotScope,
                           from_state: str,
                           to_state: str) -> bool:
        """判断状态转移是否合法"""
        transitions = self.get_valid_transitions(scope)
        return to_state in transitions.get(from_state, [])
