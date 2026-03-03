# -*- coding: utf-8 -*-
"""
Enhanced Test Generation Strategy

优化的智能体生成策略：
1. 深层次组合测试生成
2. 复杂边界情况覆盖
3. 关系约束测试
4. 自适应策略学习
"""
import time
from typing import Dict, List, Any, Set, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
from itertools import product, combinations

from core.models import SemanticCase, SlotScope, Slot, SlotType, SlotDependency
from adapters import SeekDBAdapter


class StrategyType(Enum):
    """生成策略类型"""
    BOUNDARY = "boundary"
    COMBINATORIAL = "combinatorial"
    RELATIONAL = "relational"
    EXTREME = "extreme"
    ADAPTIVE = "adaptive"


@dataclass
class GenerationStrategy:
    """生成策略"""
    name: str
    type: StrategyType
    priority: int
    complexity: int  # 1-10
    description: str


@dataclass
class TestTemplate:
    """测试模板"""
    name: str
    operation: str
    slots: Dict[str, Any]  # 槽位定义
    constraints: Dict[str, Any]  # 约束条件
    relationships: List[Dict] = field(default_factory=list)  # 槽位关系


class EnhancedTestGenerator:
    """
    增强的测试生成器

    提供更智能的测试用例生成策略，包括：
    - 深层次组合
    - 复杂边界情况
    - 关系约束测试
    """

    def __init__(self, adapter: Optional[SeekDBAdapter] = None):
        """
        初始化生成器

        Args:
            adapter: 数据库适配器（可选）
        """
        self.adapter = adapter or SeekDBAdapter()
        self.strategies: List[GenerationStrategy] = []
        self.generated_history: List[SemanticCase] = []
        self.coverage_tracker: Dict[str, Set[Any]] = {}

        # 定义测试模板
        self.templates = self._init_templates()

        # 初始化策略
        self._init_strategies()

    def _init_templates(self) -> List[TestTemplate]:
        """初始化测试模板"""
        templates = []

        # 搜索操作模板
        templates.append(TestTemplate(
            name="search_basic",
            operation="search",
            slots={
                "dimension": {"type": "int", "range": [1, 65536]},
                "top_k": {"type": "int", "range": [1, 10000]},
                "metric_type": {"type": "enum", "values": ["L2", "IP", "COSINE"]}
            },
            constraints={},
            relationships=[
                {"type": "correlation", "slots": ["dimension", "top_k"], "rule": "both_small_or_both_large"}
            ]
        ))

        # 插入操作模板
        templates.append(TestTemplate(
            name="insert_basic",
            operation="insert",
            slots={
                "dimension": {"type": "int", "range": [1, 32768]},
                "metric_type": {"type": "enum", "values": ["L2", "IP", "COSINE"]}
            },
            constraints={},
            relationships=[]
        ))

        # 高级搜索模板（带搜索范围）
        templates.append(TestTemplate(
            name="search_advanced",
            operation="search",
            slots={
                "dimension": {"type": "int", "range": [1, 65536]},
                "top_k": {"type": "int", "range": [1, 10000]},
                "metric_type": {"type": "enum", "values": ["L2", "IP", "COSINE"]},
                "search_range": {"type": "int", "range": [1, 1000]}
            },
            constraints={},
            relationships=[
                {"type": "ordering", "slots": ["search_range", "top_k"], "rule": "search_range >= top_k"},
                {"type": "boundary", "slots": ["search_range"], "rule": "power_of_2"}
            ]
        ))

        return templates

    def _init_strategies(self) -> None:
        """初始化生成策略"""
        self.strategies = [
            GenerationStrategy(
                name="boundary_deep",
                type=StrategyType.BOUNDARY,
                priority=1,
                complexity=3,
                description="深度边界值测试"
            ),
            GenerationStrategy(
                name="combinatorial_layered",
                type=StrategyType.COMBINATORIAL,
                priority=2,
                complexity=8,
                description="分层组合测试"
            ),
            GenerationStrategy(
                name="relational_constraint",
                type=StrategyType.RELATIONAL,
                priority=3,
                complexity=6,
                description="关系约束测试"
            ),
            GenerationStrategy(
                name="extreme_stress",
                type=StrategyType.EXTREME,
                priority=4,
                complexity=5,
                description="极限压力测试"
            ),
            GenerationStrategy(
                name="adaptive_learning",
                type=StrategyType.ADAPTIVE,
                priority=5,
                complexity=9,
                description="自适应学习测试"
            ),
        ]

    def generate_boundary_deep(self, count: int = 20) -> List[SemanticCase]:
        """
        生成深度边界测试

        覆盖以下边界情况：
        - 0, 1, 2^n - 1, 2^n
        - 负数（如果适用）
        - 最大值附近
        """
        tests = []
        test_id = 0

        # 维度边界：2的幂次方
        dimension_boundaries = [0, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024,
                              2048, 4096, 8192, 16384, 32768, 65536]

        for dim in dimension_boundaries:
            tests.append(SemanticCase(
                test_id=f"boundary_dim_{dim}",
                operation="search",
                slot_values={"dimension": dim, "top_k": 10},
                raw_parameters={},
                is_legal=(1 <= dim <= 32768),
                scope=SlotScope.DATABASE
            ))
            test_id += 1

        # top_k 边界
        top_k_boundaries = [0, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]

        for top_k in top_k_boundaries:
            tests.append(SemanticCase(
                test_id=f"boundary_topk_{top_k}",
                operation="search",
                slot_values={"dimension": 512, "top_k": top_k},
                raw_parameters={},
                is_legal=(1 <= top_k <= 10000),
                scope=SlotScope.DATABASE
            ))
            test_id += 1

        # 组合边界
        for dim, top_k in [(1, 1), (65536, 1), (1, 10000), (65536, 10000)]:
            tests.append(SemanticCase(
                test_id=f"boundary_combo_dim{dim}_k{top_k}",
                operation="search",
                slot_values={"dimension": dim, "top_k": top_k},
                raw_parameters={},
                is_legal=(1 <= dim <= 32768 and 1 <= top_k <= 10000),
                scope=SlotScope.DATABASE
            ))
            test_id += 1

        return tests[:count]

    def generate_combinatorial_layered(self, count: int = 30) -> List[SemanticCase]:
        """
        生成分层组合测试

        按照参数的重要性和相互作用进行分层组合
        """
        tests = []
        test_id = 0

        # 第一层：单一参数变化
        for dimension in [128, 512, 1024, 2048]:
            for metric in ["L2", "IP", "COSINE"]:
                tests.append(SemanticCase(
                    test_id=f"combo1_dim{dimension}_{metric}",
                    operation="search",
                    slot_values={"dimension": dimension, "metric_type": metric, "top_k": 10},
                    raw_parameters={},
                    is_legal=True,
                    scope=SlotScope.DATABASE
                ))
                test_id += 1

        # 第二层：两参数组合
        dimensions = [128, 512, 1024]
        top_ks = [1, 10, 100]
        metrics = ["L2", "IP", "COSINE"]

        for dim, top_k, metric in product(dimensions, top_ks, metrics):
            tests.append(SemanticCase(
                test_id=f"combo2_dim{dim}_k{top_k}_{metric}",
                operation="search",
                slot_values={"dimension": dim, "top_k": top_k, "metric_type": metric},
                raw_parameters={},
                is_legal=True,
                scope=SlotScope.DATABASE
            ))
            test_id += 1

        # 第三层：三参数组合（深层次）
        for dimension in [256, 512, 1024]:
            for metric in ["L2", "IP"]:
                for top_k in [5, 10, 50]:
                    for search_range in [10, 50, 100]:
                        if search_range >= top_k:  # 有效的关系约束
                            tests.append(SemanticCase(
                                test_id=f"combo3_dim{dimension}_{metric}_k{top_k}_r{search_range}",
                                operation="search",
                                slot_values={
                                    "dimension": dimension,
                                    "metric_type": metric,
                                    "top_k": top_k,
                                    "search_range": search_range
                                },
                                raw_parameters={},
                                is_legal=True,
                                scope=SlotScope.DATABASE
                            ))
                            test_id += 1

        return tests[:count]

    def generate_relational_constraint(self, count: int = 25) -> List[SemanticCase]:
        """
        生成关系约束测试

        专门测试参数之间的关系约束
        """
        tests = []
        test_id = 0

        # search_range >= top_k 关系
        test_cases = [
            # 有效组合：search_range >= top_k
            {"search_range": 10, "top_k": 1, "dimension": 512, "metric": "L2"},
            {"search_range": 50, "top_k": 10, "dimension": 512, "metric": "IP"},
            {"search_range": 100, "top_k": 50, "dimension": 512, "metric": "COSINE"},
            {"search_range": 100, "top_k": 100, "dimension": 1024, "metric": "L2"},

            # 无效组合：search_range < top_k（应该失败）
            {"search_range": 10, "top_k": 100, "dimension": 512, "metric": "L2"},
            {"search_range": 5, "top_k": 50, "dimension": 256, "metric": "IP"},
            {"search_range": 1, "top_k": 10, "dimension": 128, "metric": "COSINE"},
        ]

        for case in test_cases:
            is_valid = case["search_range"] >= case["top_k"]
            tests.append(SemanticCase(
                test_id=f"rel_r{case['search_range']}_k{case['top_k']}",
                operation="search",
                slot_values={
                    "search_range": case["search_range"],
                    "top_k": case["top_k"],
                    "dimension": case["dimension"],
                    "metric_type": case["metric"]
                },
                raw_parameters={},
                is_legal=is_valid,
                scope=SlotScope.DATABASE
            ))
            test_id += 1

        # 维度与 metric_type 兼容性
        dimension_metric_tests = [
            {"dimension": 128, "metric": "L2"},
            {"dimension": 128, "metric": "IP"},
            {"dimension": 128, "metric": "COSINE"},
            {"dimension": 32768, "metric": "L2"},
            {"dimension": 65536, "metric": "IP"},  # 可能不兼容
        ]

        for case in dimension_metric_tests:
            tests.append(SemanticCase(
                test_id=f"rel_dim{case['dimension']}_{case['metric']}",
                operation="search",
                slot_values={
                    "dimension": case["dimension"],
                    "metric_type": case["metric"],
                    "top_k": 10
                },
                raw_parameters={},
                is_legal=True,
                scope=SlotScope.DATABASE
            ))
            test_id += 1

        return tests[:count]

    def generate_extreme_stress(self, count: int = 15) -> List[SemanticCase]:
        """
        生成极限压力测试

        测试系统在极端条件下的行为
        """
        tests = []
        test_id = 0

        # 超大维度
        extreme_dims = [100000, 500000, 1000000, 999999]

        for dim in extreme_dims:
            tests.append(SemanticCase(
                test_id=f"extreme_dim_{dim}",
                operation="search",
                slot_values={"dimension": dim, "top_k": 10},
                raw_parameters={},
                is_legal=False,
                scope=SlotScope.DATABASE
            ))
            test_id += 1

        # 超大 top_k
        extreme_top_ks = [50000, 100000, 999999]

        for top_k in extreme_top_ks:
            tests.append(SemanticCase(
                test_id=f"extreme_topk_{top_k}",
                operation="search",
                slot_values={"dimension": 512, "top_k": top_k},
                raw_parameters={},
                is_legal=False,
                scope=SlotScope.DATABASE
            ))
            test_id += 1

        # 零和负值
        zero_tests = [
            {"dimension": 0, "top_k": 10},
            {"dimension": 512, "top_k": 0},
            {"dimension": -1, "top_k": 10},
        ]

        for case in zero_tests:
            tests.append(SemanticCase(
                test_id=f"extreme_zero_dim{case.get('dimension', 0)}_k{case.get('top_k', 0)}",
                operation="search",
                slot_values=case,
                raw_parameters={},
                is_legal=False,
                scope=SlotScope.DATABASE
            ))
            test_id += 1

        # 无效 metric_type
        tests.append(SemanticCase(
            test_id=f"extreme_invalid_metric",
            operation="search",
            slot_values={"dimension": 512, "top_k": 10, "metric_type": "INVALID"},
            raw_parameters={},
            is_legal=False,
            scope=SlotScope.DATABASE
        ))

        return tests[:count]

    def generate_adaptive_learning(self, count: int = 20) -> List[SemanticCase]:
        """
        生成自适应学习测试

        基于历史测试结果生成新的测试用例
        """
        tests = []
        test_id = 0

        # 分析历史覆盖率
        coverage_analysis = self._analyze_coverage()

        # 找出未覆盖的区域
        uncovered_dimensions = self._find_uncovered_values("dimension", coverage_analysis)
        uncovered_top_ks = self._find_uncovered_values("top_k", coverage_analysis)
        uncovered_metrics = self._find_uncovered_values("metric_type", coverage_analysis)

        # 生成覆盖未测试区域的测试
        for dim in uncovered_dimensions[:5]:
            tests.append(SemanticCase(
                test_id=f"adaptive_dim_{dim}",
                operation="search",
                slot_values={"dimension": dim, "top_k": 10},
                raw_parameters={},
                is_legal=(1 <= dim <= 32768),
                scope=SlotScope.DATABASE
            ))
            test_id += 1

        # 生成未测试的 metric 组合
        for metric in uncovered_metrics:
            for dim in [256, 512, 1024]:
                tests.append(SemanticCase(
                    test_id=f"adaptive_{metric}_dim{dim}",
                    operation="search",
                    slot_values={"dimension": dim, "metric_type": metric, "top_k": 10},
                    raw_parameters={},
                    is_legal=True,
                    scope=SlotScope.DATABASE
                ))
                test_id += 1

        # 基于错误模式生成测试
        for error_pattern in self._learn_error_patterns():
            tests.append(error_pattern)
            test_id += 1

        return tests[:count]

    def _analyze_coverage(self) -> Dict[str, Set[Any]]:
        """分析当前覆盖率"""
        if not self.generated_history:
            return {}

        coverage = {
            "dimension": set(),
            "top_k": set(),
            "metric_type": set(),
            "search_range": set()
        }

        for test in self.generated_history:
            for slot_name, slot_value in test.slot_values.items():
                if slot_name in coverage:
                    coverage[slot_name].add(slot_value)

        return coverage

    def _find_uncovered_values(self, slot_name: str, coverage: Dict) -> List[Any]:
        """找出未覆盖的值"""
        if slot_name not in coverage or not coverage[slot_name]:
            # 无历史数据，返回常见值
            if slot_name == "dimension":
                return [256, 512, 1024, 2048]
            elif slot_name == "top_k":
                return [5, 20, 50, 200]
            elif slot_name == "metric_type":
                return ["L2", "IP", "COSINE"]
            return []

        covered = coverage[slot_name]

        if slot_name == "dimension":
            all_values = set(range(1, 65537, 1000))  # 采样
        elif slot_name == "top_k":
            all_values = set(range(1, 10001, 100))
        elif slot_name == "metric_type":
            all_values = {"L2", "IP", "COSINE"}
        else:
            return []

        uncovered = all_values - covered
        return list(uncovered)[:10]  # 返回前10个

    def _learn_error_patterns(self) -> List[SemanticCase]:
        """从历史错误中学习"""
        # 简化实现：返回可能导致错误的测试
        return [
            SemanticCase(
                test_id="learn_error_dim_boundary",
                operation="search",
                slot_values={"dimension": 32769, "top_k": 10},  # 刚超出边界
                raw_parameters={},
                is_legal=False,
                scope=SlotScope.DATABASE
            ),
            SemanticCase(
                test_id="learn_error_k_boundary",
                operation="search",
                slot_values={"dimension": 512, "top_k": 10001},  # 刚超出边界
                raw_parameters={},
                is_legal=False,
                scope=SlotScope.DATABASE
            )
        ]

    def generate_mixed_strategy(self, total_count: int = 100) -> List[SemanticCase]:
        """
        混合策略生成

        按照优先级和复杂性混合使用各种策略
        """
        all_tests = []

        # 策略分配：根据优先级和复杂性分配测试数量
        strategy_distribution = {
            "boundary_deep": max(15, int(total_count * 0.20)),
            "combinatorial_layered": max(20, int(total_count * 0.30)),
            "relational_constraint": max(20, int(total_count * 0.20)),
            "extreme_stress": max(15, int(total_count * 0.15)),
            "adaptive_learning": max(10, int(total_count * 0.15)),
        }

        # 按策略生成测试
        strategy_generators = {
            "boundary_deep": self.generate_boundary_deep,
            "combinatorial_layered": self.generate_combinatorial_layered,
            "relational_constraint": self.generate_relational_constraint,
            "extreme_stress": self.generate_extreme_stress,
            "adaptive_learning": self.generate_adaptive_learning,
        }

        for strategy_name, count in strategy_distribution.items():
            generator = strategy_generators[strategy_name]
            tests = generator(count)
            all_tests.extend(tests)

        # 更新历史
        self.generated_history.extend(all_tests)

        return all_tests[:total_count]

    def analyze_diversity(self, tests: List[SemanticCase]) -> Dict[str, Any]:
        """分析测试多样性"""
        if not tests:
            return {"diversity_score": 0.0}

        metrics = {
            "total_tests": len(tests),
            "unique_operations": len(set(t.operation for t in tests)),
            "slot_diversity": {},
            "boundary_coverage": 0,
            "combinatorial_depth": 0,
            "constraint_coverage": 0
        }

        # 槽位多样性
        all_slots = set()
        for test in tests:
            all_slots.update(test.slot_values.keys())

        for slot in all_slots:
            values = set(t.slot_values.get(slot) for t in tests if slot in t.slot_values)
            metrics["slot_diversity"][slot] = len(values)

        # 边界覆盖率
        boundary_tests = sum(1 for t in tests if not t.is_legal or
                             any(v in [0, 1, 65536] for v in t.slot_values.values()))
        metrics["boundary_coverage"] = (boundary_tests / len(tests)) * 100

        # 组合深度（平均每个测试的参数数量）
        avg_params = sum(len(t.slot_values) for t in tests) / len(tests)
        metrics["combinatorial_depth"] = avg_params

        # 约束覆盖率（带关系约束的测试）
        constraint_tests = sum(1 for t in tests if "search_range" in t.slot_values and "top_k" in t.slot_values)
        metrics["constraint_coverage"] = (constraint_tests / len(tests)) * 100

        # 多样性得分
        diversity_score = (
            (metrics["unique_operations"] / 3) * 20 +  # 操作类型
            (len(metrics["slot_diversity"]) / 5) * 20 +  # 槽位类型
            min(metrics["boundary_coverage"], 30) +  # 边界覆盖
            min(metrics["constraint_coverage"], 30)  # 约束覆盖
        )
        metrics["diversity_score"] = min(diversity_score, 100.0)

        return metrics


def main():
    """测试优化的生成策略"""
    print("\n" + "="*70)
    print("Enhanced Test Generation Strategy")
    print("="*70)

    generator = EnhancedTestGenerator()

    # 使用混合策略生成测试
    print("\n[*] Generating tests with mixed strategy...")
    tests = generator.generate_mixed_strategy(total_count=100)

    print(f"[+] Generated {len(tests)} tests")

    # 分析多样性
    diversity = generator.analyze_diversity(tests)

    print(f"\n[*] Diversity Analysis:")
    print(f"   Total Tests: {diversity['total_tests']}")
    print(f"   Unique Operations: {diversity['unique_operations']}")
    print(f"   Boundary Coverage: {diversity['boundary_coverage']:.1f}%")
    print(f"   Constraint Coverage: {diversity['constraint_coverage']:.1f}%")
    print(f"   Combinatorial Depth: {diversity['combinatorial_depth']:.2f}")
    print(f"   Diversity Score: {diversity['diversity_score']:.1f}%")

    # 按策略统计
    strategy_counts = {}
    for test in tests:
        if "boundary" in test.test_id:
            strategy_counts["boundary"] = strategy_counts.get("boundary", 0) + 1
        elif "combo" in test.test_id:
            strategy_counts["combinatorial"] = strategy_counts.get("combinatorial", 0) + 1
        elif "rel" in test.test_id:
            strategy_counts["relational"] = strategy_counts.get("relational", 0) + 1
        elif "extreme" in test.test_id:
            strategy_counts["extreme"] = strategy_counts.get("extreme", 0) + 1
        elif "adaptive" in test.test_id:
            strategy_counts["adaptive"] = strategy_counts.get("adaptive", 0) + 1

    print(f"\n[*] Strategy Distribution:")
    for strategy, count in sorted(strategy_counts.items(), key=lambda x: -x[1]):
        print(f"   {strategy}: {count} tests")


if __name__ == "__main__":
    main()
