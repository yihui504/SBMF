# 语义驱动的数据库 Bug 挖掘框架
## Semantic Bug Mining Framework

**版本**: v1.1
**状态**: 架构已冻结，设计完成
**日期**: 2026-03-02

---

## 🎯 项目定位

**核心定位**: 语义驱动的数据库 Bug 挖掘框架

- **主目标**: 数据库语义验证框架
- **支撑目标**: 自动化 fuzz 平台

---

## 📁 项目结构

```
SemanticBugMiningFramework/
├── README.md                      # 本文件
├── docs/
│   └── design/                    # 设计文档
│       ├── 001-architecture-overview.md
│       ├── 002-contract-dsl-spec.md
│       ├── 003-data-models.md
│       ├── 004-execution-pipeline.md
│       ├── 005-interface-specs.md
│       ├── 006-bug-type-decision-table.md
│       └── 007-three-valued-logic.md
├── core/                          # 核心模块
│   ├── __init__.py
│   ├── models.py                  # 数据模型定义
│   ├── three_valued_logic.py      # 三值逻辑系统
│   ├── bug_type_engine.py         # Bug 类型推导引擎
│   ├── execution_pipeline.py      # 执行流程
│   └── ...
├── adapters/                      # 数据库适配器
│   ├── __init__.py
│   ├── base.py                    # 适配器基类
│   └── seekdb.py                  # SeekDB 适配器
├── oracle/                        # Oracle 检查器
│   ├── __init__.py
│   ├── base.py                    # Oracle 基类
│   ├── ast_nodes.py               # AST 节点定义
│   └── checkers.py                # 内置 Oracle
├── contracts/                     # Contract 定义
│   ├── core_slots.yaml            # 核心语义槽
│   └── profiles/
│       └── seekdb.yaml            # SeekDB Contract
├── profiles/                      # Profile Plugin
│   ├── __init__.py
│   ├── base.py                    # Plugin 基类
│   └── seekdb.py                  # SeekDB Plugin
├── state/                         # 状态机模型
│   ├── __init__.py
│   ├── base.py                    # StateModel 基类
│   └── scoped.py                  # 多粒度状态机
└── tests/                         # 测试
    ├── test_models.py
    ├── test_three_valued_logic.py
    └── ...
```

---

## 🚀 快速开始

```bash
# 进入项目目录
cd C:/Users/11428/Desktop/SemanticBugMiningFramework

# 查看设计文档
ls docs/design/

# 开始实现 Phase 1
```

---

## 📋 Phase 1 实现清单

### 核心基础 (P0)

- [ ] Contract 层数据模型
- [ ] Contract DSL 解析器
- [ ] 三值逻辑系统
- [ ] Bug 类型推导引擎
- [ ] Adapter 接口定义
- [ ] SeekDB Adapter 实现
- [ ] RuleEngine 基础评估
- [ ] Precondition Gate
- [ ] StateModel 单粒度 (COLLECTION)
- [ ] 执行流程
- [ ] 基础报告生成

---

## 📚 设计文档索引

| 文档 | 内容 |
|------|------|
| 001 | 架构总览 |
| 002 | Contract DSL 规范 v1.1 |
| 003 | 核心数据模型 |
| 004 | 执行流程规范 |
| 005 | 接口规范 |
| 006 | Bug 类型推导决策表 |
| 007 | 三值逻辑系统 |

---

## 🎨 架构冻结状态

✅ Contract 层 - 结构化 DSL (scope/depends_on/priority)
✅ Oracle 层 - AST 验证逻辑
✅ Adapter 层 - Capabilities 唯一来源
✅ Profile Plugin 层 - Skip + Post-process
✅ RuleEngine 层 - 三值逻辑 + Session 隔离
✅ Precondition Gate 层 - 执行前检查 + StateModel
✅ StateModel 层 - 多粒度 scope + 异步稳定
✅ Bug Type Engine 层 - 置信度预留
✅ 核心引擎层 - 完整执行流程
