# -*- coding: utf-8 -*-
"""堆叠组件补丁安装器（GUI exe 构建入口，交互参考 BetterNCM 安装器）。

功能：
  1. 自动探测常见的主程序目录，也可手动「浏览」选择
  2. 「安装补丁」：把 overlay 主程序集成补丁注入 ClassWidgets（幂等）
  3. 「还原补丁」：从备份恢复官方原版
  4. 日志区域实时显示操作结果

构建（PyInstaller）：
    python -m PyInstaller --onefile --windowed --name cw2-overlay-installer ^
        --add-data "host_patch;host_patch" build_overlay_installer.py
"""
import os
import sys
from pathlib import Path

# 与插件共用同一份补丁逻辑（PyInstaller 打包时置于 exe 内）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from overlay_integration import install, restore  # noqa: E402

_REL = Path("src") / "qml" / "ClassWidgets" / "Components" / "WidgetsContainer.qml"

# PyInstaller 冻结时资源在 _MEIPASS，源码运行时在脚本所在目录
_RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
_DIALOG_SRC = _RESOURCE_DIR / "host_patch" / "AddOverlayMemberDialog.qml"


def detect_app_dirs():
    """探测候选主程序目录（存在的才返回）。"""
    cands = []
    # exe 所在目录（用户可能把安装器放进主程序目录）
    cands.append(Path(sys.executable).resolve().parent)
    # 常见下载位置
    cands.append(Path.home() / "Downloads" / "ClassWidgets-2-Windows")
    cands.append(Path("F:/class widgets 2 插件"))
    seen = []
    for c in cands:
        if c not in seen and (c / _REL).is_file():
            seen.append(c)
    return seen


def is_app_dir(path: Path) -> bool:
    return bool(path) and (path / _REL).is_file()


def main_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext

    win = tk.Tk()
    win.title("堆叠组件补丁安装器")
    win.geometry("720x480")
    win.minsize(600, 400)

    tk.Label(win, text="ClassWidgets 主程序目录（含 src/qml 的目录）",
             anchor="w").pack(fill="x", padx=12, pady=(12, 4))

    top = tk.Frame(win)
    top.pack(fill="x", padx=12)
    entry = tk.Entry(top)
    entry.pack(side="left", fill="x", expand=True)
    for d in detect_app_dirs():
        entry.insert(0, str(d))
        break

    def browse():
        d = filedialog.askdirectory(title="选择 ClassWidgets 主程序目录")
        if d:
            entry.delete(0, "end")
            entry.insert(0, d)

    tk.Button(top, text="浏览…", command=browse).pack(side="left", padx=(8, 0))

    log = scrolledtext.ScrolledText(win, height=16, state="disabled")
    log.pack(fill="both", expand=True, padx=12, pady=10)

    def write(msg):
        log.configure(state="normal")
        log.insert("end", msg + "\n")
        log.see("end")
        log.configure(state="disabled")

    def do_install():
        app = Path(entry.get().strip())
        if not is_app_dir(app):
            messagebox.showerror("目录无效", "所选目录不是有效的 ClassWidgets 主程序目录。")
            return
        write(f"==> 安装补丁到: {app}")
        ok = install(_GUILogger(write), root=app)
        if ok:
            write("==> 补丁安装完成（幂等，重复安装安全）")
            messagebox.showinfo("完成", "补丁安装完成。重启主程序后生效。")
        else:
            write("==> 补丁安装失败，主程序已保持/还原为官方原版")
            messagebox.showerror("失败", "补丁安装失败，详见日志。")

    def do_restore():
        app = Path(entry.get().strip())
        if not is_app_dir(app):
            messagebox.showerror("目录无效", "所选目录不是有效的 ClassWidgets 主程序目录。")
            return
        write(f"==> 还原主程序: {app}")
        restore(_GUILogger(write), root=app)
        write("==> 还原完成（无备份时不做任何操作）")
        messagebox.showinfo("完成", "主程序已还原为官方原版。")

    btns = tk.Frame(win)
    btns.pack(fill="x", padx=12, pady=(0, 12))
    tk.Button(btns, text="安装补丁", command=do_install,
              width=14).pack(side="left")
    tk.Button(btns, text="还原补丁", command=do_restore,
              width=14).pack(side="left", padx=(8, 0))

    write("堆叠组件补丁安装器 v1.0")
    write("将 overlay 主程序集成补丁（编辑成员组件入口）注入 ClassWidgets。")
    write("检测到候选目录: " + ("；".join(str(d) for d in detect_app_dirs()) or "（无，请手动选择）"))
    win.mainloop()


class _GUILogger:
    """把补丁日志重定向到 GUI 日志区。"""

    def __init__(self, write):
        self._write = write

    def info(self, msg):
        self._write(msg)

    def warning(self, msg):
        self._write("[警告] " + msg)

    def error(self, msg):
        self._write("[错误] " + msg)


if __name__ == "__main__":
    # 支持命令行模式（便于自动化验证）：installer.py --install 目录 / --restore 目录
    if len(sys.argv) >= 3 and sys.argv[1] in ("--install", "--restore"):
        app = Path(sys.argv[2])
        if not is_app_dir(app):
            print(f"目录无效: {app}")
            sys.exit(2)
        if sys.argv[1] == "--install":
            ok = install(_GUILogger(print), root=app)
            print("补丁安装完成" if ok else "补丁安装失败")
            sys.exit(0 if ok else 1)
        restore(_GUILogger(print), root=app)
        print("主程序已还原")
        sys.exit(0)
    main_gui()
