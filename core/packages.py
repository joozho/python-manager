"""包管理：基于目标环境（venv）内的 python -m pip 执行安装/卸载/升级/查询。"""
from .runner import CommandRunner


def list_packages(venv_python, log_callback=None):
    """列出环境中已安装的包。

    返回 [(name, version), ...]，解析失败返回空列表。
    """
    runner = CommandRunner(log_callback)
    code, lines = runner.run([venv_python, "-m", "pip", "list"])
    if code != 0:
        return []
    packages = []
    for line in lines[2:]:  # 跳过两行表头
        parts = line.split()
        if len(parts) >= 2:
            packages.append((parts[0], parts[1]))
    return packages


def install_package(venv_python, requirement, log_callback):
    """安装一个包（支持 pip 全部写法：包名、版本、requirements 文件等）。"""
    runner = CommandRunner(log_callback)
    log_callback(f"[任务] pip install {requirement}")
    return runner.run([venv_python, "-m", "pip", "install", requirement])


def upgrade_package(venv_python, package, log_callback):
    runner = CommandRunner(log_callback)
    log_callback(f"[任务] pip install --upgrade {package}")
    return runner.run([venv_python, "-m", "pip", "install", "--upgrade", package])


def uninstall_package(venv_python, package, log_callback):
    runner = CommandRunner(log_callback)
    log_callback(f"[任务] pip uninstall -y {package}")
    return runner.run([venv_python, "-m", "pip", "uninstall", "-y", package])


def show_package(venv_python, package, log_callback):
    runner = CommandRunner(log_callback)
    return runner.run([venv_python, "-m", "pip", "show", package])
