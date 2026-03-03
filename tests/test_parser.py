"""
Tests for Contract YAML Parser.

Tests the YAMLParser ABC and PyYAMLParser implementation.
"""

import pytest
from pathlib import Path
from contract.parser import (
    YAMLParser,
    PyYAMLParser,
    ParserConfig,
    get_default_parser,
)
from contract.errors import ContractParseError

# Check if PyYAML is available
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


# ================================================================
# Test fixtures
# ================================================================

VALID_YAML = """
core_slots:
  - slot_name: dimension
    description: "Vector dimension"
    type: integer
    scope: COLLECTION
    depends_on: []
"""

VALID_YAML_NO_SLOTS = """
core_slots: []
"""

VALID_YAML_SIMPLE = """
database_name: test_db
version: "1.0"
core_slots: []
"""

INVALID_YAML_SYNTAX = """
core_slots:
  - slot_name: dimension
    description: "Unclosed string
"""

EMPTY_YAML = ""

YAML_LIST_ROOT = """
- item1
- item2
"""

YAML_STRING_ROOT = "just a string"

YAML_NULL_ROOT = "null"


# ================================================================
# PyYAMLParser.load_string 测试
# ================================================================

@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_load_string_valid_yaml():
    """Test loading valid YAML string"""
    parser = PyYAMLParser()
    result = parser.load_string(VALID_YAML)

    assert isinstance(result, dict)
    assert "core_slots" in result
    assert len(result["core_slots"]) == 1
    assert result["core_slots"][0]["slot_name"] == "dimension"


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_load_string_empty():
    """Test loading empty string raises error"""
    parser = PyYAMLParser()

    with pytest.raises(ContractParseError) as exc_info:
        parser.load_string("")

    assert "Empty YAML content" in str(exc_info.value)


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_load_string_whitespace_only():
    """Test loading whitespace-only string raises error"""
    parser = PyYAMLParser()

    with pytest.raises(ContractParseError) as exc_info:
        parser.load_string("   \n\t  ")

    assert "Empty YAML content" in str(exc_info.value)


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_load_string_invalid_syntax():
    """Test loading invalid YAML syntax"""
    parser = PyYAMLParser()

    with pytest.raises(ContractParseError) as exc_info:
        parser.load_string(INVALID_YAML_SYNTAX)

    assert "Failed to parse YAML" in str(exc_info.value)


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_load_string_null_result():
    """Test that YAML parsing to None raises error"""
    parser = PyYAMLParser()

    with pytest.raises(ContractParseError) as exc_info:
        parser.load_string(YAML_NULL_ROOT)

    assert "empty (results in None)" in str(exc_info.value)


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_load_string_list_root():
    """Test that YAML with list root raises error"""
    parser = PyYAMLParser()

    with pytest.raises(ContractParseError) as exc_info:
        parser.load_string(YAML_LIST_ROOT)

    assert "must be a mapping" in str(exc_info.value)


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_load_string_string_root():
    """Test that YAML with string root raises error"""
    parser = PyYAMLParser()

    with pytest.raises(ContractParseError) as exc_info:
        parser.load_string(YAML_STRING_ROOT)

    assert "must be a mapping" in str(exc_info.value)


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_load_string_simple_dict():
    """Test loading simple YAML dictionary"""
    parser = PyYAMLParser()
    result = parser.load_string(VALID_YAML_SIMPLE)

    assert result["database_name"] == "test_db"
    assert result["version"] == "1.0"
    assert result["core_slots"] == []


# ================================================================
# PyYAMLParser.load_file 测试
# ================================================================

@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_load_file_valid(tmp_path):
    """Test loading valid YAML file"""
    test_file = tmp_path / "test.yaml"
    test_file.write_text(VALID_YAML, encoding="utf-8")

    parser = PyYAMLParser()
    result = parser.load_file(test_file)

    assert isinstance(result, dict)
    assert "core_slots" in result
    assert result["core_slots"][0]["slot_name"] == "dimension"


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_load_file_not_found():
    """Test loading non-existent file raises error"""
    parser = PyYAMLParser()

    with pytest.raises(ContractParseError) as exc_info:
        parser.load_file("/nonexistent/path/file.yaml")

    assert "File not found" in str(exc_info.value)


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_load_file_with_string_path(tmp_path):
    """Test loading file with string path"""
    test_file = tmp_path / "test.yaml"
    test_file.write_text(VALID_YAML_SIMPLE, encoding="utf-8")

    parser = PyYAMLParser()
    result = parser.load_file(str(test_file))  # Pass string, not Path

    assert result["database_name"] == "test_db"


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_load_file_empty(tmp_path):
    """Test loading empty file raises error"""
    test_file = tmp_path / "empty.yaml"
    test_file.write_text("", encoding="utf-8")

    parser = PyYAMLParser()

    with pytest.raises(ContractParseError) as exc_info:
        parser.load_file(test_file)

    assert "Empty YAML content" in str(exc_info.value)


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_load_file_not_a_directory(tmp_path):
    """Test loading a directory raises error"""
    parser = PyYAMLParser()

    with pytest.raises(ContractParseError) as exc_info:
        parser.load_file(tmp_path)

    assert "Not a file" in str(exc_info.value)


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_load_file_invalid_yaml(tmp_path):
    """Test loading file with invalid YAML"""
    test_file = tmp_path / "invalid.yaml"
    test_file.write_text(INVALID_YAML_SYNTAX, encoding="utf-8")

    parser = PyYAMLParser()

    with pytest.raises(ContractParseError) as exc_info:
        parser.load_file(test_file)

    assert "Failed to parse YAML" in str(exc_info.value)


# ================================================================
# PyYAMLParser.load 智能加载测试
# ================================================================

@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_load_with_yaml_string():
    """Test load() with YAML string content"""
    parser = PyYAMLParser()
    result = parser.load(VALID_YAML_SIMPLE)

    assert result["database_name"] == "test_db"


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_load_with_path_object(tmp_path):
    """Test load() with Path object"""
    test_file = tmp_path / "test.yaml"
    test_file.write_text(VALID_YAML_SIMPLE, encoding="utf-8")

    parser = PyYAMLParser()
    result = parser.load(test_file)

    assert result["database_name"] == "test_db"


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_load_with_path_string(tmp_path):
    """Test load() with path string"""
    test_file = tmp_path / "test.yaml"
    test_file.write_text(VALID_YAML_SIMPLE, encoding="utf-8")

    parser = PyYAMLParser()
    result = parser.load(str(test_file))

    assert result["database_name"] == "test_db"


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_load_with_unsupported_type():
    """Test load() with unsupported type raises error"""
    parser = PyYAMLParser()

    with pytest.raises(ContractParseError) as exc_info:
        parser.load(123)  # type: ignore

    assert "Unsupported source type" in str(exc_info.value)


# ================================================================
# YAMLParser 抽象基类测试
# ================================================================

def test_yaml_parser_is_abc():
    """Test that YAMLParser cannot be instantiated"""
    with pytest.raises(TypeError):
        YAMLParser()


def test_pyyaml_parser_is_yaml_parser():
    """Test that PyYAMLParser is a YAMLParser subclass"""
    assert issubclass(PyYAMLParser, YAMLParser)

    parser = PyYAMLParser()
    assert isinstance(parser, YAMLParser)


# ================================================================
# get_default_parser 测试
# ================================================================

@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_get_default_parser():
    """Test get_default_parser returns PyYAMLParser"""
    parser = get_default_parser()

    assert isinstance(parser, PyYAMLParser)


@pytest.mark.skipif(YAML_AVAILABLE, reason="PyYAML is installed")
def test_get_default_parser_without_pyyaml():
    """Test get_default_parser raises ImportError when PyYAML not available"""
    with pytest.raises(ImportError) as exc_info:
        get_default_parser()

    assert "PyYAML is required" in str(exc_info.value)


# ================================================================
# PyYAML 不可用时的行为测试
# ================================================================

@pytest.mark.skipif(YAML_AVAILABLE, reason="PyYAML is installed")
def test_pyyaml_parser_raises_without_pyyaml():
    """Test PyYAMLParser raises error when PyYAML not installed"""
    parser = PyYAMLParser()

    with pytest.raises(ContractParseError) as exc_info:
        parser.load_string(VALID_YAML)

    assert "PyYAML is not installed" in str(exc_info.value)


# ================================================================
# 路径判断逻辑测试（基于 exists()，无 heuristic）
# ================================================================

@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_load_with_string_yaml_content():
    """Test load() with YAML string content (not a file)"""
    parser = PyYAMLParser()
    result = parser.load("database_name: test\nversion: 1.0")

    assert result["database_name"] == "test"


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_load_with_existing_file(tmp_path):
    """Test load() with existing file path as string"""
    test_file = tmp_path / "test.yaml"
    test_file.write_text(VALID_YAML_SIMPLE, encoding="utf-8")

    parser = PyYAMLParser()
    result = parser.load(str(test_file))

    assert result["database_name"] == "test_db"


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_load_with_nonexistent_path_as_yaml():
    """Test load() with non-existent path is treated as YAML content"""
    parser = PyYAMLParser()
    # 路径不存在，当作 YAML 内容解析
    result = parser.load("a: 1")

    assert result["a"] == 1


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_path_like_object_always_treated_as_file():
    """Test that Path objects are always treated as files"""
    parser = PyYAMLParser()

    # 即使内容看起来像 YAML，Path 对象也当作文件路径
    with pytest.raises(ContractParseError) as exc_info:
        parser.load(Path("a: 1"))

    assert "File not found" in str(exc_info.value)


# ================================================================
# 多文档 YAML 检测测试
# ================================================================

@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_multiple_documents_rejected_by_default():
    """Test that multi-document YAML is rejected by default"""
    multi_doc_yaml = """
---
a: 1
---
b: 2
"""
    parser = PyYAMLParser()

    with pytest.raises(ContractParseError) as exc_info:
        parser.load_string(multi_doc_yaml)

    assert "Multiple YAML documents" in str(exc_info.value)
    assert "not supported" in str(exc_info.value)


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_multiple_documents_allowed_with_config():
    """Test that multi-document YAML is allowed with config"""
    multi_doc_yaml = """
---
a: 1
---
b: 2
"""
    config = ParserConfig(allow_multiple_documents=True)
    parser = PyYAMLParser(config=config)

    result = parser.load_string(multi_doc_yaml)

    # 应该返回第一个文档
    assert result["a"] == 1


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_document_start_marker_at_beginning_is_ok():
    """Test that '---' at document beginning is allowed"""
    yaml_with_marker = """
---
core_slots: []
"""
    parser = PyYAMLParser()
    result = parser.load_string(yaml_with_marker)

    assert "core_slots" in result


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_contains_multiple_documents_detection():
    """Test the _contains_multiple_documents static method"""
    single_doc = "a: 1\nb: 2"
    multi_doc = "---\na: 1\n---\nb: 2"
    doc_with_start_marker = "---\na: 1\nb: 2"

    assert not PyYAMLParser._contains_multiple_documents(single_doc)
    assert PyYAMLParser._contains_multiple_documents(multi_doc)
    assert not PyYAMLParser._contains_multiple_documents(doc_with_start_marker)


# ================================================================
# ParserConfig 测试
# ================================================================

@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_parser_config_default_values():
    """Test ParserConfig default values"""
    config = ParserConfig()

    assert config.allow_multiple_documents is False
    assert config.max_file_size_bytes == 2 * 1024 * 1024  # 2MB


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_parser_config_custom_values():
    """Test ParserConfig with custom values"""
    config = ParserConfig(
        allow_multiple_documents=True,
        max_file_size_bytes=1024 * 1024  # 1MB
    )

    assert config.allow_multiple_documents is True
    assert config.max_file_size_bytes == 1024 * 1024


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_max_file_size_enforcement(tmp_path):
    """Test that max_file_size_bytes is enforced"""
    # 创建一个超过限制的文件
    large_content = "a: " + "x" * 10000  # 约 10KB
    config = ParserConfig(max_file_size_bytes=1024)  # 1KB 限制
    parser = PyYAMLParser(config=config)

    test_file = tmp_path / "large.yaml"
    test_file.write_text(large_content, encoding="utf-8")

    with pytest.raises(ContractParseError) as exc_info:
        parser.load_file(test_file)

    assert "File too large" in str(exc_info.value)


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_max_file_size_unlimited_by_default(tmp_path):
    """Test that files have no size limit by default"""
    large_content = "a: " + "x" * 100000  # 约 100KB
    parser = PyYAMLParser()

    test_file = tmp_path / "large.yaml"
    test_file.write_text(large_content, encoding="utf-8")

    # 应该成功加载
    result = parser.load_file(test_file)
    assert result["a"] is not None


# ================================================================
# get_default_parser with config 测试
# ================================================================

@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_get_default_parser_with_config():
    """Test get_default_parser with custom config"""
    config = ParserConfig(allow_multiple_documents=True)
    parser = get_default_parser(config=config)

    assert isinstance(parser, PyYAMLParser)
    assert parser.config.allow_multiple_documents is True


# ================================================================
# 边界情况测试
# ================================================================

@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_load_with_multiline_yaml():
    """Test loading complex multi-line YAML"""
    complex_yaml = """
core_slots:
  - slot_name: dimension
    description: |
      Multi-line
      description
    type: integer
    scope: COLLECTION
    depends_on: []
"""
    parser = PyYAMLParser()
    result = parser.load_string(complex_yaml)

    assert "Multi-line" in result["core_slots"][0]["description"]


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_load_with_nested_structures():
    """Test loading YAML with nested structures"""
    nested_yaml = """
database_name: test_db
version: "1.0"
metadata:
  author: "Test Author"
  tags:
    - vector
    - search
core_slots: []
"""
    parser = PyYAMLParser()
    result = parser.load_string(nested_yaml)

    assert result["metadata"]["author"] == "Test Author"
    assert result["metadata"]["tags"] == ["vector", "search"]


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_load_preserves_types():
    """Test that YAML types are preserved"""
    typed_yaml = """
integer_value: 42
float_value: 3.14
string_value: "hello"
bool_value: true
null_value: null
list_value: [1, 2, 3]
"""
    parser = PyYAMLParser()
    result = parser.load_string(typed_yaml)

    assert result["integer_value"] == 42
    assert isinstance(result["integer_value"], int)
    assert result["float_value"] == 3.14
    assert isinstance(result["float_value"], float)
    assert result["bool_value"] is True
    assert result["null_value"] is None
    assert result["list_value"] == [1, 2, 3]


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_load_with_comments():
    """Test that comments are ignored during parsing"""
    yaml_with_comments = """
# This is a comment
core_slots:
  - slot_name: dimension  # inline comment
    description: "Vector dimension"
    type: integer
    scope: COLLECTION
    depends_on: []
"""
    parser = PyYAMLParser()
    result = parser.load_string(yaml_with_comments)

    assert "core_slots" in result
    assert result["core_slots"][0]["slot_name"] == "dimension"


# ================================================================
# 错误位置信息测试
# ================================================================

@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_parse_error_includes_location():
    """Test that file parse errors include file location"""
    parser = PyYAMLParser()

    # 字符串解析不包含文件位置（验证使用空 location）
    with pytest.raises(ContractParseError) as exc_info:
        parser.load_string("invalid: [unclosed")

    # 验证是 ContractParseError
    assert isinstance(exc_info.value, ContractParseError)


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_file_error_includes_file_location():
    """Test that file errors include file path in location"""
    parser = PyYAMLParser()

    with pytest.raises(ContractParseError) as exc_info:
        parser.load_file("/nonexistent/file.yaml")

    # 错误消息应包含文件路径
    assert "file.yaml" in str(exc_info.value)


# ================================================================
# 安全性测试（确保使用 safe_load）
# ================================================================

@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
def test_safe_load_prevents_code_execution():
    """Test that safe_load prevents arbitrary code execution"""
    # 尝试加载包含 Python 对象的 YAML
    dangerous_yaml = """
!!python/object/apply:os.system
args: ['echo hello']
"""
    parser = PyYAMLParser()

    # safe_load 应该拒绝这种 YAML
    with pytest.raises(ContractParseError):
        parser.load_string(dangerous_yaml)
