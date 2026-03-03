"""
End-to-End 实战测试

使用模拟 SeekDB Adapter 验证完整框架流程。
测试 Contract → Profile → Oracle → Pipeline 的集成。
"""

import pytest
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from contract import load_contract
from profiles import SeekDBProfilePlugin
from core import (
    ExecutionPipeline,
    OracleReporter,
    RuleEngine,
    PreconditionGate,
    ReportFormat,
)
from core.models import SemanticCase, SlotScope, ExecutionStatus
from oracle import (
    RangeConstraintOracle,
    EnumConstraintOracle,
    RelationalConstraintOracle,
    StatusValidationOracle,
    OracleResult,
    ComparisonOperator,
)
from adapters.seekdb import SeekDBAdapter


# ================================================================
# Test Fixtures
# ================================================================

@pytest.fixture(scope="module")
def contract():
    """加载 SeekDB Contract"""
    contract_path = "tests/fixtures/integration/seekdb_contract.yaml"
    return load_contract(contract_path)


@pytest.fixture(scope="module")
def adapter():
    """创建 SeekDB Adapter（模拟）"""
    return SeekDBAdapter()


@pytest.fixture(scope="module")
def profile():
    """创建 SeekDB Profile Plugin"""
    return SeekDBProfilePlugin(enable_logging=False)


@pytest.fixture(scope="module")
def oracles():
    """创建 Oracle 检查器列表"""
    return [
        RangeConstraintOracle("dimension", min_value=1, max_value=32768),
        EnumConstraintOracle("metric_type", allowed_values=["L2", "IP", "COSINE"]),
        RelationalConstraintOracle("search_range", ComparisonOperator.GE, "top_k"),
        StatusValidationOracle(expected_status="SUCCESS"),
    ]


@pytest.fixture
def pipeline(contract, oracles):
    """创建完整的执行流水线"""
    rule_engine = RuleEngine(contract)
    precondition_gate = PreconditionGate(rule_engine)

    return ExecutionPipeline(
        rule_engine=rule_engine,
        precondition_gate=precondition_gate,
        oracles=oracles
    )


# ================================================================
# 场景 1: 正常流程
# ================================================================

def test_场景1_正常搜索全部通过(pipeline, contract, adapter, profile):
    """测试正常搜索：所有检查通过"""
    test_case = SemanticCase(
        test_id="S001_正常搜索",
        operation="search",
        slot_values={
            "dimension": 512,
            "metric_type": "L2",
            "top_k": 10,
            "search_range": 100,
        },
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )

    result = pipeline.execute_test_case(
        test_case=test_case,
        contract=contract,
        adapter=adapter,
        profile=profile
    )

    # 验证执行成功
    assert result.status == ExecutionStatus.SUCCESS

    # 验证所有 Oracle 检查通过
    assert len(result.oracle_results) == 4
    assert all(r.passed for r in result.oracle_results)

    print(f"✅ {test_case.test_id}: 通过")
    print(f"   Oracle: {len(result.oracle_results)}/4 通过")


# ================================================================
# 场景 2: 维度约束违反
# ================================================================

def test_场景2_维度超限被Profile过滤(pipeline, contract, adapter, profile):
    """测试维度超限被 Profile 插件过滤"""
    test_case = SemanticCase(
        test_id="S002_维度超限",
        operation="search",
        slot_values={
            "dimension": 99999,  # 超过 32768
            "metric_type": "L2",
            "top_k": 10,
        },
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )

    result = pipeline.execute_test_case(
        test_case=test_case,
        contract=contract,
        adapter=adapter,
        profile=profile
    )

    # Profile 应该在预条件阶段跳过
    assert result.status == ExecutionStatus.PRECONDITION_FAILED
    assert "exceeds maximum" in result.gate_result.reason.lower()

    print(f"✅ {test_case.test_id}: 正确跳过")
    print(f"   原因: {result.gate_result.reason}")


# ================================================================
# 场景 3: 度量类型不支持
# ================================================================

def test_场景3_度量类型不支持被过滤(pipeline, contract, adapter, profile):
    """测试不支持的度量类型被过滤"""
    test_case = SemanticCase(
        test_id="S003_度量类型不支持",
        operation="search",
        slot_values={
            "dimension": 512,
            "metric_type": "HAMMING",  # 不支持
            "top_k": 10,
        },
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )

    result = pipeline.execute_test_case(
        test_case=test_case,
        contract=contract,
        adapter=adapter,
        profile=profile
    )

    assert result.status == ExecutionStatus.PRECONDITION_FAILED
    assert "not supported" in result.gate_result.reason.lower()

    print(f"✅ {test_case.test_id}: 正确跳过")
    print(f"   原因: {result.gate_result.reason}")


# ================================================================
# 场景 4: 关系约束违反
# ================================================================

def test_场景4_关系约束违反Oracle失败(pipeline, contract, adapter, profile):
    """测试关系约束违反被 Oracle 检测"""
    # 创建只检查关系约束的 pipeline
    relation_oracles = [
        RelationalConstraintOracle("search_range", ComparisonOperator.GE, "top_k"),
    ]

    rule_engine = RuleEngine(contract)
    precondition_gate = PreconditionGate(rule_engine)
    pipeline_custom = ExecutionPipeline(
        rule_engine=rule_engine,
        precondition_gate=precondition_gate,
        oracles=relation_oracles
    )

    test_case = SemanticCase(
        test_id="S004_关系约束违反",
        operation="search",
        slot_values={
            "dimension": 512,
            "metric_type": "L2",
            "top_k": 100,
            "search_range": 50,  # < top_k，违反约束
        },
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )

    result = pipeline_custom.execute_test_case(
        test_case=test_case,
        contract=contract,
        adapter=adapter,
        profile=profile
    )

    # 执行应该成功，但 Oracle 检查失败
    assert result.status == ExecutionStatus.SUCCESS
    assert len(result.oracle_results) == 1
    assert not result.oracle_results[0].passed
    assert "search_range" in result.oracle_results[0].violated_slots

    print(f"✅ {test_case.test_id}: 正确检测到违反")
    print(f"   Oracle: {result.oracle_results[0].details}")


# ================================================================
# 场景 5: 边界值测试
# ================================================================

def test_场景5_边界值全部通过(pipeline, contract, adapter, profile):
    """测试边界值：维度最小/最大值"""
    test_cases = [
        SemanticCase(
            test_id="B001_维度最小值",
            operation="search",
            slot_values={"dimension": 1, "metric_type": "L2", "top_k": 1},
            raw_parameters={},
            is_legal=True,
            scope=SlotScope.COLLECTION
        ),
        SemanticCase(
            test_id="B002_维度最大值",
            operation="search",
            slot_values={"dimension": 32768, "metric_type": "L2", "top_k": 1},
            raw_parameters={},
            is_legal=True,
            scope=SlotScope.COLLECTION
        ),
    ]

    for test_case in test_cases:
        result = pipeline.execute_test_case(
            test_case=test_case,
            contract=contract,
            adapter=adapter,
            profile=profile
        )

        assert result.status == ExecutionStatus.SUCCESS
        assert all(r.passed for r in result.oracle_results)
        print(f"✅ {test_case.test_id}: 通过")


# ================================================================
# 场景 6: COSINE + HNSW 不支持组合
# ================================================================

def test_场景6_COSINE_HNSW组合不支持(pipeline, contract, adapter, profile):
    """测试 COSINE + HNSW 组合被正确跳过"""
    test_case = SemanticCase(
        test_id="B004_COSINE_HNSW",
        operation="search",
        slot_values={
            "dimension": 512,
            "metric_type": "COSINE",
            "index_type": "HNSW",
            "top_k": 10,
        },
        raw_parameters={},
        is_legal=True,
        scope=SlotScope.COLLECTION
    )

    result = pipeline.execute_test_case(
        test_case=test_case,
        contract=contract,
        adapter=adapter,
        profile=profile
    )

    assert result.status == ExecutionStatus.PRECONDITION_FAILED
    assert "COSINE" in result.gate_result.reason and "HNSW" in result.gate_result.reason

    print(f"✅ {test_case.test_id}: 正确跳过")
    print(f"   原因: {result.gate_result.reason}")


# ================================================================
# 测试报告生成
# ================================================================

def test_生成测试报告():
    """生成测试报告演示"""
    # 模拟多个测试的 Oracle 结果
    all_results = [
        # 测试 1: 全部通过
        [
            OracleResult(oracle_id="dimension", passed=True, details="Dimension 512 OK"),
            OracleResult(oracle_id="metric_type", passed=True, details="Metric L2 OK"),
            OracleResult(oracle_id="relational", passed=True, details="100 >= 10 OK"),
        ],
        # 测试 2: 关系约束失败
        [
            OracleResult(oracle_id="dimension", passed=True, details="Dimension 512 OK"),
            OracleResult(
                oracle_id="relational",
                passed=False,
                details="search_range (50) < top_k (100)",
                violated_slots=["search_range"]
            ),
        ],
        # 测试 3: 全部通过
        [
            OracleResult(oracle_id="dimension", passed=True, details="Dimension 1024 OK"),
            OracleResult(oracle_id="metric_type", passed=True, details="Metric IP OK"),
        ],
    ]

    reporter = OracleReporter()

    # 聚合所有结果
    aggregated_report = reporter.aggregate_results(all_results)

    # 创建报告目录
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    # 保存多格式报告
    reporter.save_report(
        aggregated_report,
        reports_dir / "实战_测试报告.json",
        ReportFormat.JSON
    )
    reporter.save_report(
        aggregated_report,
        reports_dir / "实战_测试报告.html",
        ReportFormat.HTML
    )
    reporter.save_report(
        aggregated_report,
        reports_dir / "实战_测试报告.txt",
        ReportFormat.TEXT
    )

    print(f"\n📊 测试报告摘要:")
    print(f"   总 Oracle 检查: {aggregated_report.total_oracles}")
    print(f"   通过: {aggregated_report.passed_count}")
    print(f"   失败: {aggregated_report.failed_count}")
    print(f"   通过率: {aggregated_report.pass_rate * 100:.1f}%")
    print(f"\n📁 报告已保存到:")
    print(f"   - {reports_dir / '实战_测试报告.html'}")
    print(f"   - {reports_dir / '实战_测试报告.json'}")
    print(f"   - {reports_dir / '实战_测试报告.txt'}")

    # 验证报告内容
    assert aggregated_report.total_oracles == 8
    assert aggregated_report.passed_count == 6
    assert aggregated_report.failed_count == 2


# ================================================================
# 主测试运行器
# ================================================================

def run_all_实战_tests():
    """运行所有实战测试并生成报告"""
    print("=" * 60)
    print("Semantic Bug Mining Framework - 实战测试")
    print("=" * 60)
    print()

    # 运行 pytest
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--color=yes"
    ])

    print()
    print("=" * 60)
    if exit_code == 0:
        print("✅ 所有实战测试通过!")
    else:
        print("❌ 部分测试失败，请查看详情")
    print("=" * 60)

    return exit_code


if __name__ == "__main__":
    import sys
    sys.exit(run_all_实战_tests())
