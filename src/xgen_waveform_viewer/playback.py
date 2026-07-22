"""
数据回放模块

V2.4 新增:
- 支持录制文件回放
- 变速播放 (0.1x ~ 10x)
- 播放进度条和控制
- 支持 BIN 和 CSV 格式
"""

from __future__ import annotations

import struct
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

import numpy as np
from PyQt6.QtCore import QObject, QThread, pyqtSignal

from .config import BIN_MAGIC, BIN_VERSION


PlaybackState = Literal["stopped", "playing", "paused"]


@dataclass
class PlaybackInfo:
    """回放信息"""
    path: str
    format: str
    sample_rate_hz: int
    total_frames: int
    total_samples: int
    duration_s: float
    current_frame: int = 0
    current_sample: int = 0
    current_time_s: float = 0.0
    state: PlaybackState = "stopped"
    speed: float = 1.0


class PlaybackReader(QThread):
    """
    回放读取线程
    
    从录制文件中读取数据并按照原始采样率（或变速）回放
    """
    
    # 信号
    frame_ready = pyqtSignal(np.ndarray, int)  # (samples, seq)
    progress_updated = pyqtSignal(float)  # 进度百分比 0-100
    playback_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._file_path: Path | None = None
        self._file_format: str = "bin"
        self._sample_rate_hz: int = 0
        self._playback_speed: float = 1.0
        self._file = None
        self._should_stop = False
        self._should_pause = False
        self._info: PlaybackInfo | None = None
        
        # BIN 格式专用
        self._bin_total_frames = 0
        self._bin_header_size = 24
        
        # CSV 格式专用
        self._csv_lines: list[str] = []
        self._csv_current_line = 0
    
    def load_file(self, path: str | Path) -> PlaybackInfo:
        """
        加载回放文件并解析元数据
        
        返回: PlaybackInfo 对象
        """
        self._file_path = Path(path)
        
        # 根据扩展名判断格式
        if self._file_path.suffix.lower() == ".csv":
            return self._load_csv()
        elif self._file_path.suffix.lower() == ".bin":
            return self._load_bin()
        else:
            raise ValueError(f"不支持的文件格式: {self._file_path.suffix}")
    
    def _load_bin(self) -> PlaybackInfo:
        """加载 BIN 格式文件"""
        try:
            with open(self._file_path, "rb") as f:
                # 读取文件头
                header = f.read(24)
                if len(header) < 24:
                    raise ValueError("BIN 文件头不完整（需要24字节）")
                
                magic, version, frame_count, sample_rate, segment_idx, timestamp = struct.unpack(
                    "<4sIIIIq", header
                )
                
                if magic != BIN_MAGIC:
                    raise ValueError(f"无效的 BIN 文件魔数: {magic} (期望 {BIN_MAGIC})")
                
                if version != BIN_VERSION:
                    raise ValueError(f"不支持的 BIN 版本: {version} (期望 {BIN_VERSION})")
                
                if sample_rate == 0:
                    raise ValueError("BIN 文件采样率为0")
                
                self._file_format = "bin"
                self._sample_rate_hz = sample_rate
                self._bin_total_frames = frame_count
                
                # 统计总采样点数（需要遍历文件）
                total_samples = 0
                actual_frame_count = 0
                while True:
                    frame_header = f.read(6)  # seq(4) + count(2)
                    if len(frame_header) < 6:
                        break
                    seq, count = struct.unpack("<IH", frame_header)
                    
                    # 验证采样点数是否合理
                    if count > 4096:  # MAX_FRAME_SAMPLES
                        raise ValueError(f"帧 {seq} 的采样点数异常: {count} (超过4096)")
                    
                    total_samples += count
                    actual_frame_count += 1
                    f.seek(count * 2, 1)  # 跳过数据
                
                # 验证帧数是否一致
                if actual_frame_count != frame_count:
                    import warnings
                    warnings.warn(f"实际帧数 ({actual_frame_count}) 与文件头声明 ({frame_count}) 不一致")
                
                duration = total_samples / sample_rate if sample_rate > 0 else 0
                
                self._info = PlaybackInfo(
                    path=str(self._file_path),
                    format="bin",
                    sample_rate_hz=sample_rate,
                    total_frames=actual_frame_count,
                    total_samples=total_samples,
                    duration_s=duration,
                )
                
                return self._info
                
        except FileNotFoundError:
            raise ValueError(f"文件不存在: {self._file_path}")
        except PermissionError:
            raise ValueError(f"没有读取权限: {self._file_path}")
        except struct.error as e:
            raise ValueError(f"BIN 文件格式错误: {e}")
    
    def _load_csv(self) -> PlaybackInfo:
        """加载 CSV 格式文件"""
        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            raise ValueError(f"文件不存在: {self._file_path}")
        except PermissionError:
            raise ValueError(f"没有读取权限: {self._file_path}")
        except UnicodeDecodeError:
            raise ValueError("CSV 文件编码错误（需要 UTF-8 编码）")
        
        self._csv_lines = []
        sample_rate = 0
        
        # 解析头部注释
        for line in lines:
            line = line.strip()
            if line.startswith("# sample_rate=") or line.startswith("#sample_rate="):
                try:
                    # 修复：更健壮的解析，支持多种格式
                    # 格式1: # sample_rate=400Hz
                    # 格式2: # sample_rate=400Hz, other_info
                    # 格式3: # sample_rate: 400 Hz
                    # 格式4: #sample_rate=400Hz
                    if "=" in line:
                        rate_part = line.split("=")[1].split(",")[0]  # 取逗号前的部分
                    elif ":" in line:
                        rate_part = line.split(":")[1].split(",")[0]
                    else:
                        raise ValueError("无法找到采样率分隔符")
                    
                    # 移除Hz后缀和空格
                    rate_str = rate_part.replace("Hz", "").replace("hz", "").replace("HZ", "").strip()
                    sample_rate = int(float(rate_str))  # 支持浮点数转换
                    
                except (ValueError, IndexError) as e:
                    raise ValueError(
                        f"无法解析采样率行: '{line}'\n"
                        f"期望格式: '# sample_rate=400Hz' 或 '# sample_rate=400'\n"
                        f"解析错误: {str(e)}"
                    )
            elif line.startswith("#"):
                continue
            elif line:
                self._csv_lines.append(line)
        
        if not self._csv_lines:
            raise ValueError("CSV 文件无有效数据行")
        
        if sample_rate <= 0:
            raise ValueError("CSV 文件缺少有效的采样率信息（需要注释: # sample_rate=XXXHz）")
        
        self._file_format = "csv"
        self._sample_rate_hz = sample_rate
        self._csv_current_line = 0
        
        # 统计帧数和采样点数
        total_samples = len(self._csv_lines)
        
        # 统计帧数（通过 seq 变化）
        frame_count = 0
        last_seq = None
        for line in self._csv_lines:
            parts = line.split(",")
            if len(parts) >= 1:
                try:
                    seq = int(parts[0])
                    if seq != last_seq:
                        frame_count += 1
                        last_seq = seq
                except (ValueError, IndexError):
                    continue  # 跳过无效行
        
        if frame_count == 0:
            raise ValueError("CSV 文件无法解析出有效的数据帧")
        
        duration = total_samples / sample_rate
        
        self._info = PlaybackInfo(
            path=str(self._file_path),
            format="csv",
            sample_rate_hz=sample_rate,
            total_frames=frame_count,
            total_samples=total_samples,
            duration_s=duration,
        )
        
        return self._info
    
    def set_speed(self, speed: float):
        """设置回放速度 (0.1 ~ 10.0)"""
        self._playback_speed = max(0.1, min(10.0, speed))
        if self._info:
            self._info.speed = self._playback_speed
    
    def get_info(self) -> PlaybackInfo | None:
        """获取回放信息"""
        return self._info
    
    def pause(self):
        """暂停回放"""
        self._should_pause = True
        if self._info:
            self._info.state = "paused"
    
    def resume(self):
        """恢复回放"""
        self._should_pause = False
        if self._info:
            self._info.state = "playing"
    
    def stop(self):
        """停止回放"""
        self._should_stop = True
        if self._info:
            self._info.state = "stopped"
        self.wait()
    
    def run(self):
        """回放线程主循环"""
        if not self._file_path or not self._info:
            self.error_occurred.emit("未加载回放文件")
            return
        
        self._should_stop = False
        self._should_pause = False
        self._info.state = "playing"
        
        try:
            if self._file_format == "bin":
                self._playback_bin()
            else:
                self._playback_csv()
        except Exception as e:
            self.error_occurred.emit(f"回放错误: {e}")
        finally:
            self._info.state = "stopped"
            if self._file:
                self._file.close()
                self._file = None
    
    def _playback_bin(self):
        """回放 BIN 格式"""
        self._file = open(self._file_path, "rb")
        self._file.seek(self._bin_header_size)  # 跳过文件头
        
        frame_idx = 0
        sample_idx = 0
        start_time = time.perf_counter()
        
        # 配置批处理大小（每批采样点数）
        batch_size = max(1, min(10, self._sample_rate_hz // 100))  # 根据采样率自适应
        
        while not self._should_stop:
            # 处理暂停
            while self._should_pause and not self._should_stop:
                time.sleep(0.1)
            
            if self._should_stop:
                break
            
            # 读取帧头
            frame_header = self._file.read(6)
            if len(frame_header) < 6:
                break  # 文件结束
            
            seq, count = struct.unpack("<IH", frame_header)
            
            # 读取采样数据
            data_bytes = self._file.read(count * 2)
            if len(data_bytes) < count * 2:
                break
            
            all_samples = np.frombuffer(data_bytes, dtype=np.uint16)
            
            # 将帧拆分为小批次回放，保证流畅度
            for i in range(0, len(all_samples), batch_size):
                if self._should_stop:
                    break
                
                # 处理暂停
                while self._should_pause and not self._should_stop:
                    time.sleep(0.1)
                
                if self._should_stop:
                    break
                
                # 获取当前批次
                batch = all_samples[i:i+batch_size]
                
                # 发送数据
                self.frame_ready.emit(batch, seq)
                
                # 更新进度
                sample_idx += len(batch)
                self._info.current_sample = sample_idx
                self._info.current_time_s = sample_idx / self._sample_rate_hz
                
                # 精确时序控制
                elapsed = time.perf_counter() - start_time
                expected = sample_idx / self._sample_rate_hz / self._playback_speed
                sleep_time = expected - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
            
            # 更新帧进度
            frame_idx += 1
            self._info.current_frame = frame_idx
            
            # 发送进度更新（每帧更新一次）
            progress = (sample_idx / self._info.total_samples * 100) if self._info.total_samples > 0 else 0
            self.progress_updated.emit(progress)
        
        self.playback_finished.emit()
    
    def _playback_csv(self):
        """回放 CSV 格式"""
        self._csv_current_line = 0
        
        # 按帧组织数据
        frames: dict[int, list[int]] = {}
        for line in self._csv_lines:
            parts = line.split(",")
            if len(parts) < 3:
                continue
            
            try:
                seq = int(parts[0])
                adc_value = int(parts[2])
                
                if seq not in frames:
                    frames[seq] = []
                frames[seq].append(adc_value)
            except (ValueError, IndexError):
                continue  # 跳过无效行
        
        # 按序号排序
        sorted_seqs = sorted(frames.keys())
        
        frame_idx = 0
        sample_idx = 0
        start_time = time.perf_counter()
        
        # 配置批处理大小（每批采样点数）
        # 批处理可以平衡流畅度和性能
        batch_size = max(1, min(10, self._sample_rate_hz // 100))  # 根据采样率自适应
        
        for seq in sorted_seqs:
            if self._should_stop:
                break
            
            samples_in_frame = frames[seq]
            
            # 将帧拆分为小批次回放，保证流畅度
            for i in range(0, len(samples_in_frame), batch_size):
                if self._should_stop:
                    break
                
                # 处理暂停
                while self._should_pause and not self._should_stop:
                    time.sleep(0.1)
                
                if self._should_stop:
                    break
                
                # 获取当前批次
                batch = samples_in_frame[i:i+batch_size]
                samples = np.array(batch, dtype=np.uint16)
                
                # 发送数据
                self.frame_ready.emit(samples, seq)
                
                # 更新进度
                sample_idx += len(samples)
                self._info.current_sample = sample_idx
                self._info.current_time_s = sample_idx / self._sample_rate_hz
                
                # 精确时序控制
                elapsed = time.perf_counter() - start_time
                expected = sample_idx / self._sample_rate_hz / self._playback_speed
                sleep_time = expected - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
            
            # 更新帧进度
            frame_idx += 1
            self._info.current_frame = frame_idx
            
            # 发送进度更新（每帧更新一次，避免过于频繁）
            progress = (sample_idx / self._info.total_samples * 100) if self._info.total_samples > 0 else 0
            self.progress_updated.emit(progress)
        
        self.playback_finished.emit()
