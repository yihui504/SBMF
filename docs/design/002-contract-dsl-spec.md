# Contract DSL 规范 v1.1

**版本**: v1.1
**状态**: 冻结
**日期**: 2026-03-02

---

## 一、概述

Contract DSL 是框架的核心，定义了数据库的语义契约。使用结构化 YAML 格式，支持：

- **核心语义槽**: 静态定义，不可修改
- **扩展语义槽**: 动态发现，人工审核，带版本范围和证据
- **结构化规则**: relational/conditional/enum/range/type
- **三值逻辑评估**: True/False/None

---

## 二、YAML Schema 定义

### 2.1 核心语义槽定义

```yaml
core_slots:
  - slot_name: string              # 语义槽名称（唯一标识）
    description: string            # 人类可读描述
    type: "integer" | "float" | "string" | "enum" | "boolean" | "vector"

    # ✨ v1.1 新增: Slot Scope (必填)
    scope: "DATABASE" | "COLLECTION" | "PARTITION" | "INDEX" | "REPLICA"

    # ✨ v1.1 新增: Slot Dependency 声明
    depends_on:
      - slot_name: string           # 依赖的槽名
        reason: string              # 依赖原因（可选）

    # 类型特定约束
    constraints:
      range:
        min: number | null
        max: number | null
        inclusive: boolean
      enum:
        values: list<any>
      vector:
        element_type: "float32" | "float16" | "int8" | "binary"
        dimension_slot: string

    # 规则列表
    rules:
      - rule_id: string
        type: "relational" | "range" | "conditional" | "enum" | "type"
        severity: "HIGH" | "MEDIUM" | "LOW"
        enabled: boolean
        priority: integer             # ✨ v1.1 新增，默认: 100

        relational:
          operator: ">=" | "<=" | ">" | "<" | "==" | "!=" | "in" | "not_in"
          reference_slot: string
          error_message: string
        range:
          min_value: any
          max_value: any
          inclusive_min: boolean
          inclusive_max: boolean
        conditional:
          condition:
            type: "operation_equals" | "slot_equals" | "slot_in_range" | "and" | "or" | "not"
            operands: list
          then:
            - <rule_definition>
          else:
            - <rule_definition>
        enum:
          allowed_values: list<any>
          strict: boolean
```

### 2.2 扩展语义槽定义

```yaml
extended_slots:
  - slot_name: string
    description: string
    type: string
    scope: "DATABASE" | "COLLECTION" | "PARTITION" | "INDEX" | "REPLICA"
    depends_on:
      - slot_name: string
        reason: string

  # ✨ v1.1 新增: 版本范围
  version_range:
    database_version:
      min_version: string          # 语义版本，如 "2.3.0"
      max_version: string | null
    applicable_operations: list<string> | null

  # ✨ v1.1 新增: 证据来源
  evidence:
    source: "official_documentation" | "code_analysis" | "llm_discovered" | "manual"
    url: string | null
    document_path: string | null
    excerpt: string | null
    discovered_at: string          # ISO 8601 时间戳
    discovered_by: "human" | "llm"
    reviewed_by: string | null
    review_status: "pending" | "approved" | "rejected"
    review_notes: string | null
    reviewed_at: string | null

  # 规则定义（同 core_slots）
  rules: list<rule_definition>
```

---

## 三、EBNF 语法定义

```
<contract>         ::= <core_slots> <extended_slots>?

<core_slots>       ::= "core_slots:" ":" <slot_definition_list>

<extended_slots>   ::= "extended_slots:" ":" <slot_definition_list>

<slot_definition_list> ::= "-" <slot_definition> <NL> <slot_definition_list>
                       | ε

<slot_definition>  ::= <slot_header> <scope_clause> <dependency_clause>?
                       <constraints>? <rules>

<slot_header>      ::= "slot_name:" <STRING> <NL>
                       "description:" <STRING> <NL>
                       "type:" <TYPE> <NL>

<scope_clause>     ::= "scope:" <SCOPE> <NL>

<dependency_clause>::= "depends_on:" ":" <dependency_list>

<dependency_list>  ::= "-" <dependency> <NL> <dependency_list>
                       | ε

<dependency>       ::= "slot_name:" <STRING> <NL>
                       ("reason:" <STRING> <NL>)?

<SCOPE>            ::= "DATABASE" | "COLLECTION" | "PARTITION" | "INDEX" | "REPLICA"

<TYPE>             ::= "integer" | "float" | "string" | "enum" | "boolean" | "vector"

<RULE_TYPE>        ::= "relational" | "range" | "conditional" | "enum" | "type"

<SEVERITY>         ::= "HIGH" | "MEDIUM" | "LOW"
```

---

## 四、Scope 语义说明

| Scope | 说明 | 示例 |
|-------|------|------|
| **DATABASE** | 全局级别，影响整个数据库实例 | max_connections, memory_limit |
| **COLLECTION** | 集合级别，影响单个集合 | dimension, metric_type, vector_field_name |
| **PARTITION** | 分区级别，影响单个分区 | partition_key, partition_range |
| **INDEX** | 索引级别，影响单个索引 | index_type, ef_construction, M |
| **REPLICA** | 副本级别，影响单个副本 | replica_lag, sync_mode |

---

## 五、Dependency 语义说明

`depends_on` 用于显式声明槽之间的依赖关系：

1. **测试生成器拓扑排序** - 依赖的槽先确定
2. **覆盖分析精确计算** - 依赖未覆盖时不计入
3. **影响面分析** - 快速定位修改影响范围
4. **规则冲突隔离** - 不同 scope 的同名槽不冲突

---

## 六、Priority 语义说明

`priority` 数值越小优先级越高，默认值: 100

| 优先级范围 | 用途 | 示例 |
|-----------|------|------|
| 10-49 | 核心规则 | dimension 范围检查 |
| 50-99 | 重要规则 | top_k 约束 |
| 100-199 | 普通规则 | 默认规则 |
| 200+ | 可选规则 | 调试规则 |

**冲突解决策略**:
- 同一槽的多个规则：按 priority 升序，取第一个
- 规则优先级相同时：按 rule_id 字典序

---

## 七、完整示例

```yaml
# contracts/core_slots.yaml

core_slots:
  # 示例 1: COLLECTION 级别的基础槽
  - slot_name: dimension
    description: "向量维度"
    type: integer
    scope: COLLECTION
    depends_on: []
    constraints:
      range:
        min: 1
        max: 32768
        inclusive: true
    rules:
      - rule_id: dim_range_check
        type: range
        severity: HIGH
        enabled: true
        priority: 10
        range:
          min_value: 1
          max_value: 32768
          inclusive_min: true
          inclusive_max: true

  # 示例 2: 依赖 dimension 的槽
  - slot_name: top_k
    description: "返回结果数量上限"
    type: integer
    scope: COLLECTION
    depends_on:
      - slot_name: dimension
        reason: "top_k 不应超过向量数量"
    constraints:
      range:
        min: 1
        max: 10000
        inclusive: true
    rules:
      - rule_id: top_k_range_check
        type: range
        severity: MEDIUM
        enabled: true
        priority: 50
        range:
          min_value: 1
          max_value: 10000
          inclusive_min: true
          inclusive_max: true

  # 示例 3: 依赖 top_k 的槽
  - slot_name: search_range
    description: "搜索范围参数"
    type: integer
    scope: COLLECTION
    depends_on:
      - slot_name: top_k
        reason: "search_range 必须 >= top_k"
    constraints:
      range:
        min: 1
        max: 100000
        inclusive: true
    rules:
      - rule_id: search_range_top_k_constraint
        type: relational
        severity: HIGH
        enabled: true
        priority: 10
        relational:
          operator: ">="
          reference_slot: top_k
          error_message: "search_range must be >= top_k"

  # 示例 4: INDEX 级别的槽
  - slot_name: ef
    description: "HNSW 索引的搜索参数"
    type: integer
    scope: INDEX
    depends_on:
      - slot_name: top_k
        reason: "ef 必须 >= top_k"
    constraints:
      range:
        min: 1
        max: 100000
        inclusive: true
    rules:
      - rule_id: ef_top_k_constraint
        type: relational
        severity: HIGH
        enabled: true
        priority: 10
        relational:
          operator: ">="
          reference_slot: top_k
          error_message: "ef must be >= top_k"
```

---

## 八、v1.1 变更总结

| 新增项 | 说明 | 影响 |
|--------|------|------|
| `scope` | Slot 作用域，必填 | 支持多粒度资源验证 |
| `depends_on` | 显式依赖声明 | 支持拓扑排序、影响面分析 |
| `priority` | 规则优先级 | 支持 profile override、冲突解决 |
| `version_range` | 扩展槽版本范围 | 支持版本差异管理 |
| `evidence` | 扩展槽证据来源 | 支持可追溯性 |
