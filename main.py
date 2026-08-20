"""
堆叠插件（Overlay）：把多个桌面组件叠在一起，按设定间隔循环滚动展示。
以成员中最大的组件尺寸为固定大小（灵动岛样式）。

成员组件列表由本插件后端独立持久化（.overlay_members.json），
编辑入口：桌面组件编辑界面中右键堆叠组件 → “编辑堆叠组件”。
"""

import json
from pathlib import Path

from loguru import logger
from PySide6.QtCore import Signal, Slot

from ClassWidgets.SDK import CW2Plugin, PluginAPI

# 堆叠组件自身的 widget id（禁止添加自己，避免递归）
_OVERLAY_WIDGET_ID = "com.overlay"


class Plugin(CW2Plugin):
    """堆叠插件：成员组件管理 + 轮播配置。"""

    membersChanged = Signal()

    def __init__(self, api: PluginAPI):
        super().__init__(api)
        self._members: list[str] = []       # 成员 widget_id 列表
        self._member_settings: dict = {}    # 成员 widget_id -> 该成员的组件设置
        self._members_file = Path(__file__).resolve().parent / ".overlay_members.json"
        self._settings_file = Path(__file__).resolve().parent / ".overlay_member_settings.json"
        self._load_members()
        self._load_member_settings()

    # ── 生命周期 ──────────────────────────────────────────────

    def on_load(self):
        super().on_load()
        try:
            self.api.widgets.register(
                widget_id=_OVERLAY_WIDGET_ID,
                name="堆叠 / Stack",
                qml_path="qml/overlay.qml",
                backend_obj=self,
                settings_qml="qml/overlay-settings.qml",
                default_settings={"interval_ms": 5000},
            )
            logger.info("[overlay] 堆叠组件注册成功")
        except Exception as e:
            logger.warning(f"[overlay] 注册堆叠组件失败: {e}")

    def on_unload(self):
        super().on_unload()

    # ── 成员管理 ─────────────────────────────────────────────

    @Slot(result=list)
    def getMembers(self) -> list:
        """返回成员组件 widget_id 列表（QML 轮播用）。"""
        return list(self._members)

    @Slot(result=int)
    def getMemberCount(self) -> int:
        return len(self._members)

    @Slot(str, result=bool)
    def addMember(self, widget_id: str) -> bool:
        """添加成员组件（去重；禁止添加堆叠组件自身）。"""
        wid = str(widget_id).strip()
        if not wid or wid == _OVERLAY_WIDGET_ID or wid in self._members:
            return False
        self._members.append(wid)
        self._save_members()
        self.membersChanged.emit()
        logger.info(f"[overlay] 已添加成员: {wid}")
        return True

    @Slot(str)
    def removeMember(self, widget_id: str) -> None:
        wid = str(widget_id).strip()
        if wid in self._members:
            self._members.remove(wid)
            self._member_settings.pop(wid, None)
            self._save_members()
            self._save_member_settings()
            self.membersChanged.emit()
            logger.info(f"[overlay] 已移除成员: {wid}")

    # ── 成员组件设置（单独编辑成员时使用）──────────────────────

    @Slot(str, result=dict)
    def getMemberSettings(self, widget_id: str) -> dict:
        """返回某个成员组件的个性化设置（无则空 dict，调用方回退默认设置）。"""
        return dict(self._member_settings.get(str(widget_id), {}))

    @Slot(str, dict)
    def saveMemberSettings(self, widget_id: str, settings: dict) -> None:
        """保存某个成员组件的设置（按 widget_id 独立持久化）。"""
        wid = str(widget_id).strip()
        if not wid:
            return
        self._member_settings[wid] = dict(settings or {})
        self._save_member_settings()
        logger.info(f"[overlay] 已保存成员设置: {wid}")

    # ── 持久化 ───────────────────────────────────────────────

    def _load_members(self) -> None:
        try:
            if self._members_file.exists():
                data = json.loads(self._members_file.read_text(encoding="utf-8"))
                self._members = [str(x) for x in (data.get("members") or [])]
        except Exception:
            self._members = []

    def _save_members(self) -> None:
        try:
            self._members_file.write_text(
                json.dumps({"members": self._members}, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning(f"[overlay] 保存成员列表失败: {e}")

    def _load_member_settings(self) -> None:
        try:
            if self._settings_file.exists():
                data = json.loads(self._settings_file.read_text(encoding="utf-8"))
                self._member_settings = {str(k): dict(v or {})
                                         for k, v in (data.get("settings") or {}).items()}
        except Exception:
            self._member_settings = {}

    def _save_member_settings(self) -> None:
        try:
            self._settings_file.write_text(
                json.dumps({"settings": self._member_settings}, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning(f"[overlay] 保存成员设置失败: {e}")
