# 三值逻辑系统规范

**版本**: v1.1
**状态**: 冻结
**日期**: 2026-03-02

---

## 一、三值逻辑定义

| 值 | 说明 | 符号 |
|-----|------|------|
| **True** | 规则明确通过 | ⊤ |
| **False** | 规则明确违反 | ⊥ |
| **None** | 无法评估（条件不满足/参数缺失） | ? |

---

## 二、核心计算规则

### 2.1 整体评估规则

```python
def compute_overall_passed(results: List[Optional[bool]]) -> Optional[bool]:
    """
    计算整体评估结果

    规则：
    1. False + anything → False
    2. True + None → True
    3. 全部 None → None (不可评估)

    不允许 None 被隐式当作 True 或 False
    """

    if not results:
        return None

    # 规则 1: False + anything → False
    if any(r is False for r in results):
        return False

    # 检查是否有明确的 True
    has_true = any(r is True for r in results)
    has_none = any(r is None for r in results)

    # 规则 2: True + None → True
    if has_true and has_none:
        return True

    # 规则 3: 全部 None → None
    if has_none and not has_true:
        return None

    # 全部 True
    if has_true and not has_none:
        return True

    return None
```

### 2.2 逻辑运算符

```python
class ThreeValuedLogic:
    """三值逻辑系统"""

    @staticmethod
    def and_operator(a: Optional[bool], b: Optional[bool]) -> Optional[bool]:
        """三值逻辑与运算 (∧)

        真值表:
        a ∧ b | True  | False | None
        --------|-------|-------|------
        True    | True  | False | None
        False   | False | False | False
        None    | None  | False | None
        """
        if a is False or b is False:
            return False
        if a is None or b is None:
            return None
        return True

    @staticmethod
    def or_operator(a: Optional[bool], b: Optional[bool]) -> Optional[bool]:
        """三值逻辑或运算 (∨)

        真值表:
        a ∨ b | True  | False | None
        --------|-------|-------|------
        True    | True  | True  | True
        False   | True  | False | None
        None    | True  | None  | None
        """
        if a is True or b is True:
            return True
        if a is None or b is None:
            return None
        return False

    @staticmethod
    def not_operator(a: Optional[bool]) -> Optional[bool]:
        """三值逻辑非运算 (¬)

        真值表:
        a | ¬a
        ---|---
        True | False
        False| True
        None | None
        """
        if a is None:
            return None
        return not a
```

---

## 三、评估追踪结构

```python
@dataclass
class ThreeValuedEvaluationTrace:
    """三值逻辑评估追踪

    提供可解释性输出
    """
    final_result: Optional[bool]      # 最终结果
    false_sources: List[str]          # 导致 False 的规则来源
    none_sources: List[str]           # 导致 None 的规则来源
    evaluation_path: str              # 评估路径描述

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "final_result": self.final_result,
            "false_sources": self.false_sources,
            "none_sources": self.none_sources,
            "evaluation_path": self.evaluation_path
        }
```

---

## 四、使用示例

### 4.1 基础示例

```python
# 示例 1: 全部通过
results = [True, True, True]
trace = ThreeValuedEvaluationTrace(
    final_result=True,
    false_sources=[],
    none_sources=[],
    evaluation_path="all_rules_passed"
)
# final_result: True

# 示例 2: 有一个违反
results = [True, False, True]
trace = ThreeValuedEvaluationTrace(
    final_result=False,
    false_sources=["slot_search_range.rule_relational"],
    none_sources=[],
    evaluation_path="false_from_slot_search_range"
)
# final_result: False

# 示例 3: 混合 True 和 None
results = [True, None, True]
trace = ThreeValuedEvaluationTrace(
    final_result=True,
    false_sources=[],
    none_sources=["slot_ef.rule_conditional"],
    evaluation_path="true_with_none_skipped"
)
# final_result: True

# 示例 4: 全部无法评估
results = [None, None, None]
trace = ThreeValuedEvaluationTrace(
    final_result=None,
    false_sources=[],
    none_sources=["all_rules"],
    evaluation_path="none_not_evaluable"
)
# final_result: None
```

### 4.2 条件规则示例

```python
# 场景: 仅在 search 操作时验证 search_range >= top_k
# 如果操作是 insert，则 search_range 规则返回 None

# 操作为 insert
results = [
    True,   # dimension 规则通过
    True,   # top_k 规则通过
    None    # search_range 规则不适用
]
# compute_overall_passed(results) → True

# 操作为 search，且 search_range < top_k
results = [
    True,   # dimension 规则通过
    True,   # top_k 规则通过
    False   # search_range 违反规则
]
# compute_overall_passed(results) → False
```

---

## 五、RuleEngine 集成

```python
class RuleEngine:
    """规则评估引擎"""

    def evaluate_rules(self,
                       test_case: TestCase,
                       execution_context: ExecutionContext) -> RuleEvaluationResult:
        """评估所有规则"""

        results = []
        false_sources = []
        none_sources = []

        for slot_rule in self.contract.get_all_slots():
            result = self._evaluate_slot_rule(slot_rule, test_case, execution_context)
            results.append(result)

            # 记录来源
            if result.passed is False:
                false_sources.append(f"{slot_rule.slot_name}.{result.rule_id}")
            elif result.passed is None:
                none_sources.append(f"{slot_rule.slot_name}.{result.rule_id}")

        # 计算整体结果
        overall_passed = ThreeValuedLogic.compute_overall_passed(
            [r.passed for r in results]
        )

        # 生成追踪
        trace = ThreeValuedEvaluationTrace(
            final_result=overall_passed,
            false_sources=false_sources,
            none_sources=none_sources,
            evaluation_path=self._generate_evaluation_path(results)
        )

        return RuleEvaluationResult(
            results=results,
            overall_passed=overall_passed,
            coverage_report=self.coverage_tracker.get_report(),
            trace=trace
        )
```

---

## 六、决策表

```
┌───────┬───────┬────────────────────────────────┐
│ a     │ b     │ compute_overall_passed([a,b])  │
├───────┼───────┼────────────────────────────────┤
│ True  │ True  │ True                           │
│ True  │ False │ False                          │
│ True  │ None  │ True                           │
│ False │ True  │ False                          │
│ False │ False │ False                          │
│ False │ None  │ False                          │
│ None  │ True  │ True                           │
│ None  │ False │ False                          │
│ None  │ None  │ None                           │
└───────┴───────┴────────────────────────────────┘

┌───────┬────────────────────────────────────┐
│ a     │ compute_overall_passed([a])         │
├───────┼────────────────────────────────────┤
│ True  │ True                               │
│ False │ False                              │
│ None  │ None                               │
└───────┴────────────────────────────────────┘
```

---

## 七、注意事项

### 7.1 不允许的隐式转换

```python
# ❌ 错误: 将 None 隐式当作 False
if not result.passed:
    # 这会将 None 当作 False 处理！
    pass

# ✅ 正确: 显式检查三种状态
if result.passed is False:
    # 明确违反
    pass
elif result.passed is True:
    # 明确通过
    pass
else:  # None
    # 无法评估
    pass
```

### 7.2 条件规则的特殊处理

```python
# 条件规则的评估:
# - 如果条件不满足，返回 None（不参与整体评估）
# - 如果条件满足，评估 then_rules

# 示例: 仅在 search 操作时验证 search_range
rule = ConditionalRule(
    condition=SlotEquals("operation", "search"),
    then_rules=[RelationalRule(...)]
)

# 操作为 insert:
# → 条件不满足 → 返回 None

# 操作为 search:
# → 条件满足 → 评估 then_rules
```

---

## 八、测试用例

```python
# 测试用例 1: 全部通过
assert ThreeValuedLogic.compute_overall_passed([True, True, True]) == True

# 测试用例 2: 一个违反
assert ThreeValuedLogic.compute_overall_passed([True, False, True]) == False

# 测试用例 3: 混合 True 和 None
assert ThreeValuedLogic.compute_overall_passed([True, None, True]) == True

# 测试用例 4: 全部 None
assert ThreeValuedLogic.compute_overall_passed([None, None, None]) is None

# 测试用例 5: 空列表
assert ThreeValuedLogic.compute_overall_passed([]) is None

# 测试用例 6: AND 运算
assert ThreeValuedLogic.and_operator(True, True) == True
assert ThreeValuedLogic.and_operator(True, False) == False
assert ThreeValuedLogic.and_operator(True, None) == None
assert ThreeValuedLogic.and_operator(False, None) == False

# 测试用例 7: OR 运算
assert ThreeValuedLogic.or_operator(True, True) == True
assert ThreeValuedLogic.or_operator(True, False) == True
assert ThreeValuedLogic.or_operator(False, None) == None
assert ThreeValuedLogic.or_operator(True, None) == True

# 测试用例 8: NOT 运算
assert ThreeValuedLogic.not_operator(True) == False
assert ThreeValuedLogic.not_operator(False) == True
assert ThreeValuedLogic.not_operator(None) is None
```
