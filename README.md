# 堆叠组件（Overlay / Stack）

将多个桌面组件叠放在一起，以**最大成员的尺寸**作为固定大小（灵动岛样式），按设定间隔自动循环滚动展示；也可通过组件右侧的「切换」条手动切换成员。

- 插件 ID：`com.overlay`
- 版本：1.0.0（API `~=0.6.0`）
- 仓库：<https://github.com/Kryon2025/Class-Widgets-2-overlay.git>

## 功能特性

- **多组件叠放**：任意数量的桌面组件叠成一层，容器尺寸取最大成员，成员自带卡片样式，无标题栏挤压
- **轮播展示**：按设定间隔自动循环切换成员；成员少于 2 个或处于编辑模式时自动暂停
- **手动切换**：组件右侧「切换」条（可关闭），点击立即切换到下一个成员
- **成员管理**：桌面组件编辑界面中右键堆叠组件 →「编辑重叠组件」，添加 / 移除成员、单独编辑每个成员的组件设置
- **列表编辑模式**：进入主程序编辑模式时，成员自动改为纵列列表，便于查看与操作
- **主程序免配置集成**：插件加载时自动为主程序注入「编辑成员组件」入口，卸载 / 禁用时自动还原，主程序更新覆盖后首次启动自动自愈

## 安装

1. 在主程序中导入 `com.overlay.cwplugin`（或解压到主程序 `plugins/com.overlay` 目录）
2. 重启主程序（首次加载即完成主程序集成补丁）
3. 添加组件：桌面组件列表中新增「堆叠 / Stack」

> 插件加载时会修改主程序的 3 个 QML 文件（详见下方「主程序集成」），所有改动均有备份与自动还原机制，卸载插件即可完整还原官方原版。

## 使用

### 添加成员

1. 打开主程序「桌面组件编辑界面」
2. **右键**堆叠组件 → 选择「编辑成员组件」（插件自动注入的入口）
3. 在打开的对话框中选择要叠加的组件（堆叠组件自身不可添加，自动过滤）

### 调整轮播与切换

打开堆叠组件的「组件设置」：

| 设置项 | 说明 |
| --- | --- |
| 轮播间隔 | 每个成员停留后切换到下一个的时间（1–60 秒，默认 5 秒） |
| 显示切换条 | 是否在组件右侧显示「切换」按钮（默认显示） |
| 成员组件 | 查看当前成员列表，可在此直接移除 |

### 单独编辑成员设置

在「编辑成员组件」对话框中选中某个成员，可打开该成员自己的组件设置页；设置按成员独立保存，互不影响（持久化于 `.overlay_member_settings.json`）。

## 主程序集成（补丁机制）

堆叠组件的右键入口需要修改主程序 QML，由 `overlay_integration.py` 统一管理，具备完整的**安装 / 自愈 / 还原**能力：

- **自动安装**：插件 `on_load` 时执行，先于主程序 QML 引擎加载，本次启动即生效
- **自动自愈**：主程序更新覆盖补丁后，首次启动检测到缺失自动重新注入
- **自动还原**：插件 `on_unload`（卸载 / 禁用）时移除补丁，还原官方原版
- **失败回滚**：安装过程中任一步失败即整体回滚，主程序保持官方原版，不会因补丁崩溃

### 涉及的 3 个主程序文件

| 文件 | 操作 |
| --- | --- |
| `src/qml/ClassWidgets/Components/WidgetsContainer.qml` | 打补丁（右键菜单、编辑行、`overlayEditMode` 属性） |
| `src/qml/ClassWidgets/Components/WidgetLoader.qml` | 打补丁（列表模式转发） |
| `src/qml/ClassWidgets/Components/dialogs/AddOverlayMemberDialog.qml` | 官方版本无此文件，由插件复制（资源位于 `host_patch/`） |

原始文件备份于主程序 `.backups/overlay_integration/`，还原后备份自动清理。

### 手动注入工具（可选）

正常情况下无需手动干预；如主程序目录特殊需要手动注入 / 还原 / 查看状态，可用独立脚本（位于本仓库 `tools/` 目录）：

```bash
python cw2_overlay_injector.py status   --app 主程序目录
python cw2_overlay_injector.py install  --app 主程序目录
python cw2_overlay_injector.py restore  --app 主程序目录
```

## 目录结构

```text
com.overlay/
├── main.py                  # 插件后端：成员管理、设置持久化、生命周期
├── overlay_integration.py   # 主程序集成：补丁安装 / 自愈 / 还原
├── qml/
│   ├── overlay.qml          # 组件本体（轮播 + 切换条 + 列表编辑模式）
│   └── overlay-settings.qml # 组件设置页（轮播间隔 / 切换条 / 成员列表）
├── host_patch/
│   └── AddOverlayMemberDialog.qml   # 主程序对话框文件资源
├── cwplugin.json            # 插件清单
├── icon.png
├── LICENSE
└── README.md
```

运行时数据（插件目录内自动生成）：

- `.overlay_members.json`：成员 widget_id 列表（原子写入）
- `.overlay_member_settings.json`：各成员个性化设置

## 开发

环境要求：主程序 `2.0.0`（API `~=0.6.0`）+ Python 3.12。

```bash
# 打包插件（使用主程序自带的 Class Widgets Plugin Packager）
cw-plugin-pack com.overlay

# 语法检查（需 PySide6）
python _qmltest/_check_qml_syntax.py qml/overlay.qml
```

### 代码要点

- 成员列表 / 成员设置由插件后端独立持久化，与主程序组件配置分离，卸载重装插件不清空
- 轮播 `Timer` 仅在 `members.length > 1 && !editMode` 时运行，编辑时自动暂停
- 尺寸计算取所有成员的 `implicitWidth / implicitHeight` 最大值，切换条占位宽度单独预留，避免被容器裁剪

## 常见问题

**Q：右键堆叠组件没有「编辑成员组件」？**
A：确认插件已启用并重启过主程序；若主程序刚更新过，重启一次让插件自动重新注入补丁。

**Q：卸载插件后主程序有残留吗？**
A：没有。`on_unload` 会还原被修改的 QML 并删除注入的对话框文件与备份目录，官方原版完整恢复。

**Q：可以嵌套堆叠吗？**
A：不允许。堆叠组件自身不能作为成员加入（`addMember` 自动拒绝 `com.overlay`）。

## 许可证

MIT，详见 `LICENSE`。
