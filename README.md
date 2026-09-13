# Python 管理器（基础版）

一个 Windows 桌面小工具，把 **包管理 + 版本管理 + 环境管理** 装进一个界面。
纯标准库实现（Tkinter + subprocess），**零第三方依赖**，无需安装任何库即可运行。

## 功能

| 模块 | 功能 |
| --- | --- |
| 版本管理 | 用 `py -0p` 扫描系统全部 Python 解释器（版本 / 默认标记 / 路径）；检测到 pyenv 或 uv 时支持在线安装新解释器版本 |
| 环境管理 | 在指定根目录下用**指定版本**创建虚拟环境；扫描 / 切换 / 删除环境 |
| 包管理 | 对当前环境执行 pip：安装（支持任意 pip 写法，如 `requests`、`numpy==1.26.4`）、升级、卸载、查看详情、刷新列表 |

所有命令在后台线程执行，日志实时显示在底部，界面不卡顿。

## 启动方式

**三种方式任选：**

1. **双击 `dist\Python管理器.exe`**（已打包好的单文件，无需安装 Python，11MB）
2. **双击 `start.bat`**（需本机装有 Python）
3. 在本目录执行 `python main.py`

> 若启动后无窗口弹出，请在命令行执行 `python main.py` 查看报错；exe 异常时会生成 `error.log`。

## 重新打包 exe

```bat
python -m PyInstaller --noconfirm --clean --onefile --windowed --name "Python管理器" main.py
```

## 使用说明

1. **查看解释器**：启动后自动扫描左侧「Python 解释器」列表，`●` 表示当前默认版本。
2. **创建环境**：在解释器列表中选中一个版本 → 点击「用选中版本创建环境」→ 输入环境名（只能包含字母、数字、下划线、短横线）→ 自动创建在右侧显示的根目录下。
3. **管理包**：点击左侧环境列表中的某个环境 → 右侧自动加载该环境的包列表 → 输入包名安装 / 选中包升级、卸载、查看详情。
4. **更换环境根目录**：点击「浏览…」选择存放虚拟环境的文件夹。

## 安装新 Python 版本（可选）

在线安装新解释器需要 **uv** 或 **pyenv-win** 之一（本工具会自动检测）：

```powershell
# 安装 uv（推荐，一条命令）
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

或安装 [pyenv-win](https://github.com/pyenv-win/pyenv-win) 后，在界面点击「安装新版本…」输入版本号即可。

## 目录结构

```
py-manager/
├── main.py            # 入口：Tkinter 图形界面
├── start.bat          # 双击启动脚本
├── core/
│   ├── runner.py      # 子进程执行器（实时日志、后台线程）
│   ├── interpreters.py# 解释器扫描与在线安装（py -0p / pyenv / uv）
│   ├── environments.py# venv 创建 / 扫描 / 删除
│   └── packages.py    # pip 安装 / 升级 / 卸载 / 查询
└── README.md
```

## 已知限制（基础版）

- 版本「切换」依赖 py launcher 与各解释器本身，本工具提供多版本并列使用（按版本建环境）；如需类似 pyenv 的全局版本切换，请安装 pyenv-win 后使用其命令行。
- 删除环境为物理删除，操作前有二次确认。
- 不支持 conda 环境（后续版本可扩展）。
