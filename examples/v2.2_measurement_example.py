#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2.2 测量工具使用示例
演示如何使用新的测量功能分析信号
"""

import sys
from pathlib import Path
import numpy as np

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
import pyqtgraph as pg

from xgen_waveform_viewer.measurement_tools import (
    Ruler, PeakMarker, MeasurementEngine, MeasurementResult
)


def generate_test_signal(duration=2.0, sample_rate=1000):
    """生成测试信号：正弦波 + 噪声"""
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # 10Hz 正弦波
    signal = 2048 + 800 * np.sin(2 * np.pi * 10 * t)
    
    # 添加少量噪声
    noise = np.random.normal(0, 20, len(signal))
    signal += noise
    
    # 限制在 ADC 范围内
    signal = np.clip(signal, 0, 4095).astype(np.uint16)
    
    return t, signal


def main():
    app = QApplication(sys.argv)
    
    # 创建绘图窗口
    win = pg.GraphicsLayoutWidget(show=True, title="V2.2 Measurement Tools Demo")
    win.resize(1200, 600)
    
    # 创建绘图区域
    plot = win.addPlot(title="ADC Signal with Measurements")
    plot.setLabel('left', 'ADC Value')
    plot.setLabel('bottom', 'Time', units='s')
    plot.showGrid(x=True, y=True, alpha=0.3)
    
    # 生成测试信号
    time, data = generate_test_signal()
    
    # 绘制信号
    curve = plot.plot(time, data, pen=pg.mkPen(color=(0, 255, 160), width=2))
    
    # 创建测量工具
    ruler = Ruler(plot)
    peak_marker = PeakMarker(plot)
    
    # 显示标尺
    ruler.set_positions(0.5, 1.5)  # 在 0.5s 和 1.5s 位置
    ruler.show()
    
    # 检测峰值
    pos_times, pos_values, neg_times, neg_values = MeasurementEngine.detect_peaks(
        data, time, threshold=0.6, min_distance=20
    )
    
    print(f"检测到峰值：")
    print(f"  正峰: {len(pos_times)} 个")
    print(f"  负峰: {len(neg_times)} 个")
    
    # 显示峰值标记
    if len(pos_times) > 0:
        peak_marker.show_peaks(pos_times, pos_values, positive=True)
    if len(neg_times) > 0:
        peak_marker.show_peaks(neg_times, neg_values, positive=False)
    
    # 计算频率
    if len(pos_times) >= 2:
        freq, period = MeasurementEngine.calculate_frequency(pos_times)
        print(f"\n频率分析：")
        print(f"  测量频率: {freq:.2f} Hz")
        print(f"  测量周期: {period*1000:.2f} ms")
        print(f"  理论频率: 10.00 Hz (用于对比)")
    
    # 计算标尺范围内的统计值
    result = MeasurementEngine.calculate_statistics(data, time, 0.5, 1.5)
    print(f"\n标尺范围 (0.5s - 1.5s) 统计值：")
    print(f"  平均值: {result.mean:.1f}")
    print(f"  RMS: {result.rms:.1f}")
    print(f"  最小值: {result.min_value:.1f}")
    print(f"  最大值: {result.max_value:.1f}")
    print(f"  峰峰值: {result.peak_to_peak:.1f}")
    
    # 添加文本说明
    text = pg.TextItem(
        "V2.2 Measurement Tools Demo\n"
        "- Yellow dashed lines: Ruler (drag to move)\n"
        "- Red triangles: Positive peaks\n"
        "- Green triangles: Negative peaks\n"
        f"- Detected: {len(pos_times)} peaks, {freq:.2f} Hz",
        anchor=(0, 1),
        color=(255, 255, 255)
    )
    text.setPos(0, 4095)
    plot.addItem(text)
    
    print("\n使用说明：")
    print("  - 拖动黄色虚线可以移动标尺")
    print("  - 标尺会实时显示时间间隔和频率")
    print("  - 红色/绿色三角形标记检测到的峰值")
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
