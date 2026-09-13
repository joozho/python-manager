"""Python 管理器（基础版）—— 包管理 + 版本管理 + 环境管理 合一桌面工具。

纯标准库实现（Tkinter + subprocess），无任何第三方依赖。
运行方式：双击 start.bat / Python管理器.exe，或在此目录执行 python main.py
"""
import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog, ttk

from core import environments, interpreters, packages

APP_TITLE = "Python 管理器（基础版）"
ENV_ROOT_NAME = "venvs"  # 默认环境根目录名

# 基准目录：打包成 exe 后以 exe 所在目录为准，源码运行时以项目目录为准
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class PyManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1100x720")
        self.root.minsize(900, 560)

        # 状态
        self.env_root = os.path.join(BASE_DIR, ENV_ROOT_NAME)
        os.makedirs(self.env_root, exist_ok=True)
        self.current_env = None       # 当前选中环境 {name, path, python, version}
        self._busy = False            # 是否有后台任务在跑

        self._build_ui()
        self._log("就绪。正在扫描 Python 解释器和环境…")
        self.refresh_all()

    # ================= 界面构建 =================
    def _build_ui(self):
        # 顶栏
        top = ttk.Frame(self.root, padding=(8, 6))
        top.pack(fill="x")
        ttk.Label(top, text=APP_TITLE, font=("Microsoft YaHei UI", 13, "bold")).pack(side="left")
        ttk.Button(top, text="刷新全部", command=self.refresh_all).pack(side="right")

        # 中部：左右分栏
        middle = ttk.PanedWindow(self.root, orient="horizontal")
        middle.pack(fill="both", expand=True, padx=8)

        # -------- 左栏：解释器 + 环境 --------
        left = ttk.Frame(middle)
        middle.add(left, weight=1)

        # 解释器区
        interp_frame = ttk.LabelFrame(left, text="Python 解释器（版本管理）", padding=6)
        interp_frame.pack(fill="both", expand=False, pady=(0, 6))
        self.interp_tree = ttk.Treeview(
            interp_frame, columns=("version", "default", "path"),
            show="headings", height=5,
        )
        self.interp_tree.heading("version", text="版本")
        self.interp_tree.heading("default", text="默认")
        self.interp_tree.heading("path", text="路径")
        self.interp_tree.column("version", width=110, anchor="center")
        self.interp_tree.column("default", width=40, anchor="center")
        self.interp_tree.column("path", width=300)
        self.interp_tree.pack(fill="both", expand=True)
        ibar = ttk.Frame(interp_frame)
        ibar.pack(fill="x", pady=(4, 0))
        ttk.Button(ibar, text="用选中版本创建环境", command=self.create_env).pack(side="left")
        ttk.Button(ibar, text="安装新版本…", command=self.install_new_version).pack(side="left", padx=(6, 0))

        # 环境区
        env_frame = ttk.LabelFrame(left, text="虚拟环境（环境管理）", padding=6)
        env_frame.pack(fill="both", expand=True)
        rootbar = ttk.Frame(env_frame)
        rootbar.pack(fill="x")
        ttk.Label(rootbar, text="根目录：").pack(side="left")
        self.env_root_label = ttk.Label(rootbar, text=self.env_root, foreground="#1a5fb4")
        self.env_root_label.pack(side="left", fill="x", expand=True)
        ttk.Button(rootbar, text="浏览…", command=self.choose_env_root).pack(side="left")
        self.env_tree = ttk.Treeview(
            env_frame, columns=("name", "version"),
            show="headings", height=8,
        )
        self.env_tree.heading("name", text="环境名称")
        self.env_tree.heading("version", text="Python")
        self.env_tree.column("name", width=150)
        self.env_tree.column("version", width=80, anchor="center")
        self.env_tree.pack(fill="both", expand=True, pady=(4, 4))
        self.env_tree.bind("<<TreeviewSelect>>", self._on_env_select)
        ebar = ttk.Frame(env_frame)
        ebar.pack(fill="x")
        ttk.Button(ebar, text="新建环境…", command=self.create_env).pack(side="left")
        ttk.Button(ebar, text="删除环境", command=self.delete_env).pack(side="left", padx=(6, 0))
        ttk.Button(ebar, text="刷新", command=self.refresh_envs).pack(side="left", padx=(6, 0))

        # -------- 右栏：包管理 --------
        right = ttk.Frame(middle)
        middle.add(right, weight=2)

        pkg_frame = ttk.LabelFrame(right, text="包管理（pip）", padding=6)
        pkg_frame.pack(fill="both", expand=True)
        self.env_info = ttk.Label(pkg_frame, text="未选择环境", foreground="#666666")
        self.env_info.pack(fill="x", anchor="w")
        self.pkg_tree = ttk.Treeview(
            pkg_frame, columns=("name", "version"),
            show="headings", height=14,
        )
        self.pkg_tree.heading("name", text="包名")
        self.pkg_tree.heading("version", text="版本")
        self.pkg_tree.column("name", width=260)
        self.pkg_tree.column("version", width=120, anchor="center")
        self.pkg_tree.pack(fill="both", expand=True, pady=(4, 4))

        install_bar = ttk.Frame(pkg_frame)
        install_bar.pack(fill="x")
        ttk.Label(install_bar, text="包名 / 要求：").pack(side="left")
        self.pkg_entry = ttk.Entry(install_bar)
        self.pkg_entry.pack(side="left", fill="x", expand=True, padx=4)
        self.pkg_entry.bind("<Return>", lambda e: self.install_pkg())
        ttk.Button(install_bar, text="安装", command=self.install_pkg).pack(side="left")

        op_bar = ttk.Frame(pkg_frame)
        op_bar.pack(fill="x", pady=(4, 0))
        ttk.Button(op_bar, text="升级选中", command=self.upgrade_pkg).pack(side="left")
        ttk.Button(op_bar, text="卸载选中", command=self.uninstall_pkg).pack(side="left", padx=(6, 0))
        ttk.Button(op_bar, text="查看详情", command=self.show_pkg).pack(side="left", padx=(6, 0))
        ttk.Button(op_bar, text="刷新包列表", command=self.refresh_packages).pack(side="right")

        # -------- 底部：日志 --------
        log_frame = ttk.LabelFrame(self.root, text="执行日志", padding=6)
        log_frame.pack(fill="x", padx=8, pady=(0, 8))
        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=9, state="disabled", font=("Consolas", 9),
        )
        self.log_text.pack(fill="x")

    # ================= 日志 =================
    def _log(self, msg):
        """线程安全地追加一行日志。"""
        self.root.after(0, self._append_log, str(msg))

    def _append_log(self, msg):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    # ================= 任务调度 =================
    def _run_task(self, worker, on_done=None):
        """在后台线程执行任务，避免卡界面；同一时间只允许一个任务。"""
        if self._busy:
            self._log("[提示] 有任务正在执行，请稍候…")
            return
        self._busy = True
        self.root.configure(cursor="watch")

        def _wrap():
            try:
                worker()
            except Exception as exc:  # noqa: BLE001 —— 后台异常必须落日志
                self._log(f"[异常] {type(exc).__name__}: {exc}")
            finally:
                self._busy = False
                self.root.after(0, self._unbusy, on_done)

        threading.Thread(target=_wrap, daemon=True).start()

    def _unbusy(self, on_done):
        self.root.configure(cursor="")
        if on_done:
            on_done()

    # ================= 刷新 =================
    def refresh_all(self):
        self.refresh_interpreters()
        self.refresh_envs()

    def refresh_interpreters(self):
        def worker():
            self._log("[任务] 扫描 Python 解释器…")
            items = interpreters.list_interpreters()
            self.root.after(0, self._fill_interp_tree, items)

        self._run_task(worker)

    def _fill_interp_tree(self, items):
        self.interp_tree.delete(*self.interp_tree.get_children())
        for item in items:
            self.interp_tree.insert(
                "", "end", iid=item["path"],
                values=(item["version"], "●" if item["default"] else "", item["path"]),
            )
        self._log(f"[完成] 检测到 {len(items)} 个 Python 解释器")

    def refresh_envs(self):
        def worker():
            self._log(f"[任务] 扫描环境根目录：{self.env_root}")
            envs = environments.scan_environments(self.env_root)
            self.root.after(0, self._fill_env_tree, envs)

        self._run_task(worker)

    def _fill_env_tree(self, envs):
        self.env_tree.delete(*self.env_tree.get_children())
        for env in envs:
            self.env_tree.insert(
                "", "end", iid=env["path"], values=(env["name"], env["version"])
            )
        self._log(f"[完成] 找到 {len(envs)} 个虚拟环境")
        # 若之前选中过环境，尽量恢复选中
        if self.current_env and os.path.isdir(self.current_env["path"]):
            self._select_env(self.current_env["path"])

    # ================= 环境操作 =================
    def choose_env_root(self):
        chosen = tk.filedialog.askdirectory(title="选择环境根目录", initialdir=self.env_root)
        if not chosen:
            return
        self.env_root = chosen
        self.env_root_label.configure(text=chosen)
        self.refresh_envs()

    def _selected_interpreter(self):
        sel = self.interp_tree.selection()
        return sel[0] if sel else None

    def create_env(self):
        """用选中解释器（或默认解释器）创建虚拟环境。"""
        interp = self._selected_interpreter() or interpreters.default_interpreter()
        if not interp:
            messagebox.showwarning(APP_TITLE, "未找到任何 Python 解释器。")
            return
        name = simpledialog.askstring(
            "新建环境", f"环境名称（将创建于\n{self.env_root}\n下）："
        )
        if not name or not name.strip():
            return
        name = name.strip()
        if not name.replace("_", "").replace("-", "").isalnum():
            messagebox.showwarning(APP_TITLE, "环境名只能包含字母、数字、下划线和短横线。")
            return
        env_dir = os.path.join(self.env_root, name)

        def worker():
            code, _ = environments.create_venv(interp, env_dir, self._log)
            self._log(f"[{'完成' if code == 0 else '失败'}] 创建环境：{name}")

        self._run_task(worker, on_done=self.refresh_envs)

    def delete_env(self):
        sel = self.env_tree.selection()
        if not sel:
            messagebox.showinfo(APP_TITLE, "请先在环境列表中选中一个环境。")
            return
        env_dir = sel[0]
        name = os.path.basename(env_dir)
        if not messagebox.askyesno(
            APP_TITLE, f"确定要删除环境「{name}」吗？\n{env_dir}\n\n此操作不可恢复！"
        ):
            return
        if self.current_env and self.current_env["path"] == env_dir:
            self.current_env = None

        def worker():
            ok = environments.remove_env(env_dir, self._log)
            if ok:
                self._log(f"[完成] 已删除环境：{name}")

        self._run_task(worker, on_done=self.refresh_envs)

    def _on_env_select(self, _event):
        sel = self.env_tree.selection()
        if sel:
            self._select_env(sel[0])

    def _select_env(self, env_dir):
        py = environments.venv_python(env_dir)
        if not py:
            self.current_env = None
            return
        self.current_env = {"path": env_dir, "python": py, "name": os.path.basename(env_dir)}
        self.env_info.configure(text=f"当前环境：{env_dir}")
        self.refresh_packages()

    # ================= 包操作 =================
    def refresh_packages(self):
        if not self.current_env:
            self.pkg_tree.delete(*self.pkg_tree.get_children())
            return

        def worker():
            self._log(f"[任务] 读取包列表：{self.current_env['name']}")
            pkgs = packages.list_packages(self.current_env["python"], self._log)
            self.root.after(0, self._fill_pkg_tree, pkgs)

        self._run_task(worker)

    def _fill_pkg_tree(self, pkgs):
        self.pkg_tree.delete(*self.pkg_tree.get_children())
        for name, ver in pkgs:
            self.pkg_tree.insert("", "end", iid=name, values=(name, ver))
        self._log(f"[完成] 共 {len(pkgs)} 个已安装包")

    def _require_env(self):
        if not self.current_env:
            messagebox.showinfo(APP_TITLE, "请先在左侧选择一个虚拟环境。")
            return False
        return True

    def _selected_pkg(self):
        sel = self.pkg_tree.selection()
        return sel[0] if sel else None

    def install_pkg(self):
        if not self._require_env():
            return
        req = self.pkg_entry.get().strip()
        if not req:
            messagebox.showinfo(APP_TITLE, "请先输入要安装的包名（如 requests、numpy==1.26.4）。")
            return
        self.pkg_entry.delete(0, "end")

        def worker():
            packages.install_package(self.current_env["python"], req, self._log)

        self._run_task(worker, on_done=self.refresh_packages)

    def upgrade_pkg(self):
        if not self._require_env():
            return
        pkg = self._selected_pkg()
        if not pkg:
            messagebox.showinfo(APP_TITLE, "请先在包列表中选中一个包。")
            return

        def worker():
            packages.upgrade_package(self.current_env["python"], pkg, self._log)

        self._run_task(worker, on_done=self.refresh_packages)

    def uninstall_pkg(self):
        if not self._require_env():
            return
        pkg = self._selected_pkg()
        if not pkg:
            messagebox.showinfo(APP_TITLE, "请先在包列表中选中一个包。")
            return
        if not messagebox.askyesno(APP_TITLE, f"确定卸载包「{pkg}」吗？"):
            return

        def worker():
            packages.uninstall_package(self.current_env["python"], pkg, self._log)

        self._run_task(worker, on_done=self.refresh_packages)

    def show_pkg(self):
        if not self._require_env():
            return
        pkg = self._selected_pkg()
        if not pkg:
            messagebox.showinfo(APP_TITLE, "请先在包列表中选中一个包。")
            return

        def worker():
            packages.show_package(self.current_env["python"], pkg, self._log)

        self._run_task(worker)

    # ================= 版本管理 =================
    def install_new_version(self):
        tool = interpreters.find_installer()
        if tool is None:
            messagebox.showinfo(
                APP_TITLE,
                "未检测到 pyenv 或 uv，无法在线安装新版本。\n\n"
                "建议：\n"
                "1. 安装 uv（一条命令）：\n   powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\"\n"
                "2. 或安装 pyenv-win：\n   https://github.com/pyenv-win/pyenv-win\n\n"
                "安装后重启本工具即可使用「安装新版本」。",
            )
            return
        version = simpledialog.askstring(
            "安装新解释器",
            f"检测到 {tool[0]}，请输入要安装的版本号（如 3.12 或 3.12.4）：",
        )
        if not version or not version.strip():
            return
        version = version.strip()
        if not messagebox.askyesno(
            APP_TITLE, f"将使用 {tool[0]} 安装 Python {version}，需要联网，可能耗时较长。继续？"
        ):
            return

        def worker():
            interpreters.install_version(version, self._log)

        self._run_task(worker, on_done=self.refresh_interpreters)


def main():
    # 兜底：任何未捕获异常都写入 error.log，便于 pythonw 静默启动时排查
    try:
        root = tk.Tk()
        PyManagerApp(root)
        root.mainloop()
    except Exception:
        import traceback
        log_path = os.path.join(BASE_DIR, "error.log")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
