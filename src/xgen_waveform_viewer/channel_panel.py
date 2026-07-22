"""
多通道配置面板 - V3.0

提供通道管理 UI：
- 通道列表显示
- 通道颜色和标签编辑
- 通道可见性切换
- 通道分组管理
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QColorDialog, QLineEdit, QComboBox,
    QCheckBox, QLabel, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPalette

from .multi_channel import MultiChannelManager, ChannelConfig


class ColorButton(QPushButton):
    """颜色选择按钮"""
    
    color_changed = pyqtSignal(str)
    
    def __init__(self, color: str = "#00ff00", parent=None):
        super().__init__(parent)
        self._color = color
        self.setFixedSize(30, 24)
        self.clicked.connect(self._choose_color)
        self._update_button_color()
    
    def get_color(self) -> str:
        return self._color
    
    def set_color(self, color: str):
        self._color = color
        self._update_button_color()
    
    def _update_button_color(self):
        """更新按钮显示颜色"""
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._color};
                border: 2px solid #555;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                border: 2px solid #888;
            }}
        """)
    
    def _choose_color(self):
        """打开颜色选择对话框"""
        color = QColorDialog.getColor(QColor(self._color), self, "选择通道颜色")
        if color.isValid():
            self._color = color.name()
            self._update_button_color()
            self.color_changed.emit(self._color)


class ChannelPanel(QWidget):
    """通道管理面板"""
    
    # 信号
    channel_config_changed = pyqtSignal(int)  # channel_id
    
    def __init__(self, channel_manager: MultiChannelManager, parent=None):
        super().__init__(parent)
        self._manager = channel_manager
        self._channel_widgets = {}  # {channel_id: {widgets}}
        
        self._setup_ui()
        self._connect_signals()
        self._refresh_channel_list()
    
    def _setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        
        # 标题和操作按钮
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<b>通道管理</b>"))
        header_layout.addStretch()
        
        self._btn_add = QPushButton("+ 添加通道")
        self._btn_add.clicked.connect(self._add_channel)
        header_layout.addWidget(self._btn_add)
        
        self._btn_remove = QPushButton("- 移除通道")
        self._btn_remove.clicked.connect(self._remove_channel)
        header_layout.addWidget(self._btn_remove)
        
        layout.addLayout(header_layout)
        
        # 通道表格
        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(["可见", "ID", "标签", "颜色", "分组", "Y偏移"])
        
        # 设置列宽
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # 可见
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # ID
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # 标签
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # 颜色
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # 分组
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Y偏移
        
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        
        layout.addWidget(self._table)
        
        # 统计信息
        self._stats_label = QLabel("通道数: 0")
        layout.addWidget(self._stats_label)
    
    def _connect_signals(self):
        """连接信号"""
        self._manager.channels_changed.connect(self._refresh_channel_list)
        self._manager.channel_config_changed.connect(self._on_channel_config_changed)
    
    def _refresh_channel_list(self):
        """刷新通道列表"""
        self._table.setRowCount(0)
        self._channel_widgets.clear()
        
        channels = self._manager.get_all_channels()
        channels.sort(key=lambda ch: ch.channel_id)
        
        for row, channel in enumerate(channels):
            self._add_channel_row(row, channel)
        
        # 更新统计
        visible_count = len(self._manager.get_visible_channels())
        total_count = len(channels)
        self._stats_label.setText(f"通道数: {total_count} (可见: {visible_count})")
    
    def _add_channel_row(self, row: int, channel: ChannelConfig):
        """添加通道行"""
        self._table.insertRow(row)
        channel_id = channel.channel_id
        
        # 0: 可见性复选框
        visible_checkbox = QCheckBox()
        visible_checkbox.setChecked(channel.visible)
        visible_checkbox.stateChanged.connect(
            lambda state, ch_id=channel_id: self._on_visible_changed(ch_id, state == Qt.CheckState.Checked.value)
        )
        visible_widget = QWidget()
        visible_layout = QHBoxLayout(visible_widget)
        visible_layout.addWidget(visible_checkbox)
        visible_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        visible_layout.setContentsMargins(0, 0, 0, 0)
        self._table.setCellWidget(row, 0, visible_widget)
        
        # 1: ID
        id_item = QTableWidgetItem(str(channel_id))
        id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, 1, id_item)
        
        # 2: 标签输入框
        label_edit = QLineEdit(channel.label)
        label_edit.textChanged.connect(
            lambda text, ch_id=channel_id: self._on_label_changed(ch_id, text)
        )
        self._table.setCellWidget(row, 2, label_edit)
        
        # 3: 颜色按钮
        color_btn = ColorButton(channel.color)
        color_btn.color_changed.connect(
            lambda color, ch_id=channel_id: self._on_color_changed(ch_id, color)
        )
        color_widget = QWidget()
        color_layout = QHBoxLayout(color_widget)
        color_layout.addWidget(color_btn)
        color_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        color_layout.setContentsMargins(0, 0, 0, 0)
        self._table.setCellWidget(row, 3, color_widget)
        
        # 4: 分组下拉框
        group_combo = QComboBox()
        group_combo.addItems(["default", "group1", "group2", "group3"])
        group_combo.setEditable(True)
        group_combo.setCurrentText(channel.group)
        group_combo.currentTextChanged.connect(
            lambda text, ch_id=channel_id: self._on_group_changed(ch_id, text)
        )
        self._table.setCellWidget(row, 4, group_combo)
        
        # 5: Y 偏移
        offset_item = QTableWidgetItem(f"{channel.y_offset:.1f}")
        offset_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, 5, offset_item)
        
        # 保存控件引用
        self._channel_widgets[channel_id] = {
            "visible": visible_checkbox,
            "label": label_edit,
            "color": color_btn,
            "group": group_combo,
            "offset_item": offset_item,
        }
    
    def _add_channel(self):
        """添加新通道"""
        # 找到未使用的最小 ID
        existing_ids = [ch.channel_id for ch in self._manager.get_all_channels()]
        new_id = 0
        while new_id in existing_ids:
            new_id += 1
        
        self._manager.add_channel(new_id)
    
    def _remove_channel(self):
        """移除选中的通道"""
        selected_rows = self._table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要移除的通道")
            return
        
        row = selected_rows[0].row()
        channel_id = int(self._table.item(row, 1).text())
        
        reply = QMessageBox.question(
            self,
            "确认移除",
            f"确定要移除通道 {channel_id} 吗？\n这将删除该通道的所有数据。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._manager.remove_channel(channel_id)
    
    def _on_visible_changed(self, channel_id: int, visible: bool):
        """可见性变更"""
        self._manager.update_channel_config(channel_id, visible=visible)
        self.channel_config_changed.emit(channel_id)
    
    def _on_label_changed(self, channel_id: int, label: str):
        """标签变更"""
        self._manager.update_channel_config(channel_id, label=label)
        self.channel_config_changed.emit(channel_id)
    
    def _on_color_changed(self, channel_id: int, color: str):
        """颜色变更"""
        self._manager.update_channel_config(channel_id, color=color)
        self.channel_config_changed.emit(channel_id)
    
    def _on_group_changed(self, channel_id: int, group: str):
        """分组变更"""
        self._manager.update_channel_config(channel_id, group=group)
        self.channel_config_changed.emit(channel_id)
    
    def _on_channel_config_changed(self, channel_id: int):
        """通道配置变更（外部）"""
        # 更新 UI（如果需要）
        pass
