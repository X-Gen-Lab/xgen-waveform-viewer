"""
协议配置面板 - V3.0

提供协议配置 UI：
- 协议类型选择
- 协议参数配置
- 自定义帧格式编辑
- 协议配置导入/导出
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QLabel, QLineEdit, QSpinBox, QCheckBox, QGroupBox, QFormLayout,
    QFileDialog, QMessageBox, QTextEdit, QTabWidget
)
from PyQt6.QtCore import pyqtSignal
import json
from pathlib import Path

from .protocol import ProtocolType, ProtocolFactory, FrameFormat, BinaryV2Parser, CustomBinaryParser, ASCIIParser


class ProtocolConfigPanel(QWidget):
    """协议配置面板"""
    
    # 信号
    protocol_changed = pyqtSignal(object)  # ProtocolParser
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_parser = None
        self._setup_ui()
    
    def _setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        
        # 标题
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("<b>协议配置</b>"))
        title_layout.addStretch()
        
        # 导入/导出按钮
        self._btn_import = QPushButton("导入配置")
        self._btn_import.clicked.connect(self._import_config)
        title_layout.addWidget(self._btn_import)
        
        self._btn_export = QPushButton("导出配置")
        self._btn_export.clicked.connect(self._export_config)
        title_layout.addWidget(self._btn_export)
        
        layout.addLayout(title_layout)
        
        # 协议类型选择
        protocol_group = QGroupBox("协议类型")
        protocol_layout = QFormLayout()
        
        self._protocol_combo = QComboBox()
        self._protocol_combo.addItems([
            "Binary V2 (默认)",
            "Binary Custom (自定义)",
            "ASCII Text",
        ])
        self._protocol_combo.currentIndexChanged.connect(self._on_protocol_type_changed)
        protocol_layout.addRow("类型:", self._protocol_combo)
        
        protocol_group.setLayout(protocol_layout)
        layout.addWidget(protocol_group)
        
        # 创建标签页用于不同协议的配置
        self._config_tabs = QTabWidget()
        
        # Binary V2 配置（只读，显示当前协议参数）
        self._setup_binary_v2_tab()
        
        # Binary Custom 配置
        self._setup_binary_custom_tab()
        
        # ASCII 配置
        self._setup_ascii_tab()
        
        layout.addWidget(self._config_tabs)
        
        # 应用按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self._btn_apply = QPushButton("应用配置")
        self._btn_apply.clicked.connect(self._apply_config)
        btn_layout.addWidget(self._btn_apply)
        
        self._btn_reset = QPushButton("重置为默认")
        self._btn_reset.clicked.connect(self._reset_to_default)
        btn_layout.addWidget(self._btn_reset)
        
        layout.addLayout(btn_layout)
        
        # 默认选择 Binary V2
        self._protocol_combo.setCurrentIndex(0)
        self._on_protocol_type_changed(0)
    
    def _setup_binary_v2_tab(self):
        """设置 Binary V2 配置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        info_label = QLabel(
            "<b>Binary V2 协议</b><br>"
            "这是默认的二进制协议，参数已固定。<br><br>"
            "<b>帧格式:</b><br>"
            "• 同步头: 0xA5 0x5A<br>"
            "• 序列号: 4 字节 (uint32 LE)<br>"
            "• 采样点数: 2 字节 (uint16 LE)<br>"
            "• 采样数据: N × 2 字节 (uint16 LE)<br>"
            "• CRC-16: 2 字节 (CCITT, poly=0x1021)"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        layout.addStretch()
        
        self._config_tabs.addTab(tab, "Binary V2")
    
    def _setup_binary_custom_tab(self):
        """设置自定义二进制协议配置标签页"""
        tab = QWidget()
        layout = QFormLayout(tab)
        
        # 同步头
        self._custom_sync_edit = QLineEdit("A55A")
        self._custom_sync_edit.setPlaceholderText("十六进制，如: A55A")
        layout.addRow("同步头 (Hex):", self._custom_sync_edit)
        
        # 元数据大小
        self._custom_meta_size_spin = QSpinBox()
        self._custom_meta_size_spin.setRange(1, 256)
        self._custom_meta_size_spin.setValue(6)
        layout.addRow("元数据大小 (字节):", self._custom_meta_size_spin)
        
        # CRC
        self._custom_has_crc_check = QCheckBox("启用 CRC")
        self._custom_has_crc_check.setChecked(True)
        layout.addRow("", self._custom_has_crc_check)
        
        self._custom_crc_poly_edit = QLineEdit("0x1021")
        layout.addRow("CRC 多项式:", self._custom_crc_poly_edit)
        
        self._custom_crc_init_edit = QLineEdit("0xFFFF")
        layout.addRow("CRC 初始值:", self._custom_crc_init_edit)
        
        # 采样参数
        self._custom_sample_size_spin = QSpinBox()
        self._custom_sample_size_spin.setRange(1, 4)
        self._custom_sample_size_spin.setValue(2)
        layout.addRow("采样点大小 (字节):", self._custom_sample_size_spin)
        
        self._custom_endian_combo = QComboBox()
        self._custom_endian_combo.addItems(["Little Endian", "Big Endian"])
        layout.addRow("字节序:", self._custom_endian_combo)
        
        # 序列号
        self._custom_has_seq_check = QCheckBox("包含序列号")
        self._custom_has_seq_check.setChecked(True)
        layout.addRow("", self._custom_has_seq_check)
        
        self._custom_seq_offset_spin = QSpinBox()
        self._custom_seq_offset_spin.setRange(0, 255)
        self._custom_seq_offset_spin.setValue(0)
        layout.addRow("序列号偏移:", self._custom_seq_offset_spin)
        
        self._custom_seq_size_spin = QSpinBox()
        self._custom_seq_size_spin.setRange(1, 8)
        self._custom_seq_size_spin.setValue(4)
        layout.addRow("序列号大小 (字节):", self._custom_seq_size_spin)
        
        # 通道 ID
        self._custom_has_channel_check = QCheckBox("包含通道 ID")
        self._custom_has_channel_check.setChecked(False)
        layout.addRow("", self._custom_has_channel_check)
        
        self._custom_channel_offset_spin = QSpinBox()
        self._custom_channel_offset_spin.setRange(0, 255)
        self._custom_channel_offset_spin.setValue(0)
        layout.addRow("通道 ID 偏移:", self._custom_channel_offset_spin)
        
        # 采样点数偏移
        self._custom_sample_count_offset_spin = QSpinBox()
        self._custom_sample_count_offset_spin.setRange(0, 255)
        self._custom_sample_count_offset_spin.setValue(4)
        layout.addRow("采样点数偏移:", self._custom_sample_count_offset_spin)
        
        # 最大采样点数
        self._custom_max_samples_spin = QSpinBox()
        self._custom_max_samples_spin.setRange(1, 65535)
        self._custom_max_samples_spin.setValue(1024)
        layout.addRow("最大采样点数:", self._custom_max_samples_spin)
        
        self._config_tabs.addTab(tab, "Binary Custom")
    
    def _setup_ascii_tab(self):
        """设置 ASCII 协议配置标签页"""
        tab = QWidget()
        layout = QFormLayout(tab)
        
        # 行终止符
        self._ascii_terminator_combo = QComboBox()
        self._ascii_terminator_combo.addItems(["\\n (LF)", "\\r\\n (CRLF)", "\\r (CR)"])
        layout.addRow("行终止符:", self._ascii_terminator_combo)
        
        # 分隔符
        self._ascii_delimiter_edit = QLineEdit(",")
        layout.addRow("数值分隔符:", self._ascii_delimiter_edit)
        
        # 通道前缀
        self._ascii_has_prefix_check = QCheckBox("使用通道前缀")
        self._ascii_has_prefix_check.setChecked(False)
        layout.addRow("", self._ascii_has_prefix_check)
        
        self._ascii_prefix_edit = QLineEdit("#CH")
        self._ascii_prefix_edit.setPlaceholderText("例如: #CH")
        layout.addRow("通道前缀:", self._ascii_prefix_edit)
        
        # 示例说明
        example_label = QLabel(
            "<b>示例格式:</b><br>"
            "• 简单: 1234,5678,9012<br>"
            "• 带前缀: #CH0:1234,5678,9012<br>"
            "• 多行:<br>"
            "&nbsp;&nbsp;1234,5678<br>"
            "&nbsp;&nbsp;3456,7890"
        )
        example_label.setWordWrap(True)
        layout.addRow("", example_label)
        
        self._config_tabs.addTab(tab, "ASCII Text")
    
    def _on_protocol_type_changed(self, index: int):
        """协议类型变更"""
        self._config_tabs.setCurrentIndex(index)
    
    def _create_parser_from_ui(self):
        """从 UI 创建协议解析器"""
        protocol_index = self._protocol_combo.currentIndex()
        
        if protocol_index == 0:
            # Binary V2
            return BinaryV2Parser()
        
        elif protocol_index == 1:
            # Binary Custom
            try:
                frame_format = FrameFormat(
                    sync_bytes=bytes.fromhex(self._custom_sync_edit.text()),
                    meta_size=self._custom_meta_size_spin.value(),
                    has_crc=self._custom_has_crc_check.isChecked(),
                    crc_poly=int(self._custom_crc_poly_edit.text(), 16),
                    crc_init=int(self._custom_crc_init_edit.text(), 16),
                    sample_size=self._custom_sample_size_spin.value(),
                    endianness="little" if self._custom_endian_combo.currentIndex() == 0 else "big",
                    has_sequence=self._custom_has_seq_check.isChecked(),
                    sequence_offset=self._custom_seq_offset_spin.value(),
                    sequence_size=self._custom_seq_size_spin.value(),
                    has_channel_id=self._custom_has_channel_check.isChecked(),
                    channel_id_offset=self._custom_channel_offset_spin.value(),
                    sample_count_offset=self._custom_sample_count_offset_spin.value(),
                    max_samples=self._custom_max_samples_spin.value(),
                )
                
                config = {"frame_format": frame_format.to_dict()}
                parser = CustomBinaryParser(config)
                parser.format = frame_format
                return parser
            
            except ValueError as e:
                QMessageBox.warning(self, "配置错误", f"无效的配置参数: {e}")
                return None
        
        elif protocol_index == 2:
            # ASCII
            terminator_map = {0: b"\n", 1: b"\r\n", 2: b"\r"}
            
            config = {
                "line_terminator": terminator_map[self._ascii_terminator_combo.currentIndex()],
                "delimiter": self._ascii_delimiter_edit.text(),
                "has_channel_prefix": self._ascii_has_prefix_check.isChecked(),
                "channel_prefix": self._ascii_prefix_edit.text(),
            }
            
            return ASCIIParser(config)
        
        return None
    
    def _apply_config(self):
        """应用配置"""
        parser = self._create_parser_from_ui()
        if parser:
            self._current_parser = parser
            self.protocol_changed.emit(parser)
            QMessageBox.information(self, "成功", "协议配置已应用")
    
    def _reset_to_default(self):
        """重置为默认配置"""
        reply = QMessageBox.question(
            self,
            "确认重置",
            "确定要重置为默认配置吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._protocol_combo.setCurrentIndex(0)
            self._apply_config()
    
    def _import_config(self):
        """导入协议配置"""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "导入协议配置",
            str(Path.home()),
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if not filepath:
            return
        
        try:
            parser = ProtocolFactory.load_from_file(filepath)
            self._load_parser_to_ui(parser)
            QMessageBox.information(self, "成功", "协议配置已导入")
        
        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"无法导入协议配置:\n{e}")
    
    def _export_config(self):
        """导出协议配置"""
        if not self._current_parser:
            QMessageBox.warning(self, "警告", "请先应用配置")
            return
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "导出协议配置",
            str(Path.home() / "protocol_config.json"),
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if not filepath:
            return
        
        try:
            ProtocolFactory.save_to_file(self._current_parser, filepath)
            QMessageBox.information(self, "成功", f"协议配置已导出到:\n{filepath}")
        
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"无法导出协议配置:\n{e}")
    
    def _load_parser_to_ui(self, parser):
        """将解析器配置加载到 UI"""
        if isinstance(parser, BinaryV2Parser):
            self._protocol_combo.setCurrentIndex(0)
        
        elif isinstance(parser, CustomBinaryParser):
            self._protocol_combo.setCurrentIndex(1)
            
            if hasattr(parser, 'format'):
                fmt = parser.format
                self._custom_sync_edit.setText(fmt.sync_bytes.hex().upper())
                self._custom_meta_size_spin.setValue(fmt.meta_size)
                self._custom_has_crc_check.setChecked(fmt.has_crc)
                self._custom_crc_poly_edit.setText(hex(fmt.crc_poly))
                self._custom_crc_init_edit.setText(hex(fmt.crc_init))
                self._custom_sample_size_spin.setValue(fmt.sample_size)
                self._custom_endian_combo.setCurrentIndex(0 if fmt.endianness == "little" else 1)
                self._custom_has_seq_check.setChecked(fmt.has_sequence)
                self._custom_seq_offset_spin.setValue(fmt.sequence_offset)
                self._custom_seq_size_spin.setValue(fmt.sequence_size)
                self._custom_has_channel_check.setChecked(fmt.has_channel_id)
                self._custom_channel_offset_spin.setValue(fmt.channel_id_offset)
                self._custom_sample_count_offset_spin.setValue(fmt.sample_count_offset)
                self._custom_max_samples_spin.setValue(fmt.max_samples)
        
        elif isinstance(parser, ASCIIParser):
            self._protocol_combo.setCurrentIndex(2)
            
            config = parser.config
            terminator = config.get("line_terminator", b"\n")
            if terminator == b"\n":
                self._ascii_terminator_combo.setCurrentIndex(0)
            elif terminator == b"\r\n":
                self._ascii_terminator_combo.setCurrentIndex(1)
            elif terminator == b"\r":
                self._ascii_terminator_combo.setCurrentIndex(2)
            
            self._ascii_delimiter_edit.setText(config.get("delimiter", ","))
            self._ascii_has_prefix_check.setChecked(config.get("has_channel_prefix", False))
            self._ascii_prefix_edit.setText(config.get("channel_prefix", "#CH"))
        
        self._current_parser = parser
    
    def get_current_parser(self):
        """获取当前解析器"""
        return self._current_parser
