# state/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from core.models import SlotScope


class StateModel(ABC):
    """状态机抽象基类

    职责：
    - 定义有效状态和转移
    - 检查转移合法性
    """

    @abstractmethod
    def get_valid_states(self, scope: SlotScope) -> List[str]:
        """返回指定粒度的所有有效状态

        Args:
            scope: 状态粒度

        Returns:
            List[str]: 有效状态列表
        """
        pass

    @abstractmethod
    def get_valid_transitions(self, scope: SlotScope) -> Dict[str, List[str]]:
        """返回指定粒度的有效状态转移

        Args:
            scope: 状态粒度

        Returns:
            Dict[str, List[str]]: {from_state: [to_states]}
        """
        pass

    @abstractmethod
    def get_current_state(self,
                         scope: SlotScope,
                         name: str,
                         adapter: Optional['BaseAdapter']) -> str:
        """获取指定粒度的当前状态

        Args:
            scope: 状态粒度
            name: 资源名称
            adapter: 数据库适配器

        Returns:
            str: 当前状态
        """
        pass

    @abstractmethod
    def is_transition_legal(self,
                           scope: SlotScope,
                           from_state: str,
                           to_state: str) -> bool:
        """判断状态转移是否合法

        Args:
            scope: 状态粒度
            from_state: 起始状态
            to_state: 目标状态

        Returns:
            bool: 是否合法
        """
        pass
