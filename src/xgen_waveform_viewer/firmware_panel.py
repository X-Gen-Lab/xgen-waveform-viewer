"""
固件配置面板 - V3.0

提供固件配置和管理 UI：
- 固件版本显示
- 固件配置参数编辑
- 固件更新（OTA）
- 兼容性检查
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox, QComboBox,
    QCheckBox, QProgressBar, QFileDialog, QMessageBox, QTextEdit
)
from PyQt6.QtCore import pyqtSignal, QTimer
from pathlib import Path

from .firmware_config import (
    FirmwareConfigManager, FirmwareVersion, FirmwareConfig,
    check_firmware_compatibility
)


class FirmwarePanel(QWidget):
    """固件配置面板"""
    
    # 信号
    config_applied = pyqtSignal(object)  # FirmwareConfig
    
    def __init__(self, config_manager: FirmwareConfigManager = None, parent=None):
        super().__init__(parent)
        self._config_manager = config_manager
        self._current_version: FirmwareVersion = None
        self._current_config: FirmwareConfig = None
        
        self._setup_ui()
        
        if self._config_manager:
            self._connect_signals()
    
    def set_config_manager(self, config_manager: FirmwareConfigManager):
        """设置配置管理器"""
        self._config_manager = config_manager
        self._connect_signals()
    
    def _setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        
        # 标题
        layout.addWidget(QLabel("<b>固件配置与管理</b>"))
        
        # 固件版本信息组
        version_group = QGroupBox("固件版本信息")
        version_layout = QVBoxLayout()
        
        self._version_label = QLabel("未连接")
        self._version_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        version_layout.addWidget(self._version_label)
        
        self._version_details = QLabel("")
        self._version_details.setWordWrap(True)
        version_layout.addWidget(self._version_details)
        
        version_btn_layout = QHBoxLayout()
        self._btn_get_version = QPushButton("获取版本信息")
        self._btn_get_version.clicked.connect(self._get_firmware_version)
        version_btn_layout.addWidget(self._btn_get_version)
        
        self._btn_check_compat = QPushButton("检查兼容性")
        self._btn_check_compat.clicked.connect(self._check_compatibility)
        version_btn_layout.addWidget(self._btn_check_compat)
        version_btn_layout.addStretch()
        
        version_layout.addLayout(version_btn_layout)
        version_group.setLayout(version_layout)
        layout.addWidget(version_group)
        
        # 固件配置参数组
        config_group = QGroupBox("配置参数")
        config_layout = QFormLayout()
        
        # 采样率
        self._sample_rate_spin = QSpinBox()
        self._sample_rate_spin.setRange(100, 1000000)
        self._sample_rate_spin.setValue(10000)
        self._sample_rate_spin.setSuffix(" Hz")
        config_layout.addRow("采样率:", self._sample_rate_spin)
        
        # 帧长
        self._frame_length_spin = QSpinBox()
        self._frame_length_spin.setRange(1, 4096)
        self._frame_length_spin.setValue(256)
        self._frame_length_spin.setSuffix(" samples")
        config_layout.addRow("帧长:", self._frame_length_spin)
        
        # 通道数
        self._channel_count_spin = QSpinBox()
        self._channel_count_spin.setRange(1, 16)
        self._channel_count_spin.setValue(1)
        config_layout.addRow("通道数:", self._channel_count_spin)
        
        # 通道掩码（十六进制输入）
        self._channel_mask_label = QLabel("0x0001")
        config_layout.addRow("通道掩码:", self._channel_mask_label)
        
        # ADC 分辨率
        self._adc_resolution_spin = QSpinBox()
        self._adc_resolution_spin.setRange(8, 16)
        self._adc_resolution_spin.setValue(12)
        self._adc_resolution_spin.setSuffix(" bits")
        config_layout.addRow("ADC 分辨率:", self._adc_resolution_spin)
        
        # ADC 参考电压
        self._adc_vref_spin = QDoubleSpinBox()
        self._adc_vref_spin.setRange(0.1, 10.0)
        self._adc_vref_spin.setValue(3.3)
        self._adc_vref_spin.setDecimals(2)
        self._adc_vref_spin.setSingleStep(0.1)
        self._adc_vref_spin.setSuffix(" V")
        config_layout.addRow("ADC 参考电压:", self._adc_vref_spin)
        
        # 触发配置
        self._trigger_enabled_check = QCheckBox("启用触发")
        config_layout.addRow("", self._trigger_enabled_check)
        
        self._trigger_level_spin = QSpinBox()
        self._trigger_level_spin.setRange(0, 65535)
        self._trigger_level_spin.setValue(2048)
        config_layout.addRow("触发电平:", self._trigger_level_spin)
        
        self._trigger_edge_combo = QComboBox()
        self._trigger_edge_combo.addItems(["上升沿 (Rising)", "下降沿 (Falling)", "双边沿 (Both)"])
        config_layout.addRow("触发边沿:", self._trigger_edge_combo)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # 配置操作按钮
        config_btn_layout = QHBoxLayout()
        
        self._btn_get_config = QPushButton("读取配置")
        self._btn_get_config.clicked.connect(self._get_firmware_config)
        config_btn_layout.addWidget(self._btn_get_config)
        
        self._btn_set_config = QPushButton("写入配置")
        self._btn_set_config.clicked.connect(self._set_firmware_config)
        config_btn_layout.addWidget(self._btn_set_config)
        
        self._btn_reset = QPushButton("重置设备")
        self._btn_reset.clicked.connect(self._reset_device)
        config_btn_layout.addWidget(self._btn_reset)
        
        config_btn_layout.addStretch()
        layout.addLayout(config_btn_layout)
        
        # 固件更新（OTA）组
        ota_group = QGroupBox("固件更新 (OTA)")
        ota_layout = QVBoxLayout()
        
        ota_btn_layout = QHBoxLayout()
        self._btn_select_firmware = QPushButton("选择固件文件")
        self._btn_select_firmware.clicked.connect(self._select_firmware_file)
        ota_btn_layout.addWidget(self._btn_select_firmware)
        
        self._firmware_path_label = QLabel("未选择文件")
        ota_btn_layout.addWidget(self._firmware_path_label)
        ota_btn_layout.addStretch()
        
        ota_layout.addLayout(ota_btn_layout)
        
        self._ota_progress = QProgressBar()
        self._ota_progress.setVisible(False)
        ota_layout.addWidget(self._ota_progress)
        
        self._btn_start_ota = QPushButton("开始更新")
        self._btn_start_ota.setEnabled(False)
        self._btn_start_ota.clicked.connect(self._start_ota_update)
        ota_layout.addWidget(self._btn_start_ota)
        
        ota_warning = QLabel(
            "⚠️ <b>警告:</b> 固件更新过程中请勿断开连接或关闭应用。<br>"
            "更新失败可能导致设备无法正常工作。"
        )
        ota_warning.setWordWrap(True)
        ota_warning.setStyleSheet("color: #ff8800;")
        ota_layout.addWidget(ota_warning)
        
        ota_group.setLayout(ota_layout)
        layout.addWidget(ota_group)
        
        # 日志区域
        log_group = QGroupBox("操作日志")
        log_layout = QVBoxLayout()
        
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMaximumHeight(120)
        log_layout.addWidget(self._log_text)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        layout.addStretch()
        
        # 初始状态：禁用所有按钮（需要先连接）
        self._set_buttons_enabled(False)
    
    def _connect_signals(self):
        """连接信号"""
        if not self._config_manager:
            return
        
        self._config_manager.version_received.connect(self._on_version_received)
        self._config_manager.config_received.connect(self._on_config_received)
        self._config_manager.config_updated.connect(self._on_config_updated)
        self._config_manager.error_occurred.connect(self._on_error)
        self._config_manager.ota_progress.connect(self._on_ota_progress)
        self._config_manager.ota_completed.connect(self._on_ota_completed)
        
        # 启用按钮
        self._set_buttons_enabled(True)
    
    def _set_buttons_enabled(self, enabled: bool):
        """设置按钮启用状态"""
        self._btn_get_version.setEnabled(enabled)
        self._btn_check_compat.setEnabled(enabled)
        self._btn_get_config.setEnabled(enabled)
        self._btn_set_config.setEnabled(enabled)
        self._btn_reset.setEnabled(enabled)
        self._btn_select_firmware.setEnabled(enabled)
    
    def _log(self, message: str):
        """添加日志"""
        self._log_text.append(message)
    
    def _get_firmware_version(self):
        """获取固件版本"""
        if not self._config_manager:
            QMessageBox.warning(self, "警告", "请先连接设备")
            return
        
        self._log("正在获取固件版本...")
        success = self._config_manager.get_firmware_version()
        
        if success:
            # 处理响应（异步）
            QTimer.singleShot(2000, self._check_version_response)
        else:
            self._log("❌ 发送获取版本命令失败")
    
    def _check_version_response(self):
        """检查版本响应"""
        if self._config_manager:
            self._config_manager.process_response()
    
    def _on_version_received(self, version: FirmwareVersion):
        """版本信息接收"""
        self._current_version = version
        self._version_label.setText(f"版本: {version}")
        
        details = []
        if version.commit_hash:
            details.append(f"Commit: {version.commit_hash[:8]}")
        if version.build_date:
            details.append(f"构建日期: {version.build_date}")
        
        self._version_details.setText("<br>".join(details))
        self._log(f"✓ 固件版本: {version}")
    
    def _check_compatibility(self):
        """检查兼容性"""
        if not self._current_version:
            QMessageBox.warning(self, "警告", "请先获取固件版本")
            return
        
        # 定义最小要求版本（示例）
        min_version = FirmwareVersion(3, 0, 0)
        
        is_compatible, message = check_firmware_compatibility(self._current_version, min_version)
        
        if is_compatible:
            QMessageBox.information(self, "兼容性检查", f"✓ {message}")
            self._log(f"✓ {message}")
        else:
            QMessageBox.warning(self, "兼容性检查", f"⚠️ {message}")
            self._log(f"⚠️ {message}")
    
    def _get_firmware_config(self):
        """读取固件配置"""
        if not self._config_manager:
            QMessageBox.warning(self, "警告", "请先连接设备")
            return
        
        self._log("正在读取固件配置...")
        success = self._config_manager.get_firmware_config()
        
        if success:
            QTimer.singleShot(2000, lambda: self._config_manager.process_response())
        else:
            self._log("❌ 发送读取配置命令失败")
    
    def _on_config_received(self, config: FirmwareConfig):
        """配置信息接收"""
        self._current_config = config
        
        # 更新 UI
        self._sample_rate_spin.setValue(config.sample_rate)
        self._frame_length_spin.setValue(config.frame_length)
        self._channel_count_spin.setValue(config.channel_count)
        self._channel_mask_label.setText(f"0x{config.channel_mask:04X}")
        self._adc_resolution_spin.setValue(config.adc_resolution)
        self._adc_vref_spin.setValue(config.adc_vref)
        self._trigger_enabled_check.setChecked(config.trigger_enabled)
        self._trigger_level_spin.setValue(config.trigger_level)
        
        edge_map = {"rising": 0, "falling": 1, "both": 2}
        self._trigger_edge_combo.setCurrentIndex(edge_map.get(config.trigger_edge, 0))
        
        self._log(f"✓ 配置已读取: {config.sample_rate}Hz, {config.frame_length} samples/frame")
    
    def _set_firmware_config(self):
        """写入固件配置"""
        if not self._config_manager:
            QMessageBox.warning(self, "警告", "请先连接设备")
            return
        
        # 从 UI 构建配置
        edge_map = {0: "rising", 1: "falling", 2: "both"}
        
        config = FirmwareConfig(
            sample_rate=self._sample_rate_spin.value(),
            frame_length=self._frame_length_spin.value(),
            channel_count=self._channel_count_spin.value(),
            channel_mask=(1 << self._channel_count_spin.value()) - 1,  # 自动生成掩码
            adc_resolution=self._adc_resolution_spin.value(),
            adc_vref=self._adc_vref_spin.value(),
            trigger_enabled=self._trigger_enabled_check.isChecked(),
            trigger_level=self._trigger_level_spin.value(),
            trigger_edge=edge_map[self._trigger_edge_combo.currentIndex()],
        )
        
        reply = QMessageBox.question(
            self,
            "确认写入",
            f"确定要写入以下配置吗？\n\n"
            f"采样率: {config.sample_rate} Hz\n"
            f"帧长: {config.frame_length} samples\n"
            f"通道数: {config.channel_count}\n"
            f"ADC 分辨率: {config.adc_resolution} bits\n"
            f"触发: {'启用' if config.trigger_enabled else '禁用'}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._log("正在写入配置...")
            success = self._config_manager.set_firmware_config(config)
            
            if success:
                QTimer.singleShot(2000, lambda: self._config_manager.process_response())
            else:
                self._log("❌ 发送写入配置命令失败")
    
    def _on_config_updated(self, success: bool):
        """配置更新响应"""
        if success:
            self._log("✓ 配置已成功写入")
            QMessageBox.information(self, "成功", "配置已成功写入到设备")
        else:
            self._log("❌ 配置写入失败")
            QMessageBox.warning(self, "失败", "配置写入失败，请检查设备状态")
    
    def _reset_device(self):
        """重置设备"""
        if not self._config_manager:
            QMessageBox.warning(self, "警告", "请先连接设备")
            return
        
        reply = QMessageBox.question(
            self,
            "确认重置",
            "确定要重置设备吗？\n设备将重新启动。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._log("正在重置设备...")
            self._config_manager.reset_device()
            self._log("✓ 重置命令已发送")
    
    def _select_firmware_file(self):
        """选择固件文件"""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "选择固件文件",
            str(Path.home()),
            "Firmware Files (*.bin *.hex *.elf);;All Files (*.*)"
        )
        
        if filepath:
            self._firmware_path_label.setText(Path(filepath).name)
            self._firmware_path_label.setToolTip(filepath)
            self._firmware_path = filepath
            self._btn_start_ota.setEnabled(True)
            self._log(f"已选择固件: {Path(filepath).name}")
    
    def _start_ota_update(self):
        """开始 OTA 更新"""
        if not self._config_manager:
            QMessageBox.warning(self, "警告", "请先连接设备")
            return
        
        if not hasattr(self, '_firmware_path'):
            QMessageBox.warning(self, "警告", "请先选择固件文件")
            return
        
        reply = QMessageBox.warning(
            self,
            "确认更新",
            "⚠️ 固件更新过程中请勿断开连接！\n"
            "更新失败可能导致设备无法使用。\n\n"
            "确定要继续吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                with open(self._firmware_path, 'rb') as f:
                    firmware_data = f.read()
                
                self._log(f"开始 OTA 更新，固件大小: {len(firmware_data)} bytes")
                self._ota_progress.setVisible(True)
                self._ota_progress.setValue(0)
                self._btn_start_ota.setEnabled(False)
                
                # 在后台线程执行（实际应该使用 QThread）
                self._config_manager.ota_update(firmware_data)
            
            except Exception as e:
                self._log(f"❌ 读取固件文件失败: {e}")
                QMessageBox.critical(self, "错误", f"读取固件文件失败:\n{e}")
    
    def _on_ota_progress(self, current: int, total: int):
        """OTA 进度更新"""
        progress = int(current * 100 / total)
        self._ota_progress.setValue(progress)
        self._log(f"OTA 进度: {progress}% ({current}/{total} bytes)")
    
    def _on_ota_completed(self, success: bool):
        """OTA 完成"""
        self._ota_progress.setVisible(False)
        self._btn_start_ota.setEnabled(True)
        
        if success:
            self._log("✓ OTA 更新成功！设备将重启...")
            QMessageBox.information(self, "成功", "固件更新成功！\n设备将自动重启。")
        else:
            self._log("❌ OTA 更新失败")
            QMessageBox.critical(self, "失败", "固件更新失败！\n请检查固件文件和设备状态。")
    
    def _on_error(self, message: str):
        """错误处理"""
        self._log(f"❌ 错误: {message}")
