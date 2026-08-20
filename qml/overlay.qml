import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import RinUI
import ClassWidgets.Theme 1.0

// 堆叠组件（灵动岛）：多个成员组件叠放，按设定间隔循环滚动展示（轮播模式）；
// 在主程序"编辑堆叠组件"时切换为纵列列表模式，成员依次列出，
// 右键成员可单独编辑其设置，成员左上角减号移除成员。
// 容器本身无标题无背景（不继承 Widget 卡片），成员组件自带卡片，
// 成员内容即组件内容，不会被标题栏挤下去。

Item {
    id: root

    // 主程序 WidgetLoader 注入的属性
    property var backend: null
    property var settings: null
    property bool editMode: false
    // 主程序"编辑重叠组件"模式：true 时成员纵列列出（由 WidgetLoader 转发）
    property bool overlayListMode: false

    // WidgetLoader 在组件创建完成后才注入 backend（Loader.Ready），
    // 因此不能用 onCompleted 刷新，改为 backend 注入时触发
    onBackendChanged: {
        if (backend) refresh()
    }

    property var members: []
    property int activeIndex: 0
    property var defs: WidgetsModel ? WidgetsModel.definitionsList : []
    property int maxW: 0
    property int maxH: 0
    property var memberHeights: []
    property int listSpacing: 10

    implicitWidth: Math.max(96, root.maxW)
    implicitHeight: root.overlayListMode
        ? Math.max(80, root.listTotalH())
        : Math.max(80, root.maxH)

    // 轮播间隔由组件设置 interval_ms 控制（列表模式 / 编辑模式暂停）
    property int carouselInterval: settings && settings.interval_ms ? settings.interval_ms : 5000

    Timer {
        id: carouselTimer
        interval: root.carouselInterval
        repeat: true
        running: root.members.length > 1 && !root.editMode && !root.overlayListMode
        onTriggered: {
            root.activeIndex = (root.activeIndex + 1) % root.members.length
        }
    }

    Connections {
        target: backend
        function onMembersChanged() { root.refresh() }
    }

    function findDef(widgetId) {
        for (var i = 0; i < root.defs.length; i++) {
            if (root.defs[i].id === widgetId) return root.defs[i]
        }
        return null
    }

    function refresh() {
        var list = backend.getMembers()
        root.members = list
        // 重建高度缓存：成员删除后 Repeater delegate 会被复用（onLoaded 不再触发），
        // 直接从现有 delegate 读取高度，避免 listY 全部归零导致成员叠放
        root.memberHeights = []
        for (var k = 0; k < memberRepeater.count; k++) {
            var obj = memberRepeater.itemAt(k)
            root.memberHeights[k] = (obj && obj.item) ? obj.item.height : 0
        }
        if (root.activeIndex >= list.length) root.activeIndex = 0
    }

    // 列表模式下第 i 个成员的 y（前面成员高度累计 + 间距）
    function listY(i) {
        var y = 0
        for (var k = 0; k < i; k++) {
            y += (root.memberHeights[k] || 0) + root.listSpacing
        }
        return y
    }

    function listTotalH() {
        var h = 0
        for (var k = 0; k < root.memberHeights.length; k++) {
            h += (root.memberHeights[k] || 0)
        }
        return h + root.listSpacing * Math.max(0, root.memberHeights.length - 1)
    }

    // 右键成员 → 单独编辑该组件设置
    function openMemberSettings(i) {
        var wid = root.members[i]
        var d = root.findDef(wid)
        if (!d || !root.backend) return
        // 字段兜底：不同来源的定义列表字段名可能不同
        var sq = d.settingsQml || d.settings_qml || ""
        console.log("[overlay] openMemberSettings:", wid, "settingsQml:", sq)
        if (!sq) return
        var saved = root.backend.getMemberSettings(wid) || {}
        memberSettingsDialog.currentMemberId = wid
        settingsLoader.setSource(sq, {
            "settings": saved,
            "instanceId": ""
        })
        memberSettingsDialog.visible = true
    }

    // 保存成员设置后同步到已加载的成员实例
    function applyMemberSettings(wid) {
        var saved = root.backend.getMemberSettings(wid) || {}
        for (var k = 0; k < memberRepeater.count; k++) {
            var obj = memberRepeater.itemAt(k)
            if (obj && obj.memberId === wid && obj.item
                    && obj.item.settings !== undefined) {
                obj.item.settings = saved
            }
        }
    }

    Component.onCompleted: {
        if (backend) refresh()
    }

    // 空状态提示（无成员时）
    Text {
        anchors.centerIn: parent
        visible: root.members.length === 0
        text: "堆叠组件\n右键编辑添加成员"
        horizontalAlignment: Text.AlignHCenter
        color: Theme.isDark() ? Qt.rgba(1, 1, 1, 0.55) : Qt.rgba(0, 0, 0, 0.55)
        font.pixelSize: 13
        lineHeight: 1.4
    }

    // 成员：轮播模式叠放居中（仅 activeIndex 显示，交叉淡化 + 缩放）；
    // 列表模式纵列依次排列（全部显示，右键可编辑成员设置）
    Repeater {
        id: memberRepeater
        anchors.fill: parent
        model: root.members

        Loader {
            id: memberLoader
            asynchronous: true
            z: index === root.activeIndex ? 1 : 0
            x: root.overlayListMode ? 0 : (parent.width - width) / 2
            y: root.overlayListMode ? root.listY(index) : (parent.height - height) / 2
            opacity: root.overlayListMode
                ? 1
                : (index === root.activeIndex ? 1 : 0)
            scale: root.overlayListMode
                ? 1
                : (index === root.activeIndex ? 1 : 0.9)

            Behavior on opacity {
                NumberAnimation { duration: 420; easing.type: Easing.InOutQuad }
            }
            Behavior on scale {
                NumberAnimation { duration: 420; easing.type: Easing.OutCubic }
            }

            // 右键成员 → 单独编辑该组件设置（仅编辑堆叠组件模式生效；
            // 非编辑状态禁用，右键交还堆叠组件菜单）
            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.RightButton
                enabled: root.overlayListMode
                onClicked: (mouse) => {
                    if (mouse.button === Qt.RightButton) root.openMemberSettings(index)
                }
            }

            // 列表模式下成员左上角的移除按钮（与原版组件删除按钮一致）
            ToolButton {
                visible: root.overlayListMode
                icon.name: "ic_fluent_line_horizontal_1_20_filled"
                size: 12
                width: 24
                height: 24
                anchors.top: parent.top
                anchors.left: parent.left
                onClicked: {
                    if (root.backend) root.backend.removeMember(memberId)
                }
            }

            property string memberId: modelData
            source: {
                var d = root.findDef(modelData)
                return d && d.qml_path ? d.qml_path : ""
            }

            onLoaded: {
                var d = root.findDef(memberId)
                if (d) {
                    if (d.backend_obj && item) item.backend = d.backend_obj
                    if (item) {
                        // 禁用成员自身的尺寸动画，保证堆叠布局稳定（不随成员尺寸变化抖动）
                        if (item.hasOwnProperty("animateSize")) item.animateSize = false
                        // 成员设置：优先使用右键单独保存的个性化设置，否则用默认设置
                        var saved = root.backend && root.backend.getMemberSettings
                            ? (root.backend.getMemberSettings(memberId) || {})
                            : {}
                        var hasSaved = saved && Object.keys(saved).length > 0
                        item.settings = hasSaved ? saved : (d.default_settings || {})
                    }
                }
                // 记录成员尺寸（容器随之固定；列表模式用于纵列排布）
                if (item) {
                    root.maxW = Math.max(root.maxW, item.implicitWidth)
                    root.maxH = Math.max(root.maxH, item.height)
                    root.memberHeights[index] = item.height
                }
            }

            onStatusChanged: {
                if (status === Loader.Error && source !== "") {
                    console.error("[overlay] 成员组件加载失败:", memberId, source)
                }
            }
        }
    }

    // 成员设置对话框（自绘：全屏遮罩 + 居中面板，不依赖 Dialog/Button 类型，避免被 RinUI 遮蔽）
    Item {
        id: memberSettingsDialog
        objectName: "memberSettingsDialog"
        property string currentMemberId: ""
        visible: false
        z: 10000
        width: Screen.width
        height: Screen.height

        // 遮罩（点击外部关闭）
        Rectangle {
            anchors.fill: parent
            color: Qt.rgba(0, 0, 0, 0.35)
            MouseArea {
                anchors.fill: parent
                onClicked: memberSettingsDialog.visible = false
            }
        }

        // 面板
        Rectangle {
            anchors.centerIn: parent
            width: Math.min(520, Screen.width * 0.6)
            height: 380
            radius: 12
            color: Theme.isDark() ? "#1E1D22" : "#FBFAFF"
            border.color: Qt.rgba(255, 255, 255, 0.15)
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 10

                Text {
                    text: qsTr("Member Settings")
                    font.pixelSize: 15
                    font.weight: Font.DemiBold
                    color: Theme.isDark() ? "#fff" : "#1a1a1a"
                }

                Flickable {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    contentHeight: settingsLoader.height
                    clip: true

                    Loader {
                        id: settingsLoader
                        width: parent.width
                    }
                }

                RowLayout {
                    Layout.alignment: Qt.AlignRight
                    spacing: 8

                    // 取消（自绘按钮）
                    Rectangle {
                        width: 76
                        height: 32
                        radius: 8
                        color: cancelHovered
                            ? Qt.rgba(255, 255, 255, 0.12)
                            : "transparent"
                        border.color: Qt.rgba(255, 255, 255, 0.2)
                        border.width: 1
                        property bool cancelHovered: false

                        Text {
                            anchors.centerIn: parent
                            text: qsTr("Cancel")
                            font.pixelSize: 13
                            color: Theme.isDark() ? "#ddd" : "#333"
                        }
                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            onEntered: parent.cancelHovered = true
                            onExited: parent.cancelHovered = false
                            onClicked: memberSettingsDialog.visible = false
                        }
                    }

                    // 保存（自绘按钮）
                    Rectangle {
                        width: 76
                        height: 32
                        radius: 8
                        color: saveHovered
                            ? Qt.rgba(0, 120, 212, 0.9)
                            : "#0078D4"
                        property bool saveHovered: false

                        Text {
                            anchors.centerIn: parent
                            text: qsTr("Save")
                            font.pixelSize: 13
                            color: "#fff"
                        }
                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            onEntered: parent.saveHovered = true
                            onExited: parent.saveHovered = false
                            onClicked: {
                                if (settingsLoader.item && settingsLoader.item.settings
                                        && root.backend) {
                                    root.backend.saveMemberSettings(
                                        memberSettingsDialog.currentMemberId,
                                        settingsLoader.item.settings)
                                    root.applyMemberSettings(
                                        memberSettingsDialog.currentMemberId)
                                }
                                memberSettingsDialog.visible = false
                            }
                        }
                    }
                }
            }
        }
    }
}
