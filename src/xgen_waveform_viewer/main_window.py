"""
主窗口
整合工具栏、波形显示、数据录制与保存

V2.2 新增:
- 测量工具 (标尺、峰值检测、统计值)
- 触发功能 (边沿/电平触发、单次触发)
- 录制增强 (暂停/恢复、分段录制、实时预览)

V2.3 新增:
- 性能优化 (降采样、帧率限制、内存管理)
- 鲁棒性提升 (日志系统、统计面板)

V2.4 新增:
- 数据回放 (多格式支持、变速播放、进度控制)
- 高级导出 (PNG/SVG/MATLAB/HDF5/HTML报告)
- 波形比较工具
"""

import json
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
    QMenu,
    QSplitter,
    QTabWidget,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QShortcut, QKeySequence, QAction
from serial.tools import list_ports

from .config import (
    ADC_SAMPLE_RATE_HZ,
    BIN_MAGIC,
    BIN_VERSION,
    DEFAULT_PORT,
    UART_BAUDRATE,
)
from .recorder import FrameRecorder
from .serial_reader import SerialReader
from .waveform_widget import MAX_BUFFER_SAMPLES, WaveformWidget
from .version import APP_TITLE
from .settings import AppSettings
from .theme import Theme
from .measurement_tools import (
    Ruler, PeakMarker, MeasurementPanel, MeasurementEngine, MeasurementResult
)
from .trigger import TriggerPanel, TriggerDetector, TriggerConfig
from .performance import PerformanceOptimizer, MemoryOptimizer
from .logger import init_logger, get_logger
from .statistics_panel import StatisticsPanel
from .playback_panel import PlaybackPanel
from .exporter import WaveformExporter


class MainWindow(QMainWindow):
    """ADC 波形显示主窗口"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(900, 560)

        # V2.3: 初始化日志系统
        self._logger = init_logger()
        self._logger.info("Application started", category="app")
        
        # V2.3: 性能优化器和内存优化器
        self._perf_optimizer = PerformanceOptimizer()
        self._mem_optimizer = MemoryOptimizer()

        # 设置管理
        self._settings = AppSettings()
        
        # 应用主题
        theme = self._settings.get("display/theme", "dark")
        Theme.apply_theme(theme)

        # 串口读取线程
        self._reader = SerialReader(self)
        self._reader.frame_ready.connect(self._on_frame_ready)
        self._reader.stats_updated.connect(self._on_stats_updated)
        self._reader.error_occurred.connect(self._on_serial_error)
        
        # 自动重连
        self._auto_reconnect_enabled = self._settings.get("serial/auto_reconnect", False)
        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.timeout.connect(self._attempt_reconnect)
        self._last_port_config = None

        # 录制状态
        self._recording = False
        self._recorder: FrameRecorder | None = None
        self._record_frame_count = 0
        self._record_sample_count = 0
        self._record_start_time = 0.0
        self._record_serial_stats_start = {}
        self._record_dir: Path | None = None  # 预设保存目录 (空=每次弹窗选择文件)
        self._record_format = "bin"  # bin 或 csv
        self._max_buffer_samples = MAX_BUFFER_SAMPLES
        
        # V2.2 录制增强
        self._record_preview_timer = QTimer(self)
        self._record_preview_timer.timeout.connect(self._update_record_preview)
        
        # V2.2 测量工具
        self._ruler: Ruler | None = None
        self._peak_marker: PeakMarker | None = None
        self._measurement_result = MeasurementResult()
        
        # V2.2 触发功能
        self._trigger_detector = TriggerDetector()
        self._trigger_detector.trigger_fired.connect(self._on_trigger_fired)
        
        # V2.3: 统计面板
        self._statistics_panel: StatisticsPanel | None = None
        
        # V2.4: 回放控制面板
        self._playback_panel: PlaybackPanel | None = None
        self._playback_mode = False  # 是否处于回放模式

        self._setup_ui()
        self._setup_statusbar()
        self._setup_shortcuts()
        self._setup_menu()
        
        # 恢复窗口状态
        self._restore_window_state()
        
        # 恢复用户设置
        self._restore_settings()

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
        self._btn_set_path.setToolTip("设置录制文件保存目录 (不设置则每次弹窗选择文件)")
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

        toolbar.addStretch()
        root_layout.addLayout(toolbar)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

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
        self._x_span_spin.setRange(0.001, self._max_x_window_seconds())
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

        toolbar.addWidget(QLabel("Buf:"))
        self._buffer_limit_spin = QDoubleSpinBox()
        self._buffer_limit_spin.setRange(0.01, 100.0)
        self._buffer_limit_spin.setDecimals(2)
        self._buffer_limit_spin.setSingleStep(1.0)
        self._buffer_limit_spin.setSuffix(" Mpts")
        self._buffer_limit_spin.setValue(self._max_buffer_samples / 1_000_000)
        self._buffer_limit_spin.setMinimumWidth(92)
        self._buffer_limit_spin.setToolTip("显示缓冲区最大采样点数，单位为百万点")
        self._buffer_limit_spin.valueChanged.connect(self._on_buffer_limit_changed)
        toolbar.addWidget(self._buffer_limit_spin)

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
        self._waveform.set_max_buffer_samples(self._max_buffer_samples)
        root_layout.addWidget(self._waveform)

    def _setup_statusbar(self):
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._status_label = QLabel("Disconnected")
        self._statusbar.addPermanentWidget(self._status_label)

    def _setup_shortcuts(self):
        """设置键盘快捷键"""
        if not self._settings.get("shortcuts/enabled", True):
            return
        
        # 空格：暂停/恢复自动滚动
        self._shortcut_follow = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self._shortcut_follow.activated.connect(self._on_follow_clicked)
        
        # R：开始/停止录制
        self._shortcut_record = QShortcut(QKeySequence("R"), self)
        self._shortcut_record.activated.connect(self._toggle_record_shortcut)
        
        # C：连接/断开串口
        self._shortcut_connect = QShortcut(QKeySequence("C"), self)
        self._shortcut_connect.activated.connect(self._toggle_connect)
        
        # S：保存缓冲区
        self._shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self)
        self._shortcut_save.activated.connect(self._save_buffer)
        
        # E：导出 CSV
        self._shortcut_export = QShortcut(QKeySequence("Ctrl+E"), self)
        self._shortcut_export.activated.connect(self._export_csv)
        
        # F：全屏显示缓冲区
        self._shortcut_fit = QShortcut(QKeySequence("F"), self)
        self._shortcut_fit.activated.connect(self._on_x_all_clicked)
        
        # Y：Y轴自动/手动切换
        self._shortcut_y_mode = QShortcut(QKeySequence("Y"), self)
        self._shortcut_y_mode.activated.connect(self._toggle_y_mode)
        
        # +/-：X轴缩放
        self._shortcut_zoom_in = QShortcut(QKeySequence("+"), self)
        self._shortcut_zoom_in.activated.connect(lambda: self._x_zoom(-1))
        self._shortcut_zoom_out = QShortcut(QKeySequence("-"), self)
        self._shortcut_zoom_out.activated.connect(lambda: self._x_zoom(1))

    def _setup_menu(self):
        """设置菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("&File")
        
        save_action = QAction("&Save Buffer", self)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self._save_buffer)
        file_menu.addAction(save_action)
        
        export_action = QAction("&Export CSV", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self._export_csv)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        # V2.4: 导出子菜单
        export_menu = file_menu.addMenu("E&xport As")
        
        export_png_action = QAction("Export as &PNG...", self)
        export_png_action.triggered.connect(self._export_png)
        export_menu.addAction(export_png_action)
        
        export_svg_action = QAction("Export as &SVG...", self)
        export_svg_action.triggered.connect(self._export_svg)
        export_menu.addAction(export_svg_action)
        
        export_mat_action = QAction("Export as &MATLAB (.mat)...", self)
        export_mat_action.triggered.connect(self._export_matlab)
        export_menu.addAction(export_mat_action)
        
        export_hdf5_action = QAction("Export as &HDF5 (.h5)...", self)
        export_hdf5_action.triggered.connect(self._export_hdf5)
        export_menu.addAction(export_hdf5_action)
        
        export_report_action = QAction("Export &Report (HTML)...", self)
        export_report_action.triggered.connect(self._export_report_html)
        export_menu.addAction(export_report_action)
        
        file_menu.addSeparator()
        
        # V2.4: 回放功能
        playback_action = QAction("&Playback Recording...", self)
        playback_action.setShortcut(QKeySequence("Ctrl+P"))
        playback_action.triggered.connect(self._show_playback_panel)
        file_menu.addAction(playback_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("&View")
        
        theme_menu = view_menu.addMenu("&Theme")
        dark_action = QAction("&Dark", self)
        dark_action.triggered.connect(lambda: self._switch_theme("dark"))
        theme_menu.addAction(dark_action)
        
        light_action = QAction("&Light", self)
        light_action.triggered.connect(lambda: self._switch_theme("light"))
        theme_menu.addAction(light_action)
        
        view_menu.addSeparator()
        
        follow_action = QAction("&Follow (Resume Auto-scroll)", self)
        follow_action.setShortcut(QKeySequence(Qt.Key.Key_Space))
        follow_action.triggered.connect(self._on_follow_clicked)
        view_menu.addAction(follow_action)
        
        fit_action = QAction("Show &All Buffer", self)
        fit_action.setShortcut(QKeySequence("F"))
        fit_action.triggered.connect(self._on_x_all_clicked)
        view_menu.addAction(fit_action)
        
        # 连接菜单
        conn_menu = menubar.addMenu("&Connection")
        
        connect_action = QAction("&Connect/Disconnect", self)
        connect_action.setShortcut(QKeySequence("C"))
        connect_action.triggered.connect(self._toggle_connect)
        conn_menu.addAction(connect_action)
        
        conn_menu.addSeparator()
        
        self._auto_reconnect_action = QAction("Auto &Reconnect", self)
        self._auto_reconnect_action.setCheckable(True)
        self._auto_reconnect_action.setChecked(self._auto_reconnect_enabled)
        self._auto_reconnect_action.triggered.connect(self._toggle_auto_reconnect)
        conn_menu.addAction(self._auto_reconnect_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("&Help")
        
        shortcuts_action = QAction("&Keyboard Shortcuts", self)
        shortcuts_action.triggered.connect(self._show_shortcuts_help)
        help_menu.addAction(shortcuts_action)
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

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

        # 保存配置用于自动重连
        self._last_port_config = (port_data, cfg)

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
        
        # 启动自动重连
        if self._auto_reconnect_enabled and self._last_port_config:
            reconnect_delay = self._settings.get("serial/reconnect_delay", 3.0)
            self._reconnect_timer.start(int(reconnect_delay * 1000))

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

    def _get_x_presets(self) -> list:
        max_sec = self._max_x_window_seconds()
        presets = [
            0.01, 0.05, 0.1, 0.5,
            1.0, 2.0, 5.0, 10.0,
            30.0, 60.0, 120.0, 300.0,
            600.0, 1800.0, 3600.0, 7200.0,
            14400.0, 21600.0,
        ]
        visible_presets = [sec for sec in presets if sec <= max_sec]
        if max_sec not in visible_presets:
            visible_presets.append(max_sec)
        return visible_presets

    def _max_x_window_seconds(self) -> float:
        return self._max_buffer_samples / ADC_SAMPLE_RATE_HZ

    @staticmethod
    def _fmt_seconds(sec: float) -> str:
        if sec < 1.0:
            return f"{int(sec * 1000)} ms"
        if sec < 60.0:
            return f"{sec:g} s"
        if sec < 3600.0:
            return f"{sec / 60.0:g} min"
        if sec % 3600.0 == 0:
            return f"{sec / 3600.0:g} h"
        return f"{sec:g} s"

    def _on_x_window_changed(self, index):
        sec = self._x_window_combo.currentData()
        if sec is not None:
            self._set_x_span_spin(sec)
            self._waveform.set_x_window(sec)

    def _on_x_span_changed(self, value: float):
        self._waveform.set_x_window(value)

    def _on_buffer_limit_changed(self, value: float):
        self._max_buffer_samples = max(int(round(value * 1_000_000)), 1)
        self._waveform.set_max_buffer_samples(self._max_buffer_samples)
        self._refresh_x_window_limit()

    def _refresh_x_window_limit(self):
        max_sec = self._max_x_window_seconds()
        self._x_span_spin.setMaximum(max_sec)
        if self._x_span_spin.value() > max_sec:
            self._set_x_span_spin(max_sec)
            self._waveform.set_x_window(max_sec)
        self._rebuild_x_window_presets()

    def _rebuild_x_window_presets(self):
        current = self._x_span_spin.value()
        self._x_window_combo.blockSignals(True)
        self._x_window_combo.clear()
        for sec in self._get_x_presets():
            self._x_window_combo.addItem(self._fmt_seconds(sec), sec)
        idx = self._x_window_combo.findData(current)
        if idx >= 0:
            self._x_window_combo.setCurrentIndex(idx)
        else:
            self._x_window_combo.setCurrentIndex(-1)
        self._x_window_combo.blockSignals(False)

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
        self._waveform.append_frame(samples, seq)

    def _on_stats_updated(self, fps: float, sample_rate_hz: float, frame_count: int, crc_errors: int, seq_gaps: int, resync_count: int, short_frames: int):
        self._waveform.update_stats(fps, sample_rate_hz, frame_count, crc_errors, seq_gaps, resync_count, short_frames)

    def _on_serial_error(self, msg: str):
        QMessageBox.critical(self, "Serial Error", msg)
        self._disconnect()

    def _on_trigger_fired(self, event):
        """V2.2 触发事件处理"""
        # 在状态栏显示触发信息
        trigger_info = f"Trigger: {event.trigger_type} at {event.value} (t={event.timestamp:.3f}s)"
        self._status_label.setText(trigger_info)
        
        # 可以在这里添加更多的触发响应逻辑
        # 例如：标记触发点、暂停采集等

    # ── 录制 ──────────────────────────────────────────────

    def _on_record_fmt_changed(self, text):
        self._record_format = text.lower()

    def _on_set_record_path(self):
        """预设录制文件保存目录；每次录制自动生成新文件名。"""
        path = QFileDialog.getExistingDirectory(self, "设置录制保存目录", str(Path.home()))
        if path:
            self._record_dir = Path(path)
            self._btn_set_path.setText(f"Dir: ...{self._record_dir.name[-20:]}")
            self._btn_set_path.setToolTip(str(self._record_dir))

    def _toggle_record(self):
        if self._recording:
            self._stop_record()
        else:
            self._start_record()

    def _start_record(self):
        ext = self._record_format
        default_name = f"adc_record_{datetime.now():%Y%m%d_%H%M%S}.{ext}"
        # 获取保存路径
        if self._record_dir:
            path = str(self._record_dir / default_name)
        else:
            if ext == "csv":
                filter_str = "CSV Files (*.csv)"
            else:
                filter_str = "Binary Files (*.bin)"
            path, _ = QFileDialog.getSaveFileName(self, "选择录制文件",
                                                  str(Path.home() / default_name), filter_str)
            if not path:
                return

        try:
            self._recorder = FrameRecorder(path, ext, ADC_SAMPLE_RATE_HZ)
            self._recorder.start()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"无法创建文件: {e}")
            self._recorder = None
            return

        self._reader.set_record_sink(self._recorder.enqueue)
        self._recording = True
        self._record_frame_count = 0
        self._record_sample_count = 0
        self._record_start_time = time.perf_counter()
        self._record_serial_stats_start = self._reader.get_stats()
        self._btn_record.setText("Stop")
        self._btn_record.setStyleSheet("background-color: #c00; color: white;")
        self._record_fmt_combo.setEnabled(False)
        self._btn_set_path.setEnabled(False)
        self._status_label.setText(f"REC [{ext.upper()}]: {Path(path).name}")
        
        # V2.2 启动录制预览定时器
        self._record_preview_timer.start(500)  # 每500ms更新一次

    def _stop_record(self):
        # V2.2 停止录制预览定时器
        self._record_preview_timer.stop()
        
        self._reader.set_record_sink(None)
        stats = None
        if self._recorder:
            self._status_label.setText("Stopping REC: flushing queued frames...")
            stats = self._recorder.stop(self._record_serial_stats_delta())
            self._recorder = None

        elapsed = stats.elapsed_s if stats else time.perf_counter() - self._record_start_time
        self._record_frame_count = stats.frame_count if stats else self._record_frame_count
        self._record_sample_count = stats.sample_count if stats else self._record_sample_count
        self._recording = False
        self._btn_record.setText("Record")
        self._btn_record.setStyleSheet("")
        self._record_fmt_combo.setEnabled(True)
        self._btn_set_path.setEnabled(True)
        total_samples = self._record_sample_count
        if stats and not stats.complete:
            self._status_label.setText(
                f"Saved with warnings: {self._record_frame_count} frames ({total_samples} samples) in {elapsed:.1f}s"
            )
            QMessageBox.warning(
                self,
                "Recording Warning",
                "录制已保存，但检测到完整性风险。\n"
                f"文件: {stats.path}\n"
                f"SeqGap: {stats.seq_gap_count}, QueueDrop: {stats.queue_drop_count}\n"
                f"串口统计: {stats.serial_stats}\n"
                f"详情见: {stats.path}.meta.json",
            )
        else:
            self._status_label.setText(
                f"Saved {self._record_frame_count} frames ({total_samples} samples) in {elapsed:.1f}s"
            )

    def _record_serial_stats_delta(self) -> dict:
        current = self._reader.get_stats()
        return {
            key: current.get(key, 0) - self._record_serial_stats_start.get(key, 0)
            for key in current
        }

    def _update_record_preview(self):
        """V2.2 更新录制预览信息到状态栏"""
        if not self._recording or not self._recorder:
            return
        
        try:
            preview = self._recorder.get_preview()
            duration = preview['duration']
            file_size = preview['file_size']
            frame_count = preview['frame_count']
            paused = preview['paused']
            segment_index = preview['segment_index']
            
            # 格式化时长显示
            if duration < 60:
                duration_str = f"{duration:.1f}s"
            elif duration < 3600:
                duration_str = f"{duration/60:.1f}min"
            else:
                duration_str = f"{duration/3600:.1f}h"
            
            # 格式化文件大小显示
            if file_size < 1024:
                size_str = f"{file_size}B"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size/1024:.1f}KB"
            elif file_size < 1024 * 1024 * 1024:
                size_str = f"{file_size/(1024*1024):.1f}MB"
            else:
                size_str = f"{file_size/(1024*1024*1024):.1f}GB"
            
            # 构建状态文本
            fmt = self._record_format.upper()
            status_parts = [f"REC [{fmt}]: {duration_str}", f"{size_str}", f"{frame_count} frames"]
            
            if paused:
                status_parts.append("[PAUSED]")
            
            if segment_index > 0:
                status_parts.append(f"(Seg {segment_index})")
            
            self._status_label.setText(" | ".join(status_parts))
            
        except Exception as e:
            # 静默失败，不影响录制
            pass

    # ── 保存/导出 ──────────────────────────────────────────

    def _save_buffer(self):
        """保存当前显示缓冲区数据为与 Record 一致的 BIN v2 文件"""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "保存缓冲区数据",
            str(Path.home() / f"adc_buffer_{datetime.now():%Y%m%d_%H%M%S}.bin"),
            "Binary Files (*.bin)",
        )
        if not path:
            return

        snapshot = self._waveform.get_buffer_snapshot()
        if len(snapshot.data) == 0:
            QMessageBox.information(self, "No Data", "当前缓冲区没有可保存的数据")
            return
        if not snapshot.frames:
            QMessageBox.warning(self, "No Frame Metadata", "当前缓冲区缺少帧序号信息，无法保存为统一 BIN v2 格式")
            return

        try:
            with open(path, "wb") as f:
                header = struct.pack(
                    "<4sIIIIq",
                    BIN_MAGIC,
                    BIN_VERSION,
                    len(snapshot.frames),
                    int(round(snapshot.sample_rate_hz)),
                    0,
                    int(time.time()),
                )
                f.write(header)
                for frame in snapshot.frames:
                    f.write(struct.pack("<IH", frame.seq, len(frame.samples)))
                    f.write(frame.samples.tobytes())
            self._write_buffer_metadata(path, snapshot)
            QMessageBox.information(
                self,
                "Saved",
                f"已保存 {len(snapshot.frames)} 帧 / {len(snapshot.data)} 个采样点到:\n{path}",
            )
        except OSError as e:
            QMessageBox.critical(self, "Error", f"保存失败: {e}")

    def _export_csv(self):
        """导出缓冲区数据为 CSV，包含真实样本索引、时间和帧序号"""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出 CSV",
            str(Path.home() / f"adc_data_{datetime.now():%Y%m%d_%H%M%S}.csv"),
            "CSV Files (*.csv)",
        )
        if not path:
            return

        snapshot = self._waveform.get_buffer_snapshot()
        if len(snapshot.data) == 0:
            QMessageBox.information(self, "No Data", "当前缓冲区没有可导出的数据")
            return

        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write("# source=display_buffer\n")
                f.write(f"# sample_rate={snapshot.sample_rate_hz:.6f}Hz\n")
                f.write(f"# samples={len(snapshot.data)}\n")
                f.write(f"# first_sample_index={snapshot.first_sample_index}\n")
                f.write(f"# total_samples_seen={snapshot.total_samples}\n")
                f.write("# seq,sample_index,time_s,adc_value\n")
                if snapshot.frames:
                    for frame in snapshot.frames:
                        for i, value in enumerate(frame.samples):
                            sample_index = frame.start_sample_index + i
                            t = sample_index / snapshot.sample_rate_hz
                            f.write(f"{frame.seq},{sample_index},{t:.8f},{int(value)}\n")
                else:
                    for i, value in enumerate(snapshot.data):
                        sample_index = snapshot.first_sample_index + i
                        t = sample_index / snapshot.sample_rate_hz
                        f.write(f",{sample_index},{t:.8f},{int(value)}\n")
            QMessageBox.information(self, "Exported", f"已导出 {len(snapshot.data)} 个采样点到:\n{path}")
        except OSError as e:
            QMessageBox.critical(self, "Error", f"导出失败: {e}")

    @staticmethod
    def _write_buffer_metadata(path: str, snapshot):
        frames = snapshot.frames
        metadata = {
            "source": "display_buffer",
            "format": "bin",
            "bin_version": BIN_VERSION,
            "frame_layout": "header + repeated [seq:uint32_le][cnt:uint16_le][samples:uint16_le...]",
            "path": str(path),
            "sample_rate_hz": snapshot.sample_rate_hz,
            "frame_count": len(frames),
            "sample_count": len(snapshot.data),
            "first_sample_index": snapshot.first_sample_index,
            "last_sample_index": snapshot.first_sample_index + len(snapshot.data) - 1,
            "total_samples_seen": snapshot.total_samples,
            "first_seq": frames[0].seq if frames else None,
            "last_seq": frames[-1].seq if frames else None,
            "complete": False,
            "note": "This is a display buffer export, not a full recording.",
        }
        metadata_path = Path(path).with_suffix(Path(path).suffix + ".meta.json")
        metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── 事件 ──────────────────────────────────────────────

    def _restore_window_state(self):
        """恢复窗口状态"""
        geometry = self._settings.get("window/geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            width = self._settings.get("window/width", 1100)
            height = self._settings.get("window/height", 650)
            self.resize(width, height)

    def _restore_settings(self):
        """恢复用户设置"""
        # 恢复串口设置
        last_port = self._settings.get("serial/last_port", "")
        if last_port:
            idx = self._port_combo.findText(last_port, Qt.MatchFlag.MatchStartsWith)
            if idx >= 0:
                self._port_combo.setCurrentIndex(idx)
        
        baudrate = self._settings.get("serial/baudrate", UART_BAUDRATE)
        self._baud_combo.setCurrentText(str(baudrate))
        
        databits = self._settings.get("serial/databits", 8)
        self._databits_combo.setCurrentText(str(databits))
        
        stopbits = self._settings.get("serial/stopbits", 1.0)
        self._stopbits_combo.setCurrentText(str(stopbits))
        
        parity = self._settings.get("serial/parity", "None")
        self._parity_combo.setCurrentText(parity)
        
        # 恢复显示设置
        x_window = self._settings.get("display/x_window", 2.0)
        self._x_span_spin.setValue(x_window)
        self._waveform.set_x_window(x_window)
        
        buffer_limit = self._settings.get("display/buffer_limit", 10.0)
        self._buffer_limit_spin.setValue(buffer_limit)
        
        y_auto = self._settings.get("display/y_auto", True)
        if not y_auto:
            y_min = self._settings.get("display/y_min", 0.0)
            y_max = self._settings.get("display/y_max", 1200.0)
            self._waveform.set_y_manual_range(y_min, y_max)
            self._y_min_spin.setValue(y_min)
            self._y_max_spin.setValue(y_max)
            self._btn_y_mode.setText("Manual")
        
        # 恢复录制设置
        record_format = self._settings.get("record/format", "bin")
        self._record_fmt_combo.setCurrentText(record_format.upper())
        
        record_dir = self._settings.get("record/save_dir", "")
        if record_dir:
            self._record_dir = Path(record_dir)
            self._btn_set_path.setText(f"Dir: ...{self._record_dir.name[-20:]}")
            self._btn_set_path.setToolTip(str(self._record_dir))

    def _save_settings(self):
        """保存用户设置"""
        # 保存窗口状态
        self._settings.set("window/geometry", self.saveGeometry())
        self._settings.set("window/width", self.width())
        self._settings.set("window/height", self.height())
        
        # 保存串口设置
        port_data = self._port_combo.currentData()
        if port_data:
            self._settings.set("serial/last_port", port_data)
        
        self._settings.set("serial/baudrate", int(self._baud_combo.currentText()))
        self._settings.set("serial/databits", int(self._databits_combo.currentText()))
        
        stopbits_text = self._stopbits_combo.currentText()
        self._settings.set("serial/stopbits", float(stopbits_text))
        
        self._settings.set("serial/parity", self._parity_combo.currentText())
        self._settings.set("serial/auto_reconnect", self._auto_reconnect_enabled)
        
        # 保存显示设置
        self._settings.set("display/x_window", self._x_span_spin.value())
        self._settings.set("display/buffer_limit", self._buffer_limit_spin.value())
        self._settings.set("display/y_auto", self._waveform._y_auto_fit)
        
        y_min, y_max = self._waveform.get_y_manual_range()
        self._settings.set("display/y_min", y_min)
        self._settings.set("display/y_max", y_max)
        
        # 保存录制设置
        self._settings.set("record/format", self._record_format)
        if self._record_dir:
            self._settings.set("record/save_dir", str(self._record_dir))
        
        self._settings.sync()

    def _switch_theme(self, theme: str):
        """切换主题"""
        Theme.apply_theme(theme)
        self._settings.set("display/theme", theme)
        self._settings.sync()
        
        # 更新波形颜色
        colors = Theme.get_waveform_colors(theme)
        self._waveform.apply_theme_colors(colors)
        
        QMessageBox.information(
            self,
            "Theme Changed",
            f"Theme switched to {theme.capitalize()}.\nSome changes will take full effect after restart.",
        )

    def _toggle_auto_reconnect(self):
        """切换自动重连"""
        self._auto_reconnect_enabled = self._auto_reconnect_action.isChecked()
        self._settings.set("serial/auto_reconnect", self._auto_reconnect_enabled)
        self._settings.sync()
        
        status = "enabled" if self._auto_reconnect_enabled else "disabled"
        self._status_label.setText(f"Auto-reconnect {status}")

    def _attempt_reconnect(self):
        """尝试自动重连"""
        if not self._auto_reconnect_enabled or self._reader.isRunning():
            self._reconnect_timer.stop()
            return
        
        if self._last_port_config:
            port, cfg = self._last_port_config
            self._reader.configure(port, **cfg)
            self._reader.start()
            
            if self._reader.isRunning():
                self._reconnect_timer.stop()
                self._btn_connect.setText("Disconnect")
                self._btn_record.setEnabled(True)
                self._set_config_enabled(False)
                self._status_label.setText(f"Reconnected: {port} @ {cfg['baudrate']}")
                QMessageBox.information(self, "Reconnected", f"Successfully reconnected to {port}")

    def _toggle_record_shortcut(self):
        """快捷键触发录制"""
        if not self._btn_record.isEnabled():
            return
        self._toggle_record()

    def _show_shortcuts_help(self):
        """显示快捷键帮助"""
        shortcuts = """
        <h3>Keyboard Shortcuts</h3>
        <table cellpadding="4">
        <tr><td><b>Space</b></td><td>Resume auto-scroll (Follow)</td></tr>
        <tr><td><b>C</b></td><td>Connect/Disconnect serial</td></tr>
        <tr><td><b>R</b></td><td>Start/Stop recording</td></tr>
        <tr><td><b>F</b></td><td>Fit all buffer data in view</td></tr>
        <tr><td><b>Y</b></td><td>Toggle Y-axis auto/manual mode</td></tr>
        <tr><td><b>+</b></td><td>Zoom in (X-axis)</td></tr>
        <tr><td><b>-</b></td><td>Zoom out (X-axis)</td></tr>
        <tr><td><b>Ctrl+S</b></td><td>Save buffer to file</td></tr>
        <tr><td><b>Ctrl+E</b></td><td>Export buffer as CSV</td></tr>
        <tr><td><b>Ctrl+Q</b></td><td>Exit application</td></tr>
        </table>
        <p><i>Mouse: Left-drag to pan, Scroll-wheel to zoom, Double-click to follow</i></p>
        """
        QMessageBox.information(self, "Keyboard Shortcuts", shortcuts)

    def _show_about(self):
        """显示关于对话框"""
        from .version import __version__
        about_text = f"""
        <h2>{APP_TITLE}</h2>
        <p>Version: {__version__}</p>
        <p>A PyQt6/pyqtgraph desktop viewer for real-time ADC waveform data over UART.</p>
        <p>Copyright © 2024 X-GEN-LAB</p>
        <p>License: MIT</p>
        <p><a href="https://github.com/X-Gen-Lab/xgen-waveform-viewer">GitHub Repository</a></p>
        """
        QMessageBox.about(self, "About", about_text)
    
    # ── V2.4: 导出功能 ──────────────────────────────────────
    
    def _export_png(self):
        """导出波形为 PNG 图片"""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出为 PNG",
            str(Path.home() / f"waveform_{datetime.now():%Y%m%d_%H%M%S}.png"),
            "PNG Files (*.png)",
        )
        if not path:
            return
        
        success = WaveformExporter.export_image_png(self._waveform, path, 1920, 1080)
        
        if success:
            QMessageBox.information(self, "Success", f"波形已导出到:\n{path}")
        else:
            QMessageBox.critical(self, "Error", "导出 PNG 失败")
    
    def _export_svg(self):
        """导出波形为 SVG 矢量图"""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出为 SVG",
            str(Path.home() / f"waveform_{datetime.now():%Y%m%d_%H%M%S}.svg"),
            "SVG Files (*.svg)",
        )
        if not path:
            return
        
        success = WaveformExporter.export_image_svg(self._waveform, path, 1920, 1080)
        
        if success:
            QMessageBox.information(self, "Success", f"波形已导出到:\n{path}")
        else:
            QMessageBox.critical(self, "Error", "导出 SVG 失败")
    
    def _export_matlab(self):
        """导出数据为 MATLAB .mat 格式"""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出为 MATLAB",
            str(Path.home() / f"waveform_{datetime.now():%Y%m%d_%H%M%S}.mat"),
            "MATLAB Files (*.mat)",
        )
        if not path:
            return
        
        snapshot = self._waveform.get_buffer_snapshot()
        if len(snapshot.data) == 0:
            QMessageBox.information(self, "No Data", "当前缓冲区没有可导出的数据")
            return
        
        metadata = {
            'first_sample_index': snapshot.first_sample_index,
            'total_samples_seen': snapshot.total_samples,
            'export_source': 'display_buffer',
        }
        
        success = WaveformExporter.export_matlab(
            snapshot.data,
            path,
            int(snapshot.sample_rate_hz),
            metadata
        )
        
        if success:
            QMessageBox.information(
                self,
                "Success",
                f"已导出 {len(snapshot.data)} 个采样点到 MATLAB 格式:\n{path}"
            )
        else:
            QMessageBox.critical(
                self,
                "Error",
                "导出 MATLAB 格式失败\n请确保已安装 scipy: pip install scipy"
            )
    
    def _export_hdf5(self):
        """导出数据为 HDF5 格式"""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出为 HDF5",
            str(Path.home() / f"waveform_{datetime.now():%Y%m%d_%H%M%S}.h5"),
            "HDF5 Files (*.h5 *.hdf5)",
        )
        if not path:
            return
        
        snapshot = self._waveform.get_buffer_snapshot()
        if len(snapshot.data) == 0:
            QMessageBox.information(self, "No Data", "当前缓冲区没有可导出的数据")
            return
        
        metadata = {
            'first_sample_index': snapshot.first_sample_index,
            'total_samples_seen': snapshot.total_samples,
            'export_source': 'display_buffer',
        }
        
        success = WaveformExporter.export_hdf5(
            snapshot.data,
            path,
            int(snapshot.sample_rate_hz),
            metadata,
            compression=True
        )
        
        if success:
            QMessageBox.information(
                self,
                "Success",
                f"已导出 {len(snapshot.data)} 个采样点到 HDF5 格式:\n{path}\n"
                f"文件使用 gzip 压缩，可高效存储大量数据"
            )
        else:
            QMessageBox.critical(
                self,
                "Error",
                "导出 HDF5 格式失败\n请确保已安装 h5py: pip install h5py"
            )
    
    def _export_report_html(self):
        """导出统计报告为 HTML"""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出统计报告",
            str(Path.home() / f"report_{datetime.now():%Y%m%d_%H%M%S}.html"),
            "HTML Files (*.html)",
        )
        if not path:
            return
        
        snapshot = self._waveform.get_buffer_snapshot()
        if len(snapshot.data) == 0:
            QMessageBox.information(self, "No Data", "当前缓冲区没有可导出的数据")
            return
        
        # 计算统计信息
        stats = {
            'sample_rate_hz': snapshot.sample_rate_hz,
            'total_samples': len(snapshot.data),
            'duration_s': len(snapshot.data) / snapshot.sample_rate_hz,
            'mean': float(np.mean(snapshot.data)),
            'rms': float(np.sqrt(np.mean(snapshot.data.astype(float) ** 2))),
            'max': float(np.max(snapshot.data)),
            'min': float(np.min(snapshot.data)),
            'peak_to_peak': float(np.max(snapshot.data) - np.min(snapshot.data)),
        }
        
        # 可选：先导出波形图片
        image_path = Path(path).with_suffix('.png')
        WaveformExporter.export_image_png(self._waveform, str(image_path), 1920, 1080)
        
        success = WaveformExporter.export_statistics_html(
            stats,
            path,
            waveform_image_path=image_path.name
        )
        
        if success:
            QMessageBox.information(
                self,
                "Success",
                f"统计报告已导出到:\n{path}\n\n"
                f"波形图片: {image_path}"
            )
        else:
            QMessageBox.critical(self, "Error", "导出报告失败")
    
    # ── V2.4: 回放功能 ──────────────────────────────────────
    
    def _show_playback_panel(self):
        """显示回放控制面板"""
        if self._playback_panel is None:
            self._playback_panel = PlaybackPanel(self)
            self._playback_panel.file_loaded.connect(self._on_playback_file_loaded)
            self._playback_panel.playback_started.connect(self._on_playback_started)
            self._playback_panel.playback_stopped.connect(self._on_playback_stopped)
            
            # 创建浮动窗口
            self._playback_panel.setWindowTitle("数据回放")
            self._playback_panel.setMinimumWidth(400)
            self._playback_panel.setMinimumHeight(300)
        
        self._playback_panel.show()
        self._playback_panel.raise_()
        self._playback_panel.activateWindow()
    
    def _on_playback_file_loaded(self, info):
        """回放文件加载完成"""
        self._status_label.setText(f"回放文件已加载: {Path(info.path).name}")
    
    def _on_playback_started(self):
        """回放开始"""
        # 进入回放模式
        self._playback_mode = True
        
        # 禁用串口连接
        self._btn_connect.setEnabled(False)
        
        # 清空当前波形
        self._waveform.clear()
        
        # 连接回放读取器的信号到波形显示
        reader = self._playback_panel.get_reader()
        if reader:
            reader.frame_ready.connect(self._on_frame_ready)
        
        self._status_label.setText("回放中...")
    
    def _on_playback_stopped(self):
        """回放停止"""
        # 退出回放模式
        self._playback_mode = False
        
        # 恢复串口连接按钮
        self._btn_connect.setEnabled(True)
        
        # 断开回放信号
        reader = self._playback_panel.get_reader()
        if reader:
            try:
                reader.frame_ready.disconnect(self._on_frame_ready)
            except:
                pass
        
        self._status_label.setText("回放已停止")

    def closeEvent(self, event):
        self._save_settings()
        if self._reader.isRunning():
            self._disconnect()
        event.accept()
