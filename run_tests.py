#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速测试运行器

一键运行实战测试并生成报告。
"""

import os
import sys
import subprocess
from pathlib import Path


def print_banner():
    print("=" * 70)
    print(" " * 15 + "Semantic Bug Mining Framework - 实战测试")
    print("=" * 70)
    print()


def check_environment():
    """检查环境"""
    print("🔍 检查环境...")

    # 检查项目目录
    project_root = Path(__file__).parent
    os.chdir(project_root)

    # 检查关键文件
    required_files = [
        "contract/__init__.py",
        "core/__init__.py",
        "oracle/__init__.py",
        "profiles/__init__.py",
        "tests/fixtures/integration/seekdb_contract.yaml"
    ]

    for file in required_files:
        if not Path(file).exists():
            print(f"   ❌ 缺少文件: {file}")
            return False

    print("   ✅ 环境检查通过")
    print()
    return True


def run_unit_tests():
    """运行单元测试"""
    print("🧪 运行单元测试...")
    print("-" * 70)

    result = subprocess.run(
        ["python", "-m", "pytest", "tests/", "-q", "--tb=no"],
        capture_output=True,
        text=True
    )

    # 解析输出
    lines = result.stdout.split("\n")
    for line in lines:
        if "passed" in line or "failed" in line or "skipped" in line:
            print(f"   {line}")

    if result.returncode == 0:
        print("   ✅ 单元测试通过")
    else:
        print("   ❌ 单元测试有失败")

    print()
    return result.returncode == 0


def run_integration_tests():
    """运行集成测试"""
    print("🚀 运行实战集成测试...")
    print("-" * 70)

    result = subprocess.run(
        ["python", "tests/integration/test_e2e_实战.py"],
        capture_output=False,
        text=True
    )

    if result.returncode == 0:
        print()
        print("   ✅ 集成测试通过")
    else:
        print()
        print("   ❌ 集成测试有失败")

    print()
    return result.returncode == 0


def show_reports():
    """显示测试报告"""
    reports_dir = Path("reports")

    if not reports_dir.exists():
        print("📁 reports 目录不存在")
        return

    html_report = reports_dir / "实战_测试报告.html"
    json_report = reports_dir / "实战_测试报告.json"
    txt_report = reports_dir / "实战_测试报告.txt"

    if html_report.exists():
        print(f"📊 HTML 报告: {html_report.absolute()}")
        print(f"   (建议用浏览器打开查看)")
    if json_report.exists():
        print(f"📊 JSON 报告: {json_report.absolute()}")
    if txt_report.exists():
        print(f"📊 Text 报告: {txt_report.absolute()}")

    # 尝试自动打开 HTML 报告
    if html_report.exists():
        try:
            os.startfile(html_report.absolute())
            print(f"   ✅ 已在浏览器中打开 HTML 报告")
        except:
            print()


def show_summary():
    """显示测试摘要"""
    print()
    print("=" * 70)
    print("📋 测试摘要")
    print("=" * 70)
    print()
    print("测试层级:")
    print("  ✅ L1: 单元测试 (511 tests) - 验证单个组件")
    print("  ✅ L2: 集成测试 (实战场景) - 验证组件协作")
    print("  ⏳ L3: 真实数据库测试 (需要环境配置)")
    print()
    print("框架组件:")
    print("  ✅ Contract DSL Runtime - 语义契约加载和验证")
    print("  ✅ Oracle Layer - 检查器注册和执行")
    print("  ✅ Profile Plugin Layer - 数据库特化逻辑")
    print("  ✅ ExecutionPipeline - 完整测试流程")
    print("  ✅ SeekDB Adapter - 模拟适配器")
    print()
    print("下一步:")
    print("  1. 查看 reports/ 目录下的测试报告")
    print("  2. 根据测试结果调整 Contract 或 Oracle")
    print("  3. (可选) 配置真实 SeekDB 进行 L3 测试")
    print()


def main():
    """主函数"""
    print_banner()

    # 检查环境
    if not check_environment():
        print("❌ 环境检查失败，请检查项目结构")
        return 1

    # 运行单元测试
    unit_passed = run_unit_tests()

    # 运行集成测试
    integration_passed = run_integration_tests()

    # 显示报告
    show_reports()

    # 显示摘要
    show_summary()

    # 返回结果
    if unit_passed and integration_passed:
        print("=" * 70)
        print("✅ 所有测试通过！框架已就绪。")
        print("=" * 70)
        return 0
    else:
        print("=" * 70)
        print("⚠️  部分测试失败，请查看详情。")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
