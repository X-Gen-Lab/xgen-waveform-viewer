"""
测量工具模块
提供标尺、峰值检测、频率计算、统计值显示等功能
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QPen, QColor
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QPushButton


@dataclass
class MeasurementResult:
    """测量结果数据类"""
    # 时间测量
    time_start: float = 0.0
    time_end: float = 0.0
    time_delta: float = 0.0
    frequency: float = 0.0
    period: float = 0.0
    
    # 幅值测量
    value_start: float = 0.0
    value_end: float = 0.0
    value_delta: float = 0.0
    
    # 统计值
    mean: float = 0.0
    rms: float = 0.0
    min_value: float = 0.0
    max_value: float = 0.0
    peak_to_peak: float = 0.0
    
    # 峰值位置
    peaks_positive: list = None
    peaks_negative: list = None
    
    def __post_init__(self):
        if self.peaks_positive is None:
            self.peaks_positive = []
        if self.peaks_negative is None:
            self.peaks_negative = []


class Ruler:
    """可拖动的标尺，用于测量时间间隔和幅值差"""
    
    def __init__(self, plot_item, color: tuple = (255, 255, 0)):
        """
        初始化标尺
        
        参数:
            plot_item: PlotItem 对象 (不是 PlotWidget)
            color: 标尺颜色
        """
        self.plot_item = plot_item
        self.color = color
        self.visible = False
        self.measurement_changed = None  # 信号槽，可以连接回调
        
        # 创建两条可移动的垂直线
        pen = pg.mkPen(color=color, width=2, style=Qt.PenStyle.DashLine)
        self.line1 = pg.InfiniteLine(angle=90, movable=True, pen=pen)
        self.line2 = pg.InfiniteLine(angle=90, movable=True, pen=pen)
        
        # 连接位置变化信号
        self.line1.sigPositionChanged.connect(self._on_position_changed)
        self.line2.sigPositionChanged.connect(self._on_position_changed)
        
        # 标签显示测量值
        self.label = pg.TextItem(anchor=(0.5, 1), color=color)
        
        # 初始位置
        self.line1.setPos(0)
        self.line2.setPos(1)
        
        # 自动显示
        self.show()
        
    def show(self):
        """显示标尺"""
        if not self.visible:
            self.plot_item.addItem(self.line1, ignoreBounds=True)
            self.plot_item.addItem(self.line2, ignoreBounds=True)
            self.plot_item.addItem(self.label, ignoreBounds=True)
            self.visible = True
            self.update_label()
            
    def hide(self):
        """隐藏标尺"""
        if self.visible:
            self.plot_item.removeItem(self.line1)
            self.plot_item.removeItem(self.line2)
            self.plot_item.removeItem(self.label)
            self.visible = False
    
    def remove(self):
        """移除标尺（同hide）"""
        self.hide()
            
    def set_positions(self, t1: float, t2: float):
        """设置标尺位置"""
        self.line1.setPos(t1)
        self.line2.setPos(t2)
        self.update_label()
        
    def get_positions(self) -> tuple[float, float]:
        """获取标尺位置"""
        return self.line1.pos()[0], self.line2.pos()[0]
    
    def _on_position_changed(self):
        """位置改变时的回调"""
        self.update_label()
        
    def update_label(self):
        """更新测量值标签"""
        t1, t2 = self.get_positions()
        dt = abs(t2 - t1)
        freq = 1.0 / dt if dt > 1e-9 else 0.0
        
        text = f"Δt: {dt*1000:.3f} ms\nf: {freq:.2f} Hz"
        # 标签位置在两线中间上方
        self.label.setPos((t1 + t2) / 2, 0)
        self.label.setText(text)
        
        # 触发measurement_changed回调
        if self.measurement_changed is not None:
            result = {
                'dt': dt,
                'frequency': freq,
                't1': t1,
                't2': t2
            }
            self.measurement_changed(result)


class PeakMarker:
    """峰值标记"""
    
    def __init__(self, plot_widget: pg.PlotWidget):
        self.plot_widget = plot_widget
        self.markers = []
        self.visible = False
        
    def show_peaks(self, times: np.ndarray, values: np.ndarray, 
                   positive: bool = True):
        """显示峰值标记"""
        self.clear()
        
        if len(times) == 0:
            return
            
        color = (255, 100, 100) if positive else (100, 255, 100)
        symbol = 't' if positive else 't1'  # 向上/向下三角形
        
        scatter = pg.ScatterPlotItem(
            x=times,
            y=values,
            symbol=symbol,
            size=12,
            pen=pg.mkPen(color=color, width=2),
            brush=pg.mkBrush(*color, 150)
        )
        
        self.plot_widget.addItem(scatter)
        self.markers.append(scatter)
        self.visible = True
    
    def update_peaks(self, pos_times: np.ndarray, pos_values: np.ndarray,
                     neg_times: np.ndarray, neg_values: np.ndarray):
        """更新峰值标记 (显示正负峰值)"""
        self.clear()
        
        # 显示正峰值 (红色向上三角形)
        if len(pos_times) > 0:
            color_pos = (255, 100, 100)
            scatter_pos = pg.ScatterPlotItem(
                x=pos_times,
                y=pos_values,
                symbol='t',  # 向上三角形
                size=12,
                pen=pg.mkPen(color=color_pos, width=2),
                brush=pg.mkBrush(*color_pos, 150)
            )
            self.plot_widget.addItem(scatter_pos)
            self.markers.append(scatter_pos)
        
        # 显示负峰值 (绿色向下三角形)
        if len(neg_times) > 0:
            color_neg = (100, 255, 100)
            scatter_neg = pg.ScatterPlotItem(
                x=neg_times,
                y=neg_values,
                symbol='t1',  # 向下三角形
                size=12,
                pen=pg.mkPen(color=color_neg, width=2),
                brush=pg.mkBrush(*color_neg, 150)
            )
            self.plot_widget.addItem(scatter_neg)
            self.markers.append(scatter_neg)
        
        self.visible = len(self.markers) > 0
        
    def clear(self):
        """清除所有标记"""
        for marker in self.markers:
            self.plot_widget.removeItem(marker)
        self.markers = []
        self.visible = False


class MeasurementPanel(QWidget):
    """测量结果显示面板"""
    
    ruler_toggled = pyqtSignal(bool)
    peak_detection_requested = pyqtSignal()
    clear_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        
        self.btn_ruler = QPushButton("Ruler")
        self.btn_ruler.setCheckable(True)
        self.btn_ruler.setToolTip("显示/隐藏时间标尺 (快捷键: M)")
        self.btn_ruler.clicked.connect(lambda checked: self.ruler_toggled.emit(checked))
        control_layout.addWidget(self.btn_ruler)
        
        self.btn_peaks = QPushButton("Find Peaks")
        self.btn_peaks.setToolTip("检测并标注峰值点 (快捷键: P)")
        self.btn_peaks.clicked.connect(self.peak_detection_requested.emit)
        control_layout.addWidget(self.btn_peaks)
        
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setToolTip("清除所有测量标记")
        self.btn_clear.clicked.connect(self.clear_requested.emit)
        control_layout.addWidget(self.btn_clear)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # 测量结果显示组
        group = QGroupBox("Measurement Results")
        group_layout = QVBoxLayout(group)
        
        # 时间测量
        time_layout = QHBoxLayout()
        self.lbl_time_delta = QLabel("Δt: --")
        self.lbl_frequency = QLabel("f: --")
        self.lbl_period = QLabel("T: --")
        time_layout.addWidget(self.lbl_time_delta)
        time_layout.addWidget(self.lbl_frequency)
        time_layout.addWidget(self.lbl_period)
        time_layout.addStretch()
        group_layout.addLayout(time_layout)
        
        # 幅值测量
        value_layout = QHBoxLayout()
        self.lbl_value_delta = QLabel("ΔV: --")
        self.lbl_min = QLabel("Min: --")
        self.lbl_max = QLabel("Max: --")
        value_layout.addWidget(self.lbl_value_delta)
        value_layout.addWidget(self.lbl_min)
        value_layout.addWidget(self.lbl_max)
        value_layout.addStretch()
        group_layout.addLayout(value_layout)
        
        # 统计值
        stats_layout = QHBoxLayout()
        self.lbl_mean = QLabel("Mean: --")
        self.lbl_rms = QLabel("RMS: --")
        self.lbl_pp = QLabel("Vpp: --")
        stats_layout.addWidget(self.lbl_mean)
        stats_layout.addWidget(self.lbl_rms)
        stats_layout.addWidget(self.lbl_pp)
        stats_layout.addStretch()
        group_layout.addLayout(stats_layout)
        
        # 峰值计数
        peak_layout = QHBoxLayout()
        self.lbl_peaks_pos = QLabel("Peaks+: 0")
        self.lbl_peaks_neg = QLabel("Peaks-: 0")
        peak_layout.addWidget(self.lbl_peaks_pos)
        peak_layout.addWidget(self.lbl_peaks_neg)
        peak_layout.addStretch()
        group_layout.addLayout(peak_layout)
        
        layout.addWidget(group)
        
        # 设置样式
        for lbl in [self.lbl_time_delta, self.lbl_frequency, self.lbl_period,
                    self.lbl_value_delta, self.lbl_min, self.lbl_max,
                    self.lbl_mean, self.lbl_rms, self.lbl_pp,
                    self.lbl_peaks_pos, self.lbl_peaks_neg]:
            lbl.setStyleSheet("color: #0af; font-size: 11px; padding: 2px 4px;")
    
    def update_measurements(self, result: MeasurementResult):
        """更新显示的测量结果"""
        # 时间测量
        if result.time_delta > 0:
            self.lbl_time_delta.setText(f"Δt: {result.time_delta*1000:.3f} ms")
            self.lbl_frequency.setText(f"f: {result.frequency:.2f} Hz")
            self.lbl_period.setText(f"T: {result.period*1000:.3f} ms")
        else:
            self.lbl_time_delta.setText("Δt: --")
            self.lbl_frequency.setText("f: --")
            self.lbl_period.setText("T: --")
        
        # 幅值测量
        self.lbl_value_delta.setText(f"ΔV: {result.value_delta:.1f}")
        self.lbl_min.setText(f"Min: {result.min_value:.1f}")
        self.lbl_max.setText(f"Max: {result.max_value:.1f}")
        
        # 统计值
        self.lbl_mean.setText(f"Mean: {result.mean:.1f}")
        self.lbl_rms.setText(f"RMS: {result.rms:.1f}")
        self.lbl_pp.setText(f"Vpp: {result.peak_to_peak:.1f}")
        
        # 峰值计数
        self.lbl_peaks_pos.setText(f"Peaks+: {len(result.peaks_positive)}")
        self.lbl_peaks_neg.setText(f"Peaks-: {len(result.peaks_negative)}")
    
    def clear_measurements(self):
        """清空测量结果显示"""
        result = MeasurementResult()
        self.update_measurements(result)


class MeasurementEngine:
    """测量计算引擎"""
    
    @staticmethod
    def calculate_statistics(data: np.ndarray, time: np.ndarray,
                            x_min: float, x_max: float) -> MeasurementResult:
        """计算可见区域的统计值"""
        result = MeasurementResult()
        
        if len(data) == 0:
            return result
        
        # 筛选可见区域数据
        mask = (time >= x_min) & (time <= x_max)
        visible_data = data[mask]
        visible_time = time[mask]
        
        if len(visible_data) == 0:
            return result
        
        # 统计值
        result.mean = float(np.mean(visible_data))
        result.rms = float(np.sqrt(np.mean(visible_data.astype(np.float64) ** 2)))
        result.min_value = float(np.min(visible_data))
        result.max_value = float(np.max(visible_data))
        result.peak_to_peak = result.max_value - result.min_value
        
        return result
    
    @staticmethod
    def detect_peaks(data: np.ndarray, time: np.ndarray,
                     threshold: float = 0.5,
                     min_distance: int = 5) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        检测正负峰值
        
        参数:
            data: 数据数组
            time: 时间数组
            threshold: 峰值阈值 (相对于数据范围的比例, 0-1)
            min_distance: 峰值之间的最小距离 (采样点数)
        
        返回:
            (正峰时间, 正峰值, 负峰时间, 负峰值)
        """
        if len(data) < min_distance * 2:
            return np.array([]), np.array([]), np.array([]), np.array([])
        
        # 数据标准化
        data_min = np.min(data)
        data_max = np.max(data)
        data_range = data_max - data_min
        
        if data_range < 1.0:
            return np.array([]), np.array([]), np.array([]), np.array([])
        
        data_norm = (data - data_min) / data_range
        
        # 正峰值检测 (局部最大值)
        pos_peaks = []
        for i in range(min_distance, len(data) - min_distance):
            if data_norm[i] > threshold:
                # 检查是否为局部最大值
                if np.all(data[i] >= data[i-min_distance:i]) and \
                   np.all(data[i] >= data[i+1:i+min_distance+1]):
                    pos_peaks.append(i)
        
        # 负峰值检测 (局部最小值)
        neg_peaks = []
        for i in range(min_distance, len(data) - min_distance):
            if data_norm[i] < (1.0 - threshold):
                # 检查是否为局部最小值
                if np.all(data[i] <= data[i-min_distance:i]) and \
                   np.all(data[i] <= data[i+1:i+min_distance+1]):
                    neg_peaks.append(i)
        
        # 提取峰值位置和数值
        if pos_peaks:
            pos_peaks = np.array(pos_peaks)
            pos_times = time[pos_peaks]
            pos_values = data[pos_peaks]
        else:
            pos_times = np.array([])
            pos_values = np.array([])
        
        if neg_peaks:
            neg_peaks = np.array(neg_peaks)
            neg_times = time[neg_peaks]
            neg_values = data[neg_peaks]
        else:
            neg_times = np.array([])
            neg_values = np.array([])
        
        return pos_times, pos_values, neg_times, neg_values
    
    @staticmethod
    def calculate_frequency(peaks_time: np.ndarray) -> tuple[float, float]:
        """
        根据峰值位置计算频率和周期
        
        返回: (频率Hz, 周期s)
        """
        if len(peaks_time) < 2:
            return 0.0, 0.0
        
        # 计算相邻峰值的平均间隔
        intervals = np.diff(peaks_time)
        avg_period = float(np.mean(intervals))
        
        if avg_period < 1e-9:
            return 0.0, 0.0
        
        frequency = 1.0 / avg_period
        return frequency, avg_period
