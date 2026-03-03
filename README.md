# SBMF - Semantic Bug Mining Framework

**语义驱动的数据库Bug挖掘框架**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-v1.2b-orange)](https://github.com/yihui504/SBMF)

---

## 项目概述

SBMF是一个基于语义分析的自动化数据库Bug挖掘框架，通过Contract DSL定义数据库语义约束，结合Agent驱动测试生成、Fuzzing、异常检测等技术，系统化地发现数据库产品中的潜在缺陷。

### 核心目标

- **主目标**: 数据库语义验证框架
- **支撑目标**: 自动化Fuzz平台
- **应用场景**: 向量数据库（SeekDB、Milvus、Weaviate）等

### 项目特色

- **语义驱动**: 使用Contract DSL定义数据库语义约束
- **三值逻辑**: TRUE/FALSE/UNKNOWN处理边界情况
- **Agent驱动**: 智能测试用例生成和执行
- **多维检测**: Fuzzing + 异常检测 + 并发测试 + Bug分类
- **实战验证**: 在真实SeekDB上发现6个产品级Bug

---

## 核心特性

### 1. Contract DSL系统

```yaml
# 定义数据库语义约束
database_name: seekdb
version: "1.0"

core_slots:
  - slot_name: dimension
    type: integer
    scope: COLLECTION
    constraints:
      range: {min: 1, max: 65536}

  - slot_name: top_k
    type: integer
    scope: COLLECTION
    depends_on: [dimension]
    rules:
      - type: relational
        operator: "<="
        reference_slot: dimension
```

### 2. 三值逻辑系统

| 值 | 含义 | 应用场景 |
|----|------|----------|
| TRUE | 约束满足 | 正常执行 |
| FALSE | 约束违反 | 拒绝执行 |
| UNKNOWN | 未知状态 | 运行时验证 |

### 3. Agent驱动测试

- **Runtime**: Agent运行时环境
- **Memory**: 短期/长期/工作记忆管理
- **Monitor**: 性能监控和异常检测
- **Tools**: 可扩展的工具系统

### 4. 智能Fuzzing

- 6种变异策略（RANDOM/BOUNDARY/ARITHMETIC/DICTIONARY/SPLICING/CROSSOVER）
- 反馈驱动的智能变异
- 覆盖率导向的测试生成

### 5. 异常检测

- Z-score方法
- IQR（四分位距）方法
- 自适应阈值管理

---

## 理论基础

### 语义槽（Semantic Slot）

语义槽是对数据库参数的语义抽象，包含：

- **类型约束**: integer/float/boolean/string/vector/enum
- **范围约束**: min/max值
- **依赖关系**: 参数间的依赖
- **验证规则**: 业务逻辑约束

### Bug类型推导

基于三值逻辑的Bug类型决策树：

```
执行成功 → 无Bug
   ↓
执行失败
   ↓
Precondition Gate检查
   ↓
   ├─ FALSE → USER_ERROR (用户错误)
   ├─ TRUE  → PRODUCT_SUSPECT (产品疑似)
   └─ UNKNOWN → INFRA_SUSPECT (基础设施疑似)
```

### Oracle验证

使用AST（抽象语法树）实现可编程Oracle：

```python
@oracle("dimension_range_check")
def check_dimension(result):
    return ast.BinOp(
        ast.Load("result.dimension"),
        ast.GtE(),  # >=
        ast.Constant(1)
    )
```

---

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                      Contract DSL Layer                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  Parser  │→│ Validator│→│  Builder │→│  Graph   │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                       Core Engine Layer                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Rule Engine  │  │Precondition  │  │ Bug Type     │      │
│  │ (3-valued)   │  │   Gate       │  │   Engine     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │ State Model  │  │    Oracle    │                        │
│  │ (Multi-scope)│  │   (AST)      │                        │
│  └──────────────┘  └──────────────┘                        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Agent & Testing Layer                     │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │
│  │ Runtime │  │ Memory  │  │ Monitor │  │  Tools  │       │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘       │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │
│  │Fuzzing  │  │Detector │  │Generator│  │Classifier│       │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      Adapter Layer                           │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                     │
│  │ SeekDB  │  │ Milvus  │  │Weaviate │  ...                 │
│  └─────────┘  └─────────┘  └─────────┘                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 开发进度

### Phase 1: 核心基础 ✅

- [x] Contract层数据模型
- [x] 三值逻辑系统
- [x] Bug类型推导引擎
- [x] Adapter接口定义
- [x] SeekDB Adapter实现
- [x] RuleEngine基础评估
- [x] Precondition Gate
- [x] StateModel单粒度
- [x] 执行流程

**测试**: 42个测试通过

### Phase 2: Contract DSL Runtime ✅

- [x] M0: 错误基础设施
- [x] M1: YAML Parser层
- [x] M2: Schema结构验证层
- [x] M3: 语义验证层 - 重复检测
- [x] M4: 语义验证层 - 依赖分析 + 循环检测
- [x] M5: 语义验证层 - 优先级冲突
- [x] M6: Contract构建器
- [x] M7: 端到端集成

**测试**: 157个测试通过

### Phase 3: 依赖图与状态模型 ✅

- [x] 依赖图构建
- [x] 拓扑排序
- [x] 多粒度状态模型
- [x] 状态转换追踪

**测试**: 67个测试通过

### Phase 4: Profile Plugin与Oracle集成 ✅

- [x] M0: Profile错误基础设施
- [x] M1: BaseProfilePlugin接口
- [x] M2: SeekDB Profile Plugin
- [x] M3: Plugin注册表
- [x] M4: Oracle集成
- [x] M5: 报告生成器

**测试**: 137个测试通过

### Phase 5: Agent驱动测试增强 ✅

- [x] M1: Agent基础设施（Runtime/Memory/Monitor）
- [x] M2: 智能测试生成器
  - 边界值生成
  - 组合测试生成
  - 随机生成
- [x] M3: 反馈驱动Fuzzing
  - 6种变异策略
  - 智能反馈机制
- [x] M4: 异常检测系统
  - Z-score方法
  - IQR方法
  - 自适应阈值
- [x] M5: 多数据库适配器
  - Milvus适配器
  - Weaviate适配器
  - 连接池管理
- [x] M6: Bug分类系统
  - 特征提取
  - 相似度计算
  - 修复建议生成
- [x] M7: 并发与安全测试
  - 竞态检测
  - 安全测试
  - 场景生成

**测试**: 226个测试通过

**Phase 5总测试**: 751个测试全部通过

---

## 实战测试成果

### 测试环境

- **目标**: SeekDB @ localhost:2881
- **测试日期**: 2026-03-03
- **框架版本**: v1.2b

### 测试结果

| 测试类型 | 执行数 | 结果 |
|----------|--------|------|
| 产品级测试 | 170操作 | 100%通过 |
| 高并发测试 | 50操作 | 55144 ops/s |
| 压力测试 | 100操作 | 100K ops/s |
| 探索性测试 | 114测试 | 发现6个Bug |

### 发现的产品Bug

| Bug ID | 严重度 | 问题描述 |
|--------|--------|----------|
| #1 | HIGH | 负维度被接受 (dimension=-1) |
| #2 | HIGH | 超大维度被接受 (dimension=65537) |
| #3 | HIGH | 缺少维度被接受 |
| #4 | HIGH | 零top_k被接受 (top_k=0) |
| #5 | HIGH | 超大top_k被接受 (top_k=10001) |
| #6 | HIGH | 无效metric被接受 |

### 修复建议

```python
def validate_search_params(dimension=None, top_k=None, metric_type=None):
    """验证搜索参数"""
    if dimension is not None:
        if not isinstance(dimension, int) or dimension < 1 or dimension > 65536:
            raise ValueError("dimension must be 1-65536")
    else:
        raise ValueError("dimension is required")

    if top_k is not None:
        if not isinstance(top_k, int) or top_k < 1 or top_k > 10000:
            raise ValueError("top_k must be 1-10000")

    if metric_type and metric_type not in ["L2", "IP", "COSINE"]:
        raise ValueError("metric_type must be L2, IP, or COSINE")
```

---

## 快速开始

### 安装依赖

```bash
git clone https://github.com/yihui504/SBMF.git
cd SBMF
pip install -r requirements.txt
```

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定模块测试
pytest tests/test_models.py -v
pytest tests/test_contract_builder.py -v

# 查看测试覆盖率
pytest tests/ --cov=. --cov-report=html
```

### 使用Contract DSL

```python
from contract import load_contract
from adapters import SeekDBAdapter
from core.models import SemanticCase

# 加载Contract
contract = load_contract("contracts/seekdb.yaml")

# 创建适配器
adapter = SeekDBAdapter(host="localhost", port=2881)
adapter.connect()

# 创建测试用例
test_case = SemanticCase(
    test_id="test_001",
    operation="search",
    slot_values={"dimension": 128, "top_k": 10},
    raw_parameters={},
    is_legal=True,
    scope=SlotScope.DATABASE
)

# 执行测试
result = adapter.execute_test(test_case)
print(f"Status: {result.status}")
print(f"Result: {result.result_data}")
```

### 运行实战测试

```bash
# 产品级测试
PYTHONPATH=. python tests/integration/product_level_test.py

# 探索性测试
PYTHONPATH=. python tests/integration/exploratory_testing.py

# 深度Bug分析
PYTHONPATH=. python tests/integration/deep_analysis.py
```

---

## 项目结构

```
SBMF/
├── README.md                    # 本文件
├── requirements.txt             # Python依赖
├── .env.example                 # 环境变量示例
├── docker-compose.yml           # Docker编排
│
├── core/                        # 核心模块
│   ├── models.py                # 数据模型 (Slot, Rule, Contract)
│   ├── three_valued_logic.py    # 三值逻辑系统
│   ├── bug_type_engine.py       # Bug类型推导引擎
│   ├── execution_pipeline.py    # 执行流程
│   ├── rule_engine.py           # 规则引擎
│   ├── precondition_gate.py     # 前置条件检查
│   └── oracle_reporter.py       # Oracle报告器
│
├── contract/                    # Contract DSL系统
│   ├── parser.py                # YAML解析器
│   ├── schema.py                # Schema验证
│   ├── validator.py             # 语义验证器
│   ├── builder.py               # Contract构建器
│   └── types.py                 # 数据类型定义
│
├── adapters/                    # 数据库适配器
│   ├── base.py                  # 适配器基类
│   ├── seekdb.py                # SeekDB适配器
│   ├── milvus.py                # Milvus适配器
│   └── weaviate.py              # Weaviate适配器
│
├── agent/                       # Agent系统
│   ├── runtime.py               # 运行时
│   ├── memory.py                # 记忆管理
│   ├── monitor.py               # 性能监控
│   └── tools/                   # 工具系统
│
├── fuzzing/                     # Fuzzing模块
│   ├── fuzzer.py                # Fuzzer核心
│   ├── mutation.py              # 变异策略
│   ├── feedback.py              # 反馈机制
│   └── corpus.py                # 测试语料库
│
├── detectors/                   # 异常检测
│   ├── anomaly_adapter.py       # 异常检测适配器
│   ├── pattern_learner.py       # 模式学习
│   └── threshold_manager.py     # 阈值管理
│
├── generators/                  # 测试生成器
│   ├── random_generator.py      # 随机生成
│   ├── boundary_generator.py    # 边界生成
│   ├── combinatorial.py         # 组合生成
│   └── enhanced_strategy.py     # 增强策略
│
├── bug_classifier/              # Bug分类
│   ├── agent.py                 # 分类Agent
│   ├── feature_extractor.py     # 特征提取
│   ├── similarity.py            # 相似度计算
│   └── fix_generator.py         # 修复建议
│
├── concurrency/                 # 并发测试
│   ├── race_detector.py         # 竞态检测
│   ├── scenario_generator.py    # 场景生成
│   └── security_tester.py       # 安全测试
│
├── oracle/                      # Oracle系统
│   ├── base.py                  # Oracle基类
│   ├── ast_nodes.py             # AST节点
│   └── checkers.py              # 内置检查器
│
├── tests/                       # 测试
│   ├── test_*.py                # 单元测试
│   └── integration/             # 集成测试
│
├── reports/                     # 测试报告
│   ├── phase5_final_validation.json
│   ├── exploratory_testing.json
│   └── real_world_testing_report.md
│
└── docs/                        # 文档
    └── design/                  # 设计文档
        ├── 001-architecture-overview.md
        ├── 002-contract-dsl-spec.md
        └── ...
```

---

## 测试统计

### 总体统计

- **总测试数**: 751
- **通过率**: 100%
- **代码行数**: ~15000行Python代码
- **覆盖模块**: 20+核心模块

### 分阶段测试

| Phase | 模块 | 测试数 |
|-------|------|--------|
| 1 | 核心基础 | 42 |
| 2 | Contract DSL | 157 |
| 3 | 依赖与状态 | 67 |
| 4 | Plugin与Oracle | 137 |
| 5 | Agent驱动 | 226 |
| 其他 | 集成测试 | 122 |

---

## 技术栈

### 核心依赖

- **Python**: 3.8+
- **pydantic**: 数据验证
- **PyYAML**: YAML解析
- **pytest**: 测试框架

### 设计模式

- **Builder模式**: Contract构建
- **Strategy模式**: 变异策略
- **Observer模式**: 监控系统
- **Adapter模式**: 数据库适配
- **Template Method**: Oracle检查器

---

## 贡献指南

### 开发环境设置

```bash
# 安装开发依赖
pip install -r requirements.txt
pip install black isort mypy pytest-cov

# 代码格式化
black .
isort .

# 类型检查
mypy .

# 运行测试
pytest tests/ -v
```

### 提交规范

```
feat: 新功能
fix: Bug修复
docs: 文档更新
style: 代码格式
refactor: 重构
test: 测试相关
chore: 构建/工具相关
```

---

## 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## 致谢

感谢Semantic Bug Mining Framework的所有贡献者。

---

## 联系方式

- GitHub: https://github.com/yihui504/SBMF
- Issues: https://github.com/yihui504/SBMF/issues

---

**版本**: v1.2b
**最后更新**: 2026-03-03
