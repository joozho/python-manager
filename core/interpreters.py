"""解释器管理：扫描系统已安装的 Python 版本，并提供多版本安装能力。

优先使用 Windows py launcher（py -0p）列出所有解释器；
若没有 py，则回退到 PATH 中的 python。
在线安装新版本：优先检测 pyenv-win，其次检测 uv。
"""
import os
import re
import shutil
import subprocess

from .runner import CommandRunner, _decode


def list_interpreters():
    """返回解释器列表：[{version, path, default}]，按版本号排序。"""
    result = []
    try:
        proc = subprocess.run(
            ["py", "-0p"],
            capture_output=True,
            timeout=20,
        )
        for line in _decode(proc.stdout).splitlines():
            m = re.match(r"\s*-V:(\S+)\s+(\*)?\s*(.+)", line)
            if not m:
                continue
            version = m.group(1)
            default = bool(m.group(2))
            path = m.group(3).strip()
            if path and os.path.isfile(path):
                result.append({"version": version, "path": path, "default": default})
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        pass

    if not result:
        # 回退：PATH 中的 python
        py = shutil.which("python")
        if py:
            ver_text = _run_version([py])
            result.append(
                {"version": ver_text, "path": py, "default": True}
            )
    # 排序：默认版在前，其余按版本号
    def _sort_key(item):
        m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", item["version"])
        if m:
            nums = tuple(int(g) if g else 0 for g in m.groups())
        else:
            nums = (0, 0, 0)
        return (not item["default"], -nums[0], -nums[1], -nums[2])
    result.sort(key=_sort_key)
    return result


def _run_version(py_path):
    try:
        proc = subprocess.run([py_path, "--version"], capture_output=True, timeout=15)
        text = _decode(proc.stdout + proc.stderr).strip()
        return text.replace("Python ", "") or "?"
    except (OSError, subprocess.SubprocessError):
        return "?"


def default_interpreter():
    """返回默认解释器路径；找不到返回 None。"""
    for item in list_interpreters():
        if item["default"]:
            return item["path"]
    return None


def find_installer():
    """探测可用的在线安装器：优先 pyenv，其次 uv。

    返回 (tool_name, base_args) 或 None。
    """
    pyenv = shutil.which("pyenv")
    if pyenv:
        return "pyenv", [pyenv, "install"]
    uv = shutil.which("uv")
    if uv:
        return "uv", [uv, "python", "install"]
    return None


def install_version(version, log_callback):
    """调用 pyenv/uv 安装指定版本的解释器。

    version 形如 "3.12" 或 "3.12.4"。
    返回 (returncode, lines)。
    """
    runner = CommandRunner(log_callback)
    tool = find_installer()
    if tool is None:
        msg = (
            "[提示] 未检测到 pyenv 或 uv，无法在线安装新版本。\n"
            "      请安装 pyenv-win（https://github.com/pyenv-win/pyenv-win）"
            " 或 uv（https://docs.astral.sh/uv/）后重试。"
        )
        log_callback(msg)
        return 127, [msg]
    tool_name, base = tool
    log_callback(f"[任务] 使用 {tool_name} 安装 Python {version} …")
    return runner.run(base + [version])
