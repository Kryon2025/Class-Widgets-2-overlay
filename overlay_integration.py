# -*- coding: utf-8 -*-
"""主程序集成模块（堆叠插件自带）。

安装/加载插件时给主程序 QML 打补丁，恢复"编辑成员组件"入口：
  - 右键堆叠组件菜单新增"编辑成员组件"
  - 进入后成员组件纵向排列（overlay.qml 列表模式），组件下方出现
    Add Member / Done 编辑行
卸载/禁用插件时从备份还原主程序，不留任何痕迹。

补丁在插件 on_load 阶段执行（先于主程序 QML 引擎加载），因此
本次启动即生效，无需重启；主程序被更新覆盖后，on_load 检测到
补丁缺失会自动重新安装。
"""
import shutil
from pathlib import Path

# 主程序关键文件（相对主程序根目录）
_CONTAINER_REL = Path("src") / "qml" / "ClassWidgets" / "Components" / "WidgetsContainer.qml"
_WLOADER_REL = Path("src") / "qml" / "ClassWidgets" / "Components" / "WidgetLoader.qml"
_DIALOG_REL = Path("src") / "qml" / "ClassWidgets" / "Components" / "dialogs" / "AddOverlayMemberDialog.qml"
_BACKUP_ROOT = ".cwplugin_backups"
_BACKUP_SUB = "overlay"
_MARKER = "overlayEditMode"  # 补丁已安装的特征串
# 对话框资源（打包在插件内），官方主程序没有此文件，安装补丁时复制过去
_DIALOG_SRC = Path(__file__).resolve().parent / "host_patch" / "AddOverlayMemberDialog.qml"
_NO_DIALOG_MARK = "NO_DIALOG_ORIG"  # 备份标记：官方版原本没有对话框文件


def find_app_root():
    """定位主程序根目录（含 src/qml/.../WidgetsContainer.qml 的路径）。"""
    import sys
    for p in sys.path:
        cand = Path(p)
        try:
            if (cand / _CONTAINER_REL).is_file():
                return cand
        except OSError:
            continue
    here = Path(__file__).resolve()
    for anc in here.parents:
        if (anc / _CONTAINER_REL).is_file():
            return anc
    return None


def _read(path):
    raw = path.read_bytes()
    crlf = b"\r\n" in raw
    text = raw.decode("utf-8")
    if crlf:
        text = text.replace("\r\n", "\n")
    return text, crlf


def _write(path, text, crlf):
    data = text.encode("utf-8")
    if crlf:
        data = data.replace(b"\n", b"\r\n")
    path.write_bytes(data)


def _apply(text, ops, tag):
    """顺序执行替换；锚点必须唯一，否则抛异常（由调用方回滚）。"""
    for old, new in ops:
        n = text.count(old)
        if n != 1:
            raise RuntimeError(f"{tag}: 锚点匹配 {n} 次（应为 1）: {old[:60]!r}")
        text = text.replace(old, new, 1)
    return text


# ── 补丁定义 ────────────────────────────────────────────────

_CONTAINER_OPS = [
    # 1) 顶部 import：让 AddOverlayMemberDialog（dialogs/ 子目录）可解析
    ("import ClassWidgets.Easing",
     "import ClassWidgets.Easing\nimport \"dialogs\""),
    # 2) 容器属性声明：overlayEditMode（QML 动态属性无法驱动绑定，必须显式声明）
    ("    property bool editMode: false",
     """    property bool editMode: false
    // 堆叠插件集成：编辑其内部成员（成员纵向排列 + 下方编辑行）
    property bool overlayEditMode: false"""),
    # 3) 右键菜单：Delete 项前插入"编辑成员组件"（仅堆叠组件显示）
    ("""                MenuItem {
                    icon.name: "ic_fluent_delete_20_regular"
                    text: qsTr("Delete")""",
     """                MenuItem {
                    // 堆叠插件集成：编辑其内部成员
                    visible: model.typeId === "com.overlay"
                    icon.name: "ic_fluent_layers_20_regular"
                    text: qsTr("编辑成员组件")
                    onTriggered: {
                        widgetMenu.close()
                        widgetsContainer.editMode = true
                        widgetsContainer.overlayEditMode = true
                    }
                }
                MenuItem {
                    icon.name: "ic_fluent_delete_20_regular"
                    text: qsTr("Delete")"""),
    # 3) delegate 尺寸：编辑堆叠时独占一行，下方预留编辑行
    ("""            property real visualScale: scaleFactor
            width: loader.width * visualScale
            height: loader.height * visualScale""",
     """            // 堆叠插件集成：编辑时独占一行（大组件），下方展开编辑行
            property bool isOverlay: model.typeId === "com.overlay"
            property bool overlayEditing: widgetsContainer.overlayEditMode && isOverlay
            property real visualScale: scaleFactor
            width: overlayEditing
                ? Math.max((widgetsContainer.parent ? widgetsContainer.parent.width - 16 : 0),
                           loader.width * visualScale)
                : loader.width * visualScale
            height: loader.height * visualScale
                + (overlayEditing ? editRow.height + 10 : 0)"""),
    # 4) 编辑行：组件正下方（deleteBtn 前）
    ("""            ToolButton {
                id: deleteBtn""",
     """            // 堆叠插件集成：成员编辑行（Add Member / Done）
            RowLayout {
                id: editRow
                objectName: "editRow"
                visible: widgetContainer.overlayEditing
                anchors.top: loader.bottom
                anchors.topMargin: 10
                anchors.horizontalCenter: parent.horizontalCenter
                width: implicitWidth
                height: implicitHeight
                spacing: 8

                Button {
                    id: addOverlayMemberButton
                    icon.name: "ic_fluent_add_20_regular"
                    text: qsTr("Add Member")
                    onClicked: addOverlayMemberDialog.open()
                }

                Button {
                    id: acceptOverlayButton
                    highlighted: true
                    icon.name: "ic_fluent_checkmark_20_regular"
                    text: qsTr("Done")
                    onClicked: {
                        widgetsContainer.overlayEditMode = false
                    }
                }
            }

            ToolButton {
                id: deleteBtn"""),
    # 5) 编辑堆叠时停止摇晃动画
    ("            rotation: editMode",
     "            rotation: editMode && !widgetsContainer.overlayEditMode"),
    ("                running: editMode",
     "                running: editMode && !widgetsContainer.overlayEditMode"),
    # 6) 编辑堆叠时禁用成员右键菜单（成员右键由 overlay 内部处理）
    ("""            // 鼠标右键打开设置
            TapHandler {
                acceptedButtons: Qt.RightButton""",
     """            // 鼠标右键打开设置（编辑堆叠时禁用，成员右键由 overlay 内部处理）
            TapHandler {
                acceptedButtons: Qt.RightButton
                enabled: !widgetsContainer.overlayEditMode"""),
    # 7) 官方"完成"按钮同时退出堆叠编辑态
    ("onClicked: widgetsContainer.editMode = false",
     "onClicked: { widgetsContainer.editMode = false; widgetsContainer.overlayEditMode = false }"),
    # 8) 成员选择对话框实例
    ("""    // 小组件设置窗口
    WidgetSettingsDialog {
        id: settingsDialog
    }""",
     """    // 小组件设置窗口
    WidgetSettingsDialog {
        id: settingsDialog
    }

    // 堆叠插件集成：成员选择窗口
    AddOverlayMemberDialog {
        id: addOverlayMemberDialog
    }"""),
]

_WLOADER_OPS = [
    # 1) 组件就绪时转发 overlayEditMode -> overlay.qml 的列表模式
    ("""            if (item && item.hasOwnProperty('editMode')) {
                item.editMode = widgetsContainer.editMode
            }
            anim.start()""",
     """            if (item && item.hasOwnProperty('editMode')) {
                item.editMode = widgetsContainer.editMode
            }
            if (item && item.hasOwnProperty('overlayListMode')) {
                item.overlayListMode = widgetsContainer.overlayEditMode
            }
            anim.start()"""),
    # 2) 编辑态切换时同步列表模式
    ("""        function onEditModeChanged() {
            if (loader.item && loader.item.hasOwnProperty('editMode')) {
                loader.item.editMode = widgetsContainer.editMode
            }
        }
    }""",
     """        function onEditModeChanged() {
            if (loader.item && loader.item.hasOwnProperty('editMode')) {
                loader.item.editMode = widgetsContainer.editMode
            }
        }
        function onOverlayEditModeChanged() {
            if (loader.item && loader.item.hasOwnProperty('overlayListMode')) {
                loader.item.overlayListMode = widgetsContainer.overlayEditMode
            }
        }
    }"""),
]


# ── 对外接口 ────────────────────────────────────────────────

def install(logger):
    """安装主程序集成补丁（幂等）。主程序路径不可用时静默跳过。

    补丁 = 修改 WidgetsContainer.qml + WidgetLoader.qml，并把
    AddOverlayMemberDialog.qml 复制到主程序（官方版没有该文件）。
    """
    root = find_app_root()
    if root is None:
        logger.warning("[overlay] 未找到主程序目录，跳过主程序集成")
        return False
    container = root / _CONTAINER_REL
    wloader = root / _WLOADER_REL
    dialog = root / _DIALOG_REL
    backup_dir = root / _BACKUP_ROOT / _BACKUP_SUB

    c_text = container.read_text(encoding="utf-8", errors="replace")
    w_text = wloader.read_text(encoding="utf-8", errors="replace")
    dialog_existed = dialog.is_file()
    if _MARKER in c_text or _MARKER in w_text:
        # 已打补丁：确保备份存在 + 对话框文件补齐（主程序更新可能删了它）
        if not (backup_dir / "WidgetsContainer.qml.orig").exists():
            backup_dir.mkdir(parents=True, exist_ok=True)
            (backup_dir / "WidgetsContainer.qml.orig").write_bytes(container.read_bytes())
            (backup_dir / "WidgetLoader.qml.orig").write_bytes(wloader.read_bytes())
            _record_dialog_backup(backup_dir, dialog, dialog_existed)
        if not dialog.is_file() and _DIALOG_SRC.is_file():
            dialog.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(_DIALOG_SRC, dialog)
            logger.info("[overlay] 已补全成员选择对话框文件")
        logger.info("[overlay] 主程序集成已就绪")
        return True

    # 备份官方原版
    backup_dir.mkdir(parents=True, exist_ok=True)
    (backup_dir / "WidgetsContainer.qml.orig").write_bytes(container.read_bytes())
    (backup_dir / "WidgetLoader.qml.orig").write_bytes(wloader.read_bytes())
    _record_dialog_backup(backup_dir, dialog, dialog_existed)

    # 注入；任一环节失败则整体回滚
    try:
        if not dialog.is_file():
            if not _DIALOG_SRC.is_file():
                raise RuntimeError("缺少 AddOverlayMemberDialog.qml 资源文件")
            dialog.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(_DIALOG_SRC, dialog)
        c_text, c_crlf = _read(container)
        c_text = _apply(c_text, _CONTAINER_OPS, "WidgetsContainer.qml")
        _write(container, c_text, c_crlf)
        w_text, w_crlf = _read(wloader)
        w_text = _apply(w_text, _WLOADER_OPS, "WidgetLoader.qml")
        _write(wloader, w_text, w_crlf)
    except Exception as e:
        restore(logger)
        logger.error(f"[overlay] 主程序集成补丁失败，已还原: {e}")
        return False
    logger.info("[overlay] 主程序集成补丁已安装（3 个文件：2 补丁 + 1 对话框）")
    return True


def _record_dialog_backup(backup_dir, dialog, existed):
    """记录对话框文件的官方原状：存在则备份内容，不存在则打标记。"""
    if existed:
        (backup_dir / "AddOverlayMemberDialog.qml.orig").write_bytes(dialog.read_bytes())
    else:
        (backup_dir / _NO_DIALOG_MARK).write_text(
            "official ClassWidgets has no AddOverlayMemberDialog.qml\n", encoding="utf-8")


def restore(logger):
    """从备份还原主程序文件（幂等）。无备份时不做任何事。"""
    root = find_app_root()
    if root is None:
        return False
    backup_dir = root / _BACKUP_ROOT / _BACKUP_SUB
    if not backup_dir.is_dir():
        return False
    ok = True
    for name, rel in (("WidgetsContainer.qml.orig", _CONTAINER_REL),
                      ("WidgetLoader.qml.orig", _WLOADER_REL)):
        src = backup_dir / name
        dst = root / rel
        if src.is_file():
            dst.write_bytes(src.read_bytes())
        else:
            ok = False
    # 对话框文件：官方原本有 → 还原；官方原本没有 → 删除注入的
    if (backup_dir / "AddOverlayMemberDialog.qml.orig").is_file():
        (root / _DIALOG_REL).write_bytes(
            (backup_dir / "AddOverlayMemberDialog.qml.orig").read_bytes())
    elif (backup_dir / _NO_DIALOG_MARK).is_file():
        (root / _DIALOG_REL).unlink(missing_ok=True)
    # 还原完成后备份已无意义，整体清理
    shutil.rmtree(backup_dir, ignore_errors=True)
    logger.info("[overlay] 主程序已还原（移除编辑成员组件入口）")
    return ok
