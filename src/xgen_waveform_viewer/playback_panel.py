"""
回放控制面板

V2.4 新增:
- 回放控制 UI
- 进度条显示
- 速度控制
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QSlider,
    QComboBox,
    QFileDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal

from .playback import PlaybackReader, PlaybackInfo


class PlaybackPanel(QWidget):
    """回放控制面板"""
    
    # 信号
    file_loaded = pyqtSignal(PlaybackInfo)
    playback_started = pyqtSignal()
    playback_paused = pyqtSignal()
    playback_resumed = pyqtSignal()
    playback_stopped = pyqtSignal()
    
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._reader: PlaybackReader | None = None
        self._info: PlaybackInfo | None = None
        self._is_playing = False
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 标题
        title_label = QLabel("📼 数据回放")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # 文件选择
        file_layout = QHBoxLayout()
        self._file_label = QLabel("未选择文件")
        self._file_label.setStyleSheet("color: #666;")
        file_layout.addWidget(self._file_label, 1)
        
        self._btn_open = QPushButton("打开文件...")
        self._btn_open.clicked.connect(self._on_open_file)
        file_layout.addWidget(self._btn_open)
        
        layout.addLayout(file_layout)
        
        # 播放控制
        control_layout = QHBoxLayout()
        
        self._btn_play = QPushButton("▶ 播放")
        self._btn_play.setEnabled(False)
        self._btn_play.clicked.connect(self._on_play_clicked)
        control_layout.addWidget(self._btn_play)
        
        self._btn_pause = QPushButton("⏸ 暂停")
        self._btn_pause.setEnabled(False)
        self._btn_pause.clicked.connect(self._on_pause_clicked)
        control_layout.addWidget(self._btn_pause)
        
        self._btn_stop = QPushButton("⏹ 停止")
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._on_stop_clicked)
        control_layout.addWidget(self._btn_stop)
        
        layout.addLayout(control_layout)
        
        # 速度控制
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("速度:"))
        
        self._speed_combo = QComboBox()
        self._speed_combo.addItems([
            "0.1x", "0.25x", "0.5x", "0.75x",
            "1x", "1.5x", "2x", "3x", "5x", "10x"
        ])
        self._speed_combo.setCurrentText("1x")
        self._speed_combo.currentTextChanged.connect(self._on_speed_changed)
        self._speed_combo.setEnabled(False)
        speed_layout.addWidget(self._speed_combo)
        
        speed_layout.addStretch()
        layout.addLayout(speed_layout)
        
        # 进度条
        progress_layout = QVBoxLayout()
        
        self._progress_slider = QSlider(Qt.Orientation.Horizontal)
        self._progress_slider.setRange(0, 1000)
        self._progress_slider.setValue(0)
        self._progress_slider.setEnabled(False)
        progress_layout.addWidget(self._progress_slider)
        
        self._progress_label = QLabel("00:00 / 00:00")
        self._progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self._progress_label)
        
        layout.addLayout(progress_layout)
        
        # 文件信息
        info_layout = QVBoxLayout()
        info_layout.addWidget(QLabel("文件信息:"))
        
        self._info_label = QLabel("无")
        self._info_label.setStyleSheet("color: #666; font-size: 12px;")
        self._info_label.setWordWrap(True)
        info_layout.addWidget(self._info_label)
        
        layout.addLayout(info_layout)
        
        layout.addStretch()
    
    def _on_open_file(self):
        """打开回放文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择回放文件",
            str(Path.home()),
            "录制文件 (*.bin *.csv);;BIN 文件 (*.bin);;CSV 文件 (*.csv);;所有文件 (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            # 创建读取器
            self._reader = PlaybackReader(self)
            
            # 加载文件
            self._info = self._reader.load_file(file_path)
            
            # 更新 UI
            self._file_label.setText(Path(file_path).name)
            self._file_label.setStyleSheet("color: #333;")
            
            self._update_info_display()
            
            # 启用控件
            self._btn_play.setEnabled(True)
            self._speed_combo.setEnabled(True)
            self._progress_slider.setEnabled(True)
            
            # 发送信号
            self.file_loaded.emit(self._info)
            
        except Exception as e:
            self._file_label.setText(f"加载失败: {e}")
            self._file_label.setStyleSheet("color: #c00;")
    
    def _update_info_display(self):
        """更新文件信息显示"""
        if not self._info:
            self._info_label.setText("无")
            return
        
        info_text = f"""
格式: {self._info.format.upper()}
采样率: {self._info.sample_rate_hz} Hz
总帧数: {self._info.total_frames:,}
总采样点: {self._info.total_samples:,}
时长: {self._format_time(self._info.duration_s)}
        """.strip()
        
        self._info_label.setText(info_text)
    
    def _on_play_clicked(self):
        """播放按钮点击"""
        if not self._reader or not self._info:
            return
        
        if self._is_playing:
            # 恢复播放
            self._reader.resume()
            self._btn_play.setText("▶ 播放")
            self._btn_pause.setEnabled(True)
            self.playback_resumed.emit()
        else:
            # 开始播放
            # 连接信号
            self._reader.progress_updated.connect(self._on_progress_updated)
            self._reader.playback_finished.connect(self._on_playback_finished)
            
            # 启动线程
            self._reader.start()
            self._is_playing = True
            
            # 更新 UI
            self._btn_play.setEnabled(False)
            self._btn_pause.setEnabled(True)
            self._btn_stop.setEnabled(True)
            self._btn_open.setEnabled(False)
            
            self.playback_started.emit()
    
    def _on_pause_clicked(self):
        """暂停按钮点击"""
        if not self._reader or not self._is_playing:
            return
        
        self._reader.pause()
        
        # 更新 UI
        self._btn_play.setText("▶ 恢复")
        self._btn_play.setEnabled(True)
        self._btn_pause.setEnabled(False)
        
        self.playback_paused.emit()
    
    def _on_stop_clicked(self):
        """停止按钮点击"""
        if not self._reader:
            return
        
        self._reader.stop()
        self._is_playing = False
        
        # 更新 UI
        self._btn_play.setText("▶ 播放")
        self._btn_play.setEnabled(True)
        self._btn_pause.setEnabled(False)
        self._btn_stop.setEnabled(False)
        self._btn_open.setEnabled(True)
        
        # 重置进度
        self._progress_slider.setValue(0)
        self._update_progress_label(0, self._info.duration_s if self._info else 0)
        
        self.playback_stopped.emit()
    
    def _on_speed_changed(self, text: str):
        """速度变更"""
        if not self._reader:
            return
        
        # 解析速度值
        speed_str = text.replace("x", "")
        try:
            speed = float(speed_str)
            self._reader.set_speed(speed)
        except ValueError:
            pass
    
    def _on_progress_updated(self, progress: float):
        """进度更新"""
        # 更新进度条
        self._progress_slider.setValue(int(progress * 10))
        
        # 更新时间显示
        if self._info:
            current_time = progress / 100 * self._info.duration_s
            self._update_progress_label(current_time, self._info.duration_s)
    
    def _on_playback_finished(self):
        """回放结束"""
        self._on_stop_clicked()
    
    def _update_progress_label(self, current_s: float, total_s: float):
        """更新进度标签"""
        current_str = self._format_time(current_s)
        total_str = self._format_time(total_s)
        self._progress_label.setText(f"{current_str} / {total_str}")
    
    @staticmethod
    def _format_time(seconds: float) -> str:
        """格式化时间显示"""
        if seconds < 60:
            return f"{int(seconds):02d}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes:02d}:{secs:02d}"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            secs = int(seconds % 60)
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def get_reader(self) -> PlaybackReader | None:
        """获取回放读取器"""
        return self._reader
