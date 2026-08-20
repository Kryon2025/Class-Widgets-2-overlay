import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import RinUI
import ClassWidgets.Plugins

// 重叠组件设置页：轮播间隔 + 成员组件管理
// 成员组件主要入口：桌面组件编辑界面右键 → “编辑重叠组件”

SettingsLayout {
    property int intervalValue: 5000
    property int secValue: 5
    onSecValueChanged: settings.interval_ms = secValue * 1000
    Component.onCompleted: {
        secValue = (settings.interval_ms || 5000) / 1000
    }

    // 从主程序组件定义中取重叠插件后端（设置页加载时无直接 backend 上下文）
    property var overlayBackend: {
        if (typeof WidgetsModel !== "undefined" && WidgetsModel.definitionsList) {
            var defs = WidgetsModel.definitionsList
            for (var i = 0; i < defs.length; i++) {
                if (defs[i].id === "com.overlay") return defs[i].backend_obj
            }
        }
        return null
    }

    SettingCard {
        Layout.fillWidth: true
        title: "轮播间隔"
        description: "每个组件停留后切换到下一个的时间（秒），加减按钮以 1 秒调整。"

        RowLayout {
            spacing: 8
            Button {
                text: "−"
                implicitWidth: 36
                onClicked: secValue = Math.max(1, secValue - 1)
            }
            Text {
                Layout.preferredWidth: 70
                horizontalAlignment: Text.AlignHCenter
                text: secValue + " 秒"
                font.bold: true
            }
            Button {
                text: "+"
                implicitWidth: 36
                onClicked: secValue = Math.min(60, secValue + 1)
            }
        }
    }

    SettingCard {
        Layout.fillWidth: true
        title: "成员组件"
        description: "已叠加到本组件内的成员，可在桌面组件编辑界面中右键“编辑重叠组件”添加/移除。"

        ColumnLayout {
            spacing: 4
            Repeater {
                model: overlayBackend ? overlayBackend.getMembers() : []
                delegate: RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Text {
                        Layout.fillWidth: true
                        text: modelData
                        elide: Text.ElideMiddle
                    }
                    Button {
                        text: "移除"
                        implicitWidth: 52
                        implicitHeight: 26
                        onClicked: {
                            if (overlayBackend) overlayBackend.removeMember(modelData)
                        }
                    }
                }
            }
        }
    }
}
