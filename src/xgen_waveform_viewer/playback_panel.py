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
    QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QCloseEvent

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
        
        # 设置为独立窗口，带完整标题栏和关闭按钮
        self.setWindowFlags(
            Qt.WindowType.Window |  # 独立窗口
            Qt.WindowType.WindowCloseButtonHint |  # 关闭按钮
            Qt.WindowType.WindowMinimizeButtonHint  # 最小化按钮
        )
        
        # 窗口关闭时不自动删除，以便重新打开
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        
        self._reader: PlaybackReader | None = None
        self._info: PlaybackInfo | None = None
        self._playback_state: str = "stopped"  # "stopped", "playing", "paused"
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # 标题
        title_label = QLabel("数据回放")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        layout.addWidget(title_label)
        
        # 状态指示器
        self._status_indicator = QLabel("● 已停止")
        self._status_indicator.setStyleSheet("""
            QLabel {
                padding: 8px 15px;
                border-radius: 4px;
                background-color: #e0e0e0;
                color: #757575;
                font-weight: bold;
                font-size: 13px;
            }
        """)
        self._status_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_indicator)
        
        # 分隔线
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.HLine)
        separator1.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator1)
        
        # 文件选择
        file_group_label = QLabel("文件:")
        file_group_label.setStyleSheet("font-weight: bold; color: #555;")
        layout.addWidget(file_group_label)
        
        file_layout = QHBoxLayout()
        self._file_label = QLabel("未选择文件")
        self._file_label.setStyleSheet("color: #999; padding: 5px;")
        self._file_label.setWordWrap(True)
        file_layout.addWidget(self._file_label, 1)
        
        self._btn_open = QPushButton("浏览...")
        self._btn_open.setMinimumWidth(80)
        self._btn_open.clicked.connect(self._on_open_file)
        file_layout.addWidget(self._btn_open)
        
        layout.addLayout(file_layout)
        
        # 播放控制
        control_layout = QHBoxLayout()
        control_layout.setSpacing(8)
        
        # 移除emoji图标，使用纯文字
        self._btn_play = QPushButton("播放")
        self._btn_play.setMinimumHeight(40)
        self._btn_play.setEnabled(False)
        self._btn_play.clicked.connect(self._on_play_clicked)
        control_layout.addWidget(self._btn_play)
        
        self._btn_pause = QPushButton("暂停")
        self._btn_pause.setMinimumHeight(40)
        self._btn_pause.setEnabled(False)
        self._btn_pause.clicked.connect(self._on_pause_clicked)
        control_layout.addWidget(self._btn_pause)
        
        self._btn_stop = QPushButton("停止")
        self._btn_stop.setMinimumHeight(40)
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._on_stop_clicked)
        control_layout.addWidget(self._btn_stop)
        
        layout.addLayout(control_layout)
        
        # 速度控制
        speed_layout = QHBoxLayout()
        speed_label = QLabel("播放速度:")
        speed_label.setStyleSheet("font-weight: bold; color: #555;")
        speed_layout.addWidget(speed_label)
        
        self._speed_combo = QComboBox()
        self._speed_combo.addItems([
            "0.1x", "0.25x", "0.5x", "0.75x",
            "1x", "1.5x", "2x", "3x", "5x", "10x"
        ])
        self._speed_combo.setCurrentText("1x")
        self._speed_combo.currentTextChanged.connect(self._on_speed_changed)
        self._speed_combo.setEnabled(False)
        self._speed_combo.setMinimumWidth(100)
        speed_layout.addWidget(self._speed_combo)
        
        speed_layout.addStretch()
        layout.addLayout(speed_layout)
        
        # 进度条
        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(5)
        
        self._progress_slider = QSlider(Qt.Orientation.Horizontal)
        self._progress_slider.setRange(0, 1000)
        self._progress_slider.setValue(0)
        self._progress_slider.setEnabled(False)
        self._progress_slider.setMinimumHeight(30)
        progress_layout.addWidget(self._progress_slider)
        
        self._progress_label = QLabel("00:00 / 00:00")
        self._progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._progress_label.setStyleSheet("font-family: monospace; font-size: 13px;")
        progress_layout.addWidget(self._progress_label)
        
        layout.addLayout(progress_layout)
        
        # 文件信息
        info_header = QLabel("文件信息:")
        info_header.setStyleSheet("font-weight: bold; color: #555;")
        layout.addWidget(info_header)
        
        self._info_label = QLabel("无")
        self._info_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 12px;
                background-color: #f5f5f5;
                padding: 10px;
                border-radius: 4px;
            }
        """)
        self._info_label.setWordWrap(True)
        layout.addWidget(self._info_label)
        
        # 快捷键提示
        shortcut_hint = QLabel("快捷键: 空格=播放/暂停 | Esc=停止")
        shortcut_hint.setStyleSheet("color: #999; font-size: 11px; font-style: italic;")
        shortcut_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(shortcut_hint)
        
        layout.addStretch()
    
    def _on_open_file(self):
        """打开回放文件"""
        # 先停止并清理旧的回放
        if self._reader is not None:
            if self._reader.isRunning():
                self._reader.stop()
            self._reader.deleteLater()
            self._reader = None
            self._playback_state = "stopped"
        
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
            file_name = Path(file_path).name
            self._file_label.setText(file_name)
            self._file_label.setStyleSheet("color: #333; padding: 5px;")
            self._file_label.setToolTip(str(file_path))  # 完整路径显示在工具提示中
            
            self._update_info_display()
            self._update_status_indicator()  # 更新状态显示
            
            # 启用控件
            self._btn_play.setEnabled(True)
            self._speed_combo.setEnabled(True)
            # 修复：进度条保持禁用，因为还未实现seek功能
            # self._progress_slider.setEnabled(True)
            
            # 应用当前选择的速度
            current_speed_text = self._speed_combo.currentText()
            try:
                speed = float(current_speed_text.replace("x", ""))
                self._reader.set_speed(speed)
            except ValueError:
                self._reader.set_speed(1.0)
            
            # 发送信号
            self.file_loaded.emit(self._info)
            
        except Exception as e:
            self._file_label.setText(f"加载失败: {e}")
            self._file_label.setStyleSheet("color: #c00;")
            
            # 修复：重置状态和UI
            self._reader = None
            self._info = None
            self._playback_state = "stopped"
            
            # 禁用所有控件
            self._btn_play.setEnabled(False)
            self._btn_pause.setEnabled(False)
            self._btn_stop.setEnabled(False)
            self._speed_combo.setEnabled(False)
            self._progress_slider.setEnabled(False)
            
            # 重置显示
            self._info_label.setText("无")
            self._progress_slider.setValue(0)
            self._progress_label.setText("00:00 / 00:00")
    
    def _update_info_display(self):
        """更新文件信息显示"""
        if not self._info:
            self._info_label.setText("无")
            return
        
        # 修复：使用更清晰的格式化方式
        info_text = (
            f"格式: {self._info.format.upper()}\n"
            f"采样率: {self._info.sample_rate_hz} Hz\n"
            f"总帧数: {self._info.total_frames:,}\n"
            f"总采样点: {self._info.total_samples:,}\n"
            f"时长: {self._format_time(self._info.duration_s)}"
        )
        
        self._info_label.setText(info_text)
    
    def _on_play_clicked(self):
        """播放按钮点击"""
        if not self._reader or not self._info:
            return
        
        if self._playback_state == "paused":
            # 恢复播放
            self._reader.resume()
            self._playback_state = "playing"
            
            # 修复：恢复播放后重置按钮文本并禁用
            self._btn_play.setText("播放")
            self._btn_play.setEnabled(False)
            self._btn_pause.setEnabled(True)
            
            self._update_status_indicator()  # 更新状态显示
            self.playback_resumed.emit()
        elif self._playback_state == "stopped":
            # 开始播放
            # 连接信号
            self._reader.progress_updated.connect(self._on_progress_updated)
            self._reader.playback_finished.connect(self._on_playback_finished)
            
            # 启动线程
            self._reader.start()
            self._playback_state = "playing"
            
            # 更新 UI
            self._btn_play.setEnabled(False)
            self._btn_pause.setEnabled(True)
            self._btn_stop.setEnabled(True)
            self._btn_open.setEnabled(False)
            
            self._update_status_indicator()  # 更新状态显示
            self.playback_started.emit()
    
    def _on_pause_clicked(self):
        """暂停按钮点击"""
        if not self._reader or self._playback_state != "playing":
            return
        
        self._reader.pause()
        self._playback_state = "paused"
        
        # 更新 UI
        self._btn_play.setText("恢复")
        self._btn_play.setEnabled(True)
        self._btn_pause.setEnabled(False)
        
        self._update_status_indicator()  # 更新状态显示
        self.playback_paused.emit()
    
    def _on_stop_clicked(self):
        """停止按钮点击"""
        if not self._reader:
            return
        
        self._reader.stop()
        self._playback_state = "stopped"
        
        # 更新 UI
        self._btn_play.setText("播放")
        self._btn_play.setEnabled(True)
        self._btn_pause.setEnabled(False)
        self._btn_stop.setEnabled(False)
        self._btn_open.setEnabled(True)
        
        # 重置进度
        self._progress_slider.setValue(0)
        self._update_progress_label(0, self._info.duration_s if self._info else 0)
        
        self._update_status_indicator()  # 更新状态显示
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
        """格式化时间显示（统一格式）"""
        if seconds < 3600:
            # 小于1小时：MM:SS
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes:02d}:{secs:02d}"
        else:
            # 大于1小时：HH:MM:SS
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            secs = int(seconds % 60)
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def get_reader(self) -> PlaybackReader | None:
        """获取回放读取器"""
        return self._reader
    
    def _update_status_indicator(self):
        """更新状态指示器"""
        if self._playback_state == "stopped":
            self._status_indicator.setText("● 已停止")
            self._status_indicator.setStyleSheet("""
                QLabel {
                    padding: 8px 15px;
                    border-radius: 4px;
                    background-color: #e0e0e0;
                    color: #757575;
                    font-weight: bold;
                    font-size: 13px;
                }
            """)
        elif self._playback_state == "playing":
            self._status_indicator.setText("● 播放中")
            self._status_indicator.setStyleSheet("""
                QLabel {
                    padding: 8px 15px;
                    border-radius: 4px;
                    background-color: #4caf50;
                    color: white;
                    font-weight: bold;
                    font-size: 13px;
                }
            """)
        elif self._playback_state == "paused":
            self._status_indicator.setText("❚❚ 已暂停")
            self._status_indicator.setStyleSheet("""
                QLabel {
                    padding: 8px 15px;
                    border-radius: 4px;
                    background-color: #ff9800;
                    color: white;
                    font-weight: bold;
                    font-size: 13px;
                }
            """)
    
    def keyPressEvent(self, event: QKeyEvent):
        """键盘事件处理"""
        if event.key() == Qt.Key.Key_Space:
            # 空格键：播放/暂停切换
            if self._playback_state == "playing":
                self._on_pause_clicked()
            elif self._playback_state == "paused":
                self._on_play_clicked()
            elif self._playback_state == "stopped" and self._btn_play.isEnabled():
                self._on_play_clicked()
            event.accept()
        elif event.key() == Qt.Key.Key_Escape or event.key() == Qt.Key.Key_S:
            # ESC键或S键：停止
            if self._playback_state != "stopped" and self._btn_stop.isEnabled():
                self._on_stop_clicked()
            event.accept()
        else:
            super().keyPressEvent(event)
    
    def closeEvent(self, event: QCloseEvent):
        """窗口关闭事件处理"""
        # 如果正在播放，先停止
        if self._playback_state != "stopped":
            self._on_stop_clicked()
        
        # 接受关闭事件，隐藏窗口
        event.accept()
