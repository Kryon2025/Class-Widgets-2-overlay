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

    // 右侧切换条占位宽度（仅显示切换条时预留，保证不超出组件边界被裁剪）
    property int switchBarSpace: root.showSwitchBar && root.members.length > 0 ? 48 : 0

    implicitWidth: Math.max(96, root.maxW + root.switchBarSpace)
    implicitHeight: root.overlayListMode
        ? Math.max(80, root.listTotalH())
        : Math.max(80, root.maxH)

    // 轮播间隔由组件设置 interval_ms 控制（列表模式 / 编辑模式暂停）
    property int carouselInterval: settings && settings.interval_ms ? settings.interval_ms : 5000

    // 右侧“切换”条显示开关（组件设置 show_switch_bar 控制，默认显示）
    property bool showSwitchBar: settings && settings.show_switch_bar !== false

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

    // 成员设置的最终值 = 默认设置 + 个性化设置覆盖（保证未保存过的字段
    // 显示组件默认值，与组件实际运行状态一致）
    function mergedMemberSettings(wid) {
        var d = root.findDef(wid)
        var defaults0 = d ? (d.default_settings || {}) : {}
        var saved0 = (root.backend && root.backend.getMemberSettings)
            ? (root.backend.getMemberSettings(wid) || {})
            : {}
        var merged = {}
        for (var k in defaults0) merged[k] = defaults0[k]
        for (var k2 in saved0) merged[k2] = saved0[k2]
        return merged
    }

    // 点击“切换”条：切到下一个成员并重置轮播计时（不触发组件自动隐藏）
    function nextMember() {
        if (root.members.length > 1) {
            root.activeIndex = (root.activeIndex + 1) % root.members.length
            if (carouselTimer.running) carouselTimer.restart()
        }
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
        var merged = root.mergedMemberSettings(wid)
        memberSettingsDialog.currentMemberId = wid
        settingsLoader.setSource(sq, {
            "settings": merged,
            "instanceId": ""
        })
        memberSettingsDialog.open()
    }

    // 保存成员设置后同步到已加载的成员实例
    function applyMemberSettings(wid) {
        var merged = root.mergedMemberSettings(wid)
        for (var k = 0; k < memberRepeater.count; k++) {
            var obj = memberRepeater.itemAt(k)
            if (obj && obj.memberId === wid && obj.item
                    && obj.item.settings !== undefined) {
                obj.item.settings = merged
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
            // 轮播模式在内容区（排除右侧切换条）居中；列表模式纵列
            x: root.overlayListMode ? 0 : (Math.max(0, parent.width - root.switchBarSpace - width)) / 2
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
                        // 成员设置 = 默认设置 + 个性化覆盖，保证开关等控件的
                        // 初始显示与组件实际运行状态一致
                        item.settings = root.mergedMemberSettings(memberId)
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

    // 右侧“切换”竖条：点击切换到下一个成员（消费点击，不触发组件自动隐藏）；
    // 无成员 / 编辑堆叠组件（成员列表与增删界面）时隐藏，可在组件设置中开关
    Rectangle {
        id: switchBar
        objectName: "switchBar"
        visible: root.showSwitchBar && root.members.length > 0 && !root.overlayListMode
        z: 5
        width: 36
        height: Math.min(120, Math.max(40, root.maxH))
        radius: 12
        // 固定在组件内部右侧（组件宽度已为其预留空间，不被外层裁剪）
        x: root.width - 48
        y: (root.height - height) / 2
        color: Theme.isDark() ? Qt.rgba(0.14, 0.14, 0.16, 0.9) : Qt.rgba(0.98, 0.98, 1, 0.92)
        border.color: Theme.isDark() ? Qt.rgba(1, 1, 1, 0.18) : Qt.rgba(0, 0, 0, 0.12)
        border.width: 1

        Text {
            anchors.centerIn: parent
            // 竖排显示（不旋转，字头朝上）
            text: "切\n换"
            color: Theme.isDark() ? Qt.rgba(1, 1, 1, 0.85) : Qt.rgba(0, 0, 0, 0.75)
            font.pixelSize: 13
            font.weight: Font.DemiBold
        }

        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.nextMember()
        }
    }

    // 成员设置对话框：用 Dialog（主程序窗口管理，天然屏幕居中，
    // 不受堆叠组件自身位置影响；内容按钮自绘，不依赖 RinUI 遮蔽类型）
    Dialog {
        id: memberSettingsDialog
        objectName: "memberSettingsDialog"
        title: qsTr("Member Settings")
        modal: true
        width: Math.min(520, Screen.width * 0.6)
        height: 420
        property string currentMemberId: ""

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 10

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
                        onClicked: memberSettingsDialog.close()
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
                            memberSettingsDialog.close()
                        }
                    }
                }
            }
        }
    }
}
