"""
堆叠插件（Overlay）：把多个桌面组件叠在一起，按设定间隔循环滚动展示。
以成员中最大的组件尺寸为固定大小（灵动岛样式）。

成员组件列表由本插件后端独立持久化（.overlay_members.json），
编辑入口：桌面组件编辑界面中右键堆叠组件 → “编辑堆叠组件”。
"""

import json
import os
from pathlib import Path

from loguru import logger
from PySide6.QtCore import Property, Signal, Slot

from ClassWidgets.SDK import CW2Plugin, PluginAPI
from overlay_integration import install as _install_integration, restore as _restore_integration

# 堆叠组件自身的 widget id（禁止添加自己，避免递归）
_OVERLAY_WIDGET_ID = "com.overlay"


class Plugin(CW2Plugin):
    """堆叠插件：成员组件管理 + 轮播配置。"""

    membersChanged = Signal()
    # 设置页保存"上课隐藏切换条"配置后广播，组件 QML 立即重算上课状态
    # 配置由本插件自持久化（.overlay_class_hide.json），不依赖主程序组件 settings
    classHideChanged = Signal()
    _class_hide = {"enabled": False, "days": "1,2,3,4,5", "start": "08:00", "end": "18:00"}

    def __init__(self, api: PluginAPI):
        super().__init__(api)
        self._members: list[str] = []       # 成员 widget_id 列表
        self._member_settings: dict = {}    # 成员 widget_id -> 该成员的组件设置
        self._members_file = Path(__file__).resolve().parent / ".overlay_members.json"
        self._settings_file = Path(__file__).resolve().parent / ".overlay_member_settings.json"
        self._class_hide_file = Path(__file__).resolve().parent / ".overlay_class_hide.json"
        self._load_members()
        self._load_member_settings()
        self._load_class_hide()

    # ── 上课隐藏切换条 ─────────────────────────────────────────

    def _load_class_hide(self) -> None:
        try:
            data = json.loads(self._class_hide_file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for k in ("enabled", "days", "start", "end"):
                    if k in data:
                        self._class_hide[k] = data[k]
        except Exception:
            pass

    def _save_class_hide(self) -> None:
        try:
            self._class_hide_file.write_text(
                json.dumps(self._class_hide, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"[overlay] 保存上课时段配置失败: {e}")

    def _get_class_hide_enabled(self) -> bool:
        return bool(self._class_hide.get("enabled"))

    def _get_class_hide_days(self) -> str:
        return str(self._class_hide.get("days") or "")

    def _get_class_hide_start(self) -> str:
        return str(self._class_hide.get("start") or "")

    def _get_class_hide_end(self) -> str:
        return str(self._class_hide.get("end") or "")

    classHideEnabled = Property(bool, _get_class_hide_enabled, notify=classHideChanged)
    classHideDays = Property(str, _get_class_hide_days, notify=classHideChanged)
    classHideStart = Property(str, _get_class_hide_start, notify=classHideChanged)
    classHideEnd = Property(str, _get_class_hide_end, notify=classHideChanged)

    @Slot(bool, str, str, str)
    def setClassHide(self, enabled: bool, days: str, start: str, end: str) -> None:
        """保存上课隐藏切换条配置（插件自持久化）并广播刷新。"""
        self._class_hide.update(enabled=bool(enabled), days=str(days or ""),
                                start=str(start or ""), end=str(end or ""))
        self._save_class_hide()
        self.classHideChanged.emit()

    @Slot()
    def refreshClassHide(self) -> None:
        """通知所有组件实例：立即按当前配置重算隐藏状态。"""
        self.classHideChanged.emit()

    # ── 生命周期 ──────────────────────────────────────────────

    def on_load(self):
        super().on_load()
        try:
            # 主程序集成：右键"编辑成员组件"入口（插件加载时自动安装/自愈，
            # 先于主程序 QML 引擎加载，本次启动即生效）
            _install_integration(logger)
        except Exception as e:
            logger.warning(f"[overlay] 主程序集成安装异常: {e}")
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
        try:
            # 主程序集成还原：卸载/禁用插件时移除补丁，还原官方原版
            _restore_integration(logger)
        except Exception as e:
            logger.warning(f"[overlay] 主程序集成还原异常: {e}")

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
        if not isinstance(widget_id, str):
            return False
        wid = widget_id.strip()
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

    @staticmethod
    def _atomic_write_json(path: Path, payload: dict) -> None:
        """临时文件 + os.replace 原子写，避免中途崩溃留下截断文件。"""
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)

    def _load_members(self) -> None:
        try:
            if self._members_file.exists():
                data = json.loads(self._members_file.read_text(encoding="utf-8"))
                raw = data.get("members") or []
                # 只接受非空字符串，过滤自身 id 并去重，避免幽灵成员
                cleaned = [x.strip() for x in raw
                           if isinstance(x, str) and x.strip()
                           and x.strip() != _OVERLAY_WIDGET_ID]
                self._members = list(dict.fromkeys(cleaned))
        except Exception:
            self._members = []

    def _save_members(self) -> None:
        try:
            self._atomic_write_json(self._members_file, {"members": self._members})
        except Exception as e:
            logger.warning(f"[overlay] 保存成员列表失败: {e}")

    def _load_member_settings(self) -> None:
        try:
            if self._settings_file.exists():
                data = json.loads(self._settings_file.read_text(encoding="utf-8"))
                settings = {}
                for k, v in (data.get("settings") or {}).items():
                    # 单个坏值只跳过该成员，不丢弃全部
                    if isinstance(v, dict):
                        settings[str(k)] = dict(v)
                self._member_settings = settings
        except Exception:
            self._member_settings = {}

    def _save_member_settings(self) -> None:
        try:
            self._atomic_write_json(self._settings_file, {"settings": self._member_settings})
        except Exception as e:
            logger.warning(f"[overlay] 保存成员设置失败: {e}")
