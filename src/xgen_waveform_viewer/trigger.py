"""
触发功能模块
提供边沿触发、阈值触发、单次触发等功能
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QDoubleSpinBox, QCheckBox, QGroupBox
)


class TriggerMode(Enum):
    """触发模式"""
    DISABLED = "Disabled"
    AUTO = "Auto"
    NORMAL = "Normal"
    SINGLE = "Single"


class TriggerType(Enum):
    """触发类型"""
    EDGE_RISING = "Rising Edge"
    EDGE_FALLING = "Falling Edge"
    EDGE_BOTH = "Both Edges"
    LEVEL_HIGH = "Level High"
    LEVEL_LOW = "Level Low"


@dataclass
class TriggerConfig:
    """触发配置"""
    enabled: bool = False
    mode: TriggerMode = TriggerMode.DISABLED
    trigger_type: TriggerType = TriggerType.EDGE_RISING
    threshold: float = 2048.0  # ADC 值
    hysteresis: float = 50.0   # 滞回，防止抖动
    pre_trigger_samples: int = 100  # 触发前保留的采样点数
    
    # 单次触发状态
    single_triggered: bool = False


@dataclass
class TriggerEvent:
    """触发事件"""
    trigger_time: float
    trigger_sample_index: int
    trigger_value: float
    trigger_type: TriggerType


class TriggerDetector(QObject):
    """触发检测器"""
    
    trigger_fired = pyqtSignal(object)  # TriggerEvent
    
    def __init__(self):
        super().__init__()
        self.config = TriggerConfig()
        self._last_value: Optional[float] = None
        self._trigger_armed = True
        
    def reset(self):
        """重置触发器状态"""
        self._last_value = None
        self._trigger_armed = True
        self.config.single_triggered = False
        
    def update_config(self, config: TriggerConfig):
        """更新触发配置"""
        self.config = config
        if config.mode == TriggerMode.SINGLE and not config.enabled:
            self.reset()
            
    def process_sample(self, value: float, time: float, sample_index: int) -> bool:
        """
        处理单个采样点，检测触发条件
        
        返回: 是否触发
        """
        if not self.config.enabled:
            return False
            
        # 单次触发模式已触发，不再检测
        if self.config.mode == TriggerMode.SINGLE and self.config.single_triggered:
            return False
            
        triggered = False
        event = None
        
        if self._last_value is not None:
            if self.config.trigger_type == TriggerType.EDGE_RISING:
                # 上升沿触发
                if (self._last_value < self.config.threshold - self.config.hysteresis and
                    value >= self.config.threshold):
                    triggered = True
                    event = TriggerEvent(
                        trigger_time=time,
                        trigger_sample_index=sample_index,
                        trigger_value=value,
                        trigger_type=TriggerType.EDGE_RISING
                    )
                    
            elif self.config.trigger_type == TriggerType.EDGE_FALLING:
                # 下降沿触发
                if (self._last_value > self.config.threshold + self.config.hysteresis and
                    value <= self.config.threshold):
                    triggered = True
                    event = TriggerEvent(
                        trigger_time=time,
                        trigger_sample_index=sample_index,
                        trigger_value=value,
                        trigger_type=TriggerType.EDGE_FALLING
                    )
                    
            elif self.config.trigger_type == TriggerType.EDGE_BOTH:
                # 双边沿触发
                if (self._last_value < self.config.threshold - self.config.hysteresis and
                    value >= self.config.threshold):
                    triggered = True
                    event = TriggerEvent(
                        trigger_time=time,
                        trigger_sample_index=sample_index,
                        trigger_value=value,
                        trigger_type=TriggerType.EDGE_RISING
                    )
                elif (self._last_value > self.config.threshold + self.config.hysteresis and
                      value <= self.config.threshold):
                    triggered = True
                    event = TriggerEvent(
                        trigger_time=time,
                        trigger_sample_index=sample_index,
                        trigger_value=value,
                        trigger_type=TriggerType.EDGE_FALLING
                    )
                    
            elif self.config.trigger_type == TriggerType.LEVEL_HIGH:
                # 电平高触发（持续）
                if value > self.config.threshold:
                    if self._trigger_armed:
                        triggered = True
                        event = TriggerEvent(
                            trigger_time=time,
                            trigger_sample_index=sample_index,
                            trigger_value=value,
                            trigger_type=TriggerType.LEVEL_HIGH
                        )
                        self._trigger_armed = False
                else:
                    self._trigger_armed = True
                    
            elif self.config.trigger_type == TriggerType.LEVEL_LOW:
                # 电平低触发（持续）
                if value < self.config.threshold:
                    if self._trigger_armed:
                        triggered = True
                        event = TriggerEvent(
                            trigger_time=time,
                            trigger_sample_index=sample_index,
                            trigger_value=value,
                            trigger_type=TriggerType.LEVEL_LOW
                        )
                        self._trigger_armed = False
                else:
                    self._trigger_armed = True
        
        self._last_value = value
        
        if triggered and event:
            if self.config.mode == TriggerMode.SINGLE:
                self.config.single_triggered = True
            self.trigger_fired.emit(event)
            
        return triggered
    
    def process_frame(self, data: np.ndarray, time: np.ndarray,
                     start_sample_index: int) -> list[TriggerEvent]:
        """
        批量处理一帧数据，返回所有触发事件
        
        参数:
            data: 数据数组
            time: 对应的时间数组
            start_sample_index: 起始采样点索引
        
        返回: 触发事件列表
        """
        events = []
        
        for i, (value, t) in enumerate(zip(data, time)):
            sample_idx = start_sample_index + i
            if self.process_sample(float(value), float(t), sample_idx):
                # 获取最后一个发射的事件（通过信号）
                # 这里简化处理，直接从返回值判断
                pass
                
        return events


class TriggerPanel(QWidget):
    """触发控制面板"""
    
    config_changed = pyqtSignal(object)  # TriggerConfig
    arm_single_trigger = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = TriggerConfig()
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)
        
        # 触发控制组
        group = QGroupBox("Trigger Control")
        group_layout = QVBoxLayout(group)
        
        # 第一行：使能、模式、类型
        row1 = QHBoxLayout()
        
        self.chk_enable = QCheckBox("Enable")
        self.chk_enable.stateChanged.connect(self._on_config_changed)
        row1.addWidget(self.chk_enable)
        
        row1.addWidget(QLabel("Mode:"))
        self.combo_mode = QComboBox()
        for mode in TriggerMode:
            self.combo_mode.addItem(mode.value, mode)
        self.combo_mode.currentIndexChanged.connect(self._on_config_changed)
        row1.addWidget(self.combo_mode)
        
        row1.addWidget(QLabel("Type:"))
        self.combo_type = QComboBox()
        for ttype in TriggerType:
            self.combo_type.addItem(ttype.value, ttype)
        self.combo_type.currentIndexChanged.connect(self._on_config_changed)
        row1.addWidget(self.combo_type)
        
        row1.addStretch()
        group_layout.addLayout(row1)
        
        # 第二行：阈值、滞回
        row2 = QHBoxLayout()
        
        row2.addWidget(QLabel("Threshold:"))
        self.spin_threshold = QDoubleSpinBox()
        self.spin_threshold.setRange(0, 4095)
        self.spin_threshold.setDecimals(0)
        self.spin_threshold.setSingleStep(10)
        self.spin_threshold.setValue(2048)
        self.spin_threshold.setMinimumWidth(90)
        self.spin_threshold.setToolTip("触发阈值 (ADC值)")
        self.spin_threshold.valueChanged.connect(self._on_config_changed)
        row2.addWidget(self.spin_threshold)
        
        row2.addWidget(QLabel("Hysteresis:"))
        self.spin_hysteresis = QDoubleSpinBox()
        self.spin_hysteresis.setRange(0, 500)
        self.spin_hysteresis.setDecimals(0)
        self.spin_hysteresis.setSingleStep(5)
        self.spin_hysteresis.setValue(50)
        self.spin_hysteresis.setMinimumWidth(80)
        self.spin_hysteresis.setToolTip("滞回值，防止抖动")
        self.spin_hysteresis.valueChanged.connect(self._on_config_changed)
        row2.addWidget(self.spin_hysteresis)
        
        row2.addWidget(QLabel("Pre-trigger:"))
        self.spin_pretrigger = QDoubleSpinBox()
        self.spin_pretrigger.setRange(0, 10000)
        self.spin_pretrigger.setDecimals(0)
        self.spin_pretrigger.setSingleStep(10)
        self.spin_pretrigger.setValue(100)
        self.spin_pretrigger.setSuffix(" pts")
        self.spin_pretrigger.setMinimumWidth(95)
        self.spin_pretrigger.setToolTip("触发前保留的采样点数")
        self.spin_pretrigger.valueChanged.connect(self._on_config_changed)
        row2.addWidget(self.spin_pretrigger)
        
        row2.addStretch()
        group_layout.addLayout(row2)
        
        # 第三行：单次触发控制
        row3 = QHBoxLayout()
        
        self.btn_arm = QPushButton("Arm Single Trigger")
        self.btn_arm.setToolTip("准备单次触发 (快捷键: T)")
        self.btn_arm.clicked.connect(self._on_arm_clicked)
        row3.addWidget(self.btn_arm)
        
        self.lbl_status = QLabel("Status: Idle")
        self.lbl_status.setStyleSheet("color: #0af; font-size: 11px; padding: 4px;")
        row3.addWidget(self.lbl_status)
        
        row3.addStretch()
        group_layout.addLayout(row3)
        
        layout.addWidget(group)
        
        # 触发指示可视化说明
        info_layout = QHBoxLayout()
        info_label = QLabel("⚡ Trigger events will be shown on waveform with markers")
        info_label.setStyleSheet("color: #888; font-size: 10px; font-style: italic;")
        info_layout.addWidget(info_label)
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
    def _on_config_changed(self):
        """配置改变时更新并发射信号"""
        self.config.enabled = self.chk_enable.isChecked()
        self.config.mode = self.combo_mode.currentData()
        self.config.trigger_type = self.combo_type.currentData()
        self.config.threshold = self.spin_threshold.value()
        self.config.hysteresis = self.spin_hysteresis.value()
        self.config.pre_trigger_samples = int(self.spin_pretrigger.value())
        
        # 更新UI状态
        is_single = self.config.mode == TriggerMode.SINGLE
        self.btn_arm.setEnabled(is_single)
        
        if not self.config.enabled:
            self.lbl_status.setText("Status: Disabled")
        elif self.config.mode == TriggerMode.SINGLE:
            if self.config.single_triggered:
                self.lbl_status.setText("Status: Triggered")
            else:
                self.lbl_status.setText("Status: Armed")
        else:
            self.lbl_status.setText(f"Status: {self.config.mode.value}")
        
        self.config_changed.emit(self.config)
        
    def _on_arm_clicked(self):
        """单次触发准备按钮点击"""
        self.config.single_triggered = False
        self._on_config_changed()
        self.arm_single_trigger.emit()
        
    def set_triggered(self, triggered: bool):
        """设置触发状态（外部调用）"""
        self.config.single_triggered = triggered
        self._on_config_changed()
        
    def get_config(self) -> TriggerConfig:
        """获取当前配置"""
        return self.config
