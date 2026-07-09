"""
主窗口
整合工具栏、波形显示、数据录制与保存
"""

import struct
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QDoubleSpinBox,
    QPushButton,
    QLabel,
    QFileDialog,
    QMessageBox,
    QStatusBar,
)
from PyQt6.QtCore import Qt, QTimer
from serial.tools import list_ports

from .config import (
    ADC_SAMPLE_RATE_HZ,
    FRAME_SAMPLES,
    BIN_MAGIC,
    BIN_VERSION,
    DEFAULT_PORT,
    UART_BAUDRATE,
)
from .serial_reader import SerialReader
from .waveform_widget import WaveformWidget
from .version import APP_TITLE


class MainWindow(QMainWindow):
    """ADC 波形显示主窗口"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(900, 560)

        # 串口读取线程
        self._reader = SerialReader(self)
        self._reader.frame_ready.connect(self._on_frame_ready)
        self._reader.stats_updated.connect(self._on_stats_updated)
        self._reader.error_occurred.connect(self._on_serial_error)

        # 录制状态
        self._recording = False
        self._record_file = None
        self._record_frame_count = 0
        self._record_sample_count = 0
        self._record_start_time = 0.0
        self._record_path = ""       # 预设保存路径 (空=每次弹窗选择)
        self._record_format = "bin"  # bin 或 csv

        self._setup_ui()
        self._setup_statusbar()

        # 串口列表刷新定时器
        self._port_timer = QTimer(self)
        self._port_timer.timeout.connect(self._refresh_ports)
        self._port_timer.start(2000)
        self._refresh_ports()

    # ── UI 构建 ────────────────────────────────────────────

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(6, 6, 6, 6)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        # 串口选择
        toolbar.addWidget(QLabel("Port:"))
        self._port_combo = QComboBox()
        self._port_combo.setMinimumWidth(120)
        toolbar.addWidget(self._port_combo)

        # 刷新按钮
        self._btn_refresh = QPushButton("Refresh")
        self._btn_refresh.clicked.connect(self._refresh_ports)
        toolbar.addWidget(self._btn_refresh)

        # 波特率
        toolbar.addWidget(QLabel("Baud:"))
        self._baud_combo = QComboBox()
        self._baud_combo.addItems([
            "9600", "19200", "38400", "57600", "115200",
            "230400", "460800", "921600", "1000000", "1500000", "2000000", "3000000",
        ])
        self._baud_combo.setCurrentText(str(UART_BAUDRATE))
        self._baud_combo.setMinimumWidth(90)
        toolbar.addWidget(self._baud_combo)

        # 数据位
        toolbar.addWidget(QLabel("Data:"))
        self._databits_combo = QComboBox()
        self._databits_combo.addItems(["8", "7", "6", "5"])
        self._databits_combo.setMinimumWidth(50)
        toolbar.addWidget(self._databits_combo)

        # 停止位
        toolbar.addWidget(QLabel("Stop:"))
        self._stopbits_combo = QComboBox()
        self._stopbits_combo.addItems(["1", "1.5", "2"])
        self._stopbits_combo.setMinimumWidth(55)
        toolbar.addWidget(self._stopbits_combo)

        # 校验位
        toolbar.addWidget(QLabel("Parity:"))
        self._parity_combo = QComboBox()
        self._parity_combo.addItems(["None", "Even", "Odd", "Mark", "Space"])
        self._parity_combo.setMinimumWidth(60)
        toolbar.addWidget(self._parity_combo)

        # 连接按钮
        self._btn_connect = QPushButton("Connect")
        self._btn_connect.clicked.connect(self._toggle_connect)
        toolbar.addWidget(self._btn_connect)

        toolbar.addSpacing(16)

        # ── 录制控制 ──
        # 格式选择
        toolbar.addWidget(QLabel("Fmt:"))
        self._record_fmt_combo = QComboBox()
        self._record_fmt_combo.addItems(["BIN", "CSV"])
        self._record_fmt_combo.setMinimumWidth(55)
        self._record_fmt_combo.currentTextChanged.connect(self._on_record_fmt_changed)
        toolbar.addWidget(self._record_fmt_combo)

        # 设置保存路径
        self._btn_set_path = QPushButton("Path...")
        self._btn_set_path.setToolTip("设置录制文件保存路径 (不设置则每次弹窗选择)")
        self._btn_set_path.clicked.connect(self._on_set_record_path)
        toolbar.addWidget(self._btn_set_path)

        # 录制按钮
        self._btn_record = QPushButton("Record")
        self._btn_record.setEnabled(False)
        self._btn_record.clicked.connect(self._toggle_record)
        toolbar.addWidget(self._btn_record)

        # 保存当前缓冲区
        self._btn_save = QPushButton("Save Buffer")
        self._btn_save.setEnabled(True)
        self._btn_save.clicked.connect(self._save_buffer)
        toolbar.addWidget(self._btn_save)

        # 导出缓冲区为 CSV
        self._btn_export_csv = QPushButton("Export CSV")
        self._btn_export_csv.setEnabled(True)
        self._btn_export_csv.clicked.connect(self._export_csv)
        toolbar.addWidget(self._btn_export_csv)

        toolbar.addSpacing(16)

        # ── X 轴控制 ──
        toolbar.addWidget(QLabel("X:"))

        # X 轴窗口宽度选择
        self._x_window_combo = QComboBox()
        for sec in self._get_x_presets():
            self._x_window_combo.addItem(self._fmt_seconds(sec), sec)
        self._x_window_combo.setCurrentIndex(
            self._x_window_combo.findData(2.0)
        )
        self._x_window_combo.currentIndexChanged.connect(self._on_x_window_changed)
        self._x_window_combo.setMinimumWidth(65)
        toolbar.addWidget(self._x_window_combo)

        self._x_span_spin = QDoubleSpinBox()
        self._x_span_spin.setRange(0.001, 120.0)
        self._x_span_spin.setDecimals(3)
        self._x_span_spin.setSingleStep(0.1)
        self._x_span_spin.setSuffix(" s")
        self._x_span_spin.setValue(2.0)
        self._x_span_spin.setMinimumWidth(82)
        self._x_span_spin.setToolTip("X 轴显示时间跨度")
        self._x_span_spin.valueChanged.connect(self._on_x_span_changed)
        toolbar.addWidget(self._x_span_spin)

        # X 缩小 (放大时间窗口)
        btn_x_zoom_out = QPushButton("−")
        btn_x_zoom_out.setToolTip("缩小 (显示更长时间)")
        btn_x_zoom_out.setFixedWidth(28)
        btn_x_zoom_out.clicked.connect(lambda: self._x_zoom(1))
        toolbar.addWidget(btn_x_zoom_out)

        # X 放大 (缩小时间窗口)
        btn_x_zoom_in = QPushButton("+")
        btn_x_zoom_in.setToolTip("放大 (显示更短时间)")
        btn_x_zoom_in.setFixedWidth(28)
        btn_x_zoom_in.clicked.connect(lambda: self._x_zoom(-1))
        toolbar.addWidget(btn_x_zoom_in)

        # Follow 按钮 (恢复自动滚动)
        self._btn_follow = QPushButton("Follow")
        self._btn_follow.setToolTip("恢复 X 轴自动滚动")
        self._btn_follow.clicked.connect(self._on_follow_clicked)
        toolbar.addWidget(self._btn_follow)

        self._btn_x_all = QPushButton("All")
        self._btn_x_all.setToolTip("显示当前缓冲区全部时间范围")
        self._btn_x_all.clicked.connect(self._on_x_all_clicked)
        toolbar.addWidget(self._btn_x_all)

        toolbar.addSpacing(16)

        # Y 轴模式切换
        toolbar.addWidget(QLabel("Y:"))
        self._btn_y_mode = QPushButton("Auto")
        self._btn_y_mode.setToolTip("Y 轴按当前可见波形自动缩放")
        self._btn_y_mode.clicked.connect(self._toggle_y_mode)
        toolbar.addWidget(self._btn_y_mode)

        self._btn_y_full = QPushButton("Full")
        self._btn_y_full.setToolTip("Y 轴显示 ADC 全范围")
        self._btn_y_full.clicked.connect(self._on_y_full_clicked)
        toolbar.addWidget(self._btn_y_full)

        self._btn_y_center = QPushButton("Center")
        self._btn_y_center.setToolTip("按当前可见波形居中，并保留余量")
        self._btn_y_center.clicked.connect(self._on_y_center_clicked)
        toolbar.addWidget(self._btn_y_center)

        self._y_min_spin = QDoubleSpinBox()
        self._y_min_spin.setRange(-65535.0, 65535.0)
        self._y_min_spin.setDecimals(0)
        self._y_min_spin.setSingleStep(10.0)
        self._y_min_spin.setPrefix("Min ")
        self._y_min_spin.setMinimumWidth(82)
        self._y_min_spin.valueChanged.connect(self._on_y_range_changed)
        toolbar.addWidget(self._y_min_spin)

        self._y_max_spin = QDoubleSpinBox()
        self._y_max_spin.setRange(-65535.0, 65535.0)
        self._y_max_spin.setDecimals(0)
        self._y_max_spin.setSingleStep(10.0)
        self._y_max_spin.setPrefix("Max ")
        self._y_max_spin.setValue(1200.0)
        self._y_max_spin.setMinimumWidth(82)
        self._y_max_spin.valueChanged.connect(self._on_y_range_changed)
        toolbar.addWidget(self._y_max_spin)

        toolbar.addStretch()

        root_layout.addLayout(toolbar)

        # 波形组件
        self._waveform = WaveformWidget()
        root_layout.addWidget(self._waveform)

    def _setup_statusbar(self):
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._status_label = QLabel("Disconnected")
        self._statusbar.addPermanentWidget(self._status_label)

    # ── 串口管理 ───────────────────────────────────────────

    def _refresh_ports(self):
        current = self._port_combo.currentText()
        self._port_combo.clear()
        ports = sorted(list_ports.comports(), key=lambda p: p.device)
        for p in ports:
            self._port_combo.addItem(f"{p.device} - {p.description}", p.device)
        # 恢复之前的选择
        if current:
            idx = self._port_combo.findText(current, Qt.MatchFlag.MatchStartsWith)
            if idx >= 0:
                self._port_combo.setCurrentIndex(idx)

    def _toggle_connect(self):
        if self._reader.isRunning():
            self._disconnect()
        else:
            self._connect()

    def _get_serial_config(self) -> dict:
        """从 UI 读取串口配置"""
        import serial as _serial
        stopbits_map = {"1": _serial.STOPBITS_ONE, "1.5": _serial.STOPBITS_ONE_POINT_FIVE, "2": _serial.STOPBITS_TWO}
        parity_map = {"None": _serial.PARITY_NONE, "Even": _serial.PARITY_EVEN, "Odd": _serial.PARITY_ODD,
                      "Mark": _serial.PARITY_MARK, "Space": _serial.PARITY_SPACE}
        return {
            "baudrate": int(self._baud_combo.currentText()),
            "databits": int(self._databits_combo.currentText()),
            "stopbits": stopbits_map[self._stopbits_combo.currentText()],
            "parity": parity_map[self._parity_combo.currentText()],
        }

    def _set_config_enabled(self, enabled: bool):
        """连接时禁用配置，断开时恢复"""
        for w in (self._baud_combo, self._databits_combo, self._stopbits_combo, self._parity_combo):
            w.setEnabled(enabled)

    def _connect(self):
        port_data = self._port_combo.currentData()
        if not port_data:
            QMessageBox.warning(self, "Error", "请选择串口")
            return

        cfg = self._get_serial_config()
        self._reader.configure(port_data, **cfg)
        self._reader.start()

        self._btn_connect.setText("Disconnect")
        self._btn_record.setEnabled(True)
        self._set_config_enabled(False)
        self._status_label.setText(f"Connected: {port_data} @ {cfg['baudrate']}")
        self._waveform.clear()

    def _disconnect(self):
        if self._recording:
            self._stop_record()

        self._reader.stop()
        self._btn_connect.setText("Connect")
        self._btn_record.setEnabled(False)
        self._set_config_enabled(True)
        self._status_label.setText("Disconnected")

    def _toggle_y_mode(self):
        """切换 Y 轴显示模式"""
        auto = self._waveform.toggle_y_mode()
        self._btn_y_mode.setText("Auto" if auto else "Manual")
        self._sync_y_controls_from_waveform()

    def _on_y_full_clicked(self):
        self._waveform.set_y_full_range()
        self._btn_y_mode.setText("Manual")
        self._sync_y_controls_from_waveform()

    def _on_y_center_clicked(self):
        stats = self._waveform.get_visible_stats()
        if not stats["has_data"]:
            return
        span = max(stats["span"] * 1.5, 20.0)
        self._waveform.set_y_center_span(stats["center"], span)
        self._btn_y_mode.setText("Manual")
        self._sync_y_controls_from_waveform()

    def _on_y_range_changed(self):
        if not hasattr(self, "_y_min_spin"):
            return
        y_min = self._y_min_spin.value()
        y_max = self._y_max_spin.value()
        if y_max <= y_min:
            y_max = y_min + 1.0
            self._y_max_spin.blockSignals(True)
            self._y_max_spin.setValue(y_max)
            self._y_max_spin.blockSignals(False)
        self._waveform.set_y_manual_range(y_min, y_max)
        self._btn_y_mode.setText("Manual")

    def _sync_y_controls_from_waveform(self):
        y_min, y_max = self._waveform.get_y_manual_range()
        self._y_min_spin.blockSignals(True)
        self._y_max_spin.blockSignals(True)
        self._y_min_spin.setValue(y_min)
        self._y_max_spin.setValue(y_max)
        self._y_min_spin.blockSignals(False)
        self._y_max_spin.blockSignals(False)

    # ── X 轴控制 ──────────────────────────────────────────

    @staticmethod
    def _get_x_presets() -> list:
        return [0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]

    @staticmethod
    def _fmt_seconds(sec: float) -> str:
        if sec < 1.0:
            return f"{int(sec * 1000)} ms"
        return f"{sec:g} s"

    def _on_x_window_changed(self, index):
        sec = self._x_window_combo.currentData()
        if sec is not None:
            self._set_x_span_spin(sec)
            self._waveform.set_x_window(sec)

    def _on_x_span_changed(self, value: float):
        self._waveform.set_x_window(value)

    def _x_zoom(self, direction: int):
        """direction: +1=缩小(更长时间), -1=放大(更短时间)"""
        factor = 1.5 if direction > 0 else 1 / 1.5
        self._waveform.zoom_x(factor)
        self._set_x_span_spin(self._waveform.get_x_window())

    def _on_follow_clicked(self):
        """恢复 X 轴自动滚动"""
        self._waveform.resume_auto_scroll()

    def _on_x_all_clicked(self):
        self._waveform.show_all_buffer()
        self._set_x_span_spin(self._waveform.get_x_window())

    def _set_x_span_spin(self, seconds: float):
        if not hasattr(self, "_x_span_spin"):
            return
        self._x_span_spin.blockSignals(True)
        self._x_span_spin.setValue(seconds)
        self._x_span_spin.blockSignals(False)

    # ── 数据接收 ───────────────────────────────────────────

    def _on_frame_ready(self, samples: np.ndarray, seq: int):
        self._waveform.append_frame(samples)

        # 录制时写入文件
        if self._recording and self._record_file:
            samples_count = len(samples)
            if self._record_format == "csv":
                # CSV: 每行一个采样点: time_s,adc_value
                base_t = self._record_sample_count / ADC_SAMPLE_RATE_HZ
                for i in range(samples_count):
                    t = base_t + i / ADC_SAMPLE_RATE_HZ
                    self._record_file.write(f"{t:.8f},{samples[i]}\n")
            else:
                # BIN v2: [seq(4B LE)][cnt(2B LE)][samples(cnt*2B)]
                self._record_file.write(struct.pack("<I", seq))
                self._record_file.write(struct.pack("<H", samples_count))
                self._record_file.write(samples.tobytes())
            self._record_frame_count += 1
            self._record_sample_count += samples_count

    def _on_stats_updated(self, fps: float, sample_rate_hz: float, frame_count: int, crc_errors: int, seq_gaps: int, resync_count: int, short_frames: int):
        self._waveform.update_stats(fps, sample_rate_hz, frame_count, crc_errors, seq_gaps, resync_count, short_frames)

    def _on_serial_error(self, msg: str):
        QMessageBox.critical(self, "Serial Error", msg)
        self._disconnect()

    # ── 录制 ──────────────────────────────────────────────

    def _on_record_fmt_changed(self, text):
        self._record_format = text.lower()

    def _on_set_record_path(self):
        """预设录制文件保存路径"""
        ext = self._record_format
        if ext == "csv":
            filter_str = "CSV Files (*.csv)"
        else:
            filter_str = "Binary Files (*.bin)"
        default_name = f"adc_record_{datetime.now():%Y%m%d_%H%M%S}.{ext}"
        path, _ = QFileDialog.getSaveFileName(self, "设置录制保存路径",
                                              str(Path.home() / default_name), filter_str)
        if path:
            self._record_path = path
            self._btn_set_path.setText(f"Path: ...{Path(path).name[-20:]}")
            self._btn_set_path.setToolTip(path)

    def _toggle_record(self):
        if self._recording:
            self._stop_record()
        else:
            self._start_record()

    def _start_record(self):
        ext = self._record_format
        # 获取保存路径
        if self._record_path:
            path = self._record_path
        else:
            if ext == "csv":
                filter_str = "CSV Files (*.csv)"
            else:
                filter_str = "Binary Files (*.bin)"
            default_name = f"adc_record_{datetime.now():%Y%m%d_%H%M%S}.{ext}"
            path, _ = QFileDialog.getSaveFileName(self, "选择录制文件",
                                                  str(Path.home() / default_name), filter_str)
            if not path:
                return

        try:
            if ext == "csv":
                self._record_file = open(path, "w", encoding="utf-8")
                # CSV 文件头
                self._record_file.write(f"# ADC Waveform Recording\n")
                self._record_file.write(f"# sample_rate={ADC_SAMPLE_RATE_HZ}Hz\n")
                self._record_file.write(f"# frame_samples=dynamic\n")
                self._record_file.write(f"# format=uint16\n")
                self._record_file.write(f"# start_time={datetime.now().isoformat()}\n")
                self._record_file.write(f"# time_s,adc_value\n")
            else:
                self._record_file = open(path, "wb")
                # BIN 文件头: magic(4) + version(4) + frame_count(4) + sample_rate(4) + frame_samples(4) + timestamp(8) = 28 bytes
                header = struct.pack(
                    "<4sIIIIq",
                    BIN_MAGIC,
                    BIN_VERSION,
                    0,  # frame_count placeholder
                    ADC_SAMPLE_RATE_HZ,
                    0,  # dynamic frame_samples; each BIN v2 frame stores its own cnt
                    int(time.time()),
                )
                self._record_file.write(header)
        except OSError as e:
            QMessageBox.critical(self, "Error", f"无法创建文件: {e}")
            return

        self._recording = True
        self._record_frame_count = 0
        self._record_sample_count = 0
        self._record_start_time = time.perf_counter()
        self._btn_record.setText("Stop")
        self._btn_record.setStyleSheet("background-color: #c00; color: white;")
        self._status_label.setText(f"REC [{ext.upper()}]: {Path(path).name}")

    def _stop_record(self):
        if self._record_file:
            if self._record_format == "bin":
                # 更新 BIN 文件头中的帧数 (offset 8, uint32)
                self._record_file.seek(8)
                self._record_file.write(struct.pack("<I", self._record_frame_count))
            self._record_file.close()
            self._record_file = None

        elapsed = time.perf_counter() - self._record_start_time
        total_samples = self._record_sample_count
        self._recording = False
        self._btn_record.setText("Record")
        self._btn_record.setStyleSheet("")
        self._status_label.setText(
            f"Saved {self._record_frame_count} frames ({total_samples} samples) in {elapsed:.1f}s"
        )

    # ── 保存/导出 ──────────────────────────────────────────

    def _save_buffer(self):
        """保存当前显示缓冲区数据为 .bin 文件"""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "保存缓冲区数据",
            str(Path.home() / f"adc_buffer_{datetime.now():%Y%m%d_%H%M%S}.bin"),
            "Binary Files (*.bin)",
        )
        if not path:
            return

        data = self._waveform.get_buffer_data()
        try:
            with open(path, "wb") as f:
                frame_count = len(data) // FRAME_SAMPLES
                # 文件头: magic(4) + version(4) + frame_count(4) + sample_rate(4) + frame_samples(4) + timestamp(8) = 28 bytes
                header = struct.pack(
                    "<4sIIIIq",
                    BIN_MAGIC,
                    BIN_VERSION,
                    frame_count,
                    ADC_SAMPLE_RATE_HZ,
                    FRAME_SAMPLES,
                    int(time.time()),
                )
                f.write(header)
                f.write(data.tobytes())
            QMessageBox.information(self, "Saved", f"已保存 {len(data)} 个采样点到:\n{path}")
        except OSError as e:
            QMessageBox.critical(self, "Error", f"保存失败: {e}")

    def _export_csv(self):
        """导出缓冲区数据为 CSV"""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出 CSV",
            str(Path.home() / f"adc_data_{datetime.now():%Y%m%d_%H%M%S}.csv"),
            "CSV Files (*.csv)",
        )
        if not path:
            return

        data = self._waveform.get_buffer_data()
        try:
            t = np.arange(len(data), dtype=np.float64) / ADC_SAMPLE_RATE_HZ
            header_line = f"# sample_rate={ADC_SAMPLE_RATE_HZ}Hz, samples={len(data)}\n# time_s,adc_value\n"
            with open(path, "w") as f:
                f.write(header_line)
                for i in range(len(data)):
                    f.write(f"{t[i]:.8f},{data[i]}\n")
            QMessageBox.information(self, "Exported", f"已导出 {len(data)} 个采样点到:\n{path}")
        except OSError as e:
            QMessageBox.critical(self, "Error", f"导出失败: {e}")

    # ── 事件 ──────────────────────────────────────────────

    def closeEvent(self, event):
        if self._reader.isRunning():
            self._disconnect()
        event.accept()
