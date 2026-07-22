"""
统计面板
提供丢帧、CRC 错误等统计信息的可视化显示
"""

import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QGroupBox, QGridLayout, QTextEdit
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from collections import deque
from typing import Optional

from .logger import get_logger


class StatisticsPanel(QWidget):
    """统计信息面板"""
    
    # 历史记录长度（秒）
    HISTORY_DURATION_SEC = 60
    # 更新间隔（毫秒）
    UPDATE_INTERVAL_MS = 1000
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._logger = get_logger()
        
        # 统计数据
        self._total_frames = 0
        self._total_crc_errors = 0
        self._total_seq_gaps = 0
        self._total_resyncs = 0
        self._total_short_frames = 0
        self._total_samples = 0
        
        # 时间序列数据（用于图表）
        self._max_history_points = self.HISTORY_DURATION_SEC
        self._time_history = deque(maxlen=self._max_history_points)
        self._fps_history = deque(maxlen=self._max_history_points)
        self._error_rate_history = deque(maxlen=self._max_history_points)
        self._sample_rate_history = deque(maxlen=self._max_history_points)
        
        # 累计错误率
        self._crc_error_rate = 0.0
        self._seq_gap_rate = 0.0
        self._resync_rate = 0.0
        
        self._time_counter = 0
        
        self._setup_ui()
        
        # 更新定时器
        self._update_timer = QTimer(self)
        self._update_timer.setInterval(self.UPDATE_INTERVAL_MS)
        self._update_timer.timeout.connect(self._update_plots)
        self._update_timer.start()
    
    def _setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("数据完整性统计")
        title.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        layout.addWidget(title)
        
        # 统计指标组
        metrics_group = QGroupBox("统计指标")
        metrics_layout = QGridLayout()
        
        # 创建标签
        self._lbl_total_frames = QLabel("0")
        self._lbl_total_samples = QLabel("0")
        self._lbl_crc_errors = QLabel("0")
        self._lbl_seq_gaps = QLabel("0")
        self._lbl_resyncs = QLabel("0")
        self._lbl_short_frames = QLabel("0")
        self._lbl_crc_rate = QLabel("0.00%")
        self._lbl_gap_rate = QLabel("0.00%")
        self._lbl_resync_rate = QLabel("0.00%")
        
        # 设置标签样式
        for lbl in [self._lbl_total_frames, self._lbl_total_samples, self._lbl_crc_errors,
                    self._lbl_seq_gaps, self._lbl_resyncs, self._lbl_short_frames,
                    self._lbl_crc_rate, self._lbl_gap_rate, self._lbl_resync_rate]:
            font = QFont()
            font.setBold(True)
            lbl.setFont(font)
        
        # 布局
        row = 0
        metrics_layout.addWidget(QLabel("总帧数:"), row, 0)
        metrics_layout.addWidget(self._lbl_total_frames, row, 1)
        metrics_layout.addWidget(QLabel("总样本数:"), row, 2)
        metrics_layout.addWidget(self._lbl_total_samples, row, 3)
        
        row += 1
        metrics_layout.addWidget(QLabel("CRC 错误:"), row, 0)
        metrics_layout.addWidget(self._lbl_crc_errors, row, 1)
        metrics_layout.addWidget(QLabel("错误率:"), row, 2)
        metrics_layout.addWidget(self._lbl_crc_rate, row, 3)
        
        row += 1
        metrics_layout.addWidget(QLabel("序列号间隙:"), row, 0)
        metrics_layout.addWidget(self._lbl_seq_gaps, row, 1)
        metrics_layout.addWidget(QLabel("间隙率:"), row, 2)
        metrics_layout.addWidget(self._lbl_gap_rate, row, 3)
        
        row += 1
        metrics_layout.addWidget(QLabel("重同步次数:"), row, 0)
        metrics_layout.addWidget(self._lbl_resyncs, row, 1)
        metrics_layout.addWidget(QLabel("重同步率:"), row, 2)
        metrics_layout.addWidget(self._lbl_resync_rate, row, 3)
        
        row += 1
        metrics_layout.addWidget(QLabel("短帧数:"), row, 0)
        metrics_layout.addWidget(self._lbl_short_frames, row, 1)
        
        metrics_group.setLayout(metrics_layout)
        layout.addWidget(metrics_group)
        
        # 图表组
        charts_group = QGroupBox("时间序列图表")
        charts_layout = QVBoxLayout()
        
        # 帧率图表
        self._fps_plot = pg.PlotWidget(title="帧率 (FPS)")
        self._fps_plot.setLabel("left", "FPS")
        self._fps_plot.setLabel("bottom", "时间", units="s")
        self._fps_plot.showGrid(x=True, y=True, alpha=0.3)
        self._fps_curve = self._fps_plot.plot(pen=pg.mkPen(color=(0, 255, 160), width=2))
        self._fps_plot.setFixedHeight(150)
        charts_layout.addWidget(self._fps_plot)
        
        # 错误率图表
        self._error_plot = pg.PlotWidget(title="错误率 (%)")
        self._error_plot.setLabel("left", "错误率 (%)")
        self._error_plot.setLabel("bottom", "时间", units="s")
        self._error_plot.showGrid(x=True, y=True, alpha=0.3)
        self._error_curve = self._error_plot.plot(pen=pg.mkPen(color=(255, 100, 100), width=2))
        self._error_plot.setFixedHeight(150)
        charts_layout.addWidget(self._error_plot)
        
        # 采样率图表
        self._sample_rate_plot = pg.PlotWidget(title="采样率 (Hz)")
        self._sample_rate_plot.setLabel("left", "Hz")
        self._sample_rate_plot.setLabel("bottom", "时间", units="s")
        self._sample_rate_plot.showGrid(x=True, y=True, alpha=0.3)
        self._sample_rate_curve = self._sample_rate_plot.plot(pen=pg.mkPen(color=(100, 150, 255), width=2))
        self._sample_rate_plot.setFixedHeight(150)
        charts_layout.addWidget(self._sample_rate_plot)
        
        charts_group.setLayout(charts_layout)
        layout.addWidget(charts_group)
        
        # 按钮
        btn_layout = QHBoxLayout()
        self._btn_reset = QPushButton("重置统计")
        self._btn_reset.clicked.connect(self.reset_statistics)
        self._btn_export = QPushButton("导出日志")
        self._btn_export.clicked.connect(self._export_logs)
        btn_layout.addWidget(self._btn_reset)
        btn_layout.addWidget(self._btn_export)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # 状态消息
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #888; font-size: 10px; padding: 5px;")
        layout.addWidget(self._status_label)
    
    def update_statistics(
        self,
        fps: float,
        sample_rate: float,
        frame_count: int,
        crc_errors: int,
        seq_gaps: int,
        resyncs: int,
        short_frames: int
    ):
        """更新统计信息"""
        self._total_frames = frame_count
        self._total_crc_errors = crc_errors
        self._total_seq_gaps = seq_gaps
        self._total_resyncs = resyncs
        self._total_short_frames = short_frames
        
        # 计算错误率
        if self._total_frames > 0:
            self._crc_error_rate = (self._total_crc_errors / self._total_frames) * 100
            self._seq_gap_rate = (self._total_seq_gaps / self._total_frames) * 100
            self._resync_rate = (self._total_resyncs / self._total_frames) * 100
        else:
            self._crc_error_rate = 0.0
            self._seq_gap_rate = 0.0
            self._resync_rate = 0.0
        
        # 更新标签
        self._lbl_total_frames.setText(f"{self._total_frames:,}")
        self._lbl_crc_errors.setText(f"{self._total_crc_errors:,}")
        self._lbl_seq_gaps.setText(f"{self._total_seq_gaps:,}")
        self._lbl_resyncs.setText(f"{self._total_resyncs:,}")
        self._lbl_short_frames.setText(f"{self._total_short_frames:,}")
        
        self._lbl_crc_rate.setText(f"{self._crc_error_rate:.2f}%")
        self._lbl_gap_rate.setText(f"{self._seq_gap_rate:.2f}%")
        self._lbl_resync_rate.setText(f"{self._resync_rate:.2f}%")
        
        # 设置错误标签颜色
        if self._total_crc_errors > 0:
            self._lbl_crc_errors.setStyleSheet("color: #ff5555;")
            self._lbl_crc_rate.setStyleSheet("color: #ff5555;")
        else:
            self._lbl_crc_errors.setStyleSheet("")
            self._lbl_crc_rate.setStyleSheet("")
        
        if self._total_seq_gaps > 0:
            self._lbl_seq_gaps.setStyleSheet("color: #ffaa00;")
            self._lbl_gap_rate.setStyleSheet("color: #ffaa00;")
        else:
            self._lbl_seq_gaps.setStyleSheet("")
            self._lbl_gap_rate.setStyleSheet("")
        
        if self._total_resyncs > 0:
            self._lbl_resyncs.setStyleSheet("color: #ffaa00;")
            self._lbl_resync_rate.setStyleSheet("color: #ffaa00;")
        else:
            self._lbl_resyncs.setStyleSheet("")
            self._lbl_resync_rate.setStyleSheet("")
        
        # 添加到历史记录
        self._time_history.append(self._time_counter)
        self._fps_history.append(fps)
        self._error_rate_history.append(self._crc_error_rate + self._seq_gap_rate)
        self._sample_rate_history.append(sample_rate)
        
        self._time_counter += 1
    
    def update_sample_count(self, total_samples: int):
        """更新样本计数"""
        self._total_samples = total_samples
        self._lbl_total_samples.setText(f"{self._total_samples:,}")
    
    def _update_plots(self):
        """更新图表"""
        if len(self._time_history) == 0:
            return
        
        time_arr = np.array(self._time_history, dtype=np.float64)
        
        # 更新帧率图表
        fps_arr = np.array(self._fps_history, dtype=np.float64)
        self._fps_curve.setData(time_arr, fps_arr)
        
        # 更新错误率图表
        error_arr = np.array(self._error_rate_history, dtype=np.float64)
        self._error_curve.setData(time_arr, error_arr)
        
        # 更新采样率图表
        sample_rate_arr = np.array(self._sample_rate_history, dtype=np.float64)
        self._sample_rate_curve.setData(time_arr, sample_rate_arr)
    
    def reset_statistics(self):
        """重置统计信息"""
        self._total_frames = 0
        self._total_crc_errors = 0
        self._total_seq_gaps = 0
        self._total_resyncs = 0
        self._total_short_frames = 0
        self._total_samples = 0
        
        self._crc_error_rate = 0.0
        self._seq_gap_rate = 0.0
        self._resync_rate = 0.0
        
        self._time_counter = 0
        
        self._time_history.clear()
        self._fps_history.clear()
        self._error_rate_history.clear()
        self._sample_rate_history.clear()
        
        self._fps_curve.setData([], [])
        self._error_curve.setData([], [])
        self._sample_rate_curve.setData([], [])
        
        self._update_labels()
        
        self._status_label.setText("统计信息已重置")
        self._logger.info("Statistics reset by user")
    
    def _update_labels(self):
        """更新标签显示"""
        self._lbl_total_frames.setText(f"{self._total_frames:,}")
        self._lbl_total_samples.setText(f"{self._total_samples:,}")
        self._lbl_crc_errors.setText(f"{self._total_crc_errors:,}")
        self._lbl_seq_gaps.setText(f"{self._total_seq_gaps:,}")
        self._lbl_resyncs.setText(f"{self._total_resyncs:,}")
        self._lbl_short_frames.setText(f"{self._total_short_frames:,}")
        self._lbl_crc_rate.setText(f"{self._crc_error_rate:.2f}%")
        self._lbl_gap_rate.setText(f"{self._seq_gap_rate:.2f}%")
        self._lbl_resync_rate.setText(f"{self._resync_rate:.2f}%")
    
    def _export_logs(self):
        """导出日志"""
        from PyQt6.QtWidgets import QFileDialog
        from pathlib import Path
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "导出日志",
            str(Path.home() / "xgen_waveform_log.json"),
            "JSON 文件 (*.json)"
        )
        
        if filepath:
            try:
                self._logger.export_events_json(Path(filepath))
                self._status_label.setText(f"日志已导出到: {filepath}")
                self._status_label.setStyleSheet("color: #55ff55; font-size: 10px; padding: 5px;")
            except Exception as e:
                self._status_label.setText(f"导出失败: {e}")
                self._status_label.setStyleSheet("color: #ff5555; font-size: 10px; padding: 5px;")
    
    def apply_theme_colors(self, colors: dict):
        """应用主题颜色"""
        # 更新图表背景
        bg_color = colors.get("plot_background", (3, 7, 10))
        self._fps_plot.setBackground(bg_color)
        self._error_plot.setBackground(bg_color)
        self._sample_rate_plot.setBackground(bg_color)
