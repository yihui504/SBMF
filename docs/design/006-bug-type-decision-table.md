# Bug 类型推导决策表

**版本**: v1.1
**状态**: 冻结
**日期**: 2026-03-02

---

## 一、决策表概览

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Bug 类型推导决策表                             │
├──────┬──────────────┬──────────────────┬─────────────┬───────────────┤
│ Case │ is_legal    │ status           │ violated    │ → BugType     │
├──────┼──────────────┼──────────────────┼─────────────┼───────────────┤
│  1   │ False       │ SUCCESS          │ *           │ TYPE_1        │
│  2   │ False       │ FAILURE          │ False       │ TYPE_2        │
│  3   │ True        │ FAILURE          │ *           │ TYPE_3        │
│  4   │ True        │ SUCCESS          │ True        │ TYPE_4        │
│  5   │ False       │ FAILURE          │ True        │ NOT_A_BUG     │
│  6   │ True        │ FAILURE          │ *           │ PRECONDITION  │
│  7   │ *           │ TIMEOUT          │ *           │ TYPE_3        │
│  8   │ *           │ CRASH           │ *           │ TYPE_3        │
└──────┴──────────────┴──────────────────┴─────────────┴───────────────┘
```

---

## 二、输入参数定义

| 参数 | 类型 | 说明 |
|------|------|------|
| `test_case.is_legal` | bool | 测试用例是否合法（根据 Contract 判断） |
| `execution_result.status` | ExecutionStatus | 执行结果状态 |
| `rule_result.violated` | bool? | 规则是否违反（三值逻辑） |
| `error.has_root_cause_slot` | bool | 错误是否有根因槽 |
| `precondition_passed` | bool | 预条件是否通过 |

---

## 三、详细推导逻辑

### Case 1: TYPE_1 - 非法操作成功

```
条件:
  is_legal = False
  status = SUCCESS

说明:
  非法操作未报错，被数据库接受

示例:
  dimension = 0（最小值应为 1）
  执行结果: SUCCESS

推导:
  → TYPE_1 (非法操作成功)
```

### Case 2: TYPE_2 - 错误不可诊断

```
条件:
  is_legal = False
  status = FAILURE
  has_root_cause_slot = False

说明:
  非法操作正确报错，但错误信息缺失根因槽

示例:
  dimension = 999999（超出最大值）
  错误信息: "Invalid parameter"（未说明哪个参数）

推导:
  → TYPE_2 (错误不可诊断)
```

### Case 3: TYPE_3 - 合法操作失败

```
条件:
  is_legal = True
  status = FAILURE (or CRASH or TIMEOUT)
  precondition_passed = True

说明:
  合法操作被拒绝、崩溃或超时

示例:
  dimension = 128（合法）
  top_k = 10（合法）
  执行结果: CONNECTION_ERROR

推导:
  → TYPE_3 (合法操作失败)
```

### Case 4: TYPE_4 - 语义违背

```
条件:
  is_legal = True
  status = SUCCESS
  violated = True
  precondition_passed = True

说明:
  合法操作成功，但结果违反语义规则

示例:
  top_k = 10
  返回结果数 = 11（违反 top_k 单调性）

推导:
  → TYPE_4 (语义违背)
```

### Case 5: NOT_A_BUG - 预期行为

```
条件:
  is_legal = False
  status = FAILURE
  has_root_cause_slot = True

说明:
  非法操作正确报错，且错误信息清晰

示例:
  dimension = 0（非法）
  错误信息: "dimension must be >= 1, got 0"

推导:
  → NOT_A_BUG (预期行为)
```

### Case 6: PRECONDITION_VIOLATION - 预条件未通过

```
条件:
  is_legal = True
  status = FAILURE
  precondition_passed = False

说明:
  预条件未通过，不计入 Bug

示例:
  集合不存在时执行 search

推导:
  → PRECONDITION_VIOLATION (不是 Bug)
```

### Case 7/8: TYPE_3 - 超时/崩溃

```
条件:
  status = TIMEOUT or CRASH

说明:
  超时或崩溃一律视为 TYPE_3

推导:
  → TYPE_3 (合法操作失败)
```

---

## 四、优先级顺序

```
优先级 1: 超时/崩溃 → TYPE_3
优先级 2: 非法成功 → TYPE_1
优先级 3: 预条件违反 → PRECONDITION_VIOLATION
优先级 4: 错误不可诊断 → TYPE_2
优先级 5: 预期行为 → NOT_A_BUG
优先级 6: 合法失败 → TYPE_3
优先级 7: 语义违背 → TYPE_4
```

---

## 五、Python 实现

```python
class BugTypeEngine:
    """Bug 类型推导引擎"""

    @staticmethod
    def derive_bug_type(test_case: TestCase,
                       rule_result: Optional[RuleEvaluationResult],
                       execution_result: ExecutionResult,
                       error_has_root_cause: bool,
                       precondition_passed: bool) -> BugTypeDerivation:
        """推导 Bug 类型"""

        # 优先级 1: 超时/崩溃 → TYPE_3
        if execution_result.status in [ExecutionStatus.TIMEOUT, ExecutionStatus.CRASH]:
            return BugTypeDerivation(
                bug_type=BugType.TYPE_3,
                reason=f"执行状态为 {execution_result.status.value}",
                confidence=1.0,
                decision_path="priority_1_timeout_crash"
            )

        # 优先级 2: 非法成功 → TYPE_1
        if (not test_case.is_legal and
            execution_result.status == ExecutionStatus.SUCCESS):
            return BugTypeDerivation(
                bug_type=BugType.TYPE_1,
                reason="非法操作未报错",
                confidence=1.0,
                decision_path="priority_2_illegal_success"
            )

        # 优先级 3: 预条件违反 → PRECONDITION_VIOLATION
        if not precondition_passed:
            return BugTypeDerivation(
                bug_type=None,
                reason="预条件未通过，不计入 Bug",
                confidence=1.0,
                decision_path="priority_3_precondition_failed"
            )

        # 优先级 4: 错误不可诊断 → TYPE_2
        if (not test_case.is_legal and
            execution_result.status == ExecutionStatus.FAILURE and
            not error_has_root_cause):
            return BugTypeDerivation(
                bug_type=BugType.TYPE_2,
                reason="非法操作报错但错误信息缺失根因槽",
                confidence=1.0,
                decision_path="priority_4_bad_diagnostics"
            )

        # 优先级 5: 预期行为 → NOT_A_BUG
        if (not test_case.is_legal and
            execution_result.status == ExecutionStatus.FAILURE and
            error_has_root_cause):
            return BugTypeDerivation(
                bug_type=None,
                reason="非法操作正确报错，预期行为",
                confidence=1.0,
                decision_path="priority_5_expected_failure"
            )

        # 优先级 6: 合法失败 → TYPE_3
        if (test_case.is_legal and
            execution_result.status == ExecutionStatus.FAILURE):
            return BugTypeDerivation(
                bug_type=BugType.TYPE_3,
                reason="合法操作报错/失败",
                confidence=1.0,
                decision_path="priority_6_legal_failure"
            )

        # 优先级 7: 语义违背 → TYPE_4
        if (test_case.is_legal and
            execution_result.status == ExecutionStatus.SUCCESS and
            rule_result is not None and
            rule_result.overall_passed is False):
            return BugTypeDerivation(
                bug_type=BugType.TYPE_4,
                reason="合法操作结果违反语义规则",
                confidence=1.0,
                decision_path="priority_7_semantic_violation",
                violated_rules=BugTypeEngine._extract_violated_rules(rule_result)
            )

        # 默认: 无法判断
        return BugTypeDerivation(
            bug_type=None,
            reason="无法推导 Bug 类型",
            confidence=0.0,
            decision_path="default_unknown"
        )
```

---

## 六、决策树

```
                    ┌─────────────────┐
                    │   执行结果状态    │
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
        ┌───┴────┐      ┌───┴────┐      ┌───┴────┐
        │ TIMEOUT │      │ CRASH  │      │ 其他   │
        └────┬────┘      └────┬───┘      └────┬───┘
             │                │               │
             └────────┬───────┴───────────────┘
                      │
                      ▼
              ┌─────────────────┐
              │   → TYPE_3      │
              └─────────────────┘

                    ┌─────────────────┐
                    │   其他状态       │
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
        ┌───┴────┐      ┌───┴────┐      ┌───┴────┐
        │ SUCCESS │      │ FAILURE │      │ PRECOND │
        └────┬────┘      └────┬───┘      └────┬───┘
             │                │               │
             ▼                ▼               ▼
      ┌─────────┐        ┌─────────┐    ┌─────────┐
      │ 合法?   │        │ 合法?   │    │ 预条件   │
      └────┬────┘        └────┬────┘    │ 失败    │
           │                 │           └────┬────┘
      ┌────┴────┐       ┌────┴────┐             │
      │   NO    │       │   YES   │             ▼
      └────┬────┘       └────┬────┘     ┌─────────┐
           │                 │           │ PRECOND │
           ▼                 ▼           │ VIOLAT  │
    ┌─────────┐       ┌─────────┐    └─────────┘
    │ → TYPE_1│       │ 有根因? │
    └─────────┘       └────┬────┘
                      ┌────┴────┐
                      │         │
                   ┌───┴───┐ ┌──┴───┐
                   │  NO   │ │ YES │
                   └───┬───┘ └──┬───┘
                       │        │
                       ▼        ▼
                ┌─────────┐ ┌─────────┐
                │ → TYPE_2│ │ NOT_BUG │
                └─────────┘ └─────────┘
```
