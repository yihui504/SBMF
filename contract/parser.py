"""
Contract DSL YAML Parser

提供 YAML 解析抽象和 PyYAML 实现。
职责：安全加载 YAML、错误规范化、返回原始字典。
不做任何 schema/semantic 校验。

边界保证：
- 路径判断基于文件存在性，不做 heuristic
- 拒绝非 mapping 根节点
- 拒绝多文档 YAML
- 仅返回 dict，不做任何 schema 检查
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Union, List
from pathlib import Path

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from contract.errors import ContractParseError, ValidationLocation


# ================================================================
# Parser 配置
# ================================================================

@dataclass
class ParserConfig:
    """解析器配置

    控制解析行为的可选配置项。

    Attributes:
        allow_multiple_documents: 是否允许多文档 YAML（默认 False）
        max_file_size_bytes: 最大允许的文件大小（字节），默认 2MB
    """
    allow_multiple_documents: bool = False
    max_file_size_bytes: int = 2 * 1024 * 1024  # 默认 2MB


# ================================================================
# YAML Parser 抽象基类
# ================================================================

class YAMLParser(ABC):
    """YAML 解析器抽象基类

    定义 YAML 解析接口，隔离具体 YAML 库实现。

    职责：
    - 从文件或字符串加载 YAML
    - 返回解析后的字典结构
    - 将解析错误统一转换为 ContractParseError

    不负责：
    - Schema 验证（由 ContractSchemaValidator 负责）
    - 语义验证（由 SemanticValidator 负责）
    - 任何字段存在性检查
    - 任何 enum 值验证
    """

    @abstractmethod
    def load(self, source: Union[str, Path]) -> Dict[str, Any]:
        """加载 YAML 并返回字典

        Args:
            source: YAML 文件路径或 YAML 字符串内容

        Returns:
            Dict[str, Any]: 解析后的字典，必须包含顶层结构

        Raises:
            ContractParseError: YAML 解析失败或内容无效

        路径判断规则（确定性）：
        1. 如果是 Path 对象 → 当作文件路径
        2. 如果是字符串且文件存在 → 当作文件路径
        3. 否则 → 当作 YAML 字符串内容

        不使用任何 heuristic（如包含路径分隔符、扩展名等）。
        """
        pass

    @abstractmethod
    def load_string(self, content: str) -> Dict[str, Any]:
        """从字符串加载 YAML

        Args:
            content: YAML 字符串内容

        Returns:
            Dict[str, Any]: 解析后的字典

        Raises:
            ContractParseError: 解析失败或内容无效

        验证规则：
        - 空字符串 → ContractParseError
        - None 结果 → ContractParseError
        - 非 dict 根节点 → ContractParseError
        - 多文档 YAML → ContractParseError（除非配置允许）
        """
        pass

    @abstractmethod
    def load_file(self, path: Union[str, Path]) -> Dict[str, Any]:
        """从文件加载 YAML

        Args:
            path: YAML 文件路径

        Returns:
            Dict[str, Any]: 解析后的字典

        Raises:
            ContractParseError: 文件读取或解析失败
        """
        pass


# ================================================================
# PyYAML 实现
# ================================================================

class PyYAMLParser(YAMLParser):
    """PyYAML 解析器实现

    使用 PyYAML 的 safe_load 安全加载 YAML 内容。

    错误处理策略：
    - 捕获 yaml.YAMLError 并转换为 ContractParseError
    - 空文件 → ContractParseError
    - None 结果 → ContractParseError
    - 非 dict 结果 → ContractParseError
    - 多文档 YAML → ContractParseError（默认）

    路径判断策略：
    - 使用 Path.exists() 判断，不做 heuristic
    - 字符串 "a: 1" 如果不是文件路径，当作 YAML 内容
    """

    def __init__(self, config: Union[ParserConfig, None] = None):
        """初始化解析器

        Args:
            config: 解析器配置（可选），默认使用严格配置
        """
        self.config = config or ParserConfig()

    def load(self, source: Union[str, Path]) -> Dict[str, Any]:
        """智能加载：基于文件存在性判断

        判断规则（确定性，无 heuristic）：
        1. 如果是 Path 对象 → load_file
        2. 如果是字符串且 Path(source).exists() → load_file
           - 如果 Path(source).exists() 抛出 OSError（无效文件名）→ load_string
        3. 否则 → load_string

        Args:
            source: 文件路径或 YAML 字符串

        Returns:
            Dict[str, Any]: 解析后的字典

        Raises:
            ContractParseError: 解析失败
        """
        # 规则 1: Path 对象 → 当作文件
        if isinstance(source, Path):
            return self.load_file(source)

        # 规则 2: 字符串且文件存在 → 当作文件
        if isinstance(source, str):
            source_path = Path(source)
            try:
                if source_path.exists():
                    return self.load_file(source_path)
            except OSError:
                # 路径包含无效字符（如换行符、特殊字符等）
                # 这不是有效的文件路径，当作 YAML 内容处理
                pass
            # 文件不存在或无效路径 → 当作 YAML 字符串
            return self.load_string(source)

        # 不支持的类型
        raise ContractParseError(
            f"Unsupported source type: {type(source).__name__}",
            location=ValidationLocation()
        )

    def load_string(self, content: str) -> Dict[str, Any]:
        """从字符串加载 YAML

        Args:
            content: YAML 字符串内容

        Returns:
            Dict[str, Any]: 解析后的字典

        Raises:
            ContractParseError: 解析失败或内容无效
        """
        if not YAML_AVAILABLE:
            raise ContractParseError(
                "PyYAML is not installed. Install with: pip install PyYAML",
                location=ValidationLocation()
            )

        # 验证 1: 空内容检查
        if not content or content.strip() == "":
            raise ContractParseError(
                "Empty YAML content",
                location=ValidationLocation()
            )

        try:
            # 验证 2: 多文档检测
            if self._contains_multiple_documents(content):
                if not self.config.allow_multiple_documents:
                    raise ContractParseError(
                        "Multiple YAML documents detected (separated by '---'). "
                        "This is not supported for Contract DSL. "
                        "Use a single document.",
                        location=ValidationLocation()
                    )
                # 如果允许多文档，使用 safe_load_all
                docs = list(yaml.safe_load_all(content))
                if not docs or docs[0] is None:
                    raise ContractParseError(
                        "YAML content is empty (no valid documents)",
                        location=ValidationLocation()
                    )
                result = docs[0]
            else:
                # 单文档，使用 safe_load
                result = yaml.safe_load(content)

            # 验证 3: None 结果检查
            if result is None:
                raise ContractParseError(
                    "YAML content is empty (results in None)",
                    location=ValidationLocation()
                )

            # 验证 4: 根节点必须是 dict
            if not isinstance(result, dict):
                raise ContractParseError(
                    f"YAML root must be a mapping/dict, got {type(result).__name__}",
                    location=ValidationLocation()
                )

            return result

        except yaml.YAMLError as e:
            # 包装 YAML 解析错误
            raise ContractParseError(
                f"Failed to parse YAML: {str(e)}",
                location=ValidationLocation()
            ) from e
        except ContractParseError:
            # 重新抛出（不包装）
            raise

    def load_file(self, path: Union[str, Path]) -> Dict[str, Any]:
        """从文件加载 YAML

        Args:
            path: YAML 文件路径

        Returns:
            Dict[str, Any]: 解析后的字典

        Raises:
            ContractParseError: 文件读取或解析失败
        """
        if not YAML_AVAILABLE:
            raise ContractParseError(
                "PyYAML is not installed. Install with: pip install PyYAML",
                location=ValidationLocation()
            )

        # 转换为 Path 对象
        path = Path(path)

        # 检查文件存在性
        if not path.exists():
            raise ContractParseError(
                f"File not found: {path}",
                location=ValidationLocation(field_path=f"file:{path}")
            )

        if not path.is_file():
            raise ContractParseError(
                f"Not a file: {path}",
                location=ValidationLocation(field_path=f"file:{path}")
            )

        # 检查文件大小（如果配置了限制）
        if self.config.max_file_size_bytes is not None:
            file_size = path.stat().st_size
            if file_size > self.config.max_file_size_bytes:
                raise ContractParseError(
                    f"File too large: {file_size} bytes (max: {self.config.max_file_size_bytes})",
                    location=ValidationLocation(field_path=f"file:{path}")
                )

        try:
            # 读取文件内容
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # 复用 load_string
            return self.load_string(content)

        except IOError as e:
            raise ContractParseError(
                f"Failed to read file {path}: {str(e)}",
                location=ValidationLocation(field_path=f"file:{path}")
            ) from e
        except ContractParseError:
            # 重新抛出 ContractParseError（不包装）
            raise
        except Exception as e:
            # 捕获其他意外错误
            raise ContractParseError(
                f"Unexpected error loading file {path}: {str(e)}",
                location=ValidationLocation(field_path=f"file:{path}")
            ) from e

    @staticmethod
    def _contains_multiple_documents(content: str) -> bool:
        """检测 YAML 内容是否包含多个文档

        Args:
            content: YAML 字符串内容

        Returns:
            bool: 如果包含多个文档分隔符 '---' 返回 True

        注意：
        - 忽略文档开头的 '---'（第一个文档可能以 '---' 开头）
        - 检测后续的 '---' 分隔符
        """
        lines = content.split("\n")

        # 移除开头的空行
        first_non_empty = 0
        for i, line in enumerate(lines):
            if line.strip():
                first_non_empty = i
                break

        # 检查是否有非开头的 '---'
        # 跳过文档开头的 '---'（如果有）
        start_index = first_non_empty
        if start_index < len(lines) and lines[start_index].strip() == "---":
            start_index += 1

        # 检查后续是否有 '---'
        for i in range(start_index, len(lines)):
            line = lines[i].strip()
            if line == "---":
                return True

        return False


# ================================================================
# 默认解析器实例
# ================================================================

def get_default_parser(config: Union[ParserConfig, None] = None) -> YAMLParser:
    """获取默认的 YAML 解析器

    Args:
        config: 可选的解析器配置

    Returns:
        YAMLParser: PyYAMLParser 实例

    Raises:
        ImportError: PyYAML 未安装
    """
    if not YAML_AVAILABLE:
        raise ImportError(
            "PyYAML is required for YAML parsing. "
            "Install with: pip install PyYAML"
        )
    return PyYAMLParser(config=config)
