# -*- coding: utf-8 -*-
"""堆叠组件主程序集成补丁 - 命令行手动注入工具。

在插件无法自动为主程序注入补丁时使用（详见 README「手动注入工具」）。

用法：
    python cw2_overlay_injector.py status   --app 主程序目录
    python cw2_overlay_injector.py install  --app 主程序目录
    python cw2_overlay_injector.py restore  --app 主程序目录
"""
import argparse
import sys
from pathlib import Path

# 与插件共用同一份补丁逻辑（本仓库 overlay_integration.py）
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from overlay_integration import install, restore, find_app_root  # noqa: E402

_REL = Path("src") / "qml" / "ClassWidgets" / "Components" / "WidgetsContainer.qml"
_MARKER = "overlayEditMode"


class _Logger:
    def info(self, msg):
        print(msg)

    def warning(self, msg):
        print("[警告]", msg)

    def error(self, msg):
        print("[错误]", msg)


def _status(app: Path) -> int:
    root = app or find_app_root()
    if not root:
        print("未找到主程序目录（请用 --app 指定）")
        return 2
    root = Path(root)
    container = root / _REL
    if not container.is_file():
        print(f"目录不是有效的 ClassWidgets 主程序: {root}")
        return 2
    text = container.read_text(encoding="utf-8", errors="replace")
    backup = root / ".cwplugin_backups" / "overlay"
    state = "已安装" if _MARKER in text else "未安装"
    backup_state = "有备份（可还原）" if backup.is_dir() else "无备份"
    print(f"主程序目录 : {root}")
    print(f"补丁状态   : {state}")
    print(f"备份状态   : {backup_state}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="堆叠组件主程序集成补丁 - 手动注入工具")
    ap.add_argument("action", choices=["status", "install", "restore"],
                    help="操作：查看状态 / 安装补丁 / 还原补丁")
    ap.add_argument("--app", default=None,
                    help="主程序根目录（缺省时自动探测）")
    args = ap.parse_args(argv)

    logger = _Logger()
    app = Path(args.app) if args.app else None
    if args.action == "status":
        return _status(app)
    if args.action == "install":
        ok = install(logger, root=app)
        print("补丁安装完成" if ok else "补丁安装失败")
        return 0 if ok else 1
    ok = restore(logger, root=app)
    print("主程序已还原" if ok else "还原完成（无备份或已还原）")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
