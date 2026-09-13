"""子进程执行器：负责运行 pip / python / pyenv 等命令，并实时回传输出。"""
import subprocess
import threading

# Windows 下隐藏命令行黑窗（非 Windows 平台忽略）
_NO_WINDOW = 0
if hasattr(subprocess, "CREATE_NO_WINDOW"):
    _NO_WINDOW = subprocess.CREATE_NO_WINDOW


def _decode(raw: bytes) -> str:
    """兼容 UTF-8 / GBK / Latin-1 的字节解码，避免中文乱码。"""
    for enc in ("utf-8", "gbk", "latin-1"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


class CommandRunner:
    """同步/异步执行外部命令，输出逐行回调。"""

    def __init__(self, log_callback=None):
        # log_callback(line: str) 由调用方传入；默认丢弃
        self._log = log_callback or (lambda line: None)

    def run(self, args, cwd=None, timeout=None):
        """同步执行，逐行回调输出。

        返回 (returncode, lines)
        """
        try:
            proc = subprocess.Popen(
                args,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                creationflags=_NO_WINDOW,
            )
        except FileNotFoundError:
            msg = f"[错误] 找不到命令：{args[0]}"
            self._log(msg)
            return 127, [msg]
        except OSError as exc:
            msg = f"[错误] 启动失败：{exc}"
            self._log(msg)
            return 126, [msg]

        lines = []
        for raw in proc.stdout:
            line = _decode(raw).rstrip("\r\n")
            if line:
                lines.append(line)
                self._log(line)
        try:
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            msg = "[错误] 命令执行超时，已终止。"
            self._log(msg)
            lines.append(msg)
            code = -1
        return code, lines

    def run_async(self, args, cwd=None, done_callback=None):
        """异步执行，不阻塞调用线程；done_callback(code) 在结束时回调。"""
        def _target():
            code, _lines = self.run(args, cwd=cwd)
            if done_callback is not None:
                done_callback(code)
        thread = threading.Thread(target=_target, daemon=True)
        thread.start()
        return thread
