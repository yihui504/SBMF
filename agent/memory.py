"""
Agent Memory System

Provides short-term and long-term memory capabilities for agents
to store and retrieve historical information.
"""
import json
import time
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


class MemoryType(Enum):
    """Memory types"""
    SHORT_TERM = "short_term"    # Session-based, volatile
    LONG_TERM = "long_term"      # Persistent, across sessions
    WORKING = "working"           # Current task context


@dataclass
class MemoryItem:
    """A single memory item"""
    key: str
    value: Any
    timestamp: float
    memory_type: MemoryType
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['memory_type'] = self.memory_type.value
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'MemoryItem':
        """Create from dictionary"""
        data['memory_type'] = MemoryType(data['memory_type'])
        return cls(**data)


class AgentMemory:
    """
    Agent Memory System

    Provides hierarchical memory storage:
    - Short-term: Volatile, session-based
    - Long-term: Persistent, file-based
    - Working: Current task context
    """

    def __init__(self, agent_id: str, storage_dir: Optional[Path] = None):
        """
        Initialize agent memory

        Args:
            agent_id: Unique identifier for the agent
            storage_dir: Directory for persistent storage
        """
        self.agent_id = agent_id
        self.storage_dir = storage_dir or Path("agent_memory") / agent_id
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # In-memory storage
        self._short_term: Dict[str, MemoryItem] = {}
        self._working: Dict[str, MemoryItem] = {}

        # Load long-term memory
        self._long_term: Dict[str, MemoryItem] = {}
        self._load_long_term_memory()

    def store(self, key: str, value: Any, memory_type: MemoryType,
              metadata: Optional[Dict] = None) -> None:
        """
        Store a value in memory

        Args:
            key: Unique identifier
            value: Value to store
            memory_type: Type of memory
            metadata: Optional metadata
        """
        item = MemoryItem(
            key=key,
            value=value,
            timestamp=time.time(),
            memory_type=memory_type,
            metadata=metadata or {}
        )

        if memory_type == MemoryType.SHORT_TERM:
            self._short_term[key] = item
        elif memory_type == MemoryType.LONG_TERM:
            self._long_term[key] = item
            self._save_long_term_memory()
        elif memory_type == MemoryType.WORKING:
            self._working[key] = item

    def retrieve(self, key: str, memory_type: Optional[MemoryType] = None) -> Optional[Any]:
        """
        Retrieve a value from memory

        Args:
            key: Identifier to retrieve
            memory_type: Specific memory type, or search all

        Returns:
            Stored value or None
        """
        if memory_type:
            storage = self._get_storage(memory_type)
            return storage.get(key)

        # Search all memory types
        for storage in [self._working, self._short_term, self._long_term]:
            if key in storage:
                return storage[key].value
        return None

    def search(self, query: Dict[str, Any],
               memory_types: Optional[List[MemoryType]] = None) -> List[MemoryItem]:
        """
        Search memory by metadata or value criteria

        Args:
            query: Search criteria
            memory_types: Memory types to search

        Returns:
            List of matching memory items
        """
        results = []
        storages = []

        if memory_types:
            storages = [self._get_storage(mt) for mt in memory_types]
        else:
            storages = [self._working, self._short_term, self._long_term]

        for storage in storages:
            for item in storage.values():
                if self._matches_query(item, query):
                    results.append(item)

        return sorted(results, key=lambda x: x.timestamp, reverse=True)

    def clear_working_memory(self) -> None:
        """Clear working memory"""
        self._working.clear()

    def clear_short_term_memory(self) -> None:
        """Clear short-term memory"""
        self._short_term.clear()

    def get_recent(self, count: int = 10,
                   memory_types: Optional[List[MemoryType]] = None) -> List[MemoryItem]:
        """
        Get most recent memory items

        Args:
            count: Number of items to return
            memory_types: Memory types to include

        Returns:
            List of recent memory items
        """
        storages = memory_types or [MemoryType.SHORT_TERM, MemoryType.WORKING]
        items = []

        for mt in storages:
            storage = self._get_storage(mt)
            items.extend(storage.values())

        return sorted(items, key=lambda x: x.timestamp, reverse=True)[:count]

    def get_stats(self) -> Dict[str, int]:
        """Get memory statistics"""
        return {
            "short_term_count": len(self._short_term),
            "long_term_count": len(self._long_term),
            "working_count": len(self._working),
        }

    def _get_storage(self, memory_type: MemoryType) -> Dict:
        """Get storage for memory type"""
        if memory_type == MemoryType.SHORT_TERM:
            return self._short_term
        elif memory_type == MemoryType.LONG_TERM:
            return self._long_term
        elif memory_type == MemoryType.WORKING:
            return self._working
        raise ValueError(f"Unknown memory type: {memory_type}")

    def _matches_query(self, item: MemoryItem, query: Dict) -> bool:
        """Check if memory item matches query"""
        for key, value in query.items():
            if key == "timestamp_range":
                if not (value[0] <= item.timestamp <= value[1]):
                    return False
            elif key in (item.metadata or {}):
                if item.metadata[key] != value:
                    return False
            elif isinstance(value, dict) and key == "metadata":
                # Check nested metadata dict
                for meta_key, meta_value in value.items():
                    if (item.metadata is None or
                        meta_key not in item.metadata or
                        item.metadata[meta_key] != meta_value):
                        return False
            else:
                return False
        return True

    def _load_long_term_memory(self) -> None:
        """Load long-term memory from disk"""
        memory_file = self.storage_dir / "long_term.json"
        if not memory_file.exists():
            return

        try:
            with open(memory_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item_data in data:
                    item = MemoryItem.from_dict(item_data)
                    self._long_term[item.key] = item
        except Exception as e:
            print(f"[WARNING] Failed to load long-term memory: {e}")

    def _save_long_term_memory(self) -> None:
        """Save long-term memory to disk"""
        memory_file = self.storage_dir / "long_term.json"
        try:
            data = [item.to_dict() for item in self._long_term.values()]
            with open(memory_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[WARNING] Failed to save long-term memory: {e}")


__all__ = [
    "MemoryType",
    "MemoryItem",
    "AgentMemory",
]
