"""环境管理：虚拟环境（venv）的创建、扫描与识别。"""
import os
import shutil

from .runner import CommandRunner


def venv_python(env_dir):
    """返回 venv 内 python 可执行文件的路径；不是合法 venv 返回 None。"""
    if not env_dir or not os.path.isdir(env_dir):
        return None
    exe = "python.exe" if os.name == "nt" else "python"
    for sub in ("Scripts", "bin"):
        candidate = os.path.join(env_dir, sub, exe)
        if os.path.isfile(candidate):
            return candidate
    return None


def scan_environments(root_dir):
    """扫描根目录下的一级子目录，找出其中的 venv。

    返回 [{name, path, python, version}]，version 为空串表示未能读取。
    """
    found = []
    if not root_dir or not os.path.isdir(root_dir):
        return found
    for name in sorted(os.listdir(root_dir)):
        env_dir = os.path.join(root_dir, name)
        py = venv_python(env_dir)
        if not py:
            continue
        version = _python_version(py)
        found.append(
            {"name": name, "path": env_dir, "python": py, "version": version}
        )
    return found


def create_venv(interpreter_path, env_dir, log_callback):
    """用指定解释器创建 venv。返回 (returncode, lines)。"""
    if os.path.exists(env_dir):
        log_callback(f"[错误] 目标目录已存在：{env_dir}")
        return 1, ["目标目录已存在"]
    runner = CommandRunner(log_callback)
    log_callback(f"[任务] 用 {interpreter_path} 创建环境：{env_dir}")
    return runner.run([interpreter_path, "-m", "venv", env_dir])


def remove_env(env_dir, log_callback):
    """删除一个虚拟环境目录。返回是否成功。"""
    try:
        shutil.rmtree(env_dir)
        log_callback(f"[任务] 已删除环境：{env_dir}")
        return True
    except OSError as exc:
        log_callback(f"[错误] 删除失败：{exc}")
        return False


def _python_version(py_path):
    runner = CommandRunner()
    _code, lines = runner.run([py_path, "--version"])
    return lines[0].replace("Python ", "") if lines else ""
