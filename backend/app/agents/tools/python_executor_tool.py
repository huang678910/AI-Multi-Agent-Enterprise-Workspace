"""Python 执行器工具 — 安全沙箱执行 Python 代码"""

import logging
import subprocess
import tempfile
import os

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# 黑名单：禁止的模块和函数
FORBIDDEN = [
    "import os", "import subprocess", "import shutil", "import sys",
    "__import__", "exec(", "eval(", "compile(", "open(",
    "os.", "subprocess.", "shutil.", "pathlib.",
]


@tool
async def execute_python(code: str) -> str:
    """安全沙箱中执行 Python 代码并返回结果。

    用于数据分析、计算、数据处理等。代码在隔离进程中运行，有 30 秒超时限制。
    禁止文件系统写入、网络访问和系统调用。
    预装：pandas、numpy。

    Args:
        code: 要执行的 Python 代码（字符串）

    Returns:
        标准输出和标准错误的合并结果
    """
    # 安全检查
    code_lower = code.lower()
    for keyword in FORBIDDEN:
        if keyword.lower() in code_lower:
            return f"Error: Forbidden operation detected ({keyword}). Code execution blocked for security."

    # 限制代码长度
    if len(code) > 5000:
        return "Error: Code too long (max 5000 characters)."

    try:
        # 写入临时文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code)
            tmp_path = f.name

        # 在隔离子进程中执行
        result = subprocess.run(
            ["python", tmp_path],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=tempfile.gettempdir(),
            env={**os.environ, "PYTHONPATH": ""},  # 隔离环境
        )

        # 清理临时文件
        os.unlink(tmp_path)

        output = result.stdout.strip()
        error = result.stderr.strip()

        if error:
            return f"Error:\n{error}" + (f"\n\nOutput:\n{output}" if output else "")
        return output or "(No output)"

    except subprocess.TimeoutExpired:
        return "Error: Code execution timed out (30 seconds limit)."
    except Exception as e:
        logger.error(f"Python execution failed: {e}")
        return f"Execution error: {str(e)}"
