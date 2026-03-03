# Phase 4: Profile Plugin 层与 Oracle 集成

**日期**: 2026-03-03
**状态**: ✅ 完成
**依赖**: Phase 3 (Oracle Layer) ✅ 完成

---

## 一、Phase 4 概述

### 1.1 目标

Phase 4 主要实现两个关键组件：

1. **Profile Plugin 层** - 数据库特化逻辑层
   - `should_skip_test()` - 测试过滤逻辑
   - `post_process_result()` - 结果标准化

2. **Oracle 集成** - 将 Oracle 检查器集成到执行流程
   - 在 ExecutionPipeline 中集成 Oracle 检查
   - 生成 Oracle 检查报告

### 1.2 架构位置

```
┌───────────────────────────────────────────────────────────────────┐
│                        Oracle 层 (已完成)                         │
│  • OracleDefinition / OracleResult                               │
│  • RangeConstraintOracle / EnumConstraintOracle                  │
│  • RelationalConstraintOracle / StatusValidationOracle          │
└───────────────────────────────────────────────────────────────────┘
                                    ↓
┌───────────────────────────────────────────────────────────────────┐
│                    Profile Plugin 层 (Phase 4)                   │
│  • BaseProfilePlugin (抽象基类)                                  │
│  • SeekDBProfilePlugin (SeekDB 实现)                             │
└───────────────────────────────────────────────────────────────────┘
                                    ↓
┌───────────────────────────────────────────────────────────────────┐
│               ExecutionPipeline (集成 Oracle 检查)               │
│  • 在执行后调用 Oracle 检查器                                    │
│  • 生成 Oracle 报告                                              │
└───────────────────────────────────────────────────────────────────┘
```

---

## 二、M0-M5 里程碑规划

### M0: 错误基础设施

**目标**: 定义 Profile Plugin 层的错误类型

**交付物**:
- `profiles/errors.py`
  - `ProfileError` 基类
  - `ProfileSkipError` (跳过测试时的错误)
  - `ProfilePostProcessError` (后处理错误)

**验收标准**:
- 所有错误类继承自 `Exception`
- 错误信息清晰，包含上下文

---

### M1: BaseProfilePlugin 接口定义

**目标**: 定义 Profile Plugin 抽象基类

**交付物**:
- `profiles/base.py`
  - `BaseProfilePlugin` 抽象基类
  - `should_skip_test()` 抽象方法
  - `post_process_result()` 抽象方法

**接口规范**:

```python
from abc import ABC, abstractmethod
from typing import Optional, Any
from core.models import TestCase

class BaseProfilePlugin(ABC):
    """数据库特化逻辑基类

    职责：
    - 提供 skip 逻辑 (过滤不支持的测试)
    - 提供结果后处理 (标准化结果格式)

    不允许：
    - 声明能力 (由 Adapter 提供)
    - 定义 Constraint (由 Contract 提供)
    """

    @abstractmethod
    def should_skip_test(self, test_case: TestCase) -> Optional[str]:
        """判断是否跳过某个测试

        Args:
            test_case: 测试用例

        Returns:
            Optional[str]: 跳过原因，None 表示不跳过

        Example:
            # SeekDB: COSINE + HNSW 暂不支持
            if (test_case.slot_values.get('metric_type') == 'COSINE' and
                test_case.slot_values.get('index_type') == 'HNSW'):
                return "COSINE + HNSW 暂不支持"
            return None
        """
        pass

    @abstractmethod
    def post_process_result(self, result: Any) -> Any:
        """结果后处理

        Args:
            result: 原始结果

        Returns:
            Any: 处理后的结果

        Example:
            # 统一结果格式
            if isinstance(result, dict):
                return SearchResult(
                    ids=result.get('ids', []),
                    scores=result.get('scores', []),
                    total=result.get('total', 0)
                )
            return result
        """
        pass
```

**验收标准**:
- 接口符合架构规范 (005-interface-specs.md)
- 包含完整的文档字符串和示例

---

### M2: SeekDB Profile Plugin 实现

**目标**: 实现 SeekDB 特定的 Profile Plugin

**交付物**:
- `profiles/seekdb.py`
  - `SeekDBProfilePlugin` 类
  - 实现特定的 skip 逻辑
  - 实现结果后处理

**SeekDB Skip 逻辑示例**:

| 场景 | 跳过原因 |
|------|----------|
| `metric_type=COSINE` 且 `index_type=HNSW` | COSINE + HNSW 暂不支持 |
| `dimension < 1` 或 `dimension > 32768` | 维度超出支持范围 |
| `ef_construction > 500` | ef_construction 过大 |

**验收标准**:
- 覆盖常见的不支持场景
- 错误信息清晰
- 通过单元测试

---

### M3: Profile Plugin 注册表

**目标**: 实现 Profile Plugin 的注册和管理

**交付物**:
- `profiles/registry.py`
  - `ProfilePluginRegistry` 类
  - `register_profile()` 函数
  - `get_profile()` 函数

**接口设计**:

```python
from typing import Dict, Optional

class ProfilePluginRegistry:
    """Profile Plugin 注册表"""

    def __init__(self):
        self._profiles: Dict[str, BaseProfilePlugin] = {}

    def register(self, name: str, profile: BaseProfilePlugin) -> None:
        """注册 Profile Plugin"""
        if name in self._profiles:
            raise ValueError(f"Profile '{name}' already registered")
        self._profiles[name] = profile

    def get(self, name: str) -> Optional[BaseProfilePlugin]:
        """获取 Profile Plugin"""
        return self._profiles.get(name)

    def list_all(self) -> list:
        """列出所有已注册的 Profile"""
        return list(self._profiles.keys())

# 全局注册表
_global_registry = ProfilePluginRegistry()

def register_profile(name: str, profile: BaseProfilePlugin) -> None:
    """注册到全局注册表"""
    _global_registry.register(name, profile)

def get_profile(name: str) -> Optional[BaseProfilePlugin]:
    """从全局注册表获取"""
    return _global_registry.get(name)
```

**验收标准**:
- 支持注册、获取、列出
- 防止重复注册
- 通过单元测试

---

### M4: Oracle 集成到 ExecutionPipeline

**目标**: 在执行流程中集成 Oracle 检查

**修改文件**:
- `core/execution_pipeline.py`

**集成点**:

```python
class ExecutionPipeline:
    def __init__(self, ..., oracles: List[OracleChecker] = None):
        self.oracles = oracles or []

    def execute_test_case(self, ...) -> TestExecutionResult:
        # ... 现有流程 ...

        # Step 3.5: Oracle 检查 (新增)
        oracle_results = []
        for oracle in self.oracles:
            if oracle.can_check(test_case):
                result = oracle.check(test_case, execution_result)
                oracle_results.append(result)

        # ... 继续现有流程 ...
```

**数据模型扩展**:

```python
@dataclass
class TestExecutionResult:
    # ... 现有字段 ...
    oracle_results: List[OracleResult] = field(default_factory=list)
```

**验收标准**:
- Oracle 检查在正确的时机执行
- 结果正确记录
- 向后兼容 (oracles=None 时正常工作)

---

### M5: Oracle 报告生成

**目标**: 生成 Oracle 检查报告

**交付物**:
- `core/oracle_reporter.py`
  - `OracleReporter` 类
  - `generate_report()` 方法
  - `aggregate_results()` 方法

**接口设计**:

```python
@dataclass
class OracleReport:
    """Oracle 检查报告"""
    total_oracles: int
    passed_count: int
    failed_count: int
    skipped_count: int
    results: List[OracleResult]
    summary: str

class OracleReporter:
    """Oracle 报告生成器"""

    def __init__(self, oracles: List[OracleChecker]):
        self.oracles = oracles

    def generate_report(self, results: List[OracleResult]) -> OracleReport:
        """生成 Oracle 报告"""
        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed)

        return OracleReport(
            total_oracles=len(results),
            passed_count=passed,
            failed_count=failed,
            skipped_count=0,  # TODO: 实现 skip 跟踪
            results=results,
            summary=self._generate_summary(results)
        )

    def _generate_summary(self, results: List[OracleResult]) -> str:
        """生成摘要"""
        passed = sum(1 for r in results if r.passed)
        total = len(results)
        return f"Oracle: {passed}/{total} passed"
```

**验收标准**:
- 报告包含所有关键信息
- 摘要简洁清晰
- 通过单元测试

---

## 三、测试规划

### 3.1 单元测试

| 文件 | 测试数量 | 覆盖内容 |
|------|----------|----------|
| `tests/test_profile_base.py` | ~5 | BaseProfilePlugin 接口 |
| `tests/test_seekdb_profile.py` | ~15 | SeekDB Profile Plugin 实现 |
| `tests/test_profile_registry.py` | ~10 | 注册表功能 |
| `tests/test_oracle_reporter.py` | ~10 | Oracle 报告生成 |

**总计**: ~40 个单元测试

### 3.2 集成测试

| 文件 | 测试场景 |
|------|----------|
| `tests/test_profile_integration.py` | Profile + ExecutionPipeline 集成 |
| `tests/test_oracle_integration.py` | Oracle + ExecutionPipeline 集成 |

**总计**: ~10 个集成测试

---

## 四、目录结构

```
SemanticBugMiningFramework/
├── profiles/                        # 新增
│   ├── __init__.py
│   ├── errors.py                    # M0
│   ├── base.py                      # M1
│   ├── seekdb.py                    # M2
│   └── registry.py                  # M3
├── core/
│   ├── execution_pipeline.py        # 修改 (M4)
│   └── oracle_reporter.py           # 新增 (M5)
└── tests/
    ├── test_profile_base.py         # 新增
    ├── test_seekdb_profile.py       # 新增
    ├── test_profile_registry.py     # 新增
    ├── test_oracle_reporter.py      # 新增
    ├── test_profile_integration.py  # 新增
    └── test_oracle_integration.py   # 新增
```

---

## 五、实现优先级

| 优先级 | 里程碑 | 原因 |
|--------|--------|------|
| P0 | M0-M2 | Profile Plugin 基础功能 |
| P0 | M4 | Oracle 集成 (核心价值) |
| P1 | M3 | 注册表 (可延后) |
| P1 | M5 | 报告生成 (可延后) |

**建议实施顺序**: M0 → M1 → M2 → M4 → M3 → M5

---

## 六、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Profile Plugin 接口设计不合理 | 中 | 参考架构规范，保持接口简单 |
| Oracle 集成破坏现有测试 | 高 | 确保向后兼容 (oracles=None) |
| 报告格式不符合需求 | 低 | 预留扩展接口，支持自定义格式 |

---

## 七、下一步

1. 实现 M0: 错误基础设施
2. 实现 M1: BaseProfilePlugin 接口
3. 实现 M2: SeekDB Profile Plugin
4. 实现 M4: Oracle 集成到 ExecutionPipeline
5. 实现 M3: Profile Plugin 注册表
6. 实现 M5: Oracle 报告生成
7. 运行所有测试，确保通过
8. 更新 README.md，标记 Phase 4 完成

---

**Phase 4 规划完成，准备进入实施阶段**
