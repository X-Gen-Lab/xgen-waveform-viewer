"""
波形显示组件
基于 pyqtgraph，实时滚动显示 ADC 采样数据
X 轴: 自动滚动 / 手动缩放平移 / 滚轮缩放
Y 轴: 自适应 / 固定 uint16 全范围

V2.3: 添加性能优化支持 (降采样渲染)
"""

from dataclasses import dataclass

import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, QEvent, QTimer

from .config import ADC_MAX_VALUE, ADC_SAMPLE_RATE_HZ, DISPLAY_BUFFER_SIZE


# 可选的 X 轴窗口宽度 (秒)
X_WINDOW_PRESETS = [0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
X_WINDOW_DEFAULT = 2.0
PLOT_REFRESH_MS = 33
MIN_EFFECTIVE_SAMPLE_RATE_HZ = 1.0
BUFFER_HEADROOM = 1.25
MAX_BUFFER_SAMPLES = 10_000_000
FOLLOW_RIGHT_PADDING_RATIO = 0.06
Y_MANUAL_MIN_DEFAULT = 0.0
Y_MANUAL_MAX_DEFAULT = 1200.0


@dataclass
class BufferFrame:
    seq: int
    start_sample_index: int
    samples: np.ndarray


@dataclass
class BufferSnapshot:
    data: np.ndarray
    frames: list[BufferFrame]
    first_sample_index: int
    total_samples: int
    sample_rate_hz: float


class WaveformWidget(QWidget):
    """实时波形显示组件"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # 环形缓冲区
        self._buffer = np.zeros(DISPLAY_BUFFER_SIZE, dtype=np.uint16)
        self._write_pos = 0
        self._total_samples = 0
        self._frame_history: list[BufferFrame] = []
        self._max_buffer_samples = MAX_BUFFER_SAMPLES
        self._effective_sample_rate_hz = float(ADC_SAMPLE_RATE_HZ)
        self._plot_dirty = False

        # X 轴控制
        self._x_auto_scroll = True       # 自动滚动跟随最新数据
        self._x_window_sec = X_WINDOW_DEFAULT  # 可见窗口宽度
        self._x_user_interacting = False # 用户正在交互中 (防止递归)

        # Y 轴控制
        self._y_auto_fit = True
        self._y_margin = 0.05
        self._y_manual_min = Y_MANUAL_MIN_DEFAULT
        self._y_manual_max = Y_MANUAL_MAX_DEFAULT
        
        # V2.3: 性能优化器（可选，由外部设置）
        self._perf_optimizer = None
        self._downsample_enabled = False

        self._setup_ui()

        self._plot_timer = QTimer(self)
        self._plot_timer.setInterval(PLOT_REFRESH_MS)
        self._plot_timer.timeout.connect(self._flush_plot_update)
        self._plot_timer.start()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 数据完整性告警横幅 (默认隐藏)
        self._warn_banner = QLabel()
        self._warn_banner.setStyleSheet(
            "background-color: #8B0000; color: #FFD700; font-size: 13px; "
            "font-weight: bold; padding: 4px 12px;"
        )
        self._warn_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._warn_banner.setVisible(False)
        layout.addWidget(self._warn_banner)

        # 波形图
        self._plot_widget = pg.PlotWidget()
        self._plot_widget.setBackground((3, 7, 10))
        self._plot_widget.showGrid(x=True, y=True, alpha=0.22)
        self._plot_widget.setLabel("left", "ADC Value")
        self._plot_widget.setLabel("bottom", "Time", units="s")
        self._plot_widget.setTitle("ADC Waveform")
        self._plot_widget.setLimits(xMin=0)
        self._plot_widget.setMenuEnabled(False)

        # 禁用 Y 轴 SI 前缀 (避免自动 kLSB)
        self._plot_widget.getAxis("left").enableAutoSIPrefix(False)
        self._plot_widget.getAxis("left").setPen(pg.mkPen((150, 165, 170)))
        self._plot_widget.getAxis("bottom").setPen(pg.mkPen((150, 165, 170)))
        self._plot_widget.getAxis("left").setTextPen(pg.mkPen((225, 235, 238)))
        self._plot_widget.getAxis("bottom").setTextPen(pg.mkPen((225, 235, 238)))

        # 允许鼠标缩放/拖拽
        vb = self._plot_widget.getViewBox()
        vb.setMouseEnabled(x=True, y=True)
        vb.setMouseMode(pg.ViewBox.PanMode)

        # 曲线
        self._curve = self._plot_widget.plot(
            pen=pg.mkPen(color=(0, 255, 160), width=1.4),
            name="ADC",
        )
        self._curve.setDownsampling(auto=True, method="peak")
        self._curve.setClipToView(True)

        self._empty_label = QLabel("等待有效 ADC 帧")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(
            "color: #777; background: transparent; font-size: 18px; font-weight: 600;"
        )
        self._empty_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._empty_label.setVisible(True)

        self._v_cursor = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen((255, 212, 96, 150), width=1))
        self._h_cursor = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen((255, 212, 96, 120), width=1))
        self._plot_widget.addItem(self._v_cursor, ignoreBounds=True)
        self._plot_widget.addItem(self._h_cursor, ignoreBounds=True)
        self._v_cursor.hide()
        self._h_cursor.hide()
        
        # 保存主题颜色引用
        self._theme_colors = {
            "curve": (0, 255, 160),
            "cursor_v": (255, 212, 96, 150),
            "cursor_h": (255, 212, 96, 120),
            "grid_alpha": 0.22,
            "text": (225, 235, 238),
            "axis": (150, 165, 170),
        }

        # 监听 X 轴范围变化 (用户拖拽/缩放)
        self._plot_widget.sigXRangeChanged.connect(self._on_x_range_changed)
        self._mouse_proxy = pg.SignalProxy(
            self._plot_widget.scene().sigMouseMoved,
            rateLimit=60,
            slot=self._on_mouse_moved,
        )
        self._plot_widget.scene().sigMouseClicked.connect(self._on_mouse_clicked)
        self._plot_widget.viewport().installEventFilter(self)

        layout.addWidget(self._plot_widget)
        self._empty_label.setParent(self._plot_widget)
        self._empty_label.setGeometry(self._plot_widget.rect())

        # 底部信息栏
        info_layout = QHBoxLayout()
        self._lbl_fps = QLabel("FPS: --")
        self._lbl_sample_rate = QLabel("Rate: -- Hz")
        self._lbl_frames = QLabel("Frames: 0")
        self._lbl_crc_err = QLabel("CRC: 0")
        self._lbl_short = QLabel("Short: 0")
        self._lbl_seq_gap = QLabel("SeqGap: 0")
        self._lbl_resync = QLabel("Resync: 0")
        self._lbl_latest = QLabel("Latest: --")
        self._lbl_range = QLabel("Range: --")
        self._lbl_cursor = QLabel("Cursor: --")
        self._lbl_view = QLabel("View: Follow")
        self._lbl_duration = QLabel("Duration: 0.0 s")

        for lbl in (self._lbl_fps, self._lbl_sample_rate, self._lbl_frames, self._lbl_crc_err, self._lbl_short, self._lbl_seq_gap, self._lbl_resync, self._lbl_latest, self._lbl_range, self._lbl_cursor, self._lbl_view, self._lbl_duration):
            lbl.setStyleSheet("color: #aaa; font-size: 11px; padding: 2px 8px;")
            info_layout.addWidget(lbl)
        info_layout.addStretch()

        layout.addLayout(info_layout)

    # ── X 轴交互 ──────────────────────────────────────────

    def _on_mouse_moved(self, event):
        pos = event[0]
        if not self._plot_widget.sceneBoundingRect().contains(pos):
            self._hide_cursor()
            return

        mouse_point = self._plot_widget.getViewBox().mapSceneToView(pos)
        x = float(mouse_point.x())
        y = float(mouse_point.y())
        if x < 0:
            self._hide_cursor()
            return

        self._v_cursor.setPos(x)
        self._h_cursor.setPos(y)
        self._v_cursor.show()
        self._h_cursor.show()

        latest_t = self._sample_index_to_time(self._total_samples) if self._total_samples > 0 else 0.0
        dt_latest = latest_t - x
        nearest = self._nearest_sample_value(x)
        if nearest is None:
            self._lbl_cursor.setText(f"Cursor: {x:.4f}s, {y:.0f}")
        else:
            self._lbl_cursor.setText(f"Cursor: {x:.4f}s, {nearest} ({dt_latest:+.3f}s)")

    def _on_mouse_clicked(self, event):
        if event.double() and event.button() == Qt.MouseButton.LeftButton:
            self.resume_auto_scroll()

    def _hide_cursor(self):
        self._v_cursor.hide()
        self._h_cursor.hide()
        self._lbl_cursor.setText("Cursor: --")

    def _nearest_sample_value(self, time_s: float) -> int | None:
        data = self._ordered_buffer_data()
        if len(data) == 0:
            return None

        first_sample_index = max(0, self._total_samples - len(data))
        sample_index = int(round(time_s * self._effective_sample_rate_hz))
        offset = sample_index - first_sample_index
        if offset < 0 or offset >= len(data):
            return None
        return int(data[offset])

    def _on_x_range_changed(self, widget, xrange):
        """检测用户手动操作 X 轴，决定是否暂停自动滚动"""
        if self._x_user_interacting:
            return  # 程序内部设置，忽略

        if not self._x_auto_scroll:
            return  # 已暂停，不处理

        # 用户拖拽/缩放 → 暂停自动滚动
        self._x_auto_scroll = False
        # 同步窗口宽度
        x_min, x_max = xrange
        self._x_window_sec = max(x_max - x_min, 0.001)
        self._update_view_label()

    def _is_near_latest(self, x_max: float) -> bool:
        """判断视图右边缘是否接近最新数据"""
        if self._total_samples == 0:
            return False
        latest_t = self._total_samples / self._effective_sample_rate_hz
        return (latest_t - x_max) < (self._x_window_sec * 0.1)

    def set_x_window(self, seconds: float):
        """设置 X 轴可见窗口宽度"""
        self._x_window_sec = max(seconds, 0.001)
        self._ensure_buffer_capacity()
        if self._x_auto_scroll and self._total_samples > 0:
            self._apply_auto_scroll()
        self._update_view_label()

    def get_x_window_presets(self):
        return X_WINDOW_PRESETS

    def get_x_window(self):
        return self._x_window_sec

    def show_all_buffer(self):
        """显示当前缓冲区内的全部数据"""
        if self._total_samples == 0:
            return

        first_t, latest_t = self._time_bounds()
        span = max(latest_t - first_t, 0.001)
        pad = max(span * 0.03, 0.001)
        x_min = max(0.0, first_t - pad)
        x_max = latest_t + pad

        self._x_auto_scroll = False
        self._x_window_sec = max(x_max - x_min, 0.001)
        self._x_user_interacting = True
        self._plot_widget.setXRange(x_min, x_max, padding=0)
        self._x_user_interacting = False
        self._update_view_label()

    def zoom_x(self, factor: float):
        """围绕当前视图中心缩放 X 轴；factor < 1 放大，factor > 1 缩小"""
        factor = max(float(factor), 0.001)
        x_min, x_max = self._plot_widget.getViewBox().viewRange()[0]
        center = (x_min + x_max) / 2.0
        width = max((x_max - x_min) * factor, 0.001)
        data_first, data_latest = self._time_bounds()
        max_width = max(data_latest - data_first, self._x_window_sec, 0.001)
        width = min(width, max_width * 1.2)

        new_min = max(0.0, center - width / 2.0)
        new_max = new_min + width
        self._x_auto_scroll = False
        self._x_window_sec = width
        self._x_user_interacting = True
        self._plot_widget.setXRange(new_min, new_max, padding=0)
        self._x_user_interacting = False
        self._update_view_label()

    # ── Y 轴 ──────────────────────────────────────────────

    def toggle_y_mode(self):
        """切换 Y 轴模式: 自适应 ↔ 固定"""
        self._y_auto_fit = not self._y_auto_fit
        self._plot_dirty = True
        return self._y_auto_fit

    def set_y_auto(self):
        self._y_auto_fit = True
        self._plot_dirty = True

    def set_y_manual_range(self, y_min: float, y_max: float):
        if y_max <= y_min:
            y_max = y_min + 1.0
        self._y_manual_min = float(y_min)
        self._y_manual_max = float(y_max)
        self._y_auto_fit = False
        self._plot_dirty = True

    def set_y_full_range(self):
        self.set_y_manual_range(0.0, float(ADC_MAX_VALUE))

    def set_y_center_span(self, center: float, span: float):
        span = max(float(span), 1.0)
        half = span / 2.0
        self.set_y_manual_range(center - half, center + half)

    def get_y_manual_range(self) -> tuple[float, float]:
        return self._y_manual_min, self._y_manual_max

    def get_visible_stats(self) -> dict:
        data = self._ordered_buffer_data()
        if len(data) == 0:
            return {"has_data": False}

        data_f = data.astype(np.float32)
        first_sample_index = max(0, self._total_samples - len(data_f))
        t = self._sample_index_to_time(first_sample_index + np.arange(len(data_f), dtype=np.float64))
        visible = self._visible_data(data_f, t)
        if len(visible) == 0:
            visible = data_f

        y_min = float(np.min(visible))
        y_max = float(np.max(visible))
        return {
            "has_data": True,
            "min": y_min,
            "max": y_max,
            "center": (y_min + y_max) / 2.0,
            "span": max(y_max - y_min, 1.0),
        }

    # ── 自动滚动 ──────────────────────────────────────────

    def _apply_auto_scroll(self):
        """应用自动滚动 (设置 X 范围到最新数据)"""
        if self._total_samples == 0:
            return
        latest_t = self._sample_index_to_time(self._total_samples)
        first_t = self._sample_index_to_time(max(0, self._total_samples - self._data_len()))
        data_duration = max(0.0, latest_t - first_t)

        if data_duration < self._x_window_sec:
            x_min = first_t
            x_max = first_t + self._x_window_sec
        else:
            right_padding = self._x_window_sec * FOLLOW_RIGHT_PADDING_RATIO
            x_max = latest_t + right_padding
            x_min = max(first_t, x_max - self._x_window_sec)

        self._x_user_interacting = True
        self._plot_widget.setXRange(x_min, x_max, padding=0)
        self._x_user_interacting = False
        self._update_view_label()

    def resume_auto_scroll(self):
        """恢复 X 轴自动滚动"""
        self._x_auto_scroll = True
        self._apply_auto_scroll()
        self._update_view_label()

    def is_auto_scroll(self):
        return self._x_auto_scroll

    # ── 数据 ──────────────────────────────────────────────

    def append_frame(self, samples: np.ndarray, seq: int | None = None):
        """添加一帧采样数据"""
        n = len(samples)
        if n == 0:
            return

        start_sample_index = self._total_samples
        self._ensure_buffer_capacity(incoming_samples=n)
        buf_len = len(self._buffer)
        if n >= buf_len:
            self._buffer[:] = samples[-buf_len:]
            self._write_pos = 0
            self._total_samples += n
            self._append_frame_history(seq, start_sample_index, samples)
            self._update_plot()
            return

        # 写入环形缓冲区
        end_pos = self._write_pos + n
        if end_pos <= buf_len:
            self._buffer[self._write_pos : end_pos] = samples
        else:
            first = buf_len - self._write_pos
            self._buffer[self._write_pos :] = samples[:first]
            self._buffer[: n - first] = samples[first:]

        self._write_pos = end_pos % buf_len
        self._total_samples += n
        self._append_frame_history(seq, start_sample_index, samples)

        self._plot_dirty = True

    def _append_frame_history(self, seq: int | None, start_sample_index: int, samples: np.ndarray):
        if seq is None:
            self._trim_frame_history()
            return

        self._frame_history.append(BufferFrame(int(seq), start_sample_index, samples.copy()))
        self._trim_frame_history()

    def _trim_frame_history(self):
        first_sample_index = max(0, self._total_samples - self._data_len())
        trimmed: list[BufferFrame] = []
        for frame in self._frame_history:
            frame_end = frame.start_sample_index + len(frame.samples)
            if frame_end <= first_sample_index:
                continue

            if frame.start_sample_index < first_sample_index:
                offset = first_sample_index - frame.start_sample_index
                trimmed.append(BufferFrame(frame.seq, first_sample_index, frame.samples[offset:].copy()))
            else:
                trimmed.append(frame)

        self._frame_history = trimmed

    def _flush_plot_update(self):
        if not self._plot_dirty:
            return
        self._plot_dirty = False
        self._update_plot()

    def _ordered_buffer_data(self) -> np.ndarray:
        if self._total_samples < len(self._buffer):
            return self._buffer[: self._write_pos]
        return np.concatenate([
            self._buffer[self._write_pos :],
            self._buffer[: self._write_pos],
        ])

    def _data_len(self) -> int:
        return min(self._total_samples, len(self._buffer))

    def _sample_index_to_time(self, sample_index: int) -> float:
        return sample_index / self._effective_sample_rate_hz

    def _time_bounds(self) -> tuple[float, float]:
        latest_t = self._sample_index_to_time(self._total_samples)
        first_t = self._sample_index_to_time(max(0, self._total_samples - self._data_len()))
        return first_t, latest_t

    @staticmethod
    def _fmt_time_span(seconds: float) -> str:
        seconds = max(float(seconds), 0.0)
        if seconds < 1.0:
            return f"{seconds * 1000:.1f} ms"
        return f"{seconds:.3f} s"

    def _update_view_label(self):
        if not hasattr(self, "_lbl_view"):
            return
        x_min, x_max = self._plot_widget.getViewBox().viewRange()[0]
        span = max(x_max - x_min, 0.0)
        mode = "Follow" if self._x_auto_scroll else "Manual"
        self._lbl_view.setText(
            f"View: {mode} {x_min:.3f}..{x_max:.3f}s ({self._fmt_time_span(span)})"
        )

    def _target_buffer_size(self, incoming_samples: int = 0) -> int:
        window_samples = int(self._effective_sample_rate_hz * self._x_window_sec * BUFFER_HEADROOM)
        minimum = max(DISPLAY_BUFFER_SIZE, incoming_samples, 1)
        return min(max(window_samples, minimum), self._max_buffer_samples)

    def _ensure_buffer_capacity(self, incoming_samples: int = 0):
        target_size = self._target_buffer_size(incoming_samples)
        if target_size <= len(self._buffer):
            return

        self._resize_buffer(target_size)

    def _resize_buffer(self, target_size: int):
        data = self._ordered_buffer_data()
        keep = min(len(data), target_size)
        new_buffer = np.zeros(target_size, dtype=np.uint16)
        if keep > 0:
            new_buffer[:keep] = data[-keep:]

        self._buffer = new_buffer
        self._write_pos = keep % target_size
        self._trim_frame_history()

    def set_max_buffer_samples(self, samples: int):
        self._max_buffer_samples = max(int(samples), DISPLAY_BUFFER_SIZE)
        max_window_sec = self._max_buffer_samples / self._effective_sample_rate_hz
        if self._x_window_sec > max_window_sec:
            self._x_window_sec = max(max_window_sec, 0.001)
        if len(self._buffer) > self._max_buffer_samples:
            self._resize_buffer(self._max_buffer_samples)
        self._plot_dirty = True

    def get_max_buffer_samples(self) -> int:
        return self._max_buffer_samples

    def _update_plot(self):
        """刷新波形显示"""
        data = self._ordered_buffer_data()
        self._empty_label.setVisible(len(data) == 0)
        if len(data) == 0:
            return

        data_f = data.astype(np.float32)
        first_sample_index = max(0, self._total_samples - len(data_f))
        t = self._sample_index_to_time(first_sample_index + np.arange(len(data_f), dtype=np.float64))

        # V2.3: 使用性能优化器进行降采样渲染
        if self._perf_optimizer and self._downsample_enabled:
            try:
                t_render, data_render = self._perf_optimizer.prepare_render_data(t, data_f)
                self._curve.setData(t_render, data_render)
            except Exception:
                # 降采样失败时回退到原始数据
                self._curve.setData(t, data_f)
        else:
            # 更新曲线
            self._curve.setData(t, data_f)

        # X 轴
        if self._x_auto_scroll and len(t) > 0:
            self._apply_auto_scroll()
        elif not self._x_auto_scroll and len(t) > 0:
            # 检查用户是否滚回了最新位置 → 自动恢复滚动
            x_range = self._plot_widget.getViewBox().viewRange()[0]
            if self._is_near_latest(x_range[1]):
                self._x_auto_scroll = True

        # Y 轴
        visible_data = self._visible_data(data_f, t)
        if self._y_auto_fit:
            y_lo = float(np.min(visible_data))
            y_hi = float(np.max(visible_data))
            span = max(y_hi - y_lo, 1.0)
            pad = span * self._y_margin
            self._x_user_interacting = True
            self._plot_widget.setYRange(y_lo - pad, y_hi + pad, padding=0)
            self._x_user_interacting = False
        elif len(data_f) > 0:
            self._x_user_interacting = True
            self._plot_widget.setYRange(self._y_manual_min, self._y_manual_max, padding=0)
            self._x_user_interacting = False

        latest = int(data[-1])
        self._lbl_latest.setText(f"Latest: {latest}")
        self._lbl_range.setText(f"Range: {int(np.min(visible_data))}..{int(np.max(visible_data))}")

    def _visible_data(self, data: np.ndarray, t: np.ndarray) -> np.ndarray:
        if len(data) == 0:
            return data

        x_min, x_max = self._plot_widget.getViewBox().viewRange()[0]
        mask = (t >= x_min) & (t <= x_max)
        if np.any(mask):
            return data[mask]
        return data

    # ── 统计 ──────────────────────────────────────────────

    def update_stats(self, fps: float, sample_rate_hz: float, frame_count: int, crc_errors: int, seq_gaps: int, resync_count: int = 0, short_frames: int = 0):
        """更新统计信息"""
        if sample_rate_hz >= MIN_EFFECTIVE_SAMPLE_RATE_HZ:
            self._effective_sample_rate_hz = sample_rate_hz
            self._ensure_buffer_capacity()
            self._plot_dirty = True

        self._lbl_fps.setText(f"FPS: {fps:.1f}")
        self._lbl_sample_rate.setText(f"Rate: {sample_rate_hz:.1f} Hz")
        self._lbl_frames.setText(f"Frames: {frame_count}")
        self._lbl_crc_err.setText(f"CRC: {crc_errors}")
        self._lbl_short.setText(f"Short: {short_frames}")
        self._lbl_seq_gap.setText(f"SeqGap: {seq_gaps}")
        self._lbl_resync.setText(f"Resync: {resync_count}")
        if crc_errors > 0:
            self._lbl_crc_err.setStyleSheet("color: #f55; font-size: 11px; padding: 2px 8px;")
        else:
            self._lbl_crc_err.setStyleSheet("color: #aaa; font-size: 11px; padding: 2px 8px;")
        if short_frames > 0:
            self._lbl_short.setStyleSheet("color: #f55; font-size: 11px; padding: 2px 8px;")
        else:
            self._lbl_short.setStyleSheet("color: #aaa; font-size: 11px; padding: 2px 8px;")
        if seq_gaps > 0:
            self._lbl_seq_gap.setStyleSheet("color: #fa0; font-size: 11px; padding: 2px 8px;")
        else:
            self._lbl_seq_gap.setStyleSheet("color: #aaa; font-size: 11px; padding: 2px 8px;")
        duration = self._total_samples / self._effective_sample_rate_hz
        visible_duration = self._data_len() / self._effective_sample_rate_hz
        self._lbl_duration.setText(f"Duration: {duration:.1f} s / Buf: {visible_duration:.1f} s")

        warnings = []
        if seq_gaps > 0:
            warnings.append(f"Seq Gap: {seq_gaps} (丢帧 {seq_gaps} 次)")
        if crc_errors > 0:
            warnings.append(f"CRC Error: {crc_errors}")
        if short_frames > 0:
            warnings.append(f"Short Frame: {short_frames}")
        if resync_count > 0:
            warnings.append(f"Resync: {resync_count}")
        if warnings:
            self._warn_banner.setText("DATA INTEGRITY WARNING: " + " | ".join(warnings))
            self._warn_banner.setVisible(True)
        else:
            self._warn_banner.setVisible(False)

    # ── 清理 ──────────────────────────────────────────────

    def clear(self):
        """清空缓冲区"""
        self._buffer = np.zeros(DISPLAY_BUFFER_SIZE, dtype=np.uint16)
        self._write_pos = 0
        self._total_samples = 0
        self._frame_history = []
        self._effective_sample_rate_hz = float(ADC_SAMPLE_RATE_HZ)
        self._y_auto_fit = True
        self._y_manual_min = Y_MANUAL_MIN_DEFAULT
        self._y_manual_max = Y_MANUAL_MAX_DEFAULT
        self._plot_dirty = False
        self._curve.setData([], [])
        self._x_auto_scroll = True
        self._warn_banner.setVisible(False)
        self._empty_label.setVisible(True)
        self._lbl_fps.setText("FPS: --")
        self._lbl_sample_rate.setText("Rate: -- Hz")
        self._lbl_frames.setText("Frames: 0")
        self._lbl_crc_err.setText("CRC: 0")
        self._lbl_crc_err.setStyleSheet("color: #aaa; font-size: 11px; padding: 2px 8px;")
        self._lbl_short.setText("Short: 0")
        self._lbl_short.setStyleSheet("color: #aaa; font-size: 11px; padding: 2px 8px;")
        self._lbl_seq_gap.setText("SeqGap: 0")
        self._lbl_seq_gap.setStyleSheet("color: #aaa; font-size: 11px; padding: 2px 8px;")
        self._lbl_resync.setText("Resync: 0")
        self._lbl_latest.setText("Latest: --")
        self._lbl_range.setText("Range: --")
        self._hide_cursor()
        self._lbl_view.setText("View: Follow")
        self._lbl_duration.setText("Duration: 0.0 s")

    def get_buffer_data(self) -> np.ndarray:
        """获取当前缓冲区中的有序数据 (用于保存)"""
        return self._ordered_buffer_data().copy()

    def get_buffer_snapshot(self) -> BufferSnapshot:
        data = self._ordered_buffer_data().copy()
        first_sample_index = max(0, self._total_samples - len(data))
        return BufferSnapshot(
            data=data,
            frames=[BufferFrame(frame.seq, frame.start_sample_index, frame.samples.copy()) for frame in self._frame_history],
            first_sample_index=first_sample_index,
            total_samples=self._total_samples,
            sample_rate_hz=self._effective_sample_rate_hz,
        )

    def apply_theme_colors(self, colors: dict):
        """应用主题颜色"""
        self._theme_colors = colors
        
        # 更新曲线颜色
        self._curve.setPen(pg.mkPen(color=colors["curve"], width=1.4))
        
        # 更新光标颜色
        self._v_cursor.setPen(pg.mkPen(colors["cursor_v"], width=1))
        self._h_cursor.setPen(pg.mkPen(colors["cursor_h"], width=1))
        
        # 更新网格
        self._plot_widget.showGrid(x=True, y=True, alpha=colors["grid_alpha"])
        
        # 更新坐标轴颜色
        self._plot_widget.getAxis("left").setPen(pg.mkPen(colors["axis"]))
        self._plot_widget.getAxis("bottom").setPen(pg.mkPen(colors["axis"]))
        self._plot_widget.getAxis("left").setTextPen(pg.mkPen(colors["text"]))
        self._plot_widget.getAxis("bottom").setTextPen(pg.mkPen(colors["text"]))
    
    def set_performance_optimizer(self, optimizer):
        """设置性能优化器 (V2.3)"""
        self._perf_optimizer = optimizer
        if optimizer:
            # 更新刷新间隔
            interval = optimizer.get_refresh_interval_ms()
            self._plot_timer.setInterval(interval)
            self._downsample_enabled = optimizer.is_downsampling_enabled()
    
    def enable_downsampling(self, enabled: bool):
        """启用/禁用降采样 (V2.3)"""
        self._downsample_enabled = enabled
        self._plot_dirty = True
    
    def is_downsampling_enabled(self) -> bool:
        """是否启用降采样 (V2.3)"""
        return self._downsample_enabled

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_empty_label"):
            self._empty_label.setGeometry(self._plot_widget.rect())

    def eventFilter(self, watched, event):
        if watched == self._plot_widget.viewport() and event.type() == QEvent.Type.Leave:
            self._hide_cursor()
        return super().eventFilter(watched, event)
